"""
Stage 0: Static Snapshot
========================
Purpose: Prove the data model works. Compute three-layer gap analysis.
No time dimension. No feedback loops. Just the raw organizational X-ray.

What it answers:
  - What's the Etter ceiling? (L1)
  - What's achievable with current tech? (L2)
  - What's actually automated today? (L3)
  - Where is the free money? (Adoption gap = L2 - L3)
  - Where do we need investment? (Capability gap = L1 - L2)
  - What are the top opportunities ranked by $?
"""
import sys
import os
import json
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workforce_twin_modeling.engine.loader import load_organization
from workforce_twin_modeling.engine.gap_engine import compute_snapshot


# ============================================================
# Validation Tests
# ============================================================

def validate_snapshot(org_data, result):
    """
    Run all Stage 0 acceptance tests.
    Returns (passed, failed) counts with details.
    """
    tests = []

    # Test 1: Adoption gap ≥ 0 for every task
    for func in result.functions:
        for role in func.roles:
            for wl in role.workloads:
                for task in wl.tasks:
                    if task.adoption_gap < -0.001:
                        tests.append(("FAIL", f"Task {task.task_id} adoption gap = {task.adoption_gap:.2f} (negative)"))
    if not any(t[0] == "FAIL" and "adoption gap" in t[1] for t in tests):
        tests.append(("PASS", "All adoption gaps ≥ 0"))

    # Test 2: Capability gap ≥ 0 for every task
    for func in result.functions:
        for role in func.roles:
            for wl in role.workloads:
                for task in wl.tasks:
                    if task.capability_gap < -0.001:
                        tests.append(("FAIL", f"Task {task.task_id} capability gap = {task.capability_gap:.2f} (negative)"))
    if not any(t[0] == "FAIL" and "capability gap" in t[1] for t in tests):
        tests.append(("PASS", "All capability gaps ≥ 0"))

    # Test 3: L1 ≥ L2 ≥ L3 for every task
    violation_count = 0
    for func in result.functions:
        for role in func.roles:
            for wl in role.workloads:
                for task in wl.tasks:
                    if task.l1 < task.l2 - 0.001 or task.l2 < task.l3 - 0.001:
                        violation_count += 1
    if violation_count == 0:
        tests.append(("PASS", "Layer ordering: L1 ≥ L2 ≥ L3 for all tasks"))
    else:
        tests.append(("FAIL", f"Layer ordering violated in {violation_count} tasks"))

    # Test 4: Aggregation consistency — org totals = sum of function totals
    func_hc_sum = sum(f.headcount for f in result.functions)
    func_cost_sum = sum(f.annual_cost for f in result.functions)
    func_adopt_sum = sum(f.adoption_gap_savings_annual for f in result.functions)

    if abs(result.headcount - func_hc_sum) < 1:
        tests.append(("PASS", f"HC aggregation: org={result.headcount} = Σfunctions={func_hc_sum}"))
    else:
        tests.append(("FAIL", f"HC mismatch: org={result.headcount} ≠ Σfunctions={func_hc_sum}"))

    if abs(result.annual_cost - func_cost_sum) < 1:
        tests.append(("PASS", f"Cost aggregation: ${result.annual_cost:,.0f} = Σfunctions"))
    else:
        tests.append(("FAIL", f"Cost mismatch: ${result.annual_cost:,.0f} ≠ ${func_cost_sum:,.0f}"))

    if abs(result.adoption_gap_savings_annual - func_adopt_sum) < 1:
        tests.append(("PASS", f"Savings aggregation: ${result.adoption_gap_savings_annual:,.0f} = Σfunctions"))
    else:
        tests.append(("FAIL", f"Savings mismatch"))

    # Test 5: Function aggregation = sum of role totals
    for func in result.functions:
        role_hc = sum(r.headcount for r in func.roles)
        if abs(func.headcount - role_hc) < 1:
            tests.append(("PASS", f"{func.function}: HC={func.headcount} = Σroles={role_hc}"))
        else:
            tests.append(("FAIL", f"{func.function}: HC={func.headcount} ≠ Σroles={role_hc}"))

    # Test 6: Top opportunities have positive value
    if result.top_roles_by_savings and result.top_roles_by_savings[0]["full_savings"] > 0:
        tests.append(("PASS", f"Top opportunity: {result.top_roles_by_savings[0]['role_name']} = ${result.top_roles_by_savings[0]['full_savings']:,.0f}"))
    else:
        tests.append(("FAIL", "No positive savings opportunities found"))

    # Test 7: Compliance tasks reduce ceiling
    compliance_total = result.compliance_tasks
    if compliance_total > 0:
        tests.append(("PASS", f"Compliance floor active: {compliance_total} tasks mandated human"))
    else:
        tests.append(("FAIL", "No compliance tasks found — floor not enforced"))

    # Test 8: Freed hours never exceed available hours
    for func in result.functions:
        for role in func.roles:
            total_available = role.headcount * 160.0  # hours/month
            total_monthly_effort = sum(w.total_effort_hours for w in role.workloads)
            freed_per_person = role.total_gap_hours_per_person
            if freed_per_person <= total_monthly_effort + 0.1:
                pass  # OK
            else:
                tests.append(("FAIL", f"{role.role_name}: freed {freed_per_person:.1f}h > available {total_monthly_effort:.1f}h"))
    # If no failures from this check
    if not any("freed" in t[1] and t[0] == "FAIL" for t in tests):
        tests.append(("PASS", "Freed hours ≤ available hours for all roles"))

    # Test 9: Adoption gap is the "free money" — verify it's material
    if result.adoption_gap_savings_annual > 0:
        pct_of_full = (result.adoption_gap_savings_annual / result.full_gap_savings_annual * 100) if result.full_gap_savings_annual > 0 else 0
        tests.append(("PASS", f"Adoption gap (free money) = ${result.adoption_gap_savings_annual:,.0f} ({pct_of_full:.0f}% of full potential)"))
    else:
        tests.append(("WARN", "Zero adoption gap savings — check tool deployment data"))

    return tests


