from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import func
import logging

from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.schemas.filesystem import FolderInfo, ListFolderResponse
from api.s3.schemas.documents import DocumentResponse
from models.s3 import DocumentStatus, Document, UploadModeV2

logger = logging.getLogger(__name__)


class FilesystemService:
    def __init__(self, uow: UnitOfWork, s3_service: S3ManagementService):
        self.uow = uow
        self.s3 = s3_service

    def list_folder(
        self,
        tenant_id: str,
        path: Optional[str] = None
    ) -> ListFolderResponse:
        """List folders and files at the specified path."""
        normalized_path = self._normalize_path(path) if path else ""

        # Get all documents in this folder (non-recursive)
        files = self.uow.documents.list_by_folder(
            tenant_id=tenant_id,
            folder_path=normalized_path,
            recursive=False
        )

        # Extract subfolders from paths
        folders = self._extract_subfolders(
            tenant_id=tenant_id,
            parent_path=normalized_path
        )

        return ListFolderResponse(
            folders=folders,
            files=[DocumentResponse.model_validate(f) for f in files],
            parent_path=normalized_path or None
        )

    def _extract_subfolders(
        self,
        tenant_id: str,
        parent_path: str
    ) -> List[FolderInfo]:
        """Extract unique subfolders from document paths."""
        # Query all filesystem documents for this tenant
        query = self.uow.documents.db.query(Document).filter(
            Document.tenant_id == tenant_id,
            Document.upload_mode == UploadModeV2.FILESYSTEM,
            Document.status != DocumentStatus.DELETED
        )

        # Filter by parent path
        if parent_path:
            # Find folders that are immediate children of parent_path
            query = query.filter(Document.folder_path.like(f"{parent_path}/%"))
        else:
            # Root level - exclude paths with '/' (only get top-level folders)
            query = query.filter(~Document.folder_path.contains('/'))

        all_docs = query.all()

        # Extract unique immediate subfolders
        subfolders_dict = {}
        for doc in all_docs:
            folder_path = doc.folder_path or ""

            # Extract the immediate subfolder name
            if parent_path:
                # Remove parent path prefix
                relative_path = folder_path[len(parent_path)+1:] if folder_path.startswith(parent_path + '/') else folder_path
            else:
                relative_path = folder_path

            # Get the first segment (immediate child folder)
            parts = relative_path.split('/')
            if parts and parts[0]:
                subfolder_name = parts[0]
                full_path = f"{parent_path}/{subfolder_name}" if parent_path else subfolder_name

                if subfolder_name not in subfolders_dict:
                    subfolders_dict[subfolder_name] = {
                        'name': subfolder_name,
                        'path': full_path,
                        'file_count': 0,
                        'total_size': 0,
                        'last_modified': None
                    }

                # Update stats only if this document is directly in this subfolder
                if folder_path == full_path or folder_path.startswith(full_path + '/'):
                    subfolders_dict[subfolder_name]['file_count'] += 1
                    subfolders_dict[subfolder_name]['total_size'] += doc.observed_size_bytes or 0
                    if doc.created_at:
                        if subfolders_dict[subfolder_name]['last_modified'] is None or doc.created_at > subfolders_dict[subfolder_name]['last_modified']:
                            subfolders_dict[subfolder_name]['last_modified'] = doc.created_at

        return [FolderInfo(**folder_data) for folder_data in subfolders_dict.values()]

    def _normalize_path(self, path: str) -> str:
        """Normalize folder path."""
        if not path:
            return ""
        path = path.strip('/')
        path = '/'.join(filter(None, path.split('/')))
        return path

    def validate_folder_path(self, path: str) -> str:
        """Validate and normalize folder path."""
        path = path.strip('/')
        if '..' in path or path.startswith('/'):
            raise ValueError("Invalid path")
        path = '/'.join(filter(None, path.split('/')))
        if len(path) > 500:
            raise ValueError("Path too long")
        return path

    def delete_folder(
        self,
        tenant_id: str,
        folder_path: str,
        user_id: UUID,
        recursive: bool = False
    ) -> int:
        """Delete all files in a folder."""
        documents = self.uow.documents.list_by_folder(
            tenant_id=tenant_id,
            folder_path=folder_path,
            recursive=recursive
        )

        count = 0
        for doc in documents:
            if doc.legal_hold:
                logger.warning(f"Skipping document {doc.id} with legal hold")
                continue  # Skip files with legal hold

            try:
                # Delete from S3
                self.s3.delete_object(doc.key)

                # Mark as deleted in DB
                doc.status = DocumentStatus.DELETED
                doc.deleted_at = datetime.utcnow()
                self.uow.documents.update(doc)

                # Audit
                self.uow.audit_events.create(
                    actor=user_id,
                    action="FOLDER_DELETE",
                    document_id=doc.id,
                    tenant_id=tenant_id,
                    details={'folder': folder_path}
                )
                count += 1
            except Exception as e:
                logger.error(f"Error deleting document {doc.id}: {e}")
                continue

        self.uow.commit()
        logger.info(f"Deleted {count} files from folder {folder_path}")
        return count
