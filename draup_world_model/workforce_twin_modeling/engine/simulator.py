"""
Open-Loop Simulator (Stage 2)
==============================
Time-stepped simulation with S-curves but NO feedback loops.
Human system parameters are FIXED — the adoption rate is determined
purely by the S-curve schedule.

This serves as the baseline for comparison with Stage 3 (feedback-enabled).
The difference between Stage 2 and Stage 3 outcomes IS the impact of
the human system — making it measurable and explainable.

Design: Same structure as simulator_fb.py, minus the feedback update.
  adoption_rate = S_curve(t)  [fixed, no human modulation]
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from workforce_twin_modeling.engine.rates import SimulationParams, RateParams
from workforce_twin_modeling.engine.cascade import (
    Stimulus, run_cascade, CascadeResult,
    AUTOMATION_FREED_PCT, AI_CATEGORIES, HUMAN_AI_CATEGORIES,
)
from workforce_twin_modeling.engine.loader import OrganizationData


# ============================================================
# Monthly Snapshot (open-loop — no human system trace)
# ============================================================

@dataclass
class MonthlySnapshot:
    """Monthly snapshot for open-loop simulation."""
    month: int

    # Adoption
    adopt_pct: float           # Phase 1 S-curve value
    expand_pct: float          # Phase 2 S-curve value
    extend_pct: float          # Phase 3 S-curve value
    combined_pct: float        # sum, capped at 1.0

    # Capacity
    gross_freed_hours: float
    redistributed_hours: float
    net_freed_hours: float
    cumulative_net_freed: float

    # Workforce
    headcount: int
    hc_reduced_this_month: int
    cumulative_hc_reduced: int

    # Skills
    skill_gap_opened: int
    skill_gap_closed: int
    current_skill_gap: int

    # Financial
    cumulative_investment: float
    cumulative_savings: float
    net_position: float
    monthly_savings_rate: float

    # Productivity
    productivity_index: float

    # Per-role
    role_headcounts: Dict[str, int] = field(default_factory=dict)


# ============================================================
# Simulation Result
# ============================================================

@dataclass
class SimulationResult:
    """Complete output of an open-loop simulation."""
    params: SimulationParams
    stimulus: Stimulus
    baseline: CascadeResult
    timeline: List[MonthlySnapshot]

    # Summary
    total_months: int = 0
    final_headcount: int = 0
    total_hc_reduced: int = 0
    total_investment: float = 0.0
    total_savings: float = 0.0
    net_savings: float = 0.0
    payback_month: int = 0
    peak_skill_gap_month: int = 0
    peak_skill_gap_value: int = 0
    productivity_valley_month: int = 0
    productivity_valley_value: float = 100.0


# ============================================================
# The Open-Loop Simulator
# ============================================================

def simulate(
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
) -> SimulationResult:
    """
    Run time-stepped simulation WITHOUT feedback loops.
    Adoption follows S-curves only. Human system is not modeled.
    This is the Stage 2 baseline.
    """
    # Run Stage 1 cascade for ceiling values (full instant adoption)
    ceiling_stimulus = Stimulus(
        name=stimulus.name,
        stimulus_type=stimulus.stimulus_type,
        tools=stimulus.tools,
        target_scope=stimulus.target_scope,
        target_functions=stimulus.target_functions,
        target_roles=stimulus.target_roles,
        policy=params.policy,
        absorption_factor=params.absorption_factor,
        alpha=1.0,
        training_cost_per_person=params.training_cost_per_person,
    )
    baseline = run_cascade(ceiling_stimulus, org)

    # Extract ceilings from cascade
    ceiling_gross_freed = baseline.step3_capacity.total_gross_freed_hours
    ceiling_sunrise_skills = len(baseline.step4_skills.sunrise_skills)
    original_hc = baseline.step5_workforce.total_current_hc

    role_ceiling_gross = {}
    for rc in baseline.step3_capacity.role_capacities:
        role_ceiling_gross[rc.role_id] = rc.gross_freed_hours_pp * rc.headcount

    # Investment profile
    license_annual = baseline.step6_financial.license_cost_annual
    training_total = baseline.step6_financial.training_cost
    change_mgmt_total = baseline.step6_financial.change_management_cost
    monthly_license = license_annual / 12.0
    training_per_month_phase1 = training_total / 6.0
    change_mgmt_per_month = change_mgmt_total / 6.0

    role_salaries = {wi.role_id: org.roles[wi.role_id].avg_salary
                     for wi in baseline.step5_workforce.role_impacts}

    # ── Initialize state ──
    current_hc = {r.role_id: r.current_hc for r in baseline.step5_workforce.role_impacts}
    cumulative_net_freed = 0.0
    cumulative_investment = 0.0
    cumulative_savings = 0.0
    cumulative_hc_reduced = 0
    skill_gap_opened = 0
    skill_gap_closed = 0
    prev_combined = 0.0
    timeline = []

    # ── Time loop ──
    for month in range(params.time_horizon_months + 1):
        # 1. S-curve adoption rates (pure, no feedback)
        adopt = params.adoption.at(month) if params.adoption else 0.0
        expand = params.expansion.at(month) if params.expansion else 0.0
        extend = params.extension.at(month) if params.extension else 0.0
        combined = min(1.0, adopt + expand + extend)

        # Workflow automation bonus for P5
        if params.enable_workflow_automation and extend > 0:
            combined = min(1.0, combined * params.workflow_automation_bonus)

        # Incremental adoption
        delta = max(0, combined - prev_combined)
        prev_combined = combined

        # 2. Scale freed hours
        gross_freed = ceiling_gross_freed * delta
        redistributed = gross_freed * params.absorption_factor
        net_freed = gross_freed - redistributed
        cumulative_net_freed += net_freed

        # 3. Skill gap dynamics
        new_sunrise = int(ceiling_sunrise_skills * delta)
        skill_gap_opened += new_sunrise
        if month >= params.reskilling_delay_months and skill_gap_opened > 0:
            closeable = int(skill_gap_opened * params.reskilling_rate)
            closeable = min(closeable, skill_gap_opened - skill_gap_closed)
            skill_gap_closed += max(0, closeable)
        current_gap = max(0, skill_gap_opened - skill_gap_closed)

        # 4. HC decisions (quarterly)
        hc_reduced_this_month = 0
        if month > 0 and month % params.hc_review_frequency == 0:
            for rid in list(current_hc.keys()):
                role = org.roles[rid]
                ceil = role_ceiling_gross.get(rid, 0)
                role_freed = ceil * combined * (1 - params.absorption_factor)
                fte_freed = role_freed / 160.0
                already_reduced = role.headcount - current_hc[rid]
                net_new = fte_freed - already_reduced

                if net_new >= 1.0:
                    if params.policy == "no_layoffs":
                        reducible = 0
                    elif params.policy == "natural_attrition":
                        max_attrition = max(1, int(current_hc[rid] * 0.02))
                        reducible = min(math.floor(net_new), max_attrition)
                    elif params.policy == "moderate_reduction":
                        reducible = math.floor(net_new)
                    elif params.policy == "active_reduction":
                        reducible = round(net_new)
                    elif params.policy == "rapid_redeployment":
                        reducible = math.floor(net_new * 0.8)  # 80% redeployed
                    else:
                        reducible = math.floor(net_new)

                    reducible = min(reducible, current_hc[rid])
                    if reducible > 0:
                        current_hc[rid] -= reducible
                        hc_reduced_this_month += reducible

        cumulative_hc_reduced += hc_reduced_this_month
        total_current_hc = sum(current_hc.values())

        # 5. Financial
        monthly_investment = 0.0
        if month >= 1:
            monthly_investment += monthly_license
        if 1 <= month <= 6:
            monthly_investment += training_per_month_phase1 + change_mgmt_per_month
        cumulative_investment += monthly_investment

        monthly_salary_savings = 0.0
        for rid, hc in current_hc.items():
            reduced = org.roles[rid].headcount - hc
            if reduced > 0:
                monthly_salary_savings += reduced * role_salaries.get(rid, 0) / 12.0
        cumulative_savings += monthly_salary_savings
        net_position = cumulative_savings - cumulative_investment

        # 6. Productivity (simple model — no feedback)
        gap_pct = current_gap / max(1, ceiling_sunrise_skills) * 100
        automation_lift = combined * 15.0
        skill_drag = gap_pct * 0.15
        productivity = 100.0 + automation_lift - skill_drag

        # Record
        snapshot = MonthlySnapshot(
            month=month,
            adopt_pct=adopt,
            expand_pct=expand,
            extend_pct=extend,
            combined_pct=combined,
            gross_freed_hours=gross_freed,
            redistributed_hours=redistributed,
            net_freed_hours=net_freed,
            cumulative_net_freed=cumulative_net_freed,
            headcount=total_current_hc,
            hc_reduced_this_month=hc_reduced_this_month,
            cumulative_hc_reduced=cumulative_hc_reduced,
            skill_gap_opened=skill_gap_opened,
            skill_gap_closed=skill_gap_closed,
            current_skill_gap=current_gap,
            cumulative_investment=cumulative_investment,
            cumulative_savings=cumulative_savings,
            net_position=net_position,
            monthly_savings_rate=monthly_salary_savings,
            productivity_index=productivity,
            role_headcounts=dict(current_hc),
        )
        timeline.append(snapshot)

    # ── Summary ──
    payback_month = 0
    for snap in timeline:
        if snap.net_position > 0 and payback_month == 0 and snap.month > 0:
            payback_month = snap.month
            break

    peak_gap = max(timeline, key=lambda s: s.current_skill_gap)
    valley = min(timeline, key=lambda s: s.productivity_index)

    return SimulationResult(
        params=params,
        stimulus=stimulus,
        baseline=baseline,
        timeline=timeline,
        total_months=params.time_horizon_months,
        final_headcount=timeline[-1].headcount,
        total_hc_reduced=timeline[-1].cumulative_hc_reduced,
        total_investment=timeline[-1].cumulative_investment,
        total_savings=timeline[-1].cumulative_savings,
        net_savings=timeline[-1].net_position,
        payback_month=payback_month,
        peak_skill_gap_month=peak_gap.month,
        peak_skill_gap_value=peak_gap.current_skill_gap,
        productivity_valley_month=valley.month,
        productivity_valley_value=valley.productivity_index,
    )
