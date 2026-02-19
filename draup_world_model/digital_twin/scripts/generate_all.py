"""
Master orchestration script for Digital Twin data generation.

Runs all generators in dependency order:
1. Taxonomy (seed data, no LLM)
2. Roles and Job Titles (LLM)
3. Workloads (LLM, depends on roles)
4. Tasks (LLM, depends on workloads)
5. Skills catalog + mapping (LLM, depends on roles)
6. Technology catalog + mapping (LLM, depends on roles)
7. Workflows (LLM, depends on taxonomy + roles)

Output uses per-function directory structure for resilience:
  data/acme_corp/roles/func_claims_management.json
  data/acme_corp/tasks/func_underwriting.json
  etc.

Generators with per-function output (roles, workflows) automatically
skip functions that already have files, enabling incremental runs.

Supports partial generation via --functions or --num-functions to
generate data for a subset of functions first, then expand later.

Usage:
    python -m draup_world_model.digital_twin.scripts.generate_all
    python -m draup_world_model.digital_twin.scripts.generate_all --step taxonomy
    python -m draup_world_model.digital_twin.scripts.generate_all --step roles
    python -m draup_world_model.digital_twin.scripts.generate_all --resume-from workloads
    python -m draup_world_model.digital_twin.scripts.generate_all --step roles --clean
    python -m draup_world_model.digital_twin.scripts.generate_all --num-functions 3
    python -m draup_world_model.digital_twin.scripts.generate_all --functions "Claims Management,Underwriting"
"""

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
)
from typing import Dict, List, Optional, Any

from draup_world_model.digital_twin.generators.base_generator import BaseGenerator
from draup_world_model.digital_twin.generators.taxonomy_generator import TaxonomyGenerator
from draup_world_model.digital_twin.generators.role_generator import RoleGenerator
from draup_world_model.digital_twin.generators.workload_generator import WorkloadGenerator
from draup_world_model.digital_twin.generators.task_generator import TaskGenerator
from draup_world_model.digital_twin.generators.skill_generator import SkillGenerator
from draup_world_model.digital_twin.generators.technology_generator import TechnologyGenerator
from draup_world_model.digital_twin.generators.workflow_generator import WorkflowGenerator
from draup_world_model.digital_twin.scripts.assemble_role_skill_map import assemble as assemble_role_skill_map

