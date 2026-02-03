# Etter Self-Service Pipeline: Implementation Plan & Architecture

**Document Type:** Implementation Plan  
**Version:** 1.0  
**Date:** January 2026  
**Author:** Architecture Team

---

## 1. Executive Summary

### The Problem (First Principles)

At its irreducible core, the problem is a **coupling violation**: business logic (what to do) is tightly coupled with execution mechanism (how to run it). Currently, an engineer must SSH into a machine to run Python scripts for every role onboarding.

```
CURRENT STATE (Tight Coupling):
┌──────────────┐
│   Engineer   │ ← Required for every operation
│   + Scripts  │
│   + Access   │
└──────┬───────┘
       │ (bottleneck)
       ▼
┌──────────────┐
│   Outputs    │
└──────────────┘
```

### The Solution (Decoupling via Orchestration)

Introduce an **orchestration layer** that decouples:
- **Who** can trigger (Admin/CSM vs Engineer)
- **What** executes (Activities)
- **When** it runs (Queue + Scheduler)
- **How** it tracks (State Machine)

```
TARGET STATE (Decoupled):
┌─────────┐     ┌─────────────┐     ┌───────────┐     ┌─────────┐
│  User   │────▶│ Orchestrator │────▶│  Workers  │────▶│ Outputs │
│  (UI)   │     │  (Temporal)  │     │(Activities)│    │  (DB)   │
└─────────┘     └─────────────┘     └───────────┘     └─────────┘
       │                │                  │
       │                │                  │
       │         ┌──────▼──────┐          │
       └────────▶│   Status    │◀─────────┘
                 │  (Polling)  │
                 └─────────────┘
```

### Core Architectural Decision

**Temporal as the Orchestration Engine** because:
1. Already self-hosted (qa-temporal-client.qa-internal-draup.technology:31100)
2. Provides state persistence, retries, and visibility out-of-the-box
3. Decouples workflow definition from execution
4. Enables durable execution with automatic recovery

---

## 2. System Model

### 2.1 First Principles Decomposition

**Question:** What is the minimum set of capabilities for self-service?

| Capability | Why Irreducible |
|------------|-----------------|
| **Trigger mechanism** | User must initiate action |
| **State tracking** | User must know progress |
| **Execution isolation** | One failure ≠ system failure |
| **Error visibility** | User must understand failures |
| **Idempotency** | Same action = same result |

**Question:** What is the critical path for value delivery?

```
IRREDUCIBLE CRITICAL PATH:
Role Defined → Document Linked → AI Assessment → Dashboard Visible
    │               │                 │                │
    ▼               ▼                 ▼                ▼
  P0              P0               P0              P0

Everything else is ENHANCEMENT (P1, P2).
```

### 2.2 System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM CONTEXT                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        CONTROL PLANE                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ Auth/AuthZ   │  │ Rate Limits  │  │  Audit Log   │  │ Permissions  │   │  │
│  │  │  (Existing)  │  │  (New: P2)   │  │  (New: P2)   │  │  (Existing)  │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     ORCHESTRATION PLANE (NEW)                              │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                      TEMPORAL SERVER                                  │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │  │
│  │  │  │  Workflow   │  │   State     │  │   Queue     │  │  Visibility │  │ │  │
│  │  │  │ Definitions │  │  Machine    │  │  Management │  │    API      │  │ │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │  │
│  │  └──────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         DATA PLANE (EXISTING)                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │    Neo4j     │  │    Redis     │  │  PostgreSQL  │  │    S3/Blob   │   │  │
│  │  │   (Graph)    │  │   (Cache)    │  │   (Config)   │  │   (Docs)     │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Self-Similar Architecture Pattern

