"""
Workflow data models.

Workflow: A cross-role business process with rich task-level analytics.
WorkflowTask: A task within a workflow, with impact scores, automation type,
    role assignments, and skill requirements.

Workflows represent the horizontal (process) dimension,
complementing the vertical (taxonomy) dimension.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class WorkflowTask:
    """A task within a workflow with enriched metadata.

    Maps to DTWorkflowTask in the graph. Complex fields (score_breakdown,
    primary_role, supporting_roles, skills_required, dependencies) are
    stored in JSON files but stripped for Neo4j loading.
    """
    id: str
    workflow_id: str
    sequence_number: int
    name: str
    role_id: str = ""
    description: str = ""
    expected_output: str = ""
    automation_type: str = "Human+AI"  # AI, Human+AI, Human
    time_hours: float = 1.0
    complexity: str = "moderate"  # simple, moderate, complex
    workload: str = "medium"  # low, medium, high
    impact_score: float = 0.0
    score_breakdown: Dict[str, str] = field(default_factory=lambda: {
        "time_investment": "medium",
        "strategic_value": "medium",
        "error_reduction": "medium",
        "scalability": "medium",
    })
    automation_priority: str = "medium"  # high, medium, low
    dependencies: List[int] = field(default_factory=list)
    skills_required: List[str] = field(default_factory=list)
    primary_role: Dict[str, Any] = field(default_factory=dict)
    supporting_roles: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTask":
        valid_keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in valid_keys})


@dataclass
class Workflow:
    """A business process with enriched analytics.

    Contains tasks (ordered), computed summary/metrics, and
    derived insights (quick_wins, opportunities, patterns, recommendations).
    """
    id: str
    name: str
    function_id: str
    description: str = ""
    objective: str = ""
    priority: str = "high"  # high, medium, low
    frequency: str = "daily"  # daily, weekly, monthly, quarterly, ad_hoc
    avg_cycle_time_hours: float = 0.0
    ai_optimization_score: float = 0.0
    tasks: List[WorkflowTask] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    workflow_metrics: Dict[str, Any] = field(default_factory=dict)
    quick_wins: List[Dict[str, Any]] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        tasks_data = data.pop("tasks", [])
        valid_keys = cls.__dataclass_fields__.keys()
        wf = cls(**{k: v for k, v in data.items() if k in valid_keys})
        wf.tasks = [WorkflowTask.from_dict(t) for t in tasks_data]
        return wf
