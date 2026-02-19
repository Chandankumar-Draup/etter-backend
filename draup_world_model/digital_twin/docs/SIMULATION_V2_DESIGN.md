# Simulation v2: Systems Dynamics Design

## Critical Analysis of Current Results

### What's Wrong with Role Redesign ($49M, 480% ROI)

The 480% ROI is **dangerously unrealistic** because:

1. **No technology cost**: Role redesign assumes tasks magically automate themselves.
   Automation requires tools. A 15.3% headcount reduction across 2,250 people requires
   enterprise AI investment — easily $5-15M in licensing alone. Yet cost = $8.5M (reskilling only).

2. **Instant transition**: The cascade runs once, producing a month-36 snapshot.
   No J-curve productivity dip. No 6-month adoption lag. No change management friction.
   Day 1 and Day 1,080 are treated identically.

3. **No resistance**: 346 people freed overnight, zero organizational friction.
   Real enterprises take 18-36 months to reduce headcount by 15%.
   Union negotiations, morale impact, institutional knowledge loss — all invisible.

4. **Linear savings**: `salary × headcount × freed% × 3 years`.
   No wage inflation. No diminishing returns. No attrition of the freed workers
   (who leave before you redeploy them, losing institutional knowledge).

5. **60% redeployable is assumed, not earned**: The model asserts 60% can be
   redeployed with no mechanism to validate this. If redeployment takes 12 months
   but freed workers attrit at 20%/year, actual redeployment is ~48%.

### What's Wrong with Tech Adoption ($9.1M, 84.6% ROI)

Better, but still oversimplified:

1. **Keyword matching is crude**: Copilot matches 69/335 tasks by word boundary.
   "Report" matches regardless of whether Copilot can actually help with that specific
   report type. No confidence weighting flows into the cascade — a 30% match and
   a 95% match produce identical automation shifts.

2. **Uniform classification shift**: All 69 matched tasks shift to "shared" regardless
   of their complexity, data sensitivity, or regulatory constraints. A claims fraud
   investigation document shouldn't automate at the same rate as a meeting summary.

3. **License cost is scope-wide**: $30/user/month × 2,250 headcount × 36 months.
   But only 21 roles are affected. Licensing the entire function when only 60% of
   roles benefit inflates costs (or understates per-role value).

4. **Adoption curve is cosmetic**: The adoption discount adjusts the final number
   but doesn't model month-by-month dynamics. There's no feedback from slow adoption
   to budget reallocation or scope reduction.

5. **No competitive context**: Is Copilot the right tool? What if UiPath handles
   some tasks better? No multi-technology portfolio optimization exists.

---

## The Fundamental Problem: Calculator vs. Flight Simulator

The current simulation is a **calculator**: input parameters, get a static snapshot.

What's needed is a **flight simulator**: set initial conditions, watch dynamics
unfold over time, intervene mid-simulation, observe feedback effects.

```
v1 (Calculator):
  Inputs → [8-step cascade, single pass] → Static output

v2 (Flight Simulator):
  Initial state → [monthly time steps × 36] → Time-series trajectory
                    ↑                    ↓
                    └── feedback loops ──┘
```

---

## System Boundary Definition

### Endogenous (computed by the model)

These variables are INTERNAL to the system — they evolve through stocks and flows:

- Workforce composition (headcount by band, function, skill)
- Skill competency levels (org proficiency per skill)
- Technology adoption level (fraction of org actively using)
- Financial accumulators (savings realized, costs incurred, budget remaining)
- Human factors (resistance, morale, proficiency, culture readiness)
- Risk levels (automation concentration, skill gaps, workforce reduction)

### Exogenous (user-supplied scenario parameters)

These are EXTERNAL inputs the model does not compute:

- Market: labor market tightness, wage inflation rate, talent availability
- Regulatory: constraint level, compliance cost multiplier
- Technology: vendor capability roadmap, maturity trajectory
- Competition: industry adoption benchmark, talent poaching pressure
- Economic: discount rate (for NPV), budget growth rate, inflation

### System Boundary Diagram

