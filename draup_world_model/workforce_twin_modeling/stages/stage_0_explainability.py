"""
Stage 0 Explainability Engine
=============================
Traces the three-layer gap computation from atomic task to org total.
Every number has a provenance. Every aggregation has a weight.

The question: HOW did we get L1=56.4%, L2=51.3%, L3=9.5%?

Answer: Bottom-up computation through 4 aggregation levels:
  Task (atomic classification) → Workload (effort-weighted avg)
  → Role (effort-weighted avg × headcount) → Function (HC-weighted avg)
  → Org (HC-weighted avg of functions)

At each level, the trace shows:
  1. WHAT was computed
  2. WHY (the rule that determined it)
  3. WITH WHAT inputs
  4. RESULTING IN what numbers
"""
import sys
import os
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.loader import load_organization
from engine.gap_engine import (
    CATEGORY_AUTOMATION_POTENTIAL,
    classify_task,
    compute_snapshot,
)


def trace_single_task(task, tools, role_function, role_name):
    """
    Trace the three-layer classification of ONE task.
    This is the atomic unit — everything else aggregates from here.
    """
    lines = []
    lines.append(f"\n    ┌─ TASK: {task.task_name}")
    lines.append(f"    │  ID: {task.task_id} | Category: {task.category} | Effort: {task.effort_hours_month:.1f} hrs/month")
    lines.append(f"    │  Automatable by: {task.automatable_by_tool or 'No specific tool'}")
    lines.append(f"    │  Compliance mandated human: {task.compliance_mandated_human}")

    # L1 Reasoning
    base_potential = CATEGORY_AUTOMATION_POTENTIAL.get(task.category, 0.0)
    lines.append(f"    │")
    lines.append(f"    │  L1 (Etter Ceiling):")
    lines.append(f"    │    Rule: category '{task.category}' → base potential = {base_potential:.0f}%")
    if task.compliance_mandated_human:
        lines.append(f"    │    Rule: compliance_mandated_human = True → cap at 5%")
        lines.append(f"    │    Result: L1 = min({base_potential:.0f}%, 5%) = {task.l1_etter_potential:.1f}%")
    else:
        lines.append(f"    │    Result: L1 = {task.l1_etter_potential:.1f}%")

    # L2 Reasoning
    lines.append(f"    │")
    lines.append(f"    │  L2 (Achievable with deployed tech):")
    matching_tool = None
    for tool in tools.values():
        deployed = ("All" in tool.deployed_to_functions or
                    role_function in tool.deployed_to_functions)
        category_match = task.category in tool.task_categories_addressed
        tool_match = (task.automatable_by_tool is not None and
                      task.automatable_by_tool == tool.tool_name)
        if deployed and category_match and tool_match:
            matching_tool = tool
            break

    if matching_tool:
        lines.append(f"    │    Check: Is there a tool deployed to '{role_function}' that addresses '{task.category}' tasks?")
        lines.append(f"    │    Match: {matching_tool.tool_name}")
        lines.append(f"    │      - Deployed to: {matching_tool.deployed_to_functions} → covers '{role_function}'? YES")
        lines.append(f"    │      - Addresses categories: {matching_tool.task_categories_addressed} → includes '{task.category}'? YES")
        lines.append(f"    │      - Task specifies '{task.automatable_by_tool}' → matches? YES")
        lines.append(f"    │    Result: L2 = L1 = {task.l2_achievable:.1f}% (tool CAN do this)")
    else:
        lines.append(f"    │    Check: Is there a deployed tool matching '{task.category}' for function '{role_function}'?")
        if task.automatable_by_tool:
            # Check WHY it didn't match
            for tool in tools.values():
                if tool.tool_name == task.automatable_by_tool:
                    deployed = ("All" in tool.deployed_to_functions or
                                role_function in tool.deployed_to_functions)
                    cat_match = task.category in tool.task_categories_addressed
                    lines.append(f"    │    Tool '{tool.tool_name}' exists but:")
                    if not deployed:
                        lines.append(f"    │      - NOT deployed to '{role_function}' (deployed to: {tool.deployed_to_functions})")
                    if not cat_match:
                        lines.append(f"    │      - Does NOT address '{task.category}' (addresses: {tool.task_categories_addressed})")
                    break
            else:
                lines.append(f"    │    Task specifies '{task.automatable_by_tool}' but no such tool found in tech stack")
        else:
            lines.append(f"    │    No tool specified for this task (automatable_by_tool is empty)")
        lines.append(f"    │    Result: L2 = 0.0% (no matching deployed tool)")

    # L3 Reasoning
    lines.append(f"    │")
    lines.append(f"    │  L3 (Actually realized today):")
    if matching_tool:
        lines.append(f"    │    Rule: L3 = L2 × (current_adoption_pct / 100)")
        lines.append(f"    │    {matching_tool.tool_name} adoption = {matching_tool.current_adoption_pct:.0f}%")
        lines.append(f"    │    Result: L3 = {task.l2_achievable:.1f}% × {matching_tool.current_adoption_pct:.0f}% = {task.l3_realized:.1f}%")
    else:
        lines.append(f"    │    No matching tool → L3 = 0.0%")

    # Gaps
    lines.append(f"    │")
    lines.append(f"    │  GAPS:")
    lines.append(f"    │    Adoption Gap  = L2 - L3 = {task.l2_achievable:.1f}% - {task.l3_realized:.1f}% = {task.adoption_gap:.1f}%")
    lines.append(f"    │    Capability Gap = L1 - L2 = {task.l1_etter_potential:.1f}% - {task.l2_achievable:.1f}% = {task.capability_gap:.1f}%")
    lines.append(f"    │    Total Gap     = L1 - L3 = {task.l1_etter_potential:.1f}% - {task.l3_realized:.1f}% = {task.total_gap:.1f}%")

    # Hours impact
    lines.append(f"    │")
    lines.append(f"    │  HOURS IMPACT (per person per month):")
    lines.append(f"    │    Freed by adoption gap: {task.effort_hours_month:.1f}h × {task.adoption_gap:.1f}% = {task.freed_hours_at_l2:.1f}h")
    lines.append(f"    │    Freed by total gap:    {task.effort_hours_month:.1f}h × {task.total_gap:.1f}% = {task.freed_hours_at_l1:.1f}h")
    lines.append(f"    └─")

    return "\n".join(lines)


