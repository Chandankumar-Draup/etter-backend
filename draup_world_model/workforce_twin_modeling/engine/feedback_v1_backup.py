"""
The Eight Feedback Loops
========================
4 Balancing loops (dampen change):
  B1: Capacity Absorption — more workload/person → more freed hours reabsorbed
  B2: Skill Valley — skill gap → reduces effective adoption rate
  B3: Change Resistance — too fast → resistance → readiness falls → adoption slows
  B4: Seniority Offset — as entry-level goes first, remaining is more senior, less automatable

4 Reinforcing loops (amplify change):
  R1: Trust-Adoption — more adoption → more success → more trust → more willingness
  R2: Proficiency — more adoption → more practice → more proficiency → better results
  R3: Savings — more savings → more budget → more investment capacity
  R4: Political Capital — early wins → more capital → bigger moves enabled

Key design principle from Meadows:
  Feedback loops don't operate independently — they interact.
  At any moment, some loops DOMINATE and others are dormant.
  The model's behavior is determined by which loop dominates.

  Early: B3 (resistance) and B2 (skill valley) dominate → slow start
  Mid:   R1 (trust) and R2 (proficiency) dominate → acceleration
  Late:  B1 (absorption) and B4 (seniority) dominate → diminishing returns

Implementation: each loop is a pure function.
  Input:  current state (the stocks)
  Output: delta values (the flows)
  No side effects. Composable. Testable.
"""
import math
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Human System State (dynamic — changes each timestep)
# ============================================================

@dataclass
class HumanSystemState:
    """
    The dynamic human system — Stock 6 from the system model.
    These values CHANGE at every timestep based on feedback loops.
    """
    proficiency: float = 30.0           # 0-100: can workforce work WITH AI?
    readiness: float = 50.0             # 0-100: willingness to adopt
    trust: float = 40.0                 # 0-100: trust in AI tools
    political_capital: float = 60.0     # 0-100: leadership support
    transformation_fatigue: float = 0.0 # 0-100: accumulated exhaustion

    @property
    def effective_multiplier(self) -> float:
        """How much of the theoretical adoption rate is achievable given human state."""
        return (self.proficiency / 100.0) * (self.readiness / 100.0)

    @property
    def trust_multiplier(self) -> float:
        """Trust modulates willingness — below 30 = significant drag."""
        return min(1.0, self.trust / 60.0)  # caps at 1.0 when trust >= 60

    @property
    def capital_multiplier(self) -> float:
        """Political capital enables/blocks resource allocation."""
        if self.political_capital < 20:
            return 0.2    # nearly blocked
        elif self.political_capital < 40:
            return 0.6    # constrained
        return 1.0        # green light

    def clamp(self):
        """Ensure all values stay in valid range."""
        self.proficiency = max(0, min(100, self.proficiency))
        self.readiness = max(0, min(100, self.readiness))
        self.trust = max(0, min(100, self.trust))
        self.political_capital = max(0, min(100, self.political_capital))
        self.transformation_fatigue = max(0, min(100, self.transformation_fatigue))


# ============================================================
# Feedback Parameters
# ============================================================

@dataclass
class FeedbackParams:
    """Tunable parameters for all 8 feedback loops."""

    # B1: Capacity Absorption
    base_absorption: float = 0.30           # baseline absorption rate
    workload_absorption_sensitivity: float = 0.20  # extra absorption per unit overload

    # B2: Skill Valley
    skill_gap_drag_coefficient: float = 0.5 # how much skill gap reduces effective adoption (0-1)

    # B3: Change Resistance
    resistance_sensitivity: float = 0.4     # how strongly disruption → resistance
    resistance_decay_rate: float = 0.08     # how fast resistance fades per month
    fatigue_build_rate: float = 0.03        # fatigue accumulation per unit disruption

    # B4: Seniority Offset
    seniority_penalty: float = 0.15         # % reduction in potential per seniority unit

    # R1: Trust-Adoption Flywheel
    trust_build_rate: float = 2.0           # trust gained per month of successful adoption
    trust_destruction_factor: float = 0.30  # % of trust lost on AI error (multiplicative, fast)
    success_probability: float = 0.85       # probability each month is a "success"

    # R2: Proficiency Flywheel
    learning_rate: float = 3.0              # proficiency gained per month of practice
    learning_saturation: float = 85.0       # diminishing returns above this level

    # R3: Savings Flywheel
    reinvestment_rate: float = 0.10         # % of cumulative savings reinvested
    reinvestment_effectiveness: float = 1.5 # $ return per $ reinvested

    # R4: Political Capital
    capital_build_rate: float = 1.5         # capital gained per successful month
    capital_spend_rate: float = 0.5         # capital spent per unit disruption
    capital_threshold: float = 30.0         # below this, resources are constrained

    # Event injection (for testing)
    ai_error_month: Optional[int] = None    # inject an AI error at this month


