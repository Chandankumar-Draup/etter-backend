# Quick Start: Critical Optimizations

This document provides **copy-paste ready code** for the most impactful optimizations you can implement immediately.

---

## 🚀 1. Database Indexes (2 hours, 50-90% faster queries)

### Create Migration File

```bash
alembic revision -m "add_performance_indexes"
```

### Migration Code

**File**: `alembic/versions/XXXXXX_add_performance_indexes.py`

```python
"""add_performance_indexes

Revision ID: XXXXXX
Revises: YYYYYY
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'XXXXXX'
down_revision = 'YYYYYY'
branch_labels = None
depends_on = None

def upgrade():
    op.create_index('idx_users_email', 'users', ['email'], schema='etter')
    op.create_index('idx_users_company_id', 'users', ['company_id'], schema='etter')
    op.create_index('idx_users_username', 'users', ['username'], schema='etter')
    
    op.create_index('idx_user_workflow_history_user_id', 'user_workflow_history', ['user_id'], schema='etter')
    op.create_index('idx_user_workflow_history_workflow_id', 'user_workflow_history', ['workflow_id'], schema='etter')
    op.create_index('idx_user_workflow_history_status', 'user_workflow_history', ['status'], schema='etter')
    op.create_index(
        'idx_user_workflow_history_composite',
        'user_workflow_history',
        ['user_id', 'workflow_id', 'status'],
        schema='etter'
    )
    
    op.create_index('idx_documents_tenant_id', 'documents', ['tenant_id'], schema='etter')
    op.create_index('idx_documents_status', 'documents', ['status'], schema='etter')
    op.create_index('idx_documents_created_at', 'documents', ['created_at'], schema='etter')
    op.create_index('idx_documents_tenant_status', 'documents', ['tenant_id', 'status'], schema='etter')
    
    op.create_index('idx_workflow_info_company_id', 'workflow_info', ['company_id'], schema='etter')
    op.create_index('idx_chro_dashboard_workflow_id', 'chro_dashboard_entry', ['workflow_id'], schema='etter')
    
    op.create_index('idx_master_company_name', 'master_company', ['company_name'], schema='etter')

def downgrade():
    op.drop_index('idx_users_email', schema='etter')
    op.drop_index('idx_users_company_id', schema='etter')
    op.drop_index('idx_users_username', schema='etter')
    
    op.drop_index('idx_user_workflow_history_user_id', schema='etter')
    op.drop_index('idx_user_workflow_history_workflow_id', schema='etter')
    op.drop_index('idx_user_workflow_history_status', schema='etter')
    op.drop_index('idx_user_workflow_history_composite', schema='etter')
    
    op.drop_index('idx_documents_tenant_id', schema='etter')
    op.drop_index('idx_documents_status', schema='etter')
    op.drop_index('idx_documents_created_at', schema='etter')
    op.drop_index('idx_documents_tenant_status', schema='etter')
    
    op.drop_index('idx_workflow_info_company_id', schema='etter')
    op.drop_index('idx_chro_dashboard_workflow_id', schema='etter')
    
    op.drop_index('idx_master_company_name', schema='etter')
```

### Apply Migration

```bash
alembic upgrade head
```

---

## 💨 2. Response Compression (30 min, 60-80% smaller responses)

### Update Server Configuration

**File**: `settings/server.py`

Add this import at the top:
```python
from fastapi.middleware.gzip import GZipMiddleware
```

Add this line after `add_cors_middleware(etter_app)`:
```python
etter_app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Complete updated section**:
```python
add_cors_middleware(etter_app)
etter_app.add_middleware(GZipMiddleware, minimum_size=1000)

etter_app.include_router(etter_api_router)
```

---

## 🔌 3. Connection Pooling (1 hour, 30-50% better throughput)

### Update Database Configuration

**File**: `settings/database.py`

Replace the entire file with:

```python
import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

POSTGRES_HOST = os.environ.get('ETTER_DB_HOST')
POSTGRES_PORT = os.environ.get('ETTER_DB_PORT')
POSTGRES_USER = os.environ.get('ETTER_DB_USER')
POSTGRES_PASSWORD = os.environ.get('ETTER_DB_PASSWORD')
POSTGRES_DB = os.environ.get('ETTER_DB_NAME')

DATABASE_URL = URL.create(
    drivername="postgresql",
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    port=POSTGRES_PORT
)

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.environ.get('DB_POOL_SIZE', 20)),
    max_overflow=int(os.environ.get('DB_MAX_OVERFLOW', 40)),
    pool_pre_ping=True,
    pool_recycle=int(os.environ.get('DB_POOL_RECYCLE', 3600)),
    echo=False,
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"
    }
)

