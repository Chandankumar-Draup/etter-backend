# Data Layer — Deep Dive

## The Bathtub Before the Ocean

*"A stock is the memory of the history of changing flows within the system."*
*— Donella Meadows, Thinking in Systems*

Before simulating workforce transformation, we must define what the organization **is** at rest. The data layer answers this: it captures the current state of seven organizational stocks as flat CSV files, loads them into typed Python dataclasses, and builds the index structures that let every other layer traverse the organization fractally — from a single task up to the entire enterprise.

This document covers the complete data architecture: what gets stored, how it gets loaded, and how the three-layer gap analysis transforms raw organizational data into actionable insight.

---

## 1. First Principles: Why This Data Shape?

### The Problem

Enterprise workforce data lives in HRIS systems, spreadsheets, and org charts — none of which capture the relationship between **what people do** (tasks), **what tools exist** (tech stack), and **how ready people are** (human system). Without these three dimensions connected, you cannot answer the question: "Given our people, our tools, and our culture, what will actually happen if we deploy AI?"

### The Design Decision

**Fractal organization.** The same pattern repeats at every level:

```
Organization
  └── Function (e.g., Claims, Technology, Finance, People)
       └── Sub-Function (e.g., Claims Processing, Claims Review)
            └── JFG (Job Function Group)
                 └── Role (e.g., Claims Processor, Senior Claims Analyst)
                      └── Workload (e.g., "Initial Claim Intake", 35% of time)
                           └── Task (e.g., "Extract data from claim forms", 12 hrs/month)
```

A cascade function that works at the task level works at every level — you just aggregate upward. No special cases, no branching logic, no "but functions are different from roles." This is the fractal simplicity principle.

### Second-Order Effect: Why CSV?

CSV files are the I/O boundary. The simulation engine never touches files — it works with typed dataclasses in memory. This means:
- The model can be validated with synthetic data (no database required)
- Real data can replace synthetic data without changing any engine code
- Every value is human-readable and debuggable (no binary formats, no ORM magic)

---

## 2. The Seven Stocks

The data layer defines seven organizational stocks as Python dataclasses in `models/organization.py`. Each stock captures one dimension of organizational state.

### Stock 1: Task Classification (`Task`)

The atomic unit of work. Every task belongs to one workload, which belongs to one role.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique identifier (e.g., `T-CLM-001`) |
| `workload_id` | `str` | Parent workload reference |
| `task_name` | `str` | Human-readable name |
| `category` | `str` | One of six Etter categories (see below) |
| `effort_hours_month` | `float` | Hours per person per month |
| `automatable_by_tool` | `Optional[str]` | Tool name that can automate this task, or `None` |
| `compliance_mandated_human` | `bool` | Regulatory floor — cannot be automated |
| `l1_etter_potential` | `float` | Theoretical automation % (computed) |
| `l2_achievable` | `float` | Achievable % given deployed tools (computed) |
| `l3_realized` | `float` | Currently automated % (computed) |

**The Six Etter Categories:**

| Category | Automation Ceiling | Nature |
|----------|-------------------|--------|
| `directive` | 90% | Rules-based, deterministic — fully automatable |
| `feedback_loop` | 85% | Refinement based on outcomes — highly automatable |
| `task_iteration` | 50% | Continuous human adjustment — partially automatable |
| `learning` | 40% | Knowledge acquisition — AI-assisted |
| `validation` | 45% | QA/compliance — AI-assisted with human oversight |
| `negligibility` | 5% | Creative, strategic, relationship — fundamentally human |

**Computed Properties:**

```
adoption_gap    = max(0, L2 - L3)    → "free money" (tool deployed but underused)
capability_gap  = max(0, L1 - L2)    → investment needed (new tools required)
total_gap       = max(0, L1 - L3)    → full distance from ceiling to floor
freed_hours_at_l2 = effort × (adoption_gap / 100)
freed_hours_at_l1 = effort × (total_gap / 100)
```

### Stock 2: Workforce Capacity (`Role`)

A job role with headcount and Etter automation/augmentation scores.

| Field | Type | Description |
|-------|------|-------------|
| `role_id` | `str` | Unique identifier (e.g., `R-CLM-01`) |
| `role_name` | `str` | Human-readable name |
| `function` | `str` | Organizational function |
| `sub_function` | `str` | Sub-category |
| `jfg` | `str` | Job function group code |
| `job_family` | `str` | Job family classification |
| `management_level` | `str` | IC, Senior IC, Manager, Director, VP |
| `headcount` | `int` | Number of people in role |
| `avg_salary` | `float` | Average salary per person |
| `automation_score` | `float` | Etter L1 automation potential % |
| `augmentation_score` | `float` | Etter L1 augmentation potential % |
| `quantification_score` | `float` | Quantification potential % |

