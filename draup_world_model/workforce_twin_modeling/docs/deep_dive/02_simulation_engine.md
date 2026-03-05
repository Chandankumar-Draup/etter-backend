# Simulation Engine — Deep Dive

## Turning the Faucets On

*"The behavior of a system cannot be known just by knowing the elements of which the system is made."*
*— Donella Meadows, Thinking in Systems*

The data layer captures **what the organization is**. The simulation engine answers **what happens next**. It takes the seven stocks, applies stimuli (technology deployment, headcount changes, budget constraints), and propagates effects through a 9-step cascade. Then it runs that cascade forward in time with S-curve adoption, 8 feedback loops, and human system dynamics that evolve month by month.

This document covers the complete simulation architecture: the cascade engine, the feedback system, the rate equations, and the time-stepped simulator.

---

## 1. First Principles: Why This Architecture?

### The Core Problem

Naive workforce planning: "This tool can automate 40% of tasks, so we save 40% of costs." This is wrong for five reasons, each captured by the engine:

1. **Redistribution dampening** — Not all freed capacity converts to savings. Remaining workers absorb 30-60% of freed hours.
2. **Skill valley** — Productivity dips before it rises. Workers have new tools but not the skills to use them.
3. **Trust asymmetry** — One AI error destroys more trust than ten successes build.
4. **Seniority shift** — Entry-level roles automate first. Remaining workforce is more senior and harder to automate.
5. **Political capital** — Early wins enable bigger moves. Early failures lock in caution.

### The Design Decision

**Three layers of simulation, each adding one level of complexity:**

| Layer | Module | What It Adds |
|-------|--------|-------------|
| Cascade | `engine/cascade.py` | 9-step propagation at a single point in time |
| Open-Loop | `engine/simulator.py` | S-curve adoption over 36 months, no feedback |
| Closed-Loop | `engine/simulator_fb.py` | 8 feedback loops + human system dynamics |

Each layer can run independently. Each produces valid results. Each adds one more dimension of realism. This is the "progressive complexity" principle — never add complexity you can't validate against the simpler version.

---

## 2. The 9-Step Cascade Engine

The cascade (`engine/cascade.py`) is the heart of the system. Given a stimulus and an organization, it propagates effects through all seven stocks in sequence.

### The Stimulus

A stimulus defines **what changes**:

```python
@dataclass
class Stimulus:
    name: str                              # "Deploy Microsoft Copilot to Claims"
    stimulus_type: str                     # technology_injection | headcount_target | ...
    tools: List[str]                       # ["Microsoft Copilot"]
    target_scope: str                      # function name, role_id, or "ALL"
    target_functions: List[str]            # ["Claims"]
    target_roles: List[str]               # [] (empty = all roles in function)
    policy: str                            # moderate_reduction | no_layoffs | ...
    absorption_factor: float               # 0.35 (35% of freed capacity reabsorbed)
    alpha: float                           # 1.0 (adoption completeness for single-step)
    training_cost_per_person: float        # 2000
```

### Constants

**Shadow Work Tax:** 10% overhead for AI output verification. When AI does a task, humans still spend ~10% of original effort reviewing, correcting, and validating.

**Automation Freed Percentages (after shadow work tax):**

| Category | Raw Freed % | Post-Tax Freed % |
|----------|-------------|-------------------|
| directive | 85% | 76.5% |
| feedback_loop | 75% | 67.5% |
| task_iteration | 35% | 31.5% |
| learning | 25% | 22.5% |
| validation | 30% | 27.0% |
| negligibility | 0% | 0% |

**Productive Hours by Management Level:**

| Level | Productive % | Monthly Hours |
|-------|-------------|---------------|
| Individual Contributor | 80% | 128h |
| Senior IC | 75% | 120h |
| Manager | 60% | 96h |
| Senior Manager | 55% | 88h |
| Director | 45% | 72h |
| VP | 40% | 64h |

This matters for headcount reduction: a VP's freed hours produce fewer reducible FTEs than an IC's freed hours, because each VP hour is "worth more" in terms of productive output.

### The Nine Steps

#### Step 1: Scope Resolution

**Question:** Which roles, workloads, and tasks are affected by this stimulus?

```
Input:  Stimulus (target functions, target roles, tool names)
Output: Step1_ScopeResult
  - affected_roles: List[str]
  - affected_workloads: List[str]
  - affected_tasks: List[str]        (only addressable tasks)
  - total_tasks_in_scope: int        (all tasks, including protected)
  - addressable_tasks: int
  - compliance_protected: int
  - total_headcount: int
  - total_hours_month: float
  - functions_affected: List[str]
```

