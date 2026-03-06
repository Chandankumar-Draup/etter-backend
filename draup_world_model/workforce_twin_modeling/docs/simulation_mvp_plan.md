# Workforce Twin: Simulation MVP — Implementation Plan
## From System Model to Working Simulation with Synthetic Data
*Version 1.0 — March 2026*

---

> **Goal:** Execute the system model with synthetic data to validate all stocks, flows, feedback loops, delays, and scenarios BEFORE integrating with Neo4j and real client data.

---

# PART 0: FIRST PRINCIPLES — WHAT MUST THE MVP PROVE?

## The Bathtub Test (Meadows)

Before simulating an organization, we must demonstrate we understand stocks and flows. A bathtub fills through one faucet and drains through another. The water level (stock) changes only through these flows. If the faucet flow exceeds the drain flow, the level rises. This is trivially obvious for bathtubs — but organizations regularly fail to understand it.

**Our bathtub:** Workforce Capacity is the stock. Automation frees capacity (outflow). Redistribution absorbs some back (inflow). The NET change determines headcount trajectory. The MVP must demonstrate this simple dynamic before adding complexity.

## Thought Experiment: What Would Prove the Model Wrong?

If the simulation shows:
- Linear headcount decline → **model is wrong** (should show dampened decline from redistribution)
- Instant cost savings → **model is wrong** (should show J-curve with adoption lag)
- Same results regardless of human readiness → **model is wrong** (should show dramatically different outcomes)
- Same results regardless of sequencing → **model is wrong** (should show path dependence)
- Aggressive scenario always wins → **model is wrong** (should show risk-adjusted trade-offs)

The MVP must produce all five "correct" behaviors. If it does, the model is validated for integration with real data.

## Second-Order Effects the MVP Must Capture

1. **Redistribution dampening:** Automating 40% of a role's tasks doesn't free 40% capacity — redistribution absorbs 30-60% of it
2. **Skill valley:** Productivity dips before it rises (3-12 month gap between task automation and skill acquisition)
3. **Trust asymmetry:** One AI error sets back adoption more than ten successes advance it
4. **Seniority shift:** As entry-level roles go first, remaining workforce costs more per head
5. **Political capital:** Early wins enable bigger moves; early failures lock in caution

---

# PART I: THE FIVE STAGES

## Overview

| Stage | Name | What It Proves | Feedback Loops | Time Dimension |
|-------|------|---------------|----------------|----------------|
| 0 | Static Snapshot | Data model works, gaps computable | None | Point-in-time |
| 1 | Single-Step Cascade | All 9 cascade steps execute correctly | None | One timestep |
| 2 | Time-Stepped Simulation | S-curves, delays produce realistic behavior | None (open-loop) | 36 months |
| 3 | Feedback Integration | Human system modulates rates, loops interact | All 8 loops active | 36 months |
| 4 | Scenario Comparison | Multiple policies produce meaningfully different outcomes | All loops | 36 months × 5 scenarios |

Each stage adds ONE layer of complexity. Each must pass its own validation before proceeding.

---

## Stage 0: Static Snapshot

### Purpose
Prove the data model works. Given an organization's current state, compute the three-layer gap analysis and rank opportunities.

### What It Computes
```
INPUT: Organization taxonomy + Etter scores + deployed tech stack
OUTPUT:
  - Layer 1 (Etter potential) per role: from Etter scores directly
  - Layer 2 (Achievable) per role: L1 filtered by org tech stack match
  - Layer 3 (Realized) per role: from org declaration of current automation
  - Adoption Gap = L2 - L3 (tools deployed, not used)
  - Capability Gap = L1 - L2 (need new tools)
  - Opportunity ranking: gaps × headcount × salary = $ value
```

### Stocks Exercised
- Stock 1 (Task Classification State) — all three layers
- Stock 2 (Workforce Capacity) — headcount baseline
- Stock 4 (Financial Position) — salary baseline
- Stock 5 (Org Structure) — taxonomy

