# Etter Self-Service Pipeline - Deployment Guide

This document provides comprehensive instructions for deploying and setting up the Etter Self-Service Pipeline, including Temporal workflow orchestration, Neo4j, Redis, and the API server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Temporal Setup](#temporal-setup)
- [Infrastructure Configuration](#infrastructure-configuration)
- [Deployment Options](#deployment-options)
- [Production Deployment](#production-deployment)
- [Monitoring & Operations](#monitoring--operations)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Runtime |
| Redis | 6.0+ | Status tracking |
| Neo4j | 5.0+ | Graph database |
| Temporal | 1.20+ | Workflow orchestration |

### Python Dependencies

```bash
pip install pydantic pydantic-settings fastapi uvicorn httpx redis neo4j temporalio
```

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ETTER SELF-SERVICE PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API LAYER (FastAPI)                           │   │
│  │  Port: 8090                                                          │   │
│  │  Endpoints: /push, /status, /health, /companies, /roles              │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    TEMPORAL ORCHESTRATION                            │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐   │   │
│  │  │ TEMPORAL SERVER │    │    WORKERS      │    │   WORKFLOWS    │   │   │
│  │  │   Port: 7233    │◀──▶│ Task Queue:     │◀──▶│ RoleOnboarding │   │   │
│  │  │   (gRPC)        │    │ etter-workflows │    │                │   │   │
│  │  └─────────────────┘    └─────────────────┘    └────────────────┘   │   │
│  │                                                                      │   │
│  │  Namespace: etter-{env}                                              │   │
│  │  Activities: create_company_role, link_jd, run_ai_assessment         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │     NEO4J       │  │     REDIS       │  │   WORKFLOW API      │  │   │
│  │  │  CompanyRole    │  │  Status Cache   │  │   AI Assessment     │  │   │
│  │  │  JobDescription │  │  Progress       │  │   Port: 8082        │  │   │
│  │  │  Port: 7687     │  │  Port: 6390     │  │                     │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Temporal Architecture

```
TEMPORAL WORKFLOW ORCHESTRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────────────────────────────────────────────────────────────┐
│                          TEMPORAL SERVER                                  │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐  │
│  │  Frontend      │  │  History       │  │  Matching Service          │  │
│  │  Service       │  │  Service       │  │  (Task Queue Management)   │  │
│  │  (gRPC API)    │  │  (Persistence) │  │                            │  │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘  │
│                                                                          │
│  Storage: PostgreSQL or MySQL or Cassandra                               │
│  Visibility: Elasticsearch (optional)                                    │
│                                                                          │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  │ gRPC (Port 7233)
                                  │
┌─────────────────────────────────▼────────────────────────────────────────┐
│                            WORKERS                                        │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Worker Process                                                   │    │
│  │                                                                   │    │
│  │  Task Queue: etter-workflows                                      │    │
│  │  Namespace: etter-{dev|staging|prod}                              │    │
│  │                                                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐ │    │
│  │  │ REGISTERED WORKFLOWS                                         │ │    │
│  │  │                                                              │ │    │
│  │  │ • RoleOnboardingWorkflow                                     │ │    │
│  │  │   - Executes: role_setup → ai_assessment                     │ │    │
│  │  │   - Timeout: 2 hours                                         │ │    │
│  │  │   - Retry: Per-activity                                      │ │    │
│  │  │                                                              │ │    │
│  │  └─────────────────────────────────────────────────────────────┘ │    │
│  │                                                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐ │    │
│  │  │ REGISTERED ACTIVITIES                                        │ │    │
│  │  │                                                              │ │    │
│  │  │ • create_company_role                                        │ │    │
│  │  │   Timeout: 5 min | Retry: 3x | DB: Neo4j                    │ │    │
│  │  │                                                              │ │    │
│  │  │ • link_job_description                                       │ │    │
│  │  │   Timeout: 5 min | Retry: 3x | DB: Neo4j, LLM               │ │    │
│  │  │                                                              │ │    │
│  │  │ • run_ai_assessment                                          │ │    │
│  │  │   Timeout: 30 min | Retry: 5x | API: Workflow Server         │ │    │
│  │  │                                                              │ │    │
│  │  └─────────────────────────────────────────────────────────────┘ │    │
│  │                                                                   │    │
│  │  Concurrency:                                                     │    │
│  │  • Max Concurrent Activities: 50                                  │    │
│  │  • Max Concurrent Workflows: 100                                  │    │
│  │                                                                   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Workflow Execution Flow

```
WORKFLOW EXECUTION TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

API Request                 Temporal                    Worker                   Data Layer
    │                          │                          │                          │
    │  POST /push              │                          │                          │
    │─────────────────────────▶│                          │                          │
    │                          │                          │                          │
    │  workflow_id returned    │  Schedule Workflow       │                          │
    │◀─────────────────────────│─────────────────────────▶│                          │
    │                          │                          │                          │
    │                          │                          │  Execute role_setup      │
    │                          │                          │─────────────────────────▶│
    │                          │                          │  Create CompanyRole      │
    │                          │                          │◀─────────────────────────│
    │                          │                          │                          │
    │                          │  Activity Complete       │                          │
    │                          │◀─────────────────────────│                          │
    │                          │                          │                          │
    │                          │                          │  Execute ai_assessment   │
    │                          │                          │─────────────────────────▶│
    │                          │                          │  Run Assessment          │
    │                          │                          │  (5-15 minutes)          │
    │                          │                          │◀─────────────────────────│
    │                          │                          │                          │
    │                          │  Workflow Complete       │                          │
    │                          │◀─────────────────────────│                          │
    │                          │                          │                          │
    │  GET /status/{id}        │                          │                          │
    │─────────────────────────▶│                          │                          │
    │  status: ready           │                          │                          │
    │◀─────────────────────────│                          │                          │
    │                          │                          │                          │
```

---

## Temporal Setup

### Option 1: Local Development Server

For local development and testing, use Temporal's dev server:

```bash
# Install Temporal CLI
# macOS
brew install temporal

# Linux
curl -sSf https://temporal.download/cli.sh | sh

# Start the dev server
temporal server start-dev

# The server runs on:
# - gRPC: localhost:7233
# - Web UI: http://localhost:8233
```

**Environment Configuration:**
```bash
export ETTER_TEMPORAL_HOST=localhost:7233
export ETTER_TEMPORAL_NAMESPACE=default
```

### Option 2: SSH Tunnel to QA Temporal

For connecting to the QA Temporal cluster:

```bash
# Setup SSH tunnel
ssh -N -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
    ShreyashKumar-Draup@3.128.8.200

# Keep running in background
ssh -fN -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
    ShreyashKumar-Draup@3.128.8.200
```

**Environment Configuration:**
```bash
export ETTER_TEMPORAL_HOST=localhost:5445
export ETTER_TEMPORAL_NAMESPACE=etter-dev
```

### Option 3: Docker Compose (Self-Hosted)

```yaml
# docker-compose.temporal.yml
version: '3.8'

services:
  postgresql:
    image: postgres:13
    environment:
      POSTGRES_USER: temporal
      POSTGRES_PASSWORD: temporal
      POSTGRES_DB: temporal
    volumes:
      - temporal-postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U temporal"]
      interval: 5s
      timeout: 5s
      retries: 5

  temporal:
    image: temporalio/auto-setup:1.22.0
    depends_on:
      postgresql:
        condition: service_healthy
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal
      - POSTGRES_SEEDS=postgresql
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development.yaml
    ports:
      - "7233:7233"
    volumes:
      - ./temporal-config:/etc/temporal/config/dynamicconfig

  temporal-admin-tools:
    image: temporalio/admin-tools:1.22.0
    depends_on:
      - temporal
    environment:
      - TEMPORAL_CLI_ADDRESS=temporal:7233
    stdin_open: true
    tty: true

  temporal-ui:
    image: temporalio/ui:2.17.0
    depends_on:
      - temporal
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
      - TEMPORAL_CORS_ORIGINS=http://localhost:3000
    ports:
      - "8233:8080"

volumes:
  temporal-postgres:
```

**Start Temporal:**
```bash
docker-compose -f docker-compose.temporal.yml up -d
```

### Creating Namespaces

```bash
# Using temporal CLI
temporal operator namespace create etter-dev
temporal operator namespace create etter-staging
temporal operator namespace create etter-prod

# Or via tctl (in admin-tools container)
docker exec -it temporal-admin-tools tctl namespace register etter-dev
```

---

## Infrastructure Configuration

### Production Configuration

Create a `.env` file:

```env
# Environment
ETTER_ENVIRONMENT=production
ETTER_DEBUG=false
ETTER_ENABLE_MOCK_DATA=false

# Temporal Configuration
# Option A: Direct connection (production)
ETTER_TEMPORAL_HOST=temporal-server.internal:7233
# Option B: SSH tunnel
# ETTER_TEMPORAL_HOST=localhost:5445
ETTER_TEMPORAL_NAMESPACE=etter-prod
ETTER_TEMPORAL_TASK_QUEUE=etter-workflows
ETTER_TEMPORAL_MAX_CONCURRENT_ACTIVITIES=50
ETTER_TEMPORAL_MAX_CONCURRENT_WORKFLOWS=100

# Neo4j Configuration
ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
ETTER_NEO4J_USER=neo4j
ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R
ETTER_NEO4J_DATABASE=neo4j
ETTER_NEO4J_MAX_CONNECTION_LIFETIME=3600
ETTER_NEO4J_MAX_CONNECTION_POOL_SIZE=50

# Redis Configuration
ETTER_REDIS_HOST=127.0.0.1
ETTER_REDIS_PORT=6390
ETTER_REDIS_DB=3
ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK
ETTER_REDIS_SOCKET_TIMEOUT=30
ETTER_REDIS_CONNECT_TIMEOUT=30
ETTER_REDIS_RETRY_ON_TIMEOUT=true
ETTER_REDIS_HEALTH_CHECK_INTERVAL=30
ETTER_REDIS_STATUS_TTL_SECONDS=86400

# API Configuration
ETTER_API_HOST=0.0.0.0
ETTER_API_PORT=8090

# Workflow API (existing)
ETTER_WORKFLOW_API_BASE_URL=http://127.0.0.1:8082
ETTER_WORKFLOW_API_TIMEOUT=600

# Logging
ETTER_LOG_LEVEL=INFO
```

### Development Configuration

```env
# Environment
ETTER_ENVIRONMENT=development
ETTER_DEBUG=true
ETTER_ENABLE_MOCK_DATA=true

# Temporal - Local dev server
ETTER_TEMPORAL_HOST=localhost:7233
ETTER_TEMPORAL_NAMESPACE=default

# Neo4j - Same as production (shared)
ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
ETTER_NEO4J_USER=neo4j
ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R

# Redis - Local or shared
ETTER_REDIS_HOST=127.0.0.1
ETTER_REDIS_PORT=6390
ETTER_REDIS_DB=3
ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK

# Logging
ETTER_LOG_LEVEL=DEBUG
```

---

## Deployment Options

### Option 1: Development (Single Machine)

```bash
# Terminal 1: Start Temporal dev server
temporal server start-dev

# Terminal 2: Start the worker
cd draup_world_model/etter-workflows
python -m etter_workflows.worker

# Terminal 3: Start the API server
cd draup_world_model/etter-workflows
uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --reload
```

### Option 2: Using Makefile

Create a `Makefile`:

```makefile
.PHONY: temporal worker api all stop

# Start Temporal dev server
temporal:
	temporal server start-dev

# Start the worker
worker:
	python -m etter_workflows.worker

# Start the API server
api:
	uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090

# Start API with reload (development)
api-dev:
	uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --reload

# Run demo
demo:
	python demo.py

# Install dependencies
install:
	pip install -e .

# Install dev dependencies
install-dev:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v

# Health check
health:
	curl -s http://localhost:8090/api/v1/pipeline/health | python -m json.tool
```

### Option 3: Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API Server
  etter-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8090:8090"
    environment:
      - ETTER_ENVIRONMENT=production
      - ETTER_TEMPORAL_HOST=temporal:7233
      - ETTER_TEMPORAL_NAMESPACE=etter-prod
      - ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
      - ETTER_NEO4J_USER=neo4j
      - ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R
      - ETTER_REDIS_HOST=redis
      - ETTER_REDIS_PORT=6379
      - ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK
      - ETTER_ENABLE_MOCK_DATA=false
    depends_on:
      - temporal
      - redis
    command: uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090

  # Temporal Worker
  etter-worker:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - ETTER_ENVIRONMENT=production
      - ETTER_TEMPORAL_HOST=temporal:7233
      - ETTER_TEMPORAL_NAMESPACE=etter-prod
      - ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
      - ETTER_NEO4J_USER=neo4j
      - ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R
      - ETTER_REDIS_HOST=redis
      - ETTER_REDIS_PORT=6379
      - ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK
    depends_on:
      - temporal
      - redis
    command: python -m etter_workflows.worker
    deploy:
      replicas: 2  # Run 2 workers for redundancy

  # Redis (for status tracking)
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass F6muBM65GqSyvtzBqArK
    ports:
      - "6390:6379"
    volumes:
      - redis-data:/data

  # Temporal (see temporal docker-compose above)
  # Include temporal services here or use external

volumes:
  redis-data:
```

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy package
COPY draup_world_model/etter-workflows /app/etter-workflows
COPY draup_world_model/automated_workflow /app/automated_workflow

# Install Python dependencies
RUN pip install --no-cache-dir -e /app/etter-workflows

# Set working directory
WORKDIR /app/etter-workflows

# Default command (overridden in docker-compose)
CMD ["uvicorn", "etter_workflows.api.routes:app", "--host", "0.0.0.0", "--port", "8090"]
```

---

## Production Deployment

### Systemd Service (API Server)

```ini
# /etc/systemd/system/etter-api.service
[Unit]
Description=Etter Self-Service Pipeline API
After=network.target

[Service]
Type=simple
User=etter
Group=etter
WorkingDirectory=/opt/etter/etter-workflows
Environment="PATH=/opt/etter/venv/bin"
EnvironmentFile=/opt/etter/.env
ExecStart=/opt/etter/venv/bin/uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Systemd Service (Worker)

```ini
# /etc/systemd/system/etter-worker.service
[Unit]
Description=Etter Temporal Worker
After=network.target

[Service]
Type=simple
User=etter
Group=etter
WorkingDirectory=/opt/etter/etter-workflows
Environment="PATH=/opt/etter/venv/bin"
EnvironmentFile=/opt/etter/.env
ExecStart=/opt/etter/venv/bin/python -m etter_workflows.worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable etter-api
sudo systemctl enable etter-worker

# Start services
sudo systemctl start etter-api
sudo systemctl start etter-worker

# Check status
sudo systemctl status etter-api
sudo systemctl status etter-worker

# View logs
journalctl -u etter-api -f
journalctl -u etter-worker -f
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/etter-api
upstream etter_api {
    server 127.0.0.1:8090;
}

server {
    listen 80;
    server_name etter-api.draup.technology;

    location / {
        proxy_pass http://etter_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /api/v1/pipeline/health {
        proxy_pass http://etter_api;
        access_log off;
    }
}
```

---

## Monitoring & Operations

### Health Checks

```bash
# API Health
curl http://localhost:8090/api/v1/pipeline/health

# Expected response:
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-01-28T10:00:00Z",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "mock_data": "disabled"
  }
}
```

### Temporal Web UI

Access at `http://localhost:8233` (local) or your configured URL:

- View workflow executions
- Monitor task queues
- Debug failed workflows
- View workflow history

### Key Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Queue Depth | Workflows waiting | > 200 |
| Processing Time p50 | Median duration | > 15 min |
| Processing Time p99 | 99th percentile | > 45 min |
| Success Rate | Completion rate | < 90% |
| Worker Utilization | Capacity usage | > 85% |

### Temporal CLI Commands

```bash
# List workflows
temporal workflow list --namespace etter-prod

# Describe a workflow
temporal workflow describe --workflow-id {workflow_id} --namespace etter-prod

# View workflow history
temporal workflow show --workflow-id {workflow_id} --namespace etter-prod

# Terminate a stuck workflow
temporal workflow terminate --workflow-id {workflow_id} --namespace etter-prod

# Reset a failed workflow
temporal workflow reset --workflow-id {workflow_id} --event-id {event_id} --namespace etter-prod
```

---

## Troubleshooting

### Common Issues

#### 1. Temporal Connection Failed

**Symptom:** `Failed to connect to Temporal server`

**Solutions:**
```bash
# Check if Temporal is running
curl http://localhost:7233/health

# For SSH tunnel
ssh -N -L 5445:qa-temporal-client.qa-internal-draup.technology:31100 \
    ShreyashKumar-Draup@3.128.8.200

# Verify tunnel
nc -zv localhost 5445
```

#### 2. Neo4j Connection Failed

**Symptom:** `Failed to connect to Neo4j`

**Solutions:**
```bash
# Test connection
cypher-shell -a bolt://draup-world-neo4j.draup.technology:7687 \
    -u neo4j -p BK13730kmyDcR5R \
    "RETURN 1"

# Check firewall/network
nc -zv draup-world-neo4j.draup.technology 7687
```

#### 3. Redis Connection Failed

**Symptom:** `Redis connection refused`

**Solutions:**
```bash
# Test Redis connection
redis-cli -h 127.0.0.1 -p 6390 -a 'F6muBM65GqSyvtzBqArK' ping

# Check if Redis is running
systemctl status redis
```

#### 4. Worker Not Processing

**Symptom:** Workflows stay in `queued` state

**Solutions:**
```bash
# Check worker is running
ps aux | grep etter_workflows.worker

# Check worker logs
journalctl -u etter-worker -f

# Verify task queue in Temporal UI
# Should see "etter-workflows" with active pollers
```

#### 5. API Timeout

**Symptom:** API requests timeout

**Solutions:**
```bash
# Increase timeouts in settings
export ETTER_WORKFLOW_API_TIMEOUT=1200  # 20 minutes

# Check workflow API health
curl http://127.0.0.1:8082/health
```

### Debug Mode

Enable debug logging:

```bash
export ETTER_LOG_LEVEL=DEBUG
export ETTER_DEBUG=true
```

### Log Locations

| Service | Log Location |
|---------|--------------|
| API Server | `journalctl -u etter-api` |
| Worker | `journalctl -u etter-worker` |
| Temporal | Temporal UI or Temporal logs |
| Application | stdout/stderr |

---

## Quick Reference

### Environment Variables

```bash
# Minimal configuration
export ETTER_TEMPORAL_HOST=localhost:7233
export ETTER_ENABLE_MOCK_DATA=true

# Production configuration
export ETTER_ENVIRONMENT=production
export ETTER_TEMPORAL_HOST=temporal-server.internal:7233
export ETTER_TEMPORAL_NAMESPACE=etter-prod
export ETTER_NEO4J_URI=bolt://draup-world-neo4j.draup.technology:7687
export ETTER_NEO4J_USER=neo4j
export ETTER_NEO4J_PASSWORD=BK13730kmyDcR5R
export ETTER_REDIS_HOST=127.0.0.1
export ETTER_REDIS_PORT=6390
export ETTER_REDIS_PASSWORD=F6muBM65GqSyvtzBqArK
```

### Common Commands

```bash
# Start everything (development)
temporal server start-dev &
python -m etter_workflows.worker &
uvicorn etter_workflows.api.routes:app --port 8090

# Push a role
curl -X POST "http://localhost:8090/api/v1/pipeline/push?use_mock=true" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "Liberty Mutual", "role_name": "Claims Adjuster"}'

# Check status
curl http://localhost:8090/api/v1/pipeline/status/{workflow_id}

# Health check
curl http://localhost:8090/api/v1/pipeline/health
```

### Ports Summary

| Service | Port | Protocol |
|---------|------|----------|
| API Server | 8090 | HTTP |
| Temporal gRPC | 7233 | gRPC |
| Temporal UI | 8233 | HTTP |
| Neo4j Bolt | 7687 | Bolt |
| Redis | 6390 | Redis |
| Workflow API | 8082 | HTTP |
