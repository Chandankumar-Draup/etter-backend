#!/usr/bin/env python3
"""
Run Simulation Stages
=====================
Execute individual or all simulation stages (0-4).

Usage:
    python scripts/run_stages.py           # All stages
    python scripts/run_stages.py 0         # Stage 0 only
    python scripts/run_stages.py 1 3       # Stages 1 and 3
    python scripts/run_stages.py 4         # Stage 4 only
"""
import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")


STAGE_MAP = {
    "0": ("Stage 0: Static Snapshot", "stages.stage_0_snapshot", "stage0"),
    "1": ("Stage 1: Single-Step Cascade", "stages.stage_1_cascade", "stage1"),
    "3": ("Stage 2/3: Time-Stepped + Feedback", "stages.stage_3_feedback", "stage3"),
    "4": ("Stage 4: Scenario Comparison", "stages.stage_4_scenarios", "stage4"),
}


def run_stage(stage_key: str):
    """Run a single stage."""
    if stage_key not in STAGE_MAP:
        print(f"  Unknown stage: {stage_key}. Available: {', '.join(STAGE_MAP.keys())}")
        return False

    name, module_path, out_sub = STAGE_MAP[stage_key]

    print(f"\n{'#'*90}")
    print(f"#  {name}")
    print(f"{'#'*90}")

    try:
        module = __import__(module_path, fromlist=["main"])
        out = os.path.join(OUTPUT_DIR, out_sub)
        module.main(DATA_DIR, out)
        print(f"\n  ✓ {name} completed successfully")
        return True
    except Exception as e:
        print(f"\n  ✗ {name} FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t0 = time.time()

    # Parse stage numbers from args, or run all
    if len(sys.argv) > 1:
        stage_keys = sys.argv[1:]
    else:
        stage_keys = list(STAGE_MAP.keys())

    results = {}
    for key in stage_keys:
        results[key] = run_stage(key)

    elapsed = time.time() - t0
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"\n{'='*90}")
    print(f"  STAGES: {passed} passed, {failed} failed ({elapsed:.1f}s)")
    print(f"{'='*90}")
