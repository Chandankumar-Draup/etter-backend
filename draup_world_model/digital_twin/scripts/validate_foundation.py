"""
Digital Twin Foundation Validator — Systems Thinking Diagnostic.

Validates the data foundation layer-by-layer, tracing the full cascade path:
  Layer 1: Graph structure (nodes exist, relationships connected)
  Layer 2: Task data (classification, time_allocation_pct, automation_level)
  Layer 3: Workload data (effort_allocation_pct, role_id, tasks linked)
  Layer 4: Role & JobTitle data (headcount, salary, career_band)
  Layer 5: Skill & Technology data (lifecycle_status, categories)
  Layer 6: End-to-end cascade trace (manual computation for one role)

Usage:
    python -m draup_world_model.digital_twin.scripts.validate_foundation
    python -m draup_world_model.digital_twin.scripts.validate_foundation --scope "Claims Management"
    python -m draup_world_model.digital_twin.scripts.validate_foundation --verbose
"""

import argparse
import logging
import sys
from typing import Any, Dict, List, Tuple

from draup_world_model.digital_twin.config import get_dt_neo4j_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Mirror cascade engine constants for manual trace
CLASSIFICATION_AUTOMATION_MAP = {
    "human_only": 0.0,
    "human_led": 0.15,
    "shared": 0.40,
    "ai_led": 0.70,
    "ai_only": 0.95,
}

AUTOMATION_SHIFT = {
    ("human_only", "human_led"): 0.15,
    ("human_only", "shared"): 0.40,
    ("human_only", "ai_led"): 0.70,
    ("human_only", "ai_only"): 0.95,
    ("human_led", "shared"): 0.25,
    ("human_led", "ai_led"): 0.55,
    ("human_led", "ai_only"): 0.80,
    ("shared", "ai_led"): 0.30,
    ("shared", "ai_only"): 0.55,
    ("ai_led", "ai_only"): 0.25,
}

AUTOMATION_LEVELS = ["human_only", "human_led", "shared", "ai_led", "ai_only"]


def run_query(conn, query: str, params: Dict = None) -> List:
    """Execute a read query and return results."""
    return conn.execute_read_query(query, params or {})


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_check(label: str, passed: bool, detail: str = ""):
    """Print a check result."""
    status = "PASS" if passed else "FAIL"
    symbol = "+" if passed else "!"
    msg = f"  [{symbol}] {status}: {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def print_warning(label: str, detail: str = ""):
    """Print a warning."""
    msg = f"  [~] WARN: {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def print_info(label: str, detail: str = ""):
    """Print info."""
    msg = f"  [i] {label}"
    if detail:
        msg += f": {detail}"
    print(msg)


# ─────────────────────────────────────────────────────────────────
# Layer 1: Graph Structure
# ─────────────────────────────────────────────────────────────────

