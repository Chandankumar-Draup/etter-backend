"""
Main router for S3 Document Management API.

This module combines all S3 document management routes into a single router
that can be included in the main FastAPI application.
"""
from fastapi import APIRouter

from api.s3.api.routes_uploads import uploads_router
from api.s3.api.routes_documents import documents_router
from api.s3.api.routes_filesystem import filesystem_router

# Create main S3 router
s3_router = APIRouter(prefix="/s3", tags=["S3 Documents"])

# Include sub-routers
s3_router.include_router(uploads_router)
s3_router.include_router(documents_router)
s3_router.include_router(filesystem_router)

__all__ = ["s3_router", "uploads_router", "documents_router", "filesystem_router"]