# ============================================================
# Output Formatting
# ============================================================

def print_org_summary(result):
    """Print the executive summary."""
    print("\n" + "=" * 80)
    print(f"  WORKFORCE TWIN — STAGE 0: STATIC SNAPSHOT")
    print(f"  Organization: {result.org_name}")
    print("=" * 80)

    print(f"\n  ORGANIZATIONAL OVERVIEW")
    print(f"  {'─' * 60}")
    print(f"  Total Headcount:        {result.headcount:,}")
    print(f"  Annual Labor Cost:      ${result.annual_cost:,.0f}")
    print(f"  Total Tasks Analyzed:   {result.total_tasks:,}")
    print(f"  Compliance-Protected:   {result.compliance_tasks} tasks ({result.compliance_tasks/result.total_tasks*100:.0f}%)")
    print(f"  Avg Automation Score:   {result.avg_automation_score:.1f}%")
    print(f"  Avg Augmentation Score: {result.avg_augmentation_score:.1f}%")

    print(f"\n  THREE-LAYER GAP ANALYSIS")
    print(f"  {'─' * 60}")
    print(f"  L1 Etter Ceiling (theoretical):   {result.weighted_l1:.1f}%")
    print(f"  L2 Achievable (current tech):     {result.weighted_l2:.1f}%")
    print(f"  L3 Realized (actual today):        {result.weighted_l3:.1f}%")
    print(f"  {'─' * 60}")
    print(f"  Adoption Gap (L2-L3):              {result.weighted_l2 - result.weighted_l3:.1f}%  ← FREE MONEY")
    print(f"  Capability Gap (L1-L2):            {result.weighted_l1 - result.weighted_l2:.1f}%  ← needs investment")
    print(f"  Total Gap (L1-L3):                 {result.weighted_l1 - result.weighted_l3:.1f}%")

    print(f"\n  FINANCIAL OPPORTUNITY")
    print(f"  {'─' * 60}")
    print(f"  Adoption Gap Savings:   ${result.adoption_gap_savings_annual:,.0f}/year  ({result.adoption_gap_fte_equivalent:.0f} FTEs)")
    print(f"  Full Potential Savings:  ${result.full_gap_savings_annual:,.0f}/year")
    print(f"  {'─' * 60}")


def print_function_detail(result):
    """Print per-function breakdown."""
    print(f"\n  FUNCTION-LEVEL BREAKDOWN")
    print(f"  {'─' * 76}")
    print(f"  {'Function':<14} {'HC':>6} {'Cost':>12} {'L1':>6} {'L2':>6} {'L3':>6} {'Adopt$':>12} {'Full$':>12} {'Ready':>5}")
    print(f"  {'─' * 76}")
    for f in sorted(result.functions, key=lambda x: x.adoption_gap_savings_annual, reverse=True):
        print(f"  {f.function:<14} {f.headcount:>6,} ${f.annual_cost/1e6:>9.1f}M"
              f"  {f.weighted_l1:>5.1f} {f.weighted_l2:>5.1f} {f.weighted_l3:>5.1f}"
              f"  ${f.adoption_gap_savings_annual/1e6:>9.2f}M ${f.full_gap_savings_annual/1e6:>9.2f}M"
              f"  {f.change_readiness:>4.0f}")
    print(f"  {'─' * 76}")


