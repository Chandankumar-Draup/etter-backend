from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
import logging

from api.s3.dependencies import get_auth_context, get_uow, get_s3_service, AuthContext
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.domain.services.document_custodian import DocumentCustodian
from api.s3.schemas.documents import (
    DocumentResponse,
    DocumentWithDownloadResponse,
    DeleteDocumentResponse
)
from api.s3.domain.policies import AuthorizationPolicy

logger = logging.getLogger(__name__)

documents_router = APIRouter(prefix="/documents", tags=["S3 Documents"])


@documents_router.get("/{document_id}", response_model=DocumentWithDownloadResponse, status_code=status.HTTP_200_OK)
async def get_document(
    document_id: UUID,
    generate_download_url: bool = Query(False, description="Generate presigned download URL"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Get document metadata and optionally a presigned download URL.
    
    Returns document details including status, size, content type, and timestamps.
    If generate_download_url is True, includes a presigned URL valid for 5 minutes.
    
    - **document_id**: The document ID to retrieve
    - **generate_download_url**: Whether to include a presigned download URL
    """
    try:
        custodian = DocumentCustodian(uow, s3_service)
        
        response = custodian.get_document(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            generate_download_url=generate_download_url
        )
        
        # Additional authorization check
        document = uow.documents.get_by_id(document_id, auth.tenant_id)
        if generate_download_url and document:
            if not AuthorizationPolicy.can_download_document(document, auth.tenant_id, auth.group):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Document is not available for download"
                )
        
        logger.info(
            f"Document retrieved: document_id={document_id}, "
            f"tenant_id={auth.tenant_id}, download_url={generate_download_url}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Error retrieving document: {str(e)}")
        if "not found" in str(e).lower() or "deleted" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "quarantined" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@documents_router.delete("/{document_id}", response_model=DeleteDocumentResponse, status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: UUID,
    admin_override: bool = Query(False, description="Admin override for legal hold"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Delete a document (hard delete from S3 and mark as deleted in DB).
    
    Performs a hard delete, removing the object from S3 storage.
    If the document has a legal hold, only admins can delete with admin_override=True.
    
    - **document_id**: The document ID to delete
    - **admin_override**: Admin override for legal hold (requires admin role)
    """
    try:
        # Check admin override authorization
        if admin_override and not auth.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required for admin_override"
            )
        
        # Check if document exists and user has permission
        document = uow.documents.get_by_id(document_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        if not AuthorizationPolicy.can_delete_document(document, auth.tenant_id, auth.group, auth.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this document"
            )
        
        custodian = DocumentCustodian(uow, s3_service)
        
        response = custodian.delete_document(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
            admin_override=admin_override
        )
        
        logger.info(
            f"Document deleted: document_id={document_id}, "
            f"tenant_id={auth.tenant_id}, admin_override={admin_override}"
        )
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "legal hold" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@documents_router.get("/", status_code=status.HTTP_200_OK)
async def list_documents(
    role: Optional[str] = Query(None, description="Filter by document role"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by document status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    List documents for the current tenant.
    
    Returns a paginated list of documents with optional filtering.
    
    - **role**: Filter by document role/category
    - **status**: Filter by document status (planned, uploaded, ready, deleted, quarantine, aborted)
    - **limit**: Maximum number of documents to return (1-1000)
    - **offset**: Number of documents to skip for pagination
    """
    try:
        from models.s3 import DocumentStatus
        
        # Validate status filter
        status_enum = None
        if status_filter:
            try:
                status_enum = DocumentStatus[status_filter.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Valid values: planned, uploaded, ready, deleted, quarantine, aborted"
                )
        
        documents = uow.documents.list_by_tenant(
            tenant_id=auth.tenant_id,
            role=role,
            status=status_enum,
            limit=limit,
            offset=offset
        )
        
        document_responses = [
            DocumentResponse.model_validate(doc) for doc in documents
        ]
        
        logger.info(
            f"Documents listed: tenant_id={auth.tenant_id}, "
            f"role={role}, status={status_filter}, count={len(documents)}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": {
                    "documents": [doc.model_dump(mode='json') for doc in document_responses],
                    "count": len(documents),
                    "limit": limit,
                    "offset": offset
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )


@documents_router.head("/{document_id}", status_code=status.HTTP_200_OK)
async def probe_document(
    document_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    Probe document existence and status (lightweight check).
    
    Returns only HTTP status and minimal headers, useful for checking if a document exists
    without retrieving full metadata.
    
    - **document_id**: The document ID to probe
    
    Returns:
    - 200 OK if document exists and is accessible
    - 404 Not Found if document doesn't exist or is deleted
    - 423 Locked if document is quarantined
    """
    try:
        document = uow.documents.get_by_id(document_id, auth.tenant_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        from models.s3 import DocumentStatus
        
        if document.status == DocumentStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document has been deleted"
            )
        
        if document.status == DocumentStatus.QUARANTINE:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Document is quarantined"
            )
        
        # Return empty response with headers
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=None,
            headers={
                "X-Document-Status": document.status.value,
                "X-Document-Size": str(document.observed_size_bytes or 0),
                "X-Content-Type": document.observed_content_type or ""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error probing document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to probe document"
        )


# Admin-only endpoints for quarantine management
@documents_router.post("/{document_id}/quarantine", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def quarantine_document(
    document_id: UUID,
    reason: Optional[str] = Query(None, description="Reason for quarantine"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Quarantine a document (admin only).
    
    Quarantined documents cannot be downloaded until approved.
    
    - **document_id**: The document ID to quarantine
    - **reason**: Optional reason for quarantine
    """
    if not auth.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to quarantine documents"
        )
    
    try:
        custodian = DocumentCustodian(uow, s3_service)
        
        response = custodian.quarantine_document(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
            reason=reason
        )
        
        logger.info(
            f"Document quarantined: document_id={document_id}, "
            f"tenant_id={auth.tenant_id}, reason={reason}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Error quarantining document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error quarantining document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to quarantine document"
        )


@documents_router.post("/{document_id}/approve", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def approve_document(
    document_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Approve a quarantined document (admin only).
    
    Releases the document from quarantine and makes it available for download.
    
    - **document_id**: The document ID to approve
    """
    if not auth.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to approve documents"
        )
    
    try:
        custodian = DocumentCustodian(uow, s3_service)
        
        response = custodian.approve_document(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )
        
        logger.info(
            f"Document approved: document_id={document_id}, tenant_id={auth.tenant_id}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Error approving document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error approving document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve document"
        )

