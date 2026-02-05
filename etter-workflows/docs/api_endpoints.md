# Etter Workflows API Documentation

## Overview

The Etter Self-Service Pipeline API provides endpoints for role onboarding and AI assessment workflows. It integrates with **Temporal** for workflow orchestration and supports both single-role and batch processing.

**Base URL:** `/api/v1/pipeline` (via reverse proxy)

**Integration:** When integrated with the parent etter-backend, endpoints are available at:
- Development: `http://localhost:7071/api/v1/pipeline/*`
- QA: `https://qa-etter.draup.technology/api/v1/pipeline/*`
- Production: `https://etter.draup.com/api/v1/pipeline/*`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Client Request                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  etter-backend (FastAPI) - localhost:7071                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  /api/v1/pipeline/* endpoints                                 │  │
│  │  /api/documents/*    (document storage)                       │  │
│  │  /api/taxonomy/*     (role taxonomy)                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Temporal Server - localhost:7233                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Namespace: etter-workflows-local / etter-workflows-qa        │  │
│  │  Task Queue: etter-role-onboarding                            │  │
│  │  Workflow: RoleOnboardingWorkflow                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  draup-world API - localhost:8083                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  /api/automated_workflows/create-company-role                 │  │
│  │  /api/automated_workflows/link-job-description                │  │
│  │  /api/automated_workflows/run-ai-assessment                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/push` | Start single role onboarding workflow |
| GET | `/status/{workflow_id}` | Get workflow status |
| GET | `/health` | Health check |
| GET | `/companies` | List available companies |
| GET | `/roles/{company_name}` | Get roles for a company |
| POST | `/push-batch` | Submit multiple roles for batch processing |
| GET | `/batch-status/{batch_id}` | Get aggregated batch status |
| POST | `/retry-failed/{batch_id}` | Retry failed roles in a batch |

---

## Single Role Endpoints

### POST /push

Start a role onboarding workflow for a single role. Submits workflow to Temporal for execution.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock assessment for testing (standalone mode only) |

**Request Body (Minimal):**

```json
{
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster"
}
```

**Request Body (With Documents):**

```json
{
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster",
  "documents": [
    {
      "type": "job_description",
      "uri": "https://s3.amazonaws.com/bucket/jd.pdf?presigned...",
      "name": "Claims_Adjuster_JD.pdf",
      "metadata": {
        "document_id": "dec3ac7e-a0b7-4721-b30d-7827684154b1",
        "content_type": "application/pdf"
      }
    }
  ],
  "draup_role_name": "Claims Handler",
  "options": {
    "skip_enhancement_workflows": false,
    "force_rerun": false,
    "notify_on_complete": true
  }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_id` | string | Yes | Company identifier (instance name) |
| `role_name` | string | Yes | Role name to onboard |
| `documents` | array | No | Documents to use (auto-fetched if not provided) |
| `documents[].type` | string | Yes | `job_description`, `process_map`, `sop`, `other` |
| `documents[].uri` | string | No* | S3 presigned URL or content URI |
| `documents[].content` | string | No* | Inline document content |
| `documents[].name` | string | No | Document filename |
| `documents[].metadata` | object | No | Additional metadata (document_id, roles, etc.) |
| `draup_role_id` | string | No | Draup role mapping ID |
| `draup_role_name` | string | No | Draup role name for mapping |
| `options` | object | No | Workflow options |

*Either `uri` or `content` must be provided when documents are specified.

**Document Handling:**

1. **Auto-fetch (documents not provided):**
   - System calls `/api/documents/?roles={role_name}` to find documents
   - Selects best document using priority: **PDF > DOCX > Images > Other**
   - Within same type, picks the latest by updated_at date
   - Prefers exact role match (document tagged only with this role)

2. **Explicit documents (documents provided):**
   - If `uri` is provided (S3 presigned URL), downstream API downloads and extracts content
   - If `content` is provided, it's used directly as the job description text
   - `metadata` is passed through to the link-job-description API for tracking

3. **Validation:**
   - If no documents provided AND no documents found for the role, returns 400 error

**Response (200 OK):**

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": null,
  "status": "queued",
  "estimated_duration_seconds": 600,
  "position_in_queue": null,
  "message": "Workflow submitted to Temporal for Claims Adjuster at liberty-mutual"
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Missing documents or invalid input |
| 503 | `TEMPORAL_ERROR` | Failed to submit to Temporal |
| 500 | `INTERNAL_ERROR` | Internal server error |

```json
{
  "detail": {
    "error": "VALIDATION_ERROR",
    "message": "At least one document (job_description) is required in the request",
    "recoverable": false
  }
}
```

---

### GET /status/{workflow_id}

Get the current status of a workflow. Queries Temporal directly for authoritative state, with optional Redis fallback for detailed progress.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow ID from push response |

**Response (200 OK):**

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": "c242defe4f32a6574a1abbddafe16a6a",
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster",
  "status": "processing",
  "current_step": "link_job_description",
  "progress": {
    "current": 2,
    "total": 3,
    "steps": [
      {
        "name": "create_company_role",
        "status": "completed",
        "duration_ms": 1250,
        "started_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:30:01Z",
        "error_message": null
      },
      {
        "name": "link_job_description",
        "status": "running",
        "duration_ms": null,
        "started_at": "2024-01-15T10:30:02Z",
        "completed_at": null,
        "error_message": null
      },
      {
        "name": "run_ai_assessment",
        "status": "pending",
        "duration_ms": null,
        "started_at": null,
        "completed_at": null,
        "error_message": null
      }
    ]
  },
  "queued_at": "2024-01-15T10:29:55Z",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": null,
  "estimated_duration_seconds": 600,
  "dashboard_url": null,
  "error": null
}
```

**Workflow States:**

| State | Description |
|-------|-------------|
| `queued` | Submitted to Temporal, waiting to start |
| `processing` | Workflow is executing activities |
| `ready` | Successfully completed all steps |
| `failed` | Workflow failed (see error field) |

**Step Statuses:**

| Status | Description |
|--------|-------------|
| `pending` | Activity not yet started |
| `running` | Activity currently executing |
| `completed` | Activity completed successfully |
| `failed` | Activity failed |
| `skipped` | Activity was skipped |

---

### GET /health

Health check endpoint for monitoring. Shows Temporal connection status.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "healthy",
    "temporal": "healthy",
    "temporal_address": "localhost:7233",
    "temporal_env_detection": "env=local, db_host=(not set), is_qa=false, is_prod=false",
    "redis": "healthy",
    "mock_data": "disabled"
  }
}
```

**Health Status:**
| Status | Description |
|--------|-------------|
| `healthy` | Temporal connected, all systems operational |
| `degraded` | Temporal unavailable, can run in standalone mode |
| `unhealthy` | Critical components unavailable |

---

### GET /companies

Get list of companies with available roles.

**Response (200 OK):**

```json
{
  "companies": ["Liberty Mutual", "Walmart Inc."],
  "total_count": 2
}
```

---

### GET /roles/{company_name}

Get available roles for a company.

**Response (200 OK):**

```json
{
  "company_name": "Liberty Mutual",
  "roles": [
    {
      "job_id": "job-001",
      "job_title": "Claims Adjuster",
      "job_role": "Claims Processor",
      "draup_role": "Claims Handler",
      "occupation": "Insurance",
      "job_family": "Claims",
      "status": "active"
    }
  ],
  "total_count": 1
}
```

---

## Batch Processing Endpoints

### POST /push-batch

Submit multiple roles for batch processing. Each role spawns an independent Temporal workflow.

**Request Body (Minimal - documents auto-fetched):**

```json
{
  "company_id": "liberty-mutual",
  "roles": [
    {"role_name": "Claims Adjuster"},
    {"role_name": "Underwriter"},
    {"role_name": "Risk Analyst"}
  ]
}
```

**Request Body (With explicit documents):**

```json
{
  "company_id": "liberty-mutual",
  "roles": [
    {
      "role_name": "Claims Adjuster",
      "documents": [
        {"type": "job_description", "content": "...JD content..."}
      ],
      "draup_role_name": "Claims Handler"
    },
    {
      "role_name": "Underwriter",
      "documents": [
        {"type": "job_description", "uri": "https://s3..."}
      ]
    }
  ],
  "options": {
    "skip_enhancement_workflows": false
  },
  "created_by": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123def456",
  "total_roles": 3,
  "workflow_ids": ["wf-1", "wf-2", "wf-3"],
  "status": "queued",
  "estimated_duration_seconds": 1200,
  "message": "Batch submitted: 3 roles queued for processing (via Temporal)"
}
```

**Document Handling:**
- Documents are optional for each role
- If not provided, system auto-fetches from `/api/documents/` using role name
- Selects best document: PDF > DOCX > Images > Other (latest first)
- Roles with no documents found are added to validation failures

**Validation:**
- Partial success is possible (some roles succeed, others fail)
- Validation failures are reported in the response message

---

### GET /batch-status/{batch_id}

Get aggregated status for a batch.

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123def456",
  "company_id": "liberty-mutual",
  "total": 50,
  "queued": 0,
  "in_progress": 13,
  "completed": 35,
  "failed": 2,
  "state": "in_progress",
  "progress_percent": 74.0,
  "success_rate": 94.6,
  "created_at": "2024-01-15T10:00:00Z",
  "roles": [
    {
      "role_name": "Claims Adjuster",
      "company_id": "liberty-mutual",
      "workflow_id": "wf-1",
      "status": "ready",
      "error": null,
      "dashboard_url": "https://..."
    }
  ]
}
```

---

### POST /retry-failed/{batch_id}

Retry failed roles in a batch.

**Note:** Retry does not have access to original documents. For document-dependent workflows, re-submit via `/push` instead.

**Request Body:**

```json
{
  "workflow_ids": ["wf-2", "wf-5"],
  "options": {"force_rerun": true}
}
```

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123def456",
  "retried_count": 2,
  "new_workflow_ids": ["wf-retry-2", "wf-retry-5"],
  "message": "Retried 2 failed roles"
}
```

---

## Workflow Activities

The RoleOnboardingWorkflow executes 3 activities via Temporal:

| Activity | Timeout | API Endpoint | Description |
|----------|---------|--------------|-------------|
| `create_company_role` | 5 min | `/api/automated_workflows/create-company-role` | Create/update CompanyRole node in graph |
| `link_job_description` | 5 min | `/api/automated_workflows/link-job-description` | Link JD to role, extract and format content |
| `run_ai_assessment` | 30 min | `/api/automated_workflows/run-ai-assessment` | Run AI Assessment workflow |

**Activity Flow:**
```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│ create_company_role │ ──► │ link_job_description│ ──► │  run_ai_assessment  │
│                     │     │                     │     │                     │
│ Returns:            │     │ Receives:           │     │ Receives:           │
│ - company_role_id   │     │ - company_role_id   │     │ - company_role_id   │
│                     │     │ - jd_content OR     │     │                     │
│                     │     │ - jd_uri (S3 URL)   │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**Retry Policy:**
- Maximum attempts: 2 (per activity)
- Initial interval: 5 seconds
- Maximum interval: 30 seconds
- Non-retryable errors: `HTTPError`, `ValueError`, `KeyError`

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed (missing documents, invalid fields) |
| `NOT_FOUND` | 404 | Workflow or batch not found |
| `TEMPORAL_ERROR` | 503 | Failed to connect/submit to Temporal |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `EXECUTION_ERROR` | 500 | Workflow execution failed |

---

## Configuration

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `TEMPORAL_ADDRESS` | `localhost:7233` | Temporal server address |
| `TEMPORAL_TASK_QUEUE` | `etter-role-onboarding` | Temporal task queue name |
| `ENABLE_MOCK_DATA` | `true` | Use mock data providers |
| `REDIS_HOST` | `127.0.0.1` | Redis host for batch tracking |
| `REDIS_PORT` | `6390` | Redis port |
| `ETTER_DB_HOST` | - | Database host (for environment detection) |
| `AUTOMATED_WORKFLOWS_API_BASE_URL` | `http://localhost:8083` | draup-world API URL |

**Namespace Detection:**
- Local: `etter-workflows-local` (ETTER_DB_HOST not set)
- QA: `etter-workflows-qa` (ETTER_DB_HOST contains "qa")
- Production: `etter-workflows` (ETTER_DB_HOST is production)

---

## Usage Examples

### Python - Single Role with Document URI

```python
import requests

response = requests.post(
    "http://localhost:7071/api/v1/pipeline/push",
    json={
        "company_id": "liberty-mutual",
        "role_name": "Claims Adjuster",
        "documents": [
            {
                "type": "job_description",
                "uri": "https://s3.amazonaws.com/bucket/jd.pdf?presigned...",
                "name": "Claims_Adjuster_JD.pdf",
                "metadata": {
                    "document_id": "abc-123",
                    "content_type": "application/pdf"
                }
            }
        ],
        "draup_role_name": "Claims Handler"
    }
)
workflow_id = response.json()["workflow_id"]
print(f"Workflow started: {workflow_id}")
```

### Python - Single Role with Inline Content

```python
response = requests.post(
    "http://localhost:7071/api/v1/pipeline/push",
    json={
        "company_id": "liberty-mutual",
        "role_name": "Claims Adjuster",
        "documents": [
            {
                "type": "job_description",
                "content": "The Claims Adjuster is responsible for...",
                "name": "Claims Adjuster JD"
            }
        ]
    }
)
```

### cURL - Health Check

```bash
curl http://localhost:7071/api/v1/pipeline/health | jq
```

### cURL - Push with Document

```bash
curl -X POST http://localhost:7071/api/v1/pipeline/push \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "liberty-mutual",
    "role_name": "Claims Adjuster",
    "documents": [
      {
        "type": "job_description",
        "content": "Job description content here..."
      }
    ]
  }'
```

---

## Interactive Documentation

When running, OpenAPI documentation is available at:
- Swagger UI: `http://localhost:7071/docs`
- ReDoc: `http://localhost:7071/redoc`

## Temporal UI

Monitor workflows in the Temporal Web UI:
- Local: `http://localhost:8233`
- Namespace: `etter-workflows-local` (or `etter-workflows-qa`)
