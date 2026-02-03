# Etter Workflows API Documentation

## Overview

The Etter Self-Service Pipeline API provides endpoints for role onboarding and AI assessment workflows. It supports both single-role and batch processing.

**Base URL:** `/api/v1/pipeline`

**Integration:** When integrated with the parent etter-backend, endpoints are available at:
- Development: `http://localhost:7071/api/v1/pipeline/*`
- QA/Production: Via the main Etter API gateway

---

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/push` | Start single role onboarding workflow |
| GET | `/status/{workflow_id}` | Get workflow status |
| GET | `/health` | Health check |
| GET | `/companies` | List available companies (mock data) |
| GET | `/roles/{company_name}` | Get roles for a company |
| POST | `/push-batch` | Submit multiple roles for batch processing |
| GET | `/batch-status/{batch_id}` | Get aggregated batch status |
| POST | `/retry-failed/{batch_id}` | Retry failed roles in a batch |

---

## Single Role Endpoints

### POST /push

Start a role onboarding workflow for a single role.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock assessment for testing |

**Request Body:**

```json
{
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster",
  "documents": [
    {
      "type": "job_description",
      "uri": "s3://bucket/path/jd.pdf",
      "content": null,
      "name": "Claims Adjuster JD"
    }
  ],
  "draup_role_id": "draup-role-12345",
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
| `company_id` | string | Yes | Company identifier |
| `role_name` | string | Yes | Role name to onboard |
| `documents` | array | No | Documents to link (JD, process maps) |
| `documents[].type` | string | Yes | Document type: `job_description`, `process_map`, `sop`, `other` |
| `documents[].uri` | string | No | URI to document (s3://, file://, or URL) |
| `documents[].content` | string | No | Inline document content |
| `documents[].name` | string | No | Document name |
| `draup_role_id` | string | No | Draup role mapping ID |
| `draup_role_name` | string | No | Draup role name for mapping |
| `options.skip_enhancement_workflows` | boolean | No | Skip skills/task feasibility (default: false) |
| `options.force_rerun` | boolean | No | Force re-run even if results exist (default: false) |
| `options.notify_on_complete` | boolean | No | Send notification on complete (default: true) |

**Response (200 OK):**

```json
{
  "workflow_id": "role-onboard-abc123def456",
  "role_id": null,
  "status": "queued",
  "estimated_duration_seconds": 600,
  "position_in_queue": null,
  "message": "Workflow started for Claims Adjuster at liberty-mutual"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Unique workflow identifier (Temporal workflow ID) |
| `role_id` | string | CompanyRole ID (populated after role_setup completes) |
| `status` | string | Current status: `queued`, `processing`, `ready`, `failed` |
| `estimated_duration_seconds` | integer | Estimated time to complete |
| `position_in_queue` | integer | Position in processing queue |
| `message` | string | Status message |

**Error Response (400/500):**

```json
{
  "detail": {
    "error": "VALIDATION_ERROR",
    "message": "At least one job description document is required",
    "recoverable": false
  }
}
```

---

### GET /status/{workflow_id}

Get the current status of a workflow.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow ID from push response |

**Response (200 OK):**

```json
{
  "workflow_id": "role-onboard-abc123def456",
  "role_id": "cr-liberty-claims-adjuster",
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster",
  "status": "processing",
  "current_step": "ai_assessment",
  "progress": {
    "current": 2,
    "total": 2,
    "steps": [
      {
        "name": "role_setup",
        "status": "completed",
        "duration_ms": 1250,
        "started_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:30:01Z",
        "error_message": null
      },
      {
        "name": "ai_assessment",
        "status": "running",
        "duration_ms": null,
        "started_at": "2024-01-15T10:30:02Z",
        "completed_at": null,
        "error_message": null
      }
    ]
  },
  "queued_at": "2024-01-15T10:29:55Z",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": null,
  "position_in_queue": null,
  "estimated_duration_seconds": 600,
  "dashboard_url": null,
  "error": null
}
```

**Workflow States:**

| State | Description |
|-------|-------------|
| `draft` | Initial state before validation |
| `queued` | Validated and waiting to be processed |
| `processing` | Currently executing workflow steps |
| `ready` | Successfully completed all steps |
| `failed` | Workflow failed (see error field) |
| `degraded` | Completed with some non-critical failures |
| `validation_error` | Failed input validation |
| `stale` | Results are outdated and need refresh |

**Step Statuses:**

| Status | Description |
|--------|-------------|
| `pending` | Step not yet started |
| `running` | Step currently executing |
| `completed` | Step completed successfully |
| `failed` | Step failed |
| `skipped` | Step was skipped |

---

### GET /health

Health check endpoint for monitoring.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "mock_data": "enabled"
  }
}
```

---

### GET /companies

Get list of companies with available roles (from mock data when enabled).

**Response (200 OK):**

```json
{
  "companies": [
    "Liberty Mutual",
    "Walmart Inc.",
    "Acme Corporation"
  ],
  "total_count": 3
}
```

---

### GET /roles/{company_name}

Get available roles for a company (from mock data).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `company_name` | string | Company name |

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
    },
    {
      "job_id": "job-002",
      "job_title": "Underwriter",
      "job_role": "Risk Underwriter",
      "draup_role": "Insurance Underwriter",
      "occupation": "Insurance",
      "job_family": "Underwriting",
      "status": "active"
    }
  ],
  "total_count": 2
}
```

---

## Batch Processing Endpoints

### POST /push-batch

Submit multiple roles for batch processing. Each role spawns an independent workflow.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock assessment for testing |

**Request Body:**

```json
{
  "company_id": "liberty-mutual",
  "roles": [
    {
      "company_id": "liberty-mutual",
      "role_name": "Claims Adjuster",
      "documents": [
        {"type": "job_description", "content": "...JD content..."}
      ],
      "draup_role_name": "Claims Handler"
    },
    {
      "company_id": "liberty-mutual",
      "role_name": "Underwriter",
      "documents": [],
      "draup_role_name": "Insurance Underwriter"
    },
    {
      "company_id": "liberty-mutual",
      "role_name": "Risk Analyst",
      "documents": []
    }
  ],
  "options": {
    "skip_enhancement_workflows": false,
    "force_rerun": false,
    "notify_on_complete": true
  },
  "created_by": "user@example.com"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_id` | string | Yes | Default company for all roles |
| `roles` | array | Yes | List of roles to onboard |
| `roles[].company_id` | string | No | Override company for specific role |
| `roles[].role_name` | string | Yes | Role name |
| `roles[].documents` | array | No | Documents for the role |
| `roles[].draup_role_id` | string | No | Draup role mapping ID |
| `roles[].draup_role_name` | string | No | Draup role name |
| `options` | object | No | Options applied to all roles |
| `created_by` | string | No | User/system submitting the batch |

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123def456",
  "total_roles": 3,
  "workflow_ids": [
    "role-onboard-wf1",
    "role-onboard-wf2",
    "role-onboard-wf3"
  ],
  "status": "queued",
  "estimated_duration_seconds": 1200,
  "message": "Batch submitted: 3 roles queued for processing"
}
```

---

### GET /batch-status/{batch_id}

Get aggregated status for a batch.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `batch_id` | string | Batch ID from push-batch response |

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
      "workflow_id": "role-onboard-wf1",
      "status": "ready",
      "error": null,
      "dashboard_url": "https://dashboard.example.com/role/cr-123"
    },
    {
      "role_name": "Underwriter",
      "company_id": "liberty-mutual",
      "workflow_id": "role-onboard-wf2",
      "status": "failed",
      "error": "API timeout during AI assessment",
      "dashboard_url": null
    }
  ]
}
```

**Batch States:**

| State | Description |
|-------|-------------|
| `queued` | All roles waiting to process |
| `in_progress` | Some roles currently processing |
| `completed` | All roles finished (success or failed) |
| `failed` | All roles failed |

---

### POST /retry-failed/{batch_id}

Retry failed roles in a batch. Creates new workflows for failed roles only.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `batch_id` | string | Batch ID |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock assessment for testing |

**Request Body:**

```json
{
  "workflow_ids": ["role-onboard-wf2", "role-onboard-wf5"],
  "options": {
    "skip_enhancement_workflows": false,
    "force_rerun": true,
    "notify_on_complete": true
  }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_ids` | array | No | Specific workflow IDs to retry (default: all failed) |
| `options` | object | No | Workflow options for retry |

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123def456",
  "retried_count": 2,
  "new_workflow_ids": [
    "role-onboard-retry-wf2",
    "role-onboard-retry-wf5"
  ],
  "message": "Retried 2 failed roles"
}
```

---

## Workflow Steps (Phase 1 MVP)

The role onboarding workflow consists of these steps:

| Step | Timeout | Description |
|------|---------|-------------|
| `role_setup` | 5 min | Create/update CompanyRole node, link job description |
| `ai_assessment` | 30 min | Run AI Assessment workflow, extract automation scores |

**Future Steps (Phase 2+):**
- `skills_analysis` - Extract and analyze skills
- `task_feasibility` - Run task feasibility analysis
- `finalize` - Final validation and dashboard generation

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `NOT_FOUND` | 404 | Workflow or batch not found |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `EXECUTION_ERROR` | 500 | Workflow execution failed |

---

## Usage Examples

### Python Example - Single Role

```python
import requests

# Push a single role
response = requests.post(
    "http://localhost:7071/api/v1/pipeline/push",
    json={
        "company_id": "liberty-mutual",
        "role_name": "Claims Adjuster",
        "documents": [
            {
                "type": "job_description",
                "content": "Job Description content here..."
            }
        ],
        "draup_role_name": "Claims Handler"
    }
)
result = response.json()
workflow_id = result["workflow_id"]

# Check status
status = requests.get(
    f"http://localhost:7071/api/v1/pipeline/status/{workflow_id}"
).json()
print(f"Status: {status['status']}, Step: {status['current_step']}")
```

### Python Example - Batch Processing

```python
import requests
import time

# Submit batch
batch_response = requests.post(
    "http://localhost:7071/api/v1/pipeline/push-batch",
    json={
        "company_id": "liberty-mutual",
        "roles": [
            {"role_name": "Claims Adjuster", "draup_role_name": "Claims Handler"},
            {"role_name": "Underwriter", "draup_role_name": "Insurance Underwriter"},
            {"role_name": "Risk Analyst"}
        ]
    }
).json()

batch_id = batch_response["batch_id"]

# Poll for completion
while True:
    status = requests.get(
        f"http://localhost:7071/api/v1/pipeline/batch-status/{batch_id}"
    ).json()

    print(f"Progress: {status['progress_percent']:.1f}% "
          f"({status['completed']}/{status['total']} completed)")

    if status["state"] == "completed":
        break

    time.sleep(30)

# Retry failed roles if any
if status["failed"] > 0:
    retry = requests.post(
        f"http://localhost:7071/api/v1/pipeline/retry-failed/{batch_id}",
        json={"options": {"force_rerun": True}}
    ).json()
    print(f"Retried {retry['retried_count']} roles")
```

### cURL Examples

```bash
# Push single role
curl -X POST http://localhost:7071/api/v1/pipeline/push \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "liberty-mutual",
    "role_name": "Claims Adjuster",
    "draup_role_name": "Claims Handler"
  }'

# Check status
curl http://localhost:7071/api/v1/pipeline/status/role-onboard-abc123

# Health check
curl http://localhost:7071/api/v1/pipeline/health

# Push batch
curl -X POST http://localhost:7071/api/v1/pipeline/push-batch \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "liberty-mutual",
    "roles": [
      {"role_name": "Claims Adjuster"},
      {"role_name": "Underwriter"}
    ]
  }'

# Get batch status
curl http://localhost:7071/api/v1/pipeline/batch-status/batch-abc123

# Retry failed
curl -X POST http://localhost:7071/api/v1/pipeline/retry-failed/batch-abc123 \
  -H "Content-Type: application/json" \
  -d '{"options": {"force_rerun": true}}'
```

---

## Configuration

Key environment variables for API behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MOCK_DATA` | `true` | Use mock data providers |
| `REDIS_HOST` | `127.0.0.1` | Redis host for status storage |
| `REDIS_PORT` | `6390` | Redis port |
| `REDIS_PASSWORD` | - | Redis password (set via env) |
| `ETTER_DB_HOST` | - | Database host (for environment detection) |

---

## Interactive API Documentation

When running, OpenAPI documentation is available at:
- Swagger UI: `http://localhost:7071/docs`
- ReDoc: `http://localhost:7071/redoc`
