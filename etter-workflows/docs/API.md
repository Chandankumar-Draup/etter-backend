# Etter Workflows API Documentation

## Overview

The Etter Self-Service Pipeline API provides REST endpoints for managing role onboarding workflows.

**Base URL**: `http://localhost:8090/api/v1/pipeline`

**Content-Type**: `application/json`

---

## Quick Start

```bash
# Start the API server
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090

# Check health
curl http://localhost:8090/api/v1/pipeline/health

# Start a workflow
curl -X POST http://localhost:8090/api/v1/pipeline/push \
  -H "Content-Type: application/json" \
  -d '{"company_id": "TestCorp", "role_name": "QA Engineer"}'

# Check status
curl http://localhost:8090/api/v1/pipeline/status/{workflow_id}
```

---

## Endpoints

### 1. Health Check

Check API and dependency health.

```
GET /api/v1/pipeline/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-01-29T12:00:00Z",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "mock_data": "enabled"
  }
}
```

**Status Codes**:
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is degraded

---

### 2. Push Workflow

Start a new role onboarding workflow.

```
POST /api/v1/pipeline/push
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | boolean | `false` | Use mock AI assessment for testing |

**Request Body**:
```json
{
  "company_id": "TestCorp",
  "role_name": "QA Engineer",
  "documents": [
    {
      "type": "job_description",
      "name": "QA Engineer JD",
      "content": "Job description content...",
      "uri": null
    }
  ],
  "draup_role_id": null,
  "draup_role_name": "QA Engineer",
  "options": {
    "skip_enhancement_workflows": false,
    "force_rerun": false,
    "notify_on_complete": true
  }
}
```

**Required Fields**:
- `company_id` (string): Company identifier
- `role_name` (string): Role name to process

**Optional Fields**:
- `documents` (array): List of documents to link
- `draup_role_id` (string): Draup role ID for mapping
- `draup_role_name` (string): Draup role name for mapping
- `options` (object): Workflow options

**Response** (Success):
```json
{
  "workflow_id": "abc123-def456-...",
  "status": "queued",
  "estimated_duration_seconds": 600,
  "message": "Workflow started for QA Engineer at TestCorp"
}
```

**Response** (Validation Error):
```json
{
  "detail": {
    "error": "VALIDATION_ERROR",
    "message": "At least one document (job_description) or taxonomy entry with general_summary is required",
    "recoverable": false
  }
}
```

**Status Codes**:
- `200 OK` - Workflow queued successfully
- `400 Bad Request` - Validation error
- `500 Internal Server Error` - Server error

---

### 3. Get Workflow Status

Get the current status of a workflow.

```
GET /api/v1/pipeline/status/{workflow_id}
```

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow ID from push response |

**Response** (Processing):
```json
{
  "workflow_id": "abc123-def456-...",
  "role_id": null,
  "company_id": "TestCorp",
  "role_name": "QA Engineer",
  "status": "processing",
  "current_step": "ai_assessment",
  "progress": {
    "current": 1,
    "total": 2,
    "steps": [
      {
        "name": "role_setup",
        "status": "completed",
        "duration_ms": 1500,
        "started_at": "2026-01-29T12:00:00Z",
        "completed_at": "2026-01-29T12:00:01.5Z",
        "error_message": null
      },
      {
        "name": "ai_assessment",
        "status": "running",
        "duration_ms": null,
        "started_at": "2026-01-29T12:00:01.5Z",
        "completed_at": null,
        "error_message": null
      }
    ]
  },
  "queued_at": "2026-01-29T12:00:00Z",
  "started_at": "2026-01-29T12:00:00Z",
  "completed_at": null,
  "position_in_queue": null,
  "estimated_duration_seconds": 600,
  "dashboard_url": null,
  "error": null
}
```

**Response** (Completed):
```json
{
  "workflow_id": "abc123-def456-...",
  "role_id": "testcorp_qa_engineer",
  "company_id": "TestCorp",
  "role_name": "QA Engineer",
  "status": "ready",
  "current_step": null,
  "progress": {
    "current": 2,
    "total": 2,
    "steps": [
      {
        "name": "role_setup",
        "status": "completed",
        "duration_ms": 1500
      },
      {
        "name": "ai_assessment",
        "status": "completed",
        "duration_ms": 180000
      }
    ]
  },
  "completed_at": "2026-01-29T12:03:00Z",
  "dashboard_url": "https://etter.draup.com/dashboard/TestCorp/roles/testcorp_qa_engineer",
  "error": null
}
```

**Response** (Failed):
```json
{
  "workflow_id": "abc123-def456-...",
  "status": "failed",
  "error": {
    "code": "STEP_EXECUTION_ERROR",
    "message": "AI Assessment API returned error",
    "recoverable": true
  }
}
```

**Status Codes**:
- `200 OK` - Status retrieved
- `404 Not Found` - Workflow not found

---

### 4. List Companies

Get list of companies with available roles (from mock data).

```
GET /api/v1/pipeline/companies
```

**Response**:
```json
{
  "companies": [
    "Liberty Mutual",
    "Walmart Inc.",
    "Acme Corporation",
    "TestCorp"
  ],
  "total_count": 4
}
```

---

### 5. List Roles for Company

Get roles available for a specific company.

```
GET /api/v1/pipeline/roles/{company_name}
```

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `company_name` | string | Company name |

**Response**:
```json
{
  "company_name": "TestCorp",
  "roles": [
    {
      "job_id": "test-qa-001",
      "job_title": "QA Engineer",
      "job_role": "QA Engineer",
      "draup_role": "QA Engineer",
      "occupation": "Software and Mathematics",
      "job_family": "Software Quality Assurance Analysts",
      "status": "pending"
    }
  ],
  "total_count": 1
}
```

---

## Batch Processing

For processing multiple roles at once, see the batch endpoints below. Full documentation: [BATCH_PROCESSING.md](./BATCH_PROCESSING.md)

### 6. Push Batch

Submit multiple roles for processing.

```
POST /api/v1/pipeline/push-batch
```

**Request Body**:
```json
{
  "company_id": "liberty-mutual",
  "roles": [
    {"role_name": "Claims Adjuster", "draup_role_name": "Claims Handler"},
    {"role_name": "Underwriter", "draup_role_name": "Insurance Underwriter"},
    {"role_name": "Risk Analyst"}
  ],
  "options": {
    "skip_enhancement_workflows": false
  },
  "created_by": "admin@company.com"
}
```

**Response**:
```json
{
  "batch_id": "batch-abc123def456",
  "total_roles": 3,
  "workflow_ids": ["wf-1", "wf-2", "wf-3"],
  "status": "queued",
  "estimated_duration_seconds": 1800,
  "message": "Batch submitted: 3 roles queued for processing"
}
```

---

### 7. Get Batch Status

Get aggregated status for a batch.

```
GET /api/v1/pipeline/batch-status/{batch_id}
```

**Response**:
```json
{
  "batch_id": "batch-abc123def456",
  "company_id": "liberty-mutual",
  "total": 50,
  "queued": 10,
  "in_progress": 3,
  "completed": 35,
  "failed": 2,
  "state": "in_progress",
  "progress_percent": 74.0,
  "success_rate": 94.6,
  "roles": [
    {"role_name": "Data Analyst", "status": "ready", "workflow_id": "wf-1"},
    {"role_name": "ML Engineer", "status": "failed", "error": "...", "workflow_id": "wf-2"}
  ]
}
```

---

### 8. Retry Failed Roles

Retry failed roles in a batch.

```
POST /api/v1/pipeline/retry-failed/{batch_id}
```

**Request Body**:
```json
{
  "workflow_ids": ["wf-2", "wf-5"],
  "options": {"force_rerun": true}
}
```

**Response**:
```json
{
  "batch_id": "batch-abc123def456",
  "retried_count": 2,
  "new_workflow_ids": ["wf-new-1", "wf-new-2"],
  "message": "Retried 2 failed roles"
}
```

---

## Workflow States

| State | Description |
|-------|-------------|
| `queued` | Workflow is waiting to start |
| `processing` | Workflow is actively running |
| `ready` | Workflow completed successfully |
| `failed` | Workflow failed with error |
| `degraded` | Partial success (some steps failed) |
| `validation_error` | Input validation failed |

## Step States

| State | Description |
|-------|-------------|
| `pending` | Step not yet started |
| `running` | Step is currently executing |
| `completed` | Step finished successfully |
| `failed` | Step failed with error |
| `skipped` | Step was skipped |

---

## Error Codes

| Code | Description | Recoverable |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Input validation failed | No |
| `STEP_EXECUTION_ERROR` | Activity/step failed | Yes |
| `INTERNAL_ERROR` | Unexpected server error | Yes |
| `NOT_FOUND` | Resource not found | No |

---

## Rate Limits

| Limit | Value |
|-------|-------|
| Max concurrent workflows per company | 200 |
| Max queue depth | 1000 |

---

## Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8090/api/v1/pipeline"

# Start workflow
response = requests.post(
    f"{BASE_URL}/push",
    json={
        "company_id": "TestCorp",
        "role_name": "QA Engineer"
    }
)
workflow_id = response.json()["workflow_id"]

# Check status
status = requests.get(f"{BASE_URL}/status/{workflow_id}").json()
print(f"Status: {status['status']}")
```

### cURL

```bash
# Start workflow
curl -X POST http://localhost:8090/api/v1/pipeline/push \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "TestCorp",
    "role_name": "QA Engineer",
    "options": {"force_rerun": false}
  }'

# Check status
curl http://localhost:8090/api/v1/pipeline/status/WORKFLOW_ID

# Health check
curl http://localhost:8090/api/v1/pipeline/health
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8090/api/v1/pipeline";

// Start workflow
const pushResponse = await fetch(`${BASE_URL}/push`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    company_id: "TestCorp",
    role_name: "QA Engineer"
  })
});
const { workflow_id } = await pushResponse.json();

// Check status
const statusResponse = await fetch(`${BASE_URL}/status/${workflow_id}`);
const status = await statusResponse.json();
console.log(`Status: ${status.status}`);
```

---

## OpenAPI/Swagger

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8090/docs
- **ReDoc**: http://localhost:8090/redoc
- **OpenAPI JSON**: http://localhost:8090/openapi.json
