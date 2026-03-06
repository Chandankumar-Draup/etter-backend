"""
Role and JobTitle generator.

Uses LLM to generate realistic roles for each job family,
and job titles (career-banded) for each role.

Batch strategy: One LLM call per function -> generates all roles
for all job families within that function.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
    CAREER_BANDS,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

ROLE_GENERATION_PROMPT = """You are an expert in organizational design for the insurance industry.

Generate realistic job roles for {company_name}, a {company_desc}.

For the following job families within the "{function_name}" function, generate {roles_per_family} distinct roles per family. Each role should be realistic for a mid-large insurance company.

Job Families:
{job_families_list}

For each role, provide:
- name: Clear, industry-standard role name
- job_family: Which job family this role belongs to (exact name from list above)
- description: 1-2 sentence description of what this role does
- total_headcount: Realistic headcount (the function has {function_headcount} total employees)
- avg_salary: Average annual salary in USD (realistic for insurance industry)
- automation_score: AI automation potential 0-100 (higher = more automatable)

Return a JSON array of role objects:
[
  {{
    "name": "...",
    "job_family": "...",
    "description": "...",
    "total_headcount": 0,
    "avg_salary": 0,
    "automation_score": 0.0
  }}
]

Return ONLY the JSON array, no other text.
"""

JOB_TITLE_PROMPT = """You are an expert in HR and organizational design for the insurance industry.

For each of the following roles at {company_name}, generate {titles_per_role} job titles across different career levels. Titles should follow standard insurance industry naming conventions.

Roles:
{roles_list}

Career bands to use: {career_bands}

For each title, provide:
- name: The job title (e.g., "Senior Claims Adjuster", "VP of Underwriting")
- role: Which role this title belongs to (exact name from list above)
- career_band: One of {career_bands}
- typical_experience_years: Typical years of experience for this level
- headcount: How many people hold this title (should sum approximately to role headcount)
- avg_salary: Average salary for this title level

Return a JSON array:
[
  {{
    "name": "...",
    "role": "...",
    "career_band": "...",
    "typical_experience_years": 0,
    "headcount": 0,
    "avg_salary": 0
  }}
]

