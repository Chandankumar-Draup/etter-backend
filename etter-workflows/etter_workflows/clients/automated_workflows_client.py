"""
Automated Workflows API client for Etter Workflows.

Provides HTTP client for calling the automated workflows API (localhost:8083):
- Create Company Role
- Link Job Description
- Run AI Assessment
- Get Company Role

These endpoints are defined in automated_workflows_routes.py.
"""

import logging
import time
from typing import Any, Dict, Optional

from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class AutomatedWorkflowsClient:
    """
    HTTP client for the Automated Workflows API.

    Provides methods for role setup and AI assessment activities
    by calling the Flask API endpoints at localhost:8083.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_attempts: int = 2,
    ):
        """
        Initialize Automated Workflows API client.

        Args:
            base_url: Base URL for the automated workflows API
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_automated_workflows_api_url()
        self.timeout = timeout or settings.automated_workflows_api_timeout
        self.retry_attempts = retry_attempts
        self._session = None

        # Debug logging for configuration
        logger.info(f"AutomatedWorkflowsClient initialized:")
        logger.info(f"  Base URL: {self.base_url}")
        logger.info(f"  Timeout: {self.timeout}s")
        logger.info(f"  Environment detection:")
        logger.info(f"    - etter_db_host: '{settings.etter_db_host}'")
        logger.info(f"    - is_qa_or_prod: {settings._is_qa_or_prod_environment()}")
        logger.info(f"    - is_prod_db: {settings._is_prod_db()}")
        logger.info(f"    - draup_world_api_url: '{settings.draup_world_api_url}'")

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            try:
                import httpx
                self._session = httpx.Client(
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
                self._use_httpx = True
            except ImportError:
                # Fallback to requests
                import requests
                self._session = requests.Session()
                self._use_httpx = False
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
        url = f"{self.base_url}{endpoint}"

        logger.info(f"API Request: {method} {url}")
        if data:
            logger.debug(f"  Request data keys: {list(data.keys())}")
        if params:
            logger.debug(f"  Request params: {params}")

        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                if self._use_httpx:
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

    def create_company_role(
        self,
        company_name: str,
        role_name: str,
        draup_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create or find a CompanyRole node via API.

        Args:
            company_name: Company name/identifier
            role_name: Role name
            draup_role: Draup standardized role name
            metadata: Additional metadata to store

        Returns:
            Dict with company_role_id and metadata
        """
        logger.info(f"Creating CompanyRole via API: {company_name} - {role_name}")

        payload = {
            "company_name": company_name,
            "role_name": role_name,
        }
        if draup_role:
            payload["draup_role"] = draup_role
        if metadata:
            payload["metadata"] = metadata

        result = self._request(
            "POST",
            "/api/automated_workflows/create-company-role",
            data=payload,
        )

        if result.get("status") == "error":
            raise Exception(f"Failed to create CompanyRole: {result.get('message')}")

        logger.info(f"Created CompanyRole: {result.get('company_role_id')}")
        return result

    def link_job_description(
        self,
        company_role_id: str,
        jd_content: str,
        jd_title: Optional[str] = None,
        format_with_llm: bool = True,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Link a job description to a CompanyRole via API.

        Args:
            company_role_id: CompanyRole ID
            jd_content: Job description content
            jd_title: Optional JD title
            format_with_llm: Whether to format JD with LLM
            source: Source identifier

        Returns:
            Dict with linking status
        """
        logger.info(f"Linking JD to CompanyRole via API: {company_role_id}")

        payload = {
            "company_role_id": company_role_id,
            "jd_content": jd_content,
            "format_with_llm": format_with_llm,
        }
        if jd_title:
            payload["jd_title"] = jd_title
        if source:
            payload["source"] = source

        result = self._request(
            "POST",
            "/api/automated_workflows/link-job-description",
            data=payload,
        )

        if result.get("status") == "error":
            raise Exception(f"Failed to link JD: {result.get('message')}")

        logger.info(f"Linked JD to CompanyRole: {company_role_id}, linked={result.get('jd_linked')}")
        return result

    def run_ai_assessment(
        self,
        company_name: str,
        role_name: str,
        company_role_id: Optional[str] = None,
        delete_existing: bool = False,
        store_in_neo4j: bool = True,
    ) -> Dict[str, Any]:
        """
        Run AI Assessment workflow via API.

        Args:
            company_name: Company name
            role_name: Role name
            company_role_id: Optional CompanyRole ID
            delete_existing: Delete existing assessment first
            store_in_neo4j: Store results in Neo4j database

        Returns:
            Dict with assessment results
        """
        # Ensure store_in_neo4j defaults to True even if explicitly passed as None
        if store_in_neo4j is None:
            store_in_neo4j = True

        logger.info(f"Running AI Assessment via API: {company_name} - {role_name}")

        payload = {
            "company_name": company_name,
            "role_name": role_name,
            "delete_existing": delete_existing,
            "store_in_neo4j": store_in_neo4j,
        }
        if company_role_id:
            payload["company_role_id"] = company_role_id

        result = self._request(
            "POST",
            "/api/automated_workflows/run-ai-assessment",
            data=payload,
        )

        if result.get("status") == "error":
            raise Exception(f"AI Assessment failed: {result.get('message')}")

        logger.info(
            f"AI Assessment completed: {company_name} - {role_name}, "
            f"score={result.get('ai_automation_score')}"
        )
        return result

    def get_company_role(self, company_role_id: str) -> Dict[str, Any]:
        """
        Get CompanyRole details by ID.

        Args:
            company_role_id: CompanyRole ID

        Returns:
            Dict with company role details
        """
        logger.info(f"Getting CompanyRole via API: {company_role_id}")

        result = self._request(
            "GET",
            f"/api/automated_workflows/company-role/{company_role_id}",
        )

        if result.get("status") == "error":
            raise Exception(f"Failed to get CompanyRole: {result.get('message')}")

        return result

    def health_check(self) -> Dict[str, Any]:
        """
        Health check for the automated workflows API.

        Returns:
            Health status
        """
        result = self._request("GET", "/api/automated_workflows/health")
        return result

    def close(self):
        """Close HTTP session."""
        if self._session:
            if hasattr(self._session, 'close'):
                self._session.close()
            self._session = None


# Singleton client instance
_automated_workflows_client: Optional[AutomatedWorkflowsClient] = None


def get_automated_workflows_client() -> AutomatedWorkflowsClient:
    """
    Get the singleton Automated Workflows API client instance.

    Returns:
        AutomatedWorkflowsClient instance
    """
    global _automated_workflows_client
    if _automated_workflows_client is None:
        _automated_workflows_client = AutomatedWorkflowsClient()
    return _automated_workflows_client


def reset_automated_workflows_client():
    """Reset the singleton client (for testing)."""
    global _automated_workflows_client
    if _automated_workflows_client:
        _automated_workflows_client.close()
    _automated_workflows_client = None
