"""
Role → Workload → Task → Skill mapping generator.

For each role, uses LLM to map which of the role's skills are required
by each individual task, with relevance (PRIMARY/SECONDARY).

Output per role mirrors the reference architecture:
  {
    "role_id": "...",
    "role_name": "...",
    "workloads": [
      {
        "workload_name": "...",
        "tasks": [
          {
            "task_name": "...",
            "task_id": "...",
            "automation_type": "...",
            "mapped_skills": [
              {"skill_name": "...", "skill_id": "...", "relevance": "PRIMARY", ...}
            ]
          }
        ],
        "automation_summary": {"ai": 2, "human_ai": 3, "human": 1}
      }
    ],
    "summary": {
      "total_workloads": 4,
      "total_tasks": 24,
      "total_mappings": 96,
      "avg_skills_per_task": 4.0,
      "unique_skills_used": 12
    }
  }

Usage:
    python -m draup_world_model.digital_twin.scripts.assemble_role_skill_map
    python -m draup_world_model.digital_twin.scripts.assemble_role_skill_map --no-llm
"""

import argparse
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import LLMConfig, OutputConfig
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── LLM prompt for task→skill mapping ──────────────────────────

TASK_SKILL_MAPPING_PROMPT = """You are mapping skills to tasks for the role "{role_name}".

## Role's Skills
{skills_list}

## Tasks (grouped by workload)
{tasks_list}

For EACH task, select the skills from the role's skill set that are required to perform it.
Mark each skill as:
- PRIMARY: The skill is essential/core for performing this task
- SECONDARY: The skill is helpful/supporting but not essential

Return a JSON array with one entry per task:
[
  {{
    "task_name": "exact task name",
    "mapped_skills": [
      {{"skill_name": "exact skill name", "relevance": "PRIMARY"}},
      {{"skill_name": "exact skill name", "relevance": "SECONDARY"}}
    ]
  }}
]

Rules:
- Map 3-8 skills per task (at least 1 PRIMARY)
- Use EXACT skill names from the list above
- Every task must have at least one mapped skill
- Return ONLY the JSON array, no other text
"""


# ── Data loading ───────────────────────────────────────────────

def _load_entity(output: OutputConfig, name: str) -> List[Dict[str, Any]]:
    """Load entity from per-function directory or catalog file."""
    entity_dir = output.entity_dir(name)
    if entity_dir.exists() and any(entity_dir.glob("*.json")):
        return BaseGenerator.load_from_dir(entity_dir)

    catalog_map = {
        "skills": output.skills_catalog_file,
        "technologies": output.technologies_catalog_file,
    }
    if name in catalog_map and catalog_map[name].exists():
        return BaseGenerator.load_json(catalog_map[name])

    return []


# ── Core mapping logic ─────────────────────────────────────────

def _build_role_data(
    role: Dict[str, Any],
    workloads_by_role: Dict[str, List],
    tasks_by_workload: Dict[str, List],
    skill_by_id: Dict[str, Dict],
) -> Dict[str, Any]:
    """Build the hierarchical role data structure."""
    role_skills = [
        skill_by_id[sid]
        for sid in role.get("skill_ids", [])
        if sid in skill_by_id
    ]

    role_workloads = []
    for wl in workloads_by_role.get(role["id"], []):
        wl_tasks = tasks_by_workload.get(wl["id"], [])
        role_workloads.append({
            "workload_id": wl["id"],
            "workload_name": wl["name"],
            "effort_allocation_pct": wl.get("effort_allocation_pct", 0.0),
            "automation_level": wl.get("automation_level", "human_led"),
            "tasks": wl_tasks,
        })

    return {
        "role": role,
        "skills": role_skills,
        "workloads": role_workloads,
    }


