# Workforce Twin Modeling: Full-Stack Implementation Plan
# Version 1.0 — March 2026

*Classification: Engineering Architecture Document*
*Scope: Self-contained within `workforce_twin_modeling/` — no imports from parent `draup_world_model`*
*Architecture: React/TypeScript Frontend + FastAPI Backend + Existing Python Engine*

---

> **Implementation Thesis:** The simulation engine already works — 28 Python files producing
> rich structured output across 9-step cascades, feedback loops, time-series projections,
> and 40-scenario catalogs. The gap is not computation but **legibility**. The engine
> outputs text tables to stdout. What it needs is a visual layer that makes the system's
> behavior *discoverable* — where a decision-maker can see the cascade propagate, watch
> feedback loops dominate and recede, compare scenarios side-by-side, and drill from
> org-level summaries down to individual task reclassifications. The UI is not wrapping
> the engine; it's *completing* the system.

---

# PART I: SYSTEMS THINKING ANALYSIS

## 1. First Principles Decomposition

Before designing screens, we decompose what the UI must actually *do*, reduced to atoms.

### What is a Workforce Twin UI, reduced to first principles?

A simulation UI has exactly four irreducible capabilities:

1. **Configure** — Define what to simulate (stimulus, scope, parameters, policy)
2. **Execute** — Run the simulation and track progress
3. **Visualize** — Render results as charts, tables, and narratives
4. **Compare** — Place multiple simulation outcomes side-by-side

If any one is missing, you have a dashboard (no configure), a CLI wrapper (no visualize),
or a report generator (no compare). All four must exist.

### Irreducible Atoms

| Atom | What It Means | Exists Today? |
|------|---------------|---------------|
| A1: Data Loading | Read 7 CSVs into OrganizationData, expose via API | **No** — loader.py reads from disk, no HTTP layer |
| A2: Stimulus Configuration | Build Stimulus + SimulationParams + FeedbackParams from UI | **No** — hardcoded in rates.py (P1-P5) |
| A3: Cascade Execution | Run the 9-step cascade and return structured JSON | **Partial** — cascade.py returns dataclasses, not JSON |
| A4: Time-Series Simulation | Run feedback-enabled simulator, return monthly snapshots | **Partial** — simulator_fb.py outputs dataclasses |
| A5: Trace Explainability | Return per-month feedback decomposition for any scenario | **Yes** — trace.py captures everything, needs serialization |
| A6: Scenario Comparison | Run batch, return comparison matrix | **Partial** — scenario_executor.py prints tables |
| A7: Org Snapshot | Static gap analysis at current state | **Yes** — gap_engine.py computes full snapshot |
| A8: Visual Rendering | Charts, Sankeys, heatmaps, timelines in the browser | **No** — all output is print() statements |

**Critical Insight:** A1-A6 are backend wiring (thin FastAPI layer over existing engine).
A7 already works. A8 is the entire frontend effort. The backend is ~20% of the work,
the frontend is ~80%.

---

## 2. Donella Meadows System Model

### 2.1 Stocks (What Accumulates in the UI System)

| Stock | Description | Where It Lives |
|-------|------------|----------------|
| **Organization State** | Loaded CSV data — roles, tasks, workloads, skills, tools, human system | Backend memory (OrganizationData) |
| **Scenario Library** | All configured + executed scenarios and their results | Backend + localStorage |
| **Comparison Sets** | User-defined groupings of scenarios for side-by-side analysis | Frontend state (React) |
| **User Preferences** | Selected views, drill-down paths, chart configurations | Frontend state + localStorage |

### 2.2 Flows

**Inflows:**
- CSV upload/selection → Organization State
- UI parameter configuration → Scenario Library (new scenario)
- Simulation execution → Scenario Library (results attached)
- Preset selection (P1-P5) → Scenario configuration

**Outflows:**
- Scenario results → Chart renderings
- Comparison selections → Side-by-side visualizations
- Trace data → Explainability narratives
- Export actions → CSV/JSON downloads

### 2.3 Feedback Loops in the UI

**B1: Information Overload (Balancing)**
More data shown → harder to find insights → user engagement drops.
*Mitigation: Progressive disclosure — summary first, drill to detail.*

**R1: Discovery Flywheel (Reinforcing)**
See interesting pattern → drill deeper → find insight → compare with variant → discover more.
*Leverage: Make drill-down paths frictionless. One click from summary to detail.*

---

## 3. Boundary Definition: What's In, What's Out

### IN SCOPE (self-contained within `workforce_twin_modeling/`)

- **Backend:** FastAPI app serving the existing engine via REST API
- **Frontend:** React/TypeScript SPA with Vite build tooling
- **Data:** Reads only from `workforce_twin_modeling/data/` (7 CSVs)
- **Engine:** Uses only modules in `workforce_twin_modeling/engine/`, `models/`, `stages/`
- **Scenario Catalog:** Reads from `workforce_twin_modeling/scenario_catalog/`

### OUT OF SCOPE

- No imports from `draup_world_model/` parent package
- No Neo4j, no external databases
- No LLM/AI chat integration
- No authentication (local development tool)
- No deployment to cloud (local `npm run dev` + `uvicorn`)

---

# PART II: ARCHITECTURE

## 4. Directory Structure