@event.listens_for(engine, "connect")
def set_postgres_config(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET TIME ZONE 'UTC'")
    cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Update Environment Variables

**File**: `env_example.txt`

Add these lines:
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600
```

---

## 🛡️ 4. Rate Limiting (2 hours, security protection)

### Create Rate Limiter Middleware

**File**: `middleware/rate_limiter.py` (new file)

```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from services.redis_store import get_redis_client
from common.logger import logger
import time

class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        try:
            self.redis = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
            self.redis = None

    def is_allowed(self, key: str) -> bool:
        if not self.redis:
            return True
        
        try:
            current = int(time.time())
            window_start = current - self.window
            
            redis_key = f"rate_limit:{key}"
            
            pipe = self.redis.redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zadd(redis_key, {str(current): current})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, self.window)
            results = pipe.execute()
            
            request_count = results[2]
            
            return request_count <= self.requests
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int = 1000, window: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(requests, window)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/metrics", "/docs/etter"]:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        
        if not self.limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        response = await call_next(request)
        return response
```

### Add to Server

**File**: `settings/server.py`

Add import:
```python
from middleware.rate_limiter import RateLimitMiddleware
```

Add middleware (after CORS):
```python
add_cors_middleware(etter_app)
etter_app.add_middleware(GZipMiddleware, minimum_size=1000)
etter_app.add_middleware(RateLimitMiddleware, requests=1000, window=60)
```

---

logging already implemented

<!-- ## 📝 5. Request Logging (2 hours, better debugging)

### Create Logging Middleware

**File**: `middleware/logging_middleware.py` (new file)

```python
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from common.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.time()
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                },
                exc_info=True
            )
            raise
```

### Add to Server

**File**: `settings/server.py`

Add import:
```python
from middleware.logging_middleware import RequestLoggingMiddleware
```

Add middleware:
```python
etter_app.add_middleware(RequestLoggingMiddleware)
``` -->

 --- cache already applied whereever it is needed
<!--
## 💾 6. Enhanced Caching (1 day, 90%+ faster cached responses)

### Create Cache Service

**File**: `services/cache_service.py` (new file)

```python
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
from services.redis_store import get_redis_client
from common.logger import logger

