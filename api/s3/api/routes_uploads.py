from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form, status
from fastapi.responses import JSONResponse
import logging
import json
from typing import Optional, Dict
from io import BytesIO
from datetime import datetime

from api.s3.dependencies import get_auth_context, get_uow, get_s3_service, AuthContext
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.domain.services.upload_coordinator import UploadCoordinator
from api.s3.schemas.uploads import (
    InitiateUploadRequest,
    InitiateUploadResponse,
    UploadPartResponse,
    CompleteUploadRequest,
    CompleteUploadResponse,
    CombinedUploadResponse
)
from models.s3 import UploadModeV2
from api.s3.config import s3_config

logger = logging.getLogger(__name__)

uploads_router = APIRouter(prefix="/uploads", tags=["S3 Document Uploads"])


@uploads_router.post("/initiate", response_model=InitiateUploadResponse, status_code=status.HTTP_200_OK)
async def initiate_upload(
    request: InitiateUploadRequest,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Initiate a document upload session (role-based mode for legacy flows).

    Determines whether to use single-part or multipart upload based on file size.
    Returns a session_id and upload parameters.
    This endpoint uses role-based mode for backward compatibility with existing flows.

    - **original_filename**: Name of the file to upload
    - **content_type**: MIME type of the file
    - **declared_size_bytes**: Size of the file in bytes
    - **role**: Document role/category
    - **custom_metadata**: Optional custom metadata
    - **idempotency_key**: Optional idempotency key for duplicate prevention
    """
    try:
        # Validate role is provided for role-based uploads
        if not request.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="role is required for role-based uploads"
            )

        coordinator = UploadCoordinator(uow, s3_service)

        response = coordinator.plan_upload(
            request=request,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
            mode=UploadModeV2.ROLE_BASED,
            folder_path=None,
            company_instance_name=request.company_instance_name
        )
        
        logger.info(
            f"Upload initiated: document_id={response.document_id}, "
            f"mode={response.mode}, tenant_id={auth.tenant_id}, user_id={auth.user_id}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error during upload initiation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error initiating upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate upload"
        )


@uploads_router.post("/{session_id}/data", status_code=status.HTTP_202_ACCEPTED)
async def upload_data(
    session_id: UUID,
    file: UploadFile = File(...),
    part_number: int = Query(None, ge=1, le=10000),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Upload file data for a session.
    
    For single-part uploads: Upload the entire file (no part_number needed).
    For multipart uploads: Upload a specific part (requires part_number).
    
    - **session_id**: The session ID returned from /initiate
    - **file**: The file data to upload
    - **part_number**: Part number (required for multipart uploads)
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)
        
        # Check if document exists and get mode
        document = uow.documents.get_by_id(session_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {session_id} not found"
            )
        
        if document.mode.value == "single":
            # Single-part upload
            if part_number is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="part_number should not be provided for single-part uploads"
                )
            
            coordinator.stream_single(
                document_id=session_id,
                tenant_id=auth.tenant_id,
                fileobj=file.file,
                user_id=auth.user_id
            )
            
            logger.info(f"Single upload completed: document_id={session_id}")
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "uploaded",
                    "document_id": str(session_id),
                    "message": "File uploaded successfully. Call /uploads/complete to finalize."
                }
            )
        
        elif document.mode.value == "multipart":
            # Multipart upload
            if part_number is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="part_number is required for multipart uploads"
                )
            
            result = coordinator.upload_part(
                document_id=session_id,
                tenant_id=auth.tenant_id,
                part_number=part_number,
                data=file.file,
                user_id=auth.user_id
            )
            
            logger.info(f"Part uploaded: document_id={session_id}, part={part_number}")
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "part_uploaded",
                    "document_id": str(result.document_id),
                    "part_number": result.part_number,
                    "etag": result.etag
                }
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown upload mode: {document.mode}"
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during data upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload data"
        )


@uploads_router.post("/complete", response_model=CompleteUploadResponse, status_code=status.HTTP_200_OK)
async def complete_upload(
    request: CompleteUploadRequest,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Complete an upload session and finalize the document.
    
    Performs verification checks and transitions the document to 'ready' state.
    
    - **document_id**: The document ID to complete
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)
        
        response = coordinator.complete_upload(
            document_id=request.document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )
        
        logger.info(
            f"Upload completed: document_id={request.document_id}, "
            f"tenant_id={auth.tenant_id}, size={response.verification.get('size')}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error during upload completion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error completing upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload"
        )


@uploads_router.post("/upload", response_model=CombinedUploadResponse, status_code=status.HTTP_200_OK)
async def combined_upload(
    file: UploadFile = File(...),
    role: str = Form(...),
    custom_metadata: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    company_instance_name: Optional[str] = Form(None),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Combined upload endpoint that handles initiate, upload, and complete in a single request.
    
    This endpoint simplifies the upload process for smaller files by combining all three steps.
    For files larger than the single-part upload limit, use the multi-step process.
    
    - **file**: The file to upload
    - **role**: Document role/category
    - **custom_metadata**: Optional custom metadata (JSON string)
    - **idempotency_key**: Optional idempotency key for duplicate prevention
    - **company_instance_name**: Optional company instance name for filtering
    """
    try:
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > s3_config.max_single_upload_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size ({file_size} bytes) exceeds single-part upload limit ({s3_config.max_single_upload_size} bytes). Please use the multi-step upload process."
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size cannot be zero"
            )
        
        parsed_metadata: Optional[Dict[str, str]] = None
        if custom_metadata:
            try:
                parsed_metadata = json.loads(custom_metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="custom_metadata must be a valid JSON string"
                )
        
        coordinator = UploadCoordinator(uow, s3_service)
        
        initiate_request = InitiateUploadRequest(
            original_filename=file.filename or "unknown",
            content_type=file.content_type,
            declared_size_bytes=file_size,
            role=role,
            custom_metadata=parsed_metadata,
            idempotency_key=idempotency_key,
            company_instance_name=company_instance_name
        )
        
        initiate_response = coordinator.plan_upload(
            request=initiate_request,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
            mode=UploadModeV2.ROLE_BASED,
            folder_path=None,
            company_instance_name=company_instance_name
        )
        
        document_id = initiate_response.document_id
        
        file_obj = BytesIO(file_content)
        
        if initiate_response.upload_strategy == "SINGLE":
            coordinator.stream_single(
                document_id=document_id,
                tenant_id=auth.tenant_id,
                fileobj=file_obj,
                user_id=auth.user_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected multipart mode for combined upload"
            )
        
        complete_response = coordinator.complete_upload(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )
        
        logger.info(
            f"Combined upload completed: document_id={document_id}, "
            f"tenant_id={auth.tenant_id}, size={complete_response.verification.get('size')}"
        )
        
        return CombinedUploadResponse(
            status=complete_response.status,
            document_id=complete_response.document_id,
            verification=complete_response.verification,
            completed_at=complete_response.completed_at,
            mode="single"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during combined upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in combined upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload"
        )


@uploads_router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def abort_upload(
    document_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Abort an in-progress upload.
    
    Cancels multipart upload if applicable and marks the document as aborted.
    
    - **document_id**: The document ID to abort
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)
        
        coordinator.abort_upload(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )
        
        logger.info(f"Upload aborted: document_id={document_id}, tenant_id={auth.tenant_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "aborted",
                "document_id": str(document_id),
                "message": "Upload aborted successfully"
            }
        )
        
    except ValueError as e:
        logger.error(f"Error aborting upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error aborting upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort upload"
        )

