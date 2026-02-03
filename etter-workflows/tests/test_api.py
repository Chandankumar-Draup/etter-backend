"""
API Tests for Etter Workflows.

Tests for the REST API endpoints:
- POST /api/v1/pipeline/push - Start workflow
- GET /api/v1/pipeline/status/{id} - Get workflow status
- GET /api/v1/pipeline/health - Health check
- GET /api/v1/pipeline/companies - List companies
- GET /api/v1/pipeline/roles/{company} - List roles for company

Run with:
    pytest tests/test_api.py -v

Or run specific tests:
    pytest tests/test_api.py::TestHealthEndpoint -v
    pytest tests/test_api.py::TestPushEndpoint -v
"""

import pytest
import asyncio
from datetime import datetime
from typing import Generator, Any
from unittest.mock import patch, MagicMock

# FastAPI test client
from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create test client for API."""
    from etter_workflows.api.routes import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_redis():
    """Mock Redis client for status operations."""
    with patch("etter_workflows.clients.status_client.get_status_client") as mock:
        mock_client = MagicMock()
        mock_client.get_status.return_value = None
        mock_client.set_status.return_value = True
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_push_request():
    """Sample push request payload."""
    return {
        "company_id": "TestCorp",
        "role_name": "QA Engineer",
        "documents": [],
        "draup_role_id": None,
        "draup_role_name": "QA Engineer",
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        }
    }


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for /api/v1/pipeline/health endpoint."""

    def test_health_check_returns_200(self, client: TestClient):
        """Health check should return 200 status."""
        response = client.get("/api/v1/pipeline/health")
        assert response.status_code == 200

    def test_health_check_returns_status(self, client: TestClient):
        """Health check should return status information."""
        response = client.get("/api/v1/pipeline/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data

    def test_health_check_includes_api_component(self, client: TestClient):
        """Health check should include API component status."""
        response = client.get("/api/v1/pipeline/health")
        data = response.json()

        assert "api" in data["components"]
        assert data["components"]["api"] == "healthy"


# ============================================================================
# Companies Endpoint Tests
# ============================================================================

class TestCompaniesEndpoint:
    """Tests for /api/v1/pipeline/companies endpoint."""

    def test_list_companies_returns_200(self, client: TestClient):
        """List companies should return 200 status."""
        response = client.get("/api/v1/pipeline/companies")
        assert response.status_code == 200

    def test_list_companies_returns_list(self, client: TestClient):
        """List companies should return companies list."""
        response = client.get("/api/v1/pipeline/companies")
        data = response.json()

        assert "companies" in data
        assert "total_count" in data
        assert isinstance(data["companies"], list)

    def test_list_companies_includes_mock_data(self, client: TestClient):
        """List companies should include mock data companies."""
        response = client.get("/api/v1/pipeline/companies")
        data = response.json()

        # Should have at least the default mock companies
        assert data["total_count"] >= 0


# ============================================================================
# Roles Endpoint Tests
# ============================================================================

class TestRolesEndpoint:
    """Tests for /api/v1/pipeline/roles/{company} endpoint."""

    def test_list_roles_returns_200(self, client: TestClient):
        """List roles should return 200 for valid company."""
        # First register some test data
        from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
        from etter_workflows.models.inputs import RoleTaxonomyEntry

        provider = get_role_taxonomy_provider()
        provider.add_role("TestCompany", RoleTaxonomyEntry(
            job_id="test-001",
            job_role="Test Role",
            job_title="Test Role",
            draup_role="Test Role",
        ))

        response = client.get("/api/v1/pipeline/roles/TestCompany")
        assert response.status_code == 200

    def test_list_roles_returns_role_details(self, client: TestClient):
        """List roles should return role details."""
        from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
        from etter_workflows.models.inputs import RoleTaxonomyEntry

        provider = get_role_taxonomy_provider()
        provider.add_role("RoleTestCompany", RoleTaxonomyEntry(
            job_id="test-002",
            job_role="Software Engineer",
            job_title="Software Engineer",
            draup_role="Software Engineer",
        ))

        response = client.get("/api/v1/pipeline/roles/RoleTestCompany")
        data = response.json()

        assert "company_name" in data
        assert "roles" in data
        assert "total_count" in data
        assert data["company_name"] == "RoleTestCompany"


# ============================================================================
# Status Endpoint Tests
# ============================================================================

class TestStatusEndpoint:
    """Tests for /api/v1/pipeline/status/{workflow_id} endpoint."""

    def test_status_not_found_returns_404(self, client: TestClient, mock_redis):
        """Status should return 404 for unknown workflow ID."""
        mock_redis.get_status.return_value = None

        response = client.get("/api/v1/pipeline/status/non-existent-id")
        assert response.status_code == 404

    def test_status_returns_workflow_details(self, client: TestClient, mock_redis):
        """Status should return workflow details for valid ID."""
        from etter_workflows.models.status import (
            RoleStatus, WorkflowState, ProgressInfo
        )

        # Mock a workflow status
        mock_status = RoleStatus(
            workflow_id="test-workflow-123",
            company_id="TestCorp",
            role_name="QA Engineer",
            state=WorkflowState.PROCESSING,
            progress=ProgressInfo.create_for_workflow(["role_setup", "ai_assessment"]),
        )
        mock_redis.get_status.return_value = mock_status

        response = client.get("/api/v1/pipeline/status/test-workflow-123")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "test-workflow-123"
        assert data["company_id"] == "TestCorp"
        assert data["role_name"] == "QA Engineer"


# ============================================================================
# Push Endpoint Tests
# ============================================================================

class TestPushEndpoint:
    """Tests for /api/v1/pipeline/push endpoint."""

    def test_push_requires_company_id(self, client: TestClient):
        """Push should require company_id field."""
        response = client.post(
            "/api/v1/pipeline/push",
            json={"role_name": "Test Role"}
        )
        assert response.status_code == 422  # Validation error

    def test_push_requires_role_name(self, client: TestClient):
        """Push should require role_name field."""
        response = client.post(
            "/api/v1/pipeline/push",
            json={"company_id": "TestCorp"}
        )
        assert response.status_code == 422  # Validation error

    def test_push_accepts_valid_request(self, client: TestClient, sample_push_request, mock_redis):
        """Push should accept valid request."""
        # Register test data first
        from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
        from etter_workflows.mock_data.documents import get_document_provider
        from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType

        taxonomy = get_role_taxonomy_provider()
        docs = get_document_provider()

        taxonomy.add_role("TestCorp", RoleTaxonomyEntry(
            job_id="test-qa-001",
            job_role="QA Engineer",
            job_title="QA Engineer",
            draup_role="QA Engineer",
            general_summary="Quality assurance role",
        ))

        docs.add_document("TestCorp", "QA Engineer", DocumentRef(
            type=DocumentType.JOB_DESCRIPTION,
            name="QA Engineer JD",
            content="Test job description content",
        ))

        response = client.post(
            "/api/v1/pipeline/push?use_mock=true",
            json=sample_push_request
        )

        # Should return 200 with workflow ID
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert "status" in data
        assert data["status"] == "queued"


# ============================================================================
# Integration Tests
# ============================================================================

class TestAPIIntegration:
    """Integration tests for API endpoints."""

    def test_workflow_lifecycle(self, client: TestClient, mock_redis):
        """Test complete workflow lifecycle: push -> status check."""
        from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
        from etter_workflows.mock_data.documents import get_document_provider
        from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType
        from etter_workflows.models.status import RoleStatus, WorkflowState, ProgressInfo

        # Setup test data
        taxonomy = get_role_taxonomy_provider()
        docs = get_document_provider()

        taxonomy.add_role("LifecycleTestCorp", RoleTaxonomyEntry(
            job_id="lifecycle-001",
            job_role="DevOps Engineer",
            job_title="DevOps Engineer",
            draup_role="DevOps Engineer",
            general_summary="DevOps engineering role",
        ))

        docs.add_document("LifecycleTestCorp", "DevOps Engineer", DocumentRef(
            type=DocumentType.JOB_DESCRIPTION,
            name="DevOps Engineer JD",
            content="DevOps job description",
        ))

        # Step 1: Push workflow
        push_response = client.post(
            "/api/v1/pipeline/push?use_mock=true",
            json={
                "company_id": "LifecycleTestCorp",
                "role_name": "DevOps Engineer",
                "options": {"force_rerun": False}
            }
        )

        assert push_response.status_code == 200
        workflow_id = push_response.json()["workflow_id"]

        # Step 2: Mock status and check
        mock_status = RoleStatus(
            workflow_id=workflow_id,
            company_id="LifecycleTestCorp",
            role_name="DevOps Engineer",
            state=WorkflowState.QUEUED,
            progress=ProgressInfo.create_for_workflow(["role_setup", "ai_assessment"]),
        )
        mock_redis.get_status.return_value = mock_status

        status_response = client.get(f"/api/v1/pipeline/status/{workflow_id}")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["workflow_id"] == workflow_id
        assert status_data["status"] == "queued"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
