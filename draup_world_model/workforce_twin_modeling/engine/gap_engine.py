"""
Gap computation engine for Stage 0: Static Snapshot.

Three-layer classification:
  L1 (Etter Ceiling):  What % of this task COULD be automated (from category defaults)
  L2 (Achievable):     L1 filtered by whether org has a matching deployed tool
  L3 (Realized):       L2 filtered by current adoption % of that tool

Gaps:
  Adoption Gap  = L2 - L3  (tool deployed but not used — free money)
  Capability Gap = L1 - L2  (no matching tool — need procurement)
  Total Gap     = L1 - L3  (full distance from ceiling to floor)

Principle: Compute at the leaf (task), aggregate upward. Same pattern at every scale.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from workforce_twin_modeling.models.organization import (
    Task, Role, Workload, Skill, Tool, HumanSystem,
    OrgNode, FinancialSnapshot,
)
from workforce_twin_modeling.engine.loader import OrganizationData


# ============================================================
# L1: Etter Category Defaults
# Task category → theoretical automation percentage
# These come from Etter's classification engine
# ============================================================

CATEGORY_AUTOMATION_POTENTIAL = {
    "directive":      90.0,   # Rules-based, deterministic → fully automatable
    "feedback_loop":  85.0,   # Refinement based on outcomes → highly automatable
    "task_iteration": 50.0,   # Continuous adjustment → partially automatable
    "learning":       40.0,   # Knowledge acquisition → AI-assisted
    "validation":     45.0,   # QA/compliance → AI-assisted with human oversight
    "negligibility":   5.0,   # Creative, strategic, relationship → human
}


def _tool_covers_task(tool: Tool, task: Task, role_function: str) -> bool:
    """Check if a tool is deployed to a function AND addresses this task's category."""
    # Check function deployment
    deployed = ("All" in tool.deployed_to_functions or
                role_function in tool.deployed_to_functions)
    # Check category match
    category_match = task.category in tool.task_categories_addressed
    # Check tool name match (task specifies which tool can automate it)
    tool_match = (task.automatable_by_tool is not None and
                  task.automatable_by_tool == tool.tool_name)

    return deployed and category_match and tool_match


def classify_task(task: Task, tools: Dict[str, Tool], role_function: str) -> Task:
    """
    Compute three-layer classification for a single task.
    This is the atomic operation — everything else aggregates from here.
    """
    # L1: Etter theoretical potential (from category)
    task.l1_etter_potential = CATEGORY_AUTOMATION_POTENTIAL.get(task.category, 0.0)

    # Compliance floor: if mandated human, cap L1 at 5%
    if task.compliance_mandated_human:
        task.l1_etter_potential = min(task.l1_etter_potential, 5.0)

    # L2: Achievable — is there a deployed tool that matches?
    matching_tool = None
    for tool in tools.values():
        if _tool_covers_task(tool, task, role_function):
            matching_tool = tool
            break

    if matching_tool is not None:
        # Tool is deployed AND matches category → L2 = L1
        task.l2_achievable = task.l1_etter_potential
        # L3: Realized — how much of the tool is actually adopted
        task.l3_realized = task.l2_achievable * (matching_tool.current_adoption_pct / 100.0)
    else:
        # No matching tool deployed → L2 = 0 (no achievable potential without tool)
        # But check if ANY tool in org (not deployed here) could work
        task.l2_achievable = 0.0
        task.l3_realized = 0.0

    return task


# ============================================================
# Aggregation Data Structures
# ============================================================

@dataclass
class TaskGapResult:
    """Gap analysis result for a single task."""
    task_id: str
    task_name: str
    category: str
    effort_hours: float
    l1: float
    l2: float
    l3: float
    adoption_gap: float
    capability_gap: float
    total_gap: float
    freed_hours_adoption: float     # hours freed by closing adoption gap
    freed_hours_total: float        # hours freed by closing all gaps
    compliance_mandated: bool
    matching_tool: Optional[str]


