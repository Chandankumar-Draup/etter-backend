"""
FastAPI Application — Workforce Twin Modeling
===============================================
Provides both:
  1. A combined APIRouter for integration into the outer etter_app
  2. A standalone FastAPI app for independent development

Stocks: Organization data (roles, tasks, skills, tools, human system)
Flows:  Loaded once at startup, served via REST endpoints
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from workforce_twin_modeling.engine.loader import load_organization, OrganizationData
from workforce_twin_modeling.engine.gap_engine import compute_snapshot, classify_task

# Package root — used for data/ and ui/ paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Module-level state
_org: Optional[OrganizationData] = None
_snapshot = None


def get_org() -> OrganizationData:
    """Access loaded organization data."""
    global _org
    if _org is None:
        data_dir = os.path.join(PROJECT_ROOT, "data")
        _org = load_organization(data_dir)
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


# ── Combined Router (for integration into outer app) ──────────────

from workforce_twin_modeling.api.routes import (
    organization, snapshot, cascade, simulate, scenarios, compare,
)

router = APIRouter(prefix="/v1/workforce-twin", tags=["workforce-twin"])

router.include_router(organization.router)
router.include_router(snapshot.router)
router.include_router(cascade.router)
router.include_router(simulate.router)
router.include_router(scenarios.router)
router.include_router(compare.router)


@router.get("/health")
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


# ── Standalone App (for independent development) ─────────────────

def create_app() -> FastAPI:
    """Create standalone FastAPI application for development."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        get_org()
        get_snapshot()
        print(f"  Workforce Twin API ready — {len(get_org().roles)} roles, "
              f"{len(get_org().tasks)} tasks loaded")
        yield

    standalone = FastAPI(
        title="Workforce Twin by Etter",
        description="Enterprise Workforce Digital Twin — Simulation & Analysis API",
        version="1.0.0",
        lifespan=lifespan,
    )

    standalone.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In standalone mode, routes are at /api/* (no /v1/workforce-twin prefix)
    standalone.include_router(organization.router, prefix="/api")
    standalone.include_router(snapshot.router, prefix="/api")
    standalone.include_router(cascade.router, prefix="/api")
    standalone.include_router(simulate.router, prefix="/api")
    standalone.include_router(scenarios.router, prefix="/api")
    standalone.include_router(compare.router, prefix="/api")

    @standalone.get("/api/health")
    async def standalone_health():
        return await health()

    # Serve built frontend (production)
    ui_build = os.path.join(PROJECT_ROOT, "ui", "dist")
    if os.path.isdir(ui_build):
        standalone.mount("/", StaticFiles(directory=ui_build, html=True), name="ui")

    return standalone


def get_app() -> FastAPI:
    """Get or create the standalone FastAPI app instance."""
    global _standalone_app
    try:
        return _standalone_app
    except NameError:
        pass
    _standalone_app = create_app()
    return _standalone_app
