#!/usr/bin/env python3
"""
Workforce Twin MVP — Master Runner
====================================
Executes all 5 stages sequentially with validation.
Each stage builds on the previous, proving one additional layer of complexity.

Stage 0: Static Snapshot      (data model + gap analysis)
Stage 1: Single-Step Cascade  (9-step propagation)
Stage 2/3: Time-Stepped + Feedback (S-curves + human system)
Stage 4: Scenario Comparison  (5 policies, sensitivity)
"""
import sys
import os

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")


def run_stage_0():
    """Static Snapshot — prove data model works."""
    from stages.stage_0_snapshot import main
    out = os.path.join(OUTPUT_DIR, "stage0")
    return main(DATA_DIR, out)


def run_stage_1():
    """Single-Step Cascade — prove cascade propagation."""
    from stages.stage_1_cascade import main
    out = os.path.join(OUTPUT_DIR, "stage1")
    return main(DATA_DIR, out)


def run_stage_3():
    """Feedback Integration (includes Stage 2 open-loop as baseline)."""
    from stages.stage_3_feedback import main
    out = os.path.join(OUTPUT_DIR, "stage3")
    return main(DATA_DIR, out)


def run_stage_4():
    """Multi-Scenario Comparison."""
    from stages.stage_4_scenarios import main
    out = os.path.join(OUTPUT_DIR, "stage4")
    return main(DATA_DIR, out)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    stages = [
        ("Stage 0: Static Snapshot", run_stage_0),
        ("Stage 1: Single-Step Cascade", run_stage_1),
        ("Stage 2/3: Time-Stepped + Feedback", run_stage_3),
        ("Stage 4: Scenario Comparison", run_stage_4),
    ]

    results = {}
    for name, runner in stages:
        print(f"\n{'#'*90}")
        print(f"#  {name}")
        print(f"{'#'*90}")
        try:
            results[name] = runner()
            print(f"\n  ✓ {name} completed successfully")
        except Exception as e:
            print(f"\n  ✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[name] = None

    # Summary
    print(f"\n{'='*90}")
    print(f"  WORKFORCE TWIN MVP — EXECUTION SUMMARY")
    print(f"{'='*90}")
    for name, result in results.items():
        status = "✓ PASS" if result is not None else "✗ FAIL"
        print(f"  {status}  {name}")
    print(f"{'='*90}")
