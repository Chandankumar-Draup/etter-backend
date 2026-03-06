"""
Scope selector: defines the organizational boundary for a simulation.

Every simulation starts with scope selection. The scope determines which
nodes and edges the cascade engine operates on.

Scope types: organization, function, sub_function, job_family, role
Each returns a self-contained data structure the cascade engine can process.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScopeSelector:
    """Selects organizational scope and returns scoped data for simulation."""

    def __init__(self, neo4j_conn):
        self.conn = neo4j_conn

    def select(
        self,
        scope_type: str,
        scope_name: str,
    ) -> Dict[str, Any]:
        """
        Select scope and return all entities within it.

        Args:
            scope_type: 'organization', 'function', 'sub_function', 'job_family', 'role'
            scope_name: Name of the entity to scope to

        Returns:
            Dict with roles, titles, workloads, tasks, skills, technologies
        """
        logger.info(f"Selecting scope: {scope_type}={scope_name}")

        if scope_type == "function":
            return self._scope_function(scope_name)
        elif scope_type == "role":
            return self._scope_role(scope_name)
        elif scope_type == "organization":
            return self._scope_organization(scope_name)
        elif scope_type == "sub_function":
            return self._scope_sub_function(scope_name)
        elif scope_type == "job_family_group":
            return self._scope_job_family_group(scope_name)
        elif scope_type == "job_family":
            return self._scope_job_family(scope_name)
        else:
            raise ValueError(f"Unsupported scope type: {scope_type}")

    def _scope_function(self, function_name: str) -> Dict[str, Any]:
        """Get all entities within a function."""
        # Get roles
        roles_query = """
        MATCH (f:DTFunction {name: $name})
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r
        """
        role_records = self.conn.execute_read_query(roles_query, {"name": function_name})
        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]

        if not roles:
            logger.warning(f"No roles found for function: {function_name}")
            return self._empty_scope(function_name, "function")

        return self._build_scope_data(function_name, "function", roles, role_ids)

    def _scope_role(self, role_name: str) -> Dict[str, Any]:
        """Get all entities for a single role."""
        role_query = """
        MATCH (r:DTRole {name: $name})
        RETURN r
        """
        role_records = self.conn.execute_read_query(role_query, {"name": role_name})
        if not role_records:
            logger.warning(f"Role not found: {role_name}")
            return self._empty_scope(role_name, "role")

        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]
        return self._build_scope_data(role_name, "role", roles, role_ids)

    def _scope_organization(self, org_name: str) -> Dict[str, Any]:
        """Get all entities in the organization."""
        roles_query = """
        MATCH (org:DTOrganization {name: $name})
              -[:DT_CONTAINS]->(:DTFunction)
              -[:DT_CONTAINS]->(:DTSubFunction)
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r
        """
        role_records = self.conn.execute_read_query(roles_query, {"name": org_name})
        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]
        return self._build_scope_data(org_name, "organization", roles, role_ids)

    def _scope_sub_function(self, sub_function_name: str) -> Dict[str, Any]:
        """Get all entities within a sub-function."""
        roles_query = """
        MATCH (sf:DTSubFunction {name: $name})
              -[:DT_CONTAINS]->(:DTJobFamilyGroup)
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r
        """
        role_records = self.conn.execute_read_query(
            roles_query, {"name": sub_function_name}
        )
        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]

        if not roles:
            logger.warning(f"No roles found for sub-function: {sub_function_name}")
            return self._empty_scope(sub_function_name, "sub_function")

        return self._build_scope_data(sub_function_name, "sub_function", roles, role_ids)

    def _scope_job_family_group(self, jfg_name: str) -> Dict[str, Any]:
        """Get all entities within a job family group."""
        roles_query = """
        MATCH (jfg:DTJobFamilyGroup {name: $name})
              -[:DT_CONTAINS]->(:DTJobFamily)
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r
        """
        role_records = self.conn.execute_read_query(
            roles_query, {"name": jfg_name}
        )
        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]

        if not roles:
            logger.warning(f"No roles found for job family group: {jfg_name}")
            return self._empty_scope(jfg_name, "job_family_group")

        return self._build_scope_data(jfg_name, "job_family_group", roles, role_ids)

    def _scope_job_family(self, job_family_name: str) -> Dict[str, Any]:
        """Get all entities within a job family."""
        roles_query = """
        MATCH (jf:DTJobFamily {name: $name})
              -[:DT_HAS_ROLE]->(r:DTRole)
        RETURN r
        """
        role_records = self.conn.execute_read_query(
            roles_query, {"name": job_family_name}
        )
        roles = [self._node_to_dict(r["r"]) for r in role_records]
        role_ids = [r["id"] for r in roles]

        if not roles:
            logger.warning(f"No roles found for job family: {job_family_name}")
            return self._empty_scope(job_family_name, "job_family")

        return self._build_scope_data(job_family_name, "job_family", roles, role_ids)

    def _build_scope_data(
        self,
        scope_name: str,
        scope_type: str,
        roles: List[Dict],
        role_ids: List[str],
    ) -> Dict[str, Any]:
        """Build the full scope data structure from a set of roles."""
        # Get titles for these roles
        titles = self._get_titles(role_ids)
        # Get workloads
        workloads = self._get_workloads(role_ids)
        workload_ids = [wl["id"] for wl in workloads]
        # Get tasks
        tasks = self._get_tasks(workload_ids)
        # Get task-skill mappings (DTTask → DTSkill with relevance)
        task_ids = [t["id"] for t in tasks]
        task_skill_mappings = self._get_task_skill_mappings(task_ids)
        # Get skills
        skills = self._get_skills(role_ids)
        # Get technologies
        technologies = self._get_technologies(role_ids)
        # Enrich roles with skill_ids (skills are relationships, not node properties)
        self._enrich_roles_with_skill_ids(roles, role_ids)

        scope = {
            "scope_name": scope_name,
            "scope_type": scope_type,
            "roles": roles,
            "job_titles": titles,
            "workloads": workloads,
            "tasks": tasks,
            "task_skill_mappings": task_skill_mappings,
            "skills": skills,
            "technologies": technologies,
            "summary": {
                "role_count": len(roles),
                "title_count": len(titles),
                "workload_count": len(workloads),
                "task_count": len(tasks),
                "skill_count": len(skills),
                "tech_count": len(technologies),
                "total_headcount": sum(r.get("computed_headcount") or 0 for r in roles),
            },
        }

        logger.info(
            f"Scope selected: {scope_type}={scope_name}, "
            f"{len(roles)} roles, {len(tasks)} tasks, {len(skills)} skills"
        )
        return scope

    def _get_titles(self, role_ids: List[str]) -> List[Dict]:
        query = """
        UNWIND $role_ids AS rid
        MATCH (r:DTRole {id: rid})-[:DT_HAS_TITLE]->(jt:DTJobTitle)
        RETURN jt
        """
        records = self.conn.execute_read_query(query, {"role_ids": role_ids})
        return [self._node_to_dict(r["jt"]) for r in records]

    def _get_workloads(self, role_ids: List[str]) -> List[Dict]:
        query = """
        UNWIND $role_ids AS rid
        MATCH (r:DTRole {id: rid})-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
        RETURN wl
        """
        records = self.conn.execute_read_query(query, {"role_ids": role_ids})
        return [self._node_to_dict(r["wl"]) for r in records]

    def _get_tasks(self, workload_ids: List[str]) -> List[Dict]:
        if not workload_ids:
            return []
        query = """
        UNWIND $wl_ids AS wid
        MATCH (wl:DTWorkload {id: wid})-[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN t
        """
        records = self.conn.execute_read_query(query, {"wl_ids": workload_ids})
        return [self._node_to_dict(r["t"]) for r in records]

    def _get_task_skill_mappings(self, task_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch task-to-skill mappings via (DTTask)-[:DT_REQUIRES_SKILL]->(DTSkill).

        Returns:
            Dict mapping task_id to list of {skill_id, skill_name, relevance}
        """
        if not task_ids:
            return {}
        query = """
        UNWIND $task_ids AS tid
        MATCH (t:DTTask {id: tid})-[rel:DT_REQUIRES_SKILL]->(s:DTSkill)
        RETURN t.id AS task_id, s.id AS skill_id, s.name AS skill_name,
               rel.relevance AS relevance
        """
        records = self.conn.execute_read_query(query, {"task_ids": task_ids})
        mappings: Dict[str, List[Dict]] = {}
        for r in records:
            mappings.setdefault(r["task_id"], []).append({
                "skill_id": r["skill_id"],
                "skill_name": r["skill_name"],
                "relevance": r.get("relevance", "SECONDARY"),
            })
        return mappings

    def _get_skills(self, role_ids: List[str]) -> List[Dict]:
        query = """
        UNWIND $role_ids AS rid
        MATCH (r:DTRole {id: rid})-[:DT_REQUIRES_SKILL]->(s:DTSkill)
        RETURN DISTINCT s
        """
        records = self.conn.execute_read_query(query, {"role_ids": role_ids})
        return [self._node_to_dict(r["s"]) for r in records]

    def _enrich_roles_with_skill_ids(self, roles: List[Dict], role_ids: List[str]):
        """Add skill_ids list to each role dict.

        Skills are stored as DT_REQUIRES_SKILL relationships, not as a property
        on DTRole nodes. This method queries the relationships and attaches
        skill_ids to each role so downstream code (e.g. skills_strategy) can
        access role.skill_ids directly.
        """
        query = """
        UNWIND $role_ids AS rid
        MATCH (r:DTRole {id: rid})-[:DT_REQUIRES_SKILL]->(s:DTSkill)
        RETURN r.id AS role_id, collect(s.id) AS skill_ids
        """
        records = self.conn.execute_read_query(query, {"role_ids": role_ids})
        skill_map = {r["role_id"]: r["skill_ids"] for r in records}
        for role in roles:
            role["skill_ids"] = skill_map.get(role["id"], [])

    def _get_technologies(self, role_ids: List[str]) -> List[Dict]:
        query = """
        UNWIND $role_ids AS rid
        MATCH (r:DTRole {id: rid})-[:DT_USES_TECHNOLOGY]->(t:DTTechnology)
        RETURN DISTINCT t
        """
        records = self.conn.execute_read_query(query, {"role_ids": role_ids})
        return [self._node_to_dict(r["t"]) for r in records]

    @staticmethod
    def _node_to_dict(node) -> Dict[str, Any]:
        """Convert a Neo4j node to a plain dict."""
        if isinstance(node, dict):
            return node
        return dict(node)

    @staticmethod
    def _empty_scope(name: str, scope_type: str) -> Dict[str, Any]:
        return {
            "scope_name": name,
            "scope_type": scope_type,
            "roles": [], "job_titles": [], "workloads": [],
            "tasks": [], "task_skill_mappings": {}, "skills": [], "technologies": [],
            "summary": {
                "role_count": 0, "title_count": 0, "workload_count": 0,
                "task_count": 0, "skill_count": 0, "tech_count": 0,
                "total_headcount": 0,
            },
        }
