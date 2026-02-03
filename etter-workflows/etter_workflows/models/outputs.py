"""
Output models for Etter Workflows.

These models define the data structures for workflow and activity outputs,
following the self-similar interface contract defined in the implementation plan.

Interface Contract:
    OUTPUT:
    {
        "id": "same-identifier",
        "status": "pending | running | completed | failed",
        "progress": { "current": N, "total": M },
        "outputs": { ... } | null,
        "error": { "code": "...", "message": "...", "recoverable": bool } | null
    }
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """Status of an activity or workflow result."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ErrorInfo(BaseModel):
    """
    Error information for failed operations.

    Attributes:
        code: Error code for programmatic handling
        message: Human-readable error message
        recoverable: Whether the error can be recovered by retry
        details: Additional error details
        timestamp: When the error occurred
    """
    code: str
    message: str
    recoverable: bool = True
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_exception(cls, e: Exception, code: str = "UNKNOWN_ERROR") -> "ErrorInfo":
        """Create ErrorInfo from an exception."""
        return cls(
            code=code,
            message=str(e),
            recoverable=False,
            details={"exception_type": type(e).__name__},
        )


class ExecutionMetrics(BaseModel):
    """
    Metrics for activity/workflow execution.

    Attributes:
        duration_ms: Execution time in milliseconds
        tokens_used: LLM tokens consumed (if applicable)
        api_calls: Number of external API calls
        retries: Number of retry attempts
        started_at: When execution started
        completed_at: When execution completed
    """
    duration_ms: int = 0
    tokens_used: Optional[int] = None
    api_calls: int = 0
    retries: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration_ms / 1000.0


class ActivityResult(BaseModel):
    """
    Result of an activity execution.

    Follows the self-similar interface contract for atomic operations.

    Attributes:
        id: Request identifier (same as input)
        status: Result status (success, partial, failed)
        result: Domain-specific output data
        error: Error information if failed
        metrics: Execution metrics
    """
    id: str
    status: ResultStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)

    @property
    def success(self) -> bool:
        """Check if the activity succeeded."""
        return self.status == ResultStatus.SUCCESS

    @classmethod
    def create_success(
        cls,
        id: str,
        result: Dict[str, Any],
        metrics: Optional[ExecutionMetrics] = None
    ) -> "ActivityResult":
        """Create a successful activity result."""
        return cls(
            id=id,
            status=ResultStatus.SUCCESS,
            result=result,
            metrics=metrics or ExecutionMetrics(),
        )

    @classmethod
    def create_failure(
        cls,
        id: str,
        error: ErrorInfo,
        metrics: Optional[ExecutionMetrics] = None
    ) -> "ActivityResult":
        """Create a failed activity result."""
        return cls(
            id=id,
            status=ResultStatus.FAILED,
            error=error,
            metrics=metrics or ExecutionMetrics(),
        )


class StepResult(BaseModel):
    """
    Result of a workflow step.

    Attributes:
        name: Step name (e.g., "role_setup", "ai_assessment")
        status: Step status
        duration_ms: Step execution time
        started_at: When step started
        data: Step output data
        error: Error if step failed
    """
    name: str
    status: ResultStatus
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None


class AssessmentOutputs(BaseModel):
    """
    Outputs from the AI Assessment workflow.

    Attributes:
        ai_automation_score: Primary automation score (0-100)
        validated_automation_score: Validated/adjusted score
        task_analysis: Task breakdown and analysis
        impact_analysis: AI impact analysis text
        key_metrics: Summary metrics
    """
    ai_automation_score: float = 0.0
    validated_automation_score: Optional[float] = None
    task_analysis: Optional[Dict[str, Any]] = None
    impact_analysis: Optional[str] = None
    key_metrics: Optional[Dict[str, Any]] = None

    @property
    def final_score(self) -> float:
        """Get the final score (validated if available, else primary)."""
        return self.validated_automation_score or self.ai_automation_score


class WorkflowResult(BaseModel):
    """
    Result of a workflow execution.

    Follows the self-similar interface contract for composite operations.

    Attributes:
        workflow_id: Temporal workflow ID
        role_id: Created/updated role ID
        status: Overall workflow status
        steps_completed: List of completed step results
        outputs: Assessment outputs (if completed)
        error: Error information if failed
        dashboard_url: URL to view results in CHRO dashboard
        created_at: When workflow started
        completed_at: When workflow completed
    """
    workflow_id: str
    role_id: Optional[str] = None
    status: ResultStatus
    steps_completed: List[StepResult] = Field(default_factory=list)
    outputs: Optional[AssessmentOutputs] = None
    error: Optional[ErrorInfo] = None
    dashboard_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == ResultStatus.SUCCESS

    @property
    def total_duration_ms(self) -> int:
        """Get total execution time across all steps."""
        return sum(s.duration_ms for s in self.steps_completed)

    def get_step(self, name: str) -> Optional[StepResult]:
        """Get a specific step result by name."""
        for step in self.steps_completed:
            if step.name == name:
                return step
        return None

    def add_step(self, step: StepResult) -> None:
        """Add a step result to the workflow."""
        self.steps_completed.append(step)

    @classmethod
    def create_success(
        cls,
        workflow_id: str,
        role_id: str,
        steps: List[StepResult],
        outputs: Optional[AssessmentOutputs] = None,
        dashboard_url: Optional[str] = None,
    ) -> "WorkflowResult":
        """Create a successful workflow result."""
        return cls(
            workflow_id=workflow_id,
            role_id=role_id,
            status=ResultStatus.SUCCESS,
            steps_completed=steps,
            outputs=outputs,
            dashboard_url=dashboard_url,
            completed_at=datetime.utcnow(),
        )

    @classmethod
    def create_failure(
        cls,
        workflow_id: str,
        error: ErrorInfo,
        steps: Optional[List[StepResult]] = None,
        role_id: Optional[str] = None,
    ) -> "WorkflowResult":
        """Create a failed workflow result."""
        return cls(
            workflow_id=workflow_id,
            role_id=role_id,
            status=ResultStatus.FAILED,
            steps_completed=steps or [],
            error=error,
            completed_at=datetime.utcnow(),
        )
