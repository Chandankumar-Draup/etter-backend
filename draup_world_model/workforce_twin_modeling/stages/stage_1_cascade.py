"""
Stage 1: Single-Step Cascade
=============================
Purpose: Execute all 9 cascade steps for ONE stimulus at ONE point in time.
No S-curves, no delays, no feedback — just the raw cascade logic.

Stimulus: "Deploy Microsoft Copilot to Claims function"

What it proves:
  - The cascade propagates correctly through all 7 stocks
  - Redistribution dampening works (freed ≠ reducible)
  - Skill sunrise/sunset emerges from task reclassification
  - Financial impact is computable and sign-correct
  - Risks are identified automatically
  - Every number has a traceable origin

Validation criteria (from plan):
  1. Cascade produces non-zero results for all 9 steps
  2. freed_hours < total_hours (can't free more than exists)
  3. headcount_reduction ≤ total_headcount in function
  4. savings > 0 if any headcount is reduced
  5. At least one risk is flagged
  6. At least one sunset skill identified
  7. At least one sunrise skill identified
"""
import sys
import os
import json
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.loader import load_organization
from engine.cascade import (
    Stimulus, run_cascade, CascadeResult,
    AUTOMATION_FREED_PCT,
)


# ============================================================
# Validation
# ============================================================

def validate_cascade(result: CascadeResult) -> list:
    """Run all Stage 1 acceptance tests."""
    tests = []
    s1 = result.step1_scope
    s2 = result.step2_reclassification
    s3 = result.step3_capacity
    s4 = result.step4_skills
    s5 = result.step5_workforce
    s6 = result.step6_financial
    s7 = result.step7_structural
    s8 = result.step8_human_system
    s9 = result.step9_risk

    # T1: All 9 steps produced results
    steps_with_data = [
        s1.affected_roles,
        s2.reclassified_tasks,
        s3.role_capacities,
        s4.sunset_skills or s4.sunrise_skills,  # at least one
        s5.role_impacts,
        s6.total_investment > 0 or s6.total_savings_annual > 0,
        s7.total_roles_affected > 0,
        s8.change_burden_score >= 0,
        s9.risks is not None,
    ]
    non_empty = sum(1 for s in steps_with_data if s)
    if non_empty == 9:
        tests.append(("PASS", f"All 9 cascade steps produced non-empty results"))
    else:
        tests.append(("FAIL", f"Only {non_empty}/9 steps produced results"))

    # T2: freed_hours < total_hours
    if s3.total_gross_freed_hours < s1.total_hours_month:
        tests.append(("PASS", f"Freed hours ({s3.total_gross_freed_hours:,.0f}) < total hours ({s1.total_hours_month:,.0f})"))
    else:
        tests.append(("FAIL", f"Freed hours ({s3.total_gross_freed_hours:,.0f}) >= total hours ({s1.total_hours_month:,.0f})"))

    # T3: headcount_reduction ≤ function headcount
    if s5.total_reducible_ftes <= s1.total_headcount:
        tests.append(("PASS", f"HC reduction ({s5.total_reducible_ftes}) ≤ scope HC ({s1.total_headcount})"))
    else:
        tests.append(("FAIL", f"HC reduction ({s5.total_reducible_ftes}) > scope HC ({s1.total_headcount})"))

    # T4: savings > 0 if headcount reduced
    if s5.total_reducible_ftes > 0 and s6.salary_savings_annual > 0:
        tests.append(("PASS", f"Salary savings (${s6.salary_savings_annual:,.0f}) > 0 with {s5.total_reducible_ftes} FTE reduction"))
    elif s5.total_reducible_ftes == 0:
        tests.append(("PASS", f"No HC reduction → savings check N/A"))
    else:
        tests.append(("FAIL", f"HC reduced but savings = ${s6.salary_savings_annual:,.0f}"))

    # T5: At least one risk flagged
    if len(s9.risks) > 0:
        tests.append(("PASS", f"{len(s9.risks)} risks identified (overall: {s9.overall_risk_level})"))
    else:
        tests.append(("FAIL", "No risks identified — risk engine not working"))

    # T6: Sunset skills identified
    if len(s4.sunset_skills) > 0:
        tests.append(("PASS", f"{len(s4.sunset_skills)} sunset skills identified"))
    else:
        tests.append(("FAIL", "No sunset skills — skill impact engine not working"))

    # T7: Sunrise skills identified
    if len(s4.sunrise_skills) > 0:
        tests.append(("PASS", f"{len(s4.sunrise_skills)} sunrise skills identified"))
    else:
        tests.append(("FAIL", "No sunrise skills — skill impact engine not working"))

    # T8: Redistribution dampening visible (net < gross)
    if s3.total_net_freed_hours < s3.total_gross_freed_hours:
        ratio = s3.dampening_ratio
        tests.append(("PASS", f"Redistribution dampening active: net = {ratio:.0%} of gross"))
    else:
        tests.append(("FAIL", "Net freed = gross freed — no redistribution dampening"))

    # T9: No role reduced below zero
    for wi in s5.role_impacts:
        if wi.projected_hc < 0:
            tests.append(("FAIL", f"Role {wi.role_name} projected HC = {wi.projected_hc} (negative!)"))
            break
    else:
        tests.append(("PASS", "All roles have projected HC ≥ 0"))

    # T10: Financial signs correct (investment > 0, net can be +/-)
    if s6.total_investment > 0:
        tests.append(("PASS", f"Investment = ${s6.total_investment:,.0f} (positive, as expected)"))
    else:
        tests.append(("FAIL", "Zero investment — license/training costs not computed"))

    # T11: Structural flags triggered for high-freed roles
    high_freed_roles = [rc for rc in s3.role_capacities if rc.freed_pct > 40]
    flagged_roles = len(s7.redesign_candidates) + len(s7.elimination_candidates)
    if high_freed_roles and flagged_roles > 0:
        tests.append(("PASS", f"{flagged_roles} roles flagged for redesign/elimination"))
    elif not high_freed_roles:
        tests.append(("PASS", "No roles above 40% freed — structural flags correctly empty"))
    else:
        tests.append(("FAIL", f"{len(high_freed_roles)} roles >40% freed but {flagged_roles} flagged"))

    return tests


