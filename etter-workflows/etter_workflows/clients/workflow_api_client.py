"""
Workflow API client for Etter Workflows.

Provides HTTP client for calling the existing workflow API:
- AI Assessment execution
- Workflow triggering

This mirrors the functionality in data_model_integration.py
but provides a clean interface for the self-service pipeline.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from functools import lru_cache

from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class WorkflowAPIClient:
    """
    HTTP client for the existing Etter workflow API.

    Provides methods for triggering AI assessments and other workflows.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_attempts: int = 2,
    ):
        """
        Initialize Workflow API client.

        Args:
            base_url: Base URL for the workflow API
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_workflow_api_url()
        self.timeout = timeout or settings.workflow_api_timeout
        self.retry_attempts = retry_attempts
        self._session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            try:
                import httpx
                self._session = httpx.Client(
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except ImportError:
                # Fallback to requests
                import requests
                self._session = requests.Session()
                self._session.base_url = self.base_url
        return self._session

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body
            params: Query parameters

        Returns:
            Response JSON
        """
        session = self._get_session()
        url = f"{self.base_url}{endpoint}" if hasattr(session, 'base_url') else endpoint

        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                if hasattr(session, 'request'):
                    # httpx
                    response = session.request(
                        method,
                        endpoint,
                        json=data,
                        params=params,
                    )
                    response.raise_for_status()
                    return response.json()
                else:
                    # requests
                    response = session.request(
                        method,
                        url,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    return response.json()

            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.retry_attempts + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)

        raise last_error

    def execute_ai_assessment(
        self,
        company: str,
        role: str,
        delete_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute AI assessment workflow via the API.

        This triggers the automated workflow orchestrator that runs:
        1. Entity resolution
        2. Job description fetch
        3. AI impact assessment
        4. AI impact quantification

        Args:
            company: Company name
            role: Role name
            delete_existing: Delete existing assessment first

        Returns:
            Assessment result with workflow data
        """
        try:
            # Try to use the existing workflow engine
            from draup_world_model.automated_workflow.engine import (
                AutomatedWorkflowOrchestrator,
                WorkflowConfiguration,
            )

            config = WorkflowConfiguration(
                base_url=self.base_url,
                username="self_service_pipeline",
                timeout=self.timeout,
                retry_attempts=self.retry_attempts,
            )

            orchestrator = AutomatedWorkflowOrchestrator(config)
            result = orchestrator.execute_workflow(company, role)

            return {
                "success": result.success,
                "request_id": result.request_id,
                "execution_time": result.execution_time,
                "steps_executed": result.steps_executed,
                "final_output": result.final_output,
                "step_results": result.step_results,
                "error_message": result.error_message,
            }

        except ImportError:
            logger.warning("Workflow engine not available, using HTTP API")
            # Fallback to HTTP API call (if available)
            return self._execute_assessment_via_http(company, role)

    def _execute_assessment_via_http(
        self,
        company: str,
        role: str,
    ) -> Dict[str, Any]:
        """
        Execute assessment via HTTP API (fallback).

        Args:
            company: Company name
            role: Role name

        Returns:
            Assessment result
        """
        # This is a placeholder for direct HTTP API calls
        # In practice, the workflow engine should be available
        raise NotImplementedError(
            "HTTP API execution not implemented. "
            "Please ensure draup_world_model.automated_workflow is available."
        )

    def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get status of a workflow by request ID.

        Args:
            request_id: Workflow request ID

        Returns:
            Workflow status
        """
        # This would query the workflow API for status
        # For now, we rely on the orchestrator's synchronous execution
        raise NotImplementedError("Async workflow status not implemented")

    def close(self):
        """Close HTTP session."""
        if self._session:
            if hasattr(self._session, 'close'):
                self._session.close()
            self._session = None


# Singleton client instance
_workflow_api_client: Optional[WorkflowAPIClient] = None


def get_workflow_api_client() -> WorkflowAPIClient:
    """
    Get the singleton Workflow API client instance.

    Returns:
        WorkflowAPIClient instance
    """
    global _workflow_api_client
    if _workflow_api_client is None:
        _workflow_api_client = WorkflowAPIClient()
    return _workflow_api_client


def reset_workflow_api_client():
    """Reset the singleton client (for testing)."""
    global _workflow_api_client
    if _workflow_api_client:
        _workflow_api_client.close()
    _workflow_api_client = None
