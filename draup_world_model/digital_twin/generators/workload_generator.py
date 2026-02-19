"""
Workload generator.

Generates 3-5 workloads per role using batch LLM calls.
Workloads are coherent blocks of work that decompose a role's responsibilities.

Batch strategy: One LLM call per ~10 roles -> generates all workloads for those roles.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
    AUTOMATION_LEVELS,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

WORKLOAD_PROMPT = """You are an expert in workforce analytics and job decomposition for the insurance industry.

For each role below at {company_name}, generate {workloads_per_role} distinct workloads. A workload is a coherent block of work that a role performs regularly.

Roles:
{roles_list}

For each workload:
- name: Clear name describing the work block (e.g., "Policy Review and Evaluation", "Client Communication")
- role: Exact role name from the list above
- description: 1-2 sentence description
- effort_allocation_pct: What percentage of the role's time goes to this workload (all workloads for a role should sum to approximately 100)
- automation_level: One of {automation_levels}

Return a JSON array:
[
  {{
    "name": "...",
    "role": "...",
    "description": "...",
    "effort_allocation_pct": 0.0,
    "automation_level": "..."
  }}
]

Return ONLY the JSON array, no other text.
"""


class WorkloadGenerator(BaseGenerator):
    """Generates workloads for roles using batch LLM calls."""

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

    def generate(self, roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate workloads for roles in batches, with incremental resumability.

        Loads existing workloads from disk and only generates for roles that
        don't already have workloads. This means failed batches can be retried
        without regenerating everything.
        """
        self.output.ensure_dirs()

        # Map role_id → function_id for per-function file output
        role_id_to_func = {r["id"]: r.get("function_id", "unknown") for r in roles}

        # Load existing workloads and find which roles already have workloads
        existing_wls = self.load_from_dir(self.output.entity_dir("workloads"))
        covered_role_ids = set(wl["role_id"] for wl in existing_wls)
        pending_roles = [r for r in roles if r["id"] not in covered_role_ids]

        if not pending_roles:
            logger.info(f"All {len(roles)} roles already have workloads, skipping")
            return existing_wls

        logger.info(
            f"{len(pending_roles)} of {len(roles)} roles need workloads "
            f"({len(existing_wls)} existing workloads kept)"
        )

        new_workloads = []
        batch_size = self.gen_config.workloads_per_batch

        for i in range(0, len(pending_roles), batch_size):
            batch_roles = pending_roles[i:i + batch_size]
            roles_str = "\n".join(
                f"- {r['name']}: {r['description']} (automation score: {r['automation_score']})"
                for r in batch_roles
            )

            prompt = WORKLOAD_PROMPT.format(
                company_name=self.company.name,
                roles_list=roles_str,
                workloads_per_role=self.gen_config.target_workloads_per_role,
                automation_levels=", ".join(AUTOMATION_LEVELS),
            )

            logger.info(f"Generating workloads for pending roles {i+1}-{i+len(batch_roles)}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate workloads for batch {i}: {e}")
                continue

            role_name_to_id = {r["name"]: r["id"] for r in batch_roles}

            for wl_data in batch_result:
                role_name = wl_data.get("role", "")
                role_id = role_name_to_id.get(role_name, "")
                if not role_id:
                    for name, rid in role_name_to_id.items():
                        if name.lower() in role_name.lower() or role_name.lower() in name.lower():
                            role_id = rid
                            break

                workload = {
                    "id": self.make_id("wl", role_name, wl_data["name"]),
                    "name": wl_data["name"],
                    "role_id": role_id,
                    "function_id": role_id_to_func.get(role_id, "unknown"),
                    "description": wl_data.get("description", ""),
                    "effort_allocation_pct": wl_data.get("effort_allocation_pct", 25.0),
                    "automation_level": wl_data.get("automation_level", "human_led"),
                    "skill_ids": [],
                }
                new_workloads.append(workload)

        # Merge existing + new, then save per function
        all_workloads = existing_wls + new_workloads
        self.save_per_function(all_workloads, self.output.entity_dir("workloads"))
        logger.info(
            f"Generated {len(new_workloads)} new workloads, "
            f"{len(all_workloads)} total ({len(existing_wls)} existing)"
        )
        return all_workloads
