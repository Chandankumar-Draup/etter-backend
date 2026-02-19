"""
Data loader: JSON files → Neo4j graph.

Loads generated data into Neo4j using batch UNWIND operations.
All operations are idempotent (MERGE) - safe to re-run.

Supports both per-function directory structure (preferred) and
legacy flat-file format (backward compat fallback).

Load order respects the dependency graph:
  1. Schema (constraints + indexes)
  2. Taxonomy nodes (org → function → subfunc → jfg → jf)
  3. Work entities (roles → titles → workloads → tasks)
  4. Capability entities (skills → technologies)
  5. Workflows (workflows → workflow tasks)
  6. Relationships:
     - Taxonomy containment (DT_CONTAINS)
     - Work structure (DT_HAS_ROLE, DT_HAS_TITLE, DT_HAS_WORKLOAD, DT_CONTAINS_TASK)
     - Role capabilities (DT_REQUIRES_SKILL, DT_USES_TECHNOLOGY)
     - Task skills (DT_REQUIRES_SKILL {relevance} from role_skill_mapping data)
     - Workflow links (DT_PART_OF_WORKFLOW, DT_TASK_USES_ROLE)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import OutputConfig
from draup_world_model.digital_twin.graph import queries
from draup_world_model.digital_twin.graph.schema import apply_schema

logger = logging.getLogger(__name__)


class GraphLoader:
    """Loads Digital Twin data from JSON into Neo4j."""

    def __init__(self, neo4j_conn, output: OutputConfig = None):
        self.conn = neo4j_conn
        self.output = output or OutputConfig()
        self._stats = {}

    def _load_json(self, path: Path) -> Any:
        """Load JSON file, return None if not found."""
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return None
        with open(path) as f:
            return json.load(f)

    def _load_entity(self, entity: str, flat_file_attr: Optional[str] = None) -> Optional[List[Dict]]:
        """Load entity data, preferring per-function directory over flat file.

        Tries:
          1. Per-function directory  (e.g. roles/*.json)
          2. Legacy flat file        (e.g. roles.json)
        """
        entity_dir = self.output.entity_dir(entity)
        if entity_dir.exists():
            files = sorted(entity_dir.glob("*.json"))
            if files:
                items: List[Dict] = []
                for path in files:
                    with open(path) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            items.extend(data)
                        elif isinstance(data, dict):
                            items.append(data)
                if items:
                    logger.info(f"  Loaded {len(items)} {entity} from {len(files)} files")
                    return items

        # Fallback to flat file
        if flat_file_attr:
            flat_path = getattr(self.output, flat_file_attr, None)
            if flat_path and flat_path.exists():
                logger.info(f"  Loading {entity} from legacy flat file")
                return self._load_json(flat_path)

        return None

    def _batch_write(self, query: str, items: List[Dict], label: str) -> int:
        """Execute a batch write and track stats."""
        if not items:
            return 0
        self.conn.execute_write_query(query, {"items": items})
        count = len(items) if isinstance(items, list) else 1
        self._stats[label] = count
        logger.info(f"  Loaded {count} {label}")
        return count

    def load_taxonomy(self) -> Dict[str, int]:
        """Load taxonomy nodes (Organization → Function → SubFunction → JFG → JF)."""
        logger.info("Loading taxonomy...")
        taxonomy = self._load_json(self.output.taxonomy_file)
        if not taxonomy:
            raise FileNotFoundError(f"Taxonomy file not found: {self.output.taxonomy_file}")

        org = taxonomy["organization"]
        self._batch_write(queries.MERGE_ORGANIZATION, [org], "organizations")
        self._batch_write(queries.MERGE_FUNCTIONS, taxonomy["functions"], "functions")
        self._batch_write(queries.MERGE_SUB_FUNCTIONS, taxonomy["sub_functions"], "sub_functions")
        self._batch_write(queries.MERGE_JOB_FAMILY_GROUPS, taxonomy["job_family_groups"], "job_family_groups")
        self._batch_write(queries.MERGE_JOB_FAMILIES, taxonomy["job_families"], "job_families")
        return self._stats

    def load_roles(self) -> int:
        """Load roles."""
        logger.info("Loading roles...")
        roles = self._load_entity("roles", "roles_file")
        if not roles:
            return 0
        return self._batch_write(queries.MERGE_ROLES, roles, "roles")

    def load_job_titles(self) -> int:
        """Load job titles."""
        logger.info("Loading job titles...")
        titles = self._load_entity("job_titles", "job_titles_file")
        if not titles:
            return 0
        return self._batch_write(queries.MERGE_JOB_TITLES, titles, "job_titles")

    def load_workloads(self) -> int:
        """Load workloads."""
        logger.info("Loading workloads...")
        workloads = self._load_entity("workloads", "workloads_file")
        if not workloads:
            return 0
        return self._batch_write(queries.MERGE_WORKLOADS, workloads, "workloads")

    def load_tasks(self) -> int:
        """Load tasks."""
        logger.info("Loading tasks...")
        tasks = self._load_entity("tasks", "tasks_file")
        if not tasks:
            return 0
        return self._batch_write(queries.MERGE_TASKS, tasks, "tasks")

    def load_skills(self) -> int:
        """Load skills."""
        logger.info("Loading skills...")
        # Try new catalog location first, then directory, then flat file
        skills = self._load_json(self.output.skills_catalog_file)
        if not skills:
            skills = self._load_entity("skills", "skills_file")
        if not skills:
            return 0
        return self._batch_write(queries.MERGE_SKILLS, skills, "skills")

    def load_technologies(self) -> int:
        """Load technologies."""
        logger.info("Loading technologies...")
        # Try new catalog location first, then directory, then flat file
        techs = self._load_json(self.output.technologies_catalog_file)
        if not techs:
            techs = self._load_entity("technologies", "technologies_file")
        if not techs:
            return 0
        return self._batch_write(queries.MERGE_TECHNOLOGIES, techs, "technologies")

    # Complex nested fields stripped before Neo4j loading (kept in JSON files).
    #
    # Workflow (16 fields total): 9 stored in Neo4j, 1 extracted (tasks), 6 stripped:
    _WORKFLOW_COMPLEX_FIELDS = [
        "summary",              # {total_tasks, total_hours, automation_level, *_task_count}
        "workflow_metrics",     # {estimated_fte_impact, time_savings, timeline, roi_potential}
        "quick_wins",           # [{opportunity_type, hours_saved, priority, ...}]
        "opportunities",        # [{opportunity_type, hours_saved, complexity, ...}]
        "patterns",             # [{pattern_name, description, affected_tasks, impact, ...}]
        "recommendations",      # {primary_strategy, key_actions, risks, success_factors}
    ]
    # Workflow task (18 fields total): 12 stored in Neo4j, 6 stripped:
    _TASK_COMPLEX_FIELDS = [
        "score_breakdown",      # {time_investment, strategic_value, error_reduction, scalability}
        "skills_required",      # [skill_name, ...]
        "primary_role",         # {title, seniority, role_id}
        "supporting_roles",     # [{title, seniority, role_id}]
        "dependencies",         # [sequence_number, ...]
        "expected_output",      # string (too long for Neo4j property)
    ]

    def load_workflows(self) -> int:
        """Load workflows and their workflow tasks into Neo4j.

        Each workflow JSON has 16 fields. Of these:
        - 9 scalar fields → stored as DTWorkflow node properties
        - 1 array field (tasks) → extracted and loaded as DTWorkflowTask nodes
        - 6 complex fields → stripped (summary, metrics, patterns, etc.)

        Each workflow task has 18 fields. Of these:
        - 12 scalar fields → stored as DTWorkflowTask node properties
        - 6 complex fields → stripped (score_breakdown, primary_role, etc.)

        Stripped fields remain accessible in the JSON files for reporting.
        """
        logger.info("Loading workflows...")
        workflows = self._load_entity("workflows", "workflows_file")
        if not workflows:
            return 0

        wf_nodes = []
        all_tasks = []
        for wf in workflows:
            tasks = wf.pop("tasks", [])
            # Strip complex fields not storable in Neo4j
            for key in self._WORKFLOW_COMPLEX_FIELDS:
                wf.pop(key, None)
            wf_nodes.append(wf)
            for task in tasks:
                for key in self._TASK_COMPLEX_FIELDS:
                    task.pop(key, None)
                all_tasks.append(task)

        self._batch_write(queries.MERGE_WORKFLOWS, wf_nodes, "workflows")
        if all_tasks:
            self._batch_write(
                queries.MERGE_WORKFLOW_TASKS, all_tasks, "workflow_tasks"
            )
        return len(wf_nodes)

    def create_relationships(self) -> Dict[str, int]:
        """Create all relationships between nodes."""
        logger.info("Creating relationships...")
        rel_queries = [
            ("org→functions", queries.LINK_ORG_TO_FUNCTIONS),
            ("function→subfunctions", queries.LINK_FUNCTION_TO_SUBFUNCTIONS),
            ("subfunction→jfg", queries.LINK_SUBFUNCTION_TO_JFG),
            ("jfg→jf", queries.LINK_JFG_TO_JF),
            ("jf→roles", queries.LINK_JF_TO_ROLES),
            ("role→titles", queries.LINK_ROLE_TO_TITLES),
            ("role→workloads", queries.LINK_ROLE_TO_WORKLOADS),
            ("workload→tasks", queries.LINK_WORKLOAD_TO_TASKS),
            ("workflow→tasks", queries.LINK_WORKFLOW_TASKS),
            ("task→roles", queries.LINK_WORKFLOW_TASK_ROLES),
        ]
        for name, query in rel_queries:
            try:
                self.conn.execute_write_query(query)
                logger.info(f"  Created {name} relationships")
            except Exception as e:
                logger.warning(f"  Relationship {name} note: {e}")

        # Mappings that require building arrays from entity data
        self._create_skill_mappings()
        self._create_tech_mappings()
        self._create_adjacency_mappings()
        self._create_task_skill_mappings()

        return self._stats

    def _create_skill_mappings(self):
        """Create role→skill relationships from roles data."""
        roles = self._load_entity("roles", "roles_file")
        if not roles:
            return
        mappings = []
        for role in roles:
            for skill_id in role.get("skill_ids", []):
                mappings.append({"role_id": role["id"], "skill_id": skill_id})
        if mappings:
            self.conn.execute_write_query(queries.LINK_ROLE_TO_SKILLS, {"mappings": mappings})
            logger.info(f"  Created {len(mappings)} role→skill relationships")

    def _create_tech_mappings(self):
        """Create role→technology relationships from roles data."""
        roles = self._load_entity("roles", "roles_file")
        if not roles:
            return
        mappings = []
        for role in roles:
            for tech_id in role.get("technology_ids", []):
                mappings.append({"role_id": role["id"], "tech_id": tech_id})
        if mappings:
            self.conn.execute_write_query(queries.LINK_ROLE_TO_TECHNOLOGIES, {"mappings": mappings})
            logger.info(f"  Created {len(mappings)} role→tech relationships")

    def _create_adjacency_mappings(self):
        """Create role→role adjacency relationships from roles data."""
        roles = self._load_entity("roles", "roles_file")
        if not roles:
            return
        mappings = []
        for role in roles:
            for adj_id in role.get("adjacency_role_ids", []):
                mappings.append({"role_id": role["id"], "adjacent_role_id": adj_id})
        if mappings:
            self.conn.execute_write_query(queries.LINK_ADJACENT_ROLES, {"mappings": mappings})
            logger.info(f"  Created {len(mappings)} role→role adjacency relationships")

    def _create_task_skill_mappings(self):
        """Create task→skill relationships from role_skill_mapping data.

        Reads the denormalized role_skill_mapping output and creates
        (DTTask)-[:DT_REQUIRES_SKILL {relevance}]->(DTSkill) relationships.
        """
        role_mappings = self._load_entity("role_skill_mapping")
        if not role_mappings:
            logger.info("  No task-skill mapping data found, skipping")
            return

        mappings = []
        for role_data in role_mappings:
            for wl in role_data.get("workloads", []):
                for task in wl.get("tasks", []):
                    for ms in task.get("mapped_skills", []):
                        if ms.get("skill_id"):
                            mappings.append({
                                "task_id": task["task_id"],
                                "skill_id": ms["skill_id"],
                                "relevance": ms.get("relevance", "SECONDARY"),
                            })

        if mappings:
            self.conn.execute_write_query(
                queries.LINK_TASK_TO_SKILLS, {"mappings": mappings}
            )
            self._stats["task_skill_mappings"] = len(mappings)
            logger.info(f"  Created {len(mappings)} task→skill relationships")

    def load_all(self) -> Dict[str, int]:
        """Execute the full load pipeline."""
        logger.info("="*60)
        logger.info("DIGITAL TWIN GRAPH LOADING")
        logger.info("="*60)

        # Step 1: Schema
        apply_schema(self.conn)

        # Step 2: Taxonomy nodes
        self.load_taxonomy()

        # Step 3: Work entities
        self.load_roles()
        self.load_job_titles()
        self.load_workloads()
        self.load_tasks()

        # Step 4: Capabilities
        self.load_skills()
        self.load_technologies()

        # Step 5: Workflows
        self.load_workflows()

        # Step 6: Relationships
        self.create_relationships()

        logger.info("="*60)
        logger.info(f"LOAD COMPLETE: {self._stats}")
        logger.info("="*60)
        return self._stats