```
┌──────────────────────── SYSTEM BOUNDARY ────────────────────────┐
│                                                                  │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐   │
│  │  WORKFORCE   │────▶│  SKILL       │────▶│  FINANCIAL     │   │
│  │  STOCK       │◀────│  STOCK       │◀────│  STOCK         │   │
│  │              │     │              │     │                │   │
│  │  headcount[] │     │  competency[]│     │  savings       │   │
│  │  by band,    │     │  by skill    │     │  costs         │   │
│  │  function    │     │              │     │  budget        │   │
│  └──────┬───────┘     └──────┬───────┘     └────────┬───────┘   │
│         │                    │                      │           │
│         ▼                    ▼                      ▼           │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐   │
│  │  TECHNOLOGY  │────▶│  HUMAN       │────▶│  RISK          │   │
│  │  ADOPTION    │◀────│  FACTORS     │◀────│  ASSESSMENT    │   │
│  │  STOCK       │     │              │     │                │   │
│  │  adoption[]  │     │  resistance  │     │  risk_flags[]  │   │
│  │  by tech     │     │  morale      │     │                │   │
│  │              │     │  proficiency │     │                │   │
│  └──────────────┘     │  culture     │     └────────────────┘   │
│                       └──────────────┘                          │
│                                                                  │
├──────────────────────── EXOGENOUS INPUTS ───────────────────────┤
│  labor_market │ regulation │ tech_roadmap │ competition │ macro │
└──────────────────────────────────────────────────────────────────┘
```

---

## Stocks and Flows

### Stock 1: Workforce

```
┌───────────────────────────────────────────┐
│           WORKFORCE STOCK                 │
│    Employees[band][function][skill_set]   │
├───────────────────────────────────────────┤
│                                           │
│  INFLOWS:                                 │
│    + hiring_rate(band, market_tightness)  │
│    + reskill_completion_rate              │
│    + redeployment_rate                    │
│    + promotion_in_rate                    │
│                                           │
│  OUTFLOWS:                                │
│    - voluntary_attrition(morale)          │
│    - retirement_rate                      │
│    - separation_rate(freed_capacity)      │
│    - reskill_entry_rate (temporary out)   │
│    - promotion_out_rate                   │
│                                           │
│  d(E)/dt = inflows - outflows             │
│                                           │
│  KEY DYNAMICS:                            │
│    attrition = base_rate × (1 + anxiety)  │
│    anxiety = f(pace_of_change, morale)    │
│    redeployment_delay = 3-12 months       │
└───────────────────────────────────────────┘
```

### Stock 2: Technology Adoption

```
┌───────────────────────────────────────────┐
│       TECHNOLOGY ADOPTION STOCK           │
│    Adoption[technology] : 0.0 → 1.0       │
├───────────────────────────────────────────┤
│                                           │
│  FLOW (Bass Diffusion + modifiers):       │
│                                           │
│  dA/dt = [p + q × A/M] × [M - A]         │
│          × human_factor_multiplier        │
│          × (1 - regulatory_brake)         │
│          × org_readiness                  │
│                                           │
│  p = innovation coefficient (0.01-0.03)   │
│  q = imitation coefficient (0.3-0.8)      │
│  M = max potential adopters               │
│  A = current adopters                     │
│                                           │
│  MODIFIERS:                               │
│    human_factor = f(resistance, proficiency)│
│    regulatory_brake = exogenous (0-1)     │
│    org_readiness = f(culture, leadership) │
└───────────────────────────────────────────┘
```

### Stock 3: Skill Competency

```
┌───────────────────────────────────────────┐
│        SKILL COMPETENCY STOCK             │
│    Competency[skill] : 0.0 → 1.0          │
├───────────────────────────────────────────┤
│                                           │
│  INFLOWS:                                 │
│    + training_effect(reskill_investment)   │
│    + learning_by_doing(adoption_level)    │
│    + external_hire_skills                 │
│                                           │
│  OUTFLOWS:                                │
│    - skill_decay(unused_months)           │
│    - knowledge_loss(attrition_rate)       │
│    - obsolescence(tech_evolution)         │
│                                           │
│  DYNAMICS:                                │
│    proficiency(t) = max × (1 - e^(-λt))   │
│    λ = learning_rate × training_quality   │
│    decay = competency × 0.05/month unused │
└───────────────────────────────────────────┘
```

### Stock 4: Financial

