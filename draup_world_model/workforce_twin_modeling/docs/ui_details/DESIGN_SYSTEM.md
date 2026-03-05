# Workforce Twin — Design System & Architecture Bible

> *"The purpose of a system is what it does."* — Stafford Beer
> *"You can't understand a system until you try to change it."* — Donella Meadows

---

## 1. PURPOSE (Why This System Exists)

### 1.1 Core Purpose
Workforce Twin is a **digital twin of an organization's workforce** — a living, queryable model that enables leaders to understand, simulate, and optimize their human systems with the same rigor applied to engineering systems.

### 1.2 Problem Statement
Organizations are complex adaptive systems, yet most workforce tools treat them as static spreadsheets. Leaders lack the ability to:
- **See** the true structure of their organization (beyond org charts)
- **Simulate** the consequences of decisions before making them
- **Explain** why certain outcomes emerge from systemic interactions
- **Compare** alternative futures with quantitative rigor

### 1.3 Design Moat
**Explainability is the moat.** Every metric, prediction, and recommendation must be traceable back to its causal chain. Users must always be able to ask "why?" and drill deeper.

### 1.4 Target Users
| Persona | Role | Primary Need |
|---------|------|-------------|
| **Strategic Leader** | CHRO, VP People | Scenario planning, workforce strategy |
| **Operational Manager** | Director, Team Lead | Capacity planning, skill gap analysis |
| **Analyst** | People Analytics, HR Data | Deep exploration, custom queries |
| **Systems Thinker** | Org Design, Transformation | Feedback loop identification, leverage points |

---

## 2. SYSTEM ARCHITECTURE (Elements, Connections, Purpose)

### 2.1 System Decomposition

Following Donella Meadows' framework, the system is decomposed into:

```
PURPOSE → ELEMENTS → CONNECTIONS → FUNCTION
```

#### System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFORCE TWIN SYSTEM                        │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ OBSERVE  │──▶│ ANALYZE  │──▶│ SIMULATE │──▶│  DECIDE  │    │
│  │          │   │          │   │          │   │          │    │
│  │Dashboard │   │Explorer  │   │Simulation│   │Compare   │    │
│  │Explorer  │   │Graph     │   │Chat AI   │   │Chat AI   │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       ▲                                              │         │
│       └──────────── FEEDBACK LOOP ◀──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Subsystem Details

#### Subsystem 1: Command Center (Dashboard)
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Real-time organizational health at a glance |
| **Stocks** | Headcount, skill inventory, capacity |
| **Flows** | Hiring rate, attrition rate, reskilling velocity |
| **Feedback Loops** | Workload → burnout → attrition → more workload (reinforcing) |
| **Key Metrics** | 8 KPIs: Efficiency Index, Risk Score, Automation Potential, Headcount, Attrition, Open Roles, Avg Tenure, Skill Coverage |
| **Drill-Down** | Each metric card → trend graph → causal explanation |
| **Charts** | ComposedChart (workload trajectory + AI projection), AreaChart (trends) |

#### Subsystem 2: Current State Explorer
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Fractal navigation of organizational hierarchy |
| **Structure** | Function → Sub-Function → Family → Role → Task |
| **Interaction** | Click any level to drill down; breadcrumb navigation up |
| **Detail Tabs** | Overview, Skills, Workload, Tasks |
| **Charts per Level** | BarChart (skills), AreaChart (workload over time), progress bars (task completion) |
| **Explainability** | Every metric links to its source data and calculation method |

#### Subsystem 3: Graph Topology (Network View)
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Reveal hidden connections, dependencies, and bottlenecks |
| **Levels** | Function (6 nodes) → Sub-Function (25) → Family (40) → Role (60) |
| **Metrics** | Node centrality, edge density, cluster membership |
| **Analysis Panels** | Centrality Ranking, Cross-Function Connectivity (Radar), Skill Clusters (Pie) |
| **Critical Feature** | Dependency Chain visualization — shows cascading failure paths |
| **Interaction** | Click node → detail panel with roles, connections, automation %, cluster |

