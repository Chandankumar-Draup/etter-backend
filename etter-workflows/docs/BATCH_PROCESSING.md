# Batch Processing for Role Onboarding

## Overview

Batch processing allows submitting multiple roles for onboarding in a single request. This document describes the design, API, and operational considerations for batch role processing.

## Design Principles

**"Each role is independent, batches are just bookkeeping"**

| What We Have | What We DON'T Need |
|--------------|-------------------|
| Independent workflows per role | Parent workflow coordinating children |
| Worker concurrency = natural throttle | Custom rate limiting code |
| Simple batch record (ID + workflow list) | Complex batch state machine |
| Partial success is fine | Transactional "all or nothing" |

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                    BATCH SUBMISSION                  │
│                                                      │
│  User selects: [Role A, Role B, Role C, ... Role N] │
│                         ↓                            │
│              POST /pipeline/push-batch               │
│                         ↓                            │
│  ┌─────────────────────────────────────────────┐    │
│  │  Create Batch Record (batch_id, role_ids[]) │    │
│  └─────────────────────────────────────────────┘    │
│                         ↓                            │
│     For each role → spawn independent workflow       │
│     (Temporal handles queueing automatically)        │
│                         ↓                            │
│  ┌──────┐ ┌──────┐ ┌──────┐     ┌──────┐           │
│  │WF-A  │ │WF-B  │ │WF-C  │ ... │WF-N  │           │
│  └──┬───┘ └──┬───┘ └──┬───┘     └──┬───┘           │
│     │        │        │            │                │
│  [Workers pick up based on capacity - natural throttle]
│                         ↓                            │
│         GET /pipeline/batch-status/{batch_id}        │
│         → Returns aggregated: 3/10 done, 1 failed    │
└─────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Submit Batch

**POST /api/v1/pipeline/push-batch**

Submit multiple roles for processing.

**Request:**
```json
{
    "company_id": "liberty-mutual",
    "roles": [
        {
            "role_name": "Claims Adjuster",
            "draup_role_name": "Claims Handler"
        },
        {
            "role_name": "Underwriter",
            "draup_role_name": "Insurance Underwriter"
        },
        {
            "role_name": "Risk Analyst"
        }
    ],
    "options": {
        "skip_enhancement_workflows": false,
        "force_rerun": false
    },
    "created_by": "admin@company.com"
}
```

**Response:**
```json
{
    "batch_id": "batch-abc123def456",
    "total_roles": 3,
    "workflow_ids": ["role-onboard-1", "role-onboard-2", "role-onboard-3"],
    "status": "queued",
    "estimated_duration_seconds": 1800,
    "message": "Batch submitted: 3 roles queued for processing"
}
```

### 2. Get Batch Status

**GET /api/v1/pipeline/batch-status/{batch_id}**

Get aggregated status for all roles in a batch.

