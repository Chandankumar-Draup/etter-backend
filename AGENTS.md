# Etter Backend - Agent Instructions

This document provides comprehensive guidance for AI coding assistants working with the Etter backend codebase.

## Project Overview

**Etter** is an AI-driven HR operations platform that transforms HR operations into an intelligent hub through automation and seamless integration. The backend is built with FastAPI and provides REST APIs for workforce management, AI automation impact simulation, document management (S3 integration), and user authentication.

### Key Features
- **User Management**: Authentication, authorization with JWT tokens, role-based access control
- **AI Automation Simulation**: Multi-agent simulation system to model workforce impact under automation scenarios
- **Document Management**: S3-based document upload and management with multipart upload support
- **Email Service**: Integration with DraupEmail service for notifications
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis integration for session management and caching

### Technology Stack
- **Framework**: FastAPI (v0.116.1)
- **Python Version**: 3.11+
- **Database**: PostgreSQL with SQLAlchemy 2.0.41
- **Caching**: Redis 6.4.0
- **Authentication**: JWT with PyJWT 2.10.1, bcrypt for password hashing
- **Cloud Storage**: AWS S3 via boto3
- **Migrations**: Alembic 1.16.1
- **Server**: Uvicorn 0.35.0
- **Testing**: pytest 8.4.1
- **Monitoring**: OpenTelemetry instrumentation

## Architecture and Project Structure

```
etter-backend/
├── api/                    # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── user_management.py # User CRUD operations
│   ├── etter_apis.py      # Main Etter API endpoints (simulation, etc.)
│   └── s3/                # S3 document management module
│       ├── api/           # S3 API routes
│       ├── domain/        # Business logic and domain services
│       ├── infra/         # Infrastructure layer (DB, S3)
│       └── schemas/       # Pydantic schemas for S3 operations
├── models/                # SQLAlchemy database models
│   ├── auth.py           # User and authentication models
│   ├── etter.py          # Core Etter models (Company, etc.)
│   └── s3.py             # S3 document models
├── schemas/              # Pydantic schemas for request/response validation
├── services/             # Business logic and service layer
│   ├── auth.py          # Authentication service
│   ├── email_service.py # Email integration
│   ├── etter.py         # Core Etter services
│   └── simulation/      # Simulation engine
├── settings/             # Application configuration
│   ├── server.py        # FastAPI app initialization
│   ├── database.py      # Database connection setup
│   └── service_tracer.py # OpenTelemetry tracing
├── middleware/           # Custom middleware components
├── common/              # Shared utilities and helpers
├── constants/           # Application constants
├── management_commands/ # CLI commands (e.g., generate_super_admin.py)
├── ml_models/          # Machine learning models
├── alembic/            # Database migration scripts
│   └── versions/       # Migration version files
├── docs/               # Additional documentation
├── helm-charts/        # Kubernetes deployment charts
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker container definition
├── alembic.ini       # Alembic configuration
└── uvicorn_config.py # Uvicorn server configuration
```

### Design Patterns
- **Layered Architecture**: Separation of concerns with API, service, and data layers
- **Domain-Driven Design**: S3 module follows DDD with domain services, repositories, and unit of work pattern
- **Dependency Injection**: FastAPI's dependency injection for database sessions and service instances
- **Repository Pattern**: Used in S3 module for data access abstraction

## Development Setup

### Prerequisites
1. Python 3.11 or higher
2. PostgreSQL database
3. Redis server
4. AWS credentials (for S3 operations)
5. Git

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Draup/etter-backend.git
   cd etter-backend
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install uv && uv pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp env_example.txt .env
   ```
   
   Edit `.env` with your configuration:
   - **Database**: `ETTER_DB_HOST`, `ETTER_DB_PORT`, `ETTER_DB_USER`, `ETTER_DB_PASSWORD`, `ETTER_DB_NAME`
   - **JWT**: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
   - **Admin**: `ADMIN_SECRET`
   - **Redis**: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
   - **Simulation**: `SIMULATION_PROVIDER_TYPE` (e.g., "local")

5. **Set up Redis** (if not already running)
   
   MacOS with Homebrew:
   ```bash
   brew install redis
   brew services start redis
   ```
   
   Docker:
   ```bash
   docker run -d --name redis -p 6379:6379 redis:latest
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Create super admin** (optional)
   ```bash
   python -m management_commands.generate_super_admin
   ```

