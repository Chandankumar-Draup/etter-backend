"""
Work content data models.

Workload: A coherent block of work within a role (3-5 per role).
Task: An atomic unit of work within a workload (5-10 per workload).

The cascade engine operates primarily on these entities:
Technology change -> Task reclassification -> Workload recomposition -> Role impact
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Workload:
    """A named block of work that a role performs."""
    id: str
    name: str
    role_id: str
    description: str = ""
    effort_allocation_pct: float = 0.0  # % of role's time
    automation_level: str = "human_led"  # human_only, human_led, shared, ai_led, ai_only
    skill_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workload":
        return cls(**data)


@dataclass
class Task:
    """An atomic unit of work within a workload."""
    id: str
    name: str
    workload_id: str
    description: str = ""
    classification: str = "task_iteration"  # Etter 6-category AI automation potential
    time_allocation_pct: float = 0.0  # % of workload's time
    automation_potential: float = 0.0  # 0-100
    automation_level: str = "human_led"
    current_tool_ids: List[str] = field(default_factory=list)
    future_tool_ids: List[str] = field(default_factory=list)
    skill_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**data)
