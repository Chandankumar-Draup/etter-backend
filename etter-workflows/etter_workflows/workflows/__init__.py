"""
Workflows package for Etter Workflows.

Workflows orchestrate activities to complete business processes.
Each workflow follows the self-similar interface contract.

Workflows:
- role_onboarding: Full pipeline for role setup and AI assessment

Workflow Interface:
    Input: WorkflowInput with company_id, role_name, documents, options
    Output: WorkflowResult with role_id, status, steps, outputs, error
"""

from etter_workflows.workflows.base import (
    BaseWorkflow,
    WorkflowStep,
)
from etter_workflows.workflows.role_onboarding import (
    RoleOnboardingWorkflow,
    execute_role_onboarding,
)

__all__ = [
    # Base
    "BaseWorkflow",
    "WorkflowStep",
    # Role Onboarding
    "RoleOnboardingWorkflow",
    "execute_role_onboarding",
]