## Build and Test Commands

### Running the Application

**Development server:**
```bash
uvicorn settings.server:etter_app --port 7071 --reload
```

**Production server:**
```bash
uvicorn settings.server:etter_app --host 0.0.0.0 --port 7071 --timeout-keep-alive 600 --timeout-graceful-shutdown 600 --workers 2
```

**Using Docker:**
```bash
docker build -t etter-backend --build-arg GIT_TOKEN=<your_token> .
docker run -p 7071:7071 --env-file .env etter-backend
```

### Testing

**Run tests:**
```bash
pytest
```

**Run tests with coverage:**
```bash
pytest --cov=. --cov-report=html
```

**Run specific test file:**
```bash
pytest tests/test_specific_module.py
```

**Run with verbose output:**
```bash
pytest -v
```

Note: The project includes pytest in requirements.txt but does not currently have a `tests/` directory. When adding tests, follow FastAPI testing patterns using `TestClient`.

### Linting and Code Quality

While no linting tools are explicitly configured, maintain code quality by:
- Following PEP 8 style guidelines
- Using type hints where appropriate
- Use ruff

### Linting
The project uses **Ruff** for Python linting:

```bash
# Install Ruff
pip install ruff

# Lint specific files
ruff check --select F,E,B,TCH,PYI <file.py>

# Auto-fix issues
ruff check --select F,E,B,TCH,PYI --fix <file.py>
```

**Linting Rules:**
- `F`: Pyflakes (undefined names, unused imports)
- `E`: Pycodestyle errors (PEP 8 compliance)
- `B`: Bugbear (common bugs and design problems)
- `TCH`: Type checking imports
- `PYI`: Stub file conventions


### API Documentation

**Interactive API docs (Swagger UI):**
```
http://127.0.0.1:7071/docs/etter
```

**Alternative API docs (ReDoc):**
```
http://127.0.0.1:7071/redoc
```

## Code Style Guidelines

### Python Style
- Follow **PEP 8** conventions
- Use **4 spaces** for indentation (no tabs)
- Maximum line length: Keep reasonable (typically 88-120 characters)
- Use **snake_case** for functions and variables
- Use **PascalCase** for class names
- Use **UPPER_CASE** for constants

### Import Organization
```python
# Standard library imports
import os
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Local application imports
from models.auth import User
from services.auth import verify_token
from settings.database import get_db
```

### Type Hints
Use type hints for function parameters and return values:
```python
def create_user(db: Session, email: str, password: str) -> User:
    # Implementation
    pass
```

### Docstrings
Use docstrings for API endpoints and complex functions:
```python
@router.get('/test')
def test():
    """
    Test endpoint to verify the API is working.
    """
    return {"message": "API is running"}
```

### FastAPI Patterns

**Dependency injection:**
```python
@router.get('/users')
def get_users(db: Session = Depends(get_db), user: User = Depends(verify_token)):
    # Implementation
    pass
```

**Response models:**
```python
@router.post('/users', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    # Implementation
    pass
```

**Error handling:**
```python
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
```

### SQLAlchemy Patterns

**Model definition:**
```python
from sqlalchemy import Column, Integer, String
from settings.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
```

**Query patterns:**
```python
# Use ORM methods
user = db.query(User).filter(User.email == email).first()

# Use session management
db.add(new_user)
db.commit()
db.refresh(new_user)
```

## Database and Migrations

### Database Configuration
- Database connection is configured in `settings/database.py`
- Connection URL is built from environment variables with prefix `ETTER_DB_*`
- Uses SQLAlchemy 2.0 with sessionmaker pattern

### Creating Migrations

**Auto-generate migration:**
```bash
alembic revision --autogenerate -m "Description of changes"
```

**Create empty migration:**
```bash
alembic revision -m "Description of changes"
```

### Running Migrations

**Upgrade to latest:**
```bash
alembic upgrade head
```

**Upgrade by specific steps:**
```bash
alembic upgrade +1
```

**Downgrade:**
```bash
alembic downgrade -1
```

