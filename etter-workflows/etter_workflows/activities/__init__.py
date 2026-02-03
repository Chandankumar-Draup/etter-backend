"""
Activities package for Etter Workflows.

Activities are atomic operations that can be executed by Temporal workers.
Each activity follows the self-similar interface contract.

Activities:
- role_setup: Create CompanyRole node, link documents
- ai_assessment: Run AI Assessment workflow

Activity Interface:
    Input: ActivityInput with context
    Output: ActivityResult with status, result, error, metrics
"""

from etter_workflows.activities.base import (
    BaseActivity,
    activity_with_retry,
)
from etter_workflows.activities.role_setup import (
    RoleSetupActivity,
    create_company_role,
    link_job_description,
)
from etter_workflows.activities.ai_assessment import (
    AIAssessmentActivity,
    run_ai_assessment,
)

__all__ = [
    # Base
    "BaseActivity",
    "activity_with_retry",
    # Role Setup
    "RoleSetupActivity",
    "create_company_role",
    "link_job_description",
    # AI Assessment
    "AIAssessmentActivity",
    "run_ai_assessment",
]