**Computed Properties:**

```
total_hours_month  = headcount × 160     (160 hrs/month = 1 FTE)
annual_cost        = headcount × avg_salary
etter_ai_spectrum  = automation_score + augmentation_score
```

**Design Note:** 160 hours/month is the gross FTE standard. Productive hours vary by management level (IC: 128h, Manager: 96h, VP: 64h) — but that's computed in the cascade engine, not the data model. The data model captures capacity. The engine interprets it.

### Stock 3: Skill Inventory (`Skill`)

Skills mapped to workloads with sunrise/sunset classification.

| Field | Type | Description |
|-------|------|-------------|
| `skill_id` | `str` | Unique identifier |
| `workload_id` | `str` | Parent workload reference |
| `skill_name` | `str` | Human-readable name |
| `skill_type` | `str` | `current`, `sunrise`, or `sunset` |
| `proficiency_required` | `int` | Required proficiency level (0-100) |
| `is_sunrise` | `bool` | Emerging skill flag |
| `is_sunset` | `bool` | Declining skill flag |

**Why sunrise/sunset matters:** When automation reclassifies a task, the skills associated with it may become obsolete (sunset) or newly required (sunrise). The skill gap — sunrise minus sunset — is a critical input to the B2 Skill Valley feedback loop.

### Stock 4: Workload Distribution (`Workload`)

How a role's time is distributed across work categories.

| Field | Type | Description |
|-------|------|-------------|
| `workload_id` | `str` | Unique identifier |
| `role_id` | `str` | Parent role reference |
| `workload_name` | `str` | Human-readable name |
| `time_pct` | `float` | % of role's total time (0-100) |
| `directive_pct` | `float` | % on directive tasks |
| `feedback_loop_pct` | `float` | % on feedback loop tasks |
| `task_iteration_pct` | `float` | % on task iteration tasks |
| `learning_pct` | `float` | % on learning tasks |
| `validation_pct` | `float` | % on validation tasks |
| `negligibility_pct` | `float` | % on negligible/human-only tasks |

**Invariant:** The six category percentages sum to 100 within each workload.

**Computed Properties:**

```
ai_automatable_pct = directive_pct + feedback_loop_pct       → fully automatable
augmentable_pct    = task_iteration_pct + learning_pct + validation_pct  → human+AI
human_only_pct     = negligibility_pct                       → remains human
```

### Stock 5: Financial Position (`FinancialSnapshot`)

Point-in-time financial state for a scope (role, function, or org). Not loaded from CSV — computed during gap analysis.

| Field | Type | Description |
|-------|------|-------------|
| `scope_id` | `str` | Entity identifier |
| `scope_name` | `str` | Human-readable name |
| `current_annual_cost` | `float` | Current annual salary cost |
| `adoption_gap_savings_potential` | `float` | Annual savings if adoption gap closed |
| `full_gap_savings_potential` | `float` | Annual savings if all gaps closed |
| `investment_required` | `float` | Investment to close adoption gap |
| `net_opportunity` | `float` | Savings minus investment |

### Stock 6: Human System (`HumanSystem`)

The binding constraint. Function-level human readiness state.

| Field | Type | Description |
|-------|------|-------------|
| `function` | `str` | Function name |
| `ai_proficiency` | `float` | 0-100: Can the workforce work WITH AI? |
| `change_readiness` | `float` | 0-100: Willingness to adopt change |
| `trust_level` | `float` | 0-100: Trust in AI tools |
| `political_capital` | `float` | 0-100: Leadership mandate strength |
| `transformation_fatigue` | `float` | 1-5: How tired of change |
| `learning_velocity_months` | `float` | Months to meaningful proficiency gain |

**The Effective Multiplier — the most important equation in the data layer:**

```
if trust < 10 OR readiness < 10:
    return 0.05    # VETO: near-zero adoption (only early adopters)

base = (0.35 × proficiency + 0.45 × readiness + 0.20 × trust) / 100
return max(0.15, base)    # floor at 15%
```

**Weight rationale:**
- Readiness (0.45): Highest weight because willingness is the primary driver. You cannot get proficient with tools you refuse to use.
- Proficiency (0.35): Second because quality of usage determines output quality.
- Trust (0.20): Third because it acts as a ceiling on willingness rather than a direct driver.

**Floor at 0.15:** Even in worst-case organizations, approximately 15% of people are early adopters who will use available tools regardless of organizational sentiment.

### Stock 7: Technology Stack (`Tool`)

Deployed technology tools.

