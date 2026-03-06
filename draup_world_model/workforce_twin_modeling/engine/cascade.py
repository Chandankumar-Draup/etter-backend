"""
The 9-Step Cascade Engine
=========================
Takes a stimulus and propagates it through all 7 stocks in sequence.
Stage 1 runs this ONCE (single timestep, no S-curves, no feedback).
Stage 2+ will call this repeatedly with adoption rates modulating Step 2.

Stimulus → Scope → Reclassify → Capacity → Skills → Workforce →
           Financial → Structural → Human System → Risk

Design principle: Each step is a pure function.
  Input: previous step's output + org data
  Output: this step's result dataclass
  No side effects. No mutation of org data.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from models.organization import Task, Role, Workload, Skill, Tool, HumanSystem
from engine.loader import OrganizationData
from engine.gap_engine import CATEGORY_AUTOMATION_POTENTIAL, classify_task


# ============================================================
# Stimulus Definition
# ============================================================

@dataclass
class Stimulus:
    """What triggers the cascade. The cause that produces effects."""
    name: str
    stimulus_type: str                      # technology_injection | headcount_target | ...
    tools: List[str]                        # tool names to deploy
    target_scope: str                       # function name, sub_function, role_id, or "ALL"
    target_functions: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    policy: str = "moderate_reduction"      # HC policy
    absorption_factor: float = 0.35         # % of freed capacity absorbed by redistribution
    alpha: float = 1.0                      # adoption completeness (1.0 = full instant adoption for Stage 1)
    training_cost_per_person: float = 2000  # $ per affected person
    readiness_threshold: float = 0.0        # min readiness to proceed
    # Inverse solve targets (populated for target-based stimulus types)
    target_hc_reduction_pct: Optional[float] = None   # headcount_target: desired HC reduction %
    target_budget_amount: Optional[float] = None       # budget_constraint: max investment $
    target_automation_pct: Optional[float] = None      # automation_target / competitive: desired automation %


# ============================================================
# Step Result Dataclasses (one per cascade step)
# ============================================================

@dataclass
class Step1_ScopeResult:
    """What is affected by this stimulus."""
    affected_roles: List[str]               # role_ids
    affected_workloads: List[str]           # workload_ids
    affected_tasks: List[str]               # task_ids (addressable by the tool)
    total_tasks_in_scope: int               # all tasks in scope (including non-addressable)
    addressable_tasks: int                  # tasks the tool can address
    compliance_protected: int               # tasks that can't be touched
    total_headcount: int
    total_hours_month: float                # total FTE-hours in scope
    functions_affected: List[str]


@dataclass
class TaskReclassification:
    """Single task reclassification record."""
    task_id: str
    task_name: str
    workload_id: str
    role_id: str
    category: str
    effort_hours: float
    previous_state: str                     # human | human_ai | ai
    new_state: str                          # human | human_ai | ai
    automation_pct: float                   # % of effort now automated
    freed_hours: float                      # hours freed per person
    tool_used: str
    compliance_blocked: bool


@dataclass
class Step2_ReclassificationResult:
    """Which tasks changed classification and how."""
    reclassified_tasks: List[TaskReclassification]
    tasks_to_ai: int                        # fully automated
    tasks_to_human_ai: int                  # augmented
    tasks_unchanged: int                    # stayed human (compliance or negligibility)
    total_freed_hours_per_person: float     # sum of freed hours across all tasks (per person)


@dataclass
class RoleCapacity:
    """Capacity computation for a single role."""
    role_id: str
    role_name: str
    headcount: int
    gross_freed_hours_pp: float             # per person, before redistribution
    redistributed_hours_pp: float           # absorbed from other roles
    net_freed_hours_pp: float               # after redistribution
    total_net_freed_hours: float            # × headcount
    freed_pct: float                        # % of total effort freed


@dataclass
class Step3_CapacityResult:
    """How much capacity is freed (and how much is reabsorbed)."""
    role_capacities: List[RoleCapacity]
    total_gross_freed_hours: float
    total_redistributed_hours: float
    total_net_freed_hours: float
    absorption_factor: float
    dampening_ratio: float                  # net / gross — proves redistribution works


@dataclass
class SkillImpact:
    """Impact on a single skill."""
    skill_id: str
    skill_name: str
    workload_id: str
    direction: str                          # sunrise | sunset | unchanged
    reason: str


@dataclass
class Step4_SkillResult:
    """Which skills are sunset and sunrise."""
    sunset_skills: List[SkillImpact]
    sunrise_skills: List[SkillImpact]
    unchanged_skills: int
    net_skill_gap: int                      # sunrise - sunset (positive = gap opens)
    critical_sunset: List[SkillImpact]      # sunset skills with high proficiency req


@dataclass
class RoleWorkforceImpact:
    """Workforce impact for a single role."""
    role_id: str
    role_name: str
    current_hc: int
    net_freed_ftes: float
    reducible_ftes: int                     # floor(net_freed_ftes) — can't fire 0.3 of a person
    residual_hours: float                   # leftover hours after FTE reduction
    projected_hc: int
    reduction_pct: float


@dataclass
class Step5_WorkforceResult:
    """Headcount impact per role and total."""
    role_impacts: List[RoleWorkforceImpact]
    total_current_hc: int
    total_reducible_ftes: int
    total_projected_hc: int
    total_reduction_pct: float
    policy_applied: str


@dataclass
class Step6_FinancialResult:
    """Investment vs. savings."""
    # Investment breakdown
    license_cost_annual: float
    training_cost: float
    change_management_cost: float
    total_investment: float

    # Savings breakdown
    salary_savings_annual: float            # from HC reduction
    productivity_savings_annual: float      # from residual freed hours (remaining staff more productive)
    total_savings_annual: float

    # Net
    net_annual: float                       # savings - investment
    payback_months: float                   # months to break even (investment / monthly savings)
    roi_pct: float                          # net / investment × 100

    # Per-role detail
    role_savings: List[dict] = field(default_factory=list)


@dataclass
class Step7_StructuralResult:
    """Which roles need redesign."""
    redesign_candidates: List[dict]         # roles where freed_pct > 40%
    elimination_candidates: List[dict]      # roles where freed_pct > 70%
    total_roles_affected: int
    total_roles_redesign: int
    total_roles_elimination: int


@dataclass
class Step8_HumanSystemResult:
    """Qualitative human system impact (Stage 1 = direction only, not magnitude)."""
    proficiency_direction: str              # up (training deployed) | unchanged
    readiness_direction: str                # down (disruption) | unchanged
    trust_direction: str                    # neutral (no outcome data yet)
    political_capital_direction: str        # depends on early results
    change_burden_score: float              # scope × speed / readiness (0-100)
    narrative: str                          # human-readable explanation


@dataclass
class RiskItem:
    """A single identified risk."""
    risk_type: str                          # compliance | concentration | change_burden | capability_valley | quality
    severity: str                           # low | medium | high | critical
    description: str
    affected_scope: str
    mitigation: str


@dataclass
class Step9_RiskResult:
    """Risk assessment."""
    risks: List[RiskItem]
    overall_risk_level: str                 # low | medium | high | critical
    risk_count_by_severity: Dict[str, int]
    top_risk: Optional[RiskItem]


# ============================================================
# The Complete Cascade Result
# ============================================================

@dataclass
class CascadeResult:
    """Complete output of the 9-step cascade."""
    stimulus: Stimulus
    step1_scope: Step1_ScopeResult
    step2_reclassification: Step2_ReclassificationResult
    step3_capacity: Step3_CapacityResult
    step4_skills: Step4_SkillResult
    step5_workforce: Step5_WorkforceResult
    step6_financial: Step6_FinancialResult
    step7_structural: Step7_StructuralResult
    step8_human_system: Step8_HumanSystemResult
    step9_risk: Step9_RiskResult


# ============================================================
# Task State Classification
# ============================================================

# Full automation categories → "AI" state
AI_CATEGORIES = {"directive", "feedback_loop"}
# Augmentation categories → "Human+AI" state
HUMAN_AI_CATEGORIES = {"task_iteration", "learning", "validation"}
# Stays human
HUMAN_CATEGORIES = {"negligibility"}

# T2-#11: Shadow work tax — AI tools save X% but verification overhead reclaims ~10%.
# In reality, workers spend time checking AI output, correcting errors, and working
# around tool limitations. Net freed is lower than theoretical freed.
SHADOW_WORK_TAX = 0.10  # 10% of freed capacity consumed by AI output verification

# How much effort is freed per state transition (BEFORE shadow work tax)
_RAW_AUTOMATION_FREED_PCT = {
    "directive":      85.0,   # 85% freed (15% oversight remains)
    "feedback_loop":  75.0,   # 75% freed
    "task_iteration": 35.0,   # 35% freed (human still iterates, AI assists)
    "learning":       25.0,   # 25% freed (AI curates, human learns)
    "validation":     30.0,   # 30% freed (AI validates, human reviews edge cases)
    "negligibility":   0.0,   # 0% freed
}

# T2-#11: Apply shadow work tax — net freed after verification overhead
AUTOMATION_FREED_PCT = {
    cat: pct * (1.0 - SHADOW_WORK_TAX) for cat, pct in _RAW_AUTOMATION_FREED_PCT.items()
}

# T2-#8: Productive hours per management level.
# 160h/month is gross. After meetings, admin, PTO:
#   IC: 80% productive (128h)   Senior IC: 75% (120h)
#   Manager: 60% (96h)          Director+: 45% (72h)
PRODUCTIVE_HOURS_PCT = {
    "Individual Contributor": 0.80,
    "Senior IC":              0.75,
    "Manager":                0.60,
    "Senior Manager":         0.55,
    "Director":               0.45,
    "VP":                     0.40,
}
GROSS_HOURS_MONTH = 160.0


def productive_hours_month(management_level: str) -> float:
    """Return productive (task-automatable) hours per person per month for a level."""
    pct = PRODUCTIVE_HOURS_PCT.get(management_level, 0.80)
    return GROSS_HOURS_MONTH * pct


# ============================================================
# Step 1: Scope Resolution
# ============================================================

def step1_resolve_scope(stimulus: Stimulus, org: OrganizationData) -> Step1_ScopeResult:
    """
    Identify everything affected by the stimulus.
    Walk: scope → functions → roles → workloads → tasks.
    """
    # Determine affected roles
    affected_role_ids = []
    if stimulus.target_roles:
        affected_role_ids = stimulus.target_roles
    elif stimulus.target_functions:
        for fn in stimulus.target_functions:
            affected_role_ids.extend(org.roles_by_function.get(fn, []))
    else:
        affected_role_ids = list(org.roles.keys())

    # Walk to workloads and tasks
    affected_wl_ids = []
    all_task_ids = []
    addressable_task_ids = []
    compliance_count = 0

    # Build tool lookup for matching
    stimulus_tools = {t: org.tools[tid]
                      for tid, t_obj in org.tools.items()
                      for t in stimulus.tools
                      if t_obj.tool_name == t}
    # Simpler: find tool objects by name
    tool_objs = [t for t in org.tools.values() if t.tool_name in stimulus.tools]

    for rid in affected_role_ids:
        for wl_id in org.workloads_by_role.get(rid, []):
            affected_wl_ids.append(wl_id)
            for tid in org.tasks_by_workload.get(wl_id, []):
                task = org.tasks[tid]
                all_task_ids.append(tid)

                if task.compliance_mandated_human:
                    compliance_count += 1
                    continue

                # Check if any stimulus tool addresses this task
                for tool in tool_objs:
                    role = org.roles[rid]
                    deployed = ("All" in tool.deployed_to_functions or
                                role.function in tool.deployed_to_functions)
                    cat_match = task.category in tool.task_categories_addressed
                    if deployed and cat_match:
                        addressable_task_ids.append(tid)
                        break

    functions_affected = sorted(set(org.roles[rid].function for rid in affected_role_ids))
    total_hc = sum(org.roles[rid].headcount for rid in affected_role_ids)
    # T2-#8: Use productive hours per management level instead of gross 160h
    total_hours = sum(
        org.roles[rid].headcount * productive_hours_month(org.roles[rid].management_level)
        for rid in affected_role_ids
    )

    return Step1_ScopeResult(
        affected_roles=affected_role_ids,
        affected_workloads=affected_wl_ids,
        affected_tasks=addressable_task_ids,
        total_tasks_in_scope=len(all_task_ids),
        addressable_tasks=len(set(addressable_task_ids)),
        compliance_protected=compliance_count,
        total_headcount=total_hc,
        total_hours_month=total_hours,
        functions_affected=functions_affected,
    )


# ============================================================
# Step 2: Task Reclassification
# ============================================================

def step2_reclassify_tasks(
    scope: Step1_ScopeResult,
    stimulus: Stimulus,
    org: OrganizationData,
) -> Step2_ReclassificationResult:
    """
    For each addressable task, determine new classification and freed hours.
    Stage 1: instant, full adoption (alpha=1.0). No S-curves.
    """
    reclassified = []
    tasks_to_ai = 0
    tasks_to_human_ai = 0
    tasks_unchanged = 0
    total_freed_pp = 0.0

    addressable_set = set(scope.affected_tasks)

    # Walk all tasks in scope
    for rid in scope.affected_roles:
        for wl_id in org.workloads_by_role.get(rid, []):
            for tid in org.tasks_by_workload.get(wl_id, []):
                task = org.tasks[tid]

                if tid in addressable_set and not task.compliance_mandated_human:
                    # Determine new state based on category
                    if task.category in AI_CATEGORIES:
                        new_state = "ai"
                        tasks_to_ai += 1
                    elif task.category in HUMAN_AI_CATEGORIES:
                        new_state = "human_ai"
                        tasks_to_human_ai += 1
                    else:
                        new_state = "human"
                        tasks_unchanged += 1
                        continue

                    freed_pct = AUTOMATION_FREED_PCT.get(task.category, 0.0) * stimulus.alpha
                    freed_hours = task.effort_hours_month * (freed_pct / 100.0)
                    total_freed_pp += freed_hours

                    # Determine which tool
                    tool_used = ""
                    for tn in stimulus.tools:
                        for tool in org.tools.values():
                            if tool.tool_name == tn and task.category in tool.task_categories_addressed:
                                tool_used = tn
                                break
                        if tool_used:
                            break

                    reclassified.append(TaskReclassification(
                        task_id=tid,
                        task_name=task.task_name,
                        workload_id=wl_id,
                        role_id=rid,
                        category=task.category,
                        effort_hours=task.effort_hours_month,
                        previous_state="human",
                        new_state=new_state,
                        automation_pct=freed_pct,
                        freed_hours=freed_hours,
                        tool_used=tool_used,
                        compliance_blocked=False,
                    ))
                else:
                    tasks_unchanged += 1

    return Step2_ReclassificationResult(
        reclassified_tasks=reclassified,
        tasks_to_ai=tasks_to_ai,
        tasks_to_human_ai=tasks_to_human_ai,
        tasks_unchanged=tasks_unchanged,
        total_freed_hours_per_person=total_freed_pp,
    )


# ============================================================
# Step 3: Capacity Computation
# ============================================================

def step3_compute_capacity(
    scope: Step1_ScopeResult,
    reclass: Step2_ReclassificationResult,
    stimulus: Stimulus,
    org: OrganizationData,
) -> Step3_CapacityResult:
    """
    Compute freed capacity per role, with redistribution dampening.

    Key dynamic: freed hours are PARTIALLY absorbed by work redistribution.
    If Role A loses 50% of tasks, adjacent roles absorb some of that work.
    absorption_factor (0.3-0.6) determines how much is reabsorbed.
    """
    # Group freed hours by role
    freed_by_role: Dict[str, float] = {}
    for rc in reclass.reclassified_tasks:
        freed_by_role[rc.role_id] = freed_by_role.get(rc.role_id, 0.0) + rc.freed_hours

    role_capacities = []
    total_gross = 0.0
    total_redistributed = 0.0
    total_net = 0.0

    for rid in scope.affected_roles:
        role = org.roles[rid]
        gross_freed_pp = freed_by_role.get(rid, 0.0)

        # Redistribution: absorption_factor % of freed capacity is reabsorbed
        # (tasks from eliminated/reduced positions redistributed to remaining staff)
        redistributed_pp = gross_freed_pp * stimulus.absorption_factor
        net_freed_pp = gross_freed_pp - redistributed_pp

        # Scale to full headcount
        total_net_freed = net_freed_pp * role.headcount

        # Freed % of total effort
        wl_ids = org.workloads_by_role.get(rid, [])
        total_effort = sum(
            org.tasks[tid].effort_hours_month
            for wl_id in wl_ids
            for tid in org.tasks_by_workload.get(wl_id, [])
        )
        freed_pct = (gross_freed_pp / total_effort * 100) if total_effort > 0 else 0

        role_capacities.append(RoleCapacity(
            role_id=rid,
            role_name=role.role_name,
            headcount=role.headcount,
            gross_freed_hours_pp=gross_freed_pp,
            redistributed_hours_pp=redistributed_pp,
            net_freed_hours_pp=net_freed_pp,
            total_net_freed_hours=total_net_freed,
            freed_pct=freed_pct,
        ))

        total_gross += gross_freed_pp * role.headcount
        total_redistributed += redistributed_pp * role.headcount
        total_net += total_net_freed

    dampening = total_net / total_gross if total_gross > 0 else 0

    return Step3_CapacityResult(
        role_capacities=role_capacities,
        total_gross_freed_hours=total_gross,
        total_redistributed_hours=total_redistributed,
        total_net_freed_hours=total_net,
        absorption_factor=stimulus.absorption_factor,
        dampening_ratio=dampening,
    )


# ============================================================
# Step 4: Skill Impact
# ============================================================

def step4_compute_skill_impact(
    reclass: Step2_ReclassificationResult,
    org: OrganizationData,
) -> Step4_SkillResult:
    """
    Determine which skills are sunset (from automated tasks)
    and which are sunrise (needed for AI collaboration).
    """
    # Collect workloads that had tasks reclassified
    affected_wl_ids = set()
    reclassified_wl_tasks: Dict[str, List[str]] = {}
    for rc in reclass.reclassified_tasks:
        affected_wl_ids.add(rc.workload_id)
        reclassified_wl_tasks.setdefault(rc.workload_id, []).append(rc.new_state)

    sunset_skills = []
    sunrise_skills = []
    unchanged_count = 0
    critical_sunset = []

    for wl_id in affected_wl_ids:
        skill_ids = org.skills_by_workload.get(wl_id, [])
        # Check: did ANY task in this workload go to AI?
        states = reclassified_wl_tasks.get(wl_id, [])
        has_ai_tasks = "ai" in states
        has_human_ai_tasks = "human_ai" in states

        for sid in skill_ids:
            skill = org.skills[sid]

            if skill.is_sunset and has_ai_tasks:
                # Sunset skill AND its workload is being automated → confirmed sunset
                impact = SkillImpact(
                    skill_id=sid,
                    skill_name=skill.skill_name,
                    workload_id=wl_id,
                    direction="sunset",
                    reason=f"Workload tasks automated → skill demand declining",
                )
                sunset_skills.append(impact)
                if skill.proficiency_required >= 70:
                    critical_sunset.append(impact)

            elif skill.is_sunrise and (has_ai_tasks or has_human_ai_tasks):
                # Sunrise skill AND workload is being transformed → confirmed sunrise
                sunrise_skills.append(SkillImpact(
                    skill_id=sid,
                    skill_name=skill.skill_name,
                    workload_id=wl_id,
                    direction="sunrise",
                    reason=f"AI tools deployed → new skill needed for AI collaboration",
                ))

            elif skill.skill_type == "current" and has_ai_tasks:
                # Current skill in automated workload → potential sunset
                sunset_skills.append(SkillImpact(
                    skill_id=sid,
                    skill_name=skill.skill_name,
                    workload_id=wl_id,
                    direction="sunset",
                    reason=f"Current skill in automated workload → demand declining",
                ))
            else:
                unchanged_count += 1

    return Step4_SkillResult(
        sunset_skills=sunset_skills,
        sunrise_skills=sunrise_skills,
        unchanged_skills=unchanged_count,
        net_skill_gap=len(sunrise_skills) - len(sunset_skills),
        critical_sunset=critical_sunset,
    )


# ============================================================
# Step 5: Workforce Impact
# ============================================================

def step5_compute_workforce_impact(
    capacity: Step3_CapacityResult,
    stimulus: Stimulus,
    org: OrganizationData,
) -> Step5_WorkforceResult:
    """
    Translate freed capacity into headcount changes based on policy.

    Key: can't fire 0.3 of a person. floor() to whole FTEs.
    Policy determines whether reductions happen at all.
    """
    role_impacts = []
    total_current = 0
    total_reducible = 0

    for rc in capacity.role_capacities:
        role = org.roles[rc.role_id]
        # T2-#8: Use productive hours for FTE computation
        role_hours = productive_hours_month(role.management_level)
        net_freed_ftes = rc.total_net_freed_hours / role_hours

        # Apply policy
        if stimulus.policy == "no_layoffs" or stimulus.policy == "no_change":
            reducible = 0
        elif stimulus.policy == "natural_attrition":
            # Only reduce through natural attrition (cap at ~8% annual = ~0.7%/month)
            max_attrition = max(1, int(role.headcount * 0.007))
            reducible = min(math.floor(net_freed_ftes), max_attrition)
        elif stimulus.policy == "moderate_reduction":
            reducible = math.floor(net_freed_ftes)
        elif stimulus.policy == "active_reduction":
            # Round to nearest (more aggressive)
            reducible = round(net_freed_ftes)
        elif stimulus.policy == "rapid_redeployment":
            # T1-#3: Round up — faster reallocation of freed capacity
            reducible = math.ceil(net_freed_ftes) if net_freed_ftes >= 0.5 else 0
        else:
            reducible = math.floor(net_freed_ftes)

        # T2-#9: Min staffing floor — can't reduce below 20% of original headcount
        min_staffing = max(1, math.ceil(role.headcount * 0.20))
        max_reducible = max(0, role.headcount - min_staffing)
        reducible = min(reducible, max_reducible)
        residual = rc.total_net_freed_hours - (reducible * role_hours)
        projected_hc = role.headcount - reducible
        reduction_pct = (reducible / role.headcount * 100) if role.headcount > 0 else 0

        role_impacts.append(RoleWorkforceImpact(
            role_id=rc.role_id,
            role_name=rc.role_name,
            current_hc=role.headcount,
            net_freed_ftes=net_freed_ftes,
            reducible_ftes=reducible,
            residual_hours=residual,
            projected_hc=projected_hc,
            reduction_pct=reduction_pct,
        ))

        total_current += role.headcount
        total_reducible += reducible

    total_projected = total_current - total_reducible
    total_pct = (total_reducible / total_current * 100) if total_current > 0 else 0

    return Step5_WorkforceResult(
        role_impacts=role_impacts,
        total_current_hc=total_current,
        total_reducible_ftes=total_reducible,
        total_projected_hc=total_projected,
        total_reduction_pct=total_pct,
        policy_applied=stimulus.policy,
    )


# ============================================================
# Step 6: Financial Impact
# ============================================================

def step6_compute_financial_impact(
    scope: Step1_ScopeResult,
    capacity: Step3_CapacityResult,
    workforce: Step5_WorkforceResult,
    stimulus: Stimulus,
    org: OrganizationData,
) -> Step6_FinancialResult:
    """
    Investment vs. savings computation.
    Investment: licensing + training + change management.
    Savings: salary reduction + productivity gains from residual hours.
    """
    # Investment: licensing for all affected headcount
    annual_license = 0.0
    for tool_name in stimulus.tools:
        for tool in org.tools.values():
            if tool.tool_name == tool_name:
                annual_license += tool.license_cost_per_user_month * 12 * scope.total_headcount
                break

    training = stimulus.training_cost_per_person * scope.total_headcount
    change_mgmt = training * 0.5  # rule of thumb: change mgmt ≈ 50% of training
    total_investment = annual_license + training + change_mgmt

    # Savings: salary from reduced FTEs
    salary_savings = 0.0
    role_savings_detail = []
    for wi in workforce.role_impacts:
        role = org.roles[wi.role_id]
        role_salary_saving = wi.reducible_ftes * role.avg_salary
        salary_savings += role_salary_saving

        # Productivity gain from residual hours (remaining staff are more productive)
        residual_fte_equivalent = wi.residual_hours / 160.0 if wi.residual_hours > 0 else 0
        productivity_value = residual_fte_equivalent * role.avg_salary * 0.5  # 50% of FTE value
        role_savings_detail.append({
            "role_id": wi.role_id,
            "role_name": wi.role_name,
            "hc_reduced": wi.reducible_ftes,
            "salary_savings": role_salary_saving,
            "productivity_savings": productivity_value,
        })

    productivity_savings = sum(r["productivity_savings"] for r in role_savings_detail)
    total_savings = salary_savings + productivity_savings
    net_annual = total_savings - total_investment

    # Payback
    monthly_savings = total_savings / 12.0
    payback = total_investment / monthly_savings if monthly_savings > 0 else float('inf')

    # ROI
    roi = (net_annual / total_investment * 100) if total_investment > 0 else 0

    return Step6_FinancialResult(
        license_cost_annual=annual_license,
        training_cost=training,
        change_management_cost=change_mgmt,
        total_investment=total_investment,
        salary_savings_annual=salary_savings,
        productivity_savings_annual=productivity_savings,
        total_savings_annual=total_savings,
        net_annual=net_annual,
        payback_months=payback,
        roi_pct=roi,
        role_savings=role_savings_detail,
    )


# ============================================================
# Step 7: Structural Impact
# ============================================================

def step7_compute_structural_impact(
    capacity: Step3_CapacityResult,
    org: OrganizationData,
) -> Step7_StructuralResult:
    """
    Flag roles where freed capacity exceeds redesign/elimination thresholds.
    >40% freed → redesign candidate (role needs to be redefined)
    >70% freed → elimination candidate (role may not be viable)
    """
    redesign = []
    elimination = []

    for rc in capacity.role_capacities:
        role = org.roles[rc.role_id]

        if rc.freed_pct > 70:
            elimination.append({
                "role_id": rc.role_id,
                "role_name": role.role_name,
                "function": role.function,
                "headcount": role.headcount,
                "freed_pct": round(rc.freed_pct, 1),
                "recommendation": "Role may not be viable — consider elimination and task redistribution",
            })
        elif rc.freed_pct > 40:
            redesign.append({
                "role_id": rc.role_id,
                "role_name": role.role_name,
                "function": role.function,
                "headcount": role.headcount,
                "freed_pct": round(rc.freed_pct, 1),
                "recommendation": "Significant capacity freed — role needs redesign with new task composition",
            })

    return Step7_StructuralResult(
        redesign_candidates=redesign,
        elimination_candidates=elimination,
        total_roles_affected=len(capacity.role_capacities),
        total_roles_redesign=len(redesign),
        total_roles_elimination=len(elimination),
    )


# ============================================================
# Step 8: Human System Impact
# ============================================================

def step8_compute_human_system_impact(
    scope: Step1_ScopeResult,
    workforce: Step5_WorkforceResult,
    stimulus: Stimulus,
    org: OrganizationData,
) -> Step8_HumanSystemResult:
    """
    Qualitative human system impact. Stage 1 records DIRECTION only.
    Stage 3 will compute magnitudes with feedback loops.
    """
    # Change burden = (scope × disruption) / readiness
    disruption = workforce.total_reduction_pct / 100.0  # 0-1 scale
    scope_factor = len(scope.affected_roles) / max(len(org.roles), 1)

    # Average readiness across affected functions
    avg_readiness = 0
    count = 0
    for fn in scope.functions_affected:
        hs = org.human_system.get(fn)
        if hs:
            avg_readiness += hs.change_readiness
            count += 1
    avg_readiness = avg_readiness / count if count > 0 else 50

    change_burden = (scope_factor * 50 + disruption * 50) / max(avg_readiness / 100, 0.1)
    change_burden = min(100, change_burden * 100)

    # Directions
    prof_dir = "up" if stimulus.training_cost_per_person > 0 else "unchanged"
    readiness_dir = "down" if workforce.total_reduction_pct > 5 else "unchanged"
    trust_dir = "neutral"  # no outcome data in Stage 1
    capital_dir = "pending"  # depends on results

    narrative_parts = []
    if workforce.total_reducible_ftes > 0:
        narrative_parts.append(
            f"Headcount reduction of {workforce.total_reducible_ftes} FTEs will create disruption."
            f" Readiness is likely to decline initially."
        )
    if change_burden > 60:
        narrative_parts.append(
            f"Change burden is HIGH ({change_burden:.0f}/100)."
            f" Consider phased deployment to reduce resistance."
        )
    if avg_readiness < 50:
        narrative_parts.append(
            f"Average readiness ({avg_readiness:.0f}) is below the 50-point threshold."
            f" Readiness intervention recommended BEFORE deployment."
        )
    if not narrative_parts:
        narrative_parts.append("Moderate change impact. Standard change management should suffice.")

    return Step8_HumanSystemResult(
        proficiency_direction=prof_dir,
        readiness_direction=readiness_dir,
        trust_direction=trust_dir,
        political_capital_direction=capital_dir,
        change_burden_score=change_burden,
        narrative=" ".join(narrative_parts),
    )


# ============================================================
# Step 9: Risk Assessment
# ============================================================

def step9_assess_risk(
    scope: Step1_ScopeResult,
    reclass: Step2_ReclassificationResult,
    capacity: Step3_CapacityResult,
    skills: Step4_SkillResult,
    workforce: Step5_WorkforceResult,
    human_system: Step8_HumanSystemResult,
    org: OrganizationData,
) -> Step9_RiskResult:
    """
    Identify risks from the cascade.
    Types: compliance, concentration, change_burden, capability_valley, quality.
    """
    risks = []

    # R1: Compliance risk — any compliance-protected tasks adjacent to automated ones?
    if scope.compliance_protected > 0:
        risks.append(RiskItem(
            risk_type="compliance",
            severity="medium",
            description=f"{scope.compliance_protected} compliance-mandated tasks in scope. "
                        f"Automation must NOT touch these. Verify boundary enforcement.",
            affected_scope=", ".join(scope.functions_affected),
            mitigation="Implement compliance gates in automation pipeline. Regular audit.",
        ))

    # R2: Concentration risk — critical skills in fewer hands
    if skills.critical_sunset:
        skill_names = [s.skill_name for s in skills.critical_sunset[:5]]
        risks.append(RiskItem(
            risk_type="concentration",
            severity="high" if len(skills.critical_sunset) > 5 else "medium",
            description=f"{len(skills.critical_sunset)} high-proficiency skills are being sunset: "
                        f"{', '.join(skill_names)}. Knowledge may be lost.",
            affected_scope=", ".join(scope.functions_affected),
            mitigation="Document critical knowledge before automation. Retain SMEs for oversight.",
        ))

    # R3: Change burden
    if human_system.change_burden_score > 60:
        severity = "high" if human_system.change_burden_score > 80 else "medium"
        risks.append(RiskItem(
            risk_type="change_burden",
            severity=severity,
            description=f"Change burden score is {human_system.change_burden_score:.0f}/100. "
                        f"Risk of change fatigue and resistance.",
            affected_scope=", ".join(scope.functions_affected),
            mitigation="Phase deployment. Increase change management investment. "
                       "Visible early wins to build momentum.",
        ))

    # R4: Capability valley — large skill gap opens
    if skills.net_skill_gap > 10:
        risks.append(RiskItem(
            risk_type="capability_valley",
            severity="medium",
            description=f"Net skill gap of {skills.net_skill_gap}: "
                        f"{len(skills.sunrise_skills)} sunrise vs {len(skills.sunset_skills)} sunset. "
                        f"Productivity dip expected during transition.",
            affected_scope=", ".join(scope.functions_affected),
            mitigation="Reskilling program should START before or concurrent with deployment. "
                       "Budget 3-12 months for proficiency development.",
        ))

    # R5: Quality risk — large HC reduction in short time
    if workforce.total_reduction_pct > 20:
        risks.append(RiskItem(
            risk_type="quality",
            severity="high",
            description=f"Headcount reduction of {workforce.total_reduction_pct:.1f}% may "
                        f"impact service quality. Remaining staff absorb more work.",
            affected_scope=", ".join(scope.functions_affected),
            mitigation="Monitor quality metrics post-deployment. "
                       "Establish minimum staffing floors per function.",
        ))

    # R6: Single-function concentration
    if len(scope.functions_affected) == 1 and workforce.total_reducible_ftes > 20:
        risks.append(RiskItem(
            risk_type="concentration",
            severity="medium",
            description=f"All {workforce.total_reducible_ftes} FTE reductions concentrated in "
                        f"{scope.functions_affected[0]}. Political and operational risk.",
            affected_scope=scope.functions_affected[0],
            mitigation="Consider staggering reductions. Communicate business rationale early.",
        ))

    # Overall risk level
    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if risks:
        max_severity = max(risks, key=lambda r: severity_order.get(r.severity, 0))
        overall = max_severity.severity
    else:
        overall = "low"

    count_by_severity = {}
    for r in risks:
        count_by_severity[r.severity] = count_by_severity.get(r.severity, 0) + 1

    return Step9_RiskResult(
        risks=risks,
        overall_risk_level=overall,
        risk_count_by_severity=count_by_severity,
        top_risk=risks[0] if risks else None,
    )


# ============================================================
# The Cascade: Run All 9 Steps
# ============================================================

def run_cascade(stimulus: Stimulus, org: OrganizationData) -> CascadeResult:
    """
    Execute the full 9-step cascade for a given stimulus.
    Each step feeds into the next. Pure computation, no side effects.
    """
    # Ensure all tasks are classified (from Stage 0)
    for task in org.tasks.values():
        wl = org.workloads[task.workload_id]
        role = org.roles[wl.role_id]
        classify_task(task, org.tools, role.function)

    step1 = step1_resolve_scope(stimulus, org)
    step2 = step2_reclassify_tasks(step1, stimulus, org)
    step3 = step3_compute_capacity(step1, step2, stimulus, org)
    step4 = step4_compute_skill_impact(step2, org)
    step5 = step5_compute_workforce_impact(step3, stimulus, org)
    step6 = step6_compute_financial_impact(step1, step3, step5, stimulus, org)
    step7 = step7_compute_structural_impact(step3, org)
    step8 = step8_compute_human_system_impact(step1, step5, stimulus, org)
    step9 = step9_assess_risk(step1, step2, step3, step4, step5, step8, org)

    return CascadeResult(
        stimulus=stimulus,
        step1_scope=step1,
        step2_reclassification=step2,
        step3_capacity=step3,
        step4_skills=step4,
        step5_workforce=step5,
        step6_financial=step6,
        step7_structural=step7,
        step8_human_system=step8,
        step9_risk=step9,
    )