```
workforce_twin_modeling/
├── api/                          # NEW: FastAPI backend
│   ├── __init__.py
│   ├── app.py                    # FastAPI app, CORS, lifespan
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── organization.py       # GET /api/org — loaded org data
│   │   ├── snapshot.py           # GET /api/snapshot — static gap analysis
│   │   ├── cascade.py            # POST /api/cascade — run 9-step cascade
│   │   ├── simulate.py           # POST /api/simulate — time-series simulation
│   │   ├── scenarios.py          # GET/POST /api/scenarios — catalog + batch
│   │   └── compare.py            # POST /api/compare — multi-scenario comparison
│   ├── schemas.py                # Pydantic models for request/response
│   └── serializers.py            # Dataclass → dict serialization helpers
│
├── ui/                           # NEW: React/TypeScript frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                  # API client
│   │   │   └── client.ts
│   │   ├── types/                # TypeScript interfaces mirroring Python dataclasses
│   │   │   ├── organization.ts
│   │   │   ├── cascade.ts
│   │   │   ├── simulation.ts
│   │   │   └── scenario.ts
│   │   ├── pages/                # Top-level views
│   │   │   ├── Dashboard.tsx
│   │   │   ├── OrgSnapshot.tsx
│   │   │   ├── CascadeExplorer.tsx
│   │   │   ├── SimulationLab.tsx
│   │   │   ├── ScenarioCatalog.tsx
│   │   │   └── CompareArena.tsx
│   │   ├── components/           # Reusable UI components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── PageShell.tsx
│   │   │   ├── charts/
│   │   │   │   ├── TimeSeriesChart.tsx
│   │   │   │   ├── StackedBarChart.tsx
│   │   │   │   ├── RadarChart.tsx
│   │   │   │   ├── SankeyDiagram.tsx
│   │   │   │   ├── HeatmapGrid.tsx
│   │   │   │   └── GaugeChart.tsx
│   │   │   ├── simulation/
│   │   │   │   ├── StimulusConfigurator.tsx
│   │   │   │   ├── PolicySelector.tsx
│   │   │   │   ├── ParameterSliders.tsx
│   │   │   │   ├── FeedbackLoopDiagram.tsx
│   │   │   │   └── TraceExplorer.tsx
│   │   │   ├── org/
│   │   │   │   ├── OrgTree.tsx
│   │   │   │   ├── RoleCard.tsx
│   │   │   │   ├── GapAnalysisTable.tsx
│   │   │   │   └── ThreeLayerBar.tsx
│   │   │   └── common/
│   │   │       ├── MetricCard.tsx
│   │   │       ├── DataTable.tsx
│   │   │       ├── Tooltip.tsx
│   │   │       └── ExportButton.tsx
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useOrganization.ts
│   │   │   ├── useSimulation.ts
│   │   │   └── useComparison.ts
│   │   └── styles/
│   │       └── globals.css
│   └── public/
│
├── data/                         # EXISTING: 7 CSV files (unchanged)
├── engine/                       # EXISTING: cascade, feedback, simulator, etc. (unchanged)
├── models/                       # EXISTING: organization.py (unchanged)
├── stages/                       # EXISTING: stage scripts (unchanged)
├── scenario_catalog/             # EXISTING: scenario CSVs (unchanged)
├── scripts/                      # EXISTING: run scripts (unchanged)
├── outputs/                      # EXISTING: output files (unchanged)
├── docs/                         # EXISTING + this plan
├── main.py                       # EXISTING: CLI runner (unchanged)
├── run_ui.py                     # NEW: Entry point — starts backend + opens frontend
└── requirements.txt              # NEW: Python dependencies for API
```

**Key principle:** Zero changes to existing files. The `api/` and `ui/` directories are additive.

---

## 5. Technology Stack

### Backend
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Web Framework | **FastAPI** | Async, auto-OpenAPI docs, Pydantic integration |
| Serialization | **Pydantic v2** | Type-safe request/response models |
| Server | **Uvicorn** | ASGI server, built-in with FastAPI |
| CORS | **fastapi.middleware.cors** | Allow React dev server cross-origin |

### Frontend
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | **React 18** | Component model, hooks, concurrent rendering |
| Language | **TypeScript** | Type safety mirroring Python dataclasses |
| Build Tool | **Vite** | Fast HMR, ESBuild bundling |
| Charts | **Recharts** | React-native charting, composable |
| Sankey | **d3-sankey** + custom React wrapper | For cascade flow visualization |
| Data Tables | **TanStack Table** | Sorting, filtering, column resize |
| Styling | **Tailwind CSS** | Utility-first, fast iteration |
| State | **React Query (TanStack Query)** | Server-state caching, refetch |
| Routing | **React Router v6** | Client-side page navigation |
| Icons | **Lucide React** | Clean, consistent icon set |

---

# PART III: BACKEND API DESIGN

## 6. API Endpoints

All endpoints are prefixed with `/api/`. The backend loads the organization data once
at startup and holds it in memory.

### 6.1 Organization Data

```
GET /api/org
  → Returns: { roles: [...], workloads: [...], tasks: [...], skills: [...],
               tools: [...], human_system: [...], summary: {...} }
  → Source: engine/loader.py → load_organization()
  → Serialization: Dataclass → dict for each entity
```

```
GET /api/org/hierarchy
  → Returns: Tree structure for org navigation
  → Shape: { name, level, children: [...], headcount, annual_cost }
  → Built from: roles grouped by function → sub_function → jfg → job_family
```

### 6.2 Static Snapshot (Gap Analysis)

```
GET /api/snapshot
  → Returns: Full OrgGapResult as JSON
  → Source: engine/gap_engine.py → compute_snapshot()
  → Includes: per-function, per-role, per-workload gap data
              + top opportunities ranked
```

```
GET /api/snapshot/function/{function_name}
  → Returns: FunctionGapResult for a specific function
  → Drill-down from org → function level
```

### 6.3 Cascade (Single-Step)

```
POST /api/cascade
  Body: {
    stimulus_name: str,
    tools: [str],
    target_functions: [str] | "ALL",
    policy: str,
    absorption_factor: float,
    alpha: float,
    training_cost_per_person: float
  }
  → Returns: Full CascadeResult (all 9 steps) as JSON
  → Source: engine/cascade.py → run_cascade()
```

### 6.4 Time-Series Simulation

```
POST /api/simulate
  Body: {
    stimulus: { ... },          # Same as cascade stimulus
    params: {                   # SimulationParams
      scenario_name: str,
      adoption: { alpha, k, midpoint, delay_months },
      expansion: { ... } | null,
      extension: { ... } | null,
      policy: str,
      time_horizon_months: int,
      ...
    },
    feedback_params: { ... },   # FeedbackParams overrides (optional)
    trace: bool                 # Enable trace for explainability
  }
  → Returns: {
      summary: { total_months, final_headcount, net_savings, payback_month, ... },
      timeline: [ { month, adoption_pct, headcount, net_position, productivity, ... } ],
      human_system_timeline: [ { month, proficiency, readiness, trust, fatigue, ... } ],
      trace: { ... } | null     # Full SimulationTrace if requested
    }
  → Source: engine/simulator_fb.py → simulate_with_feedback()
```

