"""
Bottom-up aggregation engine.

Computes aggregate metrics at every taxonomy level:
  Task → Workload → Role → JobFamily → JobFamilyGroup → SubFunction → Function → Organization

Metrics: automation_score, total_headcount, total_cost, avg_salary

Design principle (Meadows): Stocks accumulate flows.
Aggregate metrics are the "stocks" that reveal system state at any level.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Aggregation Cypher queries
# ──────────────────────────────────────────────────────────────

AGGREGATE_WORKLOAD_FROM_TASKS = """
MATCH (wl:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
WITH wl,
     avg(t.automation_potential) AS avg_automation,
     count(t) AS task_count
SET wl.computed_automation_score = avg_automation,
    wl.task_count = task_count
RETURN count(wl) AS updated
"""

AGGREGATE_ROLE_FROM_WORKLOADS = """
MATCH (r:DTRole)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
WHERE wl.computed_automation_score IS NOT NULL
WITH r,
     avg(wl.computed_automation_score) AS avg_automation,
     count(wl) AS workload_count
SET r.computed_automation_score = avg_automation,
    r.workload_count = workload_count
RETURN count(r) AS updated
"""

AGGREGATE_ROLE_COST = """
MATCH (r:DTRole)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
WITH r,
     sum(jt.headcount) AS total_hc,
     sum(jt.headcount * jt.avg_salary) AS total_cost
SET r.computed_headcount = total_hc,
    r.computed_total_cost = total_cost,
    r.computed_avg_salary = CASE WHEN total_hc > 0 THEN total_cost / total_hc ELSE 0 END
RETURN count(r) AS updated
"""

AGGREGATE_JF_FROM_ROLES = """
MATCH (jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
WITH jf,
     sum(coalesce(r.computed_headcount, r.total_headcount, 0)) AS total_hc,
     sum(coalesce(r.computed_total_cost, 0)) AS total_cost,
     sum(coalesce(r.computed_automation_score, r.automation_score, 0)
         * coalesce(r.computed_headcount, r.total_headcount, 0)) AS weighted_auto_sum
SET jf.total_headcount = total_hc,
    jf.total_cost = total_cost,
    jf.avg_salary = CASE WHEN total_hc > 0 THEN total_cost / total_hc ELSE 0 END,
    jf.automation_score = CASE WHEN total_hc > 0 THEN weighted_auto_sum / total_hc ELSE 0 END
RETURN count(jf) AS updated
"""

AGGREGATE_JFG_FROM_JF = """
MATCH (jfg:DTJobFamilyGroup)-[:DT_CONTAINS]->(jf:DTJobFamily)
WHERE jf.total_headcount IS NOT NULL
WITH jfg,
     sum(jf.total_headcount) AS total_hc,
     sum(jf.total_cost) AS total_cost,
     sum(jf.automation_score * jf.total_headcount) AS weighted_auto_sum
SET jfg.total_headcount = total_hc,
    jfg.total_cost = total_cost,
    jfg.automation_score = CASE WHEN total_hc > 0 THEN weighted_auto_sum / total_hc ELSE 0 END
RETURN count(jfg) AS updated
"""

AGGREGATE_SF_FROM_JFG = """
MATCH (sf:DTSubFunction)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
WHERE jfg.total_headcount IS NOT NULL
WITH sf,
     sum(jfg.total_headcount) AS total_hc,
     sum(jfg.total_cost) AS total_cost,
     sum(jfg.automation_score * jfg.total_headcount) AS weighted_auto_sum
SET sf.total_headcount = total_hc,
    sf.total_cost = total_cost,
    sf.automation_score = CASE WHEN total_hc > 0 THEN weighted_auto_sum / total_hc ELSE 0 END
RETURN count(sf) AS updated
"""

AGGREGATE_FUNC_FROM_SF = """
MATCH (f:DTFunction)-[:DT_CONTAINS]->(sf:DTSubFunction)
WHERE sf.total_headcount IS NOT NULL
WITH f,
     sum(sf.total_headcount) AS total_hc,
     sum(sf.total_cost) AS total_cost,
     sum(sf.automation_score * sf.total_headcount) AS weighted_auto_sum
SET f.computed_headcount = total_hc,
    f.computed_total_cost = total_cost,
    f.automation_score = CASE WHEN total_hc > 0 THEN weighted_auto_sum / total_hc ELSE 0 END
RETURN count(f) AS updated
"""

AGGREGATE_ORG_FROM_FUNC = """
MATCH (org:DTOrganization)-[:DT_CONTAINS]->(f:DTFunction)
WHERE f.computed_headcount IS NOT NULL
WITH org,
     sum(f.computed_headcount) AS total_hc,
     sum(f.computed_total_cost) AS total_cost,
     sum(f.automation_score * f.computed_headcount) AS weighted_auto_sum
SET org.computed_headcount = total_hc,
    org.computed_total_cost = total_cost,
    org.automation_score = CASE WHEN total_hc > 0 THEN weighted_auto_sum / total_hc ELSE 0 END
RETURN count(org) AS updated
"""


class AggregationEngine:
    """Runs bottom-up aggregation across the taxonomy."""

    def __init__(self, neo4j_conn):
        self.conn = neo4j_conn

    def run(self) -> Dict[str, int]:
        """Execute full aggregation pipeline, bottom-up."""
        logger.info("Running bottom-up aggregation...")
        results = {}

        steps = [
            ("workloads ← tasks", AGGREGATE_WORKLOAD_FROM_TASKS),
            ("roles ← workloads", AGGREGATE_ROLE_FROM_WORKLOADS),
            ("roles ← titles (cost)", AGGREGATE_ROLE_COST),
            ("job_families ← roles", AGGREGATE_JF_FROM_ROLES),
            ("job_family_groups ← jf", AGGREGATE_JFG_FROM_JF),
            ("sub_functions ← jfg", AGGREGATE_SF_FROM_JFG),
            ("functions ← sf", AGGREGATE_FUNC_FROM_SF),
            ("organization ← functions", AGGREGATE_ORG_FROM_FUNC),
        ]

        for name, query in steps:
            try:
                result = self.conn.execute_write_query(query)
                updated = result[0].get("updated", 0) if result else 0
                results[name] = updated
                logger.info(f"  Aggregated {name}: {updated} nodes updated")
            except Exception as e:
                logger.error(f"  Aggregation failed at {name}: {e}")
                results[name] = 0

        logger.info(f"Aggregation complete: {results}")
        return results
