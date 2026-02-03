"""
Status models for Etter Workflows.

These models define the state machine for role lifecycle and progress tracking.
Based on the state machine design in the implementation plan.

States:
    DRAFT → QUEUED → PROCESSING → READY
                  ↓           ↓
            VALIDATION_ERROR  FAILED → (retry) → QUEUED
                              DEGRADED
    READY → STALE → (re-run) → QUEUED
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    """
    State machine states for role lifecycle.

    Based on the role lifecycle state machine in the implementation plan.
    """
    # Initial states
    DRAFT = "draft"                      # In Taxonomy, not yet pushed

    # Processing states
    QUEUED = "queued"                    # In queue, waiting for worker
    PROCESSING = "processing"            # Currently being processed

    # Completion states
    READY = "ready"                      # Successfully completed, visible in dashboard
    DEGRADED = "degraded"                # Partial success (some workflows failed)

    # Error states
    VALIDATION_ERROR = "validation_error"  # Failed input validation
    FAILED = "failed"                    # Processing failed

    # Update states
    STALE = "stale"                      # Inputs changed, needs re-assessment


class ProcessingSubState(str, Enum):
    """
    Sub-states during PROCESSING state.

    These provide more granular visibility into the current step.
    """
    ROLE_SETUP = "role_setup"
    DOCUMENT_LINKING = "document_linking"
    AI_ASSESSMENT = "ai_assessment"
    SKILLS_ANALYSIS = "skills_analysis"
    TASK_FEASIBILITY = "task_feasibility"
    FINALIZE = "finalize"


class StepStatus(str, Enum):
    """Status of an individual workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepProgress(BaseModel):
    """
    Progress information for a single step.

    Attributes:
        name: Step name
        status: Step status
        duration_ms: Execution time if completed
        started_at: When step started
        completed_at: When step completed
        error_message: Error message if failed
    """
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ProgressInfo(BaseModel):
    """
    Progress information for workflow execution.

    This follows the self-similar interface contract:
    "progress": { "current": N, "total": M }

    Attributes:
        current: Current step number (1-indexed)
        total: Total number of steps
        percentage: Completion percentage (0-100)
        steps: Detailed progress for each step
        current_step_name: Name of currently executing step
    """
    current: int = 0
    total: int = 5  # Default: role_setup, doc_link, ai_assess, skills, finalize
    steps: List[StepProgress] = Field(default_factory=list)
    current_step_name: Optional[str] = None

    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    def update_step(
        self,
        name: str,
        status: StepStatus,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update a step's status."""
        for step in self.steps:
            if step.name == name:
                step.status = status
                if status == StepStatus.RUNNING:
                    step.started_at = datetime.utcnow()
                    self.current_step_name = name
                elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
                    step.completed_at = datetime.utcnow()
                    step.duration_ms = duration_ms
                    step.error_message = error_message
                    # Update current count
                    if status == StepStatus.COMPLETED:
                        self.current = sum(
                            1 for s in self.steps
                            if s.status == StepStatus.COMPLETED
                        )
                return

        # Step not found, add it
        new_step = StepProgress(
            name=name,
            status=status,
            started_at=datetime.utcnow() if status == StepStatus.RUNNING else None,
        )
        self.steps.append(new_step)

    @classmethod
    def create_for_workflow(cls, step_names: List[str]) -> "ProgressInfo":
        """Create progress info with predefined steps."""
        steps = [StepProgress(name=name) for name in step_names]
        return cls(
            current=0,
            total=len(steps),
            steps=steps,
        )


class RoleStatus(BaseModel):
    """
    Complete status information for a role in the pipeline.

    This is the main status model used for UI display and API responses.

    Attributes:
        workflow_id: Temporal workflow ID
        role_id: CompanyRole ID
        company_id: Company identifier
        role_name: Role name
        state: Current workflow state
        sub_state: Sub-state during processing
        progress: Detailed progress information
        queued_at: When role was queued
        started_at: When processing started
        completed_at: When processing completed
        position_in_queue: Position in queue (if queued)
        estimated_duration_seconds: Estimated time to complete
        error: Error information if failed
        dashboard_url: URL to view results (if ready)
        metadata: Additional metadata
    """
    workflow_id: str
    role_id: Optional[str] = None
    company_id: str
    role_name: str
    state: WorkflowState
    sub_state: Optional[ProcessingSubState] = None
    progress: ProgressInfo = Field(default_factory=ProgressInfo)
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    position_in_queue: Optional[int] = None
    estimated_duration_seconds: Optional[int] = None
    error: Optional[Dict[str, Any]] = None
    dashboard_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the state is a terminal state."""
        return self.state in (
            WorkflowState.READY,
            WorkflowState.FAILED,
            WorkflowState.DEGRADED,
            WorkflowState.VALIDATION_ERROR,
        )

    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully."""
        return self.state == WorkflowState.READY

    @property
    def is_processing(self) -> bool:
        """Check if the workflow is currently processing."""
        return self.state in (WorkflowState.QUEUED, WorkflowState.PROCESSING)

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format."""
        response = {
            "workflow_id": self.workflow_id,
            "role_id": self.role_id,
            "status": self.state.value,
            "current_step": self.sub_state.value if self.sub_state else None,
            "progress": {
                "current": self.progress.current,
                "total": self.progress.total,
                "steps": [
                    {
                        "name": s.name,
                        "status": s.status.value,
                        "duration_ms": s.duration_ms,
                    }
                    for s in self.progress.steps
                ],
            },
            "dashboard_url": self.dashboard_url,
            "error": self.error,
        }

        if self.position_in_queue is not None:
            response["position_in_queue"] = self.position_in_queue

        if self.estimated_duration_seconds is not None:
            response["estimated_duration_seconds"] = self.estimated_duration_seconds

        return response


# State transition rules
VALID_TRANSITIONS = {
    WorkflowState.DRAFT: [WorkflowState.QUEUED, WorkflowState.VALIDATION_ERROR],
    WorkflowState.QUEUED: [WorkflowState.PROCESSING],
    WorkflowState.PROCESSING: [
        WorkflowState.READY,
        WorkflowState.DEGRADED,
        WorkflowState.FAILED,
    ],
    WorkflowState.FAILED: [WorkflowState.QUEUED],  # Retry
    WorkflowState.READY: [WorkflowState.STALE],
    WorkflowState.STALE: [WorkflowState.QUEUED],  # Re-run
    WorkflowState.VALIDATION_ERROR: [WorkflowState.DRAFT],  # User fixes
    WorkflowState.DEGRADED: [WorkflowState.QUEUED],  # Retry
}


def can_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    """Check if a state transition is valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, [])