The same interface contract applies at every scale:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SELF-SIMILAR INTERFACE CONTRACT                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Every component (Activity, Workflow, Pipeline) implements:                  │
│                                                                              │
│  INPUT:                                                                      │
│  {                                                                           │
│    "id": "unique-identifier",                                                │
│    "inputs": { ... },                                                        │
│    "context": { "company_id": "...", "user_id": "...", "trace_id": "..." }  │
│  }                                                                           │
│                                                                              │
│  OUTPUT:                                                                     │
│  {                                                                           │
│    "id": "same-identifier",                                                  │
│    "status": "pending | running | completed | failed",                       │
│    "progress": { "current": N, "total": M },                                │
│    "outputs": { ... } | null,                                                │
│    "error": { "code": "...", "message": "...", "recoverable": bool } | null │
│  }                                                                           │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  ATOMIC (Activity)     │  COMPOSITE (Workflow)    │  AGGREGATE (Pipeline)    │
│  ─────────────────     │  ─────────────────────   │  ──────────────────────  │
│  create_role           │  role_setup_workflow     │  full_onboarding_pipeline│
│  link_document         │  ai_assessment_workflow  │                          │
│  run_ai_assessment     │  skills_analysis_workflow│                          │
│                        │                          │                          │
│  Timeout: minutes      │  Timeout: 10-30 min      │  Timeout: hours          │
│  Retry: 3x             │  Retry: per-activity     │  Retry: per-workflow     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. State Machine Design

### 3.1 Role Lifecycle States

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
│  │  • Has at least one document (JD or Process Map)?                   │    │
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
│  │  • SKILLS    │                                                   │   │   │
│  │  • FINALIZE  │                                                   │   │   │
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

STATE TRANSITIONS (Allowed):
  DRAFT → QUEUED (push action)
  DRAFT → VALIDATION_ERROR (missing docs)
  QUEUED → PROCESSING (worker picks up)
  PROCESSING → READY (success)
  PROCESSING → DEGRADED (partial success)
  PROCESSING → FAILED (error)
  FAILED → QUEUED (retry)
  READY → STALE (inputs changed)
  STALE → QUEUED (re-run)
  VALIDATION_ERROR → DRAFT (user fixes)
```

### 3.2 State Persistence Strategy

| State | Storage | Rationale |
|-------|---------|-----------|
| **Workflow execution state** | Temporal | Durability, automatic recovery |
| **Role status** | PostgreSQL | Fast reads for UI polling |
| **Progress details** | Redis (TTL: 1 hour) | High-frequency updates, acceptable loss |
| **Audit trail** | PostgreSQL | Compliance, immutability |

---

## 4. Package Architecture

### 4.1 Package Structure (Self-Sufficient Temporal Package)

```
etter-workflows/                    # External self-sufficient package
├── pyproject.toml                  # Package configuration
├── README.md                       # Usage documentation
├── etter_workflows/
│   ├── __init__.py
│   │
│   ├── activities/                 # Atomic operations (migrated scripts)
│   │   ├── __init__.py
│   │   ├── base.py                 # Base activity with standard interface
│   │   ├── role_setup.py           # create_company_role, link_documents
│   │   ├── ai_assessment.py        # run_ai_assessment
│   │   ├── skills.py               # skills_miner, skills_architecture
│   │   ├── tasks.py                # step_executor, task_feasibility
│   │   └── catalog.py              # skills_catalog, role_catalog
│   │
│   ├── workflows/                  # Orchestration logic
│   │   ├── __init__.py
│   │   ├── base.py                 # Base workflow with standard interface
│   │   ├── role_onboarding.py      # Full pipeline workflow
│   │   ├── ai_assessment.py        # AI Assessment sub-workflow
│   │   ├── skills_analysis.py      # Skills sub-workflow
│   │   └── batch_processing.py     # Batch role processing
│   │
│   ├── models/                     # Shared data models
│   │   ├── __init__.py
│   │   ├── inputs.py               # RoleOnboardingInput, BatchInput
│   │   ├── outputs.py              # AssessmentResult, WorkflowResult
│   │   └── status.py               # RoleStatus, ProgressInfo
│   │
│   ├── config/                     # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py             # Environment-based config
│   │   └── retry_policies.py       # Retry configurations
│   │
│   ├── clients/                    # External service clients
│   │   ├── __init__.py
│   │   ├── neo4j_client.py         # Graph DB operations
│   │   ├── llm_client.py           # LLM service (ModelManager)
│   │   └── status_client.py        # Status update service
│   │
│   └── worker.py                   # Worker entry point
│
└── tests/
    ├── unit/
    │   ├── test_activities/
    │   └── test_workflows/
    └── integration/
        └── test_end_to_end.py