A task is "addressable" if:
1. It belongs to a role in the target scope
2. Its `automatable_by_tool` matches one of the stimulus tools
3. It is not compliance-mandated human

#### Step 2: Task Reclassification

**Question:** Which tasks change state from human to AI or human+AI?

For each addressable task:
- Compute `automation_pct = AUTOMATION_FREED_PCT[category] × stimulus.alpha`
- Compute `freed_hours = task.effort_hours × automation_pct / 100`
- Classify new state:
  - If category is directive/feedback_loop: `new_state = "ai"` (fully automated)
  - If category is task_iteration/learning/validation: `new_state = "human_ai"` (augmented)
  - If category is negligibility or compliance-blocked: `new_state = "human"` (unchanged)

```
Output: Step2_ReclassificationResult
  - tasks_to_ai: int
  - tasks_to_human_ai: int
  - tasks_unchanged: int
  - total_freed_hours_per_person: float
  - reclassified_tasks: List[TaskReclassification]
```

#### Step 3: Capacity Computation

**Question:** How much capacity is actually freed after redistribution?

```
For each role:
  gross_freed_pp     = sum of freed_hours from reclassified tasks
  redistributed_pp   = gross_freed_pp × stimulus.absorption_factor
  net_freed_pp       = gross_freed_pp - redistributed_pp
  total_net_freed    = net_freed_pp × role.headcount
  freed_pct          = (gross_freed_pp / total_effort) × 100
```

This is the B1 (Capacity Absorption) loop in static form. The absorption factor represents organizational elasticity — work that gets informally redistributed rather than eliminated.

```
Output: Step3_CapacityResult
  - total_gross_freed_hours: float
  - total_net_freed_hours: float
  - absorption_factor: float
  - dampening_ratio: float       (net / gross)
  - role_capacities: List[RoleCapacity]
```

#### Step 4: Skill Impact

**Question:** Which skills sunset (become obsolete) and which sunrise (become needed)?

For each reclassified task, the skills associated with its workload are categorized:
- Skills on automated tasks → **sunset** (declining)
- Skills marked `is_sunrise` → **sunrise** (emerging)
- High-proficiency sunset skills (>= 70) → **critical sunset** (risk flag)

```
Output: Step4_SkillResult
  - sunset_skills: List[SkillImpact]
  - sunrise_skills: List[SkillImpact]
  - unchanged_skills: int
  - net_skill_gap: int              (sunrise - sunset)
  - critical_sunset: List[SkillImpact]
```

#### Step 5: Workforce Impact

**Question:** How many headcount reductions are possible, given the policy?

```
For each role:
  net_freed_ftes = total_net_freed_hours / productive_hours_month(level)
  reducible = apply_policy(net_freed_ftes, policy, headcount)
```

**Five HR Policies:**

| Policy | Formula |
|--------|---------|
| `no_layoffs` | reducible = 0 |
| `natural_attrition` | min(floor(freed_ftes), max(1, ceil(headcount × 0.007))) |
| `moderate_reduction` | floor(freed_ftes) |
| `active_reduction` | round(freed_ftes) |
| `rapid_redeployment` | ceil(freed_ftes) if >= 0.5 else 0 |

**Min staffing floor (safety constraint):** Never reduce below 20% of original headcount.

```
min_staffing = max(1, ceil(headcount × 0.20))
reducible = min(reducible, max(0, headcount - min_staffing))
```

```
Output: Step5_WorkforceResult
  - total_current_hc: int
  - total_reducible_ftes: int
  - total_projected_hc: int
  - total_reduction_pct: float
  - policy_applied: str
  - role_impacts: List[RoleWorkforceImpact]
```

#### Step 6: Financial Impact

**Question:** What's the investment required and what are the projected savings?

```
Investment:
  license_cost_annual    = sum(tool.license_cost × 12 × headcount) for each tool
  training_cost          = stimulus.training_cost_per_person × headcount
  change_management_cost = training_cost × 0.5
  total_investment       = license + training + change_mgmt

Savings:
  salary_savings_annual     = sum(reducible_ftes × avg_salary) for each role
  productivity_savings      = sum(residual_fte_equivalent × avg_salary × 0.5)
  total_savings_annual      = salary_savings + productivity_savings

Derived:
  net_annual    = total_savings - total_investment
  payback_months = total_investment / (total_savings / 12)
  roi_pct       = (net_annual / total_investment) × 100
```

