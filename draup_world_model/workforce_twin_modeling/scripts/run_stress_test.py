#!/usr/bin/env python3
"""
Run Stress Tests
================
Execute the full stress test suite against the model.

Usage:
    python scripts/run_stress_test.py
"""
import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "stress_test")


if __name__ == "__main__":
    from stages.stress_test import main as stress_main

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t0 = time.time()

    results = stress_main(data_dir=DATA_DIR, output_dir=OUTPUT_DIR)

    elapsed = time.time() - t0
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    warns = sum(1 for r in results if r.status == "WARN")

    print(f"\n  Stress Tests: {passed} PASS, {failed} FAIL, {warns} WARN ({elapsed:.1f}s)")
