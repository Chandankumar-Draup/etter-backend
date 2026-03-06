"""Time-series simulation endpoints (with feedback loops)."""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workforce_twin_modeling.api.app import get_org, resolve_company
from workforce_twin_modeling.api.serializers import serialize_fb_result, serialize_sim_params

from workforce_twin_modeling.engine.cascade import Stimulus
from workforce_twin_modeling.engine.feedback import FeedbackParams, HumanSystemState
from workforce_twin_modeling.engine.inverse_solver import solve_inverse
from workforce_twin_modeling.engine.rates import (
    SimulationParams, RateParams, ALL_SCENARIOS,
    P1_CAUTIOUS, P2_BALANCED, P3_AGGRESSIVE, P4_CAPABILITY_FIRST, P5_ACCELERATED,
)
from workforce_twin_modeling.engine.simulator_fb import simulate_with_feedback

router = APIRouter(tags=["simulation"])


class RateParamsInput(BaseModel):
    alpha: float = 0.6
    k: float = 0.3
    midpoint: float = 4.0
    delay_months: int = 0


class FeedbackOverrides(BaseModel):
    """Optional overrides for all 8 feedback loop parameters."""
    # B1: Capacity Absorption
    base_absorption: Optional[float] = None
    workload_absorption_sensitivity: Optional[float] = None
    # B2: Skill Valley
    skill_gap_drag_coefficient: Optional[float] = None
    # B3: Change Resistance
    resistance_sensitivity: Optional[float] = None
    resistance_decay_rate: Optional[float] = None
    fatigue_build_rate: Optional[float] = None
    fatigue_decay_rate: Optional[float] = None
    # B4: Seniority Offset
    seniority_penalty: Optional[float] = None
    # R1: Trust-Adoption
    trust_build_rate: Optional[float] = None
    trust_destruction_factor: Optional[float] = None
    success_probability: Optional[float] = None
    # R2: Proficiency
    learning_rate: Optional[float] = None
    learning_saturation: Optional[float] = None
    # R3: Savings
    reinvestment_rate: Optional[float] = None
    reinvestment_effectiveness: Optional[float] = None
    # R4: Political Capital
    capital_build_rate: Optional[float] = None
    capital_spend_rate: Optional[float] = None
    capital_threshold: Optional[float] = None
    # Events & dynamics
    hc_decision_delay_months: Optional[int] = None
    hallucination_base_rate: Optional[float] = None
    ai_error_month: Optional[int] = None


class SimulationRequest(BaseModel):
    """Full simulation configuration."""
    # Stimulus
    stimulus_name: str = "Technology Injection"
    stimulus_type: str = "technology_injection"
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []
    policy: str = "moderate_reduction"
    absorption_factor: float = 0.35
    training_cost_per_person: float = 2000

    # Rate parameters
    scenario_name: str = "Custom"
    adoption: Optional[RateParamsInput] = None
    expansion: Optional[RateParamsInput] = None
    extension: Optional[RateParamsInput] = None
    time_horizon_months: int = 36
    hc_review_frequency: int = 3

    # Feedback overrides (optional — full parameter set)
    feedback: Optional[FeedbackOverrides] = None

    # Legacy fields (still accepted for backwards compatibility)
    trust_build_rate: Optional[float] = None
    resistance_sensitivity: Optional[float] = None

    # Inverse solve targets (for target-based stimulus types)
    target_hc_reduction_pct: Optional[float] = None    # headcount_target: e.g. 15.0 for 15%
    target_budget_amount: Optional[float] = None        # budget_constraint: e.g. 2000000
    target_automation_pct: Optional[float] = None       # automation_target / competitive: e.g. 35.0

    # Trace
    trace: bool = False


@router.post("/simulate")
async def run_simulation(req: SimulationRequest, company: str = Depends(resolve_company)):
    """Run time-series simulation with feedback loops.

    For target-based stimulus types (headcount_target, budget_constraint,
    automation_target, competitive), the engine runs inverse propagation:
    binary search on adoption alpha to find the value that produces the
    target outcome. The response includes an 'inverse_solve' section with
    solver metadata alongside the standard simulation result.
    """
    org = get_org(company)

    target_fns = req.target_functions if req.target_functions else org.functions

    stimulus = Stimulus(
        name=req.stimulus_name,
        stimulus_type=req.stimulus_type,
        tools=req.tools,
        target_scope="function" if len(target_fns) < len(org.functions) else "ALL",
        target_functions=target_fns,
        policy=req.policy,
        absorption_factor=req.absorption_factor,
        training_cost_per_person=req.training_cost_per_person,
        target_hc_reduction_pct=req.target_hc_reduction_pct,
        target_budget_amount=req.target_budget_amount,
        target_automation_pct=req.target_automation_pct,
    )

    # Build rate params
    adopt = RateParams(**req.adoption.model_dump()) if req.adoption else RateParams(alpha=0.6, k=0.3, midpoint=4)
    expand = RateParams(**req.expansion.model_dump()) if req.expansion else None
    extend = RateParams(**req.extension.model_dump()) if req.extension else None

    params = SimulationParams(
        scenario_id="CUSTOM",
        scenario_name=req.scenario_name,
        adoption=adopt,
        expansion=expand,
        extension=extend,
        policy=req.policy,
        absorption_factor=req.absorption_factor,
        time_horizon_months=req.time_horizon_months,
        hc_review_frequency=req.hc_review_frequency,
        enable_workflow_automation=extend is not None,
    )

    # Build feedback params with optional overrides
    fb_params = FeedbackParams()
    # Apply structured feedback overrides
    if req.feedback:
        for field_name, value in req.feedback.model_dump(exclude_none=True).items():
            setattr(fb_params, field_name, value)
    # Legacy field support
    if req.trust_build_rate is not None:
        fb_params.trust_build_rate = req.trust_build_rate
    if req.resistance_sensitivity is not None:
        fb_params.resistance_sensitivity = req.resistance_sensitivity

    # ── Inverse propagation: route target-based types to solver ──
    inverse_target = _get_inverse_target(req)
    if inverse_target is not None:
        solve_result = solve_inverse(
            stimulus_type=req.stimulus_type,
            target_value=inverse_target,
            stimulus=stimulus,
            org=org,
            params=params,
            fb_params=fb_params,
        )
        if solve_result is not None:
            # Re-run the solved result with trace enabled if requested
            if req.trace:
                final_result = _rerun_with_trace(
                    solve_result.solved_alpha, stimulus, org, params, fb_params,
                )
            else:
                final_result = solve_result.simulation_result

            response = serialize_fb_result(final_result)
            response["inverse_solve"] = {
                "solved": solve_result.solved,
                "solved_alpha": round(solve_result.solved_alpha, 4),
                "target_value": round(solve_result.target_value, 2),
                "achieved_value": round(solve_result.achieved_value, 2),
                "error_pct": round(solve_result.error_pct, 2),
                "iterations": solve_result.iterations,
                "feasibility_range": [
                    round(solve_result.feasibility_range[0], 2),
                    round(solve_result.feasibility_range[1], 2),
                ],
                "message": solve_result.message,
            }
            return response

    # ── Standard forward simulation ──
    result = simulate_with_feedback(stimulus, org, params, fb_params, trace=req.trace)
    return serialize_fb_result(result)


