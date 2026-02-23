"""
Phase 1: Two-Step Instruction + Response Generation

Generates IFEval-style training data using a two-step approach:

Step 1: Generate User Instruction
    - System prompt teaches the model about IFEval constraints
    - User prompt provides context/topic (from HuggingFace dataset or predefined list)
    - Model generates a realistic user instruction WITH IFEval constraints

Step 2: Generate Assistant Response
    - System prompt: IFEVAL_SYSTEM_PROMPT (same constraints the instruction references)
    - User prompt: The generated instruction from Step 1
    - Model generates a response that follows the constraints

This approach:
    - Works reliably with any chat model (no Magpie hacks)
    - Provides controlled topic diversity
    - Ensures constraint consistency between instruction and response
"""

import argparse
import asyncio
import random
from typing import Optional, Dict, Any, Iterator

from openai import AsyncOpenAI
from tqdm import tqdm

from ifeval_persona.main_ifeval_code.config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    IFEVAL_SYSTEM_PROMPT,
    USER_INSTRUCTION_GENERATOR_SYSTEM_PROMPT,
    TOPIC_SOURCE,
    HF_DATASET_ID,
    HF_DATASET_SUBSET,
    HF_TEXT_FIELD,
    HF_TITLE_FIELD,
    HF_MIN_CHARS,
    HF_MAX_CONTEXT_CHARS,
    PREDEFINED_TOPICS,
    PHASE1_INSTRUCTION_TEMPERATURE,
    PHASE1_RESPONSE_TEMPERATURE,
    PHASE1_TOP_P,
    PHASE1_MAX_TOKENS_INSTRUCTION,
    PHASE1_MAX_TOKENS_RESPONSE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_NUM_ROWS,
    PHASE1_OUTPUT,
)
from ifeval_persona.main_ifeval_code.utils import get_last_processed_id, write_jsonl_batch
import re

def clean_brackets(text: str) -> str:
    """
    Remove brackets around words, except in sentences mentioning 'placeholder'.
    
    Example:
        Input:  "Inclua as palavras-chave [economia], [tech]. Use [nome] como placeholder."
        Output: "Inclua as palavras-chave economia, tech. Use [nome] como placeholder."
    """
    if not text:
        return text
    
    # Split into sentences (rough split on . ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned_sentences = []
    
    for sentence in sentences:
        # If sentence mentions placeholder, keep brackets
        if 'placeholder' in sentence.lower():
            cleaned_sentences.append(sentence)
        else:
            # Remove brackets around words: [word] -> word
            # cleaned = re.sub(r'\[([^\]]+)\]', r'\1', sentence)
            cleaned = re.sub(r'\[([^\]]+)\]', r'"\1"', sentence)
            cleaned_sentences.append(cleaned)
    
    return ' '.join(cleaned_sentences)

# -----------------------------------------------------------------------
# ASYNC CLIENT
# -----------------------------------------------------------------------
client = AsyncOpenAI(
    base_url=VLLM_BASE_URL,
    api_key=VLLM_API_KEY,
)


# -----------------------------------------------------------------------
# TOPIC/CONTEXT PROVIDERS
# -----------------------------------------------------------------------
class TopicProvider:
    """Base class for topic/context providers."""
    
    def get_context(self) -> Dict[str, str]:
        """Returns {"topic": str, "context": str (optional)}"""
        raise NotImplementedError


class PredefinedTopicProvider(TopicProvider):
    """Provides topics from a predefined list."""
    
    def __init__(self, topics: list[str]):
        self.topics = topics
    
    def get_context(self) -> Dict[str, str]:
        topic = random.choice(self.topics)
        return {"topic": topic, "context": ""}


class HuggingFaceTopicProvider(TopicProvider):
    """Provides topics/context from a HuggingFace dataset (streaming)."""
    
    def __init__(
        self,
        dataset_id: str,
        subset: str,
        text_field: str,
        title_field: str,
        min_chars: int,
        max_context_chars: int,
    ):
        self.dataset_id = dataset_id
        self.subset = subset
        self.text_field = text_field
        self.title_field = title_field
        self.min_chars = min_chars
        self.max_context_chars = max_context_chars
        self._iterator: Optional[Iterator] = None
        self._current_index: int = -1  # Track position in dataset
    
    def _get_iterator(self) -> Iterator:
        """Lazy load the dataset iterator."""
        if self._iterator is None:
            from datasets import load_dataset
            ds = load_dataset(
                self.dataset_id,
                self.subset,
                split="train",
                streaming=True,
            )
            self._iterator = iter(ds)
        return self._iterator
    
    def _truncate_context(self, text: str) -> str:
        """Truncate context to max_context_chars, ending at sentence boundary."""
        if len(text) <= self.max_context_chars:
            return text
        
        truncated = text[:self.max_context_chars]
        # Try to end at a sentence boundary
        for end_char in ['. ', '! ', '? ', '\n']:
            last_pos = truncated.rfind(end_char)
            if last_pos > self.min_chars:
                return truncated[:last_pos + 1].strip()
        return truncated.strip()
    
    def get_context(self) -> Dict[str, Any]:
        """Get next valid context from the dataset."""
        iterator = self._get_iterator()
        
        while True:
            try:
                record = next(iterator)
                self._current_index += 1
            except StopIteration:
                # Restart iterator if exhausted
                self._iterator = None
                self._current_index = -1  # Reset counter
                iterator = self._get_iterator()
                record = next(iterator)
                self._current_index += 1
            
            text = record.get(self.text_field, "")
            if not isinstance(text, str) or len(text) < self.min_chars:
                continue
            
            context_text = self._truncate_context(text)
            title = record.get(self.title_field, "")
            
            return {
                "topic": title if title else "general knowledge",
                "context": context_text,
                "source_index": self._current_index,  # Add index
            }


