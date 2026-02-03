"""
Base activity module for Etter Workflows.

Provides:
- BaseActivity class with common functionality
- Decorators for activity registration with retry policies
- Utility functions for activity execution

Activity Contract:
    Input: {id, inputs, context}
    Output: {id, status, result, error, metrics}
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from etter_workflows.models.inputs import ExecutionContext
from etter_workflows.models.outputs import (
    ActivityResult,
    ErrorInfo,
    ExecutionMetrics,
    ResultStatus,
)
from etter_workflows.config.retry_policies import RetryConfig, get_default_retry_policy

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseActivity(ABC):
    """
    Base class for all activities.

    Provides common functionality for:
    - Context management
    - Error handling
    - Metrics collection
    - Logging
    """

    def __init__(self, name: str):
        """
        Initialize activity.

        Args:
            name: Activity name for logging and metrics
        """
        self.name = name
        self._start_time: Optional[datetime] = None
        self._metrics = ExecutionMetrics()

    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActivityResult:
        """
        Execute the activity.

        Args:
            inputs: Activity-specific inputs
            context: Execution context

        Returns:
            ActivityResult with status and outputs
        """
        pass

    def _start_execution(self) -> None:
        """Mark the start of execution."""
        self._start_time = datetime.utcnow()
        self._metrics.started_at = self._start_time
        logger.info(
            f"Starting activity: {self.name}",
            extra={"activity": self.name, "start_time": self._start_time.isoformat()},
        )

    def _end_execution(self, success: bool = True) -> ExecutionMetrics:
        """
        Mark the end of execution and return metrics.

        Args:
            success: Whether execution was successful

        Returns:
            ExecutionMetrics with timing information
        """
        end_time = datetime.utcnow()
        self._metrics.completed_at = end_time

        if self._start_time:
            duration = end_time - self._start_time
            self._metrics.duration_ms = int(duration.total_seconds() * 1000)

        status = "success" if success else "failed"
        logger.info(
            f"Completed activity: {self.name} ({status})",
            extra={
                "activity": self.name,
                "status": status,
                "duration_ms": self._metrics.duration_ms,
            },
        )

        return self._metrics

    def _create_success_result(
        self,
        id: str,
        result: Dict[str, Any],
    ) -> ActivityResult:
        """Create a successful activity result."""
        metrics = self._end_execution(success=True)
        return ActivityResult.create_success(id=id, result=result, metrics=metrics)

    def _create_failure_result(
        self,
        id: str,
        error: Exception,
        error_code: str = "ACTIVITY_ERROR",
        recoverable: bool = True,
    ) -> ActivityResult:
        """Create a failed activity result."""
        metrics = self._end_execution(success=False)
        error_info = ErrorInfo(
            code=error_code,
            message=str(error),
            recoverable=recoverable,
            details={"exception_type": type(error).__name__},
        )
        return ActivityResult.create_failure(id=id, error=error_info, metrics=metrics)


def activity_with_retry(
    retry_config: Optional[RetryConfig] = None,
    timeout_seconds: int = 300,
):
    """
    Decorator for activity functions with retry policy.

    This decorator:
    1. Wraps the function for Temporal activity registration
    2. Applies retry policy
    3. Handles timeout
    4. Provides standard error handling

    Args:
        retry_config: Retry configuration (defaults to standard policy)
        timeout_seconds: Activity timeout

    Returns:
        Decorated function
    """
    if retry_config is None:
        retry_config = get_default_retry_policy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            last_error = None

            for attempt in range(retry_config.maximum_attempts):
                try:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout_seconds:
                        raise TimeoutError(
                            f"Activity timed out after {elapsed:.1f}s"
                        )

                    # Execute function
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    last_error = e
                    error_type = type(e).__name__

                    # Check if error is non-retryable
                    if error_type in retry_config.non_retryable_errors:
                        logger.error(
                            f"Non-retryable error in {func.__name__}: {e}",
                            extra={"error_type": error_type},
                        )
                        raise

                    # Log retry attempt
                    if attempt < retry_config.maximum_attempts - 1:
                        wait_time = min(
                            retry_config.initial_interval.total_seconds() * (
                                retry_config.backoff_coefficient ** attempt
                            ),
                            retry_config.maximum_interval.total_seconds(),
                        )
                        logger.warning(
                            f"Retry {attempt + 1}/{retry_config.maximum_attempts} "
                            f"for {func.__name__} after {wait_time:.1f}s: {e}"
                        )
                        time.sleep(wait_time)

            # All retries exhausted
            raise last_error

        # Store retry config for Temporal worker registration
        wrapper._retry_config = retry_config
        wrapper._timeout_seconds = timeout_seconds

        # Apply Temporal activity decorator
        try:
            from temporalio import activity
            return activity.defn(wrapper)
        except ImportError:
            # If temporalio not installed, return wrapper as-is
            logger.warning("temporalio not installed, activity decorator not applied")
            return wrapper

    return decorator


class ActivityContext:
    """
    Context manager for activity execution.

    Provides:
    - Automatic timing
    - Error handling
    - Logging
    """

    def __init__(self, activity_name: str, context: ExecutionContext):
        self.activity_name = activity_name
        self.context = context
        self.start_time: Optional[datetime] = None
        self.metrics = ExecutionMetrics()

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.metrics.started_at = self.start_time
        logger.info(
            f"Starting activity: {self.activity_name}",
            extra={
                "activity": self.activity_name,
                "trace_id": self.context.trace_id,
                "company_id": self.context.company_id,
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        self.metrics.completed_at = end_time

        if self.start_time:
            duration = end_time - self.start_time
            self.metrics.duration_ms = int(duration.total_seconds() * 1000)

        status = "success" if exc_type is None else "failed"
        logger.info(
            f"Completed activity: {self.activity_name} ({status})",
            extra={
                "activity": self.activity_name,
                "status": status,
                "duration_ms": self.metrics.duration_ms,
                "trace_id": self.context.trace_id,
            },
        )

        # Don't suppress exceptions
        return False
