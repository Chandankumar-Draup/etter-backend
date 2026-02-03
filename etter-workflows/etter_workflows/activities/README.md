# Activities Package

## First Principle: What Is an Activity?

**An activity is a single unit of work that performs I/O or computation.**

If workflows are generals, activities are soldiers—they do the actual fighting.

```
┌─────────────────────────────────────────────────────────────┐
│                      ACTIVITY                                │
│                                                              │
│   INPUT ────▶ [ Do Something ] ────▶ OUTPUT                 │
│              (call API, query DB)                            │
│                                                              │
│   • Can fail and be retried                                  │
│   • Has timeout                                              │
│   • Isolated unit of work                                    │
└─────────────────────────────────────────────────────────────┘
```

## Mental Model: The Restaurant Kitchen

Think of a restaurant:

| Restaurant | Etter System |
|------------|--------------|
| Order (ticket) | Workflow step |
| Chef | Activity |
| Recipe execution | Activity logic |
| Plated dish | Activity result |

The chef (activity) doesn't decide what to cook—they execute what the ticket (workflow) tells them.

## System Thinking: Activities in the Architecture

```
                    WORKFLOW
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │ Activity│   │ Activity│   │ Activity│
    │  (A)    │   │  (B)    │   │  (C)    │
    └────┬────┘   └────┬────┘   └────┬────┘
         │             │             │
         ▼             ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │  Neo4j  │   │   LLM   │   │   API   │
    │ Database│   │ Service │   │ Service │
    └─────────┘   └─────────┘   └─────────┘
```

**Key Insight**: Activities are the ONLY place where I/O happens. This isolation makes the system:
- Testable (mock activities)
- Retryable (retry just the failed activity)
- Observable (measure each activity)

## Files in This Package

| File | Activity | What It Does |
|------|----------|--------------|
| `base.py` | (foundation) | Retry logic, metrics, error handling |
| `role_setup.py` | `create_company_role` | Creates CompanyRole node in Neo4j |
| | `link_job_description` | Links JD document to role |
| `ai_assessment.py` | `run_ai_assessment` | Executes AI impact assessment |

## The Three Activities (MVP)

### 1. Create Company Role
```
INPUT                          OUTPUT
─────                          ──────
• company_name     ────▶       • company_role_id
• role_name                    • status
• draup_role
                   [Neo4j]
```

### 2. Link Job Description
```
INPUT                          OUTPUT
─────                          ──────
• company_role_id  ────▶       • jd_linked: true/false
• jd_content                   • jd_length
• jd_title
                   [Neo4j]
```

### 3. Run AI Assessment
```
INPUT                          OUTPUT
─────                          ──────
• company_name     ────▶       • ai_automation_score
• role_name                    • task_analysis
• company_role_id              • impact_analysis

                   [AI Assessment API]
```

## Thought Experiment: Why Activities Need Retry Logic?

**Scenario**: You're calling an external API that has 99.9% uptime.

**Problem**: 0.1% failure rate × 1000 calls/day = ~1 failure per day

**Solution**: Retry with exponential backoff

```
Attempt 1: Call API ──▶ FAIL (network timeout)
           Wait 2 seconds
Attempt 2: Call API ──▶ FAIL (service busy)
           Wait 4 seconds
Attempt 3: Call API ──▶ SUCCESS ✓
```

This is built into every activity via `@activity_with_retry`:

```python
@activity_with_retry(
    retry_config=get_db_retry_policy(),  # 3 attempts, exponential backoff
    timeout_seconds=300,                   # 5 minute max
)
async def create_company_role(...):
    ...
```

## Activity Contract

Every activity follows the same contract:

```python
# INPUT: Always receives these
async def some_activity(
    # Required parameters for the work
    company_name: str,
    role_name: str,
    # Optional execution context
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:  # OUTPUT: Always returns a dict

    # Do the work
    result = do_something()

    # Return structured result
    return {
        "success_field": result,
        "duration_ms": metrics.duration_ms,
    }
```

## Error Handling Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR CATEGORIES                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RETRYABLE                    NON-RETRYABLE                 │
│  ──────────                   ─────────────                 │
│  • Network timeout            • Invalid input               │
│  • Service temporarily down   • Permission denied           │
│  • Rate limited               • Resource not found          │
│  • Connection refused         • Business logic error        │
│                                                              │
│  ───▶ Retry automatically     ───▶ Fail immediately        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Mock vs Real Activities

For testing, we have mock versions:

```python
# Real activity (calls actual AI API)
class AIAssessmentActivity:
    async def execute(self, inputs, context):
        result = call_real_ai_api(...)  # Takes 10+ minutes
        return result

# Mock activity (returns fake data instantly)
class MockAIAssessmentActivity:
    async def execute(self, inputs, context):
        return {
            "ai_automation_score": random.uniform(30, 80),  # Random score
            "is_mock": True,
        }
```

**When to use mock**: Development, testing, demos
**When to use real**: Production, actual assessments

## Key Concepts for Architects

### 1. Idempotency

Activities should be idempotent when possible—running twice produces same result.

```python
# Good: Uses MERGE (create if not exists)
MERGE (cr:CompanyRole {id: $id})
ON CREATE SET cr.name = $name

# Bad: Always creates new
CREATE (cr:CompanyRole {name: $name})
```

### 2. Timeout Strategy

```
Activity Type          Suggested Timeout    Why
─────────────          ─────────────────    ───
Database query         30 seconds           Fast, local network
LLM formatting         60 seconds           API call, processing
AI Assessment          30 minutes           Complex analysis
```

### 3. Resource Cleanup

Activities should clean up on failure:

```python
try:
    partial_result = create_something()
    final_result = complete_something(partial_result)
    return final_result
except Exception:
    cleanup(partial_result)  # Don't leave partial state
    raise
```

## Quick Reference

```python
# Using activity directly (standalone mode)
from etter_workflows.activities.role_setup import RoleSetupActivity

activity = RoleSetupActivity()
result = await activity.execute(
    inputs={
        "company_id": "Acme Corp",
        "role_name": "Engineer",
    },
    context=ExecutionContext(company_id="Acme", user_id="demo"),
)
```

## Summary

| Aspect | Activity Responsibility |
|--------|------------------------|
| **I/O Operations** | Yes - this is where I/O lives |
| **Retry Logic** | Yes - built into decorator |
| **Business Logic** | Yes - specific to the task |
| **State Management** | No - activities are stateless |
| **Orchestration** | No - that's the workflow's job |
