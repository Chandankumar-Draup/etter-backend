"""Multi-scenario comparison endpoint."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workforce_twin_modeling.api.app import get_org, resolve_company
from workforce_twin_modeling.api.serializers import serialize_fb_result, _r

from workforce_twin_modeling.engine.cascade import Stimulus
from workforce_twin_modeling.engine.feedback import FeedbackParams
from workforce_twin_modeling.engine.rates import SimulationParams, RateParams, ALL_SCENARIOS
from workforce_twin_modeling.engine.simulator_fb import simulate_with_feedback

router = APIRouter(tags=["compare"])


class CompareScenario(BaseModel):
    """A scenario to include in comparison."""
    name: Optional[str] = None
    preset_id: Optional[str] = None  # P1-P5, if using preset
    # Custom params (used if preset_id is None)
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []
    policy: str = "moderate_reduction"
    alpha_adopt: float = 0.6
    alpha_expand: float = 0.0
    alpha_extend: float = 0.0
    k: float = 0.3
    midpoint: float = 4.0
    time_horizon_months: int = 36


class CompareRequest(BaseModel):
    """Request to compare multiple scenarios."""
    scenarios: List[CompareScenario]
    trace: bool = False


@router.post("/compare")
async def compare_scenarios(req: CompareRequest, company: str = Depends(resolve_company)):
    """Run multiple scenarios and return comparison data."""
    org = get_org(company)
    results = []

    for sc in req.scenarios:
        scenario_name = sc.name
        if sc.preset_id and sc.preset_id.upper() in ALL_SCENARIOS:
            preset = ALL_SCENARIOS[sc.preset_id.upper()]
            scenario_name = scenario_name or preset.scenario_name
            stimulus = Stimulus(
                name=scenario_name,
                stimulus_type="technology_injection",
                tools=sc.tools,
                target_scope="ALL",
                target_functions=org.functions,
                policy=preset.policy,
                absorption_factor=preset.absorption_factor,
            )
            sim_result = simulate_with_feedback(stimulus, org, preset, trace=req.trace)
        else:
            target_fns = sc.target_functions if sc.target_functions else org.functions
            scenario_name = scenario_name or "Custom"
            stimulus = Stimulus(
                name=scenario_name,
                stimulus_type="technology_injection",
                tools=sc.tools,
                target_scope="function" if len(target_fns) < len(org.functions) else "ALL",
                target_functions=target_fns,
                policy=sc.policy,
                absorption_factor=0.35,
            )
            adopt = RateParams(alpha=sc.alpha_adopt, k=sc.k, midpoint=sc.midpoint)
            expand = RateParams(alpha=sc.alpha_expand, k=sc.k, midpoint=sc.midpoint,
                                delay_months=6) if sc.alpha_expand > 0 else None
            extend = RateParams(alpha=sc.alpha_extend, k=sc.k, midpoint=sc.midpoint,
                                delay_months=10) if sc.alpha_extend > 0 else None
            params = SimulationParams(
                scenario_id="CMP",
                scenario_name=sc.name,
                adoption=adopt, expansion=expand, extension=extend,
                policy=sc.policy,
                time_horizon_months=sc.time_horizon_months,
                enable_workflow_automation=extend is not None,
            )
            sim_result = simulate_with_feedback(stimulus, org, params, trace=req.trace)

        results.append({
            "name": scenario_name,
            "result": serialize_fb_result(sim_result),
        })

    # Build comparison matrix
    metrics = [
        "total_hc_reduced", "net_savings", "total_investment", "total_savings",
        "payback_month", "final_proficiency", "final_trust", "final_readiness",
        "productivity_valley_value", "avg_adoption_dampening",
    ]
    matrix = {m: [] for m in metrics}
    for r in results:
        summary = r["result"]["summary"]
        for m in metrics:
            matrix[m].append(summary.get(m, 0))

    return {
        "scenarios": results,
        "comparison_matrix": {
            "metric_names": metrics,
            "scenario_names": [r["name"] for r in results],
            "values": matrix,
        },
    }