```

### 4.2 Component Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY DIRECTION                                 │
│                         (Inward = Dependent On)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              ┌─────────────┐                                │
│                              │   Models    │ ← Pure data, no dependencies  │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                    ┌────────────────┼────────────────┐                      │
│                    │                │                │                      │
│                    ▼                ▼                ▼                      │
│             ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│             │   Config    │  │   Clients   │  │  Retry      │               │
│             │             │  │             │  │  Policies   │               │
│             └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│                    │                │                │                      │
│                    └────────────────┼────────────────┘                      │
│                                     │                                       │
│                                     ▼                                       │
│                              ┌─────────────┐                                │
│                              │ Activities  │ ← Atomic operations            │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                                     ▼                                       │
│                              ┌─────────────┐                                │
│                              │  Workflows  │ ← Orchestration                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                                     ▼                                       │
│                              ┌─────────────┐                                │
│                              │   Worker    │ ← Entry point                  │
│                              └─────────────┘                                │
│                                                                             │
│  RULE: Dependencies flow INWARD only. Activities never import Workflows.    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Interface Contracts

**Activity Base Interface:**
```
ActivityInput:
  - role_id: str (or inputs needed for the operation)
  - context: ExecutionContext (company_id, user_id, trace_id)

ActivityOutput:
  - status: "success" | "partial" | "failed"
  - result: domain-specific output | None
  - error: ErrorInfo | None
  - metrics: ExecutionMetrics (duration, tokens_used, etc.)
```

**Workflow Base Interface:**
```
WorkflowInput:
  - company_id: str
  - role_name: str
  - documents: List[DocumentRef]
  - draup_role_id: str
  - options: WorkflowOptions (skip_steps, force_rerun, etc.)

WorkflowOutput:
  - workflow_id: str (Temporal workflow ID)
  - role_id: str (created role ID)
  - status: RoleStatus
  - steps_completed: List[StepResult]
  - outputs: AssessmentOutputs | None
  - error: ErrorInfo | None
```

---

## 5. API Design

### 5.1 API Endpoints

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/v1/pipeline/push` | POST | Start role onboarding workflow | P0 |
| `/api/v1/pipeline/status/{workflow_id}` | GET | Get workflow status | P0 |
| `/api/v1/pipeline/batch` | POST | Start batch processing | P1 |
| `/api/v1/pipeline/retry/{workflow_id}` | POST | Retry failed workflow | P1 |
| `/api/v1/pipeline/cancel/{workflow_id}` | POST | Cancel running workflow | P2 |
| `/api/v1/pipeline/history/{company_id}` | GET | List workflow history | P2 |

### 5.2 Request/Response Models

**Push Request:**
```
POST /api/v1/pipeline/push
{
  "company_id": "liberty-mutual",
  "role_name": "Claims Adjuster",
  "documents": [
    {"type": "job_description", "uri": "s3://bucket/jd.pdf"},
    {"type": "process_map", "uri": "s3://bucket/pm.pdf"}
  ],
  "draup_role_id": "draup-role-12345",
  "options": {
    "skip_enhancement_workflows": false,
    "notify_on_complete": true
  }
}
```

**Push Response:**
```
{
  "workflow_id": "role-onboard-abc123",
  "role_id": "cr-liberty-claims-adjuster",
  "status": "queued",
  "estimated_duration_seconds": 600,
  "position_in_queue": 3
}
```

**Status Response:**
```
{
  "workflow_id": "role-onboard-abc123",
  "role_id": "cr-liberty-claims-adjuster",
  "status": "processing",
  "current_step": "ai_assessment",
  "progress": {
    "current": 2,
    "total": 5,
    "steps": [
      {"name": "role_setup", "status": "completed", "duration_ms": 1200},
      {"name": "document_linking", "status": "completed", "duration_ms": 800},
      {"name": "ai_assessment", "status": "running", "started_at": "..."},
      {"name": "skills_analysis", "status": "pending"},
      {"name": "finalize", "status": "pending"}
    ]
  },
  "dashboard_url": null,  // populated when READY
  "error": null
}
```

