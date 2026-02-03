"""
Extraction Service

Handles communication with Draup World Model API for document extraction.
"""

import logging
import os
from typing import Optional
from uuid import UUID

import requests

from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from api.s3.domain.services.document_custodian import DocumentCustodian
from api.etter_apis import get_draup_world_api, get_token
from models.extraction import (
    ExtractedDocument, ExtractionSession,
    ExtractionStatus, ApprovalStatus, ExtractionSessionStatus
)
from api.etter_apis import get_draup_world_api
logger = logging.getLogger(__name__)

# Configuration
DRAUP_WORLD_MODEL_BASE_URL = get_draup_world_api()
EXTRACT_FROM_URL_ENDPOINT = f"{DRAUP_WORLD_MODEL_BASE_URL}/input_repository/extract-from-url"
TIMEOUT_SECONDS = 300  # 5 minutes for LLM processing


class ExtractionService:
    """
    Service for extracting tasks, skills, and stages from documents
    using the Draup World Model API.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        s3_service: S3ManagementService
    ):
        self.uow = uow
        self.s3_service = s3_service
        self.custodian = DocumentCustodian(uow, s3_service)

    def get_presigned_url(
        self,
        document_id: UUID,
        tenant_id: str
    ) -> tuple[str, str]:
        """
        Get presigned download URL for a document.

        Returns:
            Tuple of (download_url, original_filename)
        
        Raises:
            ValueError: If document not found or not available
        """
        document_response = self.custodian.get_document(
            document_id=document_id,
            tenant_id=tenant_id,
            generate_download_url=True
        )

        if not document_response.download or not document_response.download.url:
            raise ValueError("Document is not available for download")

        return (
            document_response.download.url,
            document_response.document.original_filename
        )

    def call_extraction_api(
        self,
        presigned_url: str,
        document_name: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> dict:
        """
        Call the Draup World Model extraction API.

        Args:
            presigned_url: Pre-signed S3 URL for document download
            document_name: Original filename (helps with type detection)
            document_type: Optional type hint (process_map, job_description, etc.)

        Returns:
            Extraction result dictionary

        Raises:
            requests.RequestException: On API communication failure
        """
        token = get_token()
        if not token:
            raise RuntimeError("Failed to obtain auth token for Draup World Model")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {token}',
            'Origin': 'https://draup-world.draup.technology'
        }

        payload = {
            "presigned_url": presigned_url,
            "document_name": document_name,
            "document_type": document_type
        }

        logger.info(f"Calling extraction API: {EXTRACT_FROM_URL_ENDPOINT}")

        response = requests.post(
            EXTRACT_FROM_URL_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SECONDS
        )

        if response.status_code != 200:
            logger.error(
                f"Extraction API error: status={response.status_code}, "
                f"body={response.text[:500]}"
            )
            raise requests.RequestException(
                f"Extraction API returned {response.status_code}: {response.text}"
            )

        return response.json()

    def process_document(
        self,
        extracted_doc: ExtractedDocument,
        tenant_id: str,
        db_session
    ) -> ExtractedDocument:
        """
        Process a single document for extraction.

        Fetches presigned URL, calls extraction API, and updates the record.

        Args:
            extracted_doc: The ExtractedDocument record to process
            tenant_id: Tenant ID for S3 access
            db_session: Database session for updates

        Returns:
            Updated ExtractedDocument
        """
        try:
            # Update status to PROCESSING
            extracted_doc.status = ExtractionStatus.PROCESSING
            db_session.commit()

            # Get presigned URL
            presigned_url, original_filename = self.get_presigned_url(
                document_id=extracted_doc.document_id,
                tenant_id=tenant_id
            )

            # Store the document name if not already set
            if not extracted_doc.document_name:
                extracted_doc.document_name = original_filename
                db_session.commit()

            # Call extraction API
            result = self.call_extraction_api(
                presigned_url=presigned_url,
                document_name=extracted_doc.document_name or original_filename,
                document_type=extracted_doc.document_type  # Use stored type hint or API will auto-detect
            )

            # Update record with results
            if result.get("status") == "success":
                extracted_doc.status = ExtractionStatus.COMPLETED
                extracted_doc.document_type = result.get("document_type")
                extracted_doc.extraction_confidence = result.get("extraction_confidence")
                extracted_doc.extraction_metadata = result.get("metadata")
                extracted_doc.tasks = result.get("tasks", [])
                extracted_doc.skills = result.get("skills", [])
                extracted_doc.stages = result.get("stages", [])
                extracted_doc.task_to_skill = result.get("task_to_skill", [])
            else:
                extracted_doc.status = ExtractionStatus.FAILED
                extracted_doc.error_message = result.get("message", "Unknown error")

            db_session.commit()
            logger.info(
                f"Extraction completed for document {extracted_doc.document_id}: "
                f"status={extracted_doc.status}"
            )

        except Exception as e:
            logger.error(f"Extraction failed for document {extracted_doc.document_id}: {e}")
            extracted_doc.status = ExtractionStatus.FAILED
            extracted_doc.error_message = str(e)[:1000]
            db_session.commit()

        return extracted_doc
