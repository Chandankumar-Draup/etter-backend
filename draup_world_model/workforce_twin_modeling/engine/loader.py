"""
Data loader for the Workforce Twin simulation.
Reads CSV files into typed dataclass instances.
Principle: I/O at the boundary, pure computation inside.
"""
import csv
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List
from workforce_twin_modeling.models.organization import (
    Task, Role, Workload, Skill, Tool, HumanSystem
)


@dataclass
class OrganizationData:
    """Complete loaded dataset — the org's current state."""
    roles: Dict[str, Role] = field(default_factory=dict)
    workloads: Dict[str, Workload] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    skills: Dict[str, Skill] = field(default_factory=dict)
    tools: Dict[str, Tool] = field(default_factory=dict)
    human_system: Dict[str, HumanSystem] = field(default_factory=dict)

    # Index lookups (built after loading)
    workloads_by_role: Dict[str, List[str]] = field(default_factory=dict)
    tasks_by_workload: Dict[str, List[str]] = field(default_factory=dict)
    skills_by_workload: Dict[str, List[str]] = field(default_factory=dict)
    roles_by_function: Dict[str, List[str]] = field(default_factory=dict)
    roles_by_jfg: Dict[str, List[str]] = field(default_factory=dict)

    def build_indexes(self):
        """Build reverse-lookup indexes for efficient traversal."""
        self.workloads_by_role = {}
        self.tasks_by_workload = {}
        self.skills_by_workload = {}
        self.roles_by_function = {}
        self.roles_by_jfg = {}

        for wl in self.workloads.values():
            self.workloads_by_role.setdefault(wl.role_id, []).append(wl.workload_id)

        for task in self.tasks.values():
            self.tasks_by_workload.setdefault(task.workload_id, []).append(task.task_id)

        for skill in self.skills.values():
            self.skills_by_workload.setdefault(skill.workload_id, []).append(skill.skill_id)

        for role in self.roles.values():
            self.roles_by_function.setdefault(role.function, []).append(role.role_id)
            self.roles_by_jfg.setdefault(role.jfg, []).append(role.role_id)

    @property
    def total_headcount(self) -> int:
        return sum(r.headcount for r in self.roles.values())

    @property
    def total_annual_cost(self) -> float:
        return sum(r.annual_cost for r in self.roles.values())

    @property
    def functions(self) -> List[str]:
        return sorted(set(r.function for r in self.roles.values()))


def _read_csv(path: Path) -> List[dict]:
    """Read a CSV file into a list of dicts."""
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def _parse_bool(value: str) -> bool:
    """Parse boolean from CSV string."""
    return value.strip().lower() in ('true', '1', 'yes')


def _parse_list(value: str) -> list:
    """Parse comma-separated string into list."""
    if not value or value.strip() == '':
        return []
    return [x.strip() for x in value.split(',')]


def load_organization(data_dir: str) -> OrganizationData:
    """
    Load all CSV files from data_dir into an OrganizationData instance.
    This is the single entry point for all data I/O.
    """
    data_path = Path(data_dir)
    org = OrganizationData()

    # Load roles
    for row in _read_csv(data_path / "roles.csv"):
        org.roles[row["role_id"]] = Role(
            role_id=row["role_id"],
            role_name=row["role_name"],
            function=row["function"],
            sub_function=row["sub_function"],
            jfg=row["jfg"],
            job_family=row["job_family"],
            management_level=row["management_level"],
            headcount=int(row["headcount"]),
            avg_salary=float(row["avg_salary"]),
            automation_score=float(row["automation_score"]),
            augmentation_score=float(row["augmentation_score"]),
            quantification_score=float(row["quantification_score"]),
        )

    # Load workloads
    for row in _read_csv(data_path / "workloads.csv"):
        org.workloads[row["workload_id"]] = Workload(
            workload_id=row["workload_id"],
            role_id=row["role_id"],
            workload_name=row["workload_name"],
            time_pct=float(row["time_pct"]),
            directive_pct=float(row["directive_pct"]),
            feedback_loop_pct=float(row["feedback_loop_pct"]),
            task_iteration_pct=float(row["task_iteration_pct"]),
            learning_pct=float(row["learning_pct"]),
            validation_pct=float(row["validation_pct"]),
            negligibility_pct=float(row["negligibility_pct"]),
        )

    # Load tasks
    for row in _read_csv(data_path / "tasks.csv"):
        tool_str = row.get("automatable_by_tool", "").strip()
        org.tasks[row["task_id"]] = Task(
            task_id=row["task_id"],
            workload_id=row["workload_id"],
            task_name=row["task_name"],
            category=row["category"],
            effort_hours_month=float(row["effort_hours_month"]),
            automatable_by_tool=tool_str if tool_str else None,
            compliance_mandated_human=_parse_bool(row.get("compliance_mandated_human", "False")),
        )

    # Load skills
    for row in _read_csv(data_path / "skills.csv"):
        org.skills[row["skill_id"]] = Skill(
            skill_id=row["skill_id"],
            workload_id=row["workload_id"],
            skill_name=row["skill_name"],
            skill_type=row["skill_type"],
            proficiency_required=int(row["proficiency_required"]),
            is_sunrise=_parse_bool(row.get("is_sunrise", "False")),
            is_sunset=_parse_bool(row.get("is_sunset", "False")),
        )

    # Load tech stack
    for row in _read_csv(data_path / "tech_stack.csv"):
        org.tools[row["tool_id"]] = Tool(
            tool_id=row["tool_id"],
            tool_name=row["tool_name"],
            deployed_to_functions=_parse_list(row["deployed_to_function"]),
            task_categories_addressed=_parse_list(row["task_categories_addressed"]),
            license_cost_per_user_month=float(row["license_cost_per_user_month"]),
            current_adoption_pct=float(row["current_adoption_pct"]),
        )

    # Load human system
    for row in _read_csv(data_path / "human_system.csv"):
        org.human_system[row["function"]] = HumanSystem(
            function=row["function"],
            ai_proficiency=float(row["ai_proficiency"]),
            change_readiness=float(row["change_readiness"]),
            trust_level=float(row["trust_level"]),
            political_capital=float(row["political_capital"]),
            transformation_fatigue=float(row["transformation_fatigue"]),
            learning_velocity_months=float(row["learning_velocity_months"]),
        )

    # Build indexes for efficient traversal
    org.build_indexes()

    return org