**Show current version:**
```bash
alembic current
```

**Show migration history:**
```bash
alembic history
```

### Migration Best Practices
- Always review auto-generated migrations before applying
- Test migrations in development before production
- Write reversible migrations (implement both upgrade and downgrade)
- Include data migrations when schema changes affect existing data
- Never modify applied migrations; create new ones instead

## Security Considerations

### Authentication and Authorization
- **JWT tokens** are used for authentication
- Tokens have expiration times configured via environment variables
- Passwords are hashed using **bcrypt** before storage
- Never log passwords or tokens
- Use `verify_token` dependency to protect routes

### Sensitive Data
- **Never commit** `.env` files or environment variables containing secrets
- Store secrets in environment variables, not in code
- Sensitive fields (passwords, tokens) should never be returned in API responses
- Use Pydantic models to exclude sensitive fields from responses

### API Security
- Use appropriate HTTP status codes
- Validate all user inputs using Pydantic schemas
- Implement rate limiting for sensitive endpoints (consider adding if not present)
- Use HTTPS in production (configure at reverse proxy/load balancer level)

### Database Security
- Use parameterized queries (SQLAlchemy ORM handles this)
- Never construct SQL with string concatenation
- Limit database user permissions to minimum required
- Use connection pooling appropriately

### AWS S3 Security
- Use IAM roles with minimal required permissions
- Implement presigned URLs for temporary access
- Validate file types and sizes before upload
- Scan uploaded files for malware (consider implementing)

### Dependencies
- Regularly update dependencies to patch security vulnerabilities
- Review security advisories for used packages
- Pin dependency versions in `requirements.txt` for reproducibility

## Environment Configuration

### Required Environment Variables

**Database:**
- `ETTER_DB_HOST`: PostgreSQL host address
- `ETTER_DB_PORT`: PostgreSQL port (default: 5432)
- `ETTER_DB_USER`: Database username
- `ETTER_DB_PASSWORD`: Database password
- `ETTER_DB_NAME`: Database name

**JWT Authentication:**
- `SECRET_KEY`: Secret key for JWT signing (generate a strong random key)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiration (default: 7)

**Admin:**
- `ADMIN_SECRET`: Secret for admin operations

**Redis:**
- `REDIS_HOST`: Redis host address (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (if required)

**Simulation:**
- `SIMULATION_PROVIDER_TYPE`: Type of simulation provider (e.g., "local")

**AWS (for S3 operations):**
- Configure AWS credentials via environment variables or IAM roles
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: AWS region for S3 bucket

### Configuration Files
- `env_example.txt`: Template for environment variables
- `.env`: Actual environment variables (never commit this)
- `alembic.ini`: Alembic migration configuration
- `uvicorn_config.py`: Uvicorn server configuration

## API Endpoints

### Core API Routes

**Base URL:** `http://127.0.0.1:7071`

**API Prefix:** `/api/etter`

### Key Endpoint Groups

1. **Authentication** (`/api/etter/auth`)
   - User registration, login, token refresh
   - JWT token management

2. **User Management** (`/api/etter/users`)
   - CRUD operations for users
   - User profile management
   - Company associations

3. **Simulation** (`/api/etter/simulation/v1`)
   - Create and run AI automation impact simulations
   - Retrieve simulation results
   - Multi-agent workforce modeling

4. **S3 Document Management** (`/api/etter/s3`)
   - Multipart upload initialization
   - Upload parts
   - Complete upload
   - Document retrieval and management

5. **Test Endpoint** (`/api/etter/test`)
   - Health check and API verification

### API Documentation Resources
- **Swagger UI**: http://127.0.0.1:7071/docs/etter
- **Additional Docs**: See `docs/etter_ai_impact_simulation.md` for detailed simulation API documentation

## Deployment

### Docker Deployment

**Build image:**
```bash
docker build -t etter-backend --build-arg GIT_TOKEN=<your_github_token> .
```

Note: The `GIT_TOKEN` is required to install private dependencies from `draup_packages`.

**Run container:**
```bash
docker run -d \
  --name etter-backend \
  -p 7071:7071 \
  --env-file .env \
  etter-backend
```

### Kubernetes Deployment

Helm charts are available in the `helm-charts/etter-backend/` directory.

**Install with Helm:**
```bash
helm install etter-backend ./helm-charts/etter-backend \
  --values ./helm-charts/etter-backend/values.yaml \
  --namespace production
```

**Upgrade deployment:**
```bash
helm upgrade etter-backend ./helm-charts/etter-backend \
  --namespace production
```

### Deployment Considerations
- Configure health check endpoints for load balancers
- Set appropriate resource limits (CPU, memory)
- Use secrets management (Kubernetes Secrets, AWS Secrets Manager)
- Configure logging and monitoring (OpenTelemetry is already integrated)
- Set up Redis for production (consider Redis Cluster for high availability)
- Use connection pooling for database
- Configure CORS if frontend is on different domain

## Commit and Pull Request Guidelines

### Commit Messages

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): add password reset functionality