#### Subsystem 4: Simulation Hub
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Test "what-if" scenarios before real-world execution |
| **Parameters** | Sliders for: workforce size change, AI adoption rate, reskilling budget, attrition modifier |
| **Scenarios** | Pre-built: AI Augmentation Wave, Reskilling Initiative, Restructuring, Market Expansion |
| **Results Tabs** | Timeline, Functions, Roles, Skills |
| **Explainability Panel** | First-Order Effects → Second-Order Effects → System Feedback Loops |
| **Causal Model** | Reinforcing loops (more AI → more data → better AI), Balancing loops (automation → anxiety → attrition) |

#### Subsystem 5: Workflow Builder
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Visual process flow editor with bottleneck detection and automation opportunity analysis |
| **Workflows** | Pre-built: Hiring Pipeline, Performance Review Cycle, Employee Offboarding |
| **Flow Visualization** | Animated step-by-step process diagram with connectors, color-coded by status (normal, bottleneck, automated) |
| **Step Metrics** | Duration (days), cost ($), ownership, automation potential (%) per step |
| **Bottleneck Detection** | Steps exceeding SLA thresholds trigger pulsing alerts; impact panel quantifies downstream delays and ROI from AI intervention |
| **Analytics** | RadarChart (efficiency dimensions: Speed, Scalability, Compliance), AreaChart (throughput vs. capacity) |
| **Step Inspector** | Context-aware sidebar with task decomposition and AI-driven reskilling recommendations |
| **Interaction** | Tab-based workflow selection → click step → inspector panel with deep metrics |

#### Subsystem 6: Scenario Comparison
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Side-by-side quantitative comparison of simulated futures |
| **Comparison Axes** | Efficiency, Cost, Risk, Timeline, Skill Coverage |
| **Verdict System** | Winner badges per dimension with quantified deltas |
| **Charts** | BarChart (metric comparison), RadarChart (multi-dimensional overlay) |

#### Subsystem 7: Twin AI (Chat)
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Natural language interface to the digital twin |
| **Capabilities** | Query data, request analysis, generate charts inline |
| **Inline Charts** | Bar, Radar, Pie charts rendered directly in chat responses |
| **Suggested Queries** | Context-aware prompts based on current system state |

---

## 3. DESIGN PRINCIPLES

### 3.1 Foundational Principles

| # | Principle | Rationale | Implementation |
|---|-----------|-----------|----------------|
| 1 | **Explainability First** | Users must trust the system to act on it | Every metric has a drill-down; every prediction shows its causal chain |
| 2 | **Fractal Consistency** | Same patterns at every zoom level | Dashboard → Explorer → Role all use identical card/chart patterns |
| 3 | **Progressive Disclosure** | Don't overwhelm; reveal on demand | Summary → click → detail → click → raw data |
| 4 | **Systems Over Snapshots** | Show dynamics, not just states | Feedback loops, trends, trajectories — never just a number |
| 5 | **Dark-First, Light-Ready** | Professional environments need both | Full dual-theme system with optimized palettes |
| 6 | **Data Density Without Clutter** | Analysts need information; leaders need clarity | Layered UI: glass cards provide visual separation without heavy borders |
| 7 | **Animation as Information** | Motion conveys state changes and relationships | Pulse = live; float = ambient; fade-in = new data; glow = attention |

### 3.2 Systems Thinking Principles (Meadows)

| Meadows Principle | Application in Workforce Twin |
|-------------------|-------------------------------|
| **Stocks & Flows** | Headcount is a stock; hiring/attrition are flows shown on Dashboard |
| **Feedback Loops** | Simulation Hub visualizes reinforcing and balancing loops |
| **Leverage Points** | Graph View identifies high-centrality nodes = leverage points |
| **Bounded Rationality** | Progressive disclosure respects cognitive limits |
| **Resilience** | Dependency chains show fragility; comparison shows alternatives |
| **Self-Organization** | Skill clusters emerge from network topology, not imposed hierarchy |

---

## 4. VISUAL DESIGN SYSTEM