**Note:** Productivity savings apply a 0.5 factor — residual freed hours (hours freed but not enough for an FTE reduction) are valued at half-salary because they represent efficiency gains, not headcount savings.

#### Step 7: Structural Impact

**Question:** Which roles need redesign or elimination?

| Threshold | Flag |
|-----------|------|
| freed_pct > 40% | Redesign candidate |
| freed_pct > 70% | Elimination candidate |

#### Step 8: Human System Impact

**Question:** How does this stimulus affect the human system qualitatively?

Computes a **change burden score** (0-100):

```
disruption    = workforce.total_reduction_pct / 100
scope_factor  = len(affected_roles) / len(all_roles)
avg_readiness = mean(human_system[fn].change_readiness) for affected functions

change_burden = (scope_factor × 50 + disruption × 50) / max(avg_readiness / 100, 0.1)
change_burden = min(100, change_burden × 100)
```

The change burden captures the tension between disruption scope/speed and organizational readiness. High burden with low readiness signals danger.

#### Step 9: Risk Assessment

**Question:** What risks emerge from this cascade?

| Risk | Trigger | Severity |
|------|---------|----------|
| Compliance | compliance_protected > 0 | medium |
| Critical Sunset | len(critical_sunset) > 5 | high / medium |
| Change Burden | burden > 80 | high; burden > 60: medium |
| Capability Valley | net_skill_gap > 10 | medium |
| Quality | total_reduction_pct > 20% | high |
| Concentration | single function + reducible > 20 | medium |

### Cascade Orchestration

```python
def run_cascade(stimulus, org) -> CascadeResult:
    step1 = step1_resolve_scope(stimulus, org)
    step2 = step2_reclassify_tasks(step1, stimulus, org)
    step3 = step3_compute_capacity(step1, step2, stimulus, org)
    step4 = step4_compute_skill_impact(step2, org)
    step5 = step5_compute_workforce_impact(step3, stimulus, org)
    step6 = step6_compute_financial_impact(step1, step3, step5, stimulus, org)
    step7 = step7_compute_structural_impact(step3, org)
    step8 = step8_compute_human_system_impact(step1, step5, stimulus, org)
    step9 = step9_assess_risk(step1, step2, step3, step4, step5, step8, org)
    return CascadeResult(step1..step9)
```

Each step is a pure function. Input = previous steps + org data. Output = result dataclass. No side effects.

---

## 3. The Rate Equations

`engine/rates.py` defines how adoption evolves over time using S-curve (logistic) functions.

### The S-Curve

```
S(t) = alpha / (1 + e^(-k × (t - midpoint)))

Parameters:
  alpha    = ceiling (0-1): maximum adoption this phase can achieve
  k        = steepness: how fast the S-curve rises
  midpoint = inflection month: when adoption rate is fastest
  delay    = months before this phase begins
```

At the inflection point (t = midpoint), adoption is exactly alpha/2. Before the inflection, adoption accelerates. After, it decelerates. This captures the natural pattern of technology adoption: slow start, rapid middle, gradual saturation.

### Three-Phase Adoption Model

Adoption isn't a single S-curve — it has three phases:

```
Phase 1 (Adopt):  Close adoption gap       → tools deployed but unused
Phase 2 (Expand): Push beyond adoption gap  → new use cases, deeper integration
Phase 3 (Extend): Workflow-level automation → non-linear, cross-task effects

Combined adoption = min(1.0, adopt + expand + extend)
```

Each phase is an independent S-curve with its own alpha, k, midpoint, and delay. Phase 2 starts after Phase 1 has meaningful progress. Phase 3 starts after Phase 2.

### The Five Preset Scenarios

| Scenario | Adopt (alpha/k/mid) | Expand | Extend | Policy | Absorption |
|----------|---------------------|--------|--------|--------|------------|
| **P1 Cautious** | 0.5 / 0.3 / 4 | None | None | natural_attrition | 0.40 |
| **P2 Balanced** | 0.6 / 0.3 / 4 | 0.3 / 0.3 / 4 (delay 6) | None | moderate_reduction | 0.35 |
| **P3 Aggressive** | 0.8 / 0.35 / 3 | 0.5 / 0.35 / 3 (delay 4) | 0.3 / 0.35 / 3 (delay 8) | active_reduction | 0.30 |
| **P4 Capability-First** | 0.6 / 0.3 / 4 | 0.3 / 0.3 / 4 (delay 6) | None | no_layoffs | 0.00 |
| **P5 Accelerated** | 0.8 / 0.4 / 3 | 0.5 / 0.4 / 3 (delay 4) | 0.3 / 0.4 / 3 (delay 6) | rapid_redeployment | 0.25 |