def trace_workload_aggregation(wl, tasks_for_wl, org):
    """Trace how task-level L1/L2/L3 aggregates to workload level."""
    lines = []
    role = org.roles[wl.role_id]

    lines.append(f"\n  ┌─ WORKLOAD: {wl.workload_name}")
    lines.append(f"  │  ID: {wl.workload_id} | Role: {role.role_name} | Time: {wl.time_pct}% of role")
    lines.append(f"  │  Category mix: Dir={wl.directive_pct}% FB={wl.feedback_loop_pct}% "
                 f"TI={wl.task_iteration_pct}% Lr={wl.learning_pct}% "
                 f"Val={wl.validation_pct}% Neg={wl.negligibility_pct}%")
    lines.append(f"  │  Tasks: {len(tasks_for_wl)}")

    # Show each task
    for t in tasks_for_wl:
        lines.append(f"  │    {t.task_name[:45]:<45} cat={t.category:<15} "
                     f"L1={t.l1_etter_potential:>5.1f}%  L2={t.l2_achievable:>5.1f}%  "
                     f"L3={t.l3_realized:>5.1f}%  effort={t.effort_hours_month:>5.1f}h")

    # Aggregation formula
    total_effort = sum(t.effort_hours_month for t in tasks_for_wl)
    weighted_l1 = sum(t.l1_etter_potential * t.effort_hours_month for t in tasks_for_wl)
    weighted_l2 = sum(t.l2_achievable * t.effort_hours_month for t in tasks_for_wl)
    weighted_l3 = sum(t.l3_realized * t.effort_hours_month for t in tasks_for_wl)

    avg_l1 = weighted_l1 / total_effort if total_effort > 0 else 0
    avg_l2 = weighted_l2 / total_effort if total_effort > 0 else 0
    avg_l3 = weighted_l3 / total_effort if total_effort > 0 else 0

    lines.append(f"  │")
    lines.append(f"  │  AGGREGATION (effort-weighted average):")
    lines.append(f"  │    Formula: Workload_Lx = Σ(task_Lx × task_effort) / Σ(task_effort)")
    lines.append(f"  │    Total effort = {total_effort:.1f} hours/month")
    lines.append(f"  │")

    # Show the weighted sum for L1
    terms_l1 = " + ".join(f"{t.l1_etter_potential:.1f}×{t.effort_hours_month:.1f}" for t in tasks_for_wl[:3])
    if len(tasks_for_wl) > 3:
        terms_l1 += f" + ...({len(tasks_for_wl)-3} more)"
    lines.append(f"  │    L1 = ({terms_l1}) / {total_effort:.1f}")
    lines.append(f"  │       = {weighted_l1:.1f} / {total_effort:.1f} = {avg_l1:.1f}%")
    lines.append(f"  │    L2 = {weighted_l2:.1f} / {total_effort:.1f} = {avg_l2:.1f}%")
    lines.append(f"  │    L3 = {weighted_l3:.1f} / {total_effort:.1f} = {avg_l3:.1f}%")

    adopt_hrs = sum(t.freed_hours_at_l2 for t in tasks_for_wl)
    total_hrs = sum(t.freed_hours_at_l1 for t in tasks_for_wl)
    compliance = sum(1 for t in tasks_for_wl if t.compliance_mandated_human)
    lines.append(f"  │")
    lines.append(f"  │  Freed hours (adoption gap): {adopt_hrs:.1f}h/person/month")
    lines.append(f"  │  Freed hours (total gap):    {total_hrs:.1f}h/person/month")
    lines.append(f"  │  Compliance-protected tasks:  {compliance}")
    lines.append(f"  └─")

    return "\n".join(lines)