# ============================================================
# B1: Capacity Absorption (Balancing)
# ============================================================

def b1_capacity_absorption(
    base_absorption: float,
    workload_per_person: float,
    max_workload: float,
    sensitivity: float,
) -> float:
    """
    As workload per person increases, more freed capacity gets reabsorbed.
    Higher workload → harder to actually free people → dampens headcount impact.

    Returns: absorption_factor (0→~0.6)
    """
    overload_ratio = min(1.0, workload_per_person / max_workload)
    return base_absorption + overload_ratio * sensitivity


# ============================================================
# B2: Skill Valley (Balancing)
# ============================================================

def b2_skill_valley(
    skill_gap_pct: float,
    drag_coefficient: float,
) -> float:
    """
    Skill gap reduces effective adoption rate.
    Big gap → people can't effectively use new tools → adoption stalls.

    Returns: effective_adoption_multiplier (0→1)
    """
    drag = skill_gap_pct / 100.0 * drag_coefficient
    return max(0.1, 1.0 - drag)  # floor at 10% — never zero


# ============================================================
# B3: Change Resistance (Balancing)
# ============================================================

def b3_change_resistance(
    hs: HumanSystemState,
    disruption_level: float,
    params: FeedbackParams,
) -> tuple:
    """
    High disruption → resistance → readiness falls → adoption slows.
    Also builds fatigue over time.

    Returns: (delta_readiness, delta_fatigue)
    """
    # Resistance force: proportional to disruption, inversely to trust
    trust_dampening = max(0.3, hs.trust / 100.0)
    resistance = disruption_level * params.resistance_sensitivity / trust_dampening

    # Fatigue accumulates slowly but decays even slower
    fatigue_delta = disruption_level * params.fatigue_build_rate

    # Readiness change: resistance pushes down, natural recovery pushes up
    # Recovery is stronger when fatigue is low
    recovery = params.resistance_decay_rate * (1 - hs.transformation_fatigue / 100)
    delta_readiness = -resistance + recovery

    return delta_readiness, fatigue_delta


# ============================================================
# B4: Seniority Offset (Balancing)
# ============================================================

def b4_seniority_offset(
    original_hc: int,
    current_hc: int,
    seniority_penalty: float,
) -> float:
    """
    As entry-level roles are automated first, remaining workforce is more senior.
    More senior = harder to automate = diminishing returns.

    Returns: effective_potential_multiplier (1.0→~0.7)
    """
    if original_hc <= 0:
        return 1.0
    reduction_pct = (original_hc - current_hc) / original_hc
    # Seniority increases roughly linearly with % reduced
    seniority_increase = reduction_pct * seniority_penalty
    return max(0.5, 1.0 - seniority_increase)


# ============================================================
# R1: Trust-Adoption Flywheel (Reinforcing)
# ============================================================

def r1_trust_adoption(
    hs: HumanSystemState,
    adoption_level: float,
    params: FeedbackParams,
    ai_error_this_month: bool = False,
) -> float:
    """
    Successful adoption builds trust → more willingness → more adoption.
    AI errors DESTROY trust (fast, multiplicative).
    Trust building is slow (additive).

    This is the key ASYMMETRY:
      Build: trust += build_rate × adoption × success_prob
      Destroy: trust *= (1 - destruction_factor)

    Returns: delta_trust
    """
    if ai_error_this_month:
        # Multiplicative destruction — 30% of current trust wiped
        return -hs.trust * params.trust_destruction_factor

    # Additive building — proportional to adoption level and success rate
    build = params.trust_build_rate * adoption_level * params.success_probability
    # Diminishing returns at high trust
    ceiling_factor = max(0.1, 1.0 - hs.trust / 100.0)
    return build * ceiling_factor


# ============================================================
# R2: Proficiency Flywheel (Reinforcing)
# ============================================================

