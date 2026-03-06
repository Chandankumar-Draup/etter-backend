"""
Feedback-Enabled Simulator (Stage 3)
======================================
Same structure as Stage 2 simulator, but:
  - Human system parameters are DYNAMIC (change each month)
  - 8 feedback loops modulate adoption rates and absorption
  - AI error events can be injected for testing trust asymmetry
  - Loop contributions are traced for explainability

The key difference in the rate equation:
  Stage 2: adoption_rate = alpha × S_curve(t)  [fixed]
  Stage 3: adoption_rate = alpha × S_curve(t) × f(proficiency, readiness, trust, skill_gap, seniority, capital)  [dynamic]

This makes the system NON-LINEAR:
  - Same stimulus to different functions → different outcomes
  - Same stimulus at different times → different outcomes (path dependency)
  - Small changes in initial conditions → large divergence over time
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.rates import SimulationParams, RateParams
from collections import deque
from engine.cascade import (
    Stimulus, run_cascade, CascadeResult,
    AUTOMATION_FREED_PCT, AI_CATEGORIES, HUMAN_AI_CATEGORIES,
    productive_hours_month,
)
from engine.loader import OrganizationData
from engine.feedback import (
    HumanSystemState, FeedbackParams,
    compute_effective_adoption, compute_dynamic_absorption,
    update_human_system, b2_skill_valley, b4_seniority_offset,
    r3_savings_reinvestment,
    r1_trust_adoption, r2_proficiency, b3_change_resistance, r4_political_capital,
)
from engine.trace import (
    MonthTrace, SimulationTrace,
    trust_band, capital_band,
    determine_dominant_loop, compute_phase_summary, compute_improvement_summary,
    format_trace,
)

# T2-#10: Capacity realization delay — months between adoption and freed hours
CAPACITY_REALIZATION_DELAY = 2

# T2-#10: Capacity realization delay — months between adoption and freed hours
CAPACITY_REALIZATION_DELAY = 2


# ============================================================
# Extended Monthly Snapshot (includes human system trace)
# ============================================================

@dataclass
class FBMonthlySnapshot:
    """Monthly snapshot WITH feedback loop tracing."""
    month: int

    # Adoption
    raw_adoption_pct: float         # S-curve only (what Stage 2 would give)
    effective_adoption_pct: float   # after all feedback multipliers
    adoption_dampening: float       # effective / raw (shows feedback impact)

    # Capacity
    gross_freed_hours: float
    redistributed_hours: float
    net_freed_hours: float
    cumulative_net_freed: float
    dynamic_absorption_rate: float  # changes over time (B1)

    # Workforce
    headcount: int
    hc_reduced_this_month: int
    cumulative_hc_reduced: int
    hc_pct_of_original: float

    # Skills
    skill_gap_opened: int
    skill_gap_closed: int
    current_skill_gap: int
    skill_gap_pct: float

    # Financial
    cumulative_investment: float
    cumulative_savings: float
    net_position: float
    monthly_savings_rate: float

    # Productivity
    productivity_index: float

    # Human System State (the key addition)
    proficiency: float
    readiness: float
    trust: float
    political_capital: float
    transformation_fatigue: float
    human_multiplier: float         # proficiency × readiness
    trust_multiplier: float
    capital_multiplier: float

    # Loop contributions (for explainability)
    b2_skill_drag: float            # how much skill gap is dragging
    b4_seniority_mult: float        # seniority offset
    ai_error_occurred: bool = False

    # Per-role
    role_headcounts: Dict[str, int] = field(default_factory=dict)


# ============================================================
# Feedback Simulation Result
# ============================================================

@dataclass
class FBSimulationResult:
    """Complete output of a feedback-enabled simulation."""
    params: SimulationParams
    feedback_params: FeedbackParams
    stimulus: Stimulus
    baseline: CascadeResult
    timeline: List[FBMonthlySnapshot]

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

    # Feedback-specific
    final_proficiency: float = 0.0
    final_trust: float = 0.0
    final_readiness: float = 0.0
    avg_adoption_dampening: float = 0.0    # how much feedback slowed adoption overall

    # Traceability (populated when trace=True)
    trace: Optional[SimulationTrace] = None


# ============================================================
# The Feedback Simulator
# ============================================================

def simulate_with_feedback(
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
    fb_params: FeedbackParams = None,
    initial_hs: HumanSystemState = None,
    trace: bool = False,
) -> FBSimulationResult:
    """
    Run time-stepped simulation WITH feedback loops.
    Human system is updated every month based on outcomes.

    Args:
        trace: When True, captures detailed per-month computation decomposition
               in result.trace (SimulationTrace). Zero overhead when False.
    """
    if fb_params is None:
        fb_params = FeedbackParams()

    # Run Stage 1 cascade for ceiling values
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

    # Extract ceilings
    ceiling_gross_freed = baseline.step3_capacity.total_gross_freed_hours
    ceiling_sunrise_skills = len(baseline.step4_skills.sunrise_skills)
    original_hc = baseline.step5_workforce.total_current_hc

    role_ceiling_gross = {}
    role_ceiling_freed_pct = {}
    for rc in baseline.step3_capacity.role_capacities:
        role_ceiling_gross[rc.role_id] = rc.gross_freed_hours_pp * rc.headcount
        role_ceiling_freed_pct[rc.role_id] = rc.freed_pct

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

    # Initialize human system from org data or parameter override
    if initial_hs:
        hs = HumanSystemState(
            proficiency=initial_hs.proficiency,
            readiness=initial_hs.readiness,
            trust=initial_hs.trust,
            political_capital=initial_hs.political_capital,
            transformation_fatigue=initial_hs.transformation_fatigue,
        )
    else:
        # Average across affected functions
        avg_prof = avg_read = avg_trust = 0
        count = 0
        for fn in stimulus.target_functions:
            org_hs = org.human_system.get(fn)
            if org_hs:
                avg_prof += org_hs.ai_proficiency
                avg_read += org_hs.change_readiness
                avg_trust += org_hs.trust_level
                count += 1
        if count > 0:
            hs = HumanSystemState(
                proficiency=avg_prof / count,
                readiness=avg_read / count,
                trust=avg_trust / count,
                political_capital=60.0,
            )
        else:
            hs = HumanSystemState()

    # T1-#6: Compute per-function learning velocity factor
    # Baseline = 6 months. Function with learning_velocity_months=3 learns 2x faster.
    LEARNING_VELOCITY_BASELINE = 6.0
    avg_learning_velocity = LEARNING_VELOCITY_BASELINE
    lv_count = 0
    for fn in stimulus.target_functions:
        org_hs = org.human_system.get(fn)
        if org_hs and org_hs.learning_velocity_months > 0:
            avg_learning_velocity += org_hs.learning_velocity_months
            lv_count += 1
    if lv_count > 0:
        avg_learning_velocity = avg_learning_velocity / (lv_count + 1)
    learning_velocity_factor = LEARNING_VELOCITY_BASELINE / max(1.0, avg_learning_velocity)

    cumulative_hc_reduced = 0
    cumulative_investment = 0.0
    cumulative_savings = 0.0
    cumulative_net_freed = 0.0
    skill_gap_opened = 0
    skill_gap_closed = 0
    prev_effective_adoption = 0.0

    # T3-#7: Track capability upgrade ceiling boost accumulation
    capability_ceiling_boost = 0.0

    # T3-#8: Shadow AI parallel adoption (runs ahead of official)
    shadow_adoption = 0.0

    # T2-#10: Capacity realization delay pipeline
    # Freed capacity enters a pipeline and releases after CAPACITY_REALIZATION_DELAY months
    capacity_pipeline = deque([0.0] * CAPACITY_REALIZATION_DELAY)

    # ── Initialize trace ──
    sim_trace = None
    if trace:
        sim_trace = SimulationTrace(
            scenario_id=params.scenario_id,
            scenario_name=params.scenario_name,
            stimulus_name=stimulus.name,
            policy=params.policy,
            time_horizon=params.time_horizon_months,
            initial_conditions={
                "proficiency": hs.proficiency,
                "readiness": hs.readiness,
                "trust": hs.trust,
                "political_capital": hs.political_capital,
                "fatigue": hs.transformation_fatigue,
                "learning_velocity_factor": learning_velocity_factor,
                "ceiling_freed": ceiling_gross_freed,
                "original_hc": original_hc,
                "capacity_delay": CAPACITY_REALIZATION_DELAY,
                "shadow_work_tax": 10,
                # T3 parameters
                "t3_fast_start_months": fb_params.genai_fast_start_months,
                "t3_fast_start_boost": fb_params.genai_fast_start_multiplier,
                "t3_workflow_disruption_coeff": fb_params.workflow_disruption_coefficient,
                "t3_trust_thresholds": list(fb_params.trust_evidence_thresholds),
                "t3_hc_decision_delay": fb_params.hc_decision_delay_months,
                "t3_hallucination_rate": fb_params.hallucination_base_rate,
                "t3_capability_upgrade_months": list(fb_params.capability_upgrade_months),
                "t3_shadow_ai_multiplier": fb_params.shadow_ai_speed_multiplier,
            },
        )

    timeline = []

    # ── Main time loop ──
    for month in range(0, params.time_horizon_months + 1):

        # 1. Raw S-curve adoption (same as Stage 2)
        raw_adopt = params.adoption.at(month) if params.adoption else 0.0
        raw_expand = params.expansion.at(month) if params.expansion else 0.0
        raw_extend = params.extension.at(month) if params.extension else 0.0
        raw_combined = min(1.0, raw_adopt + raw_expand + raw_extend)

        # T3-#7: Apply capability upgrade ceiling boosts
        # Each upgrade raises the effective ceiling of what can be automated
        if month in fb_params.capability_upgrade_months:
            capability_ceiling_boost += fb_params.capability_upgrade_ceiling_boost
            # Skill disruption: new capabilities require new skills
            hs.proficiency = max(0, hs.proficiency - fb_params.capability_upgrade_skill_disruption)
            # Trust disruption: regression risk from model changes
            hs.trust = max(0, hs.trust - fb_params.capability_upgrade_trust_disruption)
            hs.clamp()

        # Apply accumulated capability boost to raw adoption ceiling
        raw_combined = min(1.0, raw_combined + capability_ceiling_boost)

        # T3-#8: Shadow AI parallel adoption
        # Shadow adoption runs ahead of official but doesn't directly affect the cascade
        if month > 0:
            shadow_raw = min(1.0, raw_combined * fb_params.shadow_ai_speed_multiplier)
            shadow_adoption = max(shadow_adoption, shadow_raw * hs.effective_multiplier)
            # Shadow conversion: some shadow users become official adopters (boosts proficiency)
            shadow_conversion = shadow_adoption * fb_params.shadow_ai_conversion_rate
            # Shadow conversion accelerates proficiency (people are learning informally)
            hs.proficiency = min(100, hs.proficiency + shadow_conversion * 0.5)
            hs.clamp()

        # 2. FEEDBACK: Compute effective adoption (the key difference)
        skill_gap_pct = (max(0, skill_gap_opened - skill_gap_closed) /
                         max(1, ceiling_sunrise_skills) * 100)
        total_current_hc = sum(current_hc.values())

        effective_combined = compute_effective_adoption(
            raw_adoption=raw_combined,
            hs=hs,
            skill_gap_pct=skill_gap_pct,
            original_hc=original_hc,
            current_hc=total_current_hc,
            params=fb_params,
        )

        dampening = effective_combined / raw_combined if raw_combined > 0 else 1.0

        # Incremental effective adoption
        delta_adoption = max(0, effective_combined - prev_effective_adoption)
        adoption_velocity = delta_adoption  # T1-#2: track for fatigue
        prev_effective_adoption = effective_combined

        # 3. Scale freed hours to effective (not raw) adoption
        gross_freed_this_month = ceiling_gross_freed * delta_adoption
        gross_before_bonus = gross_freed_this_month  # save for trace

        # T1-#4: Apply workflow_automation_bonus when extension phase is active
        if params.enable_workflow_automation and raw_extend > 0:
            gross_freed_this_month *= params.workflow_automation_bonus

        # T2-#10: Push into capacity pipeline (delayed realization)
        capacity_pipeline.append(gross_freed_this_month)
        realized_freed = capacity_pipeline.popleft()  # freed from N months ago

        # T1-#4: Apply workflow_automation_bonus when extension phase is active
        if params.enable_workflow_automation and raw_extend > 0:
            gross_freed_this_month *= params.workflow_automation_bonus

        # T2-#10: Push into capacity pipeline (delayed realization)
        capacity_pipeline.append(gross_freed_this_month)
        realized_freed = capacity_pipeline.popleft()  # freed from N months ago

        # 4. FEEDBACK B1: Dynamic absorption rate
        dynamic_absorption = compute_dynamic_absorption(
            params.absorption_factor, total_current_hc, original_hc, fb_params,
        )
        redistributed = realized_freed * dynamic_absorption
        net_freed = realized_freed - redistributed
        cumulative_net_freed += net_freed

        # 5. Skill gap dynamics
        new_sunrise = int(ceiling_sunrise_skills * delta_adoption)
        skill_gap_opened += new_sunrise
        if month >= params.reskilling_delay_months and skill_gap_opened > 0:
            closeable = int(skill_gap_opened * params.reskilling_rate)
            closeable = min(closeable, skill_gap_opened - skill_gap_closed)
            skill_gap_closed += max(0, closeable)
        current_gap = max(0, skill_gap_opened - skill_gap_closed)
        gap_pct = current_gap / max(1, ceiling_sunrise_skills) * 100

        # 6. HC decisions (periodic, with capital check)
        hc_reduced_this_month = 0
        hc_trace_roles = []  # trace: per-role HC decision data
        pre_hc_total = total_current_hc  # save for trace (pre-HC total)
        # T1-#3: rapid_redeployment uses monthly HC reviews
        hc_freq = 1 if params.policy == "rapid_redeployment" else params.hc_review_frequency
        # T3-#4: HC decision latency — no reductions before delay period
        hc_decision_delay = fb_params.hc_decision_delay_months
        if params.policy == "rapid_redeployment":
            hc_decision_delay = max(1, hc_decision_delay // 3)  # rapid = shorter delay
        elif params.policy == "active_reduction":
            hc_decision_delay = max(3, hc_decision_delay // 2)  # active = moderate delay
        if month > hc_decision_delay and month % hc_freq == 0:
            # R4: Political capital gates HC decisions
            if hs.political_capital >= fb_params.capital_threshold or params.policy == "no_layoffs":
                for rid in list(current_hc.keys()):
                    role = org.roles[rid]
                    ceil = role_ceiling_gross.get(rid, 0)
                    role_freed = ceil * effective_combined * (1 - dynamic_absorption)
                    # T2-#8: Use productive hours per management level
                    role_hours = productive_hours_month(role.management_level)
                    fte_freed = role_freed / role_hours
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
                            # T1-#3: Faster reallocation — round up where viable
                            reducible = math.ceil(net_new) if net_new >= 0.5 else 0
                        else:
                            reducible = math.floor(net_new)

                        # T2-#9: Min staffing floor — 20% of original role headcount
                        min_staffing = max(1, math.ceil(role.headcount * 0.20))
                        max_reducible = max(0, current_hc[rid] - min_staffing)
                        pre_floor = reducible  # save for trace
                        reducible = min(reducible, max_reducible)

                        # Trace: capture per-role HC reasoning
                        if trace and pre_floor > 0:
                            hc_trace_roles.append({
                                "role_id": rid,
                                "role_name": role.role_name,
                                "fte_freed": round(fte_freed, 2),
                                "net_new": round(net_new, 2),
                                "policy_reducible": pre_floor,
                                "min_staffing": min_staffing,
                                "floor_hit": pre_floor > max_reducible,
                                "reduced": reducible,
                                "hc_before": current_hc[rid],
                                "hc_after": current_hc[rid] - reducible,
                            })

                        if reducible > 0:
                            current_hc[rid] -= reducible
                            hc_reduced_this_month += reducible

        cumulative_hc_reduced += hc_reduced_this_month
        total_current_hc = sum(current_hc.values())

        # 7. Financial
        monthly_investment = 0.0
        if month >= 1:
            # T1-#5: Scale license cost by adoption level (phased deployment)
            monthly_investment += monthly_license * max(0.1, effective_combined)
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

        # R3: Savings reinvestment — accumulated savings boost adoption
        # (more budget → more training → faster rollout)
        effective_pre_r3 = effective_combined  # save for trace
        r3_boost_val = 0.0
        if cumulative_savings > 0:
            r3_boost_val = r3_savings_reinvestment(cumulative_savings, fb_params)
            effective_combined = min(raw_combined, effective_combined + r3_boost_val)

        # 8. T1-#1: Productivity with DELAYED automation lift
        # Benefits lag adoption by CAPACITY_REALIZATION_DELAY months (drag hits immediately).
        # This creates the "Valley of Despair" observed in real transformations.
        b2_drag = b2_skill_valley(gap_pct, fb_params.skill_gap_drag_coefficient)
        delayed_month = max(0, month - CAPACITY_REALIZATION_DELAY)
        if delayed_month > 0 and len(timeline) > delayed_month:
            delayed_adoption = timeline[delayed_month].effective_adoption_pct
        else:
            delayed_adoption = 0.0
        automation_lift = delayed_adoption * 15.0                   # delayed: benefits come later
        skill_drag = (1 - b2_drag) * 20.0                          # immediate: skill gap hits now
        fatigue_drag = hs.transformation_fatigue * 0.15             # T1-#2: was 0.05, now meaningful

        # T3-#2: Workflow disruption drag — introducing AI disrupts existing workflows
        # Disruption intensity peaks during rapid adoption ramp, decays over first year
        disruption_decay = max(0, 1.0 - month / fb_params.workflow_disruption_decay_months)
        workflow_disruption_drag = (
            adoption_velocity * fb_params.workflow_disruption_coefficient * disruption_decay
        )

        productivity = 100.0 + automation_lift - skill_drag - fatigue_drag - workflow_disruption_drag

        # 9. FEEDBACK: Update human system for NEXT month
        disruption = hc_reduced_this_month / max(1, total_current_hc) * 10  # 0-10 scale
        ai_error = (fb_params.ai_error_month is not None and month == fb_params.ai_error_month)

        # T3-#6: Hallucination-driven trust damage (continuous background process)
        # Probability of a trust-damaging incident scales with adoption level
        hallucination_trust_hit = 0.0
        if effective_combined > 0.01 and month > 0:
            # Deterministic approximation: expected trust damage per month
            incident_probability = fb_params.hallucination_base_rate * effective_combined
            hallucination_trust_hit = incident_probability * fb_params.hallucination_trust_damage

        # T3-#3b: Periodic trust shocks (deterministic, reproducible)
        trust_shock_hit = 0.0
        if (month >= fb_params.trust_shock_start_month and
                month > 0 and
                (month - fb_params.trust_shock_start_month) % fb_params.trust_shock_interval == 0):
            trust_shock_hit = fb_params.trust_shock_magnitude

        # Compute HC reduction percentage for T3-#5 fatigue
        hc_reduced_pct = hc_reduced_this_month / max(1, pre_hc_total)
        is_stable_month = (hc_reduced_this_month == 0)

        hs_before = hs  # save pre-update state for trace decomposition
        hs = update_human_system(
            hs=hs,
            adoption_level=effective_combined,
            disruption_level=disruption,
            skill_gap_pct=gap_pct,
            cumulative_savings=cumulative_savings,
            original_hc=original_hc,
            current_hc=total_current_hc,
            params=fb_params,
            ai_error_this_month=ai_error,
            adoption_velocity=adoption_velocity,
            learning_velocity_factor=learning_velocity_factor,
            month=month,
            hc_reduced_pct=hc_reduced_pct,
            is_stable_month=is_stable_month,
        )

        # Apply T3-#6 hallucination and T3-#3b shock trust damage AFTER the standard update
        if hallucination_trust_hit > 0 or trust_shock_hit > 0:
            hs.trust = max(0, hs.trust - hallucination_trust_hit - trust_shock_hit)
            hs.clamp()

        # ── TRACE CAPTURE ──
        if trace:
            mt = MonthTrace(month=month)

            # S-CURVE
            mt.s_curve = {
                "adopt": raw_adopt, "expand": raw_expand,
                "extend": raw_extend, "combined": raw_combined,
            }

            # MULTIPLIERS (using pre-update human state)
            t_human = hs_before.effective_multiplier
            t_trust = hs_before.trust_multiplier
            t_skill = b2_skill_valley(skill_gap_pct, fb_params.skill_gap_drag_coefficient)
            t_seniority = b4_seniority_offset(
                original_hc, pre_hc_total, fb_params.seniority_penalty,
            )
            t_capital = hs_before.capital_multiplier

            # Multiplier detail decomposition
            veto = hs_before.trust < 10.0 or hs_before.readiness < 10.0
            if veto:
                human_detail = (
                    f"VETO [T2-#7]: trust={hs_before.trust:.1f} or "
                    f"ready={hs_before.readiness:.1f} < 10 -> 0.05"
                )
            else:
                raw_hm = (
                    0.35 * hs_before.proficiency
                    + 0.45 * hs_before.readiness
                    + 0.20 * hs_before.trust
                ) / 100.0
                human_detail = (
                    f"0.35x{hs_before.proficiency:.1f} + 0.45x{hs_before.readiness:.1f} + "
                    f"0.20x{hs_before.trust:.1f} = {raw_hm:.3f}"
                    f"{' (floor->0.15)' if raw_hm < 0.15 else ''}"
                )

            drag_val = skill_gap_pct / 100.0 * fb_params.skill_gap_drag_coefficient
            red_pct = ((original_hc - pre_hc_total) / original_hc) if original_hc > 0 else 0

            mt.multipliers = {
                "human_system": {"value": t_human, "detail": human_detail, "veto": veto},
                "trust_gate": {
                    "value": t_trust,
                    "detail": f"trust={hs_before.trust:.1f} {trust_band(hs_before.trust)}",
                },
                "skill_valley": {
                    "value": t_skill,
                    "detail": (
                        f"gap={skill_gap_pct:.1f}% x coeff="
                        f"{fb_params.skill_gap_drag_coefficient} -> drag={drag_val:.3f}"
                    ),
                },
                "seniority": {
                    "value": t_seniority,
                    "detail": (
                        f"reduced={red_pct:.1%} x penalty={fb_params.seniority_penalty}"
                    ),
                },
                "capital": {
                    "value": t_capital,
                    "detail": (
                        f"capital={hs_before.political_capital:.1f} "
                        f"{capital_band(hs_before.political_capital)}"
                    ),
                },
            }

            # ADOPTION
            mt.adoption = {
                "raw": raw_combined,
                "effective": effective_pre_r3,
                "effective_post_r3": effective_combined,
                "r3_boost": r3_boost_val,
                "formula": (
                    f"{raw_combined:.4f} x {t_human:.4f} x {t_trust:.4f} x "
                    f"{t_skill:.4f} x {t_seniority:.4f} x {t_capital:.4f} "
                    f"= {effective_pre_r3:.4f}"
                ),
                "dampening_pct": dampening * 100,
                "delta": delta_adoption,
                "velocity": adoption_velocity,
            }

            # CAPACITY PIPELINE
            wf_active = params.enable_workflow_automation and raw_extend > 0
            mt.capacity = {
                "gross_delta": gross_before_bonus,
                "workflow_bonus_active": wf_active,
                "workflow_bonus_value": params.workflow_automation_bonus if wf_active else 1.0,
                "pipeline_in": gross_freed_this_month,
                "pipeline_out": realized_freed,
                "delay": CAPACITY_REALIZATION_DELAY,
                "absorption_rate": dynamic_absorption,
                "redistributed": redistributed,
                "net_freed": net_freed,
            }

            # FEEDBACK LOOP DELTAS (decompose what update_human_system computed)
            # R1: Trust
            if ai_error:
                dt_trust = -hs_before.trust * fb_params.trust_destruction_factor
                trust_detail = (
                    f"ERROR: -{hs_before.trust:.1f} x "
                    f"{fb_params.trust_destruction_factor} = {dt_trust:.3f}"
                )
            else:
                _build = (
                    fb_params.trust_build_rate * effective_combined
                    * fb_params.success_probability
                )
                _ceil = max(0.1, 1.0 - hs_before.trust / 100.0)
                dt_trust = _build * _ceil
                # T3-#3: Apply evidence threshold gating in trace too
                _at_thresh = False
                for _thr in fb_params.trust_evidence_thresholds:
                    if abs(effective_combined - _thr) < 0.02:
                        _at_thresh = True
                        break
                if not _at_thresh:
                    dt_trust *= fb_params.trust_between_threshold_rate
                _thresh_tag = " AT-THRESHOLD" if _at_thresh else f" x{fb_params.trust_between_threshold_rate:.2f}[T3-#3]"
                trust_detail = (
                    f"build: {fb_params.trust_build_rate}x{effective_combined:.3f}"
                    f"x{fb_params.success_probability}xceil({_ceil:.2f}){_thresh_tag} = {dt_trust:.3f}"
                )

            # R2: Proficiency (T3-#1: fast-start)
            _practice = effective_combined
            _prof_ceil = max(
                0.05, 1.0 - hs_before.proficiency / fb_params.learning_saturation,
            )
            _eff_lr = fb_params.learning_rate
            if month < fb_params.genai_fast_start_months:
                _eff_lr *= fb_params.genai_fast_start_multiplier
            dt_prof = (
                _eff_lr * _practice * _prof_ceil * learning_velocity_factor
            )
            _fast_tag = " [T3-#1 FAST-START]" if month < fb_params.genai_fast_start_months else ""
            prof_detail = (
                f"learn: {_eff_lr:.1f}x{_practice:.3f}"
                f"xceil({_prof_ceil:.2f})xvel({learning_velocity_factor:.2f}) "
                f"= {dt_prof:.3f}{_fast_tag}"
            )

            # B3: Readiness + Fatigue (T3-#5: restructured fatigue)
            _trust_damp = max(0.3, hs_before.trust / 100.0)
            _resistance = disruption * fb_params.resistance_sensitivity / _trust_damp
            # T3-#5: New fatigue decomposition
            _ai_work_fatigue = fb_params.fatigue_ai_work_burden * effective_combined
            _hc_anxiety = fb_params.fatigue_hc_anxiety_factor * hc_reduced_pct
            _ai_anxiety = fb_params.fatigue_ai_anxiety_baseline if effective_combined > 0.01 else 0.0
            _pace_fatigue = adoption_velocity * fb_params.fatigue_build_rate * 10.0
            _disr_fatigue = disruption * fb_params.fatigue_build_rate
            _base_decay = fb_params.fatigue_decay_rate * (1.0 - effective_combined)
            _stab_bonus = fb_params.fatigue_recovery_stability_bonus if is_stable_month else 0.0
            _fat_recovery = _base_decay + _stab_bonus * fb_params.fatigue_decay_rate
            dt_fatigue = (
                _ai_work_fatigue + _hc_anxiety + _ai_anxiety +
                _pace_fatigue + _disr_fatigue - _fat_recovery
            )

            _recovery = fb_params.resistance_decay_rate * (
                1 - hs_before.transformation_fatigue / 100
            )
            _ready_ceil = max(0.1, 1.0 - hs_before.readiness / 100.0)
            _adopt_boost = (
                fb_params.readiness_boost_rate * effective_combined * _ready_ceil
            )
            dt_readiness = -_resistance + _recovery + _adopt_boost

            # R4: Capital
            _cap_build = (
                fb_params.capital_build_rate * effective_combined
                * fb_params.success_probability
            )
            _cap_spend = fb_params.capital_spend_rate * disruption
            dt_capital = _cap_build - _cap_spend

            mt.loop_deltas = {
                "R1_trust": {
                    "value": dt_trust,
                    "detail": trust_detail,
                    "hallucination_hit": hallucination_trust_hit,
                    "trust_shock_hit": trust_shock_hit,
                },
                "R2_proficiency": {"value": dt_prof, "detail": prof_detail},
                "B3_readiness": {
                    "value": dt_readiness,
                    "detail": (
                        f"resist={-_resistance:.3f} + recov={_recovery:.3f} "
                        f"+ boost={_adopt_boost:.3f}"
                    ),
                },
                "B3_fatigue": {
                    "value": dt_fatigue,
                    "detail": (
                        f"ai_work={_ai_work_fatigue:.3f} + hc_anx={_hc_anxiety:.3f} "
                        f"+ ai_anx={_ai_anxiety:.3f} + pace={_pace_fatigue:.3f} "
                        f"+ disrupt={_disr_fatigue:.3f} - recovery={_fat_recovery:.3f} "
                        f"[T3-#5]"
                    ),
                },
                "R4_capital": {
                    "value": dt_capital,
                    "detail": f"build={_cap_build:.3f} - spend={_cap_spend:.3f}",
                },
            }

            # HC DECISION
            is_review = month > hc_decision_delay and month % hc_freq == 0
            cap_ok = (
                hs_before.political_capital >= fb_params.capital_threshold
                or params.policy == "no_layoffs"
            )
            mt.hc_decision = {
                "review_month": is_review,
                "freq": hc_freq,
                "policy": params.policy,
                "capital_value": hs_before.political_capital,
                "capital_threshold": fb_params.capital_threshold,
                "capital_check": cap_ok if is_review else None,
                "roles": hc_trace_roles,
                "total_reduced": hc_reduced_this_month,
                "reason": (
                    "month 0" if month == 0 else
                    f"HC decision delay [T3-#4]: month {month} <= {hc_decision_delay}" if month <= hc_decision_delay else
                    "not review month" if not is_review else
                    "capital below threshold" if is_review and not cap_ok else
                    f"review executed, {hc_reduced_this_month} reduced"
                ),
            }

            # PRODUCTIVITY (T3-#2: workflow disruption added)
            mt.productivity = {
                "automation_lift": automation_lift,
                "skill_drag": skill_drag,
                "fatigue_drag": fatigue_drag,
                "workflow_disruption_drag": workflow_disruption_drag,
                "index": productivity,
                "delayed_month": delayed_month,
                "delayed_adoption": delayed_adoption,
                "b2_drag_mult": b2_drag,
                "formula": (
                    f"100.0 + {automation_lift:.1f}(auto, M{delayed_month}) "
                    f"- {skill_drag:.1f}(skill) "
                    f"- {fatigue_drag:.1f}(fatigue) "
                    f"- {workflow_disruption_drag:.1f}(disruption[T3-#2]) "
                    f"= {productivity:.1f}"
                ),
            }

            # FINANCIAL
            license_this = (
                monthly_license * max(0.1, effective_combined) if month >= 1 else 0
            )
            train_this = training_per_month_phase1 if 1 <= month <= 6 else 0
            cm_this = change_mgmt_per_month if 1 <= month <= 6 else 0
            mt.financial = {
                "monthly_investment": monthly_investment,
                "investment_detail": (
                    f"license=${license_this:,.0f}"
                    f"[T1-#5 x{max(0.1, effective_combined):.3f}]"
                    f" + train=${train_this:,.0f} + cm=${cm_this:,.0f}"
                ),
                "license_scale_factor": (
                    max(0.1, effective_combined) if month >= 1 else 0
                ),
                "monthly_savings": monthly_salary_savings,
                "cumulative_net": net_position,
            }

            # IMPROVEMENTS ACTIVE THIS MONTH
            imps = []
            imps.append(
                f"T1-#1: Productivity valley — delayed lift "
                f"{CAPACITY_REALIZATION_DELAY}mo, "
                f"delayed_adoption={delayed_adoption:.4f}"
            )
            if _pace_fatigue > 0.001:
                imps.append(
                    f"T1-#2: Fatigue from pace — "
                    f"velocity={adoption_velocity:.4f}, "
                    f"pace_fatigue={_pace_fatigue:.4f}"
                )
            if params.policy == "rapid_redeployment":
                imps.append("T1-#3: Rapid redeployment — monthly HC reviews")
            if wf_active:
                imps.append(
                    f"T1-#4: Workflow bonus "
                    f"x{params.workflow_automation_bonus:.1f} applied"
                )
            if month >= 1:
                imps.append(
                    f"T1-#5: License scaled "
                    f"x{max(0.1, effective_combined):.3f}"
                )
            if abs(learning_velocity_factor - 1.0) > 0.01:
                imps.append(
                    f"T1-#6: Learning velocity x{learning_velocity_factor:.2f}"
                )
            if veto:
                imps.append("T2-#7: Trust VETO active")
            imps.append("T2-#8: Productive hours by level")
            floor_hits = sum(
                1 for r in hc_trace_roles if r.get("floor_hit")
            )
            if floor_hits > 0:
                imps.append(
                    f"T2-#9: Min staffing floor hit for {floor_hits} roles"
                )
            imps.append(
                f"T2-#10: Capacity pipeline delay "
                f"{CAPACITY_REALIZATION_DELAY}mo, "
                f"releasing={realized_freed:.1f}h"
            )
            imps.append("T2-#11: Shadow work tax 10%")
            # T3 improvements
            if month < fb_params.genai_fast_start_months:
                imps.append(
                    f"T3-#1: GenAI fast-start x{fb_params.genai_fast_start_multiplier:.1f} "
                    f"(month {month}/{fb_params.genai_fast_start_months})"
                )
            if workflow_disruption_drag > 0.01:
                imps.append(
                    f"T3-#2: Workflow disruption drag={workflow_disruption_drag:.2f}"
                )
            if not _at_thresh:
                imps.append(
                    f"T3-#3: Trust between thresholds — rate x{fb_params.trust_between_threshold_rate:.2f}"
                )
            if trust_shock_hit > 0:
                imps.append(
                    f"T3-#3b: Trust shock -{trust_shock_hit:.1f}pts"
                )
            if month <= hc_decision_delay and month > 0:
                imps.append(
                    f"T3-#4: HC decision delay — no reductions until M{hc_decision_delay}"
                )
            if _ai_work_fatigue > 0.01 or _hc_anxiety > 0.01 or _ai_anxiety > 0.01:
                imps.append(
                    f"T3-#5: Fatigue restructured — "
                    f"ai_work={_ai_work_fatigue:.2f} hc_anx={_hc_anxiety:.2f} "
                    f"ai_anx={_ai_anxiety:.2f}"
                )
            if hallucination_trust_hit > 0.001:
                imps.append(
                    f"T3-#6: Hallucination trust damage={hallucination_trust_hit:.3f}/mo"
                )
            if month in fb_params.capability_upgrade_months:
                imps.append(
                    f"T3-#7: Capability upgrade — ceiling +{fb_params.capability_upgrade_ceiling_boost:.0%}, "
                    f"prof -{fb_params.capability_upgrade_skill_disruption:.0f}, "
                    f"trust -{fb_params.capability_upgrade_trust_disruption:.0f}"
                )
            if shadow_adoption > 0.01:
                imps.append(
                    f"T3-#8: Shadow AI adoption={shadow_adoption:.1%} "
                    f"(official={effective_combined:.1%})"
                )
            mt.improvements = imps

            mt.dominant_loop = determine_dominant_loop(mt)
            sim_trace.months.append(mt)

        # 10. Record snapshot
        b4_mult = b4_seniority_offset(original_hc, total_current_hc, fb_params.seniority_penalty)

        snapshot = FBMonthlySnapshot(
            month=month,
            raw_adoption_pct=raw_combined,
            effective_adoption_pct=effective_combined,
            adoption_dampening=dampening,
            gross_freed_hours=realized_freed,
            redistributed_hours=redistributed,
            net_freed_hours=net_freed,
            cumulative_net_freed=cumulative_net_freed,
            dynamic_absorption_rate=dynamic_absorption,
            headcount=total_current_hc,
            hc_reduced_this_month=hc_reduced_this_month,
            cumulative_hc_reduced=cumulative_hc_reduced,
            hc_pct_of_original=(total_current_hc / original_hc * 100) if original_hc > 0 else 100,
            skill_gap_opened=skill_gap_opened,
            skill_gap_closed=skill_gap_closed,
            current_skill_gap=current_gap,
            skill_gap_pct=gap_pct,
            cumulative_investment=cumulative_investment,
            cumulative_savings=cumulative_savings,
            net_position=net_position,
            monthly_savings_rate=monthly_salary_savings,
            productivity_index=productivity,
            proficiency=hs.proficiency,
            readiness=hs.readiness,
            trust=hs.trust,
            political_capital=hs.political_capital,
            transformation_fatigue=hs.transformation_fatigue,
            human_multiplier=hs.effective_multiplier,
            trust_multiplier=hs.trust_multiplier,
            capital_multiplier=hs.capital_multiplier,
            b2_skill_drag=b2_drag,
            b4_seniority_mult=b4_mult,
            ai_error_occurred=ai_error,
            role_headcounts=dict(current_hc),
        )
        timeline.append(snapshot)

    # ── Summary metrics ──
    payback_month = 0
    for snap in timeline:
        if snap.net_position > 0 and payback_month == 0 and snap.month > 0:
            payback_month = snap.month
            break

    peak_gap_snap = max(timeline, key=lambda s: s.current_skill_gap)
    valley_snap = min(timeline, key=lambda s: s.productivity_index)
    avg_dampening = (sum(s.adoption_dampening for s in timeline[1:]) /
                     max(1, len(timeline) - 1))

    # ── Compute trace summaries ──
    if trace and sim_trace:
        sim_trace.phase_summary = compute_phase_summary(sim_trace)
        sim_trace.improvement_summary = compute_improvement_summary(sim_trace)

    return FBSimulationResult(
        params=params,
        feedback_params=fb_params,
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
        peak_skill_gap_month=peak_gap_snap.month,
        peak_skill_gap_value=peak_gap_snap.current_skill_gap,
        productivity_valley_month=valley_snap.month,
        productivity_valley_value=valley_snap.productivity_index,
        final_proficiency=timeline[-1].proficiency,
        final_trust=timeline[-1].trust,
        final_readiness=timeline[-1].readiness,
        avg_adoption_dampening=avg_dampening,
        trace=sim_trace,
    )