def _map_skills_with_llm(
    generator: BaseGenerator,
    role_name: str,
    role_skills: List[Dict],
    role_workloads: List[Dict],
) -> Dict[str, List[Dict]]:
    """Use LLM to map skills to each task. Returns {task_name: [mapped_skills]}."""
    skills_list = "\n".join(
        f"- {s['name']} (category: {s.get('category', '')}, type: {s.get('skill_type', 'core')})"
        for s in role_skills
    )

    tasks_list_parts = []
    for wl in role_workloads:
        tasks_list_parts.append(f"\n### Workload: {wl['workload_name']}")
        for t in wl["tasks"]:
            classification = t.get("classification", "")
            auto_level = t.get("automation_level", "")
            tasks_list_parts.append(
                f"- {t['name']}: {t.get('description', '')} "
                f"[classification: {classification}, automation: {auto_level}]"
            )
    tasks_list = "\n".join(tasks_list_parts)

    prompt = TASK_SKILL_MAPPING_PROMPT.format(
        role_name=role_name,
        skills_list=skills_list,
        tasks_list=tasks_list,
    )

    try:
        result = generator.generate_batch(prompt)
    except Exception as e:
        logger.error(f"LLM mapping failed for {role_name}: {e}")
        return {}

    # Build lookup: task_name → mapped_skills
    mapping = {}
    for item in result:
        task_name = item.get("task_name", "")
        mapped = item.get("mapped_skills", [])
        mapping[task_name] = mapped

    return mapping


def _automation_type(task: Dict) -> str:
    """Derive automation_type from task classification/automation_level."""
    level = task.get("automation_level", "human_led")
    if level in ("ai_only", "ai_led"):
        return "ai"
    elif level in ("shared",):
        return "human_ai"
    return "human"


def _assemble_result(
    role: Dict,
    role_skills: List[Dict],
    role_workloads: List[Dict],
    task_skill_map: Dict[str, List[Dict]],
    skill_name_to_id: Dict[str, str],
    skill_by_id: Dict[str, Dict],
) -> Dict[str, Any]:
    """Assemble final output for one role."""
    total_mappings = 0
    unique_skills = set()
    total_tasks = 0

    workloads_out = []
    for wl in role_workloads:
        auto_counts = {"ai": 0, "human_ai": 0, "human": 0}
        tasks_out = []

        for t in wl["tasks"]:
            total_tasks += 1
            at = _automation_type(t)
            auto_counts[at] += 1

            # Get LLM-mapped skills for this task
            raw_mapped = task_skill_map.get(t["name"], [])
            mapped_skills = []
            for ms in raw_mapped:
                sname = ms.get("skill_name", "")
                sid = skill_name_to_id.get(sname, "")
                if not sid:
                    continue
                skill_info = skill_by_id.get(sid, {})
                mapped_skills.append({
                    "skill_name": sname,
                    "skill_id": sid,
                    "relevance": ms.get("relevance", "SECONDARY"),
                    "skill_category": skill_info.get("category", ""),
                    "skill_type": skill_info.get("skill_type", "core"),
                })
                unique_skills.add(sid)

            total_mappings += len(mapped_skills)

            tasks_out.append({
                "task_name": t["name"],
                "task_id": t["id"],
                "automation_type": at,
                "classification": t.get("classification", ""),
                "time_allocation_pct": t.get("time_allocation_pct", 0.0),
                "mapped_skills": mapped_skills,
            })

        workloads_out.append({
            "workload_name": wl["workload_name"],
            "workload_id": wl["workload_id"],
            "effort_allocation_pct": wl["effort_allocation_pct"],
            "tasks": tasks_out,
            "automation_summary": auto_counts,
        })

    return {
        "role_id": role["id"],
        "role_name": role["name"],
        "description": role.get("description", ""),
        "total_headcount": role.get("total_headcount", 0),
        "workloads": workloads_out,
        "summary": {
            "total_workloads": len(workloads_out),
            "total_tasks": total_tasks,
            "total_mappings": total_mappings,
            "avg_skills_per_task": round(total_mappings / max(total_tasks, 1), 1),
            "unique_skills_used": len(unique_skills),
        },
    }


# ── Public API ─────────────────────────────────────────────────

