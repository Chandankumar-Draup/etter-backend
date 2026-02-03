"""
Mock data providers for Etter Workflows.

Provides mock data for development and testing:
- role_taxonomy: Mock role taxonomy data (mirrors platform API format)
- documents: Mock document data (JDs, process maps)

These providers are designed to be easily replaced with real API calls
by implementing the same interface.
"""

from etter_workflows.mock_data.role_taxonomy import (
    RoleTaxonomyProvider,
    MockRoleTaxonomyProvider,
    get_role_taxonomy_provider,
)
from etter_workflows.mock_data.documents import (
    DocumentProvider,
    MockDocumentProvider,
    get_document_provider,
)

__all__ = [
    "RoleTaxonomyProvider",
    "MockRoleTaxonomyProvider",
    "get_role_taxonomy_provider",
    "DocumentProvider",
    "MockDocumentProvider",
    "get_document_provider",
]
