#!/usr/bin/env python3
"""
Master Runner — Execute All Simulation Modes
=============================================
Runs stages, scenario catalog, and stress tests in sequence.
Use this as the single entry point for full validation.

Usage:
    python scripts/run_all.py                    # Run everything
    python scripts/run_all.py --stages           # Stages only
    python scripts/run_all.py --catalog          # Catalog only
    python scripts/run_all.py --stress           # Stress tests only
    python scripts/run_all.py --stages --stress  # Combine as needed
"""
import sys
import os
import argparse
import time

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
CATALOG_PATH = os.path.join(PROJECT_ROOT, "scenario_catalog", "simulation_scenarios_extended.csv")


def run_stages() -> dict:
    """Run all 5 simulation stages."""
    from stages.stage_0_snapshot import main as stage0_main
    from stages.stage_1_cascade import main as stage1_main
    from stages.stage_3_feedback import main as stage3_main
    from stages.stage_4_scenarios import main as stage4_main

    stages = [
        ("Stage 0: Static Snapshot", stage0_main, "stage0"),
        ("Stage 1: Single-Step Cascade", stage1_main, "stage1"),
        ("Stage 2/3: Time-Stepped + Feedback", stage3_main, "stage3"),
        ("Stage 4: Scenario Comparison", stage4_main, "stage4"),
    ]

    results = {}
    for name, runner, out_sub in stages:
        print(f"\n{'#'*90}")
        print(f"#  {name}")
        print(f"{'#'*90}")
        try:
            out = os.path.join(OUTPUT_DIR, out_sub)
            results[name] = runner(DATA_DIR, out)
            print(f"\n  ✓ {name} completed successfully")
        except Exception as e:
            print(f"\n  ✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[name] = None

    return results


def run_catalog() -> list:
    """Run the full scenario catalog."""
    from stages.scenario_executor import main as catalog_main

    print(f"\n{'#'*90}")
    print(f"#  Scenario Catalog ({CATALOG_PATH})")
    print(f"{'#'*90}")

    try:
        results = catalog_main(
            data_dir=DATA_DIR,
            catalog_path=CATALOG_PATH,
            output_dir=os.path.join(OUTPUT_DIR, "catalog"),
        )
        print(f"\n  ✓ Scenario Catalog completed successfully")
        return results
    except Exception as e:
        print(f"\n  ✗ Scenario Catalog FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_stress_tests() -> list:
    """Run the stress test suite."""
    from stages.stress_test import main as stress_main

    print(f"\n{'#'*90}")
    print(f"#  Stress Tests")
    print(f"{'#'*90}")

    try:
        results = stress_main(
            data_dir=DATA_DIR,
            output_dir=os.path.join(OUTPUT_DIR, "stress_test"),
        )
        print(f"\n  ✓ Stress Tests completed successfully")
        return results
    except Exception as e:
        print(f"\n  ✗ Stress Tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_summary(
    stage_results: dict = None,
    catalog_results: list = None,
    stress_results: list = None,
    elapsed: float = 0,
):
    """Print execution summary."""
    W = 90
    print(f"\n{'='*W}")
    print(f"  WORKFORCE TWIN — FULL EXECUTION SUMMARY")
    print(f"{'='*W}")

    if stage_results is not None:
        stage_pass = sum(1 for v in stage_results.values() if v is not None)
        stage_fail = sum(1 for v in stage_results.values() if v is None)
        print(f"\n  STAGES: {stage_pass} passed, {stage_fail} failed")
        for name, result in stage_results.items():
            status = "✓ PASS" if result is not None else "✗ FAIL"
            print(f"    {status}  {name}")

    if catalog_results is not None:
        if isinstance(catalog_results, list):
            cat_pass = sum(1 for r in catalog_results if r.error is None)
            cat_fail = sum(1 for r in catalog_results if r.error is not None)
            print(f"\n  CATALOG: {cat_pass} passed, {cat_fail} failed out of {len(catalog_results)} scenarios")
        else:
            print(f"\n  CATALOG: FAILED")

    if stress_results is not None:
        if isinstance(stress_results, list):
            st_pass = sum(1 for r in stress_results if r.status == "PASS")
            st_fail = sum(1 for r in stress_results if r.status == "FAIL")
            st_warn = sum(1 for r in stress_results if r.status == "WARN")
            st_info = sum(1 for r in stress_results if r.status == "INFO")
            print(f"\n  STRESS TESTS: {st_pass} PASS, {st_fail} FAIL, {st_warn} WARN, {st_info} INFO")
        else:
            print(f"\n  STRESS TESTS: FAILED")

    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"{'='*W}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workforce Twin — Master Runner")
    parser.add_argument("--stages", action="store_true", help="Run simulation stages")
    parser.add_argument("--catalog", action="store_true", help="Run scenario catalog")
    parser.add_argument("--stress", action="store_true", help="Run stress tests")
    args = parser.parse_args()

    # If no flags, run everything
    run_all = not (args.stages or args.catalog or args.stress)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t0 = time.time()

    stage_results = None
    catalog_results = None
    stress_results = None

    if run_all or args.stages:
        stage_results = run_stages()

    if run_all or args.catalog:
        catalog_results = run_catalog()

    if run_all or args.stress:
        stress_results = run_stress_tests()

    elapsed = time.time() - t0
    print_summary(stage_results, catalog_results, stress_results, elapsed)