**Thought experiment:** P1 and P3 use the same data, the same organization, the same tools. The only difference is policy. P1 saves ~$1.2M with low risk. P3 saves ~$6.8M with high risk. The model reveals the trade-off — it doesn't make the decision.

---

## 4. The Eight Feedback Loops

`engine/feedback.py` implements the closed-loop dynamics that make the simulation realistic. Without feedback, the model produces the "theoretical ceiling" — what would happen in a perfect world. With feedback, it produces the "realistic adjustment."

### The Human System State (Dynamic Stock)

```python
@dataclass
class HumanSystemState:
    proficiency: float = 30.0          # 0-100
    readiness: float = 50.0            # 0-100
    trust: float = 40.0                # 0-100
    political_capital: float = 60.0    # 0-100
    transformation_fatigue: float = 0.0 # 0-100
```

This state evolves every month based on what happened that month. It starts at the function's baseline values and drifts based on adoption success, disruption events, and organizational dynamics.

### Multiplier Architecture

Three multipliers gate the effective adoption rate:

**Effective Multiplier (human system blend):**
```
if trust < 10 OR readiness < 10:
    return 0.05                    # VETO — near-zero adoption
else:
    base = (0.35 × proficiency + 0.45 × readiness + 0.20 × trust) / 100
    return max(0.15, base)         # floor at 15%
```

**Trust Multiplier (smooth threshold bands):**
```
trust < 20:        return 0.50     # CRISIS — half-speed
trust 20-40:       0.50 → 0.90    # Linear transition
trust 40-60:       0.90 → 1.00    # Near-normal
trust >= 60:       return 1.00     # ENABLER — full speed
```

**Capital Multiplier:**
```
capital < 20:      return 0.20     # Nearly blocked
capital 20-40:     return 0.60     # Constrained
capital >= 40:     return 1.00     # Green light
```

### The Four Balancing Loops (Resist Change)

#### B1: Capacity Absorption — Always On

**Mechanism:** As workload per remaining person increases (from HC reductions), more freed capacity is reabsorbed through informal scope expansion.

```
overload_ratio = min(1.0, workload_per_person / max_workload)
absorption = base_absorption + (overload_ratio × sensitivity)
```

Base absorption is 0.30 (30% of freed hours are absorbed even with zero overload). This grows to ~0.37 as headcount decreases. This loop never turns off — it is the most persistent dampening force.

#### B2: Skill Valley — Peaks Early, Fades

**Mechanism:** Deploying AI creates a gap between existing skills and needed skills. Until reskilling catches up, this gap reduces effective adoption.

```
drag = (skill_gap_pct / 100) × drag_coefficient
skill_multiplier = max(0.1, 1.0 - drag)
```

Floor of 0.1 — adoption never completely stops, even with large skill gaps. This loop peaks around month 6 (maximum skill gap) and fades as training closes the gap.

#### B3: Change Resistance — Strong Early, Fading

**Mechanism:** Disruption creates resistance, which reduces readiness, which slows adoption. This is the most complex balancing loop because it interacts with R5 (readiness boost).

Three forces on readiness each month:

```
1. Resistance (negative):
   trust_dampening = max(0.3, trust / 100)
   resistance = (disruption × sensitivity) / trust_dampening

2. Recovery (positive):
   recovery = decay_rate × (1 - fatigue / 100)

3. Adoption Boost (positive, from R5):
   ceiling = max(0.1, 1.0 - readiness / 100)
   boost = 1.5 × adoption_level × ceiling

delta_readiness = -resistance + recovery + boost
```

**Fatigue (v3 restructured):** Five sources accumulate fatigue:

| Source | Formula | Nature |
|--------|---------|--------|
| AI work burden | `0.6 × adoption_level` | Cognitive load of working WITH AI |
| HC anxiety | `20.0 × hc_reduced_pct` | Fear from layoff events |
| AI anxiety | `0.20` (if AI deployed) | Persistent baseline fear |
| Pace fatigue | `adoption_velocity × rate × 10` | Change happening too fast |
| Disruption | `disruption × rate` | Original mechanism |

