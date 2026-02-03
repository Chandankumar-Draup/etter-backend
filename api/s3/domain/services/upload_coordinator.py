import uuid
from typing import BinaryIO, Optional
from datetime import datetime
import logging

from models.s3 import Document, DocumentStatus, UploadMode
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.config import s3_config, Constants
from api.s3.schemas.uploads import (
    InitiateUploadRequest,
    InitiateUploadResponse,
    UploadPartResponse,
    CompleteUploadResponse
)
from models.s3 import UploadModeV2
logger = logging.getLogger(__name__)


class UploadCoordinator:
    def __init__(self, uow: UnitOfWork, s3_service: S3ManagementService):
        self.uow = uow
        self.s3 = s3_service

    def plan_upload(
        self,
        request: InitiateUploadRequest,
        tenant_id: str,
        user_id: uuid.UUID,
        mode: 'UploadModeV2', 
        folder_path: Optional[str] = None,
        company_instance_name: Optional[str] = None
    ) -> InitiateUploadResponse:

        if request.idempotency_key:
            existing = self.uow.idempotency_keys.get_by_key(request.idempotency_key, tenant_id)
            if existing:
                doc = self.uow.documents.get_by_id(existing.document_id, tenant_id)
                if doc:
                    logger.info(f"Returning existing upload session for idempotency_key={request.idempotency_key}")
                    return self._build_initiate_response(doc)

        if request.declared_size_bytes <= s3_config.max_single_upload_size:
            return self._plan_single_upload(request, tenant_id, user_id, mode, folder_path, company_instance_name)
        else:
            return self._plan_multipart_upload(request, tenant_id, user_id, mode, folder_path, company_instance_name)

    def _plan_single_upload(
        self,
        request: InitiateUploadRequest,
        tenant_id: str,
        user_id: uuid.UUID,
        upload_mode_v2: 'UploadModeV2', 
        folder_path: Optional[str] = None,
        company_instance_name: Optional[str] = None
    ) -> InitiateUploadResponse:
        from models.s3 import UploadModeV2

        document_id = uuid.uuid4()

        # Build key based on mode
        key = self.s3.build_key(
            tenant_id=tenant_id,
            mode=upload_mode_v2,
            folder_path=folder_path,
            role=request.role if upload_mode_v2 == UploadModeV2.ROLE_BASED else None,
            original_filename=request.original_filename
        )

        # Check uniqueness for filesystem mode
        # if upload_mode_v2 == UploadModeV2.FILESYSTEM:
        #     existing = self.uow.documents.get_by_path(
        #         tenant_id, folder_path, request.original_filename
        #     )
        #     if existing and existing.status != DocumentStatus.DELETED:
        #         raise ValueError(f"File '{request.original_filename}' already exists in folder '{folder_path}'")

        document = Document(
            id=document_id,
            tenant_id=tenant_id,
            role=request.role if upload_mode_v2 == UploadModeV2.ROLE_BASED else None,
            bucket=self.s3.bucket,
            key=key,
            mode=UploadMode.SINGLE,
            upload_mode=upload_mode_v2,
            folder_path=folder_path,
            status=DocumentStatus.PLANNED,
            declared_size_bytes=request.declared_size_bytes,
            declared_content_type=request.content_type,
            created_by=user_id,
            original_filename=request.original_filename,
            custom_metadata=request.custom_metadata,
            company_instance_name=company_instance_name
        )

        self.uow.documents.create(document)

        if request.idempotency_key:
            self.uow.idempotency_keys.create(
                request.idempotency_key,
                document_id,
                tenant_id,
                Constants.IDEMPOTENCY_KEY_TTL_HOURS
            )

        self.uow.commit()

        logger.info(f"Planned single upload: document_id={document_id}, tenant_id={tenant_id}")

        return InitiateUploadResponse(
            session_id=document_id,
            document_id=document_id,
            upload_strategy="SINGLE",
            upload_id=None,
            part_size=None,
            max_parts=None
        )

    def _plan_multipart_upload(
        self,
        request: InitiateUploadRequest,
        tenant_id: str,
        user_id: uuid.UUID,
        upload_mode_v2: 'UploadModeV2',
        folder_path: Optional[str] = None,
        company_instance_name: Optional[str] = None
    ) -> InitiateUploadResponse:
        from models.s3 import UploadModeV2

        document_id = uuid.uuid4()

        # Build key based on mode
        key = self.s3.build_key(
            tenant_id=tenant_id,
            mode=upload_mode_v2,
            folder_path=folder_path,
            role=request.role if upload_mode_v2 == UploadModeV2.ROLE_BASED else None,
            original_filename=request.original_filename
        )

        # Check uniqueness for filesystem mode
        # if upload_mode_v2 == UploadModeV2.FILESYSTEM:
        #     existing = self.uow.documents.get_by_path(
        #         tenant_id, folder_path, request.original_filename
        #     )
        #     if existing and existing.status != DocumentStatus.DELETED:
        #         raise ValueError(f"File '{request.original_filename}' already exists in folder '{folder_path}'")

        tags = {
            'tenant_id': tenant_id,
            'role': request.role if upload_mode_v2 == UploadModeV2.ROLE_BASED else '',
            'document_id': str(document_id),
            'status': DocumentStatus.PLANNED.value
        }

        multipart_upload = self.s3.create_multipart(
            key=key,
            tags=tags,
            content_type=request.content_type
        )

        document = Document(
            id=document_id,
            tenant_id=tenant_id,
            role=request.role if upload_mode_v2 == UploadModeV2.ROLE_BASED else None,
            bucket=self.s3.bucket,
            key=key,
            mode=UploadMode.MULTIPART,
            upload_mode=upload_mode_v2,
            folder_path=folder_path,
            upload_id=multipart_upload.upload_id,
            status=DocumentStatus.PLANNED,
            declared_size_bytes=request.declared_size_bytes,
            declared_content_type=request.content_type,
            created_by=user_id,
            original_filename=request.original_filename,
            custom_metadata=request.custom_metadata,
            company_instance_name=company_instance_name
        )

        self.uow.documents.create(document)

        if request.idempotency_key:
            self.uow.idempotency_keys.create(
                request.idempotency_key,
                document_id,
                tenant_id,
                Constants.IDEMPOTENCY_KEY_TTL_HOURS
            )

        self.uow.commit()

        logger.info(f"Planned multipart upload: document_id={document_id}, upload_id={multipart_upload.upload_id}")

        max_parts = (request.declared_size_bytes // s3_config.multipart_part_size) + 1

        return InitiateUploadResponse(
            session_id=document_id,
            document_id=document_id,
            upload_strategy="MULTIPART",
            upload_id=multipart_upload.upload_id,
            part_size=s3_config.multipart_part_size,
            max_parts=int(max_parts)
        )

    def _build_initiate_response(self, document: Document) -> InitiateUploadResponse:
        if document.mode == UploadMode.SINGLE:
            return InitiateUploadResponse(
                session_id=document.id,
                document_id=document.id,
                upload_strategy="SINGLE",
                upload_id=None,
                part_size=None,
                max_parts=None
            )
        else:
            max_parts = None
            if document.declared_size_bytes:
                max_parts = int((document.declared_size_bytes // s3_config.multipart_part_size) + 1)

            return InitiateUploadResponse(
                session_id=document.id,
                document_id=document.id,
                upload_strategy="MULTIPART",
                upload_id=document.upload_id,
                part_size=s3_config.multipart_part_size,
                max_parts=max_parts
            )

    def stream_single(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        fileobj: BinaryIO,
        user_id: uuid.UUID
    ) -> None:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status != DocumentStatus.PLANNED:
            raise ValueError(f"Document {document_id} is not in PLANNED state")

        if document.mode != UploadMode.SINGLE:
            raise ValueError(f"Document {document_id} is not a single-part upload")

        tags = {
            'tenant_id': tenant_id,
            'role': document.role,
            'document_id': str(document_id),
            'status': DocumentStatus.UPLOADED.value
        }

        result = self.s3.put_single(
            key=document.key,
            fileobj=fileobj,
            tags=tags,
            content_type=document.declared_content_type
        )

        verification = self.s3.head_object(document.key)

        document.status = DocumentStatus.UPLOADED
        document.observed_size_bytes = verification.content_length
        document.observed_content_type = verification.content_type
        self.uow.documents.update(document)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_UPLOADED,
            document_id=document_id,
            tenant_id=tenant_id,
            details={'etag': result.etag, 'sse': result.sse_algorithm}
        )

        self.uow.commit()

        logger.info(f"Single upload completed: document_id={document_id}, size={verification.content_length}")

    def upload_part(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        part_number: int,
        data: BinaryIO,
        user_id: uuid.UUID
    ) -> UploadPartResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status not in [DocumentStatus.PLANNED, DocumentStatus.UPLOADED]:
            raise ValueError(f"Document {document_id} is not in a valid state for part upload")

        if document.mode != UploadMode.MULTIPART:
            raise ValueError(f"Document {document_id} is not a multipart upload")

        if not document.upload_id:
            raise ValueError(f"Document {document_id} has no upload_id")

        result = self.s3.upload_part(
            key=document.key,
            upload_id=document.upload_id,
            part_number=part_number,
            data=data
        )

        self.uow.parts.upsert(
            document_id=document_id,
            part_number=part_number,
            etag=result.etag
        )

        if document.status == DocumentStatus.PLANNED:
            document.status = DocumentStatus.UPLOADED
            self.uow.documents.update(document)

        self.uow.commit()

        logger.info(f"Part uploaded: document_id={document_id}, part={part_number}, etag={result.etag}")

        return UploadPartResponse(
            part_number=part_number,
            etag=result.etag,
            document_id=document_id
        )

    def complete_upload(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        user_id: uuid.UUID
    ) -> CompleteUploadResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status == DocumentStatus.READY:
            logger.info(f"Document {document_id} already in READY state, returning existing verification")
            return self._build_complete_response(document)

        if document.status != DocumentStatus.UPLOADED:
            raise ValueError(f"Document {document_id} is not in UPLOADED state")

        if document.mode == UploadMode.MULTIPART:
            return self._complete_multipart(document, user_id)
        else:
            return self._complete_single(document, user_id)

    def _complete_single(self, document: Document, user_id: uuid.UUID) -> CompleteUploadResponse:
        verification = self.s3.head_object(document.key)

        if verification.sse_algorithm != s3_config.sse_algorithm:
            raise ValueError(f"SSE algorithm mismatch: expected {s3_config.sse_algorithm}, got {verification.sse_algorithm}")

        required_tags = {'tenant_id', 'role', 'document_id', 'status'}
        if not required_tags.issubset(verification.tags.keys()):
            raise ValueError(f"Missing required tags: {required_tags - verification.tags.keys()}")

        document.status = DocumentStatus.READY
        document.completed_at = datetime.utcnow()
        document.observed_size_bytes = verification.content_length
        document.observed_content_type = verification.content_type
        self.uow.documents.update(document)

        tags = verification.tags.copy()
        tags['status'] = DocumentStatus.READY.value
        self.s3.put_tags(document.key, tags)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_UPLOADED,
            document_id=document.id,
            tenant_id=document.tenant_id,
            details={
                'size': verification.content_length,
                'content_type': verification.content_type,
                'sse': verification.sse_algorithm
            }
        )

        self.uow.commit()

        logger.info(f"Single upload finalized: document_id={document.id}")

        return CompleteUploadResponse(
            status="ok",
            document_id=document.id,
            verification={
                'size': verification.content_length,
                'content_type': verification.content_type,
                'sse': verification.sse_algorithm,
                'etag': verification.etag
            },
            completed_at=document.completed_at
        )

    def _complete_multipart(self, document: Document, user_id: uuid.UUID) -> CompleteUploadResponse:
        parts = self.uow.parts.list_by_document(document.id)
        if not parts:
            raise ValueError(f"No parts found for document {document.id}")

        parts_list = [
            {'PartNumber': part.part_number, 'ETag': part.etag}
            for part in parts
        ]

        self.s3.complete_multipart(
            key=document.key,
            upload_id=document.upload_id,
            parts=parts_list
        )

        verification = self.s3.head_object(document.key)

        if verification.sse_algorithm != s3_config.sse_algorithm:
            raise ValueError(f"SSE algorithm mismatch: expected {s3_config.sse_algorithm}, got {verification.sse_algorithm}")

        required_tags = {'tenant_id', 'role', 'document_id', 'status'}
        if not required_tags.issubset(verification.tags.keys()):
            raise ValueError(f"Missing required tags: {required_tags - verification.tags.keys()}")

        document.status = DocumentStatus.READY
        document.completed_at = datetime.utcnow()
        document.observed_size_bytes = verification.content_length
        document.observed_content_type = verification.content_type
        self.uow.documents.update(document)

        tags = verification.tags.copy()
        tags['status'] = DocumentStatus.READY.value
        self.s3.put_tags(document.key, tags)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_UPLOADED,
            document_id=document.id,
            tenant_id=document.tenant_id,
            details={
                'size': verification.content_length,
                'content_type': verification.content_type,
                'sse': verification.sse_algorithm,
                'parts': len(parts)
            }
        )

        self.uow.commit()

        logger.info(f"Multipart upload finalized: document_id={document.id}, parts={len(parts)}")

        return CompleteUploadResponse(
            status="ok",
            document_id=document.id,
            verification={
                'size': verification.content_length,
                'content_type': verification.content_type,
                'sse': verification.sse_algorithm,
                'etag': verification.etag,
                'parts': len(parts)
            },
            completed_at=document.completed_at
        )

    def _build_complete_response(self, document: Document) -> CompleteUploadResponse:
        return CompleteUploadResponse(
            status="ok",
            document_id=document.id,
            verification={
                'size': document.observed_size_bytes,
                'content_type': document.observed_content_type
            },
            completed_at=document.completed_at or datetime.utcnow()
        )

    def abort_upload(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        user_id: uuid.UUID
    ) -> None:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.mode == UploadMode.MULTIPART and document.upload_id:
            self.s3.abort_multipart(document.key, document.upload_id)

        document.status = DocumentStatus.ABORTED
        self.uow.documents.update(document)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_UPLOAD_ABORTED,
            document_id=document_id,
            tenant_id=tenant_id
        )

        self.uow.commit()

        logger.info(f"Upload aborted: document_id={document_id}")