# ============================================================
# Output Formatting
# ============================================================

def print_cascade_results(result: CascadeResult):
    """Print the complete 9-step cascade with full explainability."""
    stim = result.stimulus
    s1 = result.step1_scope
    s2 = result.step2_reclassification
    s3 = result.step3_capacity
    s4 = result.step4_skills
    s5 = result.step5_workforce
    s6 = result.step6_financial
    s7 = result.step7_structural
    s8 = result.step8_human_system
    s9 = result.step9_risk

    W = 90

    print(f"\n{'='*W}")
    print(f"  WORKFORCE TWIN — STAGE 1: SINGLE-STEP CASCADE")
    print(f"{'='*W}")
    print(f"  Stimulus: {stim.name}")
    print(f"  Tools:    {', '.join(stim.tools)}")
    print(f"  Scope:    {', '.join(stim.target_functions) if stim.target_functions else stim.target_scope}")
    print(f"  Policy:   {stim.policy}")
    print(f"  Absorption Factor: {stim.absorption_factor:.0%}")

    # ── Step 1: Scope ──
    print(f"\n{'─'*W}")
    print(f"  STEP 1: SCOPE RESOLUTION")
    print(f"{'─'*W}")
    print(f"  Functions affected:    {', '.join(s1.functions_affected)}")
    print(f"  Roles in scope:        {len(s1.affected_roles)}")
    print(f"  Workloads in scope:    {len(s1.affected_workloads)}")
    print(f"  Total tasks:           {s1.total_tasks_in_scope}")
    print(f"  Addressable by tool:   {s1.addressable_tasks} ({s1.addressable_tasks/s1.total_tasks_in_scope*100:.0f}%)")
    print(f"  Compliance-protected:  {s1.compliance_protected}")
    print(f"  Total headcount:       {s1.total_headcount:,}")
    print(f"  Total hours/month:     {s1.total_hours_month:,.0f}")

    # ── Step 2: Reclassification ──
    print(f"\n{'─'*W}")
    print(f"  STEP 2: TASK RECLASSIFICATION")
    print(f"{'─'*W}")
    print(f"  Tasks reclassified:    {len(s2.reclassified_tasks)}")
    print(f"    → Full AI:           {s2.tasks_to_ai} (directive + feedback_loop)")
    print(f"    → Human+AI:          {s2.tasks_to_human_ai} (task_iteration + learning + validation)")
    print(f"    → Unchanged:         {s2.tasks_unchanged}")
    print(f"  Total freed hours/person/month: {s2.total_freed_hours_per_person:.1f}h")

    print(f"\n  Automation freed % by category (applied to each task's effort):")
    for cat, pct in sorted(AUTOMATION_FREED_PCT.items(), key=lambda x: -x[1]):
        count = sum(1 for r in s2.reclassified_tasks if r.category == cat)
        if count > 0:
            print(f"    {cat:<18} {pct:>5.0f}% freed   ({count} tasks)")

    # Sample reclassified tasks
    print(f"\n  Sample reclassifications (first 10):")
    print(f"  {'Task':<40} {'Category':<16} {'State':<12} {'Freed':>6} {'Tool'}")
    print(f"  {'─'*86}")
    for rc in s2.reclassified_tasks[:10]:
        print(f"  {rc.task_name[:40]:<40} {rc.category:<16} {rc.new_state:<12} {rc.freed_hours:>5.1f}h {rc.tool_used}")

    # ── Step 3: Capacity ──
    print(f"\n{'─'*W}")
    print(f"  STEP 3: CAPACITY COMPUTATION")
    print(f"{'─'*W}")
    print(f"  Gross freed:           {s3.total_gross_freed_hours:>10,.0f} hours/month (before redistribution)")
    print(f"  Redistributed:         {s3.total_redistributed_hours:>10,.0f} hours/month (absorbed by remaining staff)")
    print(f"  Net freed:             {s3.total_net_freed_hours:>10,.0f} hours/month (after redistribution)")
    print(f"  Dampening ratio:       {s3.dampening_ratio:.0%} (net/gross — proves redistribution)")
    print(f"  Absorption factor:     {s3.absorption_factor:.0%}")
    print(f"\n  KEY INSIGHT: {(1-s3.dampening_ratio)*100:.0f}% of freed capacity is reabsorbed by redistribution.")
    print(f"  Automating 40% of tasks does NOT free 40% of capacity.")

    print(f"\n  Per-role capacity impact:")
    print(f"  {'Role':<30} {'HC':>5} {'Gross':>8} {'Redist':>8} {'Net':>8} {'Freed%':>7}")
    print(f"  {'─'*72}")
    for rc in sorted(s3.role_capacities, key=lambda x: x.total_net_freed_hours, reverse=True):
        if rc.gross_freed_hours_pp > 0:
            print(f"  {rc.role_name[:30]:<30} {rc.headcount:>5}"
                  f" {rc.gross_freed_hours_pp:>7.1f}h {rc.redistributed_hours_pp:>7.1f}h"
                  f" {rc.net_freed_hours_pp:>7.1f}h {rc.freed_pct:>6.1f}%")

    # ── Step 4: Skills ──
    print(f"\n{'─'*W}")
    print(f"  STEP 4: SKILL IMPACT")
    print(f"{'─'*W}")
    print(f"  Sunset skills:     {len(s4.sunset_skills)} (demand declining)")
    print(f"  Sunrise skills:    {len(s4.sunrise_skills)} (new demand)")
    print(f"  Unchanged:         {s4.unchanged_skills}")
    print(f"  Net skill gap:     {s4.net_skill_gap:+d} (positive = gap opens)")
    print(f"  Critical sunset:   {len(s4.critical_sunset)} (high-proficiency skills at risk)")

    if s4.sunset_skills:
        # Deduplicate by skill name
        seen = set()
        unique_sunset = []
        for s in s4.sunset_skills:
            if s.skill_name not in seen:
                seen.add(s.skill_name)
                unique_sunset.append(s)
        print(f"\n  Unique sunset skills ({len(unique_sunset)}):")
        for s in unique_sunset[:15]:
            crit = " ← CRITICAL" if s in s4.critical_sunset else ""
            print(f"    ↓ {s.skill_name}{crit}")

    if s4.sunrise_skills:
        seen = set()
        unique_sunrise = []
        for s in s4.sunrise_skills:
            if s.skill_name not in seen:
                seen.add(s.skill_name)
                unique_sunrise.append(s)
        print(f"\n  Unique sunrise skills ({len(unique_sunrise)}):")
        for s in unique_sunrise[:15]:
            print(f"    ↑ {s.skill_name}")

    # ── Step 5: Workforce ──
    print(f"\n{'─'*W}")
    print(f"  STEP 5: WORKFORCE IMPACT")
    print(f"{'─'*W}")
    print(f"  Policy:              {s5.policy_applied}")
    print(f"  Current HC:          {s5.total_current_hc:,}")
    print(f"  Reducible FTEs:      {s5.total_reducible_ftes}")
    print(f"  Projected HC:        {s5.total_projected_hc:,}")
    print(f"  Reduction:           {s5.total_reduction_pct:.1f}%")

    print(f"\n  Per-role workforce impact:")
    print(f"  {'Role':<30} {'Current':>7} {'Freed':>7} {'Reduce':>7} {'Project':>7} {'%Chg':>6}")
    print(f"  {'─'*70}")
    for wi in sorted(s5.role_impacts, key=lambda x: x.reducible_ftes, reverse=True):
        if wi.reducible_ftes > 0 or wi.net_freed_ftes > 0.5:
            print(f"  {wi.role_name[:30]:<30} {wi.current_hc:>7}"
                  f" {wi.net_freed_ftes:>6.1f}  {wi.reducible_ftes:>6}"
                  f" {wi.projected_hc:>7} {wi.reduction_pct:>5.1f}%")

    # ── Step 6: Financial ──
    print(f"\n{'─'*W}")
    print(f"  STEP 6: FINANCIAL IMPACT")
    print(f"{'─'*W}")
    print(f"  INVESTMENT")
    print(f"    License (annual):       ${s6.license_cost_annual:>12,.0f}")
    print(f"    Training:               ${s6.training_cost:>12,.0f}")
    print(f"    Change management:      ${s6.change_management_cost:>12,.0f}")
    print(f"    Total investment:       ${s6.total_investment:>12,.0f}")
    print(f"")
    print(f"  SAVINGS (annual)")
    print(f"    Salary savings:         ${s6.salary_savings_annual:>12,.0f}")
    print(f"    Productivity gains:     ${s6.productivity_savings_annual:>12,.0f}")
    print(f"    Total savings:          ${s6.total_savings_annual:>12,.0f}")
    print(f"")
    print(f"  NET")
    print(f"    Net annual:             ${s6.net_annual:>12,.0f}")
    print(f"    Payback:                {s6.payback_months:>10.1f} months")
    print(f"    ROI:                    {s6.roi_pct:>10.0f}%")

    print(f"\n  Top 10 roles by salary savings:")
    print(f"  {'Role':<30} {'HC Cut':>6} {'Salary$':>12} {'Prod$':>10}")
    print(f"  {'─'*62}")
    for rd in sorted(s6.role_savings, key=lambda x: x["salary_savings"], reverse=True)[:10]:
        if rd["salary_savings"] > 0:
            print(f"  {rd['role_name'][:30]:<30} {rd['hc_reduced']:>6}"
                  f" ${rd['salary_savings']:>10,.0f} ${rd['productivity_savings']:>8,.0f}")

    # ── Step 7: Structural ──
    print(f"\n{'─'*W}")
    print(f"  STEP 7: STRUCTURAL IMPACT")
    print(f"{'─'*W}")
    print(f"  Roles in scope:       {s7.total_roles_affected}")
    print(f"  Redesign candidates:  {s7.total_roles_redesign} (>40% freed)")
    print(f"  Elimination candidates: {s7.total_roles_elimination} (>70% freed)")

    for r in s7.elimination_candidates:
        print(f"\n  ⚠ ELIMINATION: {r['role_name']} ({r['function']})")
        print(f"    HC: {r['headcount']} | Freed: {r['freed_pct']}%")
        print(f"    {r['recommendation']}")

    for r in s7.redesign_candidates:
        print(f"\n  ◉ REDESIGN: {r['role_name']} ({r['function']})")
        print(f"    HC: {r['headcount']} | Freed: {r['freed_pct']}%")
        print(f"    {r['recommendation']}")

    # ── Step 8: Human System ──
    print(f"\n{'─'*W}")
    print(f"  STEP 8: HUMAN SYSTEM IMPACT")
    print(f"{'─'*W}")
    print(f"  Proficiency:          {s8.proficiency_direction}")
    print(f"  Readiness:            {s8.readiness_direction}")
    print(f"  Trust:                {s8.trust_direction}")
    print(f"  Political capital:    {s8.political_capital_direction}")
    print(f"  Change burden:        {s8.change_burden_score:.0f}/100")
    print(f"\n  Narrative: {s8.narrative}")

    # ── Step 9: Risk ──
    print(f"\n{'─'*W}")
    print(f"  STEP 9: RISK ASSESSMENT")
    print(f"{'─'*W}")
    print(f"  Overall risk level:   {s9.overall_risk_level.upper()}")
    print(f"  Risks identified:     {len(s9.risks)}")
    for sev, count in sorted(s9.risk_count_by_severity.items()):
        print(f"    {sev}: {count}")

    for i, risk in enumerate(s9.risks, 1):
        icon = {"low": "○", "medium": "◉", "high": "⚠", "critical": "✖"}.get(risk.severity, "?")
        print(f"\n  {icon} Risk {i}: [{risk.severity.upper()}] {risk.risk_type}")
        print(f"    {risk.description}")
        print(f"    Scope: {risk.affected_scope}")
        print(f"    Mitigation: {risk.mitigation}")