Fatigue recovery depends on stability — months without HC reductions allow more recovery.

#### B4: Seniority Offset — Slow, Growing

**Mechanism:** As entry-level roles are automated first, the remaining workforce becomes more senior on average. Senior roles are harder to automate.

```
reduction_pct = (original_hc - current_hc) / original_hc
seniority_increase = reduction_pct × seniority_penalty
seniority_multiplier = max(0.5, 1.0 - seniority_increase)
```

This loop is barely noticeable in the first 12 months but grows steadily, creating a natural ceiling on automation returns.

### The Four Reinforcing Loops (Amplify Change)

#### R1: Trust-Adoption Flywheel — Slow Start, Compounds

**Mechanism:** Successful AI use builds trust, which increases willingness, which drives more adoption. But trust destruction is multiplicative and fast.

```
ON SUCCESS:
  build = trust_build_rate × adoption_level × success_probability
  ceiling_factor = max(0.1, 1.0 - trust / 100)
  delta_trust = build × ceiling_factor

ON AI ERROR:
  delta_trust = -trust × trust_destruction_factor    # 30% of current trust wiped
```

**Trust evidence thresholds (v3):** Trust doesn't build smoothly. It jumps at evidence milestones (10%, 25%, 50% adoption). Between milestones, trust growth runs at 50% of normal rate. This captures the "show me it works" dynamic — people need to see concrete evidence before trusting more.

**Trust shocks (v3):** Every 10 months (starting month 4), a small trust shock occurs (1.5 points lost). This represents the steady drip of AI incidents — hallucinations, wrong answers, workflow disruptions — that chip away at trust even in successful deployments.

#### R2: Proficiency Flywheel — Strongest Reinforcing Loop

**Mechanism:** More adoption leads to more practice, which builds proficiency, which improves results, which encourages more adoption.

```
practice_intensity = adoption_level
ceiling_factor = max(0.05, 1.0 - proficiency / learning_saturation)
delta_proficiency = learning_rate × practice_intensity × ceiling_factor × velocity_factor
```

**GenAI fast-start (v3):** During the first 6 months, learning rate is doubled (2x multiplier). This captures the observation that generative AI tools have rapid individual skill acquisition (2-8 weeks for basic proficiency) compared to traditional enterprise software.

**Learning saturation:** Proficiency growth slows as it approaches the saturation level (85 by default). This creates the classic learning curve — fast initial gains that taper off.

#### R3: Savings Reinvestment Flywheel — Activates Late

**Mechanism:** Accumulated savings create budget for further investment, enabling faster rollout.

```
reinvestment = cumulative_savings × reinvestment_rate
boost = (reinvestment × effectiveness) / 1,000,000
additional_adoption_boost = min(0.05, boost)    # cap at 5%
```

This loop was structurally disconnected in v1 (the function existed but was never called). In v2.1, it provides a small but growing boost after breakeven — approximately +1-2% adoption acceleration.

#### R4: Political Capital — Enables Scope Expansion

**Mechanism:** Early wins build executive confidence, which allocates more resources, which enables bigger scope.

```
build = capital_build_rate × adoption_level × success_probability
spend = capital_spend_rate × disruption_level
delta_capital = build - spend
```

Political capital doesn't directly affect the adoption math, but it gates HC decisions. Below the threshold (30), the organization won't approve headcount reductions — even if the math supports them.

### Composite: Effective Adoption Rate

All feedback loops combine multiplicatively:

```
effective_adoption = raw_adoption
                   × human_system_multiplier
                   × trust_multiplier
                   × skill_valley_multiplier    (B2)
                   × seniority_multiplier       (B4)
                   × capital_multiplier

Result is clamped: max(0, min(raw_adoption, effective))
```

---

## 5. The Time-Stepped Simulator

`engine/simulator_fb.py` runs the cascade forward in time, applying feedback loops at each monthly timestep.

### Monthly Simulation Loop

For each month (1 to 36):

**1. Raw S-Curve Adoption**
```
raw = min(1.0, adopt_phase(t) + expand_phase(t) + extend_phase(t))
```

**2. Capability Upgrades (v3)**
At predefined months (12, 24), the technology ceiling gets a boost (+10%), but proficiency and trust take a hit (tool disruption).

