# Etter Workflows - Package Context

## What This Package Does (First Principles)

**Core problem**: Role onboarding into the Etter platform required 4 manual engineering steps. This package automates that entire pipeline so non-engineers (Admin/CSM) can push roles via a single API call.

**The critical path**:
```
Push API call → Create CompanyRole → Link Job Description → Run AI Assessment → Dashboard Visible
```

That's it. Three activities, orchestrated by Temporal, exposed via FastAPI.

---

## Architecture (Minimal Mental Model)

```
┌─────────────────────────────┐
│  FastAPI (etter-backend)    │  Port 7071
│  /api/v1/pipeline/*         │  Routes defined in api/routes.py
└──────────┬──────────────────┘
           │ Submits workflow
           ▼
┌─────────────────────────────┐
│  Temporal Server            │  Port 7233
│  Namespace: etter-dev (QA)  │  Task Queue: etter-workflows
│           etter-prod (Prod) │
└──────────┬──────────────────┘
           │ Executes activities
           ▼
┌─────────────────────────────┐
│  draup-world API            │  Port 8083 (local) or draup-world URLs (QA/prod)
│  /api/automated_workflows/* │  The actual backend doing the work
└─────────────────────────────┘
```

**Key insight**: This package is a thin orchestration layer. The real work happens in the `draup-world` API. This package handles sequencing, retries, status tracking, and the REST interface.

---

## Directory Map

```
etter-workflows/
├── etter_workflows/           # Installable Python package
│   ├── activities/            # Temporal activity definitions (the "do" layer)
│   │   ├── base.py            # BaseActivity ABC, retry decorator, ActivityContext
│   │   ├── role_setup.py      # create_company_role, link_job_description
│   │   └── ai_assessment.py   # run_ai_assessment, MockAIAssessmentActivity
│   │
│   ├── workflows/             # Temporal workflow definitions (the "orchestrate" layer)
│   │   ├── base.py            # BaseWorkflow ABC, WorkflowStep, status helpers
│   │   └── role_onboarding.py # RoleOnboardingWorkflow (main workflow)
│   │
│   ├── api/                   # FastAPI REST layer (the "expose" layer)
│   │   ├── routes.py          # All endpoint handlers (push, status, batch, health)
│   │   └── schemas.py         # Pydantic request/response models
│   │
│   ├── clients/               # External service clients (the "connect" layer)
│   │   ├── automated_workflows_client.py  # HTTP client to draup-world API
│   │   ├── status_client.py               # Redis client for status tracking
│   │   ├── workflow_api_client.py         # Legacy workflow API client
│   │   ├── llm_client.py                 # LLM integration client
│   │   └── neo4j_client.py               # Graph database client
│   │
│   ├── models/                # Data models (the "shape" layer)
│   │   ├── inputs.py          # RoleOnboardingInput, DocumentRef, ExecutionContext
│   │   ├── outputs.py         # WorkflowResult, ActivityResult, AssessmentOutputs
│   │   ├── status.py          # RoleStatus, WorkflowState (state machine)
│   │   └── batch.py           # BatchRecord, BatchStatus
│   │
│   ├── config/                # Configuration
│   │   ├── settings.py        # Pydantic Settings (env-based), environment detection
│   │   └── retry_policies.py  # RetryConfig presets (default, LLM, DB, API)
│   │
│   ├── mock_data/             # Test/development data providers
│   │   ├── api_providers.py   # Mock API response providers
│   │   ├── documents.py       # Mock document data
│   │   └── role_taxonomy.py   # Mock role taxonomy
│   │
│   └── worker.py              # Temporal worker entry point (WorkerManager)
│
├── tests/                     # Test suite
├── docs/                      # Documentation
├── test_all_apis.py           # Comprehensive API test suite
└── pyproject.toml             # Package config
```

---

## The 3 Activities

All activities call the `draup-world` API (`/api/automated_workflows/*`). The `AutomatedWorkflowsClient` handles HTTP with retry.

### 1. `create_company_role`
- **File**: `activities/role_setup.py:172`
- **API**: `POST /api/automated_workflows/create-company-role`
- **Input**: company_name, role_name, draup_role
- **Output**: `{ company_role_id }` - the ID used by all subsequent activities
- **Timeout**: 5 min, 3 retries (DB retry policy)

### 2. `link_job_description`
- **File**: `activities/role_setup.py:245`
- **API**: `POST /api/automated_workflows/link-job-description`
- **Input**: company_role_id, jd_content OR jd_uri (S3 presigned URL), metadata
- **Output**: `{ jd_linked: bool }`
- **Timeout**: 5 min, 2 retries
- **Note**: Supports both inline content and S3 download URLs. The API handles PDF extraction.

### 3. `run_ai_assessment`
- **File**: `activities/ai_assessment.py:181`
- **API**: `POST /api/automated_workflows/run-ai-assessment`
- **Input**: company_name, role_name, company_role_id, delete_existing, store_in_neo4j
- **Output**: Assessment results with ai_automation_score, task analysis, impact data
- **Timeout**: 30 min, 5 retries (LLM retry policy - handles rate limits)

---

## The Workflow

### `RoleOnboardingWorkflow`
- **File**: `workflows/role_onboarding.py:77`
- **Steps**: `role_setup` → `ai_assessment`
- **State machine**: `QUEUED → PROCESSING → READY` (or `FAILED`)

**Dual execution mode**:
- **Temporal mode**: Uses `workflow.execute_activity()` for each step. Temporal handles retries, timeouts, and state persistence.
- **Standalone mode**: Direct class instantiation (`RoleSetupActivity`, `AIAssessmentActivity`). Used when Temporal is unavailable.