def trace_role_aggregation(role, workloads_for_role, org):
    """Trace how workload-level metrics aggregate to role level."""
    lines = []

    lines.append(f"\n┌─ ROLE: {role.role_name}")
    lines.append(f"│  ID: {role.role_id} | Function: {role.function} | HC: {role.headcount} | Salary: ${role.avg_salary:,.0f}")
    lines.append(f"│  Etter scores: automation={role.automation_score}% augmentation={role.augmentation_score}%")
    lines.append(f"│  Workloads: {len(workloads_for_role)}")

    total_effort = 0.0
    w_l1 = 0.0
    w_l2 = 0.0
    w_l3 = 0.0
    adopt_hrs_pp = 0.0
    total_hrs_pp = 0.0

    for wl in workloads_for_role:
        task_ids = org.tasks_by_workload.get(wl.workload_id, [])
        tasks = [org.tasks[tid] for tid in task_ids]
        wl_effort = sum(t.effort_hours_month for t in tasks)
        wl_w_l1 = sum(t.l1_etter_potential * t.effort_hours_month for t in tasks)
        wl_w_l2 = sum(t.l2_achievable * t.effort_hours_month for t in tasks)
        wl_w_l3 = sum(t.l3_realized * t.effort_hours_month for t in tasks)
        wl_avg_l1 = wl_w_l1 / wl_effort if wl_effort > 0 else 0
        wl_avg_l2 = wl_w_l2 / wl_effort if wl_effort > 0 else 0
        wl_avg_l3 = wl_w_l3 / wl_effort if wl_effort > 0 else 0
        wl_adopt = sum(t.freed_hours_at_l2 for t in tasks)
        wl_total = sum(t.freed_hours_at_l1 for t in tasks)

        total_effort += wl_effort
        w_l1 += wl_w_l1
        w_l2 += wl_w_l2
        w_l3 += wl_w_l3
        adopt_hrs_pp += wl_adopt
        total_hrs_pp += wl_total

        lines.append(f"│    {wl.workload_name:<30} time={wl.time_pct:>3.0f}% effort={wl_effort:>5.1f}h "
                     f"L1={wl_avg_l1:>5.1f}% L2={wl_avg_l2:>5.1f}% L3={wl_avg_l3:>5.1f}%  "
                     f"adopt_hrs={wl_adopt:>5.1f}h")

    avg_l1 = w_l1 / total_effort if total_effort > 0 else 0
    avg_l2 = w_l2 / total_effort if total_effort > 0 else 0
    avg_l3 = w_l3 / total_effort if total_effort > 0 else 0

    lines.append(f"│")
    lines.append(f"│  AGGREGATION (effort-weighted across workloads):")
    lines.append(f"│    Total effort per person: {total_effort:.1f} hours/month")
    lines.append(f"│    Role L1 = {w_l1:.1f} / {total_effort:.1f} = {avg_l1:.1f}%")
    lines.append(f"│    Role L2 = {w_l2:.1f} / {total_effort:.1f} = {avg_l2:.1f}%")
    lines.append(f"│    Role L3 = {w_l3:.1f} / {total_effort:.1f} = {avg_l3:.1f}%")

    lines.append(f"│")
    lines.append(f"│  SCALING TO HEADCOUNT ({role.headcount} people):")
    lines.append(f"│    Adoption gap hours = {adopt_hrs_pp:.1f}h/person × {role.headcount} people = {adopt_hrs_pp * role.headcount:.0f}h total/month")
    fte_freed = adopt_hrs_pp * role.headcount / 160.0
    lines.append(f"│    FTEs freed (adoption gap) = {adopt_hrs_pp * role.headcount:.0f}h / 160h = {fte_freed:.1f} FTEs")
    savings = fte_freed * role.avg_salary
    lines.append(f"│    Annual savings = {fte_freed:.1f} FTEs × ${role.avg_salary:,.0f} = ${savings:,.0f}")

    freed_pct = (total_hrs_pp / total_effort * 100) if total_effort > 0 else 0
    lines.append(f"│")
    lines.append(f"│  Freed capacity: {freed_pct:.1f}% of role effort → redesign candidate? {'YES' if freed_pct > 40 else 'NO'} (threshold: 40%)")
    lines.append(f"└─")

    return "\n".join(lines)


