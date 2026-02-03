# Etter Self-Service Pipeline: Systems Exploration

**Document Type:** Exploratory Analysis  
**Version:** 0.1 (Draft)  
**Date:** January 2026  
**Author:** Architecture Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Current State Analysis](#3-current-state-analysis)
4. [First Principles Decomposition](#4-first-principles-decomposition)
5. [System Model](#5-system-model)
6. [Second-Order Thinking](#6-second-order-thinking)
7. [Thought Experiments](#7-thought-experiments)
8. [Solution Paths](#8-solution-paths)
9. [Tradeoffs Analysis](#9-tradeoffs-analysis)
10. [Metrics Framework](#10-metrics-framework)
11. [Next Steps](#11-next-steps)

---

## 1. Executive Summary

### The Core Problem

Etter requires manual engineering intervention for client onboarding and role setup. This creates a bottleneck that prevents scalability.

### The Desired State

Admin users and CSM team can handle end-to-end setup independently: data ingestion → taxonomy configuration → CHRO dashboard activation → workflow execution.

### The Mental Model

Think of Etter as a factory:
- **Raw Materials** = Documents (JDs, process maps)
- **Assembly Instructions** = Taxonomy (role definitions)
- **Production Line** = Automated workflows
- **Finished Product** = Role assessments in CHRO Dashboard

Currently, an engineer must manually start each production run. Self-service means the factory foreman (Admin/CSM) can press the start button themselves.

---

## 2. Problem Statement

### Current Pain Point

```
┌─────────────────────────────────────────────────────────────────┐
│ FOR EVERY NEW ROLE IN ETTER:                                    │
│                                                                 │
│   1. Engineering creates CompanyRole node (manual)              │
│   2. Engineering links Job Description (manual)                 │
│   3. Engineering links Process Maps (manual - often missing)    │
│   4. Engineering triggers AI Assessment (manual script)         │
│   5. Engineering runs Top Tasks workflow (manual script)        │
│   6. Engineering runs Skills Architecture (manual script)       │
│   7. Engineering runs Task Feasibility (manual script)          │
│   8. Engineering runs Skills Catalog (manual script)            │
│                                                                 │
│   → Only then does role appear in CHRO Dashboard                │
└─────────────────────────────────────────────────────────────────┘
```

### Concrete Example: Liberty Mutual

- Client has **2,500 roles** in their organization
- Etter currently has capacity for **150-200 roles**
- Each role requires the manual steps above
- Scaling to 2,500 roles is not feasible with current approach

### Symptoms of the Problem

| Symptom | Impact |
|---------|--------|
| Engineering bottleneck | Delayed client onboarding |
| Manual script execution | Error-prone, inconsistent |
| No status visibility | Clients can't see progress |
| Workflow coupling | Can't run partial updates |
| No self-service | CSM team blocked on engineering |

---

## 3. Current State Analysis

### 3.1 Data Architecture

```
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│    REPOSITORY      │     │     TAXONOMY       │     │   CHRO DASHBOARD   │
│    (Documents)     │────▶│     (Roles)        │────▶│   (Outputs)        │
├────────────────────┤     ├────────────────────┤     ├────────────────────┤
│ • Job Descriptions │     │ • Company Roles    │     │ • AI Assessment    │
│ • Process Maps     │     │ • Draup Mapping    │     │ • Skills Analysis  │
│ • SOPs             │     │ • Job Families     │     │ • Workflows        │
│ • Company Docs     │     │ • Org Hierarchy    │     │ • Reskilling       │
└────────────────────┘     └────────────────────┘     └────────────────────┘
         │                          │                          │
         │          ┌───────────────┴───────────────┐          │
         │          │    CURRENT GAP: Manual        │          │
         └─────────▶│    linking and execution      │◀─────────┘
                    │    by Engineering Team        │
                    └───────────────────────────────┘
```

### 3.2 Current Workflow Components

**Critical Reality: No Orchestration Layer Exists**

All workflows are currently local Python scripts run manually by engineering. There is no Temporal, no queue, no state management.

| Component | Current State | Location | Trigger |
|-----------|---------------|----------|---------|
| CompanyRole Creation | Manual script | Local | Engineer runs script |
| JD Linking | Manual script | Local | Engineer runs script |
| Process Map Linking | Not implemented | - | Missing |
| AI Assessment | **Manual script** | **Local** | **Engineer runs script** |
| Top Tasks | Manual script | Local | Engineer runs script |
| Skills Architecture | Manual script | Local | Engineer runs script |
| Task Feasibility | Manual script | Local | Engineer runs script |
| Skills Catalog | Manual script | Local | Engineer runs script |
| Role Catalog | Manual script | Local | Engineer runs script |

```
CURRENT REALITY:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Engineer's Local Machine                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  $ python create_company_role.py --company X --role Y   │   │
│   │  $ python link_documents.py --role Y --jd path/to/jd    │   │
│   │  $ python run_ai_assessment.py --role Y                 │   │
│   │  $ python step_executor.py --role Y                     │   │
│   │  $ python skills_architecture.py --role Y               │   │
│   │  ... and so on for each workflow                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   → No queue                                                    │
│   → No state tracking                                           │
│   → No error recovery                                           │
│   → No parallelization                                          │
│   → No status visibility                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ETTER SYSTEM BOUNDARY                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     CURRENT INFRASTRUCTURE                           │    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │   Neo4j      │  │   Redis      │  │  PostgreSQL  │               │    │
│  │  │  (Graph DB)  │  │  (Cache)     │  │  (Relational)│               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐    ┌─────────────────────────┐  │    │
│  │  │   FastAPI    │  │   React UI   │    │   LOCAL SCRIPTS         │  │    │
│  │  │  (Backend)   │  │  (Frontend)  │    │   (No orchestration)    │  │    │
│  │  └──────────────┘  └──────────────┘    │   ← THIS IS THE GAP     │  │    │
│  │                                         └─────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     TARGET STATE (TO BUILD)                          │    │
│  │  ┌──────────────┐                                                   │    │
│  │  │  Temporal    │  ← DOES NOT EXIST YET                             │    │
│  │  │  (Workflow)  │  ← Must be implemented for self-service           │    │
│  │  └──────────────┘                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      EXTERNAL INTERFACES                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │   Workato    │  │   Workday    │  │ SuccessFactors│              │    │
│  │  │   (iPaaS)    │  │   (HRIS)     │  │   (HRIS)     │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

THE FUNDAMENTAL GAP:
  → No orchestration layer between UI and scripts
  → No state management for workflow execution  
  → No way for users to trigger anything
  → All execution requires engineer with local environment
  → Document Upload (Repository boundary)
  → Role Selection (Taxonomy boundary)  
  → Workflow Trigger (Execution boundary)
  → Status Query (Dashboard boundary)
```

---

## 4. First Principles Decomposition

### 4.1 What is the Irreducible Core?

**Question:** What must happen for a role to appear in CHRO Dashboard?

**Answer:** The simplest path:

```
IRREDUCIBLE MINIMUM:
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Role   │────▶│Document │────▶│   AI    │────▶│Dashboard│
│ Exists  │     │ Linked  │     │ Assess  │     │ Visible │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

**Everything else is enhancement:**
- Skills Architecture → enhances insights
- Task Feasibility → enhances automation scoring
- Skills Catalog → enables reskilling
- Workflow Builder → enables process optimization

### 4.2 Fundamental Questions

| Question | First Principle Answer |
|----------|----------------------|
| **Why does Engineering need to be involved?** | Workflows are scripts, not services. No UI trigger mechanism. |
| **What data is truly required?** | Role name + at least one document (JD or process map) |
| **What is the minimum viable assessment?** | AI Assessment produces the core metrics |
| **Why can't users trigger workflows?** | No state machine. No API. No authorization layer. |
| **What creates the CompanyRole node?** | Currently: manual script. Should be: automatic on role selection. |

### 4.3 Breaking Down the "Push to Etter" Action

If a user selects a role and clicks "Push to Etter", what must happen?

```
USER ACTION: "Push Role X to Etter"

ATOMIC OPERATIONS (cannot be broken down further):
1. CREATE CompanyRole node in Neo4j
2. CREATE relationship: CompanyRole → Document(s)
3. CREATE relationship: CompanyRole → DraupRole (mapping)
4. TRIGGER AI Assessment workflow
5. WAIT for AI Assessment completion
6. TRIGGER dependent workflows (if AI Assessment succeeds)
7. UPDATE status at each step

EACH OPERATION NEEDS:
├── Input validation
├── Idempotency guarantee  
├── Error handling
├── Rollback capability
└── Status reporting
```

### 4.4 The Control Plane vs Data Plane Separation

```
CONTROL PLANE (Who can do what)          DATA PLANE (What happens)
┌─────────────────────────────┐          ┌─────────────────────────────┐
│                             │          │                             │
│  • User Roles (Admin, CSM)  │          │  • Role Creation            │
│  • Permissions              │          │  • Document Linking         │
│  • Company Scoping          │          │  • AI Assessment            │
│  • Rate Limiting            │          │  • Skills Mining            │
│  • Audit Logging            │          │  • Workflow Execution       │
│                             │          │                             │
└─────────────────────────────┘          └─────────────────────────────┘
              │                                       │
              └───────────────────────────────────────┘
                    SELF-SERVICE = Connecting these
```

---

## 5. System Model

### 5.1 State Machine for Role Lifecycle

```
                    ┌───────────────────────────────────────────────────────┐
                    │              ROLE LIFECYCLE STATE MACHINE              │
                    └───────────────────────────────────────────────────────┘

     ┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐
     │ DRAFT   │────────▶│ QUEUED  │────────▶│PROCESSING────────▶│ READY   │
     │         │         │         │         │         │         │         │
     │ • In    │         │ • In    │         │ • AI    │         │ • In    │
     │   Taxonomy│       │   Queue │         │   Assess │        │   CHRO  │
     │ • Not   │         │ • Await │         │   Running│        │   Dash  │
     │   in    │         │   Exec  │         │         │         │         │
     │   Etter │         │         │         │         │         │         │
     └─────────┘         └─────────┘         └─────────┘         └─────────┘
          │                   │                   │                   │
          │                   │                   │                   │
          ▼                   ▼                   ▼                   ▼
     ┌─────────────────────────────────────────────────────────────────────┐
     │                         ERROR STATES                                 │
     │  • VALIDATION_FAILED: Missing required documents                     │
     │  • ASSESSMENT_FAILED: AI Assessment error                            │
     │  • WORKFLOW_FAILED: Downstream workflow error                        │
     │  • STALE: Inputs changed, needs re-assessment                        │
     └─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Component Interaction Model (TARGET ARCHITECTURE)

**Note:** This is the desired state. Currently, the Orchestration and Execution layers do not exist - all workflows are local scripts.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SELF-SERVICE PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER INTERFACE LAYER                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Taxonomy   │  │ Repository  │  │   Status    │  │    CHRO     │        │
│  │   Builder   │  │   Upload    │  │  Dashboard  │  │  Dashboard  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│  ───────┼────────────────┼────────────────┼────────────────┼───────────    │
│         │                │                │                │               │
│  API LAYER              │                │                │               │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │  /roles     │  │ /documents  │  │  /status    │  │ /assessments│        │
│  │  CRUD       │  │  Upload     │  │  Query      │  │  Results    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│  ───────┼────────────────┼────────────────┼────────────────┼───────────    │
│         │                │                │                │               │
│  ORCHESTRATION LAYER    │                │                │               │
│  ┌──────▼───────────────▼────────────────▼────────────────▼──────┐         │
│  │                      WORKFLOW CONTROLLER                       │         │
│  │  • State Management   • Dependency Resolution                 │         │
│  │  • Error Handling     • Retry Logic                           │         │
│  │  • Progress Tracking  • Notification                          │         │
│  └───────────────────────────────┬───────────────────────────────┘         │
│                                  │                                          │
│  ────────────────────────────────┼──────────────────────────────────────    │
│                                  │                                          │
│  EXECUTION LAYER (Temporal)     │                                          │
│  ┌───────────────────────────────▼───────────────────────────────┐         │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │         │
│  │ │  Role   │▶│   AI    │▶│  Skills │▶│  Task   │▶│ Skills  │   │         │
│  │ │ Setup   │ │ Assess  │ │  Arch   │ │Feasibil │ │ Catalog │   │         │
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Self-Similar Architecture Pattern

The same pattern applies at every scale:

```
ATOMIC UNIT (Single Task)           MODULE (Workflow)              SYSTEM (Pipeline)
┌──────────────────────┐           ┌──────────────────────┐       ┌──────────────────────┐
│                      │           │                      │       │                      │
│  Input → Process →   │           │  Tasks →  Steps →    │       │  Modules → Stages → │
│        → Output      │           │        → Workflow    │       │          → Pipeline  │
│        → Status      │           │        → Status      │       │          → Status    │
│                      │           │                      │       │                      │
│  Error → Retry →     │           │  Error → Retry →     │       │  Error → Retry →     │
│        → Report      │           │        → Report      │       │        → Report      │
│                      │           │                      │       │                      │
└──────────────────────┘           └──────────────────────┘       └──────────────────────┘

INTERFACE CONTRACT (same at every level):
{
  "id": "unique identifier",
  "inputs": { ... },
  "status": "pending | running | success | failed",
  "outputs": { ... },
  "error": { "code": "...", "message": "...", "retry_at": "..." }
}
```

---

## 6. Second-Order Thinking

### 6.1 Consequences of Self-Service

**First-Order Effect:** Users can push roles to Etter without engineering.

**Second-Order Effects:**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        SECOND-ORDER CONSEQUENCES                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  POSITIVE                              │  NEGATIVE                         │
│  ─────────                             │  ─────────                        │
│                                        │                                   │
│  ✓ Faster onboarding                   │  ✗ Compute cost spikes            │
│    → More clients served               │    → Need rate limiting           │
│    → Higher revenue potential          │    → Need cost allocation         │
│                                        │                                   │
│  ✓ CSM empowerment                     │  ✗ Quality control challenges     │
│    → Deeper client relationships       │    → Bad inputs → bad outputs     │
│    → Engineering focuses on product    │    → Need validation layer        │
│                                        │                                   │
│  ✓ Transparent status                  │  ✗ Support burden shift           │
│    → Reduced "where is it?" queries    │    → Users need training          │
│    → Client trust increases            │    → Documentation needed         │
│                                        │                                   │
│  ✓ Incremental role addition           │  ✗ Dependency complexity visible  │
│    → Start with 50, scale to 2500      │    → Users see workflow failures  │
│    → Phased rollout possible           │    → Need clear error messaging   │
│                                        │                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Third-Order Effects

If self-service succeeds:
- **Market Position:** Etter becomes truly enterprise-scalable
- **Competitive Moat:** Speed-to-value differentiator
- **Product Evolution:** Foundation for workflow builder self-service
- **Data Network:** More roles → better Draup mapping → better assessments

If self-service has issues:
- **Trust Erosion:** Failed runs damage client confidence
- **Support Overload:** Troubleshooting moves from engineering to CSM
- **Technical Debt:** Rushed features create maintenance burden

### 6.3 Dependency Chain Analysis

```
What breaks if each component fails?

┌─────────────────────────────────────────────────────────────────────────────┐
│ COMPONENT          │ IF FAILS                         │ BLAST RADIUS        │
├────────────────────┼──────────────────────────────────┼─────────────────────┤
│ Role Creation      │ Nothing downstream works         │ ALL subsequent ops  │
│ Document Linking   │ AI Assessment has no context     │ Poor quality output │
│ AI Assessment      │ No scores, no dashboard entry    │ Role invisible      │
│ Skills Architecture│ No skills analysis               │ Degraded insights   │
│ Task Feasibility   │ Missing automation recommendations│ Reduced value      │
│ Skills Catalog     │ No reskilling capabilities       │ Feature gap         │
│ Status Tracking    │ Users blind to progress          │ Trust/UX issue      │
└─────────────────────────────────────────────────────────────────────────────┘

CRITICAL PATH: Role Creation → Document Linking → AI Assessment → Dashboard
ENHANCEMENT PATH: Skills Architecture → Task Feasibility → Skills Catalog
```

---

## 7. Thought Experiments

### 7.1 Thought Experiment: The Naive User

**Scenario:** A new CSM, unfamiliar with Etter, is given access to self-service.

**What they try:**
1. Upload 500 JDs at once (bulk import)
2. Select 200 roles and push all simultaneously
3. Check status every 30 seconds
4. See a failure and push again (duplicate)
5. Call support: "It's not working"

**System requirements this reveals:**
- Bulk operation limits with clear feedback
- Queue management with position visibility
- Idempotency (prevent duplicate processing)
- Clear error messages with suggested actions
- Graceful degradation under load

### 7.2 Thought Experiment: The Power User

**Scenario:** An experienced admin wants fine-grained control.

**What they need:**
1. Push only roles with complete documents
2. Re-run only Skills Architecture (not full AI Assessment)
3. Schedule runs for off-peak hours
4. Get notifications when complete
5. Export audit trail for compliance

**System requirements this reveals:**
- Document completeness validation
- Granular workflow triggering
- Scheduling capability
- Notification system
- Audit logging with export

### 7.3 Thought Experiment: The Stressed System

**Scenario:** Client pushes 1000 roles during peak hours.

**What happens:**
1. Queue backs up
2. LLM rate limits hit
3. Database connections exhausted
4. Workers fall behind
5. Timeouts cascade

**System requirements this reveals:**
- Backpressure mechanisms
- Rate limiting at multiple levels
- Circuit breakers
- Priority queuing (paying clients first?)
- Horizontal scaling triggers

### 7.4 Thought Experiment: The Bad Data

**Scenario:** Client uploads JD that is actually a meeting agenda.

**What should happen:**
1. Document type validation flags it
2. User warned but can proceed
3. AI Assessment notes low confidence
4. Assessment flagged for human review
5. User can replace document and re-run

**System requirements this reveals:**
- Document quality scoring
- Soft validation (warn) vs hard validation (block)
- Confidence metrics in output
- Document replacement flow
- Incremental re-processing

---

## 8. Solution Paths

### 8.0 Prerequisite: Temporal Infrastructure

**Before any self-service is possible, we need orchestration.**

```
FOUNDATIONAL WORK (Must happen first):
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. TEMPORAL SETUP                                                          │
│     ├── Deploy Temporal server (or use Temporal Cloud)                      │
│     ├── Configure workers                                                   │
│     ├── Set up namespaces for tenant isolation                              │
│     └── Monitoring/alerting integration                                     │
│                                                                             │
│  2. SCRIPT → WORKFLOW MIGRATION                                             │
│     ├── Convert each script to Temporal Activity                            │
│     ├── Define Workflow that orchestrates Activities                        │
│     ├── Add retry policies, timeouts                                        │
│     └── Test each workflow in isolation                                     │
│                                                                             │
│  3. API LAYER                                                               │
│     ├── FastAPI endpoints to start workflows                                │
│     ├── Status query endpoints                                              │
│     └── Authentication/authorization                                        │
│                                                                             │
│  EFFORT: ~3-4 weeks (parallel to Path work)                                 │
│  THIS IS NON-NEGOTIABLE FOR SELF-SERVICE                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Path A: Minimal Viable Self-Service

**Philosophy:** Do the smallest thing that provides value.

```
PREREQUISITES:
├── Temporal deployed ✓
├── AI Assessment migrated to Temporal ✓
└── Basic API layer ✓

SCOPE:
├── Role Selection UI in Taxonomy Builder
├── "Push to Etter" button
├── Basic status display (waiting/running/done)
└── Link to CHRO Dashboard when ready

NOT IN SCOPE:
├── Other workflows (Skills Architecture, etc.)
├── Document management
├── Re-run capabilities
└── Scheduling

EFFORT: ~4-5 weeks (including Temporal setup)
VALUE: Unblocks basic onboarding for AI Assessment only
RISK: Limited value - only AI Assessment, users need more
```

### 8.2 Path B: Full Orchestration Layer

**Philosophy:** Build it right the first time.

```
PREREQUISITES:
├── Temporal deployed ✓
├── ALL workflows migrated to Temporal ✓
└── Complete API layer ✓

SCOPE:
├── Complete state machine
├── All workflows in Temporal
├── Full status dashboard
├── Document management
├── Role ↔ Document linking UI
├── Selective re-runs
├── Scheduling
└── Audit logging

NOT IN SCOPE:
├── Multi-tenant priority queues
├── Custom workflow definition
└── API for external triggers

EFFORT: ~10-12 weeks
VALUE: Complete self-service
RISK: Scope creep, delayed delivery, big bang release
```

### 8.3 Path C: Progressive Enhancement (Recommended)

**Philosophy:** Start minimal, add capabilities based on usage.

```
PHASE 0 (Week 1-3): Infrastructure [BLOCKING]
├── Temporal server deployment
├── Worker configuration
├── AI Assessment → Temporal Activity migration
├── Role Setup → Temporal Activity migration
└── Basic orchestrating Workflow definition

PHASE 1 (Week 4-5): MVP Self-Service
├── FastAPI endpoints (start workflow, get status)
├── Role Selection UI in Taxonomy Builder
├── "Push to Etter" button
├── Status polling (waiting/running/done/error)
└── Link to CHRO Dashboard when ready

PHASE 2 (Week 6-7): Core Workflows
├── Migrate Top Tasks to Temporal
├── Migrate Skills Architecture to Temporal
├── Parent workflow orchestrating child workflows
├── Progress indicators per workflow step
└── Retry mechanism for failures

PHASE 3 (Week 8-9): Enhancement
├── Migrate remaining workflows (Task Feasibility, Skills Catalog)
├── Document linking UI
├── Selective re-runs
├── Batch operations
└── Process Map linking (if ready)

PHASE 4 (Week 10-11): Polish
├── Status dashboard UI improvements
├── Notifications (email/slack)
├── Audit logging
├── Rate limiting
└── Documentation & training

EFFORT: ~11 weeks total, USABLE at week 5
VALUE: Incremental value delivery, early feedback
RISK: Some refactoring between phases, but manageable
```

### 8.4 Recommendation

**Path C (Progressive Enhancement)** aligns with first principles:
- Infrastructure first (Temporal) - no shortcuts
- Delivers usable MVP at week 5 (AI Assessment self-service)
- Gathers real usage feedback before completing all workflows
- Allows course correction based on client needs
- Manages risk through iteration

**Critical Insight:** The Temporal migration is the real work. Once scripts become Activities and we have orchestrating Workflows, the UI/API layer is straightforward.

---

## 9. Tradeoffs Analysis

### 9.1 Build vs Buy

| Aspect | Build (Temporal) | Buy (Workato/External) |
|--------|------------------|------------------------|
| Control | Full | Limited |
| Customization | Complete | Constrained by platform |
| Cost | Development time | License + integration |
| Maintenance | Internal | Shared with vendor |
| Scaling | Manual | Often included |
| Lock-in | None | Vendor-specific |

**Decision:** Build on Temporal (already in stack, need full control)

### 9.2 Synchronous vs Asynchronous

| Aspect | Synchronous | Asynchronous |
|--------|-------------|--------------|
| User Experience | Wait for result | Submit and check later |
| Scalability | Poor (connections held) | Good (queue-based) |
| Timeout Risk | High | Low |
| Complexity | Lower | Higher |
| Status Tracking | Implicit | Explicit (required) |

**Decision:** Asynchronous with status tracking (scale requirement)

### 9.3 Fine-Grained vs Coarse-Grained Workflows

| Aspect | Fine-Grained | Coarse-Grained |
|--------|--------------|----------------|
| Flexibility | High (pick any combination) | Low (all-or-nothing) |
| Complexity | High (many permutations) | Low (fixed sequence) |
| Error Recovery | Partial re-run possible | Full re-run required |
| User Confusion | Higher | Lower |
| Development Cost | Higher | Lower |

**Decision:** Coarse-grained initially, with opt-in fine-grained later

### 9.4 Push-Based vs Pull-Based Status

| Aspect | Push (Websocket) | Pull (Polling) |
|--------|------------------|----------------|
| Real-time | Yes | Delayed |
| Server Load | Persistent connections | Intermittent requests |
| Complexity | Higher | Lower |
| Offline Handling | Need reconnect logic | Natural (just poll) |
| Scalability | Need socket infrastructure | Stateless |

**Decision:** Pull (polling) initially, push as enhancement

---

## 10. Metrics Framework

### 10.1 Leading Metrics (Predictive)

| Metric | Description | Target |
|--------|-------------|--------|
| **Queue Depth** | Roles waiting for processing | < 100 |
| **Document Completeness** | Roles with all required docs | > 80% |
| **Error Rate (Validation)** | Roles rejected at input | < 5% |
| **API Response Time** | Push action latency | < 500ms |

### 10.2 Lagging Metrics (Outcome)

| Metric | Description | Target |
|--------|-------------|--------|
| **Time to Dashboard** | Role push to CHRO visible | < 15 min |
| **Success Rate** | Roles completing full pipeline | > 95% |
| **Self-Service Ratio** | Roles pushed by users vs engineering | > 90% |
| **Re-run Rate** | Roles requiring re-processing | < 10% |

### 10.3 Operational Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Workflow Duration** | Full pipeline execution time | < 10 min |
| **LLM Token Consumption** | Cost per role assessment | < $X |
| **Worker Utilization** | Processing capacity usage | 60-80% |
| **Failed Workflow Recovery** | Time to resolve failures | < 1 hour |

### 10.4 Business Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Client Onboarding Time** | Days from contract to first dashboard | < 5 days |
| **Roles Per Client** | Average roles in Etter per client | > 100 |
| **CSM Productivity** | Clients per CSM | +20% |
| **Engineering Touch Points** | Manual interventions per client | < 2 |

---

## 11. Next Steps

### 11.1 Immediate Actions (This Week)

1. **Temporal Infrastructure Decision**
   - Evaluate: Temporal Cloud vs Self-hosted
   - Estimate infrastructure costs
   - Define deployment approach (EKS, etc.)

2. **Script Inventory & Analysis**
   - Catalog ALL scripts that need migration
   - Document inputs/outputs for each script
   - Map data dependencies between scripts
   - Identify scripts that can run in parallel vs sequential

3. **Migration Complexity Assessment**
   - For each script, estimate effort to convert to Temporal Activity
   - Identify shared utilities that become reusable Activities
   - Flag scripts with external dependencies (LLM calls, DB writes)

### 11.2 Technical Decisions Needed

| Decision | Options | Impact |
|----------|---------|--------|
| **Temporal deployment** | Cloud vs Self-hosted | Cost, ops complexity |
| **Worker architecture** | Single vs Multiple worker types | Scale, isolation |
| **Activity granularity** | Fine (1 script = 1 activity) vs Coarse (grouped) | Flexibility vs simplicity |
| **Error handling** | Auto-retry with backoff vs Manual intervention | User experience |
| **Tenant isolation** | Namespace per tenant vs Workflow metadata | Security, scale |

### 11.3 Design Decisions Needed

| Decision | Options | Stakeholder |
|----------|---------|-------------|
| Entry point for self-service | Taxonomy Builder vs CHRO Dashboard | Product |
| Granularity of status updates | High (per-step) vs Low (per-workflow) | UX |
| Permission model | Role-based vs Feature-based | Security |
| Batch limits | How many roles can be pushed at once? | Product, Engineering |

### 11.4 Open Questions

1. **Process Map Linking:** Currently not implemented. Is this a blocker for self-service?
2. **Draup Role Mapping:** Is manual mapping required before push, or can it be automated?
3. **Multi-company Support:** How should tenant isolation work for queuing?
4. **Workflow Dependencies:** Can Skills Architecture run if AI Assessment partially fails?
5. **Cost Allocation:** How do we track compute costs per client?
6. **Temporal Learning Curve:** Does the team have Temporal experience? Training needed?
7. **Migration Strategy:** Can we run scripts and Temporal in parallel during transition?

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **CompanyRole** | Neo4j node representing a client's specific role |
| **DraupRole** | Standardized role from Draup taxonomy |
| **AI Assessment** | Core Etter analysis producing automation/augmentation scores |
| **CHRO Dashboard** | Client-facing UI showing assessment results |
| **Repository** | Document storage (JDs, process maps) |
| **Taxonomy** | Role definitions and hierarchies |
| **Temporal** | Workflow orchestration engine (TARGET - does not exist yet) |
| **Activity** | Temporal term: A single unit of work (what scripts become) |
| **Workflow** | Temporal term: Orchestrator that sequences Activities |
| **Worker** | Temporal term: Process that executes Activities |

---

## Appendix B: Current Workflow Scripts (TO BE MIGRATED)

These scripts will become Temporal Activities:

| Script | Purpose | Dependencies | Output | Migration Priority |
|--------|---------|--------------|--------|-------------------|
| `create_company_role.py` | Create CompanyRole node | Company name, role name | Neo4j node | P0 (Critical) |
| `link_documents.py` | Connect JD to role | CompanyRole, document path | Relationship | P0 (Critical) |
| `run_ai_assessment.py` | Trigger AI Assessment | CompanyRole with JD | Assessment scores | P0 (Critical) |
| `step_executor.py` | Top Tasks workflow | CompanyRole | Task analysis | P1 (High) |
| `run_standardisation.py` | Standardize tasks | Task analysis | Standardized tasks | P1 (High) |
| `skills_miner.py` | Extract skills | CompanyRole | Skills list | P1 (High) |
| `skills_architecture.py` | Build skill framework | Skills list | Architecture | P1 (High) |
| `reskilling_batch.py` | Reskilling analysis | Skills architecture | Recommendations | P2 (Medium) |
| `task_feasibility.py` | Automation feasibility | Tasks | Feasibility scores | P2 (Medium) |
| `skills_catalog.py` | Catalog population | Skills | Catalog entries | P2 (Medium) |

**Migration Note:** P0 scripts are required for MVP self-service. P1 completes the core pipeline. P2 are enhancements.

---

## Appendix C: Temporal Workflow Design (Draft)

```python
# Conceptual structure - not production code

# Each script becomes an Activity
@activity.defn
async def create_company_role(company: str, role: str) -> str:
    """Create CompanyRole node, return role_id"""
    # Current script logic here
    pass

@activity.defn  
async def link_documents(role_id: str, documents: List[str]) -> bool:
    """Link documents to role"""
    pass

@activity.defn
async def run_ai_assessment(role_id: str) -> AssessmentResult:
    """Execute AI Assessment"""
    pass

# Workflow orchestrates Activities
@workflow.defn
class RoleOnboardingWorkflow:
    @workflow.run
    async def run(self, input: RoleOnboardingInput) -> RoleOnboardingResult:
        # Step 1: Create role
        role_id = await workflow.execute_activity(
            create_company_role,
            args=[input.company, input.role],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 2: Link documents
        await workflow.execute_activity(
            link_documents,
            args=[role_id, input.documents],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 3: AI Assessment
        assessment = await workflow.execute_activity(
            run_ai_assessment,
            args=[role_id],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        
        # Continue with other workflows...
        return RoleOnboardingResult(role_id=role_id, assessment=assessment)
```

---

*Document End*
