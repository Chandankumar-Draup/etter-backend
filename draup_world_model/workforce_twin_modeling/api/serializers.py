"""
Serializers: Engine Dataclass → JSON-safe Dict
================================================
Each engine dataclass gets an explicit serializer. We do NOT use generic
dataclasses.asdict() because:
  1. Nested dataclass lists need controlled recursion
  2. Some fields need formatting (floats rounded, etc.)
  3. We control exactly what reaches the frontend
"""
import math
from dataclasses import asdict
from typing import Any, Dict, List

from workforce_twin_modeling.engine.cascade import (
    CascadeResult, Stimulus, Step1_ScopeResult, Step2_ReclassificationResult,
    TaskReclassification, Step3_CapacityResult, RoleCapacity,
    Step4_SkillResult, SkillImpact, Step5_WorkforceResult, RoleWorkforceImpact,
    Step6_FinancialResult, Step7_StructuralResult, Step8_HumanSystemResult,
    Step9_RiskResult, RiskItem,
)
from workforce_twin_modeling.engine.feedback import HumanSystemState, FeedbackParams
from workforce_twin_modeling.engine.gap_engine import (
    OrgGapResult, FunctionGapResult, RoleGapResult,
    WorkloadGapResult, TaskGapResult,
)
from workforce_twin_modeling.engine.loader import OrganizationData
from workforce_twin_modeling.engine.rates import SimulationParams, RateParams
from workforce_twin_modeling.engine.simulator import SimulationResult, MonthlySnapshot
from workforce_twin_modeling.engine.simulator_fb import FBSimulationResult, FBMonthlySnapshot
from workforce_twin_modeling.engine.trace import SimulationTrace
from workforce_twin_modeling.models.organization import (
    Task, Role, Workload, Skill, Tool, HumanSystem, OrgNode,
)


def _r(v: float, decimals: int = 2) -> float:
    """Round a float for clean JSON output. Sanitizes inf/nan to 0."""
    if v is None:
        return 0.0
    f = float(v)
    if math.isinf(f) or math.isnan(f):
        return 0.0
    return round(f, decimals)


# ────────────────────────────────────────────
# Organization Data Serializers
# ────────────────────────────────────────────

def serialize_role(role: Role) -> dict:
    return {
        "role_id": role.role_id,
        "role_name": role.role_name,
        "function": role.function,
        "sub_function": role.sub_function,
        "jfg": role.jfg,
        "job_family": role.job_family,
        "management_level": role.management_level,
        "headcount": role.headcount,
        "avg_salary": _r(role.avg_salary, 0),
        "annual_cost": _r(role.annual_cost, 0),
        "automation_score": _r(role.automation_score, 1),
        "augmentation_score": _r(role.augmentation_score, 1),
        "quantification_score": _r(role.quantification_score, 1),
    }


def serialize_workload(wl: Workload) -> dict:
    return {
        "workload_id": wl.workload_id,
        "role_id": wl.role_id,
        "workload_name": wl.workload_name,
        "time_pct": _r(wl.time_pct, 1),
        "directive_pct": _r(wl.directive_pct, 1),
        "feedback_loop_pct": _r(wl.feedback_loop_pct, 1),
        "task_iteration_pct": _r(wl.task_iteration_pct, 1),
        "learning_pct": _r(wl.learning_pct, 1),
        "validation_pct": _r(wl.validation_pct, 1),
        "negligibility_pct": _r(wl.negligibility_pct, 1),
        "ai_automatable_pct": _r(wl.ai_automatable_pct, 1),
        "augmentable_pct": _r(wl.augmentable_pct, 1),
        "human_only_pct": _r(wl.human_only_pct, 1),
    }


def serialize_task(task: Task) -> dict:
    return {
        "task_id": task.task_id,
        "workload_id": task.workload_id,
        "task_name": task.task_name,
        "category": task.category,
        "effort_hours_month": _r(task.effort_hours_month, 1),
        "automatable_by_tool": task.automatable_by_tool,
        "compliance_mandated_human": task.compliance_mandated_human,
        "l1_etter_potential": _r(task.l1_etter_potential, 1),
        "l2_achievable": _r(task.l2_achievable, 1),
        "l3_realized": _r(task.l3_realized, 1),
        "adoption_gap": _r(task.adoption_gap, 1),
        "capability_gap": _r(task.capability_gap, 1),
        "total_gap": _r(task.total_gap, 1),
    }


