# Config Package

## First Principle: What Is Configuration?

**Configuration is the set of values that change between environments without changing code.**

```
SAME CODE + DIFFERENT CONFIG = DIFFERENT BEHAVIOR

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Development │     │   Staging   │     │ Production  │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ localhost   │     │ staging-db  │     │ prod-db     │
│ mock data   │     │ test data   │     │ real data   │
│ debug logs  │     │ info logs   │     │ warn logs   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                  │                   │
       └──────────────────┴───────────────────┘
                          │
                    ┌─────┴─────┐
                    │ SAME CODE │
                    └───────────┘
```

## Mental Model: The Control Panel

Configuration is like a control panel:

| Control Panel | Configuration |
|---------------|---------------|
| Dials and switches | Config values |
| Labels on dials | Config keys |
| Default positions | Default values |
| Operator adjustments | Environment overrides |

**Key insight**: The control panel lets you tune behavior without rewiring.

## System Thinking: Config as Environment Adapter

```
┌─────────────────────────────────────────────────────────────────┐
│                         APPLICATION                              │
│                                                                  │
│     ┌─────────────────────────────────────────────────────┐    │
│     │                    CODE (FIXED)                      │    │
│     │                                                      │    │
│     │   workflow = RoleOnboardingWorkflow()               │    │
│     │   client = Neo4jClient(uri=settings.neo4j_uri)      │    │
│     │                          ▲                          │    │
│     └──────────────────────────┼──────────────────────────┘    │
│                                │                                 │
│     ┌──────────────────────────┼──────────────────────────┐    │
│     │               CONFIG (VARIABLE)                      │    │
│     │                                                      │    │
│     │   neo4j_uri = "bolt://server:7687"                  │    │
│     │   redis_host = "127.0.0.1"                          │    │
│     │   enable_mock_data = True                           │    │
│     └─────────────────────────────────────────────────────┘    │
│                                ▲                                 │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     ENVIRONMENT          │
                    │  (env vars, .env file)   │
                    └─────────────────────────┘
```

## Files in This Package

| File | Purpose |
|------|---------|
| `settings.py` | All configuration values (Pydantic Settings) |
| `retry_policies.py` | Retry configurations for different operations |

## Configuration Categories

### 1. Database Connections

```python
# Neo4j
neo4j_uri: str = "bolt://localhost:7687"
neo4j_user: str = "neo4j"
neo4j_password: str = "password"
neo4j_database: str = "neo4j"

# Redis
redis_host: str = "127.0.0.1"
redis_port: int = 6390
redis_password: Optional[str] = None
```

### 2. Temporal Settings

```python
temporal_host: str = "localhost:7233"
temporal_namespace: str = "default"
temporal_task_queue: str = "etter-workflows"
```

### 3. Feature Flags

```python
enable_mock_data: bool = True    # Use mock providers
debug_mode: bool = False         # Extra logging
```

### 4. Operational Limits

```python
temporal_max_concurrent_activities: int = 10
neo4j_max_connection_pool_size: int = 50
redis_socket_timeout: int = 30
```

## The 12-Factor App: Config in Environment