@dataclass
class WorkloadGapResult:
    """Aggregated gap result for a workload."""
    workload_id: str
    workload_name: str
    role_id: str
    time_pct: float
    total_effort_hours: float
    tasks: List[TaskGapResult] = field(default_factory=list)

    # Aggregated from tasks
    avg_l1: float = 0.0
    avg_l2: float = 0.0
    avg_l3: float = 0.0
    adoption_gap_hours: float = 0.0
    capability_gap_hours: float = 0.0
    total_gap_hours: float = 0.0
    compliance_tasks: int = 0


@dataclass
class RoleGapResult:
    """Aggregated gap result for a role."""
    role_id: str
    role_name: str
    function: str
    sub_function: str
    jfg: str
    job_family: str
    management_level: str
    headcount: int
    avg_salary: float
    annual_cost: float
    workloads: List[WorkloadGapResult] = field(default_factory=list)

    # Etter scores
    automation_score: float = 0.0
    augmentation_score: float = 0.0

    # Aggregated from workloads
    weighted_l1: float = 0.0
    weighted_l2: float = 0.0
    weighted_l3: float = 0.0
    adoption_gap_hours_per_person: float = 0.0
    capability_gap_hours_per_person: float = 0.0
    total_gap_hours_per_person: float = 0.0
    total_adoption_gap_hours: float = 0.0     # × headcount
    total_capability_gap_hours: float = 0.0
    total_gap_hours: float = 0.0
    compliance_tasks: int = 0
    total_tasks: int = 0

    # Financial
    adoption_gap_savings_annual: float = 0.0   # $ saved if adoption gap closed
    full_gap_savings_annual: float = 0.0       # $ saved if all gaps closed
    adoption_gap_fte_equivalent: float = 0.0   # FTEs freed by adoption gap

    # Flags
    redesign_candidate: bool = False           # >40% freed capacity


@dataclass
class FunctionGapResult:
    """Aggregated gap result for a function."""
    function: str
    roles: List[RoleGapResult] = field(default_factory=list)

    headcount: int = 0
    annual_cost: float = 0.0
    avg_automation_score: float = 0.0
    avg_augmentation_score: float = 0.0
    weighted_l1: float = 0.0
    weighted_l2: float = 0.0
    weighted_l3: float = 0.0
    total_adoption_gap_hours: float = 0.0
    total_capability_gap_hours: float = 0.0
    total_gap_hours: float = 0.0
    adoption_gap_savings_annual: float = 0.0
    full_gap_savings_annual: float = 0.0
    adoption_gap_fte_equivalent: float = 0.0
    compliance_tasks: int = 0
    total_tasks: int = 0

    # Human system
    ai_proficiency: float = 0.0
    change_readiness: float = 0.0
    trust_level: float = 0.0
    effective_multiplier: float = 0.0


@dataclass
class OrgGapResult:
    """Top-level org gap analysis — the complete snapshot."""
    org_name: str
    functions: List[FunctionGapResult] = field(default_factory=list)

    headcount: int = 0
    annual_cost: float = 0.0
    avg_automation_score: float = 0.0
    avg_augmentation_score: float = 0.0
    weighted_l1: float = 0.0
    weighted_l2: float = 0.0
    weighted_l3: float = 0.0
    total_adoption_gap_hours: float = 0.0
    total_capability_gap_hours: float = 0.0
    total_gap_hours: float = 0.0
    adoption_gap_savings_annual: float = 0.0
    full_gap_savings_annual: float = 0.0
    adoption_gap_fte_equivalent: float = 0.0
    compliance_tasks: int = 0
    total_tasks: int = 0

    # Top opportunities
    top_roles_by_adoption_gap: List[dict] = field(default_factory=list)
    top_roles_by_total_gap: List[dict] = field(default_factory=list)
    top_roles_by_savings: List[dict] = field(default_factory=list)


# ============================================================
# Opportunity Ranking
# ============================================================

@dataclass
class Opportunity:
    """A ranked automation opportunity."""
    rank: int
    role_id: str
    role_name: str
    function: str
    gap_type: str                    # adoption|capability|total
    gap_hours_annual: float
    fte_equivalent: float
    savings_annual: float
    headcount_affected: int
    avg_salary: float
    automation_score: float
    risk_level: str                  # low|medium|high
    notes: str = ""