### 6.5 Preset Scenarios

```
GET /api/scenarios/presets
  → Returns: [ { id: "P1", name: "Cautious", params: {...} }, ... ]
  → Source: engine/rates.py → ALL_SCENARIOS
```

```
GET /api/scenarios/catalog
  → Returns: All rows from scenario_catalog/simulation_scenarios_extended.csv
  → Source: stages/scenario_executor.py → load_catalog()
```

```
POST /api/scenarios/run
  Body: { scenario_ids: [str] | null, families: [str] | null }
  → Returns: [ ScenarioResult, ... ] with summary metrics
  → Source: stages/scenario_executor.py → run_batch()
```

### 6.6 Comparison

```
POST /api/compare
  Body: {
    scenarios: [
      { name: str, stimulus: {...}, params: {...} },
      { name: str, stimulus: {...}, params: {...} },
      ...
    ]
  }
  → Returns: {
      scenarios: [ { name, summary, timeline } ],
      comparison_matrix: {
        metrics: ["hc_reduced", "net_savings", "payback_month", "final_trust", ...],
        values: [ [val_s1, val_s2, ...], ... ]
      }
    }
```

### 6.7 Serialization Strategy

Each Python dataclass gets a `to_dict()` helper in `api/serializers.py`:

```python
def serialize_cascade_result(result: CascadeResult) -> dict:
    """Convert CascadeResult to JSON-serializable dict."""
    return {
        "stimulus": asdict(result.stimulus),
        "step1_scope": asdict(result.step1_scope),
        "step2_reclassification": {
            "tasks_to_ai": result.step2_reclassification.tasks_to_ai,
            "tasks_to_human_ai": result.step2_reclassification.tasks_to_human_ai,
            "tasks_unchanged": result.step2_reclassification.tasks_unchanged,
            "reclassified_tasks": [asdict(t) for t in result.step2_reclassification.reclassified_tasks],
        },
        # ... all 9 steps
    }
```

**Why not just `dataclasses.asdict()`?** It works for simple cases but doesn't handle
nested lists of dataclasses with properties. Explicit serializers give control over
what data reaches the frontend and handle computed properties.

---

# PART IV: FRONTEND PAGES & COMPONENTS

## 7. Page Architecture

The UI has **6 pages**, accessible via a sidebar. Each page maps to a distinct
user workflow. The design follows progressive disclosure: summary → drill-down → detail.

### Page 1: Dashboard (Home)

**Purpose:** At-a-glance health check of the organization + quick-launch simulation.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  WORKFORCE TWIN DASHBOARD                             │
├────────┬────────┬────────┬────────┬─────────┬────────┤
│ Total  │ Annual │ Avg    │ Avg    │ Adopt   │ Full   │
│ HC     │ Cost   │ Auto%  │ Aug%   │ Gap $   │ Gap $  │
│ 680    │ $38.6M │ 33.2%  │ 20.1%  │ $4.2M   │ $12.8M │
├────────┴────────┴────────┴────────┴─────────┴────────┤
│  FUNCTION OVERVIEW (bar chart)                        │
│  ┌─────────────────────────────────────────┐          │
│  │ Claims      ████████████░░░░░   340 HC  │          │
│  │ Technology  ████████░░░░░░░░░   120 HC  │          │
│  │ Finance     ██████░░░░░░░░░░░   140 HC  │          │
│  │ People      ████░░░░░░░░░░░░░    80 HC  │          │
│  └─────────────────────────────────────────┘          │
│  L1 (Etter) vs L2 (Achievable) vs L3 (Realized)      │
│                                                       │
│  QUICK ACTIONS                                        │
│  [▶ Run P2 Balanced] [▶ Custom Simulation] [📊 Compare]│
└──────────────────────────────────────────────────────┘
```

**Data Source:** `GET /api/snapshot` (top-level OrgGapResult)

**Components:**
- `MetricCard` × 6 (KPI tiles)
- `StackedBarChart` (function overview with L1/L2/L3 layers)
- Quick-action buttons → navigate to SimulationLab or CompareArena

---

### Page 2: Org Snapshot (Gap Analysis Explorer)

**Purpose:** Drill into the static gap analysis. Answer: "Where are the gaps?"

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  ORG SNAPSHOT: Gap Analysis                           │
├─────────────────┬────────────────────────────────────┤
│  ORG TREE       │  DETAIL PANEL                      │
│                 │                                     │
│  ▼ InsureCo     │  [Claims Function]                 │
│    ▼ Claims     │  ┌────────────────────────────┐    │
│      Processing │  │ Headcount:     340         │    │
│        Intake   │  │ Annual Cost:   $16.4M      │    │
│        Adjust   │  │ Avg Automation: 37.2%      │    │
│      Support    │  │ Adoption Gap:  $2.1M       │    │
│    ▶ Technology │  │ Full Gap:      $6.3M       │    │
│    ▶ Finance    │  └────────────────────────────┘    │
│    ▶ People     │                                     │
│                 │  THREE-LAYER ANALYSIS               │
│                 │  (stacked bars per role)             │
│                 │  ┌──────────────────────────────┐   │
│                 │  │ Intake Spec  ▓▓▓▓░░░░░▒▒▒   │   │
│                 │  │ Adjuster     ▓▓░░░░░░▒▒▒▒   │   │
│                 │  │ Data Entry   ▓▓▓▓▓▓░░▒▒     │   │
│                 │  └──────────────────────────────┘   │
│                 │  ▓ L3 Realized  ░ L2 Achievable     │
│                 │  ▒ L1 Potential                      │
│                 │                                      │
│                 │  TOP OPPORTUNITIES TABLE             │
│                 │  (sortable by savings, gap hours)    │
└─────────────────┴────────────────────────────────────┘
```

**Data Source:** `GET /api/snapshot`, `GET /api/org/hierarchy`

