# User Interface — Deep Dive

## Making the Invisible Visible

*"The least obvious part of the system, its function or purpose, is often the most crucial determinant of the system's behavior."*
*— Donella Meadows, Thinking in Systems*

The simulation engine answers "what will happen." The UI answers "what does that mean for the person making decisions?" It translates stocks, flows, and feedback loops into charts, cards, and drill-downs that enterprise leaders can use to compare scenarios, understand trade-offs, and build conviction.

This document covers the complete frontend architecture: the technology stack, the five core pages, the component system, and the design philosophy.

---

## 1. First Principles: Why This UI?

### The Problem

Workforce transformation decisions are made by people who don't think in S-curves and feedback loops. They think in headcount, dollars, risk, and timing. But the naive version of these metrics ("automation saves 40%") is wrong — the simulation engine exists precisely to correct this.

The UI must bridge this gap: take the engine's nuanced, feedback-adjusted, time-series outputs and present them as clear, actionable insights without losing the nuance that makes them valuable.

### The Design Decisions

1. **Progressive disclosure.** Dashboard shows 8 KPIs. Explorer lets you drill into any one. Simulation Lab lets you test hypotheses. Deep Dive lets you compare scenarios. Each layer adds detail for users who want it, without overwhelming users who don't.

2. **Dark mode, data-first.** Dense information density. Glassmorphic cards. Charts dominate. Text is secondary. The aesthetic matches the seriousness of the decisions being made — this is an analytical instrument, not a marketing site.

3. **Simulation as conversation.** The Simulation Lab doesn't just run one scenario and show results. It lets you adjust parameters, re-run, compare, and iterate. The UI supports the cognitive loop: hypothesis -> simulate -> observe -> refine -> repeat.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | React 18.3 | Component-based UI |
| Build | Vite 7.3 | Fast development server + production builds |
| Language | TypeScript | Type safety across frontend |
| Styling | TailwindCSS 3.4 | Utility-first CSS with dark mode |
| Charts | Recharts 2.12 | Composable chart components |
| Tables | TanStack Table | Complex data grids |
| State | TanStack Query (React Query) | Server state management |
| Routing | React Router 6.22 | Client-side navigation |
| Icons | Lucide React 0.344 | Consistent icon system |

### Why This Stack

- **React + TypeScript** — The TypeScript interfaces in `types/index.ts` mirror the Python dataclasses exactly. A `TimelinePoint` in TypeScript has the same fields as an `FBMonthlySnapshot` in Python. Type mismatches are caught at compile time, not at runtime.
- **Recharts** — Composable. A `TimeSeriesChart` can render lines, areas, and bars simultaneously (ComposedChart). This is essential for showing adoption curves (line) against headcount (area) against investment (bar) on the same time axis.
- **TanStack Query** — Separates server state from UI state. The org data is fetched once and cached. Simulation results are fetched on demand and not cached (each run is unique).

---

## 3. Application Structure

### Routing

```
/                → Dashboard ("Pulse")
/explorer        → Explorer ("Current State Explorer")
/simulation      → SimulationLab ("Simulation Lab")
/nova            → Nova ("Nova" — AI assistant)
/deep-dive       → DeepDive ("Deep Dive")
```

### Layout

```
┌──────────────────────────────────────────────────┐
│  Sidebar (collapsible)  │  Header (title + theme) │
│                         │                         │
│  Pulse                  │  ┌─────────────────────┐│
│  Explorer               │  │                     ││
│  Simulation             │  │   Page Content      ││
│  Nova                   │  │   (scrollable)      ││
│  ───────                │  │                     ││
│  Deep Dive              │  │                     ││
│                         │  └─────────────────────┘│
└──────────────────────────────────────────────────┘
```

The sidebar collapses to icon-only mode (58px from 220px). The main content area fills the remaining viewport. Each page manages its own scrolling.

### API Client (`api/client.ts`)

A typed fetch wrapper:
```typescript
const api = {
    // Organization
    health: () => fetchJSON('/health'),
    org: () => fetchJSON('/org'),
    orgHierarchy: () => fetchJSON('/org/hierarchy'),
    orgFunctions: () => fetchJSON('/org/functions'),
    orgRole: (id: string) => fetchJSON(`/org/roles/${id}`),

    // Snapshot
    snapshot: () => fetchJSON('/snapshot'),
    opportunities: () => fetchJSON('/snapshot/opportunities'),

    // Simulation
    simulate: (config: any) => post('/simulate', config),
    simulatePreset: (id: string, trace = false) =>
        post(`/simulate/preset/${id}?trace=${trace}`, {}),
    presets: () => fetchJSON('/simulate/presets'),

    // Scenarios
    catalog: () => fetchJSON('/scenarios/catalog'),
    compare: (scenarios: any[], trace = false) =>
        post('/compare', { scenarios, trace }),
};
```