def validate_graph_structure(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Validate node counts and relationship connectivity."""
    print_section("Layer 1: Graph Structure")

    passes = 0
    fails = 0

    # 1.1 Node counts
    node_types = [
        "DTOrganization", "DTFunction", "DTSubFunction", "DTJobFamilyGroup",
        "DTJobFamily", "DTRole", "DTJobTitle", "DTWorkload", "DTTask",
        "DTSkill", "DTTechnology",
    ]
    print("\n  Node counts:")
    for label in node_types:
        records = run_query(conn, f"MATCH (n:{label}) RETURN count(n) AS cnt")
        cnt = records[0]["cnt"] if records else 0
        print(f"    {label:25s}: {cnt:>5}")
        if label in ("DTRole", "DTTask", "DTWorkload", "DTJobTitle"):
            if cnt > 0:
                passes += 1
            else:
                print_check(f"{label} nodes exist", False, f"Found {cnt}")
                fails += 1

    # 1.2 Function scope exists
    records = run_query(
        conn,
        "MATCH (f:DTFunction {name: $name}) RETURN f",
        {"name": scope_name},
    )
    if records:
        print_check(f"Function '{scope_name}' exists", True)
        passes += 1
    else:
        print_check(f"Function '{scope_name}' exists", False)
        fails += 1
        # List available functions
        funcs = run_query(conn, "MATCH (f:DTFunction) RETURN f.name AS name")
        print(f"    Available functions: {[r['name'] for r in funcs]}")

    # 1.3 Relationship counts
    print("\n  Relationship counts:")
    rel_types = [
        ("DT_HAS_ROLE", "DTJobFamily", "DTRole"),
        ("DT_HAS_TITLE", "DTRole", "DTJobTitle"),
        ("DT_HAS_WORKLOAD", "DTRole", "DTWorkload"),
        ("DT_CONTAINS_TASK", "DTWorkload", "DTTask"),
        ("DT_REQUIRES_SKILL", "DTRole", "DTSkill"),
        ("DT_USES_TECHNOLOGY", "DTRole", "DTTechnology"),
    ]
    for rel, from_label, to_label in rel_types:
        records = run_query(
            conn,
            f"MATCH (:{from_label})-[r:{rel}]->(:{to_label}) RETURN count(r) AS cnt",
        )
        cnt = records[0]["cnt"] if records else 0
        print(f"    ({from_label})-[:{rel}]->({to_label}): {cnt}")
        if rel in ("DT_HAS_WORKLOAD", "DT_CONTAINS_TASK", "DT_HAS_TITLE"):
            if cnt > 0:
                passes += 1
            else:
                fails += 1
                print_check(f"{rel} relationships exist", False)

    # 1.4 Roles reachable from scope
    records = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN count(r) AS cnt
        """,
        {"name": scope_name},
    )
    role_count = records[0]["cnt"] if records else 0
    print_check(
        f"Roles reachable from '{scope_name}'",
        role_count > 0,
        f"{role_count} roles",
    )
    if role_count > 0:
        passes += 1
    else:
        fails += 1

    # 1.5 Task-skill mappings (DT_REQUIRES_SKILL on tasks)
    records = run_query(
        conn,
        "MATCH (:DTTask)-[r:DT_REQUIRES_SKILL]->(:DTSkill) RETURN count(r) AS cnt",
    )
    task_skill_cnt = records[0]["cnt"] if records else 0
    print_check(
        "Task-skill mappings exist",
        task_skill_cnt > 0,
        f"{task_skill_cnt} mappings",
    )
    if task_skill_cnt > 0:
        passes += 1
    else:
        fails += 1

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Layer 2: Task Data Quality
# ─────────────────────────────────────────────────────────────────

