from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentResponse(BaseModel):
    id: UUID
    tenant_id: str
    role: Optional[str]
    status: str
    original_filename: Optional[str]
    declared_size_bytes: Optional[int]
    observed_size_bytes: Optional[int]
    declared_content_type: Optional[str]
    observed_content_type: Optional[str]
    created_by: UUID
    created_at: datetime
    completed_at: Optional[datetime]
    custom_metadata: Optional[Dict[str, Any]]
    legal_hold: bool
    upload_mode: str
    folder_path: Optional[str]

    class Config:
        from_attributes = True


class DownloadInfo(BaseModel):
    url: str
    expires_in: int


class DocumentWithDownloadResponse(BaseModel):
    document: DocumentResponse
    download: Optional[DownloadInfo] = None


class DeleteDocumentResponse(BaseModel):
    status: str
    document_id: UUID
    deleted_at: datetime

