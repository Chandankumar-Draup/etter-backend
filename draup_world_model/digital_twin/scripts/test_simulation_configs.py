"""
Test script: Run all simulation scenarios with v2 time-stepped engine.

Covers every scenario type and hierarchy level:
  1. Role Redesign (baseline)                    — function scope
  2. Role Redesign (aggressive automation)       — function scope
  3. Single Tech Adoption (Copilot)              — function scope
  4. Single Tech Adoption (UiPath)               — function scope
  5. Multi-Tech Adoption (Copilot + Claims AI)   — function scope
  6. Multi-Tech Adoption (3 technologies)        — function scope
  7. Role Redesign (high-resistance org)         — function scope
  8. Role Redesign (low redeployability)         — function scope
  9. Role Redesign (sub-function scope)          — sub_function scope
  10. Role Redesign (job family scope)           — job_family scope
  11. Tech Adoption (job family scope)           — job_family scope
  12. Role Redesign (single role scope)          — role scope

Each scenario runs through the v2 engine (Bass diffusion, human factors,
feedback loops) and prints a monthly trajectory table.

Usage:
    python -m draup_world_model.digital_twin.scripts.test_simulation_configs
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


# ──────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────

SCENARIOS = [
    # 1. Role redesign — baseline
    {
        "label": "1. Role Redesign (baseline)",
        "sim_type": "role_redesign",
        "scope": "Claims Management",
        "params": {"automation_factor": 0.5},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 2. Role redesign — aggressive automation
    {
        "label": "2. Role Redesign (aggressive, factor=0.8)",
        "sim_type": "role_redesign",
        "scope": "Claims Management",
        "params": {"automation_factor": 0.8},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 3. Single tech — Microsoft Copilot
    {
        "label": "3. Tech: Microsoft Copilot",
        "sim_type": "tech_adoption",
        "scope": "Claims Management",
        "params": {
            "technology_name": "Microsoft Copilot",
            "adoption_months": 12,
        },
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 4. Single tech — UiPath
    {
        "label": "4. Tech: UiPath",
        "sim_type": "tech_adoption",
        "scope": "Claims Management",
        "params": {
            "technology_name": "UiPath",
            "adoption_months": 12,
        },
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 5. Multi-tech — Copilot + Claims AI
    {
        "label": "5. Multi-Tech: Copilot + Claims AI",
        "sim_type": "multi_tech_adoption",
        "scope": "Claims Management",
        "params": {
            "technology_names": ["Microsoft Copilot", "Claims AI"],
            "adoption_months": 12,
        },
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 6. Multi-tech — Copilot + UiPath + Claims AI
    {
        "label": "6. Multi-Tech: Copilot + UiPath + Claims AI",
        "sim_type": "multi_tech_adoption",
        "scope": "Claims Management",
        "params": {
            "technology_names": ["Microsoft Copilot", "UiPath", "Claims AI"],
            "adoption_months": 12,
        },
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 7. Role redesign — high-resistance organization
    {
        "label": "7. Role Redesign (high resistance org)",
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
    # 8. Role redesign — low redeployability
    {
        "label": "8. Role Redesign (low redeployability 30%)",
        "sim_type": "role_redesign",
        "scope": "Claims Management",
        "params": {"automation_factor": 0.5},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
            cascade=CascadeConfig(redeployability_pct=30.0),
        ),
    },
    # ── Multi-scope scenarios (different hierarchy levels) ──
    # 9. Sub-function scope — Claims Processing only
    {
        "label": "9. Sub-Function: Claims Processing",
        "sim_type": "role_redesign",
        "scope_type": "sub_function",
        "scope": "Claims Processing",
        "params": {"automation_factor": 0.5},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 10. Job family scope — Claims Adjusters only
    {
        "label": "10. Job Family: Claims Adjusters",
        "sim_type": "role_redesign",
        "scope_type": "job_family",
        "scope": "Claims Adjusters",
        "params": {"automation_factor": 0.5},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 11. Job family scope — Fraud Investigators (Copilot)
    {
        "label": "11. Job Family: Fraud Investigators + Copilot",
        "sim_type": "tech_adoption",
        "scope_type": "job_family",
        "scope": "Fraud Investigators",
        "params": {"technology_name": "Microsoft Copilot", "adoption_months": 12},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
    # 12. Single role scope — smallest possible unit
    {
        "label": "12. Role: Senior Claims Adjuster - P&C",
        "sim_type": "role_redesign",
        "scope_type": "role",
        "scope": "Senior Claims Adjuster - Property & Casualty",
        "params": {"automation_factor": 0.5},
        "config": SimulationConfig(
            financial=FinancialConfig(j_curve_enabled=True),
        ),
    },
]


# ──────────────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────────────

def fmt_money(val):
    """Format dollar amount concisely."""
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

    print(f"\n{'=' * 100}")
    print(f"  {label}")
    print(f"{'=' * 100}")

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

    print(f"{'=' * 100}")


def print_summary_table(results):
    """Print a compact comparison table across all scenarios."""
    print(f"\n\n{'=' * 115}")
    print("QUICK COMPARISON TABLE (v2 Time-Stepped)")
    print(f"{'=' * 115}")
    header = (
        f"{'Scenario':<45} {'Adopt':>5} {'FreeHC':>7} {'Savings':>10} "
        f"{'Cost':>10} {'Net':>10} {'ROI':>7} {'BkEv':>4} {'HFM':>4}"
    )
    print(header)
    print("-" * len(header))

    for label, result in results:
        if "error" in result:
            print(f"{label:<45} {'ERROR':>5}")
            continue

        summary = result.get("trajectory_summary", {})
        actual = summary.get("actual_at_end", {})
        hf = summary.get("human_factors_final", {})
        breakeven = summary.get("breakeven_month", 0)

        print(
            f"{label:<45} "
            f"{actual.get('adoption_level', 0):>4.0%} "
            f"{actual.get('effective_freed_hc', 0):>7.1f} "
            f"{fmt_money(actual.get('cumulative_savings', 0)):>10} "
            f"{fmt_money(actual.get('cumulative_costs', 0)):>10} "
            f"{fmt_money(actual.get('cumulative_net', 0)):>10} "
            f"{actual.get('roi_pct', 0):>6.1f}% "
            f"{breakeven:>4} "
            f"{hf.get('composite_multiplier', 0):>.2f}"
        )

    print(f"{'=' * 115}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print("Connecting to Digital Twin Neo4j...")
    conn = get_dt_neo4j_connection()

    try:
        results = []
        for i, scenario_def in enumerate(SCENARIOS):
            label = scenario_def["label"]
            print(f"\nRunning [{i + 1}/{len(SCENARIOS)}]: {label}")
            try:
                manager = ScenarioManager(
                    conn, simulation_config=scenario_def["config"]
                )
                sc = ScenarioConfig(
                    name=label,
                    simulation_type=scenario_def["sim_type"],
                    scope_type=scenario_def.get("scope_type", "function"),
                    scope_name=scenario_def["scope"],
                    parameters=scenario_def["params"],
                )
                sid = manager.create_scenario(sc)
                result = manager.run_scenario_v2(sid)
                results.append((label, result))

                actual = result.get("trajectory_summary", {}).get("actual_at_end", {})
                print(f"  -> Adoption: {actual.get('adoption_level', 0):.0%}, "
                      f"Net: {fmt_money(actual.get('cumulative_net', 0))}, "
                      f"ROI: {actual.get('roi_pct', 0):.1f}%")
            except Exception as e:
                print(f"  -> FAILED: {e}")
                import traceback
                traceback.print_exc()
                results.append((label, {"error": str(e)}))

        # Print individual trajectories
        for label, result in results:
            print_trajectory(result, label)

        # Print summary comparison
        print_summary_table(results)

    finally:
        conn.close()
        print("\nDone. Connection closed.")


if __name__ == "__main__":
    main()