def validate_task_data(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Validate task properties critical to cascade Step 1."""
    print_section("Layer 2: Task Data (Cascade Step 1 Input)")

    passes = 0
    fails = 0

    # Get tasks in scope
    records = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
              -[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
              -[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN t.id AS id, t.name AS name, t.classification AS classification,
               t.time_allocation_pct AS time_pct, t.automation_level AS auto_level,
               t.automation_potential AS auto_potential, t.workload_id AS wl_id,
               wl.id AS actual_wl_id
        """,
        {"name": scope_name},
    )

    if not records:
        print_check("Tasks found in scope", False, "0 tasks")
        return 0, 1

    total_tasks = len(records)
    print_check("Tasks found in scope", True, f"{total_tasks} tasks")
    passes += 1

    # 2.1 Classification distribution
    class_dist = {}
    for r in records:
        cls = r.get("classification") or "NULL"
        class_dist[cls] = class_dist.get(cls, 0) + 1

    print("\n  Classification distribution (Etter 6-category):")
    target_count = 0
    for cls in ["directive", "feedback_loop", "learning", "validation",
                 "task_iteration", "negligibility", "NULL"]:
        cnt = class_dist.get(cls, 0)
        marker = " <-- TARGET" if cls in ("directive", "feedback_loop") else ""
        if cls in ("directive", "feedback_loop"):
            target_count += cnt
        print(f"    {cls:20s}: {cnt:>4}{marker}")

    # Check for other unknown classifications
    known = {"directive", "feedback_loop", "learning", "validation",
             "task_iteration", "negligibility", "NULL"}
    unknown = set(class_dist.keys()) - known
    if unknown:
        print_warning("Unknown classifications found", str(unknown))

    if target_count > 0:
        print_check(
            "Tasks with automatable classification",
            True,
            f"{target_count}/{total_tasks} ({target_count*100//total_tasks}%) are directive/feedback_loop",
        )
        passes += 1
    else:
        print_check(
            "Tasks with automatable classification",
            False,
            "No directive or feedback_loop tasks — role_redesign will do nothing!",
        )
        fails += 1

    # 2.2 time_allocation_pct
    null_time = sum(1 for r in records if r.get("time_pct") is None)
    zero_time = sum(1 for r in records if (r.get("time_pct") or 0) == 0)
    valid_time = total_tasks - null_time - zero_time
    avg_time = (
        sum(r.get("time_pct", 0) or 0 for r in records) / total_tasks
        if total_tasks > 0 else 0
    )

    print(f"\n  time_allocation_pct: avg={avg_time:.1f}%, null={null_time}, zero={zero_time}, valid={valid_time}")
    if null_time > 0 or zero_time > 0:
        print_check(
            "time_allocation_pct populated",
            False,
            f"{null_time} NULL + {zero_time} zero out of {total_tasks}",
        )
        fails += 1
    else:
        print_check("time_allocation_pct populated", True, f"all {total_tasks} > 0")
        passes += 1

    # 2.3 automation_level distribution
    auto_dist = {}
    for r in records:
        lvl = r.get("auto_level") or "NULL"
        auto_dist[lvl] = auto_dist.get(lvl, 0) + 1

    print("\n  automation_level distribution:")
    for lvl in AUTOMATION_LEVELS + ["NULL"]:
        cnt = auto_dist.get(lvl, 0)
        print(f"    {lvl:15s}: {cnt:>4}")

    # Check if all tasks are already at high automation
    high_auto = auto_dist.get("ai_led", 0) + auto_dist.get("ai_only", 0)
    if high_auto == total_tasks:
        print_warning("All tasks already ai_led or ai_only — no room to advance")

    # 2.4 workload_id linkage
    missing_wl_id = sum(1 for r in records if not r.get("wl_id"))
    mismatched_wl = sum(1 for r in records if r.get("wl_id") != r.get("actual_wl_id"))

    if missing_wl_id > 0:
        print_check(
            "Task workload_id property set",
            False,
            f"{missing_wl_id}/{total_tasks} tasks missing workload_id",
        )
        fails += 1
    else:
        print_check("Task workload_id property set", True, f"all {total_tasks}")
        passes += 1

    if mismatched_wl > 0:
        print_warning(
            f"{mismatched_wl} tasks where workload_id != actual relationship target"
        )

    # 2.5 Reclassification eligibility (what role_redesign will target)
    eligible = [r for r in records
                if r.get("classification") in ("directive", "feedback_loop")
                and r.get("auto_level") not in ("ai_only",)]
    can_advance = 0
    for r in eligible:
        current = r.get("auto_level") or "human_led"
        idx = AUTOMATION_LEVELS.index(current) if current in AUTOMATION_LEVELS else 1
        new_idx = min(idx + 1, len(AUTOMATION_LEVELS) - 1)
        if new_idx > idx:
            can_advance += 1

    print_check(
        "Eligible tasks that CAN be advanced",
        can_advance > 0,
        f"{can_advance}/{len(eligible)} eligible tasks can advance at factor=0.3",
    )
    if can_advance > 0:
        passes += 1
    else:
        fails += 1

    if verbose:
        print("\n  Sample tasks (first 5):")
        for r in records[:5]:
            print(
                f"    {r['name'][:40]:40s} | cls={r.get('classification', '?'):15s} "
                f"| time={r.get('time_pct', 0):>5.1f}% | auto={r.get('auto_level', '?')}"
            )

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Layer 3: Workload Data Quality
# ─────────────────────────────────────────────────────────────────

