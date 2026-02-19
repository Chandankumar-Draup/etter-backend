"""
Technology catalog generator.

Generates a technology/tool catalog for the insurance industry,
then maps technologies to roles and tasks.

Batch strategy: 1-2 LLM calls for the full catalog, then mapping calls.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
    TECHNOLOGY_CATEGORIES,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

TECH_CATALOG_PROMPT = """You are an expert in enterprise technology for the insurance industry.

Generate a comprehensive technology catalog for {company_name}, a {company_desc}.

Generate {target_count} technologies across these categories:
{categories}

Include a realistic mix of:
- AI/ML tools (OpenAI, UiPath, Copilot, custom ML models)
- Insurance-specific platforms (Guidewire, Duck Creek, Majesco)
- Analytics/BI (Tableau, Power BI, SAS)
- Cloud (AWS, Azure, GCP services)
- CRM (Salesforce, ServiceNow)
- ERP (SAP, Oracle)
- Communication (Teams, Slack, Zoom)
- Security/Compliance tools
- Development tools (GitHub, Jira, Jenkins)
- RPA and automation (UiPath, Automation Anywhere, Power Automate)

For each technology:
- name: Product/tool name
- category: One of {categories}
- vendor: Vendor name
- description: Brief description of what it does
- capabilities: List of 2-4 key capabilities
- license_cost_tier: "low", "medium", "high", or "enterprise"
- adoption_stage: "emerging", "early_adopter", "mainstream", "mature", or "legacy"

Return a JSON array:
[
  {{
    "name": "...",
    "category": "...",
    "vendor": "...",
    "description": "...",
    "capabilities": ["...", "..."],
    "license_cost_tier": "...",
    "adoption_stage": "..."
  }}
]

Return ONLY the JSON array, no other text.
"""

TECH_MAPPING_PROMPT = """You are an expert in enterprise technology for the insurance industry.

Given these roles and the technology catalog below, assign 3-8 relevant technologies to each role.

Roles:
{roles_list}

Available Technologies (by name):
{tech_list}

Return a JSON array mapping roles to technology names:
[
  {{
    "role": "exact role name",
    "technologies": ["tech name 1", "tech name 2", ...]
  }}
]

Return ONLY the JSON array, no other text.
"""


class TechnologyGenerator(BaseGenerator):
    """Generates technology catalog and role-tech mappings."""

    # Category groups for batched catalog generation.
    # Splitting avoids LLM response truncation at max_tokens.
    CATEGORY_GROUPS = [
        ["ai_ml", "automation_rpa", "analytics_bi"],
        ["cloud_infrastructure", "crm_customer", "erp_enterprise"],
        ["communication_collaboration", "security_compliance", "industry_specific", "development_tools"],
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
        """Generate the full technology catalog in per-category-group batches.

        Splits the target count across category groups to keep each LLM
        response within token limits. Deduplicates by technology name.
        """
        self.output.ensure_dirs()
        total = self.gen_config.target_technologies_total
        num_groups = len(self.CATEGORY_GROUPS)
        all_technologies = []

        for group_idx, categories in enumerate(self.CATEGORY_GROUPS):
            batch_count = total // num_groups
            if group_idx < total % num_groups:
                batch_count += 1

            categories_str = ", ".join(categories)
            prompt = TECH_CATALOG_PROMPT.format(
                company_name=self.company.name,
                company_desc=self.company.description,
                target_count=batch_count,
                categories=categories_str,
            )

            logger.info(f"Generating ~{batch_count} technologies for categories: {categories_str}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate technologies for {categories_str}: {e}")
                continue

            for tech_data in batch_result:
                category = tech_data.get("category", categories[0])
                if category not in TECHNOLOGY_CATEGORIES:
                    category = categories[0]

                tech = {
                    "id": self.make_id("tech", tech_data["name"]),
                    "name": tech_data["name"],
                    "category": category,
                    "vendor": tech_data.get("vendor", ""),
                    "description": tech_data.get("description", ""),
                    "capabilities": tech_data.get("capabilities", []),
                    "license_cost_tier": tech_data.get("license_cost_tier", "medium"),
                    "adoption_stage": tech_data.get("adoption_stage", "mainstream"),
                }
                all_technologies.append(tech)

        # Deduplicate by name
        seen = set()
        unique_technologies = []
        for t in all_technologies:
            if t["name"] not in seen:
                seen.add(t["name"])
                unique_technologies.append(t)

        self.save_json(unique_technologies, self.output.technologies_catalog_file)
        logger.info(f"Generated {len(unique_technologies)} unique technologies")
        return unique_technologies

    def map_tech_to_roles(
        self,
        roles: List[Dict[str, Any]],
        technologies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Map technologies to roles using LLM. Returns updated roles."""
        tech_name_to_id = {t["name"]: t["id"] for t in technologies}
        tech_names_str = ", ".join(t["name"] for t in technologies)
        batch_size = self.gen_config.roles_per_batch

        for i in range(0, len(roles), batch_size):
            batch_roles = roles[i:i + batch_size]
            roles_str = "\n".join(
                f"- {r['name']}: {r['description']}"
                for r in batch_roles
            )

            prompt = TECH_MAPPING_PROMPT.format(
                roles_list=roles_str,
                tech_list=tech_names_str,
            )

            logger.info(f"Mapping technologies to roles {i+1}-{i+len(batch_roles)}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to map tech for batch {i}: {e}")
                continue

            role_name_to_idx = {}
            for idx, r in enumerate(roles):
                role_name_to_idx[r["name"]] = idx

            for mapping in batch_result:
                role_name = mapping.get("role", "")
                if role_name in role_name_to_idx:
                    idx = role_name_to_idx[role_name]
                    tech_ids = [
                        tech_name_to_id[t]
                        for t in mapping.get("technologies", [])
                        if t in tech_name_to_id
                    ]
                    roles[idx]["technology_ids"] = tech_ids

        # Re-save roles with technology mappings (per-function files)
        self.save_per_function(roles, self.output.entity_dir("roles"))
        logger.info("Updated roles with technology mappings")
        return roles

    def generate(self, roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate technology catalog and map to roles."""
        technologies = self.generate_catalog()
        updated_roles = self.map_tech_to_roles(roles, technologies)
        return {"technologies": technologies, "roles": updated_roles}