def serialize_skill(skill: Skill) -> dict:
    return {
        "skill_id": skill.skill_id,
        "workload_id": skill.workload_id,
        "skill_name": skill.skill_name,
        "skill_type": skill.skill_type,
        "proficiency_required": skill.proficiency_required,
        "is_sunrise": skill.is_sunrise,
        "is_sunset": skill.is_sunset,
    }


def serialize_tool(tool: Tool) -> dict:
    return {
        "tool_id": tool.tool_id,
        "tool_name": tool.tool_name,
        "deployed_to_functions": tool.deployed_to_functions,
        "task_categories_addressed": tool.task_categories_addressed,
        "license_cost_per_user_month": _r(tool.license_cost_per_user_month, 2),
        "current_adoption_pct": _r(tool.current_adoption_pct, 1),
    }


def serialize_human_system(hs: HumanSystem) -> dict:
    return {
        "function": hs.function,
        "ai_proficiency": _r(hs.ai_proficiency, 1),
        "change_readiness": _r(hs.change_readiness, 1),
        "trust_level": _r(hs.trust_level, 1),
        "political_capital": _r(hs.political_capital, 1),
        "transformation_fatigue": _r(hs.transformation_fatigue, 1),
        "learning_velocity_months": _r(hs.learning_velocity_months, 1),
        "effective_multiplier": _r(hs.effective_multiplier, 3),
    }


def serialize_org(org: OrganizationData) -> dict:
    """Full org data for the organization endpoint."""
    return {
        "roles": [serialize_role(r) for r in org.roles.values()],
        "workloads": [serialize_workload(w) for w in org.workloads.values()],
        "tasks": [serialize_task(t) for t in org.tasks.values()],
        "skills": [serialize_skill(s) for s in org.skills.values()],
        "tools": [serialize_tool(t) for t in org.tools.values()],
        "human_system": [serialize_human_system(h) for h in org.human_system.values()],
        "summary": {
            "total_headcount": org.total_headcount,
            "total_annual_cost": _r(org.total_annual_cost, 0),
            "functions": org.functions,
            "role_count": len(org.roles),
            "task_count": len(org.tasks),
            "skill_count": len(org.skills),
            "tool_count": len(org.tools),
        },
    }


def serialize_org_hierarchy(org: OrganizationData) -> dict:
    """Build org tree: function → sub_function → jfg → job_family → role."""
    tree = {"name": "Organization", "level": "org", "children": [], "headcount": 0, "annual_cost": 0}

    func_map: Dict[str, dict] = {}
    for role in org.roles.values():
        # Function level
        if role.function not in func_map:
            func_node = {
                "name": role.function, "level": "function", "children": [],
                "headcount": 0, "annual_cost": 0,
                "avg_automation": 0, "avg_augmentation": 0, "_role_count": 0,
            }
            func_map[role.function] = func_node
            tree["children"].append(func_node)

        fn = func_map[role.function]
        fn["headcount"] += role.headcount
        fn["annual_cost"] += role.annual_cost
        fn["avg_automation"] += role.automation_score
        fn["avg_augmentation"] += role.augmentation_score
        fn["_role_count"] += 1

        # Sub-function level
        sf_node = None
        for child in fn["children"]:
            if child["name"] == role.sub_function:
                sf_node = child
                break
        if sf_node is None:
            sf_node = {
                "name": role.sub_function, "level": "sub_function",
                "children": [], "headcount": 0, "annual_cost": 0,
            }
            fn["children"].append(sf_node)
        sf_node["headcount"] += role.headcount
        sf_node["annual_cost"] += role.annual_cost

        # JFG level
        jfg_node = None
        for child in sf_node["children"]:
            if child["name"] == role.jfg:
                jfg_node = child
                break
        if jfg_node is None:
            jfg_node = {
                "name": role.jfg, "level": "jfg",
                "children": [], "headcount": 0, "annual_cost": 0,
            }
            sf_node["children"].append(jfg_node)
        jfg_node["headcount"] += role.headcount
        jfg_node["annual_cost"] += role.annual_cost

        # Role as leaf
        jfg_node["children"].append({
            "name": role.role_name, "level": "role",
            "role_id": role.role_id, "headcount": role.headcount,
            "annual_cost": _r(role.annual_cost, 0),
            "automation_score": _r(role.automation_score, 1),
            "augmentation_score": _r(role.augmentation_score, 1),
            "management_level": role.management_level,
        })

    # Average automation scores
    for fn in func_map.values():
        c = fn.pop("_role_count", 1)
        fn["avg_automation"] = _r(fn["avg_automation"] / max(c, 1), 1)
        fn["avg_augmentation"] = _r(fn["avg_augmentation"] / max(c, 1), 1)
        fn["annual_cost"] = _r(fn["annual_cost"], 0)

    tree["headcount"] = sum(fn["headcount"] for fn in tree["children"])
    tree["annual_cost"] = _r(sum(fn["annual_cost"] for fn in tree["children"]), 0)
    return tree


