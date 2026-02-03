from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.s3 import (
    Document, DocumentPart, AuditEvent, IdempotencyKey,
    DocumentStatus, UploadMode
)


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_id(self, document_id: UUID, tenant_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.tenant_id == tenant_id
            )
        ).first()

    def get_by_id_any_tenant(self, document_id: UUID) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def update(self, document: Document) -> Document:
        self.db.flush()
        return document

    def list_by_tenant(
        self,
        tenant_id: str,
        role: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        query = self.db.query(Document).filter(Document.tenant_id == tenant_id)
        
        if role:
            query = query.filter(Document.role == role)
        
        if status:
            query = query.filter(Document.status == status)
        
        query = query.order_by(Document.created_at.desc())
        query = query.limit(limit).offset(offset)

        return query.all()

    def get_by_path(
        self,
        tenant_id: str,
        folder_path: str,
        filename: str
    ) -> Optional[Document]:
        """Get document by filesystem path."""
        from models.s3 import UploadModeV2

        return self.db.query(Document).filter(
            and_(
                Document.tenant_id == tenant_id,
                Document.upload_mode == UploadModeV2.FILESYSTEM,
                Document.folder_path == folder_path,
                Document.original_filename == filename
            )
        ).first()

    def list_by_folder(
        self,
        tenant_id: str,
        folder_path: str,
        recursive: bool = False,
        limit: int = 100,
        offset: int = 0,
        company_instance_name: Optional[str] = None
    ) -> List[Document]:
        """List documents in a folder."""
        from models.s3 import UploadModeV2

        query = self.db.query(Document).filter(
            and_(
                Document.tenant_id == tenant_id,
                Document.upload_mode == UploadModeV2.FILESYSTEM,
                Document.status != DocumentStatus.DELETED
            )
        )

        if recursive:
            # folder_path LIKE 'contracts/2024%'
            query = query.filter(Document.folder_path.like(f"{folder_path}%"))
        else:
            # Exact folder match
            query = query.filter(Document.folder_path == folder_path)

        if company_instance_name:
            query = query.filter(Document.company_instance_name == company_instance_name)

        return query.order_by(Document.created_at.desc()).limit(limit).offset(offset).all()


class DocumentPartRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, part: DocumentPart) -> DocumentPart:
        self.db.add(part)
        self.db.flush()
        return part

    def upsert(self, document_id: UUID, part_number: int, etag: str, size_bytes: Optional[int] = None) -> DocumentPart:
        existing = self.db.query(DocumentPart).filter(
            and_(
                DocumentPart.document_id == document_id,
                DocumentPart.part_number == part_number
            )
        ).first()
        
        if existing:
            existing.etag = etag
            if size_bytes is not None:
                existing.size_bytes = size_bytes
            self.db.flush()
            return existing
        else:
            part = DocumentPart(
                document_id=document_id,
                part_number=part_number,
                etag=etag,
                size_bytes=size_bytes
            )
            return self.create(part)

    def list_by_document(self, document_id: UUID) -> List[DocumentPart]:
        return self.db.query(DocumentPart).filter(
            DocumentPart.document_id == document_id
        ).order_by(DocumentPart.part_number).all()


class AuditEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        actor: UUID,
        action: str,
        document_id: UUID,
        tenant_id: str,
        details: Optional[dict] = None
    ) -> AuditEvent:
        event = AuditEvent(
            actor=actor,
            action=action,
            document_id=document_id,
            tenant_id=tenant_id,
            details_json=details
        )
        self.db.add(event)
        self.db.flush()
        return event

    def list_by_document(self, document_id: UUID, limit: int = 100) -> List[AuditEvent]:
        return self.db.query(AuditEvent).filter(
            AuditEvent.document_id == document_id
        ).order_by(AuditEvent.time.desc()).limit(limit).all()


class IdempotencyKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, key: str, document_id: UUID, tenant_id: str, ttl_hours: int = 24) -> IdempotencyKey:
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        idempotency = IdempotencyKey(
            key=key,
            document_id=document_id,
            tenant_id=tenant_id,
            expires_at=expires_at
        )
        self.db.add(idempotency)
        self.db.flush()
        return idempotency

    def get_by_key(self, key: str, tenant_id: str) -> Optional[IdempotencyKey]:
        return self.db.query(IdempotencyKey).filter(
            and_(
                IdempotencyKey.key == key,
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.expires_at > datetime.utcnow()
            )
        ).first()

    def cleanup_expired(self) -> int:
        deleted = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.expires_at <= datetime.utcnow()
        ).delete()
        self.db.flush()
        return deleted