```
┌───────────────────────────────────────────┐
│         FINANCIAL STOCK                   │
│    Budget, Savings, Costs                 │
├───────────────────────────────────────────┤
│                                           │
│  INFLOWS:                                 │
│    + budget_allocation(annual_cycle)      │
│    + realized_savings(adoption × freed)   │
│    + roi_reinvestment(savings × rate)     │
│                                           │
│  OUTFLOWS:                                │
│    - licensing_cost(adoption × per_user)  │
│    - implementation_cost(phased)          │
│    - reskilling_spend(per_month)          │
│    - severance_cost(separation_rate)      │
│    - change_mgmt_cost(ongoing)            │
│                                           │
│  KEY: Savings only accrue to the extent   │
│  adoption has ACTUALLY reached that level │
│  NOT the theoretical maximum              │
│                                           │
│  realized_savings(t) =                    │
│    Σ (title_salary × freed_pct            │
│       × adoption_level(t)                 │
│       × proficiency(t))                   │
│    / 12  (monthly)                        │
└───────────────────────────────────────────┘
```

### Stock 5: Human Factors

```
┌───────────────────────────────────────────┐
│        HUMAN FACTORS (4 sub-stocks)       │
├───────────────────────────────────────────┤
│                                           │
│  RESISTANCE (0-1, starts at 0.6):         │
│    dR/dt = change_shock                   │
│            - adaptation_rate              │
│            - communication_investment     │
│    change_shock = pace × uncertainty      │
│    adaptation_rate = R × 0.05/month       │
│                                           │
│  MORALE (0-1, starts at 0.7):             │
│    dM/dt = + skill_growth_signal          │
│            + career_opportunity_signal    │
│            - layoff_shock                 │
│            - uncertainty_drag            │
│    layoff_shock = separation_rate × 0.3   │
│                                           │
│  PROFICIENCY (0-1, starts at 0.1):        │
│    dP/dt = learning_rate × (1 - P)        │
│    learning_rate = training_investment    │
│                    × aptitude(band)       │
│                                           │
│  CULTURE READINESS (0-1, starts at 0.3):  │
│    dC/dt = -(C - target) / τ              │
│    τ = 12-36 months (org size dependent)  │
│    target = leadership_vision (exogenous) │
│                                           │
│  COMPOSITE MULTIPLIER:                    │
│    HFM = 0.30×(1-R) + 0.25×P             │
│         + 0.20×M    + 0.25×C             │
│    Applied to: adoption rate, freed       │
│    capacity effectiveness, savings rate   │
└───────────────────────────────────────────┘
```

---

## Feedback Loops

### Reinforcing Loops (self-amplifying)

```
R1: PRODUCTIVITY FLYWHEEL
    AI Adoption ──▶ Productivity Gains ──▶ Cost Savings
         ▲                                      │
         └──── Budget for More AI ◀─────────────┘

R2: CAPABILITY COMPOUNDING
    AI Usage ──▶ AI Literacy Improves ──▶ Better AI Application
       ▲                                       │
       └────── More Value from AI ◀────────────┘

R3: TALENT MAGNET
    AI Reputation ──▶ Attracts Tech Talent ──▶ Better Implementation
         ▲                                          │
         └──────── Stronger Reputation ◀────────────┘
```

### Balancing Loops (self-correcting)

```
B1: CHANGE RESISTANCE
    Pace of Change ──▶ Employee Anxiety ──▶ Resistance
         ▲                                      │
         └──── Slower Implementation ◀──────────┘

B2: SKILL GAP BRAKE
    AI Deployment ──▶ New Skill Requirements ──▶ Skill Gaps
         ▲                                           │
         └──── Reduced Effective Adoption ◀──────────┘

B3: KNOWLEDGE DRAIN
    Headcount Reduction ──▶ Knowledge Loss ──▶ Quality Issues
            ▲                                       │
            └──── Pressure to Rehire/Slow ◀─────────┘

B4: ORGANIZATIONAL FATIGUE
    Change Initiatives ──▶ Org Load ──▶ Change Fatigue
            ▲                                │
            └──── Reduced Capacity ◀─────────┘

B5: REGULATORY RESPONSE
    AI Incidents ──▶ Scrutiny ──▶ Compliance Requirements
         ▲                              │
         └── Slower/Costlier Deploy ◀───┘
```

### Critical Delay Constants

| Delay | Duration | Effect |
|-------|----------|--------|
| Training lag | 3-12 months | Skills supply lags demand |
| Cultural adoption | 6-18 months | Behavior trails tool deployment |
| Technology maturation | 6-24 months | Full ROI lags initial deployment |
| Productivity J-curve | 3-9 months | Performance temporarily DROPS then rises |
| Redeployment pipeline | 3-12 months | Freed workers can't move instantly |
| Knowledge codification | 6-12 months | Tacit knowledge takes time to document |
| Hiring pipeline | 2-6 months | Can't instantly scale workforce |