Implement password reset flow with email verification.
Includes new endpoints and email templates.

Closes #123
```

```
fix(simulation): correct automation rate calculation

The automation rate was not properly normalized across
multiple iterations. Fixed the aggregation logic.
```

### Pull Request Guidelines

**PR Title:** Use same format as commit messages

**PR Description should include:**
- Summary of changes
- Motivation and context
- List of changes (use checkboxes)
- Testing performed
- Related issues/tickets
- Screenshots (for UI changes)
- Breaking changes (if any)

**Before submitting a PR:**
- Ensure code follows style guidelines
- Update documentation if needed
- Add or update tests for new functionality
- Verify all tests pass
- Check for any security implications
- Update API documentation if endpoints changed
- Ensure database migrations are included (if schema changes)

**PR Review Checklist:**
- Code quality and readability
- Proper error handling
- Security considerations
- Performance implications
- Test coverage
- Documentation completeness

## Working with AI Automation Simulation

The simulation feature is a core component. Key points:

- **Simulation Engine**: Multi-agent based modeling using Mesa framework
- **Long-running Process**: Simulations can take significant time; use async patterns
- **Request/Response Pattern**: Initial request returns simulation ID; poll for results
- **Data Model**: Iterations (independent simulations) × Steps (time periods)
- **Input Parameters**: Company, roles, headcount, salaries, automation factor
- **Output Metrics**: Workforce changes, salary impacts, automation rates, capacity utilization

Refer to `docs/etter_ai_impact_simulation.md` for detailed API specifications.

## Common Tasks and Workflows

### Adding a New API Endpoint

1. Define Pydantic schema in `schemas/`
2. Add route handler in appropriate API module (e.g., `api/etter_apis.py`)
3. Implement business logic in `services/`
4. Update database models if needed
5. Create migration if schema changes: `alembic revision --autogenerate -m "Add new table"`
6. Run migration: `alembic upgrade head`
7. Test endpoint using Swagger UI or curl
8. Update API documentation if needed

### Adding a New Database Model

1. Create or update model in `models/` directory
2. Import model in `alembic/env.py` if not auto-discovered
3. Generate migration: `alembic revision --autogenerate -m "Add new model"`
4. Review migration file in `alembic/versions/`
5. Run migration: `alembic upgrade head`
6. Verify in database

### Debugging Issues

1. Check application logs for errors
2. Verify environment variables are set correctly
3. Check database connection and migrations status: `alembic current`
4. Verify Redis is running: `redis-cli ping`
5. Use FastAPI's automatic docs to test endpoints: `/docs/etter`
6. Check OpenTelemetry traces if available

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **Pydantic Documentation**: https://docs.pydantic.dev/
- **Mesa Documentation**: https://mesa.readthedocs.io/ (for simulation framework)

## Notes for AI Agents

- The project uses SQLAlchemy 2.0; be aware of API changes from 1.x
- Some internal dependencies are from private `draup_packages` repository
- When making changes to database schema, always create migrations
- Be careful with async/await patterns; most routes are synchronous
- Redis is used for caching and session management
- The S3 module follows Domain-Driven Design; respect layer boundaries
- When adding authentication to routes, use the `verify_token` dependency
- Environment variables use `ETTER_DB_*` prefix for database config
- The application serves docs at `/docs/etter`, not the default `/docs`