---

## 6. Second-Order Thinking Analysis

### 6.1 Consequence Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SECOND-ORDER CONSEQUENCE CHAIN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FIRST ORDER: Users can push roles without engineering                       │
│       │                                                                     │
│       ├──▶ SECOND ORDER: Volume increases significantly                     │
│       │         │                                                           │
│       │         ├──▶ THIRD ORDER: LLM costs spike                           │
│       │         │         │                                                 │
│       │         │         └──▶ MITIGATION: Cost allocation per company      │
│       │         │                           Rate limiting per tier          │
│       │         │                                                           │
│       │         └──▶ THIRD ORDER: Queue depth grows                         │
│       │                   │                                                 │
│       │                   └──▶ MITIGATION: Priority queues                  │
│       │                                     Horizontal scaling               │
│       │                                                                     │
│       ├──▶ SECOND ORDER: Bad inputs possible                                │
│       │         │                                                           │
│       │         └──▶ THIRD ORDER: Bad outputs damage trust                  │
│       │                   │                                                 │
│       │                   └──▶ MITIGATION: Validation layer                 │
│       │                                     Confidence scoring               │
│       │                                     Human review flags              │
│       │                                                                     │
│       └──▶ SECOND ORDER: Support burden shifts to CSM                       │
│                 │                                                           │
│                 └──▶ THIRD ORDER: CSM needs training                        │
│                           │                                                 │
│                           └──▶ MITIGATION: Clear error messages             │
│                                             Documentation                    │
│                                             Self-service troubleshooting    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Mitigations Built Into Design

| Second-Order Effect | Mitigation | Phase |
|---------------------|------------|-------|
| Volume spike | Rate limiting per company | P2 |
| Cost explosion | Token metering per workflow | P2 |
| Quality degradation | Input validation layer | P0 |
| User confusion | Clear status + error messages | P0 |
| Support overload | Self-service retry mechanism | P1 |
| System overload | Backpressure (queue limits) | P1 |

---

## 7. Thought Experiments Applied

### 7.1 Thought Experiment: 2,500 Roles at Once

**Scenario:** Liberty Mutual wants to onboard all 2,500 roles simultaneously.

**System Behavior:**
1. Validation rejects roles without documents (~500 roles → batch size: 2000)
2. Queue accepts with company-specific limit (max 200 concurrent per company)
3. Remaining 1,800 enter waiting state with position visibility
4. Workers process at ~10 roles/minute (rate-limited by LLM)
5. Full batch completes in ~3-4 hours with progress updates

**Design Implications:**
- Need batch endpoint with smart chunking
- Need queue position visibility
- Need company-level concurrency limits
- Need estimated completion time

### 7.2 Thought Experiment: Partial Failure Recovery

**Scenario:** AI Assessment completes, but Skills Architecture fails mid-way.

**System Behavior:**
1. Workflow enters DEGRADED state (not FAILED)
2. Role visible in dashboard with core metrics (AI Assessment done)
3. Skills section shows "Analysis in progress" or "Retry needed"
4. User can trigger selective retry of Skills workflows only
5. Completed work (AI Assessment) is preserved

**Design Implications:**
- State machine needs DEGRADED state
- Activities must be idempotent
- Workflow must checkpoint after each step
- Selective retry API needed

### 7.3 Thought Experiment: Document Replacement

**Scenario:** User uploads wrong JD, Assessment runs, user wants to fix.

**System Behavior:**
1. User replaces document in Repository
2. System detects input change for existing role
3. Role status changes to STALE
4. User dashboard shows "Re-assessment recommended"
5. User triggers re-run, only affected steps execute

**Design Implications:**
- Need document change detection
- Need input hashing for staleness check
- Need dependency graph for selective re-run
- STALE state in state machine

---

## 8. Workflow Dependency Graph

