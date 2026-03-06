"""
Task generator.

Generates 5-8 tasks per workload using batch LLM calls.
Tasks are atomic units of work - the most granular level.
This is where cascade simulation starts (technology -> task reclassification).

Batch strategy: One LLM call per ~5 workloads -> generates all tasks for those workloads.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
    TASK_CLASSIFICATIONS,
    AUTOMATION_LEVELS,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

TASK_PROMPT = """You are an expert in task analysis and job decomposition for the insurance industry.

For each workload below, generate {tasks_per_workload} specific tasks. Tasks are atomic units of work performed within a workload.

Workloads (with their parent role for context):
{workloads_list}

Task classification categories (Etter 6-category AI automation potential):
- directive: Fully automatable tasks with minimal human input (scheduling, standard validations, routine data checks)
- feedback_loop: Automatable tasks requiring feedback adjustments (analyzing metrics, iterating on reports, tuning workflows)
- learning: Tasks requiring knowledge acquisition and understanding (researching trends, learning frameworks, studying best practices)
- validation: Tasks where AI helps verify and improve work (reviewing outputs, verifying compliance, quality assurance)
- task_iteration: Tasks needing human-AI collaboration (co-authoring documents, building components with AI, iterative design)
- negligibility: Tasks that cannot be automated using AI (relationship building, strategic discussions, trust-building)

Automation levels: {automation_levels}

For each task:
- name: Specific, actionable task name
- workload: Exact workload name from the list above
- description: 1 sentence description
- classification: One of the 6 categories above
- time_allocation_pct: Percentage of workload time (tasks within a workload should sum to ~100)
- automation_potential: 0-100 score for AI automation potential
- automation_level: Current automation level

Return a JSON array:
[
  {{
    "name": "...",
    "workload": "...",
    "description": "...",
    "classification": "...",
    "time_allocation_pct": 0.0,
    "automation_potential": 0.0,
    "automation_level": "..."
  }}
]

Return ONLY the JSON array, no other text.
"""


class TaskGenerator(BaseGenerator):
    """Generates tasks for workloads using batch LLM calls."""

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        gen_config: Optional[GenerationConfig] = None,
        company: Optional[CompanyProfile] = None,
        output: Optional[OutputConfig] = None,
    ):
        super().__init__(llm_config)
        self.gen_config = gen_config or GenerationConfig()
        self.company = company or CompanyProfile()
        self.output = output or OutputConfig()

    def generate(
        self,
        workloads: List[Dict[str, Any]],
        roles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate tasks for workloads in batches, with incremental resumability.

        Loads existing tasks from disk and only generates for workloads that
        don't already have tasks. This means failed batches can be retried
        without regenerating everything.
        """
        self.output.ensure_dirs()

        # Build role_id -> name lookup
        role_id_to_name = {r["id"]: r["name"] for r in roles}

        # Map workload → function via role for per-function file output
        role_id_to_func = {r["id"]: r.get("function_id", "unknown") for r in roles}
        wl_id_to_func = {
            wl["id"]: wl.get("function_id") or role_id_to_func.get(wl.get("role_id"), "unknown")
            for wl in workloads
        }

        # Load existing tasks and find which workloads already have tasks
        existing_tasks = self.load_from_dir(self.output.entity_dir("tasks"))
        covered_wl_ids = set(t["workload_id"] for t in existing_tasks)
        pending_wls = [wl for wl in workloads if wl["id"] not in covered_wl_ids]

        if not pending_wls:
            logger.info(f"All {len(workloads)} workloads already have tasks, skipping")
            return existing_tasks

        logger.info(
            f"{len(pending_wls)} of {len(workloads)} workloads need tasks "
            f"({len(existing_tasks)} existing tasks kept)"
        )

        new_tasks = []
        batch_size = self.gen_config.tasks_per_batch

        for i in range(0, len(pending_wls), batch_size):
            batch_wls = pending_wls[i:i + batch_size]
            wls_str = "\n".join(
                f"- Workload: \"{wl['name']}\" (Role: {role_id_to_name.get(wl['role_id'], 'Unknown')}, "
                f"Effort: {wl['effort_allocation_pct']}%, Automation: {wl['automation_level']})"
                for wl in batch_wls
            )

            prompt = TASK_PROMPT.format(
                company_name=self.company.name,
                workloads_list=wls_str,
                tasks_per_workload=self.gen_config.target_tasks_per_workload,
                automation_levels=", ".join(AUTOMATION_LEVELS),
            )

            logger.info(f"Generating tasks for pending workloads {i+1}-{i+len(batch_wls)}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate tasks for batch {i}: {e}")
                continue

            wl_name_to_id = {wl["name"]: wl["id"] for wl in batch_wls}

            for task_data in batch_result:
                wl_name = task_data.get("workload", "")
                wl_id = wl_name_to_id.get(wl_name, "")
                if not wl_id:
                    for name, wid in wl_name_to_id.items():
                        if name.lower() in wl_name.lower() or wl_name.lower() in name.lower():
                            wl_id = wid
                            break

                classification = task_data.get("classification", "task_iteration")
                if classification not in TASK_CLASSIFICATIONS:
                    classification = "task_iteration"

                auto_level = task_data.get("automation_level", "human_led")
                if auto_level not in AUTOMATION_LEVELS:
                    auto_level = "human_led"

                task = {
                    "id": self.make_id("task", wl_name, task_data["name"]),
                    "name": task_data["name"],
                    "workload_id": wl_id,
                    "function_id": wl_id_to_func.get(wl_id, "unknown"),
                    "description": task_data.get("description", ""),
                    "classification": classification,
                    "time_allocation_pct": task_data.get("time_allocation_pct", 15.0),
                    "automation_potential": task_data.get("automation_potential", 30.0),
                    "automation_level": auto_level,
                    "current_tool_ids": [],
                    "future_tool_ids": [],
                    "skill_ids": [],
                }
                new_tasks.append(task)

        # Merge existing + new, then save per function
        all_tasks = existing_tasks + new_tasks
        self.save_per_function(all_tasks, self.output.entity_dir("tasks"))
        logger.info(
            f"Generated {len(new_tasks)} new tasks, "
            f"{len(all_tasks)} total ({len(existing_tasks)} existing)"
        )
        return all_tasks