### 4.1 Color Architecture

All colors are defined as HSL values in CSS custom properties, enabling seamless theme switching.

#### Dark Theme (Default — Mission Control)

| Token | HSL Value | Usage |
|-------|-----------|-------|
| `--background` | `222 47% 6%` | Page background — near-black with blue undertone |
| `--foreground` | `210 40% 96%` | Primary text — off-white for reduced glare |
| `--card` | `222 47% 9%` | Card surfaces — slightly elevated from background |
| `--primary` | `187 94% 43%` | Cyan accent — data highlights, active states, links |
| `--accent` | `265 80% 60%` | Violet — secondary accent for gradients and emphasis |
| `--muted-foreground` | `215 20% 55%` | Secondary text — labels, descriptions |
| `--border` | `222 30% 16%` | Subtle borders — glass edge definition |
| `--success` | `160 84% 39%` | Green — positive metrics, growth indicators |
| `--warning` | `38 92% 50%` | Amber — caution states, medium risk |
| `--destructive` | `0 72% 51%` | Red — high risk, negative trends, errors |

#### Light Theme (High Contrast)

| Token | HSL Value | Usage |
|-------|-----------|-------|
| `--background` | `220 20% 97%` | Cool off-white — reduces eye strain |
| `--foreground` | `222 47% 8%` | Near-black — maximum text readability |
| `--card` | `0 0% 100%` | Pure white cards — clean separation |
| `--primary` | `187 100% 30%` | Deeper cyan — maintains contrast on white |
| `--accent` | `265 85% 48%` | Deeper violet — legible on light backgrounds |
| `--muted-foreground` | `215 20% 40%` | Medium gray — clear secondary text |
| `--border` | `220 16% 82%` | Defined borders — stronger than dark theme |
| `--success` | `152 80% 28%` | Deeper green — passes WCAG AA |
| `--warning` | `32 95% 40%` | Deeper amber — readable on white |
| `--destructive` | `0 80% 45%` | Deeper red — accessible contrast |

#### Chart Palette (5-Color System)

| Token | Dark HSL | Light HSL | Semantic Use |
|-------|----------|-----------|-------------|
| `--chart-1` | `187 94% 43%` | `199 90% 38%` | Primary data series / Cyan-Teal |
| `--chart-2` | `265 80% 60%` | `270 70% 50%` | Secondary series / Violet |
| `--chart-3` | `160 84% 39%` | `152 75% 30%` | Tertiary series / Green |
| `--chart-4` | `38 92% 50%` | `28 90% 42%` | Quaternary series / Amber |
| `--chart-5` | `340 75% 55%` | `345 80% 45%` | Quinary series / Rose |

### 4.2 Typography System

| Element | Font | Weight | Size | Tracking | Usage |
|---------|------|--------|------|----------|-------|
| **Page Title** | Inter | 700 (Bold) | `text-xl` (20px) | `tracking-tight` | Page headers with gradient text |
| **Section Header** | Inter | 600 (Semibold) | `text-sm` (14px) | Default | Card titles, panel headers |
| **Body Text** | Inter | 400 (Regular) | `text-sm` (14px) | Default | Descriptions, paragraphs |
| **Label** | Inter | 500 (Medium) | `text-xs` (12px) | `tracking-widest uppercase` | Metric labels (`stat-label` class) |
| **Caption** | Inter | 400 (Regular) | `text-[10px]` (10px) | Default | Chart legends, footnotes |
| **Stat Value** | JetBrains Mono | 700 (Bold) | `text-3xl` (30px) | `tracking-tight` | KPI numbers (`stat-value` class) |
| **Data/Code** | JetBrains Mono | 400–500 | `text-xs` (12px) | Default | Inline data, monospace values |
| **Live Indicator** | JetBrains Mono | 400 | `text-xs` (12px) | Default | "LIVE" badge in header |