**Components:**
- `OrgTree` — collapsible hierarchy (function → sub_function → jfg → job_family → role)
- `ThreeLayerBar` — L1/L2/L3 stacked horizontal bars per role
- `GapAnalysisTable` — sortable table with adoption_gap, capability_gap, savings
- `MetricCard` — function-level summary metrics
- `RoleCard` — detailed view when a role is selected (workloads, tasks, skills)

**Interactions:**
- Click tree node → update detail panel
- Click role in table → open RoleCard modal with workload-level breakdown
- Click task → show task classification detail (category, compliance, tool match)

---

### Page 3: Cascade Explorer

**Purpose:** Run a single 9-step cascade and explore each step.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  CASCADE EXPLORER                                     │
├──────────────────────────────────────────────────────┤
│  STIMULUS CONFIGURATION                               │
│  ┌────────────────────────────────────────────┐       │
│  │ Tools: [Microsoft Copilot ▼] [+ Add]       │       │
│  │ Scope: [All Functions ▼]                    │       │
│  │ Policy: [Moderate Reduction ▼]              │       │
│  │ Absorption: [====●====] 0.35                │       │
│  │ Training $/person: [2000]                   │       │
│  │                        [▶ Run Cascade]      │       │
│  └────────────────────────────────────────────┘       │
│                                                       │
│  CASCADE FLOW (9 steps, horizontal pipeline)          │
│  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
│  │S1│→│S2│→│S3│→│S4│→│S5│→│S6│→│S7│→│S8│→│S9│       │
│  │░░│  │██│  │░░│  │░░│  │██│  │░░│  │░░│  │░░│  │░░│
│  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘
│  Scope Reclass Cap  Skill  WF   Fin  Struct Human Risk │
│                                                       │
│  STEP DETAIL (expands on click)                       │
│  ┌────────────────────────────────────────────┐       │
│  │ Step 2: Task Reclassification              │       │
│  │   To AI: 45 tasks  To Human+AI: 62 tasks  │       │
│  │   Unchanged: 38 tasks                      │       │
│  │   Total freed: 12.4 hrs/person/month       │       │
│  │   [Show task-level detail ▶]               │       │
│  └────────────────────────────────────────────┘       │
│                                                       │
│  SANKEY DIAGRAM (optional visualization)              │
│  Tasks → Categories → States → Capacity Impact        │
└──────────────────────────────────────────────────────┘
```

**Data Source:** `POST /api/cascade`

**Components:**
- `StimulusConfigurator` — tool selection, scope, policy, parameter sliders
- `CascadePipeline` — horizontal 9-step visualization, click to expand
- `StepDetailPanel` — renders step-specific data (tables, charts)
- `SankeyDiagram` — task flow from categories → states → capacity
- `RiskCards` — Step 9 risks as severity-colored cards

**Key feature:** The 9 steps are shown as a pipeline. Clicking a step expands its
detail panel below. The pipeline visually shows "energy" flowing through — where
scope is wide at Step 1 and narrows through capacity dampening and policy filtering.

---

### Page 4: Simulation Lab (Time-Series)

**Purpose:** Run feedback-enabled simulations and explore the dynamics over time.
This is the **core page** — the most complex and most valuable.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  SIMULATION LAB                                       │
├──────────────────────────────────────────────────────┤
│  CONFIGURATION (collapsible)                          │
│  ┌────────────┬──────────────┬─────────────┐          │
│  │ STIMULUS   │ RATE PARAMS  │ FEEDBACK    │          │
│  │ Tools: ... │ Adopt: α k m │ Trust build │          │
│  │ Scope: ... │ Expand: ...  │ Resist sens │          │
│  │ Policy: .. │ Extend: ...  │ Fatigue ... │          │
│  │            │ Horizon: 36m │ ...         │          │
│  └────────────┴──────────────┴─────────────┘          │
│  Preset: [P1] [P2] [P3] [P4] [P5] [Custom]           │
│                                   [▶ Run Simulation]  │
│                                                       │
│  ═══════════════ RESULTS ══════════════════════════   │
│                                                       │
│  SUMMARY CARDS                                        │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┐          │
│  │ HC↓  │ Net$ │ Pay  │ Prof │Trust │ Risk │          │
│  │ -47  │$2.1M │ M14  │ 67.2 │58.3 │ Med  │          │
│  └──────┴──────┴──────┴──────┴──────┴──────┘          │
│                                                       │
│  TIME SERIES (tabbed charts)                          │
│  [Adoption] [Workforce] [Financial] [Human System]    │
│  ┌────────────────────────────────────────────┐       │
│  │        ╱‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾      │       │
│  │       ╱  ← Effective adoption              │       │
│  │      ╱     (feedback-modulated)            │       │
│  │     ╱                                      │       │
│  │    ╱   ╱‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾                │       │
│  │   ╱   ╱  ← Raw S-curve                    │       │
│  │  ╱   ╱     (no feedback)                   │       │
│  │ ╱   ╱                                      │       │
│  │╱   ╱                                       │       │
│  └──M0────M6────M12───M18───M24───M30───M36──┘       │
│                                                       │
│  FEEDBACK LOOP EXPLORER                               │
│  ┌────────────────────────────────────────────┐       │
│  │ Dominant loop by phase:                    │       │
│  │ M0-6:  B3 (Resistance) — slow start       │       │
│  │ M6-18: R1 (Trust) + R2 (Prof) — accel     │       │
│  │ M18+:  B1 (Absorption) + B4 (Seniority)   │       │
│  │                                            │       │
│  │ MULTIPLIER TIMELINE                        │       │
│  │ (stacked area: human, trust, skill,        │       │
│  │  seniority, capital — shows how each       │       │
│  │  constrains adoption over time)            │       │
│  └────────────────────────────────────────────┘       │
│                                                       │
│  TRACE EXPLORER (if trace=true)                       │
│  [Month selector: ●──────────────────●]               │
│  Per-month: S-curve input → multipliers → effective   │
│  → capacity → HC decision → financial                 │
└──────────────────────────────────────────────────────┘
```

**Data Source:** `POST /api/simulate` (with `trace: true`)

