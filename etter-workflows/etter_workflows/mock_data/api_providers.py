"""
API-based providers for documents and role taxonomy.

These providers call the real APIs instead of using mock data.
They implement the same interfaces as the mock providers.

Primary approach: HTTP API calls
- GET /api/documents/ - List documents
- GET /api/documents/{id}?generate_download_url=true - Get document with download URL
- GET /api/extraction/role_taxonomy/company/{company_id} - List role taxonomy

Fallback approach (when HTTP fails): Direct database access
- Uses parent package models: Document, ExtractedDocument, RoleTaxonomy
- Queries the database directly when running inside etter-backend
"""

import logging
import requests
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime

from etter_workflows.mock_data.role_taxonomy import RoleTaxonomyProvider
from etter_workflows.mock_data.documents import DocumentProvider
from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)

# Type hints for parent package imports (optional - only used when available)
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _get_db_session() -> Optional["Session"]:
    """
    Get database session from parent package.

    Returns None if parent package is not available.
    This is used as a fallback when HTTP API calls fail.

    Tries multiple import paths to work from different contexts:
    1. Direct import (when running inside etter-backend)
    2. After adding etter-backend to path (when running tests)
    """
    # Try 1: Direct import (running from etter-backend)
    try:
        from settings.database import SessionLocal
        return SessionLocal()
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Direct import failed: {e}")

    # Try 2: Add parent path and try again
    try:
        import sys
        import os

        # Get etter-backend path (parent of etter-workflows)
        current_file = os.path.abspath(__file__)
        etter_workflows_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        etter_backend_root = os.path.dirname(etter_workflows_root)

        if etter_backend_root not in sys.path:
            sys.path.insert(0, etter_backend_root)
            logger.debug(f"Added to sys.path: {etter_backend_root}")

        from settings.database import SessionLocal
        return SessionLocal()
    except ImportError as e:
        logger.debug(f"Parent database module not available: {e}")
        return None
    except Exception as e:
        logger.debug(f"Failed to get database session: {e}")
        return None


def _get_company_id_from_name(db: "Session", company_name: str) -> Optional[int]:
    """
    Get company ID from company name using parent models.

    Returns None if not found or parent package not available.
    """
    try:
        from models import MasterCompany
        company = db.query(MasterCompany).filter(
            MasterCompany.company_name == company_name
        ).first()
        if company:
            return company.id
        return None
    except Exception as e:
        logger.debug(f"Failed to get company ID: {e}")
        return None


