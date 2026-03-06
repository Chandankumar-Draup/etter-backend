"""
Phase 3.11: Human Factors Engine.

Models 4 organizational stocks that evolve over time and modulate
the effectiveness of automation interventions:

  1. Resistance (0→1): Employee anxiety and pushback against change.
     Spikes with change announcements, decays through adaptation and communication.

  2. Morale (0→1): Workforce psychological state.
     Boosted by skill growth and career opportunity, hurt by layoffs and uncertainty.

  3. Proficiency (0→1): Organizational AI competency.
     Grows via training investment and learning-by-doing, bounded by aptitude.

  4. Culture Readiness (0→1): How ready the org culture is for AI transformation.
     Moves slowly toward a leadership-set target (exponential decay with time constant τ).

The four stocks combine into a Human Factor Multiplier (HFM) that scales
the effective adoption rate and freed capacity throughout the time-stepped simulation.

Equations follow Meadows' stock-and-flow notation:
  dStock/dt = inflows - outflows
  Euler integration: Stock(t+1) = Stock(t) + dStock/dt × dt

References:
  - Donella Meadows, "Thinking in Systems" (2008)
  - Bass Diffusion Model for adoption dynamics
  - Kübler-Ross change curve for resistance modeling
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from draup_world_model.digital_twin.config import OrganizationProfile

logger = logging.getLogger(__name__)


@dataclass
class HumanFactorState:
    """Snapshot of the 4 human factor stocks at a point in time.

    All values are bounded [0, 1].
    """
    resistance: float = 0.6
    morale: float = 0.7
    proficiency: float = 0.1
    culture_readiness: float = 0.3

    def clamp(self) -> "HumanFactorState":
        """Ensure all values are within [0, 1]."""
        self.resistance = max(0.0, min(1.0, self.resistance))
        self.morale = max(0.0, min(1.0, self.morale))
        self.proficiency = max(0.0, min(1.0, self.proficiency))
        self.culture_readiness = max(0.0, min(1.0, self.culture_readiness))
        return self

    def composite_multiplier(
        self,
        w_resistance: float = 0.30,
        w_proficiency: float = 0.25,
        w_morale: float = 0.20,
        w_culture: float = 0.25,
    ) -> float:
        """Compute the Human Factor Multiplier (HFM).

        HFM = w_r×(1-R) + w_p×P + w_m×M + w_c×C
        Range: 0 (fully blocked) to 1 (fully effective).
        """
        return (
            w_resistance * (1 - self.resistance)
            + w_proficiency * self.proficiency
            + w_morale * self.morale
            + w_culture * self.culture_readiness
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "resistance": round(self.resistance, 4),
            "morale": round(self.morale, 4),
            "proficiency": round(self.proficiency, 4),
            "culture_readiness": round(self.culture_readiness, 4),
            "composite_multiplier": round(self.composite_multiplier(), 4),
        }


class HumanFactorsEngine:
    """Computes monthly evolution of the 4 human factor stocks.

    Usage:
        engine = HumanFactorsEngine(org_profile)
        state = engine.initial_state()
        for month in range(1, 37):
            state = engine.step(state, month, context)
    """

    def __init__(self, org_profile: Optional[OrganizationProfile] = None):
        self.org = org_profile or OrganizationProfile()

    def initial_state(self) -> HumanFactorState:
        """Create initial state from organization profile."""
        return HumanFactorState(
            resistance=self.org.initial_resistance,
            morale=self.org.initial_morale,
            proficiency=self.org.initial_ai_proficiency,
            culture_readiness=self.org.initial_culture_readiness,
        )

    def step(
        self,
        state: HumanFactorState,
        month: int,
        context: Dict[str, Any],
    ) -> HumanFactorState:
        """Advance human factor stocks by one month.

        Args:
            state: Current human factor state
            month: Current month number (1-based)
            context: Dict with simulation state variables:
                - adoption_level: float (0-1), current tech adoption
                - separation_rate: float, fraction of workforce separated this month
                - reskilling_active: bool, whether reskilling program is running
                - training_investment: float (0-1), normalized training spend
                - pace_of_change: float (0-1), how fast changes are happening
                - leadership_target: float (0-1), culture target set by leadership

        Returns:
            New HumanFactorState after one month.
        """
        dt = 1.0  # 1 month time step

        dr = self._resistance_delta(state, context)
        dm = self._morale_delta(state, context)
        dp = self._proficiency_delta(state, context)
        dc = self._culture_delta(state, context)

        new_state = HumanFactorState(
            resistance=state.resistance + dr * dt,
            morale=state.morale + dm * dt,
            proficiency=state.proficiency + dp * dt,
            culture_readiness=state.culture_readiness + dc * dt,
        )
        return new_state.clamp()

    def _resistance_delta(
        self, state: HumanFactorState, ctx: Dict[str, Any]
    ) -> float:
        """dR/dt = change_shock - adaptation_rate - communication_effect.

        Resistance spikes when pace_of_change is high and decays naturally
        through adaptation (people get used to change) and communication
        investment (leadership transparency).
        """
        pace = ctx.get("pace_of_change", 0.3)
        training = ctx.get("training_investment", 0.2)

        # Change shock: proportional to pace × current uncertainty
        # Uncertainty is higher when proficiency is low
        uncertainty = 1.0 - state.proficiency
        change_shock = pace * uncertainty * 0.08  # max +0.08/month

        # Natural adaptation: resistance decays at 5%/month
        adaptation = state.resistance * 0.05

        # Communication/training investment reduces resistance
        communication_effect = training * 0.03  # max -0.03/month

        return change_shock - adaptation - communication_effect

    def _morale_delta(
        self, state: HumanFactorState, ctx: Dict[str, Any]
    ) -> float:
        """dM/dt = skill_growth + career_signal - layoff_shock - uncertainty_drag.

        Morale is hurt by separations and uncertainty, boosted by visible
        skill growth and career opportunities from the transformation.
        """
        separation_rate = ctx.get("separation_rate", 0.0)
        adoption = ctx.get("adoption_level", 0.0)
        reskilling = ctx.get("reskilling_active", False)

        # Skill growth signal: proficiency improvement gives hope
        skill_growth = state.proficiency * 0.02  # max +0.02/month

        # Career opportunity: higher adoption creates new roles
        career_signal = adoption * 0.015  # max +0.015/month

        # Layoff shock: proportional to separation rate
        layoff_shock = separation_rate * 0.30  # separation of 10% → -0.03 morale

        # Uncertainty drag: inversely proportional to culture readiness
        uncertainty_drag = (1 - state.culture_readiness) * 0.01

        # Reskilling boost: active program signals investment in people
        reskill_boost = 0.01 if reskilling else 0.0

        return skill_growth + career_signal + reskill_boost - layoff_shock - uncertainty_drag

    def _proficiency_delta(
        self, state: HumanFactorState, ctx: Dict[str, Any]
    ) -> float:
        """dP/dt = learning_rate × (1 - P).

        Proficiency follows a saturating growth curve (logistic-like).
        Learning rate depends on training investment and aptitude.
        Learning-by-doing: higher adoption accelerates learning.
        """
        training = ctx.get("training_investment", 0.2)
        adoption = ctx.get("adoption_level", 0.0)

        # Base learning rate from training
        base_rate = training * 0.06  # max ~0.06/month at full investment

        # Learning-by-doing: accelerates with adoption
        lbd_rate = adoption * 0.03  # max +0.03/month

        # Total learning rate, capped
        learning_rate = min(base_rate + lbd_rate, 0.10)

        # Saturating growth: slows as proficiency approaches 1
        headroom = 1.0 - state.proficiency
        return learning_rate * headroom

    def _culture_delta(
        self, state: HumanFactorState, ctx: Dict[str, Any]
    ) -> float:
        """dC/dt = -(C - target) / τ.

        Culture readiness moves toward a leadership-set target with
        exponential decay time constant τ (typically 12-36 months).
        This models the slow, inertial nature of culture change.
        """
        target = ctx.get("leadership_target", 0.8)
        tau = self.org.culture_time_constant_months

        # Exponential approach to target
        return -(state.culture_readiness - target) / tau
