#!/usr/bin/env python3
"""
Run Scenario Catalog
====================
Execute scenarios from the catalog CSV, with optional filtering.

Usage:
    python scripts/run_catalog.py                           # All scenarios
    python scripts/run_catalog.py --family stress_test      # Filter by family
    python scripts/run_catalog.py --ids SC-1.1 SC-1.2      # Specific IDs
    python scripts/run_catalog.py --family technology_injection --family composite
"""
import sys
import os
import argparse
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "catalog")
CATALOG_PATH = os.path.join(PROJECT_ROOT, "scenario_catalog", "simulation_scenarios_extended.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run scenario catalog")
    parser.add_argument("--family", action="append", help="Filter by family (repeatable)")
    parser.add_argument("--ids", nargs="*", help="Filter by scenario IDs")
    parser.add_argument("--catalog", default=CATALOG_PATH, help="Path to catalog CSV")
    args = parser.parse_args()

    from engine.loader import load_organization
    from stages.scenario_executor import (
        load_catalog, run_batch, print_batch_summary, export_batch,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t0 = time.time()

    print(f"\n  Loading organization data from {DATA_DIR}...")
    org = load_organization(DATA_DIR)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.tasks)} tasks")

    print(f"\n  Running scenario catalog from {args.catalog}...")
    results = run_batch(
        args.catalog, org,
        scenario_ids=args.ids,
        families=args.family,
    )

    print_batch_summary(results)

    export_batch(results, os.path.join(OUTPUT_DIR, "scenario_catalog_results.csv"))

    elapsed = time.time() - t0
    passed = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)

    print(f"\n  Catalog: {passed} passed, {failed} failed ({elapsed:.1f}s)")