Base URL: `/api` (proxied to `localhost:8000` in development via Vite config).

---

## 4. The Five Core Pages

### 4.1 Dashboard ("Pulse")

**Purpose:** At-a-glance organizational health and automation opportunity assessment.

**Data Sources:**
- `useSnapshot()` hook → org gap data
- `useFunctions()` hook → function list

**Layout:**

```
┌──────────────────────────────────────────────────┐
│  KPI Row 1 (4 cards)                              │
│  [Headcount] [Annual Cost] [Realized Auto] [Value]│
│                                                    │
│  KPI Row 2 (4 cards)                              │
│  [Adopt Gap] [At-Risk] [Compliance] [Skills]      │
│                                                    │
│  ┌───────────────────────┐ ┌─────────────────────┐│
│  │ Automation by Function│ │ Readiness Radar     ││
│  │ (Stacked Bar Chart)   │ │ (Radar Chart)       ││
│  │ L3 | L2-L3 | L1-L2   │ │ prof/ready/trust    ││
│  └───────────────────────┘ └─────────────────────┘│
│                                                    │
│  ┌───────────────────────┐ ┌─────────────────────┐│
│  │ Function Overview     │ │ Top Savings         ││
│  │ (clickable list)      │ │ Opportunities       ││
│  └───────────────────────┘ └─────────────────────┘│
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │ AI Insight Strip (gradient glass card)         ││
│  │ "Adoption gap represents..." + CTA buttons    ││
│  └────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

**Key Metrics Displayed:**
| Metric | Source | Format |
|--------|--------|--------|
| Total Headcount | `snapshot.headcount` | Number |
| Annual Cost | `snapshot.annual_cost` | Currency ($XM) |
| Realized Automation | `snapshot.weighted_l3` | Percentage |
| Unrealized Value | `snapshot.full_gap_savings` | Currency |
| Adoption Gap | `snapshot.adoption_gap_savings` | Currency |
| At-Risk Roles | Count of `redesign_candidate = true` | Number |
| Compliance Tasks | `snapshot.compliance_tasks` | Number |
| Total Skills | Total skill count | Number |

**Charts:**
- **Stacked Bar (Automation by Function):** Three segments per function:
  - L3 (green) — already automated
  - L2 - L3 (amber) — adoption gap
  - L1 - L2 (blue) — capability gap
- **Radar (Transformation Readiness):** Per-function radar with three axes: proficiency, readiness, trust

**Interactions:**
- Click a function row → navigate to `/explorer?function={name}`
- Click "Explore Gaps" → navigate to `/explorer`
- Click "Run Simulation" → navigate to `/simulation`

### 4.2 Explorer ("Current State")

**Purpose:** Fractal drill-down into the organization hierarchy. Browse from function to sub-function to role to workload to task.

**Data Sources:**
- `useSnapshot()` hook → org gap data with nested functions/roles
- `useRoleDetail(roleId)` hook → detailed role data (fetched on role selection)

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ Left Panel   │  │ Right Panel                  │ │
│  │ (4 cols)     │  │ (8 cols)                     │ │
│  │              │  │                              │ │
│  │ [Search]     │  │ Function Detail              │ │
│  │              │  │ ┌──────────────────────────┐ │ │
│  │ Function A   │  │ │ 4 KPI metrics            │ │ │
│  │   ├─ Role 1  │  │ │ HC | Cost | Adopt | Full │ │ │
│  │   ├─ Role 2  │  │ └──────────────────────────┘ │ │
│  │   └─ Role 3  │  │                              │ │
│  │ Function B   │  │ [Bar Chart: Role Gaps]       │ │
│  │   ├─ Role 4  │  │                              │ │
│  │   └─ Role 5  │  │ [Table: Role Details]        │ │
│  │              │  │                              │ │
│  └──────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Left Panel (Hierarchy Tree):**
- Search input filters roles by name
- Functions are expandable/collapsible
- Roles show headcount and redesign-candidate indicator (red dot)
- Click function → expand to show child roles
- Click role → show Role Detail in right panel

**Right Panel (Detail View):**

Three modes based on selection:

**No Selection → Empty State**
```
"Select a function or role to explore"
```

**Function Selected → Function Detail**
- 4 KPI cards: Headcount, Annual Cost, Adoption Gap, Full Gap
- Horizontal bar chart: Realized vs Gap per role
- Table: Role | HC | L1% | L3% | Gap Savings | Status

**Role Selected → Role Detail**
- Header: role_name, function, management_level, headcount
- 3 tabs:
  - **Overview:** Automation Score, Augmentation Score, Avg Salary, Annual Cost
  - **Tasks:** Per-workload task table with L1/L3 percentages and category labels
  - **Skills:** Skill list with sunrise (green), sunset (red), current (neutral) tags

### 4.3 Simulation Lab

**Purpose:** The primary decision-support tool. Configure stimuli, run simulations, visualize cascades and time-series results.

**Data Sources:**
- `usePresets()` hook → preset scenario definitions
- `useTools()` hook → available tools
- `useFunctions()` hook → target functions
- `useMutation()` for simulation, cascade, and preset API calls

**This is the most complex page (~58KB).** It combines:

**Configuration Panel:**
- Stimulus type selector (technology injection, headcount target, budget constraint, etc.)
- Tool selection (multi-select from available tools)
- Target function selection (multi-select)
- Policy selection (5 options)
- Rate parameter sliders (alpha, k, midpoint for each phase)
- Feedback parameter overrides (advanced mode)
- Inverse solve targets (optional)

**Results Tabs:**

| Tab | Icon | Content |
|-----|------|---------|
| Headcount | Users | HC trajectory chart, role-level HC table, reduction summary |
| Financial | DollarSign | Investment vs savings chart, payback analysis, ROI metrics |
| Adoption | TrendingUp | Raw vs effective adoption, dampening ratio, human system trajectory |
| Cascade | Layers | Full 9-step cascade visualization (CascadeView component) |
| Trace | Settings | Simulation trace data (when tracing enabled) |

**Headcount Tab:**
- Time-series chart: headcount over 36 months
- Table: per-role headcount at key milestones (M0, M6, M12, M18, M24, M36)
- Summary metrics: total reduced, reduction %, projected final HC

**Financial Tab:**
- Time-series chart: cumulative investment, cumulative savings, net position
- Payback month indicator (reference line)
- ROI calculation
- Investment breakdown (license, training, change management)

**Adoption Tab:**
- Dual-line chart: raw adoption vs effective adoption (the dampening gap)
- Human system trajectory: proficiency, readiness, trust over 36 months
- Multiplier trajectory: human_multiplier, trust_multiplier
- Feedback loop contribution analysis

**Cascade Tab:**
- Animated 9-step cascade visualization (CascadeView component)
- Sequential reveal animation (400ms per step)
- Clickable steps for detail panels

### 4.4 Nova (AI Assistant)

**Purpose:** Conversational interface for exploratory workforce analysis questions.

**Current State:** Mock responses based on keyword matching. Not connected to a live LLM.

**Interface:**

```
┌──────────────────────────────────────────┐
│  Chat Messages (scrollable)              │
│                                          │
│  [User] Which roles are most at risk?    │
│                                          │
│  [Assistant] Based on the analysis...    │
│  ┌──────────────────────────────┐        │
│  │ Insight Cards                │        │
│  │ [HC: 45] [Risk: High] [...]  │        │
│  └──────────────────────────────┘        │
│  Sources: [Claims Processor] [...]       │
│  [Copy] [Helpful] [Not Helpful]          │
│                                          │
├──────────────────────────────────────────┤
│  [New] [Textarea input...] [Send]        │
└──────────────────────────────────────────┘
```

**Suggested Prompts:**
- "Which roles are most at risk?" (Workforce Risk)
- "Top cost-saving opportunities?" (Cost Savings)
- "Critical skill gaps?" (Skill Gaps)
- "Headcount breakdown by function" (HC Summary)

**Response Components:**
- Markdown-formatted text (bold, bullets, numbered lists, tables)
- Insight cards with sentiment (positive/negative/neutral) and icons
- Data source tags (role, function, skill, task types)
- Action bar (copy, thumbs up/down)

### 4.5 Deep Dive

**Purpose:** Advanced analysis tools for comparing scenarios, exploring cascades, and browsing the scenario catalog.

**Three Sub-Tabs:**

| Tab | Component | Purpose |
|-----|-----------|---------|
| Compare | `CompareArena` | Side-by-side multi-scenario comparison |
| Cascade | `CascadeExplorer` | Interactive cascade analysis |
| Scenarios | `ScenarioCatalog` | Pre-built scenario catalog browser |

**CompareArena:**
- Select 2-5 scenarios (presets or custom)
- Run all simultaneously via `/api/compare`
- Comparison matrix: metrics x scenarios
- Overlay charts: HC trajectory, financial trajectory, adoption curves
- Side-by-side summary cards

**CascadeExplorer:**
- Configure stimulus parameters
- Run single cascade via `/api/cascade`
- Full 9-step cascade visualization
- Detailed per-step analysis

**ScenarioCatalog:**
- Browse 40+ pre-built scenarios
- Filter by family (technology_injection, sequencing, stress_test, etc.)
- Run individual scenarios
- View results with summary metrics

---

## 5. The Component System

### Layout Components

**Sidebar (`components/layout/Sidebar.tsx`):**
- Collapsible navigation (220px → 58px)
- 4 main nav items + 1 advanced section
- Active state: `bg-primary/10 text-primary` with glow border
- NavLink-based routing with active detection

**Header (`components/layout/Header.tsx`):**
- Page title (changes with route)
- Theme toggle (dark/light)
- Minimal — doesn't compete with page content

### Common Components

**GlassCard:** Container with glassmorphic styling. Props: `title`, `subtitle`, `icon`, `glow` (boolean). Used everywhere for content grouping.

**MetricCard:** Single KPI display. Props: `icon`, `value`, `label`, `format` (number/currency/percent), `delta` (change indicator), `colorClass`. Used in Dashboard and Explorer.

**ErrorBoundary:** React error boundary with fallback UI. Catches rendering errors in any child component.

### Chart Components

**TimeSeriesChart (`components/charts/TimeSeriesChart.tsx`):**
- Renders line, area, and bar series on a shared time axis
- Uses Recharts ComposedChart
- Supports reference lines (e.g., payback month)
- Click handler for drill-down
- Dark theme tooltips

Props:
```typescript
{
  data: Record<string, unknown>[]
  lines: LineConfig[]              // dataKey, label, color, type, dashed
  xKey?: string                    // default: 'month'
  height?: number                  // default: 300
  referenceLines?: RefLine[]
  onClick?: (data) => void
}
```

**BarChartHorizontal (`components/charts/BarChartHorizontal.tsx`):**
- Horizontal stacked or grouped bars
- Used for function-level automation breakdown
- Dynamic fill colors from props

**RadarChartComponent (`components/charts/RadarChart.tsx`):**
- Multi-series radar for human system dimensions
- Used for readiness/proficiency/trust comparison across functions

### Simulation Components

**CascadeView (`components/simulation/CascadeView.tsx`):**

The most complex visualization component. Renders the 9-step cascade as an animated horizontal strip with detail panels.

**Animation System:**
- Auto-play on mount: reveals steps sequentially at 400ms intervals
- Total duration: ~3.6 seconds (300ms initial + 9 x 400ms)
- Each step transitions from `opacity-0 scale-75` to `opacity-100 scale-100`
- Arrow connectors between steps animate with `scale-x`
- Replay button resets animation

**AnimatedNumber:** Counts up from 0 to target value with ease-out-quartic easing over 1400ms. Uses IntersectionObserver to trigger on scroll visibility.

**Step Detail Panels (9):**

| Step | Hero Metrics | Visualization |
|------|-------------|---------------|
| 1. Scope | HC, tasks, addressable, compliance | Function chips, role grid |
| 2. Reclassify | to_ai, to_human_ai, unchanged, freed_hrs | Pie chart + task list |
| 3. Capacity | gross, net, absorption%, dampening% | Role capacity bar chart |
| 4. Skills | net_gap, sunset, sunrise | Two-column skill lists |
| 5. Workforce | current, projected, reducible, reduction% | HC comparison bar chart |
| 6. Financial | investment, savings, net | Investment breakdown bars |
| 7. Structural | redesign, elimination candidates | Candidate chip lists |
| 8. Human System | change burden score, direction indicators | Color-coded narrative |
| 9. Risk | overall level, risk count, top risk | Risk cards with mitigations |

---

## 6. Design System

### Color Palette (CSS Variables)

Dark mode semantic colors using HSL:

| Token | HSL Value | Usage |
|-------|-----------|-------|
| `--background` | 222, 47%, 6% | Page background |
| `--foreground` | 210, 40%, 98% | Primary text |
| `--primary` | 187, 94%, 43% | Primary actions, active states |
| `--accent` | 265, 80%, 60% | Secondary highlights |
| `--muted` | 222, 30%, 16% | Borders, subtle backgrounds |
| `--success` | 160, 84%, 39% | Positive indicators |
| `--warning` | 38, 92%, 50% | Caution indicators |
| `--destructive` | 350, 89%, 60% | Negative/risk indicators |

### Typography

- **Sans:** Inter — clean, readable at small sizes
- **Mono:** JetBrains Mono — code, data tables, technical metrics

### Animation

Custom keyframes:
- `fade-in`: opacity 0 → 1 (500ms)
- `slide-up`: translateY(10px) + opacity → normal (500ms)
- `pulse-glow`: box-shadow pulsation for active elements

Cascade-specific:
- `cascade-card-reveal`: scale(0.8) → scale(1) + opacity
- `cascade-detail-enter`: translateY(20px) → 0 with spring easing
- `cascade-chip-enter`: staggered chip appearance
- `cascade-bar-fill`: width 0% → target% with ease-out

### Glass Morphism

The `.glass` class applies:
```css
background: rgba(var(--card-rgb), 0.6);
backdrop-filter: blur(12px);
border: 1px solid hsl(var(--muted));
border-radius: 12px;
```

This creates the frosted-glass effect that unifies the design system — content cards float above the dark background with subtle depth.

---

## 7. State Management Architecture

### Server State (React Query)

Organization data, snapshots, and presets are fetched via custom hooks:

```typescript
// Fetched once, cached for session
useSnapshot()      → { data: OrgGap, isLoading }
useFunctions()     → { data: FunctionInfo[], isLoading }
usePresets()       → { data: PresetScenario[], isLoading }