| Field | Type | Description |
|-------|------|-------------|
| `tool_id` | `str` | Unique identifier |
| `tool_name` | `str` | Human-readable name |
| `deployed_to_functions` | `list` | Functions this tool is deployed to (or `["All"]`) |
| `task_categories_addressed` | `list` | Task categories it can automate |
| `license_cost_per_user_month` | `float` | Monthly cost per user |
| `current_adoption_pct` | `float` | 0-100: How much of deployment is actually used |

---

## 3. The Synthetic Organization: InsureCo

The MVP uses synthetic data representing a mid-size insurance company. The data is realistic enough to exercise every element of the model while small enough to trace by hand.

| Dimension | Count |
|-----------|-------|
| Functions | 4 (Claims, Technology, Finance, People) |
| Roles | 37 |
| Workloads | 152 |
| Tasks | 581 |
| Skills | 692 |
| Tools | 5 |
| Total Headcount | ~1,370 |
| Total Annual Cost | ~$91M |

**Tech Stack:**

| Tool | Deployed To | Categories Addressed |
|------|-------------|---------------------|
| Microsoft Copilot | All functions | Document generation, email, summarization |
| ServiceNow AI | Technology, Claims | Ticket routing, KB search, incident classification |
| UiPath RPA | Claims, Finance | Data entry, form processing, reconciliation |
| Workday AI | People, Finance | Report generation, absence analysis |
| Custom Claims AI | Claims only | Claims triage, fraud scoring, doc extraction |

**Human System Initial Conditions:**

| Function | Proficiency | Readiness | Trust | Political Capital | Fatigue |
|----------|-------------|-----------|-------|-------------------|---------|
| Claims | 25 | 45 | 35 | 50 | 2.0 |
| Technology | 60 | 70 | 65 | 75 | 1.5 |
| Finance | 30 | 50 | 40 | 55 | 2.0 |
| People | 20 | 55 | 45 | 60 | 1.8 |

---

## 4. Data Loading: The I/O Boundary

`engine/loader.py` implements the I/O boundary pattern. All file access happens here. The rest of the system works with typed dataclasses in memory.

### The `OrganizationData` Container

```python
@dataclass
class OrganizationData:
    roles: Dict[str, Role]
    workloads: Dict[str, Workload]
    tasks: Dict[str, Task]
    skills: Dict[str, Skill]
    tools: Dict[str, Tool]
    human_system: Dict[str, HumanSystem]

    # Index lookups (built after loading)
    workloads_by_role: Dict[str, List[str]]
    tasks_by_workload: Dict[str, List[str]]
    skills_by_workload: Dict[str, List[str]]
    roles_by_function: Dict[str, List[str]]
    roles_by_jfg: Dict[str, List[str]]
```

### Loading Sequence

```
load_organization(data_dir) → OrganizationData

  1. Read roles.csv       → Dict[str, Role]
  2. Read workloads.csv   → Dict[str, Workload]
  3. Read tasks.csv       → Dict[str, Task]
  4. Read skills.csv      → Dict[str, Skill]
  5. Read tech_stack.csv  → Dict[str, Tool]
  6. Read human_system.csv → Dict[str, HumanSystem]
  7. Build reverse-lookup indexes
  8. Return OrganizationData
```

### Index Building

The reverse-lookup indexes enable efficient traversal in any direction:

```
role_id    → [workload_ids]     (workloads_by_role)
workload_id → [task_ids]        (tasks_by_workload)
workload_id → [skill_ids]       (skills_by_workload)
function   → [role_ids]         (roles_by_function)
jfg        → [role_ids]         (roles_by_jfg)
```

This is the fractal structure in practice. Given a function name, you can reach every task in that function by traversing: `function → roles → workloads → tasks`. Given a task, you can reach every ancestor by walking the reverse indexes.

---

## 5. Three-Layer Gap Analysis

The gap engine (`engine/gap_engine.py`) transforms raw organizational data into actionable gap analysis. This is the static snapshot — Stage 0 of the simulation pipeline.

### The Three Layers

```
L1 (Etter Ceiling)  — What COULD be automated (from task category)
L2 (Achievable)     — What CAN be automated (from deployed tech stack)
L3 (Realized)       — What IS automated (from current adoption %)
```

```
         L1 ─────────────────────────── 90% (directive task)
         │
         │  ← Capability Gap (L1 - L2): Need new tools
         │
         L2 ─────────────────── 90% (if matching tool deployed)
         │
         │  ← Adoption Gap (L2 - L3): "Free money"
         │
         L3 ────────── 27% (tool at 30% adoption)
         │
         │  ← Current automation
         │
         0% ─
```

### Classification Algorithm

For each task:

**Step 1 — L1 (Etter Ceiling):**
- Look up category in `CATEGORY_AUTOMATION_POTENTIAL` dict
- If compliance-mandated: cap at 5%

**Step 2 — L2 (Achievable):**
- Search deployed tools for one that:
  1. Is deployed to this task's function (or "All")
  2. Addresses this task's category
  3. Matches the task's `automatable_by_tool` field
- If match found: L2 = L1
- If no match: L2 = 0

**Step 3 — L3 (Realized):**
- If matching tool exists: L3 = L2 x (tool.current_adoption_pct / 100)
- If no matching tool: L3 = 0

### Aggregation Cascade

The gap analysis aggregates from task level to org level:

```
Phase 1: Classify every task          → L1, L2, L3 per task
Phase 2: Aggregate tasks → workloads  → effort-weighted averages
Phase 3: Aggregate workloads → roles  → effort-weighted + financial calculations
Phase 4: Aggregate roles → functions  → headcount-weighted + human system
Phase 5: Aggregate functions → org    → headcount-weighted totals
Phase 6: Rank opportunities           → top roles by savings
```

**Weighting principle:**
- Task → Workload: **effort-weighted** (a 40-hour task matters more than a 2-hour task)
- Workload → Role: **effort-weighted** (same principle)
- Role → Function: **headcount-weighted** (a 200-person role matters more than a 5-person role)
- Function → Org: **headcount-weighted** (same principle)

### Financial Calculations (per role)

```
hours_freed         = gap_hours_per_person × headcount
fte_equivalent      = hours_freed / 160
savings_annual      = fte_equivalent × avg_salary
redesign_candidate  = True if freed_pct > 40%
```

### Result Hierarchy

```
OrgGapResult
  ├── org totals (headcount, cost, gaps, savings)
  ├── top_roles_by_adoption_gap (top 10)
  ├── top_roles_by_total_gap (top 10)
  ├── top_roles_by_savings (top 10)
  └── functions: List[FunctionGapResult]
       ├── function totals + human system state
       └── roles: List[RoleGapResult]
            ├── role totals + redesign flag
            └── workloads: List[WorkloadGapResult]
                 ├── workload totals
                 └── tasks: List[TaskGapResult]
                      └── task-level L1/L2/L3 + gaps
```

---

## 6. Data Integrity Invariants

Stage 0 runs 9 acceptance tests to validate the gap analysis:

| Test | Invariant |
|------|-----------|
| T1 | All adoption gaps >= 0 (L2 >= L3 always) |
| T2 | All capability gaps >= 0 (L1 >= L2 always) |
| T3 | Layer ordering: L1 >= L2 >= L3 |
| T4 | Org aggregation consistent with function sums |
| T5 | Function aggregation consistent with role sums |
| T6 | Top opportunities have positive values |
| T7 | Compliance floor active (compliance tasks capped at 5%) |
| T8 | Freed hours <= available hours (can't free more than exists) |
| T9 | Adoption gap is material (non-trivially zero) |

These invariants are structural — if any fails, the data model has a bug.

---

## 7. Data Flow Summary

```
CSV Files (6 types)
    │
    ▼
load_organization() ──► OrganizationData
    │                     (roles, workloads, tasks, skills, tools, human_system)
    │                     (+ reverse-lookup indexes)
    │
    ▼
classify_task() for each task ──► L1, L2, L3 populated on Task objects
    │
    ▼
compute_snapshot(org) ──► OrgGapResult
    │                      (fractal aggregation: task → workload → role → function → org)
    │
    ├──► Stage 0 output (static gap analysis)
    ├──► Stage 1 input (cascade engine uses classified tasks)
    ├──► Stage 3 input (simulator uses org data + human system)
    └──► API responses (serialized to JSON for frontend)
```

---

## 8. Systems Thinking: Stocks and Flows in the Data Layer

The data layer embodies Meadows' principle that **"a stock is the memory of the history of changing flows."**

At rest (Stage 0), the seven stocks are snapshots — frozen in time. The gap analysis reveals the *potential* for change: adoption gaps are latent flows waiting to be activated, capability gaps are structural barriers to flow.

The data layer does not contain flows. It contains the initial conditions from which flows will emerge. This is the bathtub at rest: water level measured, faucet capacity known, drain rate estimated. The simulation engine (documented separately) is what turns the faucets on.

The separation is deliberate. Data is fact. Simulation is hypothesis. By keeping them apart, we can change the hypothesis (different scenarios, different parameters) without changing the facts. And we can update the facts (real client data) without changing the hypothesis.

*The data layer is the ground truth. Everything else is a question about what happens next.*
