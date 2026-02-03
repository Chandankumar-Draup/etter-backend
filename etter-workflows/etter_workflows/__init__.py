"""
Etter Workflows - Self-Service Pipeline for Role Onboarding

This package provides Temporal-based workflow orchestration for the Etter
AI transformation platform. It enables self-service role onboarding through:

- Role taxonomy management
- Document linking (JD, Process Maps)
- AI Assessment execution
- Status tracking and progress reporting

Architecture:
    - activities/: Atomic operations (Temporal Activities)
    - workflows/: Orchestration logic (Temporal Workflows)
    - models/: Shared data models (Pydantic)
    - config/: Configuration management
    - clients/: External service clients
    - mock_data/: Mock data providers for development
    - api/: FastAPI routes for HTTP interface

Usage:
    # Start the worker
    from etter_workflows.worker import start_worker
    start_worker()

    # Or use the API
    from etter_workflows.api import create_app
    app = create_app()
"""

__version__ = "0.1.0"
__author__ = "Etter Architecture Team"

from etter_workflows.models.inputs import (
    RoleOnboardingInput,
    DocumentRef,
    ExecutionContext,
)
from etter_workflows.models.outputs import (
    WorkflowResult,
    ActivityResult,
    StepResult,
)
from etter_workflows.models.status import (
    RoleStatus,
    ProgressInfo,
    WorkflowState,
)

__all__ = [
    # Inputs
    "RoleOnboardingInput",
    "DocumentRef",
    "ExecutionContext",
    # Outputs
    "WorkflowResult",
    "ActivityResult",
    "StepResult",
    # Status
    "RoleStatus",
    "ProgressInfo",
    "WorkflowState",
]