---

## User-Controllable Levers

### Tier 1: Task Distribution Controls (Per Stage)

Users MUST be able to adjust the task automation distribution at each stage.
Instead of the engine deciding everything, the user sets target distributions:

```python
@dataclass
class TaskDistributionControl:
    """User-defined target task distribution by automation level."""
    # What percentage of tasks should be at each level
    human_only_pct: float = 10.0     # User adjustable
    human_led_pct: float = 30.0      # User adjustable
    shared_pct: float = 35.0         # User adjustable (Human+AI)
    ai_led_pct: float = 20.0         # User adjustable
    ai_only_pct: float = 5.0         # User adjustable
    # Must sum to 100%

    # Which classification categories to include
    target_classifications: List[str] = field(default_factory=lambda: [
        "directive", "feedback_loop", "validation"
    ])

    # Transition constraints
    max_steps_per_task: int = 1       # How many levels a task can jump
    min_confidence_for_shift: float = 0.5  # Minimum match confidence
```

This replaces the current binary "factor=0.3 advances everything by 1 step".
Users see the current distribution, set a target, and the engine computes the
minimum changes needed to reach that target.

### Tier 2: Organizational Parameters

```python
@dataclass
class OrganizationProfile:
    """Organization-specific parameters that override defaults."""
    # Workforce dynamics
    redeployability_pct: float = 60.0      # Currently hardcoded
    base_attrition_rate: float = 12.0      # Annual % voluntary turnover
    reskilling_pct_per_band: float = 30.0  # % needing reskilling

    # Human factors initial conditions
    initial_resistance: float = 0.6         # 0=none, 1=total
    initial_morale: float = 0.7             # 0=low, 1=high
    initial_ai_proficiency: float = 0.1     # 0=none, 1=expert
    initial_culture_readiness: float = 0.3  # 0=resistant, 1=ready
    culture_time_constant_months: int = 24  # Inertia

    # Financial
    change_management_budget_pct: float = 5.0  # % of savings allocated
    severance_months_per_employee: int = 3     # Severance package

    # Level-specific impact factors (user can override)
    level_impact_factors: Dict[str, float] = field(default_factory=lambda: {
        "entry": 1.4, "mid": 1.2, "senior": 1.0,
        "lead": 0.8, "principal": 0.6,
        "director": 0.4, "vp": 0.3, "c_suite": 0.2,
    })

    # Risk appetite
    max_headcount_reduction_pct: float = 25.0
    max_roles_redesigned_pct: float = 50.0
    protected_roles: List[str] = field(default_factory=list)
```

### Tier 3: Technology Parameters

```python
@dataclass
class TechnologyConfig:
    """User-configurable technology parameters."""
    name: str
    license_cost_per_user_month: float  # Actual negotiated price
    implementation_cost_total: float     # Actual estimate
    adoption_speed: str = "moderate"     # or custom curve
    custom_adoption_curve: Optional[Dict[int, float]] = None
    capabilities: List[str] = field(default_factory=list)
    task_keywords: List[str] = field(default_factory=list)
    classification_shift: str = "shared"
    confidence_threshold: float = 0.5    # Min match to include

    # Phasing
    deployment_phases: int = 3           # Staggered rollout
    phase_gap_months: int = 3            # Gap between phases
```

### Tier 4: Exogenous Scenario Parameters

```python
@dataclass
class ExogenousScenario:
    """External environment parameters."""
    # Market
    labor_market_tightness: float = 0.5   # 0=loose, 1=tight
    annual_wage_inflation_pct: float = 3.0

    # Regulatory
    regulatory_constraint_level: float = 0.3  # 0=none, 1=heavy
    compliance_cost_multiplier: float = 1.0

    # Competition
    industry_adoption_benchmark: float = 0.3  # How far the industry has gone
    talent_poaching_pressure: float = 0.2

    # Economic
    discount_rate: float = 0.10        # For NPV/IRR calculations
    annual_budget_growth_pct: float = 5.0
```

---

## The Time-Stepped Engine

### Architecture