# ────────────────────────────────────────────
# Gap Analysis Serializers
# ────────────────────────────────────────────

def serialize_task_gap(tg: TaskGapResult) -> dict:
    return {
        "task_id": tg.task_id,
        "task_name": tg.task_name,
        "category": tg.category,
        "effort_hours": _r(tg.effort_hours, 1),
        "l1": _r(tg.l1, 1), "l2": _r(tg.l2, 1), "l3": _r(tg.l3, 1),
        "adoption_gap": _r(tg.adoption_gap, 1),
        "capability_gap": _r(tg.capability_gap, 1),
        "total_gap": _r(tg.total_gap, 1),
        "freed_hours_adoption": _r(tg.freed_hours_adoption, 1),
        "freed_hours_total": _r(tg.freed_hours_total, 1),
        "compliance_mandated": tg.compliance_mandated,
        "matching_tool": tg.matching_tool,
    }


def serialize_role_gap(rg: RoleGapResult) -> dict:
    return {
        "role_id": rg.role_id,
        "role_name": rg.role_name,
        "function": rg.function,
        "sub_function": rg.sub_function,
        "jfg": rg.jfg,
        "job_family": rg.job_family,
        "management_level": rg.management_level,
        "headcount": rg.headcount,
        "avg_salary": _r(rg.avg_salary, 0),
        "annual_cost": _r(rg.annual_cost, 0),
        "automation_score": _r(rg.automation_score, 1),
        "augmentation_score": _r(rg.augmentation_score, 1),
        "weighted_l1": _r(rg.weighted_l1, 1),
        "weighted_l2": _r(rg.weighted_l2, 1),
        "weighted_l3": _r(rg.weighted_l3, 1),
        "adoption_gap_hours_pp": _r(rg.adoption_gap_hours_per_person, 1),
        "total_adoption_gap_hours": _r(rg.total_adoption_gap_hours, 1),
        "total_gap_hours": _r(rg.total_gap_hours, 1),
        "adoption_gap_savings": _r(rg.adoption_gap_savings_annual, 0),
        "full_gap_savings": _r(rg.full_gap_savings_annual, 0),
        "adoption_gap_fte": _r(rg.adoption_gap_fte_equivalent, 1),
        "compliance_tasks": rg.compliance_tasks,
        "total_tasks": rg.total_tasks,
        "redesign_candidate": rg.redesign_candidate,
        "workloads": [
            {
                "workload_id": w.workload_id,
                "workload_name": w.workload_name,
                "time_pct": _r(w.time_pct, 1),
                "avg_l1": _r(w.avg_l1, 1),
                "avg_l2": _r(w.avg_l2, 1),
                "avg_l3": _r(w.avg_l3, 1),
                "adoption_gap_hours": _r(w.adoption_gap_hours, 1),
                "total_gap_hours": _r(w.total_gap_hours, 1),
                "tasks": [serialize_task_gap(t) for t in w.tasks],
            }
            for w in rg.workloads
        ],
    }


def serialize_function_gap(fg: FunctionGapResult) -> dict:
    return {
        "function": fg.function,
        "headcount": fg.headcount,
        "annual_cost": _r(fg.annual_cost, 0),
        "avg_automation_score": _r(fg.avg_automation_score, 1),
        "avg_augmentation_score": _r(fg.avg_augmentation_score, 1),
        "weighted_l1": _r(fg.weighted_l1, 1),
        "weighted_l2": _r(fg.weighted_l2, 1),
        "weighted_l3": _r(fg.weighted_l3, 1),
        "total_adoption_gap_hours": _r(fg.total_adoption_gap_hours, 1),
        "total_gap_hours": _r(fg.total_gap_hours, 1),
        "adoption_gap_savings": _r(fg.adoption_gap_savings_annual, 0),
        "full_gap_savings": _r(fg.full_gap_savings_annual, 0),
        "adoption_gap_fte": _r(fg.adoption_gap_fte_equivalent, 1),
        "compliance_tasks": fg.compliance_tasks,
        "total_tasks": fg.total_tasks,
        "ai_proficiency": _r(fg.ai_proficiency, 1),
        "change_readiness": _r(fg.change_readiness, 1),
        "trust_level": _r(fg.trust_level, 1),
        "effective_multiplier": _r(fg.effective_multiplier, 3),
        "roles": [serialize_role_gap(r) for r in fg.roles],
    }


