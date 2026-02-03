"""
Chatbot API Router

Handles chatbot query requests with optional S3 document integration.
Enriches requests with S3 document metadata before forwarding to workflow engine.
"""

import logging
import os
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import requests

from api.s3.dependencies import get_auth_context, get_uow, get_s3_service, AuthContext
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.domain.services.document_custodian import DocumentCustodian
from api.etter_apis import get_draup_world_api, get_token

logger = logging.getLogger(__name__)

chatbot_router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# Configuration
DRAUP_WORLD_MODEL_BASE_URL = get_draup_world_api()
CHATBOT_QUERY_ENDPOINT = f"{DRAUP_WORLD_MODEL_BASE_URL}/query"
TIMEOUT_SECONDS = 300  # 5 minutes for long-running workflows


class ChatbotQueryRequest(BaseModel):
    """Request model for chatbot queries."""
    query: str = Field(..., description="User query text", min_length=1)
    document_id: Optional[UUID] = Field(None, description="Optional document ID to use as job description")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    model: Optional[str] = Field(None, description="LLM model to use")
    stream_answers: bool = Field(True, description="Enable streaming responses")
    selected_steps: Optional[list] = Field(None, description="Optional list of workflow steps to execute")


@chatbot_router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Download S3 file by document ID.
    
    Streams the file directly from S3 to the client.
    
    Args:
        document_id: The document ID to download
        auth: Authentication context
        uow: Unit of work for database operations
        s3_service: S3 management service
        
    Returns:
        Streaming response with file content
    """
    try:
        from api.s3.domain.policies import AuthorizationPolicy
        from models.s3 import DocumentStatus
        
        document = uow.documents.get_by_id(document_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document.status == DocumentStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document has been deleted"
            )
        
        if not AuthorizationPolicy.can_download_document(document, auth.tenant_id, auth.group):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document is not available for download"
            )
        
        try:
            file_stream = s3_service.get_object_stream(document.key)
            
            content_type = document.observed_content_type or "application/octet-stream"
            filename = document.original_filename or f"document_{document_id}"
            
            logger.info(
                f"Downloading document: document_id={document_id}, "
                f"filename={filename}, tenant_id={auth.tenant_id}"
            )
            
            return StreamingResponse(
                file_stream.iter_chunks(chunk_size=8192),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        except Exception as e:
            logger.error(f"Error streaming file from S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download file"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@chatbot_router.post("/query")
async def query_chatbot(
    query_request: ChatbotQueryRequest,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Process a chatbot query with optional S3 document integration.

    If document_id is provided:
    1. Fetches document metadata and generates pre-signed download URL
    2. Enriches request with document data
    3. Forwards to draup_world_model_graph for workflow execution

    If document_id is not provided:
    1. Forwards query directly to draup_world_model_graph

    Args:
        query_request: Chatbot query request
        request: FastAPI request object for accessing headers
        auth: Authentication context
        uow: Unit of work for database operations
        s3_service: S3 management service

    Returns:
        Streaming response from workflow engine
    """
    try:
        # Prepare request payload for draup_world_model_graph
        payload = {
            "query": query_request.query,
            "session_id": query_request.session_id,
            "model": query_request.model,
            "stream_answers": query_request.stream_answers,
            "selected_steps": query_request.selected_steps
        }

        # NEW: If document_id is provided, fetch S3 document metadata
        if query_request.document_id:
            logger.info(f"Fetching S3 document metadata for document_id={query_request.document_id}")

            try:
                # Get document with pre-signed download URL
                custodian = DocumentCustodian(uow, s3_service)
                document_response = custodian.get_document(
                    document_id=query_request.document_id,
                    tenant_id=auth.tenant_id,
                    generate_download_url=True
                )

                # Validate document is ready for download
                if not document_response.download or not document_response.download.url:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Document is not available for download"
                    )

                # Add S3 document data to payload
                payload["s3_document_data"] = {
                    "document_id": str(query_request.document_id),
                    "original_filename": document_response.document.original_filename,
                    "observed_content_type": document_response.document.observed_content_type,
                    "download_url": document_response.download.url,
                    "expires_in": document_response.download.expires_in
                }

                logger.info(
                    f"Enriched request with S3 document: "
                    f"filename={document_response.document.original_filename}, "
                    f"content_type={document_response.document.observed_content_type}"
                )

            except ValueError as e:
                # Document not found or not accessible
                logger.error(f"Error fetching document: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document not found or not accessible: {str(e)}"
                )

        # Get authentication token for draup_world_model_graph
        # Use the same authentication pattern as other etter-backend APIs
        token = get_token()
        if not token:
            logger.error("Failed to obtain auth token for draup_world_model_graph")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain authentication token for workflow engine"
            )

        # Prepare headers for forwarding to draup_world_model_graph
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {token}',
            'Origin': 'https://draup-world.draup.technology'
        }

        logger.debug("Successfully obtained auth token for workflow engine")
        # Forward request to draup_world_model_graph
        logger.info(f"Forwarding chatbot query to {CHATBOT_QUERY_ENDPOINT}")

        response = requests.post(
            CHATBOT_QUERY_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            stream=query_request.stream_answers
        )

        # Check response status
        if response.status_code != 200:
            logger.error(
                f"Workflow engine returned error: "
                f"status={response.status_code}, body={response.text[:500]}"
            )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Workflow engine error: {response.text}"
            )

        # Return streaming response
        if query_request.stream_answers:
            return StreamingResponse(
                response.iter_content(chunk_size=8192),
                media_type="text/event-stream"
            )
        else:
            return response.json()

    except HTTPException:
        raise
    except requests.Timeout:
        logger.error(f"Timeout calling workflow engine after {TIMEOUT_SECONDS}s")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Workflow engine timeout"
        )
    except requests.RequestException as e:
        logger.error(f"Error calling workflow engine: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with workflow engine: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in chatbot query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
