"""
Financial projection module.

Computes per-JobTitle financial impact from simulation results.
Formula: savings = salary × headcount × freed_capacity_pct × (timeline_months / 12)

Also computes: technology costs, reskilling investment, change management,
severance, and optional J-curve productivity dip.

Design insight: Financial projections are sixth-order effects in the cascade.
They are derived, not assumed. This makes them trustworthy.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import FinancialConfig

logger = logging.getLogger(__name__)


class FinancialProjection:
    """Computes financial impact from simulation cascade results."""

    def __init__(
        self,
        timeline_months: int = 36,
        financial_config: Optional[FinancialConfig] = None,
    ):
        self.timeline_months = timeline_months
        self.cfg = financial_config or FinancialConfig()

    def compute(
        self,
        title_impacts: List[Dict[str, Any]],
        technology_costs: Dict[str, Any] = None,
        reskilling_data: Dict[str, Any] = None,
        redeployability_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute full financial projection.

        Args:
            title_impacts: List of per-title impact dicts with:
                - name, avg_salary, headcount, freed_capacity_pct
            technology_costs: Optional tech cost data
            reskilling_data: Optional reskilling cost data
            redeployability_pct: Fraction of freed workers redeployable (from CascadeConfig).
                Falls back to technology_costs dict, then 60.0 default.
        """
        # Per-title savings
        gross_savings = 0.0
        title_details = []
        total_freed_hc = 0.0
        for ti in title_impacts:
            salary = ti.get("avg_salary", 0)
            hc = ti.get("headcount", 0)
            freed = ti.get("freed_capacity_pct", 0) / 100.0
            title_savings = salary * hc * freed * (self.timeline_months / 12)
            gross_savings += title_savings
            total_freed_hc += hc * freed
            title_details.append({
                "title": ti.get("name", "Unknown"),
                "headcount": hc,
                "avg_salary": salary,
                "freed_capacity_pct": ti.get("freed_capacity_pct", 0),
                "savings": round(title_savings, 2),
            })

        # Technology costs
        tech_licensing = 0.0
        implementation_cost = 0.0
        if technology_costs:
            tech_licensing = technology_costs.get("total_licensing", 0)
            implementation_cost = technology_costs.get("implementation", 0)

        # Reskilling costs
        reskilling_cost = 0.0
        if reskilling_data:
            reskilling_cost = reskilling_data.get("total_cost", 0)

        # Change management cost (fraction of gross savings)
        change_mgmt_cost = round(
            gross_savings * self.cfg.change_management_pct / 100.0, 2
        )

        # Severance cost (non-redeployable freed workers × avg salary × months)
        # Priority: explicit param > technology_costs dict > 60% default
        if redeployability_pct is not None:
            redeployable_pct = redeployability_pct
        elif technology_costs and "redeployability_pct" in technology_costs:
            redeployable_pct = technology_costs["redeployability_pct"]
        else:
            redeployable_pct = 60.0
        non_redeployable_hc = total_freed_hc * (1 - redeployable_pct / 100.0)
        avg_salary = 0
        total_hc = sum(ti.get("headcount", 0) for ti in title_impacts)
        if total_hc > 0:
            avg_salary = sum(
                ti.get("avg_salary", 0) * ti.get("headcount", 0)
                for ti in title_impacts
            ) / total_hc
        severance_cost = round(
            non_redeployable_hc * avg_salary * self.cfg.severance_months / 12.0, 2
        )

        # J-curve productivity dip (temporary cost during transition)
        j_curve_cost = 0.0
        if self.cfg.j_curve_enabled:
            dip_months = min(self.cfg.j_curve_duration_months, self.timeline_months)
            # Cost = total affected headcount × avg salary × dip% × dip months / 12
            j_curve_cost = round(
                total_hc * avg_salary * (self.cfg.j_curve_dip_pct / 100.0)
                * dip_months / 12.0, 2
            )

        total_cost = (
            tech_licensing + implementation_cost + reskilling_cost
            + change_mgmt_cost + severance_cost + j_curve_cost
        )
        net_impact = gross_savings - total_cost
        roi_pct = (net_impact / total_cost * 100) if total_cost > 0 else (
            9999.0 if gross_savings > 0 else 0)
        monthly_savings = gross_savings / self.timeline_months if self.timeline_months > 0 else 0
        payback_months = int(total_cost / monthly_savings) if monthly_savings > 0 else 0

        projection = {
            "timeline_months": self.timeline_months,
            "gross_savings": round(gross_savings, 2),
            "technology_licensing": round(tech_licensing, 2),
            "implementation_cost": round(implementation_cost, 2),
            "reskilling_cost": round(reskilling_cost, 2),
            "change_management_cost": round(change_mgmt_cost, 2),
            "severance_cost": round(severance_cost, 2),
            "j_curve_cost": round(j_curve_cost, 2),
            "total_cost": round(total_cost, 2),
            "net_impact": round(net_impact, 2),
            "roi_pct": round(roi_pct, 1),
            "payback_months": payback_months,
            "title_details": title_details,
        }

        logger.info(
            f"Financial projection: gross_savings=${gross_savings:,.0f}, "
            f"net=${net_impact:,.0f}, ROI={roi_pct:.1f}%"
        )
        return projection

    def compute_tech_costs(
        self,
        tech_name: str,
        license_tier: str,
        headcount: int,
        timeline_months: int,
        monthly_per_user_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute technology licensing and implementation costs."""
        monthly_per_user = monthly_per_user_override or self.cfg.license_cost_tiers.get(
            license_tier, 30.0
        )
        total_licensing = monthly_per_user * headcount * timeline_months
        implementation = total_licensing * self.cfg.implementation_cost_factor

        return {
            "technology": tech_name,
            "monthly_per_user": monthly_per_user,
            "headcount": headcount,
            "total_licensing": round(total_licensing, 2),
            "implementation": round(implementation, 2),
            "total": round(total_licensing + implementation, 2),
        }

    def compute_reskilling_costs(
        self,
        skill_gaps: List[Dict],
        headcount_needing_reskill: int,
    ) -> Dict[str, Any]:
        """Compute reskilling investment."""
        num_skills = len(skill_gaps)
        cost_per = self.cfg.reskilling_cost_per_skill_per_person
        total = num_skills * headcount_needing_reskill * cost_per

        return {
            "skills_to_learn": num_skills,
            "headcount_reskilled": headcount_needing_reskill,
            "cost_per_skill_per_person": cost_per,
            "total_cost": round(total, 2),
        }

    def estimate_role_redesign_tech_cost(
        self,
        affected_headcount: int,
        timeline_months: int,
    ) -> Dict[str, Any]:
        """Estimate technology cost for role redesign when no specific tech is given.

        Uses a default per-user-month rate as a reasonable proxy for the
        mix of AI tools needed to achieve the automation targets.
        """
        rate = self.cfg.default_tech_cost_per_user_month
        total_licensing = rate * affected_headcount * timeline_months
        implementation = total_licensing * self.cfg.implementation_cost_factor

        return {
            "technology": "Estimated AI tooling (blended rate)",
            "monthly_per_user": rate,
            "headcount": affected_headcount,
            "total_licensing": round(total_licensing, 2),
            "implementation": round(implementation, 2),
            "total": round(total_licensing + implementation, 2),
        }
