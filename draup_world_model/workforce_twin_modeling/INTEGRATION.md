# Workforce Twin Modeling — Integration Guide

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│  etter_app (FastAPI)  —  settings/server.py             │
│  root_path: /api     port: 7071                         │
│                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │ etter_api     │  │ pipeline      │  │ workforce   │ │
│  │ auth          │  │ (etter-       │  │ twin        │ │
│  │ chatbot       │  │  workflows)   │  │ (this pkg)  │ │
│  │ extraction    │  │ /v1/pipeline  │  │ /v1/        │ │
│  │ gateway ...   │  │               │  │ workforce-  │ │
│  │               │  │               │  │ twin        │ │
│  └───────────────┘  └───────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install the package

```bash
pip install -e ./draup_world_model
```

Or via `requirements.txt` (already added):
```
-e ./draup_world_model
```

### 2. Run the full etter_app (integrated mode)

```bash
python uvicorn_config.py
```

Workforce Twin endpoints are available at:
```
/api/v1/workforce-twin/health
/api/v1/workforce-twin/org
/api/v1/workforce-twin/snapshot
/api/v1/workforce-twin/cascade
/api/v1/workforce-twin/simulate
/api/v1/workforce-twin/scenarios/catalog
/api/v1/workforce-twin/compare
```

### 3. Run standalone (for development)

```bash
cd draup_world_model/workforce_twin_modeling
python run_ui.py
```

Standalone endpoints at `http://localhost:8000/api/*` (same routes, no `/v1/workforce-twin` prefix).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/workforce-twin/health` | Health check |
| GET | `/v1/workforce-twin/org` | Full organization data |
| GET | `/v1/workforce-twin/org/hierarchy` | Org tree structure |
| GET | `/v1/workforce-twin/org/functions` | Function summary |
| GET | `/v1/workforce-twin/org/roles/{role_id}` | Role detail |
| GET | `/v1/workforce-twin/org/tools` | Technology tools |
| GET | `/v1/workforce-twin/snapshot` | Full gap analysis |
| GET | `/v1/workforce-twin/snapshot/function/{name}` | Function gap analysis |
| GET | `/v1/workforce-twin/snapshot/role/{role_id}` | Role gap analysis |
| GET | `/v1/workforce-twin/snapshot/opportunities` | Top automation opportunities |
| POST | `/v1/workforce-twin/cascade` | Run 9-step cascade |
| POST | `/v1/workforce-twin/simulate` | Run time-series simulation |
| POST | `/v1/workforce-twin/simulate/preset/{id}` | Run preset scenario (P1-P5) |
| GET | `/v1/workforce-twin/simulate/presets` | List preset scenarios |
| GET | `/v1/workforce-twin/scenarios/catalog` | Load scenario catalog |
| POST | `/v1/workforce-twin/scenarios/run` | Run batch scenarios |
| POST | `/v1/workforce-twin/scenarios/run-single/{id}` | Run single scenario |
| POST | `/v1/workforce-twin/compare` | Compare multiple scenarios |

## Architecture (Systems Thinking)

**Stocks**: Roles, Tasks, Skills, Tools, Headcount, Financial Position, Human System State
**Flows**: Cascade propagation, adoption S-curves, feedback loops (B1-B4 balancing, R1-R4 reinforcing)
**Delays**: Skill valley, trust building, HC decision lag, political capital accumulation

**Package boundary**: All engine, models, and data stay inside `workforce_twin_modeling/`. The outer app only imports the router.
