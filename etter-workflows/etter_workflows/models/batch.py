"""
Batch processing models for Etter Workflows.

These models support batch role onboarding where multiple roles
can be submitted together and tracked as a group.

Design Principle: "Each role is independent, batches are just bookkeeping"
- No parent workflow coordinating children (over-engineering)
- No custom rate limiting code (Temporal handles it)
- No complex batch state machine (roles have their own states)
- No transactional "all or nothing" (partial success is fine)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class BatchState(str, Enum):
    """
    Aggregate state for a batch based on constituent workflow states.

    This is computed from individual role states, not stored.
    """
    PENDING = "pending"          # All roles queued, none started
    IN_PROGRESS = "in_progress"  # At least one processing
    COMPLETED = "completed"      # All done (success or fail)
    PARTIAL = "partial"          # Some succeeded, some failed


class BatchRoleStatus(BaseModel):
    """
    Status of a single role within a batch.

    Lightweight view for batch status aggregation.
    """
    role_name: str
    company_id: str
    workflow_id: str
    status: str  # WorkflowState value
    error: Optional[str] = None
    dashboard_url: Optional[str] = None


class BatchRecord(BaseModel):
    """
    Record of a batch submission.

    This is the core model for batch tracking:
    - batch_id: Unique identifier for the batch
    - workflow_ids: List of individual workflow IDs (one per role)
    - created_at: When batch was submitted
    - created_by: User/system that submitted
    - company_id: Company the batch belongs to (for filtering)

    Key insight: The batch is just bookkeeping.
    Each workflow is independent and executes on its own.
    """
    batch_id: str = Field(default_factory=lambda: f"batch-{uuid.uuid4().hex[:12]}")
    workflow_ids: List[str] = Field(default_factory=list)
    company_id: str
    role_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_workflow(self, workflow_id: str) -> None:
        """Add a workflow to the batch."""
        self.workflow_ids.append(workflow_id)
        self.role_count = len(self.workflow_ids)


class BatchStatus(BaseModel):
    """
    Aggregated status for a batch.

    Computed by querying individual workflow statuses and aggregating.

    Example response:
    {
        "batch_id": "batch-123",
        "total": 50,
        "completed": 35,
        "failed": 2,
        "in_progress": 13,
        "roles": [
            {"role": "Data Analyst", "status": "READY", "workflow_id": "wf-1"},
            {"role": "ML Engineer", "status": "FAILED", "error": "...", "workflow_id": "wf-2"},
            ...
        ]
    }
    """
    batch_id: str
    company_id: str
    total: int = 0
    queued: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    created_at: Optional[datetime] = None
    roles: List[BatchRoleStatus] = Field(default_factory=list)

    @property
    def state(self) -> BatchState:
        """Compute aggregate state from role counts."""
        if self.total == 0:
            return BatchState.PENDING

        done = self.completed + self.failed

        if done == 0:
            if self.in_progress > 0:
                return BatchState.IN_PROGRESS
            return BatchState.PENDING
        elif done == self.total:
            if self.failed > 0 and self.completed > 0:
                return BatchState.PARTIAL
            return BatchState.COMPLETED
        else:
            return BatchState.IN_PROGRESS

    @property
    def progress_percent(self) -> float:
        """Calculate overall progress percentage."""
        if self.total == 0:
            return 0.0
        return ((self.completed + self.failed) / self.total) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate of completed roles."""
        done = self.completed + self.failed
        if done == 0:
            return 0.0
        return (self.completed / done) * 100

    def get_failed_workflow_ids(self) -> List[str]:
        """Get workflow IDs of failed roles for retry."""
        return [r.workflow_id for r in self.roles if r.status == "failed"]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary for logging/display."""
        return {
            "batch_id": self.batch_id,
            "state": self.state.value,
            "progress": f"{self.completed + self.failed}/{self.total}",
            "success_rate": f"{self.success_rate:.1f}%",
            "queued": self.queued,
            "in_progress": self.in_progress,
            "completed": self.completed,
            "failed": self.failed,
        }