**Components:**
- `StimulusConfigurator` (shared with Cascade Explorer)
- `PolicySelector` — the 5 presets as quick-select cards
- `ParameterSliders` — S-curve α, k, midpoint for each phase
- `TimeSeriesChart` — multi-line chart (Recharts) with tab switching:
  - **Adoption tab:** raw vs effective adoption %, S-curve phases
  - **Workforce tab:** headcount over time, monthly reductions
  - **Financial tab:** cumulative investment vs savings, net position, payback marker
  - **Human System tab:** 5 dimensions (proficiency, readiness, trust, capital, fatigue) on one chart
  - **Productivity tab:** productivity index with valley annotation
  - **Skill Gap tab:** opened vs closed vs current gap
- `FeedbackLoopDiagram` — visual showing which loops dominate by phase
- `TraceExplorer` — month slider + per-month computation breakdown
- `RadarChart` — human system state as radar (5 axes) at selected month

**Key interactions:**
1. Select preset (P1-P5) → auto-fills all parameters
2. Click "Run Simulation" → loading state → results appear
3. Hover on any chart point → tooltip shows month detail
4. Click a month on the timeline → TraceExplorer shows full decomposition
5. Toggle trace mode → enables detailed per-month explainability

---

### Page 5: Scenario Catalog

**Purpose:** Run the full 40-scenario catalog, browse results, select for comparison.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  SCENARIO CATALOG                                     │
├──────────────────────────────────────────────────────┤
│  FILTERS                                              │
│  Family: [All ▼] [Baseline] [Technology] [Policy] ... │
│  Status: [All] [Passed] [Failed]                      │
│                                    [▶ Run All]        │
│                                    [▶ Run Selected]   │
│                                                       │
│  RESULTS TABLE                                        │
│  ┌────────────────────────────────────────────┐       │
│  │ ☐ ID     Name              HC↓ Net$  Pay  │       │
│  │ ☑ SC-01  Baseline          -12 $0.8M M18  │       │
│  │ ☑ SC-02  Copilot Claims    -28 $1.4M M12  │       │
│  │ ☐ SC-03  UiPath Finance    -15 $0.9M M16  │       │
│  │ ☑ SC-04  Aggressive All    -47 $2.1M M10  │       │
│  │ ...                                        │       │
│  └────────────────────────────────────────────┘       │
│                                                       │
│  [📊 Compare Selected (3)]                            │
│                                                       │
│  HEATMAP: scenario × metric                          │
│  (rows = scenarios, cols = metrics,                   │
│   color intensity = relative magnitude)               │
└──────────────────────────────────────────────────────┘
```

**Data Source:** `GET /api/scenarios/catalog`, `POST /api/scenarios/run`

**Components:**
- `DataTable` (TanStack Table) — sortable, filterable, selectable rows
- `HeatmapGrid` — scenario × metric heatmap with color scale
- Selection checkboxes → "Compare Selected" button → navigates to CompareArena

---

### Page 6: Compare Arena

**Purpose:** Side-by-side comparison of 2-4 scenarios across all dimensions.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  COMPARE ARENA                                        │
├──────────────────────────────────────────────────────┤
│  SCENARIO SELECTOR                                    │
│  [Cautious P1 ×] [Balanced P2 ×] [Aggressive P3 ×]   │
│  [+ Add Scenario]                                     │
│                                                       │
│  OVERLAY CHARTS (same axes, different colors)         │
│  ┌────────────────────────────────────────────┐       │
│  │ ADOPTION OVER TIME                         │       │
│  │     ─── P1 (cautious, green)               │       │
│  │     ─── P2 (balanced, blue)                │       │
│  │     ─── P3 (aggressive, red)               │       │
│  │   ╱‾‾‾‾──────────────────── P3             │       │
│  │  ╱  ╱‾‾‾‾──────────── P2                  │       │
│  │ ╱  ╱  ╱‾‾‾‾───── P1                       │       │
│  └────────────────────────────────────────────┘       │
│                                                       │
│  COMPARISON MATRIX                                    │
│  ┌──────────────┬──────┬──────┬──────┐                │
│  │ Metric       │  P1  │  P2  │  P3  │                │
│  ├──────────────┼──────┼──────┼──────┤                │
│  │ HC Reduced   │  -12 │  -28 │  -47 │                │
│  │ Net Savings  │ $0.8M│ $1.4M│ $2.1M│                │
│  │ Payback      │ M18  │ M12  │ M10  │                │
│  │ Final Trust  │ 62.1 │ 58.3 │ 41.7 │                │
│  │ Peak Fatigue │ 12.4 │ 28.7 │ 52.3 │                │
│  │ Risk Level   │  Low │  Med │ High │                │
│  └──────────────┴──────┴──────┴──────┘                │
│                                                       │
│  TRADE-OFF RADAR                                      │
│  (radar chart: efficiency, cost, risk, human impact)  │
│                                                       │
│  NARRATIVE SUMMARY                                    │
│  "P1 is safest but slowest. P3 saves most but has     │
│   highest change burden. P2 offers the best balance   │
│   of savings vs. organizational impact."              │
└──────────────────────────────────────────────────────┘
```

**Data Source:** `POST /api/compare`

**Components:**
- Scenario selection tags (removable, +add)
- `TimeSeriesChart` — overlaid multi-scenario lines (same chart, different colors)
- Comparison matrix table
- `RadarChart` — overlaid per-scenario (efficiency, savings, risk, trust, fatigue axes)
- Narrative summary (generated from comparison data, not LLM — rule-based)

---

# PART V: IMPLEMENTATION PHASES

## Phase 1: Backend Foundation (API Layer)

**Goal:** Expose all engine functionality via REST API. No UI yet.

**Tasks:**
1. Create `api/` directory structure
2. Write `api/app.py` — FastAPI app with CORS, lifespan (loads org data on startup)
3. Write `api/serializers.py` — convert all engine dataclasses to dicts
4. Write `api/schemas.py` — Pydantic models for requests
5. Write route files:
   - `routes/organization.py` — org data + hierarchy
   - `routes/snapshot.py` — gap analysis
   - `routes/cascade.py` — 9-step cascade
   - `routes/simulate.py` — time-series with feedback
   - `routes/scenarios.py` — catalog + batch
   - `routes/compare.py` — multi-scenario comparison