def serialize_org_gap(og: OrgGapResult) -> dict:
    return {
        "org_name": og.org_name,
        "headcount": og.headcount,
        "annual_cost": _r(og.annual_cost, 0),
        "avg_automation_score": _r(og.avg_automation_score, 1),
        "avg_augmentation_score": _r(og.avg_augmentation_score, 1),
        "weighted_l1": _r(og.weighted_l1, 1),
        "weighted_l2": _r(og.weighted_l2, 1),
        "weighted_l3": _r(og.weighted_l3, 1),
        "total_adoption_gap_hours": _r(og.total_adoption_gap_hours, 1),
        "total_gap_hours": _r(og.total_gap_hours, 1),
        "adoption_gap_savings": _r(og.adoption_gap_savings_annual, 0),
        "full_gap_savings": _r(og.full_gap_savings_annual, 0),
        "adoption_gap_fte": _r(og.adoption_gap_fte_equivalent, 1),
        "compliance_tasks": og.compliance_tasks,
        "total_tasks": og.total_tasks,
        "top_roles_by_adoption_gap": og.top_roles_by_adoption_gap,
        "top_roles_by_total_gap": og.top_roles_by_total_gap,
        "top_roles_by_savings": og.top_roles_by_savings,
        "functions": [serialize_function_gap(f) for f in og.functions],
    }


# ────────────────────────────────────────────
# Cascade Serializers
# ────────────────────────────────────────────

def serialize_stimulus(s: Stimulus) -> dict:
    return {
        "name": s.name,
        "stimulus_type": s.stimulus_type,
        "tools": s.tools,
        "target_scope": s.target_scope,
        "target_functions": s.target_functions,
        "target_roles": s.target_roles,
        "policy": s.policy,
        "absorption_factor": _r(s.absorption_factor, 2),
        "alpha": _r(s.alpha, 2),
        "training_cost_per_person": _r(s.training_cost_per_person, 0),
    }