class CacheService:
    def __init__(self):
        try:
            self.redis = get_redis_client()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis = None
            self.enabled = False
        
        self.default_ttl = 3600

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix] + [str(arg) for arg in args]
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])
        
        key_string = ":".join(key_parts)
        if len(key_string) > 250:
            key_string = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"etter:{key_string}"

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        
        try:
            data = self.redis.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        if not self.enabled:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.enabled:
            return False
        
        try:
            self.redis.delete(key)
            logger.debug(f"Deleted cache: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis.redis.keys(f"etter:{pattern}*")
            if keys:
                count = self.redis.redis.delete(*keys)
                logger.info(f"Deleted {count} keys matching {pattern}")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

def cache_result(ttl: int = 3600, key_prefix: str = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheService()
            
            if not cache.enabled:
                return func(*args, **kwargs)
            
            prefix = key_prefix or func.__name__
            
            cache_args = args[1:] if len(args) > 0 else args
            cache_key = cache._generate_key(prefix, *cache_args, **kwargs)
            
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

cache_service = CacheService()
```

### Apply Caching to Endpoints

**Example 1**: Cache master companies

**File**: `api/etter_apis.py`

Add import:
```python
from services.cache_service import cache_result
```

Update endpoint:
```python
@etter_api_router.get("/master_companies")
@cache_result(ttl=3600, key_prefix="master_companies")
def get_master_companies(
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    companies = db.query(MasterCompany).all()
    return {
        "status": "success",
        "data": [{"id": c.id, "company_name": c.company_name} for c in companies]
    }
```

**Example 2**: Cache autocomplete

```python
@etter_api_router.get('/auto_complete_username')
@cache_result(ttl=300, key_prefix="autocomplete_username")
async def auto_complete_username(
    username: Optional[str] = None,
    user_group: Optional[str] = None,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
```

--- -->

table and api both removed

<!-- ## 🔧 7. Fix N+1 Query in get_chro_data (2 hours, 70-90% faster)

### Update get_chro_data Endpoint

**File**: `api/etter_apis.py`

Find the `get_chro_data` function and replace with:

```python
from sqlalchemy.orm import joinedload

@etter_api_router.get("/get_chro_data")
def get_chro_data(
    db: Session = Depends(get_db),
    draup_user = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.get("data")
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        company_id = current_user.company_id if current_user else None
        
        query = (
            db.query(ChroDashboardEntry)
            .options(
                joinedload(ChroDashboardEntry.workflow),
                joinedload(ChroDashboardEntry.etter_impact_score),
                joinedload(ChroDashboardEntry.validated_ai_impact_score)
                    .joinedload(UserWorkflowHistory.user)
            )
        )
        
        if company_id:
            query = query.join(WorkflowInfo).filter(WorkflowInfo.company_id == company_id)
        
        results = query.all()
        
        response = []
        for entry in results:
            response.append({
                "chro_entry_id": entry.id,
                "workflow_id": entry.workflow.id if entry.workflow else None,
                "workflow_name": entry.workflow.workflow_name if entry.workflow else None,
                "job_role": entry.job_role,
                "etter_score": entry.etter_impact_score.score if entry.etter_impact_score else None,
                "validated_score": entry.validated_ai_impact_score.score if entry.validated_ai_impact_score else None,
                "validated_user": entry.validated_ai_impact_score.user.username if entry.validated_ai_impact_score and entry.validated_ai_impact_score.user else None
            })
        
        return {
            "status": "success",
            "data": response
        }
    
    except Exception as e:
        logger.error(f"Error in get_chro_data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

--- -->

## 📊 8. Add Pagination Helper (1 hour, consistent performance)

### Create Pagination Utility

**File**: `common/pagination.py` (new file)

```python
from typing import List, Any, Optional
from math import ceil
from sqlalchemy.orm import Query
from pydantic import BaseModel

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 50
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    def validate(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 1000:
            raise ValueError("Page size must be between 1 and 1000")

class PaginatedResult(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 50
) -> PaginatedResult:
    params = PaginationParams(page=page, page_size=page_size)
    params.validate()
    
    total = query.count()
    items = query.offset(params.offset).limit(page_size).all()
    
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    return PaginatedResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
```

### Use Pagination in Endpoints

**Example**: Paginate user list

```python
from common.pagination import paginate
from fastapi import Query

@etter_api_router.get("/users")
def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    query = db.query(User).filter(User.company_id == current_user.company_id)
    
    result = paginate(query, page, page_size)
    
    return {
        "status": "success",
        "data": {
            "users": [user.to_dict() for user in result.items],
            "pagination": {
                "total": result.total,
                "page": result.page,
                "page_size": result.page_size,
                "total_pages": result.total_pages,
                "has_next": result.has_next,
                "has_prev": result.has_prev
            }
        }
    }
```

---

## ✅ Deployment Checklist

### Before Deploying

- [ ] Run migrations in development
- [ ] Test all changes locally
- [ ] Update environment variables
- [ ] Review logs for errors
- [ ] Test rate limiting doesn't block legitimate users
- [ ] Verify caching works correctly
- [ ] Check database connection pool metrics

### After Deploying

- [ ] Monitor response times
- [ ] Check error rates
- [ ] Verify cache hit rates
- [ ] Monitor database connection pool
- [ ] Check rate limit logs
- [ ] Review application logs

### Rollback Plan

If issues occur:
1. Remove middleware from `settings/server.py`
2. Revert database.py changes
3. Downgrade database migration
4. Restart application

---

## 📈 Measuring Success

### Before Optimization

Run these queries to establish baseline:

```bash
# Average response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:7071/api/etter/master_companies

# Database query count (check logs)
# Look for number of SELECT statements per request
```

### After Optimization

Compare metrics:
- Response time should be 50-90% faster
- Database queries should be 70-90% fewer
- Response size should be 60-80% smaller (with compression)
- Cache hit rate should be 80%+ after warmup

---

## 🆘 Troubleshooting

### Issue: Rate limiting blocking legitimate users
**Solution**: Increase limits in `settings/server.py`:
```python
etter_app.add_middleware(RateLimitMiddleware, requests=2000, window=60)
```

### Issue: Cache not working
**Solution**: Check Redis connection:
```python
from services.redis_store import get_redis_client
redis = get_redis_client()
redis.ping()
```

### Issue: Database connection pool exhausted
**Solution**: Increase pool size in environment variables:
```bash
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=60
```

### Issue: Slow queries after adding indexes
**Solution**: Run ANALYZE on tables:
```sql
ANALYZE users;
ANALYZE user_workflow_history;
ANALYZE documents;
```

---

## 🎉 Next Steps

After implementing these optimizations:

1. **Measure improvements** - Track response times and throughput
2. **Monitor for issues** - Watch logs and error rates
3. **Iterate** - Apply learnings to other endpoints
4. **Move to Phase 2** - Implement advanced optimizations from main guide

**Congratulations!** These changes alone should give you 2-3x performance improvement! 🚀

