"""
API routes for Etter Workflows.

FastAPI routes for the self-service pipeline.
Based on the API design in the implementation plan.

Endpoints (via reverse proxy at /api):
- POST /api/v1/pipeline/push - Start role onboarding workflow
- GET /api/v1/pipeline/status/{workflow_id} - Get workflow status
- GET /api/v1/pipeline/health - Health check
- GET /api/v1/pipeline/companies - Get available companies
- GET /api/v1/pipeline/roles/{company_name} - Get roles for a company
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse

# Temporal client imports
try:
    from temporalio.client import Client as TemporalClient
    from temporalio.common import RetryPolicy
    TEMPORAL_AVAILABLE = True
except ImportError:
    TemporalClient = None
    RetryPolicy = None
    TEMPORAL_AVAILABLE = False

from etter_workflows.api.schemas import (
    PushRequest,
    PushResponse,
    StatusResponse,
    ErrorResponse,
    HealthResponse,
    ProgressInfo,
    StepProgress,
    CompanyRolesResponse,
    # Batch schemas
    BatchPushRequest,
    BatchPushResponse,
    BatchStatusResponse,
    BatchRoleStatusResponse,
    BatchRetryRequest,
    BatchRetryResponse,
)
from etter_workflows.models.inputs import (
    RoleOnboardingInput,
    DocumentRef,
    DocumentType,
    WorkflowOptions,
    ExecutionContext,
)
from etter_workflows.models.status import (
    RoleStatus,
    WorkflowState,
    StepStatus,
)
from etter_workflows.models.batch import BatchRecord
from etter_workflows.workflows.role_onboarding import (
    RoleOnboardingWorkflow,
    execute_role_onboarding,
)
from etter_workflows.clients.status_client import get_status_client
from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
# Note: get_document_provider removed - documents must be provided in request
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)

# Router prefix: /v1/pipeline (accessed via /api/v1/pipeline through reverse proxy)
router = APIRouter(prefix="/v1/pipeline", tags=["pipeline"])

# Global Temporal client singleton
_temporal_client: Optional[TemporalClient] = None
_temporal_client_lock = asyncio.Lock()


async def get_temporal_client() -> Optional[TemporalClient]:
    """
    Get or create the Temporal client singleton.

    Returns:
        Temporal client if available and connected, None otherwise.
    """
    global _temporal_client

    if not TEMPORAL_AVAILABLE:
        logger.warning("Temporal client not available (temporalio not installed)")
        return None

    async with _temporal_client_lock:
        if _temporal_client is not None:
            return _temporal_client

        try:
            settings = get_settings()
            logger.info(f"Connecting to Temporal at {settings.temporal_address}")

            _temporal_client = await TemporalClient.connect(
                settings.temporal_address,
                namespace=settings.get_temporal_namespace(),
            )

            logger.info(f"Connected to Temporal namespace: {settings.get_temporal_namespace()}")
            return _temporal_client

        except Exception as e:
            logger.error(f"Failed to connect to Temporal: {e}")
            return None


async def is_temporal_connected() -> tuple[bool, str]:
    """
    Check if Temporal is connected.

    Returns:
        Tuple of (is_connected, status_message)
    """
    if not TEMPORAL_AVAILABLE:
        return False, "temporalio package not installed"

    try:
        client = await get_temporal_client()
        if client is None:
            settings = get_settings()
            return False, f"failed to connect to {settings.temporal_address}"
        return True, "healthy"
    except Exception as e:
        return False, f"error: {str(e)}"


@router.post("/push", response_model=PushResponse)
async def push_role(
    request: PushRequest,
    background_tasks: BackgroundTasks,
    use_mock: bool = Query(default=False, description="Use mock assessment for testing"),
) -> PushResponse:
    """
    Start role onboarding workflow.

    This endpoint triggers the self-service pipeline for a role:
    1. Creates/updates CompanyRole node
    2. Links job description
    3. Runs AI Assessment

    Args:
        request: Push request with company_id, role_name, documents
        background_tasks: FastAPI background tasks
        use_mock: Use mock assessment for testing

    Returns:
        PushResponse with workflow_id and initial status
    """
    logger.info(
        f"Push request received",
        extra={
            "company_id": request.company_id,
            "role_name": request.role_name,
        },
    )

    try:
        # Convert documents
        documents = []
        for doc in request.documents:
            doc_type = DocumentType(doc.type) if doc.type in [t.value for t in DocumentType] else DocumentType.OTHER
            documents.append(DocumentRef(
                type=doc_type,
                uri=doc.uri,
                content=doc.content,
                name=doc.name,
            ))

        # Create workflow input
        input = RoleOnboardingInput(
            company_id=request.company_id,
            role_name=request.role_name,
            documents=documents,
            draup_role_name=request.draup_role_name or request.draup_role_id,
            options=WorkflowOptions(
                skip_enhancement_workflows=request.options.skip_enhancement_workflows,
                force_rerun=request.options.force_rerun,
                notify_on_complete=request.options.notify_on_complete,
            ),
        )

        # Validate that documents are provided in the request
        if not input.has_documents():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": "At least one document (job_description) is required in the request",
                    "recoverable": False,
                },
            )

        # Optionally load taxonomy data for role mapping (does not replace documents)
        settings = get_settings()
        if not input.draup_role_name:
            try:
                taxonomy_provider = get_role_taxonomy_provider()
                taxonomy_entry = taxonomy_provider.get_role(
                    request.company_id,
                    request.role_name,
                )
                if taxonomy_entry:
                    input.taxonomy_entry = taxonomy_entry
                    input.draup_role_name = taxonomy_entry.get_draup_role()
            except Exception as e:
                logger.warning(f"Failed to fetch taxonomy data: {e}")

        # Validate input
        validation_errors = input.validate_for_processing()
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": "; ".join(validation_errors),
                    "recoverable": False,
                },
            )

        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        settings = get_settings()

        # Try to submit to Temporal
        temporal_client = await get_temporal_client()

        if temporal_client:
            # Submit workflow to Temporal
            logger.info(f"Submitting workflow {workflow_id} to Temporal")

            try:
                await temporal_client.start_workflow(
                    RoleOnboardingWorkflow,
                    input,
                    id=workflow_id,
                    task_queue=settings.temporal_task_queue,
                    execution_timeout=timedelta(minutes=input.options.timeout_minutes),
                )

                logger.info(f"Workflow {workflow_id} submitted to Temporal successfully")

                return PushResponse(
                    workflow_id=workflow_id,
                    status="queued",
                    estimated_duration_seconds=600,
                    message=f"Workflow submitted to Temporal for {request.role_name} at {request.company_id}",
                )

            except Exception as e:
                logger.error(f"Failed to submit workflow to Temporal: {e}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "TEMPORAL_ERROR",
                        "message": f"Failed to submit workflow to Temporal: {str(e)}",
                        "recoverable": True,
                    },
                )
        else:
            # Fallback to standalone mode (for development/testing without Temporal)
            logger.warning("Temporal not available, running workflow in standalone mode")

            # Create workflow
            workflow = RoleOnboardingWorkflow(
                workflow_id=workflow_id,
                use_mock_assessment=use_mock,
            )

            # Create initial status in Redis (if available)
            try:
                status_client = get_status_client()
                initial_status = RoleStatus(
                    workflow_id=workflow.workflow_id,
                    company_id=input.company_id,
                    role_name=input.role_name,
                    state=WorkflowState.QUEUED,
                    progress=workflow._create_progress_info(),
                    queued_at=datetime.utcnow(),
                    estimated_duration_seconds=600,
                )
                status_client.set_status(initial_status)
            except Exception as e:
                logger.warning(f"Failed to set initial status in Redis: {e}")

            # Execute workflow in background
            async def run_workflow():
                try:
                    await workflow.execute(input)
                except Exception as e:
                    logger.error(f"Workflow execution failed: {e}")
                    try:
                        status_client = get_status_client()
                        status_client.update_state(
                            workflow.workflow_id,
                            WorkflowState.FAILED,
                            error={"code": "EXECUTION_ERROR", "message": str(e)},
                        )
                    except Exception:
                        pass

            background_tasks.add_task(asyncio.create_task, run_workflow())

            return PushResponse(
                workflow_id=workflow.workflow_id,
                status="queued",
                estimated_duration_seconds=600,
                message=f"Workflow started (standalone mode) for {request.role_name} at {request.company_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Push request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "recoverable": True,
            },
        )


@router.get("/status/{workflow_id}", response_model=StatusResponse)
async def get_workflow_status(workflow_id: str) -> StatusResponse:
    """
    Get workflow status.

    Queries Temporal directly for workflow state. Falls back to Redis
    for detailed progress information if available.

    Args:
        workflow_id: Workflow ID to query

    Returns:
        StatusResponse with current status and progress
    """
    logger.info(f"Status request for workflow: {workflow_id}")

    try:
        # First try to get detailed status from Redis (if available)
        redis_status = None
        try:
            status_client = get_status_client()
            redis_status = status_client.get_status(workflow_id)
        except Exception as e:
            logger.debug(f"Redis status not available: {e}")

        # Query Temporal directly for authoritative workflow state
        temporal_client = await get_temporal_client()
        if temporal_client:
            try:
                handle = temporal_client.get_workflow_handle(workflow_id)
                description = await handle.describe()

                # Map Temporal status to our status
                temporal_status = description.status.name  # RUNNING, COMPLETED, FAILED, etc.
                status_map = {
                    "RUNNING": "processing",
                    "COMPLETED": "ready",
                    "FAILED": "failed",
                    "CANCELED": "failed",
                    "TERMINATED": "failed",
                    "CONTINUED_AS_NEW": "processing",
                    "TIMED_OUT": "failed",
                }
                workflow_status = status_map.get(temporal_status, "queued")

                # Use Redis data if available for detailed progress
                if redis_status:
                    steps = [
                        StepProgress(
                            name=s.name,
                            status=s.status.value,
                            duration_ms=s.duration_ms,
                            started_at=s.started_at,
                            completed_at=s.completed_at,
                            error_message=s.error_message,
                        )
                        for s in redis_status.progress.steps
                    ]
                    progress = ProgressInfo(
                        current=redis_status.progress.current,
                        total=redis_status.progress.total,
                        steps=steps,
                    )
                    error = redis_status.error
                else:
                    # Minimal progress info from Temporal only
                    progress = ProgressInfo(current=0, total=0, steps=[])
                    error = None
                    if temporal_status == "FAILED":
                        error = {"error": "WORKFLOW_FAILED", "message": "Workflow failed in Temporal"}

                return StatusResponse(
                    workflow_id=workflow_id,
                    role_id=redis_status.role_id if redis_status else None,
                    company_id=redis_status.company_id if redis_status else "unknown",
                    role_name=redis_status.role_name if redis_status else "unknown",
                    status=workflow_status,
                    current_step=redis_status.sub_state.value if redis_status and redis_status.sub_state else None,
                    progress=progress,
                    queued_at=redis_status.queued_at if redis_status else None,
                    started_at=description.start_time,
                    completed_at=description.close_time,
                    position_in_queue=None,
                    estimated_duration_seconds=redis_status.estimated_duration_seconds if redis_status else None,
                    dashboard_url=redis_status.dashboard_url if redis_status else None,
                    error=error,
                )

            except Exception as e:
                # Workflow not found in Temporal
                logger.debug(f"Workflow not found in Temporal: {e}")

        # If we have Redis status but no Temporal, return Redis status
        if redis_status:
            steps = [
                StepProgress(
                    name=s.name,
                    status=s.status.value,
                    duration_ms=s.duration_ms,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                    error_message=s.error_message,
                )
                for s in redis_status.progress.steps
            ]

            return StatusResponse(
                workflow_id=redis_status.workflow_id,
                role_id=redis_status.role_id,
                company_id=redis_status.company_id,
                role_name=redis_status.role_name,
                status=redis_status.state.value,
                current_step=redis_status.sub_state.value if redis_status.sub_state else None,
                progress=ProgressInfo(
                    current=redis_status.progress.current,
                    total=redis_status.progress.total,
                    steps=steps,
                ),
                queued_at=redis_status.queued_at,
                started_at=redis_status.started_at,
                completed_at=redis_status.completed_at,
                position_in_queue=redis_status.position_in_queue,
                estimated_duration_seconds=redis_status.estimated_duration_seconds,
                dashboard_url=redis_status.dashboard_url,
                error=redis_status.error,
            )

        # Neither Temporal nor Redis has the workflow
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"Workflow {workflow_id} not found",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status
    """
    settings = get_settings()

    # Log Temporal configuration for debugging
    temporal_debug = settings.get_temporal_debug_info()
    logger.info(f"Temporal config debug: {temporal_debug}")

    components = {
        "api": "healthy",
    }

    # Check Temporal connection
    temporal_connected, temporal_status = await is_temporal_connected()
    if temporal_connected:
        components["temporal"] = "healthy"
    else:
        components["temporal"] = f"unhealthy: {temporal_status}"

    # Add Temporal debug info to components for visibility (must be strings)
    components["temporal_address"] = settings.temporal_address
    env_info = f"env={settings.environment}, db_host={settings.etter_db_host or '(not set)'}, is_qa={settings._is_qa_environment()}, is_prod={settings._is_prod_db()}"
    components["temporal_env_detection"] = env_info

    # Check Redis
    try:
        status_client = get_status_client()
        status_client._get_redis().ping()
        components["redis"] = "healthy"
    except Exception as e:
        components["redis"] = f"unhealthy: {str(e)}"

    # Check if mock data is enabled
    if settings.enable_mock_data:
        components["mock_data"] = "enabled"
    else:
        components["mock_data"] = "disabled"

    # Service is healthy if Temporal is connected (Redis is optional for Temporal mode)
    # In Temporal mode, Redis is only used for batch tracking, not for workflow execution
    if temporal_connected:
        overall_status = "healthy"
    elif components.get("redis") == "healthy":
        # Fallback: can run in standalone mode with Redis
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        components=components,
    )