**The workflow detects mode** via `is_temporal_workflow_context()` (checks if `workflow.info()` succeeds).

**Document resolution** (in the workflow, not the activity):
1. Try `input.get_job_description()` (Pydantic model method)
2. Iterate documents manually (handles dict/object from Temporal serialization)
3. Fallback to first document with URI
4. Fallback to taxonomy entry content
5. Last resort: use role name as placeholder

---

## API Endpoints

**Base**: `/api/v1/pipeline` (router prefix: `/v1/pipeline`, mounted under `/api`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/push` | Start single role workflow via Temporal |
| `GET` | `/status/{workflow_id}` | Query Temporal + Redis for workflow state |
| `GET` | `/health` | Temporal connection + component health |
| `GET` | `/companies` | List companies (from mock/taxonomy data) |
| `GET` | `/roles/{company_name}` | Get roles for company |
| `POST` | `/push-batch` | Submit multiple roles (independent Temporal workflows) |
| `GET` | `/batch-status/{batch_id}` | Aggregated status across batch |
| `POST` | `/retry-failed/{batch_id}` | Retry failed roles in batch |

**Document handling on push**:
- If documents provided in request → use them directly (uri or content)
- If no documents → auto-fetch from `/api/documents/?roles={role_name}` (etter-backend endpoint)
- Priority: PDF > DOCX > Images > Other, latest first
- If still no documents → return 400

---

## State Machine

```
DRAFT → QUEUED → PROCESSING → READY
                      ↓
                    FAILED → (retry) → QUEUED
                    DEGRADED
READY → STALE → (re-run) → QUEUED
```

**Status tracking**: Redis (key: `etter:workflow:status:{workflow_id}`, TTL: 24h).
In Temporal mode, Redis updates are skipped (Temporal provides its own state tracking).

---

## Configuration (Environment Detection)

**File**: `config/settings.py`

The system auto-detects environment from `ETTER_DB_HOST`:
- **Local** (empty/localhost): Uses `localhost:7233` for Temporal, `localhost:8083` for API
- **QA** (contains "qa" or "dev-gateway"): Uses QA Temporal host, QA draup-world URL
- **Prod** (non-local, non-QA): Uses Prod Temporal host, Prod draup-world URL

**Key env vars**:
| Variable | Default | What it controls |
|----------|---------|-----------------|
| `ETTER_DB_HOST` | `""` | Environment detection (local vs QA vs prod) |
| `TEMPORAL_HOST` | `localhost` | Temporal server host (overridden by env detection) |
| `TEMPORAL_PORT` | `7233` | Temporal server port |
| `AUTOMATED_WORKFLOWS_API_BASE_URL` | `http://127.0.0.1:8083` | draup-world API |
| `REDIS_HOST` | `127.0.0.1` | Redis for status tracking |
| `REDIS_PORT` | `6390` | Redis port |
| `ENABLE_MOCK_DATA` | `false` | Mock data mode |
| `ETTER_AUTH_TOKEN` | `None` | Bearer token for API auth |

---

## Retry Policies

| Policy | Max Attempts | Initial Interval | Max Interval | Use Case |
|--------|-------------|------------------|--------------|----------|
| Default | 3 | 1s | 5min | General activities |
| LLM | 5 | 5s | 10min | AI assessment (rate limits) |
| DB | 2 | 2s | 30s | Role creation, JD linking |
| API | 3 | 1s | 1min | External API calls |
| None | 1 | - | - | Idempotent operations |

Non-retryable errors: `ValidationError`, `AuthenticationError`, `HTTPError` (for DB policy).

---

## Batch Processing

**Design**: "Each role is independent, batches are just bookkeeping."
- No parent workflow coordinating children
- No custom rate limiting (Temporal handles it)
- Partial success is fine
- Batch record stored in Redis with workflow ID list
- Status is computed by querying individual workflow statuses

---

## Worker

**File**: `worker.py`
**Entry point**: `etter-worker` CLI or `python -m etter_workflows.worker`

Registers:
- Activities: `create_company_role`, `link_job_description`, `run_ai_assessment`
- Workflows: `RoleOnboardingWorkflow`
- Uses `UnsandboxedWorkflowRunner` (Pydantic models use `datetime.utcnow()` in defaults)

**Concurrency**: 5 activities, 10 workflows (configurable).

---

## Integration with etter-backend

The package is installed as editable dependency: `pip install -e ./etter-workflows` (in requirements.txt).

The FastAPI router is mounted in the parent app, making endpoints available at `localhost:7071/api/v1/pipeline/*`.

---

## Testing

- `test_all_apis.py`: Comprehensive test script with multiple modes (health, push, batch, status)
- `tests/test_api.py`: API endpoint unit tests
- `tests/test_workflows.py`: Workflow execution tests
- `test_pharmacist_e2e.py`: End-to-end test for pharmacist role

---

## Key Design Decisions

1. **Temporal for orchestration, not computation**: Activities are thin wrappers around HTTP calls to draup-world API.
2. **Dual-mode execution**: Works with or without Temporal (standalone mode for dev/testing).
3. **Environment auto-detection**: Single codebase deploys to local/QA/prod without code changes.
4. **Redis for ephemeral status**: High-frequency updates, 24h TTL, acceptable loss. Temporal is the source of truth.
5. **No Temporal sandbox**: Uses `UnsandboxedWorkflowRunner` due to Pydantic datetime defaults. Workflows must be manually careful about determinism.
6. **Documents flow through workflow, not activity**: The `RoleOnboardingWorkflow.execute()` resolves documents and passes content/URI to `link_job_description` activity.
