"""
API schemas for Etter Workflows.

Request and response models for the REST API endpoints.
Based on the API design in the implementation plan.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentInput(BaseModel):
    """Document input for push request."""
    type: str = Field(description="Document type (job_description, process_map)")
    uri: Optional[str] = Field(default=None, description="URI to the document")
    content: Optional[str] = Field(default=None, description="Inline document content")
    name: Optional[str] = Field(default=None, description="Document name")


class PushOptions(BaseModel):
    """Options for push request."""
    skip_enhancement_workflows: bool = Field(
        default=False,
        description="Skip enhancement workflows (skills, task feasibility)"
    )
    force_rerun: bool = Field(
        default=False,
        description="Force re-run even if results exist"
    )
    notify_on_complete: bool = Field(
        default=True,
        description="Send notification when complete"
    )


class PushRequest(BaseModel):
    """
    Request model for POST /api/v1/pipeline/push.

    Example:
    {
        "company_id": "liberty-mutual",
        "role_name": "Claims Adjuster",
        "documents": [
            {"type": "job_description", "uri": "s3://bucket/jd.pdf"}
        ],
        "draup_role_id": "draup-role-12345",
        "options": {
            "skip_enhancement_workflows": false,
            "notify_on_complete": true
        }
    }
    """
    company_id: str = Field(description="Company identifier")
    role_name: str = Field(description="Role name to onboard")
    documents: List[DocumentInput] = Field(
        default_factory=list,
        description="Documents to link (JD, process maps)"
    )
    draup_role_id: Optional[str] = Field(
        default=None,
        description="Draup role mapping ID"
    )
    draup_role_name: Optional[str] = Field(
        default=None,
        description="Draup role name"
    )
    options: PushOptions = Field(
        default_factory=PushOptions,
        description="Workflow options"
    )


class PushResponse(BaseModel):
    """
    Response model for POST /api/v1/pipeline/push.

    Example:
    {
        "workflow_id": "role-onboard-abc123",
        "role_id": "cr-liberty-claims-adjuster",
        "status": "queued",
        "estimated_duration_seconds": 600,
        "position_in_queue": 3
    }
    """
    workflow_id: str = Field(description="Temporal workflow ID")
    role_id: Optional[str] = Field(
        default=None,
        description="CompanyRole ID (populated after role_setup)"
    )
    status: str = Field(description="Current workflow status")
    estimated_duration_seconds: Optional[int] = Field(
        default=None,
        description="Estimated time to complete"
    )
    position_in_queue: Optional[int] = Field(
        default=None,
        description="Position in queue (if queued)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Status message"
    )


class StepProgress(BaseModel):
    """Progress information for a single step."""
    name: str = Field(description="Step name")
    status: str = Field(description="Step status (pending, running, completed, failed)")
    duration_ms: Optional[int] = Field(default=None, description="Step duration in ms")
    started_at: Optional[datetime] = Field(default=None, description="When step started")
    completed_at: Optional[datetime] = Field(default=None, description="When step completed")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class ProgressInfo(BaseModel):
    """Progress information for the workflow."""
    current: int = Field(description="Current step number")
    total: int = Field(description="Total number of steps")
    steps: List[StepProgress] = Field(description="Progress for each step")


class StatusResponse(BaseModel):
    """
    Response model for GET /api/v1/pipeline/status/{workflow_id}.

    Example:
    {
        "workflow_id": "role-onboard-abc123",
        "role_id": "cr-liberty-claims-adjuster",
        "status": "processing",
        "current_step": "ai_assessment",
        "progress": {
            "current": 2,
            "total": 5,
            "steps": [
                {"name": "role_setup", "status": "completed", "duration_ms": 1200},
                {"name": "ai_assessment", "status": "running", "started_at": "..."}
            ]
        },
        "dashboard_url": null,
        "error": null
    }
    """
    workflow_id: str = Field(description="Workflow ID")
    role_id: Optional[str] = Field(default=None, description="CompanyRole ID")
    company_id: str = Field(description="Company identifier")
    role_name: str = Field(description="Role name")
    status: str = Field(description="Current workflow status")
    current_step: Optional[str] = Field(default=None, description="Currently executing step")
    progress: ProgressInfo = Field(description="Progress information")
    queued_at: Optional[datetime] = Field(default=None, description="When queued")
    started_at: Optional[datetime] = Field(default=None, description="When processing started")
    completed_at: Optional[datetime] = Field(default=None, description="When completed")
    position_in_queue: Optional[int] = Field(default=None, description="Queue position")
    estimated_duration_seconds: Optional[int] = Field(default=None, description="Estimated time")
    dashboard_url: Optional[str] = Field(default=None, description="Dashboard URL when ready")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service status")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(description="Current timestamp")
    components: Dict[str, str] = Field(description="Component health status")


class CompanyRolesRequest(BaseModel):
    """Request to get available roles for a company."""
    company_name: str = Field(description="Company name")


class CompanyRolesResponse(BaseModel):
    """Response with available roles for a company."""
    company_name: str
    roles: List[Dict[str, Any]]
    total_count: int


# =============================================================================
# Batch Processing Schemas
# =============================================================================

class BatchRoleInput(BaseModel):
    """
    Single role input for batch submission.

    Simplified version of PushRequest for batch processing.
    """
    company_id: str = Field(description="Company identifier")
    role_name: str = Field(description="Role name to onboard")
    documents: List[DocumentInput] = Field(
        default_factory=list,
        description="Documents to link (JD, process maps)"
    )
    draup_role_id: Optional[str] = Field(
        default=None,
        description="Draup role mapping ID"
    )
    draup_role_name: Optional[str] = Field(
        default=None,
        description="Draup role name"
    )


class BatchPushRequest(BaseModel):
    """
    Request model for POST /api/v1/pipeline/push-batch.

    Example:
    {
        "company_id": "liberty-mutual",
        "roles": [
            {"role_name": "Claims Adjuster", "draup_role_name": "Claims Handler"},
            {"role_name": "Underwriter", "draup_role_name": "Insurance Underwriter"},
            {"role_name": "Risk Analyst"}
        ],
        "options": {
            "skip_enhancement_workflows": false
        }
    }
    """
    company_id: str = Field(description="Company identifier (default for all roles)")
    roles: List[BatchRoleInput] = Field(
        description="List of roles to onboard"
    )
    options: PushOptions = Field(
        default_factory=PushOptions,
        description="Workflow options (applied to all roles)"
    )
    created_by: Optional[str] = Field(
        default=None,
        description="User/system submitting the batch"
    )


class BatchRoleStatusResponse(BaseModel):
    """Status of a single role within a batch."""
    role_name: str
    company_id: str
    workflow_id: str
    status: str
    error: Optional[str] = None
    dashboard_url: Optional[str] = None


class BatchPushResponse(BaseModel):
    """
    Response model for POST /api/v1/pipeline/push-batch.

    Example:
    {
        "batch_id": "batch-abc123def456",
        "total_roles": 3,
        "workflow_ids": ["wf-1", "wf-2", "wf-3"],
        "status": "queued",
        "message": "Batch submitted: 3 roles queued for processing"
    }
    """
    batch_id: str = Field(description="Batch identifier")
    total_roles: int = Field(description="Number of roles in batch")
    workflow_ids: List[str] = Field(description="Workflow IDs for each role")
    status: str = Field(description="Initial batch status")
    estimated_duration_seconds: Optional[int] = Field(
        default=None,
        description="Estimated time to complete all roles"
    )
    message: Optional[str] = Field(default=None, description="Status message")


class BatchStatusResponse(BaseModel):
    """
    Response model for GET /api/v1/pipeline/batch-status/{batch_id}.

    Example:
    {
        "batch_id": "batch-123",
        "total": 50,
        "completed": 35,
        "failed": 2,
        "in_progress": 13,
        "state": "in_progress",
        "progress_percent": 74.0,
        "roles": [
            {"role_name": "Data Analyst", "status": "ready", "workflow_id": "wf-1"},
            {"role_name": "ML Engineer", "status": "failed", "error": "...", "workflow_id": "wf-2"}
        ]
    }
    """
    batch_id: str = Field(description="Batch identifier")
    company_id: str = Field(description="Company identifier")
    total: int = Field(description="Total roles in batch")
    queued: int = Field(description="Roles waiting in queue")
    in_progress: int = Field(description="Roles currently processing")
    completed: int = Field(description="Successfully completed roles")
    failed: int = Field(description="Failed roles")
    state: str = Field(description="Aggregate batch state")
    progress_percent: float = Field(description="Overall progress percentage")
    success_rate: float = Field(description="Success rate of completed roles")
    created_at: Optional[datetime] = None
    roles: List[BatchRoleStatusResponse] = Field(
        default_factory=list,
        description="Status of each role"
    )


class BatchRetryRequest(BaseModel):
    """
    Request model for POST /api/v1/pipeline/retry-failed/{batch_id}.

    By default, retries all failed roles. Can optionally specify
    which workflow IDs to retry.
    """
    workflow_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific workflow IDs to retry (default: all failed)"
    )
    options: PushOptions = Field(
        default_factory=PushOptions,
        description="Workflow options for retry"
    )


class BatchRetryResponse(BaseModel):
    """
    Response model for POST /api/v1/pipeline/retry-failed/{batch_id}.
    """
    batch_id: str = Field(description="Original batch ID")
    retried_count: int = Field(description="Number of roles retried")
    new_workflow_ids: List[str] = Field(description="New workflow IDs for retried roles")
    message: str = Field(description="Status message")