#### Font Loading
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
```

### 4.3 Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--radius` | `0.75rem` (12px) | Default border radius for cards |
| `p-5` | 20px | Standard card padding |
| `p-6` | 24px | Main content area padding |
| `gap-4` | 16px | Standard grid gap |
| `gap-6` | 24px | Section spacing |
| `max-w-[1400px]` | 1400px | Content max-width |
| Grid: `grid-cols-4` | 4-column | Dashboard KPI layout |
| Grid: `lg:grid-cols-4` | Responsive | Graph view (3+1 sidebar) |
| Grid: `md:grid-cols-3` | Responsive | Analysis panels |
| Grid: `md:grid-cols-2` | Responsive | Comparison, dependencies |

### 4.4 Elevation & Glass System

The glassmorphism system creates depth without heavy shadows:

| Class | Properties (Dark) | Properties (Light) | Usage |
|-------|-------------------|---------------------|-------|
| `.glass` | `bg-card/60 backdrop-blur-xl border-border/50` | `bg-card/80 backdrop-blur-xl border-border shadow-sm` | Standard card surface |
| `.glass-strong` | `bg-card/80 backdrop-blur-2xl border-border/60` | `bg-card/90 backdrop-blur-xl border-border shadow-sm` | Overlays, tooltips, floating panels |
| `.glow-border` | `box-shadow: 0 0 0 1px primary/0.2, 0 0 20px -5px primary/0.15` | `box-shadow: 0 0 0 1px primary/0.3, 0 0 12px -3px primary/0.1` | Active states, selected items |
| `.grid-pattern` | 40px grid lines at `border/0.3` opacity | Same | Page background texture |

### 4.5 Gradients

| Class | Definition | Usage |
|-------|-----------|-------|
| `.gradient-primary` | `linear-gradient(135deg, primary, accent)` | Brand elements, logo badge |
| `.gradient-text` | Same gradient + `bg-clip-text text-transparent` | Emphasized text in headings |
| `.gradient-surface` | `linear-gradient(180deg, card, background)` | Subtle surface differentiation |

---

## 5. ANIMATION SYSTEM

### 5.1 Philosophy
Animation serves three purposes:
1. **State indication** — pulse/glow = live/active
2. **Spatial orientation** — slide/fade = entry direction implies origin
3. **Data revelation** — stagger = sequential data loading

### 5.2 Animation Catalog

| Animation | Implementation | Duration | Easing | Usage |
|-----------|---------------|----------|--------|-------|
| **Card Entry** | `framer-motion: opacity 0→1, y 20→0` | 500ms | `easeOut` | All GlassCards on mount |
| **Stagger Entry** | `delay: index * 50ms` | 500ms + stagger | `easeOut` | Lists, grid items |
| **Pulse Glow** | `@keyframes pulseGlow` (box-shadow cycle) | 3s | `ease-in-out infinite` | Active/highlighted cards |
| **Float** | `@keyframes float` (translateY 0→-10→0) | 6s | `ease-in-out infinite` | Ambient decorative elements |
| **Fade In** | `@keyframes fade-in` (opacity + translateY) | 400ms | `ease-out` | Generic enter animation |
| **Scale In** | `@keyframes scale-in` (scale 0.95→1) | 300ms | `ease-out` | Modals, popovers |
| **Slide In Right** | `@keyframes slide-in-right` (translateX 100%→0) | 300ms | `ease-out` | Sidebar panels |
| **Animated Counter** | `AnimatedCounter: requestAnimationFrame + easeOutExpo` | 1200ms (configurable) | `easeOutExpo` | KPI numbers, stat values — triggers on viewport entry via `useInView` |
| **Progress Bar Fill** | `framer-motion: width 0→n%` | 800ms | Default spring | Centrality bars, skill bars |
| **Tab Content Switch** | `AnimatePresence + motion.div` | 300ms | `easeOut` | Tab panel transitions |
| **Live Indicator** | `animate-pulse` (Tailwind built-in) | 2s | `ease-in-out infinite` | LIVE badge in header |

### 5.3 Framer Motion Patterns

