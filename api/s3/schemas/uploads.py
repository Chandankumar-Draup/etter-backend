from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class InitiateUploadRequest(BaseModel):
    original_filename: str = Field(..., min_length=1, max_length=255)
    content_type: Optional[str] = None
    declared_size_bytes: int = Field(..., gt=0)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    custom_metadata: Optional[Dict[str, str]] = None
    idempotency_key: Optional[str] = None
    company_instance_name: Optional[str] = None

    @field_validator('original_filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Filename contains invalid characters')
        return v


class InitiateUploadResponse(BaseModel):
    session_id: UUID
    document_id: UUID
    upload_strategy: str  # "SINGLE" or "MULTIPART"
    upload_id: Optional[str] = None  # For multipart uploads
    part_size: Optional[int] = None  # For multipart uploads
    max_parts: Optional[int] = None  # For multipart uploads


class UploadPartResponse(BaseModel):
    part_number: int
    etag: str
    document_id: UUID


class CompleteUploadRequest(BaseModel):
    document_id: UUID


class CompleteUploadResponse(BaseModel):
    status: str
    document_id: UUID
    verification: Dict[str, Any]
    completed_at: datetime


class CombinedUploadResponse(BaseModel):
    status: str
    document_id: UUID
    verification: Dict[str, Any]
    completed_at: datetime
    mode: str
