"""
Graph integrity validation and data readiness scoring.

Two responsibilities:
1. Structural validation - are all nodes and relationships correct?
2. Readiness scoring - is the twin ready for simulation? (100-point scale)

Readiness dimensions (from design docs):
  Taxonomy Completeness:  25 pts
  Role Decomposition:     30 pts
  Skills Architecture:    20 pts
  Enterprise Context:     15 pts
  Validation & Trust:     10 pts
"""

import logging
from typing import Dict, Any, List, Tuple

from draup_world_model.digital_twin.graph import queries

logger = logging.getLogger(__name__)


class GraphValidator:
    """Validates graph integrity and computes readiness score."""

    def __init__(self, neo4j_conn):
        self.conn = neo4j_conn

    def get_node_counts(self) -> Dict[str, int]:
        """Count nodes by label."""
        result = self.conn.execute_read_query(queries.COUNT_NODES)
        return {row["label"]: row["count"] for row in result}

    def get_relationship_counts(self) -> Dict[str, int]:
        """Count relationships by type."""
        result = self.conn.execute_read_query(queries.COUNT_RELATIONSHIPS)
        return {row["rel_type"]: row["count"] for row in result}

    def check_orphan_roles(self) -> List[Dict]:
        """Find roles not connected to any job family."""
        query = """
        MATCH (r:DTRole)
        WHERE NOT (:DTJobFamily)-[:DT_HAS_ROLE]->(r)
        RETURN r.id AS id, r.name AS name
        """
        return self.conn.execute_read_query(query)

    def check_orphan_tasks(self) -> List[Dict]:
        """Find tasks not connected to any workload."""
        query = """
        MATCH (t:DTTask)
        WHERE NOT (:DTWorkload)-[:DT_CONTAINS_TASK]->(t)
        RETURN t.id AS id, t.name AS name
        """
        return self.conn.execute_read_query(query)

    def check_roles_without_workloads(self) -> List[Dict]:
        """Find roles with no workload decomposition."""
        query = """
        MATCH (r:DTRole)
        WHERE NOT (r)-[:DT_HAS_WORKLOAD]->()
        RETURN r.id AS id, r.name AS name
        """
        return self.conn.execute_read_query(query)

    def check_roles_without_skills(self) -> List[Dict]:
        """Find roles with no skill mappings."""
        query = """
        MATCH (r:DTRole)
        WHERE NOT (r)-[:DT_REQUIRES_SKILL]->()
        RETURN r.id AS id, r.name AS name
        """
        return self.conn.execute_read_query(query)

    def validate(self) -> Dict[str, Any]:
        """Run all validation checks and return a report."""
        logger.info("Running graph validation...")
        node_counts = self.get_node_counts()
        rel_counts = self.get_relationship_counts()
        orphan_roles = self.check_orphan_roles()
        orphan_tasks = self.check_orphan_tasks()
        roles_no_wl = self.check_roles_without_workloads()
        roles_no_skills = self.check_roles_without_skills()

        report = {
            "node_counts": node_counts,
            "relationship_counts": rel_counts,
            "orphan_roles": len(orphan_roles),
            "orphan_tasks": len(orphan_tasks),
            "roles_without_workloads": len(roles_no_wl),
            "roles_without_skills": len(roles_no_skills),
            "is_valid": len(orphan_roles) == 0 and len(orphan_tasks) == 0,
        }

        logger.info(f"Validation report: {report}")
        return report

    def compute_readiness_score(self) -> Dict[str, Any]:
        """
        Compute the data readiness score (0-100).

        Dimensions:
          1. Taxonomy Completeness (25 pts)
          2. Role Decomposition (30 pts)
          3. Skills Architecture (20 pts)
          4. Enterprise Context (15 pts)
          5. Validation & Trust (10 pts)
        """
        logger.info("Computing readiness score...")
        node_counts = self.get_node_counts()

        # Extract counts with defaults
        org_count = node_counts.get("DTOrganization", 0)
        func_count = node_counts.get("DTFunction", 0)
        sf_count = node_counts.get("DTSubFunction", 0)
        jfg_count = node_counts.get("DTJobFamilyGroup", 0)
        jf_count = node_counts.get("DTJobFamily", 0)
        role_count = node_counts.get("DTRole", 0)
        title_count = node_counts.get("DTJobTitle", 0)
        wl_count = node_counts.get("DTWorkload", 0)
        task_count = node_counts.get("DTTask", 0)
        skill_count = node_counts.get("DTSkill", 0)
        tech_count = node_counts.get("DTTechnology", 0)

        scores = {}

        # 1. Taxonomy Completeness (25 pts)
        tax_score = 0
        # All 6 hierarchy levels present: 10 pts
        levels_present = sum(1 for c in [org_count, func_count, sf_count, jfg_count, jf_count, role_count] if c > 0)
        tax_score += min(10, int(levels_present / 6 * 10))
        # Role coverage (>0 roles): 10 pts
        tax_score += 10 if role_count > 0 else 0
        # Title mappings present: 5 pts
        tax_score += 5 if title_count > 0 else 0
        scores["taxonomy_completeness"] = {"score": tax_score, "max": 25}

        # 2. Role Decomposition (30 pts)
        decomp_score = 0
        # Roles have workloads: 10 pts
        roles_with_wl = self._count_roles_with_workloads()
        wl_coverage = roles_with_wl / role_count if role_count > 0 else 0
        decomp_score += min(10, int(wl_coverage * 10))
        # Avg tasks per workload is 4-8: 10 pts
        avg_tasks = task_count / wl_count if wl_count > 0 else 0
        if 4 <= avg_tasks <= 8:
            decomp_score += 10
        elif avg_tasks > 0:
            decomp_score += 5
        # Task classifications present: 10 pts
        decomp_score += 10 if task_count > 0 else 0
        scores["role_decomposition"] = {"score": decomp_score, "max": 30}

        # 3. Skills Architecture (20 pts)
        skills_score = 0
        # Roles have skills mapped: 10 pts
        roles_with_skills = self._count_roles_with_skills()
        skill_coverage = roles_with_skills / role_count if role_count > 0 else 0
        skills_score += min(10, int(skill_coverage * 10))
        # Skill catalog exists: 5 pts
        skills_score += 5 if skill_count >= 50 else (3 if skill_count > 0 else 0)
        # Technology catalog exists: 5 pts
        skills_score += 5 if tech_count >= 20 else (3 if tech_count > 0 else 0)
        scores["skills_architecture"] = {"score": skills_score, "max": 20}

        # 4. Enterprise Context (15 pts)
        context_score = 0
        # Headcount data: 5 pts
        context_score += 5 if title_count > 0 else 0
        # Salary data: 5 pts
        has_salary = self._check_salary_data()
        context_score += 5 if has_salary else 0
        # Aggregation computed: 5 pts
        has_agg = self._check_aggregation()
        context_score += 5 if has_agg else 0
        scores["enterprise_context"] = {"score": context_score, "max": 15}

        # 5. Validation & Trust (10 pts)
        validation_score = 0
        # No orphan nodes: 5 pts
        orphan_roles = self.check_orphan_roles()
        orphan_tasks = self.check_orphan_tasks()
        validation_score += 5 if len(orphan_roles) == 0 and len(orphan_tasks) == 0 else 0
        # Graph is structurally valid: 5 pts
        validation_score += 5 if role_count > 0 and wl_count > 0 else 0
        scores["validation_trust"] = {"score": validation_score, "max": 10}

        total = sum(d["score"] for d in scores.values())
        max_total = sum(d["max"] for d in scores.values())

        if total >= 70:
            status = "READY"
        elif total >= 50:
            status = "PARTIAL"
        else:
            status = "NOT_READY"

        result = {
            "total_score": total,
            "max_score": max_total,
            "status": status,
            "dimensions": scores,
        }

        logger.info(f"Readiness score: {total}/{max_total} ({status})")
        return result

    def _count_roles_with_workloads(self) -> int:
        """Count roles that have at least one workload."""
        query = """
        MATCH (r:DTRole)-[:DT_HAS_WORKLOAD]->()
        RETURN count(DISTINCT r) AS count
        """
        result = self.conn.execute_read_query(query)
        return result[0]["count"] if result else 0

    def _count_roles_with_skills(self) -> int:
        """Count roles that have at least one skill mapped."""
        query = """
        MATCH (r:DTRole)-[:DT_REQUIRES_SKILL]->()
        RETURN count(DISTINCT r) AS count
        """
        result = self.conn.execute_read_query(query)
        return result[0]["count"] if result else 0

    def _check_salary_data(self) -> bool:
        """Check if salary data exists on job titles."""
        query = """
        MATCH (jt:DTJobTitle)
        WHERE jt.avg_salary > 0
        RETURN count(jt) AS count
        """
        result = self.conn.execute_read_query(query)
        return result[0]["count"] > 0 if result else False

    def _check_aggregation(self) -> bool:
        """Check if aggregation has been computed."""
        query = """
        MATCH (r:DTRole)
        WHERE r.computed_automation_score IS NOT NULL
        RETURN count(r) AS count
        """
        result = self.conn.execute_read_query(query)
        return result[0]["count"] > 0 if result else False