**3. Shadow AI (v3)**
Informal, unsanctioned AI usage runs in parallel at 1.5x the official adoption speed. A fraction (10%) converts to official adoption over time, and it passively builds proficiency.

**4. Feedback: Compute Effective Adoption**
```
skill_gap_pct = (open_gaps - closed_gaps) / total_sunrise_skills × 100
effective = compute_effective_adoption(raw, hs, skill_gap_pct, original_hc, current_hc)
dampening = effective / raw
delta_adoption = max(0, effective - previous_effective)
```

**5. Capacity Pipeline (2-month delay)**
Freed capacity doesn't materialize instantly. A 2-month pipeline delays realization:
```
capacity_pipeline.append(gross_freed_this_month)
realized = capacity_pipeline.popleft()    # from 2 months ago
```

**6. Dynamic Absorption (B1)**
```
dynamic_absorption = compute_dynamic_absorption(base_absorption, current_hc, original_hc)
net_freed = realized - (realized × dynamic_absorption)
cumulative_net_freed += net_freed
```

**7. Skill Gap Dynamics**
```
new_sunrise_skills = ceiling_sunrise × delta_adoption
skill_gap_opened += new_sunrise_skills

if month >= reskilling_delay:
    closeable = skill_gap_opened × reskilling_rate
    skill_gap_closed += closeable

current_gap = max(0, opened - closed)
```

**8. HC Decisions (Policy-Gated + Capital-Gated)**
HC reviews happen at intervals (quarterly for most policies, monthly for rapid_redeployment). Additional delay in early months (HC decision latency):
```
if month > hc_decision_delay AND month % review_freq == 0:
    if political_capital >= threshold OR policy == "no_layoffs":
        for each role:
            compute reducible FTEs, apply policy, enforce min staffing floor
```

**9. Financial Impact**
```
Investment (phased):
  License cost: scaled by adoption level (min 10%)
  Training: spread over first 6 months
  Change mgmt: spread over first 6 months

Savings:
  Monthly salary savings = sum(reduced_ftes × salary / 12)

R3 Boost:
  If cumulative_savings > 0: apply reinvestment boost to effective adoption
```

**10. Productivity Index**
```
productivity = 100
             + automation_lift     (delayed by 2 months)
             - skill_drag          (immediate)
             - fatigue_drag
             - workflow_disruption (decays over 12 months)
```

The productivity valley is the visible dip that occurs when automation is deployed but skills haven't caught up. It typically bottoms at 92-95 (5-8% productivity loss) around month 4-6, then recovers above baseline by month 12-18.

**11. Update Human System**
All eight feedback loops fire simultaneously:
- R1: Trust update (with hallucination and periodic shocks)
- R2: Proficiency update (with GenAI fast-start)
- B3: Readiness + fatigue update (with R5 boost)
- R4: Political capital update

The new human system state feeds back into next month's effective adoption calculation, closing the loop.

### Monthly Snapshot

Each month produces a `FBMonthlySnapshot` capturing 30+ metrics:

| Category | Metrics |
|----------|---------|
| Adoption | raw_adoption_pct, effective_adoption_pct, adoption_dampening |
| Capacity | gross_freed, redistributed, net_freed, cumulative, absorption_rate |
| Workforce | headcount, hc_reduced_this_month, cumulative_hc_reduced |
| Skills | gap_opened, gap_closed, current_gap, gap_pct |
| Financial | cumulative_investment, cumulative_savings, net_position |
| Productivity | productivity_index |
| Human System | proficiency, readiness, trust, political_capital, fatigue |
| Multipliers | human_multiplier, trust_multiplier, capital_multiplier |
| Loop Contributions | b2_skill_drag, b4_seniority_mult, ai_error_occurred |
| Detail | role_headcounts (per-role HC at this month) |

### Simulation Result

The complete `FBSimulationResult` contains:
- Timeline of 37 monthly snapshots (month 0 through 36)
- Summary metrics (final HC, total savings, payback month, peak skill gap, productivity valley)
- Baseline cascade (the ceiling values from a single-step cascade)
- Feedback parameters used
- Optional trace for explainability

---

## 6. The Inverse Solver

`engine/inverse_solver.py` solves the simulation in reverse: "If I want outcome Y, what parameters do I need?"

**Constraint Types:**
- Target headcount reduction % (e.g., "reduce HC by 20%")
- Target budget amount (e.g., "spend no more than $5M")
- Target automation % (e.g., "automate 50% of tasks in Claims")