### 8.1 Activity Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW DEPENDENCY GRAPH                             │
│                        (Arrows show "depends on")                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌───────────────┐                                   │
│                         │  Role Setup   │ (P0)                              │
│                         │  + Document   │                                   │
│                         │    Linking    │                                   │
│                         └───────┬───────┘                                   │
│                                 │                                           │
│                                 ▼                                           │
│                         ┌───────────────┐                                   │
│                         │ AI Assessment │ (P0) ← CRITICAL PATH              │
│                         │               │                                   │
│                         └───────┬───────┘                                   │
│                                 │                                           │
│               ┌─────────────────┼─────────────────┐                        │
│               │                 │                 │                         │
│               ▼                 ▼                 ▼                         │
│       ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │
│       │  Top Tasks  │   │Skills Miner │   │ Task Feas.  │ (P1)             │
│       │  (P1)       │   │  (P1)       │   │             │                  │
│       └──────┬──────┘   └──────┬──────┘   └─────────────┘                  │
│              │                 │                                            │
│              ▼                 ▼                                            │
│       ┌─────────────┐   ┌─────────────┐                                    │
│       │Standardize  │   │ Skills Arch │ (P1)                               │
│       │   (P1)      │   │             │                                    │
│       └─────────────┘   └──────┬──────┘                                    │
│                                │                                            │
│                                ▼                                            │
│                         ┌─────────────┐                                    │
│                         │Skills Catalog│ (P2)                               │
│                         │ + Reskilling│                                    │
│                         └─────────────┘                                    │
│                                                                             │
│  PARALLEL EXECUTION:                                                        │
│  - After AI Assessment: Top Tasks, Skills Miner, Task Feasibility          │
│  - These can run concurrently to reduce total time                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Workflow Composition

```
RoleOnboardingWorkflow (Parent)
├── RoleSetupActivity (sync, short)
├── DocumentLinkingActivity (sync, short)
├── AIAssessmentWorkflow (child workflow, long-running)
│   └── AIAssessmentActivity (async, 5-15 min)
├── [PARALLEL GROUP - after AI Assessment]
│   ├── TopTasksWorkflow
│   │   ├── StepExecutorActivity
│   │   └── StandardizationActivity
│   ├── SkillsAnalysisWorkflow
│   │   ├── SkillsMinerActivity
│   │   └── SkillsArchitectureActivity
│   └── TaskFeasibilityActivity
├── SkillsCatalogActivity (after Skills Analysis)
└── FinalizeActivity (dashboard visibility)
```

---

## 9. Implementation Phases

### 9.1 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION TIMELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 0: INFRASTRUCTURE (Week 1-2) [BLOCKING]                              │
│  ├── Temporal connectivity verification                                     │
│  ├── Worker deployment setup                                                │
│  ├── Package structure creation                                             │
│  └── CI/CD pipeline                                                         │
│                                                                             │
│  PHASE 1: MVP (Week 3-5) [USABLE]                                          │
│  ├── Migrate: create_company_role → Activity                                │
│  ├── Migrate: link_documents → Activity                                     │
│  ├── Migrate: run_ai_assessment → Activity                                  │
│  ├── Create: RoleOnboardingWorkflow (basic)                                 │
│  ├── Create: FastAPI endpoints (push, status)                               │
│  └── Create: Basic UI (push button, status display)                         │
│                                                                             │
│  ── CHECKPOINT: Self-service AI Assessment available ──                     │
│                                                                             │
│  PHASE 2: CORE WORKFLOWS (Week 6-8)                                         │
│  ├── Migrate: step_executor, standardisation → Activities                   │
│  ├── Migrate: skills_miner, skills_architecture → Activities                │
│  ├── Create: Child workflows with parallel execution                        │
│  ├── Create: Progress tracking per step                                     │
│  └── Create: Retry mechanism                                                │
│                                                                             │
│  PHASE 3: ENHANCEMENT (Week 9-11)                                           │
│  ├── Migrate: task_feasibility, skills_catalog → Activities                 │
│  ├── Create: Batch processing endpoint                                      │
│  ├── Create: Selective re-run capability                                    │
│  ├── Create: Input validation layer                                         │
│  └── Create: Error messaging improvements                                   │
│                                                                             │
│  PHASE 4: SCALE (Week 12+)                                                  │
│  ├── Rate limiting implementation                                           │
│  ├── Cost tracking per workflow                                             │
│  ├── Audit logging                                                          │
│  ├── Priority queues                                                        │
│  └── Horizontal scaling triggers                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Phase 0: Infrastructure Details