# Generation steps in dependency order
STEPS = [
    "taxonomy",
    "roles",
    "workloads",
    "tasks",
    "skills",
    "technologies",
    "workflows",
    "role_skill_mapping",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_existing(output: OutputConfig, name: str) -> any:
    """Load previously generated data, preferring per-function directories.

    Resolution order:
      1. Per-function directory  (e.g. roles/*.json)
      2. Catalog file            (e.g. skills/catalog.json)
      3. Legacy flat file        (e.g. roles.json)
    """
    # Directory-based entities
    dir_entities = {"roles", "job_titles", "workloads", "tasks", "workflows"}
    if name in dir_entities:
        entity_dir = output.entity_dir(name)
        if entity_dir.exists() and any(entity_dir.glob("*.json")):
            return BaseGenerator.load_from_dir(entity_dir)

    # Catalog entities (new directory-based location)
    catalog_map = {
        "skills": output.skills_catalog_file,
        "technologies": output.technologies_catalog_file,
    }
    if name in catalog_map:
        path = catalog_map[name]
        if path.exists():
            return BaseGenerator.load_json(path)

    # Fallback: legacy flat files
    flat_map = {
        "taxonomy": output.taxonomy_file,
        "roles": output.roles_file,
        "job_titles": output.job_titles_file,
        "workloads": output.workloads_file,
        "tasks": output.tasks_file,
        "skills": output.skills_file,
        "technologies": output.technologies_file,
        "workflows": output.workflows_file,
    }
    path = flat_map.get(name)
    if path and path.exists():
        return BaseGenerator.load_json(path)
    return None


def _fix_skill_types(output: OutputConfig):
    """Migrate existing skill data: rename skill_type 'hard' → 'core'.

    Updates skills catalog and any role files that embed skill data.
    Safe to run multiple times (idempotent).
    """
    catalog_path = output.skills_catalog_file
    fixed = 0
    if catalog_path.exists():
        with open(catalog_path) as f:
            skills = json.load(f)
        for skill in skills:
            if skill.get("skill_type") == "hard":
                skill["skill_type"] = "core"
                fixed += 1
        if fixed:
            with open(catalog_path, "w") as f:
                json.dump(skills, f, indent=2)
            logger.info(f"Fixed {fixed} skills: skill_type 'hard' → 'core' in {catalog_path}")
        else:
            logger.info("Skills catalog already uses 'core', no changes needed")
    else:
        logger.info("No skills catalog found, nothing to fix")


def _clean_step_data(output: OutputConfig, step: str):
    """Remove existing per-function files for a step so it regenerates fresh."""
    # Map step names to entity directories
    step_entities = {
        "roles": ["roles", "job_titles"],
        "workloads": ["workloads"],
        "tasks": ["tasks"],
        "skills": ["skills"],
        "technologies": ["technologies"],
        "workflows": ["workflows"],
    }
    for entity in step_entities.get(step, []):
        entity_dir = output.entity_dir(entity)
        if entity_dir.exists():
            for f in entity_dir.glob("*.json"):
                f.unlink()
            logger.info(f"Cleaned {entity_dir}")


def filter_taxonomy(
    taxonomy: Dict[str, Any],
    function_names: Optional[List[str]] = None,
    num_functions: Optional[int] = None,
) -> Dict[str, Any]:
    """Filter taxonomy to include only selected functions and their children.

    The full taxonomy is always saved to disk (it's cheap seed data).
    This filter narrows what downstream generators process.

    Args:
        taxonomy: Full taxonomy dict with organization, functions, sub_functions, etc.
        function_names: Explicit list of function names to include (case-insensitive partial match).
        num_functions: Take the first N functions (by taxonomy order).

    Returns:
        Filtered taxonomy dict with only selected functions and their descendants.
    """
    all_functions = taxonomy["functions"]

    if function_names:
        # Case-insensitive matching: exact match always, substring match for 3+ char queries
        selected = []
        names_lower = [n.strip().lower() for n in function_names]
        for func in all_functions:
            func_lower = func["name"].lower()
            for n in names_lower:
                if func_lower == n or (len(n) >= 3 and n in func_lower):
                    selected.append(func)
                    break
        if not selected:
            available = [f["name"] for f in all_functions]
            raise ValueError(
                f"No functions matched {function_names}. "
                f"Available: {available}"
            )
    elif num_functions:
        selected = all_functions[:num_functions]
    else:
        return taxonomy  # No filter

    selected_ids = {f["id"] for f in selected}
    logger.info(f"Filtering to {len(selected)} functions: {[f['name'] for f in selected]}")

    # Filter sub_functions by function_id
    sub_functions = [sf for sf in taxonomy["sub_functions"] if sf["function_id"] in selected_ids]
    sf_ids = {sf["id"] for sf in sub_functions}

    # Filter JFGs by sub_function_id
    jfgs = [jfg for jfg in taxonomy["job_family_groups"] if jfg["sub_function_id"] in sf_ids]
    jfg_ids = {jfg["id"] for jfg in jfgs}

    # Filter JFs by jfg_id
    jfs = [jf for jf in taxonomy["job_families"] if jf["job_family_group_id"] in jfg_ids]

    return {
        "organization": taxonomy["organization"],
        "functions": selected,
        "sub_functions": sub_functions,
        "job_family_groups": jfgs,
        "job_families": jfs,
    }


def run_generation(
    step: str = None,
    resume_from: str = None,
    clean: bool = False,
    function_names: Optional[List[str]] = None,
    num_functions: Optional[int] = None,
    llm_config: LLMConfig = None,
    gen_config: GenerationConfig = None,
):
    """Run the data generation pipeline."""
    company = CompanyProfile()
    output = OutputConfig()
    llm_config = llm_config or LLMConfig()
    gen_config = gen_config or GenerationConfig()
    output.ensure_dirs()

    # Clean per-function files for targeted steps if requested
    if clean:
        targets = [step] if step else (STEPS[STEPS.index(resume_from):] if resume_from else STEPS)
        for s in targets:
            _clean_step_data(output, s)

    # Determine which steps to run
    if step:
        steps_to_run = [step]
    elif resume_from:
        start_idx = STEPS.index(resume_from)
        steps_to_run = STEPS[start_idx:]
    else:
        steps_to_run = STEPS

    # Function filter scope
    has_function_filter = bool(function_names or num_functions)

    logger.info(f"Running generation steps: {steps_to_run}")
    logger.info(f"Company: {company.name} ({company.industry})")
    logger.info(f"LLM: {llm_config.model}")
    logger.info(f"Output: {output.base_dir}")
    if has_function_filter:
        label = function_names if function_names else f"first {num_functions}"
        logger.info(f"Function filter: {label}")

    start_time = time.time()
    stats = {}

    for current_step in steps_to_run:
        step_start = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP: {current_step.upper()}")
        logger.info(f"{'='*60}")

        if current_step == "taxonomy":
            gen = TaxonomyGenerator(company=company, output=output)
            taxonomy = gen.generate()
            stats["taxonomy"] = {
                "functions": len(taxonomy["functions"]),
                "sub_functions": len(taxonomy["sub_functions"]),
                "job_family_groups": len(taxonomy["job_family_groups"]),
                "job_families": len(taxonomy["job_families"]),
            }

        elif current_step == "roles":
            taxonomy = load_existing(output, "taxonomy")
            if not taxonomy:
                raise RuntimeError("Taxonomy data not found. Run 'taxonomy' step first.")
            if has_function_filter:
                taxonomy = filter_taxonomy(taxonomy, function_names, num_functions)

            gen = RoleGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            result = gen.generate(taxonomy)
            stats["roles"] = len(result["roles"])
            stats["job_titles"] = len(result["job_titles"])

        elif current_step == "workloads":
            roles = load_existing(output, "roles")
            if not roles:
                raise RuntimeError("Roles data not found. Run 'roles' step first.")

            gen = WorkloadGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            workloads = gen.generate(roles)
            stats["workloads"] = len(workloads)

        elif current_step == "tasks":
            roles = load_existing(output, "roles")
            workloads = load_existing(output, "workloads")
            if not workloads:
                raise RuntimeError("Workloads data not found. Run 'workloads' step first.")

            gen = TaskGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            tasks = gen.generate(workloads, roles or [])
            stats["tasks"] = len(tasks)

        elif current_step == "skills":
            roles = load_existing(output, "roles")
            if not roles:
                raise RuntimeError("Roles data not found. Run 'roles' step first.")

            gen = SkillGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            result = gen.generate(roles)
            stats["skills"] = len(result["skills"])

        elif current_step == "technologies":
            roles = load_existing(output, "roles")
            if not roles:
                raise RuntimeError("Roles data not found. Run 'roles' step first.")

            gen = TechnologyGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            result = gen.generate(roles)
            stats["technologies"] = len(result["technologies"])

        elif current_step == "workflows":
            taxonomy = load_existing(output, "taxonomy")
            roles = load_existing(output, "roles")
            if not taxonomy or not roles:
                raise RuntimeError("Taxonomy and roles data required. Run those steps first.")
            if has_function_filter:
                taxonomy = filter_taxonomy(taxonomy, function_names, num_functions)

            # Load additional context for enriched workflows
            tasks = load_existing(output, "tasks")
            skills = load_existing(output, "skills")
            job_titles = load_existing(output, "job_titles")

            gen = WorkflowGenerator(
                llm_config=llm_config,
                gen_config=gen_config,
                company=company,
                output=output,
            )
            workflows = gen.generate(
                taxonomy, roles, tasks=tasks, skills=skills,
                job_titles=job_titles,
            )
            stats["workflows"] = len(workflows)

        elif current_step == "role_skill_mapping":
            logger.info("skipping task-skill mapping currently")
            # LLM-based task→skill mapping per role
            # result = assemble_role_skill_map(output, llm_config=llm_config)
            # stats["role_skill_mapping"] = len(result)

        step_time = time.time() - step_start
        logger.info(f"Step '{current_step}' completed in {step_time:.1f}s")

    total_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info("GENERATION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total time: {total_time:.1f}s")
    logger.info(f"Statistics: {json.dumps(stats, indent=2)}")

    # Save generation stats
    stats_path = output.base_dir / "generation_stats.json"
    BaseGenerator.save_json(stats, stats_path)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate Digital Twin data for Acme Corporation")
    parser.add_argument(
        "--step",
        choices=STEPS,
        help="Run only a specific step",
    )
    parser.add_argument(
        "--resume-from",
        choices=STEPS,
        help="Resume from a specific step (runs that step and all subsequent)",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="LLM model to use (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="LLM temperature (default: 0.3)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing per-function files before regenerating (forces fresh generation)",
    )
    parser.add_argument(
        "--functions",
        type=str,
        default=None,
        help='Comma-separated function names to generate (e.g., "Claims Management,Underwriting")',
    )
    parser.add_argument(
        "--num-functions",
        type=int,
        default=None,
        help="Generate for the first N functions only (e.g., 3 for Claims, Underwriting, Actuarial)",
    )
    parser.add_argument(
        "--fix-skill-type",
        action="store_true",
        help="Fix existing skill data: rename skill_type 'hard' → 'core' (no LLM calls needed)",
    )
    args = parser.parse_args()

    # Handle data fix commands (no LLM needed)
    if args.fix_skill_type:
        output = OutputConfig()
        _fix_skill_types(output)
        return

    llm_config = LLMConfig(model=args.model, temperature=args.temperature)
    func_names = [n.strip() for n in args.functions.split(",")] if args.functions else None

    try:
        run_generation(
            step=args.step,
            resume_from=args.resume_from,
            clean=args.clean,
            function_names=func_names,
            num_functions=args.num_functions,
            llm_config=llm_config,
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