def serialize_cascade(result: CascadeResult) -> dict:
    s1 = result.step1_scope
    s2 = result.step2_reclassification
    s3 = result.step3_capacity
    s4 = result.step4_skills
    s5 = result.step5_workforce
    s6 = result.step6_financial
    s7 = result.step7_structural
    s8 = result.step8_human_system
    s9 = result.step9_risk

    return {
        "stimulus": serialize_stimulus(result.stimulus),
        "step1_scope": {
            "affected_roles": s1.affected_roles,
            "affected_tasks": len(s1.affected_tasks),
            "total_tasks_in_scope": s1.total_tasks_in_scope,
            "addressable_tasks": s1.addressable_tasks,
            "compliance_protected": s1.compliance_protected,
            "total_headcount": s1.total_headcount,
            "total_hours_month": _r(s1.total_hours_month, 0),
            "functions_affected": s1.functions_affected,
        },
        "step2_reclassification": {
            "tasks_to_ai": s2.tasks_to_ai,
            "tasks_to_human_ai": s2.tasks_to_human_ai,
            "tasks_unchanged": s2.tasks_unchanged,
            "total_freed_hours_per_person": _r(s2.total_freed_hours_per_person, 1),
            "reclassified_tasks": [
                {
                    "task_id": t.task_id, "task_name": t.task_name,
                    "role_id": t.role_id, "category": t.category,
                    "previous_state": t.previous_state, "new_state": t.new_state,
                    "automation_pct": _r(t.automation_pct, 1),
                    "freed_hours": _r(t.freed_hours, 2),
                    "tool_used": t.tool_used,
                    "compliance_blocked": t.compliance_blocked,
                }
                for t in s2.reclassified_tasks
            ],
        },
        "step3_capacity": {
            "total_gross_freed_hours": _r(s3.total_gross_freed_hours, 0),
            "total_redistributed_hours": _r(s3.total_redistributed_hours, 0),
            "total_net_freed_hours": _r(s3.total_net_freed_hours, 0),
            "absorption_factor": _r(s3.absorption_factor, 2),
            "dampening_ratio": _r(s3.dampening_ratio, 3),
            "role_capacities": [
                {
                    "role_id": rc.role_id, "role_name": rc.role_name,
                    "headcount": rc.headcount,
                    "gross_freed_pp": _r(rc.gross_freed_hours_pp, 2),
                    "net_freed_pp": _r(rc.net_freed_hours_pp, 2),
                    "total_net_freed": _r(rc.total_net_freed_hours, 0),
                    "freed_pct": _r(rc.freed_pct, 1),
                }
                for rc in s3.role_capacities
            ],
        },
        "step4_skills": {
            "sunset_skills": [
                {"skill_id": s.skill_id, "skill_name": s.skill_name,
                 "direction": s.direction, "reason": s.reason}
                for s in s4.sunset_skills
            ],
            "sunrise_skills": [
                {"skill_id": s.skill_id, "skill_name": s.skill_name,
                 "direction": s.direction, "reason": s.reason}
                for s in s4.sunrise_skills
            ],
            "unchanged_skills": s4.unchanged_skills,
            "net_skill_gap": s4.net_skill_gap,
            "critical_sunset_count": len(s4.critical_sunset),
        },
        "step5_workforce": {
            "total_current_hc": s5.total_current_hc,
            "total_reducible_ftes": s5.total_reducible_ftes,
            "total_projected_hc": s5.total_projected_hc,
            "total_reduction_pct": _r(s5.total_reduction_pct, 1),
            "policy_applied": s5.policy_applied,
            "role_impacts": [
                {
                    "role_id": ri.role_id, "role_name": ri.role_name,
                    "current_hc": ri.current_hc, "projected_hc": ri.projected_hc,
                    "reducible_ftes": ri.reducible_ftes,
                    "reduction_pct": _r(ri.reduction_pct, 1),
                }
                for ri in s5.role_impacts
            ],
        },
        "step6_financial": {
            "license_cost_annual": _r(s6.license_cost_annual, 0),
            "training_cost": _r(s6.training_cost, 0),
            "change_management_cost": _r(s6.change_management_cost, 0),
            "total_investment": _r(s6.total_investment, 0),
            "salary_savings_annual": _r(s6.salary_savings_annual, 0),
            "productivity_savings_annual": _r(s6.productivity_savings_annual, 0),
            "total_savings_annual": _r(s6.total_savings_annual, 0),
            "net_annual": _r(s6.net_annual, 0),
            "payback_months": _r(s6.payback_months, 1),
            "roi_pct": _r(s6.roi_pct, 1),
            "role_savings": s6.role_savings,
        },
        "step7_structural": {
            "redesign_candidates": s7.redesign_candidates,
            "elimination_candidates": s7.elimination_candidates,
            "total_roles_affected": s7.total_roles_affected,
            "total_roles_redesign": s7.total_roles_redesign,
            "total_roles_elimination": s7.total_roles_elimination,
        },
        "step8_human_system": {
            "proficiency_direction": s8.proficiency_direction,
            "readiness_direction": s8.readiness_direction,
            "trust_direction": s8.trust_direction,
            "political_capital_direction": s8.political_capital_direction,
            "change_burden_score": _r(s8.change_burden_score, 0),
            "narrative": s8.narrative,
        },
        "step9_risk": {
            "overall_risk_level": s9.overall_risk_level,
            "risk_count_by_severity": s9.risk_count_by_severity,
            "risks": [
                {
                    "risk_type": r.risk_type, "severity": r.severity,
                    "description": r.description, "affected_scope": r.affected_scope,
                    "mitigation": r.mitigation,
                }
                for r in s9.risks
            ],
        },
    }


# ────────────────────────────────────────────
# Simulation Serializers
# ────────────────────────────────────────────