**Temporal Connectivity:**
```
Development:
  ssh -N -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
      ShreyashKumar-Draup@3.128.8.200

Production:
  Direct connection to temporal-server.internal:7233
```

**Namespace Strategy:**
```
etter-dev       → Development/testing
etter-staging   → Pre-production validation
etter-prod      → Production workloads
```

**Worker Configuration:**
```
Workers per environment:
  Dev:     1 worker, 10 concurrent activities
  Staging: 2 workers, 20 concurrent activities
  Prod:    4 workers, 50 concurrent activities (auto-scale)
```

### 9.3 Phase 1: MVP Deliverables

| Deliverable | Definition of Done |
|-------------|-------------------|
| Activity: create_company_role | Passes existing test cases, creates Neo4j node |
| Activity: link_documents | Links JD to CompanyRole in Neo4j |
| Activity: run_ai_assessment | Produces assessment scores, stores in DB |
| Workflow: RoleOnboarding | Orchestrates 3 activities with error handling |
| API: POST /pipeline/push | Starts workflow, returns workflow_id |
| API: GET /pipeline/status | Returns current status with step progress |
| UI: Push button | In Taxonomy Builder, triggers push API |
| UI: Status display | Shows waiting/running/done/error |

---

## 10. Metrics Framework

### 10.1 System Health Metrics

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| **Queue depth** | Workflows waiting | < 100 | > 200 |
| **Processing time p50** | Median workflow duration | < 10 min | > 15 min |
| **Processing time p99** | 99th percentile duration | < 30 min | > 45 min |
| **Success rate** | Workflows completing successfully | > 95% | < 90% |
| **Worker utilization** | Active / Total capacity | 40-70% | > 85% |

### 10.2 Business Metrics

| Metric | Description | Target | Measurement |
|--------|-------------|--------|-------------|
| **Self-service ratio** | Roles pushed by users vs engineering | > 90% | Weekly |
| **Time to dashboard** | Push to CHRO visible | < 15 min | Per workflow |
| **Engineering touches** | Manual interventions per client | < 2/month | Monthly |
| **Client onboarding time** | Contract to first assessment | < 5 days | Per client |

### 10.3 Operational Metrics

| Metric | Description | Target | Use |
|--------|-------------|--------|-----|
| **LLM tokens per role** | Token consumption per assessment | < X tokens | Cost allocation |
| **Retry rate** | Workflows requiring retry | < 10% | Quality indicator |
| **Error distribution** | Errors by type/step | - | Debugging |
| **Queue wait time** | Time from push to start | < 2 min | Capacity planning |

---

## 11. Risk Analysis

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Temporal connectivity issues | Medium | High | Health checks, circuit breaker |
| LLM rate limits | High | Medium | Queuing, exponential backoff |
| Long-running workflow timeouts | Medium | Medium | Heartbeats, checkpointing |
| Data inconsistency | Low | High | Idempotent activities, transactions |

### 11.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Volume overwhelms system | Medium | High | Rate limiting, backpressure |
| Bad inputs produce bad outputs | High | Medium | Validation layer, confidence scoring |
| Support burden increases | Medium | Medium | Clear errors, documentation |
| Cost overruns | Medium | Medium | Metering, alerts, quotas |

### 11.3 Migration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Script behavior changes during migration | Medium | High | Parallel running, output comparison |
| Missing edge cases in activities | Medium | Medium | Comprehensive test coverage |
| Integration failures | Low | High | Integration tests, staging validation |

---

## 12. Decision Log

