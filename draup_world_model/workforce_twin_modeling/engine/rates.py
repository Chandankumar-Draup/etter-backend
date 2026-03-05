"""
Rate Equations and Scenario Definitions
========================================
The three S-curves that drive adoption over time:
  Phase 1 (Adopt):   close the adoption gap (tools deployed but unused)
  Phase 2 (Expand):  push beyond adoption gap (new use cases)
  Phase 3 (Extend):  workflow-level automation (non-linear gains)

Each phase follows a logistic S-curve: S(t) = alpha / (1 + e^(-k * (t - midpoint)))
  alpha:    ceiling (max % of potential realized)
  k:        steepness (how fast adoption happens)
  midpoint: inflection point (month of fastest change)

Five policy scenarios vary these parameters to produce dramatically different outcomes.
"""
import math
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Rate Parameters (single S-curve)
# ============================================================

@dataclass
class RateParams:
    """
    One S-curve phase. The atomic building block of adoption dynamics.
    Logistic function: alpha / (1 + e^(-k * (t - midpoint)))
    """
    alpha: float          # ceiling (0-1): max adoption this phase can achieve
    k: float              # steepness: how fast the S-curve rises
    midpoint: float       # inflection month: when adoption is fastest
    delay_months: int = 0 # months before this phase begins

    def at(self, month: int) -> float:
        """Return the S-curve value at a given month."""
        if self.alpha <= 0:
            return 0.0
        t = month - self.delay_months
        if t < 0:
            return 0.0
        # Logistic S-curve
        exponent = -self.k * (t - self.midpoint)
        # Clamp exponent to avoid overflow
        exponent = max(-20, min(20, exponent))
        return self.alpha / (1.0 + math.exp(exponent))


# ============================================================
# Simulation Parameters (composite of 3 S-curves + policy)
# ============================================================

@dataclass
class SimulationParams:
    """
    Complete parameter set for a simulation scenario.
    Combines rate equations with policy decisions.
    """
    scenario_id: str
    scenario_name: str

    # Three-phase rate parameters
    adoption: Optional[RateParams] = None    # Phase 1: close adoption gap
    expansion: Optional[RateParams] = None   # Phase 2: expand beyond current tech
    extension: Optional[RateParams] = None   # Phase 3: workflow automation

    # Policy parameters
    policy: str = "moderate_reduction"       # HC policy
    absorption_factor: float = 0.35          # base redistribution absorption
    training_cost_per_person: float = 2000   # $ per affected person
    readiness_threshold: float = 0.0         # min readiness to proceed

    # Time
    time_horizon_months: int = 36
    hc_review_frequency: int = 3             # HC decisions every N months

    # Skill dynamics
    reskilling_delay_months: int = 5         # months before reskilling closes gaps
    reskilling_rate: float = 0.15            # % of open gaps closed per month after delay

    # Workflow automation bonus (Phase 3 only)
    enable_workflow_automation: bool = False
    workflow_automation_bonus: float = 1.3   # non-linear multiplier for P5

    # Trust dynamics
    trust_build_rate: float = 0.025
    trust_destroy_factor: float = 0.30


# ============================================================
# The Five Policy Scenarios
# ============================================================

# P1: Cautious — adoption gap only, natural attrition
P1_CAUTIOUS = SimulationParams(
    scenario_id="P1",
    scenario_name="Cautious",
    adoption=RateParams(alpha=0.5, k=0.3, midpoint=4),
    expansion=None,
    extension=None,
    policy="natural_attrition",
    absorption_factor=0.40,
    readiness_threshold=0,
    reskilling_delay_months=6,
    reskilling_rate=0.12,
    trust_build_rate=0.02,
    trust_destroy_factor=0.30,
)

# P2: Balanced — adoption + expansion, moderate reduction
P2_BALANCED = SimulationParams(
    scenario_id="P2",
    scenario_name="Balanced",
    adoption=RateParams(alpha=0.6, k=0.3, midpoint=4),
    expansion=RateParams(alpha=0.3, k=0.3, midpoint=4, delay_months=6),
    extension=None,
    policy="moderate_reduction",
    absorption_factor=0.35,
    readiness_threshold=50,
    reskilling_delay_months=5,
    reskilling_rate=0.15,
    trust_build_rate=0.025,
    trust_destroy_factor=0.30,
)

# P3: Aggressive — all 3 phases, active reduction
P3_AGGRESSIVE = SimulationParams(
    scenario_id="P3",
    scenario_name="Aggressive",
    adoption=RateParams(alpha=0.8, k=0.35, midpoint=3),
    expansion=RateParams(alpha=0.5, k=0.35, midpoint=3, delay_months=4),
    extension=RateParams(alpha=0.3, k=0.35, midpoint=3, delay_months=8),
    policy="active_reduction",
    absorption_factor=0.30,
    readiness_threshold=70,
    reskilling_delay_months=4,
    reskilling_rate=0.18,
    trust_build_rate=0.03,
    trust_destroy_factor=0.35,
)

# P4: Capability-First — no layoffs, redirect freed capacity
P4_CAPABILITY_FIRST = SimulationParams(
    scenario_id="P4",
    scenario_name="Capability-First",
    adoption=RateParams(alpha=0.6, k=0.3, midpoint=4),
    expansion=RateParams(alpha=0.3, k=0.3, midpoint=4, delay_months=6),
    extension=None,
    policy="no_layoffs",
    absorption_factor=0.0,  # all freed capacity redeployed
    readiness_threshold=40,
    reskilling_delay_months=5,
    reskilling_rate=0.15,
    trust_build_rate=0.03,
    trust_destroy_factor=0.20,
)

# P5: AI-Age Accelerated — workflow automation, rapid redeployment
P5_ACCELERATED = SimulationParams(
    scenario_id="P5",
    scenario_name="AI-Age Accelerated",
    adoption=RateParams(alpha=0.8, k=0.4, midpoint=3),
    expansion=RateParams(alpha=0.5, k=0.4, midpoint=3, delay_months=4),
    extension=RateParams(alpha=0.3, k=0.4, midpoint=3, delay_months=6),
    policy="rapid_redeployment",
    absorption_factor=0.25,
    readiness_threshold=80,
    reskilling_delay_months=3,
    reskilling_rate=0.20,
    enable_workflow_automation=True,
    workflow_automation_bonus=1.3,
    trust_build_rate=0.035,
    trust_destroy_factor=0.35,
)

# All scenarios indexed
ALL_SCENARIOS = {
    "P1": P1_CAUTIOUS,
    "P2": P2_BALANCED,
    "P3": P3_AGGRESSIVE,
    "P4": P4_CAPABILITY_FIRST,
    "P5": P5_ACCELERATED,
}
