import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, BigInteger, Text, DateTime, Boolean, 
    ForeignKey, Index, UniqueConstraint, Integer, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from settings.database import Base


class UploadMode(str, enum.Enum):
    SINGLE = "single"
    MULTIPART = "multipart"


class UploadModeV2(str, enum.Enum):
    FILESYSTEM = "filesystem"
    ROLE_BASED = "role_based"


class DocumentStatus(str, enum.Enum):
    PLANNED = "planned"
    UPLOADED = "uploaded"
    READY = "ready"
    DELETED = "deleted"
    QUARANTINE = "quarantine"
    ABORTED = "aborted"


class Document(Base):
    __tablename__ = "s3_documents"
    __table_args__ = (
        Index("ix_s3_documents_tenant_role_created", "tenant_id", "role", "created_at"),
        Index("ix_s3_documents_status", "status"),
        Index("idx_s3_documents_tenant_id", "tenant_id"),
        Index("idx_s3_documents_status", "status"),
        Index("idx_s3_documents_created_at", "created_at"),
        Index("idx_s3_documents_tenant_status", "tenant_id", "status"),
        {'schema': 'etter'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    role = Column(Text, nullable=False)
    bucket = Column(Text, nullable=False)
    key = Column(Text, nullable=False)
    mode = Column(Enum(UploadMode), nullable=False)
    upload_id = Column(Text, nullable=True)
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.PLANNED)
    declared_size_bytes = Column(BigInteger, nullable=True)
    observed_size_bytes = Column(BigInteger, nullable=True)
    declared_content_type = Column(Text, nullable=True)
    observed_content_type = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    custom_metadata = Column(JSONB, nullable=True)
    legal_hold = Column(Boolean, default=False, nullable=False)
    original_filename = Column(Text, nullable=True)
    upload_mode = Column(Enum(UploadModeV2), nullable=False)
    folder_path = Column(Text, nullable=True)
    company_instance_name = Column(Text, nullable=True)

    parts = relationship("DocumentPart", back_populates="document", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="document", cascade="all, delete-orphan")


class DocumentPart(Base):
    __tablename__ = "s3_document_parts"
    __table_args__ = (
        UniqueConstraint("document_id", "part_number", name="uq_s3_document_part"),
        Index("ix_s3_document_parts_document_id", "document_id"),
        {'schema': 'etter'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("etter.s3_documents.id", ondelete="CASCADE"), nullable=False)
    part_number = Column(Integer, nullable=False)
    etag = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="parts")


class AuditEvent(Base):
    __tablename__ = "s3_audit_events"
    __table_args__ = (
        Index("ix_s3_audit_events_document_id", "document_id"),
        Index("ix_s3_audit_events_tenant_action", "tenant_id", "action"),
        {'schema': 'etter'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    actor = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Text, nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("etter.s3_documents.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Text, nullable=False, index=True)
    details_json = Column(JSONB, nullable=True)

    document = relationship("Document", back_populates="audit_events")


class IdempotencyKey(Base):
    __tablename__ = "s3_idempotency_keys"
    __table_args__ = (
        Index("ix_s3_idempotency_keys_expires_at", "expires_at"),
        {'schema': 'etter'}
    )

    key = Column(Text, primary_key=True)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id = Column(Text, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

