"""
Models package for Etter Workflows.

Contains Pydantic models for:
- inputs: Input data models for activities and workflows
- outputs: Output data models for results
- status: Status tracking and progress models
- batch: Batch processing models
"""

from etter_workflows.models.inputs import (
    RoleOnboardingInput,
    DocumentRef,
    ExecutionContext,
    WorkflowOptions,
    RoleTaxonomyEntry,
)
from etter_workflows.models.outputs import (
    WorkflowResult,
    ActivityResult,
    StepResult,
    AssessmentOutputs,
    ErrorInfo,
    ExecutionMetrics,
)
from etter_workflows.models.status import (
    RoleStatus,
    ProgressInfo,
    WorkflowState,
    StepStatus,
)
from etter_workflows.models.batch import (
    BatchRecord,
    BatchStatus,
    BatchRoleStatus,
    BatchState,
)

__all__ = [
    # Inputs
    "RoleOnboardingInput",
    "DocumentRef",
    "ExecutionContext",
    "WorkflowOptions",
    "RoleTaxonomyEntry",
    # Outputs
    "WorkflowResult",
    "ActivityResult",
    "StepResult",
    "AssessmentOutputs",
    "ErrorInfo",
    "ExecutionMetrics",
    # Status
    "RoleStatus",
    "ProgressInfo",
    "WorkflowState",
    "StepStatus",
    # Batch
    "BatchRecord",
    "BatchStatus",
    "BatchRoleStatus",
    "BatchState",
]
