"""
Skill catalog generator.

Generates a comprehensive skill catalog for the insurance industry,
then maps skills to roles.

Batch strategy: 1-2 LLM calls for the full catalog, then 1 call per
~15 roles for skill mapping.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
    SKILL_CATEGORIES,
    SKILL_LIFECYCLE,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

SKILL_CATALOG_PROMPT = """You are an expert in workforce skills taxonomy for the insurance industry.

Generate a comprehensive skill catalog for {company_name}, a {company_desc}.

Generate {target_count} skills across these categories:
{categories}

Lifecycle statuses: {lifecycle_statuses}

Include a mix of:
- Insurance domain skills (claims handling, underwriting, actuarial science, etc.)
- Technical skills (programming, data analysis, cloud, AI/ML, etc.)
- Business skills (project management, strategic planning, etc.)
- Soft/interpersonal skills (communication, leadership, negotiation, etc.)
- Digital transformation skills (emerging AI, automation, GenAI, etc.)
- Regulatory/compliance skills (insurance regulation, NAIC, SOX, etc.)

For each skill:
- name: Clear skill name
- category: One of {categories}
- skill_type: "core" or "soft"
- lifecycle_status: One of {lifecycle_statuses}
- description: Brief description
- market_demand_trend: "rising", "stable", or "falling"

Return a JSON array:
[
  {{
    "name": "...",
    "category": "...",
    "skill_type": "...",
    "lifecycle_status": "...",
    "description": "...",
    "market_demand_trend": "..."
  }}
]

Return ONLY the JSON array, no other text.
"""

SKILL_MAPPING_PROMPT = """You are an expert in workforce skills for the insurance industry.

Given these roles and the skill catalog below, assign 5-12 relevant skills to each role. Pick skills that a person in this role would need.

Roles:
{roles_list}

Available Skills (by name):
{skills_list}

Return a JSON array mapping roles to skill names:
[
  {{
    "role": "exact role name",
    "skills": ["skill name 1", "skill name 2", ...]
  }}
]

Return ONLY the JSON array, no other text.
"""


class SkillGenerator(BaseGenerator):
    """Generates skill catalog and role-skill mappings."""

    # Category groups for batched catalog generation.
    # Splitting avoids LLM response truncation at max_tokens.
    CATEGORY_GROUPS = [
        ["domain", "regulatory"],
        ["technical", "digital"],
        ["analytical", "leadership", "communication"],
    ]

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

    def generate_catalog(self) -> List[Dict[str, Any]]:
        """Generate the full skill catalog in per-category-group batches.

        Splits the target count across category groups to keep each LLM
        response within token limits. Deduplicates by skill name.
        """
        self.output.ensure_dirs()
        lifecycle_str = ", ".join(SKILL_LIFECYCLE)
        total = self.gen_config.target_skills_total
        num_groups = len(self.CATEGORY_GROUPS)
        all_skills = []

        for group_idx, categories in enumerate(self.CATEGORY_GROUPS):
            # Distribute target evenly, remainder goes to earlier groups
            batch_count = total // num_groups
            if group_idx < total % num_groups:
                batch_count += 1

            categories_str = ", ".join(categories)
            prompt = SKILL_CATALOG_PROMPT.format(
                company_name=self.company.name,
                company_desc=self.company.description,
                target_count=batch_count,
                categories=categories_str,
                lifecycle_statuses=lifecycle_str,
            )

            logger.info(f"Generating ~{batch_count} skills for categories: {categories_str}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate skills for {categories_str}: {e}")
                continue

            for skill_data in batch_result:
                category = skill_data.get("category", categories[0])
                if category not in SKILL_CATEGORIES:
                    category = categories[0]

                lifecycle = skill_data.get("lifecycle_status", "stable")
                if lifecycle not in SKILL_LIFECYCLE:
                    lifecycle = "stable"

                skill = {
                    "id": self.make_id("skill", skill_data["name"]),
                    "name": skill_data["name"],
                    "category": category,
                    "skill_type": skill_data.get("skill_type", "core"),
                    "lifecycle_status": lifecycle,
                    "description": skill_data.get("description", ""),
                    "market_demand_trend": skill_data.get("market_demand_trend", "stable"),
                }
                all_skills.append(skill)

        # Deduplicate by name (LLM may repeat skills across groups)
        seen = set()
        unique_skills = []
        for s in all_skills:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique_skills.append(s)

        self.save_json(unique_skills, self.output.skills_catalog_file)
        logger.info(f"Generated {len(unique_skills)} unique skills")
        return unique_skills

    def map_skills_to_roles(
        self,
        roles: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Map skills to roles using LLM. Returns updated roles with skill_ids."""
        skill_name_to_id = {s["name"]: s["id"] for s in skills}
        skill_names_str = ", ".join(s["name"] for s in skills)
        batch_size = self.gen_config.roles_per_batch

        for i in range(0, len(roles), batch_size):
            batch_roles = roles[i:i + batch_size]
            roles_str = "\n".join(
                f"- {r['name']}: {r['description']}"
                for r in batch_roles
            )

            prompt = SKILL_MAPPING_PROMPT.format(
                roles_list=roles_str,
                skills_list=skill_names_str,
            )

            logger.info(f"Mapping skills to roles {i+1}-{i+len(batch_roles)}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to map skills for batch {i}: {e}")
                continue

            role_name_to_idx = {}
            for idx, r in enumerate(roles):
                role_name_to_idx[r["name"]] = idx

            for mapping in batch_result:
                role_name = mapping.get("role", "")
                if role_name in role_name_to_idx:
                    idx = role_name_to_idx[role_name]
                    skill_ids = [
                        skill_name_to_id[s]
                        for s in mapping.get("skills", [])
                        if s in skill_name_to_id
                    ]
                    roles[idx]["skill_ids"] = skill_ids

        # Re-save roles with skill mappings (per-function files)
        self.save_per_function(roles, self.output.entity_dir("roles"))
        logger.info("Updated roles with skill mappings")
        return roles

    def generate(self, roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate skill catalog and map to roles."""
        skills = self.generate_catalog()
        updated_roles = self.map_skills_to_roles(roles, skills)
        return {"skills": skills, "roles": updated_roles}