// Fetched on demand (per role selection)
useRoleDetail(id)  → { data: RoleDetail, isLoading }
```

### Local State (useState)

Page-level state for UI interactions:

```typescript
// Explorer
selectedFunction: string | null
selectedRole: string | null
searchQuery: string

// SimulationLab
activeTab: 'headcount' | 'financial' | 'adoption' | 'cascade' | 'trace'
simulationResult: SimulationResult | null

// Nova
messages: ChatMessage[]
input: string
isTyping: boolean

// DeepDive
activeTab: 'compare' | 'cascade' | 'scenarios'
```

### Mutation State (React Query)

Simulation operations use `useMutation` for async execution with loading states:

```typescript
const simulateMutation = useMutation({
    mutationFn: (config) => api.simulate(config),
    onSuccess: (data) => setSimulationResult(data),
});
```

---

## 8. TypeScript Type System

`types/index.ts` mirrors the Python dataclass hierarchy exactly. This creates a type-safe bridge from engine to UI.

### Key Interface Hierarchy

```
Organization Domain:
  Role → basic role info + scores
  TaskDetail → task + L1/L2/L3
  SkillDetail → skill + sunrise/sunset
  ToolInfo → tool + deployment + adoption
  HumanSystemInfo → 5 dimensions + multiplier
  OrgSummary → aggregate counts

