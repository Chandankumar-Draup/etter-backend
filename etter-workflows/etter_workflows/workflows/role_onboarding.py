"""
Role Onboarding Workflow for Etter Workflows.

This is the main workflow for the self-service pipeline.
It orchestrates:
1. Role Setup (create CompanyRole, link documents)
2. AI Assessment (run automated assessment)

Based on the implementation plan Phase 1 (MVP):
- Role Defined → Document Linked → AI Assessment → Dashboard Visible

Future phases will add:
- Skills Architecture
- Task Feasibility
- Skills Catalog
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Import Temporal decorators
try:
    from temporalio import workflow
    from temporalio.common import RetryPolicy
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    workflow = None
    RetryPolicy = None

from etter_workflows.workflows.base import BaseWorkflow, WorkflowStep, get_workflow_time, is_temporal_workflow_context
from etter_workflows.models.inputs import (
    RoleOnboardingInput,
    ExecutionContext,
    DocumentRef,
    DocumentType,
)
from etter_workflows.models.outputs import (
    WorkflowResult,
    StepResult,
    AssessmentOutputs,
    ErrorInfo,
    ResultStatus,
    ActivityResult,
)
from etter_workflows.models.status import (
    RoleStatus,
    WorkflowState,
    ProcessingSubState,
    StepStatus,
)
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


def _apply_temporal_decorators(cls):
    """
    Apply Temporal workflow decorators if available.

    This applies both @workflow.defn to the class and @workflow.run to
    the execute method.
    """
    if TEMPORAL_AVAILABLE and workflow:
        # Apply @workflow.run to the execute method
        if hasattr(cls, 'execute'):
            original_execute = cls.execute
            cls.execute = workflow.run(original_execute)
        # Apply @workflow.defn to the class
        return workflow.defn(cls)
    return cls


@_apply_temporal_decorators
class RoleOnboardingWorkflow(BaseWorkflow):
    """
    Main workflow for role onboarding in the self-service pipeline.

    This workflow executes the critical path:
    1. Role Setup: Create CompanyRole node and link documents
    2. AI Assessment: Run automated AI impact assessment

    The workflow follows the state machine:
    DRAFT → QUEUED → PROCESSING → READY (or FAILED)
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        use_mock_assessment: bool = False,
    ):
        """
        Initialize the workflow.

        Args:
            workflow_id: Unique workflow identifier
            use_mock_assessment: Use mock AI assessment (for testing)
        """
        super().__init__(workflow_id)
        self.use_mock_assessment = use_mock_assessment
        # Activity instances for standalone mode (lazy-loaded)
        # In Temporal mode, activities are called via workflow.execute_activity()
        self._role_setup_activity = None
        self._ai_assessment_activity = None
        self.steps = self.define_steps()

    def define_steps(self) -> List[WorkflowStep]:
        """
        Define the workflow steps.

        MVP Steps (Phase 1):
        1. role_setup: Create CompanyRole and link JD
        2. ai_assessment: Run AI Assessment

        Returns:
            List of WorkflowStep definitions
        """
        return [
            WorkflowStep(
                name="role_setup",
                sub_state=ProcessingSubState.ROLE_SETUP,
                execute=self._execute_role_setup,
                required=True,
                timeout_seconds=300,  # 5 minutes
            ),
            WorkflowStep(
                name="ai_assessment",
                sub_state=ProcessingSubState.AI_ASSESSMENT,
                execute=self._execute_ai_assessment,
                required=True,
                timeout_seconds=1800,  # 30 minutes
            ),
        ]

    async def execute(self, input: RoleOnboardingInput) -> WorkflowResult:
        """
        Execute the role onboarding workflow.

        Args:
            input: RoleOnboardingInput with company_id, role_name, documents

        Returns:
            WorkflowResult with status and outputs
        """
        self._start_time = get_workflow_time()

        # Only log outside Temporal context to avoid I/O in workflow code
        if not is_temporal_workflow_context():
            logger.info(
                f"Starting role onboarding workflow",
                extra={
                    "workflow_id": self.workflow_id,
                    "company_id": input.company_id,
                    "role_name": input.role_name,
                },
            )

        # Validate input
        validation_errors = input.validate_for_processing()
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            if not is_temporal_workflow_context():
                logger.error(f"Input validation failed: {error_msg}")

            # Create validation error status (skip Redis in Temporal context)
            status = self._create_initial_status(input)
            status.state = WorkflowState.VALIDATION_ERROR
            status.error = {"code": "VALIDATION_ERROR", "message": error_msg}
            if not is_temporal_workflow_context() and self.status_client:
                self.status_client.set_status(status)

            return self._create_failure_result(
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=error_msg,
                    recoverable=False,
                ),
            )

        # Create execution context if not provided
        context = input.context or ExecutionContext(
            company_id=input.company_id,
            user_id="self_service",
        )

        # Initialize status
        status = self._create_initial_status(input)
        self._update_status(status, state=WorkflowState.PROCESSING)

        # Workflow state to pass between steps
        workflow_state: Dict[str, Any] = {
            "company_role_id": None,
            "assessment_outputs": None,
        }

        # Execute steps
        for step in self.steps:
            step_result = await self._execute_step(
                step=step,
                inputs={
                    "input": input,
                    "context": context,
                    "workflow_state": workflow_state,
                },
                context=context,
                status=status,
            )

            self.completed_steps.append(step_result)

            # Check if step failed and is required
            if step_result.status == ResultStatus.FAILED and step.required:
                if not is_temporal_workflow_context():
                    logger.error(f"Required step failed: {step.name}")

                self._update_status(
                    status,
                    state=WorkflowState.FAILED,
                )

                return self._create_failure_result(
                    error=step_result.error or ErrorInfo(
                        code="STEP_FAILED",
                        message=f"Step {step.name} failed",
                        recoverable=True,
                    ),
                    role_id=workflow_state.get("company_role_id"),
                )

            # Update workflow state from step result
            if step_result.data:
                if "company_role_id" in step_result.data:
                    workflow_state["company_role_id"] = step_result.data["company_role_id"]
                if "assessment_outputs" in step_result.data:
                    workflow_state["assessment_outputs"] = step_result.data["assessment_outputs"]

        # Workflow completed successfully
        if not is_temporal_workflow_context():
            logger.info(
                f"Role onboarding workflow completed successfully",
                extra={
                    "workflow_id": self.workflow_id,
                    "company_role_id": workflow_state.get("company_role_id"),
                },
            )

        # Generate dashboard URL
        dashboard_url = self._generate_dashboard_url(
            company_id=input.company_id,
            role_id=workflow_state.get("company_role_id"),
        )

        # Update final status
        self._update_status(
            status,
            state=WorkflowState.READY,
            role_id=workflow_state.get("company_role_id"),
            dashboard_url=dashboard_url,
        )

        # Create assessment outputs
        assessment_outputs = None
        if workflow_state.get("assessment_outputs"):
            outputs_data = workflow_state["assessment_outputs"]
            assessment_outputs = AssessmentOutputs(**outputs_data)

        return self._create_success_result(
            role_id=workflow_state.get("company_role_id", ""),
            outputs=assessment_outputs,
            dashboard_url=dashboard_url,
        )

    async def _execute_role_setup(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """
        Execute the role setup step.

        Args:
            inputs: Step inputs including RoleOnboardingInput
            context: Execution context

        Returns:
            ActivityResult from role setup
        """
        input: RoleOnboardingInput = inputs["input"]
        workflow_state: Dict[str, Any] = inputs["workflow_state"]

        # Prepare activity inputs
        activity_inputs = {
            "company_id": input.company_id,
            "role_name": input.role_name,
            "documents": [doc.model_dump() for doc in input.documents],
            "draup_role_name": input.draup_role_name,
            "taxonomy_entry": (
                input.taxonomy_entry.model_dump()
                if input.taxonomy_entry else None
            ),
            "context": context.model_dump() if hasattr(context, 'model_dump') else {
                "company_id": context.company_id,
                "user_id": context.user_id,
                "trace_id": context.trace_id,
            },
        }

        # Execute activity - use Temporal's execute_activity in workflow context
        if is_temporal_workflow_context() and workflow:
            # In Temporal context: use workflow.execute_activity()
            # Import activity function reference for Temporal
            from etter_workflows.activities.role_setup import create_company_role, link_job_description

            # Step 1: Create company role
            result_dict = await workflow.execute_activity(
                create_company_role,
                args=[
                    input.company_id,  # company_name
                    input.role_name,   # role_name
                    input.draup_role_name,  # draup_role
                    None,  # context (will be created inside activity)
                ],
                start_to_close_timeout=timedelta(seconds=300),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0,
                ),
            )

            company_role_id = result_dict.get("company_role_id")

            # Step 2: Link job description if we have one
            jd_content = None
            for doc in input.documents:
                if doc.type == DocumentType.JOB_DESCRIPTION:
                    jd_content = doc.content
                    break

            # Try taxonomy entry if no JD in documents
            if not jd_content and input.taxonomy_entry:
                taxonomy_dict = input.taxonomy_entry.model_dump() if hasattr(input.taxonomy_entry, 'model_dump') else input.taxonomy_entry
                general_summary = taxonomy_dict.get("general_summary", "")
                duties = taxonomy_dict.get("duties_responsibilities", "")
                if general_summary or duties:
                    jd_content = f"{general_summary}\n\n{duties}".strip()

            if jd_content and company_role_id:
                jd_result = await workflow.execute_activity(
                    link_job_description,
                    args=[
                        company_role_id,  # company_role_id
                        jd_content,       # jd_content
                        input.role_name,  # jd_title
                        True,             # format_with_llm
                        None,             # context
                    ],
                    start_to_close_timeout=timedelta(seconds=300),
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=30),
                        backoff_coefficient=2.0,
                    ),
                )
                result_dict["jd_linked"] = jd_result.get("jd_linked", False)
            else:
                result_dict["jd_linked"] = False

            # Activity returns dict directly with company_role_id
            # Convert to ActivityResult format for consistent handling
            result = ActivityResult.create_success(
                id=self.workflow_id,
                result=result_dict,
            )
        else:
            # Standalone mode: use direct activity class execution
            from etter_workflows.activities.role_setup import RoleSetupActivity
            if self._role_setup_activity is None:
                self._role_setup_activity = RoleSetupActivity()
            result = await self._role_setup_activity.execute(activity_inputs, context)

        # Store company_role_id in workflow state
        if result.success and result.result:
            workflow_state["company_role_id"] = result.result.get("company_role_id")

        return result

    async def _execute_ai_assessment(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """
        Execute the AI assessment step.

        Args:
            inputs: Step inputs including workflow state
            context: Execution context

        Returns:
            ActivityResult from AI assessment
        """
        input: RoleOnboardingInput = inputs["input"]
        workflow_state: Dict[str, Any] = inputs["workflow_state"]

        company_role_id = workflow_state.get("company_role_id")
        if not company_role_id:
            raise ValueError("company_role_id not available from role_setup step")

        # Prepare activity inputs
        activity_inputs = {
            "company_role_id": company_role_id,
            "company_name": input.company_id,
            "role_name": input.role_name,
            "delete_existing": input.options.force_rerun,
            "context": context.model_dump() if hasattr(context, 'model_dump') else {
                "company_id": context.company_id,
                "user_id": context.user_id,
                "trace_id": context.trace_id,
            },
        }

        # Execute activity - use Temporal's execute_activity in workflow context
        if is_temporal_workflow_context() and workflow:
            # In Temporal context: use workflow.execute_activity()
            from etter_workflows.activities.ai_assessment import run_ai_assessment

            # Activity function takes individual params
            result_dict = await workflow.execute_activity(
                run_ai_assessment,
                args=[
                    input.company_id,  # company_name
                    input.role_name,   # role_name
                    company_role_id,   # company_role_id
                    input.options.force_rerun,  # delete_existing
                    None,  # context (will be created inside activity)
                ],
                start_to_close_timeout=timedelta(seconds=1800),  # 30 minutes for AI assessment
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=60),
                    backoff_coefficient=2.0,
                ),
            )
            # Activity returns dict directly with assessment results
            # Convert to ActivityResult format for consistent handling
            result = ActivityResult.create_success(
                id=self.workflow_id,
                result={"assessment_outputs": result_dict},
            )
        else:
            # Standalone mode: use direct activity class execution
            from etter_workflows.activities.ai_assessment import (
                AIAssessmentActivity,
                MockAIAssessmentActivity,
            )
            if self._ai_assessment_activity is None:
                if self.use_mock_assessment:
                    self._ai_assessment_activity = MockAIAssessmentActivity()
                else:
                    self._ai_assessment_activity = AIAssessmentActivity()
            result = await self._ai_assessment_activity.execute(activity_inputs, context)

        # Store assessment outputs in workflow state
        if result.success and result.result:
            workflow_state["assessment_outputs"] = result.result.get("assessment_outputs")

        return result

    def _generate_dashboard_url(
        self,
        company_id: str,
        role_id: Optional[str],
    ) -> str:
        """
        Generate URL to view role in CHRO dashboard.

        Args:
            company_id: Company identifier
            role_id: CompanyRole identifier

        Returns:
            Dashboard URL
        """
        settings = get_settings()
        base_url = "https://etter.draup.com"

        if role_id:
            return f"{base_url}/dashboard/{company_id}/roles/{role_id}"
        return f"{base_url}/dashboard/{company_id}/roles"


