"""
S3 Document Management Module

This module provides a complete document upload and access management system
with S3 storage backend.

Phase 1 Endpoints:
- POST /s3/uploads/initiate - Initiate upload session
- POST /s3/uploads/{session_id}/data - Upload file data
- POST /s3/uploads/complete - Complete upload
- DELETE /s3/uploads/{document_id} - Abort upload
- GET /s3/documents/{id} - Get document with optional download URL
- DELETE /s3/documents/{id} - Delete document
- GET /s3/documents - List documents
- HEAD /s3/documents/{id} - Probe document
- POST /s3/documents/{id}/quarantine - Quarantine document (admin)
- POST /s3/documents/{id}/approve - Approve document (admin)
"""

from api.s3.router import s3_router

__all__ = ["s3_router"]

