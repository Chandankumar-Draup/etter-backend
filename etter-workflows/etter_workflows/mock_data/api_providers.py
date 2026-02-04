"""
API-based providers for documents and role taxonomy.

These providers call the real APIs instead of using mock data.
They implement the same interfaces as the mock providers.

APIs used:
- GET /api/documents/ - List documents
- GET /api/documents/{id}?generate_download_url=true - Get document with download URL
- GET /api/taxonomy/roles?company_id=<id> - List role taxonomy
"""

import logging
import requests
from typing import Dict, List, Optional, Any

from etter_workflows.mock_data.role_taxonomy import RoleTaxonomyProvider
from etter_workflows.mock_data.documents import DocumentProvider
from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class APIRoleTaxonomyProvider(RoleTaxonomyProvider):
    """
    API-based role taxonomy provider.

    Calls GET /api/taxonomy/roles to fetch role data.
    """

    def __init__(self, base_url: str = None, auth_token: str = None, company_id: int = None):
        """
        Initialize the API provider.

        Args:
            base_url: API base URL (defaults to settings)
            auth_token: Bearer token for auth (defaults to settings)
            company_id: Company ID for taxonomy queries (defaults to settings)
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_automated_workflows_api_url()
        self.auth_token = auth_token or settings.etter_auth_token
        self.company_id = company_id or getattr(settings, 'company_id', None)
        self._cache: Dict[str, List[RoleTaxonomyEntry]] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_roles(self, company_id: int = None, status_filter: str = None) -> List[Dict]:
        """
        Fetch roles from API.

        Args:
            company_id: Company ID (uses self.company_id if not provided)
            status_filter: Optional approval_status filter

        Returns:
            List of role dicts from API
        """
        cid = company_id or self.company_id
        if not cid:
            logger.warning("No company_id configured for taxonomy API")
            return []

        url = f"{self.base_url}/api/taxonomy/roles"
        params = {"company_id": cid, "page_size": 200}
        if status_filter:
            params["approval_status"] = status_filter

        try:
            logger.info(f"Fetching roles from {url} for company_id={cid}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            roles = data.get("data", [])
            logger.info(f"Fetched {len(roles)} roles from taxonomy API")
            return roles

        except Exception as e:
            logger.error(f"Failed to fetch roles from API: {e}")
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
        # Note: API uses company_id, not company_name
        # For now, we use the configured company_id
        roles_data = self._fetch_roles(status_filter=status_filter)
        return [self._convert_to_entry(r) for r in roles_data]

    def get_role(
        self,
        company_name: str,
        job_title: str,
    ) -> Optional[RoleTaxonomyEntry]:
        """Get a specific role by job title."""
        roles = self.get_roles_for_company(company_name)
        for role in roles:
            if role.job_title.lower() == job_title.lower():
                return role
            if role.job_role.lower() == job_title.lower():
                return role
        return None

    def get_role_by_id(self, job_id: str) -> Optional[RoleTaxonomyEntry]:
        """Get a role by job ID."""
        # Would need to fetch all and filter, or have a dedicated endpoint
        roles = self.get_roles_for_company("")
        for role in roles:
            if role.job_id == job_id:
                return role
        return None

    def get_companies(self) -> List[str]:
        """Get list of companies (not directly supported by API)."""
        # This would need a separate endpoint or configuration
        return []


class APIDocumentProvider(DocumentProvider):
    """
    API-based document provider.

    Calls GET /api/documents/ to fetch documents.
    """

    def __init__(self, base_url: str = None, auth_token: str = None):
        """
        Initialize the API provider.

        Args:
            base_url: API base URL (defaults to settings)
            auth_token: Bearer token for auth (defaults to settings)
        """
        settings = get_settings()
        self.base_url = base_url or settings.get_automated_workflows_api_url()
        self.auth_token = auth_token or settings.etter_auth_token
        self._cache: Dict[str, DocumentRef] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
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
        url = f"{self.base_url}/api/documents/"
        params = {"limit": 1000}
        if roles:
            params["roles"] = ",".join(roles)
        if company_instance_name:
            params["company_instance_name"] = company_instance_name
        if status:
            params["status"] = status

        try:
            logger.info(f"Fetching documents from {url}")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            docs = data.get("data", {}).get("documents", [])
            logger.info(f"Fetched {len(docs)} documents from API")
            return docs

        except Exception as e:
            logger.error(f"Failed to fetch documents from API: {e}")
            return []

    def _fetch_document_content(self, document_id: str) -> Optional[str]:
        """
        Fetch document content via download URL.

        Args:
            document_id: Document UUID

        Returns:
            Document content as string, or None
        """
        url = f"{self.base_url}/api/documents/{document_id}"
        params = {"generate_download_url": "true"}

        try:
            logger.info(f"Fetching document {document_id} with download URL")
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            download_info = data.get("download")

            if download_info and download_info.get("url"):
                # Fetch content from presigned URL
                content_response = requests.get(download_info["url"], timeout=60)
                content_response.raise_for_status()
                return content_response.text

            return None

        except Exception as e:
            logger.error(f"Failed to fetch document content: {e}")
            return None

    def _convert_to_ref(self, doc_data: Dict, content: str = None) -> DocumentRef:
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

        return DocumentRef(
            type=doc_type,
            uri=f"api://documents/{doc_data.get('id')}",
            name=doc_data.get("original_filename"),
            content=content,
            metadata={
                "id": doc_data.get("id"),
                "status": doc_data.get("status"),
                "roles": doc_data.get("roles", []),
                "content_type": content_type,
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
                # Fetch content
                content = self._fetch_document_content(doc.get("id"))
                if content:
                    ref.content = content
                    return ref

        return None

    def get_documents_for_role(
        self,
        company_name: str,
        role_name: str,
    ) -> List[DocumentRef]:
        """Get all documents for a role."""
        docs = self._fetch_documents(roles=[role_name], company_instance_name=company_name)

        result = []
        for doc in docs:
            ref = self._convert_to_ref(doc)
            # Optionally fetch content for each
            content = self._fetch_document_content(doc.get("id"))
            if content:
                ref.content = content
            result.append(ref)

        return result

    def get_document_content(self, doc_ref: DocumentRef) -> Optional[str]:
        """Get the content of a document."""
        if doc_ref.content:
            return doc_ref.content

        # Extract document ID from metadata or URI
        doc_id = None
        if doc_ref.metadata and "id" in doc_ref.metadata:
            doc_id = doc_ref.metadata["id"]
        elif doc_ref.uri and doc_ref.uri.startswith("api://documents/"):
            doc_id = doc_ref.uri.replace("api://documents/", "")

        if doc_id:
            return self._fetch_document_content(doc_id)

        return None