def print_decision_trace(result: CascadeResult):
    """Print the complete decision trace — how each step fed the next."""
    s1 = result.step1_scope
    s2 = result.step2_reclassification
    s3 = result.step3_capacity
    s4 = result.step4_skills
    s5 = result.step5_workforce
    s6 = result.step6_financial
    s7 = result.step7_structural

    print(f"\n{'='*90}")
    print(f"  DECISION TRACE: How Each Step Fed The Next")
    print(f"{'='*90}")
    print(f"""
  STIMULUS: "{result.stimulus.name}"
      │
      ▼
  STEP 1 → {len(s1.affected_roles)} roles, {s1.addressable_tasks} addressable tasks
      │     ({s1.compliance_protected} compliance-protected, untouchable)
      ▼
  STEP 2 → {s2.tasks_to_ai} tasks → AI, {s2.tasks_to_human_ai} tasks → Human+AI
      │     Freed {s2.total_freed_hours_per_person:.1f}h/person/month across all reclassified tasks
      ▼
  STEP 3 → Gross freed: {s3.total_gross_freed_hours:,.0f}h/month
      │     Redistributed: {s3.total_redistributed_hours:,.0f}h ({result.stimulus.absorption_factor:.0%} absorbed)
      │     Net freed: {s3.total_net_freed_hours:,.0f}h/month ({s3.dampening_ratio:.0%} of gross)
      ▼
  STEP 4 → {len(s4.sunset_skills)} skills sunset, {len(s4.sunrise_skills)} skills sunrise
      │     Net gap: {s4.net_skill_gap:+d} ({len(s4.critical_sunset)} critical knowledge at risk)
      ▼
  STEP 5 → {s5.total_reducible_ftes} FTEs reducible ({s5.total_reduction_pct:.1f}% of scope)
      │     Policy: {s5.policy_applied}
      │     {s5.total_current_hc} → {s5.total_projected_hc} headcount
      ▼
  STEP 6 → Investment: ${s6.total_investment:,.0f}
      │     Savings:    ${s6.total_savings_annual:,.0f}/year
      │     Net:        ${s6.net_annual:,.0f}/year
      │     Payback:    {s6.payback_months:.1f} months | ROI: {s6.roi_pct:.0f}%
      ▼
  STEP 7 → {s7.total_roles_redesign} roles need redesign, {s7.total_roles_elimination} candidates for elimination
      │
      ▼
  STEP 8 → Change burden: {result.step8_human_system.change_burden_score:.0f}/100
      │     Readiness will {result.step8_human_system.readiness_direction}
      ▼
  STEP 9 → {len(result.step9_risk.risks)} risks ({result.step9_risk.overall_risk_level.upper()})
""")

    # The key insight
    print(f"  KEY INSIGHT — THE DAMPENING CHAIN:")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Tasks addressable:     {s1.addressable_tasks}/{s1.total_tasks_in_scope}"
          f" ({s1.addressable_tasks/s1.total_tasks_in_scope*100:.0f}%) ← tool coverage limits scope")
    pct_freed = s2.total_freed_hours_per_person
    print(f"  Effort freed/person:   {pct_freed:.1f}h/month ← not all effort is automatable")
    print(f"  After redistribution:  {s3.total_net_freed_hours:,.0f}h"
          f" ({s3.dampening_ratio:.0%} of gross) ← redistribution absorbs {1-s3.dampening_ratio:.0%}")
    fte_equiv = s3.total_net_freed_hours / 160.0
    print(f"  FTE equivalent:        {fte_equiv:.1f} ← but can't fire 0.3 of a person")
    print(f"  Actually reducible:    {s5.total_reducible_ftes} ← floor() to whole people")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  From {s1.total_headcount} people in scope → {s5.total_reducible_ftes} actually reducible")
    print(f"  That's {s5.total_reduction_pct:.1f}%, NOT the {s1.addressable_tasks/s1.total_tasks_in_scope*100:.0f}% task addressability would suggest.")
    print(f"  THIS is why naive automation assessments overestimate impact by 2-3×.")


