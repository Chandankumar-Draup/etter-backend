"""
Phase 3 orchestration: Run Digital Twin simulations.

SAFETY: Uses DTNeo4jConfig (DT_NEO4J_* env vars) so it NEVER
accidentally connects to the production database.

Usage:
    # Role redesign for Claims
    python -m draup_world_model.digital_twin.scripts.run_simulation \
        --type role_redesign --scope "Claims Management" --factor 0.5

    # Technology adoption impact
    python -m draup_world_model.digital_twin.scripts.run_simulation \
        --type tech_adoption --scope "Claims Management" --tech "Microsoft Copilot"

    # Compare two scenarios
    python -m draup_world_model.digital_twin.scripts.run_simulation \
        --compare scenario_1 scenario_2
"""

import argparse
import json
import logging
import sys

from draup_world_model.digital_twin.config import (
    CascadeConfig,
    FinancialConfig,
    OrganizationProfile,
    OutputConfig,
    SimulationConfig,
    get_dt_neo4j_connection,
)
from draup_world_model.digital_twin.simulation.scenario_manager import (
    ScenarioManager,
    ScenarioConfig,
)
from draup_world_model.digital_twin.simulation.simulations.tech_adoption import (
    TechAdoptionSimulation,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_sim_config(args) -> SimulationConfig:
    """Build SimulationConfig from CLI arguments."""
    cascade_kwargs = {}
    financial_kwargs = {}
    org_kwargs = {}

    if args.redeployability is not None:
        cascade_kwargs["redeployability_pct"] = args.redeployability
    if args.reskilling_fraction is not None:
        cascade_kwargs["reskilling_fraction"] = args.reskilling_fraction

    if args.change_mgmt_pct is not None:
        financial_kwargs["change_management_pct"] = args.change_mgmt_pct
    if args.severance_months is not None:
        financial_kwargs["severance_months"] = args.severance_months
    if args.j_curve:
        financial_kwargs["j_curve_enabled"] = True
    if args.no_tech_cost:
        financial_kwargs["include_tech_cost_in_role_redesign"] = False

    if args.max_reduction is not None:
        org_kwargs["max_headcount_reduction_pct"] = args.max_reduction

    return SimulationConfig(
        cascade=CascadeConfig(**cascade_kwargs),
        financial=FinancialConfig(**financial_kwargs),
        organization=OrganizationProfile(**org_kwargs),
        timeline_months=args.timeline,
    )


def run_simulation(args):
    """Run a simulation scenario."""
    conn = get_dt_neo4j_connection()
    try:
        sim_config = _build_sim_config(args)
        manager = ScenarioManager(conn, simulation_config=sim_config)

        if args.type == "role_redesign":
            config = ScenarioConfig(
                name=f"Role Redesign - {args.scope}",
                simulation_type="role_redesign",
                scope_type="function",
                scope_name=args.scope,
                parameters={
                    "automation_factor": args.factor,
                },
                timeline_months=args.timeline,
            )
        elif args.type == "tech_adoption":
            config = ScenarioConfig(
                name=f"{args.tech} - {args.scope}",
                simulation_type="tech_adoption",
                scope_type="function",
                scope_name=args.scope,
                parameters={
                    "technology_name": args.tech,
                    "adoption_months": 12,
                },
                timeline_months=args.timeline,
            )
        else:
            logger.error(f"Unknown simulation type: {args.type}")
            sys.exit(1)

        scenario_id = manager.create_scenario(config)
        use_v2 = getattr(args, "engine", "v1") == "v2"
        if use_v2:
            result = manager.run_scenario_v2(scenario_id)
            _print_v2_result(result, config.name)
            return scenario_id, manager
        result = manager.run_scenario(scenario_id)

        # Print summary
        cascade = result.get("cascade", {})
        if cascade:
            summary = cascade.get("summary", {})
            financial = cascade.get("financial", {})
            workforce = cascade.get("workforce", {})

            print("\n" + "=" * 60)
            print(f"SIMULATION RESULT: {config.name}")
            print("=" * 60)
            print(f"Tasks affected:     {summary.get('tasks_affected', 0)}")
            print(f"Roles affected:     {summary.get('roles_affected', 0)}")
            print(f"Freed headcount:    {workforce.get('freed_headcount', 0):.0f}")
            print(f"Reduction:          {workforce.get('reduction_pct', 0):.1f}%")
            print(f"Gross savings:      ${financial.get('gross_savings', 0):,.0f}")
            tech_lic = financial.get('technology_licensing', 0)
            impl_cost = financial.get('implementation_cost', 0)
            change_mgmt = financial.get('change_management_cost', 0)
            severance = financial.get('severance_cost', 0)
            j_curve = financial.get('j_curve_cost', 0)
            if tech_lic > 0:
                print(f"  Tech licensing:   ${tech_lic:,.0f}")
            if impl_cost > 0:
                print(f"  Implementation:   ${impl_cost:,.0f}")
            if change_mgmt > 0:
                print(f"  Change mgmt:      ${change_mgmt:,.0f}")
            if severance > 0:
                print(f"  Severance:        ${severance:,.0f}")
            if j_curve > 0:
                print(f"  J-curve dip:      ${j_curve:,.0f}")
            print(f"Total cost:         ${financial.get('total_cost', 0):,.0f}")
            print(f"Net impact:         ${financial.get('net_impact', 0):,.0f}")
            print(f"ROI:                {financial.get('roi_pct', 0):.1f}%")
            print(f"Payback:            {financial.get('payback_months', 0)} months")
            print("=" * 60)

            # Risks
            risks = cascade.get("risks", {})
            if risks.get("flags"):
                print("\nRISK FLAGS:")
                for rf in risks["flags"]:
                    print(f"  [{rf['severity'].upper()}] {rf['type']}: {rf['detail']}")
        else:
            print("No cascade results (no tasks matched or no data in scope)")

        return scenario_id, manager

    finally:
        conn.close()


def _print_v2_result(result: dict, name: str):
    """Print v2 time-stepped simulation result."""
    if "error" in result:
        print(f"\nv2 simulation error: {result['error']}")
        return

    summary = result.get("trajectory_summary", {})
    theoretical = summary.get("theoretical_max", {})
    actual = summary.get("actual_at_end", {})
    hf = summary.get("human_factors_final", {})

    print("\n" + "=" * 70)
    print(f"SIMULATION RESULT (v2 time-stepped): {name}")
    print("=" * 70)

    print(f"\nTheoretical max (if 100% adoption from day 1):")
    print(f"  Freed headcount:     {theoretical.get('freed_headcount', 0):.0f}")
    print(f"  Gross savings:       ${theoretical.get('gross_savings', 0):,.0f}")

    print(f"\nActual at month {summary.get('timeline_months', 36)}:")
    print(f"  Adoption level:      {actual.get('adoption_level', 0):.1%}")
    print(f"  Effective freed HC:  {actual.get('effective_freed_hc', 0):.1f}")
    print(f"  Cumulative savings:  ${actual.get('cumulative_savings', 0):,.0f}")
    print(f"  Cumulative costs:    ${actual.get('cumulative_costs', 0):,.0f}")
    print(f"  Net impact:          ${actual.get('cumulative_net', 0):,.0f}")
    print(f"  NPV (10% discount):  ${actual.get('npv', 0):,.0f}")
    print(f"  ROI:                 {actual.get('roi_pct', 0):.1f}%")

    payback = summary.get("payback_month", 0)
    breakeven = summary.get("breakeven_month", 0)
    if payback > 0:
        print(f"  Payback month:       {payback}")
    if breakeven > 0:
        print(f"  Breakeven month:     {breakeven}")

    print(f"\nHuman Factors (final):")
    print(f"  Resistance:          {hf.get('resistance', 0):.2f}")
    print(f"  Morale:              {hf.get('morale', 0):.2f}")
    print(f"  Proficiency:         {hf.get('proficiency', 0):.2f}")
    print(f"  Culture readiness:   {hf.get('culture_readiness', 0):.2f}")
    print(f"  Composite (HFM):     {hf.get('composite_multiplier', 0):.2f}")

    print(f"\nTrajectory milestones:")
    print(f"  {'Month':>5}  {'Adopt':>6}  {'Freed HC':>9}  {'Savings':>12}  {'Costs':>12}  {'Net':>12}  {'HFM':>5}")
    print(f"  {'-'*5}  {'-'*6}  {'-'*9}  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*5}")
    for ms in result.get("milestones", []):
        m = ms["month"]
        a = ms["adoption"]["level"]
        fhc = ms["workforce"]["effective_freed_hc"]
        sav = ms["financial"]["cumulative_savings"]
        cst = ms["financial"]["cumulative_costs"]
        net = ms["financial"]["cumulative_net"]
        hfm_val = ms["human_factors"].get("composite_multiplier", 0)
        print(
            f"  {m:>5}  {a:>5.0%}  {fhc:>9.1f}  "
            f"${sav:>11,.0f}  ${cst:>11,.0f}  ${net:>11,.0f}  {hfm_val:>5.2f}"
        )

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run Digital Twin simulations")
    parser.add_argument("--type", choices=["role_redesign", "tech_adoption"],
                        default="role_redesign", help="Simulation type")
    parser.add_argument("--scope", default="Claims Management",
                        help="Function name to scope to")
    parser.add_argument("--factor", type=float, default=0.5,
                        help="Automation factor 0-1 (role_redesign only)")
    parser.add_argument("--tech", default="Microsoft Copilot",
                        help="Technology name (tech_adoption only)")
    parser.add_argument("--timeline", type=int, default=36,
                        help="Timeline in months (default: 36)")
    parser.add_argument("--engine", choices=["v1", "v2"], default="v1",
                        help="v1=single-shot cascade, v2=time-stepped (default: v1)")
    parser.add_argument("--list-tech", action="store_true",
                        help="List available technology profiles")

    # Simulation config overrides (Phase 3.9)
    config_group = parser.add_argument_group("simulation config overrides")
    config_group.add_argument("--redeployability", type=float, default=None,
                              help="Redeployability %% (default: 60)")
    config_group.add_argument("--reskilling-fraction", type=float, default=None,
                              help="Fraction needing reskilling (default: 0.3)")
    config_group.add_argument("--change-mgmt-pct", type=float, default=None,
                              help="Change management cost as %% of savings (default: 5)")
    config_group.add_argument("--severance-months", type=float, default=None,
                              help="Severance months per separated employee (default: 3)")
    config_group.add_argument("--j-curve", action="store_true", default=False,
                              help="Enable productivity J-curve dip")
    config_group.add_argument("--no-tech-cost", action="store_true", default=False,
                              help="Disable technology cost in role redesign")
    config_group.add_argument("--max-reduction", type=float, default=None,
                              help="Cap headcount reduction %% (default: no cap)")
    args = parser.parse_args()

    if args.list_tech:
        print("Available technologies:")
        for tech in TechAdoptionSimulation.available_technologies():
            print(f"  - {tech}")
        return

    try:
        run_simulation(args)
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
