"""
Shared utilities for the vLLM pipeline.
Based on patterns from example.py (lines 14-63).
"""

import json
import os
from typing import Dict, Iterator, List


def get_last_processed_id(filepath: str) -> int:
    """
    Get the highest ID that has been processed in a JSONL file.
    Used for resumability - based on example.py lines 14-31.
    """
    if not os.path.exists(filepath):
        return -1
    last_id = -1
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    current_id = data.get("id")
                    if isinstance(current_id, int) and current_id > last_id:
                        last_id = current_id
                except (json.JSONDecodeError, AttributeError):
                    continue
    except Exception as e:
        print(f"Error reading progress file: {e}")
        return -1
    return last_id


def iter_jsonl_batches(
    jsonl_path: str,
    batch_size: int,
    start_from_id: int = 0,
    required_fields: List[str] | None = None,
) -> Iterator[List[Dict]]:
    """
    Reads a JSONL and yields batches starting from start_from_id.
    Based on example.py lines 34-63.
    
    Args:
        jsonl_path: Path to the JSONL file
        batch_size: Number of items per batch
        start_from_id: Skip items with id < start_from_id
        required_fields: List of field names that must be present in each item
    """
    required_fields = required_fields or []
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        batch = []
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Check required fields
            if not all(k in obj for k in required_fields):
                continue
            if not isinstance(obj.get("id"), int):
                continue
            if obj["id"] < start_from_id:
                continue

            batch.append(obj)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


def write_jsonl_line(filepath: str, data: Dict) -> None:
    """Append a single JSON object as a line to a JSONL file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def write_jsonl_batch(filepath: str, batch: List[Dict]) -> None:
    """Append multiple JSON objects to a JSONL file."""
    with open(filepath, "a", encoding="utf-8") as f:
        for data in batch:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


def count_jsonl_lines(filepath: str) -> int:
    """Count the number of lines in a JSONL file."""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)
