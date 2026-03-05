"""Organization data endpoints."""
from fastapi import APIRouter

from api.app import get_org
from api.serializers import serialize_org, serialize_org_hierarchy, serialize_role, serialize_role_gap
from api.app import get_snapshot

router = APIRouter(tags=["organization"])


@router.get("/org")
async def get_organization():
    """Full organization data — roles, workloads, tasks, skills, tools, human system."""
    return serialize_org(get_org())


@router.get("/org/hierarchy")
async def get_hierarchy():
    """Org tree: function → sub_function → jfg → role."""
    return serialize_org_hierarchy(get_org())


@router.get("/org/functions")
async def get_functions():
    """List of function names."""
    org = get_org()
    result = []
    for fn in org.functions:
        role_ids = org.roles_by_function.get(fn, [])
        hc = sum(org.roles[rid].headcount for rid in role_ids)
        hs = org.human_system.get(fn)
        result.append({
            "name": fn,
            "role_count": len(role_ids),
            "headcount": hc,
            "ai_proficiency": hs.ai_proficiency if hs else 0,
            "change_readiness": hs.change_readiness if hs else 0,
            "trust_level": hs.trust_level if hs else 0,
        })
    return result


@router.get("/org/roles/{role_id}")
async def get_role_detail(role_id: str):
    """Detailed role info with workloads, tasks, skills."""
    org = get_org()
    role = org.roles.get(role_id)
    if not role:
        return {"error": f"Role {role_id} not found"}

    data = serialize_role(role)

    # Add workloads
    wl_ids = org.workloads_by_role.get(role_id, [])
    workloads = []
    for wl_id in wl_ids:
        wl = org.workloads[wl_id]
        task_ids = org.tasks_by_workload.get(wl_id, [])
        skill_ids = org.skills_by_workload.get(wl_id, [])
        workloads.append({
            "workload_id": wl.workload_id,
            "workload_name": wl.workload_name,
            "time_pct": wl.time_pct,
            "category_distribution": {
                "directive": wl.directive_pct,
                "feedback_loop": wl.feedback_loop_pct,
                "task_iteration": wl.task_iteration_pct,
                "learning": wl.learning_pct,
                "validation": wl.validation_pct,
                "negligibility": wl.negligibility_pct,
            },
            "tasks": [
                {
                    "task_id": org.tasks[tid].task_id,
                    "task_name": org.tasks[tid].task_name,
                    "category": org.tasks[tid].category,
                    "effort_hours": org.tasks[tid].effort_hours_month,
                    "automatable_by": org.tasks[tid].automatable_by_tool,
                    "compliance": org.tasks[tid].compliance_mandated_human,
                    "l1": org.tasks[tid].l1_etter_potential,
                    "l2": org.tasks[tid].l2_achievable,
                    "l3": org.tasks[tid].l3_realized,
                }
                for tid in task_ids
            ],
            "skills": [
                {
                    "skill_id": org.skills[sid].skill_id,
                    "skill_name": org.skills[sid].skill_name,
                    "skill_type": org.skills[sid].skill_type,
                    "proficiency_required": org.skills[sid].proficiency_required,
                    "is_sunrise": org.skills[sid].is_sunrise,
                    "is_sunset": org.skills[sid].is_sunset,
                }
                for sid in skill_ids
            ],
        })

    data["workloads"] = workloads
    return data


@router.get("/org/tools")
async def get_tools():
    """Available technology tools."""
    org = get_org()
    return [
        {
            "tool_id": t.tool_id,
            "tool_name": t.tool_name,
            "deployed_to_functions": t.deployed_to_functions,
            "task_categories_addressed": t.task_categories_addressed,
            "license_cost": t.license_cost_per_user_month,
            "current_adoption_pct": t.current_adoption_pct,
        }
        for t in org.tools.values()
    ]
