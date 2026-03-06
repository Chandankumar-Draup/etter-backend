"""
Scenario Executor
==================
Maps the 40-scenario catalog to the simulation engine.
Each scenario in the CSV defines WHAT to simulate.
This module translates WHAT → HOW (engine parameters).

Design: One function maps CSV row → (Stimulus, SimulationParams, FeedbackParams).
        One function runs a scenario and returns results.
        One function runs a batch and compares.

Principle: The catalog is the WHAT (business question).
           The engine is the HOW (mechanics).
           This module is the bridge — keep it thin.
"""
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workforce_twin_modeling.engine.loader import load_organization, OrganizationData
from workforce_twin_modeling.engine.cascade import Stimulus
from workforce_twin_modeling.engine.rates import SimulationParams, RateParams
from workforce_twin_modeling.engine.feedback import HumanSystemState, FeedbackParams
from workforce_twin_modeling.engine.simulator_fb import simulate_with_feedback, FBSimulationResult


# ============================================================
# Scenario → Engine Parameter Mapping
# ============================================================

def _parse_phases(phases_str: str) -> list:
    """Parse comma-separated phases."""
    if not phases_str:
        return ["adoption"]
    return [p.strip() for p in phases_str.split(",")]


def _parse_tools(tools_str: str, org: OrganizationData) -> list:
    """Resolve tool names. ALL_DEPLOYED → all tools in org."""
    if not tools_str:
        return []
    if tools_str.strip() == "ALL_DEPLOYED":
        return [t.tool_name for t in org.tools.values()]
    if tools_str.strip() == "ALL_AVAILABLE":
        return [t.tool_name for t in org.tools.values()]
    return [t.strip() for t in tools_str.split(",")]


def _parse_functions(func_str: str, org: OrganizationData) -> list:
    """Resolve function names. ALL → all functions in org."""
    if not func_str:
        return []
    funcs = [f.strip() for f in func_str.split(",")]
    if "ALL" in funcs or func_str.strip() == "ALL":
        return org.functions
    return funcs


def _safe_float(val, default=0.0):
    """Safely parse float from CSV."""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    """Safely parse int from CSV."""
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default


def map_scenario(row: dict, org: OrganizationData) -> Tuple[Stimulus, SimulationParams, FeedbackParams]:
    """
    Map a scenario catalog row to engine parameters.
    This is the single translation point between business intent and simulation mechanics.
    """
    # Parse basic fields
    alpha_adopt = _safe_float(row.get("alpha_adopt"), 0.6)
    alpha_expand = _safe_float(row.get("alpha_expand"), 0.0)
    alpha_extend = _safe_float(row.get("alpha_extend"), 0.0)
    k = _safe_float(row.get("s_curve_k"), 0.3)
    midpoint = _safe_float(row.get("s_curve_midpoint"), 4)
    time_horizon = _safe_int(row.get("time_horizon_months"), 36)
    policy = row.get("hc_policy", "moderate_reduction") or "moderate_reduction"
    readiness_threshold = _safe_float(row.get("readiness_threshold"), 0)
    tools = _parse_tools(row.get("tools", ""), org)
    functions = _parse_functions(row.get("target_functions", ""), org)
    target_scope = row.get("target_scope", "ALL") or "ALL"

    # Build rate parameters
    phases = _parse_phases(row.get("adoption_phases", "adoption"))
    adoption = RateParams(alpha=alpha_adopt, k=k, midpoint=midpoint) if "adoption" in phases else None
    expansion = RateParams(alpha=alpha_expand, k=k, midpoint=midpoint, delay_months=6) if "expansion" in phases and alpha_expand > 0 else None
    extension = RateParams(alpha=alpha_extend, k=k, midpoint=midpoint, delay_months=10) if "extension" in phases and alpha_extend > 0 else None

    # Build SimulationParams
    params = SimulationParams(
        scenario_id=row.get("scenario_id", "SC-?"),
        scenario_name=row.get("scenario_name", "Unknown"),
        adoption=adoption,
        expansion=expansion,
        extension=extension,
        policy=policy,
        absorption_factor=0.35,
        training_cost_per_person=2000,
        readiness_threshold=readiness_threshold,
        time_horizon_months=time_horizon,
        enable_workflow_automation=("extension" in phases and alpha_extend > 0),
    )

    # Build Stimulus
    if not tools:
        tools = ["Microsoft Copilot"]  # default
    scope_type = "function" if len(functions) == 1 else "ALL"

    stimulus = Stimulus(
        name=row.get("scenario_name", "Scenario"),
        stimulus_type="technology_injection",
        tools=tools,
        target_scope=scope_type,
        target_functions=functions if functions else org.functions,
        policy=policy,
        absorption_factor=0.35,
        training_cost_per_person=2000,
    )

    # Build FeedbackParams (events)
    fb_params = FeedbackParams()
    events_str = row.get("events", "[]")
    if events_str and events_str != "[]":
        try:
            events = json.loads(events_str)
            for evt in events:
                if isinstance(evt, dict) and evt.get("type") == "ai_error":
                    fb_params.ai_error_month = evt.get("month", 7)
        except (json.JSONDecodeError, TypeError):
            pass

    return stimulus, params, fb_params


# ============================================================
# Scenario Result
# ============================================================