```tsx
// Standard card entry
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5, delay, ease: "easeOut" }}
/>

// List item stagger
<motion.div
  initial={{ opacity: 0, x: 10 }}
  animate={{ opacity: 1, x: 0 }}
  transition={{ delay: 0.1 * index }}
/>

// Animated presence for conditional panels
<AnimatePresence>
  {isVisible && (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    />
  )}
</AnimatePresence>
```

---

## 6. COMPONENT ARCHITECTURE

### 6.1 Component Hierarchy

```
App
├── ThemeProvider (context: theme state + toggle)
├── AppLayout
│   ├── AppSidebar (navigation)
│   │   ├── SidebarHeader (logo + brand)
│   │   ├── SidebarContent (NavLinks)
│   │   └── SidebarFooter (collapse toggle)
│   ├── Header (page title + live indicator + theme toggle)
│   └── <Outlet> (page content)
│       ├── Dashboard (KPIs + charts)
│       ├── Explorer (fractal hierarchy)
│       ├── GraphView (network topology)
│       ├── Workflows (process flow editor)
│       ├── Simulation (what-if scenarios)
│       ├── Compare (scenario comparison)
│       └── Chat (AI assistant)
├── Toaster (notifications)
└── Sonner (toast notifications)
```

### 6.2 Shared Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| `GlassCard` | `GlassCard.tsx` | `children, className, glow, delay` | Animated glass container — the atomic building block |
| `MetricCard` | `MetricCard.tsx` | `label, value, change, changeType, icon, delay` | KPI display with animated counter and trend indicator |
| `AnimatedCounter` | `AnimatedCounter.tsx` | `value, duration, prefix, suffix, decimals, className, separator` | Viewport-triggered count-up animation with easeOutExpo easing |
| `MiniGraph` | `MiniGraph.tsx` | `width, height, nodeCount` | Canvas-based animated network visualization |
| `NavLink` | `NavLink.tsx` | `to, end, className, activeClassName` | Router-aware navigation link with active styling |
| `ThemeProvider` | `ThemeProvider.tsx` | `children` | Theme context provider with toggle and persistence |

### 6.3 UI Primitives (shadcn/ui)

All primitives from `src/components/ui/` follow Radix UI patterns:

| Category | Components |
|----------|-----------|
| **Layout** | Card, Separator, Tabs, Accordion, Collapsible, Resizable |
| **Navigation** | Sidebar, Navigation Menu, Breadcrumb, Pagination |
| **Forms** | Input, Textarea, Select, Checkbox, Radio Group, Switch, Slider, Calendar, DatePicker |
| **Feedback** | Toast, Sonner, Alert, Progress, Skeleton, Badge |
| **Overlay** | Dialog, Sheet, Drawer, Popover, Hover Card, Tooltip, Dropdown Menu, Context Menu |
| **Data** | Table, Chart (Recharts wrapper) |

---

## 7. DATA VISUALIZATION STANDARDS

### 7.1 Chart Library: Recharts

All charts use `recharts` with `ResponsiveContainer` for fluid sizing.

### 7.2 Chart Type Selection Guide

| Data Type | Chart | Recharts Component | When to Use |
|-----------|-------|-------------------|-------------|
| Trend over time | Area/Line | `AreaChart`, `LineChart` | Workload trajectories, hiring trends |
| Comparison | Bar | `BarChart` | Skill levels, scenario metrics |
| Composition | Pie/Donut | `PieChart` with `innerRadius` | Skill clusters, role distribution |
| Multi-dimensional | Radar | `RadarChart` | Cross-function connectivity, balanced scorecard |
| Combined | Composed | `ComposedChart` (Area + Bar + Line) | Projected vs actual with overlay |
| Network | Custom SVG | `MiniGraph` component | Organizational topology |

### 7.3 Chart Styling Rules

