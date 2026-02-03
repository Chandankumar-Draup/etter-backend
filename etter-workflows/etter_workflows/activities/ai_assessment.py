"""
AI Assessment Activity for Etter Workflows.

Activity for running AI Assessment workflow:
- run_ai_assessment: Execute the automated AI assessment

Uses the Automated Workflows API (localhost:8083) for all operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from etter_workflows.activities.base import (
    BaseActivity,
    ActivityContext,
    activity_with_retry,
)
from etter_workflows.models.inputs import ExecutionContext
from etter_workflows.models.outputs import (
    ActivityResult,
    AssessmentOutputs,
    ErrorInfo,
    ResultStatus,
)
from etter_workflows.config.retry_policies import get_llm_retry_policy
from etter_workflows.clients.automated_workflows_client import get_automated_workflows_client

logger = logging.getLogger(__name__)


class AIAssessmentActivity(BaseActivity):
    """
    Activity for running AI Assessment.

    This activity:
    1. Triggers the AI Assessment workflow via the Automated Workflows API
    2. Extracts and stores assessment results
    3. Returns assessment scores and outputs
    """

    def __init__(self):
        super().__init__(name="ai_assessment")
        self.api_client = get_automated_workflows_client()

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActivityResult:
        """
        Execute AI Assessment activity.

        Args:
            inputs: {
                "company_role_id": str,
                "company_name": str,
                "role_name": str,
                "delete_existing": bool (optional),
                "store_in_neo4j": bool (optional, default True),
            }
            context: Execution context

        Returns:
            ActivityResult with assessment outputs
        """
        self._start_execution()

        try:
            company_role_id = inputs["company_role_id"]
            company_name = inputs["company_name"]
            role_name = inputs["role_name"]
            delete_existing = inputs.get("delete_existing", False)
            # Ensure store_in_neo4j defaults to True even if explicitly passed as None
            store_in_neo4j = inputs.get("store_in_neo4j")
            if store_in_neo4j is None:
                store_in_neo4j = True

            logger.info(
                f"Running AI Assessment for {role_name} at {company_name} via API",
                extra={
                    "company_role_id": company_role_id,
                    "trace_id": context.trace_id,
                },
            )

            # Execute assessment via Automated Workflows API
            assessment_result = self.api_client.run_ai_assessment(
                company_name=company_name,
                role_name=role_name,
                company_role_id=company_role_id,
                delete_existing=delete_existing,
                store_in_neo4j=store_in_neo4j,
            )

            if assessment_result.get("status") == "error":
                error_msg = assessment_result.get("message", "Unknown error")
                logger.error(f"AI Assessment failed: {error_msg}")
                return self._create_failure_result(
                    id=context.trace_id,
                    error=Exception(error_msg),
                    error_code="AI_ASSESSMENT_FAILED",
                    recoverable=True,
                )

            # Extract assessment data from API response
            assessment_data = assessment_result.get("assessment_data", {})
            final_output = assessment_data.get("final_output", {})
            step_results = assessment_data.get("step_results", {})

            # Extract scores from impact quantification step
            impact_data = {}
            if "ai_impact_quantification" in step_results:
                impact_step = step_results["ai_impact_quantification"]
                impact_data = impact_step.get("current_step", {}).get("data", {})

            ai_automation_score = assessment_result.get(
                "ai_automation_score",
                impact_data.get("ai_automation_score", 0.0)
            )
            validated_score = impact_data.get("validated_automation_score")

            # Extract task analysis from ai_impact_assessment step
            task_analysis = {}
            if "ai_impact_assessment" in step_results:
                task_step = step_results["ai_impact_assessment"]
                task_data = task_step.get("current_step", {}).get("data", {})
                task_analysis = {
                    "task_analysis_table": task_data.get("task_analysis_table", {}),
                    "task_count": len(
                        task_data.get("task_analysis_table", {}).get("body", [])
                    ),
                }

            # Create assessment outputs
            assessment_outputs = AssessmentOutputs(
                ai_automation_score=ai_automation_score,
                validated_automation_score=validated_score,
                task_analysis=task_analysis,
                impact_analysis=impact_data.get("ai_impact_analysis"),
                key_metrics=final_output.get("key_metrics"),
            )

            result = {
                "company_role_id": company_role_id,
                "company_name": company_name,
                "role_name": role_name,
                "request_id": assessment_result.get("request_id"),
                "execution_time": assessment_result.get("execution_time", 0),
                "steps_executed": assessment_result.get("steps_executed", []),
                "ai_automation_score": assessment_outputs.final_score,
                "task_count": task_analysis.get("task_count", 0),
                "assessment_outputs": assessment_outputs.model_dump(),
                "neo4j_storage": assessment_result.get("neo4j_storage"),
            }

            logger.info(
                f"AI Assessment completed for {role_name} via API",
                extra={
                    "company_role_id": company_role_id,
                    "ai_automation_score": assessment_outputs.final_score,
                    "trace_id": context.trace_id,
                },
            )

            return self._create_success_result(
                id=context.trace_id,
                result=result,
            )

        except Exception as e:
            logger.error(f"AI Assessment failed: {e}")
            return self._create_failure_result(
                id=context.trace_id,
                error=e,
                error_code="AI_ASSESSMENT_ERROR",
                recoverable=True,
            )


@activity_with_retry(retry_config=get_llm_retry_policy(), timeout_seconds=1800)
async def run_ai_assessment(
    company_name: str,
    role_name: str,
    company_role_id: Optional[str] = None,
    delete_existing: bool = False,
    store_in_neo4j: bool = True,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Run AI Assessment workflow via Automated Workflows API.

    This is a standalone activity function that can be registered
    with the Temporal worker.

    Args:
        company_name: Company name
        role_name: Role name
        company_role_id: Optional CompanyRole ID
        delete_existing: Whether to delete existing assessment
        store_in_neo4j: Store results in Neo4j database
        context: Execution context

    Returns:
        Dict with assessment results
    """
    # Ensure store_in_neo4j defaults to True even if explicitly passed as None
    if store_in_neo4j is None:
        store_in_neo4j = True

    with ActivityContext("run_ai_assessment", context or ExecutionContext(
        company_id=company_name, user_id="system"
    )) as ctx:
        api_client = get_automated_workflows_client()

        # Execute assessment via API
        assessment_result = api_client.run_ai_assessment(
            company_name=company_name,
            role_name=role_name,
            company_role_id=company_role_id,
            delete_existing=delete_existing,
            store_in_neo4j=store_in_neo4j,
        )

        if assessment_result.get("status") == "error":
            error_msg = assessment_result.get("message", "Unknown error")
            raise Exception(f"AI Assessment failed: {error_msg}")

        # Extract key metrics from API response
        assessment_data = assessment_result.get("assessment_data", {})
        final_output = assessment_data.get("final_output", {})
        step_results = assessment_data.get("step_results", {})

        # Extract scores
        ai_automation_score = assessment_result.get("ai_automation_score", 0.0)

        return {
            "company_role_id": company_role_id,
            "company_name": company_name,
            "role_name": role_name,
            "success": True,
            "request_id": assessment_result.get("request_id"),
            "execution_time": assessment_result.get("execution_time", 0),
            "steps_executed": assessment_result.get("steps_executed", []),
            "ai_automation_score": ai_automation_score,
            "assessment_data": {
                "final_output": final_output,
                "step_results": step_results,
            },
            "neo4j_storage": assessment_result.get("neo4j_storage"),
            "duration_ms": ctx.metrics.duration_ms,
        }