Gap Analysis:
  OrgGap
    └── FunctionGap[]
         └── RoleGap[]

Cascade:
  CascadeResult
    ├── step1_scope
    ├── step2_reclassification
    ├── step3_capacity
    ├── step4_skills
    ├── step5_workforce
    ├── step6_financial
    ├── step7_structural
    ├── step8_human_system
    └── step9_risk

Simulation:
  SimulationResult
    ├── summary: SimulationSummary
    ├── timeline: TimelinePoint[]
    ├── cascade: CascadeResult
    ├── trace?: TraceData
    └── inverse_solve?: InverseSolveResult

Comparison:
  ComparisonData
    ├── scenarios: { name, result }[]
    └── comparison_matrix: { metrics, values }
```

The 1:1 correspondence between Python and TypeScript types means that if a field exists in the engine output, it has a typed accessor in the frontend. No `any` types in the critical path. No runtime surprises.

---

## 9. Page-to-API Data Flow

### Dashboard
```
Dashboard mounts
  → useSnapshot() fetches /api/snapshot
  → useFunctions() fetches /api/org/functions
  → Data transforms:
      atRiskRoles = count(roles where redesign_candidate)
      funcBarData = functions.map(fn → { L3, L2-L3, L1-L2 })
      radarData = functions.map(fn → { proficiency, readiness, trust })
      topOpps = snapshot.top_roles_by_savings.slice(0, 5)
  → Renders: MetricCards + BarChart + RadarChart + tables