def r2_proficiency(
    hs: HumanSystemState,
    adoption_level: float,
    params: FeedbackParams,
) -> float:
    """
    More adoption → more practice → more proficiency → better results.
    Follows a learning curve with diminishing returns.

    Returns: delta_proficiency
    """
    practice_intensity = adoption_level  # 0→1
    # Diminishing returns above saturation point
    ceiling_factor = max(0.05, 1.0 - hs.proficiency / params.learning_saturation)
    return params.learning_rate * practice_intensity * ceiling_factor


# ============================================================
# R3: Savings Flywheel (Reinforcing)
# ============================================================

def r3_savings_reinvestment(
    cumulative_savings: float,
    params: FeedbackParams,
) -> float:
    """
    More savings → more budget → more investment capacity → more automation.
    Returns: additional_adoption_boost (0→small positive)
    """
    reinvestment = cumulative_savings * params.reinvestment_rate
    # Convert $ to adoption boost (small effect)
    boost = reinvestment * params.reinvestment_effectiveness / 1_000_000  # normalize
    return min(0.05, boost)  # cap at 5% boost


# ============================================================
# R4: Political Capital (Reinforcing)
# ============================================================

def r4_political_capital(
    hs: HumanSystemState,
    adoption_level: float,
    disruption_level: float,
    params: FeedbackParams,
) -> float:
    """
    Early wins build capital → enables bigger moves.
    Disruption spends capital.
    Below threshold → resources constrained → everything slows.

    Returns: delta_political_capital
    """
    # Build: proportional to adoption success
    build = params.capital_build_rate * adoption_level * params.success_probability

    # Spend: proportional to disruption
    spend = params.capital_spend_rate * disruption_level

    return build - spend


# ============================================================
# Composite: Apply All Loops to Compute Effective Adoption Rate
# ============================================================

def compute_effective_adoption(
    raw_adoption: float,
    hs: HumanSystemState,
    skill_gap_pct: float,
    original_hc: int,
    current_hc: int,
    params: FeedbackParams,
) -> float:
    """
    Apply all feedback loops to modulate the raw S-curve adoption rate.

    raw_adoption × human_multiplier × trust × skill_valley × seniority × capital
    """
    human_mult = hs.effective_multiplier
    trust_mult = hs.trust_multiplier
    skill_mult = b2_skill_valley(skill_gap_pct, params.skill_gap_drag_coefficient)
    seniority_mult = b4_seniority_offset(original_hc, current_hc, params.seniority_penalty)
    capital_mult = hs.capital_multiplier

    effective = raw_adoption * human_mult * trust_mult * skill_mult * seniority_mult * capital_mult
    return max(0, min(raw_adoption, effective))  # can't exceed raw, can't go negative


def compute_dynamic_absorption(
    base_absorption: float,
    current_hc: int,
    original_hc: int,
    params: FeedbackParams,
) -> float:
    """
    Dynamic absorption rate — increases as workforce shrinks
    (fewer people → each person absorbs more redistributed work).
    """
    if original_hc <= 0:
        return base_absorption
    reduction_ratio = (original_hc - current_hc) / original_hc
    workload_increase = 1.0 + reduction_ratio  # relative to original
    return b1_capacity_absorption(
        params.base_absorption,
        workload_increase,
        1.5,  # max workload ratio
        params.workload_absorption_sensitivity,
    )


# ============================================================
# Update Human System State (one timestep)
# ============================================================

def update_human_system(
    hs: HumanSystemState,
    adoption_level: float,
    disruption_level: float,
    skill_gap_pct: float,
    cumulative_savings: float,
    original_hc: int,
    current_hc: int,
    params: FeedbackParams,
    ai_error_this_month: bool = False,
) -> HumanSystemState:
    """
    Apply all feedback loops to update human system state.
    Returns a NEW HumanSystemState (no mutation).
    """
    # R1: Trust
    delta_trust = r1_trust_adoption(hs, adoption_level, params, ai_error_this_month)

    # R2: Proficiency
    delta_prof = r2_proficiency(hs, adoption_level, params)

    # B3: Change resistance → readiness + fatigue
    delta_readiness, delta_fatigue = b3_change_resistance(hs, disruption_level, params)

    # R4: Political capital
    delta_capital = r4_political_capital(hs, adoption_level, disruption_level, params)

    # Apply deltas
    new_hs = HumanSystemState(
        proficiency=hs.proficiency + delta_prof,
        readiness=hs.readiness + delta_readiness,
        trust=hs.trust + delta_trust,
        political_capital=hs.political_capital + delta_capital,
        transformation_fatigue=hs.transformation_fatigue + delta_fatigue,
    )
    new_hs.clamp()
    return new_hs