def _get_inverse_target(req: SimulationRequest) -> Optional[float]:
    """Extract the inverse solve target value based on stimulus_type."""
    if req.stimulus_type == "headcount_target" and req.target_hc_reduction_pct is not None:
        return req.target_hc_reduction_pct
    if req.stimulus_type == "budget_constraint" and req.target_budget_amount is not None:
        return req.target_budget_amount
    if req.stimulus_type in ("automation_target", "competitive") and req.target_automation_pct is not None:
        return req.target_automation_pct
    return None


def _rerun_with_trace(
    solved_alpha: float,
    stimulus: Stimulus,
    org,
    base_params: SimulationParams,
    fb_params: FeedbackParams,
):
    """Re-run the simulation at the solved alpha with tracing enabled."""
    adopt = RateParams(
        alpha=solved_alpha,
        k=base_params.adoption.k if base_params.adoption else 0.3,
        midpoint=base_params.adoption.midpoint if base_params.adoption else 4.0,
        delay_months=base_params.adoption.delay_months if base_params.adoption else 0,
    )
    scale = solved_alpha / max(0.01, base_params.adoption.alpha) if base_params.adoption else 1.0
    expand = None
    if base_params.expansion:
        expand = RateParams(
            alpha=min(1.0, base_params.expansion.alpha * scale),
            k=base_params.expansion.k,
            midpoint=base_params.expansion.midpoint,
            delay_months=base_params.expansion.delay_months,
        )
    extend = None
    if base_params.extension:
        extend = RateParams(
            alpha=min(1.0, base_params.extension.alpha * scale),
            k=base_params.extension.k,
            midpoint=base_params.extension.midpoint,
            delay_months=base_params.extension.delay_months,
        )
    params = SimulationParams(
        scenario_id=base_params.scenario_id,
        scenario_name=base_params.scenario_name,
        adoption=adopt,
        expansion=expand,
        extension=extend,
        policy=base_params.policy,
        absorption_factor=base_params.absorption_factor,
        training_cost_per_person=base_params.training_cost_per_person,
        time_horizon_months=base_params.time_horizon_months,
        hc_review_frequency=base_params.hc_review_frequency,
        reskilling_delay_months=base_params.reskilling_delay_months,
        reskilling_rate=base_params.reskilling_rate,
        enable_workflow_automation=base_params.enable_workflow_automation,
        workflow_automation_bonus=base_params.workflow_automation_bonus,
    )
    return simulate_with_feedback(stimulus, org, params, fb_params, trace=True)


@router.post("/simulate/preset/{preset_id}")
async def run_preset_simulation(preset_id: str, trace: bool = False, company: str = Depends(resolve_company)):
    """Run a preset scenario (P1-P5) with default parameters."""
    org = get_org(company)
    preset = ALL_SCENARIOS.get(preset_id.upper())
    if not preset:
        return {"error": f"Preset '{preset_id}' not found. Available: P1, P2, P3, P4, P5"}

    stimulus = Stimulus(
        name=f"{preset.scenario_name} Scenario",
        stimulus_type="technology_injection",
        tools=["Microsoft Copilot"],
        target_scope="ALL",
        target_functions=org.functions,
        policy=preset.policy,
        absorption_factor=preset.absorption_factor,
    )

    result = simulate_with_feedback(stimulus, org, preset, trace=trace)
    return serialize_fb_result(result)


@router.get("/simulate/presets")
async def get_presets(company: str = Depends(resolve_company)):
    """Available preset scenarios with their parameters."""
    return [
        {
            "id": sid,
            "name": sp.scenario_name,
            "policy": sp.policy,
            "params": serialize_sim_params(sp),
            "description": _preset_description(sid),
        }
        for sid, sp in ALL_SCENARIOS.items()
    ]


def _preset_description(sid: str) -> str:
    descs = {
        "P1": "Close adoption gap only, natural attrition. Safest, slowest.",
        "P2": "Adopt + expand, moderate reductions. Balanced approach.",
        "P3": "All 3 phases, active reductions. Aggressive transformation.",
        "P4": "No layoffs, redirect all freed capacity. Capability-building focus.",
        "P5": "Workflow automation, rapid redeployment. AI-age acceleration.",
    }
    return descs.get(sid, "")