```

### Explorer
```
Explorer mounts
  → useSnapshot() fetches /api/snapshot
  → User clicks function → filter roles
  → User clicks role → useRoleDetail(roleId) fetches /api/org/roles/{id}
  → Renders: tree (left) + detail (right)
```

### Simulation Lab
```
SimulationLab mounts
  → usePresets() fetches /api/simulate/presets
  → useTools() fetches /api/org/tools
  → useFunctions() fetches /api/org/functions
  → User configures stimulus parameters
  → User clicks "Run Simulation"
      → api.simulate(config) POST to /api/simulate
      → Results populate all 5 tabs
  → OR: User clicks preset
      → api.simulatePreset(id) POST to /api/simulate/preset/{id}
```

### Deep Dive (Compare)
```
CompareArena
  → User selects 2-5 scenarios
  → api.compare(scenarios) POST to /api/compare
  → comparison_matrix drives comparison table
  → individual results drive overlay charts
```

---

## 10. Systems Thinking: The UI as Decision Support System

The UI embodies Meadows' observation that **"many of the interconnections in systems operate through the flow of information."**

### Five Lenses on the Same System

The five pages offer five different lenses on the same underlying system:

| Page | Lens | Question Answered |
|------|------|-------------------|
| Dashboard | Snapshot | "Where are we now?" |
| Explorer | Structure | "What does this role/function look like in detail?" |
| Simulation Lab | Dynamics | "What happens if we do X?" |
| Nova | Conversation | "Help me understand Y" |
| Deep Dive | Comparison | "Which option is better and why?" |

Each lens is valuable independently. Together, they support the complete decision cycle:

```
Dashboard → "We have a $12M adoption gap"
    ↓
