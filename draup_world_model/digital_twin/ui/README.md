# Digital Twin UI - Beginner's Guide

> This guide is for developers new to web/UI development.
> It explains every concept from first principles so you can understand,
> set up, modify, and extend the Digital Twin user interface.

---

## Table of Contents

1. [What Is a Web UI? (First Principles)](#1-what-is-a-web-ui-first-principles)
2. [Tech Stack Explained](#2-tech-stack-explained)
3. [Setup & Running](#3-setup--running)
4. [How the Code Is Organized](#4-how-the-code-is-organized)
5. [The Server Side (Flask)](#5-the-server-side-flask)
6. [The Client Side (React)](#6-the-client-side-react)
7. [How Data Flows (End to End)](#7-how-data-flows-end-to-end)
8. [Each View Explained](#8-each-view-explained)
9. [Shared Components Library](#9-shared-components-library)
10. [How to Modify the UI](#10-how-to-modify-the-ui)
11. [Common Patterns](#11-common-patterns)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What Is a Web UI? (First Principles)

A web UI is a conversation between two programs:

```
┌──────────────┐           HTTP           ┌──────────────┐
│   Browser    │ ◄──── requests/json ────►│   Server     │
│  (React JS)  │                          │  (Flask/Py)  │
│              │  GET /api/dt/readiness    │              │
│  Renders     │ ──────────────────────►  │  Runs query  │
│  what the    │                          │  on Neo4j    │
│  user sees   │  ◄────── JSON ─────────  │  Returns     │
│              │  {readiness: {score: 75}} │  data        │
└──────────────┘                          └──────────────┘
```

**The server** (Flask) is a Python program that:
- Listens for HTTP requests on a port (default: 5001)
- Routes requests to the right handler function
- Talks to Neo4j to get data
- Returns JSON responses

**The client** (React in the browser) is a JavaScript program that:
- Makes HTTP requests to the server (using `fetch()`)
- Receives JSON data back
- Renders that data as HTML elements on screen
- Handles user interactions (clicks, form inputs, etc.)

### Why Separate Server and Client?

**Systems thinking**: The server is the *data gateway* - it knows how to talk to Neo4j and run simulations. The client is the *presentation layer* - it knows how to display data to humans. Separating them means you can change how things look without changing how things work (and vice versa).

---

## 2. Tech Stack Explained

### What Each Piece Does

| Technology | What | Why We Use It | Where It Comes From |
|-----------|------|--------------|-------------------|
| **Flask** | Python web server | Lightweight, simple, our codebase is already Python | `pip install flask` |
| **React 18** | JavaScript UI library | Lets us build interactive UIs with reusable components | CDN (unpkg.com) |
| **htm** | Template literals for React | Lets us write React components without a build step (no JSX compiler needed) | CDN (unpkg.com) |
| **Tailwind CSS** | Utility-first CSS framework | Style elements with classes (`bg-blue-500 text-white p-4`) instead of writing CSS files | CDN (cdn.tailwindcss.com) |
| **Chart.js** | Charting library | Renders bar charts, radar charts, line charts | CDN (cdn.jsdelivr.net) |

### What Is htm? (The Key Insight)

Normally, React uses **JSX** - a syntax that looks like HTML inside JavaScript:
```jsx
// JSX (requires build step to compile)
return <div className="card"><h1>{title}</h1></div>;
```

JSX requires a **build step** (Babel/webpack) to transform it into regular JavaScript. We don't want a build step for a prototype.

**htm** is an alternative that uses JavaScript's built-in [tagged template literals](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals):
```javascript
// htm (works natively in the browser, no build step)
return html`<div class="card"><h1>${title}</h1></div>`;
```

The key differences from JSX:
- Use `html` backtick template instead of JSX syntax
- Use `class=` instead of `className=`
- Use `${expression}` instead of `{expression}`
- Use `onClick=${handler}` instead of `onClick={handler}`

### What Is Tailwind CSS?

Instead of writing CSS in separate files:
```css
/* Traditional CSS */
.card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }
```

You use utility classes directly on elements:
```html
<!-- Tailwind CSS -->
<div class="bg-white border border-gray-200 rounded-xl p-4">...</div>
```

Common Tailwind classes you'll see in this codebase:
| Class | Meaning |
|-------|---------|
| `bg-blue-500` | Background color: blue, shade 500 (medium) |
| `text-white` | Text color: white |
| `p-4` | Padding: 1rem (16px) on all sides |
| `px-3 py-2` | Padding: 0.75rem horizontal, 0.5rem vertical |
| `rounded-xl` | Border radius: extra-large (12px) |
| `border border-gray-200` | 1px border, light gray color |
| `flex items-center gap-2` | Flexbox, centered vertically, 0.5rem gap |
| `grid grid-cols-2 md:grid-cols-4` | 2 columns on mobile, 4 on medium+ screens |
| `text-sm` | Small text (14px) |
| `font-bold` | Bold text |
| `hover:bg-gray-50` | On hover: light gray background |
| `transition` | Smooth CSS transitions |

---

## 3. Setup & Running

### Prerequisites

```bash
# 1. Flask must be installed
pip install flask

# 2. Neo4j must be running and loaded with data
#    (See Phase 1 and Phase 2 in DOCUMENTATION.md)

# 3. Environment variables must be set
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
```

### Starting the Server

```bash
# Default port (5001)
python -m draup_world_model.digital_twin.ui.app

# Custom port
DT_UI_PORT=8080 python -m draup_world_model.digital_twin.ui.app
```

### What Happens When You Start

1. Flask creates the app (`create_app()` in `app.py`)
2. It connects to Neo4j (`get_dt_neo4j_connection()` — isolated from production)
3. It initializes the API (`init_api(conn)`) which creates a `ScenarioManager`
4. It registers the API blueprint (all `/api/dt/*` routes)
5. It starts listening on port 5001
6. When you open `http://localhost:5001`, Flask serves `index.html`
7. The browser loads React, htm, Tailwind, Chart.js from CDN
8. The browser loads our JS files: `components.js`, all views, `app.js`
9. `app.js` mounts the React application into `<div id="root">`
10. The Dashboard view loads and makes API calls to show data

### Verifying It Works

1. Open `http://localhost:5001` in your browser
2. You should see the Dashboard with a "Data Readiness" score
3. Try clicking "Explore Taxonomy" to navigate the org structure
4. Try clicking "Run Simulation" to configure a simulation

---

## 4. How the Code Is Organized

```
ui/
├── __init__.py              # Empty package init
├── app.py                   # Flask application (entry point)
├── api.py                   # REST API endpoints (Flask Blueprint)
├── templates/
│   └── index.html           # HTML shell (loads all JS from CDN + static)
└── static/js/
    ├── components.js         # Shared components + API helper + formatters
    ├── app.js               # Main app: navigation, routing, layout
    └── views/
        ├── Dashboard.js     # Dashboard view
        ├── Explorer.js      # Taxonomy tree view
        ├── Simulator.js     # Simulation config + run
        ├── Results.js       # Results display (6 tabs)
        └── Comparison.js    # Multi-scenario comparison
```

### Script Loading Order (matters!)

In `index.html`, scripts are loaded in this order:
```html
<!-- 1. External libraries (from CDN) -->
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://unpkg.com/react@18/..."></script>
<script src="https://unpkg.com/react-dom@18/..."></script>
<script src="https://unpkg.com/htm@3/..."></script>

<!-- 2. Our shared code (must come before views) -->
<script src="/static/js/components.js"></script>

<!-- 3. Views (each registers on window.DT) -->
<script src="/static/js/views/Dashboard.js"></script>
<script src="/static/js/views/Explorer.js"></script>
<script src="/static/js/views/Simulator.js"></script>
<script src="/static/js/views/Results.js"></script>
<script src="/static/js/views/Comparison.js"></script>

<!-- 4. Main app (uses views, must come last) -->
<script src="/static/js/app.js"></script>
```

**Why does order matter?** Each script builds on the previous ones:
- `components.js` sets up `window.DT` with shared utilities
- Each view reads from `window.DT` and adds itself (e.g., `window.DT.Dashboard = Dashboard`)
- `app.js` reads all views from `window.DT` and builds the router

---

## 5. The Server Side (Flask)

### app.py - The Entry Point

```python
def create_app() -> Flask:
    # 1. Create Flask instance
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # 2. Register API routes (/api/dt/*)
    app.register_blueprint(dt_api)

    # 3. Connect to Neo4j (uses DT_NEO4J_* env vars, NOT production)
    conn = get_dt_neo4j_connection()
    init_api(conn)  # Gives the API a database connection

    # 4. Serve the SPA for all non-API routes
    @app.route("/")
    @app.route("/dt")
    @app.route("/dt/<path:path>")
    def serve_spa(path=""):
        return render_template("index.html")

    return app
```

**Key concept**: Flask serves `index.html` for *any* URL that isn't an API call. This is called a **Single-Page Application (SPA)** pattern - the browser handles navigation client-side.

### api.py - The API Layer

The API is a Flask Blueprint - a group of related routes. It wraps the simulation engine:

```python
dt_api = Blueprint("dt_api", __name__, url_prefix="/api/dt")

# All routes start with /api/dt/
# e.g., /api/dt/readiness, /api/dt/simulate, etc.
```

The API initializes with a Neo4j connection and creates a `ScenarioManager`:
```python
def init_api(neo4j_conn):
    global _neo4j_conn, _scenario_manager
    _neo4j_conn = neo4j_conn
    _scenario_manager = ScenarioManager(neo4j_conn)
```

Every endpoint follows the same pattern:
1. Parse request (URL params or JSON body)
2. Call the appropriate simulation/graph module
3. Return JSON response
4. Catch errors → return `{"error": "message"}` with status 500

---

## 6. The Client Side (React)

### How Components Work

A React component is a JavaScript function that returns HTML-like markup:

```javascript
function MetricCard({ label, value, color }) {
    return html`
        <div class="border rounded-xl p-4 bg-${color}-50">
            <span class="text-xs">${label}</span>
            <div class="text-2xl font-bold">${value}</div>
        </div>
    `;
}
```

You use it like an HTML tag:
```javascript
html`<${MetricCard} label="Headcount" value="2,500" color="blue" />`
```

### State Management (useState)

React components can have **state** - data that changes over time:

```javascript
function Counter() {
    const [count, setCount] = useState(0);  // Initial value: 0

    return html`
        <button onClick=${() => setCount(count + 1)}>
            Clicked ${count} times
        </button>
    `;
}
```

When `setCount` is called, React re-renders the component with the new value.

### Side Effects (useEffect)

To load data when a component first appears:

```javascript
function Dashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // This runs once when the component mounts
        api.get("/readiness")
            .then(d => { setData(d); setLoading(false); });
    }, []);  // Empty array = run once

    if (loading) return html`<${Spinner} />`;
    return html`<div>Score: ${data.readiness.total_score}</div>`;
}
```

### The window.DT Pattern

Since we don't have a module bundler, all components communicate through `window.DT`:

```javascript
// In components.js:
window.DT = { html, useState, useEffect, api, MetricCard, ... };

// In Dashboard.js:
const { html, useState, useEffect, api, MetricCard } = window.DT;
function Dashboard() { ... }
window.DT.Dashboard = Dashboard;  // Export back

// In app.js:
const { Dashboard, Explorer, Simulator, Results, Comparison } = window.DT;
```

This is a simple module pattern for prototype code. In a production app, you'd use ES modules or a bundler.

---

## 7. How Data Flows (End to End)

### Example: User Runs a Simulation

```
1. USER clicks "Run Simulation" button in Simulator view

2. BROWSER JavaScript:
   const result = await api.post("/simulate", {
       type: "tech_adoption",
       scope_name: "Claims Management",
       parameters: { technology_name: "Microsoft Copilot" },
       timeline_months: 36,
   });

3. BROWSER sends HTTP POST to Flask:
   POST /api/dt/simulate
   Content-Type: application/json
   {"type": "tech_adoption", "scope_name": "Claims Management", ...}

4. FLASK (api.py → run_simulation()):
   - Parses JSON body
   - Creates a ScenarioConfig dataclass
   - Calls manager.create_scenario(config)
   - Calls manager.run_scenario(scenario_id)

5. SCENARIO MANAGER:
   - ScopeSelector queries Neo4j for all roles/tasks in Claims
   - TechAdoptionSimulation matches tasks to Microsoft Copilot
   - CascadeEngine runs 8-step propagation
   - FinancialProjection computes savings/ROI
   - SkillsStrategy identifies sunrise/sunset skills

6. FLASK returns JSON:
   {
       "scenario_id": "scenario_1",
       "config": {"name": "Microsoft Copilot - Claims Management", ...},
       "result": {
           "cascade": {
               "task_changes": {...},
               "workload_changes": {...},
               "role_impacts": {...},
               "financial": {"gross_savings": 5200000, "roi_pct": 145.2, ...},
               "workforce": {"freed_headcount": 47.3, ...},
               "risks": {"flags": [...], ...},
           },
           "skills_strategy": {...},
           "recommendation": {"verdict": "RECOMMEND", ...},
       }
   }

7. BROWSER receives JSON, navigates to Results view:
   onNavigate("results", { scenarioId: "scenario_1", result: result.result });

8. RESULTS VIEW renders:
   - MetricCards for financial summary
   - DataTable for role impacts
   - Badge components for risk flags
   - Chart for financial breakdown
```

---

## 8. Each View Explained

### Dashboard (`views/Dashboard.js`)

**Purpose**: First thing the user sees. Shows the health of the digital twin.

**What it shows**:
- **Data Readiness Score**: 5 progress bars (Taxonomy, Role Decomposition, Skills, Enterprise Context, Validation) with a total score out of 100
- **Graph Overview**: Card grid showing how many nodes of each type exist (Functions, Roles, Tasks, Skills, etc.)
- **Quick Actions**: Three buttons - Role Redesign, Technology Adoption, Explore Taxonomy
- **Recent Scenarios**: List of previously run simulations with status badges

**API calls**: `GET /api/dt/readiness`, `GET /api/dt/scenarios`

### Explorer (`views/Explorer.js`)

**Purpose**: Navigate the organizational structure interactively.

**Layout**: Two-panel (left: tree, right: details)

**What it shows**:
- **Left panel**: Collapsible tree view
  - Organization → Function → SubFunction → JobFamilyGroup → JobFamily
  - Click to expand/collapse, click to select
  - Shows headcount next to function names
- **Right panel**: Details for the selected node
  - If a Function is selected: loads scope data from API
  - Shows MetricCards: role count, headcount, task count, skill count
  - Shows DataTables: roles with headcount, tasks with automation levels

**API calls**: `GET /api/dt/taxonomy` (tree), `GET /api/dt/scope/function/{name}` (details)

### Simulator (`views/Simulator.js`)

**Purpose**: Configure simulation parameters and run.

**What it shows**:
- **Simulation Type**: Two cards - "Role Redesign" and "Technology Adoption"
- **Scope**: Dropdown of all functions (loaded from API)
- **Parameters**:
  - *Role Redesign*: Automation factor slider (0.1 to 1.0)
  - *Tech Adoption*: Technology profile gallery (6 pre-built profiles with badges)
- **Timeline**: Slider (12 to 60 months)
- **Scenario Name**: Optional text input
- **Run Button**: Sends POST to `/api/dt/simulate`, shows "Running Cascade..." animation

**After run**: Auto-navigates to Results view with the simulation output.

**API calls**: `GET /api/dt/functions`, `GET /api/dt/technologies`, `POST /api/dt/simulate`

### Results (`views/Results.js`)

**Purpose**: Display the full cascade results from a simulation.

**What it shows** (6 tabs):

1. **Overview Tab**: 8 MetricCards (tasks affected, roles affected, freed headcount, reduction %, gross savings, net impact, ROI, payback). Plus technology recommendation if applicable.

2. **Financial Tab**: MetricCards (gross savings, total cost, net impact, ROI). Bar chart showing savings vs costs breakdown. Per-title impact DataTable (job title, headcount, avg salary, freed %, savings). Cost breakdown cards (licensing, implementation, reskilling).

3. **Workforce Tab**: MetricCards (current headcount, freed headcount, reduction %, redeployable). Role impact DataTable with transformation index progress bars.

4. **Skills Tab**: MetricCards (sunrise/sunset skill counts, high-risk skills, reskilling cost). Sunrise skills badges (green). Sunset skills badges (red). Build-vs-buy recommendations table.

5. **Risks Tab**: MetricCards (total risk flags, high severity). Risk flag cards with severity badges, type, detail, and entity.

6. **Details Tab**: Cascade trace (visual 7-step flow with counts). Task reclassification table (from → to with automation delta). Workload shift table.

**API calls**: `GET /api/dt/scenarios/{id}` (if loaded by ID)

### Comparison (`views/Comparison.js`)

**Purpose**: Compare 2+ scenarios side-by-side.

**What it shows**:
- **Scenario Selector**: Checkbox list of all completed scenarios
- **Compare Button**: Sends selected IDs to API
- **After comparison**:
  - Best-by-ROI and Lowest-risk MetricCards
  - **Radar Chart**: 5-dimensional comparison (ROI, Savings, Low Risk, Low HC Cut, Skills Gap)
  - **Financial Comparison Table**: Side-by-side metrics with best value highlighted
  - **Workforce Comparison Table**: Freed headcount, reduction %, redeployable
  - **Risk Comparison Table**: Total risks, high risks with badges

**API calls**: `GET /api/dt/scenarios`, `POST /api/dt/compare`

---

## 9. Shared Components Library

All reusable components live in `components.js`:

### api (API Helper)
```javascript
// GET request
const data = await api.get("/readiness");

// POST request
const result = await api.post("/simulate", { type: "role_redesign", ... });

// DELETE request
await api.del("/scenarios/scenario_1");
```

### MetricCard
```javascript
html`<${MetricCard}
    label="Gross Savings"      // Small uppercase label
    value=${fmt.currency(val)} // Large bold value
    sub="3-year projection"    // Optional subtitle
    icon="$"                   // Optional icon
    color="green"              // blue|green|amber|red|purple|indigo|slate
    onClick=${handler}         // Optional click handler
/>`
```

### Badge
```javascript
html`<${Badge} text="human_led" color="gray" />`
// Colors: gray, blue, green, amber, red, purple
```

### ProgressBar
```javascript
html`<${ProgressBar} value=${75} max=${100} label="Skills" color="green" />`
```

### Spinner
```javascript
html`<${Spinner} text="Loading..." />`
```

### ErrorBox
```javascript
html`<${ErrorBox} message="Something went wrong" onRetry=${retryFn} />`
```

### DataTable
```javascript
html`<${DataTable}
    columns=${[
        { key: "name", label: "Role Name" },
        { key: "headcount", label: "HC", render: r => fmt.number(r.headcount) },
    ]}
    rows=${data}
    onRowClick=${row => console.log(row)}
/>`
```

### ChartCanvas (Chart.js wrapper)
```javascript
html`<${ChartCanvas}
    type="bar"
    data=${{ labels: [...], datasets: [...] }}
    options=${{ plugins: { legend: { display: false } } }}
    height="300px"
/>`
```

### fmt (Formatters)
```javascript
fmt.currency(5200000)  // → "$5.2M"
fmt.currency(45000)    // → "$45K"
fmt.pct(14.5)          // → "14.5%"
fmt.number(2500)       // → "2,500"
fmt.severity("high")   // → "red" (color for badges)
```

---

## 10. How to Modify the UI

### Adding a New MetricCard to the Dashboard

1. Open `views/Dashboard.js`
2. Find the "Graph Overview" section (the grid of MetricCards)
3. Add a new card:
```javascript
html`<${MetricCard} label="My Metric" value="42" color="purple" />`
```

### Adding a New Tab to Results

1. Open `views/Results.js`
2. Add to the `tabs` array:
```javascript
const tabs = [
    ...existing tabs...,
    { id: "mytab", label: "My Tab" },
];
```
3. Add the tab content:
```javascript
${activeTab === "mytab" && html`<div>My tab content</div>`}
```

### Adding a New API Endpoint

1. Open `api.py`
2. Add a new route:
```python
@dt_api.route("/my-endpoint")
def my_endpoint():
    conn = _get_conn()
    result = conn.execute_read_query("MATCH (n:DTRole) RETURN count(n) AS c")
    return jsonify({"count": result[0]["c"]})
```
3. Call it from JavaScript:
```javascript
const data = await api.get("/my-endpoint");
```

### Adding a New View

1. Create `views/MyView.js`:
```javascript
(function () {
    const { html, useState, useEffect, api, SectionHeader } = window.DT;

    function MyView({ onNavigate }) {
        return html`
            <div class="fade-in">
                <${SectionHeader} title="My New View" />
                <p>Content goes here</p>
            </div>
        `;
    }

    window.DT.MyView = MyView;
})();
```
2. Add the script tag to `index.html` (before `app.js`)
3. Add to `app.js` NAV_ITEMS and the switch statement

---

## 11. Common Patterns

### Loading Data Pattern
```javascript
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

const load = () => {
    setLoading(true);
    setError(null);
    api.get("/endpoint")
        .then(d => { setData(d); setLoading(false); })
        .catch(e => { setError(e.message); setLoading(false); });
};

useEffect(load, []);  // Load on mount

if (loading) return html`<${Spinner} text="Loading..." />`;
if (error) return html`<${ErrorBox} message=${error} onRetry=${load} />`;
```

### Navigation Pattern
```javascript
// Navigate to another view
onNavigate("results", { scenarioId: "abc123" });

// Receive navigation params
function Results({ scenarioId, result, config, onNavigate }) {
    // scenarioId comes from navigation
}
```

### Conditional Rendering
```javascript
// Show component only if data exists
${data && html`<${MetricCard} label="Score" value=${data.score} />`}

// Toggle between states
${loading
    ? html`<${Spinner} />`
    : html`<div>Content</div>`
}
```

---

## 12. Troubleshooting

### "Blank page / nothing renders"
- Open browser DevTools (F12) → Console tab
- Look for JavaScript errors (red text)
- Common cause: a syntax error in one of the JS files prevents all subsequent scripts from loading
- Try loading `http://localhost:5001/static/js/components.js` directly - if it returns a Python error, Flask isn't serving static files correctly

### "API calls fail with 500"
- Check the Flask terminal for error messages
- Common cause: Neo4j isn't connected or has no data
- Try: `curl http://localhost:5001/api/dt/readiness` to see the raw error

### "Charts don't render"
- Check that Chart.js loaded: in browser console, type `Chart` - it should be defined
- Check that the canvas element exists in the DOM
- Common cause: the data format doesn't match what Chart.js expects

### "Tailwind styles not working"
- Check that the CDN script loaded: look for `tailwindcss` in the Network tab (F12)
- Some ad blockers block CDN scripts - try disabling

### "Components show undefined"
- Check the script loading order in `index.html`
- Every view script must come AFTER `components.js` and BEFORE `app.js`
- In console, check: `window.DT.Dashboard` should be a function