6. Write `requirements.txt` (fastapi, uvicorn, pydantic)
7. Write `run_ui.py` entry point
8. Test all endpoints via Swagger UI (`/docs`)

**Estimated scope:** ~800-1000 lines of Python

**Dependencies:** Zero changes to existing engine files. Pure additive.

---

## Phase 2: Frontend Scaffold (React/TypeScript Setup)

**Goal:** Build the UI skeleton — routing, layout, API client, types.

**Tasks:**
1. Initialize Vite + React + TypeScript project in `ui/`
2. Install dependencies (recharts, tailwindcss, tanstack-query, tanstack-table, react-router, lucide-react)
3. Define TypeScript types mirroring Python dataclasses (`types/`)
4. Build API client (`api/client.ts`) — typed fetch wrappers for all endpoints
5. Build layout components (Sidebar, Header, PageShell)
6. Set up React Router with 6 pages (empty shells)
7. Set up TanStack Query provider
8. Configure Vite proxy to FastAPI backend
9. Build reusable `MetricCard`, `DataTable`, `ExportButton` components

**Estimated scope:** ~1500-2000 lines of TypeScript/TSX

---

## Phase 3: Dashboard + Org Snapshot Pages

**Goal:** First two pages fully functional — view org data and gap analysis.

**Tasks:**
1. Dashboard page — 6 KPI cards + function overview chart + quick actions
2. `StackedBarChart` component (L1/L2/L3 layers per function)
3. Org Snapshot page — tree navigation + detail panel
4. `OrgTree` component — collapsible hierarchy with click handlers
5. `ThreeLayerBar` component — per-role L1/L2/L3 horizontal bars
6. `GapAnalysisTable` — sortable opportunity table
7. `RoleCard` — modal/drawer with workload and task detail
8. Hook up to `GET /api/snapshot` and `GET /api/org/hierarchy`

**Estimated scope:** ~2000-2500 lines

---

## Phase 4: Cascade Explorer Page

**Goal:** Configure and run single-step cascades, explore each step.

**Tasks:**
1. `StimulusConfigurator` — tool multi-select, function scope, policy dropdown, sliders
2. `CascadePipeline` — 9-step horizontal visualization (SVG or flex layout)
3. Step detail panels — step-specific content (tables, metrics) for each of 9 steps
4. `SankeyDiagram` — optional cascade flow visualization (d3-sankey)
5. Risk cards — severity-colored risk items from Step 9
6. Hook up to `POST /api/cascade`

**Estimated scope:** ~2500-3000 lines

---

## Phase 5: Simulation Lab Page (Core)

**Goal:** The flagship page — configure, run, and explore time-series simulations.

**Tasks:**
1. Configuration panel — stimulus + rate params + feedback params
2. `PolicySelector` — P1-P5 preset cards with quick-fill
3. `ParameterSliders` — S-curve parameters (α, k, midpoint, delay) with live preview
4. `TimeSeriesChart` — 6 tabbed chart variants (adoption, workforce, financial, human system, productivity, skill gap)
5. Raw vs effective adoption overlay
6. `FeedbackLoopDiagram` — phase dominance visualization
7. `TraceExplorer` — month slider + computation breakdown panel
8. `RadarChart` — human system radar at selected month
9. `GaugeChart` — risk level gauge
10. Hook up to `POST /api/simulate`

**Estimated scope:** ~3000-4000 lines

---

## Phase 6: Scenario Catalog + Compare Arena

**Goal:** Batch execution and side-by-side comparison.

**Tasks:**
1. Scenario Catalog page — filterable table with run controls
2. `HeatmapGrid` — scenario × metric heatmap
3. Selection → Compare flow
4. Compare Arena page — scenario selector + overlay charts
5. Overlay `TimeSeriesChart` (multiple scenarios on same axes)
6. Comparison matrix table
7. Trade-off `RadarChart` (overlaid radar)
8. Rule-based narrative summary generation
9. Hook up to `POST /api/scenarios/run` and `POST /api/compare`

**Estimated scope:** ~2500-3000 lines

---

## Phase 7: Polish & Integration

**Goal:** Consistent design, error handling, export capabilities, documentation.

**Tasks:**
1. Consistent color scheme and typography across all pages
2. Loading states, error boundaries, empty states
3. CSV/JSON export for all data views
4. Chart responsiveness (resize handling)
5. Keyboard navigation and accessibility basics
6. `run_ui.py` → starts both uvicorn and vite dev server with one command
7. README with setup instructions in the `ui/` directory

---

# PART VI: DATA FLOW ARCHITECTURE

## 8. End-to-End Data Flow

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  7 CSVs  │────▶│  loader  │────▶│ OrganizationData │────▶│  FastAPI     │
│  (data/) │     │  .py     │     │  (in-memory)     │     │  (api/)      │
└─────────┘     └──────────┘     └──────┬───────────┘     └──────┬───────┘
                                        │                         │
              ┌─────────────────────────┤                         │ JSON
              │                         │                         │
         ┌────▼────┐  ┌────────▼────┐  ┌─────▼──────┐     ┌──────▼───────┐
         │gap_engine│  │  cascade    │  │simulator_fb│     │  React SPA   │
         │.py      │  │  .py        │  │.py         │     │  (ui/)       │
         └─────────┘  └────────────┘  └────────────┘     └──────────────┘
              │              │               │                    │
              ▼              ▼               ▼                    ▼
         OrgGapResult  CascadeResult  FBSimulationResult   Charts/Tables
