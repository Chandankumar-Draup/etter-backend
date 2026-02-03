# API Package

## First Principle: What Is an API?

**An API is the front door to your system—it defines how the outside world interacts with your service.**

```
┌─────────────────┐         ┌─────────────────────────────────────┐
│   OUTSIDE       │         │           ETTER SYSTEM              │
│   WORLD         │         │                                      │
│                 │   API   │  ┌──────────┐    ┌──────────────┐  │
│  • Web UI       │ ──────▶ │  │  Routes  │───▶│  Workflows   │  │
│  • CLI tools    │         │  └──────────┘    └──────────────┘  │
│  • Other APIs   │ ◀────── │       │                             │
│  • Scripts      │  JSON   │       ▼                             │
│                 │         │  ┌──────────┐                       │
└─────────────────┘         │  │ Schemas  │                       │
                            │  └──────────┘                       │
                            └─────────────────────────────────────┘
```

## Mental Model: The Restaurant Host Stand

An API is like the host stand at a restaurant:

| Restaurant | API |
|------------|-----|
| Host greets customer | API receives request |
| Host checks reservation | API validates input |
| Host assigns table | API routes to handler |
| Waiter serves food | Response returned |
| Menu | API documentation |

**Key insight**: The host doesn't cook—they coordinate access to the kitchen.

## System Thinking: API as System Boundary

```
                    UNTRUSTED                    TRUSTED
                    ─────────                    ───────
                         │
    User Request    ─────┼────▶  Validation  ────▶  Workflow
    (unknown format)     │      (enforce schema)    (known good data)
                         │
                    ┌────┴────┐
                    │   API   │
                    │ BOUNDARY│
                    └─────────┘
```

**The API's job**:
1. Accept requests from untrusted sources
2. Validate and sanitize input
3. Translate to internal format
4. Call internal services
5. Translate response back
6. Return to caller

## Files in This Package

| File | Purpose |
|------|---------|
| `routes.py` | HTTP endpoint definitions (FastAPI) |
| `schemas.py` | Request/response Pydantic models |

## API Endpoints

### Core Workflow Endpoints

```
POST /api/v1/pipeline/push
────────────────────────────
Start a new role onboarding workflow

Request:
{
    "company_id": "Acme Corp",
    "role_name": "Software Engineer",
    "documents": [],
    "options": {
        "force_rerun": false,
        "notify_on_complete": true
    }
}

Response:
{
    "workflow_id": "abc-123",
    "status": "queued",
    "message": "Workflow started"
}
```

```
GET /api/v1/pipeline/status/{workflow_id}
────────────────────────────────────────────
Check workflow progress

Response:
{
    "workflow_id": "abc-123",
    "state": "processing",
    "progress": {
        "current_step": "ai_assessment",
        "completed_steps": ["role_setup"],
        "percent_complete": 50
    }
}
```

### Utility Endpoints

```
GET /api/v1/health
────────────────────
Health check for load balancers

Response:
{
    "status": "healthy",
    "timestamp": "2024-01-28T12:00:00Z"
}
```

```
GET /api/v1/roles/available
────────────────────────────
List available companies and roles

Response:
{
    "companies": [
        {
            "name": "Liberty Mutual",
            "roles": ["Claims Adjuster", "Underwriter"]
        }
    ]
}
```

## Request/Response Flow

```
1. HTTP Request arrives
        │
        ▼
2. FastAPI route handler
        │
        ▼
3. Pydantic validates request body ──▶ 400 Bad Request (if invalid)
        │
        ▼
4. Business logic executes
        │
        ▼
5. Pydantic serializes response
        │
        ▼
6. HTTP Response sent
```

## Schemas: The Contract

Schemas define exact request/response formats:

```python
# Request schema
class PushRequest(BaseModel):
    company_id: str = Field(..., min_length=1, description="Company name")
    role_name: str = Field(..., min_length=1, description="Role name")
    documents: List[DocumentInput] = Field(default_factory=list)
    options: PushOptions = Field(default_factory=PushOptions)

# Response schema
class PushResponse(BaseModel):
    workflow_id: str
    status: str
    message: str
```

