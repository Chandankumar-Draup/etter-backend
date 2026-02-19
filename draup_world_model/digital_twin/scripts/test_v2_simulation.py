"""
Test script: Run v2 time-stepped simulation and display monthly trajectory.

Runs role redesign and tech adoption through the v2 engine, then prints
month-by-month stocks so you can see how adoption, savings, human factors,
and feedback loops evolve over 36 months.

Usage:
    python -m draup_world_model.digital_twin.scripts.test_v2_simulation
"""

import logging
import sys

from draup_world_model.digital_twin.config import (
    CascadeConfig,
    FinancialConfig,
    OrganizationProfile,
    SimulationConfig,
    get_dt_neo4j_connection,
)
from draup_world_model.digital_twin.simulation.scenario_manager import (
    ScenarioManager,
    ScenarioConfig,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def fmt_money(val):
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"${val / 1_000:,.0f}K"
    return f"${val:,.0f}"


def print_trajectory(result, label):
    """Print v2 trajectory in a readable table."""
    if "error" in result:
        print(f"\n  ERROR: {result['error']}")
        return

    summary = result.get("trajectory_summary", {})
    theoretical = summary.get("theoretical_max", {})
    actual = summary.get("actual_at_end", {})
    hf = summary.get("human_factors_final", {})

    print(f"\n{'=' * 95}")
    print(f"  {label}")
    print(f"{'=' * 95}")

    print(f"\n  Theoretical max (100% adoption day 1):")
    print(f"    Freed HC: {theoretical.get('freed_headcount', 0):.0f}  |  "
          f"Gross savings: {fmt_money(theoretical.get('gross_savings', 0))}")

    print(f"\n  Actual at month {summary.get('timeline_months', 0)}:")
    print(f"    Adoption: {actual.get('adoption_level', 0):.0%}  |  "
          f"Freed HC: {actual.get('effective_freed_hc', 0):.1f}  |  "
          f"Net: {fmt_money(actual.get('cumulative_net', 0))}  |  "
          f"NPV: {fmt_money(actual.get('npv', 0))}  |  "
          f"ROI: {actual.get('roi_pct', 0):.1f}%")

    payback = summary.get("payback_month", 0)
    breakeven = summary.get("breakeven_month", 0)
    if payback:
        print(f"    Payback: month {payback}  |  Breakeven: month {breakeven}")

    print(f"\n  Human Factors (final): "
          f"R={hf.get('resistance', 0):.2f}  "
          f"M={hf.get('morale', 0):.2f}  "
          f"P={hf.get('proficiency', 0):.2f}  "
          f"C={hf.get('culture_readiness', 0):.2f}  "
          f"HFM={hf.get('composite_multiplier', 0):.2f}")

    # Monthly trajectory table
    snapshots = result.get("monthly_snapshots", [])
    print(f"\n  {'Mo':>3}  {'Adopt':>5}  {'FreeHC':>7}  {'Mo.Save':>9}  {'Mo.Cost':>9}  "
          f"{'CumNet':>10}  {'R':>4}  {'M':>4}  {'P':>4}  {'HFM':>4}  {'Loops'}")
    print(f"  {'---':>3}  {'-----':>5}  {'------':>7}  {'-------':>9}  {'-------':>9}  "
          f"{'------':>10}  {'----':>4}  {'----':>4}  {'----':>4}  {'----':>4}  {'-----'}")

    for snap in snapshots:
        m = snap["month"]
        # Show every month for first 6, then every 3, then every 6
        if m <= 6 or (m <= 18 and m % 3 == 0) or m % 6 == 0 or m == len(snapshots):
            adopt = snap["adoption"]["level"]
            fhc = snap["workforce"]["effective_freed_hc"]
            ms = snap["financial"]["monthly_savings"]
            mc = snap["financial"]["monthly_costs"]
            cn = snap["financial"]["cumulative_net"]
            hf_d = snap["human_factors"]
            r = hf_d.get("resistance", 0)
            mo = hf_d.get("morale", 0)
            p = hf_d.get("proficiency", 0)
            hfm = hf_d.get("composite_multiplier", 0)
            loops = ", ".join(
                l.split("_")[0] for l in snap.get("active_feedback_loops", [])
            )
            j = " J" if snap.get("j_curve_active") else ""
            print(
                f"  {m:>3}  {adopt:>4.0%}  {fhc:>7.1f}  {fmt_money(ms):>9}  "
                f"{fmt_money(mc):>9}  {fmt_money(cn):>10}  "
                f"{r:>.2f}  {mo:>.2f}  {p:>.2f}  {hfm:>.2f}  {loops}{j}"
            )

    print(f"{'=' * 95}")


def main():
    print("Connecting to Digital Twin Neo4j...")
    conn = get_dt_neo4j_connection()

    scenarios = [
        {
            "label": "v2 Role Redesign (moderate adoption)",
            "sim_type": "role_redesign",
            "scope": "Claims Management",
            "params": {"automation_factor": 0.5},
            "config": SimulationConfig(
                financial=FinancialConfig(j_curve_enabled=True),
            ),
        },
        {
            "label": "v2 Tech: Copilot (moderate adoption)",
            "sim_type": "tech_adoption",
            "scope": "Claims Management",
            "params": {
                "technology_name": "Microsoft Copilot",
                "adoption_months": 12,
                "adoption_speed": "moderate",
            },
            "config": SimulationConfig(
                financial=FinancialConfig(j_curve_enabled=True),
            ),
        },
        {
            "label": "v2 Role Redesign (high resistance org)",
            "sim_type": "role_redesign",
            "scope": "Claims Management",
            "params": {"automation_factor": 0.5},
            "config": SimulationConfig(
                financial=FinancialConfig(j_curve_enabled=True),
                organization=OrganizationProfile(
                    initial_resistance=0.85,
                    initial_morale=0.5,
                    initial_ai_proficiency=0.05,
                    culture_time_constant_months=36,
                ),
            ),
        },
    ]

    try:
        results = []
        for i, s in enumerate(scenarios):
            label = s["label"]
            print(f"\nRunning [{i + 1}/{len(scenarios)}]: {label}")
            manager = ScenarioManager(conn, simulation_config=s["config"])
            sc = ScenarioConfig(
                name=label,
                simulation_type=s["sim_type"],
                scope_type="function",
                scope_name=s["scope"],
                parameters=s["params"],
            )
            sid = manager.create_scenario(sc)
            result = manager.run_scenario_v2(sid)
            results.append((label, result))
            actual = result.get("trajectory_summary", {}).get("actual_at_end", {})
            print(f"  -> Adoption: {actual.get('adoption_level', 0):.0%}, "
                  f"Net: {fmt_money(actual.get('cumulative_net', 0))}, "
                  f"ROI: {actual.get('roi_pct', 0):.1f}%")

        for label, result in results:
            print_trajectory(result, label)

    finally:
        conn.close()
        print("\nDone. Connection closed.")


if __name__ == "__main__":
    main()