```
SimulationV2Engine
├── TimeStepLoop (NEW — the core evolution)
│   ├── ExogenousInputManager (reads per-month external params)
│   ├── AdoptionDynamics (Bass diffusion, replaces ADOPTION_CURVES)
│   ├── HumanFactorEngine (resistance, morale, proficiency, culture)
│   ├── CascadeEngine (EXISTING — called per time step with current state)
│   ├── FeedbackComputer (R1-R3, B1-B5 loop calculations)
│   └── StockUpdater (Euler integration of all stock differentials)
├── ScenarioManager (EXISTING — extended for time-series)
├── FinancialProjection (EXISTING — extended for monthly NPV)
└── InterventionScheduler (NEW — user mid-simulation actions)
```

### Time Step Loop (Pseudocode)

```python
def simulate(initial_state, config, timeline_months):
    state = initial_state
    trajectory = []

    for month in range(1, timeline_months + 1):
        # 1. Apply exogenous inputs
        exo = config.exogenous.for_month(month)

        # 2. Compute human factor multiplier
        hfm = human_factors.compute_multiplier(state)

        # 3. Update adoption level (Bass diffusion)
        state.adoption = adoption.step(
            state.adoption, hfm, exo.regulatory_brake
        )

        # 4. Apply user-scheduled interventions for this month
        interventions = config.interventions.for_month(month)
        if interventions:
            state = apply_interventions(state, interventions)

        # 5. Run cascade with current adoption level
        effective_freed = cascade.run_partial(
            state.scope_data,
            state.task_reclassifications,
            adoption_level=state.adoption,
            human_factor=hfm,
        )

        # 6. Update financial stocks (monthly)
        state.financial = financial.step(
            state, effective_freed, exo
        )

        # 7. Update workforce stocks (hiring, attrition, separation)
        state.workforce = workforce.step(
            state, effective_freed, exo
        )

        # 8. Update human factor stocks
        state.human_factors = human_factors.step(
            state, month
        )

        # 9. Compute feedback effects
        feedback = compute_feedback(state, month)
        state = apply_feedback(state, feedback)

        # 10. Risk assessment
        state.risks = assess_risks(state, month)

        # 11. Record snapshot
        trajectory.append(state.snapshot(month))

    return SimulationTrajectory(trajectory)
```

### Monthly Output Structure

Each month produces a snapshot:

```python
{
    "month": 12,
    "stocks": {
        "workforce": {
            "total_headcount": 2150,
            "by_band": {"entry": 620, "mid": 580, "senior": 520, ...},
            "in_reskilling": 85,
            "separated_ytd": 42,
            "redeployed_ytd": 28,
        },
        "adoption": {
            "level": 0.45,  # 45% effective adoption
            "monthly_delta": 0.03,
        },
        "skills": {
            "avg_ai_proficiency": 0.35,
            "sunrise_competency": {"AI Literacy": 0.42, ...},
            "sunset_competency": {"Manual Data Entry": 0.65, ...},
        },
        "financial": {
            "cumulative_savings": 4_200_000,
            "cumulative_costs": 3_800_000,
            "monthly_net": 120_000,
            "npv_to_date": 350_000,
            "budget_remaining": 1_200_000,
        },
        "human_factors": {
            "resistance": 0.42,
            "morale": 0.65,
            "proficiency": 0.35,
            "culture_readiness": 0.38,
            "composite_multiplier": 0.52,
        },
    },
    "flows_this_month": {
        "hired": 12,
        "attrited": 8,
        "separated": 5,
        "entered_reskilling": 15,
        "completed_reskilling": 10,
        "redeployed": 3,
    },
    "active_feedback_loops": ["R1", "B1", "B2"],
    "risks": {...},
}
```

---

## What Role Redesign Should Include (Missing Costs)

Currently role_redesign has ZERO technology cost. v2 must include:

