# Mock Data Package

## First Principle: What Is Mock Data?

**Mock data is fake but realistic data used when real data isn't available or appropriate.**

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   REAL SYSTEM                    MOCK SYSTEM                │
│   ───────────                    ───────────                │
│                                                              │
│   ┌──────────┐                   ┌──────────┐               │
│   │ Database │                   │ In-Memory│               │
│   │ (Neo4j)  │                   │   Dict   │               │
│   └──────────┘                   └──────────┘               │
│        │                              │                      │
│        ▼                              ▼                      │
│   Real company                   Fake company               │
│   roles from DB                  roles from code            │
│                                                              │
│   ───────────────────────────────────────────────────────   │
│   SAME INTERFACE: get_role(company, title) → RoleEntry      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Mental Model: The Flight Simulator

Mock data is like a flight simulator:

| Real Airplane | Flight Simulator | Our System |
|---------------|------------------|------------|
| Real sky | Projected visuals | Real database |
| Real controls | Simulated response | Real API |
| Real danger | Safe practice | Mock providers |

**Key insight**: The pilot (your code) can't tell the difference—both respond the same way.

## System Thinking: Dependency Inversion

```
                    WITHOUT MOCKS
                    ─────────────
    ┌──────────────┐         ┌──────────────┐
    │   Workflow   │────────▶│   Database   │
    └──────────────┘         └──────────────┘

    Problem: Can't test workflow without database


                    WITH MOCKS (Dependency Inversion)
                    ────────────────────────────────
    ┌──────────────┐         ┌────────────────────┐
    │   Workflow   │────────▶│ Provider Interface │ (abstract)
    └──────────────┘         └─────────┬──────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         ▼                           ▼
                ┌────────────────┐         ┌────────────────┐
                │ RealProvider   │         │ MockProvider   │
                │ (database)     │         │ (in-memory)    │
                └────────────────┘         └────────────────┘

    Solution: Swap providers without changing workflow
```

## Files in This Package

| File | Mock Provider | Real Equivalent |
|------|---------------|-----------------|
| `role_taxonomy.py` | MockRoleTaxonomyProvider | Platform API |
| `documents.py` | MockDocumentProvider | S3/Document Storage |

## The Provider Pattern

### Abstract Interface (Contract)

```python
class RoleTaxonomyProvider(ABC):
    @abstractmethod
    def get_role(self, company: str, title: str) -> Optional[RoleEntry]:
        """Get role by company and title."""
        pass

    @abstractmethod
    def get_roles_for_company(self, company: str) -> List[RoleEntry]:
        """Get all roles for a company."""
        pass
```

### Mock Implementation

```python
class MockRoleTaxonomyProvider(RoleTaxonomyProvider):
    def __init__(self):
        self._data = {}  # In-memory storage
        self._populate_sample_data()

    def get_role(self, company: str, title: str) -> Optional[RoleEntry]:
        return self._data.get(company, {}).get(title)
```

### Factory Function (Swaps Implementation)

```python
def get_role_taxonomy_provider() -> RoleTaxonomyProvider:
    settings = get_settings()
    if settings.enable_mock_data:
        return MockRoleTaxonomyProvider()  # In-memory fake
    else:
        return RealTaxonomyProvider()       # Platform API
```

## Sample Data Included

### Companies

```
┌─────────────────────────────────────────────────────────────┐
│  Liberty Mutual (Insurance)                                  │
│  ├── Claims Adjuster        ✓ Has JD                        │
│  ├── Senior Underwriter     ✓ Has JD                        │
│  └── Risk Analyst           ✗ No JD                         │
├─────────────────────────────────────────────────────────────┤
│  Walmart Inc. (Retail)                                       │
│  ├── Store Manager          ✓ Has JD                        │
│  ├── Software Engineer      ✓ Has JD                        │
│  └── Supply Chain Analyst   ✗ No JD                         │
├─────────────────────────────────────────────────────────────┤
│  Acme Corporation (Tech)                                     │
│  ├── Product Manager        ✗ No JD                         │
│  └── Data Scientist         ✓ Has JD                        │
└─────────────────────────────────────────────────────────────┘
```

### Sample Job Description

