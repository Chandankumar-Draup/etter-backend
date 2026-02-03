import uuid
from typing import Optional
from datetime import datetime
import logging

from models.s3 import Document, DocumentStatus
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.config import Constants
from api.s3.schemas.documents import (
    DocumentResponse,
    DocumentWithDownloadResponse,
    DeleteDocumentResponse,
    DownloadInfo
)

logger = logging.getLogger(__name__)


class DocumentCustodian:
    def __init__(self, uow: UnitOfWork, s3_service: S3ManagementService):
        self.uow = uow
        self.s3 = s3_service

    def get_document(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        generate_download_url: bool = False
    ) -> DocumentWithDownloadResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status == DocumentStatus.DELETED:
            raise ValueError(f"Document {document_id} has been deleted")
        
        if document.status == DocumentStatus.QUARANTINE and generate_download_url:
            raise ValueError(f"Document {document_id} is quarantined and cannot be downloaded")

        document_response = DocumentResponse.model_validate(document)

        download_info = None
        if generate_download_url and document.status in [DocumentStatus.READY, DocumentStatus.UPLOADED]:
            url = self.s3.generate_presigned_get_url(document.key, ttl_seconds=7200)  # 2 hour
            download_info = DownloadInfo(url=url, expires_in=7200)

        return DocumentWithDownloadResponse(
            document=document_response,
            download=download_info
        )

    def delete_document(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        user_id: uuid.UUID,
        admin_override: bool = False
    ) -> DeleteDocumentResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status == DocumentStatus.DELETED:
            logger.info(f"Document {document_id} already deleted")
            return DeleteDocumentResponse(
                status="deleted",
                document_id=document_id,
                deleted_at=document.deleted_at or datetime.utcnow()
            )

        if document.legal_hold and not admin_override:
            raise ValueError(f"Document {document_id} has legal hold and cannot be deleted without admin override")

        self.s3.delete_object(document.key)

        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.utcnow()
        self.uow.documents.update(document)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_DELETED,
            document_id=document_id,
            tenant_id=tenant_id,
            details={'admin_override': admin_override}
        )

        self.uow.commit()

        logger.info(f"Document deleted: document_id={document_id}, admin_override={admin_override}")

        return DeleteDocumentResponse(
            status="deleted",
            document_id=document_id,
            deleted_at=document.deleted_at
        )

    def quarantine_document(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        user_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> DocumentResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.QUARANTINE
        self.uow.documents.update(document)

        tags = self.s3.get_tags(document.key)
        tags['status'] = DocumentStatus.QUARANTINE.value
        self.s3.put_tags(document.key, tags)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_QUARANTINED,
            document_id=document_id,
            tenant_id=tenant_id,
            details={'reason': reason}
        )

        self.uow.commit()

        logger.info(f"Document quarantined: document_id={document_id}, reason={reason}")

        return DocumentResponse.model_validate(document)

    def approve_document(
        self,
        document_id: uuid.UUID,
        tenant_id: str,
        user_id: uuid.UUID
    ) -> DocumentResponse:
        document = self.uow.documents.get_by_id(document_id, tenant_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status != DocumentStatus.QUARANTINE:
            raise ValueError(f"Document {document_id} is not quarantined")

        document.status = DocumentStatus.READY
        self.uow.documents.update(document)

        tags = self.s3.get_tags(document.key)
        tags['status'] = DocumentStatus.READY.value
        self.s3.put_tags(document.key, tags)

        self.uow.audit_events.create(
            actor=user_id,
            action=Constants.AUDIT_ACTION_DOCUMENT_APPROVED,
            document_id=document_id,
            tenant_id=tenant_id
        )

        self.uow.commit()

        logger.info(f"Document approved: document_id={document_id}")

        return DocumentResponse.model_validate(document)

