"""
Retry policies for Etter Workflows.

Defines retry configurations for different types of activities:
- LLM calls (handle rate limits, transient errors)
- Database operations (handle connection issues)
- API calls (handle network issues)

Based on Temporal RetryPolicy configuration:
    Initial Interval: 1 second
    Backoff Coefficient: 2.0
    Maximum Interval: 5 minutes
    Maximum Attempts: 3
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional


@dataclass
class RetryConfig:
    """
    Retry configuration for activities.

    This maps to Temporal RetryPolicy configuration.

    Attributes:
        initial_interval: Initial retry interval
        backoff_coefficient: Multiplier for each retry
        maximum_interval: Maximum time between retries
        maximum_attempts: Maximum number of retry attempts
        non_retryable_errors: List of error types that should not be retried
    """
    initial_interval: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    backoff_coefficient: float = 2.0
    maximum_interval: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    maximum_attempts: int = 3
    non_retryable_errors: List[str] = field(default_factory=list)

    def to_temporal_dict(self) -> dict:
        """Convert to Temporal RetryPolicy dict format."""
        return {
            "initial_interval": self.initial_interval,
            "backoff_coefficient": self.backoff_coefficient,
            "maximum_interval": self.maximum_interval,
            "maximum_attempts": self.maximum_attempts,
            "non_retryable_error_types": self.non_retryable_errors,
        }


# Default retry policy (for general activities)
DEFAULT_RETRY_CONFIG = RetryConfig(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
    non_retryable_errors=[
        "ValidationError",
        "AuthenticationError",
        "PermissionDeniedError",
    ],
)


# LLM-specific retry policy (handle rate limits)
LLM_RETRY_CONFIG = RetryConfig(
    initial_interval=timedelta(seconds=5),  # Start higher due to rate limits
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),  # Allow longer waits for rate limits
    maximum_attempts=5,  # More attempts for transient rate limits
    non_retryable_errors=[
        "ValidationError",
        "AuthenticationError",
        "InvalidPromptError",
        "ContentPolicyViolationError",
    ],
)


# Database retry policy (handle connection issues)
DB_RETRY_CONFIG = RetryConfig(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=1.5,  # Slower backoff for DB
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=4,
    non_retryable_errors=[
        "ConstraintViolationError",
        "SchemaError",
        "AuthenticationError",
    ],
)


# API retry policy (handle network issues)
API_RETRY_CONFIG = RetryConfig(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
    non_retryable_errors=[
        "AuthenticationError",
        "NotFoundError",
        "ValidationError",
    ],
)


# No retry policy (for idempotent critical operations)
NO_RETRY_CONFIG = RetryConfig(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=1.0,
    maximum_interval=timedelta(seconds=1),
    maximum_attempts=1,
    non_retryable_errors=[],
)


def get_default_retry_policy() -> RetryConfig:
    """Get the default retry policy."""
    return DEFAULT_RETRY_CONFIG


def get_llm_retry_policy() -> RetryConfig:
    """Get the retry policy for LLM operations."""
    return LLM_RETRY_CONFIG


def get_db_retry_policy() -> RetryConfig:
    """Get the retry policy for database operations."""
    return DB_RETRY_CONFIG


def get_api_retry_policy() -> RetryConfig:
    """Get the retry policy for API calls."""
    return API_RETRY_CONFIG


def get_no_retry_policy() -> RetryConfig:
    """Get a policy with no retries."""
    return NO_RETRY_CONFIG


def create_custom_retry_policy(
    max_attempts: int = 3,
    initial_interval_seconds: int = 1,
    max_interval_minutes: int = 5,
    backoff_coefficient: float = 2.0,
    non_retryable_errors: Optional[List[str]] = None,
) -> RetryConfig:
    """
    Create a custom retry policy.

    Args:
        max_attempts: Maximum retry attempts
        initial_interval_seconds: Initial retry interval in seconds
        max_interval_minutes: Maximum retry interval in minutes
        backoff_coefficient: Backoff multiplier
        non_retryable_errors: List of non-retryable error types

    Returns:
        Custom RetryConfig
    """
    return RetryConfig(
        initial_interval=timedelta(seconds=initial_interval_seconds),
        backoff_coefficient=backoff_coefficient,
        maximum_interval=timedelta(minutes=max_interval_minutes),
        maximum_attempts=max_attempts,
        non_retryable_errors=non_retryable_errors or [],
    )
