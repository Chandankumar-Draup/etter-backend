"""
Schema context builder for the Digital Twin graph.

Loads the DT graph schema once at startup (node types, relationships,
properties, live entity names/counts) and builds a compact context
string that the LLM uses to generate accurate Cypher queries.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Static schema definition ────────────────────────────────────────
# This is the ground truth for the DT graph. It never changes at runtime.

STATIC_SCHEMA = """
## Node Types & Key Properties

DTOrganization: id, name, industry, sub_industry, size, revenue_millions, hq_location, computed_headcount, computed_total_cost, automation_score
DTFunction: id, name, headcount, computed_headcount, computed_total_cost, automation_score
DTSubFunction: id, name, total_headcount, total_cost, automation_score
DTJobFamilyGroup: id, name, total_headcount, total_cost, automation_score
DTJobFamily: id, name, total_headcount, total_cost, avg_salary, automation_score
DTRole: id, name, description, total_headcount, avg_salary, automation_score, workload_count
DTJobTitle: id, name, career_band, level, typical_experience_years, headcount, avg_salary
DTWorkload: id, name, description, effort_allocation_pct, automation_level, task_count
DTTask: id, name, description, classification, time_allocation_pct, automation_potential (float 0-100), automation_level (one of: human_only, human_led, shared, ai_led, ai_only)
DTSkill: id, name, category, skill_type (technical / soft / domain), lifecycle_status, market_demand_trend
DTTechnology: id, name, category, vendor, capabilities (list), license_cost_tier, adoption_stage

## Relationships (all directed)

(DTOrganization)-[:DT_CONTAINS]->(DTFunction)
(DTFunction)-[:DT_CONTAINS]->(DTSubFunction)
(DTSubFunction)-[:DT_CONTAINS]->(DTJobFamilyGroup)
(DTJobFamilyGroup)-[:DT_CONTAINS]->(DTJobFamily)
(DTJobFamily)-[:DT_HAS_ROLE]->(DTRole)
(DTRole)-[:DT_HAS_TITLE]->(DTJobTitle)
(DTRole)-[:DT_HAS_WORKLOAD]->(DTWorkload)
(DTWorkload)-[:DT_CONTAINS_TASK]->(DTTask)
(DTRole)-[:DT_REQUIRES_SKILL]->(DTSkill)
(DTTask)-[:DT_REQUIRES_SKILL {relevance: "PRIMARY"|"SECONDARY"}]->(DTSkill)
(DTRole)-[:DT_USES_TECHNOLOGY]->(DTTechnology)
(DTTask)-[:DT_AFFECTED_BY {shift, time_reduction}]->(DTTechnology)
(DTRole)-[:DT_ADJACENT_TO {score: float}]->(DTRole)

## Hierarchy Pattern

The taxonomy is: Organization > Function > SubFunction > JobFamilyGroup > JobFamily > Role.
All containment uses DT_CONTAINS except the last hop which is DT_HAS_ROLE.

To get roles under a Function (traversing through sub-levels):
  MATCH (f:DTFunction {name: $name})-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)

To get roles under a SubFunction:
  MATCH (sf:DTSubFunction {name: $name})-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)

## Key Conventions

- automation_score and automation_potential range 0–100 (0 = fully manual, 100 = fully automated); display with round() and a % suffix
- automation_level is an enum: human_only, human_led, shared, ai_led, ai_only
- total_headcount is the primary headcount field on roles/families
- computed_headcount on Function/Organization is the aggregated sum
- Property values are CASE-SENSITIVE
- Always add LIMIT (max 50) unless doing count/sum aggregations
- Use variable-length paths [:DT_CONTAINS*] to traverse the hierarchy
""".strip()

# ── Example queries (few-shot) ──────────────────────────────────────

EXAMPLE_QUERIES = """
## Example Queries

Q: How many roles are in Claims Management?
MATCH (f:DTFunction {name: "Claims Management"})-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
RETURN count(r) AS role_count

Q: List all roles with their headcount and automation score in Claims Management
MATCH (f:DTFunction {name: "Claims Management"})-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
RETURN r.name AS role, r.total_headcount AS headcount, round(r.automation_score) AS automation_pct
ORDER BY r.total_headcount DESC

Q: What skills does the Claims Adjuster role require?
MATCH (r:DTRole {name: "Claims Adjuster"})-[:DT_REQUIRES_SKILL]->(s:DTSkill)
RETURN s.name AS skill, s.category, s.skill_type
ORDER BY s.category, s.name

