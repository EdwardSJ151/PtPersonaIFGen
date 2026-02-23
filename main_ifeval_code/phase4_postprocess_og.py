"""
Phase 4: Post-Processing

Reuses logic from filter_ifeval_data.py to:
1. Restructure kwargs (flat dict -> per-instruction list)
2. Filter conflicting constraints
3. Validate responses with lm-eval IFEval checker
4. Keep only samples where prompt_level_strict_acc == True

Key Functions from filter_ifeval_data.py:
- build_instruction_kwargs() (lines 257-285)
- filter_not_valid_rows() (lines 288-305)
- get_ifeval_results() (lines 308-321)

Key Data Structures from filter_ifeval_data.py:
- INSTRUCTION_ARGS (lines 11-41)
- LANGUAGE_TO_CODE (lines 223-254)
- IFEVAL_INSTRUCTION_CONFLICTS (lines 70-221)
"""

import argparse
import json

from tqdm import tqdm

from ifeval_persona.main_ifeval_code.filter_ifeval_data_pt import (
    INSTRUCTION_ARGS,
    LANGUAGE_TO_CODE,
    IFEVAL_INSTRUCTION_CONFLICTS,
    build_instruction_kwargs,
    filter_not_valid_rows,
    get_ifeval_results,
)

from ifeval_persona.main_ifeval_code.config import (
    PHASE3_OUTPUT,
    PHASE4_OUTPUT,
)
from ifeval_persona.main_ifeval_code.utils import (
    iter_jsonl_batches,
    write_jsonl_line,
    count_jsonl_lines,
)


# -----------------------------------------------------------------------
# STEP 4.1: RESTRUCTURE KWARGS
# Reuses build_instruction_kwargs() from filter_ifeval_data.py (lines 257-285)
# -----------------------------------------------------------------------
def restructure_kwargs(item: dict) -> dict:
    """
    Transform flat kwargs dict into per-instruction kwargs list.
    Wraps build_instruction_kwargs() from filter_ifeval_data.py.
    """
    result = build_instruction_kwargs(item)
    item["kwargs"] = result.get("kwargs", item.get("kwargs"))
    item["valid_kwargs_json"] = result.get("valid_kwargs_json", False)
    return item


# -----------------------------------------------------------------------
# STEP 4.2: FILTER CONFLICTING CONSTRAINTS
# Reuses filter_not_valid_rows() from filter_ifeval_data.py (lines 288-305)
# -----------------------------------------------------------------------
def is_valid_row(item: dict) -> bool:
    """
    Check if a row has valid kwargs and no conflicting constraints.
    Wraps filter_not_valid_rows() from filter_ifeval_data.py.
    """
    return filter_not_valid_rows(item)


# -----------------------------------------------------------------------
# STEP 4.3: VALIDATE WITH LM-EVAL
# Reuses get_ifeval_results() from filter_ifeval_data.py (lines 308-321)
# -----------------------------------------------------------------------
def validate_response(item: dict) -> dict:
    """
    Validate response against constraints using lm-eval IFEval checker.
    Wraps get_ifeval_results() from filter_ifeval_data.py.
    """
    # Rename instruction to prompt (as done in filter_ifeval_data.py line 329)
    item["prompt"] = item.pop("instruction", item.get("prompt"))
    
    results = get_ifeval_results(item)
    item.update(results)
    return item


# -----------------------------------------------------------------------
# MAIN PROCESSING
# -----------------------------------------------------------------------
def process_item(item: dict) -> dict | None:
    """
    Process a single item through all post-processing steps.
    Returns None if the item should be filtered out.
    """
    # Step 4.1: Restructure kwargs
    item = restructure_kwargs(item)
    
    # Step 4.2: Filter invalid/conflicting
    if not is_valid_row(item):
        return None
    
    # Step 4.3: Validate with lm-eval
    item = validate_response(item)
    
    # Step 4.4: Filter by strict accuracy
    if not item.get("prompt_level_strict_acc", False):
        return None
    
    # Clean up intermediate fields
    if "valid_kwargs_json" in item:
        del item["valid_kwargs_json"]
    
    return item


def main(
    input_file: str = PHASE3_OUTPUT,
    output_file: str = PHASE4_OUTPUT,
    batch_size: int = 100,
):
    """
    Run post-processing on Phase 3 output.
    
    Note: This is CPU-bound (no LLM calls), so we process sequentially.
    The main bottleneck is the lm-eval validation.
    """
    # Count total items
    total_items = count_jsonl_lines(input_file)
    print(f"Processing {total_items} items from {input_file}...")
    
    # Track stats
    stats = {
        "total": 0,
        "invalid_kwargs": 0,
        "conflicts": 0,
        "failed_validation": 0,
        "passed": 0,
    }
    
    # Process items
    pbar = tqdm(total=total_items, desc="Post-processing")
    
    for batch in iter_jsonl_batches(
        input_file,
        batch_size,
        start_from_id=0,
        required_fields=["instruction", "response", "instruction_id_list", "kwargs"],
    ):
        for item in batch:
            stats["total"] += 1
            
            # Step 4.1: Restructure kwargs
            item = restructure_kwargs(item)
            if not item.get("valid_kwargs_json", False):
                stats["invalid_kwargs"] += 1
                pbar.update(1)
                continue
            
            # Step 4.2: Filter invalid/conflicting
            if not is_valid_row(item):
                stats["conflicts"] += 1
                pbar.update(1)
                continue
            
            # Step 4.3: Validate with lm-eval
            item = validate_response(item)
            
            # Step 4.4: Filter by strict accuracy
            if not item.get("prompt_level_strict_acc", False):
                stats["failed_validation"] += 1
                pbar.update(1)
                continue
            
            # Clean up intermediate fields
            if "valid_kwargs_json" in item:
                del item["valid_kwargs_json"]
            
            # Write passing item
            write_jsonl_line(output_file, item)
            stats["passed"] += 1
            pbar.update(1)
    
    pbar.close()
    
    # Print summary
    print("\n" + "=" * 50)
    print("Post-processing Summary")
    print("=" * 50)
    print(f"Total processed:      {stats['total']:,}")
    print(f"Invalid kwargs:       {stats['invalid_kwargs']:,}")
    print(f"Conflicting:          {stats['conflicts']:,}")
    print(f"Failed validation:    {stats['failed_validation']:,}")
    print(f"Passed (final):       {stats['passed']:,}")
    print(f"Pass rate:            {stats['passed']/max(stats['total'],1)*100:.1f}%")
    print("=" * 50)
    print(f"Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4: Post-Processing")
    parser.add_argument("--input", default=PHASE3_OUTPUT, help="Input JSONL file from Phase 3")
    parser.add_argument("--output", default=PHASE4_OUTPUT, help="Output JSONL file")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for reading")
    args = parser.parse_args()
    
    main(
        input_file=args.input,
        output_file=args.output,
        batch_size=args.batch_size,
    )