### Validation Criteria
1. Adoption gap ≥ 0 for every role (L2 ≥ L3 always)
2. Capability gap ≥ 0 for every role (L1 ≥ L2 always)
3. Aggregation works: role metrics → JF → JFG → function → org
4. Top opportunities ranked correctly by $ value

### Metrics Produced
- Current Automation Rate per level
- Adoption Gap Size per level
- Capability Gap Size per level
- Automation Opportunity Cost per level

---

## Stage 1: Single-Step Cascade

### Purpose
Execute all 9 cascade steps for ONE stimulus at ONE point in time. No S-curves, no delays, no feedback — just the raw cascade logic.

### Stimulus
"Deploy Copilot to Claims Processing function" — affects all roles in that function.

### What It Computes (the 9 cascade steps)

**Step 1 — Scope Resolution:** Identify all roles in Claims Processing → their workloads → their tasks.

**Step 2 — Task Reclassification:** For each task where Copilot can help AND the task isn't already automated:
- If task is Directive or Feedback Loop → classify as AI (fully automatable)
- If task is Task Iteration, Learning, or Validation → classify as Human+AI (augmented)
- If task is Negligibility → remains Human

**Step 3 — Capacity Computation:**
```
freed_hours_per_role = Σ (reclassified tasks × effort_pct × hours_per_month)
net_freed = freed_hours - (redistributed_hours × absorption_factor)
```

**Step 4 — Skill Impact:** For each reclassified task:
- Sunset skills: skills associated with automated tasks
- Sunrise skills: AI collaboration, prompt engineering, validation oversight

**Step 5 — Workforce Impact:**
```
if net_freed_hours ≥ 160 (1 FTE) AND policy allows:
    headcount_reduction = floor(net_freed / 160)
    residual_hours = net_freed - (headcount_reduction × 160)
```

**Step 6 — Financial Impact:**
```
investment = copilot_license_cost × headcount + training_cost
savings = headcount_reduction × avg_salary_per_level
net = savings - investment
```

**Step 7 — Structural Impact:** Flag roles where freed_pct > 40% for redesign.

**Step 8 — Human System Impact:** Record qualitative direction (not computed yet):
- Trust change direction: up (if successful deployment) or down (if errors)
- Readiness change direction: down (from disruption) unless managed

**Step 9 — Risk Assessment:**
```
compliance_risk = any mandated-human tasks affected?
concentration_risk = critical skills now in fewer hands?
change_burden = scope × speed / readiness
```

### Stocks Exercised
- All 7 stocks (Stock 6 in qualitative direction only)

