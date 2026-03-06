"""Static gap analysis (snapshot) endpoints."""
from fastapi import APIRouter, Depends

from workforce_twin_modeling.api.app import get_snapshot, resolve_company
from workforce_twin_modeling.api.serializers import serialize_org_gap, serialize_function_gap, serialize_role_gap

router = APIRouter(tags=["snapshot"])


@router.get("/snapshot")
async def get_snapshot_full(company: str = Depends(resolve_company)):
    """Full org-level gap analysis — three-layer classification."""
    return serialize_org_gap(get_snapshot(company))


@router.get("/snapshot/function/{function_name}")
async def get_function_snapshot(function_name: str, company: str = Depends(resolve_company)):
    """Gap analysis for a specific function."""
    snap = get_snapshot(company)
    for fg in snap.functions:
        if fg.function == function_name:
            return serialize_function_gap(fg)
    return {"error": f"Function '{function_name}' not found"}


@router.get("/snapshot/role/{role_id}")
async def get_role_snapshot(role_id: str, company: str = Depends(resolve_company)):
    """Gap analysis for a specific role."""
    snap = get_snapshot(company)
    for fg in snap.functions:
        for rg in fg.roles:
            if rg.role_id == role_id:
                return serialize_role_gap(rg)
    return {"error": f"Role '{role_id}' not found"}


@router.get("/snapshot/opportunities")
async def get_opportunities(company: str = Depends(resolve_company)):
    """Top automation opportunities ranked by savings."""
    snap = get_snapshot(company)
    return {
        "by_adoption_gap": snap.top_roles_by_adoption_gap,
        "by_total_gap": snap.top_roles_by_total_gap,
        "by_savings": snap.top_roles_by_savings,
    }
