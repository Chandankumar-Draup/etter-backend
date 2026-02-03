"""
Role Setup Activity for Etter Workflows.

Activities for role creation and document linking:
- create_company_role: Create CompanyRole node in Neo4j
- link_job_description: Link JD to CompanyRole

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
from etter_workflows.models.inputs import (
    RoleOnboardingInput,
    DocumentRef,
    DocumentType,
    ExecutionContext,
)
from etter_workflows.models.outputs import (
    ActivityResult,
    ErrorInfo,
    ExecutionMetrics,
    ResultStatus,
)
from etter_workflows.config.retry_policies import get_db_retry_policy
from etter_workflows.clients.automated_workflows_client import get_automated_workflows_client
from etter_workflows.mock_data.documents import get_document_provider
from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider

logger = logging.getLogger(__name__)


class RoleSetupActivity(BaseActivity):
    """
    Activity for setting up a company role.

    This activity:
    1. Creates/finds CompanyRole node via Automated Workflows API
    2. Links job description document via API
    3. Returns the company_role_id for subsequent activities
    """

    def __init__(self):
        super().__init__(name="role_setup")
        self.api_client = get_automated_workflows_client()
        self.doc_provider = get_document_provider()
        self.taxonomy_provider = get_role_taxonomy_provider()

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActivityResult:
        """
        Execute role setup activity.

        Args:
            inputs: {
                "company_id": str,
                "role_name": str,
                "documents": List[DocumentRef],
                "draup_role_name": Optional[str],
                "taxonomy_entry": Optional[RoleTaxonomyEntry],
            }
            context: Execution context

        Returns:
            ActivityResult with company_role_id
        """
        self._start_execution()

        try:
            company_id = inputs["company_id"]
            role_name = inputs["role_name"]
            documents = inputs.get("documents", [])
            draup_role_name = inputs.get("draup_role_name")
            taxonomy_entry = inputs.get("taxonomy_entry")

            # Get draup role from taxonomy if available
            if not draup_role_name and taxonomy_entry:
                draup_role_name = taxonomy_entry.get("draup_role") or taxonomy_entry.get("job_role")

            # Step 1: Create/find CompanyRole via API
            logger.info(f"Creating CompanyRole for {role_name} at {company_id} via API")
            create_result = self.api_client.create_company_role(
                company_name=company_id,
                role_name=role_name,
                draup_role=draup_role_name,
                metadata={
                    "created_by": context.user_id,
                    "trace_id": context.trace_id,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            company_role_id = create_result.get("company_role_id")

            # Step 2: Get and link job description
            jd_content = None
            jd_linked = False

            # Try to get JD from documents
            for doc_data in documents:
                if isinstance(doc_data, dict):
                    doc = DocumentRef(**doc_data)
                else:
                    doc = doc_data

                if doc.type == DocumentType.JOB_DESCRIPTION:
                    jd_content = doc.content
                    break

            # Try to get JD from taxonomy entry
            if not jd_content and taxonomy_entry:
                general_summary = taxonomy_entry.get("general_summary", "")
                duties = taxonomy_entry.get("duties_responsibilities", "")
                if general_summary or duties:
                    jd_content = f"{general_summary}\n\n{duties}".strip()

            # Try to get JD from mock data provider
            if not jd_content:
                doc_ref = self.doc_provider.get_document(
                    company_name=company_id,
                    role_name=role_name,
                    doc_type=DocumentType.JOB_DESCRIPTION,
                )
                if doc_ref:
                    jd_content = self.doc_provider.get_document_content(doc_ref)

            # Link JD if we have content via API
            if jd_content:
                link_result = self.api_client.link_job_description(
                    company_role_id=company_role_id,
                    jd_content=jd_content,
                    jd_title=role_name,
                    format_with_llm=True,
                    source="self_service_pipeline",
                )
                jd_linked = link_result.get("jd_linked", False)
                logger.info(f"Linked JD to CompanyRole via API: {company_role_id}")

            result = {
                "company_role_id": company_role_id,
                "company_name": company_id,
                "role_name": role_name,
                "draup_role": draup_role_name,
                "jd_linked": jd_linked,
                "jd_content_length": len(jd_content) if jd_content else 0,
            }

            return self._create_success_result(
                id=context.trace_id,
                result=result,
            )

        except Exception as e:
            logger.error(f"Role setup failed: {e}")
            return self._create_failure_result(
                id=context.trace_id,
                error=e,
                error_code="ROLE_SETUP_ERROR",
                recoverable=True,
            )


@activity_with_retry(retry_config=get_db_retry_policy(), timeout_seconds=300)
async def create_company_role(
    company_name: str,
    role_name: str,
    draup_role: Optional[str] = None,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Create or find a CompanyRole node via Automated Workflows API.

    This is a standalone activity function that can be registered
    with the Temporal worker.

    Args:
        company_name: Company name
        role_name: Role name
        draup_role: Draup standardized role name
        context: Execution context

    Returns:
        Dict with company_role_id and metadata
    """
    with ActivityContext("create_company_role", context or ExecutionContext(
        company_id=company_name, user_id="system"
    )) as ctx:
        api_client = get_automated_workflows_client()

        result = api_client.create_company_role(
            company_name=company_name,
            role_name=role_name,
            draup_role=draup_role,
            metadata={
                "created_by": ctx.context.user_id,
                "trace_id": ctx.context.trace_id,
            },
        )

        return {
            "company_role_id": result.get("company_role_id"),
            "company_name": result.get("company_name", company_name),
            "role_name": result.get("role_name", role_name),
            "draup_role": result.get("draup_role", draup_role),
            "created": result.get("created", False),
            "duration_ms": ctx.metrics.duration_ms,
        }


@activity_with_retry(retry_config=get_db_retry_policy(), timeout_seconds=300)
async def link_job_description(
    company_role_id: str,
    jd_content: str,
    jd_title: Optional[str] = None,
    format_with_llm: bool = True,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Link a job description to a CompanyRole via Automated Workflows API.

    This is a standalone activity function that can be registered
    with the Temporal worker.

    Args:
        company_role_id: CompanyRole ID
        jd_content: Job description content
        jd_title: Optional title
        format_with_llm: Whether to format JD with LLM
        context: Execution context

    Returns:
        Dict with linking status
    """
    with ActivityContext("link_job_description", context or ExecutionContext(
        company_id="unknown", user_id="system"
    )) as ctx:
        api_client = get_automated_workflows_client()

        result = api_client.link_job_description(
            company_role_id=company_role_id,
            jd_content=jd_content,
            jd_title=jd_title,
            format_with_llm=format_with_llm,
            source="self_service_pipeline",
        )

        return {
            "company_role_id": company_role_id,
            "jd_linked": result.get("jd_linked", False),
            "jd_content_length": result.get("jd_content_length", len(jd_content)),
            "formatted": result.get("formatted", format_with_llm),
            "duration_ms": ctx.metrics.duration_ms,
        }