def trace_function_aggregation(func_name, func_roles, org):
    """Trace how role-level metrics aggregate to function level."""
    lines = []

    total_hc = sum(r.headcount for r in func_roles)
    lines.append(f"\n{'='*90}")
    lines.append(f"  FUNCTION: {func_name}")
    lines.append(f"  Roles: {len(func_roles)} | Total HC: {total_hc}")
    lines.append(f"{'='*90}")

    # Show per-role contribution
    lines.append(f"\n  ROLE CONTRIBUTIONS (headcount-weighted):")
    lines.append(f"  {'Role':<30} {'HC':>5} {'Weight':>7} {'L1':>6} {'L2':>6} {'L3':>6}  {'HC×L1':>8} {'HC×L2':>8} {'HC×L3':>8}")
    lines.append(f"  {'─'*88}")

    sum_hc_l1 = 0
    sum_hc_l2 = 0
    sum_hc_l3 = 0
    sum_adopt_savings = 0
    sum_full_savings = 0

    for role in sorted(func_roles, key=lambda r: r.headcount, reverse=True):
        # Recompute role-level L1/L2/L3 for the trace
        wl_ids = org.workloads_by_role.get(role.role_id, [])
        total_effort = 0
        w_l1 = w_l2 = w_l3 = 0
        adopt_hrs_pp = 0

        for wl_id in wl_ids:
            task_ids = org.tasks_by_workload.get(wl_id, [])
            for tid in task_ids:
                t = org.tasks[tid]
                total_effort += t.effort_hours_month
                w_l1 += t.l1_etter_potential * t.effort_hours_month
                w_l2 += t.l2_achievable * t.effort_hours_month
                w_l3 += t.l3_realized * t.effort_hours_month
                adopt_hrs_pp += t.freed_hours_at_l2

        r_l1 = w_l1 / total_effort if total_effort > 0 else 0
        r_l2 = w_l2 / total_effort if total_effort > 0 else 0
        r_l3 = w_l3 / total_effort if total_effort > 0 else 0
        weight = role.headcount / total_hc * 100

        hc_l1 = r_l1 * role.headcount
        hc_l2 = r_l2 * role.headcount
        hc_l3 = r_l3 * role.headcount
        sum_hc_l1 += hc_l1
        sum_hc_l2 += hc_l2
        sum_hc_l3 += hc_l3

        fte_freed = adopt_hrs_pp * role.headcount / 160.0
        adopt_savings = fte_freed * role.avg_salary
        full_freed = sum(org.tasks[tid].freed_hours_at_l1 for wl_id in wl_ids for tid in org.tasks_by_workload.get(wl_id, []))
        full_savings = (full_freed * role.headcount / 160.0) * role.avg_salary
        sum_adopt_savings += adopt_savings
        sum_full_savings += full_savings

        lines.append(f"  {role.role_name[:30]:<30} {role.headcount:>5} {weight:>5.1f}%"
                     f"  {r_l1:>5.1f} {r_l2:>5.1f} {r_l3:>5.1f}"
                     f"  {hc_l1:>8.1f} {hc_l2:>8.1f} {hc_l3:>8.1f}")

    lines.append(f"  {'─'*88}")
    lines.append(f"  {'TOTAL':<30} {total_hc:>5} {'100%':>7}"
                 f"  {'':>6} {'':>6} {'':>6}"
                 f"  {sum_hc_l1:>8.1f} {sum_hc_l2:>8.1f} {sum_hc_l3:>8.1f}")

    func_l1 = sum_hc_l1 / total_hc
    func_l2 = sum_hc_l2 / total_hc
    func_l3 = sum_hc_l3 / total_hc

    lines.append(f"\n  FUNCTION-LEVEL RESULT (Σ(HC×Lx) / total_HC):")
    lines.append(f"    L1 = {sum_hc_l1:.1f} / {total_hc} = {func_l1:.1f}%")
    lines.append(f"    L2 = {sum_hc_l2:.1f} / {total_hc} = {func_l2:.1f}%")
    lines.append(f"    L3 = {sum_hc_l3:.1f} / {total_hc} = {func_l3:.1f}%")
    lines.append(f"    Adoption Gap = {func_l2:.1f} - {func_l3:.1f} = {func_l2 - func_l3:.1f}%")
    lines.append(f"    Capability Gap = {func_l1:.1f} - {func_l2:.1f} = {func_l1 - func_l2:.1f}%")
    lines.append(f"\n    Adoption gap savings: ${sum_adopt_savings:,.0f}/year")
    lines.append(f"    Full gap savings:     ${sum_full_savings:,.0f}/year")

    hs = org.human_system.get(func_name)
    if hs:
        lines.append(f"\n    Human System: proficiency={hs.ai_proficiency} readiness={hs.change_readiness} "
                     f"trust={hs.trust_level} → effective_multiplier={hs.effective_multiplier:.3f}")
        lines.append(f"    (This means only {hs.effective_multiplier*100:.1f}% of adoption gap is practically closeable without human system intervention)")

    return "\n".join(lines), func_l1, func_l2, func_l3, total_hc