@router.get("/companies")
async def get_companies() -> Dict[str, Any]:
    """
    Get list of companies with available roles (from mock data).

    Returns:
        List of company names
    """
    try:
        taxonomy_provider = get_role_taxonomy_provider()
        companies = taxonomy_provider.get_companies()

        return {
            "companies": companies,
            "total_count": len(companies),
        }

    except Exception as e:
        logger.error(f"Failed to get companies: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )


@router.get("/roles/{company_name}", response_model=CompanyRolesResponse)
async def get_company_roles(company_name: str) -> CompanyRolesResponse:
    """
    Get roles for a company (from mock data).

    Args:
        company_name: Company name

    Returns:
        List of roles for the company
    """
    try:
        taxonomy_provider = get_role_taxonomy_provider()
        roles = taxonomy_provider.get_roles_for_company(company_name)

        return CompanyRolesResponse(
            company_name=company_name,
            roles=[
                {
                    "job_id": r.job_id,
                    "job_title": r.job_title,
                    "job_role": r.job_role,
                    "draup_role": r.draup_role,
                    "occupation": r.occupation,
                    "job_family": r.job_family,
                    "status": r.status,
                }
                for r in roles
            ],
            total_count=len(roles),
        )

    except Exception as e:
        logger.error(f"Failed to get roles for {company_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )


# =============================================================================
# Batch Processing Endpoints
# =============================================================================

@router.post("/push-batch", response_model=BatchPushResponse)
async def push_batch(
    request: BatchPushRequest,
    background_tasks: BackgroundTasks,
    use_mock: bool = Query(default=False, description="Use mock assessment for testing"),
) -> BatchPushResponse:
    """
    Submit multiple roles for batch processing.

    Design: Each role is independent, batches are just bookkeeping.
    - Spawns independent workflows for each role
    - Temporal handles queueing automatically
    - Worker concurrency provides natural throttling

    Args:
        request: Batch push request with list of roles
        background_tasks: FastAPI background tasks
        use_mock: Use mock assessment for testing

    Returns:
        BatchPushResponse with batch_id and workflow_ids
    """
    logger.info(
        f"Batch push request received",
        extra={
            "company_id": request.company_id,
            "role_count": len(request.roles),
        },
    )

    try:
        settings = get_settings()
        temporal_client = await get_temporal_client()

        # Create batch record
        batch = BatchRecord(
            company_id=request.company_id,
            role_count=len(request.roles),
            created_by=request.created_by,
        )

        workflow_ids = []
        validation_failures = []

        # Spawn independent workflow for each role
        for role_input in request.roles:
            # Use company_id from role or default from request
            company_id = role_input.company_id or request.company_id

            # Convert documents
            documents = []
            for doc in role_input.documents:
                doc_type = DocumentType(doc.type) if doc.type in [t.value for t in DocumentType] else DocumentType.OTHER
                documents.append(DocumentRef(
                    type=doc_type,
                    uri=doc.uri,
                    content=doc.content,
                    name=doc.name,
                ))

            # Create workflow input
            input = RoleOnboardingInput(
                company_id=company_id,
                role_name=role_input.role_name,
                documents=documents,
                draup_role_name=role_input.draup_role_name or role_input.draup_role_id,
                options=WorkflowOptions(
                    skip_enhancement_workflows=request.options.skip_enhancement_workflows,
                    force_rerun=request.options.force_rerun,
                    notify_on_complete=request.options.notify_on_complete,
                ),
            )

            # Validate that documents are provided in the request
            if not input.has_documents():
                logger.warning(f"No documents provided for {role_input.role_name}")
                validation_failures.append({
                    "role_name": role_input.role_name,
                    "errors": ["At least one document (job_description) is required"],
                })
                continue

            # Optionally load taxonomy data for role mapping
            if not input.draup_role_name:
                try:
                    taxonomy_provider = get_role_taxonomy_provider()
                    taxonomy_entry = taxonomy_provider.get_role(company_id, role_input.role_name)
                    if taxonomy_entry:
                        input.taxonomy_entry = taxonomy_entry
                        input.draup_role_name = taxonomy_entry.get_draup_role()
                except Exception as e:
                    logger.warning(f"Failed to fetch taxonomy data for {role_input.role_name}: {e}")

            # Validate input
            validation_errors = input.validate_for_processing()
            if validation_errors:
                logger.warning(
                    f"Validation failed for {role_input.role_name}: {validation_errors}"
                )
                validation_failures.append({
                    "role_name": role_input.role_name,
                    "errors": validation_errors,
                })
                continue

            # Generate workflow ID
            workflow_id = str(uuid.uuid4())
            workflow_ids.append(workflow_id)
            batch.add_workflow(workflow_id)

            if temporal_client:
                # Submit workflow to Temporal
                try:
                    await temporal_client.start_workflow(
                        RoleOnboardingWorkflow,
                        input,
                        id=workflow_id,
                        task_queue=settings.temporal_task_queue,
                        execution_timeout=timedelta(minutes=input.options.timeout_minutes),
                    )
                    logger.info(f"Batch workflow {workflow_id} submitted to Temporal for {role_input.role_name}")
                except Exception as e:
                    logger.error(f"Failed to submit batch workflow to Temporal: {e}")
                    # Remove from workflow_ids since submission failed
                    workflow_ids.remove(workflow_id)
                    batch.workflow_ids.remove(workflow_id)
                    validation_failures.append({
                        "role_name": role_input.role_name,
                        "errors": [f"Temporal submission failed: {str(e)}"],
                    })
            else:
                # Fallback to standalone mode
                logger.warning(f"Temporal not available, running workflow {workflow_id} in standalone mode")

                workflow = RoleOnboardingWorkflow(
                    workflow_id=workflow_id,
                    use_mock_assessment=use_mock,
                )

                # Try to create initial status in Redis
                try:
                    status_client = get_status_client()
                    initial_status = RoleStatus(
                        workflow_id=workflow_id,
                        company_id=company_id,
                        role_name=role_input.role_name,
                        state=WorkflowState.QUEUED,
                        progress=workflow._create_progress_info(),
                        queued_at=datetime.utcnow(),
                        estimated_duration_seconds=600,
                        metadata={"batch_id": batch.batch_id},
                    )
                    status_client.set_status(initial_status)
                except Exception as e:
                    logger.warning(f"Failed to set initial status in Redis: {e}")

                # Execute workflow in background
                async def run_workflow(wf=workflow, inp=input):
                    try:
                        await wf.execute(inp)
                    except Exception as e:
                        logger.error(f"Workflow execution failed: {e}")
                        try:
                            status_client = get_status_client()
                            status_client.update_state(
                                wf.workflow_id,
                                WorkflowState.FAILED,
                                error={"code": "EXECUTION_ERROR", "message": str(e)},
                            )
                        except Exception:
                            pass

                background_tasks.add_task(asyncio.create_task, run_workflow())

        # Try to store batch record in Redis
        try:
            status_client = get_status_client()
            status_client.set_batch(batch)
        except Exception as e:
            logger.warning(f"Failed to store batch record in Redis: {e}")

        # Estimate total duration (assuming some parallelism)
        # With 3-5 concurrent workers, batch of N roles takes ~(N/4)*15 minutes
        estimated_seconds = max(600, (len(request.roles) // 4 + 1) * 600)

        message = f"Batch submitted: {len(workflow_ids)} roles queued for processing"
        if temporal_client:
            message += " (via Temporal)"
        else:
            message += " (standalone mode)"
        if validation_failures:
            message += f", {len(validation_failures)} roles failed validation"

        return BatchPushResponse(
            batch_id=batch.batch_id,
            total_roles=len(request.roles),
            workflow_ids=workflow_ids,
            status="queued",
            estimated_duration_seconds=estimated_seconds,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch push request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "recoverable": True,
            },
        )


@router.get("/batch-status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """
    Get aggregated status for a batch.

    Returns counts and individual role statuses aggregated from
    the constituent workflows.

    Args:
        batch_id: Batch ID to query

    Returns:
        BatchStatusResponse with aggregated status
    """
    logger.info(f"Batch status request for: {batch_id}")

    try:
        status_client = get_status_client()
        status = status_client.get_batch_status(batch_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"Batch {batch_id} not found",
                },
            )

        return BatchStatusResponse(
            batch_id=status.batch_id,
            company_id=status.company_id,
            total=status.total,
            queued=status.queued,
            in_progress=status.in_progress,
            completed=status.completed,
            failed=status.failed,
            state=status.state.value,
            progress_percent=status.progress_percent,
            success_rate=status.success_rate,
            created_at=status.created_at,
            roles=[
                BatchRoleStatusResponse(
                    role_name=r.role_name,
                    company_id=r.company_id,
                    workflow_id=r.workflow_id,
                    status=r.status,
                    error=r.error,
                    dashboard_url=r.dashboard_url,
                )
                for r in status.roles
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch status request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post("/retry-failed/{batch_id}", response_model=BatchRetryResponse)
async def retry_failed_roles(
    batch_id: str,
    request: BatchRetryRequest,
    background_tasks: BackgroundTasks,
    use_mock: bool = Query(default=False, description="Use mock assessment for testing"),
) -> BatchRetryResponse:
    """
    Retry failed roles in a batch.

    Creates new workflows for failed roles only.

    Args:
        batch_id: Batch ID
        request: Retry request with optional workflow_ids filter
        background_tasks: FastAPI background tasks
        use_mock: Use mock assessment for testing

    Returns:
        BatchRetryResponse with new workflow IDs
    """
    logger.info(f"Retry request for batch: {batch_id}")

    try:
        status_client = get_status_client()
        batch_status = status_client.get_batch_status(batch_id)

        if not batch_status:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"Batch {batch_id} not found",
                },
            )

        # Get failed workflow IDs
        if request.workflow_ids:
            # Filter to only specified and failed
            failed_ids = set(batch_status.get_failed_workflow_ids())
            workflow_ids_to_retry = [
                wid for wid in request.workflow_ids if wid in failed_ids
            ]
        else:
            # Retry all failed
            workflow_ids_to_retry = batch_status.get_failed_workflow_ids()

        if not workflow_ids_to_retry:
            return BatchRetryResponse(
                batch_id=batch_id,
                retried_count=0,
                new_workflow_ids=[],
                message="No failed roles to retry",
            )

        new_workflow_ids = []

        # Re-submit each failed role
        for old_workflow_id in workflow_ids_to_retry:
            # Get original role status
            old_status = status_client.get_status(old_workflow_id)
            if not old_status:
                continue

            # Create new workflow
            workflow = RoleOnboardingWorkflow(use_mock_assessment=use_mock)
            new_workflow_ids.append(workflow.workflow_id)

            # Create input from original status
            input = RoleOnboardingInput(
                company_id=old_status.company_id,
                role_name=old_status.role_name,
                options=WorkflowOptions(
                    skip_enhancement_workflows=request.options.skip_enhancement_workflows,
                    force_rerun=request.options.force_rerun,
                    notify_on_complete=request.options.notify_on_complete,
                ),
            )

            # Note: Retry does not have access to original documents
            # The workflow will fail validation if documents are required
            # Consider re-submitting via /push endpoint with documents instead

            # Optionally load taxonomy data for role mapping
            if not input.draup_role_name:
                try:
                    taxonomy_provider = get_role_taxonomy_provider()
                    taxonomy_entry = taxonomy_provider.get_role(
                        old_status.company_id, old_status.role_name
                    )
                    if taxonomy_entry:
                        input.taxonomy_entry = taxonomy_entry
                        input.draup_role_name = taxonomy_entry.get_draup_role()
                except Exception as e:
                    logger.warning(f"Failed to fetch taxonomy data for retry: {e}")

            # Create initial status
            initial_status = RoleStatus(
                workflow_id=workflow.workflow_id,
                company_id=old_status.company_id,
                role_name=old_status.role_name,
                state=WorkflowState.QUEUED,
                progress=workflow._create_progress_info(),
                queued_at=datetime.utcnow(),
                estimated_duration_seconds=600,
                metadata={
                    "batch_id": batch_id,
                    "retry_of": old_workflow_id,
                },
            )
            status_client.set_status(initial_status)

            # Add to batch
            status_client.add_workflow_to_batch(batch_id, workflow.workflow_id)

            # Execute workflow in background
            async def run_workflow(wf=workflow, inp=input):
                try:
                    await wf.execute(inp)
                except Exception as e:
                    logger.error(f"Retry workflow execution failed: {e}")
                    status_client.update_state(
                        wf.workflow_id,
                        WorkflowState.FAILED,
                        error={"code": "EXECUTION_ERROR", "message": str(e)},
                    )

            background_tasks.add_task(asyncio.create_task, run_workflow())

        return BatchRetryResponse(
            batch_id=batch_id,
            retried_count=len(new_workflow_ids),
            new_workflow_ids=new_workflow_ids,
            message=f"Retried {len(new_workflow_ids)} failed roles",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retry request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )


def create_app():
    """
    Create FastAPI application.

    Returns:
        FastAPI application instance
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    settings = get_settings()

    app = FastAPI(
        title="Etter Self-Service Pipeline API",
        description="API for self-service role onboarding and AI assessment workflows",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include router
    app.include_router(router)

    @app.get("/")
    async def root():
        return {
            "name": "Etter Self-Service Pipeline API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# Lazy app instance - only created when accessed directly (standalone mode)
# When integrated with parent app, only the router is imported
app = None


def get_app():
    """Get or create the FastAPI app instance (for standalone mode)."""
    global app
    if app is None:
        app = create_app()
    return app
