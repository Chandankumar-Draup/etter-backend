"""
Phase 3.12: Time-Stepped Simulation Engine (v2).

Replaces the single-shot cascade with a monthly time-stepping loop.
Each month evolves 5 stock types and computes feedback effects:

  Stocks:
    1. Workforce    — headcount, separations, redeployment, hiring
    2. Adoption     — Bass diffusion S-curve for technology uptake
    3. Skills       — proficiency growth, decay, gaps
    4. Financial    — monthly savings, costs, cumulative NPV
    5. Human Factors — resistance, morale, proficiency, culture

  Feedback Loops:
    R1: Productivity flywheel  (adoption → savings → budget → more adoption)
    R2: Capability compounding (adoption → proficiency → better adoption)
    B1: Change resistance      (pace → anxiety → slower adoption)
    B2: Skill gap brake        (deployment → gaps → reduced adoption)
    B3: Knowledge drain        (separations → knowledge loss → quality issues)

  Key equations:
    - Adoption: Bass diffusion dA/dt = [p + q×A/M]×[M-A] × HFM
    - Savings:  monthly = freed_hc × avg_salary × adoption(t) × proficiency(t) / 12
    - J-curve:  productivity_multiplier = 1 - dip% × max(0, 1 - t/dip_months)
    - HFM:      0.30×(1-R) + 0.25×P + 0.20×M + 0.25×C

Wraps the EXISTING CascadeEngine (does NOT replace it). The cascade
runs once to compute the theoretical maximum impact, then the time-stepped
loop applies adoption, human factors, and feedback to determine the actual
month-by-month trajectory.

Usage:
    engine = SimulationEngineV2(cascade_engine, sim_config)
    trajectory = engine.run(scope_data, reclassifications, tech_costs)
    # trajectory.snapshots[0..35] — monthly state
    # trajectory.summary — final numbers
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    FinancialConfig,
    OrganizationProfile,
    SimulationConfig,
)
from draup_world_model.digital_twin.simulation.cascade_engine import CascadeEngine
from draup_world_model.digital_twin.simulation.human_factors import (
    HumanFactorsEngine,
    HumanFactorState,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Bass Diffusion Model for technology adoption
# ──────────────────────────────────────────────────────────────

# Bass parameters by adoption speed
BASS_PARAMS = {
    "fast":     {"p": 0.03, "q": 0.60},   # high innovation + imitation
    "moderate": {"p": 0.02, "q": 0.40},   # typical enterprise
    "slow":     {"p": 0.01, "q": 0.25},   # conservative org
}


def bass_diffusion_step(
    current_adopters: float,
    max_adopters: float,
    p: float,
    q: float,
    human_factor_multiplier: float = 1.0,
) -> float:
    """One-month Bass diffusion step.

    dA/dt = [p + q × A/M] × [M - A] × HFM

    Args:
        current_adopters: A(t) — number currently adopted
        max_adopters: M — maximum potential adopters
        p: Innovation coefficient (external influence)
        q: Imitation coefficient (internal influence / word of mouth)
        human_factor_multiplier: HFM scales the adoption rate

    Returns:
        New number of adopters after 1 month.
    """
    if max_adopters <= 0:
        return current_adopters

    a_frac = current_adopters / max_adopters
    remaining = max_adopters - current_adopters
    da = (p + q * a_frac) * remaining * human_factor_multiplier
    return min(current_adopters + da, max_adopters)


# ──────────────────────────────────────────────────────────────
# Monthly snapshot
# ──────────────────────────────────────────────────────────────

@dataclass
class MonthlySnapshot:
    """State of all stocks at the end of a given month."""
    month: int

    # Adoption
    adoption_level: float = 0.0       # 0-1 fraction
    adoption_delta: float = 0.0       # change this month

    # Workforce
    current_headcount: int = 0
    effective_freed_hc: float = 0.0   # freed × adoption × proficiency
    separated_this_month: float = 0.0
    redeployed_cumulative: float = 0.0
    separated_cumulative: float = 0.0
    attrited_this_month: float = 0.0

    # Financial
    monthly_savings: float = 0.0
    monthly_costs: float = 0.0
    cumulative_savings: float = 0.0
    cumulative_costs: float = 0.0
    monthly_net: float = 0.0
    cumulative_net: float = 0.0
    npv_to_date: float = 0.0

    # Human factors
    human_factors: Dict[str, float] = field(default_factory=dict)
    human_factor_multiplier: float = 0.0

    # J-curve
    j_curve_active: bool = False
    productivity_multiplier: float = 1.0

    # Feedback loops active
    active_loops: List[str] = field(default_factory=list)

    # Risks snapshot
    risk_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "month": self.month,
            "adoption": {
                "level": round(self.adoption_level, 4),
                "delta": round(self.adoption_delta, 4),
            },
            "workforce": {
                "current_headcount": self.current_headcount,
                "effective_freed_hc": round(self.effective_freed_hc, 1),
                "separated_this_month": round(self.separated_this_month, 1),
                "separated_cumulative": round(self.separated_cumulative, 1),
                "redeployed_cumulative": round(self.redeployed_cumulative, 1),
                "attrited_this_month": round(self.attrited_this_month, 1),
            },
            "financial": {
                "monthly_savings": round(self.monthly_savings, 2),
                "monthly_costs": round(self.monthly_costs, 2),
                "monthly_net": round(self.monthly_net, 2),
                "cumulative_savings": round(self.cumulative_savings, 2),
                "cumulative_costs": round(self.cumulative_costs, 2),
                "cumulative_net": round(self.cumulative_net, 2),
                "npv_to_date": round(self.npv_to_date, 2),
            },
            "human_factors": self.human_factors,
            "productivity_multiplier": round(self.productivity_multiplier, 4),
            "j_curve_active": self.j_curve_active,
            "active_feedback_loops": self.active_loops,
        }


@dataclass
class SimulationTrajectory:
    """Full result of a time-stepped simulation."""
    snapshots: List[MonthlySnapshot]
    cascade_result: Dict[str, Any]  # original v1 cascade (theoretical max)
    config_used: Dict[str, Any]

    @property
    def final(self) -> MonthlySnapshot:
        return self.snapshots[-1] if self.snapshots else MonthlySnapshot(month=0)

    def summary(self) -> Dict[str, Any]:
        """Generate summary comparable to v1 output."""
        f = self.final
        cascade = self.cascade_result
        return {
            "engine": "v2_time_stepped",
            "timeline_months": len(self.snapshots),
            "theoretical_max": {
                "freed_headcount": cascade.get("workforce", {}).get("freed_headcount", 0),
                "gross_savings": cascade.get("financial", {}).get("gross_savings", 0),
            },
            "actual_at_end": {
                "adoption_level": round(f.adoption_level, 3),
                "effective_freed_hc": round(f.effective_freed_hc, 1),
                "cumulative_savings": round(f.cumulative_savings, 2),
                "cumulative_costs": round(f.cumulative_costs, 2),
                "cumulative_net": round(f.cumulative_net, 2),
                "npv": round(f.npv_to_date, 2),
                "roi_pct": round(
                    (f.cumulative_net / f.cumulative_costs * 100)
                    if f.cumulative_costs > 0 else 0, 1
                ),
            },
            "human_factors_final": f.human_factors,
            "payback_month": self._find_payback_month(),
            "breakeven_month": self._find_breakeven_month(),
        }

    def milestone_months(self, milestones: List[int] = None) -> List[Dict]:
        """Extract snapshots at milestone months for summary display."""
        milestones = milestones or [3, 6, 12, 18, 24, 36]
        result = []
        for m in milestones:
            if m <= len(self.snapshots):
                snap = self.snapshots[m - 1]
                result.append(snap.to_dict())
        return result

    def _find_payback_month(self) -> int:
        """Month where cumulative savings first exceed cumulative costs."""
        for snap in self.snapshots:
            if snap.cumulative_savings >= snap.cumulative_costs and snap.cumulative_costs > 0:
                return snap.month
        return 0

    def _find_breakeven_month(self) -> int:
        """Month where cumulative net first turns positive."""
        for snap in self.snapshots:
            if snap.cumulative_net > 0:
                return snap.month
        return 0


# ──────────────────────────────────────────────────────────────
# Main Engine
# ──────────────────────────────────────────────────────────────

class SimulationEngineV2:
    """Time-stepped simulation engine.

    Wraps the existing CascadeEngine to get theoretical max impact,
    then evolves stocks monthly to produce a realistic trajectory.
    """

    def __init__(
        self,
        cascade_engine: CascadeEngine,
        config: Optional[SimulationConfig] = None,
    ):
        self.cascade = cascade_engine
        self.config = config or (cascade_engine.config if cascade_engine else SimulationConfig())
        self.fin_cfg = self.config.financial
        self.org_cfg = self.config.organization
        self.human_engine = HumanFactorsEngine(self.org_cfg)

    def run(
        self,
        scope_data: Dict[str, Any],
        task_reclassifications: List[Dict[str, Any]],
        technology_costs: Optional[Dict[str, Any]] = None,
        adoption_speed: str = "moderate",
    ) -> SimulationTrajectory:
        """Run time-stepped simulation.

        Args:
            scope_data: From ScopeSelector.select()
            task_reclassifications: Task changes (from role_redesign or task_distributor)
            technology_costs: Optional tech cost dict
            adoption_speed: "fast", "moderate", or "slow"

        Returns:
            SimulationTrajectory with monthly snapshots.
        """
        timeline = self.config.timeline_months

        # Step 0: Run v1 cascade to get theoretical maximum
        # Deep-copy scope_data to avoid mutating the caller's data
        import copy
        scope_copy = copy.deepcopy(scope_data)
        cascade_result = self.cascade.run(scope_copy, task_reclassifications, technology_costs)

        # Extract theoretical maximums from cascade
        theoretical_freed_hc = cascade_result.get("workforce", {}).get("freed_headcount", 0)
        total_headcount = cascade_result.get("workforce", {}).get("current_headcount", 0)
        cascade_financial = cascade_result.get("financial", {})

        # Cost components (from cascade's theoretical-max financial model)
        total_tech_licensing = cascade_financial.get("technology_licensing", 0)
        total_implementation = cascade_financial.get("implementation_cost", 0)
        total_reskilling = cascade_financial.get("reskilling_cost", 0)
        total_change_mgmt = cascade_financial.get("change_management_cost", 0)
        # Note: severance is computed per-month proportional to actual separations
        # (not front-loaded from cascade total), so no total_severance variable needed.

        # Monthly cost schedule
        monthly_tech = total_tech_licensing / timeline if timeline > 0 else 0
        monthly_impl = total_implementation / min(12, timeline) if timeline > 0 else 0
        monthly_reskilling = total_reskilling / min(18, timeline) if timeline > 0 else 0
        monthly_change_mgmt = total_change_mgmt / min(24, timeline) if timeline > 0 else 0
        # Average salary for J-curve computation
        title_impacts = []
        for impact in cascade_result.get("role_impacts", {}).get("impacts", []):
            title_impacts.extend(impact.get("title_impacts", []))
        total_hc_affected = sum(ti.get("headcount", 0) for ti in title_impacts)
        avg_salary = 0
        if total_hc_affected > 0:
            avg_salary = sum(
                ti.get("avg_salary", 0) * ti.get("headcount", 0)
                for ti in title_impacts
            ) / total_hc_affected

        # Bass diffusion parameters
        bass = BASS_PARAMS.get(adoption_speed, BASS_PARAMS["moderate"])
        max_adopters = float(total_headcount)

        # Redeployability
        redeploy_rate = self.config.cascade.redeployability_pct / 100.0
        monthly_attrition_rate = self.org_cfg.base_annual_attrition_pct / 100.0 / 12.0

        # J-curve params
        j_dip_pct = self.fin_cfg.j_curve_dip_pct / 100.0
        j_duration = self.fin_cfg.j_curve_duration_months
        j_enabled = self.fin_cfg.j_curve_enabled

        # J-curve disruption fraction: scales the dip by how much work actually
        # changes. Deploying Copilot that frees 16% of capacity shouldn't cause
        # the same dip as redesigning 35%+ of all roles. Capped at 1.0.
        j_disruption_fraction = (
            min(1.0, theoretical_freed_hc / total_headcount * 2.0)
            if total_headcount > 0 else 0.0
        )

        # Discount rate (monthly) for NPV
        annual_discount = 0.10  # 10% default
        monthly_discount = (1 + annual_discount) ** (1 / 12) - 1

        # ──────────────────────────────────────────────────
        # Time-stepping loop
        # ──────────────────────────────────────────────────
        hf_state = self.human_engine.initial_state()
        current_adopters = 0.0
        cumulative_savings = 0.0
        cumulative_costs = 0.0
        cumulative_separated = 0.0
        cumulative_redeployed = 0.0
        npv_to_date = 0.0
        snapshots = []

        for month in range(1, timeline + 1):
            # 1. Human Factor Multiplier
            hfm = hf_state.composite_multiplier()

            # 2. Adoption step (Bass diffusion × HFM)
            prev_adopters = current_adopters
            current_adopters = bass_diffusion_step(
                current_adopters, max_adopters,
                bass["p"], bass["q"],
                human_factor_multiplier=hfm,
            )
            adoption_level = current_adopters / max_adopters if max_adopters > 0 else 0
            adoption_delta = (current_adopters - prev_adopters) / max_adopters if max_adopters > 0 else 0

            # 3. J-curve productivity multiplier (tracked for reporting only;
            #    actual cost impact is via j_curve_monthly direct cost below)
            j_active = j_enabled and month <= j_duration
            if j_active:
                taper = max(0.0, 1.0 - (month - 1) / j_duration)
                prod_mult = 1.0 - j_dip_pct * taper
            else:
                prod_mult = 1.0

            # 4. Effective freed capacity
            #    adoption: is the tool deployed? (0→1 via Bass diffusion)
            #    proficiency_effectiveness: can people use it? Floor of 0.5
            #      because automation tools provide substantial benefit even
            #      when users are beginners. Full proficiency adds the rest.
            #    J-curve is NOT applied here — it's a separate cost for
            #      overall productivity loss, not a reduction in freed capacity.
            proficiency_effectiveness = 0.5 + 0.5 * hf_state.proficiency
            effective_freed_hc = (
                theoretical_freed_hc
                * adoption_level
                * proficiency_effectiveness
            )

            # 5. Monthly savings (only for actually freed capacity)
            monthly_savings = (effective_freed_hc * avg_salary / 12.0) if avg_salary > 0 else 0

            # 6. Workforce flows (computed before costs so severance can use monthly_sep)
            monthly_sep_target = theoretical_freed_hc * (1 - redeploy_rate) / timeline
            monthly_sep = monthly_sep_target * adoption_level
            cumulative_separated += monthly_sep

            redeploy_delay = 3  # months before redeployment starts
            monthly_redeploy = 0.0
            if month > redeploy_delay:
                monthly_redeploy_target = theoretical_freed_hc * redeploy_rate / (timeline - redeploy_delay)
                monthly_redeploy = monthly_redeploy_target * adoption_level
                cumulative_redeployed += monthly_redeploy

            monthly_attrition = total_headcount * monthly_attrition_rate

            # 7. Monthly costs
            #
            # COMMITTED costs (fixed schedule, incurred regardless of adoption):
            #   - Implementation: infrastructure and integration, first 12 months
            #   - Change management: communication/stakeholder program, first 24 months
            #   - J-curve: productivity dip during transition (tapers linearly)
            #
            # ADOPTION-PROPORTIONAL costs (scale with actual adoption level):
            #   - Tech licensing: you buy licenses as people adopt, not all day 1
            #   - Reskilling: you train people as they onboard to new tools
            #
            # SEPARATION-PROPORTIONAL costs (scale with actual separations):
            #   - Severance: paid when people actually leave, not upfront
            #
            monthly_cost = 0.0

            # Committed: Implementation (first 12 months)
            if month <= 12:
                monthly_cost += monthly_impl

            # Committed: Change management (first 24 months)
            if month <= 24:
                monthly_cost += monthly_change_mgmt

            # Adoption-proportional: Tech licensing (pay for active licenses)
            monthly_cost += monthly_tech * adoption_level

            # Adoption-proportional: Reskilling (train as adoption grows, 18 months)
            if month <= 18:
                monthly_cost += monthly_reskilling * adoption_level

            # Separation-proportional: Severance (paid when people actually leave)
            if monthly_sep > 0 and avg_salary > 0:
                monthly_cost += monthly_sep * avg_salary * self.fin_cfg.severance_months / 12.0

            # J-curve cost (productivity dip scaled by disruption magnitude)
            # The dip is proportional to how much of the workforce's work is
            # actually changing. A narrow tool deployment (16% freed) causes
            # ~32% of the theoretical max dip; a major redesign (50%+ freed)
            # causes the full dip.
            j_curve_monthly = 0.0
            if j_active and total_hc_affected > 0:
                taper = max(0.0, 1.0 - (month - 1) / j_duration)
                j_curve_monthly = (
                    total_hc_affected * avg_salary * j_dip_pct
                    * taper * j_disruption_fraction / 12.0
                )
                monthly_cost += j_curve_monthly

            # 8. Financial accumulation
            cumulative_savings += monthly_savings
            cumulative_costs += monthly_cost
            monthly_net = monthly_savings - monthly_cost
            cumulative_net = cumulative_savings - cumulative_costs

            # NPV (present value of this month's net — running sum)
            discount_factor = 1.0 / ((1 + monthly_discount) ** month)
            npv_to_date += monthly_net * discount_factor

            # 9. Human factors step
            pace_of_change = min(1.0, adoption_delta * 5)  # scale adoption delta to 0-1
            separation_rate = monthly_sep / total_headcount if total_headcount > 0 else 0

            hf_context = {
                "adoption_level": adoption_level,
                "separation_rate": separation_rate,
                "reskilling_active": month <= 18,
                "training_investment": min(0.5, 0.1 + adoption_level * 0.4),
                "pace_of_change": pace_of_change,
                "leadership_target": 0.8,
            }
            hf_state = self.human_engine.step(hf_state, month, hf_context)

            # 10. Feedback loop detection
            active_loops = self._detect_feedback_loops(
                month, adoption_level, hf_state, monthly_savings, monthly_cost,
                separation_rate,
            )

            # 11. Risk assessment
            risk_flags = []
            if cumulative_separated > total_headcount * 0.15:
                risk_flags.append("high_workforce_reduction")
            if hf_state.morale < 0.4:
                risk_flags.append("low_morale")
            if hf_state.resistance > 0.7:
                risk_flags.append("high_resistance")

            # 12. Record snapshot
            snap = MonthlySnapshot(
                month=month,
                adoption_level=adoption_level,
                adoption_delta=adoption_delta,
                current_headcount=total_headcount,
                effective_freed_hc=effective_freed_hc,
                separated_this_month=monthly_sep,
                separated_cumulative=cumulative_separated,
                redeployed_cumulative=cumulative_redeployed,
                attrited_this_month=monthly_attrition,
                monthly_savings=monthly_savings,
                monthly_costs=monthly_cost,
                cumulative_savings=cumulative_savings,
                cumulative_costs=cumulative_costs,
                monthly_net=monthly_net,
                cumulative_net=cumulative_net,
                npv_to_date=npv_to_date,
                human_factors=hf_state.to_dict(),
                human_factor_multiplier=hfm,
                j_curve_active=j_active,
                productivity_multiplier=prod_mult,
                active_loops=active_loops,
                risk_flags=risk_flags,
            )
            snapshots.append(snap)

        logger.info(
            f"v2 simulation complete: {timeline} months, "
            f"final adoption={snapshots[-1].adoption_level:.1%}, "
            f"net={cumulative_net:,.0f}"
        )

        return SimulationTrajectory(
            snapshots=snapshots,
            cascade_result=cascade_result,
            config_used={
                "adoption_speed": adoption_speed,
                "j_curve_enabled": j_enabled,
                "timeline_months": timeline,
                "bass_params": bass,
            },
        )

    def _detect_feedback_loops(
        self,
        month: int,
        adoption: float,
        hf: HumanFactorState,
        monthly_savings: float,
        monthly_cost: float,
        separation_rate: float,
    ) -> List[str]:
        """Detect which feedback loops are active this month."""
        loops = []

        # R1: Productivity flywheel — savings > costs means budget for more AI
        if monthly_savings > monthly_cost and adoption > 0.3:
            loops.append("R1_productivity_flywheel")

        # R2: Capability compounding — proficiency > 0.4 accelerates adoption
        if hf.proficiency > 0.4 and adoption > 0.2:
            loops.append("R2_capability_compounding")

        # B1: Change resistance — resistance > 0.5 slows adoption
        if hf.resistance > 0.5:
            loops.append("B1_change_resistance")

        # B2: Skill gap brake — low proficiency brakes adoption
        if hf.proficiency < 0.3 and adoption > 0.1:
            loops.append("B2_skill_gap_brake")

        # B3: Knowledge drain — high separation threatens quality
        if separation_rate > 0.01:
            loops.append("B3_knowledge_drain")

        return loops