```
ROLE REDESIGN COST MODEL:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Technology cost (NEW):                                      │
│    Automation of 135 tasks requires tools.                   │
│    Estimate: $30/user/mo × affected_headcount × months       │
│    Or: user specifies technology portfolio                   │
│                                                              │
│  Change management cost (NEW):                               │
│    5-10% of gross savings, phased over 12-18 months          │
│    Includes: communication, stakeholder management,          │
│    pilot programs, feedback collection                       │
│                                                              │
│  Severance cost (NEW):                                       │
│    For non-redeployable workers:                             │
│    separated_hc × avg_salary × severance_months / 12        │
│                                                              │
│  Productivity dip cost (NEW):                                │
│    J-curve: months 1-6, productivity drops 10-20%            │
│    Before rising above baseline                              │
│    Cost = headcount × salary × dip% × dip_months / 12       │
│                                                              │
│  Reskilling cost (existing, enhanced):                       │
│    Band-weighted, time-phased, success-rate-adjusted         │
│                                                              │
│  TOTAL REALISTIC COST ≈ 2-3× current estimate               │
│  ROI drops from 480% → 80-150% (still positive, now real)   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Hardcoded Constants → User-Configurable Parameters

Every hardcoded constant becomes a configurable parameter with a sensible default:

| Constant | Current Value | Default | Configurable Via |
|----------|--------------|---------|-----------------|
| Redeployability % | 60% | 60% | OrganizationProfile |
| Reskilling % per band | 30% | 30% | OrganizationProfile |
| Level impact factors | 0.2-1.4 | 0.2-1.4 | OrganizationProfile |
| Reskilling cost/skill | $2,500 | $2,500 | SimulationConfig |
| Implementation cost factor | 15% | 15% | TechnologyConfig |
| Sunset skill threshold | 30% | 30% | SimulationConfig |
| Redesign trigger | 40% freed | 40% | SimulationConfig |
| Risk thresholds | 60/20/5/50 | 60/20/5/50 | RiskConfig |
| Adoption curves | 3 presets | 3 presets | TechnologyConfig |
| Reskilling timelines | 2-8 months | 2-8 months | SkillConfig |
| Band cost multipliers | 0.7-2.5 | 0.7-2.5 | SkillConfig |
| Change mgmt budget | (none) | 5% | OrganizationProfile |
| Severance months | (none) | 3 | OrganizationProfile |
| Base attrition rate | (none) | 12%/yr | OrganizationProfile |

---

## Implementation Phases

### Phase 3.9: Foundation (Make Constants Configurable)

**Goal**: Zero new features, but every hardcoded constant becomes a parameter.

Files to modify:
- `config.py` — Add SimulationConfig, OrganizationProfile, RiskConfig dataclasses
- `cascade_engine.py` — Accept config parameter, use it instead of hardcoded values
- `financial.py` — Accept configurable cost parameters
- `role_redesign.py` — Add technology cost estimation to role redesign
- `tech_adoption.py` — Accept user-defined technology profiles
- `skills_strategy.py` — Accept configurable thresholds
- `scenario_manager.py` — Pass config through to all simulations

Estimated scope: ~400 lines changed across 7 files.

### Phase 3.10: Task Distribution Controls

**Goal**: Users set target automation distribution, engine computes minimum changes.

New module: `task_distributor.py`
- Input: current task distribution + target distribution
- Output: task reclassifications that minimize total moves
- Respects constraints: max_steps_per_task, classification filters
- Visualizable: before/after distribution chart

Estimated scope: ~300 lines new, ~100 lines modified.

### Phase 3.11: Human Factors Engine

**Goal**: Model resistance, morale, proficiency, culture as evolving stocks.

New module: `human_factors.py`
- 4 stock variables with differential equations
- Composite Human Factor Multiplier
- Applied to cascade freed capacity and financial projections
- Initial conditions from OrganizationProfile

Estimated scope: ~400 lines new, ~150 lines modified.

### Phase 3.12: Time-Stepped Simulation Loop

**Goal**: Monthly time stepping with stock evolution and feedback loops.

New module: `simulation_engine_v2.py`
- Time step loop (Euler integration)
- Stock updaters for all 5 stock types
- Feedback loop computation (R1-R3, B1-B5)
- Monthly snapshot recording
- Wraps existing CascadeEngine (does NOT replace it)

Modified: `scenario_manager.py` — Support v2 engine alongside v1
Modified: `run_simulation.py` — CLI flag for v1 vs v2 engine

Estimated scope: ~800 lines new, ~200 lines modified.

### Phase 3.13: Enhanced Financial Model

**Goal**: Monthly NPV, J-curve productivity dip, phased costs, severance.

Modified: `financial.py`
- Monthly cash flow computation
- NPV, IRR calculations
- J-curve productivity model
- Severance and change management costs
- Savings conditioned on adoption level AND proficiency

Estimated scope: ~300 lines new, ~200 lines modified.

### Phase 3.14: Sensitivity Analysis & Scenario Comparison

**Goal**: Parameter sweeps, Tornado charts, scenario branching.

New module: `sensitivity.py`
- Run simulation N times with varied parameters
- Produce min/max/mean trajectories
- Identify most sensitive parameters (Tornado chart data)
- Scenario branching from any month

Estimated scope: ~400 lines new.

---

## Comparison: v1 Output vs v2 Output

### v1 (Current)
```
SIMULATION RESULT: Role Redesign - Claims Management
====================================================
Tasks affected:     135
Roles affected:     22
Freed headcount:    346         ← single number, instant
Reduction:          15.3%
Gross savings:      $49,084,914 ← assumes 100% from day 1
Total cost:         $8,462,500  ← reskilling only
Net impact:         $40,622,414
ROI:                480.0%      ← unrealistic
Payback:            6 months
```

### v2 (Target)
```
SIMULATION RESULT: Role Redesign - Claims Management (v2)
==========================================================
Timeline:           36 months
Technology:         Microsoft Copilot + UiPath (user-selected)