```

Key architectural invariant: **The engine files are never modified.** The API layer
is a thin translation between HTTP request → engine function call → JSON response.

---

## 9. State Management Strategy

| State Type | Solution | Rationale |
|-----------|---------|-----------|
| Server data (org, snapshots, results) | **TanStack Query** | Caching, refetch, stale management |
| UI navigation state | **React Router** | URL-driven navigation |
| Page-local interaction state | **useState/useReducer** | Simple, colocated |
| Cross-page selection (compare set) | **React Context** | Small, shared state |
| User preferences | **localStorage** | Persist across sessions |

No Redux, no Zustand — the app is primarily a server-state viewer.
TanStack Query handles 90% of state management needs.

---

# PART VII: KEY DESIGN DECISIONS

## 10. Design Decisions with Rationale

### D1: Self-Contained Package (No Parent Imports)
**Decision:** All code stays within `workforce_twin_modeling/`. No imports from `draup_world_model/`.
**Rationale:** The workforce twin modeling is a standalone analytical tool. Coupling it
to the parent package's web framework, connectors, or chatbot would create unnecessary
dependencies and deployment complexity.

### D2: FastAPI over Flask/Django
**Decision:** FastAPI for the backend.
**Rationale:** Pydantic request validation mirrors the existing dataclass patterns.
Auto-generated OpenAPI docs (`/docs`) provide API documentation for free.
Async capability future-proofs for long-running simulations.

### D3: React + TypeScript over Python-Rendered Templates
**Decision:** Full React SPA instead of Jinja templates or Streamlit.
**Rationale:** The UI requires rich interactivity — drill-downs, linked charts,
parameter sliders with live feedback, overlay comparisons. These are fundamentally
client-side interactions that don't benefit from server rendering.

### D4: Recharts over D3-only
**Decision:** Recharts for most charts, D3 only for Sankey diagrams.
**Rationale:** Recharts provides React-native composable charts with built-in
tooltips, legends, and responsiveness. D3 is used only where Recharts lacks
a component type (Sankey flow diagrams).

### D5: No Database
**Decision:** All data from CSVs in memory. No SQLite, no PostgreSQL.
**Rationale:** The dataset is small (680 employees, ~200 tasks, ~150 skills).
Loading into memory takes <100ms. Scenario results are transient — the value
is in exploring different configurations, not persisting runs.

### D6: Vite Dev Server + FastAPI (Dual Process)
**Decision:** Development runs two processes: Vite (frontend) + Uvicorn (backend).
Production can serve the built frontend from FastAPI's static files.
**Rationale:** Standard pattern. Vite proxy configuration sends `/api/*` to Uvicorn.
No complex reverse proxy needed for development.

### D7: Zero Changes to Existing Engine
**Decision:** No modifications to any file in `engine/`, `models/`, `stages/`, `data/`.
**Rationale:** The engine is battle-tested with stress tests and critical examination.
The API layer wraps it; it doesn't modify it. This prevents regressions.

---

# PART VIII: COMPONENT SPECIFICATIONS

## 11. Critical Component Details

### 11.1 TimeSeriesChart (the workhorse)

The time-series chart appears on Simulation Lab and Compare Arena. It must handle:

- **Single scenario mode:** 2-6 lines on one chart (e.g., raw vs effective adoption)
- **Multi-scenario mode:** same metric across 2-4 scenarios (overlay)
- **Tab switching:** adoption, workforce, financial, human system, productivity, skill gap

```typescript
interface TimeSeriesChartProps {
  data: MonthlyDataPoint[];           // Array of { month, ...metrics }
  lines: LineConfig[];                // Which fields to plot
  xKey: string;                       // "month"
  yLabel: string;                     // axis label
  annotations?: Annotation[];          // vertical lines (payback month), markers
  highlightMonth?: number;            // linked to TraceExplorer
  onMonthClick?: (month: number) => void;
}

interface LineConfig {
  dataKey: string;                     // field name in data
  label: string;                       // legend label
  color: string;                       // line color
  strokeDasharray?: string;            // dashed for raw/reference lines
  area?: boolean;                      // fill area under line
}
```

### 11.2 StimulusConfigurator (shared input form)

Used by both Cascade Explorer and Simulation Lab:

```typescript
interface StimulusConfig {
  name: string;
  tools: string[];                     // from available tools in org
  targetFunctions: string[] | "ALL";   // from org functions
  policy: "no_layoffs" | "natural_attrition" | "moderate_reduction"
         | "active_reduction" | "rapid_redeployment";
  absorptionFactor: number;            // 0.0 - 1.0 slider
  trainingCostPerPerson: number;       // $ input
}
```

The configurator shows available tools and functions from the loaded org data
(fetched via `GET /api/org`), so selections are always valid.

### 11.3 TraceExplorer (month-by-month explainability)

The most novel component — renders the SimulationTrace data:

```typescript
interface TraceExplorerProps {
  trace: SimulationTrace;
  selectedMonth: number;
  onMonthChange: (month: number) => void;
}

// Renders:
// 1. Month slider (0 → time_horizon)
// 2. S-curve input values
// 3. Feedback multiplier breakdown (5 bars showing how much each constrains)
// 4. Effective adoption computation (formula rendered)
// 5. HC decision detail (if review month)
// 6. Dominant loop badge
// 7. Active improvements list (T1/T2 annotations)
```

This component is what makes the simulation *explainable*. Instead of seeing
a chart line go up or down, the user can click any month and see *exactly why*
the adoption rate was dampened — which multiplier was lowest, which feedback
loop dominated, what the HC decision reasoning was.

### 11.4 FeedbackLoopDiagram (system dynamics visualization)

A visual representation of the 8 feedback loops and which ones dominate:

```
     ┌──────────────┐
     │   S-CURVE     │  ← Raw adoption rate
     │   (input)     │
     └───────┬───────┘
             │
     ┌───────▼───────┐
     │  HUMAN SYSTEM  │ ← B3 resistance, R1 trust, R2 proficiency
     │  multiplier    │
     └───────┬───────┘
             │
     ┌───────▼───────┐
     │  SKILL VALLEY  │ ← B2 skill gap drag
     │  multiplier    │
     └───────┬───────┘
             │
     ┌───────▼───────┐
     │  SENIORITY     │ ← B4 diminishing returns
     │  offset        │
     └───────┬───────┘
             │
     ┌───────▼───────┐
     │  EFFECTIVE     │ ← Final adoption rate
     │  ADOPTION      │
     └───────────────┘
```

Each box is highlighted (green/red/neutral) based on its current multiplier value.
Boxes close to 1.0 are neutral. Boxes < 0.8 are red (constraining). Boxes can pulse
to show which is *currently dominant*.

---

# PART IX: RISK & MITIGATION

## 12. Implementation Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Engine dataclasses have nested structures that don't serialize cleanly | Medium | Explicit serializers (not generic asdict). Test each route end-to-end. |
| Simulation runs take >2s for 36 months → UI feels sluggish | Low | Simulations typically run in <500ms. Add loading spinners. Future: Web Workers for frontend, background tasks for backend. |
| Recharts can't render Sankey diagrams | Low | Use d3-sankey for Sankey only. Wrap in React component. Sankey is optional (nice-to-have, not critical). |
| Type drift between Python and TypeScript | Medium | Generate TypeScript types from Pydantic schemas (pydantic-to-typescript). Or maintain manually — small surface area. |
| Data CSV format changes break loader | Low | Loader is existing code, already handles this. No change needed. |
| Frontend bundle size too large | Low | Vite tree-shakes. Recharts is ~150KB gzipped. d3-sankey is ~20KB. Tailwind purges unused CSS. |

---

# PART X: SUCCESS CRITERIA

## 13. Definition of Done

The implementation is complete when a user can:

1. **Start the app** with one command (`python run_ui.py` or `npm run dev` + `uvicorn`)
2. **See the dashboard** with org-level KPIs and function overview
3. **Drill into any function** → roles → workloads → tasks in the Org Snapshot
4. **Configure a stimulus** (select tools, scope, policy) and run a cascade
5. **See all 9 cascade steps** with expandable detail panels
6. **Run a time-series simulation** with any of the 5 presets or custom parameters
7. **See 6 time-series charts** (adoption, workforce, financial, human system, productivity, skills)
8. **Explore the trace** month-by-month to understand why the simulation behaved as it did
9. **Run the scenario catalog** and filter/sort results
10. **Compare 2-4 scenarios** side-by-side with overlaid charts and comparison matrix
11. **Export data** as CSV or JSON from any view

---

# PART XI: FILE-LEVEL IMPLEMENTATION CHECKLIST

## Phase 1: Backend
- [ ] `api/__init__.py`
- [ ] `api/app.py` (FastAPI app, CORS, lifespan, org data loading)
- [ ] `api/serializers.py` (all engine dataclass → dict converters)
- [ ] `api/schemas.py` (Pydantic request models)
- [ ] `api/routes/__init__.py`
- [ ] `api/routes/organization.py`
- [ ] `api/routes/snapshot.py`
- [ ] `api/routes/cascade.py`
- [ ] `api/routes/simulate.py`
- [ ] `api/routes/scenarios.py`
- [ ] `api/routes/compare.py`
- [ ] `requirements.txt`
- [ ] `run_ui.py`

## Phase 2: Frontend Scaffold
- [ ] `ui/package.json`
- [ ] `ui/tsconfig.json`
- [ ] `ui/vite.config.ts`
- [ ] `ui/index.html`
- [ ] `ui/src/main.tsx`
- [ ] `ui/src/App.tsx`
- [ ] `ui/src/api/client.ts`
- [ ] `ui/src/types/organization.ts`
- [ ] `ui/src/types/cascade.ts`
- [ ] `ui/src/types/simulation.ts`
- [ ] `ui/src/types/scenario.ts`
- [ ] `ui/src/components/layout/Sidebar.tsx`
- [ ] `ui/src/components/layout/Header.tsx`
- [ ] `ui/src/components/layout/PageShell.tsx`
- [ ] `ui/src/components/common/MetricCard.tsx`
- [ ] `ui/src/components/common/DataTable.tsx`
- [ ] `ui/src/components/common/ExportButton.tsx`
- [ ] `ui/src/hooks/useOrganization.ts`
- [ ] `ui/src/hooks/useSimulation.ts`
- [ ] `ui/src/hooks/useComparison.ts`
- [ ] `ui/src/styles/globals.css`

## Phase 3: Dashboard + Org Snapshot
- [ ] `ui/src/pages/Dashboard.tsx`
- [ ] `ui/src/pages/OrgSnapshot.tsx`
- [ ] `ui/src/components/charts/StackedBarChart.tsx`
- [ ] `ui/src/components/org/OrgTree.tsx`
- [ ] `ui/src/components/org/ThreeLayerBar.tsx`
- [ ] `ui/src/components/org/GapAnalysisTable.tsx`
- [ ] `ui/src/components/org/RoleCard.tsx`

## Phase 4: Cascade Explorer
- [ ] `ui/src/pages/CascadeExplorer.tsx`
- [ ] `ui/src/components/simulation/StimulusConfigurator.tsx`
- [ ] `ui/src/components/simulation/PolicySelector.tsx`
- [ ] `ui/src/components/cascade/CascadePipeline.tsx`
- [ ] `ui/src/components/cascade/StepDetailPanel.tsx`
- [ ] `ui/src/components/charts/SankeyDiagram.tsx`

## Phase 5: Simulation Lab
- [ ] `ui/src/pages/SimulationLab.tsx`
- [ ] `ui/src/components/simulation/ParameterSliders.tsx`
- [ ] `ui/src/components/simulation/FeedbackLoopDiagram.tsx`
- [ ] `ui/src/components/simulation/TraceExplorer.tsx`
- [ ] `ui/src/components/charts/TimeSeriesChart.tsx`
- [ ] `ui/src/components/charts/RadarChart.tsx`
- [ ] `ui/src/components/charts/GaugeChart.tsx`

## Phase 6: Scenario Catalog + Compare Arena
- [ ] `ui/src/pages/ScenarioCatalog.tsx`
- [ ] `ui/src/pages/CompareArena.tsx`
- [ ] `ui/src/components/charts/HeatmapGrid.tsx`

## Phase 7: Polish
- [ ] Consistent color tokens
- [ ] Loading/error/empty states
- [ ] CSV/JSON export integration
- [ ] `run_ui.py` dual-server launch
- [ ] `ui/README.md`

---

*Total estimated new code: ~15,000-20,000 lines (800-1000 Python API + 14,000-19,000 TypeScript/React)*
*Zero modifications to existing engine files.*
*Self-contained within `workforce_twin_modeling/`.*