@dataclass
class ScenarioResult:
    """Result of executing one scenario."""
    scenario_id: str
    scenario_name: str
    family: str
    direction: str
    result: Optional[FBSimulationResult] = None
    error: Optional[str] = None

    # Summary metrics (extracted from result)
    hc_reduced: int = 0
    final_hc: int = 0
    net_savings: float = 0.0
    total_investment: float = 0.0
    total_savings: float = 0.0
    payback_month: int = 0
    final_proficiency: float = 0.0
    final_trust: float = 0.0
    risk_score: float = 0.0

    def extract_metrics(self):
        """Pull summary metrics from simulation result."""
        if self.result:
            self.hc_reduced = self.result.total_hc_reduced
            self.final_hc = self.result.final_headcount
            self.net_savings = self.result.net_savings
            self.total_investment = self.result.total_investment
            self.total_savings = self.result.total_savings
            self.payback_month = self.result.payback_month
            self.final_proficiency = self.result.final_proficiency
            self.final_trust = self.result.final_trust


# ============================================================
# Executor
# ============================================================

def run_scenario(
    row: dict,
    org: OrganizationData,
    trace: bool = False,
) -> ScenarioResult:
    """Execute a single scenario from the catalog.

    Args:
        trace: When True, enables per-month computation tracing in the simulation.
               Access via result.result.trace (SimulationTrace object).
    """
    sid = row.get("scenario_id", "?")
    sname = row.get("scenario_name", "?")
    family = row.get("scenario_family", "?")
    direction = row.get("direction", "forward")

    sr = ScenarioResult(
        scenario_id=sid,
        scenario_name=sname,
        family=family,
        direction=direction,
    )

    try:
        stimulus, params, fb_params = map_scenario(row, org)
        result = simulate_with_feedback(stimulus, org, params, fb_params, trace=trace)
        sr.result = result
        sr.extract_metrics()
    except Exception as e:
        sr.error = str(e)

    return sr


def load_catalog(catalog_path: str) -> list:
    """Load scenario catalog from CSV."""
    with open(catalog_path, newline='') as f:
        return list(csv.DictReader(f))


def run_batch(
    catalog_path: str,
    org: OrganizationData,
    scenario_ids: list = None,
    families: list = None,
) -> List[ScenarioResult]:
    """
    Run a batch of scenarios.
    Filter by IDs or families. None = run all.
    """
    rows = load_catalog(catalog_path)

    if scenario_ids:
        rows = [r for r in rows if r["scenario_id"] in scenario_ids]
    if families:
        rows = [r for r in rows if r["scenario_family"] in families]

    results = []
    for row in rows:
        sid = row.get("scenario_id", "?")
        sname = row.get("scenario_name", "?")[:50]
        print(f"    {sid:<10} {sname:<50}", end="", flush=True)
        sr = run_scenario(row, org)
        status = "✓" if sr.error is None else f"✗ {sr.error[:40]}"
        print(f" {status}")
        results.append(sr)

    return results


# ============================================================
# Output
# ============================================================

def print_batch_summary(results: List[ScenarioResult]):
    """Print comparison table for batch results."""
    W = 120
    print(f"\n{'='*W}")
    print(f"  SCENARIO CATALOG EXECUTION SUMMARY")
    print(f"{'='*W}")

    # Group by family
    families = {}
    for sr in results:
        families.setdefault(sr.family, []).append(sr)

    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    print(f"\n  Executed: {len(results)} scenarios")
    print(f"  Passed:   {len(successful)}")
    print(f"  Failed:   {len(failed)}")

    if failed:
        print(f"\n  FAILURES:")
        for sr in failed:
            print(f"    {sr.scenario_id}: {sr.error}")

    # Comparison table
    print(f"\n  {'─'*W}")
    print(f"  {'ID':<10} {'Name':<45} {'Family':<22} {'HC↓':>4} {'Net$M':>8} {'Inv$M':>7} {'Sav$M':>7} {'Pay':>4} {'Prof':>5} {'Trust':>5}")
    print(f"  {'─'*W}")

    for sr in successful:
        payback = f"M{sr.payback_month}" if sr.payback_month > 0 else "N/A"
        print(f"  {sr.scenario_id:<10} {sr.scenario_name[:44]:<45} {sr.family[:21]:<22} "
              f"{sr.hc_reduced:>4} {sr.net_savings/1e6:>7.1f} {sr.total_investment/1e6:>6.1f} "
              f"{sr.total_savings/1e6:>6.1f} {payback:>4} {sr.final_proficiency:>5.1f} {sr.final_trust:>5.1f}")

    print(f"  {'─'*W}")


def export_batch(results: List[ScenarioResult], output_path: str):
    """Export batch results to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    rows = []
    for sr in results:
        rows.append({
            "scenario_id": sr.scenario_id,
            "scenario_name": sr.scenario_name,
            "family": sr.family,
            "direction": sr.direction,
            "status": "pass" if sr.error is None else "fail",
            "error": sr.error or "",
            "hc_reduced": sr.hc_reduced,
            "final_hc": sr.final_hc,
            "net_savings": round(sr.net_savings, 0),
            "total_investment": round(sr.total_investment, 0),
            "total_savings": round(sr.total_savings, 0),
            "payback_month": sr.payback_month,
            "final_proficiency": round(sr.final_proficiency, 1),
            "final_trust": round(sr.final_trust, 1),
        })
    if rows:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  Exported to {output_path}")


# ============================================================
# Main
# ============================================================

def main(data_dir: str, catalog_path: str, output_dir: str = None):
    """Run all scenarios from the catalog."""
    print(f"\n  Loading organization data from {data_dir}...")
    org = load_organization(data_dir)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.tasks)} tasks")

    print(f"\n  Running scenario catalog...")
    results = run_batch(catalog_path, org)

    print_batch_summary(results)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        export_batch(results, os.path.join(output_dir, "scenario_catalog_results.csv"))

    return results


if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main(
        data_dir=os.path.join(PROJECT_ROOT, "data"),
        catalog_path=os.path.join(PROJECT_ROOT, "scenario_catalog", "simulation_scenarios_extended.csv"),
        output_dir=os.path.join(PROJECT_ROOT, "outputs", "catalog"),
    )
