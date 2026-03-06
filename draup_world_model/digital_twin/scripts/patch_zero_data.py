"""
Patch zero-value data in Digital Twin graph.

Fixes 3 data quality issues found by validate_foundation.py:
  1. Tasks with time_allocation_pct = 0  → set to workload average
  2. JobTitles with headcount = 0        → distribute from role total
  3. JobTitles with avg_salary = 0       → set from career band median

Usage:
    python -m draup_world_model.digital_twin.scripts.patch_zero_data
    python -m draup_world_model.digital_twin.scripts.patch_zero_data --dry-run
"""

import argparse
import logging
import sys

from draup_world_model.digital_twin.config import get_dt_neo4j_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Career band salary benchmarks (insurance industry, USD)
BAND_SALARY = {
    "entry": 48000,
    "mid": 68000,
    "senior": 88000,
    "lead": 105000,
    "principal": 120000,
    "director": 140000,
    "vp": 165000,
    "c_suite": 200000,
}


def patch_tasks(conn, dry_run: bool) -> int:
    """Fix tasks with time_allocation_pct = 0 by setting to workload average."""
    # Find zero-time tasks and their workload siblings' average
    records = conn.execute_read_query("""
        MATCH (wl:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
        WHERE t.time_allocation_pct = 0 OR t.time_allocation_pct IS NULL
        WITH t, wl
        OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(sibling:DTTask)
        WHERE sibling.time_allocation_pct > 0
        WITH t, wl, avg(sibling.time_allocation_pct) AS avg_time,
             count(sibling) AS sibling_count
        RETURN t.id AS task_id, t.name AS task_name,
               wl.id AS wl_id, wl.name AS wl_name,
               avg_time, sibling_count
    """)

    if not records:
        print("  No tasks with zero time_allocation_pct found.")
        return 0

    print(f"  Found {len(records)} tasks with time_allocation_pct = 0:")
    patched = 0
    for r in records:
        # Use sibling average, fallback to 15.0 (generation default)
        new_time = round(r["avg_time"], 1) if r["avg_time"] else 15.0
        print(f"    {r['task_name'][:50]:50s} → {new_time}% (wl: {r['wl_name'][:30]})")

        if not dry_run:
            conn.execute_write_query(
                "MATCH (t:DTTask {id: $tid}) SET t.time_allocation_pct = $val",
                {"tid": r["task_id"], "val": new_time},
            )
            patched += 1

    return patched


def patch_job_titles(conn, dry_run: bool) -> int:
    """Fix JobTitles with headcount=0 or avg_salary=0."""
    # Find zero-headcount titles with their role context
    records = conn.execute_read_query("""
        MATCH (r:DTRole)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
        WHERE jt.headcount = 0 OR jt.headcount IS NULL
           OR jt.avg_salary = 0 OR jt.avg_salary IS NULL
        WITH r, jt
        OPTIONAL MATCH (r)-[:DT_HAS_TITLE]->(sibling:DTJobTitle)
        WHERE sibling.headcount > 0
        WITH r, jt,
             sum(sibling.headcount) AS sibling_hc_sum,
             count(sibling) AS sibling_count,
             avg(sibling.avg_salary) AS sibling_avg_sal
        RETURN jt.id AS title_id, jt.name AS title_name,
               jt.career_band AS band, jt.headcount AS hc,
               jt.avg_salary AS salary,
               r.id AS role_id, r.name AS role_name,
               r.total_headcount AS role_hc,
               sibling_hc_sum, sibling_count, sibling_avg_sal
    """)

    if not records:
        print("  No JobTitles with zero headcount/salary found.")
        return 0

    print(f"  Found {len(records)} JobTitles to patch:")
    patched = 0
    for r in records:
        band = r.get("band") or "mid"
        current_hc = r.get("hc") or 0
        current_sal = r.get("salary") or 0
        role_hc = r.get("role_hc") or 0
        sibling_hc_sum = r.get("sibling_hc_sum") or 0
        sibling_count = r.get("sibling_count") or 0

        # Compute new headcount: distribute remaining role headcount
        new_hc = current_hc
        if current_hc == 0 and role_hc > 0:
            remaining = max(role_hc - sibling_hc_sum, 0)
            # How many zero-hc titles share this role?
            zero_titles_in_role = conn.execute_read_query(
                """MATCH (r:DTRole {id: $rid})-[:DT_HAS_TITLE]->(jt:DTJobTitle)
                   WHERE jt.headcount = 0 OR jt.headcount IS NULL
                   RETURN count(jt) AS cnt""",
                {"rid": r["role_id"]},
            )
            zero_count = zero_titles_in_role[0]["cnt"] if zero_titles_in_role else 1
            new_hc = max(int(remaining / max(zero_count, 1)), 1)

        # Compute new salary from band benchmark
        new_sal = current_sal
        if current_sal == 0:
            new_sal = BAND_SALARY.get(band, 68000)

        changes = []
        if current_hc == 0 and new_hc > 0:
            changes.append(f"hc: 0→{new_hc}")
        if current_sal == 0 and new_sal > 0:
            changes.append(f"sal: $0→${new_sal:,}")

        print(f"    {r['title_name'][:45]:45s} | band={band:6s} | {', '.join(changes)}")

        if not dry_run:
            updates = {}
            set_clauses = []
            if current_hc == 0 and new_hc > 0:
                set_clauses.append("jt.headcount = $hc")
                updates["hc"] = new_hc
            if current_sal == 0 and new_sal > 0:
                set_clauses.append("jt.avg_salary = $sal")
                updates["sal"] = new_sal

            if set_clauses:
                conn.execute_write_query(
                    f"MATCH (jt:DTJobTitle {{id: $tid}}) SET {', '.join(set_clauses)}",
                    {"tid": r["title_id"], **updates},
                )
                patched += 1

    return patched


def main():
    parser = argparse.ArgumentParser(description="Patch zero-value data in DT graph")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be patched without writing")
    args = parser.parse_args()

    conn = get_dt_neo4j_connection()
    try:
        mode = "DRY RUN" if args.dry_run else "LIVE"
        print(f"\n{'='*60}")
        print(f"  DATA PATCH ({mode})")
        print(f"{'='*60}")

        print("\n[1/2] Patching tasks with time_allocation_pct = 0:")
        task_count = patch_tasks(conn, args.dry_run)

        print("\n[2/2] Patching JobTitles with headcount/salary = 0:")
        title_count = patch_job_titles(conn, args.dry_run)

        print(f"\n{'='*60}")
        if args.dry_run:
            print(f"  DRY RUN complete. Would patch {task_count} tasks + {title_count} titles.")
            print("  Run without --dry-run to apply changes.")
        else:
            print(f"  Patched {task_count} tasks + {title_count} titles.")
        print(f"{'='*60}\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
