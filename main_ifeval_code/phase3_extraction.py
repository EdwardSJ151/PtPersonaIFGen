"""
Phase 3: Parameter Extraction

Replicates IFEvalKwargsAssignator from pipeline/ifeval_tasks.py (lines 43-70).
For each detected constraint type, extracts the specific parameter values from the instruction.

System Prompt: pipeline/system_prompts.py -> IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT (lines 95-227)
JSON Schema: pipeline/json_schemas.py -> IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA (lines 1-152)
Generation Params: pipeline/pipeline.py (lines 229-231)

Input Format (from format_input, ifeval_tasks.py lines 48-58):
    instruction_id_list_str = "\\n".join(instruction_id_list)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"## Instruction\\n\\n{instruction}## Instruction ID List\\n\\n{instruction_id_list_str}"}
    ]
"""

import argparse
import asyncio
import json
from typing import Optional

from openai import AsyncOpenAI
from tqdm import tqdm

from ifeval_persona.main_ifeval_code.config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT,
    IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA,
    PHASE3_TEMPERATURE,
    PHASE3_MAX_TOKENS,
    DEFAULT_BATCH_SIZE,
    PHASE2_OUTPUT,
    PHASE3_OUTPUT,
)
from ifeval_persona.main_ifeval_code.utils import (
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
# Replicates IFEvalKwargsAssignator.format_input()
# from pipeline/ifeval_tasks.py lines 48-58
# -----------------------------------------------------------------------
def build_messages(instruction: str, instruction_id_list: list[str]) -> list[dict]:
    """
    Build chat messages for parameter extraction.
    Exact replication of format_input() from ifeval_tasks.py.
    
    Note: The original code has a subtle formatting issue where there's no
    newline between the instruction and "## Instruction ID List". We replicate
    this exactly.
    """
    instruction_id_list_str = "\n".join(instruction_id_list)
    
    return [
        {"role": "system", "content": IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"## Instrução\n\n{instruction}## Lista de IDs de Instrução\n\n{instruction_id_list_str}",
        },
    ]


# -----------------------------------------------------------------------
# OUTPUT PARSING
# Replicates IFEvalKwargsAssignator.format_output()
# from pipeline/ifeval_tasks.py lines 64-70
# -----------------------------------------------------------------------
def parse_output(output: str | None) -> dict:
    """
    Parse the LLM output to extract kwargs.
    Exact replication of format_output() from ifeval_tasks.py.
    
    Note: The original stores the raw JSON string, not parsed dict.
    """
    if output is None:
        return {"kwargs": None}
    
    return {"kwargs": output}


# -----------------------------------------------------------------------
# VLLM CALL WITH GUIDED JSON
# Based on example.py lines 146-164
# -----------------------------------------------------------------------
async def extract_kwargs(
    model_id: str,
    item: dict,
) -> Optional[dict]:
    """
    Extract constraint parameters from an instruction.
    Uses guided JSON decoding with IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA.
    """
    instruction = item.get("instruction")
    instruction_id_list = item.get("instruction_id_list")
    
    if not instruction or not instruction_id_list:
        return None
    
    messages = build_messages(instruction, instruction_id_list)
    
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE3_TEMPERATURE,
            max_tokens=PHASE3_MAX_TOKENS,
            extra_body={
                "guided_json": IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA
            },
        )
        raw_output = resp.choices[0].message.content
        parsed = parse_output(raw_output)
        
        # Build output record
        return {
            "id": item["id"],
            "instruction": item["instruction"],
            "response": item["response"],
            "instruction_id_list": item["instruction_id_list"],
            "kwargs": parsed.get("kwargs"),
        }
    except Exception as e:
        print(f"Error extracting kwargs for id={item.get('id')}: {e}")
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
    tasks = [extract_kwargs(model_id, item) for item in batch]
    results = await asyncio.gather(*tasks)
    # Filter out None results
    return [r for r in results if r is not None]


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
async def main(
    input_file: str = PHASE2_OUTPUT,
    output_file: str = PHASE3_OUTPUT,
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
    pbar = tqdm(total=remaining, initial=0, desc="Extracting kwargs")
    
    for batch in iter_jsonl_batches(
        input_file,
        batch_size,
        start_from_id,
        required_fields=["instruction", "response", "instruction_id_list"],
    ):
        results = await process_batch(model_id, batch)
        
        if results:
            write_jsonl_batch(output_file, results)
            pbar.update(len(results))

    pbar.close()
    print(f"Phase 3 complete. Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 3: Parameter Extraction")
    parser.add_argument("--input", default=PHASE2_OUTPUT, help="Input JSONL file from Phase 2")
    parser.add_argument("--output", default=PHASE3_OUTPUT, help="Output JSONL file")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size for concurrent requests")
    args = parser.parse_args()
    
    asyncio.run(main(
        input_file=args.input,
        output_file=args.output,
        batch_size=args.batch_size,
    ))
