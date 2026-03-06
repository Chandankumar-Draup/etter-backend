"""
S4: Skills Strategy Simulation (P0 - Foundation).

Analyzes the skills landscape after a simulation to identify:
  - Sunrise skills (emerging, growing demand)
  - Sunset skills (declining, reduced need)
  - Skill concentration risk (skills held by very few people)
  - Reskilling cost and timeline
  - Build vs. buy recommendation

This simulation always runs AFTER a cascade (it reads cascade results).
It's the fourth-order effect made actionable.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import FinancialConfig

logger = logging.getLogger(__name__)


class SkillsStrategySimulation:
    """
    Analyzes skills impact from cascade results and generates strategy.

    Usage:
        sim = SkillsStrategySimulation()
        result = sim.run(scope_data, cascade_result)
    """

    def __init__(self, financial_config: Optional[FinancialConfig] = None):
        self.cfg = financial_config or FinancialConfig()

    def run(
        self,
        scope_data: Dict[str, Any],
        cascade_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run skills strategy simulation.

        Args:
            scope_data: Output from ScopeSelector.select()
            cascade_result: Output from CascadeEngine.run()
        """
        logger.info("Running skills strategy simulation")

        skills = scope_data["skills"]
        titles = scope_data["job_titles"]
        skill_shifts = cascade_result.get("skill_shifts", {})
        role_impacts = cascade_result.get("role_impacts", {}).get("impacts", [])

        # Skill demand analysis
        demand = self._analyze_demand(skills, skill_shifts)

        # Concentration risk
        concentration = self._analyze_concentration(skills, scope_data["roles"])

        # Reskilling plan
        reskilling = self._build_reskilling_plan(
            skill_shifts.get("sunrise_skills", []),
            titles,
            role_impacts,
        )

        # Build vs buy
        build_buy = self._build_vs_buy(demand, reskilling)

        return {
            "simulation_type": "skills_strategy",
            "demand_analysis": demand,
            "concentration_risk": concentration,
            "reskilling_plan": reskilling,
            "build_vs_buy": build_buy,
            "summary": {
                "sunrise_count": len(demand["sunrise"]),
                "sunset_count": len(demand["sunset"]),
                "stable_count": len(demand["stable"]),
                "high_risk_skills": concentration["high_risk_count"],
                "total_reskilling_cost": reskilling["total_cost"],
                "avg_reskilling_months": reskilling["avg_months"],
            },
        }

    def _analyze_demand(
        self,
        skills: List[Dict],
        skill_shifts: Dict,
    ) -> Dict[str, Any]:
        """Categorize skills by future demand."""
        sunrise = []
        sunset = []
        stable = []

        # From cascade skill shifts
        sunrise_names = {s["name"] for s in skill_shifts.get("sunrise_skills", [])}
        sunset_names = {s["name"] for s in skill_shifts.get("sunset_skills", [])}

        for skill in skills:
            name = skill.get("name", "")
            lifecycle = skill.get("lifecycle_status", "stable")

            if name in sunrise_names or lifecycle == "emerging":
                sunrise.append({
                    "name": name,
                    "category": skill.get("category", ""),
                    "trend": "rising",
                    "priority": "high" if name in sunrise_names else "medium",
                })
            elif name in sunset_names or lifecycle == "declining":
                sunset.append({
                    "name": name,
                    "category": skill.get("category", ""),
                    "trend": "falling",
                    "action": "phase_out",
                })
            else:
                stable.append({
                    "name": name,
                    "category": skill.get("category", ""),
                    "trend": "stable",
                })

        # Add cascade-identified sunrise skills not in catalog
        for ss in skill_shifts.get("sunrise_skills", []):
            if ss["name"] not in {s["name"] for s in sunrise}:
                sunrise.append({
                    "name": ss["name"],
                    "category": "digital",
                    "trend": "rising",
                    "priority": "high",
                })

        return {"sunrise": sunrise, "sunset": sunset, "stable": stable}

    def _analyze_concentration(
        self,
        skills: List[Dict],
        roles: List[Dict],
    ) -> Dict[str, Any]:
        """Identify skills concentrated in very few roles.

        Threshold is normalized by scope size: max(2, 15% of roles).
        In a 2-role scope, threshold = 2 (avoids flagging everything).
        In a 20-role scope, threshold = 3 (skills in <=3 roles are risky).
        """
        total_roles = len(roles)
        threshold = max(2, int(total_roles * 0.15))

        # Build skill -> role count (from role skill_ids)
        skill_role_count = {}
        for role in roles:
            for sid in role.get("skill_ids", []):
                skill_role_count[sid] = skill_role_count.get(sid, 0) + 1

        high_risk = []
        for skill in skills:
            sid = skill.get("id", "")
            count = skill_role_count.get(sid, 0)
            if count <= threshold and count > 0:
                high_risk.append({
                    "skill_name": skill.get("name", ""),
                    "role_count": count,
                    "risk": "critical" if count == 1 else "high",
                    "recommendation": "Cross-train immediately",
                })

        return {
            "total_roles_in_scope": total_roles,
            "concentration_threshold": threshold,
            "high_risk_count": len(high_risk),
            "high_risk_skills": high_risk,
        }

    def _build_reskilling_plan(
        self,
        sunrise_skills: List[Dict],
        titles: List[Dict],
        role_impacts: List[Dict],
    ) -> Dict[str, Any]:
        """Build a reskilling plan with band-weighted costs and timelines.

        Applies band_cost_multiplier so senior/leadership reskilling
        is costed higher than entry-level (reflects training complexity).
        """
        if not sunrise_skills:
            return {"skills": [], "total_cost": 0, "avg_months": 0, "headcount_impacted": 0}

        reskilling_timeline = self.cfg.reskilling_timeline_months
        band_cost_mult = self.cfg.band_cost_multiplier
        cost_per_skill = self.cfg.reskilling_cost_per_skill_per_person

        # Group affected headcount by career band (~30% need reskilling)
        band_headcount: Dict[str, int] = {}
        for impact in role_impacts:
            for ti in impact.get("title_impacts", []):
                if ti.get("freed_capacity_pct", 0) > 10:
                    band = ti.get("career_band", "mid")
                    band_headcount[band] = (
                        band_headcount.get(band, 0) + ti.get("headcount", 0)
                    )

        band_reskill: Dict[str, int] = {}
        for band, hc in band_headcount.items():
            band_reskill[band] = max(1, int(hc * 0.3))
        reskill_hc = sum(band_reskill.values()) or 1

        skill_plans = []
        total_cost = 0
        total_months = 0

        for skill in sunrise_skills:
            category = skill.get("category", "digital")
            months = reskilling_timeline.get(category, 4)
            # Band-weighted cost: each band's headcount x base cost x multiplier
            cost = sum(
                bhc * cost_per_skill * band_cost_mult.get(band, 1.0)
                for band, bhc in band_reskill.items()
            )

            skill_plans.append({
                "skill_name": skill.get("name", ""),
                "category": category,
                "timeline_months": months,
                "headcount": reskill_hc,
                "cost": round(cost, 2),
            })
            total_cost += cost
            total_months += months

        avg_months = total_months / len(skill_plans) if skill_plans else 0

        return {
            "skills": skill_plans,
            "total_cost": round(total_cost, 2),
            "avg_months": round(avg_months, 1),
            "headcount_impacted": reskill_hc,
            "band_breakdown": {
                band: {"headcount": hc, "multiplier": band_cost_mult.get(band, 1.0)}
                for band, hc in band_reskill.items()
            },
        }

    @staticmethod
    def _build_vs_buy(demand: Dict, reskilling: Dict) -> Dict[str, Any]:
        """Recommend build (train) vs. buy (hire) for each sunrise skill."""
        recommendations = []

        for skill in demand["sunrise"]:
            cost = reskilling["total_cost"] / max(len(demand["sunrise"]), 1)
            months = reskilling["avg_months"]

            # Heuristic: if fast to train and moderate cost -> build
            if months <= 4 and cost < 100000:
                action = "build"
                reasoning = "Fast reskilling timeline and manageable cost"
            elif skill.get("priority") == "high":
                action = "buy_and_build"
                reasoning = "High priority - hire externally while training internally"
            else:
                action = "build"
                reasoning = "Standard reskilling path recommended"

            recommendations.append({
                "skill": skill["name"],
                "action": action,
                "reasoning": reasoning,
            })

        return {"recommendations": recommendations}