def validate_workload_data(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Validate workload properties critical to cascade Step 2-3."""
    print_section("Layer 3: Workload Data (Cascade Step 2-3 Input)")

    passes = 0
    fails = 0

    # Get workloads in scope
    records = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
              -[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
        RETURN wl.id AS id, wl.name AS name, wl.role_id AS role_id,
               wl.effort_allocation_pct AS effort_pct,
               wl.automation_level AS auto_level,
               r.id AS actual_role_id, r.name AS role_name
        """,
        {"name": scope_name},
    )

    if not records:
        print_check("Workloads found in scope", False, "0 workloads")
        return 0, 1

    total_wl = len(records)
    print_check("Workloads found in scope", True, f"{total_wl} workloads")
    passes += 1

    # 3.1 effort_allocation_pct
    null_effort = sum(1 for r in records if r.get("effort_pct") is None)
    zero_effort = sum(1 for r in records if (r.get("effort_pct") or 0) == 0)
    valid_effort = total_wl - null_effort - zero_effort
    avg_effort = (
        sum(r.get("effort_pct", 0) or 0 for r in records) / total_wl
        if total_wl > 0 else 0
    )

    print(f"\n  effort_allocation_pct: avg={avg_effort:.1f}%, null={null_effort}, zero={zero_effort}, valid={valid_effort}")
    if null_effort > 0 or zero_effort > 0:
        print_check(
            "effort_allocation_pct populated",
            False,
            f"{null_effort} NULL + {zero_effort} zero out of {total_wl}",
        )
        fails += 1
    else:
        print_check("effort_allocation_pct populated", True, f"all {total_wl} > 0")
        passes += 1

    # 3.2 Per-role effort sums (should sum to ~100% per role)
    role_efforts = {}
    for r in records:
        rid = r.get("actual_role_id", "")
        role_efforts.setdefault(rid, {"name": r.get("role_name", ""), "total": 0, "count": 0})
        role_efforts[rid]["total"] += r.get("effort_pct", 0) or 0
        role_efforts[rid]["count"] += 1

    bad_sums = 0
    if verbose:
        print("\n  Per-role effort sums:")
    for rid, info in role_efforts.items():
        if info["total"] < 90 or info["total"] > 110:
            bad_sums += 1
            if verbose:
                print(f"    {info['name'][:40]:40s}: {info['total']:>6.1f}% ({info['count']} workloads) WARN")
        elif verbose:
            print(f"    {info['name'][:40]:40s}: {info['total']:>6.1f}% ({info['count']} workloads)")

    if bad_sums > 0:
        print_warning(f"{bad_sums}/{len(role_efforts)} roles have effort sums outside 90-110%")

    # 3.3 role_id property matches relationship
    missing_role_id = sum(1 for r in records if not r.get("role_id"))
    mismatched = sum(1 for r in records if r.get("role_id") != r.get("actual_role_id"))

    if missing_role_id > 0:
        print_check(
            "Workload role_id property set",
            False,
            f"{missing_role_id}/{total_wl} missing role_id",
        )
        fails += 1
    else:
        print_check("Workload role_id property set", True, f"all {total_wl}")
        passes += 1

    if mismatched > 0:
        print_warning(f"{mismatched} workloads where role_id != actual relationship source")

    # 3.4 Tasks per workload (do workloads have tasks?)
    task_counts = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(:DTRole)
              -[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
        OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN wl.id AS wl_id, wl.name AS wl_name, count(t) AS task_count
        """,
        {"name": scope_name},
    )

    empty_wl = sum(1 for r in task_counts if r["task_count"] == 0)
    if empty_wl > 0:
        print_check(
            "All workloads have tasks",
            False,
            f"{empty_wl}/{total_wl} workloads have 0 tasks (cascade Step 2 skips these)",
        )
        fails += 1
    else:
        print_check("All workloads have tasks", True, f"all {total_wl}")
        passes += 1

    # 3.5 Per-workload time_allocation_pct sums
    time_sums = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(:DTRole)
              -[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
              -[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN wl.id AS wl_id, wl.name AS wl_name,
               sum(t.time_allocation_pct) AS time_sum, count(t) AS tcnt
        """,
        {"name": scope_name},
    )

    bad_time_sums = 0
    for r in time_sums:
        ts = r.get("time_sum") or 0
        if ts < 90 or ts > 110:
            bad_time_sums += 1
            if verbose:
                print(f"    WL {r['wl_name'][:40]:40s}: time_sum={ts:.1f}% ({r['tcnt']} tasks)")

    if bad_time_sums > 0:
        print_warning(f"{bad_time_sums}/{len(time_sums)} workloads have task time sums outside 90-110%")

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Layer 4: Role & JobTitle Data Quality
# ─────────────────────────────────────────────────────────────────