def assemble(
    output: OutputConfig = None,
    llm_config: Optional[LLMConfig] = None,
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    """Generate role → workload → task → skill mapping.

    Args:
        output: Output configuration for file paths.
        llm_config: LLM settings. Uses defaults if None.
        use_llm: If True, use LLM for task-skill mapping.
                 If False, assign all role skills to all tasks (for testing).
    """
    output = output or OutputConfig()

    # Load all entities
    roles = _load_entity(output, "roles")
    workloads = _load_entity(output, "workloads")
    tasks = _load_entity(output, "tasks")
    skills = _load_entity(output, "skills")

    if not roles:
        logger.error("No roles found. Run generation first.")
        return []

    logger.info(
        f"Loaded: {len(roles)} roles, {len(workloads)} workloads, "
        f"{len(tasks)} tasks, {len(skills)} skills"
    )

    # Build lookup indexes
    skill_by_id = {s["id"]: s for s in skills}
    skill_name_to_id = {s["name"]: s["id"] for s in skills}
    workloads_by_role: Dict[str, List] = defaultdict(list)
    for wl in workloads:
        workloads_by_role[wl["role_id"]].append(wl)
    tasks_by_workload: Dict[str, List] = defaultdict(list)
    for t in tasks:
        tasks_by_workload[t["workload_id"]].append(t)

    # Init LLM generator if needed
    generator = None
    if use_llm:
        generator = BaseGenerator(llm_config=llm_config or LLMConfig())

    result = []
    for i, role in enumerate(roles, 1):
        role_data = _build_role_data(role, workloads_by_role, tasks_by_workload, skill_by_id)

        if not role_data["skills"] or not role_data["workloads"]:
            logger.warning(f"Skipping {role['name']}: no skills or workloads")
            continue

        logger.info(f"[{i}/{len(roles)}] Mapping skills for: {role['name']}")

        if use_llm and generator:
            task_skill_map = _map_skills_with_llm(
                generator,
                role["name"],
                role_data["skills"],
                role_data["workloads"],
            )
        else:
            # Fallback: assign all role skills as SECONDARY to every task
            all_skills = [{"skill_name": s["name"], "relevance": "SECONDARY"} for s in role_data["skills"]]
            task_skill_map = {}
            for wl in role_data["workloads"]:
                for t in wl["tasks"]:
                    task_skill_map[t["name"]] = all_skills

        role_result = _assemble_result(
            role, role_data["skills"], role_data["workloads"],
            task_skill_map, skill_name_to_id, skill_by_id,
        )
        result.append(role_result)

    # Save per-function files
    out_dir = output.entity_dir("role_skill_mapping")
    out_dir.mkdir(parents=True, exist_ok=True)
    grouped: Dict[str, List] = defaultdict(list)
    for item in result:
        func_id = _get_function_id(item["role_id"], roles)
        grouped[func_id].append(item)

    for func_id, items in grouped.items():
        path = out_dir / f"{func_id}.json"
        with open(path, "w") as f:
            json.dump(items, f, indent=2)
        logger.info(f"Saved {path.name}: {len(items)} roles")

    logger.info(
        f"Mapped task-level skills for {len(result)} roles "
        f"across {len(grouped)} functions"
    )
    return result


def _get_function_id(role_id: str, roles: List[Dict[str, Any]]) -> str:
    """Extract function_id from role data."""
    for role in roles:
        if role["id"] == role_id:
            return role.get("function_id", "unknown")
    return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description="Generate role → workload → task → skill mapping"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM mapping; assign all role skills to all tasks (for testing)",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="LLM model (default: claude-haiku-4-5-20251001)",
    )
    args = parser.parse_args()

    output = OutputConfig()
    llm_config = LLMConfig(model=args.model) if not args.no_llm else None

    result = assemble(output, llm_config=llm_config, use_llm=not args.no_llm)
    if result:
        total_mappings = sum(r["summary"]["total_mappings"] for r in result)
        logger.info(f"Done. {len(result)} roles, {total_mappings} task-skill mappings.")
    else:
        logger.warning("No data mapped. Ensure generation has been run first.")


if __name__ == "__main__":
    main()
