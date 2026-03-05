# Data Ingestion Analysis: First Principles & Systems Thinking

## Document Purpose

A comprehensive analysis of every data point in the Workforce Twin simulation system -- what they are, how they connect, how they flow through the computation pipeline, and how the ingestion system can be improved.

---

## 1. The System from First Principles

### 1.1 What Problem Does This Data Solve?

The Workforce Twin models an organization as a **system of stocks and flows** (per Donella Meadows' systems thinking framework). The core question:

> "If we deploy AI tools into this organization, what happens to the workforce over 36 months?"

This requires modeling **7 interacting stocks**:
1. **Task Classification State** -- what work exists and how automatable it is
2. **Workforce Capacity** -- who does the work and at what cost
3. **Skill Inventory** -- what capabilities exist and which are changing
4. **Financial Position** -- investment vs. savings over time
5. **Org Structure** -- hierarchy for aggregation
6. **Human System** -- readiness, trust, proficiency (the binding constraint)
7. **Tech Stack** -- what tools are deployed and how adopted

### 1.2 The Fundamental Data Equation

At its core, the entire simulation reduces to:

```
Freed Capacity = f(Task Automation Potential, Tool Coverage, Human Adoption Rate)
```

Where:
- **Task Automation Potential** comes from task category classification (the Etter framework)
- **Tool Coverage** comes from matching deployed tools to tasks
- **Human Adoption Rate** is modulated by 8 feedback loops operating on human system state

Every data point exists to serve one side of this equation.

---

## 2. Data Entity Analysis: The 7 CSV Files

### 2.1 roles.csv -- Stock 2: Workforce Capacity

**File**: `data/roles.csv` | **Records**: 38 roles | **Model**: `Role` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `role_id` | PK | Unique identifier (e.g., CL-001) | Foreign key in workloads; index key everywhere |
| `role_name` | str | Human-readable name | Display, reporting, explainability narratives |
| `function` | str | Top-level org unit (Claims, Technology, Finance, People) | **Critical**: determines tool deployment scope, human system lookup, function-level aggregation |
| `sub_function` | str | Second-level grouping | Org hierarchy (OrgNode), scenario targeting |
| `jfg` | str | Job Function Group | Aggregation level between sub_function and job_family |
| `job_family` | str | Specific job family | Finest non-role grouping; used in org tree |
| `management_level` | str | IC, Senior IC, Manager, Director | **Critical**: determines productive hours (IC=128h, Director=72h), seniority offset in feedback loops |
| `headcount` | int | Number of people in this role | **Critical**: scales everything -- hours, costs, FTEs freed, financial impact |
| `avg_salary` | float | Average annual salary ($) | Financial impact: annual_cost = headcount x avg_salary; savings = FTEs_freed x avg_salary |
| `automation_score` | float | Etter L1 automation % (0-100) | Role-level aggregation display; NOT used in task-level computation |
| `augmentation_score` | float | Etter L1 augmentation % (0-100) | Role-level aggregation display; combined with automation for "AI spectrum" |
| `quantification_score` | float | Overall quantification confidence (0-100) | Currently display-only; could be used as confidence weighting |

**First Principles Assessment**:
- `automation_score` and `augmentation_score` are **redundant** with the task-level computation. The gap engine computes L1/L2/L3 from tasks, making these role-level scores decorative. They exist as Etter input scores but the simulation doesn't actually use them for computation.
- `quantification_score` is **unused** in any engine computation. It represents data quality confidence but is never applied as a weight or filter.

**Entity Relationships**:
```
Role (1) ---> (N) Workload ---> (N) Task
                             ---> (N) Skill
Role.function ---> HumanSystem.function (1:1)
Role.function ---> Tool.deployed_to_functions (N:M)
```

### 2.2 workloads.csv -- The Bridge Entity

**File**: `data/workloads.csv` | **Records**: 152 workloads | **Model**: `Workload` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `workload_id` | PK | Unique identifier (e.g., WL-0001) | FK in tasks and skills |
| `role_id` | FK | Parent role | Builds `workloads_by_role` index |
| `workload_name` | str | Activity cluster name (e.g., "Document Processing") | Display, aggregation labels |
| `time_pct` | float | % of role's time spent on this workload | **Critical**: determines workload weight in role-level aggregation |
| `directive_pct` | float | % of workload that is directive tasks | Category distribution; used in `ai_automatable_pct` property |
| `feedback_loop_pct` | float | % that is feedback loop tasks | Part of `ai_automatable_pct` |
| `task_iteration_pct` | float | % that is task iteration | Part of `augmentable_pct` |
| `learning_pct` | float | % that is learning tasks | Part of `augmentable_pct` |
| `validation_pct` | float | % that is validation tasks | Part of `augmentable_pct` |
| `negligibility_pct` | float | % that is human-only tasks | The `human_only_pct` property |

**First Principles Assessment**:
- The 6 category percentages **must sum to 100** but this is never validated in the loader. A data quality risk.
- `time_pct` across all workloads for a role **must sum to 100** -- also not validated.
- The category percentages are **duplicative** with the actual task-level categories. The tasks.csv has individual task categories, while workloads.csv has aggregate percentages. These can drift out of sync.
- The workload is the **critical bridge** between the role (who) and tasks (what). Without it, you can't map people to work.

**Computed Properties**:
- `ai_automatable_pct` = directive_pct + feedback_loop_pct (fully automatable categories)
- `augmentable_pct` = task_iteration_pct + learning_pct + validation_pct
- `human_only_pct` = negligibility_pct

### 2.3 tasks.csv -- Stock 1: Task Classification State (The Leaf)

**File**: `data/tasks.csv` | **Records**: 583 tasks | **Model**: `Task` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `task_id` | PK | Unique identifier (e.g., TK-0001) | Index key |
| `workload_id` | FK | Parent workload | Builds `tasks_by_workload` index |
| `task_name` | str | Activity name (e.g., "Flag missing information") | Display, reclassification reporting |
| `category` | str | Etter classification: directive/feedback_loop/task_iteration/learning/validation/negligibility | **THE most critical field**: determines L1 automation potential via `CATEGORY_AUTOMATION_POTENTIAL` lookup |
| `effort_hours_month` | float | Hours per person per month | **Critical**: multiplied by automation % to get freed hours; base for all capacity calculations |
| `automatable_by_tool` | str/null | Which specific tool can automate this | **Critical**: the L2 achievable test -- task must match tool by name AND category AND function deployment |
| `compliance_mandated_human` | bool | Regulatory floor flag | If True, L1 is capped at 5% regardless of category; task is protected from automation |

**First Principles Assessment**:
- This is where **value is computed**. The gap engine's `classify_task()` operates at this level.
- The `category` field drives the entire automation potential hierarchy:
  - directive: 90% potential, 85% freed (76.5% after shadow work tax)
  - feedback_loop: 85% potential, 75% freed (67.5% after shadow work tax)
  - task_iteration: 50% potential, 35% freed (31.5% after shadow work tax)
  - learning: 40% potential, 25% freed (22.5% after shadow work tax)
  - validation: 45% potential, 30% freed (27% after shadow work tax)
  - negligibility: 5% potential, 0% freed
- The **three-layer model** computed on each task:
  - **L1 (Etter Ceiling)**: From category lookup. "What COULD be automated?"
  - **L2 (Achievable)**: L1 if a matching tool exists, else 0. "What CAN be automated given our tech?"
  - **L3 (Realized)**: L2 x tool's current_adoption_pct. "What IS automated today?"
- Gaps are the economic signal:
  - **Adoption Gap** = L2 - L3 (free money -- tool exists, just use it more)
  - **Capability Gap** = L1 - L2 (need new tools)
  - **Total Gap** = L1 - L3 (full opportunity)

**Three-way matching requirement** (in `_tool_covers_task`):
```python
deployed_to_function AND task.category in tool.task_categories_addressed AND task.automatable_by_tool == tool.tool_name
```
All three conditions must be True for L2 > 0. This is strict by design.

### 2.4 skills.csv -- Stock 3: Skill Inventory

**File**: `data/skills.csv` | **Records**: 692 skills | **Model**: `Skill` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `skill_id` | PK | Unique identifier | Index key |
| `workload_id` | FK | Parent workload | Builds `skills_by_workload` index |
| `skill_name` | str | Skill name (e.g., "insurance regulation", "AI-assisted triage") | Display, sunset/sunrise reporting |
| `skill_type` | str | current/sunrise/sunset | **Critical**: determines cascade Step 4 behavior |
| `proficiency_required` | int | Required level (0-100) | Used to flag `critical_sunset` skills (>= 70 proficiency) |
| `is_sunrise` | bool | Emerging skill flag | When True + workload being transformed -> confirmed sunrise |
| `is_sunset` | bool | Declining skill flag | When True + workload being automated -> confirmed sunset |

**First Principles Assessment**:
- Skills drive the **Step 4 cascade** (skill impact) and the **skill valley feedback loop** (B2)
- The skill gap (sunrise count - sunset count) modulates effective adoption rate via `b2_skill_valley()`
- `proficiency_required` is currently only used for the critical_sunset threshold (>= 70). It could be much more valuable as a reskilling cost/duration driver.
- Skills are **per-workload, not per-role**. This means skill transitions are tied to which workloads get automated, not which roles are affected. This is architecturally correct (skills attach to work, not people).
- The `is_sunrise`/`is_sunset` booleans are **redundant** with `skill_type`. A skill with type="sunrise" always has is_sunrise=True. This is a normalization issue.

### 2.5 tech_stack.csv -- Stock 7: Technology Stack

**File**: `data/tech_stack.csv` | **Records**: 5 tools | **Model**: `Tool` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `tool_id` | PK | Unique identifier (e.g., TOOL-01) | Index key |
| `tool_name` | str | Tool name (e.g., "Microsoft Copilot") | **Critical**: matched against task.automatable_by_tool |
| `deployed_to_function` | list(str) | Functions where deployed ("All" or specific) | **Critical**: scope filter in tool-task matching |
| `task_categories_addressed` | list(str) | Which Etter categories this tool handles | **Critical**: category filter in tool-task matching |
| `license_cost_per_user_month` | float | Monthly per-user license cost ($) | Financial impact: annual_license = cost x 12 x affected_headcount |
| `current_adoption_pct` | float | Current adoption level (0-100) | **Critical**: L3 = L2 x (current_adoption_pct / 100). The adoption gap signal. |

**First Principles Assessment**:
- With only 5 tools, this is the **smallest but most impactful** dataset. Each tool's `current_adoption_pct` directly determines the adoption gap (free money).
- The `deployed_to_function` field creates a **scope matrix** -- not all tools serve all functions.
- The `task_categories_addressed` field creates a **capability matrix** -- not all tools automate all category types.
- **Missing data**: No tool versioning, no effectiveness rating, no integration complexity score.

### 2.6 human_system.csv -- Stock 6: Human Readiness (The Binding Constraint)

**File**: `data/human_system.csv` | **Records**: 4 (one per function) | **Model**: `HumanSystem` dataclass

| Column | Type | Purpose | How It's Used |
|--------|------|---------|---------------|
| `function` | PK | Function name | Lookup key from Role.function |
| `ai_proficiency` | float | Can the workforce work WITH AI? (0-100) | Weight: 0.35 in effective_multiplier |
| `change_readiness` | float | Willingness to adopt (0-100) | Weight: 0.45 in effective_multiplier (highest) |
| `trust_level` | float | Trust in AI tools (0-100) | Weight: 0.20 in effective_multiplier; veto if < 10 |
| `political_capital` | float | Leadership mandate strength (0-100) | Capital multiplier: < 20 -> 0.2, < 40 -> 0.6, else 1.0 |
| `transformation_fatigue` | float | Accumulated change exhaustion (1-5 scale) | Recovery dampener in readiness change calculation |
| `learning_velocity_months` | float | Months to meaningful proficiency gain | Proficiency learning rate factor = baseline / function_months |

**First Principles Assessment**:
- This is the **smallest file but arguably the most important**. It seeds the initial conditions for 8 feedback loops that run for 36 months.
- The effective_multiplier formula: `max(0.15, 0.35*proficiency + 0.45*readiness + 0.20*trust) / 100`
- The **veto mechanism**: if trust < 10 OR readiness < 10, multiplier drops to 0.05 regardless of other values.
- `learning_velocity_months` creates **function-specific learning speeds**: Technology (3mo) learns 2x faster than baseline (6mo), Claims (8mo) learns 0.75x.
- **Critical limitation**: One row per function means ALL roles within a function share the same human system parameters. A Claims Director and a Claims Data Entry Clerk have the same trust and readiness levels. This is a significant modeling simplification.

### 2.7 simulation_params.csv -- The 5 Policy Scenarios

**File**: `data/simulation_params.csv` | **Records**: 5 scenarios

| Column | Type | Purpose |
|--------|------|---------|
| `scenario_id` | PK | P1-P5 |
| `scenario_name` | str | Cautious, Balanced, Aggressive, Capability-First, AI-Age Accelerated |
| `alpha_adopt` | float | Phase 1 S-curve ceiling (0.5-0.8) |
| `alpha_expand` | float | Phase 2 S-curve ceiling (0.0-0.5) |
| `alpha_extend` | float | Phase 3 S-curve ceiling (0.0-0.3) |
| `phases` | list(str) | Which phases are active |
| `policy` | str | HC policy: natural_attrition/moderate_reduction/active_reduction/no_layoffs/rapid_redeployment |
| `readiness_threshold` | float | Minimum readiness to proceed (0-80) |
| `investment_budget` | str | low/medium/high |
| `enable_workflow_automation` | bool | P5 only: non-linear workflow gains |
| `s_curve_k_adopt` | float | S-curve steepness (0.3-0.4) |
| `s_curve_midpoint_adopt` | float | S-curve inflection month (3-4) |
| `absorption_factor` | float | Base redistribution (0.0-0.4) |
| `trust_build_rate` | float | Monthly trust gain rate (0.02-0.035) |
| `trust_destroy_factor` | float | Trust destruction on error (0.2-0.35) |
| `reskilling_delay_months` | float | Months before reskilling takes effect (3-6) |

**First Principles Assessment**:
- These scenarios are loaded from CSV but **also hardcoded** in `rates.py` as `P1_CAUTIOUS` through `P5_ACCELERATED`. The CSV and Python definitions could diverge.
- The S-curve equation: `S(t) = alpha / (1 + e^(-k * (t - midpoint)))` -- only 3 parameters but they produce dramatically different adoption trajectories.

---

## 3. Data Flow Architecture

### 3.1 The Pipeline

```
CSV Files (7 sources)
    |
    v
loader.py: load_organization()
    |  Reads CSVs into typed dataclasses
    |  Builds reverse-lookup indexes
    v
OrganizationData (in-memory graph)
    |
    +---> gap_engine.py: compute_snapshot()     [Stage 0: Static Analysis]
    |         classify_task() x 583 tasks
    |         Aggregate: task -> workload -> role -> function -> org
    |
    +---> cascade.py: run_cascade()             [Stage 1: Single Cascade]
    |         9 steps: Scope -> Reclassify -> Capacity -> Skills ->
    |                  Workforce -> Financial -> Structural -> Human -> Risk
    |
    +---> simulator.py: simulate()              [Stage 2: Open-Loop Time Series]
    |         S-curve adoption over 36 months, NO feedback loops
    |
    +---> simulator_fb.py: simulate_with_feedback()  [Stage 3: Feedback-Enabled]
    |         8 feedback loops modulate adoption dynamically
    |         Non-linear, path-dependent outcomes
    |
    +---> inverse_solver.py: solve_inverse()    [Stage 4: Target-Seeking]
              Binary search on alpha to hit HC/budget/automation targets
```

### 3.2 The Index System

After loading, `OrganizationData.build_indexes()` creates 5 reverse-lookup dictionaries:

| Index | Mapping | Purpose |
|-------|---------|---------|
| `workloads_by_role` | role_id -> [workload_ids] | Walk from role to its work |
| `tasks_by_workload` | workload_id -> [task_ids] | Walk from workload to leaf tasks |
| `skills_by_workload` | workload_id -> [skill_ids] | Walk from workload to required skills |
| `roles_by_function` | function -> [role_ids] | Function-level aggregation |
| `roles_by_jfg` | jfg -> [role_ids] | JFG-level aggregation |

These indexes enable O(1) traversal in all computation phases.

---

## 4. Systems Thinking Analysis

### 4.1 The Feedback Loop Structure

The data feeds 8 feedback loops (4 balancing, 4 reinforcing):

**Balancing (dampen change)**:
- **B1: Capacity Absorption** -- Uses: headcount, workload effort hours, absorption_factor
- **B2: Skill Valley** -- Uses: skill sunrise/sunset counts, proficiency_required
- **B3: Change Resistance** -- Uses: human_system readiness, trust, transformation_fatigue
- **B4: Seniority Offset** -- Uses: management_level (determines productive hours), headcount reduction ratio

**Reinforcing (amplify change)**:
- **R1: Trust-Adoption** -- Uses: human_system trust_level, adoption level, success probability
- **R2: Proficiency** -- Uses: human_system ai_proficiency, learning_velocity_months
- **R3: Savings** -- Uses: avg_salary, headcount, cumulative financial savings
- **R4: Political Capital** -- Uses: human_system political_capital, adoption level, disruption level

### 4.2 Loop Dominance Over Time

The data determines WHICH loops dominate at each phase:

| Phase | Months | Dominant Loops | Key Data Drivers |
|-------|--------|----------------|------------------|
| Early | 0-6 | B3 (resistance), B2 (skill valley) | change_readiness, skill gap, trust_level |
| Mid | 6-18 | R1 (trust), R2 (proficiency) | ai_proficiency, trust_level, learning_velocity |
| Late | 18-36 | B1 (absorption), B4 (seniority) | headcount, management_level, absorption_factor |

### 4.3 Leverage Points in the Data

Ranked by system impact (per Meadows' hierarchy):

1. **Task category** (rules of the system) -- Changing a task from "negligibility" to "directive" changes its automation potential from 5% to 90%. The highest-leverage data point.
2. **compliance_mandated_human** (constraints) -- Overrides L1 to max 5%. A boolean that blocks entire savings chains.
3. **human_system parameters** (feedback loop gains) -- Seeds 8 dynamic loops. Small changes in initial trust (35 vs 65) produce dramatically different 36-month outcomes.
4. **current_adoption_pct** (stock level) -- Directly determines L3 and the adoption gap. Going from 15% to 30% doubles the realized automation.
5. **headcount** (stock level) -- Linear multiplier on everything. 120 people vs 12 people means 10x the financial impact.
6. **effort_hours_month** (flow rate) -- The denominator in all capacity calculations. Under/over-estimating task effort directly scales freed hours.

---

## 5. Improvement Recommendations

### 5.1 Data Validation (Critical -- Zero Cost, High Impact)

**Problem**: The loader (`loader.py`) performs zero validation. Invalid data silently produces wrong results.

**Recommendations**:

1. **Referential integrity checks**:
   - Every `workload.role_id` must exist in `roles.csv`
   - Every `task.workload_id` must exist in `workloads.csv`
   - Every `skill.workload_id` must exist in `workloads.csv`
   - Every `task.automatable_by_tool` (when not null) must match a `tool.tool_name`

2. **Constraint validation**:
   - Workload `time_pct` values for each role must sum to 100 (+/- 1%)
   - Workload category percentages must sum to 100 (+/- 1%)
   - All percentage fields must be 0-100
   - headcount > 0, avg_salary > 0, effort_hours_month > 0
   - `skill_type` must be in {current, sunrise, sunset}
   - `category` must be in {directive, feedback_loop, task_iteration, learning, validation, negligibility}
   - `management_level` must be in the known set (IC, Senior IC, Manager, Director, VP)

3. **Consistency checks**:
   - `is_sunrise` should be True iff `skill_type == "sunrise"` (detect drift)
   - Task category distribution within a workload should roughly match the workload's category percentages
   - Every function in `roles.csv` should have a corresponding row in `human_system.csv`

### 5.2 Schema Evolution (Medium Effort, High Impact)

**Problem**: The flat CSV format makes it hard to represent complex relationships and evolve the schema.

**Recommendations**:

1. **Add a schema version header** to each CSV or a separate `schema_version.json`:
   ```json
   {"version": "2.0", "generated_at": "2026-03-05", "company": "InsureCo"}
   ```

2. **Normalize the redundancy**:
   - Remove `is_sunrise`/`is_sunset` columns from skills.csv (derivable from `skill_type`)
   - Consider removing role-level `automation_score`/`augmentation_score` or using them as validation checks against task-computed values

3. **Add missing dimensions** (see Section 5.4)

### 5.3 Multi-Company / Multi-Dataset Support

**Problem**: Data directory path is hardcoded. Single company at a time.

**Recommendations**:

1. **Directory-per-company structure**:
   ```
   data/
     insureco/
       roles.csv, tasks.csv, ...
       metadata.json  (company name, industry, date)
     techcorp/
       roles.csv, tasks.csv, ...
       metadata.json
   ```

2. **Company metadata file** (`metadata.json`):
   ```json
   {
     "company_id": "insureco",
     "company_name": "InsureCo",
     "industry": "Insurance",
     "data_date": "2026-03-01",
     "currency": "USD",
     "schema_version": "2.0"
   }
   ```

3. **Modify `load_organization()`** to accept company_id and resolve the data directory.

### 5.4 Missing Data Dimensions (High Effort, High Impact)

The current data model is missing several dimensions that would significantly improve simulation fidelity:

#### 5.4.1 Role-Level Additions

| Missing Field | Why It Matters |
|--------------|----------------|
| `attrition_rate_annual` | Natural attrition varies by role (tech = 15-20%, claims = 8-10%). Currently uses flat 8% for all. |
| `hiring_difficulty` | Hard-to-fill roles should have different replacement assumptions |
| `remote_pct` | Remote workers may have different AI adoption patterns |
| `tenure_avg_years` | Longer tenure correlates with higher change resistance |
| `contractor_pct` | Contractors have different cost structures and flexibility |

#### 5.4.2 Task-Level Additions

| Missing Field | Why It Matters |
|--------------|----------------|
| `quality_sensitivity` | High-quality tasks need more human oversight even when automated |
| `interdependency_score` | Tasks that depend on other tasks can't be automated in isolation |
| `variability` | Highly variable tasks are harder to automate than routine ones |
| `data_availability` | AI tools need data; tasks with poor data access can't be automated |
| `customer_facing` | Customer-facing tasks have different risk profiles for automation |

#### 5.4.3 Tool-Level Additions

| Missing Field | Why It Matters |
|--------------|----------------|
| `implementation_months` | Different tools have different deployment timelines |
| `integration_complexity` | Complex integrations reduce effective adoption |
| `effectiveness_rating` | Not all tools are equally good at their category |
| `version` | Track tool capability evolution over time |
| `training_hours_required` | Different tools need different training investments |

#### 5.4.4 Human System Additions

| Missing Field | Why It Matters |
|--------------|----------------|
| `role_level_readiness` | A Director and IC in the same function have very different readiness |
| `union_presence` | Unionized workforces have fundamentally different change dynamics |
| `recent_change_history` | Organizations with recent M&A or restructuring have higher fatigue |
| `leadership_quality_score` | Weak middle management blocks adoption regardless of executive mandate |
| `cultural_innovation_index` | Some cultures embrace AI faster than others |

### 5.5 Data Ingestion Pipeline Improvements

#### 5.5.1 From Static CSV to Dynamic Ingestion

**Current state**: 7 CSV files loaded once at startup.

**Recommended architecture**:

```
Data Sources                    Ingestion Layer              Application
-----------                    ---------------              -----------
HRIS (Workday/SAP)    --->   |                  |
Ticketing (ServiceNow) --->  | ETL Pipeline     | ---> OrganizationData
Financial Systems     --->   | (validate,        |      (in-memory)
Skill Assessments     --->   |  transform,       |
Tool Usage Analytics  --->   |  reconcile)       |
                             |__________________|
                                     |
                                     v
                              Versioned Data Store
                              (CSV / Parquet / DB)
```

#### 5.5.2 Automated Data Quality Pipeline

```python
# Proposed validation pipeline
class DataValidator:
    def validate_roles(self, roles: Dict[str, Role]) -> List[ValidationError]:
        errors = []
        for role in roles.values():
            if role.headcount <= 0:
                errors.append(f"Role {role.role_id}: headcount must be > 0")
            if role.avg_salary <= 0:
                errors.append(f"Role {role.role_id}: salary must be > 0")
            if role.management_level not in VALID_LEVELS:
                errors.append(f"Role {role.role_id}: unknown level {role.management_level}")
        return errors

    def validate_referential_integrity(self, org: OrganizationData) -> List[ValidationError]:
        errors = []
        for wl in org.workloads.values():
            if wl.role_id not in org.roles:
                errors.append(f"Workload {wl.workload_id}: references non-existent role {wl.role_id}")
        for task in org.tasks.values():
            if task.workload_id not in org.workloads:
                errors.append(f"Task {task.task_id}: references non-existent workload {task.workload_id}")
            if task.automatable_by_tool:
                tool_names = {t.tool_name for t in org.tools.values()}
                if task.automatable_by_tool not in tool_names:
                    errors.append(f"Task {task.task_id}: references unknown tool {task.automatable_by_tool}")
        return errors
```

#### 5.5.3 Incremental Update Support

Instead of loading everything from scratch:

```python
def update_roles(org: OrganizationData, changes: List[RoleChange]) -> OrganizationData:
    """Apply incremental role changes without full reload."""
    for change in changes:
        if change.type == "headcount_update":
            org.roles[change.role_id].headcount = change.new_value
        elif change.type == "salary_update":
            org.roles[change.role_id].avg_salary = change.new_value
    org.build_indexes()  # Rebuild indexes after changes
    return org
```

#### 5.5.4 Data Lineage & Audit Trail

Track where each data point came from and when it was last updated:

```json
{
  "role_id": "CL-001",
  "field": "headcount",
  "value": 120,
  "source": "workday_extract_2026-03-01",
  "updated_at": "2026-03-01T00:00:00Z",
  "updated_by": "etl_pipeline",
  "confidence": 0.95
}
```

### 5.6 Format & Serialization Improvements

| Current | Recommended | Why |
|---------|------------|-----|
| CSV only | CSV + Parquet + JSON Schema | Parquet for large datasets, JSON Schema for validation |
| No schema definition | JSON Schema or Pydantic models | Machine-readable validation rules |
| No compression | gzip for archived datasets | Storage efficiency for versioned data |
| No partitioning | Partition by function/date | Enable incremental processing |

### 5.7 Testing Data Ingestion

```python
# Proposed test structure
class TestDataIngestion:
    def test_all_csv_files_exist(self, data_dir):
        """Verify all required files are present."""
        required = ["roles.csv", "workloads.csv", "tasks.csv", "skills.csv",
                     "tech_stack.csv", "human_system.csv", "simulation_params.csv"]
        for f in required:
            assert (data_dir / f).exists(), f"Missing required file: {f}"

    def test_referential_integrity(self, org):
        """All foreign keys resolve."""
        for wl in org.workloads.values():
            assert wl.role_id in org.roles

    def test_workload_time_sums_to_100(self, org):
        """Per-role workload time_pct sums to ~100."""
        for role_id, wl_ids in org.workloads_by_role.items():
            total = sum(org.workloads[wid].time_pct for wid in wl_ids)
            assert 99 <= total <= 101, f"Role {role_id}: workloads sum to {total}%"

    def test_category_pcts_sum_to_100(self, org):
        """Per-workload category percentages sum to ~100."""
        for wl in org.workloads.values():
            total = (wl.directive_pct + wl.feedback_loop_pct + wl.task_iteration_pct +
                     wl.learning_pct + wl.validation_pct + wl.negligibility_pct)
            assert 99 <= total <= 101, f"Workload {wl.workload_id}: categories sum to {total}%"

    def test_no_orphan_tools(self, org):
        """Every tool referenced in tasks exists in tech_stack."""
        tool_names = {t.tool_name for t in org.tools.values()}
        for task in org.tasks.values():
            if task.automatable_by_tool:
                assert task.automatable_by_tool in tool_names

    def test_human_system_coverage(self, org):
        """Every function in roles has human system data."""
        for func in org.functions:
            assert func in org.human_system, f"No human_system data for function: {func}"
```

---

## 6. Priority Matrix

| Priority | Improvement | Effort | Impact | Risk of NOT Doing |
|----------|------------|--------|--------|-------------------|
| P0 | Data validation in loader | Low | High | Silent wrong results |
| P0 | Referential integrity checks | Low | High | Crashes on bad data |
| P1 | Multi-company directory support | Medium | High | Single-tenant limitation |
| P1 | Schema version tracking | Low | Medium | Breaking changes undetected |
| P1 | Validation test suite | Medium | High | Regression risk |
| P2 | Role-level human system params | Medium | High | Inaccurate per-role adoption |
| P2 | Task interdependency modeling | High | High | Overestimates automatable work |
| P2 | Tool effectiveness ratings | Low | Medium | All tools treated as equal |
| P3 | Real-time data connectors | High | High | Stale data |
| P3 | Incremental update pipeline | Medium | Medium | Full reload on any change |
| P3 | Data lineage tracking | Medium | Medium | No audit trail |

---

## 7. Summary

The current data model is **architecturally sound** -- it correctly maps the stocks-and-flows system thinking model into a computational pipeline. The 7 CSV files cover the essential entities, and the loader + index system enables efficient traversal.

The three biggest improvement areas are:

1. **Data validation** -- The loader trusts all input blindly. Adding validation guards catches errors before they propagate through 583 tasks x 36 months x 8 feedback loops.

2. **Granularity gaps** -- Human system parameters at function-level (4 rows) lose the variation between an IC and a Director. Role-level or at least management-level human system parameters would dramatically improve fidelity.

3. **Multi-tenancy** -- The single hardcoded data directory prevents the system from serving multiple organizations. Directory-per-company with metadata is a straightforward fix.

The data ingestion system works well for the prototype stage. Scaling it requires adding the validation, versioning, and multi-tenant layers described above.