```tsx
// Tooltip — always use custom glass tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null;
  return (
    <div className="glass-strong rounded-md px-3 py-2 text-xs font-mono">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
};

// Axis styling
<XAxis
  dataKey="name"
  tick={{ fill: "hsl(215, 20%, 55%)", fontSize: 10 }}
  axisLine={false}
  tickLine={false}
/>

// Grid — use theme-aware stroke
<CartesianGrid strokeDasharray="3 3" stroke="hsl(222, 30%, 16%)" />

// Gradient fills for area charts
<defs>
  <linearGradient id="primaryGradient" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stopColor="hsl(187, 94%, 43%)" stopOpacity={0.3} />
    <stop offset="100%" stopColor="hsl(187, 94%, 43%)" stopOpacity={0} />
  </linearGradient>
</defs>
```

---

## 8. INTERACTION PATTERNS

### 8.1 Navigation Model

| Pattern | Implementation | Example |
|---------|---------------|---------|
| **Global Navigation** | Sidebar with collapsible icon mode | 6 primary routes |
| **Fractal Drill-Down** | Click item → expand detail panel/tabs | Explorer hierarchy |
| **Tabs** | `Tabs` + `TabsList` + `TabsTrigger` | Simulation results, Explorer details |
| **Selection** | Click to select → detail panel appears | Graph View node selection |
| **Hover** | Tooltip with data preview | Chart data points |

### 8.2 State Indicators

| State | Visual Treatment |
|-------|-----------------|
| **Active/Selected** | `bg-primary/10 text-primary glow-border` |
| **Hover** | `hover:bg-secondary hover:text-foreground` |
| **Live/Real-time** | `animate-pulse` on Activity icon + "LIVE" text |
| **Loading** | Skeleton components with pulse animation |
| **High Risk** | `text-destructive border-destructive/30` badge |
| **Medium Risk** | `text-warning border-warning/30` badge |
| **Success/Positive** | `text-success` values |

---

## 9. ROUTING & PAGE STRUCTURE

### 9.1 Route Map

| Path | Component | Page Title | Icon |
|------|-----------|------------|------|
| `/` | `Dashboard` | Command Center | `LayoutDashboard` |
| `/explorer` | `Explorer` | Current State Explorer | `Eye` |
| `/graph` | `GraphView` | Graph View | `Network` |
| `/simulation` | `Simulation` | Simulation Hub | `FlaskConical` |
| `/compare` | `Compare` | Scenario Comparison | `GitCompare` |
| `/workflows` | `Workflows` | Workflow Builder | `Workflow` |
| `/chat` | `Chat` | Twin AI | `MessageCircle` |
| `*` | `NotFound` | 404 | — |

### 9.2 Page Layout Template

Every page follows this structure:

```tsx
<div className="space-y-6 max-w-[1400px] mx-auto">
  {/* 1. Page header with icon + title + controls */}
  <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
    <h2 className="text-xl font-bold flex items-center gap-2">
      <Icon className="h-5 w-5 text-primary" />
      <span>Title <span className="gradient-text">Accent</span></span>
    </h2>
    <p className="text-xs text-muted-foreground mt-1">Description</p>
  </motion.div>

  {/* 2. KPI row (if applicable) */}
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    <MetricCard ... />
  </div>

  {/* 3. Primary content area */}
  <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
    <GlassCard glow>Main visualization</GlassCard>
    <GlassCard>Side panel</GlassCard>
  </div>

  {/* 4. Analysis panels */}
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    <GlassCard delay={0.1}>Panel 1</GlassCard>
    <GlassCard delay={0.15}>Panel 2</GlassCard>
    <GlassCard delay={0.2}>Panel 3</GlassCard>
  </div>
</div>
```

---

## 10. TECHNOLOGY STACK

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | React 18 | Component model, concurrent features |
| **Build** | Vite | Fast HMR, optimized builds |
| **Language** | TypeScript | Type safety across the system |
| **Routing** | React Router v6 | Declarative routing with nested layouts |
| **Styling** | Tailwind CSS + CSS custom properties | Utility-first with semantic tokens |
| **Components** | shadcn/ui (Radix primitives) | Accessible, composable UI primitives |
| **Animation** | Framer Motion | Declarative animations, AnimatePresence |
| **Charts** | Recharts | Composable chart components |
| **State** | React Query (TanStack) | Server state management |
| **Forms** | React Hook Form + Zod | Validated form handling |
| **Icons** | Lucide React | Consistent icon system (462+ icons) |
| **Theming** | Custom ThemeProvider + localStorage | Persistent light/dark mode |

