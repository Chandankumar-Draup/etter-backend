"""
API-based providers for documents and role taxonomy.

These providers call the real APIs instead of using mock data.
They implement the same interfaces as the mock providers.

APIs used:
- GET /api/documents/ - List documents
- GET /api/documents/{id}?generate_download_url=true - Get document with download URL
- GET /api/taxonomy/roles?company_name=<company_name>&job_title=<job_title> - List role taxonomy
"""

import io
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

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
        self._cache: Dict[str, List[RoleTaxonomyEntry]] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _fetch_roles(self, company_name: str, job_title: str = None, status_filter: str = None) -> List[Dict]:
        """
        Fetch roles from API.

        Args:
            company_name: Company name
            job_title: Optional job title to filter
            status_filter: Optional approval_status filter

        Returns:
            List of role dicts from API
        """
        if not company_name:
            logger.warning("No company_name provided")
            return []

        url = f"{self.base_url}/api/taxonomy/roles"
        # API uses company_name and job_title parameters for filtering
        params = {"company_name": company_name}
        if job_title:
            params["job_title"] = job_title
        if status_filter:
            params["approval_status"] = status_filter

        try:
            logger.info(f"Fetching roles from {url} for company: {company_name}, job_title: {job_title}")
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

    def _fetch_document_content(self, document_id: str, convert_to_markdown: bool = False) -> Optional[str]:
        """
        Fetch document content via download URL.

        Args:
            document_id: Document UUID
            convert_to_markdown: If True, convert PDF content to Markdown using LLM

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
            filename = data.get("original_filename", "").lower()
            content_type = data.get("observed_content_type", "")

            if download_info and download_info.get("url"):
                download_url = download_info["url"]
                logger.info(f"Downloading content from presigned URL for {filename}")

                # Fetch content from presigned URL
                content_response = requests.get(download_url, timeout=60)
                content_response.raise_for_status()

                # Check if it's a PDF file
                is_pdf = filename.endswith('.pdf') or 'pdf' in content_type.lower()

                if is_pdf:
                    # Parse PDF content
                    raw_text = self._extract_pdf_content(content_response.content)
                    if raw_text and convert_to_markdown:
                        # Convert to Markdown using LLM
                        return self._convert_to_markdown_with_llm(raw_text, filename)
                    return raw_text
                else:
                    # Return text content directly
                    return content_response.text

            return None

        except Exception as e:
            logger.error(f"Failed to fetch document content: {e}")
            return None

    def _extract_pdf_content(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Extract text content from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Extracted text content, or None
        """
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                pdf_file = io.BytesIO(pdf_bytes)
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                if text_parts:
                    content = "\n\n".join(text_parts)
                    logger.info(f"Extracted {len(content)} chars from PDF using PyPDF2")
                    return content
            except ImportError:
                logger.warning("PyPDF2 not installed, trying pdfplumber")

            # Try pdfplumber as fallback
            try:
                import pdfplumber
                pdf_file = io.BytesIO(pdf_bytes)
                with pdfplumber.open(pdf_file) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)

                    if text_parts:
                        content = "\n\n".join(text_parts)
                        logger.info(f"Extracted {len(content)} chars from PDF using pdfplumber")
                        return content
            except ImportError:
                logger.warning("pdfplumber not installed")

            logger.error("No PDF parser available. Install PyPDF2 or pdfplumber: pip install PyPDF2")
            return None

        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            return None

    def _convert_to_markdown_with_llm(self, raw_text: str, filename: str = "") -> str:
        """
        Convert raw document text to formatted Markdown using LLM.

        Args:
            raw_text: Raw extracted text from document
            filename: Original filename for context

        Returns:
            Formatted Markdown content
        """
        try:
            settings = get_settings()

            # Check for Gemini API (default LLM)
            if settings.llm_provider == "gemini" and settings.llm_api_key:
                return self._convert_with_gemini(raw_text, filename, settings)

            # Check for OpenAI API
            elif settings.llm_provider == "openai" and settings.llm_api_key:
                return self._convert_with_openai(raw_text, filename, settings)

            else:
                logger.warning("No LLM API key configured, returning raw text")
                return raw_text

        except Exception as e:
            logger.error(f"Failed to convert to Markdown with LLM: {e}")
            return raw_text

    def _convert_with_gemini(self, raw_text: str, filename: str, settings) -> str:
        """Convert text to Markdown using Google Gemini API."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.llm_api_key)
            model = genai.GenerativeModel(settings.llm_model or "gemini-2.0-flash")

            prompt = f"""Convert the following job description document to well-formatted Markdown.

