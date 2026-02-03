# Workflows Package

## First Principle: What Is a Workflow?

**A workflow is a state machine that orchestrates a sequence of steps to achieve a goal.**

Think of it like a recipe:
- Input: Ingredients (company, role, documents)
- Steps: Cooking instructions (create role, run assessment)
- Output: Finished dish (role ready for dashboard)

```
┌─────────┐    ┌────────────┐    ┌───────────────┐    ┌─────────┐
│  DRAFT  │───▶│   QUEUED   │───▶│  PROCESSING   │───▶│  READY  │
└─────────┘    └────────────┘    └───────────────┘    └─────────┘
                                        │
                                        ▼
                                   ┌─────────┐
                                   │ FAILED  │
                                   └─────────┘
```

## Mental Model: The Assembly Line

Imagine a car factory assembly line:

1. **Workflow = The Assembly Line** - Defines the sequence of stations
2. **Steps = Stations** - Each station does one specific job
3. **Activities = Workers** - Actually perform the work at each station
4. **State = Position on Line** - Where is the car right now?

The workflow doesn't build the car—it coordinates who builds what and when.

## System Thinking: Where Workflows Fit

```
┌─────────────────────────────────────────────────────────────────┐
│                        ETTER SYSTEM                              │
│                                                                  │
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │   API    │────▶│   WORKFLOW   │────▶│    ACTIVITIES     │   │
│  │ (Entry)  │     │ (Orchestrator)│     │ (Actual Work)     │   │
│  └──────────┘     └──────────────┘     └───────────────────┘   │
│                          │                      │               │
│                          ▼                      ▼               │
│                   ┌────────────┐         ┌───────────┐         │
│                   │   STATUS   │         │  CLIENTS  │         │
│                   │  (Redis)   │         │ (Neo4j)   │         │
│                   └────────────┘         └───────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Workflows are the "brain" that coordinates everything but don't do the actual work themselves.

## Files in This Package

| File | Purpose | Analogy |
|------|---------|---------|
| `base.py` | Abstract workflow foundation | Blueprint for all assembly lines |
| `role_onboarding.py` | Specific workflow for role setup | The actual car assembly line |

## The Role Onboarding Workflow

This is our MVP workflow. It has exactly 2 steps:

```
Step 1: role_setup          Step 2: ai_assessment
┌─────────────────┐         ┌─────────────────┐
│ Create Company  │         │ Run AI Impact   │
│ Role in Neo4j   │────────▶│ Assessment      │
│ + Link JD       │         │                 │
└─────────────────┘         └─────────────────┘
     ~5 min max                  ~30 min max
```

## Thought Experiment: Why Separate Workflows from Activities?

**Question**: Why not just put all the logic in one big function?

**Answer**: Separation of concerns enables:

1. **Retry at the right level** - If AI assessment fails, don't redo role creation
2. **Visibility** - Know exactly which step failed
3. **Reusability** - Same activity can be used in different workflows
4. **Testing** - Test each piece independently

**Analogy**: A general doesn't fight battles—they coordinate troops. The workflow is the general.

## Temporal Integration

When running with Temporal (production):
- Workflows are durable (survive crashes)
- State is persisted automatically
- Steps can be retried independently

When running standalone (development):
- Workflows run in-memory
- State is lost on crash
- Simpler for testing

```python
# The decorator handles both modes
@_apply_temporal_decorators
class RoleOnboardingWorkflow(BaseWorkflow):
    ...
```

## Key Concepts for Architects

### 1. Determinism Requirement (Temporal)

Workflows must be deterministic—same input always produces same decisions.

**Allowed**: `workflow.now()` (Temporal provides consistent time)
**Not Allowed**: `datetime.utcnow()` (different each replay)

### 2. No I/O in Workflows

Workflows should never:
- Make HTTP calls directly
- Query databases directly
- Read files directly

Instead, delegate to Activities (which CAN do I/O).

### 3. State Machine Pattern

```python
class WorkflowState(str, Enum):
    DRAFT = "draft"           # Not started
    QUEUED = "queued"         # Waiting to run
    PROCESSING = "processing" # Currently running
    READY = "ready"           # Completed successfully
    FAILED = "failed"         # Completed with error
```

## Quick Reference

```python
# Create and run a workflow
from etter_workflows.workflows.role_onboarding import execute_role_onboarding

result = await execute_role_onboarding(
    company_id="Acme Corp",
    role_name="Software Engineer",
    use_mock_assessment=True,  # Safe for testing
)

if result.success:
    print(f"Role ID: {result.role_id}")
    print(f"AI Score: {result.outputs.final_score}%")
```

## Summary

| Concept | Workflow Responsibility |
|---------|------------------------|
| **Orchestration** | Yes - coordinates steps |
| **State Management** | Yes - tracks progress |
| **Business Logic** | No - delegates to activities |
| **I/O Operations** | No - delegates to activities |
| **Error Handling** | Yes - decides retry/fail |
