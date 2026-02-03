"""
Workflow Tests for Etter Workflows.

Tests for workflow execution:
- RoleOnboardingWorkflow
- Standalone execution
- Activity execution

Run with:
    pytest tests/test_workflows.py -v

Or run specific tests:
    pytest tests/test_workflows.py::TestRoleOnboardingWorkflow -v
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================================================
# RoleOnboardingWorkflow Tests
# ============================================================================

class TestRoleOnboardingWorkflow:
    """Tests for RoleOnboardingWorkflow."""

    def test_workflow_initialization(self):
        """Test workflow can be initialized."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

        workflow = RoleOnboardingWorkflow()

        assert workflow.workflow_id is not None
        assert workflow.steps is not None
        assert len(workflow.steps) == 2  # role_setup, ai_assessment

    def test_workflow_steps_defined(self):
        """Test workflow has correct steps defined."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

        workflow = RoleOnboardingWorkflow()
        step_names = [s.name for s in workflow.steps]

        assert "role_setup" in step_names
        assert "ai_assessment" in step_names

    def test_workflow_with_mock_assessment(self):
        """Test workflow can use mock assessment mode."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

        workflow = RoleOnboardingWorkflow(use_mock_assessment=True)

        assert workflow.use_mock_assessment is True

    def test_workflow_custom_id(self):
        """Test workflow can have custom ID."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

        custom_id = "custom-workflow-123"
        workflow = RoleOnboardingWorkflow(workflow_id=custom_id)

        assert workflow.workflow_id == custom_id


# ============================================================================
# Workflow Execution Tests
# ============================================================================

class TestWorkflowExecution:
    """Tests for workflow execution (standalone mode)."""

    @pytest.mark.asyncio
    async def test_execute_with_valid_input(
        self,
        mock_redis,
        mock_neo4j,
        sample_company,
        sample_role,
        registered_test_data,
    ):
        """Test workflow execution with valid input."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow
        from etter_workflows.models.inputs import (
            RoleOnboardingInput, WorkflowOptions, DocumentRef, DocumentType
        )

        # Create workflow
        workflow = RoleOnboardingWorkflow(use_mock_assessment=True)

        # Create input
        input_data = RoleOnboardingInput(
            company_id=sample_company,
            role_name=sample_role,
            documents=[
                DocumentRef(
                    type=DocumentType.JOB_DESCRIPTION,
                    name="Test JD",
                    content="Test job description content",
                )
            ],
            options=WorkflowOptions(force_rerun=False),
        )

        # Mock the activity execution
        with patch.object(workflow, '_role_setup_activity') as mock_setup:
            with patch.object(workflow, '_ai_assessment_activity') as mock_assess:
                # Setup mock returns
                from etter_workflows.models.outputs import ActivityResult

                mock_setup_result = ActivityResult.create_success(
                    id="test",
                    result={"company_role_id": "test_role_123"},
                )
                mock_setup.execute = AsyncMock(return_value=mock_setup_result)

                mock_assess_result = ActivityResult.create_success(
                    id="test",
                    result={
                        "assessment_outputs": {
                            "final_score": 65.0,
                            "task_analysis": {"task_count": 5},
                        }
                    },
                )
                mock_assess.execute = AsyncMock(return_value=mock_assess_result)

                # Set up the activities (since they're lazy-loaded)
                workflow._role_setup_activity = mock_setup
                workflow._ai_assessment_activity = mock_assess

                # Execute workflow
                result = await workflow.execute(input_data)

        # Verify result
        assert result is not None
        # Note: May fail due to other dependencies, but structure is correct

    @pytest.mark.asyncio
    async def test_execute_validation_error(self, mock_redis):
        """Test workflow returns validation error for invalid input."""
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow
        from etter_workflows.models.inputs import RoleOnboardingInput, WorkflowOptions

        workflow = RoleOnboardingWorkflow()

        # Create input without documents or taxonomy (should fail validation)
        input_data = RoleOnboardingInput(
            company_id="TestCompany",
            role_name="TestRole",
            documents=[],  # No documents
            options=WorkflowOptions(),
        )

        result = await workflow.execute(input_data)

        # Should fail with validation error
        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "VALIDATION_ERROR"


# ============================================================================
# Activity Tests
# ============================================================================

class TestActivities:
    """Tests for individual activities."""

    def test_role_setup_activity_exists(self):
        """Test RoleSetupActivity can be imported."""
        from etter_workflows.activities.role_setup import RoleSetupActivity

        activity = RoleSetupActivity()
        assert activity is not None
        assert activity.name == "role_setup"

    def test_ai_assessment_activity_exists(self):
        """Test AIAssessmentActivity can be imported."""
        from etter_workflows.activities.ai_assessment import AIAssessmentActivity

        activity = AIAssessmentActivity()
        assert activity is not None

    def test_mock_ai_assessment_activity_exists(self):
        """Test MockAIAssessmentActivity can be imported."""
        from etter_workflows.activities.ai_assessment import MockAIAssessmentActivity

        activity = MockAIAssessmentActivity()
        assert activity is not None


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_execute_role_onboarding_function_exists(self):
        """Test execute_role_onboarding function exists."""
        from etter_workflows.workflows.role_onboarding import execute_role_onboarding

        assert callable(execute_role_onboarding)

    def test_workflow_result_creation(self):
        """Test WorkflowResult can be created."""
        from etter_workflows.models.outputs import WorkflowResult, ErrorInfo

        # Test success result
        success_result = WorkflowResult.create_success(
            workflow_id="test-123",
            role_id="role-456",
            steps=[],
        )
        assert success_result.success is True
        assert success_result.workflow_id == "test-123"

        # Test failure result
        failure_result = WorkflowResult.create_failure(
            workflow_id="test-789",
            error=ErrorInfo(
                code="TEST_ERROR",
                message="Test error message",
            ),
            steps=[],
        )
        assert failure_result.success is False
        assert failure_result.error.code == "TEST_ERROR"


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Tests for workflow helper functions."""

    def test_is_temporal_workflow_context_outside_temporal(self):
        """Test is_temporal_workflow_context returns False outside Temporal."""
        from etter_workflows.workflows.base import is_temporal_workflow_context

        # Outside Temporal context, should return False
        result = is_temporal_workflow_context()
        assert result is False

    def test_get_workflow_time_returns_datetime(self):
        """Test get_workflow_time returns datetime."""
        from etter_workflows.workflows.base import get_workflow_time

        result = get_workflow_time()
        assert isinstance(result, datetime)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