---

## 11. ACCESSIBILITY STANDARDS

| Requirement | Implementation |
|-------------|----------------|
| **Color Contrast** | Light theme tokens pass WCAG AA (4.5:1 for text) |
| **Keyboard Navigation** | All Radix primitives support full keyboard nav |
| **Focus Indicators** | `--ring` token used for focus-visible outlines |
| **Screen Readers** | Semantic HTML (`<header>`, `<main>`, `<nav>`) |
| **Motion Sensitivity** | Animations use `prefers-reduced-motion` via Framer Motion |
| **Responsive** | Mobile-first grid system, collapsible sidebar |

---

## 12. FILE ORGANIZATION

```
src/
├── components/
│   ├── ui/              # shadcn/ui primitives (50+ components)
│   ├── AppLayout.tsx     # Root layout with header + sidebar
│   ├── AppSidebar.tsx    # Navigation sidebar
│   ├── AnimatedCounter.tsx # Viewport-triggered count-up animation
│   ├── GlassCard.tsx     # Animated glass container
│   ├── MetricCard.tsx    # KPI display card with animated counter
│   ├── MiniGraph.tsx     # Canvas network visualization
│   ├── NavLink.tsx       # Active-aware navigation link
│   └── ThemeProvider.tsx # Theme context + toggle
├── pages/
│   ├── Dashboard.tsx     # Command Center
│   ├── Explorer.tsx      # Fractal hierarchy browser
│   ├── GraphView.tsx     # Network topology
│   ├── Simulation.tsx    # What-if scenario engine
│   ├── Compare.tsx       # Scenario comparison
│   ├── Workflows.tsx     # Visual process flow editor
│   ├── Chat.tsx          # AI assistant
│   ├── Index.tsx         # Landing/redirect
│   └── NotFound.tsx      # 404 page
├── hooks/
│   ├── use-mobile.tsx    # Responsive breakpoint hook
│   └── use-toast.ts      # Toast notification hook
├── lib/
│   └── utils.ts          # cn() utility for class merging
├── index.css             # Design tokens + utility classes
├── App.tsx               # Root component with routing
└── main.tsx              # Entry point
```

---

## 13. NAMING CONVENTIONS

| Domain | Convention | Example |
|--------|-----------|---------|
| **Components** | PascalCase | `GlassCard`, `MetricCard` |
| **Pages** | PascalCase | `Dashboard`, `GraphView` |
| **Files** | PascalCase for components, kebab-case for hooks | `GlassCard.tsx`, `use-mobile.tsx` |
| **CSS Classes** | kebab-case utilities | `.glass-strong`, `.glow-border` |
| **CSS Variables** | kebab-case with `--` prefix | `--primary`, `--chart-1` |
| **Props** | camelCase | `glow`, `activeClassName`, `nodeCount` |
| **Routes** | kebab-case | `/graph`, `/simulation` |
| **Constants** | camelCase arrays/objects | `navItems`, `nodeDetails` |

---

## 14. FUTURE EXTENSION POINTS

| Extension | Approach |
|-----------|----------|
| **Real Data** | Replace mock data with React Query + Lovable Cloud backend |
| **Authentication** | Add auth flow protecting all routes |
| **Real-time Updates** | WebSocket/SSE subscriptions for live dashboard |
| **Export** | PDF/CSV export of simulation results and comparisons |
| **Custom Scenarios** | User-defined simulation parameters stored in DB |
| **Collaboration** | Shared scenarios with commenting |
| **Workflow Builder** | ✅ Implemented — visual process flow editor with bottleneck detection |
| **Prediction Engine** | ML-powered forecasting via edge functions |

---

*This document is the single source of truth for all design and architecture decisions in the Workforce Twin platform. Every component, color, animation, and interaction pattern should be traceable back to the principles defined here.*
