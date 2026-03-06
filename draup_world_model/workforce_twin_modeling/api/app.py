"""
FastAPI Application — Workforce Twin Modeling
===============================================
Single entry point. Loads organization data once at startup,
serves all engine functionality via REST API.

Zero imports from parent draup_world_model package.
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is on path for engine imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.loader import load_organization, OrganizationData
from engine.gap_engine import compute_snapshot

# Module-level state
_org: Optional[OrganizationData] = None
_snapshot = None


def get_org() -> OrganizationData:
    """Access loaded organization data."""
    global _org
    if _org is None:
        data_dir = os.path.join(PROJECT_ROOT, "data")
        _org = load_organization(data_dir)
        # Pre-classify tasks for gap analysis
        from engine.gap_engine import classify_task
        for task in _org.tasks.values():
            wl = _org.workloads[task.workload_id]
            role = _org.roles[wl.role_id]
            classify_task(task, _org.tools, role.function)
    return _org


def get_snapshot():
    """Access cached gap analysis snapshot."""
    global _snapshot
    if _snapshot is None:
        _snapshot = compute_snapshot(get_org())
    return _snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup."""
    get_org()
    get_snapshot()
    print(f"  Workforce Twin API ready — {len(get_org().roles)} roles, "
          f"{len(get_org().tasks)} tasks loaded")
    yield


app = FastAPI(
    title="Workforce Twin by Etter",
    description="Enterprise Workforce Digital Twin — Simulation & Analysis API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include route modules
from api.routes import organization, snapshot, cascade, simulate, scenarios, compare

app.include_router(organization.router, prefix="/api")
app.include_router(snapshot.router, prefix="/api")
app.include_router(cascade.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(compare.router, prefix="/api")

# Serve built frontend (production)
UI_BUILD = os.path.join(PROJECT_ROOT, "ui", "dist")
if os.path.isdir(UI_BUILD):
    app.mount("/", StaticFiles(directory=UI_BUILD, html=True), name="ui")


@app.get("/api/health")
async def health():
    org = get_org()
    return {
        "status": "ok",
        "roles": len(org.roles),
        "tasks": len(org.tasks),
        "skills": len(org.skills),
        "tools": len(org.tools),
        "functions": org.functions,
    }