Return ONLY the JSON array, no other text.
"""


class RoleGenerator(BaseGenerator):
    """Generates roles and job titles using batch LLM calls."""

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

    def generate_roles(self, taxonomy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate roles for all job families, one LLM call per function."""
        all_roles = []
        functions = taxonomy["functions"]
        job_families = taxonomy["job_families"]
        job_family_groups = taxonomy["job_family_groups"]
        sub_functions = taxonomy["sub_functions"]

        # Build lookup: function_id -> list of job family names
        sf_by_func = {}
        for sf in sub_functions:
            sf_by_func.setdefault(sf["function_id"], []).append(sf)

        jfg_by_sf = {}
        for jfg in job_family_groups:
            jfg_by_sf.setdefault(jfg["sub_function_id"], []).append(jfg)

        jf_by_jfg = {}
        for jf in job_families:
            jf_by_jfg.setdefault(jf["job_family_group_id"], []).append(jf)

        for func in functions:
            func_jfs = []
            for sf in sf_by_func.get(func["id"], []):
                for jfg in jfg_by_sf.get(sf["id"], []):
                    for jf in jf_by_jfg.get(jfg["id"], []):
                        func_jfs.append(jf)

            if not func_jfs:
                continue

            # Per-function resumability: skip if file already exists
            func_file = self.output.function_file("roles", func["id"])
            if func_file.exists():
                existing = self.load_json(func_file)
                all_roles.extend(existing)
                logger.info(f"Loaded {len(existing)} existing roles for {func['name']}")
                continue

            jf_list_str = "\n".join(f"- {jf['name']}" for jf in func_jfs)

            prompt = ROLE_GENERATION_PROMPT.format(
                company_name=self.company.name,
                company_desc=self.company.description,
                function_name=func["name"],
                job_families_list=jf_list_str,
                roles_per_family=self.gen_config.target_roles_per_family,
                function_headcount=func["headcount"],
            )

            logger.info(f"Generating roles for function: {func['name']} ({len(func_jfs)} families)")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate roles for {func['name']}: {e}")
                continue

            # Build jf name -> id lookup
            jf_name_to_id = {jf["name"]: jf["id"] for jf in func_jfs}

            func_roles = []
            for role_data in batch_result:
                jf_name = role_data.get("job_family", "")
                jf_id = jf_name_to_id.get(jf_name, "")
                if not jf_id:
                    # Try fuzzy match
                    for name, fid in jf_name_to_id.items():
                        if name.lower() in jf_name.lower() or jf_name.lower() in name.lower():
                            jf_id = fid
                            break

                role = {
                    "id": self.make_id("role", role_data["name"]),
                    "name": role_data["name"],
                    "function_id": func["id"],
                    "job_family_id": jf_id,
                    "description": role_data.get("description", ""),
                    "total_headcount": role_data.get("total_headcount", 0),
                    "avg_salary": role_data.get("avg_salary", 0),
                    "automation_score": role_data.get("automation_score", 0.0),
                    "skill_ids": [],
                    "technology_ids": [],
                    "adjacency_role_ids": [],
                }
                func_roles.append(role)

            # Save this function's roles immediately (failure-resilient)
            if func_roles:
                self.save_json(func_roles, func_file)
            all_roles.extend(func_roles)

        logger.info(f"Generated {len(all_roles)} roles across {len(functions)} functions")
        return all_roles

    def generate_job_titles(self, roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate job titles for roles in batches, with incremental resumability.

        Loads existing titles from disk and only generates for roles that
        don't already have titles. Failed batches can be retried without
        regenerating everything.
        """
        # Map role_id → function_id for per-function file output
        role_id_to_func = {r["id"]: r.get("function_id", "unknown") for r in roles}

        # Load existing titles and find which roles already have titles
        existing_titles = self.load_from_dir(self.output.entity_dir("job_titles"))
        covered_role_ids = set(t["role_id"] for t in existing_titles)
        pending_roles = [r for r in roles if r["id"] not in covered_role_ids]

        if not pending_roles:
            logger.info(f"All {len(roles)} roles already have job titles, skipping")
            return existing_titles

        logger.info(
            f"{len(pending_roles)} of {len(roles)} roles need job titles "
            f"({len(existing_titles)} existing titles kept)"
        )

        new_titles = []
        batch_size = self.gen_config.roles_per_batch

        for i in range(0, len(pending_roles), batch_size):
            batch_roles = pending_roles[i:i + batch_size]
            roles_list_str = "\n".join(
                f"- {r['name']} (headcount: {r['total_headcount']}, avg salary: ${r['avg_salary']:,})"
                for r in batch_roles
            )
            career_bands_str = ", ".join(CAREER_BANDS[:6])  # up to director for most roles

            prompt = JOB_TITLE_PROMPT.format(
                company_name=self.company.name,
                roles_list=roles_list_str,
                titles_per_role=self.gen_config.target_titles_per_role,
                career_bands=career_bands_str,
            )

            logger.info(f"Generating job titles for pending roles {i+1}-{i+len(batch_roles)}")

            try:
                batch_result = self.generate_batch(prompt)
            except Exception as e:
                logger.error(f"Failed to generate titles for batch {i}: {e}")
                continue

            role_name_to_id = {r["name"]: r["id"] for r in batch_roles}

            for title_data in batch_result:
                role_name = title_data.get("role", "")
                role_id = role_name_to_id.get(role_name, "")
                if not role_id:
                    for name, rid in role_name_to_id.items():
                        if name.lower() in role_name.lower() or role_name.lower() in name.lower():
                            role_id = rid
                            break

                title = {
                    "id": self.make_id("title", title_data["name"]),
                    "name": title_data["name"],
                    "role_id": role_id,
                    "function_id": role_id_to_func.get(role_id, "unknown"),
                    "career_band": title_data.get("career_band", "mid"),
                    "level": CAREER_BANDS.index(title_data.get("career_band", "mid"))
                    if title_data.get("career_band", "mid") in CAREER_BANDS
                    else 1,
                    "typical_experience_years": title_data.get("typical_experience_years", 3),
                    "headcount": title_data.get("headcount", 0),
                    "avg_salary": title_data.get("avg_salary", 0),
                }
                new_titles.append(title)

        # Merge existing + new, then save per function
        all_titles = existing_titles + new_titles
        self.save_per_function(all_titles, self.output.entity_dir("job_titles"))
        logger.info(
            f"Generated {len(new_titles)} new job titles, "
            f"{len(all_titles)} total ({len(existing_titles)} existing)"
        )
        return all_titles

    def generate(self, taxonomy: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Generate all roles and job titles."""
        self.output.ensure_dirs()
        roles = self.generate_roles(taxonomy)
        titles = self.generate_job_titles(roles)
        return {"roles": roles, "job_titles": titles}
