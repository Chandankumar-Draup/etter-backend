# Models Package

## First Principle: What Are Models?

**Models are data contracts—they define the shape of information flowing through the system.**

Think of models as the "language" different parts of the system use to communicate.

```
┌─────────┐          ┌─────────┐          ┌─────────┐
│  API    │──INPUT──▶│ WORKFLOW│──OUTPUT─▶│  USER   │
└─────────┘  MODEL   └─────────┘  MODEL   └─────────┘
```

Without models, components would pass arbitrary data and hope for the best.
With models, contracts are enforced, documented, and validated.

## Mental Model: The Shipping Container

International shipping works because of standardized containers:

| Shipping | Etter System |
|----------|--------------|
| Container spec | Model definition |
| Container contents | Actual data |
| Port cranes | Code that processes data |
| Shipping manifest | Model validation |

**Key insight**: The crane doesn't care what's IN the container—it knows the container SHAPE is standard.

## System Thinking: Models as Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│                                                                 │
│     EXTERNAL WORLD          │          INTERNAL SYSTEM         │
│     ───────────────         │          ───────────────         │
│                             │                                   │
│    Raw JSON request    ────▶│ INPUT MODELS ────▶ Workflow      │
│                             │                                   │
│    Dashboard display   ◀────│ OUTPUT MODELS ◀─── Activities    │
│                             │                                   │
│    Status polling      ◀────│ STATUS MODELS ◀─── Redis         │
│                             │                                   │
└────────────────────────────────────────────────────────────────┘
```

Models serve as **boundaries**:
- Validate data at entry points
- Ensure consistency across components
- Document expectations explicitly

## Files in This Package

| File | Purpose | Contains |
|------|---------|----------|
| `inputs.py` | Data coming IN | RoleOnboardingInput, DocumentRef, ExecutionContext |
| `outputs.py` | Data going OUT | WorkflowResult, ActivityResult, AssessmentOutputs |
| `status.py` | Current STATE | RoleStatus, WorkflowState, ProgressInfo |

## The Three Model Categories

### 1. Input Models (`inputs.py`)

**Question they answer**: "What does the system need to start?"

```python
class RoleOnboardingInput(BaseModel):
    company_id: str          # Who is this for?
    role_name: str           # What role?
    documents: List[DocumentRef]  # What documents?
    options: WorkflowOptions # How to run?
```

**Thought experiment**: If you had to fax instructions to start a workflow, what would you include?

### 2. Output Models (`outputs.py`)

**Question they answer**: "What did the system produce?"

```python
class WorkflowResult(BaseModel):
    workflow_id: str         # Which run?
    success: bool            # Did it work?
    role_id: Optional[str]   # What was created?
    outputs: Optional[AssessmentOutputs]  # What's the score?
    error: Optional[ErrorInfo]  # What went wrong?
```

**Thought experiment**: If someone asks "what happened?", what would you tell them?

### 3. Status Models (`status.py`)

**Question they answer**: "What is happening right now?"

```python
class RoleStatus(BaseModel):
    workflow_id: str
    state: WorkflowState     # QUEUED, PROCESSING, READY, FAILED
    progress: ProgressInfo   # Which step? How far?
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
```

**Thought experiment**: If you're watching a progress bar, what info do you need?

## The State Machine

Status models implement a state machine:

```
                    trigger: "submit"
     ┌─────────┐ ─────────────────────▶ ┌──────────┐
     │  DRAFT  │                        │  QUEUED  │
     └─────────┘                        └────┬─────┘
                                             │
                              trigger: "start"
                                             ▼
                                       ┌──────────────┐
                        ┌──────────────│  PROCESSING  │──────────────┐
                        │              └──────────────┘              │
                        │                                            │
              trigger: "complete"                          trigger: "fail"
                        │                                            │
                        ▼                                            ▼
                  ┌───────────┐                               ┌──────────┐
                  │   READY   │                               │  FAILED  │
                  └───────────┘                               └──────────┘
```

## Pydantic: The Validation Engine

All models use Pydantic for automatic validation:

```python
from pydantic import BaseModel, Field, validator

class RoleOnboardingInput(BaseModel):
    company_id: str = Field(..., min_length=1)  # Required, non-empty
    role_name: str = Field(..., min_length=1)
    documents: List[DocumentRef] = Field(default_factory=list)

    @validator('company_id')
    def company_id_not_empty(cls, v):
        if not v.strip():
            raise ValueError('company_id cannot be empty')
        return v.strip()
```

**What Pydantic gives you**:
- Type checking at runtime
- Automatic JSON serialization
- Clear error messages
- Default values
- Custom validation

## Key Patterns

### 1. Optional Fields with Defaults

```python
class WorkflowOptions(BaseModel):
    force_rerun: bool = False        # Default: don't rerun
    notify_on_complete: bool = True  # Default: send notification
```

### 2. Nested Models

```python
class RoleOnboardingInput(BaseModel):
    documents: List[DocumentRef]     # List of another model
    options: WorkflowOptions         # Another model
    context: Optional[ExecutionContext]  # Optional model
```

### 3. Enums for Fixed Choices

```python
class WorkflowState(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
```

### 4. Factory Methods

```python
class WorkflowResult(BaseModel):
    @classmethod
    def create_success(cls, workflow_id, role_id, outputs, ...):
        return cls(
            workflow_id=workflow_id,
            success=True,
            role_id=role_id,
            outputs=outputs,
        )

    @classmethod
    def create_failure(cls, workflow_id, error, ...):
        return cls(
            workflow_id=workflow_id,
            success=False,
            error=error,
        )
```

## Thought Experiment: Why Not Just Use Dicts?

**With dicts**:
```python
result = {
    "workfow_id": "123",  # Typo - no error!
    "sucess": True,       # Typo - no error!
    "role_id": 456,       # Wrong type - no error!
}
```

**With models**:
```python
result = WorkflowResult(
    workfow_id="123",  # ERROR: Unknown field 'workfow_id'
    sucess=True,       # ERROR: Unknown field 'sucess'
    role_id=456,       # ERROR: role_id must be str, not int
)
```

**Models catch errors at creation time, not when something breaks later.**

## Quick Reference

```python
# Creating input
from etter_workflows.models.inputs import RoleOnboardingInput, DocumentRef, DocumentType

input = RoleOnboardingInput(
    company_id="Acme Corp",
    role_name="Software Engineer",
    documents=[
        DocumentRef(
            type=DocumentType.JOB_DESCRIPTION,
            name="SWE JD",
            content="...",
        )
    ],
)

# Checking output
from etter_workflows.models.outputs import WorkflowResult

if result.success:
    print(f"Score: {result.outputs.final_score}")
else:
    print(f"Error: {result.error.message}")

# Tracking status
from etter_workflows.models.status import WorkflowState

if status.state == WorkflowState.PROCESSING:
    print(f"Step: {status.progress.current_step}")
```

## Summary

| Model Type | Purpose | When Used |
|------------|---------|-----------|
| **Input** | Define what's needed | API receives request |
| **Output** | Define what's returned | Workflow completes |
| **Status** | Define current state | Polling for progress |

**Remember**: Models don't DO anything—they DESCRIBE things. They're the blueprints, not the building.
