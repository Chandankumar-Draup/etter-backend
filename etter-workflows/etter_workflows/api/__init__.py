"""
API package for Etter Workflows.

Provides FastAPI routes for:
- Pipeline push endpoint
- Status query endpoint
- Health check endpoint

API Endpoints (from implementation plan):
- POST /api/v1/pipeline/push - Start role onboarding workflow
- GET /api/v1/pipeline/status/{workflow_id} - Get workflow status
- POST /api/v1/pipeline/retry/{workflow_id} - Retry failed workflow (P1)
- POST /api/v1/pipeline/batch - Start batch processing (P1)
"""

from etter_workflows.api.routes import router, create_app, get_app
from etter_workflows.api.schemas import (
    PushRequest,
    PushResponse,
    StatusResponse,
    ErrorResponse,
)

__all__ = [
    "router",
    "create_app",
    "get_app",
    "PushRequest",
    "PushResponse",
    "StatusResponse",
    "ErrorResponse",
]
