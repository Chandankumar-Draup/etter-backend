from typing import List
from uuid import UUID

from models.s3 import Document, DocumentStatus


class AuthorizationPolicy:
    @staticmethod
    def can_read_document(document: Document, tenant_id: str, user_group: str) -> bool:
        if document.tenant_id != tenant_id:
            return False
        
        if document.status == DocumentStatus.DELETED:
            return False
        
        return True

    @staticmethod
    def can_delete_document(document: Document, tenant_id: str, user_group: str, is_admin: bool = False) -> bool:
        if document.tenant_id != tenant_id:
            return False
        
        if document.status == DocumentStatus.DELETED:
            return False
        
        if document.legal_hold and not is_admin:
            return False
        
        return True

    @staticmethod
    def can_download_document(document: Document, tenant_id: str, user_group: str) -> bool:
        if document.tenant_id != tenant_id:
            return False
        
        if document.status not in [DocumentStatus.READY, DocumentStatus.UPLOADED]:
            return False
        
        return True


class ValidationPolicy:
    MAX_FILENAME_LENGTH = 255
    ALLOWED_CONTENT_TYPES = [
        'application/pdf',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/json',
        'application/xml'
    ]

    @staticmethod
    def validate_filename(filename: str) -> bool:
        if not filename or len(filename) > ValidationPolicy.MAX_FILENAME_LENGTH:
            return False
        
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        return True

    @staticmethod
    def validate_content_type(content_type: str, strict: bool = False) -> bool:
        if not strict:
            return True
        
        return content_type in ValidationPolicy.ALLOWED_CONTENT_TYPES

