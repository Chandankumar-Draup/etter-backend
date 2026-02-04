"""
Data providers for Etter Workflows.

Provides data for development, testing, and production:
- role_taxonomy: Role taxonomy data (mock or API)
- documents: Document data (mock or API)

Provider selection:
- enable_mock_data=True: Uses MockRoleTaxonomyProvider/MockDocumentProvider
- enable_mock_data=False: Uses APIRoleTaxonomyProvider/APIDocumentProvider
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
from etter_workflows.mock_data.api_providers import (
    APIRoleTaxonomyProvider,
    APIDocumentProvider,
)

__all__ = [
    "RoleTaxonomyProvider",
    "MockRoleTaxonomyProvider",
    "APIRoleTaxonomyProvider",
    "get_role_taxonomy_provider",
    "DocumentProvider",
    "MockDocumentProvider",
    "APIDocumentProvider",
    "get_document_provider",
]
