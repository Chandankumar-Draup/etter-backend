"""
Clients package for Etter Workflows.

Contains clients for external services:
- neo4j_client: Graph database operations
- llm_client: LLM service (ModelManager integration)
- status_client: Status update service (Redis)
- workflow_api_client: Existing workflow API client
- automated_workflows_client: Automated Workflows API client (localhost:8083)
"""

from etter_workflows.clients.neo4j_client import Neo4jClient, get_neo4j_client
from etter_workflows.clients.llm_client import LLMClient, get_llm_client
from etter_workflows.clients.status_client import StatusClient, get_status_client
from etter_workflows.clients.workflow_api_client import WorkflowAPIClient, get_workflow_api_client
from etter_workflows.clients.automated_workflows_client import (
    AutomatedWorkflowsClient,
    get_automated_workflows_client,
)

__all__ = [
    "Neo4jClient",
    "get_neo4j_client",
    "LLMClient",
    "get_llm_client",
    "StatusClient",
    "get_status_client",
    "WorkflowAPIClient",
    "get_workflow_api_client",
    "AutomatedWorkflowsClient",
    "get_automated_workflows_client",
]