class MockAIAssessmentActivity(BaseActivity):
    """
    Mock AI Assessment activity for testing.

    Returns simulated assessment results without calling the real API.
    """

    def __init__(self):
        super().__init__(name="mock_ai_assessment")

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActivityResult:
        """Execute mock AI Assessment."""
        self._start_execution()

        try:
            company_role_id = inputs["company_role_id"]
            company_name = inputs["company_name"]
            role_name = inputs["role_name"]

            # Simulate some processing time
            import asyncio
            await asyncio.sleep(1)

            # Generate mock assessment outputs
            import random
            ai_score = round(random.uniform(30, 80), 2)

            assessment_outputs = AssessmentOutputs(
                ai_automation_score=ai_score,
                validated_automation_score=ai_score,
                task_analysis={
                    "task_analysis_table": {
                        "headers": ["Task", "AI Impact", "Automation Potential"],
                        "body": [
                            {"Task": "Data Entry", "AI Impact": "High", "Automation Potential": "90%"},
                            {"Task": "Report Generation", "AI Impact": "Medium", "Automation Potential": "70%"},
                            {"Task": "Decision Making", "AI Impact": "Low", "Automation Potential": "30%"},
                        ],
                    },
                    "task_count": 3,
                },
                impact_analysis="Mock AI impact analysis for testing purposes.",
                key_metrics={
                    "total_tasks": 3,
                    "automatable_tasks": 2,
                    "augmentable_tasks": 1,
                },
            )

            result = {
                "company_role_id": company_role_id,
                "company_name": company_name,
                "role_name": role_name,
                "request_id": f"mock-{context.trace_id}",
                "execution_time": 1.0,
                "steps_executed": ["mock_assessment"],
                "ai_automation_score": ai_score,
                "task_count": 3,
                "assessment_outputs": assessment_outputs.model_dump(),
                "is_mock": True,
            }

            return self._create_success_result(
                id=context.trace_id,
                result=result,
            )

        except Exception as e:
            return self._create_failure_result(
                id=context.trace_id,
                error=e,
                error_code="MOCK_ASSESSMENT_ERROR",
            )