def trace_org_aggregation(func_results):
    """Trace how function-level metrics aggregate to org level."""
    lines = []
    total_hc = sum(r[4] for r in func_results)

    lines.append(f"\n{'='*90}")
    lines.append(f"  ORGANIZATION: InsureCo")
    lines.append(f"  Functions: {len(func_results)} | Total HC: {total_hc}")
    lines.append(f"{'='*90}")

    lines.append(f"\n  FUNCTION CONTRIBUTIONS (headcount-weighted):")
    lines.append(f"  {'Function':<15} {'HC':>6} {'Weight':>7} {'L1':>6} {'L2':>6} {'L3':>6}  {'HC×L1':>10} {'HC×L2':>10} {'HC×L3':>10}")
    lines.append(f"  {'─'*82}")

    sum_hc_l1 = sum_hc_l2 = sum_hc_l3 = 0

    for name, l1, l2, l3, hc in func_results:
        weight = hc / total_hc * 100
        hcl1 = l1 * hc
        hcl2 = l2 * hc
        hcl3 = l3 * hc
        sum_hc_l1 += hcl1
        sum_hc_l2 += hcl2
        sum_hc_l3 += hcl3
        lines.append(f"  {name:<15} {hc:>6} {weight:>5.1f}%"
                     f"  {l1:>5.1f} {l2:>5.1f} {l3:>5.1f}"
                     f"  {hcl1:>10.1f} {hcl2:>10.1f} {hcl3:>10.1f}")

    lines.append(f"  {'─'*82}")

    org_l1 = sum_hc_l1 / total_hc
    org_l2 = sum_hc_l2 / total_hc
    org_l3 = sum_hc_l3 / total_hc

    lines.append(f"\n  ORG-LEVEL RESULT:")
    lines.append(f"    L1 = {sum_hc_l1:.1f} / {total_hc} = {org_l1:.1f}%  ← This is the 56.4%")
    lines.append(f"    L2 = {sum_hc_l2:.1f} / {total_hc} = {org_l2:.1f}%  ← This is the 51.3%")
    lines.append(f"    L3 = {sum_hc_l3:.1f} / {total_hc} = {org_l3:.1f}%  ← This is the 9.5%")
    lines.append(f"")
    lines.append(f"    Adoption Gap  = L2 - L3 = {org_l2:.1f}% - {org_l3:.1f}% = {org_l2-org_l3:.1f}%")
    lines.append(f"    Capability Gap = L1 - L2 = {org_l1:.1f}% - {org_l2:.1f}% = {org_l1-org_l2:.1f}%")
    lines.append(f"    Total Gap     = L1 - L3 = {org_l1:.1f}% - {org_l3:.1f}% = {org_l1-org_l3:.1f}%")

    return "\n".join(lines)


