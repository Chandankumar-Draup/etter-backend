"""
Status client for Etter Workflows.

Provides status tracking operations using Redis:
- Store and retrieve workflow status
- Update progress information
- TTL-based caching
- Batch record management

Based on the state persistence strategy:
    - Progress details: Redis (TTL: 1 hour)
    - High-frequency updates, acceptable loss
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import lru_cache

from etter_workflows.config.settings import get_settings
from etter_workflows.models.status import (
    RoleStatus,
    WorkflowState,
    ProcessingSubState,
    ProgressInfo,
    StepStatus,
)
from etter_workflows.models.batch import (
    BatchRecord,
    BatchStatus,
    BatchRoleStatus,
)

logger = logging.getLogger(__name__)


class StatusClient:
    """
    Redis-based status client for workflow progress tracking.

    Provides methods for storing and retrieving workflow status
    with automatic TTL expiration.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ):
        """
        Initialize Status client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ttl_seconds: Default TTL for status entries
        """
        settings = get_settings()
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self.password = password or settings.redis_password
        self.ttl_seconds = ttl_seconds or settings.redis_status_ttl_seconds
        self._redis = None

    def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis
                settings = get_settings()
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=settings.redis_socket_timeout,
                    socket_connect_timeout=settings.redis_connect_timeout,
                    retry_on_timeout=settings.redis_retry_on_timeout,
                    health_check_interval=settings.redis_health_check_interval,
                )
                # Test connection
                self._redis.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except ImportError:
                raise ImportError("redis package not installed. Install with: pip install redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._redis

    def _get_key(self, workflow_id: str) -> str:
        """Get Redis key for workflow status."""
        return f"etter:workflow:status:{workflow_id}"

    def _get_queue_key(self, company_id: str) -> str:
        """Get Redis key for company queue."""
        return f"etter:queue:{company_id}"

    def _get_batch_key(self, batch_id: str) -> str:
        """Get Redis key for batch record."""
        return f"etter:batch:{batch_id}"

    def _get_company_batches_key(self, company_id: str) -> str:
        """Get Redis key for company's batch list."""
        return f"etter:company:batches:{company_id}"

    def set_status(self, status: RoleStatus) -> bool:
        """
        Store workflow status in Redis.

        Args:
            status: RoleStatus to store

        Returns:
            True if successful
        """
        try:
            redis = self._get_redis()
            key = self._get_key(status.workflow_id)

            # Serialize status
            data = {
                "workflow_id": status.workflow_id,
                "role_id": status.role_id,
                "company_id": status.company_id,
                "role_name": status.role_name,
                "state": status.state.value,
                "sub_state": status.sub_state.value if status.sub_state else None,
                "progress": {
                    "current": status.progress.current,
                    "total": status.progress.total,
                    "steps": [
                        {
                            "name": s.name,
                            "status": s.status.value,
                            "duration_ms": s.duration_ms,
                            "started_at": s.started_at.isoformat() if s.started_at else None,
                            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                            "error_message": s.error_message,
                        }
                        for s in status.progress.steps
                    ],
                    "current_step_name": status.progress.current_step_name,
                },
                "queued_at": status.queued_at.isoformat() if status.queued_at else None,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                "position_in_queue": status.position_in_queue,
                "estimated_duration_seconds": status.estimated_duration_seconds,
                "error": status.error,
                "dashboard_url": status.dashboard_url,
                "metadata": status.metadata,
            }

            redis.setex(key, self.ttl_seconds, json.dumps(data))
            logger.debug(f"Stored status for workflow: {status.workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store status: {e}")
            return False

    def get_status(self, workflow_id: str) -> Optional[RoleStatus]:
        """
        Retrieve workflow status from Redis.

        Args:
            workflow_id: Workflow ID to look up

        Returns:
            RoleStatus or None if not found
        """
        try:
            redis = self._get_redis()
            key = self._get_key(workflow_id)

            data = redis.get(key)
            if not data:
                return None

            data = json.loads(data)

            # Reconstruct ProgressInfo
            progress = ProgressInfo(
                current=data["progress"]["current"],
                total=data["progress"]["total"],
                current_step_name=data["progress"].get("current_step_name"),
            )
            for step_data in data["progress"]["steps"]:
                from etter_workflows.models.status import StepProgress
                step = StepProgress(
                    name=step_data["name"],
                    status=StepStatus(step_data["status"]),
                    duration_ms=step_data.get("duration_ms"),
                    started_at=(
                        datetime.fromisoformat(step_data["started_at"])
                        if step_data.get("started_at") else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(step_data["completed_at"])
                        if step_data.get("completed_at") else None
                    ),
                    error_message=step_data.get("error_message"),
                )
                progress.steps.append(step)

            # Reconstruct RoleStatus
            status = RoleStatus(
                workflow_id=data["workflow_id"],
                role_id=data.get("role_id"),
                company_id=data["company_id"],
                role_name=data["role_name"],
                state=WorkflowState(data["state"]),
                sub_state=(
                    ProcessingSubState(data["sub_state"])
                    if data.get("sub_state") else None
                ),
                progress=progress,
                queued_at=(
                    datetime.fromisoformat(data["queued_at"])
                    if data.get("queued_at") else None
                ),
                started_at=(
                    datetime.fromisoformat(data["started_at"])
                    if data.get("started_at") else None
                ),
                completed_at=(
                    datetime.fromisoformat(data["completed_at"])
                    if data.get("completed_at") else None
                ),
                position_in_queue=data.get("position_in_queue"),
                estimated_duration_seconds=data.get("estimated_duration_seconds"),
                error=data.get("error"),
                dashboard_url=data.get("dashboard_url"),
                metadata=data.get("metadata", {}),
            )

            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return None

    def update_state(
        self,
        workflow_id: str,
        state: WorkflowState,
        sub_state: Optional[ProcessingSubState] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update workflow state.

        Args:
            workflow_id: Workflow ID
            state: New state
            sub_state: Optional sub-state
            error: Optional error info

        Returns:
            True if successful
        """
        status = self.get_status(workflow_id)
        if not status:
            logger.warning(f"Status not found for workflow: {workflow_id}")
            return False

        status.state = state
        status.sub_state = sub_state
        if error:
            status.error = error

        # Update timestamps
        if state == WorkflowState.PROCESSING and status.started_at is None:
            status.started_at = datetime.utcnow()
        elif state in (WorkflowState.READY, WorkflowState.FAILED, WorkflowState.DEGRADED):
            status.completed_at = datetime.utcnow()

        return self.set_status(status)

    def update_progress(
        self,
        workflow_id: str,
        step_name: str,
        step_status: StepStatus,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update progress for a specific step.

        Args:
            workflow_id: Workflow ID
            step_name: Name of the step
            step_status: Status of the step
            duration_ms: Execution time
            error_message: Error message if failed

        Returns:
            True if successful
        """
        status = self.get_status(workflow_id)
        if not status:
            logger.warning(f"Status not found for workflow: {workflow_id}")
            return False

        status.progress.update_step(
            name=step_name,
            status=step_status,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        return self.set_status(status)

    def delete_status(self, workflow_id: str) -> bool:
        """
        Delete workflow status.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted
        """
        try:
            redis = self._get_redis()
            key = self._get_key(workflow_id)
            return redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Failed to delete status: {e}")
            return False

    def get_queue_position(self, company_id: str, workflow_id: str) -> Optional[int]:
        """
        Get position in queue for a workflow.

        Args:
            company_id: Company ID
            workflow_id: Workflow ID

        Returns:
            Position (1-indexed) or None if not in queue
        """
        try:
            redis = self._get_redis()
            key = self._get_queue_key(company_id)
            position = redis.lpos(key, workflow_id)
            return position + 1 if position is not None else None
        except Exception as e:
            logger.error(f"Failed to get queue position: {e}")
            return None

    def close(self):
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def set_batch(self, batch: BatchRecord) -> bool:
        """
        Store batch record in Redis.

        Args:
            batch: BatchRecord to store

        Returns:
            True if successful
        """
        try:
            redis = self._get_redis()
            key = self._get_batch_key(batch.batch_id)

            data = {
                "batch_id": batch.batch_id,
                "workflow_ids": batch.workflow_ids,
                "company_id": batch.company_id,
                "role_count": batch.role_count,
                "created_at": batch.created_at.isoformat(),
                "created_by": batch.created_by,
                "metadata": batch.metadata,
            }

            # Store batch record
            redis.setex(key, self.ttl_seconds, json.dumps(data))

            # Add to company's batch list for lookup
            company_batches_key = self._get_company_batches_key(batch.company_id)
            redis.lpush(company_batches_key, batch.batch_id)
            redis.expire(company_batches_key, self.ttl_seconds)

            logger.debug(f"Stored batch: {batch.batch_id} with {batch.role_count} roles")
            return True

        except Exception as e:
            logger.error(f"Failed to store batch: {e}")
            return False

    def get_batch(self, batch_id: str) -> Optional[BatchRecord]:
        """
        Retrieve batch record from Redis.

        Args:
            batch_id: Batch ID to look up

        Returns:
            BatchRecord or None if not found
        """
        try:
            redis = self._get_redis()
            key = self._get_batch_key(batch_id)

            data = redis.get(key)
            if not data:
                return None

            data = json.loads(data)

            return BatchRecord(
                batch_id=data["batch_id"],
                workflow_ids=data["workflow_ids"],
                company_id=data["company_id"],
                role_count=data["role_count"],
                created_at=datetime.fromisoformat(data["created_at"]),
                created_by=data.get("created_by"),
                metadata=data.get("metadata", {}),
            )

        except Exception as e:
            logger.error(f"Failed to get batch: {e}")
            return None

    def get_batch_status(self, batch_id: str) -> Optional[BatchStatus]:
        """
        Get aggregated status for a batch.

        This queries individual workflow statuses and aggregates them.

        Args:
            batch_id: Batch ID

        Returns:
            BatchStatus with aggregated information
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return None

        # Initialize counters
        status = BatchStatus(
            batch_id=batch.batch_id,
            company_id=batch.company_id,
            total=batch.role_count,
            created_at=batch.created_at,
        )

        # Query each workflow status
        for workflow_id in batch.workflow_ids:
            role_status = self.get_status(workflow_id)
            if not role_status:
                # Workflow status not found, count as queued
                status.queued += 1
                status.roles.append(BatchRoleStatus(
                    role_name="unknown",
                    company_id=batch.company_id,
                    workflow_id=workflow_id,
                    status="unknown",
                ))
                continue

            # Map state to counter
            state = role_status.state
            if state == WorkflowState.QUEUED:
                status.queued += 1
            elif state == WorkflowState.PROCESSING:
                status.in_progress += 1
            elif state == WorkflowState.READY:
                status.completed += 1
            elif state in (WorkflowState.FAILED, WorkflowState.VALIDATION_ERROR, WorkflowState.DEGRADED):
                status.failed += 1
            else:
                status.queued += 1

            # Add role status
            status.roles.append(BatchRoleStatus(
                role_name=role_status.role_name,
                company_id=role_status.company_id,
                workflow_id=workflow_id,
                status=state.value,
                error=role_status.error.get("message") if role_status.error else None,
                dashboard_url=role_status.dashboard_url,
            ))

        return status

    def add_workflow_to_batch(self, batch_id: str, workflow_id: str) -> bool:
        """
        Add a workflow to an existing batch.

        Args:
            batch_id: Batch ID
            workflow_id: Workflow ID to add

        Returns:
            True if successful
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return False

        batch.add_workflow(workflow_id)
        return self.set_batch(batch)

    def get_company_batches(
        self,
        company_id: str,
        limit: int = 10
    ) -> List[BatchRecord]:
        """
        Get recent batches for a company.

        Args:
            company_id: Company ID
            limit: Maximum batches to return

        Returns:
            List of BatchRecord
        """
        try:
            redis = self._get_redis()
            key = self._get_company_batches_key(company_id)

            batch_ids = redis.lrange(key, 0, limit - 1)
            batches = []

            for batch_id in batch_ids:
                batch = self.get_batch(batch_id)
                if batch:
                    batches.append(batch)

            return batches

        except Exception as e:
            logger.error(f"Failed to get company batches: {e}")
            return []


# Singleton client instance
_status_client: Optional[StatusClient] = None


def get_status_client() -> StatusClient:
    """
    Get the singleton Status client instance.

    Returns:
        StatusClient instance
    """
    global _status_client
    if _status_client is None:
        _status_client = StatusClient()
    return _status_client


def reset_status_client():
    """Reset the singleton client (for testing)."""
    global _status_client
    if _status_client:
        _status_client.close()
    _status_client = None
