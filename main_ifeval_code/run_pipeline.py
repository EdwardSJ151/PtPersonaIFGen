#!/usr/bin/env python3
"""
Main Pipeline Runner

Orchestrates the complete IFEval-like data generation pipeline:
- Phase 1: Magpie generation (instruction + response pairs)
- Phase 2: Constraint detection (classify constraint types)
- Phase 3: Parameter extraction (extract kwargs for each constraint)
- Phase 4: Post-processing (validate and filter)

Usage:
    # Run complete pipeline
    python run_pipeline.py --num-rows 200

    # Run specific phase
    python run_pipeline.py --phase 2 --input phase1_output.jsonl

    # Run from specific phase onwards
    python run_pipeline.py --start-phase 3

Environment Variables:
    VLLM_BASE_URL: vLLM server URL (default: http://localhost:8000/v1)
    VLLM_API_KEY: API key (default: no-key-needed)
"""

import argparse
import asyncio
import os
import sys

from ifeval_persona.main_ifeval_code.config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_NUM_ROWS,
    PHASE1_OUTPUT,
    PHASE2_OUTPUT,
    PHASE3_OUTPUT,
    PHASE4_OUTPUT,
)


async def run_phase1(num_rows: int, batch_size: int, output: str):
    """Run Phase 1: Magpie Generation"""
    print("\n" + "=" * 60)
    print("PHASE 1: Magpie Instruction + Response Generation")
    print("=" * 60)
    
    from ifeval_persona.main_ifeval_code.phase1_magpie import main as phase1_main
    await phase1_main(
        output_file=output,
        num_rows=num_rows,
        batch_size=batch_size,
    )


async def run_phase2(input_file: str, batch_size: int, output: str):
    """Run Phase 2: Constraint Detection"""
    print("\n" + "=" * 60)
    print("PHASE 2: Constraint Type Detection")
    print("=" * 60)
    
    from ifeval_persona.main_ifeval_code.phase2_detection import main as phase2_main
    await phase2_main(
        input_file=input_file,
        output_file=output,
        batch_size=batch_size,
    )


async def run_phase3(input_file: str, batch_size: int, output: str):
    """Run Phase 3: Parameter Extraction"""
    print("\n" + "=" * 60)
    print("PHASE 3: Parameter Extraction")
    print("=" * 60)
    
    from ifeval_persona.main_ifeval_code.phase3_extraction import main as phase3_main
    await phase3_main(
        input_file=input_file,
        output_file=output,
        batch_size=batch_size,
    )


def run_phase4(input_file: str, batch_size: int, output: str):
    """Run Phase 4: Post-Processing"""
    print("\n" + "=" * 60)
    print("PHASE 4: Post-Processing")
    print("=" * 60)
    
    from ifeval_persona.main_ifeval_code.phase4_postprocess import main as phase4_main
    phase4_main(
        input_file=input_file,
        output_file=output,
        batch_size=batch_size,
    )


async def run_full_pipeline(
    num_rows: int,
    batch_size: int,
    start_phase: int = 1,
    phase1_output: str = PHASE1_OUTPUT,
    phase2_output: str = PHASE2_OUTPUT,
    phase3_output: str = PHASE3_OUTPUT,
    phase4_output: str = PHASE4_OUTPUT,
):
    """Run the complete pipeline from start_phase onwards."""
    
    if start_phase <= 1:
        await run_phase1(num_rows, batch_size, phase1_output)
    
    if start_phase <= 2:
        await run_phase2(phase1_output, batch_size, phase2_output)
    
    if start_phase <= 3:
        await run_phase3(phase2_output, batch_size, phase3_output)
    
    if start_phase <= 4:
        run_phase4(phase3_output, batch_size, phase4_output)
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Final output: {phase4_output}")


async def run_single_phase(
    phase: int,
    input_file: str | None,
    output_file: str | None,
    batch_size: int,
    num_rows: int,
):
    """Run a single specific phase."""
    
    if phase == 1:
        output = output_file or PHASE1_OUTPUT
        await run_phase1(num_rows, batch_size, output)
    
    elif phase == 2:
        input_f = input_file or PHASE1_OUTPUT
        output = output_file or PHASE2_OUTPUT
        await run_phase2(input_f, batch_size, output)
    
    elif phase == 3:
        input_f = input_file or PHASE2_OUTPUT
        output = output_file or PHASE3_OUTPUT
        await run_phase3(input_f, batch_size, output)
    
    elif phase == 4:
        input_f = input_file or PHASE3_OUTPUT
        output = output_file or PHASE4_OUTPUT
        run_phase4(input_f, batch_size, output)
    
    else:
        print(f"Invalid phase: {phase}. Must be 1-4.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="IFEval-like Data Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run complete pipeline with 10k rows
    python run_pipeline.py --num-rows 10000

    # Run only Phase 2 with custom input
    python run_pipeline.py --phase 2 --input my_phase1.jsonl

    # Resume pipeline from Phase 3
    python run_pipeline.py --start-phase 3

    # Run Phase 1 with larger batch size
    python run_pipeline.py --phase 1 --batch-size 100 --num-rows 50000
        """
    )
    
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run only this specific phase"
    )
    parser.add_argument(
        "--start-phase",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Start from this phase (runs all subsequent phases)"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input file for the phase (defaults to previous phase output)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for the phase (defaults to phase-specific name)"
    )
    parser.add_argument(
        "--num-rows",
        type=int,
        default=DEFAULT_NUM_ROWS,
        help=f"Number of rows to generate in Phase 1 (default: {DEFAULT_NUM_ROWS})"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for concurrent requests (default: {DEFAULT_BATCH_SIZE})"
    )
    
    args = parser.parse_args()
    
    # Print configuration
    print("=" * 60)
    print("IFEval-like Data Generation Pipeline")
    print("=" * 60)
    print(f"vLLM URL: {os.environ.get('VLLM_BASE_URL', 'http://localhost:8000/v1')}")
    print(f"Batch size: {args.batch_size}")
    print(f"Num rows: {args.num_rows}")
    
    if args.phase:
        print(f"Running: Phase {args.phase} only")
        asyncio.run(run_single_phase(
            phase=args.phase,
            input_file=args.input,
            output_file=args.output,
            batch_size=args.batch_size,
            num_rows=args.num_rows,
        ))
    else:
        print(f"Running: Phase {args.start_phase} onwards")
        asyncio.run(run_full_pipeline(
            num_rows=args.num_rows,
            batch_size=args.batch_size,
            start_phase=args.start_phase,
        ))


if __name__ == "__main__":
    main()
