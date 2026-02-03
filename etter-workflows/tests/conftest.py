"""
Pytest configuration and shared fixtures for Etter Workflows tests.

This file provides:
- Common fixtures for API testing
- Mock clients for Redis, Neo4j
- Test data generators
"""

import pytest
from datetime import datetime
from typing import Generator
from unittest.mock import patch, MagicMock

# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def api_client() -> Generator:
    """Create FastAPI test client for the session."""
    from fastapi.testclient import TestClient
    from etter_workflows.api.routes import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(api_client):
    """Alias for api_client fixture."""
    return api_client


# ============================================================================
# Mock Client Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis status client."""
    with patch("etter_workflows.clients.status_client.get_status_client") as mock:
        mock_client = MagicMock()
        mock_client.get_status.return_value = None
        mock_client.set_status.return_value = True
        mock_client.update_state.return_value = True
        mock_client.update_progress.return_value = True
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j client."""
    with patch("etter_workflows.clients.neo4j_client.get_neo4j_client") as mock:
        mock_client = MagicMock()
        mock_client.create_company_role.return_value = "test_company_role_id"
        mock_client.link_job_description.return_value = True
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    with patch("etter_workflows.clients.llm_client.get_llm_client") as mock:
        mock_client = MagicMock()
        mock_client.format_job_description.return_value = "Formatted JD content"
        mock.return_value = mock_client
        yield mock_client


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_company():
    """Sample company name."""
    return "TestCompany"


@pytest.fixture
def sample_role():
    """Sample role name."""
    return "Test Engineer"


@pytest.fixture
def sample_workflow_id():
    """Sample workflow ID."""
    return "test-workflow-12345678"


@pytest.fixture
def sample_push_request(sample_company, sample_role):
    """Sample push request payload."""
    return {
        "company_id": sample_company,
        "role_name": sample_role,
        "documents": [],
        "draup_role_id": None,
        "draup_role_name": sample_role,
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        }
    }


@pytest.fixture
def sample_role_taxonomy(sample_company, sample_role):
    """Register sample role taxonomy data."""
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.models.inputs import RoleTaxonomyEntry

    provider = get_role_taxonomy_provider()
    entry = RoleTaxonomyEntry(
        job_id=f"test-{sample_role.lower().replace(' ', '-')}-001",
        job_role=sample_role,
        job_title=sample_role,
        draup_role=sample_role,
        general_summary=f"Test role: {sample_role}",
    )
    provider.add_role(sample_company, entry)
    return entry


@pytest.fixture
def sample_document(sample_company, sample_role):
    """Register sample document."""
    from etter_workflows.mock_data.documents import get_document_provider
    from etter_workflows.models.inputs import DocumentRef, DocumentType

    provider = get_document_provider()
    doc = DocumentRef(
        type=DocumentType.JOB_DESCRIPTION,
        name=f"{sample_role} JD",
        content=f"Job description for {sample_role} at {sample_company}",
    )
    provider.add_document(sample_company, sample_role, doc)
    return doc


@pytest.fixture
def sample_workflow_status(sample_workflow_id, sample_company, sample_role):
    """Create sample workflow status."""
    from etter_workflows.models.status import (
        RoleStatus, WorkflowState, ProgressInfo
    )

    return RoleStatus(
        workflow_id=sample_workflow_id,
        company_id=sample_company,
        role_name=sample_role,
        state=WorkflowState.PROCESSING,
        progress=ProgressInfo.create_for_workflow(["role_setup", "ai_assessment"]),
        queued_at=datetime.utcnow(),
    )


@pytest.fixture
def registered_test_data(sample_role_taxonomy, sample_document):
    """Ensure test data is registered (combines taxonomy and document fixtures)."""
    return {
        "taxonomy": sample_role_taxonomy,
        "document": sample_document,
    }


# ============================================================================
# Event Loop Fixture (for async tests)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_mock_data():
    """Clean up mock data after each test."""
    yield
    # No cleanup needed - mock data is in-memory and reset per session


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