def trace_category_distribution(org):
    """Show why L1 isn't 100% — task category distribution limits the ceiling."""
    lines = []
    lines.append(f"\n{'='*90}")
    lines.append(f"  WHY ISN'T L1 = 100%? (Task Category Distribution)")
    lines.append(f"{'='*90}")
    lines.append(f"")
    lines.append(f"  The Etter ceiling is NOT 100% because work is distributed across 6 task categories,")
    lines.append(f"  each with a different automation potential:")
    lines.append(f"")
    lines.append(f"  {'Category':<18} {'Potential':>10} {'Description'}")
    lines.append(f"  {'─'*75}")
    for cat, pct in sorted(CATEGORY_AUTOMATION_POTENTIAL.items(), key=lambda x: -x[1]):
        desc = {
            "directive": "Rules-based, deterministic → fully automatable",
            "feedback_loop": "Refinement-based → highly automatable",
            "task_iteration": "Continuous adjustment cycles → partially automatable",
            "validation": "QA/compliance verification → AI-assisted",
            "learning": "Knowledge acquisition → AI-assisted",
            "negligibility": "Creative, strategic, relationship → human-only",
        }.get(cat, "")
        lines.append(f"  {cat:<18} {pct:>8.0f}%   {desc}")
    lines.append(f"  {'─'*75}")

    # Count tasks by category
    cat_counts = defaultdict(lambda: {"count": 0, "effort": 0.0})
    for t in org.tasks.values():
        cat_counts[t.category]["count"] += 1
        cat_counts[t.category]["effort"] += t.effort_hours_month

    total_effort = sum(v["effort"] for v in cat_counts.values())
    total_tasks = sum(v["count"] for v in cat_counts.values())

    lines.append(f"\n  InsureCo's actual task distribution:")
    lines.append(f"  {'Category':<18} {'Tasks':>6} {'% Tasks':>8} {'Effort':>8} {'% Effort':>9} {'Potential':>10} {'Weighted':>9}")
    lines.append(f"  {'─'*75}")

    weighted_potential = 0
    for cat in ["directive", "feedback_loop", "task_iteration", "learning", "validation", "negligibility"]:
        v = cat_counts[cat]
        pct_tasks = v["count"] / total_tasks * 100
        pct_effort = v["effort"] / total_effort * 100
        potential = CATEGORY_AUTOMATION_POTENTIAL[cat]
        weighted = pct_effort / 100 * potential
        weighted_potential += weighted
        lines.append(f"  {cat:<18} {v['count']:>6} {pct_tasks:>7.1f}% {v['effort']:>7.0f}h {pct_effort:>8.1f}% {potential:>8.0f}%  {weighted:>8.1f}%")

    lines.append(f"  {'─'*75}")
    lines.append(f"  {'TOTAL':<18} {total_tasks:>6} {'100%':>8} {total_effort:>7.0f}h {'100.0%':>9} {'':>10} {weighted_potential:>8.1f}%")
    lines.append(f"")
    lines.append(f"  If ALL tasks had matching tools and full adoption, the org-level average would be")
    lines.append(f"  ~{weighted_potential:.1f}%. But compliance mandates and tool coverage gaps reduce this further.")

    return "\n".join(lines)


