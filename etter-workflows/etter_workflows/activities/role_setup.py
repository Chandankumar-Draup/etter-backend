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
        # Debug logging for environment and configuration
        from etter_workflows.config.settings import get_settings
        settings = get_settings()

        logger.info("=" * 60)
        logger.info("CREATE_COMPANY_ROLE Activity Starting")
        logger.info("=" * 60)
        logger.info(f"Input Parameters:")
        logger.info(f"  - company_name: {company_name}")
        logger.info(f"  - role_name: {role_name}")
        logger.info(f"  - draup_role: {draup_role}")
        logger.info(f"  - trace_id: {ctx.context.trace_id}")
        logger.info(f"Environment Configuration:")
        logger.info(f"  - etter_db_host: '{settings.etter_db_host}'")
        logger.info(f"  - environment: '{settings.environment}'")
        logger.info(f"  - is_qa_or_prod: {settings._is_qa_or_prod_environment()}")
        logger.info(f"  - is_prod_db: {settings._is_prod_db()}")
        logger.info(f"  - draup_world_api_url: '{settings.draup_world_api_url}'")
        logger.info(f"  - effective_api_url: '{settings.get_automated_workflows_api_url()}'")
        logger.info("=" * 60)

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

        logger.info(f"API Response received:")
        logger.info(f"  - company_role_id: {result.get('company_role_id')}")
        logger.info(f"  - created: {result.get('created', False)}")
        logger.info("=" * 60)

        return {
            "company_role_id": result.get("company_role_id"),
            "company_name": result.get("company_name", company_name),
            "role_name": result.get("role_name", role_name),
            "draup_role": result.get("draup_role", draup_role),
            "created": result.get("created", False),
            "duration_ms": ctx.metrics.duration_ms,
        }


@activity_with_retry(retry_config=get_db_retry_policy(), timeout_seconds=120)
async def download_document_from_url(
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Download document content from a URL (e.g., S3 presigned URL).

    Handles PDF files by extracting text content.

    Args:
        url: Document URL (presigned S3 URL)
        metadata: Optional document metadata

    Returns:
        Dict with content and metadata
    """
    import requests
    import io

    logger.info(f"Downloading document from URL")
    logger.info(f"  - URL preview: {url[:80]}...")
    if metadata:
        logger.info(f"  - Document ID: {metadata.get('document_id', 'N/A')}")
        logger.info(f"  - Content Type: {metadata.get('content_type', 'N/A')}")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        is_pdf = "pdf" in content_type.lower() or url.lower().endswith(".pdf")

        logger.info(f"  - Response Content-Type: {content_type}")
        logger.info(f"  - Is PDF: {is_pdf}")
        logger.info(f"  - Content Length: {len(response.content)} bytes")

        if is_pdf:
            # Extract text from PDF
            try:
                import PyPDF2
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                text_parts = []
                for i, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                        logger.debug(f"  - Page {i+1}: {len(text)} chars")

                if text_parts:
                    content = "\n\n".join(text_parts)
                    logger.info(f"  - Extracted {len(content)} chars from {len(pdf_reader.pages)} pages")
                    return {
                        "content": content,
                        "content_length": len(content),
                        "pages": len(pdf_reader.pages),
                        "content_type": "application/pdf",
                        "extracted": True,
                    }
                else:
                    logger.warning("  - No text extracted from PDF (may be image-based)")
                    return {
                        "content": None,
                        "content_length": 0,
                        "error": "No text extracted from PDF",
                    }
            except ImportError:
                logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
                return {
                    "content": None,
                    "error": "PyPDF2 not installed",
                }
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return {
                    "content": None,
                    "error": str(e),
                }
        else:
            # Return text content directly
            content = response.text
            logger.info(f"  - Text content: {len(content)} chars")
            return {
                "content": content,
                "content_length": len(content),
                "content_type": content_type,
                "extracted": False,
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        return {
            "content": None,
            "error": str(e),
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
