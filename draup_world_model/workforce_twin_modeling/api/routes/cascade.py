"""9-Step Cascade endpoints."""
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.app import get_org
from api.serializers import serialize_cascade

from engine.cascade import Stimulus, run_cascade

router = APIRouter(tags=["cascade"])


class CascadeRequest(BaseModel):
    """Stimulus configuration for a cascade run."""
    stimulus_name: str = "Technology Injection"
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []
    target_roles: List[str] = []
    policy: str = "moderate_reduction"
    absorption_factor: float = 0.35
    alpha: float = 1.0
    training_cost_per_person: float = 2000


@router.post("/cascade")
async def run_cascade_endpoint(req: CascadeRequest):
    """Run the 9-step cascade for a given stimulus configuration."""
    org = get_org()

    target_fns = req.target_functions if req.target_functions else org.functions
    stimulus = Stimulus(
        name=req.stimulus_name,
        stimulus_type="technology_injection",
        tools=req.tools,
        target_scope="function" if len(target_fns) < len(org.functions) else "ALL",
        target_functions=target_fns,
        target_roles=req.target_roles,
        policy=req.policy,
        absorption_factor=req.absorption_factor,
        alpha=req.alpha,
        training_cost_per_person=req.training_cost_per_person,
    )

    result = run_cascade(stimulus, org)
    return serialize_cascade(result)