def trace_why_adoption_gap_dominates(org):
    """Explain why 88% of opportunity is in the adoption gap."""
    lines = []
    lines.append(f"\n{'='*90}")
    lines.append(f"  WHY IS 88% OF OPPORTUNITY IN THE ADOPTION GAP?")
    lines.append(f"{'='*90}")
    lines.append(f"")
    lines.append(f"  The tech stack covers MOST task categories that Etter identifies as automatable.")
    lines.append(f"  The gap is NOT missing tools — it's missing adoption.")
    lines.append(f"")
    lines.append(f"  Tool Coverage Analysis:")
    lines.append(f"  {'Tool':<22} {'Deployed To':<25} {'Categories':<40} {'Adoption':>8}")
    lines.append(f"  {'─'*100}")
    for tool in org.tools.values():
        lines.append(f"  {tool.tool_name:<22} {','.join(tool.deployed_to_functions):<25} "
                     f"{','.join(tool.task_categories_addressed):<40} {tool.current_adoption_pct:>6.0f}%")
    lines.append(f"  {'─'*100}")
    lines.append(f"")
    lines.append(f"  The tools ARE deployed. Microsoft Copilot covers ALL functions.")
    lines.append(f"  But adoption rates are 10-30% — meaning 70-90% of potential is unused.")
    lines.append(f"")
    lines.append(f"  This is the Adoption Gap = L2 - L3.")
    lines.append(f"  L2 says 'the tool CAN do this task'.")
    lines.append(f"  L3 says 'the tool IS doing this task at X% adoption'.")
    lines.append(f"  The difference is pure waste — licensed software sitting on the shelf.")
    lines.append(f"")
    lines.append(f"  KEY INSIGHT: Closing the adoption gap requires:")
    lines.append(f"    - Training (not procurement)")
    lines.append(f"    - Change management (not technology)")
    lines.append(f"    - Time (not money)")
    lines.append(f"  This is why it's 'free money' — the investment is already made.")

    return "\n".join(lines)