**Response:**
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
    "created_at": "2024-01-15T10:30:00Z",
    "roles": [
        {
            "role_name": "Data Analyst",
            "company_id": "liberty-mutual",
            "workflow_id": "role-onboard-1",
            "status": "ready",
            "dashboard_url": "/dashboard/roles/cr-123"
        },
        {
            "role_name": "ML Engineer",
            "company_id": "liberty-mutual",
            "workflow_id": "role-onboard-2",
            "status": "failed",
            "error": "AI Assessment timeout"
        }
    ]
}
```

**Batch States:**
| State | Description |
|-------|-------------|
| `pending` | All roles queued, none started |
| `in_progress` | At least one role processing |
| `completed` | All roles done (success or fail) |
| `partial` | Completed with some failures |

### 3. Retry Failed Roles

**POST /api/v1/pipeline/retry-failed/{batch_id}**

Retry failed roles in a batch.

**Request (retry all failed):**
```json
{
    "options": {
        "force_rerun": true
    }
}
```

**Request (retry specific roles):**
```json
{
    "workflow_ids": ["role-onboard-2", "role-onboard-5"],
    "options": {
        "force_rerun": true
    }
}
```

**Response:**
```json
{
    "batch_id": "batch-abc123def456",
    "retried_count": 2,
    "new_workflow_ids": ["role-onboard-new-1", "role-onboard-new-2"],
    "message": "Retried 2 failed roles"
}
```

## Throttling & Rate Limiting

### Worker Concurrency (Natural Throttle)

The system uses Temporal worker concurrency as a natural throttle:

```python
# settings.py
temporal_max_concurrent_activities = 5  # 3-5 recommended
temporal_max_concurrent_workflows = 10
```

**Benefits:**
- No custom rate limiting code needed
- Workers self-regulate based on capacity
- System backpressure is automatic

### Expected Throughput

| Batch Size | Concurrent Workers | Estimated Time |
|------------|-------------------|----------------|
| 5 roles | 5 | ~15 min |
| 10 roles | 5 | ~30 min |
| 50 roles | 5 | ~2.5 hours |
| 100 roles | 5 | ~5 hours |

*Assuming ~15 min per role (mostly AI assessment time)*

## Error Handling

### Partial Failures

Each role processes independently. If one fails:
- Other roles continue processing
- Failed roles can be retried individually
- Batch status shows aggregate counts

### Validation Errors

Roles with validation errors are skipped during submission:
- Batch continues with valid roles
- Invalid roles logged with reason
- Use individual `/push` endpoint to debug

### Retry Strategy

1. Check batch status: `GET /batch-status/{batch_id}`
2. Review failed roles in response
3. Fix underlying issues (data, documents)
4. Retry: `POST /retry-failed/{batch_id}`

## Data Models

### BatchRecord

```python
@dataclass
class BatchRecord:
    batch_id: str        # "batch-abc123def456"
    workflow_ids: List[str]  # One per role
    company_id: str
    role_count: int
    created_at: datetime
    created_by: Optional[str]
    metadata: Dict[str, Any]
```

### BatchStatus (Computed)

```python
@dataclass
class BatchStatus:
    batch_id: str
    company_id: str
    total: int
    queued: int
    in_progress: int
    completed: int
    failed: int
    state: BatchState  # Computed from counts
    progress_percent: float
    success_rate: float
    roles: List[BatchRoleStatus]
```

## Implementation Details

### Storage

Batch records are stored in Redis with TTL:
- Key: `etter:batch:{batch_id}`
- TTL: 24 hours (configurable)
- Company index: `etter:company:batches:{company_id}`

### Status Aggregation

Batch status is computed on-demand by:
1. Loading batch record (workflow_ids list)
2. Querying each workflow status from Redis
3. Aggregating counts and states

This "pull" approach:
- Keeps batch record simple (just IDs)
- Always reflects current state
- No sync issues between batch and workflow states

## Best Practices

### Optimal Batch Sizes

| Scenario | Recommended Batch Size |
|----------|----------------------|
| Initial onboarding | 10-20 roles |
| Daily updates | 5-10 roles |
| Full company load | 50-100 roles (expect hours) |

### Monitoring

Poll batch status at reasonable intervals:
```
Small batches (<10): Every 30 seconds
Medium batches (10-50): Every 1 minute
Large batches (>50): Every 2-3 minutes
```

### Error Recovery

1. **Transient failures** (API timeouts): Auto-retry via Temporal
2. **Data issues** (missing JD): Fix data, then retry batch
3. **System issues** (worker down): Check health, restart workers

## Configuration

Environment variables for tuning:

```bash
# Worker concurrency (natural throttle)
ETTER_TEMPORAL_MAX_CONCURRENT_ACTIVITIES=5
ETTER_TEMPORAL_MAX_CONCURRENT_WORKFLOWS=10

# Status TTL
ETTER_REDIS_STATUS_TTL_SECONDS=86400

# Feature flag
ETTER_ENABLE_BATCH_PROCESSING=true
```

## Scaling Considerations

### Horizontal Scaling

To increase throughput:
1. Deploy more workers (each with concurrency=5)
2. Workers share the task queue
3. Temporal distributes work automatically

### Vertical Limits

Current limits per worker:
- 5 concurrent AI assessments
- 10 concurrent workflow executions

### Future Enhancements

- Priority queues for urgent batches
- Cost tracking per batch
- Audit logging
- Rate limiting per company
