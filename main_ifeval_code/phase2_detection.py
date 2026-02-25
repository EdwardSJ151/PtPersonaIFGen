"""
Phase 2: Constraint Type Detection

Replicates IFEvalInstructionIdListAssignator from pipeline/ifeval_tasks.py (lines 14-40).
Takes each instruction and classifies which of the 25 IFEval constraint types are present.

System Prompt: pipeline/system_prompts.py -> IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT (lines 55-93)
JSON Schema: pipeline/json_schemas.py -> IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA (lines 154-193)
Generation Params: pipeline/pipeline.py (lines 207-209)

Input Format (from format_input, ifeval_tasks.py lines 19-28):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": instruction}
    ]
"""

import argparse
import asyncio
import json
from typing import Optional

from openai import AsyncOpenAI
from tqdm import tqdm

from main_ifeval_code.config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT,
    IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA,
    PHASE2_TEMPERATURE,
    PHASE2_MAX_TOKENS,
    DEFAULT_BATCH_SIZE,
    PHASE1_OUTPUT,
    PHASE2_OUTPUT,
)
from main_ifeval_code.utils import (
    get_last_processed_id,
    iter_jsonl_batches,
    write_jsonl_batch,
    count_jsonl_lines,
)


# -----------------------------------------------------------------------
# ASYNC CLIENT
# -----------------------------------------------------------------------
client = AsyncOpenAI(
    base_url=VLLM_BASE_URL,
    api_key=VLLM_API_KEY,
)


# -----------------------------------------------------------------------
# MESSAGE CONSTRUCTION
# Replicates IFEvalInstructionIdListAssignator.format_input()
# from pipeline/ifeval_tasks.py lines 19-28
# -----------------------------------------------------------------------
def build_messages(instruction: str) -> list[dict]:
    """
    Build chat messages for constraint detection.
    Exact replication of format_input() from ifeval_tasks.py.
    """
    return [
        {
            "role": "system",
            "content": IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT,
        },
        {"role": "user", "content": instruction},
    ]


# -----------------------------------------------------------------------
# OUTPUT PARSING
# Replicates IFEvalInstructionIdListAssignator.format_output()
# from pipeline/ifeval_tasks.py lines 34-40
# -----------------------------------------------------------------------
def parse_output(output: str | None) -> dict:
    """
    Parse the LLM output to extract instruction_id_list.
    Exact replication of format_output() from ifeval_tasks.py.
    """
    if output is None:
        return {"instruction_id_list": None}
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"instruction_id_list": None}


# -----------------------------------------------------------------------
# VLLM CALL WITH GUIDED JSON
# Based on example.py lines 146-164
# -----------------------------------------------------------------------
async def detect_constraints(
    model_id: str,
    item: dict,
) -> Optional[dict]:
    """
    Detect constraint types in an instruction.
    Uses guided JSON decoding with IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA.
    """
    instruction = item.get("instruction")
    if not instruction:
        return None
    
    messages = build_messages(instruction)
    
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE2_TEMPERATURE,
            max_tokens=PHASE2_MAX_TOKENS,
            extra_body={"guided_json": IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA},
        )
        raw_output = resp.choices[0].message.content
        parsed = parse_output(raw_output)
        
        # Build output record
        return {
            "id": item["id"],
            "instruction": item["instruction"],
            "response": item["response"],
            "instruction_id_list": parsed.get("instruction_id_list"),
        }
    except Exception as e:
        print(f"Error detecting constraints for id={item.get('id')}: {e}")
        return None


# -----------------------------------------------------------------------
# BATCH PROCESSING
# Based on example.py lines 184-195
# -----------------------------------------------------------------------
async def process_batch(
    model_id: str,
    batch: list[dict],
) -> list[dict]:
    """Process a batch of items concurrently."""
    tasks = [detect_constraints(model_id, item) for item in batch]
    results = await asyncio.gather(*tasks)
    # Filter out None results
    return [r for r in results if r is not None]


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
async def main(
    input_file: str = PHASE1_OUTPUT,
    output_file: str = PHASE2_OUTPUT,
    batch_size: int = DEFAULT_BATCH_SIZE,
):
    # Discover model
    try:
        models_resp = await client.models.list()
        model_id = models_resp.data[0].id
        print(f"Using model: {model_id}")
    except Exception as e:
        print(f"Could not list models. Is vLLM running? Error: {e}")
        return

    # Resume from last processed ID
    last_id = get_last_processed_id(output_file)
    start_from_id = last_id + 1
    
    if start_from_id > 0:
        print(f"Resuming from ID: {start_from_id}")
    else:
        print("Starting from scratch.")

    # Count total items
    total_items = count_jsonl_lines(input_file)
    remaining = total_items - start_from_id
    
    if remaining <= 0:
        print(f"All {total_items} items already processed. Nothing to do.")
        return

    print(f"Processing {remaining} items from {input_file}...")

    # Process in batches
    pbar = tqdm(total=remaining, initial=0, desc="Detecting constraints")
    
    for batch in iter_jsonl_batches(
        input_file,
        batch_size,
        start_from_id,
        required_fields=["instruction", "response"],
    ):
        results = await process_batch(model_id, batch)
        
        if results:
            write_jsonl_batch(output_file, results)
            pbar.update(len(results))

    pbar.close()
    print(f"Phase 2 complete. Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2: Constraint Detection")
    parser.add_argument("--input", default=PHASE1_OUTPUT, help="Input JSONL file from Phase 1")
    parser.add_argument("--output", default=PHASE2_OUTPUT, help="Output JSONL file")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size for concurrent requests")
    args = parser.parse_args()
    
    asyncio.run(main(
        input_file=args.input,
        output_file=args.output,
        batch_size=args.batch_size,
    ))