def get_topic_provider() -> TopicProvider:
    """Factory function to get the appropriate topic provider."""
    if TOPIC_SOURCE == "huggingface":
        return HuggingFaceTopicProvider(
            dataset_id=HF_DATASET_ID,
            subset=HF_DATASET_SUBSET,
            text_field=HF_TEXT_FIELD,
            title_field=HF_TITLE_FIELD,
            min_chars=HF_MIN_CHARS,
            max_context_chars=HF_MAX_CONTEXT_CHARS,
        )
    else:
        return PredefinedTopicProvider(PREDEFINED_TOPICS)


# -----------------------------------------------------------------------
# STEP 1: GENERATE USER INSTRUCTION
# -----------------------------------------------------------------------
async def generate_user_instruction(
    model_id: str,
    topic: str,
    context: str = "",
) -> Optional[str]:
    """
    Generate a user instruction that includes IFEval-style constraints.
    
    Args:
        model_id: The vLLM model ID
        topic: The topic/theme for the instruction
        context: Optional context text (e.g., from Wikipedia)
    
    Returns:
        A user instruction string with embedded IFEval constraints
    """
    # Build the user prompt that asks the model to generate an instruction
    if context:
        user_prompt = f"""Generate a user instruction/query about the following topic. The instruction MUST include 1-3 IFEval-style constraints (word count, formatting, keywords, etc.).

## Topic: {topic}

## Context:
{context}

## Requirements:
- The instruction should ask about something related to the topic/context
- Include 1-3 constraints from the list in your system prompt
- Make it sound like a natural user request
- Output ONLY the user instruction, nothing else

Generate the user instruction:"""
    else:
        user_prompt = f"""Generate a user instruction/query about: {topic}

The instruction MUST include 1-3 IFEval-style constraints (word count, formatting, keywords, etc.).

## Requirements:
- The instruction should be about the given topic
- Include 1-3 constraints from the list in your system prompt
- Make it sound like a natural user request
- Output ONLY the user instruction, nothing else

Generate the user instruction:"""

    messages = [
        {"role": "system", "content": USER_INSTRUCTION_GENERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE1_INSTRUCTION_TEMPERATURE,
            top_p=PHASE1_TOP_P,
            max_tokens=PHASE1_MAX_TOKENS_INSTRUCTION,
        )
        instruction = resp.choices[0].message.content
        return instruction.strip() if instruction else None
    except Exception as e:
        print(f"Error generating instruction: {e}")
        return None


# -----------------------------------------------------------------------
# STEP 2: GENERATE ASSISTANT RESPONSE
# -----------------------------------------------------------------------
async def generate_response(
    model_id: str,
    instruction: str,
) -> Optional[str]:
    """
    Generate an assistant response for the given instruction.
    
    Uses IFEVAL_SYSTEM_PROMPT which teaches the model to follow
    the constraints specified in the user instruction.
    
    Args:
        model_id: The vLLM model ID
        instruction: The user instruction (with embedded constraints)
    
    Returns:
        An assistant response that follows the constraints
    """
    messages = [
        {"role": "system", "content": IFEVAL_SYSTEM_PROMPT},
        {"role": "user", "content": instruction},
    ]
    
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE1_RESPONSE_TEMPERATURE,
            top_p=PHASE1_TOP_P,
            max_tokens=PHASE1_MAX_TOKENS_RESPONSE,
        )
        response = resp.choices[0].message.content
        return response.strip() if response else None
    except Exception as e:
        print(f"Error generating response: {e}")
        return None