### 12.1 Key Decisions Made

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Orchestration engine | Temporal | Already self-hosted, proven, durable | Celery, custom state machine |
| Status communication | Polling (pull) | Simpler, stateless, scales | WebSocket (push) |
| Workflow granularity | Coarse-grained initially | Simplicity, user clarity | Fine-grained from start |
| Error handling | Retry with exponential backoff | Resilience for LLM flakiness | Fail fast, manual retry |
| Tenant isolation | Workflow metadata | Simpler than namespaces | Namespace per tenant |

### 12.2 Decisions Deferred

| Decision | Options | Deferred Until | Rationale |
|----------|---------|----------------|-----------|
| Priority queues | Per-tier, per-company | Phase 4 | Need usage patterns first |
| Cost allocation model | Per-role, per-token, per-company | Phase 4 | Need cost data first |
| Custom workflow definition | UI builder vs config file | Future | Not MVP |
| External API triggers | REST, webhooks, Workato | Future | Not MVP |

---

## 13. Open Questions

### 13.1 Requires Product Decision

| Question | Options | Impact |
|----------|---------|--------|
| Where is entry point? | Taxonomy Builder vs CHRO Dashboard | UX flow |
| What batch limits? | 10, 50, 100, unlimited per push | Capacity, UX |
| What status granularity? | Per-workflow vs per-step vs per-activity | UI complexity |
| Re-run scope? | Full workflow only vs selective steps | Engineering effort |

### 13.2 Requires Technical Investigation

| Question | Investigation Needed |
|----------|---------------------|
| Process Map linking | How does it work? Is it blocking? |
| Draup role mapping automation | Can we auto-map or is manual required? |
| Existing script dependencies | Full inventory of external calls |
| Current test coverage | What tests exist for scripts? |

---

## 14. Success Criteria

### 14.1 Phase 1 (MVP) Success

- [ ] CSM can push a single role without engineering involvement
- [ ] Status visible within 5 seconds of action
- [ ] Role appears in CHRO Dashboard within 15 minutes
- [ ] Error messages actionable (user knows what to do)
- [ ] 95% success rate for valid inputs

### 14.2 Full Implementation Success

- [ ] Batch processing of 100+ roles at once
- [ ] < 2 engineering touches per client per month
- [ ] Self-service ratio > 90%
- [ ] Client onboarding < 5 days from contract
- [ ] System handles 1000 concurrent workflows

---

## Appendix A: Script Migration Inventory

| Script | Activity Name | Priority | Dependencies | Estimated Effort |
|--------|---------------|----------|--------------|------------------|
| create_company_role.py | create_role | P0 | Neo4j | 2 days |
| link_documents.py | link_documents | P0 | Neo4j, S3 | 2 days |
| run_ai_assessment.py | run_ai_assessment | P0 | Neo4j, LLM | 3 days |
| step_executor.py | execute_top_tasks | P1 | Neo4j, LLM | 3 days |
| run_standardisation.py | standardize_tasks | P1 | Neo4j | 2 days |
| skills_miner.py | mine_skills | P1 | Neo4j, LLM | 3 days |
| skills_architecture.py | build_skills_arch | P1 | Neo4j | 2 days |
| task_feasibility.py | assess_feasibility | P2 | Neo4j, LLM | 2 days |
| skills_catalog.py | populate_catalog | P2 | Neo4j | 2 days |
| reskilling_batch.py | generate_reskilling | P2 | Neo4j | 2 days |

---

## Appendix B: Temporal Configuration Reference

**Worker Configuration:**
```
Task Queue: etter-workflows
Namespace: etter-{environment}
Max Concurrent Activities: 50
Activity Task Timeout: 30 minutes
Workflow Execution Timeout: 2 hours
Heartbeat Timeout: 60 seconds
Retry Policy:
  Initial Interval: 1 second
  Backoff Coefficient: 2.0
  Maximum Interval: 5 minutes
  Maximum Attempts: 3
```

**Connectivity:**
```
Development SSH Tunnel:
  ssh -N -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
      ShreyashKumar-Draup@3.128.8.200

Local Development:
  temporal server start-dev

Production:
  Direct gRPC connection to temporal-server.internal:7233
```

---

*Document End*
