# Clients Package

## First Principle: What Is a Client?

**A client is an adapter that talks to external systems using their language.**

Your code speaks Python. Neo4j speaks Cypher. Redis speaks its protocol. LLMs speak JSON.
Clients are the translators.

```
┌──────────────┐         ┌──────────┐         ┌──────────────┐
│  Your Code   │◀───────▶│  CLIENT  │◀───────▶│   External   │
│  (Python)    │ Python  │(Adapter) │ Protocol│   System     │
└──────────────┘         └──────────┘         └──────────────┘
```

## Mental Model: The Embassy

Clients are like embassies:

| Embassy Concept | Client Equivalent |
|-----------------|-------------------|
| Embassy building | Client class |
| Ambassador | Client instance |
| Diplomatic protocol | API/protocol |
| Translators | Serialization/deserialization |
| Secure communication | Connection management |

**Key insight**: You don't need to speak every language—you need an embassy that does.

## System Thinking: Clients as Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                     ETTER SYSTEM BOUNDARY                        │
│                                                                  │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│   │  Workflow  │    │  Activity  │    │    API     │           │
│   └─────┬──────┘    └─────┬──────┘    └─────┬──────┘           │
│         │                 │                 │                   │
│         └────────────┬────┴────────────────┘                   │
│                      │                                          │
│                      ▼                                          │
│              ┌───────────────┐                                  │
│              │    CLIENTS    │  ◀── Single point of contact    │
│              └───────┬───────┘                                  │
│                      │                                          │
└──────────────────────┼──────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │  Neo4j  │   │  Redis  │   │   LLM   │   │Workflow │
    │ Database│   │  Cache  │   │ Service │   │   API   │
    └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

## Files in This Package

| File | Client | External System | Purpose |
|------|--------|-----------------|---------|
| `neo4j_client.py` | Neo4jClient | Neo4j graph database | Store roles, JDs, relationships |
| `status_client.py` | StatusClient | Redis | Store workflow status for polling |
| `llm_client.py` | LLMClient | LLM Service (Gemini) | Format JDs, text processing |
| `workflow_api_client.py` | WorkflowAPIClient | Existing workflow API | Trigger AI assessments |

## The Four Clients Explained

### 1. Neo4j Client

**What it does**: Manages graph data (nodes, relationships)

```
                    ┌──────────────┐
                    │ CompanyRole  │
                    │  (Liberty,   │
                    │   Claims)    │
                    └──────┬───────┘
                           │
                    HAS_JOB_DESCRIPTION
                           │
                           ▼
                    ┌──────────────┐
                    │ JobDescription│
                    │  (JD content) │
                    └──────────────┘
```

**Key operations**:
- `create_company_role()` - Create/find role node
- `link_job_description()` - Connect JD to role
- `get_company_role()` - Retrieve role data

### 2. Status Client

**What it does**: Tracks workflow progress in Redis (fast key-value store)

```
Redis Key                          Value
─────────                          ─────
workflow:abc123:status    ──▶     {"state": "processing", "step": "ai_assessment"}
workflow:abc123:progress  ──▶     {"completed": 1, "total": 2, "percent": 50}
```

**Why Redis?**:
- Fast (sub-millisecond reads)
- Ephemeral (status is temporary)
- TTL support (auto-cleanup)

### 3. LLM Client

**What it does**: Uses AI to format and enhance text

```
INPUT                              OUTPUT
─────                              ──────
Raw JD text:              ──▶      Formatted markdown:
"We need someone                   # Software Engineer
who can code and                   ## Responsibilities
work with team..."                 - Write code
                                   - Collaborate with team
```

**Why?**: Consistent, professional JD formatting for AI assessment.

### 4. Workflow API Client

**What it does**: Calls existing AI Assessment workflow

```
┌─────────────────┐         ┌─────────────────┐
│  Etter Workflow │  HTTP   │ Existing AI     │
│  (This package) │ ──────▶ │ Assessment API  │
└─────────────────┘  POST   └─────────────────┘
```

**Why separate?**: AI Assessment is a complex existing system—we integrate, not replace.

## Design Pattern: Singleton with Lazy Loading

All clients use the singleton pattern:

```python
# Global instance (starts as None)
_neo4j_client: Optional[Neo4jClient] = None

def get_neo4j_client() -> Neo4jClient:
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()  # Created only once
    return _neo4j_client
```

**Why singleton?**:
- Connection pooling (reuse connections)
- Resource efficiency (don't open 100 connections)
- Consistent state

## Design Pattern: Dual-Mode Connection

Clients can use existing connections OR create new ones:

```python
class Neo4jClient:
    def __init__(self, use_existing_connection=True):
        if use_existing_connection:
            try:
                # Try to use draup_world_model's connection
                from draup_world_model.connectors.neo4j_connection import Neo4jConnection
                self._external_conn = Neo4jConnection()
            except ImportError:
                # Fall back to standalone connection
                self._driver = create_new_connection()
```

**Why?**:
- In full system: Reuse existing, managed connections
- In isolation: Works without full system installed

## Thought Experiment: Why Not Call Neo4j Directly?

**Without client (scattered calls)**:
```python
# In activity A
driver.session().run("MATCH (n) WHERE n.id = $id", id=id)

# In activity B (different query style)
driver.session().run("MATCH (n {id: $id})", {"id": id})

# In activity C (forgot to close session)
session = driver.session()
session.run(...)
# Oops, no session.close()
```

**With client (centralized)**:
```python
# Everywhere
client.get_company_role(company, role)  # Consistent, managed, tested
```

**Benefits**:
- Single place to change queries
- Connection management in one place
- Consistent error handling
- Easy to mock for testing

## Error Handling Strategy

```python
class Neo4jClient:
    def execute_query(self, query, params):
        try:
            return self._run_query(query, params)
        except ServiceUnavailable:
            # Database is down - retryable
            raise
        except AuthError:
            # Credentials wrong - not retryable
            logger.error("Neo4j authentication failed")
            raise
        except CypherSyntaxError:
            # Bug in our code - not retryable
            logger.error(f"Invalid query: {query}")
            raise
```

## Connection Configuration

All connection details come from `config/settings.py`:

```python
# Neo4j
neo4j_uri = "bolt://neo4j-server:7687"
neo4j_user = "neo4j"
neo4j_password = "secret"

# Redis
redis_host = "127.0.0.1"
redis_port = 6390
redis_password = "secret"

# LLM
llm_model = "gemini-2.0-flash"
```

## Quick Reference

```python
# Neo4j operations
from etter_workflows.clients.neo4j_client import get_neo4j_client

client = get_neo4j_client()
role_id = client.create_company_role("Acme", "Engineer", "Software Engineer")
client.link_job_description(role_id, jd_content, "Engineer JD")

# Status tracking
from etter_workflows.clients.status_client import get_status_client

status_client = get_status_client()
status_client.set_status(workflow_status)
current = status_client.get_status(workflow_id)

# LLM operations
from etter_workflows.clients.llm_client import get_llm_client

llm = get_llm_client()
formatted_jd = llm.format_job_description(raw_jd, "Engineer")
```

## Summary

| Client | External System | Data Type | Persistence |
|--------|-----------------|-----------|-------------|
| Neo4jClient | Neo4j | Graph (roles, JDs) | Permanent |
| StatusClient | Redis | Key-value (status) | Temporary (TTL) |
| LLMClient | Gemini/Claude | Text | None (stateless) |
| WorkflowAPIClient | Assessment API | JSON | None (passthrough) |

**Remember**: Clients isolate external complexity. Your code asks "create role", not "construct Cypher query, manage transaction, handle retries, parse response".