def serialize_fb_snapshot(snap: FBMonthlySnapshot) -> dict:
    return {
        "month": snap.month,
        "adoption_rate": _r(snap.effective_adoption_pct, 4),
        "raw_adoption_pct": _r(snap.raw_adoption_pct, 4),
        "effective_adoption_pct": _r(snap.effective_adoption_pct, 4),
        "adoption_dampening": _r(snap.adoption_dampening, 3),
        "gross_freed_hours": _r(snap.gross_freed_hours, 1),
        "redistributed_hours": _r(snap.redistributed_hours, 1),
        "net_freed_hours": _r(snap.net_freed_hours, 1),
        "hours_freed_this_month": _r(snap.net_freed_hours, 1),
        "cumulative_net_freed": _r(snap.cumulative_net_freed, 0),
        "dynamic_absorption_rate": _r(snap.dynamic_absorption_rate, 3),
        "headcount": snap.headcount,
        "hc_reduced_this_month": snap.hc_reduced_this_month,
        "cumulative_hc_reduced": snap.cumulative_hc_reduced,
        "hc_pct_of_original": _r(snap.hc_pct_of_original, 1),
        "skill_gap_opened": snap.skill_gap_opened,
        "skill_gap_closed": snap.skill_gap_closed,
        "current_skill_gap": snap.current_skill_gap,
        "skill_gap_pct": _r(snap.skill_gap_pct, 1),
        "cumulative_investment": _r(snap.cumulative_investment, 0),
        "cumulative_savings": _r(snap.cumulative_savings, 0),
        "net_position": _r(snap.net_position, 0),
        "monthly_savings_rate": _r(snap.monthly_savings_rate, 0),
        "productivity_index": _r(snap.productivity_index, 1),
        "proficiency": _r(snap.proficiency, 1),
        "readiness": _r(snap.readiness, 1),
        "trust": _r(snap.trust, 1),
        "political_capital": _r(snap.political_capital, 1),
        "transformation_fatigue": _r(snap.transformation_fatigue, 1),
        "human_multiplier": _r(snap.human_multiplier, 3),
        "trust_multiplier": _r(snap.trust_multiplier, 3),
        "capital_multiplier": _r(snap.capital_multiplier, 3),
        "b2_skill_drag": _r(snap.b2_skill_drag, 3),
        "b4_seniority_mult": _r(snap.b4_seniority_mult, 3),
        "ai_error_occurred": snap.ai_error_occurred,
        "role_headcounts": snap.role_headcounts,
    }


def serialize_fb_result(result: FBSimulationResult) -> dict:
    return {
        "summary": {
            "total_months": result.total_months,
            "initial_headcount": result.final_headcount + result.total_hc_reduced,
            "final_headcount": result.final_headcount,
            "total_hc_reduced": result.total_hc_reduced,
            "total_investment": _r(result.total_investment, 0),
            "total_savings": _r(result.total_savings, 0),
            "net_savings": _r(result.net_savings, 0),
            "roi_pct": _r((result.net_savings / result.total_investment * 100) if result.total_investment > 0 else 0, 1),
            "peak_adoption": _r(max((s.effective_adoption_pct for s in result.timeline), default=0), 3),
            "payback_month": result.payback_month,
            "peak_skill_gap_month": result.peak_skill_gap_month,
            "peak_skill_gap_value": result.peak_skill_gap_value,
            "productivity_valley_month": result.productivity_valley_month,
            "productivity_valley_value": _r(result.productivity_valley_value, 1),
            "final_proficiency": _r(result.final_proficiency, 1),
            "final_trust": _r(result.final_trust, 1),
            "final_readiness": _r(result.final_readiness, 1),
            "avg_adoption_dampening": _r(result.avg_adoption_dampening, 3),
        },
        "timeline": [serialize_fb_snapshot(s) for s in result.timeline],
        "cascade": serialize_cascade(result.baseline),
        "trace": result.trace.to_dict() if result.trace else None,
    }


def serialize_rate_params(rp: RateParams) -> dict:
    if rp is None:
        return None
    return {
        "alpha": _r(rp.alpha, 2),
        "k": _r(rp.k, 2),
        "midpoint": _r(rp.midpoint, 1),
        "delay_months": rp.delay_months,
    }


def serialize_sim_params(sp: SimulationParams) -> dict:
    return {
        "scenario_id": sp.scenario_id,
        "scenario_name": sp.scenario_name,
        "adoption": serialize_rate_params(sp.adoption),
        "expansion": serialize_rate_params(sp.expansion),
        "extension": serialize_rate_params(sp.extension),
        "policy": sp.policy,
        "absorption_factor": _r(sp.absorption_factor, 2),
        "time_horizon_months": sp.time_horizon_months,
        "hc_review_frequency": sp.hc_review_frequency,
        "enable_workflow_automation": sp.enable_workflow_automation,
    }