# ============================================================
# The Core Computation: compute_snapshot
# ============================================================

def compute_snapshot(org: OrganizationData) -> OrgGapResult:
    """
    Compute the complete three-layer gap analysis.

    Flow: task → workload → role → function → org
    Same pattern at every scale. Classify at leaf, aggregate upward.
    """
    # Phase 1: Classify every task
    for task in org.tasks.values():
        wl = org.workloads[task.workload_id]
        role = org.roles[wl.role_id]
        classify_task(task, org.tools, role.function)

    # Phase 2: Aggregate tasks → workloads
    workload_results = {}
    for wl_id, wl in org.workloads.items():
        task_ids = org.tasks_by_workload.get(wl_id, [])
        task_results = []
        total_effort = 0.0
        weighted_l1 = 0.0
        weighted_l2 = 0.0
        weighted_l3 = 0.0
        adopt_hours = 0.0
        cap_hours = 0.0
        tot_hours = 0.0
        compliance_count = 0

        for tid in task_ids:
            t = org.tasks[tid]
            total_effort += t.effort_hours_month

            tr = TaskGapResult(
                task_id=t.task_id,
                task_name=t.task_name,
                category=t.category,
                effort_hours=t.effort_hours_month,
                l1=t.l1_etter_potential,
                l2=t.l2_achievable,
                l3=t.l3_realized,
                adoption_gap=t.adoption_gap,
                capability_gap=t.capability_gap,
                total_gap=t.total_gap,
                freed_hours_adoption=t.freed_hours_at_l2,
                freed_hours_total=t.freed_hours_at_l1,
                compliance_mandated=t.compliance_mandated_human,
                matching_tool=t.automatable_by_tool if t.l2_achievable > 0 else None,
            )
            task_results.append(tr)

            # Effort-weighted layer averages
            weighted_l1 += t.l1_etter_potential * t.effort_hours_month
            weighted_l2 += t.l2_achievable * t.effort_hours_month
            weighted_l3 += t.l3_realized * t.effort_hours_month
            adopt_hours += t.freed_hours_at_l2
            cap_hours += t.effort_hours_month * (t.capability_gap / 100.0)
            tot_hours += t.freed_hours_at_l1
            if t.compliance_mandated_human:
                compliance_count += 1

        wl_result = WorkloadGapResult(
            workload_id=wl_id,
            workload_name=wl.workload_name,
            role_id=wl.role_id,
            time_pct=wl.time_pct,
            total_effort_hours=total_effort,
            tasks=task_results,
            avg_l1=weighted_l1 / total_effort if total_effort > 0 else 0,
            avg_l2=weighted_l2 / total_effort if total_effort > 0 else 0,
            avg_l3=weighted_l3 / total_effort if total_effort > 0 else 0,
            adoption_gap_hours=adopt_hours,
            capability_gap_hours=cap_hours,
            total_gap_hours=tot_hours,
            compliance_tasks=compliance_count,
        )
        workload_results[wl_id] = wl_result

    # Phase 3: Aggregate workloads → roles
    role_results = {}
    for role_id, role in org.roles.items():
        wl_ids = org.workloads_by_role.get(role_id, [])
        wl_results_for_role = [workload_results[wid] for wid in wl_ids if wid in workload_results]

        total_effort = sum(w.total_effort_hours for w in wl_results_for_role)
        adopt_hrs = sum(w.adoption_gap_hours for w in wl_results_for_role)
        cap_hrs = sum(w.capability_gap_hours for w in wl_results_for_role)
        tot_hrs = sum(w.total_gap_hours for w in wl_results_for_role)
        compliance = sum(w.compliance_tasks for w in wl_results_for_role)
        n_tasks = sum(len(w.tasks) for w in wl_results_for_role)

        # Effort-weighted layer averages
        w_l1 = sum(w.avg_l1 * w.total_effort_hours for w in wl_results_for_role)
        w_l2 = sum(w.avg_l2 * w.total_effort_hours for w in wl_results_for_role)
        w_l3 = sum(w.avg_l3 * w.total_effort_hours for w in wl_results_for_role)

        # Per-person hours
        adopt_per_person = adopt_hrs
        cap_per_person = cap_hrs
        tot_per_person = tot_hrs

        # Scale to full headcount (hours are already per-person from task definitions)
        total_adopt_hours = adopt_per_person * role.headcount
        total_cap_hours = cap_per_person * role.headcount
        total_tot_hours = tot_per_person * role.headcount

        # Financial impact
        fte_freed_adoption = total_adopt_hours / 160.0 if total_adopt_hours > 0 else 0
        cost_per_fte_monthly = role.avg_salary / 12.0
        adopt_savings_annual = fte_freed_adoption * role.avg_salary
        full_savings_annual = (total_tot_hours / 160.0) * role.avg_salary if total_tot_hours > 0 else 0

        # Redesign flag: >40% of effort could be freed
        freed_pct = (tot_per_person / total_effort * 100) if total_effort > 0 else 0

        rr = RoleGapResult(
            role_id=role_id,
            role_name=role.role_name,
            function=role.function,
            sub_function=role.sub_function,
            jfg=role.jfg,
            job_family=role.job_family,
            management_level=role.management_level,
            headcount=role.headcount,
            avg_salary=role.avg_salary,
            annual_cost=role.annual_cost,
            workloads=wl_results_for_role,
            automation_score=role.automation_score,
            augmentation_score=role.augmentation_score,
            weighted_l1=w_l1 / total_effort if total_effort > 0 else 0,
            weighted_l2=w_l2 / total_effort if total_effort > 0 else 0,
            weighted_l3=w_l3 / total_effort if total_effort > 0 else 0,
            adoption_gap_hours_per_person=adopt_per_person,
            capability_gap_hours_per_person=cap_per_person,
            total_gap_hours_per_person=tot_per_person,
            total_adoption_gap_hours=total_adopt_hours,
            total_capability_gap_hours=total_cap_hours,
            total_gap_hours=total_tot_hours,
            compliance_tasks=compliance,
            total_tasks=n_tasks,
            adoption_gap_savings_annual=adopt_savings_annual,
            full_gap_savings_annual=full_savings_annual,
            adoption_gap_fte_equivalent=fte_freed_adoption,
            redesign_candidate=freed_pct > 40.0,
        )
        role_results[role_id] = rr

    # Phase 4: Aggregate roles → functions
    function_results = {}
    for func_name in org.functions:
        role_ids = org.roles_by_function.get(func_name, [])
        func_roles = [role_results[rid] for rid in role_ids if rid in role_results]
        hs = org.human_system.get(func_name)

        total_hc = sum(r.headcount for r in func_roles)
        total_cost = sum(r.annual_cost for r in func_roles)
        total_adopt_hrs = sum(r.total_adoption_gap_hours for r in func_roles)
        total_cap_hrs = sum(r.total_capability_gap_hours for r in func_roles)
        total_tot_hrs = sum(r.total_gap_hours for r in func_roles)
        adopt_savings = sum(r.adoption_gap_savings_annual for r in func_roles)
        full_savings = sum(r.full_gap_savings_annual for r in func_roles)
        adopt_ftes = sum(r.adoption_gap_fte_equivalent for r in func_roles)
        compliance = sum(r.compliance_tasks for r in func_roles)
        total_tasks = sum(r.total_tasks for r in func_roles)

        # Headcount-weighted automation scores
        w_auto = sum(r.automation_score * r.headcount for r in func_roles)
        w_aug = sum(r.augmentation_score * r.headcount for r in func_roles)
        # Headcount-weighted layers
        w_l1 = sum(r.weighted_l1 * r.headcount for r in func_roles)
        w_l2 = sum(r.weighted_l2 * r.headcount for r in func_roles)
        w_l3 = sum(r.weighted_l3 * r.headcount for r in func_roles)

        fr = FunctionGapResult(
            function=func_name,
            roles=func_roles,
            headcount=total_hc,
            annual_cost=total_cost,
            avg_automation_score=w_auto / total_hc if total_hc > 0 else 0,
            avg_augmentation_score=w_aug / total_hc if total_hc > 0 else 0,
            weighted_l1=w_l1 / total_hc if total_hc > 0 else 0,
            weighted_l2=w_l2 / total_hc if total_hc > 0 else 0,
            weighted_l3=w_l3 / total_hc if total_hc > 0 else 0,
            total_adoption_gap_hours=total_adopt_hrs,
            total_capability_gap_hours=total_cap_hrs,
            total_gap_hours=total_tot_hrs,
            adoption_gap_savings_annual=adopt_savings,
            full_gap_savings_annual=full_savings,
            adoption_gap_fte_equivalent=adopt_ftes,
            compliance_tasks=compliance,
            total_tasks=total_tasks,
            ai_proficiency=hs.ai_proficiency if hs else 0,
            change_readiness=hs.change_readiness if hs else 0,
            trust_level=hs.trust_level if hs else 0,
            effective_multiplier=hs.effective_multiplier if hs else 0,
        )
        function_results[func_name] = fr

    # Phase 5: Aggregate functions → org
    all_func_results = list(function_results.values())
    total_hc = sum(f.headcount for f in all_func_results)

    org_result = OrgGapResult(
        org_name="InsureCo",
        functions=all_func_results,
        headcount=total_hc,
        annual_cost=sum(f.annual_cost for f in all_func_results),
        avg_automation_score=sum(f.avg_automation_score * f.headcount for f in all_func_results) / total_hc if total_hc > 0 else 0,
        avg_augmentation_score=sum(f.avg_augmentation_score * f.headcount for f in all_func_results) / total_hc if total_hc > 0 else 0,
        weighted_l1=sum(f.weighted_l1 * f.headcount for f in all_func_results) / total_hc if total_hc > 0 else 0,
        weighted_l2=sum(f.weighted_l2 * f.headcount for f in all_func_results) / total_hc if total_hc > 0 else 0,
        weighted_l3=sum(f.weighted_l3 * f.headcount for f in all_func_results) / total_hc if total_hc > 0 else 0,
        total_adoption_gap_hours=sum(f.total_adoption_gap_hours for f in all_func_results),
        total_capability_gap_hours=sum(f.total_capability_gap_hours for f in all_func_results),
        total_gap_hours=sum(f.total_gap_hours for f in all_func_results),
        adoption_gap_savings_annual=sum(f.adoption_gap_savings_annual for f in all_func_results),
        full_gap_savings_annual=sum(f.full_gap_savings_annual for f in all_func_results),
        adoption_gap_fte_equivalent=sum(f.adoption_gap_fte_equivalent for f in all_func_results),
        compliance_tasks=sum(f.compliance_tasks for f in all_func_results),
        total_tasks=sum(f.total_tasks for f in all_func_results),
    )

    # Phase 6: Rank opportunities
    all_roles = list(role_results.values())

    org_result.top_roles_by_adoption_gap = sorted(
        [{"role_id": r.role_id, "role_name": r.role_name, "function": r.function,
          "adoption_gap_hours": r.total_adoption_gap_hours,
          "savings_annual": r.adoption_gap_savings_annual,
          "fte_freed": r.adoption_gap_fte_equivalent}
         for r in all_roles if r.total_adoption_gap_hours > 0],
        key=lambda x: x["savings_annual"], reverse=True
    )[:10]

    org_result.top_roles_by_total_gap = sorted(
        [{"role_id": r.role_id, "role_name": r.role_name, "function": r.function,
          "total_gap_hours": r.total_gap_hours,
          "savings_annual": r.full_gap_savings_annual,
          "headcount": r.headcount}
         for r in all_roles if r.total_gap_hours > 0],
        key=lambda x: x["savings_annual"], reverse=True
    )[:10]

    org_result.top_roles_by_savings = sorted(
        [{"role_id": r.role_id, "role_name": r.role_name, "function": r.function,
          "adoption_savings": r.adoption_gap_savings_annual,
          "full_savings": r.full_gap_savings_annual,
          "headcount": r.headcount,
          "redesign_candidate": r.redesign_candidate}
         for r in all_roles],
        key=lambda x: x["full_savings"], reverse=True
    )[:10]

    return org_result