### Validation Criteria
1. Cascade produces non-zero results for all 9 steps
2. freed_hours < total_hours (can't free more than exists)
3. headcount_reduction ≤ total_headcount in function
4. savings > 0 if any headcount is reduced
5. At least one risk is flagged

---

## Stage 2: Time-Stepped Simulation

### Purpose
Same cascade, but now it runs over 36 monthly timesteps with S-curve adoption and delays. NO feedback loops yet — this is open-loop (human parameters are fixed).

### What Changes from Stage 1
- Adoption doesn't happen instantly — follows S-curve
- Capacity freeing is gradual (not instant)
- Costs precede savings (J-curve shape)
- Skill gap opens fast, closes slowly (with reskilling delay)

### The Core Time Loop
```
for month in range(1, 37):
    # 1. Compute adoption progress via S-curve
    adoption_pct = logistic(month, k=0.3, midpoint=4) * alpha_adopt
    
    # 2. Reclassify tasks proportional to adoption_pct
    newly_reclassified = remaining_tasks × adoption_pct × dt
    
    # 3. Compute freed capacity (cumulative)
    freed_this_month = newly_reclassified × effort_pct × hours
    total_freed += freed_this_month
    net_freed = total_freed × (1 - absorption_factor)
    
    # 4. Compute skill gap (opens immediately, closes with delay)
    skill_gap_opened += newly_reclassified × skills_per_task
    if month > reskilling_delay:
        skills_acquired += training_rate × dt
    current_gap = skill_gap_opened - skills_acquired
    
    # 5. Compute headcount (discrete decisions, batched quarterly)
    if month % 3 == 0:  # quarterly review
        reducible_ftes = floor(net_freed / 160)
        headcount -= reducible_ftes
    
    # 6. Compute financials
    investment_this_month = (license_cost if month == 1 else 0) + training_cost / 6
    savings_this_month = cumulative_reductions × avg_salary / 12
    net_position += savings_this_month - investment_this_month
    
    # 7. Record all metrics for this timestep
    record(month, adoption_pct, freed_hours, headcount, 
           net_position, skill_gap, productivity)
```

### S-Curve Function
```python
def logistic(t, k, midpoint):
    """Standard logistic S-curve. Returns 0→1 over time."""
    return 1.0 / (1.0 + exp(-k * (t - midpoint)))
```

### Expected Behavior (Reference Mode)

| Variable | Month 0 | Month 6 | Month 12 | Month 24 | Month 36 |
|----------|---------|---------|----------|----------|----------|
| Adoption % | 0% | 30% | 70% | 90% | 95% |
| Freed hours | 0 | low | growing | plateau | plateau |
| Headcount | 100% | ~95% | ~88% | ~80% | ~78% |
| Net savings | negative | break-even | positive | growing | plateau |
| Skill gap | 0 | peak | declining | small | near-zero |
| Productivity | 100% | 92% (dip) | 100% | 108% | 110% |

### Validation Criteria
1. Adoption follows S-curve shape (not linear, not step)
2. Headcount declines in steps (quarterly batches), not smoothly
3. Net savings shows J-curve (or flat-then-rise for adoption gap)
4. Skill gap shows inverted-U (rises, peaks at month ~4, falls)
5. Productivity shows valley (dips then recovers above baseline)
6. Total freed hours never exceeds total available hours
7. Three phases (adoption, expansion, extension) have different speeds

---

## Stage 3: Feedback Integration

### Purpose
Close the feedback loops. Human system parameters (trust, readiness, proficiency) now CHANGE over time based on outcomes, and their changes MODULATE adoption rates.

### What Changes from Stage 2

The three rate equations now use DYNAMIC human parameters instead of fixed values:

```python
# Stage 2: fixed human parameters
adoption_rate = alpha * s_curve(t) * ease * (FIXED_PROFICIENCY / 100) * (FIXED_READINESS / 100)

# Stage 3: dynamic human parameters that change based on outcomes
adoption_rate = alpha * s_curve(t) * ease * (proficiency[t] / 100) * (readiness[t] / 100)
```

### The Eight Feedback Loops (Implementation)

**B1 — Capacity Absorption:**
```python
absorption_factor = base_absorption + (workload_per_person / max_workload) * 0.3
# As workload increases, more freed capacity gets absorbed
```

**B2 — Skill Valley:**
```python
effective_adoption = adoption_rate * (1 - skill_gap / max_gap)
# Skill gap reduces effective adoption rate
```

**B3 — Change Resistance:**
```python
resistance = base_resistance + disruption_level * sensitivity
readiness[t+1] = readiness[t] - resistance * dt + recovery_rate * dt
# Too fast → resistance rises → readiness falls → adoption slows
```

**B4 — Seniority Offset:**
```python
avg_seniority[t] = compute_weighted_seniority(remaining_roles)
effective_potential = base_potential * (1 - seniority_penalty * avg_seniority[t])
# More senior workforce → less automatable
```

**R1 — Trust-Adoption Flywheel:**
```python
positive_outcomes = adoption_rate * success_probability
trust[t+1] = trust[t] + trust_build_rate * positive_outcomes * dt
willingness = trust[t] * base_willingness
# More adoption → more success → more trust → more willingness
```

**Trust Destruction (asymmetric, within R1):**
```python
if ai_error_event:
    trust[t+1] = trust[t] * (1 - trust_destruction_factor)  # Multiplicative, fast
    # vs. trust building which is additive, slow
```

**R2 — Proficiency Flywheel:**
```python
practice = adoption_level * hours_per_person
proficiency[t+1] = proficiency[t] + learning_rate * practice * dt
# More adoption → more practice → more proficiency → better results
```

**R3 — Savings Flywheel:**
```python
budget[t+1] = base_budget + cumulative_savings * reinvestment_rate
investment_capacity = budget[t]
# More savings → more budget → more investment → more automation
```

**R4 — Political Capital:**
```python
capital[t+1] = capital[t] + success_score * capital_build_rate - disruption * capital_spend_rate
if capital[t] < threshold:
    resource_allocation = reduced  # Balking: leadership won't fund
```

### Validation Criteria
1. Higher initial readiness → faster adoption (human multiplier works)
2. AI error event → visible trust drop → adoption slows for 2-3 months
3. Proficiency grows with practice (learning curve visible)
4. Resistance increases with speed, decreases with time
5. Savings reinvestment visibly accelerates Phase 2
6. Low political capital prevents resource allocation

### Key Test: Feedback vs. No-Feedback Comparison
Run same scenario with feedback ON and OFF. With feedback:
- Adoption should be SLOWER initially (resistance dampens)
- But FASTER in Phase 2 (proficiency flywheel kicks in)
- Overall trajectory should be more realistic (S-curves within S-curves)

---

## Stage 4: Scenario Comparison

### Purpose
Run the five policy scenarios from the system model. Compare outcomes. Prove that small parameter changes produce dramatically different results.

### The Five Scenarios

**P1: Cautious**
```python
params = {
    'phases': ['adoption'],         # Gap A only
    'policy': 'natural_attrition',  # No layoffs, wait for people to leave
    'alpha_adopt': 0.5,
    'readiness_required': 0,        # Any readiness level
    'investment_budget': 'low',
}
```

**P2: Balanced**
```python
params = {
    'phases': ['adoption', 'expansion'],
    'policy': 'moderate_reduction',   # Managed reductions
    'alpha_adopt': 0.6,
    'alpha_expand': 0.3,
    'readiness_required': 50,
    'investment_budget': 'medium',
}
```

**P3: Aggressive**
```python
params = {
    'phases': ['adoption', 'expansion', 'extension'],
    'policy': 'active_reduction',
    'alpha_adopt': 0.8,
    'alpha_expand': 0.5,
    'alpha_extend': 0.3,
    'readiness_required': 70,
    'investment_budget': 'high',
}
```

**P4: Capability-First**
```python
params = {
    'phases': ['adoption', 'expansion'],
    'policy': 'no_layoffs',           # All freed capacity → new work
    'alpha_adopt': 0.6,
    'readiness_required': 40,
    'investment_budget': 'medium',
    'redirect_freed_capacity': True,
}
```

**P5: AI-Age Accelerated**
```python
params = {
    'phases': ['adoption', 'expansion', 'extension'],
    'policy': 'rapid_redeployment',
    'alpha_adopt': 0.8,
    'alpha_expand': 0.5,
    'alpha_extend': 0.3,
    'readiness_required': 80,
    'enable_workflow_automation': True,  # Non-linear workflow effects
    'investment_budget': 'high',
}
```

### Expected Comparison Outputs

| Metric | P1 | P2 | P3 | P4 | P5 |
|--------|-----|-----|-----|-----|-----|
| Net savings (36mo) | $2-4M | $6-10M | $10-15M | ~$0 | $12-18M |
| Headcount change | -5-10% | -20-28% | -35-42% | 0% | -30-35% |
| Risk level | Low | Medium | High | Low | Very High |
| Skill gap peak | Small | Medium | Large | Medium | Large |
| Trust trajectory | Stable | Growing | Volatile | Growing | Volatile |
| Break-even month | Month 3 | Month 8 | Month 14 | Never | Month 10 |

### Validation Criteria
1. P1 saves least, risks least (monotonic relationship)
2. P3 saves most gross but has highest risk (trade-off visible)
3. P4 shows $0 savings but workforce capability improves
4. P5 shows non-linear gains from workflow automation
5. Sensitivity: ±20% change readiness shifts all outcomes by ~35%
6. Path dependency: different sequencing within P2 produces different 36-month outcomes

---

# PART II: SYNTHETIC DATA SPECIFICATION

## Design Principles

**Minimum viable size:** Large enough to show interesting dynamics, small enough to trace by hand.

**Target:** 50 roles across 4 functions, with ~200 workloads, ~800 tasks. This is 1% of the real dataset (5,003 roles) but sufficient to exercise every element of the model.

**Realistic distributions:** Scores match real data ranges (automation: 0.2-56.8, avg 16.1; augmentation: 3.7-34.5, avg 14.5).

## The Synthetic Organization: "InsureCo"

A mid-size insurance company with 2,400 employees across 4 core functions.

### Organization Taxonomy

| Function | Sub-Function | JFG | Roles | Headcount | Avg Salary |
|----------|-------------|-----|-------|-----------|------------|
| Claims | Claims Processing | Claims Operations | 8 | 450 | $52K |
| Claims | Claims Review | Claims Management | 4 | 120 | $72K |
| Technology | Software Dev | Technology | 6 | 280 | $95K |
| Technology | IT Operations | Technology Support | 4 | 180 | $68K |
| Finance | Accounting | Finance Operations | 5 | 200 | $65K |
| Finance | Financial Planning | Finance Analytics | 3 | 80 | $82K |
| People | HR Operations | People Services | 4 | 160 | $58K |
| People | Talent & Learning | People Development | 3 | 90 | $70K |
| **Total** | | | **37** | **1,560** | |

### Tech Stack (for Layer 2 computation)

| Tool | Deployed To | Tasks It Can Address |
|------|-----------|---------------------|
| Microsoft Copilot | All functions | Document generation, email drafting, data summarization |
| ServiceNow AI | Technology, Claims | Ticket routing, knowledge base search, incident classification |
| UiPath RPA | Claims, Finance | Data entry, form processing, reconciliation |
| Workday AI | People, Finance | Report generation, absence pattern analysis |
| Custom Claims AI | Claims only | Claims triage, fraud scoring, document extraction |

### Human System Initial Conditions (per function)

| Function | AI Proficiency | Change Readiness | Trust Level | Political Capital |
|----------|---------------|-----------------|------------|-------------------|
| Claims | 25 | 45 | 35 | 50 |
| Technology | 60 | 70 | 65 | 75 |
| Finance | 30 | 50 | 40 | 55 |
| People | 20 | 55 | 45 | 60 |

### Management Level Distribution

| Level | Claims | Technology | Finance | People | Total |
|-------|--------|-----------|---------|--------|-------|
| Individual Contributor | 380 | 300 | 180 | 160 | 1,020 |
| Senior IC | 100 | 80 | 50 | 40 | 270 |
| Manager | 60 | 50 | 30 | 30 | 170 |
| Senior Manager | 20 | 20 | 15 | 15 | 70 |
| Director | 8 | 8 | 4 | 4 | 24 |
| VP | 2 | 2 | 1 | 1 | 6 |
| **Total** | **570** | **460** | **280** | **250** | **1,560** |

---

# PART III: DATA FILES SPECIFICATION

## File 1: `roles.csv` — The Role Catalog

```
role_id, role_name, function, sub_function, jfg, job_family,
management_level, headcount, avg_salary, automation_score,
augmentation_score, quantification_score
```

37 rows. One per role. Scores match real-data distributions.

## File 2: `workloads.csv` — Workloads per Role

```
workload_id, role_id, workload_name, time_pct,
directive_pct, feedback_loop_pct, task_iteration_pct,
learning_pct, validation_pct, negligibility_pct
```

~150 rows. 3-5 workloads per role. The 6-category percentages sum to 100.

## File 3: `tasks.csv` — Tasks per Workload

```
task_id, workload_id, task_name, category,
effort_hours_month, skill_required, automatable_by_tool,
compliance_mandated_human
```

~600 rows. 3-5 tasks per workload. `category` is one of the six Etter categories. `automatable_by_tool` maps to tech stack.

## File 4: `skills.csv` — Skills per Workload

```
skill_id, workload_id, skill_name, skill_type,
proficiency_required, is_sunrise, is_sunset
```

~400 rows. Skills mapped to workloads with sunrise/sunset flags.

## File 5: `tech_stack.csv` — Deployed Technology

```
tool_id, tool_name, deployed_to_function, task_categories_addressed,
license_cost_per_user_month, current_adoption_pct
```

~12 rows. Tech stack with deployment scope and current adoption.

## File 6: `human_system.csv` — Human System State

```
function, ai_proficiency, change_readiness, trust_level,
political_capital, transformation_fatigue, learning_velocity
```

4 rows. One per function. Initial conditions.

## File 7: `simulation_params.csv` — Scenario Parameters

```
scenario_id, scenario_name, alpha_adopt, alpha_expand, alpha_extend,
phases, policy, readiness_threshold, investment_budget,
enable_workflow_automation, s_curve_k, s_curve_midpoint
```

5 rows. One per policy scenario (P1-P5).

---

# PART IV: IMPLEMENTATION ARCHITECTURE

## Design Principle: Fractal Simplicity

The same cascade function operates at every scale. No special cases for roles vs. functions vs. org — just different aggregation levels.

```
CASCADE(scope, stimulus, params, timestep)
  → resolves affected entities
  → computes per-entity changes
  → aggregates to parent level
  → returns metrics at all levels
```

## Module Structure

```
workforce_twin_mvp/
├── data/                        # Synthetic data (CSV files)
│   ├── roles.csv
│   ├── workloads.csv
│   ├── tasks.csv
│   ├── skills.csv
│   ├── tech_stack.csv
│   ├── human_system.csv
│   └── simulation_params.csv
│
├── models/                      # Data models (stocks)
│   ├── __init__.py
│   ├── organization.py          # Stock 5: Org structure + taxonomy
│   ├── task_state.py            # Stock 1: Three-layer classification
│   ├── workforce.py             # Stock 2: Capacity
│   ├── skills.py                # Stock 3: Skill inventory
│   ├── financial.py             # Stock 4: Financial position
│   ├── human_system.py          # Stock 6: Trust, readiness, proficiency
│   └── risk.py                  # Stock 7: Risk register
│
├── engine/                      # Simulation engine (flows)
│   ├── __init__.py
│   ├── cascade.py               # The 9-step cascade propagation
│   ├── rates.py                 # Three rate equations (S-curves)
│   ├── feedback.py              # Eight feedback loops
│   └── simulator.py             # Time-step loop orchestrator
│
├── analysis/                    # Metrics and comparison
│   ├── __init__.py
│   ├── metrics.py               # All metric computations
│   ├── scenarios.py             # Multi-scenario comparison
│   └── sensitivity.py           # Sensitivity analysis
│
├── stages/                      # Stage-specific runners
│   ├── stage_0_snapshot.py      # Static gap analysis
│   ├── stage_1_cascade.py       # Single-step cascade
│   ├── stage_2_timeseries.py    # Time-stepped (no feedback)
│   ├── stage_3_feedback.py      # Full feedback loops
│   └── stage_4_scenarios.py     # Multi-scenario comparison
│
├── tests/                       # Validation tests
│   ├── test_stage_0.py
│   ├── test_stage_1.py
│   ├── test_stage_2.py
│   ├── test_stage_3.py
│   └── test_stage_4.py
│
├── outputs/                     # Simulation results
│   └── (generated CSV/JSON/charts)
│
└── main.py                      # CLI entry point
```

## Key Design Decisions

**Python dataclasses for stocks:** Simple, type-hinted, no ORM overhead. Each stock is a dataclass with methods for inflow/outflow.

**Monthly timestep:** Matches enterprise decision cycles (quarterly reviews = every 3 timesteps).

**CSV for data, JSON for results:** CSV is human-readable and debuggable. JSON captures hierarchical simulation results.

**No database in MVP:** Everything in-memory. The point is to validate the MODEL, not the infrastructure. Neo4j integration comes after the model is proven.

---

# PART V: VALIDATION FRAMEWORK

## Per-Stage Acceptance Tests

### Stage 0 Tests
```
assert all(adoption_gap >= 0 for role in roles)
assert all(capability_gap >= 0 for role in roles)
assert org_total == sum(function_totals)
assert top_opportunity.value > 0
```

### Stage 1 Tests
```
assert 0 < freed_hours < total_hours
assert headcount_reduced <= function_headcount
assert savings_if_any > 0 or headcount_reduced == 0
assert len(risks_flagged) > 0
assert len(sunset_skills) > 0
assert len(sunrise_skills) > 0
```

### Stage 2 Tests
```
# S-curve shape
assert adoption[0] < adoption[6] < adoption[12] < adoption[24]
assert (adoption[24] - adoption[12]) < (adoption[12] - adoption[6])  # decelerating

# J-curve financials
assert net_position[3] <= net_position[0]  # initial dip (or flat for adoption gap)
assert net_position[36] > net_position[12] > 0  # eventual positive

# Skill valley
assert skill_gap[6] > skill_gap[0]   # gap opens
assert skill_gap[6] > skill_gap[24]  # gap closes

# Productivity valley
assert productivity[4] < productivity[0]   # dip
assert productivity[24] > productivity[0]  # recovery above baseline
```

### Stage 3 Tests
```
# Feedback effects
high_readiness_result = simulate(readiness=80)
low_readiness_result = simulate(readiness=30)
assert high_readiness_result.adoption_speed > low_readiness_result.adoption_speed

# Trust asymmetry
pre_error_trust = trust[6]
inject_ai_error(month=7)
assert trust[8] < pre_error_trust * 0.7  # significant drop
assert trust[12] < pre_error_trust       # still not recovered

# Proficiency compounds
assert proficiency[24] > proficiency[12] > proficiency[6]
```

### Stage 4 Tests
```
# Scenario ordering
assert p3.savings > p2.savings > p1.savings
assert p3.risk > p2.risk > p1.risk
assert p4.headcount_change == 0
assert p5.savings > p3.savings  # workflow automation bonus

# Sensitivity
base = simulate(readiness=50)
high = simulate(readiness=60)  # +20%
low = simulate(readiness=40)   # -20%
assert abs(high.savings - base.savings) / base.savings > 0.25  # >25% swing
```

---

# PART VI: SUCCESS CRITERIA

## The Model is Validated When:

1. **Redistribution dampening** is visible: automation of 40% ≠ 40% headcount reduction
2. **S-curves** produce realistic adoption shapes (not linear, not step)
3. **Skill valley** creates a productivity dip of 5-15% lasting 3-8 months
4. **Human multiplier** causes 2-3× difference in outcomes between high and low readiness
5. **Trust asymmetry** is visible: error recovery takes 3× longer than trust building
6. **J-curve** (or flat-then-rise) is visible in financial trajectory
7. **Seniority shift** produces diminishing returns visible after month 18
8. **Political capital** blocks resource allocation when below threshold
9. **Five scenarios** produce meaningfully different outcomes (not just scaled versions)
10. **Sensitivity analysis** confirms change readiness as #1 parameter

## What Comes After MVP Validation

| Step | Description | Timeline |
|------|------------|---------|
| 1 | Neo4j graph model for organization taxonomy | Week 1-2 post-validation |
| 2 | Real client data ingestion (HRIS integration) | Week 2-4 |
| 3 | Etter pipeline integration (Layer 1 scores) | Week 3-5 |
| 4 | Human system survey/inference engine | Week 4-6 |
| 5 | API endpoints for simulation trigger/results | Week 5-7 |
| 6 | Visualization layer (charts, dashboards) | Week 6-8 |

---

*No code without a validated model. No integration without validated code.*
*Stage 0 → 1 → 2 → 3 → 4. Each stage proves one more layer of the system.*
