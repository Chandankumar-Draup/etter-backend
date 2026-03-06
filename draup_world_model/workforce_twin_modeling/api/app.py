"""
FastAPI Application — Workforce Twin Modeling
===============================================
Provides both:
  1. A combined APIRouter for integration into the outer etter_app
  2. A standalone FastAPI app for independent development

Stocks: Organization data (roles, tasks, skills, tools, human system)
Flows:  Loaded once at startup per company, served via REST endpoints
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.auth import verify_token

from workforce_twin_modeling.engine.loader import load_organization, OrganizationData
from workforce_twin_modeling.engine.gap_engine import compute_snapshot, classify_task

logger = logging.getLogger("workforce_twin")

# Package root — used for data/ and ui/ paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")

# Skip auth in local dev: set WORKFORCE_TWIN_SKIP_AUTH=1
_SKIP_AUTH = os.environ.get("WORKFORCE_TWIN_SKIP_AUTH", "").strip() in ("1", "true")
# Default company for local dev: set WORKFORCE_TWIN_DEFAULT_COMPANY
_DEFAULT_COMPANY = os.environ.get("WORKFORCE_TWIN_DEFAULT_COMPANY", "NTT Data")

if _SKIP_AUTH:
    logger.info("Auth SKIPPED (WORKFORCE_TWIN_SKIP_AUTH=1)")
    logger.info(f"Default company: {_DEFAULT_COMPANY}")

# ── Per-company cache ──────────────────────────────────────────────

_org_cache: Dict[str, OrganizationData] = {}
_snapshot_cache: Dict[str, object] = {}


def _available_companies() -> list:
    """List company directories under data/."""
    if not os.path.isdir(DATA_ROOT):
        return []
    return [d for d in os.listdir(DATA_ROOT) if os.path.isdir(os.path.join(DATA_ROOT, d))]


def _resolve_data_dir(company: str) -> str:
    """
    Find the data directory for a company.

    Exact match first, then case-insensitive fallback. This prevents 404s
    when the auth system returns a slightly different casing or name than
    the folder on disk (e.g. "NTT Data" vs "NTT data").
    """
    exact = os.path.join(DATA_ROOT, company)
    if os.path.isdir(exact):
        return exact

    # Case-insensitive fallback
    available = _available_companies()
    lower = company.lower()
    for name in available:
        if name.lower() == lower:
            logger.info(f"Company '{company}' matched case-insensitively to '{name}'")
            return os.path.join(DATA_ROOT, name)

    # If only one company exists, use it (single-tenant deployment)
    if len(available) == 1:
        logger.warning(
            f"Company '{company}' not found, but only one dataset exists: "
            f"'{available[0]}'. Using it as fallback."
        )
        return os.path.join(DATA_ROOT, available[0])

    return ""


def get_org(company: str) -> OrganizationData:
    """Load and cache organization data for a company."""
    if company in _org_cache:
        return _org_cache[company]

    data_dir = _resolve_data_dir(company)
    if not data_dir:
        available = _available_companies()
        logger.error(f"Company data not found: '{company}'. Available: {available}")
        raise HTTPException(
            status_code=404,
            detail=f"No data for company '{company}'. Available: {available}",
        )

    logger.info(f"Loading data for company: {company} from {data_dir}")
    org = load_organization(data_dir)
    for task in org.tasks.values():
        wl = org.workloads[task.workload_id]
        role = org.roles[wl.role_id]
        classify_task(task, org.tools, role.function)

    _org_cache[company] = org
    logger.info(
        f"Loaded company '{company}': {len(org.roles)} roles, "
        f"{len(org.tasks)} tasks, {len(org.tools)} tools"
    )
    return org


def get_snapshot(company: str):
    """Compute and cache gap analysis snapshot for a company."""
    if company in _snapshot_cache:
        return _snapshot_cache[company]

    snap = compute_snapshot(get_org(company))
    _snapshot_cache[company] = snap
    logger.info(f"Computed snapshot for company: {company}")
    return snap


# ── Company resolution dependency ──────────────────────────────────

async def _resolve_company_from_token(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Extract company_name from the auth token via verify_token.
    The verify_token dependency hits the Draup API and returns user details
    including company info.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # verify_token is called by the router dependency already,
    # but we need the user data here to get company_name.
    # Re-use the same auth mechanism.
    from fastapi.security import HTTPAuthorizationCredentials
    token = authorization.replace("Bearer ", "")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    try:
        result = verify_token(creds)
    except HTTPException:
        raise

    if not result or not result.data:
        raise HTTPException(status_code=401, detail="Token validation failed")

    company_name = None
    if isinstance(result.data, dict):
        company_name = result.data.get("company_name")
    elif hasattr(result.data, "company_name"):
        company_name = result.data.company_name

    if not company_name:
        raise HTTPException(status_code=400, detail="Could not extract company_name from token")

    logger.info(f"Resolved company from token: {company_name}")
    return company_name


async def resolve_company(
    company: Optional[str] = Query(None, description="Company name (for local dev)"),
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Resolve company name. Priority:
      1. Auth token (prod/QA) — extracts company_name from verify_token
      2. ?company= query param (local dev)
      3. WORKFORCE_TWIN_DEFAULT_COMPANY env var fallback
    """
    # If auth is enabled and token is present, extract company from token
    if not _SKIP_AUTH and authorization:
        return await _resolve_company_from_token(authorization)

    # Local dev: use query param or default
    resolved = company or _DEFAULT_COMPANY
    logger.info(f"Using company: {resolved} (query_param={company}, default={_DEFAULT_COMPANY})")
    return resolved


# ── Combined Router (for integration into outer app) ──────────────

from workforce_twin_modeling.api.routes import (
    organization, snapshot, cascade, simulate, scenarios, compare,
)

_auth_deps = [] if _SKIP_AUTH else [Depends(verify_token)]

router = APIRouter(
    prefix="/v1/workforce-twin",
    tags=["workforce-twin"],
    dependencies=_auth_deps,
)

router.include_router(organization.router)
router.include_router(snapshot.router)
router.include_router(cascade.router)
router.include_router(simulate.router)
router.include_router(scenarios.router)
router.include_router(compare.router)


@router.get("/health")
async def health(company: str = Depends(resolve_company)):
    org = get_org(company)
    return {
        "status": "ok",
        "company": company,
        "roles": len(org.roles),
        "tasks": len(org.tasks),
        "skills": len(org.skills),
        "tools": len(org.tools),
        "functions": org.functions,
    }


@router.get("/companies")
async def list_companies():
    """List available company datasets."""
    companies = _available_companies()
    return {"companies": companies}


# ── Standalone App (for independent development) ─────────────────

def create_app() -> FastAPI:
    """Create standalone FastAPI application for development."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        companies = _available_companies()
        logger.info(f"Available companies: {companies}")
        if _DEFAULT_COMPANY in companies:
            org = get_org(_DEFAULT_COMPANY)
            get_snapshot(_DEFAULT_COMPANY)
            logger.info(
                f"Workforce Twin API ready — {_DEFAULT_COMPANY}: "
                f"{len(org.roles)} roles, {len(org.tasks)} tasks"
            )
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
