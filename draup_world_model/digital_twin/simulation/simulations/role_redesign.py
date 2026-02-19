"""
S1: Role Redesign Simulation (P0 - Foundation).

Given a role, applies automation factor to reclassify tasks,
then runs the cascade to produce a future-state role profile.

Outputs:
  - Current vs. future role profile (side-by-side)
  - Freed capacity per job title (level-specific)
  - Skill delta (sunrise/sunset)
  - Role Transformation Index (0-100)
  - Reskilling cost estimate
  - Technology cost estimate (v1.1: added in Phase 3.9)

Trigger: When freed capacity > 40%, role needs complete redesign.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import AUTOMATION_LEVELS, SimulationConfig
from draup_world_model.digital_twin.simulation.cascade_engine import (
    CascadeEngine,
    CLASSIFICATION_AUTOMATION_MAP,
)

logger = logging.getLogger(__name__)


def _advance_automation_level(current_level: str, automation_factor: float) -> str:
    """Advance the automation level based on the automation factor (0-1).

    The factor interpolates between the current level and the maximum
    (ai_only).  ``remaining`` is the number of levels between current
    and ai_only; the factor controls how far along that gap we jump:

        factor=0.25  →  ~25 % of the remaining gap
        factor=0.50  →  ~50 %
        factor=1.00  →  jump all the way to ai_only

    A task already at ai_only is returned unchanged.
    """
    if current_level not in AUTOMATION_LEVELS:
        current_level = "human_led"
    current_idx = AUTOMATION_LEVELS.index(current_level)
    max_idx = len(AUTOMATION_LEVELS) - 1
    remaining = max_idx - current_idx
    if remaining <= 0:
        return current_level
    steps = round(remaining * automation_factor)
    if steps < 1:
        return current_level  # factor too low to advance this task
    new_idx = min(current_idx + steps, max_idx)
    return AUTOMATION_LEVELS[new_idx]


class RoleRedesignSimulation:
    """
    Simulates role redesign by applying automation to tasks.

    Usage:
        sim = RoleRedesignSimulation(cascade_engine)
        result = sim.run(scope_data, automation_factor=0.5)
    """

    def __init__(self, cascade_engine: CascadeEngine):
        self.cascade = cascade_engine

    def run(
        self,
        scope_data: Dict[str, Any],
        automation_factor: float = 0.5,
        target_classifications: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run role redesign simulation.

        Args:
            scope_data: Output from ScopeSelector.select()
            automation_factor: 0-1, how aggressively to automate (0.5 = moderate)
            target_classifications: Only automate tasks with these classifications.
                Defaults to directive and feedback_loop (most automatable in Etter framework).
        """
        if target_classifications is None:
            target_classifications = ["directive", "feedback_loop"]

        logger.info(
            f"Running role redesign: factor={automation_factor}, "
            f"classifications={target_classifications}"
        )

        # Build current state snapshot
        current_state = self._snapshot_current(scope_data)

        # Generate task reclassifications.
        # The automation_factor gates in two ways:
        #   1. Selection: only tasks whose automation_potential exceeds a
        #      threshold are eligible.  A higher factor lowers the bar,
        #      bringing more tasks into scope.
        #   2. Magnitude: _advance_automation_level uses the factor to
        #      decide how many levels to advance (see docstring).
        potential_threshold = (1.0 - automation_factor) * 100  # e.g. factor=0.3 → 70, factor=0.8 → 20

        reclassifications = []
        for task in scope_data["tasks"]:
            if task.get("classification") not in target_classifications:
                continue
            if (task.get("automation_potential") or 0) < potential_threshold:
                continue
            current_level = task.get("automation_level", "human_led")
            new_level = _advance_automation_level(current_level, automation_factor)
            if new_level != current_level:
                reclassifications.append({
                    "task_id": task["id"],
                    "new_automation_level": new_level,
                })

        if not reclassifications:
            logger.info("No tasks eligible for reclassification")
            return {"current": current_state, "future": current_state, "cascade": None}

        # Estimate technology costs for role redesign
        # Automation requires tools — this is the cost of the AI tooling needed
        fin_cfg = self.cascade.config.financial
        technology_costs = None
        if fin_cfg.include_tech_cost_in_role_redesign:
            affected_hc = scope_data["summary"]["total_headcount"]
            technology_costs = self.cascade.financial.estimate_role_redesign_tech_cost(
                affected_hc, self.cascade.timeline_months
            )

        # Run cascade
        cascade_result = self.cascade.run(
            scope_data, reclassifications, technology_costs
        )

        # Build future state
        future_state = self._build_future_state(current_state, cascade_result)

        return {
            "simulation_type": "role_redesign",
            "parameters": {
                "automation_factor": automation_factor,
                "target_classifications": target_classifications,
                "tasks_reclassified": len(reclassifications),
                "include_tech_cost": fin_cfg.include_tech_cost_in_role_redesign,
            },
            "current": current_state,
            "future": future_state,
            "cascade": cascade_result,
            "technology_costs": technology_costs,
            "comparison": self._compare(current_state, future_state, cascade_result),
        }

    def _snapshot_current(self, scope_data: Dict) -> Dict[str, Any]:
        """Take a snapshot of current state metrics."""
        roles = scope_data["roles"]
        titles = scope_data["job_titles"]
        tasks = scope_data["tasks"]

        total_hc = sum(r.get("total_headcount", 0) for r in roles)
        avg_auto = (
            sum(r.get("automation_score", 0) for r in roles) / len(roles)
            if roles else 0
        )

        # Task classification distribution
        class_dist = {}
        for t in tasks:
            cls = t.get("classification", "unknown")
            class_dist[cls] = class_dist.get(cls, 0) + 1

        return {
            "role_count": len(roles),
            "total_headcount": total_hc,
            "avg_automation_score": round(avg_auto, 1),
            "task_count": len(tasks),
            "task_classification_distribution": class_dist,
            "skill_count": len(scope_data["skills"]),
        }

    def _build_future_state(self, current: Dict, cascade: Dict) -> Dict[str, Any]:
        """Build future state from cascade results."""
        workforce = cascade["workforce"]
        return {
            "role_count": current["role_count"],
            "total_headcount": current["total_headcount"] - int(workforce["freed_headcount"]),
            "avg_automation_score": round(
                current["avg_automation_score"] + cascade["summary"]["reduction_pct"] * 0.5, 1
            ),
            "task_count": current["task_count"],
            "freed_headcount": workforce["freed_headcount"],
            "redeployable": workforce["redeployable"],
            "sunrise_skills": len(cascade["skill_shifts"]["sunrise_skills"]),
            "sunset_skills": len(cascade["skill_shifts"]["sunset_skills"]),
        }

    def _compare(self, current: Dict, future: Dict, cascade: Dict) -> Dict[str, Any]:
        """Generate comparison metrics."""
        role_impacts = cascade["role_impacts"]["impacts"]
        max_transform = max((r["transformation_index"] for r in role_impacts), default=0)
        avg_transform = (
            sum(r["transformation_index"] for r in role_impacts) / len(role_impacts)
            if role_impacts else 0
        )

        # Roles needing full redesign (>40% freed capacity)
        redesign_needed = [
            r["role_name"] for r in role_impacts
            if r["freed_capacity_pct"] > 40
        ]

        return {
            "headcount_delta": future["total_headcount"] - current["total_headcount"],
            "headcount_delta_pct": round(
                (future["total_headcount"] - current["total_headcount"]) / current["total_headcount"] * 100, 1
            ) if current["total_headcount"] > 0 else 0,
            "avg_transformation_index": round(avg_transform, 1),
            "max_transformation_index": round(max_transform, 1),
            "roles_needing_redesign": redesign_needed,
            "roles_needing_redesign_count": len(redesign_needed),
            "financial_summary": {
                "gross_savings": cascade["financial"]["gross_savings"],
                "net_impact": cascade["financial"]["net_impact"],
                "roi_pct": cascade["financial"]["roi_pct"],
                "payback_months": cascade["financial"]["payback_months"],
            },
        }
