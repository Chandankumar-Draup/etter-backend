"""
API-based providers for documents and role taxonomy.

These providers call the real APIs instead of using mock data.
They implement the same interfaces as the mock providers.

APIs used:
- GET /api/documents/ - List documents
- GET /api/documents/{id}?generate_download_url=true - Get document with download URL
- GET /api/extraction/files - List extracted files with roles filter
"""

import logging
import requests
from contextvars import ContextVar
from typing import Dict, List, Optional
from datetime import datetime

from etter_workflows.mock_data.role_taxonomy import RoleTaxonomyProvider
from etter_workflows.mock_data.documents import DocumentProvider
from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)

# Context variable for propagating auth token from incoming requests to internal API calls
# This allows internal HTTP calls to use the same auth as the original request
auth_token_context: ContextVar[Optional[str]] = ContextVar('auth_token', default=None)


class APIRoleTaxonomyProvider(RoleTaxonomyProvider):
    """
    API-based role taxonomy provider.

    Calls the extraction API to fetch role taxonomy data.
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
        """Get request headers with auth.

        Uses auth token from context (propagated from incoming request) if available,
        otherwise falls back to configured auth token.
        """
        headers = {"Content-Type": "application/json"}
        # First check context for propagated auth token from incoming request
        context_token = auth_token_context.get()
        if context_token:
            headers["Authorization"] = context_token
        elif self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_roles(self, company_name: str, job_title: str = None, status_filter: str = None) -> List[Dict]:
        """
        Fetch roles from API.

        Args:
            company_name: Company name (used for logging, API uses auth token for tenant)
            job_title: Optional job title to filter
            status_filter: Optional approval_status filter

        Returns:
            List of role dicts from API
        """
        if not company_name:
            logger.warning("No company_name provided")
            return []

        # Use extraction/role_taxonomy endpoint
        url = f"{self.base_url}/api/extraction/role_taxonomy/company/0"  # company_id from auth
        params = {}
        if job_title:
            params["job_title"] = job_title
        if status_filter:
            params["status"] = status_filter

        try:
            logger.info(f"Fetching roles from {url}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            roles = data.get("data", [])
            logger.info(f"Fetched {len(roles)} roles from API")
            return roles

        except requests.exceptions.HTTPError as e:
            # Log as warning since taxonomy is optional - workflow can proceed without it
            logger.warning(
                f"Role taxonomy API returned error (taxonomy data is optional, workflow will continue): "
                f"status={e.response.status_code if e.response else 'unknown'}, error={e}"
            )
            return []
        except Exception as e:
            # Log as warning since taxonomy is optional
            logger.warning(f"Failed to fetch role taxonomy (optional, workflow will continue): {e}")
            return []

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
        roles_data = self._fetch_roles(company_name, job_title=job_title)
        if roles_data:
            return self._convert_to_entry(roles_data[0])
        return None

    def get_role_by_id(self, job_id: str) -> Optional[RoleTaxonomyEntry]:
        """Get a role by job ID (requires company context - not supported without it)."""
        logger.warning("get_role_by_id called without company context - not supported by API")
        return None

    def get_companies(self) -> List[str]:
        """Get list of companies (not supported by this API - returns empty)."""
        return []


class APIDocumentProvider(DocumentProvider):
    """
    API-based document provider.

    Calls GET /api/documents/ and /api/extraction/files to fetch document metadata.
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
        """Get request headers with auth.

        Uses auth token from context (propagated from incoming request) if available,
        otherwise falls back to configured auth token.
        """
        headers = {"Content-Type": "application/json"}
        # First check context for propagated auth token from incoming request
        context_token = auth_token_context.get()
        if context_token:
            headers["Authorization"] = context_token
        elif self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_documents(
        self,
        roles: List[str] = None,
        company_instance_name: str = None,
        status: str = "ready",
    ) -> List[Dict]:
        """
        Fetch documents from API.

        Args:
            roles: Filter by role names
            company_instance_name: Filter by company
            status: Document status filter (default: ready)

        Returns:
            List of document dicts from API
        """
        # Try the extraction/files endpoint first (has roles filter)
        url = f"{self.base_url}/api/extraction/files"
        params = {"page_size": 1000}
        if roles:
            params["roles"] = roles[0]  # API takes single role
        if company_instance_name:
            params["company_instance_name"] = company_instance_name
        if status:
            params["status"] = "COMPLETED"  # Extraction status

        try:
            logger.info(f"[DOC_FETCH] Fetching documents from extraction API: {url}")
            logger.info(f"[DOC_FETCH] Request params: {params}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            files = data.get("files", [])
            logger.info(f"[DOC_FETCH] Extraction API response: {len(files)} files found")
            if files:
                for f in files[:5]:  # Log first 5 files
                    logger.info(f"[DOC_FETCH]   - {f.get('original_filename')} (id={f.get('document_id')}, status={f.get('document_status')})")
                return [
                    {
                        "id": f.get("document_id"),
                        "original_filename": f.get("original_filename"),
                        "status": f.get("document_status"),
                        "observed_content_type": f.get("content_type"),
                        "roles": [],
                        "created_at": f.get("created_at"),
                    }
                    for f in files
                ]

        except Exception as e:
            logger.warning(f"[DOC_FETCH] Extraction API failed: {e}, trying documents API...")

        # Fallback to S3 documents endpoint
        url = f"{self.base_url}/api/documents/"
        params = {"limit": 1000}
        if roles:
            params["roles"] = ",".join(roles)
        if status:
            params["status"] = status

        try:
            logger.info(f"[DOC_FETCH] Fetching documents from documents API: {url}")
            logger.info(f"[DOC_FETCH] Request params: {params}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            docs = data.get("data", {}).get("documents", [])
            logger.info(f"[DOC_FETCH] Documents API response: {len(docs)} documents found")
            for doc in docs[:5]:  # Log first 5 docs
                logger.info(f"[DOC_FETCH]   - {doc.get('original_filename')} (id={doc.get('id')}, status={doc.get('status')})")
            return docs

        except Exception as e:
            logger.error(f"[DOC_FETCH] Failed to fetch documents from API: {e}")
            return []

    def _fetch_document_detail(self, document_id: str) -> Optional[Dict]:
        """
        Fetch document details including download URL.

        Args:
            document_id: Document UUID

        Returns:
            Document dict with download info, or None
        """
        url = f"{self.base_url}/api/documents/{document_id}"
        params = {"generate_download_url": "true"}

        try:
            logger.info(f"[DOC_DETAIL] Fetching document detail: {url}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()
            detail = response.json()
            logger.info(f"[DOC_DETAIL] Document detail retrieved:")
            logger.info(f"[DOC_DETAIL]   - filename: {detail.get('original_filename')}")
            logger.info(f"[DOC_DETAIL]   - content_type: {detail.get('observed_content_type')}")
            logger.info(f"[DOC_DETAIL]   - has_download_url: {bool(detail.get('download', {}).get('url'))}")
            return detail

        except Exception as e:
            logger.error(f"[DOC_DETAIL] Failed to fetch document detail: {e}")
            return None

    def _convert_to_ref(self, doc_data: Dict) -> DocumentRef:
        """Convert API response to DocumentRef."""
        filename = doc_data.get("original_filename", "").lower()
        content_type = doc_data.get("observed_content_type", "")

        doc_type = DocumentType.OTHER
        if "job" in filename or "jd" in filename or "description" in filename:
            doc_type = DocumentType.JOB_DESCRIPTION
        elif "process" in filename or "map" in filename:
            doc_type = DocumentType.PROCESS_MAP
        elif "sop" in filename:
            doc_type = DocumentType.SOP

        download_url = None
        download_info = doc_data.get("download")
        if download_info and download_info.get("url"):
            download_url = download_info["url"]

        doc_id = doc_data.get("id")
        uri = download_url or f"api://documents/{doc_id}"

        logger.info(f"[DOC_CONVERT] Converting document to ref:")
        logger.info(f"[DOC_CONVERT]   - filename: {doc_data.get('original_filename')}")
        logger.info(f"[DOC_CONVERT]   - detected_type: {doc_type} (from filename pattern)")
        logger.info(f"[DOC_CONVERT]   - has_download_url: {bool(download_url)}")
        logger.info(f"[DOC_CONVERT]   - uri: {uri}")

        return DocumentRef(
            type=doc_type,
            uri=uri,
            name=doc_data.get("original_filename"),
            content=None,
            metadata={
                "id": doc_id,
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
        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)

        for doc in docs:
            ref = self._convert_to_ref(doc)
            if ref.type == doc_type:
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
        Get file type priority for sorting (lower = better).

        Priority: PDF (1) > DOCX (2) > Images (3) > Other (99)
        """
        filename = doc.get("original_filename", "").lower()
        content_type = doc.get("observed_content_type", "").lower()

        if filename.endswith(".pdf") or "pdf" in content_type:
            return 1
        if filename.endswith((".docx", ".doc")) or "word" in content_type:
            return 2
        if filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")) or content_type.startswith("image/"):
            return 3
        return 99

    def get_best_document_for_role(
        self,
        role_name: str,
        company_name: str = None,
    ) -> Optional[DocumentRef]:
        """
        Get the best document for a role.

        Logic:
        1. Filter to exact role match where possible
        2. Sort by file type priority (PDF > DOCX > images)
        3. Return best document with download URL
        """
        logger.info(f"[BEST_DOC] ========== Getting best document for role ==========")
        logger.info(f"[BEST_DOC] Role: {role_name}, Company: {company_name}")

        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)

        if not docs:
            logger.warning(f"[BEST_DOC] No documents found for role: {role_name}")
            return None

        logger.info(f"[BEST_DOC] Found {len(docs)} documents for role {role_name}")

        # Filter to exact role match
        exact_match_docs = [d for d in docs if d.get("roles") == [role_name]]
        logger.info(f"[BEST_DOC] Exact role matches: {len(exact_match_docs)}")
        if not exact_match_docs:
            logger.warning(f"[BEST_DOC] No exact role match [{role_name}], using all documents")
            exact_match_docs = docs

        # Sort by priority
        def get_date_key(doc):
            for field in ["updated_at", "created_at"]:
                if doc.get(field):
                    try:
                        return datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
            return datetime.min

        exact_match_docs.sort(key=lambda d: (self._get_file_type_priority(d), -get_date_key(d).timestamp()))
        logger.info(f"[BEST_DOC] After sorting by priority (PDF>DOCX>Image>Other):")
        for i, doc in enumerate(exact_match_docs[:3]):
            logger.info(f"[BEST_DOC]   {i+1}. {doc.get('original_filename')} (priority={self._get_file_type_priority(doc)})")

        # Deduplicate by filename
        seen = set()
        deduped = []
        for doc in exact_match_docs:
            fn = doc.get("original_filename", "")
            if fn not in seen:
                seen.add(fn)
                deduped.append(doc)

        logger.info(f"[BEST_DOC] After deduplication: {len(deduped)} unique documents")

        if not deduped:
            logger.warning(f"[BEST_DOC] No documents after deduplication")
            return None

        best_doc = deduped[0]
        logger.info(f"[BEST_DOC] Selected best document: {best_doc.get('original_filename')} (id={best_doc.get('id')})")

        detail = self._fetch_document_detail(best_doc.get("id"))
        doc_ref = self._convert_to_ref(detail) if detail else self._convert_to_ref(best_doc)

        # Force type to JOB_DESCRIPTION when auto-fetching for role processing
        # This is the primary use case - the best document for a role IS the job description
        if doc_ref.type != DocumentType.JOB_DESCRIPTION:
            logger.info(f"[BEST_DOC] Forcing document type to JOB_DESCRIPTION (was {doc_ref.type})")
            doc_ref = DocumentRef(
                type=DocumentType.JOB_DESCRIPTION,
                uri=doc_ref.uri,
                name=doc_ref.name,
                content=doc_ref.content,
                metadata=doc_ref.metadata,
            )

        logger.info(f"[BEST_DOC] Final document ref:")
        logger.info(f"[BEST_DOC]   - name: {doc_ref.name}")
        logger.info(f"[BEST_DOC]   - type: {doc_ref.type}")
        logger.info(f"[BEST_DOC]   - uri: {doc_ref.uri[:100]}..." if len(doc_ref.uri or '') > 100 else f"[BEST_DOC]   - uri: {doc_ref.uri}")
        logger.info(f"[BEST_DOC] ========== End getting best document ==========")

        return doc_ref

    def get_document_content(
        self,
        doc_ref: DocumentRef,
    ) -> Optional[str]:
        """
        Get the content of a document.

        For API-based provider, content is fetched via the download URL.
        """
        if doc_ref.content:
            return doc_ref.content

        if not doc_ref.uri:
            logger.warning(f"No URI available for document: {doc_ref.name}")
            return None

        if doc_ref.uri.startswith("api://"):
            logger.debug(f"Document has API URI, content fetched downstream: {doc_ref.uri}")
            return None

        try:
            logger.info(f"Fetching document content from URI")
            response = requests.get(doc_ref.uri, timeout=60)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "text" in content_type or "json" in content_type:
                return response.text

            logger.debug(f"Document is binary ({content_type}), handled downstream")
            return None

        except Exception as e:
            logger.warning(f"Failed to fetch document content: {e}")
            return None