async def execute_role_onboarding(
    company_id: str,
    role_name: str,
    documents: Optional[List[DocumentRef]] = None,
    draup_role_name: Optional[str] = None,
    force_rerun: bool = False,
    use_mock_assessment: bool = False,
    context: Optional[ExecutionContext] = None,
) -> WorkflowResult:
    """
    Execute role onboarding workflow (convenience function).

    This is a standalone function that creates and executes
    the RoleOnboardingWorkflow.

    Args:
        company_id: Company identifier
        role_name: Role name
        documents: List of documents to link
        draup_role_name: Draup role mapping
        force_rerun: Force re-run of assessment
        use_mock_assessment: Use mock assessment (testing)
        context: Execution context

    Returns:
        WorkflowResult with status and outputs
    """
    # Create input
    from etter_workflows.models.inputs import WorkflowOptions

    input = RoleOnboardingInput(
        company_id=company_id,
        role_name=role_name,
        documents=documents or [],
        draup_role_name=draup_role_name,
        options=WorkflowOptions(force_rerun=force_rerun),
        context=context,
    )

    # Check if we need to load documents from mock data
    if not input.has_documents():
        from etter_workflows.mock_data.documents import get_document_provider
        from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider

        doc_provider = get_document_provider()
        taxonomy_provider = get_role_taxonomy_provider()

        # Try to get JD from mock data
        jd_doc = doc_provider.get_document(
            company_name=company_id,
            role_name=role_name,
            doc_type=DocumentType.JOB_DESCRIPTION,
        )
        if jd_doc:
            input.documents.append(jd_doc)

        # Try to get taxonomy entry
        taxonomy_entry = taxonomy_provider.get_role(company_id, role_name)
        if taxonomy_entry:
            input.taxonomy_entry = taxonomy_entry
            if not input.draup_role_name:
                input.draup_role_name = taxonomy_entry.get_draup_role()

    # Create and execute workflow
    workflow = RoleOnboardingWorkflow(use_mock_assessment=use_mock_assessment)
    return await workflow.execute(input)
