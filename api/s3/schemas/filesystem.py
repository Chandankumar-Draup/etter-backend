from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


class CreateFolderRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip('/')
        if '..' in v or not v:
            raise ValueError('Invalid folder path')
        return v


class FolderInfo(BaseModel):
    name: str
    path: str
    file_count: int
    total_size: int
    last_modified: Optional[datetime]


class ListFolderResponse(BaseModel):
    folders: List[FolderInfo]
    files: List['DocumentResponse']  # from documents.py
    parent_path: Optional[str]


class FilesystemUploadRequest(BaseModel):
    folder_path: str = Field(..., min_length=0, max_length=500)
    original_filename: str = Field(..., min_length=1, max_length=255)
    declared_size_bytes: int = Field(..., gt=0)
    content_type: Optional[str] = None
    custom_metadata: Optional[Dict[str, str]] = None
    company_instance_name: Optional[str] = None

    @field_validator('folder_path')
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        v = v.strip('/')
        if '..' in v:
            raise ValueError('Invalid folder path')
        return v

    @field_validator('original_filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Filename contains invalid characters')
        return v


# Import DocumentResponse to resolve forward reference
from api.s3.schemas.documents import DocumentResponse
ListFolderResponse.model_rebuild()
