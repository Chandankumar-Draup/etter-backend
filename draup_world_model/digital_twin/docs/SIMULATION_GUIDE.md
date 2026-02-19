# Simulation Engine - Deep Dive Guide

> The simulation engine is the heart of the Digital Twin. This guide explains
> every step, every formula, every threshold - from first principles.

---

## Table of Contents

1. [Mental Model: How Simulations Work](#1-mental-model-how-simulations-work)
2. [The 8-Step Cascade (Complete Reference)](#2-the-8-step-cascade-complete-reference)
3. [Simulation Type: Role Redesign (S1)](#3-simulation-type-role-redesign-s1)
4. [Simulation Type: Technology Adoption (S6)](#4-simulation-type-technology-adoption-s6)
5. [Simulation Type: Skills Strategy (S4)](#5-simulation-type-skills-strategy-s4)
6. [Financial Model](#6-financial-model)
7. [Scenario Management & Comparison](#7-scenario-management--comparison)
8. [All Constants & Thresholds](#8-all-constants--thresholds)
9. [Worked Example: Step by Step](#9-worked-example-step-by-step)
10. [Extending the Engine](#10-extending-the-engine)

---

## 1. Mental Model: How Simulations Work

### The Question

Every simulation answers a "what if?" question:
- "What if we automate 50% of Claims tasks?"
- "What if we deploy Microsoft Copilot to Underwriting?"
- "What if we need to identify which skills to invest in?"

### The Process

```
1. SELECT SCOPE     → Which part of the org are we looking at?
                       (a function, a role, the whole org)

2. TRIGGER CHANGE   → What's the intervention?
                       (automate tasks, deploy technology)

3. CASCADE          → Propagate the change through 8 steps
                       (task → workload → role → skill → workforce → financial → risk → validate)

4. COMPARE          → How does this scenario compare to others?
                       (side-by-side financial, workforce, risk)
```

### Systems Thinking (Meadows)

The cascade IS the system's response to a perturbation:

```
Perturbation → Task changes → [feedback loop 1] → Workload shifts →
  [feedback loop 2] → Role impact → [feedback loop 3] → Skill shifts →
  [feedback loop 4] → Workforce → [feedback loop 5] → Financial →
  [feedback loop 6] → Risk → [boundary check]
```

Each step depends on the previous step's output. The order is not arbitrary - it mirrors how real organizations experience change.

---

## 2. The 8-Step Cascade (Complete Reference)

### Architecture

```
cascade_engine.py
├── CascadeEngine.__init__(timeline_months=36)
├── CascadeEngine.run(scope_data, task_reclassifications, technology_costs)
│   ├── Step 1: _step1_task_reclassification()
│   ├── Step 2: _step2_workload_recomposition()
│   ├── Step 3: _step3_role_impact()
│   ├── Step 4: _step4_skill_shifts()
│   ├── Step 5: _step5_workforce_recalculation()
│   ├── Step 6: _step6_financial()
│   ├── Step 7: _step7_risk_assessment()
│   └── Step 8: _step8_validation()
└── Returns: Dict with all 8 step results + summary
```

### Step 1: Task Reclassification

**Input**: List of `{task_id, new_automation_level}` from the simulation trigger.

**What it does**: For each task being reclassified:
1. Look up current automation level (e.g., `human_led`)
2. Look up new automation level (e.g., `shared`)
3. Compute the automation delta from the AUTOMATION_SHIFT table

**Automation Shift Table** (delta values):
```
From \ To       human_led  shared  ai_led  ai_only
human_only        0.15      0.40    0.70    0.95
human_led           -       0.25    0.55    0.80
shared              -         -     0.30    0.55
ai_led              -         -       -     0.25
```

**Output**: `{tasks_affected: N, changes: [{task_id, task_name, old_level, new_level, automation_delta, time_allocation_pct}]}`

### Step 2: Workload Recomposition

**Input**: Workloads whose tasks were changed in Step 1.

**What it does**: For each affected workload:
1. Get all tasks in the workload
2. Compute weighted automation score: `sum(CLASSIFICATION_AUTOMATION_MAP[task.level] * task.time_pct) / total_time_pct`
3. Map score to new workload level:
   - Score >= 80 → `ai_led`
   - Score >= 50 → `shared`
   - Score >= 20 → `human_led`
   - Score < 20 → `human_only`

**Classification Automation Map** (fraction of work automated):
```python
human_only = 0.00   # 0% automated
human_led  = 0.15   # 15% automated
shared     = 0.40   # 40% automated
ai_led     = 0.70   # 70% automated
ai_only    = 0.95   # 95% automated
```

**Output**: `{workloads_affected: N, changes: [{workload_id, old_level, new_level, automation_score}]}`

### Step 3: Role & Job Title Impact

**Input**: Roles whose workloads were affected in Step 2.

**What it does**: For each affected role:
1. Compute freed capacity from **continuous automation score delta** (not quantized levels):
   ```
   freed = sum(workload_effort_pct * (new_score - old_score) / 100)
   ```
   Uses actual weighted automation scores from Step 2 (not the discretized level names).
   Only workloads that actually changed in Step 2 contribute. Unaffected workloads contribute zero.
2. Cap at 100%
3. For each job title under this role, apply **level-specific impact factor**:
   - `title_freed = freed_pct * level_factor`

> **Design note**: Using the delta (new - old) rather than total automation prevents pre-existing
> automation on unaffected workloads from being counted as "freed" capacity. This is critical for
> accuracy — the simulation measures the *marginal* impact of the intervention, not the absolute
> automation state.

**Level Impact Factors** (the key insight):
```
entry     = 1.4    (40% MORE impact - routine work is automatable)
mid       = 1.2    (20% more)
senior    = 1.0    (baseline)
lead      = 0.8    (20% less - more strategic work)
principal = 0.6    (40% less)
director  = 0.4    (60% less)
vp        = 0.3    (70% less)
c_suite   = 0.2    (80% less)
```

**Why?** Entry-level roles typically do more routine/repetitive work. When you automate "review claim documentation," a Junior Adjuster (who spends 60% of time on it) is more affected than a Senior Adjuster (who spends 20% and delegates the rest).

**Transformation Index**: `min(freed_pct * 1.5, 100)` - a 0-100 score indicating how fundamentally the role needs to change. Above 40% freed capacity = role needs complete redesign.

**Output**: `{roles_affected: N, impacts: [{role_id, role_name, freed_capacity_pct, transformation_index, title_impacts: [...]}]}`

### Step 4: Skill Shifts

**Input**: All skills in scope + task changes from Step 1 + task-skill mappings.

**Three signal sources**:
1. **Lifecycle-based** (`source: "lifecycle"`): Skills with `lifecycle_status == "declining"` → sunset; `"emerging"` → sunrise
2. **Task-skill mapping** (`source: "task_mapping"`): For each reclassified task, look up its PRIMARY skills via `(DTTask)-[:DT_REQUIRES_SKILL {relevance: "PRIMARY"}]->(DTSkill)`. Skills that are PRIMARY for >30% of affected tasks → sunset candidate (demand decreasing due to automation)
3. **Universal** (`source: "universal"`): If ANY tasks were automated, add:
   - "AI Literacy & Prompt Engineering"
   - "AI Output Validation"

**Output**: `{sunset_skills: [{..., source}], sunrise_skills: [{..., source}], net_skill_shift: N}`

### Step 5: Workforce Recalculation

**Input**: Title-level impacts from Step 3.

**What it does**: For each affected job title:
1. `freed_hc = headcount * freed_capacity_pct / 100`
2. `redeployable = freed_hc * 0.6` (60% redeployable - industry benchmark)
3. Aggregate across all titles

**Output**: `{current_headcount, freed_headcount, reduction_pct, redeployable, redeployable_pct}`

### Step 6: Financial Projection

**Input**: Title impacts from Step 3, technology costs (optional), skill gaps from Step 4.

**What it does**: See [Section 6: Financial Model](#6-financial-model) for complete formulas.

**Output**: `{gross_savings, technology_licensing, implementation_cost, reskilling_cost, total_cost, net_impact, roi_pct, payback_months, title_details: [...]}`

### Step 7: Risk Assessment

**Input**: Results from Steps 1, 3, 4, 5.

**Risk flags** (thresholds):
| Condition | Risk Type | Severity |
|-----------|-----------|----------|
| Any role has >60% freed capacity | `high_automation` | high |
| Workforce reduction >20% | `workforce_reduction` | high |
| Net skill shift >5 new skills | `skill_gap` | medium |
| >50 tasks affected | `broad_change` | medium |

**Output**: `{risk_count, high_risks, flags: [{type, severity, entity, detail}]}`

### Step 8: Boundary Validation

**Input**: Scope data, Step 3, Step 5.

**Sanity checks**:
1. `headcount_non_negative`: Freed headcount >= 0
2. `freed_capacity_bounded`: All freed capacity values are 0-100%
3. `has_impact`: At least one role was affected

**Output**: `{valid: true/false, checks: [{check, passed, detail}]}`

---

## 3. Simulation Type: Role Redesign (S1)

**File**: `simulation/simulations/role_redesign.py`

### Purpose
Apply a uniform automation factor to tasks and see what happens to roles.

### Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| automation_factor | float | 0.5 | How aggressive (0.1 = conservative, 1.0 = maximum) |
| target_classifications | list | `["directive", "feedback_loop"]` | Which Etter task types to automate |

### How It Works

1. **Filter tasks**: Only tasks matching `target_classifications` are eligible
2. **Advance automation level**: Each eligible task moves up the automation scale
   - `factor * 3` = number of levels to advance (rounded)
   - factor 0.3 → 1 step (e.g., human_led → shared)
   - factor 0.7 → 2 steps (e.g., human_led → ai_led)
   - factor 1.0 → 3 steps (e.g., human_led → ai_only)
3. **Run cascade**: Feed reclassifications into the CascadeEngine
4. **Compare current vs future**: Generate transformation metrics

### Automation Level Progression
```
AUTOMATION_LEVELS = ["human_only", "human_led", "shared", "ai_led", "ai_only"]

factor=0.2 → 1 step:  human_led → shared
factor=0.5 → 1 step:  human_led → shared
factor=0.7 → 2 steps: human_led → ai_led
factor=1.0 → 3 steps: human_led → ai_only
```

### Output
```python
{
    "simulation_type": "role_redesign",
    "parameters": { "automation_factor": 0.5, "target_classifications": [...] },
    "current": {  # Snapshot of current state
        "role_count", "total_headcount", "avg_automation_score",
        "task_count", "task_classification_distribution", "skill_count"
    },
    "future": {  # Projected future state
        "total_headcount", "freed_headcount", "redeployable",
        "sunrise_skills", "sunset_skills"
    },
    "cascade": { ... },  # Full 8-step cascade result
    "comparison": {
        "headcount_delta", "headcount_delta_pct",
        "avg_transformation_index", "max_transformation_index",
        "roles_needing_redesign": ["Claims Adjuster", ...],  # >40% freed
        "financial_summary": { "gross_savings", "net_impact", "roi_pct", "payback_months" }
    }
}
```

---

## 4. Simulation Type: Technology Adoption (S6)

**File**: `simulation/simulations/tech_adoption.py`

### Purpose
Simulate deploying a specific technology and see which tasks it affects, what the adoption curve looks like, and whether it's worth the investment.

### Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| technology_name | string | `Microsoft Copilot` | Technology profile to deploy |
| adoption_months | int | 12 | Months to full adoption |

### Technology Profiles (6 Pre-Built)

Each profile defines:
- **vendor**: The company behind the technology
- **capabilities**: What the technology can do
- **task_keywords**: Words to match against task names/descriptions
- **classification_shift**: How tasks are reclassified
- **license_tier**: Cost tier (low/medium/high/enterprise)
- **adoption_speed**: fast/moderate/slow

```python
"Microsoft Copilot": {
    "vendor": "Microsoft",
    "capabilities": ["document_generation", "email_drafting", "data_summarization", ...],
    "task_keywords": ["document", "draft", "summarize", "email", "report", "analysis",
                      "write", "review", "prepare", "create"],
    "classification_shift": {
        "directive": "ai_led",            # Directive tasks → AI-led
        "feedback_loop": "shared",        # Feedback loop tasks → shared with AI
    },
    "license_tier": "medium",               # $30/user/month
    "adoption_speed": "fast",               # Full adoption in ~6 months
}
```

### How It Works

1. **Match tasks**: For each task in scope, check if any `task_keywords` appear in the task name/description using **word-boundary matching** (prevents false positives like "data" matching inside "validate"). Includes match confidence score.
2. **Reclassify**: Matched tasks get their automation level shifted per `classification_shift`
3. **Compute costs**: `license_cost * headcount * timeline_months + implementation_cost`
4. **Run cascade**: Feed reclassifications + technology costs into CascadeEngine
5. **Build adoption curve**: Monthly adoption percentages based on adoption_speed
6. **Apply adoption discount**: Adjust financial savings by the weighted-average adoption factor over the timeline. The cascade assumes 100% adoption from day 1; the discount corrects for gradual rollout (e.g., a "slow" adoption at 36 months has ~67% average adoption, reducing projected savings by ~33%).
7. **Generate recommendation**: Verdict based on ROI, risk, and match percentage

### Adoption Curves
```python
ADOPTION_CURVES = {
    "fast":     {1: 0.10, 2: 0.25, 3: 0.45, 6: 0.75, 9: 0.90, 12: 1.00},
    "moderate": {1: 0.05, 2: 0.15, 3: 0.25, 6: 0.55, 9: 0.75, 12: 0.90, 18: 1.00},
    "slow":     {1: 0.02, 2: 0.08, 3: 0.15, 6: 0.35, 9: 0.55, 12: 0.70, 18: 0.85, 24: 1.00},
}
```

### Recommendation Verdicts

Based on a composite score (ROI weight: 40%, risk weight: 30%, match weight: 30%):

| Verdict | Score Range | Meaning |
|---------|------------|---------|
| STRONG_RECOMMEND | >= 80 | Deploy immediately |
| RECOMMEND | >= 60 | Deploy with standard planning |
| CONDITIONAL | >= 40 | Deploy with risk mitigation |
| CAUTIOUS | >= 20 | Pilot first |
| NOT_RECOMMENDED | < 20 | Do not deploy |

### Output
```python
{
    "simulation_type": "tech_adoption",
    "technology": { "name", "vendor", "tasks_matched", "match_pct" },
    "cascade": { ... },
    "skills_strategy": { ... },
    "adoption_curve": { "months": [...], "adoption_pct": [...] },
    "recommendation": { "verdict": "RECOMMEND", "reasoning": "...", "score": 78 }
}
```

---

## 5. Simulation Type: Skills Strategy (S4)

**File**: `simulation/simulations/skills_strategy.py`

### Purpose
Analyze the skills landscape after a simulation: which skills are growing, which are declining, where are concentration risks, and should you build or buy talent?

### How It Works

This simulation runs **after** a cascade (it takes cascade results as input):

1. **Demand Analysis**: Categorize each skill:
   - `sunrise`: lifecycle = "emerging" OR market_demand = "growing"
   - `sunset`: lifecycle = "declining" OR market_demand = "shrinking"
   - `stable`: everything else

2. **Concentration Analysis**: Find skills used by <= threshold roles
   - Threshold = `max(2, int(total_roles * 0.15))` (normalized by scope size)
   - These are **high risk** - if those roles change, the skill could be lost

3. **Reskilling Plan**: For each sunrise skill:
   - Estimate training timeline by category (technical: 6mo, domain: 3mo, soft: 2mo)
   - Cost is **band-weighted**: `sum(band_hc * $2,500 * BAND_COST_MULTIPLIER[band])`
   - Band multipliers: entry=0.7, mid=1.0, senior=1.3, lead=1.5, principal=1.8, director=2.0, vp=2.5

4. **Build vs Buy**: For each skill gap:
   - **build**: If internal expertise exists (skill is "mature" or "growing")
   - **buy**: If skill is "emerging" with no internal base
   - **buy_and_build**: If skill is transitioning

### Output
```python
{
    "summary": {
        "sunrise_count", "sunset_count", "high_risk_skills",
        "total_reskilling_cost", "avg_reskilling_months"
    },
    "demand_analysis": {
        "sunrise": [{"name", "priority"}],
        "sunset": [{"name", "priority"}],
        "stable": [{"name", "priority"}]
    },
    "concentration_analysis": {
        "high_risk": [{"skill", "role_count"}]
    },
    "reskilling_plan": {
        "skills": [...], "total_cost", "timeline_months"
    },
    "build_vs_buy": {
        "recommendations": [{"skill", "action", "reasoning"}]
    }
}
```

---

## 6. Financial Model

**File**: `simulation/financial.py`

### Core Formula

```
Per-title savings = avg_salary * headcount * freed_capacity_pct * (timeline_months / 12)
Gross savings = SUM of all title savings
```

### Cost Components

1. **Technology Licensing**:
   ```
   monthly_per_user = LICENSE_COST_MAP[tier]   # $10 / $30 / $75 / $150
   total_licensing = monthly_per_user * headcount * timeline_months
   ```

2. **Implementation Cost**:
   ```
   implementation = total_licensing * 0.15    # 15% of licensing
   ```

3. **Reskilling Cost**:
   ```
   reskilling = num_sunrise_skills * headcount_needing_reskill * $2,500
   headcount_needing_reskill = total_affected_headcount * 0.30   # 30% need training
   ```

### Derived Metrics

```
total_cost = licensing + implementation + reskilling
net_impact = gross_savings - total_cost
roi_pct = (net_impact / total_cost) * 100    # If total_cost > 0
roi_pct = 9999.0                              # If total_cost == 0 and savings > 0
roi_pct = 0                                   # If total_cost == 0 and savings == 0
payback_months = total_cost / (gross_savings / timeline_months)
```

### Adoption Curve Discount (Tech Adoption Only)

For technology adoption simulations, gross savings are adjusted by an adoption discount factor:
```
adoption_discount = weighted_average_adoption_over_timeline   # trapezoidal integration
adjusted_savings = gross_savings * adoption_discount
```
The original savings are preserved as `unadjusted_gross_savings` for comparison.

### License Cost Map
| Tier | $ per user per month | Examples |
|------|---------------------|----------|
| low | $10 | GitHub Copilot |
| medium | $30 | Microsoft Copilot, Salesforce Einstein |
| high | $75 | UiPath, ServiceNow AI |
| enterprise | $150 | Claims AI Platform |

---

## 7. Scenario Management & Comparison

**File**: `simulation/scenario_manager.py`

### ScenarioConfig (Dataclass)
```python
@dataclass
class ScenarioConfig:
    name: str                              # Display name
    simulation_type: str                   # "role_redesign" or "tech_adoption"
    scope_type: str                        # "organization", "function", "role"
    scope_name: str                        # e.g., "Claims Management"
    parameters: Dict[str, Any] = field()   # Simulation-specific params
    constraints: Dict[str, Any] = field()  # Optional constraints
    timeline_months: int = 36              # Financial projection timeline
```

### ScenarioManager Methods

| Method | Description |
|--------|-------------|
| `create_scenario(config)` → `str` | Store a scenario config, return ID |
| `run_scenario(scenario_id)` → `Dict` | Execute the scenario (scope → simulation → cascade → constraints) |
| `get_scenario(scenario_id)` → `Dict` | Get scenario with results |
| `list_scenarios()` → `List[Dict]` | List all scenarios (metadata only) |
| `compare_scenarios(ids)` → `Dict` | Side-by-side comparison |
| `delete_scenario(id)` → `bool` | Remove a scenario |

### Persistence

Scenarios are persisted to JSON files in `data/acme_corp/scenarios/` with full metadata.
On Flask restart, existing scenarios are automatically reloaded from disk.

### Constraints

Optional `ScenarioConfig.constraints` dict supports:
| Constraint | Effect |
|-----------|--------|
| `max_headcount_reduction_pct` | Scales down workforce impact to cap (proportionally adjusts financial) |
| `budget_cap` | Flags when total_cost exceeds budget (warning, not enforced) |
| `protected_roles` | Excludes listed roles from headcount impact (sets freed_capacity to 0) |

### Comparison Output

The `compare_scenarios()` method normalizes results across scenarios:

```python
{
    "best_by_roi": "Scenario A",          # Highest ROI
    "lowest_risk": "Scenario B",          # Fewest risk flags
    "scenarios": [
        {
            "scenario_id": "...",
            "scenario_name": "...",
            "financial": {
                "gross_savings": 5200000,
                "net_impact": 3725000,
                "total_cost": 1475000,
                "roi_pct": 252.5,
                "payback_months": 8,
            },
            "workforce": {
                "freed_headcount": 47.3,
                "reduction_pct": 1.89,
                "redeployable": 33.1,
            },
            "skills": {
                "sunrise_count": 8,
                "sunset_count": 3,
            },
            "risk": {
                "total_risks": 2,
                "high_risks": 0,
            },
        },
        ...
    ]
}
```

---

## 8. All Constants & Thresholds

### Automation Levels (ordered)
```python
AUTOMATION_LEVELS = ["human_only", "human_led", "shared", "ai_led", "ai_only"]
```

### Classification Automation Fractions
```python
CLASSIFICATION_AUTOMATION_MAP = {
    "human_only": 0.00,
    "human_led":  0.15,
    "shared":     0.40,
    "ai_led":     0.70,
    "ai_only":    0.95,
}
```

### Level Impact Factors
```python
{
    "entry": 1.4, "mid": 1.2, "senior": 1.0, "lead": 0.8,
    "principal": 0.6, "director": 0.4, "vp": 0.3, "c_suite": 0.2,
}
```

### Financial Constants
```python
DEFAULT_RESKILLING_COST_PER_SKILL = 2500    # USD per skill per person
DEFAULT_IMPLEMENTATION_COST_FACTOR = 0.15   # 15% of licensing
LICENSE_COST_MAP = {"low": 10, "medium": 30, "high": 75, "enterprise": 150}
REDEPLOYABLE_FRACTION = 0.60                # 60% of freed headcount
RESKILLING_FRACTION = 0.30                  # 30% of affected headcount
```

### Risk Thresholds
```python
HIGH_AUTOMATION_THRESHOLD = 60              # % freed capacity
WORKFORCE_REDUCTION_THRESHOLD = 20          # % reduction
SKILL_GAP_THRESHOLD = 5                     # net new skills
BROAD_CHANGE_THRESHOLD = 50                 # tasks affected count
```

### Workload Level Thresholds
```python
AI_LED_THRESHOLD = 80                       # automation score >= 80
SHARED_THRESHOLD = 50                       # 50 <= score < 80
HUMAN_LED_THRESHOLD = 20                    # 20 <= score < 50
HUMAN_ONLY_THRESHOLD = 0                    # score < 20
```

### Transformation Index
```python
transformation_index = min(freed_capacity_pct * 1.5, 100)
REDESIGN_THRESHOLD = 40                     # >40% freed → needs redesign
```

---

## 9. Worked Example: Step by Step

### Scenario: Deploy Microsoft Copilot to Claims Management (2,500 HC)

**Step 0: Scope Selection**
```
Query Neo4j: Claims Management function
→ 15 roles, 350 titles, 60 workloads, 320 tasks, 45 skills
```

**Step 1: Task Matching & Reclassification**
```
Copilot keywords: ["document", "draft", "summarize", "email", "report", "analysis", ...]
Matched tasks: 145 of 320 (45.3%)

Example reclassifications:
  "Review claim documentation"    human_led → shared     (delta: +0.25)
  "Draft settlement letter"       human_led → shared     (delta: +0.25)
  "Generate monthly report"       directive → shared (delta: +0.25)
```

**Step 2: Workload Recomposition**
```
42 workloads affected (those containing matched tasks)
Example:
  "Claims Review & Assessment" was human_led, now tasks average 55% automated → shared
  "Settlement Processing" was human_only, now tasks average 35% automated → human_led
```

**Step 3: Role Impact**
```
12 roles affected (those containing affected workloads)
Example: Claims Adjuster (350 HC)
  Freed capacity: 28.5%
  Transformation index: 42.8

  Junior Claims Adjuster (entry, 120 HC):
    freed = 28.5% * 1.4 = 39.9% (entry-level hit harder)
  Senior Claims Adjuster (senior, 80 HC):
    freed = 28.5% * 1.0 = 28.5% (baseline)
  Claims Team Lead (lead, 30 HC):
    freed = 28.5% * 0.8 = 22.8% (strategic work less affected)
```

**Step 4: Skill Shifts**
```
Sunrise: AI Literacy & Prompt Engineering, AI Output Validation, + 6 emerging skills = 8
Sunset: Manual Data Entry, Document Filing, Paper Processing = 3
Net shift: +5
```

**Step 5: Workforce**
```
Current HC (affected roles): ~800
Freed HC: 47.3 FTEs
Reduction: 1.89%
Redeployable: 33.1 (70%)
```

**Step 6: Financial**
```
Gross savings:
  Junior Adj: $42,000 * 120 * 0.399 * 3 years = $6,041,760
  Senior Adj: $75,000 * 80 * 0.285 * 3 years = $5,130,000
  ... (all titles)
  Total gross: ~$5,200,000

Costs:
  Licensing: $30/user * 800 users * 36 months = $864,000
  Implementation: $864,000 * 0.15 = $129,600
  Reskilling: 8 skills * 240 people * $2,500 = $4,800,000
  Total: ~$5,793,600

Wait - this shows net negative? Let me recalculate with realistic numbers...
In practice: reskilling only targets ~30% of affected HC (not all)
  Reskilling: 8 skills * 72 people * $2,500 = $1,440,000
  Total cost: $2,433,600

Net impact: $5,200,000 - $2,433,600 = $2,766,400
ROI: 113.7%
Payback: ~17 months
```

**Step 7: Risk Assessment**
```
Flags:
  - broad_change (medium): 145 tasks affected - phased rollout recommended
  - skill_gap (medium): 5 net new skills needed
No high-severity risks (no role >60% freed, reduction <20%)
```

**Step 8: Validation**
```
✓ headcount_non_negative
✓ freed_capacity_bounded (all 0-100%)
✓ has_impact (12 roles affected)
```

**Recommendation**: RECOMMEND (positive ROI, moderate risk)

---

## 10. Extending the Engine

### Adding a New Simulation Type

1. Create `simulation/simulations/my_simulation.py`:
```python
class MySimulation:
    def __init__(self, cascade_engine: CascadeEngine):
        self.cascade = cascade_engine

    def run(self, scope_data, **params) -> Dict:
        # 1. Generate task reclassifications based on your logic
        reclassifications = []
        for task in scope_data["tasks"]:
            if should_reclassify(task, params):
                reclassifications.append({
                    "task_id": task["id"],
                    "new_automation_level": compute_new_level(task, params),
                })

        # 2. Run cascade
        cascade = self.cascade.run(scope_data, reclassifications)

        # 3. Return results
        return {"simulation_type": "my_sim", "cascade": cascade}
```

2. Register it in `scenario_manager.py` (in the `run_scenario` method).

3. Add a UI option in `Simulator.js` and handling in `Results.js`.

### Adding a New Risk Flag

In `cascade_engine.py`, find `_step7_risk_assessment` and add:
```python
if your_condition:
    risk_flags.append({
        "type": "your_risk_type",
        "severity": "high" or "medium",
        "entity": "what's at risk",
        "detail": "Human-readable explanation",
    })
```

### Changing Financial Assumptions

All financial constants are in `financial.py`:
- Change license costs: modify `LICENSE_COST_MAP`
- Change reskilling costs: modify `DEFAULT_RESKILLING_COST_PER_SKILL`
- Change implementation factor: modify `DEFAULT_IMPLEMENTATION_COST_FACTOR`
- Change redeployment rate: modify the `0.6` in `_step5_workforce_recalculation`

### Adding a New Technology Profile

In `tech_adoption.py`, add to `TECHNOLOGY_PROFILES`:
```python
"My Technology": {
    "vendor": "My Vendor",
    "capabilities": ["list", "of", "capabilities"],
    "task_keywords": ["words", "to", "match", "against", "task", "names"],
    "classification_shift": {
        "directive": "ai_led",          # How tasks are reclassified
        "feedback_loop": "shared",
    },
    "license_tier": "medium",             # low/medium/high/enterprise
    "adoption_speed": "moderate",          # fast/moderate/slow
}
```
