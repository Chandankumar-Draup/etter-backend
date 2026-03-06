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
        """
        How much of the theoretical adoption rate is achievable given human state.

        DESIGN RATIONALE (v2):
        The v1 formula used (prof/100) × (ready/100) — a joint probability model.
        This assumes independence: "only people who are BOTH proficient AND ready adopt."
        
        In reality, these are correlated CONTRIBUTING DIMENSIONS:
          - Proficiency → quality of usage (how WELL they use AI)
          - Readiness → speed of adoption (how FAST they start)
          - Trust → willingness ceiling (how MUCH they'll commit)
        
        Weighted blend treats each as a contributor to a single adoption capacity score.
        Weights: readiness(0.45) > proficiency(0.35) > trust(0.20)
        because willingness to change (readiness) is the largest behavioral driver.
        
        Floor at 0.15: even in worst-case orgs, early adopters (~15%) will use new tools.

        T2-#7 VETO MECHANISM (v2.2):
        If ANY dimension is critically low (<10), it acts as a hard blocker.
        In real organizations, near-zero trust/readiness vetoes adoption regardless
        of other dimensions. Without this, zero trust + high proficiency still allows
        25% adoption, which is unrealistic (confirmed by stress test HF-03).
        """
        # T2-#7: Veto — any critical dimension below 10 hard-caps adoption
        if self.trust < 10.0 or self.readiness < 10.0:
            return 0.05  # near-zero: only the most determined early adopters

        base = (0.35 * self.proficiency + 0.45 * self.readiness + 0.20 * self.trust) / 100.0
        return max(0.15, base)

    @property
    def trust_multiplier(self) -> float:
        """
        Trust modulates willingness — threshold-based with smooth transitions.
        
        DESIGN RATIONALE (v2.1):
        Trust acts as a behavioral gate with four regimes:
          - Below 20: CRISIS — active resistance (0.50)
          - 20-40: SKEPTICISM → CAUTIOUS — linear ramp 0.50 → 0.90
          - 40-60: CAUTIOUS → NEUTRAL — linear ramp 0.90 → 1.00
          - Above 60: ENABLER — trust no longer constrains (1.00)
        
        Smooth transitions within bands prevent discontinuous jumps in adoption
        that would create artificial "tipping points" in the simulation.
        """
        if self.trust < 20:
            return 0.50
        elif self.trust < 40:
            # Linear interpolation: 0.50 at trust=20 → 0.90 at trust=40
            return 0.50 + (self.trust - 20) / 20 * 0.40
        elif self.trust < 60:
            # Linear interpolation: 0.90 at trust=40 → 1.00 at trust=60
            return 0.90 + (self.trust - 40) / 20 * 0.10
        else:
            return 1.0

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
    fatigue_build_rate: float = 0.5         # T1-#2: was 0.03, now driven by adoption pace too
    fatigue_decay_rate: float = 0.02        # T1-#2: monthly fatigue recovery during low-change periods

    # R5: Readiness-Adoption Flywheel (missing in v1 — readiness had NO upward driver)
    readiness_boost_rate: float = 1.5       # readiness gained per month from successful adoption

    # B4: Seniority Offset
    seniority_penalty: float = 0.15         # % reduction in potential per seniority unit

    # R1: Trust-Adoption Flywheel
    trust_build_rate: float = 2.0           # trust gained per month of successful adoption
    trust_destruction_factor: float = 0.30  # % of trust lost on AI error (multiplicative, fast)
    success_probability: float = 0.85       # probability each month is a "success"

    # R2: Proficiency Flywheel
    learning_rate: float = 3.0              # proficiency gained per month of practice
    learning_saturation: float = 85.0       # diminishing returns above this level

    # T3-#1: GenAI fast-start — tool proficiency ramps in weeks, org maturity in months
    # Real-world: Copilot/ChatGPT skill acquisition = 2-8 weeks (fast).
    # Organizational workflow integration = 6-18 months (slow).
    # During first genai_fast_start_months, learning_rate is boosted.
    genai_fast_start_months: int = 6        # months of accelerated learning (tool skill ramp)
    genai_fast_start_multiplier: float = 2.0  # learning boost during fast-start phase

    # T3-#2: Workflow disruption — introducing AI disrupts existing workflows.
    # Real-world: 5-15% productivity dip for 3-6 months (McKinsey/BCG).
    # Disruption intensity scales with adoption velocity and decays over first year.
    workflow_disruption_coefficient: float = 50.0   # disruption per unit adoption velocity
    workflow_disruption_decay_months: float = 12.0  # months over which disruption decays to zero

    # T3-#3: Trust evidence thresholds — trust grows in step-function, not linear.
    # Real-world: trust builds at "evidence windows" when adoption crosses milestones.
    # Between thresholds, trust growth rate is reduced.
    trust_evidence_thresholds: tuple = (0.10, 0.25, 0.50)  # adoption milestones that unlock trust
    trust_between_threshold_rate: float = 0.50  # trust growth = 50% of normal between thresholds

    # T3-#3b: Periodic trust shocks from hallucinations/incidents.
    # Real-world: Deloitte TrustID showed -31% trust drop in 2 months of 2025.
    # Modeled as deterministic periodic shocks (reproducible, no randomness).
    # Calibrated so trust is roughly flat in moderate scenarios, declining in aggressive.
    trust_shock_interval: int = 10          # months between trust shock events
    trust_shock_magnitude: float = 1.5      # trust points lost per shock event
    trust_shock_start_month: int = 4        # first shock possible after month N

    # T3-#4: HC decision latency — organizations don't reduce headcount immediately.
    # Real-world: 6-18 month delay between "capacity freed" and "people reduced".
    # Modeled as minimum months before any HC reduction occurs.
    hc_decision_delay_months: int = 6       # no HC reductions before this month

    # T3-#5: Restructured fatigue — current system is mathematically inert.
    # Real-world: 73% of orgs report change fatigue as #1 barrier (Prosci).
    # New fatigue drivers: ongoing AI work burden + HC anxiety + baseline AI anxiety.
    fatigue_ai_work_burden: float = 0.6     # fatigue/month from working WITH AI (cognitive load)
    fatigue_hc_anxiety_factor: float = 20.0 # fatigue per HC reduction event (% of workforce reduced × factor)
    fatigue_ai_anxiety_baseline: float = 0.20  # constant fatigue/month when adoption > 0 (fear of replacement)
    fatigue_recovery_stability_bonus: float = 1.5  # extra recovery during stable periods (no HC change)

    # T3-#6: Hallucination rate — continuous background quality risk.
    # Real-world: 15-34% hallucination rates (Stanford HAI, Chelli 2024).
    # Each month, probability of trust-damaging incident scales with adoption.
    hallucination_base_rate: float = 0.08   # base monthly probability of quality incident
    hallucination_trust_damage: float = 1.5 # trust points lost per hallucination incident

    # T3-#7: Model capability step-changes (GPT-4 → 4o → o1 → o3 within 36 months).
    # Each upgrade increases automation ceiling but temporarily disrupts workflows.
    capability_upgrade_months: tuple = (12, 24)  # months when capability jumps occur
    capability_upgrade_ceiling_boost: float = 0.10  # +10% to raw adoption ceiling per upgrade
    capability_upgrade_skill_disruption: float = 3.0  # proficiency points lost per upgrade (new features)
    capability_upgrade_trust_disruption: float = 2.0  # trust points lost per upgrade (regression risk)

    # T3-#8: Shadow AI — unauthorized GenAI usage that runs ahead of official adoption.
    # Real-world: 80%+ workers use unapproved tools (UpGuard), 68% via personal accounts.
    # Shadow adoption doesn't contribute to savings but affects trust and proficiency.
    shadow_ai_speed_multiplier: float = 1.5  # shadow adoption runs 1.5x ahead of official
    shadow_ai_conversion_rate: float = 0.10  # 10% of shadow adoption converts to official per month

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
    adoption_level: float,
    params: FeedbackParams,
    adoption_velocity: float = 0.0,
    hc_reduced_pct: float = 0.0,
    is_stable_month: bool = True,
) -> tuple:
    """
    High disruption → resistance → readiness falls → adoption slows.
    Successful adoption → readiness rises (R5 reinforcing loop, added in v2).
    Also builds fatigue over time.

    Three forces on readiness:
      1. Resistance (negative): disruption pushes readiness down
      2. Recovery (positive): natural mean-reversion, constant
      3. Adoption boost (positive): seeing AI work → more willingness (R5)

    T1-#2 FATIGUE FIX (v2.2):
    Fatigue now accumulates from TWO sources:
      1. Disruption events (HC reduction) — original signal
      2. Adoption velocity (pace of change) — NEW

    T3-#5 FATIGUE RESTRUCTURE (v3):
    Previous system was mathematically inert (0→1.1 on 0-100 scale).
    New fatigue model has FOUR drivers:
      1. AI work burden: continuous cognitive load of working WITH AI
      2. HC reduction anxiety: fear and disruption from layoff events
      3. AI replacement anxiety: persistent baseline fear when AI is deployed
      4. Recovery: enhanced during stable periods (no HC changes)
    Target: fatigue reaches 15-30 by M12 in moderate, 40-60 in aggressive scenarios.

    Returns: (delta_readiness, delta_fatigue)
    """
    # Resistance force: proportional to disruption, inversely to trust
    trust_dampening = max(0.3, hs.trust / 100.0)
    resistance = disruption_level * params.resistance_sensitivity / trust_dampening

    # T3-#5: Restructured fatigue from FOUR sources
    # Source 1: Ongoing AI work burden (cognitive load of working with AI tools)
    ai_work_fatigue = params.fatigue_ai_work_burden * adoption_level

    # Source 2: HC reduction anxiety (sharp spike when people are laid off)
    hc_anxiety = params.fatigue_hc_anxiety_factor * hc_reduced_pct

    # Source 3: AI replacement anxiety (constant background fear when AI is present)
    ai_anxiety = params.fatigue_ai_anxiety_baseline if adoption_level > 0.01 else 0.0

    # Source 4: Adoption pace fatigue (original T1-#2 mechanism, retained)
    pace_fatigue = adoption_velocity * params.fatigue_build_rate * 10.0

    # Source 5: Disruption event fatigue (original mechanism, retained)
    disruption_fatigue = disruption_level * params.fatigue_build_rate

    # Recovery: natural decay, enhanced during stable months
    base_decay = params.fatigue_decay_rate * (1.0 - adoption_level)
    stability_bonus = params.fatigue_recovery_stability_bonus if is_stable_month else 0.0
    fatigue_recovery = base_decay + stability_bonus * params.fatigue_decay_rate

    fatigue_delta = (
        ai_work_fatigue + hc_anxiety + ai_anxiety + pace_fatigue + disruption_fatigue
        - fatigue_recovery
    )

    # Readiness change: resistance pushes down, natural recovery pushes up
    # Recovery is stronger when fatigue is low
    recovery = params.resistance_decay_rate * (1 - hs.transformation_fatigue / 100)

    # R5: Adoption-driven readiness boost (v2 addition)
    # Seeing AI work successfully makes people MORE ready to adopt
    # Diminishing returns at high readiness (already convinced)
    readiness_ceiling = max(0.1, 1.0 - hs.readiness / 100.0)
    adoption_boost = params.readiness_boost_rate * adoption_level * readiness_ceiling

    delta_readiness = -resistance + recovery + adoption_boost

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

    T3-#3 TRUST EVIDENCE THRESHOLDS (v3):
    Trust grows in step-function, not smoothly. Between evidence thresholds
    (10%, 25%, 50% adoption), trust growth is reduced to 33% of normal.
    When adoption crosses a threshold, the full trust build rate applies.
    This produces the "evidence window" pattern observed in real deployments.

    Returns: delta_trust
    """
    if ai_error_this_month:
        # Multiplicative destruction — 30% of current trust wiped
        return -hs.trust * params.trust_destruction_factor

    # Additive building — proportional to adoption level and success rate
    build = params.trust_build_rate * adoption_level * params.success_probability
    # Diminishing returns at high trust
    ceiling_factor = max(0.1, 1.0 - hs.trust / 100.0)
    base_delta = build * ceiling_factor

    # T3-#3: Apply evidence threshold gating
    # Check if adoption is within ±2% of any evidence threshold (at threshold = full rate)
    # Otherwise, between thresholds = reduced rate
    at_threshold = False
    for threshold in params.trust_evidence_thresholds:
        if abs(adoption_level - threshold) < 0.02:
            at_threshold = True
            break

    if not at_threshold:
        base_delta *= params.trust_between_threshold_rate

    return base_delta


# ============================================================
# R2: Proficiency Flywheel (Reinforcing)
# ============================================================

def r2_proficiency(
    hs: HumanSystemState,
    adoption_level: float,
    params: FeedbackParams,
    learning_velocity_factor: float = 1.0,
    month: int = 0,
) -> float:
    """
    More adoption → more practice → more proficiency → better results.
    Follows a learning curve with diminishing returns.

    T1-#6 LEARNING VELOCITY (v2.2):
    Per-function learning speed from human_system.csv. Technology (3mo) learns
    2x faster than the baseline (6mo), while Claims (8mo) learns 0.75x.
    learning_velocity_factor = baseline_months / function_months.

    T3-#1 GENAI FAST-START (v3):
    GenAI tools have fast individual learning curves (2-8 weeks). During the
    first genai_fast_start_months, learning rate is boosted by the fast-start
    multiplier. This captures the rapid "tool skill" acquisition followed by
    slower "organizational proficiency" growth.

    Returns: delta_proficiency
    """
    practice_intensity = adoption_level  # 0→1
    # Diminishing returns above saturation point
    ceiling_factor = max(0.05, 1.0 - hs.proficiency / params.learning_saturation)

    # T3-#1: Fast-start boost during initial tool skill acquisition phase
    effective_learning_rate = params.learning_rate
    if month < params.genai_fast_start_months:
        effective_learning_rate *= params.genai_fast_start_multiplier

    # T1-#6: Scale by function-specific learning velocity
    return effective_learning_rate * practice_intensity * ceiling_factor * learning_velocity_factor


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
    
    v2 FIX: At zero HC reduction, absorption = base_absorption (0.30).
    v1 BUG: workload_increase started at 1.0, making initial absorption 0.43.
    The overload signal should be the REDUCTION RATIO, not total workload.
    """
    if original_hc <= 0:
        return base_absorption
    reduction_ratio = (original_hc - current_hc) / original_hc
    return b1_capacity_absorption(
        params.base_absorption,
        reduction_ratio,       # v2: 0 at start, grows with HC reduction
        0.5,                   # v2: max overload at 50% HC reduction
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
    adoption_velocity: float = 0.0,
    learning_velocity_factor: float = 1.0,
    month: int = 0,
    hc_reduced_pct: float = 0.0,
    is_stable_month: bool = True,
) -> HumanSystemState:
    """
    Apply all feedback loops to update human system state.
    Returns a NEW HumanSystemState (no mutation).

    v2.2: Added adoption_velocity for fatigue calculation (T1-#2)
          and learning_velocity_factor for per-function proficiency (T1-#6).
    v3:   Added month for T3-#1 fast-start, hc_reduced_pct for T3-#5 fatigue,
          is_stable_month for T3-#5 recovery bonus.
    """
    # R1: Trust
    delta_trust = r1_trust_adoption(hs, adoption_level, params, ai_error_this_month)

    # R2: Proficiency (T1-#6: learning velocity, T3-#1: fast-start)
    delta_prof = r2_proficiency(
        hs, adoption_level, params, learning_velocity_factor, month=month,
    )

    # B3: Change resistance → readiness + fatigue (T1-#2 + T3-#5)
    delta_readiness, delta_fatigue = b3_change_resistance(
        hs, disruption_level, adoption_level, params, adoption_velocity,
        hc_reduced_pct=hc_reduced_pct,
        is_stable_month=is_stable_month,
    )

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