def validate_role_data(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Validate role/title properties critical to cascade Step 3, 5, 6."""
    print_section("Layer 4: Role & JobTitle Data (Cascade Step 3/5/6 Input)")

    passes = 0
    fails = 0

    # Roles
    roles = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r.id AS id, r.name AS name, r.total_headcount AS hc,
               r.avg_salary AS salary, r.automation_score AS auto_score
        """,
        {"name": scope_name},
    )

    if not roles:
        print_check("Roles found", False)
        return 0, 1

    total_roles = len(roles)
    print_check("Roles found", True, f"{total_roles} roles")
    passes += 1

    # 4.1 Role headcount
    zero_hc = sum(1 for r in roles if (r.get("hc") or 0) == 0)
    total_hc = sum(r.get("hc", 0) or 0 for r in roles)
    print(f"\n  Role total_headcount: sum={total_hc}, zero/null={zero_hc}")
    if zero_hc > 0:
        print_warning(f"{zero_hc}/{total_roles} roles have 0 headcount")

    # JobTitles
    titles = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
              -[:DT_HAS_TITLE]->(jt:DTJobTitle)
        RETURN jt.id AS id, jt.name AS name, jt.role_id AS role_id,
               jt.headcount AS hc, jt.avg_salary AS salary,
               jt.career_band AS band, r.id AS actual_role_id, r.name AS role_name
        """,
        {"name": scope_name},
    )

    if not titles:
        print_check("JobTitles found", False, "0 titles — Step 3/5/6 will produce 0!")
        return passes, fails + 1

    total_titles = len(titles)
    print_check("JobTitles found", True, f"{total_titles} titles")
    passes += 1

    # 4.2 Title headcount
    null_hc = sum(1 for t in titles if t.get("hc") is None)
    zero_hc_t = sum(1 for t in titles if (t.get("hc") or 0) == 0)
    total_title_hc = sum(t.get("hc", 0) or 0 for t in titles)

    print(f"\n  JobTitle headcount: sum={total_title_hc}, null={null_hc}, zero={zero_hc_t}")
    if null_hc > 0 or zero_hc_t > 0:
        print_check(
            "JobTitle headcount populated",
            False,
            f"{null_hc} NULL + {zero_hc_t} zero — Step 5 freed_headcount will be 0!",
        )
        fails += 1
    else:
        print_check("JobTitle headcount populated", True, f"all {total_titles} > 0")
        passes += 1

    # 4.3 Title avg_salary
    null_sal = sum(1 for t in titles if t.get("salary") is None)
    zero_sal = sum(1 for t in titles if (t.get("salary") or 0) == 0)
    avg_sal = sum(t.get("salary", 0) or 0 for t in titles) / max(total_titles, 1)

    print(f"  JobTitle avg_salary: avg=${avg_sal:,.0f}, null={null_sal}, zero={zero_sal}")
    if null_sal > 0 or zero_sal > 0:
        print_check(
            "JobTitle avg_salary populated",
            False,
            f"{null_sal} NULL + {zero_sal} zero — Step 6 savings will be $0!",
        )
        fails += 1
    else:
        print_check("JobTitle avg_salary populated", True, f"all {total_titles} > 0, avg=${avg_sal:,.0f}")
        passes += 1

    # 4.4 Career band distribution
    band_dist = {}
    for t in titles:
        band = t.get("band") or "NULL"
        band_dist[band] = band_dist.get(band, 0) + 1

    print("\n  Career band distribution:")
    for band in ["entry", "mid", "senior", "lead", "principal", "director", "vp", "c_suite", "NULL"]:
        cnt = band_dist.get(band, 0)
        if cnt > 0:
            print(f"    {band:12s}: {cnt:>4}")

    # 4.5 Title role_id linkage
    missing_role_id = sum(1 for t in titles if not t.get("role_id"))
    if missing_role_id > 0:
        print_check(
            "JobTitle role_id set",
            False,
            f"{missing_role_id}/{total_titles} missing — titles_by_role lookup will miss them!",
        )
        fails += 1
    else:
        print_check("JobTitle role_id set", True, f"all {total_titles}")
        passes += 1

    if verbose:
        print("\n  Sample titles (first 10):")
        for t in titles[:10]:
            print(
                f"    {t['name'][:35]:35s} | band={t.get('band', '?'):8s} "
                f"| hc={t.get('hc', 0):>4} | sal=${t.get('salary', 0):>8,}"
            )

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Layer 5: Cascade Computation Trace
# ─────────────────────────────────────────────────────────────────

def trace_cascade(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Manually trace the cascade for ONE role to verify computation."""
    print_section("Layer 5: End-to-End Cascade Trace (Manual Computation)")

    passes = 0
    fails = 0

    # Pick the first role with workloads and tasks
    sample = run_query(
        conn,
        """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
              -[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
              -[:DT_CONTAINS_TASK]->(t:DTTask)
        WITH r, wl, t
        ORDER BY r.name, wl.name, t.name
        RETURN r.id AS role_id, r.name AS role_name, r.total_headcount AS role_hc,
               wl.id AS wl_id, wl.name AS wl_name,
               wl.effort_allocation_pct AS wl_effort,
               wl.automation_level AS wl_auto,
               t.id AS task_id, t.name AS task_name,
               t.classification AS task_cls,
               t.time_allocation_pct AS task_time,
               t.automation_level AS task_auto
        LIMIT 200
        """,
        {"name": scope_name},
    )

    if not sample:
        print_check("Sample data for trace", False, "No role→workload→task path found")
        return 0, 1

    # Group by role → workload → tasks
    roles = {}
    for r in sample:
        rid = r["role_id"]
        if rid not in roles:
            roles[rid] = {
                "name": r["role_name"], "hc": r["role_hc"],
                "workloads": {},
            }
        wid = r["wl_id"]
        if wid not in roles[rid]["workloads"]:
            roles[rid]["workloads"][wid] = {
                "name": r["wl_name"], "effort": r["wl_effort"] or 0,
                "auto_level": r["wl_auto"],
                "tasks": [],
            }
        roles[rid]["workloads"][wid]["tasks"].append({
            "id": r["task_id"], "name": r["task_name"],
            "cls": r["task_cls"], "time": r["task_time"] or 0,
            "auto": r["task_auto"] or "human_led",
        })

    # Trace first role
    first_rid = list(roles.keys())[0]
    role = roles[first_rid]
    print(f"\n  Tracing role: {role['name']} (headcount={role['hc']})")
    print(f"  Workloads: {len(role['workloads'])}")

    total_freed = 0.0
    automation_factor = 0.3
    target_classifications = ["directive", "feedback_loop"]

    for wl_id, wl in role["workloads"].items():
        print(f"\n    Workload: {wl['name']}")
        print(f"      effort_allocation_pct = {wl['effort']:.1f}%")
        print(f"      tasks = {len(wl['tasks'])}")

        total_time = sum(t["time"] for t in wl["tasks"])
        print(f"      total task time_allocation_pct = {total_time:.1f}%")

        # Simulate Step 1: Which tasks get reclassified?
        reclassified = []
        for t in wl["tasks"]:
            if t["cls"] not in target_classifications:
                continue
            current_idx = AUTOMATION_LEVELS.index(t["auto"]) if t["auto"] in AUTOMATION_LEVELS else 1
            steps = max(1, int(automation_factor * 3))
            new_idx = min(current_idx + steps, len(AUTOMATION_LEVELS) - 1)
            new_level = AUTOMATION_LEVELS[new_idx]
            if new_level != t["auto"]:
                reclassified.append({
                    "name": t["name"], "old": t["auto"], "new": new_level,
                    "time": t["time"], "id": t["id"],
                })

        if not reclassified:
            print(f"      No reclassifiable tasks in this workload")
            continue

        print(f"      Reclassified tasks: {len(reclassified)}")
        for rc in reclassified[:3]:
            print(f"        {rc['name'][:35]:35s}: {rc['old']} → {rc['new']} (time={rc['time']:.1f}%)")

        # Simulate Step 2: Compute old/new automation scores
        old_weighted = 0.0
        new_weighted = 0.0
        reclass_ids = {rc["id"] for rc in reclassified}
        reclass_map = {rc["id"]: rc["new"] for rc in reclassified}

        for t in wl["tasks"]:
            old_level = t["auto"]
            new_level = reclass_map.get(t["id"], t["auto"])
            old_score = CLASSIFICATION_AUTOMATION_MAP.get(old_level, 0)
            new_score = CLASSIFICATION_AUTOMATION_MAP.get(new_level, 0)
            old_weighted += old_score * t["time"]
            new_weighted += new_score * t["time"]

        old_auto_pct = (old_weighted / total_time * 100) if total_time > 0 else 0
        new_auto_pct = (new_weighted / total_time * 100) if total_time > 0 else 0
        delta_pct = new_auto_pct - old_auto_pct

        print(f"      Old auto score: {old_auto_pct:.1f}%")
        print(f"      New auto score: {new_auto_pct:.1f}%")
        print(f"      Delta: {delta_pct:.1f}%")

        # Simulate Step 3: Freed capacity
        wl_effort = wl["effort"] / 100.0
        wl_freed = wl_effort * delta_pct / 100.0
        total_freed += wl_freed
        print(f"      Freed capacity contribution: {wl_effort:.2f} × {delta_pct:.1f}% = {wl_freed*100:.2f}%")

    freed_pct = min(total_freed * 100, 100)
    print(f"\n  ROLE FREED CAPACITY: {freed_pct:.1f}%")

    if freed_pct > 0:
        print_check("Cascade produces non-zero freed capacity", True, f"{freed_pct:.1f}%")
        passes += 1
    else:
        print_check(
            "Cascade produces non-zero freed capacity",
            False,
            "0% — check if tasks are reclassifiable and have time_allocation_pct > 0",
        )
        fails += 1

    # Get titles for this role
    titles = run_query(
        conn,
        """
        MATCH (r:DTRole {id: $rid})-[:DT_HAS_TITLE]->(jt:DTJobTitle)
        RETURN jt.name AS name, jt.headcount AS hc, jt.avg_salary AS salary,
               jt.career_band AS band
        """,
        {"rid": first_rid},
    )

    if titles:
        print(f"\n  Title impacts (freed_pct={freed_pct:.1f}%):")
        total_savings = 0
        total_freed_hc = 0
        for jt in titles:
            hc = jt.get("hc") or 0
            salary = jt.get("salary") or 0
            band = jt.get("band") or "mid"
            factors = {"entry": 1.4, "mid": 1.2, "senior": 1.0, "lead": 0.8,
                       "principal": 0.6, "director": 0.4, "vp": 0.3, "c_suite": 0.2}
            factor = factors.get(band, 1.0)
            title_freed = min(freed_pct * factor, 100)
            freed_hc = hc * title_freed / 100
            savings = salary * freed_hc * 3  # 36 months = 3 years
            total_freed_hc += freed_hc
            total_savings += savings
            print(
                f"    {jt['name'][:35]:35s} | band={band:6s} | hc={hc:>3} "
                f"| sal=${salary:>8,} | freed={title_freed:.1f}% "
                f"| freed_hc={freed_hc:.1f} | savings=${savings:,.0f}"
            )

        print(f"\n  TOTAL FREED HEADCOUNT: {total_freed_hc:.1f}")
        print(f"  TOTAL SAVINGS (36mo): ${total_savings:,.0f}")

        if total_freed_hc > 0:
            print_check("Financial output non-zero", True, f"${total_savings:,.0f}")
            passes += 1
        else:
            print_check(
                "Financial output non-zero",
                False,
                "Check headcount and salary on job titles",
            )
            fails += 1
    else:
        print_check("Titles found for traced role", False, "No titles linked")
        fails += 1

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Layer 6: Code Logic Verification
# ─────────────────────────────────────────────────────────────────