```markdown
# Claims Adjuster

## Overview
The Claims Adjuster investigates insurance claims by interviewing
claimants, witnesses, and experts...

## Key Responsibilities
### Claims Investigation
- Conduct thorough investigations of insurance claims
- Interview claimants, witnesses, and experts
...

## Requirements
### Education
- Bachelor's degree in Business, Finance, or related field
...
```

## Thought Experiment: Why Not Just Use Empty Data?

**Empty data** (poor testing):
```python
def test_workflow():
    result = workflow.run(company="", role="")
    # What are we testing? Edge cases only.
```

**Realistic mock data** (good testing):
```python
def test_workflow():
    result = workflow.run(company="Liberty Mutual", role="Claims Adjuster")
    # Tests with realistic company name, role name, JD content
    # Catches issues that only appear with real-world data
```

**Mock data should be**:
- Realistic (mirrors production data shape)
- Diverse (covers different scenarios)
- Consistent (same data every run for reproducible tests)

## When to Use Mock Data

```
┌─────────────────────────────────────────────────────────────┐
│  USE MOCK DATA                                               │
├─────────────────────────────────────────────────────────────┤
│  ✓ Local development (no database needed)                   │
│  ✓ Unit tests (fast, isolated)                              │
│  ✓ Demos (predictable results)                              │
│  ✓ CI/CD pipelines (no external dependencies)               │
│  ✓ Learning the system (safe exploration)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  USE REAL DATA                                               │
├─────────────────────────────────────────────────────────────┤
│  ✓ Integration tests (verify real connections)              │
│  ✓ Staging environment (pre-production validation)          │
│  ✓ Production (actual business operations)                  │
│  ✓ Performance testing (realistic load)                     │
└─────────────────────────────────────────────────────────────┘
```

## Adding Custom Test Data

The demo script can add data dynamically:

```python
from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
from etter_workflows.mock_data.documents import get_document_provider
from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType

# Get providers
taxonomy = get_role_taxonomy_provider()
docs = get_document_provider()

# Add custom role
taxonomy.add_role("MyCompany", RoleTaxonomyEntry(
    job_id="my-001",
    job_role="My Custom Role",
    job_title="My Custom Role",
    draup_role="Custom Role",
))

# Add custom JD
docs.add_document("MyCompany", "My Custom Role", DocumentRef(
    type=DocumentType.JOB_DESCRIPTION,
    name="My JD",
    content="# My Custom Role\n\n...",
))
```

## Provider Lifecycle

```
Application Start
        │
        ▼
┌───────────────────┐
│ get_*_provider()  │  ◀── First call creates singleton
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Check settings    │
│ enable_mock_data? │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
  True        False
    │           │
    ▼           ▼
┌───────┐   ┌───────┐
│ Mock  │   │ Real  │
│Provider│   │Provider│
└───────┘   └───────┘
          │
          ▼
    Singleton stored
    (reused for all calls)
```

## Quick Reference

```python
# Get mock taxonomy data
from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider

taxonomy = get_role_taxonomy_provider()
companies = taxonomy.get_companies()  # ['Liberty Mutual', 'Walmart Inc.', ...]
roles = taxonomy.get_roles_for_company("Liberty Mutual")
role = taxonomy.get_role("Liberty Mutual", "Claims Adjuster")

# Get mock documents
from etter_workflows.mock_data.documents import get_document_provider
from etter_workflows.models.inputs import DocumentType

docs = get_document_provider()
jd = docs.get_document("Liberty Mutual", "Claims Adjuster", DocumentType.JOB_DESCRIPTION)
content = docs.get_document_content(jd)

# Reset providers (for testing)
from etter_workflows.mock_data.role_taxonomy import reset_role_taxonomy_provider
from etter_workflows.mock_data.documents import reset_document_provider

reset_role_taxonomy_provider()
reset_document_provider()
```

## Summary

| Aspect | Mock Provider | Real Provider |
|--------|---------------|---------------|
| **Data source** | In-memory dict | External system |
| **Speed** | Instant | Network latency |
| **Setup required** | None | Database, credentials |
| **Reliability** | 100% | Depends on external system |
| **Data realism** | Curated samples | Actual business data |
| **Use case** | Dev, test, demo | Staging, production |

**Remember**: Mock data lets you develop and test without dependencies. The same code works with both—only the provider changes.