We follow the [12-factor app](https://12factor.net/config) principle:

**"Store config in the environment"**

```bash
# Set via environment variables
export ETTER_NEO4J_URI="bolt://prod-neo4j:7687"
export ETTER_REDIS_HOST="prod-redis"
export ETTER_ENABLE_MOCK_DATA="false"

# Or via .env file
cat .env
ETTER_NEO4J_URI=bolt://prod-neo4j:7687
ETTER_REDIS_HOST=prod-redis
ETTER_ENABLE_MOCK_DATA=false
```

## Pydantic Settings

We use Pydantic's `BaseSettings` for automatic environment loading:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    redis_host: str = Field(default="127.0.0.1")
    enable_mock_data: bool = Field(default=True)

    class Config:
        env_prefix = "ETTER_"  # All vars start with ETTER_
        env_file = ".env"      # Load from .env file
```

**Resolution order** (later wins):
1. Default value in code
2. `.env` file
3. Environment variable

## Thought Experiment: Why Not Hardcode?

**Hardcoded** (bad):
```python
client = Neo4jClient(uri="bolt://prod-server:7687")
# To change: edit code → commit → deploy
# Risk: accidentally deploy dev settings to prod
```

**Configured** (good):
```python
client = Neo4jClient(uri=settings.neo4j_uri)
# To change: set environment variable
# No code change needed
```

## Retry Policies

Different operations need different retry strategies:

```python
# Database operations - fast retries
def get_db_retry_policy():
    return RetryConfig(
        maximum_attempts=3,
        initial_interval=timedelta(seconds=1),
        maximum_interval=timedelta(seconds=10),
        backoff_coefficient=2.0,
    )

# LLM calls - slower retries (rate limits)
def get_llm_retry_policy():
    return RetryConfig(
        maximum_attempts=3,
        initial_interval=timedelta(seconds=5),
        maximum_interval=timedelta(seconds=60),
        backoff_coefficient=2.0,
    )
```

**Why different?**:
- DB failures: Usually brief, retry quickly
- LLM failures: Often rate limits, wait longer

## Environment-Specific Configs

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT                               │
├─────────────────────────────────────────────────────────────┤
│  neo4j_uri = "bolt://localhost:7687"                        │
│  redis_host = "localhost"                                    │
│  enable_mock_data = True      ◀── Safe, no real changes     │
│  log_level = "DEBUG"          ◀── Verbose logging           │
│  temporal_namespace = "etter-dev"                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION                                │
├─────────────────────────────────────────────────────────────┤
│  neo4j_uri = "bolt://prod-neo4j.internal:7687"             │
│  redis_host = "prod-redis.internal"                         │
│  enable_mock_data = False     ◀── Real data                 │
│  log_level = "WARNING"        ◀── Less noise                │
│  temporal_namespace = "etter-prod"                          │
└─────────────────────────────────────────────────────────────┘
```

## Sensitive Values

**Never commit secrets to code!**

```python
# Good: Read from environment
neo4j_password: str = Field(default="")  # Empty default, MUST be set

# In production:
export ETTER_NEO4J_PASSWORD="actual-secret-password"
```

**For production**, use:
- Environment variables
- Secret managers (AWS Secrets Manager, HashiCorp Vault)
- Kubernetes secrets

## Quick Reference

```python
# Access settings anywhere
from etter_workflows.config.settings import get_settings

settings = get_settings()
print(f"Neo4j: {settings.neo4j_uri}")
print(f"Mock mode: {settings.enable_mock_data}")

# Override for testing
import os
os.environ["ETTER_ENABLE_MOCK_DATA"] = "true"
settings = get_settings()  # Will use mock data
```

## Configuration Checklist

```
┌─────────────────────────────────────────────────────────────┐
│  BEFORE DEPLOYMENT                                           │
├─────────────────────────────────────────────────────────────┤
│  □ Neo4j URI points to correct database                     │
│  □ Neo4j credentials are set (not defaults)                 │
│  □ Redis host is reachable                                  │
│  □ Temporal namespace exists                                │
│  □ enable_mock_data = False (for production)                │
│  □ Log level is appropriate (not DEBUG in prod)             │
│  □ Secrets are not in code or .env committed to git         │
└─────────────────────────────────────────────────────────────┘
```

## Summary

| Concept | Implementation |
|---------|---------------|
| **Config source** | Environment variables (ETTER_* prefix) |
| **Fallback** | .env file, then code defaults |
| **Validation** | Pydantic (type checking, constraints) |
| **Access** | `get_settings()` singleton |
| **Secrets** | Environment only, never in code |

**Remember**: Code should be environment-agnostic. The same code runs everywhere—only config changes.