def print_role_detail(result):
    """Print per-role detail for each function."""
    for func in result.functions:
        print(f"\n  {func.function.upper()} — ROLE DETAIL")
        print(f"  {'─' * 100}")
        print(f"  {'Role':<30} {'HC':>5} {'Auto%':>6} {'L1':>5} {'L2':>5} {'L3':>5}"
              f" {'AdoptGap':>10} {'FullGap':>10} {'Adopt$':>10} {'Redesign':>8}")
        print(f"  {'─' * 100}")
        for r in sorted(func.roles, key=lambda x: x.adoption_gap_savings_annual, reverse=True):
            adopt_gap_pct = r.weighted_l2 - r.weighted_l3
            total_gap_pct = r.weighted_l1 - r.weighted_l3
            print(f"  {r.role_name[:30]:<30} {r.headcount:>5} {r.automation_score:>5.1f}%"
                  f" {r.weighted_l1:>5.1f} {r.weighted_l2:>5.1f} {r.weighted_l3:>5.1f}"
                  f"  {adopt_gap_pct:>8.1f}%  {total_gap_pct:>8.1f}%"
                  f"  ${r.adoption_gap_savings_annual/1e3:>7.0f}K"
                  f"  {'  YES' if r.redesign_candidate else '   no':>8}")
        print(f"  {'─' * 100}")


def print_opportunities(result):
    """Print ranked opportunity tables."""
    print(f"\n  TOP 10 OPPORTUNITIES — BY ADOPTION GAP SAVINGS (FREE MONEY)")
    print(f"  {'─' * 80}")
    print(f"  {'Rank':>4} {'Role':<30} {'Function':<12} {'FTEs':>5} {'Savings':>12}")
    print(f"  {'─' * 80}")
    for i, opp in enumerate(result.top_roles_by_adoption_gap, 1):
        print(f"  {i:>4} {opp['role_name'][:30]:<30} {opp['function']:<12}"
              f" {opp['fte_freed']:>5.1f} ${opp['savings_annual']:>10,.0f}")

    print(f"\n  TOP 10 OPPORTUNITIES — BY FULL POTENTIAL SAVINGS")
    print(f"  {'─' * 80}")
    print(f"  {'Rank':>4} {'Role':<30} {'Function':<12} {'HC':>5} {'Savings':>12} {'Redesign':>8}")
    print(f"  {'─' * 80}")
    for i, opp in enumerate(result.top_roles_by_savings, 1):
        print(f"  {i:>4} {opp['role_name'][:30]:<30} {opp['function']:<12}"
              f" {opp['headcount']:>5} ${opp['full_savings']:>10,.0f}"
              f" {'  YES' if opp['redesign_candidate'] else '   no':>8}")