TRAJECTORY SUMMARY:
  Month  6: Adoption  35% | Freed HC   82 | Savings  $2.1M | Morale 0.58
  Month 12: Adoption  62% | Freed HC  168 | Savings  $8.4M | Morale 0.62
  Month 18: Adoption  78% | Freed HC  234 | Savings $17.2M | Morale 0.68
  Month 24: Adoption  88% | Freed HC  289 | Savings $27.1M | Morale 0.72
  Month 36: Adoption  95% | Freed HC  329 | Savings $41.8M | Morale 0.75

FINANCIAL (NPV @ 10% discount):
  Gross savings:      $41,800,000 (adoption-adjusted, J-curve included)
  Technology cost:    $12,400,000 (Copilot + UiPath licensing + impl.)
  Change mgmt cost:   $2,100,000 (5% of savings)
  Reskilling cost:     $8,462,500
  Severance cost:      $1,850,000 (non-redeployable × 3 months)
  Total cost:         $24,812,500
  Net impact (NPV):  $14,200,000
  IRR:                 42%
  ROI:                 68.5%       ← realistic
  Payback:             22 months   ← realistic

HUMAN FACTORS (month 36):
  Resistance:  0.18 (started 0.60 — 70% reduction over 36mo)
  Morale:      0.75 (dipped to 0.55 at month 6, recovered)
  Proficiency: 0.82 (steady growth from 0.10)
  Culture:     0.65 (slow shift from 0.30, τ=24mo)

FEEDBACK LOOPS ACTIVE:
  R1: Productivity flywheel engaged from month 14
  B1: Resistance peaked at month 4, declining since
  B2: Skill gap braked adoption months 3-9, resolved by month 12
  B3: Knowledge drain risk LOW (attrition contained)

TASK DISTRIBUTION (user target achieved):
  Human only:  8% (was 13%)
  Human-led:  25% (was 47%)
  Shared:     40% (was 26%) ← Human+AI, user target met
  AI-led:     22% (was 14%)
  AI-only:     5% (was 0%)

RISKS:
  [MEDIUM] broad_change: 135 tasks — phased rollout recommended
  [LOW] morale_dip: Expected month 3-8, recovers by month 12
  [LOW] skill_gap: 4 sunrise skills needed, training underway
```

---

## Summary: Current vs. Target Model

| Dimension | v1 (Current) | v2 (Target) |
|-----------|-------------|-------------|
| Time | Single snapshot | Monthly time series (1-60 months) |
| Causality | Linear open-loop cascade | Circular closed-loop feedback |
| Adoption | Pre-computed lookup table | Bass diffusion + org modifiers |
| Human factors | Not modeled | 4 stocks: resistance, morale, proficiency, culture |
| Feedback | None | 3 reinforcing + 5 balancing loops |
| Delays | None (instantaneous) | Training, cultural, J-curve, redeployment |
| Costs | Reskilling only (role redesign) | Tech + change mgmt + severance + J-curve + reskilling |
| Financial | Simple ROI | NPV, IRR, monthly cash flow |
| User control | automation_factor (0-1) | Task distribution, org profile, tech config, exogenous scenario |
| Output | Single dict | Time-series trajectory with monthly snapshots |
| Exogenous | Implicit | Explicit scenario parameters |
| Validation | 3 sanity checks | Conservation laws + bounds at every time step |