Q: Which tasks have high automation potential for Claims Adjuster?
MATCH (r:DTRole {name: "Claims Adjuster"})-[:DT_HAS_WORKLOAD]->(w:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
WHERE t.automation_potential > 60
RETURN t.name AS task, t.automation_potential, t.automation_level, w.name AS workload
ORDER BY t.automation_potential DESC

Q: What is the total headcount across all functions?
MATCH (f:DTFunction)
RETURN f.name AS function_name, f.computed_headcount AS headcount, round(f.automation_score) AS automation_pct
ORDER BY f.computed_headcount DESC

Q: Which roles are most at risk from automation?
MATCH (f:DTFunction)-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
WHERE r.automation_score > 50 AND r.total_headcount > 0
RETURN r.name AS role, f.name AS function_name, r.total_headcount AS headcount, round(r.automation_score) AS automation_pct
ORDER BY r.automation_score * r.total_headcount DESC
LIMIT 20

Q: What technologies are used across the organization?
MATCH (r:DTRole)-[:DT_USES_TECHNOLOGY]->(t:DTTechnology)
RETURN t.name AS technology, t.vendor, t.category, count(r) AS roles_using
ORDER BY roles_using DESC

Q: Show workload breakdown for Claims Adjuster
MATCH (r:DTRole {name: "Claims Adjuster"})-[:DT_HAS_WORKLOAD]->(w:DTWorkload)
RETURN w.name AS workload, w.effort_allocation_pct AS effort_pct, w.automation_level
ORDER BY w.effort_allocation_pct DESC

Q: Which roles are adjacent or similar to Claims Adjuster?
MATCH (r:DTRole {name: "Claims Adjuster"})-[:DT_ADJACENT_TO]->(r2:DTRole)
RETURN r2.name AS similar_role, r2.automation_score
ORDER BY r2.automation_score DESC

Q: What is the task distribution by automation level across a function?
MATCH (f:DTFunction {name: "Claims Management"})-[:DT_CONTAINS*]->(jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)-[:DT_HAS_WORKLOAD]->(w:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
RETURN t.automation_level AS level, count(t) AS task_count, round(avg(t.automation_potential)) AS avg_potential_pct
ORDER BY avg_potential_pct DESC

Q: Compare automation scores across all job families
MATCH (jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
RETURN jf.name AS job_family, count(r) AS roles, round(avg(r.automation_score)) AS avg_automation_pct, sum(r.total_headcount) AS total_headcount
ORDER BY avg_automation_pct DESC
LIMIT 20

Q: What is the organization overview?
MATCH (o:DTOrganization)
RETURN o.name AS organization, o.industry, o.computed_headcount AS total_headcount, round(o.automation_score) AS automation_pct
""".strip()


class SchemaContext:
    """
    Loads and caches the DT graph schema context for LLM prompts.

    Call `load(neo4j_conn)` once at startup. Then use `context` to get
    the full schema string for Cypher generation prompts.
    """

    def __init__(self):
        self._context: Optional[str] = None
        self._entity_names: Dict[str, List[str]] = {}
        self._node_counts: Dict[str, int] = {}

    @property
    def context(self) -> str:
        """Full schema context string for LLM prompts."""
        if self._context is None:
            # Fallback: static schema only (no live data)
            return f"# Digital Twin Workforce Graph Schema\n\n{STATIC_SCHEMA}\n\n{EXAMPLE_QUERIES}"
        return self._context

    @property
    def entity_names(self) -> Dict[str, List[str]]:
        """Known entity names by type (for validation / suggestions)."""
        return self._entity_names

    def load(self, neo4j_conn: Any) -> None:
        """
        Load live graph metadata from Neo4j and build the full context.

        Called once at startup. Fast queries only (~100ms total).
        """
        try:
            # Node counts
            counts = neo4j_conn.execute_read_query(
                "MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'DT') "
                "WITH [l IN labels(n) WHERE l STARTS WITH 'DT'][0] AS label "
                "RETURN label, count(*) AS cnt ORDER BY cnt DESC"
            )
            self._node_counts = {r["label"]: r["cnt"] for r in counts} if counts else {}

            # Function names
            funcs = neo4j_conn.execute_read_query(
                "MATCH (f:DTFunction) RETURN f.name AS name ORDER BY f.name"
            )
            self._entity_names["functions"] = [r["name"] for r in funcs] if funcs else []

            # Technology names
            techs = neo4j_conn.execute_read_query(
                "MATCH (t:DTTechnology) RETURN t.name AS name ORDER BY t.name"
            )
            self._entity_names["technologies"] = [r["name"] for r in techs] if techs else []

            # Skill categories
            cats = neo4j_conn.execute_read_query(
                "MATCH (s:DTSkill) RETURN DISTINCT s.category AS cat ORDER BY cat"
            )
            self._entity_names["skill_categories"] = [r["cat"] for r in cats if r["cat"]] if cats else []

            # Role names (sample — top 30 by headcount)
            roles = neo4j_conn.execute_read_query(
                "MATCH (r:DTRole) RETURN r.name AS name "
                "ORDER BY r.total_headcount DESC LIMIT 30"
            )
            self._entity_names["roles"] = [r["name"] for r in roles] if roles else []

            # Build enriched context
            self._context = self._build_context()

            logger.info(
                "Schema context loaded: %d node types, %d functions, %d technologies, %d roles",
                len(self._node_counts),
                len(self._entity_names.get("functions", [])),
                len(self._entity_names.get("technologies", [])),
                len(self._entity_names.get("roles", [])),
            )

        except Exception as e:
            logger.warning("Failed to load live schema context, using static fallback: %s", e)
            self._context = f"# Digital Twin Workforce Graph Schema\n\n{STATIC_SCHEMA}\n\n{EXAMPLE_QUERIES}"

    def _build_context(self) -> str:
        """Assemble the full context string with live data."""
        parts = ["# Digital Twin Workforce Graph Schema\n"]

        # Live counts
        if self._node_counts:
            parts.append("## Graph Size")
            for label, cnt in self._node_counts.items():
                parts.append(f"- {label}: {cnt:,} nodes")
            parts.append("")

        # Known entity names
        if self._entity_names.get("functions"):
            parts.append(f"## Available Functions\n{', '.join(self._entity_names['functions'])}\n")
        if self._entity_names.get("technologies"):
            parts.append(f"## Available Technologies\n{', '.join(self._entity_names['technologies'])}\n")
        if self._entity_names.get("skill_categories"):
            parts.append(f"## Skill Categories\n{', '.join(self._entity_names['skill_categories'])}\n")
        if self._entity_names.get("roles"):
            parts.append(f"## Sample Roles (top by headcount)\n{', '.join(self._entity_names['roles'])}\n")

        parts.append(STATIC_SCHEMA)
        parts.append("")
        parts.append(EXAMPLE_QUERIES)

        return "\n".join(parts)


# Module-level singleton
schema_context = SchemaContext()
