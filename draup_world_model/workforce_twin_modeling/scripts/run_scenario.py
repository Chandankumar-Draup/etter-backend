#!/usr/bin/env python3
"""
Run a Single Scenario with Detailed Output
===========================================
Execute one scenario by ID and print the full timeline.

Usage:
    python scripts/run_scenario.py SC-1.1
    python scripts/run_scenario.py SC-ST.3 --verbose
"""
import sys
import os
import argparse
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_PATH = os.path.join(PROJECT_ROOT, "scenario_catalog", "simulation_scenarios_extended.csv")


def print_timeline(result, verbose: bool = False):
    """Print monthly timeline for a scenario result."""
    if not result.result:
        print(f"  No result — scenario may have failed: {result.error}")
        return

    fb_result = result.result
    tl = fb_result.timeline
    W = 130

    print(f"\n{'='*W}")
    print(f"  {result.scenario_id}: {result.scenario_name}")
    print(f"{'='*W}")

    print(f"\n  Summary:")
    print(f"    HC Reduced:     {fb_result.total_hc_reduced}")
    print(f"    Final HC:       {fb_result.final_headcount}")
    print(f"    Net Savings:    ${fb_result.net_savings/1e6:.2f}M")
    print(f"    Total Inv:      ${fb_result.total_investment/1e6:.2f}M")
    print(f"    Total Savings:  ${fb_result.total_savings/1e6:.2f}M")
    print(f"    Payback:        M{fb_result.payback_month}" if fb_result.payback_month > 0 else "    Payback:        Never")
    print(f"    Proficiency:    {fb_result.final_proficiency:.1f}")
    print(f"    Trust:          {fb_result.final_trust:.1f}")
    print(f"    Readiness:      {fb_result.final_readiness:.1f}")

    print(f"\n  Monthly Timeline:")
    print(f"  {'─'*W}")
    print(f"  {'Mo':>3} {'Raw%':>5} {'Eff%':>5} {'Damp':>5}  {'HC':>5} {'HC%':>6} "
          f"{'Prof':>5} {'Rdns':>5} {'Trust':>5} {'PCap':>5} {'Fatig':>5} "
          f"{'Net$M':>8} {'Prod':>5} {'AbsR':>5}")
    print(f"  {'─'*W}")

    for s in tl:
        print(f"  {s.month:>3} "
              f"{s.raw_adoption_pct:>4.0%} "
              f"{s.effective_adoption_pct:>4.0%} "
              f"{s.adoption_dampening:>4.0%}  "
              f"{s.headcount:>5} "
              f"{s.hc_pct_of_original:>5.1f}% "
              f"{s.proficiency:>5.1f} "
              f"{s.readiness:>5.1f} "
              f"{s.trust:>5.1f} "
              f"{s.political_capital:>5.1f} "
              f"{s.transformation_fatigue:>5.1f} "
              f"${s.net_position/1e6:>6.2f}M "
              f"{s.productivity_index:>5.1f} "
              f"{s.dynamic_absorption_rate:>4.2f}")

    print(f"  {'─'*W}")

    if verbose:
        print(f"\n  Loop Contributions:")
        print(f"  {'─'*80}")
        print(f"  {'Mo':>3} {'HumanMult':>10} {'TrustMult':>10} {'CapMult':>9} "
              f"{'B2Skill':>8} {'B4Senior':>9} {'SkGap':>6}")
        print(f"  {'─'*80}")
        for s in tl:
            print(f"  {s.month:>3} "
                  f"{s.human_multiplier:>9.3f} "
                  f"{s.trust_multiplier:>9.3f} "
                  f"{s.capital_multiplier:>8.2f} "
                  f"{s.b2_skill_drag:>7.3f} "
                  f"{s.b4_seniority_mult:>8.3f} "
                  f"{s.current_skill_gap:>5}")
        print(f"  {'─'*80}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a single scenario")
    parser.add_argument("scenario_id", help="Scenario ID (e.g., SC-1.1, SC-ST.3)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show loop contributions")
    parser.add_argument("--trace", "-t", action="store_true",
                        help="Enable full traceability output (explainability)")
    parser.add_argument("--trace-months", nargs="*", type=int, default=None,
                        help="Specific months to trace (default: milestones)")
    parser.add_argument("--trace-json", type=str, default=None,
                        help="Export trace to JSON file")
    parser.add_argument("--catalog", default=CATALOG_PATH, help="Path to catalog CSV")
    args = parser.parse_args()

    from engine.loader import load_organization
    from stages.scenario_executor import load_catalog, run_scenario

    print(f"\n  Loading data from {DATA_DIR}...")
    org = load_organization(DATA_DIR)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.tasks)} tasks")

    rows = load_catalog(args.catalog)
    matching = [r for r in rows if r["scenario_id"] == args.scenario_id]

    if not matching:
        print(f"  ERROR: Scenario '{args.scenario_id}' not found in catalog.")
        print(f"  Available: {', '.join(r['scenario_id'] for r in rows)}")
        sys.exit(1)

    print(f"\n  Running {args.scenario_id}{'  [trace=True]' if args.trace else ''}...")
    result = run_scenario(matching[0], org, trace=args.trace)

    if result.error:
        print(f"  FAILED: {result.error}")
        sys.exit(1)

    print_timeline(result, verbose=args.verbose)

    # Trace output
    if args.trace and result.result and result.result.trace:
        from engine.trace import format_trace
        trace_output = format_trace(
            result.result.trace,
            months=args.trace_months,
            verbose=True,
        )
        print(trace_output)

        if args.trace_json:
            with open(args.trace_json, 'w') as f:
                f.write(result.result.trace.to_json())
            print(f"\n  Trace exported to {args.trace_json}")
