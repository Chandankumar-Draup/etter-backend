"""
Neo4j graph schema definition for the Digital Twin.

Defines node labels, relationship types, constraints, and indexes.
The schema is the structural contract that all graph operations respect.

Design principle (Meadows): Structure determines behavior.
The schema design directly determines what questions the twin can answer.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Node labels
# ──────────────────────────────────────────────────────────────
NODE_LABELS = [
    "DTOrganization",
    "DTFunction",
    "DTSubFunction",
    "DTJobFamilyGroup",
    "DTJobFamily",
    "DTRole",
    "DTJobTitle",
    "DTWorkload",
    "DTTask",
    "DTSkill",
    "DTTechnology",
    "DTWorkflow",
    "DTWorkflowTask",
    "DTScenario",
    "DTSimulationResult",
]

# ──────────────────────────────────────────────────────────────
# Relationship types
# ──────────────────────────────────────────────────────────────
RELATIONSHIP_TYPES = [
    # Taxonomy containment (hierarchical)
    "DT_CONTAINS",          # Organization→Function→SubFunction→JFG→JF
    # Work structure
    "DT_HAS_ROLE",          # JobFamily→Role
    "DT_HAS_TITLE",         # Role→JobTitle
    "DT_HAS_WORKLOAD",      # Role→Workload
    "DT_CONTAINS_TASK",     # Workload→Task
    # Capabilities
    "DT_REQUIRES_SKILL",    # Role/Task→Skill
    "DT_USES_TECHNOLOGY",   # Role→Technology
    "DT_AFFECTED_BY",       # Task→Technology (with shift, time_reduction)
    # Cross-role
    "DT_ADJACENT_TO",       # Role→Role (with score)
    "DT_PART_OF_WORKFLOW",  # WorkflowTask→Workflow
    "DT_TASK_USES_ROLE",    # WorkflowTask→Role
    # Simulation
    "DT_APPLIED_TO",        # Scenario→(Org|Function|Role)
    "DT_PRODUCES",          # Scenario→SimulationResult
]


def get_constraint_queries() -> List[str]:
    """Return Cypher queries to create uniqueness constraints."""
    constraints = []
    for label in NODE_LABELS:
        name = f"constraint_{label.lower()}_id"
        constraints.append(
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    return constraints


def get_index_queries() -> List[str]:
    """Return Cypher queries to create performance indexes."""
    indexes = [
        # Name indexes for scope selection and display
        "CREATE INDEX idx_dt_role_name IF NOT EXISTS FOR (n:DTRole) ON (n.name)",
        "CREATE INDEX idx_dt_function_name IF NOT EXISTS FOR (n:DTFunction) ON (n.name)",
        "CREATE INDEX idx_dt_skill_name IF NOT EXISTS FOR (n:DTSkill) ON (n.name)",
        "CREATE INDEX idx_dt_tech_name IF NOT EXISTS FOR (n:DTTechnology) ON (n.name)",
        # Classification index for task filtering
        "CREATE INDEX idx_dt_task_classification IF NOT EXISTS FOR (n:DTTask) ON (n.classification)",
        # Automation score for simulation queries
        "CREATE INDEX idx_dt_task_automation IF NOT EXISTS FOR (n:DTTask) ON (n.automation_potential)",
        "CREATE INDEX idx_dt_role_automation IF NOT EXISTS FOR (n:DTRole) ON (n.automation_score)",
        # Workflow and workflow task lookups
        "CREATE INDEX idx_dt_workflow_name IF NOT EXISTS FOR (n:DTWorkflow) ON (n.name)",
        "CREATE INDEX idx_dt_wftask_workflow IF NOT EXISTS FOR (n:DTWorkflowTask) ON (n.workflow_id)",
        # Scenario lookup
        "CREATE INDEX idx_dt_scenario_name IF NOT EXISTS FOR (n:DTScenario) ON (n.name)",
    ]
    return indexes


def get_drop_queries() -> List[str]:
    """Return Cypher queries to drop all Digital Twin data (DT-prefixed labels only)."""
    queries = []
    for label in NODE_LABELS:
        queries.append(f"MATCH (n:{label}) DETACH DELETE n")
    return queries


def apply_schema(neo4j_conn) -> None:
    """Apply constraints and indexes to Neo4j."""
    logger.info("Applying Digital Twin graph schema...")

    for query in get_constraint_queries():
        try:
            neo4j_conn.execute_write_query(query)
        except Exception as e:
            # Constraint may already exist
            logger.debug(f"Constraint query note: {e}")

    for query in get_index_queries():
        try:
            neo4j_conn.execute_write_query(query)
        except Exception as e:
            logger.debug(f"Index query note: {e}")

    logger.info(f"Schema applied: {len(NODE_LABELS)} constraints, {len(get_index_queries())} indexes")


def drop_all_dt_data(neo4j_conn) -> None:
    """Drop all Digital Twin nodes and relationships. Use with caution."""
    logger.warning("Dropping ALL Digital Twin data from Neo4j...")
    for query in get_drop_queries():
        neo4j_conn.execute_write_query(query)
    logger.info("All Digital Twin data removed.")