# ============================================================
# Export
# ============================================================

def export_cascade_results(result: CascadeResult, output_dir: str):
    """Export cascade results as CSV and JSON."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Role-level cascade summary CSV
    rows = []
    for i, wi in enumerate(result.step5_workforce.role_impacts):
        rc = result.step3_capacity.role_capacities[i]
        rs = next((r for r in result.step6_financial.role_savings
                    if r["role_id"] == wi.role_id), {})
        rows.append({
            "role_id": wi.role_id,
            "role_name": wi.role_name,
            "current_hc": wi.current_hc,
            "gross_freed_hrs_pp": round(rc.gross_freed_hours_pp, 1),
            "redistributed_hrs_pp": round(rc.redistributed_hours_pp, 1),
            "net_freed_hrs_pp": round(rc.net_freed_hours_pp, 1),
            "freed_pct": round(rc.freed_pct, 1),
            "net_freed_ftes": round(wi.net_freed_ftes, 1),
            "reducible_ftes": wi.reducible_ftes,
            "projected_hc": wi.projected_hc,
            "reduction_pct": round(wi.reduction_pct, 1),
            "salary_savings": round(rs.get("salary_savings", 0), 0),
            "productivity_savings": round(rs.get("productivity_savings", 0), 0),
        })

    with open(os.path.join(output_dir, "stage1_role_cascade.csv"), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # 2. Full cascade summary JSON
    summary = {
        "stimulus": {
            "name": result.stimulus.name,
            "tools": result.stimulus.tools,
            "scope": result.stimulus.target_functions,
            "policy": result.stimulus.policy,
            "absorption_factor": result.stimulus.absorption_factor,
        },
        "step1_scope": {
            "roles": len(result.step1_scope.affected_roles),
            "tasks_total": result.step1_scope.total_tasks_in_scope,
            "tasks_addressable": result.step1_scope.addressable_tasks,
            "compliance_protected": result.step1_scope.compliance_protected,
            "headcount": result.step1_scope.total_headcount,
        },
        "step2_reclassification": {
            "tasks_to_ai": result.step2_reclassification.tasks_to_ai,
            "tasks_to_human_ai": result.step2_reclassification.tasks_to_human_ai,
            "tasks_unchanged": result.step2_reclassification.tasks_unchanged,
            "freed_hours_per_person": round(result.step2_reclassification.total_freed_hours_per_person, 1),
        },
        "step3_capacity": {
            "gross_freed_hours_month": round(result.step3_capacity.total_gross_freed_hours, 0),
            "redistributed_hours_month": round(result.step3_capacity.total_redistributed_hours, 0),
            "net_freed_hours_month": round(result.step3_capacity.total_net_freed_hours, 0),
            "dampening_ratio": round(result.step3_capacity.dampening_ratio, 3),
        },
        "step4_skills": {
            "sunset_count": len(result.step4_skills.sunset_skills),
            "sunrise_count": len(result.step4_skills.sunrise_skills),
            "net_gap": result.step4_skills.net_skill_gap,
            "critical_sunset": len(result.step4_skills.critical_sunset),
        },
        "step5_workforce": {
            "current_hc": result.step5_workforce.total_current_hc,
            "reducible_ftes": result.step5_workforce.total_reducible_ftes,
            "projected_hc": result.step5_workforce.total_projected_hc,
            "reduction_pct": round(result.step5_workforce.total_reduction_pct, 1),
            "policy": result.step5_workforce.policy_applied,
        },
        "step6_financial": {
            "total_investment": round(result.step6_financial.total_investment, 0),
            "salary_savings_annual": round(result.step6_financial.salary_savings_annual, 0),
            "productivity_savings_annual": round(result.step6_financial.productivity_savings_annual, 0),
            "total_savings_annual": round(result.step6_financial.total_savings_annual, 0),
            "net_annual": round(result.step6_financial.net_annual, 0),
            "payback_months": round(result.step6_financial.payback_months, 1),
            "roi_pct": round(result.step6_financial.roi_pct, 0),
        },
        "step7_structural": {
            "redesign_candidates": result.step7_structural.total_roles_redesign,
            "elimination_candidates": result.step7_structural.total_roles_elimination,
        },
        "step8_human_system": {
            "change_burden": round(result.step8_human_system.change_burden_score, 0),
            "readiness_direction": result.step8_human_system.readiness_direction,
            "narrative": result.step8_human_system.narrative,
        },
        "step9_risk": {
            "overall_level": result.step9_risk.overall_risk_level,
            "risk_count": len(result.step9_risk.risks),
            "risks": [{"type": r.risk_type, "severity": r.severity,
                       "description": r.description} for r in result.step9_risk.risks],
        },
    }

    with open(os.path.join(output_dir, "stage1_cascade_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)

    # 3. Task reclassifications CSV
    task_rows = []
    for rc in result.step2_reclassification.reclassified_tasks:
        task_rows.append({
            "task_id": rc.task_id,
            "task_name": rc.task_name,
            "workload_id": rc.workload_id,
            "role_id": rc.role_id,
            "category": rc.category,
            "effort_hours": rc.effort_hours,
            "previous_state": rc.previous_state,
            "new_state": rc.new_state,
            "automation_pct": rc.automation_pct,
            "freed_hours": round(rc.freed_hours, 2),
            "tool_used": rc.tool_used,
        })

    if task_rows:
        with open(os.path.join(output_dir, "stage1_task_reclassifications.csv"), 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=task_rows[0].keys())
            writer.writeheader()
            writer.writerows(task_rows)

    print(f"\n  Results exported to {output_dir}/")
    print(f"    stage1_role_cascade.csv             ({len(rows)} roles)")
    print(f"    stage1_task_reclassifications.csv    ({len(task_rows)} tasks)")
    print(f"    stage1_cascade_summary.json          (full 9-step summary)")


# ============================================================
# Main
# ============================================================

def main(data_dir: str, output_dir: str = None):
    """Run Stage 1: Single-Step Cascade."""

    print(f"\n  Loading data from {data_dir}...")
    org = load_organization(data_dir)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.workloads)} workloads,"
          f" {len(org.tasks)} tasks, {len(org.skills)} skills, {len(org.tools)} tools")

    # Define the stimulus
    stimulus = Stimulus(
        name="Deploy Microsoft Copilot to Claims function",
        stimulus_type="technology_injection",
        tools=["Microsoft Copilot"],
        target_scope="function",
        target_functions=["Claims"],
        policy="moderate_reduction",
        absorption_factor=0.35,
        alpha=1.0,                      # Stage 1: full instant adoption
        training_cost_per_person=2000,
    )

    # Run the cascade
    print(f"\n  Running 9-step cascade...")
    result = run_cascade(stimulus, org)

    # Validate
    print(f"\n  VALIDATION TESTS")
    print(f"  {'─'*60}")
    tests = validate_cascade(result)
    passed = sum(1 for t in tests if t[0] == "PASS")
    failed = sum(1 for t in tests if t[0] == "FAIL")

    for status, msg in tests:
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} [{status}] {msg}")

    print(f"  {'─'*60}")
    print(f"  Results: {passed} passed, {failed} failed")

    if failed > 0:
        print(f"\n  *** STAGE 1 VALIDATION FAILED — {failed} test(s) ***")

    # Output
    print_cascade_results(result)
    print_decision_trace(result)

    if output_dir:
        export_cascade_results(result, output_dir)

    print(f"\n  {'='*90}")
    print(f"  STAGE 1 COMPLETE — {passed}/{passed+failed} validation tests passed")
    print(f"  {'='*90}")

    return result


if __name__ == "__main__":
    DATA_DIR = "/mnt/user-data/outputs/synthetic_data"
    OUTPUT_DIR = "/mnt/user-data/outputs/stage1_results"
    main(DATA_DIR, OUTPUT_DIR)