**Method:** Binary search on the adoption alpha parameter. The solver:
1. Sets alpha_low = 0, alpha_high = 1.0
2. Runs simulation at midpoint
3. Checks if result meets target
4. Narrows search range
5. Converges within tolerance

This enables question-driven analysis: instead of "what happens if we adopt at 60%?", leaders ask "what adoption level do we need to reduce headcount by 15%?"

---

## 7. The Stage Pipeline

Four stages validate progressive complexity:

### Stage 0: Static Snapshot
- Proves data model works
- Computes L1/L2/L3 gap analysis
- No cascade, no time, no feedback
- 9 acceptance tests

### Stage 1: Single-Step Cascade
- Proves 9-step cascade executes correctly
- Full propagation at alpha=1.0 (instant adoption)
- No time dimension, no feedback
- 11 acceptance tests

### Stage 3: Feedback Integration
- Proves feedback loops work
- Runs 5 simulation variants:
  - Open-loop (no feedback, theoretical ceiling)
  - Baseline (Claims p=25, r=45, t=35)
  - AI error at month 7 (trust destruction test)
  - High readiness (p=60, r=70, t=65)
  - Low readiness (p=15, r=30, t=25)
- 12 acceptance tests

### Stage 4: Scenario Comparison
- Proves five policies produce different outcomes
- Runs all 5 preset scenarios (P1-P5)
- Computes risk scores and sensitivity analysis
- 9 acceptance tests

### What the Stages Prove

| Behavior | Stage | Validation |
|----------|-------|------------|
| Redistribution dampening | 1 | net_freed < gross_freed |
| S-curve adoption | 3 | Non-linear, decelerating shape |
| Skill valley | 3 | Inverted-U skill gap |
| Trust asymmetry | 3 | Error variant: slow recovery |
| Seniority shift | 3 | B4 multiplier visible after month 18 |
| Political capital gating | 4 | Capital < threshold blocks HC decisions |
| Readiness sensitivity | 4 | +-20% readiness shifts outcomes ~35% |
| Policy trade-offs | 4 | P1-P5 produce meaningfully different results |

---

## 8. Systems Thinking: Why Feedback Changes Everything

### The Dampening Gap

The most important metric in the system is **average dampening** — the fraction of raw adoption lost to human system dynamics.

| Variant | Dampening | Net 36mo | Interpretation |
|---------|-----------|----------|----------------|
| Open-loop | 0% | +$17.8M | Theoretical ceiling |
| High readiness | 31% | +$11.0M | Best realistic case |
| Baseline | 35% | +$4.7M | Moderate organization |
| Low readiness | 93% | -$1.4M | Unprepared organization |

The difference between high and low readiness is $12.3M over 36 months. Readiness alone accounts for more variance than any technology choice, deployment speed, or policy decision.

### Loop Dominance Over Time

The system transitions through three phases of loop dominance:

**Phase 1 (M0-M12): Balancing Dominant — "The system feels stuck"**
- B2 (Skill Valley) peaks at month 6
- B3 (Change Resistance) is high
- B1 (Absorption) is constant
- Financial position is negative
- R2 (Proficiency) is slowly building but not yet visible

**Phase 2 (M12-M24): Tipping Point — "Momentum builds"**
- R2 (Proficiency) emerges as strongest reinforcing loop
- R5 (Readiness Boost) counterbalances B3
- B2 has largely closed (reskilling caught up)
- Financial breakeven at M18
- The system has crossed the tipping point

**Phase 3 (M24-M36): Reinforcing Dominant — "Compounding returns"**
- R1 (Trust), R2 (Proficiency), R4 (Capital) all strong
- B1 (Absorption) persists but is overwhelmed
- B4 (Seniority) is growing, creating diminishing returns
- Financial returns compound

### The Strategic Implication

The organization must survive Phase 1 to reach Phase 2. The first 12 months produce negative financial returns, visible resistance, and modest adoption gains. Leaders who evaluate the transformation during this period will see a system that appears to be failing. In reality, the reinforcing loops are silently building strength.

The decision to continue investing through Phase 1 — maintaining training budgets, sustaining change management, not declaring failure — is the single most consequential strategic choice.

*"Stocks generally change slowly, even when the flows into or out of them change suddenly. Therefore, stocks act as delays or buffers or shock absorbers in systems."*
*— Donella Meadows*
