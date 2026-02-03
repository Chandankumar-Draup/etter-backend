# Etter Self-Service Pipeline

Self-Service Pipeline for Etter - Temporal-based workflow orchestration for role onboarding and AI assessment.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Programmatic Usage](#programmatic-usage)
- [Architecture](#architecture)
- [Components](#components)
- [State Machine](#state-machine)
- [Mock Data](#mock-data)
- [Extensibility](#extensibility)
- [Integration Guide](#integration-guide)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Overview

This package implements the self-service pipeline as specified in `docs/etter_self_service_implementation_plan.md`. It enables non-engineering users (Admin/CSM) to push roles to Etter without manual engineering intervention.

### Problem Solved

Before this pipeline, every role onboarding required:
1. Engineer creates CompanyRole node (manual)
2. Engineer links Job Description (manual)
3. Engineer triggers AI Assessment (manual script)
4. Engineer runs subsequent workflows (manual scripts)

**Now**: Users click "Push to Etter" and the pipeline handles everything automatically.

### Critical Path (MVP - Phase 1)

```
Role Defined → Document Linked → AI Assessment → Dashboard Visible
    │               │                 │                │
    ▼               ▼                 ▼                ▼
  P0              P0               P0              P0
```

### Key Features

- **Self-Service API**: REST endpoints for triggering workflows
- **Status Tracking**: Real-time progress visibility via Redis
- **State Machine**: Robust lifecycle management with retry support
- **Mock Data**: Built-in sample data for development/testing
- **Extensibility**: Abstract interfaces for real API integration
- **Temporal Ready**: Designed for Temporal workflow orchestration

---

## Quick Start

### 1. Install the Package

```bash
cd draup_world_model/etter-workflows
pip install -e .
```

### 2. Start the API Server

```bash
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090
```

### 3. Push a Role (using mock assessment)

```bash
curl -X POST "http://localhost:8090/api/v1/pipeline/push?use_mock=true" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "Liberty Mutual", "role_name": "Claims Adjuster"}'
```

### 4. Check Status

```bash
curl http://localhost:8090/api/v1/pipeline/status/{workflow_id}
```

### 5. Run the Demo

```bash
python demo.py
```

---

## Installation

### Basic Installation

```bash
# From the etter-workflows directory
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

### Required Dependencies

The package requires:
- `pydantic>=2.0` - Data validation
- `pydantic-settings>=2.0` - Settings management
- `fastapi>=0.100` - API framework
- `httpx>=0.24` - HTTP client
- `redis>=4.0` - Status tracking (optional)

### Optional Dependencies

- `temporalio>=1.0` - Temporal workflow orchestration
- `neo4j>=5.0` - Graph database client
- `uvicorn>=0.20` - ASGI server

---

## Configuration

> **Note:** For comprehensive deployment instructions including Temporal setup, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Environment Variables

All configuration uses the `ETTER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| **General** | | |
| `ETTER_ENVIRONMENT` | `development` | Environment name (`development`, `staging`, `production`) |
| `ETTER_LOG_LEVEL` | `INFO` | Logging level |
| `ETTER_ENABLE_MOCK_DATA` | `true` | Use mock data providers |
| **Temporal** | | |
| `ETTER_TEMPORAL_HOST` | `localhost:7233` | Temporal server host:port (see Temporal Setup below) |
| `ETTER_TEMPORAL_NAMESPACE` | `etter-dev` | Temporal namespace |
| `ETTER_TEMPORAL_TASK_QUEUE` | `etter-workflows` | Task queue name |
| `ETTER_TEMPORAL_MAX_CONCURRENT_ACTIVITIES` | `50` | Max concurrent activities |
| `ETTER_TEMPORAL_MAX_CONCURRENT_WORKFLOWS` | `100` | Max concurrent workflow tasks |
| **Neo4j** | | |
| `ETTER_NEO4J_URI` | `bolt://draup-world-neo4j.draup.technology:7687` | Neo4j connection URI |
| `ETTER_NEO4J_USER` | `neo4j` | Neo4j username |
| `ETTER_NEO4J_PASSWORD` | `BK13730kmyDcR5R` | Neo4j password |
| `ETTER_NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| **Redis** | | |
| `ETTER_REDIS_HOST` | `127.0.0.1` | Redis host |
| `ETTER_REDIS_PORT` | `6390` | Redis port |
| `ETTER_REDIS_DB` | `3` | Redis database number |
| `ETTER_REDIS_PASSWORD` | `F6muBM65GqSyvtzBqArK` | Redis password |
| `ETTER_REDIS_SOCKET_TIMEOUT` | `30` | Redis socket timeout (seconds) |
| `ETTER_REDIS_STATUS_TTL_SECONDS` | `86400` | Status TTL (24 hours) |
| **Workflow API** | | |
| `ETTER_WORKFLOW_API_BASE_URL` | `http://127.0.0.1:8082` | Existing workflow API URL |
| `ETTER_WORKFLOW_API_TIMEOUT` | `600` | API timeout in seconds |

### Temporal Setup

#### Option 1: Local Development Server
```bash
# Install Temporal CLI
brew install temporal  # macOS
# or: curl -sSf https://temporal.download/cli.sh | sh  # Linux

# Start dev server (runs on localhost:7233)
temporal server start-dev
```

#### Option 2: SSH Tunnel to QA Temporal
```bash
# Setup SSH tunnel
ssh -N -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
    ShreyashKumar-Draup@3.128.8.200

# Then configure
export ETTER_TEMPORAL_HOST=localhost:5445
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Docker Compose and production setup.

### Configuration File (Recommended)

Create a `.env` file in the package directory:

```env
# Environment
ETTER_ENVIRONMENT=development
ETTER_ENABLE_MOCK_DATA=true

# Temporal (Local dev server)
ETTER_TEMPORAL_HOST=localhost:7233
ETTER_TEMPORAL_NAMESPACE=default

# Neo4j (Production)
ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
ETTER_NEO4J_USER=neo4j
ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R
ETTER_NEO4J_DATABASE=neo4j

# Redis (Production)
ETTER_REDIS_HOST=127.0.0.1
ETTER_REDIS_PORT=6390
ETTER_REDIS_DB=3
ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK

# Logging
ETTER_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from etter_workflows.config.settings import Settings

# Create custom settings
settings = Settings(
    environment="production",
    temporal_host="temporal.internal:7233",
    enable_mock_data=False,
)

# Or load from environment
from etter_workflows.config.settings import get_settings
settings = get_settings()
```

---

## API Reference

### Base URL

```
http://{host}:{port}/api/v1/pipeline
```

### Endpoints

#### POST `/push` - Start Role Onboarding

Start a new role onboarding workflow.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock AI assessment for testing |

**Request Body:**
```json
{
  "company_id": "string (required)",
  "role_name": "string (required)",
  "documents": [
    {
      "type": "job_description | process_map | sop | other",
      "uri": "string (optional) - S3 or file path",
      "content": "string (optional) - inline content",
      "name": "string (optional)"
    }
  ],
  "draup_role_id": "string (optional) - Draup role mapping",
  "draup_role_name": "string (optional) - Draup role name",
  "options": {
    "skip_enhancement_workflows": false,
    "force_rerun": false,
    "notify_on_complete": true
  }
}
```

**Response (200 OK):**
```json
{
  "workflow_id": "role-onboard-abc123",
  "status": "queued",
  "estimated_duration_seconds": 600,
  "message": "Workflow started for Claims Adjuster at Liberty Mutual"
}
```

**Example:**
```bash
# Push with inline JD content
curl -X POST "http://localhost:8090/api/v1/pipeline/push" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "Liberty Mutual",
    "role_name": "Claims Adjuster",
    "documents": [{
      "type": "job_description",
      "content": "# Claims Adjuster\n\n## Overview\nThe Claims Adjuster investigates insurance claims..."
    }],
    "options": {
      "notify_on_complete": true
    }
  }'

# Push using mock data (no documents needed)
curl -X POST "http://localhost:8090/api/v1/pipeline/push?use_mock=true" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "Liberty Mutual", "role_name": "Claims Adjuster"}'
```

---

#### GET `/status/{workflow_id}` - Get Workflow Status

Get the current status and progress of a workflow.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | The workflow ID returned from push |

**Response (200 OK):**
```json
{
  "workflow_id": "role-onboard-abc123",
  "role_id": "cr-liberty-claims-adjuster",
  "company_id": "Liberty Mutual",
  "role_name": "Claims Adjuster",
  "status": "processing",
  "current_step": "ai_assessment",
  "progress": {
    "current": 1,
    "total": 2,
    "steps": [
      {
        "name": "role_setup",
        "status": "completed",
        "duration_ms": 1200,
        "started_at": "2026-01-28T10:00:00Z",
        "completed_at": "2026-01-28T10:00:01Z"
      },
      {
        "name": "ai_assessment",
        "status": "running",
        "started_at": "2026-01-28T10:00:02Z"
      }
    ]
  },
  "queued_at": "2026-01-28T09:59:55Z",
  "started_at": "2026-01-28T10:00:00Z",
  "completed_at": null,
  "estimated_duration_seconds": 600,
  "dashboard_url": null,
  "error": null
}
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `queued` | Waiting in queue for worker |
| `processing` | Currently being processed |
| `ready` | Completed successfully, visible in dashboard |
| `failed` | Processing failed (can retry) |
| `degraded` | Partial success (some steps failed) |
| `validation_error` | Input validation failed |
| `stale` | Inputs changed, re-assessment needed |

**Example:**
```bash
curl http://localhost:8090/api/v1/pipeline/status/role-onboard-abc123
```

---

#### GET `/health` - Health Check

Check the health of the pipeline service.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-01-28T10:00:00Z",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "mock_data": "enabled"
  }
}
```

**Example:**
```bash
curl http://localhost:8090/api/v1/pipeline/health
```

---

#### GET `/companies` - List Companies

List all companies with available roles (from mock data or taxonomy).

**Response (200 OK):**
```json
{
  "companies": ["Liberty Mutual", "Walmart Inc.", "Acme Corporation"],
  "total_count": 3
}
```

**Example:**
```bash
curl http://localhost:8090/api/v1/pipeline/companies
```

---

#### GET `/roles/{company_name}` - List Roles for Company

Get all roles for a specific company.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `company_name` | string | URL-encoded company name |

**Response (200 OK):**
```json
{
  "company_name": "Liberty Mutual",
  "roles": [
    {
      "job_id": "lm-001",
      "job_title": "Claims Adjuster",
      "job_role": "Claims Adjuster",
      "draup_role": "Insurance Claims Specialist",
      "occupation": "Claims Specialist",
      "job_family": "Claims Operations",
      "status": "active"
    },
    {
      "job_id": "lm-002",
      "job_title": "Underwriter",
      "job_role": "Senior Underwriter",
      "draup_role": "Insurance Underwriter",
      "occupation": "Underwriter",
      "job_family": "Underwriting",
      "status": "active"
    }
  ],
  "total_count": 2
}
```

**Example:**
```bash
curl "http://localhost:8090/api/v1/pipeline/roles/Liberty%20Mutual"
```

---

### Error Responses

All endpoints return errors in a consistent format:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Human-readable error message",
    "recoverable": true
  }
}
```

**Common Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `INTERNAL_ERROR` | 500 | Internal server error |

---

## Programmatic Usage

### Basic Workflow Execution

```python
import asyncio
from etter_workflows.workflows.role_onboarding import execute_role_onboarding

async def main():
    result = await execute_role_onboarding(
        company_id="Liberty Mutual",
        role_name="Claims Adjuster",
        use_mock_assessment=True,  # Use mock for testing
    )

    if result.success:
        print(f"Success! Role ID: {result.role_id}")
        print(f"AI Score: {result.outputs.final_score}")
        print(f"Dashboard: {result.dashboard_url}")

        # Access step results
        for step in result.steps_completed:
            print(f"  {step.name}: {step.status.value} ({step.duration_ms}ms)")
    else:
        print(f"Failed: {result.error.message}")
        print(f"Recoverable: {result.error.recoverable}")

asyncio.run(main())
```

### With Custom Documents

```python
import asyncio
from etter_workflows.workflows.role_onboarding import execute_role_onboarding
from etter_workflows.models.inputs import DocumentRef, DocumentType

async def main():
    # Create document reference
    jd_document = DocumentRef(
        type=DocumentType.JOB_DESCRIPTION,
        name="Software Engineer JD",
        content="""
        # Software Engineer

        ## Overview
        Design and develop software applications...

        ## Responsibilities
        - Write clean, maintainable code
        - Participate in code reviews
        - Debug and troubleshoot issues

        ## Requirements
        - 3+ years experience
        - Proficiency in Python, Java, or Go
        """
    )

    result = await execute_role_onboarding(
        company_id="My Company",
        role_name="Software Engineer",
        documents=[jd_document],
        draup_role_name="Software Developer",
        use_mock_assessment=True,
    )

    print(f"Result: {result.success}")

asyncio.run(main())
```

### Using the Workflow Class Directly

```python
import asyncio
from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow
from etter_workflows.models.inputs import RoleOnboardingInput, ExecutionContext

async def main():
    # Create workflow instance
    workflow = RoleOnboardingWorkflow(
        workflow_id="my-custom-id",
        use_mock_assessment=True,
    )

    # Create input
    input = RoleOnboardingInput(
        company_id="Liberty Mutual",
        role_name="Claims Adjuster",
        context=ExecutionContext(
            company_id="Liberty Mutual",
            user_id="admin@company.com",
        ),
    )

    # Execute
    result = await workflow.execute(input)

    print(f"Workflow ID: {result.workflow_id}")
    print(f"Success: {result.success}")

asyncio.run(main())
```

### Using Individual Activities

```python
import asyncio
from etter_workflows.activities.role_setup import create_company_role, link_job_description
from etter_workflows.activities.ai_assessment import run_ai_assessment
from etter_workflows.models.inputs import ExecutionContext

async def main():
    context = ExecutionContext(
        company_id="Liberty Mutual",
        user_id="system",
    )

    # Step 1: Create CompanyRole
    role_result = await create_company_role(
        company_name="Liberty Mutual",
        role_name="Claims Adjuster",
        draup_role_name="Insurance Claims Specialist",
        context=context,
    )
    print(f"Created role: {role_result['company_role_id']}")

    # Step 2: Link JD
    link_result = await link_job_description(
        company_role_id=role_result['company_role_id'],
        jd_content="# Claims Adjuster\n\nJob description content...",
        context=context,
    )
    print(f"Linked JD: {link_result['jd_id']}")

    # Step 3: Run AI Assessment
    assessment_result = await run_ai_assessment(
        company_name="Liberty Mutual",
        role_name="Claims Adjuster",
        company_role_id=role_result['company_role_id'],
        context=context,
    )
    print(f"AI Score: {assessment_result['ai_automation_score']}")

asyncio.run(main())
```

### Accessing Mock Data

```python
from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
from etter_workflows.mock_data.documents import get_document_provider
from etter_workflows.models.inputs import DocumentType

# Get providers
taxonomy = get_role_taxonomy_provider()
documents = get_document_provider()

# List companies
companies = taxonomy.get_companies()
print(f"Companies: {companies}")

# Get roles for a company
roles = taxonomy.get_roles_for_company("Liberty Mutual")
for role in roles:
    print(f"  {role.job_title} -> {role.draup_role}")

# Get JD for a role
jd = documents.get_document(
    "Liberty Mutual",
    "Claims Adjuster",
    DocumentType.JOB_DESCRIPTION,
)
print(f"JD Content: {jd.content[:100]}...")
```

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM CONTEXT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        CONTROL PLANE                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ Auth/AuthZ   │  │ Rate Limits  │  │  Audit Log   │                 │  │
│  │  │  (Existing)  │  │  (Future)    │  │  (Future)    │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     ORCHESTRATION PLANE (NEW)                          │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                      TEMPORAL SERVER                              │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │  │
│  │  │  │  Workflow   │  │   State     │  │  Visibility │               │ │  │
│  │  │  │ Definitions │  │  Machine    │  │    API      │               │ │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘               │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         DATA PLANE (EXISTING)                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │    Neo4j     │  │    Redis     │  │    S3/Blob   │                 │  │
│  │  │   (Graph)    │  │   (Cache)    │  │   (Docs)     │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
USER INTERFACE LAYER
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Taxonomy   │  │ Repository  │  │   Status    │
│   Builder   │  │   Upload    │  │  Dashboard  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
───────┼────────────────┼────────────────┼─────────
       │                │                │
API LAYER (FastAPI)
┌──────▼───────────────▼────────────────▼──────┐
│  POST /push    GET /status    GET /health    │
└──────────────────────┬───────────────────────┘
                       │
───────────────────────┼───────────────────────────
                       │
ORCHESTRATION LAYER
┌──────────────────────▼──────────────────────┐
│           RoleOnboardingWorkflow             │
│                                              │
│  ┌─────────────┐      ┌─────────────────┐   │
│  │ Role Setup  │─────▶│  AI Assessment  │   │
│  │  Activity   │      │    Activity     │   │
│  └─────────────┘      └─────────────────┘   │
│                                              │
│  Sub-activities:      Sub-activities:       │
│  - create_role        - execute_workflow    │
│  - link_jd            - extract_scores      │
│  - format_jd_md       - store_results       │
└─────────────────────────────────────────────┘
                       │
───────────────────────┼───────────────────────────
                       │
DATA LAYER
┌──────────────────────▼──────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │  Neo4j  │  │  Redis  │  │   LLM   │      │
│  │ (Graph) │  │(Status) │  │  (API)  │      │
│  └─────────┘  └─────────┘  └─────────┘      │
└─────────────────────────────────────────────┘
```

### Self-Similar Interface Contract

Every component (Activity, Workflow, Pipeline) implements the same interface:

```
INPUT:
{
  "id": "unique-identifier",
  "inputs": { ... },
  "context": { "company_id": "...", "user_id": "...", "trace_id": "..." }
}

OUTPUT:
{
  "id": "same-identifier",
  "status": "pending | running | completed | failed",
  "progress": { "current": N, "total": M },
  "outputs": { ... } | null,
  "error": { "code": "...", "message": "...", "recoverable": bool } | null
}
```

---

## Components

### Package Structure

```
etter_workflows/
├── __init__.py              # Package exports
├── worker.py                # Temporal worker entry point
│
├── activities/              # Atomic operations (Temporal Activities)
│   ├── __init__.py
│   ├── base.py              # BaseActivity with metrics and retry
│   ├── role_setup.py        # create_company_role, link_job_description
│   └── ai_assessment.py     # run_ai_assessment
│
├── workflows/               # Orchestration logic (Temporal Workflows)
│   ├── __init__.py
│   ├── base.py              # BaseWorkflow with state machine
│   └── role_onboarding.py   # RoleOnboardingWorkflow
│
├── models/                  # Data models (Pydantic)
│   ├── __init__.py
│   ├── inputs.py            # RoleOnboardingInput, DocumentRef, etc.
│   ├── outputs.py           # WorkflowResult, ActivityResult, etc.
│   └── status.py            # RoleStatus, WorkflowState, ProgressInfo
│
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── settings.py          # Settings class with env vars
│   └── retry_policies.py    # Retry configurations for activities
│
├── clients/                 # External service clients
│   ├── __init__.py
│   ├── neo4j_client.py      # Neo4j graph operations
│   ├── llm_client.py        # LLM for JD formatting
│   ├── status_client.py     # Redis status tracking
│   └── workflow_api_client.py # Existing workflow API
│
├── mock_data/               # Mock data providers
│   ├── __init__.py
│   ├── role_taxonomy.py     # Mock role taxonomy
│   └── documents.py         # Mock JDs and documents
│
└── api/                     # FastAPI routes
    ├── __init__.py
    ├── schemas.py           # Pydantic request/response models
    └── routes.py            # API endpoint handlers
```

### Activities

| Activity | Description | Timeout | Retry |
|----------|-------------|---------|-------|
| `create_company_role` | Create CompanyRole node in Neo4j | 5 min | 3x |
| `link_job_description` | Link JD to CompanyRole, format to markdown | 5 min | 3x |
| `run_ai_assessment` | Execute AI assessment workflow | 30 min | 5x |

### Workflows

| Workflow | Description | Steps | Timeout |
|----------|-------------|-------|---------|
| `RoleOnboardingWorkflow` | Main pipeline workflow | role_setup → ai_assessment | 2 hours |

### Models

**Input Models:**
- `RoleOnboardingInput` - Main workflow input
- `DocumentRef` - Document reference (URI or content)
- `ExecutionContext` - Execution context with trace ID
- `WorkflowOptions` - Workflow options (skip, force, notify)
- `TaxonomyEntry` - Role taxonomy entry

**Output Models:**
- `WorkflowResult` - Complete workflow result
- `ActivityResult` - Single activity result
- `StepResult` - Workflow step result
- `AssessmentOutputs` - AI assessment outputs

**Status Models:**
- `RoleStatus` - Complete role status
- `WorkflowState` - State enum
- `ProgressInfo` - Progress tracking
- `StepProgress` - Step-level progress

---

## State Machine

### Role Lifecycle States

```
                         ROLE LIFECYCLE STATE MACHINE
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          ┌──────────────┐                                   │
│                          │   DRAFT      │                                   │
│                          │   (Taxonomy) │                                   │
│                          └──────┬───────┘                                   │
│                                 │ User clicks "Push to Etter"               │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        VALIDATION                                    │    │
│  │  • Has at least one document (JD)?                                  │    │
│  │  • Has Draup role mapping?                                          │    │
│  │  • Not already processing?                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│            │                                              │                  │
│            │ Pass                                         │ Fail             │
│            ▼                                              ▼                  │
│  ┌──────────────┐                              ┌──────────────┐              │
│  │   QUEUED     │                              │ VALIDATION   │              │
│  │  (Waiting)   │                              │   _ERROR     │──────┐       │
│  └──────┬───────┘                              └──────────────┘      │       │
│         │ Worker picks up                                           │       │
│         ▼                                                           │       │
│  ┌──────────────┐                                                   │       │
│  │  PROCESSING  │◀──────────────────────────────────────────────────┼───┐   │
│  │              │                                                   │   │   │
│  │  Sub-states: │                                                   │   │   │
│  │  • ROLE_SETUP│                                                   │   │   │
│  │  • AI_ASSESS │                                                   │   │   │
│  └──────┬───────┘                                                   │   │   │
│         │                                                           │   │   │
│         ├───────────────────────┬──────────────────────┐            │   │   │
│         │ Success               │ Partial              │ Failure    │   │   │
│         ▼                       ▼                      ▼            │   │   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐       │   │   │
│  │   READY      │      │  DEGRADED    │      │   FAILED     │       │   │   │
│  │ (Dashboard)  │      │ (Partial OK) │      │              │       │   │   │
│  └──────────────┘      └──────────────┘      └──────┬───────┘       │   │   │
│                                                     │               │   │   │
│                                                     │ User retries  │   │   │
│                                                     └───────────────┘   │   │
│                                                                         │   │
│  ┌──────────────┐                                                       │   │
│  │    STALE     │ ← Inputs changed, re-assessment needed                │   │
│  │              │────────────────────────────────────────────────────────┘   │
│  └──────────────┘   (User triggers re-run)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Valid State Transitions

| From State | To States |
|------------|-----------|
| `DRAFT` | `QUEUED`, `VALIDATION_ERROR` |
| `QUEUED` | `PROCESSING` |
| `PROCESSING` | `READY`, `DEGRADED`, `FAILED` |
| `FAILED` | `QUEUED` (retry) |
| `READY` | `STALE` |
| `STALE` | `QUEUED` (re-run) |
| `VALIDATION_ERROR` | `DRAFT` (user fixes) |
| `DEGRADED` | `QUEUED` (retry) |

---

## Mock Data

The package includes mock data for development and testing. Mock data is enabled by default (`ETTER_ENABLE_MOCK_DATA=true`).

### Available Companies

| Company | Roles | Has JDs |
|---------|-------|---------|
| Liberty Mutual | 3 | Yes |
| Walmart Inc. | 3 | Yes |
| Acme Corporation | 2 | Yes |

### Available Roles

**Liberty Mutual:**
- Claims Adjuster → Insurance Claims Specialist
- Underwriter → Insurance Underwriter
- Risk Analyst → Risk Assessment Specialist

**Walmart Inc.:**
- Store Manager → Retail Store Manager
- Software Development Engineer → Software Developer
- Supply Chain Analyst → Supply Chain Specialist

**Acme Corporation:**
- Product Manager → Product Management Lead
- Data Scientist → Data Science Specialist

### Mock JD Format

Mock JDs follow a standard markdown format:

```markdown
# Role Title

## Overview
Brief description of the role...

## Key Responsibilities

### Category 1
- Responsibility 1
- Responsibility 2

### Category 2
- Responsibility 3
- Responsibility 4

## Requirements

### Education
- Bachelor's degree in...

### Experience
- X years experience in...

### Skills
- Skill 1
- Skill 2
```

---

## Extensibility

### Replacing Mock Data with Real APIs

The mock data providers implement abstract interfaces that can be replaced.

#### Role Taxonomy Provider

```python
from etter_workflows.mock_data.role_taxonomy import RoleTaxonomyProvider, TaxonomyEntry

class PlatformRoleTaxonomyProvider(RoleTaxonomyProvider):
    """Real implementation using platform API."""

    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=api_base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )

    def get_roles_for_company(
        self,
        company_name: str,
        status_filter: Optional[str] = None,
    ) -> List[TaxonomyEntry]:
        response = self._client.get(
            f"/api/v1/taxonomy/roles",
            params={"company": company_name, "status": status_filter}
        )
        response.raise_for_status()

        return [TaxonomyEntry(**role) for role in response.json()["roles"]]

    def get_role(self, company_name: str, role_name: str) -> Optional[TaxonomyEntry]:
        roles = self.get_roles_for_company(company_name)
        return next((r for r in roles if r.job_title == role_name), None)

    def get_companies(self) -> List[str]:
        response = self._client.get("/api/v1/taxonomy/companies")
        response.raise_for_status()
        return response.json()["companies"]

# Register the provider
from etter_workflows.mock_data.role_taxonomy import _role_taxonomy_provider
_role_taxonomy_provider = PlatformRoleTaxonomyProvider(
    api_base_url="https://platform.etter.com",
    api_key="your-api-key"
)
```

#### Document Provider

```python
from etter_workflows.mock_data.documents import DocumentProvider
from etter_workflows.models.inputs import DocumentRef, DocumentType

class S3DocumentProvider(DocumentProvider):
    """Real implementation using S3."""

    def __init__(self, bucket: str):
        import boto3
        self.s3 = boto3.client('s3')
        self.bucket = bucket

    def get_document(
        self,
        company_name: str,
        role_name: str,
        doc_type: DocumentType,
    ) -> Optional[DocumentRef]:
        key = f"{company_name}/{role_name}/{doc_type.value}.md"

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            content = response['Body'].read().decode('utf-8')

            return DocumentRef(
                type=doc_type,
                uri=f"s3://{self.bucket}/{key}",
                content=content,
                name=f"{role_name} - {doc_type.value}",
            )
        except self.s3.exceptions.NoSuchKey:
            return None

    def get_documents_for_role(
        self,
        company_name: str,
        role_name: str,
    ) -> List[DocumentRef]:
        prefix = f"{company_name}/{role_name}/"
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)

        docs = []
        for obj in response.get('Contents', []):
            # Parse document type from key
            doc_type = self._parse_doc_type(obj['Key'])
            doc = self.get_document(company_name, role_name, doc_type)
            if doc:
                docs.append(doc)

        return docs
```

### Adding New Activities

```python
from etter_workflows.activities.base import BaseActivity, activity_with_retry
from etter_workflows.models.inputs import ExecutionContext
from etter_workflows.models.outputs import ActivityResult
from etter_workflows.config.retry_policies import get_llm_retry_policy

class SkillsArchitectureActivity(BaseActivity):
    """Activity for building skills architecture."""

    def __init__(self):
        super().__init__(name="skills_architecture")

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActivityResult:
        self._start_execution()

        try:
            company_role_id = inputs["company_role_id"]

            # Your implementation here
            skills = await self._extract_skills(company_role_id)
            architecture = await self._build_architecture(skills)

            return self._create_success_result(
                id=context.trace_id,
                result={
                    "skills_count": len(skills),
                    "architecture": architecture,
                },
            )
        except Exception as e:
            return self._create_failure_result(
                id=context.trace_id,
                error=e,
                error_code="SKILLS_ARCH_ERROR",
            )

# Standalone function for Temporal
@activity_with_retry(retry_config=get_llm_retry_policy())
async def build_skills_architecture(
    company_role_id: str,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    activity = SkillsArchitectureActivity()
    result = await activity.execute(
        {"company_role_id": company_role_id},
        context or ExecutionContext(company_id="system", user_id="system"),
    )
    return result.result
```

### Adding New Workflows

```python
from etter_workflows.workflows.base import BaseWorkflow, WorkflowStep
from etter_workflows.models.status import ProcessingSubState

class SkillsAnalysisWorkflow(BaseWorkflow):
    """Workflow for skills analysis."""

    def __init__(self):
        super().__init__()
        self.skills_activity = SkillsMinerActivity()
        self.arch_activity = SkillsArchitectureActivity()
        self.steps = self.define_steps()

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="skills_mining",
                sub_state=ProcessingSubState.SKILLS_ANALYSIS,
                execute=self._execute_skills_mining,
                required=True,
                timeout_seconds=600,
            ),
            WorkflowStep(
                name="skills_architecture",
                sub_state=ProcessingSubState.SKILLS_ANALYSIS,
                execute=self._execute_skills_architecture,
                required=False,  # Can continue if fails
                timeout_seconds=600,
            ),
        ]

    async def _execute_skills_mining(self, inputs, context):
        # Implementation
        pass

    async def _execute_skills_architecture(self, inputs, context):
        # Implementation
        pass
```

---

## Integration Guide

### Integrating with Existing Systems

#### 1. Connect to Existing Workflow API

The package connects to the existing workflow API for AI assessment:

```python
from etter_workflows.config.settings import Settings

settings = Settings(
    workflow_api_base_url="http://your-workflow-api:8080",
    workflow_api_timeout=600,
)
```

#### 2. Connect to Neo4j

```python
from etter_workflows.clients.neo4j_client import Neo4jClient

client = Neo4jClient(
    uri="bolt://neo4j.internal:7687",
    user="etter_service",
    password="secure_password",
)

# Create CompanyRole
role_id = await client.create_company_role(
    company_name="My Company",
    role_name="Software Engineer",
    draup_role_name="Software Developer",
)
```

#### 3. Connect to Redis for Status

```python
from etter_workflows.clients.status_client import StatusClient

client = StatusClient(
    host="redis.internal",
    port=6379,
    db=5,
    password="redis_password",
)

# Get status
status = client.get_status("workflow-id")
```

### Adding Routes to Existing FastAPI App

```python
from fastapi import FastAPI
from etter_workflows.api.routes import router as pipeline_router

# Your existing app
app = FastAPI()

# Include pipeline routes
app.include_router(
    pipeline_router,
    prefix="/api/v1/pipeline",
    tags=["pipeline"],
)
```

---

## Deployment

### Running with Uvicorn

```bash
# Development
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --reload

# Production
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --workers 4
```

### Running with Gunicorn

```bash
gunicorn etter_workflows.api.routes:app \
    --bind 0.0.0.0:8090 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY draup_world_model/etter-workflows /app/etter-workflows
COPY draup_world_model/automated_workflow /app/automated_workflow

RUN pip install -e /app/etter-workflows

EXPOSE 8090

CMD ["uvicorn", "etter_workflows.api.routes:app", "--host", "0.0.0.0", "--port", "8090"]
```

### Environment Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  etter-pipeline:
    build: .
    ports:
      - "8090:8090"
    environment:
      - ETTER_ENVIRONMENT=production
      - ETTER_NEO4J_URI=bolt://neo4j:7687
      - ETTER_NEO4J_USER=neo4j
      - ETTER_NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - ETTER_REDIS_HOST=redis
      - ETTER_REDIS_PORT=6379
      - ETTER_ENABLE_MOCK_DATA=false
      - ETTER_WORKFLOW_API_BASE_URL=http://workflow-api:8080
    depends_on:
      - neo4j
      - redis
```

### Temporal Worker Deployment

```bash
# Run the Temporal worker
python -m etter_workflows.worker
```

With environment:
```bash
ETTER_TEMPORAL_HOST=temporal.internal:7233 \
ETTER_TEMPORAL_NAMESPACE=etter-prod \
python -m etter_workflows.worker
```

---

## Troubleshooting

### Common Issues

#### 1. "No module named 'pydantic'"

```bash
pip install pydantic pydantic-settings
```

#### 2. "No module named 'fastapi'"

```bash
pip install fastapi uvicorn
```

#### 3. "Redis connection refused"

Check Redis is running:
```bash
redis-cli -h localhost -p 6390 ping
```

Or disable Redis status tracking:
```python
# Status client will fall back to in-memory storage
```

#### 4. "Validation failed: At least one document required"

Either:
1. Provide a document in the request
2. Enable mock data: `ETTER_ENABLE_MOCK_DATA=true`
3. Use a role that exists in mock data

#### 5. "Workflow API connection error"

Check the workflow API is accessible:
```bash
curl http://127.0.0.1:8082/health
```

Update the URL if needed:
```bash
export ETTER_WORKFLOW_API_BASE_URL=http://your-api:8080
```

### Debug Logging

Enable debug logging:
```bash
ETTER_LOG_LEVEL=DEBUG python -m etter_workflows.worker
```

Or in code:
```python
import logging
logging.getLogger("etter_workflows").setLevel(logging.DEBUG)
```

### Health Check

```bash
curl http://localhost:8090/api/v1/pipeline/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "mock_data": "enabled"
  }
}
```

---

## Development

### Setting Up Development Environment

```bash
# Clone and navigate
cd draup_world_model/etter-workflows

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=etter_workflows --cov-report=html

# Run specific test file
pytest tests/test_workflows.py -v
```

### Code Style

- **Type hints**: Required for all functions
- **Docstrings**: Google-style docstrings
- **Line length**: 100 characters max
- **Imports**: Standard library → Third-party → Local

### Running the Demo

```bash
python demo.py

# With specific company/role
python demo.py --company "Walmart Inc." --role "Store Manager"

# With real assessment (requires workflow API)
python demo.py --use-real-assessment
```

---

## Related Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Comprehensive deployment, Temporal setup, and operations
- [Implementation Plan](docs/etter_self_service_implementation_plan.md) - Architecture and design decisions
- [Systems Exploration](docs/etter_self_service_exploration.md) - Problem analysis and solution paths

---

## License

Internal use only. Part of the Etter AI Transformation Platform.

---

## Changelog

### v0.1.0 (Phase 1 MVP)

- Initial release with core functionality
- Role onboarding workflow (role_setup + ai_assessment)
- FastAPI endpoints (push, status, health)
- Mock data providers for development
- Redis status tracking
- Temporal worker support
