"""Scenario catalog endpoints."""
import os

from fastapi import APIRouter, Depends

from workforce_twin_modeling.api.app import get_org, resolve_company, PROJECT_ROOT
from workforce_twin_modeling.api.serializers import _r

from workforce_twin_modeling.stages.scenario_executor import load_catalog, run_scenario, run_batch

router = APIRouter(tags=["scenarios"])

CATALOG_PATH = os.path.join(PROJECT_ROOT, "scenario_catalog", "simulation_scenarios_extended.csv")


@router.get("/scenarios/catalog")
async def get_catalog():
    """Load the scenario catalog (all rows from CSV)."""
    if not os.path.exists(CATALOG_PATH):
        return {"error": "Scenario catalog not found", "path": CATALOG_PATH}
    rows = load_catalog(CATALOG_PATH)
    return {
        "total": len(rows),
        "scenarios": rows,
    }


@router.post("/scenarios/run")
async def run_scenarios(
    scenario_ids: list[str] | None = None,
    families: list[str] | None = None,
    company: str = Depends(resolve_company),
):
    """Run a batch of scenarios from the catalog."""
    if not os.path.exists(CATALOG_PATH):
        return {"error": "Scenario catalog not found"}

    org = get_org(company)
    results = run_batch(CATALOG_PATH, org, scenario_ids=scenario_ids, families=families)

    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.error is None),
        "failed": sum(1 for r in results if r.error is not None),
        "results": [
            {
                "scenario_id": r.scenario_id,
                "scenario_name": r.scenario_name,
                "family": r.family,
                "direction": r.direction,
                "status": "pass" if r.error is None else "fail",
                "error": r.error,
                "hc_reduced": r.hc_reduced,
                "final_hc": r.final_hc,
                "net_savings": _r(r.net_savings, 0),
                "total_investment": _r(r.total_investment, 0),
                "total_savings": _r(r.total_savings, 0),
                "payback_month": r.payback_month,
                "final_proficiency": _r(r.final_proficiency, 1),
                "final_trust": _r(r.final_trust, 1),
            }
            for r in results
        ],
    }


@router.post("/scenarios/run-single/{scenario_id}")
async def run_single_scenario(scenario_id: str, trace: bool = False, company: str = Depends(resolve_company)):
    """Run a single scenario from the catalog with optional trace."""
    if not os.path.exists(CATALOG_PATH):
        return {"error": "Scenario catalog not found"}

    org = get_org(company)
    rows = load_catalog(CATALOG_PATH)
    row = next((r for r in rows if r["scenario_id"] == scenario_id), None)
    if not row:
        return {"error": f"Scenario '{scenario_id}' not found in catalog"}

    from api.serializers import serialize_fb_result
    result = run_scenario(row, org, trace=trace)

    if result.error:
        return {"error": result.error, "scenario_id": scenario_id}

    return {
        "scenario_id": result.scenario_id,
        "scenario_name": result.scenario_name,
        "family": result.family,
        "result": serialize_fb_result(result.result) if result.result else None,
    }