class APIRoleTaxonomyProvider(RoleTaxonomyProvider):
    """
    API-based role taxonomy provider.

    Primary: HTTP API calls to /api/extraction/role_taxonomy/company/{company_id}
    Fallback: Direct database access when HTTP fails
    """

    def __init__(self, base_url: str = None, auth_token: str = None):
        """
        Initialize the API provider.

        Args:
            base_url: API base URL (defaults to localhost:7071)
            auth_token: Bearer token for auth (defaults to settings)
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_etter_backend_api_url()
        self.auth_token = auth_token or settings.etter_auth_token
        self._cache: Dict[str, List[RoleTaxonomyEntry]] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_roles_via_db(self, company_name: str, job_title: str = None, status_filter: str = None) -> List[Dict]:
        """
        Fallback: Fetch roles directly from database using parent models.

        Args:
            company_name: Company name
            job_title: Optional job title to filter
            status_filter: Optional approval_status filter

        Returns:
            List of role dicts from database
        """
        db = _get_db_session()
        if not db:
            logger.debug("Database session not available for fallback")
            return []

        try:
            from models.extraction import RoleTaxonomy

            # Get company ID from name
            company_id = _get_company_id_from_name(db, company_name)
            if not company_id:
                logger.warning(f"Company not found: {company_name}")
                return []

            # Build query
            query = db.query(RoleTaxonomy).filter(RoleTaxonomy.company_id == company_id)

            if job_title:
                query = query.filter(RoleTaxonomy.job_title.ilike(f"%{job_title}%"))
            if status_filter:
                query = query.filter(RoleTaxonomy.approval_status == status_filter)

            roles = query.all()
            logger.info(f"Fetched {len(roles)} roles from database (fallback)")

            # Convert to dict format matching API response
            return [
                {
                    "id": r.id,
                    "job_id": r.job_id,
                    "job_role": r.job_role,
                    "job_title": r.job_title,
                    "occupation": r.occupation,
                    "job_family": r.job_family,
                    "job_level": r.job_level,
                    "job_track": r.job_track,
                    "management_level": r.management_level,
                    "pay_grade": r.pay_grade,
                    "draup_role": r.draup_role,
                    "general_summary": r.general_summary,
                    "duties_responsibilities": r.duties_responsibilities,
                    "source": r.source,
                    "approval_status": r.approval_status,
                }
                for r in roles
            ]

        except ImportError:
            logger.debug("Parent models not available for database fallback")
            return []
        except Exception as e:
            logger.warning(f"Database fallback failed: {e}")
            return []
        finally:
            db.close()

    def _fetch_roles(self, company_name: str, job_title: str = None, status_filter: str = None) -> List[Dict]:
        """
        Fetch roles from API, with fallback to direct database access.

        Args:
            company_name: Company name
            job_title: Optional job title to filter
            status_filter: Optional approval_status filter

        Returns:
            List of role dicts from API or database
        """
        if not company_name:
            logger.warning("No company_name provided")
            return []

        # First, try the HTTP API
        # Try extraction endpoint which uses company_id
        db = _get_db_session()
        company_id = None
        if db:
            try:
                company_id = _get_company_id_from_name(db, company_name)
            finally:
                db.close()

        if company_id:
            url = f"{self.base_url}/api/extraction/role_taxonomy/company/{company_id}"
            params = {}
            if job_title:
                params["job_title"] = job_title
            if status_filter:
                params["status"] = status_filter

            try:
                logger.info(f"Fetching roles from {url} for company_id: {company_id}")
                response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                roles = data.get("data", [])
                logger.info(f"Fetched {len(roles)} roles from extraction API")
                return roles

            except Exception as e:
                logger.warning(f"HTTP API failed: {e}, trying database fallback...")

        # Fallback: Direct database access
        return self._fetch_roles_via_db(company_name, job_title, status_filter)

    def _convert_to_entry(self, role_data: Dict) -> RoleTaxonomyEntry:
        """Convert API response to RoleTaxonomyEntry."""
        return RoleTaxonomyEntry(
            job_id=str(role_data.get("job_id", role_data.get("id", ""))),
            job_role=role_data.get("job_role", ""),
            job_title=role_data.get("job_title", ""),
            occupation=role_data.get("occupation"),
            job_family=role_data.get("job_family"),
            job_level=role_data.get("job_level"),
            job_track=role_data.get("job_track"),
            management_level=role_data.get("management_level"),
            pay_grade=role_data.get("pay_grade"),
            draup_role=role_data.get("draup_role"),
            general_summary=role_data.get("general_summary"),
            duties_responsibilities=role_data.get("duties_responsibilities"),
            source=role_data.get("source", "api"),
            status=role_data.get("approval_status", "pending"),
        )

    def get_roles_for_company(
        self,
        company_name: str,
        status_filter: Optional[str] = None,
    ) -> List[RoleTaxonomyEntry]:
        """Get all roles for a company."""
        # Use cache if available
        cache_key = f"{company_name}:{status_filter or 'all'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        roles_data = self._fetch_roles(company_name, status_filter=status_filter)
        roles = [self._convert_to_entry(r) for r in roles_data]

        # Cache the results
        self._cache[cache_key] = roles
        return roles

    def get_role(
        self,
        company_name: str,
        job_title: str,
    ) -> Optional[RoleTaxonomyEntry]:
        """Get a specific role by job title."""
        # Use API-level filtering with job_title parameter for lower latency
        roles_data = self._fetch_roles(company_name, job_title=job_title)
        if roles_data:
            # Return first matching role
            return self._convert_to_entry(roles_data[0])
        return None

    def get_role_by_id(self, job_id: str) -> Optional[RoleTaxonomyEntry]:
        """Get a role by job ID (requires company context - not supported without it)."""
        # Note: This requires knowing which company to search
        # In practice, job_id queries should include company context
        logger.warning("get_role_by_id called without company context - not supported by API")
        return None

    def get_companies(self) -> List[str]:
        """Get list of companies (not supported by this API - returns empty)."""
        # The taxonomy API doesn't have a companies list endpoint
        # Companies are determined by the authenticated user's context
        return []


class APIDocumentProvider(DocumentProvider):
    """
    API-based document provider.

    Primary: HTTP API calls to /api/documents/ and /api/extraction/files
    Fallback: Direct database access when HTTP fails
    """

    def __init__(self, base_url: str = None, auth_token: str = None):
        """
        Initialize the API provider.

        Args:
            base_url: API base URL (defaults to localhost:7071)
            auth_token: Bearer token for auth (defaults to settings)
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_etter_backend_api_url()
        self.auth_token = auth_token or settings.etter_auth_token
        self._cache: Dict[str, DocumentRef] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_documents_via_db(
        self,
        roles: List[str] = None,
        company_instance_name: str = None,
        tenant_id: str = None,
    ) -> List[Dict]:
        """
        Fallback: Fetch documents directly from database using parent models.

        Uses Document and ExtractedDocument models to find documents
        that have been extracted and have the specified role.

        Args:
            roles: Filter by role names
            company_instance_name: Filter by company
            tenant_id: Tenant ID (company_id as string)

        Returns:
            List of document dicts from database
        """
        db = _get_db_session()
        if not db:
            logger.debug("Database session not available for document fallback")
            return []

        try:
            from models.s3 import Document, DocumentStatus
            from models.extraction import ExtractedDocument, ExtractionStatus
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import JSONB
            import json

            # Get tenant_id from company name if not provided
            if not tenant_id and company_instance_name:
                company_id = _get_company_id_from_name(db, company_instance_name)
                if company_id:
                    tenant_id = str(company_id)

            if not tenant_id:
                logger.warning("No tenant_id available for document query")
                return []

            # Build query: Document + ExtractedDocument join
            query = db.query(Document, ExtractedDocument).join(
                ExtractedDocument,
                Document.id == ExtractedDocument.document_id
            ).filter(
                Document.tenant_id == tenant_id,
                Document.status == DocumentStatus.READY,
                ExtractedDocument.status == ExtractionStatus.COMPLETED
            )

            # Filter by company_instance_name if provided
            if company_instance_name:
                query = query.filter(Document.company_instance_name == company_instance_name)

            # Filter by roles using JSONB containment
            if roles:
                role_array = json.dumps(roles)
                query = query.filter(
                    ExtractedDocument.roles.op('@>')(cast(role_array, JSONB))
                )

            results = query.order_by(Document.created_at.desc()).limit(1000).all()
            logger.info(f"Fetched {len(results)} documents from database (fallback)")

            # Convert to dict format matching API response
            docs = []
            for doc, extraction in results:
                docs.append({
                    "id": str(doc.id),
                    "original_filename": doc.original_filename,
                    "status": doc.status.value,
                    "observed_content_type": doc.observed_content_type,
                    "declared_content_type": doc.declared_content_type,
                    "observed_size_bytes": doc.observed_size_bytes,
                    "roles": extraction.roles or [],
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.completed_at.isoformat() if doc.completed_at else None,
                    "company_instance_name": doc.company_instance_name,
                })
            return docs

        except ImportError as e:
            logger.debug(f"Parent models not available for database fallback: {e}")
            return []
        except Exception as e:
            logger.warning(f"Database fallback failed for documents: {e}")
            return []
        finally:
            db.close()

    def _fetch_documents(
        self,
        roles: List[str] = None,
        company_instance_name: str = None,
        status: str = "ready",
    ) -> List[Dict]:
        """
        Fetch documents from API, with fallback to direct database access.

        Args:
            roles: Filter by role names
            company_instance_name: Filter by company
            status: Document status filter (default: ready)

        Returns:
            List of document dicts from API or database
        """
        # First, try the extraction/files endpoint (has roles filter)
        url = f"{self.base_url}/api/extraction/files"
        params = {"page_size": 1000}
        if roles:
            params["roles"] = roles[0]  # API takes single role
        if company_instance_name:
            params["company_instance_name"] = company_instance_name
        if status:
            params["status"] = "COMPLETED"  # Extraction status

        try:
            logger.info(f"Fetching documents from {url}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            # extraction/files returns files array with document_id
            files = data.get("files", [])
            if files:
                logger.info(f"Fetched {len(files)} documents from extraction API")
                # Convert to standard format
                return [
                    {
                        "id": f.get("document_id"),
                        "original_filename": f.get("original_filename"),
                        "status": f.get("document_status"),
                        "observed_content_type": f.get("content_type"),
                        "roles": [],  # Not included in extraction/files response
                        "created_at": f.get("created_at"),
                    }
                    for f in files
                ]

        except Exception as e:
            logger.warning(f"Extraction API failed: {e}, trying documents API...")

        # Try the S3 documents endpoint
        url = f"{self.base_url}/api/documents/"
        params = {"limit": 1000}
        if status:
            params["status"] = status

        try:
            logger.info(f"Fetching documents from {url}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            docs = data.get("data", {}).get("documents", [])
            logger.info(f"Fetched {len(docs)} documents from documents API")
            return docs

        except Exception as e:
            logger.warning(f"Documents API failed: {e}, trying database fallback...")

        # Fallback: Direct database access
        # Get tenant_id from auth token or company name
        tenant_id = None
        if company_instance_name:
            db = _get_db_session()
            if db:
                try:
                    company_id = _get_company_id_from_name(db, company_instance_name)
                    if company_id:
                        tenant_id = str(company_id)
                finally:
                    db.close()

        return self._fetch_documents_via_db(roles, company_instance_name, tenant_id)

    def _fetch_document_detail_via_db(self, document_id: str) -> Optional[Dict]:
        """
        Fallback: Fetch document details directly from database.

        Note: This does not generate a presigned download URL (requires S3 service).
        The document can still be used with document_id for content fetching.

        Args:
            document_id: Document UUID

        Returns:
            Document dict, or None
        """
        db = _get_db_session()
        if not db:
            logger.debug("Database session not available for document detail fallback")
            return None

        try:
            from models.s3 import Document
            from models.extraction import ExtractedDocument
            from uuid import UUID

            doc_uuid = UUID(document_id)
            doc = db.query(Document).filter(Document.id == doc_uuid).first()
            if not doc:
                logger.warning(f"Document not found in database: {document_id}")
                return None

            # Get extraction data for roles
            extraction = db.query(ExtractedDocument).filter(
                ExtractedDocument.document_id == doc_uuid
            ).first()

            logger.info(f"Fetched document detail from database (fallback): {doc.original_filename}")

            return {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "status": doc.status.value,
                "observed_content_type": doc.observed_content_type,
                "declared_content_type": doc.declared_content_type,
                "observed_size_bytes": doc.observed_size_bytes,
                "roles": extraction.roles if extraction else [],
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.completed_at.isoformat() if doc.completed_at else None,
                # Note: No download URL in fallback - requires S3 service
                "download": None,
            }

        except ImportError:
            logger.debug("Parent models not available for document detail fallback")
            return None
        except Exception as e:
            logger.warning(f"Database fallback failed for document detail: {e}")
            return None
        finally:
            db.close()

    def _fetch_document_detail(self, document_id: str) -> Optional[Dict]:
        """
        Fetch document details including download URL, with fallback to database.

        Args:
            document_id: Document UUID

        Returns:
            Document dict with download info, or None
        """
        url = f"{self.base_url}/api/documents/{document_id}"
        params = {"generate_download_url": "true"}

        try:
            logger.info(f"Fetching document detail for {document_id}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.warning(f"HTTP API failed for document detail: {e}, trying database fallback...")

        # Fallback: Direct database access (without download URL)
        return self._fetch_document_detail_via_db(document_id)

    def _convert_to_ref(self, doc_data: Dict) -> DocumentRef:
        """Convert API response to DocumentRef."""
        # Determine document type from filename or content type
        filename = doc_data.get("original_filename", "").lower()
        content_type = doc_data.get("observed_content_type", "")

        doc_type = DocumentType.OTHER
        if "job" in filename or "jd" in filename or "description" in filename:
            doc_type = DocumentType.JOB_DESCRIPTION
        elif "process" in filename or "map" in filename:
            doc_type = DocumentType.PROCESS_MAP
        elif "sop" in filename:
            doc_type = DocumentType.SOP

        # Get download URL if available
        download_url = None
        download_info = doc_data.get("download")
        if download_info and download_info.get("url"):
            download_url = download_info["url"]

        return DocumentRef(
            type=doc_type,
            uri=download_url or f"api://documents/{doc_data.get('id')}",
            name=doc_data.get("original_filename"),
            content=None,  # Content extraction handled downstream
            metadata={
                "id": doc_data.get("id"),
                "status": doc_data.get("status"),
                "roles": doc_data.get("roles", []),
                "content_type": content_type,
                "download_url": download_url,
                "updated_at": doc_data.get("updated_at"),
                "created_at": doc_data.get("created_at"),
            }
        )

    def get_document(
        self,
        company_name: str,
        role_name: str,
        doc_type: DocumentType,
    ) -> Optional[DocumentRef]:
        """Get a document for a role."""
        # Fetch documents filtered by role
        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)

        for doc in docs:
            ref = self._convert_to_ref(doc)
            if ref.type == doc_type:
                # Fetch detail to get download URL
                detail = self._fetch_document_detail(doc.get("id"))
                if detail:
                    return self._convert_to_ref(detail)
                return ref

        return None

    def get_documents_for_role(
        self,
        company_name: str,
        role_name: str,
    ) -> List[DocumentRef]:
        """Get all documents for a role."""
        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)
        return [self._convert_to_ref(doc) for doc in docs]

    def _get_file_type_priority(self, doc: Dict) -> int:
        """
        Get file type priority for sorting.

        Priority order (lower number = higher priority):
        1. PDF (priority 1)
        2. DOCX/DOC (priority 2)
        3. Images - PNG, JPG, JPEG (priority 3)
        4. Other (priority 99)

        Args:
            doc: Document dict with original_filename and/or observed_content_type

        Returns:
            Priority number (lower = better)
        """
        filename = doc.get("original_filename", "").lower()
        content_type = doc.get("observed_content_type", "").lower()

        # PDF - highest priority
        if filename.endswith(".pdf") or "pdf" in content_type:
            return 1

        # DOCX/DOC - second priority
        if filename.endswith((".docx", ".doc")) or "word" in content_type or "document" in content_type:
            return 2

        # Images - third priority
        image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")
        if filename.endswith(image_extensions) or content_type.startswith("image/"):
            return 3

        # Other - lowest priority
        return 99

    def get_best_document_for_role(
        self,
        role_name: str,
        company_name: str = None,
    ) -> Optional[DocumentRef]:
        """
        Get the best document for a role with intelligent filtering.

        Logic:
        1. Filter to documents where roles == [role_name] exactly (not mixed with other roles)
        2. Sort by file type priority (PDF > DOCX > images > other)
        3. Within same file type, sort by date (latest first)
        4. Deduplicate by filename (take the latest if duplicates exist)
        5. Return the best document with download URL

        Args:
            role_name: Role name to filter by
            company_name: Optional company name to filter

        Returns:
            Best matching DocumentRef with download URL, or None
        """
        # Fetch documents filtered by role
        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)

        if not docs:
            logger.warning(f"No documents found for role: {role_name}")
            return None

        logger.info(f"Found {len(docs)} documents for role {role_name}")

        # Filter to documents where roles is exactly [role_name]
        exact_match_docs = []
        for doc in docs:
            doc_roles = doc.get("roles", [])
            if doc_roles == [role_name]:
                exact_match_docs.append(doc)
                logger.debug(f"Exact match: {doc.get('original_filename')} - roles: {doc_roles}")
            else:
                logger.debug(f"Skipped (mixed roles): {doc.get('original_filename')} - roles: {doc_roles}")

        if not exact_match_docs:
            logger.warning(f"No documents with exact role match [{role_name}], using all documents")
            exact_match_docs = docs

        logger.info(f"Exact match documents: {len(exact_match_docs)}")

        # Helper to get date for sorting
        def get_date_key(doc):
            for field in ["updated_at", "created_at", "uploaded_at"]:
                if doc.get(field):
                    try:
                        return datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
            return datetime.min

        # Sort by: 1) file type priority (lower = better), 2) date (latest first)
        exact_match_docs.sort(key=lambda doc: (self._get_file_type_priority(doc), -get_date_key(doc).timestamp()))

        # Log the sorted order with priorities
        for doc in exact_match_docs[:5]:  # Log top 5
            priority = self._get_file_type_priority(doc)
            logger.debug(f"Sorted: {doc.get('original_filename')} - priority: {priority}, date: {get_date_key(doc)}")

        # Deduplicate by filename (keep the first/best)
        seen_filenames = {}
        deduped_docs = []
        for doc in exact_match_docs:
            filename = doc.get("original_filename", "")
            if filename not in seen_filenames:
                seen_filenames[filename] = True
                deduped_docs.append(doc)
                logger.debug(f"Keeping: {filename} (priority: {self._get_file_type_priority(doc)})")
            else:
                logger.debug(f"Skipped (duplicate): {filename}")

        logger.info(f"After deduplication: {len(deduped_docs)} documents")

        if not deduped_docs:
            return None

        # Take the first (best priority, latest) document
        best_doc = deduped_docs[0]
        priority = self._get_file_type_priority(best_doc)
        logger.info(f"Selected best document: {best_doc.get('original_filename')} (id: {best_doc.get('id')}, priority: {priority})")

        # Fetch document detail to get download URL
        detail = self._fetch_document_detail(best_doc.get("id"))
        if detail:
            return self._convert_to_ref(detail)

        return self._convert_to_ref(best_doc)

    def get_document_content(
        self,
        doc_ref: DocumentRef,
    ) -> Optional[str]:
        """
        Get the content of a document.

        For API-based provider, content is typically fetched via the download URL.
        This method downloads the content if a URI is available.

        Args:
            doc_ref: Document reference with URI

        Returns:
            Document content as string, or None if not available
        """
        # If content is already available, return it
        if doc_ref.content:
            return doc_ref.content

        # If no URI, we can't fetch content
        if not doc_ref.uri:
            logger.warning(f"No URI available for document: {doc_ref.name}")
            return None

        # Skip API-style URIs (these need special handling downstream)
        if doc_ref.uri.startswith("api://"):
            logger.debug(f"Document has API URI, content will be fetched downstream: {doc_ref.uri}")
            return None

        # Try to download content from URI (presigned URL)
        try:
            logger.info(f"Fetching document content from URI: {doc_ref.uri[:80]}...")
            response = requests.get(doc_ref.uri, timeout=60)
            response.raise_for_status()

            # For text-based content, return as string
            content_type = response.headers.get("Content-Type", "")
            if "text" in content_type or "json" in content_type:
                return response.text

            # For binary content (PDF, DOCX), return as base64 or None
            # (downstream processors handle binary formats)
            logger.debug(f"Document is binary ({content_type}), content extraction handled downstream")
            return None

        except Exception as e:
            logger.warning(f"Failed to fetch document content: {e}")
            return None
