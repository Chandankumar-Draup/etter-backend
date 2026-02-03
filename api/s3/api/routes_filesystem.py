from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional, List
from uuid import UUID
import logging

from api.s3.dependencies import get_auth_context, get_uow, get_s3_service, AuthContext
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.domain.services.filesystem_service import FilesystemService
from api.s3.domain.services.upload_coordinator import UploadCoordinator
from api.s3.schemas.filesystem import (
    CreateFolderRequest,
    FilesystemUploadRequest,
    ListFolderResponse
)
from api.s3.schemas.uploads import (
    InitiateUploadRequest,
    InitiateUploadResponse,
    CompleteUploadRequest,
    CompleteUploadResponse
)
from api.s3.schemas.documents import DocumentResponse
from models.s3 import UploadModeV2

logger = logging.getLogger(__name__)

filesystem_router = APIRouter(prefix="/s3/filesystem", tags=["File System"])


@filesystem_router.get("/folders", response_model=ListFolderResponse, status_code=status.HTTP_200_OK)
async def list_folder(
    path: Optional[str] = Query(None, description="Parent folder path to list contents of"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    List folders and files at the specified path.

    Returns a list of immediate subfolders and files in the given folder path.

    S3 Path Structure:
    - {environment}/{tenant_id}/fs/{folder_path}/{filename}
    - Environment: dev, qa, or prod (automatically determined from ENV variable or database host)
    - Tenant ID: Company identifier from auth token
    - Folder path: User-defined folder hierarchy

    - **path**: Parent folder path (optional, defaults to root)
    """
    try:
        service = FilesystemService(uow, s3_service)
        response = service.list_folder(auth.tenant_id, path)

        logger.info(
            f"Folder listed: path={path}, tenant_id={auth.tenant_id}, "
            f"folders={len(response.folders)}, files={len(response.files)}"
        )

        return response
    except ValueError as e:
        logger.error(f"Invalid folder path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing folder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list folder contents"
        )


@filesystem_router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(
    request: CreateFolderRequest,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Validate folder path (folders are created implicitly when files are uploaded).

    This endpoint validates the folder path format but doesn't create any database records.
    Folders are created automatically when the first file is uploaded to them.

    - **path**: Folder path to validate
    """
    try:
        service = FilesystemService(uow, s3_service)
        normalized = service.validate_folder_path(request.path)

        logger.info(f"Folder path validated: path={normalized}, tenant_id={auth.tenant_id}")

        return {
            "status": "ok",
            "path": normalized,
            "message": "Folder path is valid. Upload files to create this folder."
        }
    except ValueError as e:
        logger.error(f"Invalid folder path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error validating folder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate folder path"
        )


@filesystem_router.delete("/folders", status_code=status.HTTP_200_OK)
async def delete_folder(
    path: str = Query(..., description="Folder path to delete"),
    recursive: bool = Query(False, description="Delete subfolders recursively"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Delete all files in a folder.

    Deletes all files in the specified folder. If recursive=True, also deletes files in subfolders.
    Files with legal hold are skipped.

    - **path**: Folder path to delete
    - **recursive**: Whether to delete subfolders recursively
    """
    try:
        service = FilesystemService(uow, s3_service)
        count = service.delete_folder(
            tenant_id=auth.tenant_id,
            folder_path=path,
            user_id=auth.user_id,
            recursive=recursive
        )

        logger.info(
            f"Folder deleted: path={path}, tenant_id={auth.tenant_id}, "
            f"recursive={recursive}, deleted_count={count}"
        )

        return {
            "status": "ok",
            "deleted_count": count,
            "message": f"Successfully deleted {count} file(s)"
        }
    except ValueError as e:
        logger.error(f"Error deleting folder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete folder"
        )


@filesystem_router.post("/upload", response_model=InitiateUploadResponse, status_code=status.HTTP_200_OK)
async def initiate_filesystem_upload(
    request: FilesystemUploadRequest,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Initiate file upload to filesystem.

    Initiates an upload session for a file in filesystem mode. Enforces unique filenames per folder.
    Returns session information for completing the upload.

    - **folder_path**: Folder path where the file will be stored
    - **original_filename**: Name of the file
    - **declared_size_bytes**: Size of the file in bytes
    - **content_type**: MIME type of the file (optional)
    - **custom_metadata**: Custom metadata (optional)
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)

        # Convert to internal upload request
        upload_req = InitiateUploadRequest(
            original_filename=request.original_filename,
            declared_size_bytes=request.declared_size_bytes,
            content_type=request.content_type,
            role=None,  # Not used in filesystem mode
            custom_metadata=request.custom_metadata
        )

        response = coordinator.plan_upload(
            request=upload_req,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
            mode=UploadModeV2.FILESYSTEM,
            folder_path=request.folder_path,
            company_instance_name=request.company_instance_name
        )

        logger.info(
            f"Filesystem upload initiated: document_id={response.document_id}, "
            f"folder={request.folder_path}, filename={request.original_filename}, "
            f"tenant_id={auth.tenant_id}"
        )

        return response
    except ValueError as e:
        logger.error(f"Validation error during filesystem upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error initiating filesystem upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate filesystem upload"
        )


@filesystem_router.post("/upload/{session_id}/data", status_code=status.HTTP_202_ACCEPTED)
async def upload_filesystem_data(
    session_id: UUID,
    file: UploadFile = File(...),
    part_number: int = Query(None, ge=1, le=10000),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Upload file data for a filesystem upload session.

    For single-part uploads: Upload the entire file (no part_number needed).
    For multipart uploads: Upload a specific part (requires part_number).

    - **session_id**: The session ID returned from /upload
    - **file**: The file data to upload
    - **part_number**: Part number (required for multipart uploads)
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)

        # Check if document exists and verify it's in filesystem mode
        document = uow.documents.get_by_id(session_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {session_id} not found"
            )

        # Verify it's a filesystem upload
        if document.upload_mode != UploadModeV2.FILESYSTEM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session {session_id} is not a filesystem upload"
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

            logger.info(f"Filesystem single upload completed: document_id={session_id}")

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "uploaded",
                    "document_id": str(session_id),
                    "message": "File uploaded successfully. Call /complete to finalize."
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

            logger.info(f"Filesystem part uploaded: document_id={session_id}, part={part_number}")

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
        logger.error(f"Validation error during filesystem data upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading filesystem data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload filesystem data"
        )


@filesystem_router.post("/upload/complete", response_model=CompleteUploadResponse, status_code=status.HTTP_200_OK)
async def complete_filesystem_upload(
    request: CompleteUploadRequest,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Complete a filesystem upload session and finalize the document.

    Performs verification checks and transitions the document to 'ready' state.

    - **document_id**: The document ID to complete
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)

        # Verify the document is a filesystem upload
        document = uow.documents.get_by_id(request.document_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {request.document_id} not found"
            )

        if document.upload_mode != UploadModeV2.FILESYSTEM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {request.document_id} is not a filesystem upload"
            )

        response = coordinator.complete_upload(
            document_id=request.document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )

        logger.info(
            f"Filesystem upload completed: document_id={request.document_id}, "
            f"tenant_id={auth.tenant_id}, size={response.verification.get('size')}"
        )

        return response

    except ValueError as e:
        logger.error(f"Validation error during filesystem upload completion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error completing filesystem upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete filesystem upload"
        )


@filesystem_router.delete("/upload/{document_id}", status_code=status.HTTP_200_OK)
async def abort_filesystem_upload(
    document_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Abort an in-progress filesystem upload.

    Cancels multipart upload if applicable and marks the document as aborted.

    - **document_id**: The document ID to abort
    """
    try:
        coordinator = UploadCoordinator(uow, s3_service)

        # Verify the document is a filesystem upload
        document = uow.documents.get_by_id(document_id, auth.tenant_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {document_id} not found"
            )

        if document.upload_mode != UploadModeV2.FILESYSTEM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {document_id} is not a filesystem upload"
            )

        coordinator.abort_upload(
            document_id=document_id,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id
        )

        logger.info(f"Filesystem upload aborted: document_id={document_id}, tenant_id={auth.tenant_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "aborted",
                "document_id": str(document_id),
                "message": "Filesystem upload aborted successfully"
            }
        )

    except ValueError as e:
        logger.error(f"Error aborting filesystem upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error aborting filesystem upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort filesystem upload"
        )


@filesystem_router.get("/files", response_model=List[DocumentResponse], status_code=status.HTTP_200_OK)
async def list_files(
    path: str = Query("", description="Folder path to list files from"),
    recursive: bool = Query(False, description="List files recursively from subfolders"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip"),
    company_instance_name: Optional[str] = Query(None, description="Filter by company instance name"),
    auth: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    List files in a folder.

    Returns a paginated list of files in the specified folder.

    - **path**: Folder path to list files from
    - **recursive**: Whether to include files from subfolders
    - **limit**: Maximum number of files to return (1-1000)
    - **offset**: Number of files to skip for pagination
    """
    try:
        documents = uow.documents.list_by_folder(
            tenant_id=auth.tenant_id,
            folder_path=path,
            recursive=recursive,
            limit=limit,
            offset=offset,
            company_instance_name=company_instance_name
        )

        logger.info(
            f"Files listed: path={path}, tenant_id={auth.tenant_id}, "
            f"recursive={recursive}, count={len(documents)}"
        )

        return [DocumentResponse.model_validate(doc) for doc in documents]
    except ValueError as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )
