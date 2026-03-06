# Backend API — Deep Dive

## The Boundary Between Engine and World

*"Information holds systems together and plays a great role in determining how they operate."*
*— Donella Meadows, Thinking in Systems*

The backend API is the information boundary of the Workforce Twin system. It translates between two fundamentally different representations: the engine's typed Python dataclasses (optimized for computation) and the frontend's JSON payloads (optimized for rendering). It also orchestrates multi-step operations (cascade + simulate + compare) that the frontend triggers but doesn't need to understand.

This document covers the FastAPI application, all route modules, the serialization layer, and the stage orchestration system.

---

## 1. First Principles: Why This API Shape?

### The Problem

The simulation engine produces deeply nested, heavily cross-referenced Python objects. A single `FBSimulationResult` contains 37 monthly snapshots, each with 30+ metrics, nested role-level detail, and trace data. The frontend needs the same data, but as flat JSON that can drive charts, tables, and cards.

### The Design Decision

**Strict separation of concerns:**
- **Engine** computes. It knows nothing about HTTP, JSON, or browsers.
- **API** translates and orchestrates. It doesn't compute anything — it calls engine functions and serializes results.
- **Frontend** renders. It doesn't know about Python dataclasses or CSV files.

This means you can change the engine's internal representation without touching the API (as long as serializers are updated). You can add new frontend pages without touching the engine. And you can test the engine without starting a server.

### Second-Order Effect

The API also acts as a **caching layer**. Organization data and the static gap snapshot are loaded once at startup and cached for the lifetime of the server process. This means the first API call takes seconds (loading CSVs, classifying tasks), but subsequent calls return instantly for read operations.

---

## 2. Application Architecture

### FastAPI Application (`api/app.py`)

```
FastAPI App
  ├── Title: "Workforce Twin by Etter"
  ├── Version: 1.0.0
  ├── CORS: All origins allowed (development mode)
  │
  ├── Lifespan: async context manager
  │   ├── Startup: load_organization() + compute_snapshot()
  │   └── Prints readiness message with entity counts
  │
  ├── Health Check: GET /api/health
  │   └── Returns { status, roles, functions[] }
  │
  ├── Static Files: /ui/dist (production build)
  │
  └── Route Modules (all at /api prefix):
      ├── organization.router  → /api/org*
      ├── snapshot.router      → /api/snapshot*
      ├── cascade.router       → /api/cascade
      ├── simulate.router      → /api/simulate*
      ├── scenarios.router     → /api/scenarios*
      └── compare.router       → /api/compare
```

### Global State

Two module-level caches:
- `_org: OrganizationData` — Complete organization data (loaded once)
- `_snapshot: OrgGapResult` — Pre-computed gap analysis (computed once)

Both are lazily initialized on first access and cached for the process lifetime. Helper functions `get_org()` and `get_snapshot()` provide access with lazy initialization.

---

## 3. Route Modules

### 3.1 Organization Routes (`api/routes/organization.py`)

Read-only endpoints for inspecting the current organization state.

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/org` | GET | Full serialized organization data |
| `/api/org/hierarchy` | GET | Tree structure (function -> sub_function -> jfg -> role) |
| `/api/org/functions` | GET | Function list with metadata (HC, readiness, proficiency) |
| `/api/org/roles/{role_id}` | GET | Role detail with workloads, tasks, skills |
| `/api/org/tools` | GET | Tech stack (tools, deployment scope, adoption %) |

**Key Design:** The hierarchy endpoint builds a tree structure on the fly by traversing the organization's role data. Each node contains aggregated metrics (headcount, annual cost, automation scores). This enables the Explorer page's fractal drill-down without pre-computing every possible aggregation.

**Role Detail Endpoint:** Returns the complete drill-down for a single role:
```json
{
  "role_id": "R-CLM-01",
  "role_name": "Claims Processor",
  "function": "Claims",
  "workloads": [
    {
      "workload_id": "W-CLM-01-1",
      "workload_name": "Initial Claim Intake",
      "time_pct": 35.0,
      "category_distribution": {
        "directive": 45.0,
        "feedback_loop": 20.0,
        "task_iteration": 15.0,
        "learning": 10.0,
        "validation": 5.0,
        "negligibility": 5.0
      },
      "tasks": [ ... ],
      "skills": [ ... ]
    }
  ]
}
```

### 3.2 Snapshot Routes (`api/routes/snapshot.py`)

Gap analysis endpoints at different aggregation levels.

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/snapshot` | GET | Full org-level gap analysis (L1/L2/L3, all functions) |
| `/api/snapshot/function/{name}` | GET | Function-level gap analysis |
| `/api/snapshot/role/{role_id}` | GET | Role-level gap analysis |
| `/api/snapshot/opportunities` | GET | Top automation opportunities by savings |

**Opportunities Endpoint Response:**
```json
{
  "by_adoption_gap": [ ... top 10 roles by adoption gap savings ... ],
  "by_total_gap":    [ ... top 10 roles by total gap ... ],
  "by_savings":      [ ... top 10 roles by full savings potential ... ]
}
```

Each opportunity entry contains: role_id, role_name, function, gap_hours, savings_annual, headcount, fte_equivalent.

### 3.3 Cascade Route (`api/routes/cascade.py`)

Single-point-in-time 9-step cascade execution.

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/cascade` | POST | `CascadeRequest` | Serialized 9-step cascade result |

**Request Model:**
```python
class CascadeRequest(BaseModel):
    stimulus_name: str = "Technology Injection"
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []          # empty = all functions
    target_roles: List[str] = []              # empty = all roles in scope
    policy: str = "moderate_reduction"
    absorption_factor: float = 0.35
    alpha: float = 1.0
    training_cost_per_person: float = 2000
```

**Logic:** Constructs a `Stimulus` from request parameters, calls `run_cascade(stimulus, org)`, serializes result with `serialize_cascade()`.

### 3.4 Simulate Routes (`api/routes/simulate.py`)

Time-series simulation with feedback loops. The most complex route module.

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/simulate` | POST | `SimulationRequest` | Serialized simulation result |
| `/api/simulate/preset/{id}` | POST | `preset_id` + `trace` flag | Serialized preset simulation |
| `/api/simulate/presets` | GET | — | Array of preset definitions |

**SimulationRequest Model (key fields):**
```python
class SimulationRequest(BaseModel):
    # Stimulus
    stimulus_name: str = "Technology Injection"
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []
    policy: str = "moderate_reduction"
    absorption_factor: float = 0.35

    # Rate Parameters
    adoption: Optional[RateParamsInput]      # alpha, k, midpoint, delay
    expansion: Optional[RateParamsInput]
    extension: Optional[RateParamsInput]
    time_horizon_months: int = 36
    hc_review_frequency: int = 3

    # Feedback Overrides
    feedback: Optional[FeedbackOverrides]    # B1-B4, R1-R4 parameters

    # Inverse Solve Targets
    target_hc_reduction_pct: Optional[float]
    target_budget_amount: Optional[float]
    target_automation_pct: Optional[float]

    trace: bool = False
```

**FeedbackOverrides:** Optional overrides for any of the 8 feedback loop parameters. When provided, these override the defaults in `FeedbackParams`. This allows the frontend to expose "advanced tuning" sliders for each feedback loop.

**Inverse Solve Flow:** When any `target_*` field is set, the route runs the inverse solver instead of the forward simulator:
1. Binary search on adoption alpha to find the value that achieves the target
2. Returns the solved alpha and the simulation result
3. If trace is enabled, re-runs with tracing for explainability

**Response includes an `inverse_solve` section:**
```json
{
  "inverse_solve": {
    "solved": true,
    "solved_alpha": 0.72,
    "target_value": 20.0,
    "achieved_value": 20.3,
    "error_pct": 1.5,
    "iterations": 12,
    "message": "Solved within tolerance"
  },
  "summary": { ... },
  "timeline": [ ... ]
}
```

**Preset Descriptions:**
| Preset | Description |
|--------|-------------|
| P1 | Conservative approach: adoption-gap only, natural attrition, low risk |
| P2 | Balanced transformation with phased adoption and moderate workforce adjustment |
| P3 | Aggressive push: all three phases, active HC reduction, high risk |
| P4 | No layoffs: invest in capability, redirect freed capacity to new work |
| P5 | Maximum speed: workflow automation enabled, rapid redeployment |

### 3.5 Scenario Routes (`api/routes/scenarios.py`)

Catalog-based scenario management.

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/scenarios/catalog` | GET | — | Full scenario catalog |
| `/api/scenarios/run` | POST | `scenario_ids`, `families` | Batch execution results |
| `/api/scenarios/run-single/{id}` | POST | `scenario_id`, `trace` | Single scenario result |

**Catalog Source:** Reads from `scenario_catalog/simulation_scenarios_extended.csv` — a curated catalog of 40+ scenarios spanning 12 families.

**Batch Execution Response:**
```json
{
  "total": 40,
  "passed": 25,
  "failed": 15,
  "results": [
    {
      "scenario_id": "SC-1.1",
      "scenario_name": "Copilot to Claims (Balanced)",
      "family": "technology_injection",
      "status": "pass",
      "hc_reduced": 66,
      "final_hc": 474,
      "net_savings": 4657000,
      "total_investment": 1820000,
      "total_savings": 6477000,
      "payback_month": 18,
      "final_proficiency": 44.9,
      "final_trust": 46.4
    }
  ]
}
```

### 3.6 Compare Route (`api/routes/compare.py`)

Multi-scenario side-by-side comparison.

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/compare` | POST | `CompareRequest` | Comparison matrix + individual results |

**Request Model:**
```python
class CompareRequest(BaseModel):
    scenarios: List[CompareScenario]
    trace: bool = False

class CompareScenario(BaseModel):
    name: Optional[str] = None
    preset_id: Optional[str] = None       # P1-P5 shortcut
    # ... or custom parameters
    tools: List[str] = ["Microsoft Copilot"]
    target_functions: List[str] = []
    policy: str = "moderate_reduction"
    alpha_adopt: float = 0.6
    # ...
```

**Comparison Matrix Response:**
```json
{
  "scenarios": [
    { "name": "Cautious", "result": { ... } },
    { "name": "Aggressive", "result": { ... } }
  ],
  "comparison_matrix": {
    "metric_names": [
      "total_hc_reduced", "net_savings", "total_investment",
      "payback_month", "final_proficiency", "final_trust",
      "productivity_valley_value", "avg_adoption_dampening"
    ],
    "scenario_names": ["Cautious", "Aggressive"],
    "values": {
      "total_hc_reduced": [34, 80],
      "net_savings": [1200000, 6800000],
      ...
    }
  }
}
```

---

## 4. The Serialization Layer

`api/serializers.py` (598 lines) translates every engine dataclass into JSON-safe dicts.

### Design Principles

1. **Explicit, not automatic.** Each dataclass has its own serializer function. No magic `to_dict()` methods. This means the API contract is explicit and stable — internal engine changes don't leak to the frontend.

2. **Consistent rounding.** The `_r(value, decimals=2)` utility rounds all floats and handles edge cases (inf, nan → 0).

3. **Recursive nesting.** Complex objects serialize recursively: `serialize_org_gap()` calls `serialize_function_gap()` which calls `serialize_role_gap()` which calls `serialize_workload_gap()`.

### Serializer Inventory

| Serializer | Input | Used By |
|------------|-------|---------|
| `serialize_role(Role)` | Role dataclass | org endpoint |
| `serialize_workload(Workload)` | Workload dataclass | org endpoint |
| `serialize_task(Task)` | Task dataclass | org endpoint |
| `serialize_skill(Skill)` | Skill dataclass | org endpoint |
| `serialize_tool(Tool)` | Tool dataclass | org endpoint |
| `serialize_human_system(HumanSystem)` | HumanSystem dataclass | org endpoint |
| `serialize_org(OrganizationData)` | Full org data | org endpoint |
| `serialize_org_hierarchy(OrganizationData)` | Org → tree | hierarchy endpoint |
| `serialize_task_gap(TaskGapResult)` | Task gap result | snapshot endpoints |
| `serialize_role_gap(RoleGapResult)` | Role gap result | snapshot endpoints |
| `serialize_function_gap(FunctionGapResult)` | Function gap result | snapshot endpoints |
| `serialize_org_gap(OrgGapResult)` | Full gap result | snapshot endpoints |
| `serialize_stimulus(Stimulus)` | Cascade stimulus | cascade, simulate |
| `serialize_cascade(CascadeResult)` | Full 9-step result | cascade, simulate |
| `serialize_fb_snapshot(FBMonthlySnapshot)` | Monthly data point | simulate endpoint |
| `serialize_fb_result(FBSimulationResult)` | Full simulation | simulate, compare |
| `serialize_rate_params(RateParams)` | S-curve params | presets endpoint |
| `serialize_sim_params(SimulationParams)` | Simulation params | presets endpoint |

### Example: Monthly Snapshot Serialization

A single `FBMonthlySnapshot` serializes to ~30 fields:
```json
{
  "month": 12,
  "raw_adoption_pct": 74.4,
  "effective_adoption_pct": 28.3,
  "adoption_dampening": 0.38,
  "gross_freed_hours": 4200.5,
  "redistributed_hours": 1470.2,
  "net_freed_hours": 2730.3,
  "cumulative_net_freed": 18500.0,
  "dynamic_absorption_rate": 0.35,
  "headcount": 502,
  "hc_reduced_this_month": 6,
  "cumulative_hc_reduced": 38,
  "hc_pct_of_original": 93.0,
  "skill_gap_opened": 35,
  "skill_gap_closed": 22,
  "current_skill_gap": 13,
  "cumulative_investment": 1200000,
  "cumulative_savings": 750000,
  "net_position": -450000,
  "monthly_savings_rate": 125000,
  "productivity_index": 97.5,
  "proficiency": 29.2,
  "readiness": 46.9,
  "trust": 37.2,
  "political_capital": 63.5,
  "transformation_fatigue": 12.3,
  "human_multiplier": 0.38,
  "trust_multiplier": 0.87,
  "capital_multiplier": 1.0,
  "b2_skill_drag": 0.85,
  "b4_seniority_mult": 0.97,
  "ai_error_occurred": false,
  "role_headcounts": { "R-CLM-01": 85, "R-CLM-02": 42, ... }
}
```

---

## 5. The Stage Orchestration System

The `stages/` directory contains four orchestration modules that validate the engine at progressive complexity levels.

### Stage 0: Static Snapshot (`stages/stage_0_snapshot.py`)

**Purpose:** Prove the data model and gap analysis work.

**Orchestration Flow:**
```
main(data_dir)
  → load_organization(data_dir)
  → compute_snapshot(org)      → OrgGapResult
  → validate_snapshot(org, result)   → 9 acceptance tests
  → print_org_summary(result)
  → print_function_detail(result)
  → print_role_detail(result)
  → print_opportunities(result)
  → export_results(result, output_dir)
```

**Exports:** `stage0_role_gaps.csv`, `stage0_function_gaps.csv`, `stage0_org_summary.json`

### Stage 1: Single-Step Cascade (`stages/stage_1_cascade.py`)

**Purpose:** Prove the 9-step cascade propagation works.

**Default Stimulus:**
- Tool: Microsoft Copilot
- Target: Claims function
- Policy: moderate_reduction
- Absorption: 0.35
- Alpha: 1.0 (instant adoption)

**Orchestration Flow:**
```
main(data_dir)
  → load_organization(data_dir)
  → create Stimulus
  → run_cascade(stimulus, org)   → CascadeResult
  → validate_cascade(result)     → 11 acceptance tests
  → print_cascade_results(result)
  → print_decision_trace(result)    (dampening chain insights)
  → export_cascade_results(result, output_dir)
```

**Exports:** `stage1_role_cascade.csv`, `stage1_task_reclassifications.csv`, `stage1_cascade_summary.json`

### Stage 3: Feedback Integration (`stages/stage_3_feedback.py`)

**Purpose:** Prove all 8 feedback loops work and produce realistic dynamics.

**Five Simulation Variants:**

| Variant | Parameters | Purpose |
|---------|-----------|---------|
| A: Baseline | readiness=45, trust=35 | Reference mode |
| B: AI Error | AI error injected at month 7 | Trust destruction test |
| C: High Readiness | readiness=80 | Upper bound |
| D: Low Readiness | readiness=25 | Lower bound |
| OL: Open-Loop | No feedback | Theoretical ceiling |

**Validation Tests (12):**
1. Higher readiness produces faster adoption
2. AI error causes trust drop
3. Trust recovery is slow (asymmetry)
4. Proficiency grows with practice
5. Feedback adoption <= open-loop early
6. Feedback produces more conservative HC outcomes
7. High vs low readiness divergence > 25%
8. Transformation fatigue accumulates
9. Adoption dampening is visible
10. Seniority offset is visible
11. Dynamic absorption increases over time
12. Feedback delays payback vs open-loop

**Visualization:** ASCII sparklines for human system trajectories, adoption curves, and monthly milestone tables.

**Exports:** `stage3_feedback_timeseries.csv`, `stage3_comparison.json`

### Stage 4: Scenario Comparison (`stages/stage_4_scenarios.py`)

**Purpose:** Prove five policies produce meaningfully different outcomes.

**Risk Scoring:**
```python
def compute_risk_score(result) -> dict:
    # Components:
    #   HC concentration risk
    #   Change burden
    #   Trust volatility
    #   Skill gap severity
    #   Financial exposure
    # Returns: total (0-100), level, component breakdown
```

**Sensitivity Analysis:** Runs readiness at +-20% to measure parameter sensitivity. Confirms readiness as the #1 driver of outcome variance.

**Validation Tests (9):**
1. Risk ordering: P1 <= P3
2. Highest risk identified correctly
3. P4 no_layoffs enforced (zero HC change)
4. P5 outperforms P3 on adoption
5. Sensitivity swing is significant
6. Meaningful variation across scenarios
7. All complete 36-month horizon
8. Learning effect visible (proficiency grows)
9. P4 capability grows (proficiency improves despite no savings)

**Exports:** `stage4_scenario_overlay.csv`, `stage4_summary.json`, `stage4_sensitivity.csv`

---

## 6. Request-Response Flow

### Example: Running a Simulation

```
Frontend                    API                          Engine
   │                         │                             │
   │  POST /api/simulate     │                             │
   │  {tools, policy, ...}   │                             │
   │ ───────────────────────>│                             │
   │                         │  Construct Stimulus          │
   │                         │  Construct SimulationParams  │
   │                         │  Construct FeedbackParams    │
   │                         │                             │
   │                         │  simulate_with_feedback()   │
   │                         │ ──────────────────────────> │
   │                         │                             │ run_cascade() [baseline]
   │                         │                             │ for month in 1..36:
   │                         │                             │   compute adoption
   │                         │                             │   apply feedback loops
   │                         │                             │   update human system
   │                         │                             │   compute HC, financials
   │                         │                             │   record snapshot
   │                         │  <───────────────────────── │
   │                         │  FBSimulationResult          │
   │                         │                             │
   │                         │  serialize_fb_result()       │
   │                         │                             │
   │  <──────────────────────│                             │
   │  { summary, timeline,   │                             │
   │    cascade, trace }     │                             │
```

### Example: Inverse Solve

```
Frontend                    API                          Engine
   │                         │                             │
   │  POST /api/simulate     │                             │
   │  {target_hc_reduction:  │                             │
   │   20, ...}              │                             │
   │ ───────────────────────>│                             │
   │                         │  Detect inverse target       │
   │                         │  solve_inverse()             │
   │                         │ ──────────────────────────> │
   │                         │                             │ Binary search:
   │                         │                             │   alpha_low = 0
   │                         │                             │   alpha_high = 1.0
   │                         │                             │   loop:
   │                         │                             │     simulate(alpha_mid)
   │                         │                             │     check: HC reduced >= 20%?
   │                         │                             │     narrow range
   │                         │  <───────────────────────── │
   │                         │  solved_alpha + result       │
   │                         │                             │
   │  <──────────────────────│                             │
   │  { inverse_solve: {     │                             │
   │      solved_alpha: 0.72 │                             │
   │    },                   │                             │
   │    summary, timeline }  │                             │
```

---

## 7. Error Handling and Edge Cases

### Invalid Inputs
- Unknown preset ID → 404
- Empty tools list → cascade produces zero-scope result (valid but empty)
- Target function that doesn't exist → 404
- Invalid policy string → falls through to default behavior

### Data Consistency
- Organization data is immutable after loading (no mutation endpoints)
- Gap snapshot is recomputed if org data changes (but this never happens at runtime)
- Simulation results are computed fresh for each request (no result caching)

### Performance Characteristics
- Organization load: ~1 second (37 roles, 152 workloads, 581 tasks)
- Gap analysis: ~100ms
- Single cascade: ~50ms
- 36-month simulation: ~200-500ms
- 5-scenario comparison: ~1-2 seconds
- 40-scenario catalog run: ~10-20 seconds

---

## 8. Systems Thinking: The API as Information Flow

In Meadows' framework, information flows are the interconnections that hold systems together. The API is the primary information flow between the simulation engine and the decision-making interface (UI).

The API design reflects three information principles:

1. **Progressive disclosure.** The `/api/snapshot` endpoint returns org-level summaries. The `/api/snapshot/function/{name}` drills down. The `/api/snapshot/role/{role_id}` drills further. Each level adds detail without requiring the previous level's data to be re-fetched.

2. **Separation of fact and hypothesis.** Organization and snapshot endpoints return facts (current state). Cascade, simulate, and compare endpoints return hypotheses (what might happen). The API makes this distinction structural — you can't accidentally confuse a simulation result with real data.

3. **Feedback-complete.** The compare endpoint enables the fundamental feedback loop of decision-making: hypothesis -> simulate -> compare -> decide -> new hypothesis. Without comparison, leaders optimize for single-scenario outcomes. With comparison, they optimize for robustness across scenarios.

*The API doesn't just move data. It shapes the decision process by controlling what information flows to whom, when, and at what level of detail.*