**Why schemas?**:
- Auto-generate API documentation (Swagger/OpenAPI)
- Validate input automatically
- Type hints for IDE support
- Clear contract for API consumers

## Thought Experiment: Sync vs Async API

**Problem**: AI assessment takes 10-30 minutes. Do we:

**Option A: Synchronous** (wait for completion)
```
POST /assess ──▶ [wait 30 minutes] ──▶ Response
```
Problems: HTTP timeouts, blocked resources, poor UX

**Option B: Asynchronous** (return immediately, poll later)
```
POST /push ──▶ {"workflow_id": "123", "status": "queued"}

GET /status/123 ──▶ {"status": "processing", "step": 1}
GET /status/123 ──▶ {"status": "processing", "step": 2}
GET /status/123 ──▶ {"status": "ready", "result": {...}}
```

**We chose Option B** (async with polling).

## Error Handling

```python
# Structured error responses
class ErrorResponse(BaseModel):
    error: str           # Error type
    message: str         # Human-readable message
    details: Optional[dict]  # Additional context

# HTTP Status Codes
200 OK           - Success
201 Created      - Workflow started
400 Bad Request  - Invalid input
404 Not Found    - Workflow not found
500 Server Error - Internal failure
```

## FastAPI Features We Use

### 1. Automatic Validation

```python
@router.post("/push")
async def push_role(request: PushRequest):  # Auto-validated!
    ...
```

### 2. Automatic Documentation

Visit `http://localhost:8090/docs` for interactive Swagger UI.

### 3. Dependency Injection

```python
async def get_current_user(token: str = Header(...)):
    return validate_token(token)

@router.post("/push")
async def push_role(
    request: PushRequest,
    user: User = Depends(get_current_user)  # Injected!
):
    ...
```

### 4. Background Tasks

```python
@router.post("/push")
async def push_role(
    request: PushRequest,
    background_tasks: BackgroundTasks
):
    workflow_id = create_workflow()
    background_tasks.add_task(run_workflow, workflow_id)  # Runs after response
    return {"workflow_id": workflow_id, "status": "queued"}
```

## Running the API

```bash
# Development (with auto-reload)
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --reload

# Production
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --workers 4
```

## Quick Reference

```python
# Testing with curl
curl -X POST http://localhost:8090/api/v1/pipeline/push \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "Acme Corp",
    "role_name": "Software Engineer"
  }'

# Testing with Python
import httpx

response = httpx.post(
    "http://localhost:8090/api/v1/pipeline/push",
    json={
        "company_id": "Acme Corp",
        "role_name": "Software Engineer"
    }
)
workflow_id = response.json()["workflow_id"]

# Poll for status
status = httpx.get(f"http://localhost:8090/api/v1/pipeline/status/{workflow_id}")
print(status.json())
```

## Security Considerations

```
┌─────────────────────────────────────────────────────────────┐
│  PRODUCTION SECURITY CHECKLIST                               │
├─────────────────────────────────────────────────────────────┤
│  □ HTTPS only (TLS termination at load balancer)            │
│  □ Authentication (API keys or OAuth)                       │
│  □ Rate limiting (prevent abuse)                            │
│  □ Input validation (Pydantic handles this)                 │
│  □ CORS configuration (limit origins)                       │
│  □ Request size limits (prevent DoS)                        │
│  □ Logging (audit trail)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Summary

| Concept | API Responsibility |
|---------|-------------------|
| **Request validation** | Yes - schemas enforce contracts |
| **Authentication** | Yes - verify caller identity |
| **Business logic** | No - delegate to workflows |
| **Data storage** | No - delegate to clients |
| **Error translation** | Yes - internal errors → HTTP errors |

**Remember**: The API is a thin layer—validate, delegate, respond. It should be boring.