Document: {filename}

Instructions:
- Preserve all important information
- Use proper Markdown headings (##, ###)
- Use bullet points for lists
- Format requirements, responsibilities, qualifications as separate sections
- Clean up any OCR artifacts or formatting issues
- Keep the content professional and readable

Raw Content:
{raw_text}

Formatted Markdown:"""

            response = model.generate_content(prompt)
            if response.text:
                logger.info(f"Converted to Markdown using Gemini ({len(response.text)} chars)")
                return response.text

            return raw_text

        except ImportError:
            logger.error("google-generativeai not installed: pip install google-generativeai")
            return raw_text
        except Exception as e:
            logger.error(f"Gemini conversion failed: {e}")
            return raw_text

    def _convert_with_openai(self, raw_text: str, filename: str, settings) -> str:
        """Convert text to Markdown using OpenAI API."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.llm_api_key)

            prompt = f"""Convert the following job description document to well-formatted Markdown.

Document: {filename}

Instructions:
- Preserve all important information
- Use proper Markdown headings (##, ###)
- Use bullet points for lists
- Format requirements, responsibilities, qualifications as separate sections
- Clean up any OCR artifacts or formatting issues
- Keep the content professional and readable

Raw Content:
{raw_text}"""

            response = client.chat.completions.create(
                model=settings.llm_model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a document formatter. Convert raw text to clean Markdown."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
            )

            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                logger.info(f"Converted to Markdown using OpenAI ({len(content)} chars)")
                return content

            return raw_text

        except ImportError:
            logger.error("openai not installed: pip install openai")
            return raw_text
        except Exception as e:
            logger.error(f"OpenAI conversion failed: {e}")
            return raw_text

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

    def get_best_document_for_role(
        self,
        role_name: str,
        company_name: str = None,
        convert_to_markdown: bool = False,
    ) -> Optional[DocumentRef]:
        """
        Get the best document for a role with intelligent filtering.

        Logic:
        1. Filter to documents where roles == [role_name] exactly (not mixed with other roles)
        2. Sort by date (latest first based on updated_at or created_at)
        3. Deduplicate by filename (take the latest if duplicates exist)
        4. Return the best document with content extracted

        Args:
            role_name: Role name to filter by
            company_name: Optional company name to filter
            convert_to_markdown: If True, convert PDF content to Markdown using LLM

        Returns:
            Best matching DocumentRef with content, or None
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

        # Sort by date (latest first)
        # Try updated_at, then created_at, then id as fallback
        def get_date_key(doc):
            for field in ["updated_at", "created_at", "uploaded_at"]:
                if doc.get(field):
                    try:
                        return datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
            return datetime.min

        exact_match_docs.sort(key=get_date_key, reverse=True)

        # Deduplicate by filename (keep the latest)
        seen_filenames = {}
        deduped_docs = []
        for doc in exact_match_docs:
            filename = doc.get("original_filename", "")
            if filename not in seen_filenames:
                seen_filenames[filename] = True
                deduped_docs.append(doc)
                logger.debug(f"Keeping (latest): {filename}")
            else:
                logger.debug(f"Skipped (duplicate): {filename}")

        logger.info(f"After deduplication: {len(deduped_docs)} documents")

        if not deduped_docs:
            return None

        # Take the first (latest) document
        best_doc = deduped_docs[0]
        logger.info(f"Selected best document: {best_doc.get('original_filename')} (id: {best_doc.get('id')})")

        # Fetch content
        content = self._fetch_document_content(
            best_doc.get("id"),
            convert_to_markdown=convert_to_markdown
        )

        # Create DocumentRef
        ref = self._convert_to_ref(best_doc, content=content)
        return ref

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