def main():
    """Generate the complete explainability trace."""
    data_dir = "/mnt/user-data/outputs/synthetic_data"
    output_dir = "/mnt/user-data/outputs/stage0_results"

    print("Loading data...")
    org = load_organization(data_dir)

    # Classify all tasks first
    for task in org.tasks.values():
        wl = org.workloads[task.workload_id]
        role = org.roles[wl.role_id]
        classify_task(task, org.tools, role.function)

    report = []

    # ============================================================
    # SECTION 1: Category Distribution (why L1 isn't 100%)
    # ============================================================
    report.append(trace_category_distribution(org))

    # ============================================================
    # SECTION 2: Deep Dive — One Task (the atomic trace)
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  DEEP DIVE: TRACING ONE TASK END-TO-END")
    report.append(f"{'='*90}")
    report.append(f"  Let's follow one task through the entire computation.")

    # Pick a representative task — a directive task with a matching tool
    sample_task = None
    for t in org.tasks.values():
        if t.category == "directive" and t.automatable_by_tool and t.l2_achievable > 0:
            sample_task = t
            break
    if sample_task:
        wl = org.workloads[sample_task.workload_id]
        role = org.roles[wl.role_id]
        report.append(trace_single_task(sample_task, org.tools, role.function, role.role_name))

    # Also trace a compliance-mandated task
    report.append(f"\n  Now a COMPLIANCE-MANDATED task (ceiling is capped):")
    for t in org.tasks.values():
        if t.compliance_mandated_human and t.category != "negligibility":
            wl = org.workloads[t.workload_id]
            role = org.roles[wl.role_id]
            report.append(trace_single_task(t, org.tools, role.function, role.role_name))
            break

    # And a task with no matching tool
    report.append(f"\n  Now a task with NO matching tool (capability gap):")
    for t in org.tasks.values():
        if t.l2_achievable == 0 and t.l1_etter_potential > 20:
            wl = org.workloads[t.workload_id]
            role = org.roles[wl.role_id]
            report.append(trace_single_task(t, org.tools, role.function, role.role_name))
            break

    # ============================================================
    # SECTION 3: Workload Aggregation Example
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  AGGREGATION LEVEL 1: Tasks → Workload")
    report.append(f"{'='*90}")

    # Pick a workload from Claims Intake Specialist (highest opportunity)
    for wl_id in org.workloads_by_role.get("CL-001", [])[:1]:
        wl = org.workloads[wl_id]
        tasks = [org.tasks[tid] for tid in org.tasks_by_workload.get(wl_id, [])]
        report.append(trace_workload_aggregation(wl, tasks, org))

    # ============================================================
    # SECTION 4: Role Aggregation Example
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  AGGREGATION LEVEL 2: Workloads → Role")
    report.append(f"{'='*90}")

    role = org.roles["CL-001"]
    workloads = [org.workloads[wid] for wid in org.workloads_by_role.get("CL-001", [])]
    report.append(trace_role_aggregation(role, workloads, org))

    # ============================================================
    # SECTION 5: Function Aggregation (all 4 functions)
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  AGGREGATION LEVEL 3: Roles → Function")
    report.append(f"{'='*90}")

    func_summaries = []
    for func_name in sorted(org.roles_by_function.keys()):
        role_ids = org.roles_by_function[func_name]
        func_roles = [org.roles[rid] for rid in role_ids]
        text, l1, l2, l3, hc = trace_function_aggregation(func_name, func_roles, org)
        report.append(text)
        func_summaries.append((func_name, l1, l2, l3, hc))

    # ============================================================
    # SECTION 6: Org Aggregation (the final number)
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  AGGREGATION LEVEL 4: Functions → Organization")
    report.append(f"{'='*90}")
    report.append(trace_org_aggregation(func_summaries))

    # ============================================================
    # SECTION 7: Why Adoption Gap Dominates
    # ============================================================
    report.append(trace_why_adoption_gap_dominates(org))

    # ============================================================
    # SECTION 8: The Complete Provenance Chain
    # ============================================================
    report.append(f"\n{'='*90}")
    report.append(f"  THE COMPLETE PROVENANCE CHAIN")
    report.append(f"{'='*90}")
    report.append(f"""
  Every number in the Stage 0 output can be traced through this chain:

  1. TASK LEVEL (581 tasks)
     Each task has a CATEGORY (from Etter's 6-category classification).
     Category determines L1 potential: directive=90%, feedback_loop=85%, ...
     L1 is CAPPED at 5% if compliance_mandated_human=True (87 tasks).

  2. TOOL MATCHING (5 tools × 581 tasks)
     For each task, check: is there a tool deployed to this function
     that addresses this task's category AND is named in the task's
     automatable_by_tool field?
     YES → L2 = L1 (tool can do it)
     NO  → L2 = 0  (no matching tool)

  3. ADOPTION FILTER (per tool)
     L3 = L2 × (tool.current_adoption_pct / 100)
     Copilot at 15% adoption → L3 = L2 × 0.15
     UiPath at 20% adoption → L3 = L2 × 0.20

  4. GAPS (per task)
     Adoption Gap  = L2 - L3 (tool is there, not used)
     Capability Gap = L1 - L2 (no tool, need procurement)

  5. HOURS (per task)
     freed_hours = effort_hours × gap_pct / 100

  6. AGGREGATION: tasks → workloads → roles → functions → org
     At EVERY level: effort-weighted average for percentages,
                     headcount-weighted average across roles,
                     simple sum for hours and dollars.

  7. FINANCIAL TRANSLATION
     FTEs freed = freed_hours / 160 (hours per month)
     Savings = FTEs × avg_salary

  This chain is DETERMINISTIC. Same inputs → same outputs.
  Every number is auditable. No black boxes.
""")

    # Write report
    full_report = "\n".join(report)
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "stage0_explainability_trace.txt"), 'w') as f:
        f.write(full_report)

    print(full_report)
    print(f"\n  Report saved to {output_dir}/stage0_explainability_trace.txt")


if __name__ == "__main__":
    main()