# -----------------------------------------------------------------------
# COMBINED: GENERATE INSTRUCTION-RESPONSE PAIR
# -----------------------------------------------------------------------
async def generate_instruction_response_pair(
    model_id: str,
    item_id: int,
    topic_provider: TopicProvider,
) -> Optional[Dict[str, Any]]:
    """
    Generate a complete instruction-response pair using the two-step approach.
    
    Step 1: Generate user instruction with IFEval constraints
    Step 2: Generate assistant response following those constraints
    
    Returns:
        Dict with id, instruction, response, topic, and context (if applicable)
    """
    # Get topic/context
    context_data = topic_provider.get_context()
    topic = context_data["topic"]
    context = context_data.get("context", "")
    
    # Step 1: Generate user instruction
    instruction = await generate_user_instruction(model_id, topic, context)
    if not instruction:
        return None
    
    # Clean brackets from instruction (except placeholder sentences)
    # instruction = clean_brackets(instruction)
    
    # Step 2: Generate response (using cleaned instruction)
    response = await generate_response(model_id, instruction)
    if not response:
        return None
    
    # Clean brackets from response (except placeholder sentences)
    # response = clean_brackets(response)
    
    result = {
        "id": item_id,
        "instruction": instruction,
        "response": response,
        "topic": topic,
    }
    
    if context:
        result["context"] = context
    if "source_index" in context_data:
        result["source_index"] = context_data["source_index"]
    
    return result


# -----------------------------------------------------------------------
# BATCH PROCESSING
# -----------------------------------------------------------------------
async def process_batch(
    model_id: str,
    start_id: int,
    batch_size: int,
    topic_provider: TopicProvider,
) -> list[Dict[str, Any]]:
    """Process a batch of generations concurrently."""
    tasks = [
        generate_instruction_response_pair(model_id, start_id + i, topic_provider)
        for i in range(batch_size)
    ]
    results = await asyncio.gather(*tasks)
    # Filter out None results
    return [r for r in results if r is not None]


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
async def main(
    output_file: str = PHASE1_OUTPUT,
    num_rows: int = DEFAULT_NUM_ROWS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    topic_source: str = TOPIC_SOURCE,
):
    # Override topic source if specified
    global TOPIC_SOURCE
    if topic_source != TOPIC_SOURCE:
        print(f"Overriding topic source: {topic_source}")
    
    # Discover model
    try:
        models_resp = await client.models.list()
        model_id = models_resp.data[0].id
        print(f"Using model: {model_id}")
    except Exception as e:
        print(f"Could not list models. Is vLLM running? Error: {e}")
        return

    # Initialize topic provider
    print(f"Topic source: {topic_source}")
    if topic_source == "huggingface":
        topic_provider = HuggingFaceTopicProvider(
            dataset_id=HF_DATASET_ID,
            subset=HF_DATASET_SUBSET,
            text_field=HF_TEXT_FIELD,
            title_field=HF_TITLE_FIELD,
            min_chars=HF_MIN_CHARS,
            max_context_chars=HF_MAX_CONTEXT_CHARS,
        )
        print(f"  Dataset: {HF_DATASET_ID}/{HF_DATASET_SUBSET}")
    else:
        topic_provider = PredefinedTopicProvider(PREDEFINED_TOPICS)
        print(f"  Using {len(PREDEFINED_TOPICS)} predefined topics")

    # Resume from last processed ID
    last_id = get_last_processed_id(output_file)
    start_from_id = last_id + 1
    
    if start_from_id > 0:
        print(f"Resuming from ID: {start_from_id}")
    else:
        print("Starting from scratch.")

    # Calculate remaining rows
    remaining_rows = num_rows - start_from_id
    if remaining_rows <= 0:
        print(f"Already generated {num_rows} rows. Nothing to do.")
        return

    print(f"Generating {remaining_rows} instruction-response pairs...")

    # Process in batches
    current_id = start_from_id
    pbar = tqdm(total=remaining_rows, initial=0, desc="Generating")
    
    while current_id < num_rows:
        # Calculate batch size for this iteration
        this_batch_size = min(batch_size, num_rows - current_id)
        
        # Generate batch
        results = await process_batch(
            model_id, current_id, this_batch_size, topic_provider
        )
        
        # Write results
        if results:
            write_jsonl_batch(output_file, results)
            pbar.update(len(results))
        
        current_id += this_batch_size

    pbar.close()
    print(f"Phase 1 complete. Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 1: Two-Step Instruction + Response Generation"
    )
    parser.add_argument(
        "--output", default=PHASE1_OUTPUT,
        help="Output JSONL file"
    )
    parser.add_argument(
        "--num-rows", type=int, default=DEFAULT_NUM_ROWS,
        help="Number of rows to generate"
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help="Batch size for concurrent requests"
    )
    parser.add_argument(
        "--topic-source", choices=["predefined", "huggingface"],
        default=TOPIC_SOURCE,
        help="Source for topics: 'predefined' list or 'huggingface' dataset"
    )
    args = parser.parse_args()
    
    asyncio.run(main(
        output_file=args.output,
        num_rows=args.num_rows,
        batch_size=args.batch_size,
        topic_source=args.topic_source,
    ))