def export_results(result, output_dir):
    """Export results as CSV and JSON for downstream consumption."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Role-level summary CSV
    role_rows = []
    for func in result.functions:
        for r in func.roles:
            role_rows.append({
                "role_id": r.role_id,
                "role_name": r.role_name,
                "function": r.function,
                "sub_function": r.sub_function,
                "jfg": r.jfg,
                "management_level": r.management_level,
                "headcount": r.headcount,
                "avg_salary": r.avg_salary,
                "annual_cost": r.annual_cost,
                "automation_score": r.automation_score,
                "augmentation_score": r.augmentation_score,
                "l1_etter_ceiling": round(r.weighted_l1, 2),
                "l2_achievable": round(r.weighted_l2, 2),
                "l3_realized": round(r.weighted_l3, 2),
                "adoption_gap_pct": round(r.weighted_l2 - r.weighted_l3, 2),
                "capability_gap_pct": round(r.weighted_l1 - r.weighted_l2, 2),
                "total_gap_pct": round(r.weighted_l1 - r.weighted_l3, 2),
                "adoption_gap_hours": round(r.total_adoption_gap_hours, 1),
                "capability_gap_hours": round(r.total_capability_gap_hours, 1),
                "adoption_gap_savings_annual": round(r.adoption_gap_savings_annual, 0),
                "full_gap_savings_annual": round(r.full_gap_savings_annual, 0),
                "adoption_gap_fte": round(r.adoption_gap_fte_equivalent, 1),
                "compliance_tasks": r.compliance_tasks,
                "total_tasks": r.total_tasks,
                "redesign_candidate": r.redesign_candidate,
            })

    with open(os.path.join(output_dir, "stage0_role_gaps.csv"), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=role_rows[0].keys())
        writer.writeheader()
        writer.writerows(role_rows)

    # 2. Function-level summary CSV
    func_rows = []
    for f in result.functions:
        func_rows.append({
            "function": f.function,
            "headcount": f.headcount,
            "annual_cost": f.annual_cost,
            "avg_automation_score": round(f.avg_automation_score, 2),
            "l1_etter_ceiling": round(f.weighted_l1, 2),
            "l2_achievable": round(f.weighted_l2, 2),
            "l3_realized": round(f.weighted_l3, 2),
            "adoption_gap_pct": round(f.weighted_l2 - f.weighted_l3, 2),
            "capability_gap_pct": round(f.weighted_l1 - f.weighted_l2, 2),
            "adoption_gap_savings": round(f.adoption_gap_savings_annual, 0),
            "full_gap_savings": round(f.full_gap_savings_annual, 0),
            "adoption_gap_fte": round(f.adoption_gap_fte_equivalent, 1),
            "ai_proficiency": f.ai_proficiency,
            "change_readiness": f.change_readiness,
            "trust_level": f.trust_level,
            "effective_multiplier": round(f.effective_multiplier, 3),
            "compliance_tasks": f.compliance_tasks,
            "total_tasks": f.total_tasks,
        })

    with open(os.path.join(output_dir, "stage0_function_gaps.csv"), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=func_rows[0].keys())
        writer.writeheader()
        writer.writerows(func_rows)

    # 3. Org-level summary JSON
    summary = {
        "org_name": result.org_name,
        "headcount": result.headcount,
        "annual_cost": result.annual_cost,
        "total_tasks": result.total_tasks,
        "compliance_tasks": result.compliance_tasks,
        "three_layer_analysis": {
            "l1_etter_ceiling": round(result.weighted_l1, 2),
            "l2_achievable": round(result.weighted_l2, 2),
            "l3_realized": round(result.weighted_l3, 2),
            "adoption_gap_pct": round(result.weighted_l2 - result.weighted_l3, 2),
            "capability_gap_pct": round(result.weighted_l1 - result.weighted_l2, 2),
            "total_gap_pct": round(result.weighted_l1 - result.weighted_l3, 2),
        },
        "financial_opportunity": {
            "adoption_gap_savings_annual": round(result.adoption_gap_savings_annual, 0),
            "full_gap_savings_annual": round(result.full_gap_savings_annual, 0),
            "adoption_gap_fte_equivalent": round(result.adoption_gap_fte_equivalent, 1),
        },
        "top_opportunities_adoption_gap": result.top_roles_by_adoption_gap[:5],
        "top_opportunities_full_potential": result.top_roles_by_savings[:5],
    }

    with open(os.path.join(output_dir, "stage0_org_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n  Results exported to {output_dir}/")
    print(f"    stage0_role_gaps.csv       ({len(role_rows)} roles)")
    print(f"    stage0_function_gaps.csv   ({len(func_rows)} functions)")
    print(f"    stage0_org_summary.json    (org summary + top opportunities)")


# ============================================================
# Main
# ============================================================

def main(data_dir: str, output_dir: str = None):
    """Run Stage 0: Static Snapshot."""
    # Load
    print(f"  Loading data from {data_dir}...")
    org = load_organization(data_dir)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.workloads)} workloads,"
          f" {len(org.tasks)} tasks, {len(org.skills)} skills, {len(org.tools)} tools")

    # Compute
    print(f"\n  Computing three-layer gap analysis...")
    result = compute_snapshot(org)

    # Validate
    print(f"\n  VALIDATION TESTS")
    print(f"  {'─' * 60}")
    tests = validate_snapshot(org, result)
    passed = sum(1 for t in tests if t[0] == "PASS")
    failed = sum(1 for t in tests if t[0] == "FAIL")
    warned = sum(1 for t in tests if t[0] == "WARN")

    for status, msg in tests:
        icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"  {icon} [{status}] {msg}")

    print(f"  {'─' * 60}")
    print(f"  Results: {passed} passed, {failed} failed, {warned} warnings")

    if failed > 0:
        print(f"\n  *** STAGE 0 VALIDATION FAILED — {failed} test(s) ***")
        return None

    # Output
    print_org_summary(result)
    print_function_detail(result)
    print_role_detail(result)
    print_opportunities(result)

    if output_dir:
        export_results(result, output_dir)

    print(f"\n  {'=' * 80}")
    print(f"  STAGE 0 COMPLETE — All {passed} validation tests passed")
    print(f"  {'=' * 80}")

    return result


if __name__ == "__main__":
    DATA_DIR = "/mnt/user-data/outputs/synthetic_data"
    OUTPUT_DIR = "/mnt/user-data/outputs/stage0_results"
    main(DATA_DIR, OUTPUT_DIR)