Explorer → "Claims Processing has the biggest opportunity"
    ↓
Simulation Lab → "Deploying Copilot with moderate policy yields $4.7M"
    ↓
Deep Dive → "P2 vs P3: P2 saves less but risks less"
    ↓
Dashboard → "After deployment, the gap has narrowed"
```

### Progressive Disclosure as System Boundary

Each page defines a system boundary. The Dashboard shows the organization as a single stock with aggregate metrics. The Explorer decomposes that stock into its fractal components. The Simulation Lab adds flows and feedback to those stocks. Deep Dive adds comparison across multiple possible futures.

This mirrors the systems thinking principle: **"A system is an interconnected set of elements that is coherently organized in a way that achieves something."** The UI reveals the interconnections progressively, showing first the elements (Dashboard), then the connections (Explorer), then the purpose (Simulation Lab), then the alternatives (Deep Dive).

### The Cascade Animation as Systems Narrative

The CascadeView component's 9-step animation is the most systems-thinking-native element of the UI. By revealing steps sequentially with 400ms delays, it forces the viewer to experience the cascade as a narrative:

1. *"Here's what's affected..."* (Scope)
2. *"Here's what changes..."* (Reclassification)
3. *"Here's how much capacity frees..."* (Capacity)
4. *"Here's what skills shift..."* (Skills)
5. *"Here's the headcount impact..."* (Workforce)
6. *"Here's the money..."* (Financial)
7. *"Here's the structural change..."* (Structure)
8. *"Here's how people feel..."* (Human System)
9. *"Here's what could go wrong..."* (Risk)

Each step connects to the previous. Each builds on the previous. By the time the viewer reaches Risk, they have a mental model of the entire cascade — not just the end result, but the causal chain that produced it.

*"A good diagram must be recognized as real."*
*— Rule 10 of the 12 Golden Rules of Causal Loop Diagrams*

The same principle applies to a good interface. It must be recognized as real — as reflecting the actual dynamics of the system it represents, not an idealized version. The Workforce Twin UI achieves this by showing dampening, delays, feedback loops, and trade-offs alongside the optimistic projections. The gap between raw adoption and effective adoption, visible in every simulation chart, is the UI's most honest feature.