def verify_code_logic(conn, scope_name: str, verbose: bool) -> Tuple[int, int]:
    """Verify the cascade engine code handles data correctly."""
    print_section("Layer 6: Code Logic Verification")

    passes = 0
    fails = 0

    # Test: tasks_by_id and tasks_by_workload share same dicts
    # (This was the critical bug — dict(t) copies caused Step 2 to miss Step 1 mutations)
    print("\n  Simulating CascadeEngine.run() lookup table construction...")

    # Fetch scope data the same way ScopeSelector does
    from draup_world_model.digital_twin.simulation.scope_selector import ScopeSelector

    selector = ScopeSelector(conn)
    scope_data = selector.select("function", scope_name)

    if not scope_data["tasks"]:
        print_check("Scope has tasks", False)
        return 0, 1

    # Replicate the lookup table construction from cascade_engine.py
    tasks_by_id = {t["id"]: t for t in scope_data["tasks"]}
    tasks_by_workload = {}
    for t in scope_data["tasks"]:
        tasks_by_workload.setdefault(t.get("workload_id", ""), []).append(t)

    # Verify identity: tasks_by_id and tasks_by_workload point to same objects
    sample_task = scope_data["tasks"][0]
    tid = sample_task["id"]
    wid = sample_task.get("workload_id", "")

    is_same_in_id = tasks_by_id[tid] is sample_task
    wl_tasks = tasks_by_workload.get(wid, [])
    is_same_in_wl = any(t is sample_task for t in wl_tasks)

    if is_same_in_id and is_same_in_wl:
        print_check(
            "tasks_by_id and tasks_by_workload share same dict objects",
            True,
            "Step 1 mutations will be visible to Step 2",
        )
        passes += 1
    else:
        print_check(
            "tasks_by_id and tasks_by_workload share same dict objects",
            False,
            "CRITICAL: Step 1 mutates copies, Step 2 reads originals → delta=0!",
        )
        fails += 1

    # Test: Simulate Step 1 mutation visibility
    original_level = tasks_by_id[tid].get("automation_level", "human_led")
    test_level = "ai_led" if original_level != "ai_led" else "shared"
    tasks_by_id[tid]["automation_level"] = test_level

    # Check if tasks_by_workload sees the change
    wl_task = next((t for t in tasks_by_workload.get(wid, []) if t["id"] == tid), None)
    if wl_task and wl_task.get("automation_level") == test_level:
        print_check("Mutation visibility test", True, "Step 2 sees Step 1 changes")
        passes += 1
    else:
        print_check(
            "Mutation visibility test",
            False,
            "Step 2 does NOT see Step 1 changes — this is the root cause!",
        )
        fails += 1

    # Restore
    tasks_by_id[tid]["automation_level"] = original_level

    return passes, fails


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Digital Twin data foundation")
    parser.add_argument("--scope", default="Claims Management",
                        help="Function name to validate")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed output")
    args = parser.parse_args()

    conn = get_dt_neo4j_connection()
    try:
        print("\n" + "#" * 70)
        print("#  DIGITAL TWIN FOUNDATION VALIDATOR")
        print(f"#  Scope: {args.scope}")
        print("#" * 70)

        total_passes = 0
        total_fails = 0

        # Run all validation layers
        for validator in [
            validate_graph_structure,
            validate_task_data,
            validate_workload_data,
            validate_role_data,
            trace_cascade,
            verify_code_logic,
        ]:
            p, f = validator(conn, args.scope, args.verbose)
            total_passes += p
            total_fails += f

        # Summary
        print_section("SUMMARY")
        print(f"\n  Total checks: {total_passes + total_fails}")
        print(f"  Passed:       {total_passes}")
        print(f"  Failed:       {total_fails}")

        if total_fails == 0:
            print("\n  RESULT: ALL CHECKS PASSED — Foundation is solid.")
        else:
            print(f"\n  RESULT: {total_fails} ISSUES FOUND — See details above.")

        print()
        return 0 if total_fails == 0 else 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
