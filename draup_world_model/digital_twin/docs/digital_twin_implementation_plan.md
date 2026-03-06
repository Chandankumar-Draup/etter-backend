# Etter Digital Twin: Implementation Architecture & Detailed Plan
# Version 1.0 — February 2026

*Classification: Engineering Architecture Document*
*Companion to: digital_twin_comprehensive_v2.1 (Exploration) + digital_twin_addendum_v0.3 (Data Mapping)*
*Audience: Engineering Team + CEO Vijay*

---

> **Implementation Thesis:** The Digital Twin is not a new system to build from scratch — it is a *composition layer* that connects existing Etter outputs into a unified graph where traversal reveals emergent properties no single API can. The 80/20 rule applies: Etter already produces ~80% of the data. The gap is graph composition, simulation generalization, and feedback loops.

---

# PART I: SYSTEMS THINKING ANALYSIS

## 1. First Principles Decomposition

Before writing a single line of architecture, we must decompose what we're actually building into irreducible atoms.

### What is a Digital Twin, reduced to first principles?

A Digital Twin is a system with exactly three properties:

1. **Representation** — A model that mirrors a real-world entity (the organization's workforce)
2. **Simulation** — The ability to project forward from the current state given hypothetical inputs
3. **Feedback** — A mechanism to compare predictions against reality and recalibrate

If any one of these is missing, you don't have a twin. You have a dashboard (no simulation), a simulator (no feedback), or a disconnected model (no representation fidelity).

### Irreducible Atoms of Implementation

| Atom | What It Means Concretely | Exists Today? |
|------|--------------------------|---------------|
| A1: Connected Graph | All entities (roles, tasks, skills, etc.) linked in a single traversable structure | **No** — Etter outputs are separate API responses |
| A2: Scope Selection | Ability to "zoom" to any level of the taxonomy (org → function → role → task) | **Partial** — taxonomy exists but not queryable as graph |
| A3: Stimulus Engine | Apply a "what-if" (technology, restructuring, etc.) and propagate effects through the graph | **Partial** — financial simulator exists for headcount/cost curves |
| A4: Cascade Propagation | Effects at task level propagate up through workload → role → family → function → org | **No** — this is the core new capability |
| A5: Scenario Management | Create, store, compare, version simulation configurations and results | **No** — needs to be built |
| A6: Feedback Loop | Compare twin predictions against actual enterprise outcomes, recalibrate | **No** — Phase 3+ capability |

**Critical Insight:** Atoms A1 + A2 + A3 + A4 + A5 = Minimum Viable Twin. A6 turns it from a simulator into a true twin. Build A1-A5 first; A6 is the maturity layer.

---

## 2. Donella Meadows System Model

Using the *Thinking in Systems* framework, we define the system in terms of **stocks, flows, feedback loops, and leverage points**.

### 2.1 Stocks (What Accumulates)

| Stock | Description | Unit | Where It Lives |
|-------|------------|------|----------------|
| **Graph State** | Current snapshot of all entities and relationships | Nodes + Edges | Neo4j |
| **Intelligence Layer** | AI assessment scores, task classifications, skill mappings | Scores per role | Neo4j (from Etter APIs) |
| **Scenario Library** | All simulation configurations and results | Scenario objects | PostgreSQL + Neo4j |
| **Validation Pool** | Human-validated scores that anchor the model | Locked score versions | Neo4j |
| **Cross-Client Corpus** | Anonymized patterns from all clients (Phase 4+) | Pattern library | Separate graph partition |

### 2.2 Flows (What Changes Stocks)

**Inflows (data entering the system):**
- Enterprise HRIS data → Graph State (taxonomy, headcount, salary)
- Etter Assessment pipeline → Intelligence Layer (scores, tasks, workloads)
- Etter Skills pipeline → Intelligence Layer (skills, sunrise/sunset)
- SME validation → Validation Pool (locked scores)
- Simulation runs → Scenario Library (results)

**Outflows (data leaving the system):**
- Simulation results → Enterprise decision-makers (reports, dashboards)
- Aggregated patterns → Cross-Client Corpus (anonymized)
- Drift alerts → Operations team (recalibration triggers)

**Processing Flows (internal transformations):**
- Stimulus → Cascade Propagation → Result Computation (the simulation engine)
- Graph Aggregation → Scope-level metrics (rolling up from task → org)
- Scenario Comparison → Trade-off Analysis (multi-scenario evaluation)

### 2.3 Feedback Loops

**Balancing Loop B1: Validation-Calibration**
```
Twin produces prediction → SME validates → 
Discrepancy detected → Score adjusted → 
Better prediction next time
```
*Type: Balancing (self-correcting)*
*Delay: Days to weeks (validation cycle time)*
*Leverage: Reduce validation cycle time = faster convergence*

**Balancing Loop B2: Drift Detection**
```
Twin state → Time passes → Enterprise changes (HRIS refresh) →
Drift detected (twin ≠ reality) → State refresh triggered →
Twin realigned with reality
```
*Type: Balancing (self-correcting)*
*Delay: 30-90 days (HRIS sync cadence)*
*Leverage: More frequent sync = less drift*

**Reinforcing Loop R1: Cross-Client Intelligence**
```
More clients onboard → More data patterns → 
Better simulations for new clients → 
Higher conversion → More clients
```
*Type: Reinforcing (compounding)*
*Delay: 6-12 months to see effect*
*Leverage: This is the moat — accelerates with scale*

**Reinforcing Loop R2: Technology Profile Refinement**
```
Client simulates Copilot deployment → 
Actual outcome measured → Technology profile refined →
Next client's Copilot simulation is more accurate →
More clients trust the tool → More data
```
*Type: Reinforcing (compounding)*
*Delay: 6-18 months per technology profile*

### 2.4 Leverage Points (Where Small Changes Have Large Effects)

Ranked from least to most powerful (Meadows' hierarchy):

| Rank | Leverage Point | Application to Digital Twin |
|------|---------------|---------------------------|
| 12 | Constants, parameters | Automation factors, adoption curves — tune these |
| 9 | Delays | Graph composition pipeline speed, validation cycle time |
| 8 | Balancing loops | B1 (validation) and B2 (drift) — invest here early |
| 6 | Information flows | Making simulation results visible to decision-makers — the UX |
| 5 | Rules of the system | What the twin will/won't simulate, compliance gates |
| 4 | Power to self-organize | Configuration-over-code — enterprises customize without engineering |
| 3 | Goals of the system | "Enable confident decisions" not "produce dashboards" |
| 2 | Mindset/paradigm | Twin as living system, not static report — enterprise must adopt this |

**Highest-leverage investment:** Information flows (Layer 5: Experience) and Balancing loops (validation + drift). A twin that nobody uses because the UX is poor is worthless. A twin that diverges from reality because validation is slow is dangerous.

---

## 3. Second-Order Effects Analysis

### Thought Experiment: "What breaks if we build this wrong?"

**If we build the graph but skip validation:**
→ First-order: Twin runs simulations fast
→ Second-order: Client sees number they disagree with, asks "where did this come from?", no provenance
→ Third-order: Loss of trust in entire system. Client never uses it again.
→ **Design implication:** Explainability and provenance from Day 1, not Day 100.

**If we build simulation but skip cascade propagation:**
→ First-order: Can show "this role's automation score changes"
→ Second-order: Can't show "what happens to adjacent roles, downstream workflows, total cost"
→ Third-order: Answers are incomplete; client goes back to consultants for "full picture"
→ **Design implication:** Cascade propagation is non-negotiable for Phase 1.

**If we over-optimize the graph schema before testing with real data:**
→ First-order: Beautiful schema, clean code
→ Second-order: Real GLIC data doesn't fit the schema — taxonomy mapping is messy
→ Third-order: Major refactoring, delayed delivery, lost momentum
→ **Design implication:** Schema must be validated against real client data within Week 2. Don't gold-plate.

**If we build all 21 simulation domains simultaneously:**
→ First-order: Impressive roadmap
→ Second-order: Nothing works well, everything is half-built
→ Third-order: Demo fails, client loses confidence, team burns out
→ **Design implication:** Strict phase-gating. "One Client, Full Value" test before advancing.

---

## 4. The Fractal Architecture Principle

The exploration document established a critical design principle: **self-similar simplicity at every scale**. Every component follows the same shape:

```
Input → Process → Output → Metrics
```

This applies at every level:
- A single task classification: JD text → LLM classification → AI/Human+AI/Human → confidence score
- A workload decomposition: Role → task extraction → workload grouping → automation breakdown
- A role simulation: Role + scenario → cascade propagation → future-state profile → transformation index
- An org simulation: Function + scenario → multi-role cascade → org-level projection → enterprise metrics

**Implementation rule:** If a new component doesn't fit this shape, it's designed wrong. Refactor until it does.

---

# PART II: ARCHITECTURE DECISIONS

## 5. System Architecture Overview

### 5.1 The Five Layers (Refined from Exploration)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: EXPERIENCE LAYER                                                │
│                                                                          │
│  Twin Explorer  │  Scenario Builder  │  Comparison View  │  API Gateway  │
│  (React)        │  (React)           │  (React)          │  (FastAPI)    │
├──────────────────────────────────────────────────────────────────────────┤
│ LAYER 4: SIMULATION LAYER                                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │              Simulation Orchestrator (Temporal)                     │  │
│  │                                                                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │  │
│  │  │ Cascade  │ │ Financial│ │ Skills   │ │ Role Redesign      │   │  │
│  │  │ Engine   │ │ Engine   │ │ Engine   │ │ Engine             │   │  │
│  │  │ (core)   │ │ (exists) │ │ (new)    │ │ (new)              │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                         │  │
│  │  │ Tech     │ │ Process  │ │ Scenario │                         │  │
│  │  │ Adoption │ │ Optimizer│ │ Manager  │                         │  │
│  │  │ (Phase2) │ │ (Phase1) │ │ (core)   │                         │  │
│  │  └──────────┘ └──────────┘ └──────────┘                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│ LAYER 3: GRAPH COMPOSITION LAYER                                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    Neo4j TwinCell Graph                             │  │
│  │  Taxonomy ↔ Roles ↔ Workloads ↔ Tasks ↔ Skills ↔ Technologies    │  │
│  │                  ↔ Workflows ↔ Scenarios ↔ Results                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Scope Selector  │  Aggregation Engine  │  Boundary Validator            │
├──────────────────────────────────────────────────────────────────────────┤
│ LAYER 2: DATA PROCESSING LAYER                                           │
│                                                                          │
│  Graph Composer  │  Taxonomy Mapper  │  Etter Pipeline Connector         │
│  (new - core)    │  (extend)         │  (adapt existing)                 │
├──────────────────────────────────────────────────────────────────────────┤
│ LAYER 1: DATA INGESTION LAYER                                            │
│                                                                          │
│  HRIS Connector  │  Etter API Outputs  │  Enterprise Context  │  Draup   │
│  (Workato)       │  (existing)          │  (CSV/API)           │  Intel   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Technology Stack Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Graph Database** | Neo4j (existing) | Already in Etter stack; natural fit for relationship traversal; Cypher for queries |
| **Workflow Orchestration** | Temporal (existing) | Already in Etter stack; handles long-running simulations, retries, state management |
| **API Layer** | FastAPI (existing) | Already in Etter stack; async support; fast; good for streaming simulation progress |
| **Cache** | Redis (existing) | Cache aggregated metrics, simulation results for repeated queries |
| **Scenario Storage** | PostgreSQL/Aurora (existing) | Scenario configs, audit logs, user sessions; relational is correct for this |
| **Frontend** | React (existing) | Twin Explorer, Scenario Builder, Comparison views |
| **LLM Integration** | Claude + Gemini via ModelManager (existing) | Technology-task matching, natural language query interface |

**Key architectural decision: No new infrastructure.** Everything runs on existing stack. The twin is a new *application layer* on existing infrastructure, not a new infrastructure investment.

### 5.3 Tradeoff Analysis: Architecture Decisions

**Tradeoff 1: Single Graph vs. Separate Graphs per Client**

| Option | Pros | Cons |
|--------|------|------|
| Single Neo4j with client partitioning | Cross-client queries possible, simpler ops | Security boundaries need careful design, noisy neighbor risk |
| Separate Neo4j per client | Strong isolation, no noisy neighbor | No cross-client intelligence, more ops overhead |
| **Recommended: Single graph with tenant isolation** | Enables Phase 4 (cross-client intelligence) without migration. Use Neo4j multi-database or labeled subgraphs with tenant_id on every node. |

**Tradeoff 2: Simulation Execution — Synchronous vs. Asynchronous**

| Option | Pros | Cons |
|--------|------|------|
| Synchronous (API returns result) | Simple; immediate feedback | Slow for multi-role cascades; blocks UI |
| Asynchronous (Temporal workflow) | Handles long simulations; progress tracking; retry | More complex; needs polling/websocket for UI |
| **Recommended: Async via Temporal** | Multi-role cascade across 100+ roles can take 10-60 seconds. Temporal handles this natively. UI shows progress bar. Simple simulations (<5 roles) can still feel synchronous with fast response. |

**Tradeoff 3: Graph Schema — Strict vs. Flexible**

| Option | Pros | Cons |
|--------|------|------|
| Strict schema (all fields required) | Consistent; easy to query; no nulls | Clients with partial data blocked; slow onboarding |
| Flexible schema (optional fields, defaults) | Fast onboarding; partial twins valuable | More complex queries; need null handling |
| **Recommended: Flexible with Readiness Scoring** | Accept partial data; compute a Data Readiness Score (0-100) per the addendum's framework. Twin operates with whatever data exists but flags confidence levels. "This projection has confidence 62/100 because salary data is missing." |

**Tradeoff 4: Cascade Propagation — Eager vs. Lazy**

| Option | Pros | Cons |
|--------|------|------|
| Eager (compute all cascades at simulation time) | Complete results; all effects visible | Slow for large scopes; compute-heavy |
| Lazy (compute cascades on-demand as user explores) | Fast initial result; progressive detail | User might miss important cascades; inconsistent state |
| **Recommended: Two-pass approach** | Pass 1 (eager): Compute direct effects (task reclassification, workload recomposition, per-role metrics) — fast, always done. Pass 2 (lazy): Compute cross-role cascades, workflow impacts, org-level aggregation — triggered on demand or in background. This gives fast feedback with full depth available. |

---

## 6. Data Flow Architecture

### 6.1 The Composition Pipeline (Layer 2 — The Heart of Phase 0)

This is the most critical new component. It transforms separate Etter API outputs into a connected graph.

```
PIPELINE: Client Onboarding → Graph Composition

Step 1: TAXONOMY INGESTION
  Input:  Client HRIS export (CSV/API) OR manual taxonomy definition
  Process: Parse hierarchy → Validate levels → Create taxonomy nodes
  Output: Organization → Function → SubFunction → JobFamilyGroup → 
          JobFamily → JobRole → JobTitle nodes in Neo4j
  Gate:   Taxonomy structure queryable; all levels present
  Metrics: Taxonomy completeness score, node count per level

Step 2: INTELLIGENCE HYDRATION  
  Input:  Etter Assessment API responses (per role)
  Process: For each assessed role:
           - Create Workload nodes from assessment.workloads[]
           - Create Task nodes from workload.tasks[]
           - Set classifications, impact scores, time allocations
           - Link: Role -[:DECOMPOSES_INTO]-> Workload -[:CONTAINS]-> Task
  Output: Intelligence layer populated
  Gate:   Assessment coverage ≥ 85% of roles in scope
  Metrics: Assessment coverage %, avg tasks per role, classification distribution

Step 3: SKILLS HYDRATION
  Input:  Etter Dynamic Skills API responses (per role)
  Process: For each role:
           - Create/merge Skill nodes (deduplicate across roles)
           - Link: Role/Workload/Task -[:REQUIRES]-> Skill
           - Link: Workload -[:HAS_SUNRISE]-> Skill, -[:HAS_SUNSET]-> Skill
           - Set lifecycle_status, market_demand (from Draup)
  Output: Skills layer populated with cross-role deduplication
  Gate:   Skill coverage ≥ 90% of roles; sunrise/sunset populated
  Metrics: Unique skill count, sunrise/sunset ratio, skill concentration

Step 4: ENTERPRISE CONTEXT HYDRATION
  Input:  HRIS data (headcount, salary, location per role/title)
  Process: Attach context to existing nodes:
           - JobTitle.headcount, JobTitle.avg_salary, JobTitle.location
           - Compute blended metrics at Role level
  Output: Context layer populated
  Gate:   Headcount present for ≥ 95% of roles; salary for ≥ 80%
  Metrics: Context coverage %, data freshness (last HRIS sync date)

Step 5: RELATIONSHIP ENRICHMENT
  Input:  Etter Adjacency Model, Workflow Analysis, Ecosystem Model
  Process: Create cross-cutting edges:
           - Role -[:ADJACENT_TO {score}]-> Role
           - Task -[:PART_OF {sequence}]-> Workflow
           - Role -[:PARTICIPATES_IN]-> Workflow
           - Task -[:AFFECTED_BY {shift, reduction}]-> Technology
  Output: Full relationship graph
  Gate:   Adjacency scores for ≥ 80% of role pairs; workflow coverage ≥ 70%
  Metrics: Edge count, avg adjacency score, workflow coverage %

Step 6: AGGREGATION COMPUTATION
  Input:  Complete graph
  Process: Bottom-up aggregation:
           - Task metrics → Workload metrics (weighted by effort_allocation)
           - Workload metrics → Role metrics (weighted by time_pct)
           - Role metrics → JobTitle metrics (weighted by task_time_weights)
           - Role metrics → Family → FamilyGroup → SubFunction → Function → Org
  Output: Pre-computed aggregate metrics at every taxonomy level
  Gate:   Aggregation matches manual calculation for 3 sample roles
  Metrics: Aggregation consistency score, computation time

Step 7: READINESS SCORING
  Input:  All gates from Steps 1-6
  Process: Compute Data Readiness Score (0-100) per addendum framework:
           - Taxonomy Completeness (25 pts)
           - Role Decomposition (30 pts)
           - Skills Architecture (20 pts)
           - Enterprise Context (15 pts)
           - Validation & Trust (10 pts)
  Output: Readiness score with dimension-level breakdown
  Gate:   Score ≥ 70 → Twin activatable. Score 50-69 → Partial twin with flags.
  Metrics: Readiness score, per-dimension scores, gap list
```

### 6.2 The Simulation Pipeline (Layer 4 — The Core Loop)

Every simulation follows the same pattern regardless of domain (S1-S21):

```
PIPELINE: Simulation Execution

Input: Scenario configuration + Scope selection + Graph state

Step 1: SCOPE RESOLUTION
  Process: Traverse taxonomy to identify all nodes within scope
  Output: Set of affected roles, workloads, tasks, skills
  Metrics: Scope size (roles, tasks), boundary clarity

Step 2: STIMULUS APPLICATION  
  Process: Apply scenario parameters to affected tasks
  Varies by simulation type:
    - Technology Adoption: Match tech capabilities → tasks → reclassify
    - Role Redesign: Manual task reclassification
    - Cost Optimization: Multi-objective optimization across roles
  Output: Modified task states (before/after per task)
  Metrics: Tasks affected count, classification shifts count

Step 3: CASCADE PROPAGATION (The 8-Step Chain from Exploration)
  Process: Propagate effects through the graph:
    3a: Task reclassification (first-order)
    3b: Workload recomposition (second-order)
    3c: Role & JobTitle impact (third-order)
    3d: Skill shifts (fourth-order)
    3e: Workforce recalculation (fifth-order)
    3f: Financial projection (sixth-order)
    3g: Risk assessment (cross-cutting)
  Output: Complete simulation result with effects at every level
  Metrics: Cascade depth reached, effects per level, computation time

Step 4: RESULT PACKAGING
  Process: Structure results into standardized output format
  Output: SimulationResult node linked to Scenario
  Includes: financial, headcount, skills, risks, timeline projections
  Metrics: Result completeness score

Step 5: CONFIDENCE SCORING
  Process: Assess result reliability based on:
    - Data readiness score of input data
    - Validation coverage of affected scores
    - Monte Carlo CI width (if applicable)
  Output: Confidence interval per metric
  Metrics: Average confidence, min confidence, low-confidence flags
```

---

# PART III: PHASED IMPLEMENTATION PLAN

## 7. Phase 0: Foundation Infrastructure (Weeks 1-3)

### 7.0 Goal
Build the plumbing that every subsequent phase depends on. No simulation logic yet — just the ability to compose Etter outputs into a connected graph and query it.

### 7.1 Deliverables

**D0.1: Neo4j Graph Schema Implementation**
- Create all node labels: Organization, Function, SubFunction, JobFamilyGroup, JobFamily, JobRole, JobTitle, Workload, Task, Skill, Technology, Workflow, Scenario, SimulationResult
- Create all relationship types with property schemas
- Create indexes for performance: tenant_id, role.name, skill.name, task.classification
- Create constraints: unique IDs per tenant, taxonomy hierarchy integrity
- Estimated effort: 3-4 days
- Success metric: Schema deployed; sample data loadable; Cypher queries return correct results

**D0.2: Graph Composer Service**
- Python service that takes Etter API outputs and loads them into Neo4j
- Modular design: separate composers for taxonomy, assessment, skills, context, relationships
- Idempotent operations (re-run safely without duplication)
- Pipeline orchestrated via Temporal workflow
- Estimated effort: 5-7 days
- Success metric: GLIC assessment data loaded into graph; query returns correct role→workload→task chain

**D0.3: Scope Selector**
- Cypher query templates for selecting nodes at any taxonomy level
- Input: tenant_id + scope_type (org/function/subfamily/role) + scope_id
- Output: All nodes and edges within scope
- Estimated effort: 2-3 days
- Success metric: "Show me everything in GLIC Claims" returns correct subgraph

**D0.4: Aggregation Engine**
- Bottom-up metric aggregation from tasks → org level
- Weighted aggregation respecting JobTitle task_time_weights
- Pre-computed and cached in Redis for fast dashboard rendering
- Recalculated on data change (event-driven)
- Estimated effort: 3-4 days
- Success metric: Function-level automation score matches manual calculation

**D0.5: Data Readiness Scorer**
- Computes readiness score per the addendum's framework
- Returns dimension-level scores and gap list
- Determines twin activation status: READY / PARTIAL / NOT_READY
- Estimated effort: 2 days
- Success metric: Score computed for GLIC; gaps correctly identified

### 7.2 Phase 0 Architecture Detail

```
Graph Composer Service (Temporal Workflow)
├── TaxonomyComposer
│   ├── parse_hris_export(csv/json) → taxonomy nodes
│   ├── validate_hierarchy() → completeness check
│   └── create_taxonomy_graph(neo4j) → nodes + CONTAINS edges
│
├── AssessmentComposer  
│   ├── fetch_assessments(etter_api, role_ids) → assessment data
│   ├── create_workload_nodes(workloads) → Workload nodes
│   ├── create_task_nodes(tasks) → Task nodes
│   └── link_role_workload_tasks(neo4j) → DECOMPOSES_INTO + CONTAINS edges
│
├── SkillsComposer
│   ├── fetch_skills(etter_api, role_ids) → skills data
│   ├── deduplicate_skills(skills) → canonical skill set
│   ├── create_skill_nodes(skills) → Skill nodes
│   └── link_skills(neo4j) → REQUIRES + HAS_SUNRISE + HAS_SUNSET edges
│
├── ContextComposer
│   ├── parse_enterprise_data(hris_export) → headcount, salary, location
│   └── attach_context(neo4j, context) → properties on JobTitle/Role nodes
│
├── RelationshipComposer
│   ├── fetch_adjacency(etter_api) → adjacency scores
│   ├── fetch_workflows(etter_api) → workflow data
│   └── create_cross_edges(neo4j) → ADJACENT_TO, PART_OF, PARTICIPATES_IN
│
└── ReadinessScorer
    ├── score_taxonomy_completeness() → 0-25
    ├── score_role_decomposition() → 0-30
    ├── score_skills_architecture() → 0-20
    ├── score_enterprise_context() → 0-15
    ├── score_validation_trust() → 0-10
    └── compute_total() → 0-100 with status
```

### 7.3 Phase 0 Gates

| Gate | Criterion | How to Test |
|------|----------|-------------|
| G0.1 | Graph schema deployed and queryable | Run standard Cypher queries against empty graph |
| G0.2 | GLIC data loaded successfully | Query: "Return all roles in Claims function with workloads and tasks" |
| G0.3 | Aggregation correct | Compare function-level scores with manually computed values for 3 roles |
| G0.4 | Readiness score computed | Score matches expected value for GLIC's known data state |
| G0.5 | Scope selector works at all levels | Query from org down to individual task; each level returns correct subgraph |

### 7.4 Phase 0 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Graph load time (full client) | < 5 minutes | Time from pipeline start to graph ready |
| Query response time (scope select) | < 500ms | P95 for function-level scope query |
| Aggregation accuracy | 100% match | Automated comparison against manual calculation |
| Data readiness score accuracy | Matches manual audit | Score reviewed by team for 2 clients |

---

## 8. Phase 1: Minimum Viable Twin (Weeks 3-8)

### 8.0 Goal
Answer the question: "What happens if we automate the top N tasks in [function/role]?" with quantified results across roles, skills, and finances. This is the "One Client, Full Value" test.

### 8.1 Deliverables

**D1.1: Scenario Manager**
- CRUD for Scenario objects (create, read, update, delete)
- Scenario configuration: scope, automation_factor, time_horizon, constraints
- Scenario versioning and comparison grouping
- Storage: PostgreSQL for config; Neo4j for results linked to graph
- API: FastAPI endpoints for scenario lifecycle
- Estimated effort: 4-5 days
- Success metric: Create scenario, run simulation, retrieve results via API

**D1.2: Cascade Propagation Engine (Core)**
- The heart of the simulation layer
- Implements the 8-step cascade chain from the exploration document
- Input: Scenario config + scope-resolved graph subgraph
- Output: Effects at every level (task → workload → role → title → family → function)
- Architecture: Temporal workflow with one activity per cascade step
- Estimated effort: 8-10 days
- Success metric: "Automate top 10 tasks in Claims Adjudicator" produces correct cascade to financial projection

**D1.2a: Step 1-2 — Task Reclassification + Workload Recomposition**
```
Input: Set of tasks + reclassification rules (manual or from tech profile)
Process:
  For each affected task:
    - Store original classification
    - Apply new classification (Human → Human+AI, Human+AI → AI)
    - Recalculate task-level metrics
  For each affected workload:
    - Recalculate automation_breakdown (ai_pct, human_ai_pct, human_pct)
    - Recalculate effort_allocation
    - Identify new sunrise skills needed
    - Identify accelerated sunset skills
Output: Modified workload states
```

**D1.2b: Step 3-4 — Role/Title Impact + Skill Shifts**
```
Input: Modified workload states + JobTitle task_time_weights
Process:
  For each affected role:
    For each JobTitle within role:
      - Compute title-specific freed capacity (Σ task.time_pct × title.weight × classification_change)
      - Compute title-specific automation score change
    - Compute role-level aggregate metrics
    - Flag roles with >40% freed capacity for redesign trigger
  For each affected role:
    - Compute skill gap (current skills vs. future-required skills)
    - Identify new sunrise skills per workload context
    - Compute reskilling requirements
Output: Per-title impact metrics + skill shift analysis
```

**D1.2c: Step 5-6 — Workforce Recalculation + Financial Projection**
```
Input: Per-title freed capacity + existing Financial Simulator
Process:
  - Aggregate freed capacity across function
  - Feed into Financial Simulator (already exists):
    - Headcount trajectory over time
    - Cost savings curve with adoption modeling
    - Monte Carlo for confidence intervals
  - Compute per-title financial impact (salary × headcount × freed_capacity)
  - Compute reskilling investment (skill_gap × training_cost_per_skill)
  - Compute technology licensing cost (if applicable)
  - Net ROI = savings - licensing - implementation - reskilling
Output: Financial projection with CI, headcount trajectory, reskilling cost
```

**D1.2d: Step 7 — Risk Assessment (Cross-Cutting)**
```
Input: All cascade results + compliance rules (if configured)
Process:
  - Flag compliance-sensitive tasks being automated
  - Flag single-point-of-failure roles (skills concentrated in few people)
  - Flag workloads with >80% automation (complete restructuring signal)
  - Estimate change management burden (function of scope × speed)
Output: Risk flags with severity and recommended mitigations
```

**D1.3: Role Redesign Engine (S1)**
- Given a role + simulation results → generate future-state role profile
- Current vs. future side-by-side: task list, workload composition, skills, time allocation
- Identifies "role vacuum" — orphaned tasks that need a new home
- Estimated effort: 4-5 days
- Success metric: Future-state Claims Adjudicator profile generated correctly

**D1.4: Skills Strategy Engine (S4)**
- Skills heatmap: sunrise/sustaining/sunset across all roles in scope
- Skill concentration risk alerts
- Reskilling pathway generation (leveraging existing Etter reskilling capability)
- Build vs. buy recommendation per skill
- Estimated effort: 4-5 days
- Success metric: Skills heatmap for Claims function matches manual analysis

**D1.5: Financial Simulator Integration**
- Connect existing Financial Simulator to twin's cascade output
- Extend for multi-role simulation (currently single-role)
- Accept twin-computed freed capacity as input instead of raw automation scores
- Support level-specific (JobTitle-aware) financial projections
- Estimated effort: 5-7 days
- Success metric: Financial projection for "automate Claims" matches standalone simulator ±5%

**D1.6: Basic Twin Explorer UI**
- Graph visualization: Navigate taxonomy (org → function → role → workload → task)
- Drill-down: Click any node to see its metrics and children
- Scope selection: Pick a function, family, or role to focus simulation
- Results display: Show cascade effects at every level after simulation
- Estimated effort: 8-10 days (parallel with backend work)
- Success metric: GLIC stakeholder can navigate Claims function and see task-level detail

**D1.7: Scenario Comparison (Basic)**
- Run 2-3 scenarios with different parameters
- Side-by-side comparison of key metrics: financial, headcount, skills
- Even if the UI is basic (table comparison), the capability must exist
- Estimated effort: 3-4 days
- Success metric: Compare Conservative (0.15) vs. Moderate (0.30) vs. Aggressive (0.50) scenarios

### 8.2 Phase 1 Architecture Detail

```
Simulation Orchestrator (Temporal)
│
├── SimulationWorkflow
│   ├── resolve_scope(tenant_id, scope) → node_set
│   ├── apply_stimulus(node_set, scenario) → modified_tasks
│   ├── cascade_step_1_task_reclassification(modified_tasks) → task_effects
│   ├── cascade_step_2_workload_recomposition(task_effects) → workload_effects
│   ├── cascade_step_3_role_title_impact(workload_effects) → role_effects
│   ├── cascade_step_4_skill_shifts(role_effects) → skill_effects
│   ├── cascade_step_5_workforce_recalculation(role_effects) → workforce_projection
│   ├── cascade_step_6_financial_projection(workforce_projection) → financial_result
│   ├── cascade_step_7_risk_assessment(all_effects) → risk_flags
│   └── package_result(all_effects) → SimulationResult
│
├── RoleRedesignWorkflow
│   ├── get_current_profile(role_id) → current_state
│   ├── apply_simulation_effects(current_state, sim_result) → future_state
│   ├── compute_delta(current_state, future_state) → transformation_report
│   └── detect_role_vacuum(future_state) → orphaned_tasks
│
└── ScenarioComparisonWorkflow
    ├── run_scenarios(scenario_configs[]) → sim_results[]
    ├── align_metrics(sim_results[]) → comparable_metrics
    └── generate_comparison(comparable_metrics) → comparison_report
```

### 8.3 Phase 1 Gates — "One Client, Full Value" Test

| # | Gate | How to Verify |
|---|------|--------------|
| 1 | Can ingest GLIC role data and display twin of Claims function | Navigate taxonomy in UI; see all roles, workloads, tasks |
| 2 | Can run "What if we automate top 10 tasks?" with role impact | Run simulation; verify cascade produces effects at every level |
| 3 | Can show skill shifts and reskilling requirements | Skills heatmap shows sunrise/sunset; reskilling paths generated |
| 4 | Can project financial impact over 36 months with Monte Carlo CI | Financial chart with confidence band; drill into per-role breakdown |
| 5 | Can compare 3 scenarios side-by-side | Conservative/Moderate/Aggressive comparison table renders correctly |

**ALL FIVE MUST PASS before proceeding to Phase 2.**

### 8.4 Phase 1 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cascade computation time | < 10s for single function | P95 for GLIC Claims (~50 roles) |
| Financial projection accuracy | Within 5% of standalone simulator | Comparison test |
| Graph query latency | < 200ms for drill-down | P95 for role-level detail query |
| Scenario comparison load time | < 3s for 3-way comparison | Full comparison rendering |
| Data readiness score for GLIC | ≥ 70 | Computed by D0.5 |
| Cascade depth | All 7 steps complete | Verify all steps produce output |

---

## 9. Phase 2: Value Layer (Weeks 6-14, overlaps Phase 1)

### 9.0 Goal
Answer CxO-level questions. The "Boardroom Test" from the exploration document. Technology Adoption Impact is the killer feature.

### 9.1 Deliverables

**D2.1: Technology Adoption Impact Engine (S6) ⭐ KILLER FEATURE**
- Pre-built Technology Profiles: Copilot, UiPath, ServiceNow AI, Salesforce Einstein, SAP Joule, GitHub Copilot, Claims AI
- Semantic matching: Technology capabilities → affected tasks (LLM-powered)
- Reclassification engine: Apply technology impact to tasks automatically
- Full cascade: Technology → task → workload → role → title → financial
- Estimated effort: 10-14 days
- Success metric: "What happens when we deploy Copilot across Claims?" returns quantified answer matching exploration document's example

Architecture for Technology Matching:
```
TechAdoptionWorkflow (Temporal)
├── load_tech_profile(tech_id) → capabilities[]
├── match_capabilities_to_tasks(capabilities, scope_tasks)
│   ├── semantic_match(capability, task.description) → relevance_score
│   ├── filter(relevance_score > threshold) → affected_tasks
│   └── determine_shift(capability, task.current_classification) → new_classification
├── compute_adoption_curve(tech.adoption_type, enterprise.change_readiness)
│   └── Returns time-series adoption factors [month_1: 0.05, month_6: 0.25, ...]
├── run_cascade(affected_tasks, adoption_curve) → cascade_result
├── compute_technology_costs(tech.license_cost, scope_headcount, timeline)
├── compute_net_roi(cascade_result.savings, tech_costs, reskilling_costs)
└── generate_report() → TechAdoptionReport
```

**D2.2: Cost Optimization Engine (S7)**
- Multi-objective optimization: minimize cost while preserving critical capabilities
- Compare: targeted optimization vs. across-the-board cuts
- Constraint-aware: "no layoffs," "preserve customer-facing," budget ceiling
- Estimated effort: 6-8 days
- Success metric: "Save $5M without destroying Claims capability" produces actionable path

**D2.3: Risk & Readiness Assessment (S9)**
- 8-dimension risk scoring (data quality, integration, governance, analytics, process, team, tech, culture)
- Enterprise self-assessment input mechanism (questionnaire or API)
- Risk overlay on simulation results: adjusts confidence intervals, extends timelines
- Estimated effort: 5-7 days
- Success metric: Risk score computed for GLIC; "medium" risks correctly lower confidence in projections

**D2.4: Process Optimization Simulation (S3)**
- Workflow analysis: bottleneck identification, automation sequencing
- Bottleneck migration map: "automating step 3 moves bottleneck to step 7"
- Cross-functional impact detection
- Estimated effort: 5-7 days
- Success metric: Claims Processing workflow shows bottleneck shift after Copilot deployment

**D2.5: Enhanced Twin Explorer UI**
- Technology adoption wizard: "Select a technology → Select scope → See results"
- Financial dashboard with drill-down (function → role → title level)
- Risk overlay visualization (heatmap by dimension)
- Workflow visualization with bottleneck highlighting
- Estimated effort: 10-12 days (parallel with backend)
- Success metric: CHRO can answer "Boardroom Test" question using the UI

### 9.2 Phase 2 Gates — "Boardroom Test"

A CHRO using the Digital Twin must be able to answer:

> "We're considering deploying Microsoft Copilot across Claims and Underwriting — 3,000 people. What happens?"

With:
1. Tasks affected count and list ✓
2. Classification shifts per task ✓
3. Workload-level impact (which areas of work change most) ✓
4. Role-level automation score changes ✓
5. Title-specific impact (entry vs. senior) ✓
6. Financial impact (gross savings, net ROI, payback month) ✓
7. Skills impact (sunrise, sunset, reskilling cost) ✓
8. Risk flags (compliance, change management) ✓
9. 3-scenario comparison (conservative, moderate, aggressive) ✓
10. Confidence intervals on all numbers ✓

### 9.3 Phase 2 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tech-task matching accuracy | > 80% precision | Validated by SME on sample |
| Technology adoption simulation time | < 30s | P95 for 100-role scope |
| Financial projection CI width | < 30% at 90% confidence | Monte Carlo output |
| Boardroom Test completeness | 10/10 checklist items | Manual verification |
| Client engagement score | > 4/5 | Post-demo feedback |

---

## 10. Phase 3: Complete Product (Weeks 10-22)

### 10.0 Goal
Full enterprise simulation suite expected by sophisticated buyers. Add compliance gates, org structure optimization, competitive benchmarking, and the meta-capability of scenario comparison.

### 10.1 Deliverables

**D3.1: Compliance & Regulatory Impact Analyzer (S11)**
- Task-level compliance flagging per industry ruleset
- Mandatory human oversight detection
- Adjusted automation scores (compliance-constrained)
- Regulatory-safe transformation path generation
- Industry rulesets: Insurance (NAIC), Healthcare (HIPAA), Financial Services (SOX)
- **Critical: Auto-runs as background check on every simulation** — no result presented without compliance flags
- Estimated effort: 6-8 days

**D3.2: Spans & Layers Optimizer (S12)**
- Post-transformation management structure analysis
- Identifies over-managed teams (AI reduces coordination overhead)
- Recommends structural changes with cost impact
- Estimated effort: 4-5 days

**D3.3: Scenario Comparison Engine (Meta-Capability)**
- Advanced multi-scenario comparison with weighted trade-off analysis
- Trade-off dimensions: cost vs. risk vs. timeline vs. capability preservation
- Visual comparison dashboards (radar charts, waterfall charts)
- "Recommended path" generation based on constraint priorities
- Estimated effort: 6-8 days

**D3.4: Location Strategy Engine (S8)**
- Cost arbitrage analysis: onshore vs. offshore vs. automate
- Talent availability risk scoring per location
- Transition cost and timeline modeling
- Estimated effort: 5-6 days

**D3.5: Competitive Benchmarking (S14)**
- Anonymous cross-client comparison (requires ≥ 3 clients in same industry)
- Industry percentile ranking
- Transformation velocity comparison
- **Note: Limited value until Phase 4 with more clients; build foundation now**
- Estimated effort: 4-5 days

**D3.6: Vendor/Outsourcing Analyzer (S10)**
- Make-Buy-Automate three-path comparison
- 3-year TCO modeling per path
- Capability control scoring
- Estimated effort: 4-5 days

**D3.7: Human Validation Integration**
- Survey mechanism for SME validation of scores
- Score locking (validated scores don't change on model re-run)
- Validation coverage tracking
- Connects to existing Etter survey capability
- Estimated effort: 5-7 days

**D3.8: Full Enterprise Dashboard**
- Organization-level overview with drill-down to any level
- Transformation readiness heatmap (by function)
- Simulation history and audit trail
- Export capabilities (PDF reports, executive summaries)
- Estimated effort: 12-15 days (parallel)

### 10.2 Phase 3 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Compliance flag accuracy | > 90% | Validated against industry regulatory expert |
| Full enterprise simulation time | < 2 minutes | For 200-role enterprise |
| Scenario comparison dimensions | ≥ 5 | Cost, risk, timeline, capability, compliance |
| Validation coverage | > 80% of scores reviewed | Per addendum framework |
| Export report completeness | All 10 Boardroom Test items | PDF report review |

---

## 11. Phase 4: Moat Builders (Weeks 18-30+)

### 11.0 Goal
Build capabilities that compound over time and become impossible for competitors to replicate.

### 11.1 Deliverables

**D4.1: Transformation Sequencing Optimizer (S15)**
- Multi-function dependency analysis
- Critical path identification
- Resource-constrained scheduling
- Compounding benefit modeling (early wins fund later phases)
- **Moat: Requires complete enterprise assessment + accumulated sequencing data**

**D4.2: Decision Provenance Engine (S16)**
- Pattern matching against historical scenarios from all clients
- Anonymized outcome retrieval
- "Organizations similar to yours that made choice X achieved outcome Y"
- Confidence intervals based on sample size
- **Moat: Every transformation tracked makes the engine smarter**

**D4.3: Cross-Client Intelligence Engine (S17)**
- Industry transformation trend detection
- Emerging skill patterns across clients
- Technology adoption wave analysis
- Transformation playbooks by industry
- **Moat: Pure network effect — value scales superlinearly with client count**

**D4.4: State Refresh & Drift Detection (Feedback Loop B2)**
- Periodic HRIS sync (monthly/quarterly)
- Drift detection: compare twin state vs. actual enterprise state
- Alert system for significant drift
- Automatic recalibration triggers
- **This is what turns the simulator into a true Digital Twin**

---

## 12. Phase 5: Horizon (12+ months)

### 12.0 Future Vision

**D5.1: M&A Workforce Integration (S18)** — Simulate combining two organizations' workforces
**D5.2: External Labor Market Intelligence (S19)** — Connect to Draup talent intelligence
**D5.3: Culture & Change Readiness (S20)** — Enterprise engagement data integration
**D5.4: ESG/Sustainability Impact (S21)** — ESG framework mapping to workforce metrics

These are listed for completeness. Architecture should NOT constrain these — the graph schema and simulation framework must be extensible enough to accommodate them without structural changes.

---

# PART IV: CROSS-CUTTING CONCERNS

## 13. Multi-Tenancy & Data Isolation

**Strategy: Neo4j labeled subgraphs with tenant_id**

Every node has a `tenant_id` property. Every Cypher query includes `WHERE n.tenant_id = $tenant_id`. This is enforced at the query layer, not left to individual queries.

```
Query Layer (enforces tenant isolation)
├── resolve_tenant(request) → tenant_id
├── inject_tenant_filter(cypher_query, tenant_id) → filtered_query
└── validate_result_tenant(result, tenant_id) → assertion
```

**Exception: Cross-Client Intelligence** (Phase 4) operates on anonymized aggregates only. No raw client data crosses tenant boundaries. Aggregation happens in a separate pipeline that strips PII and client identifiers before writing to the shared intelligence layer.

## 14. Performance & Scalability

| Concern | Solution | Target |
|---------|----------|--------|
| Large graph queries | Neo4j indexes on tenant_id, taxonomy level, role_name | < 500ms P95 |
| Multi-role cascade | Parallel cascade per role within Temporal workflow | < 30s for 100 roles |
| Monte Carlo simulations | Pre-compute and cache; invalidate on data change | < 60s for 1000 runs |
| Dashboard rendering | Redis-cached aggregations; incremental updates | < 200ms for drill-down |
| Graph composition pipeline | Batch Neo4j writes (UNWIND); parallel Etter API calls | < 5 min full client load |

## 15. Explainability & Trust Architecture

**Every number must have a drill-down path to its source.** This is not a feature — it is the trust architecture.

```
Level 0: Headline metric (e.g., "51% automation score")
  ↓ click to expand
Level 1: Contributing workloads and their automation breakdowns
  ↓ click to expand  
Level 2: Individual tasks with classifications and impact scores
  ↓ click to expand
Level 3: Classification rationale (LLM explanation), source data (JD text), confidence score
```

Implementation: Every SimulationResult stores the full cascade trace. Every aggregate links back to its constituent parts. The UI renders drill-down lazily (query-on-demand, not pre-loaded).

## 16. Configuration-Over-Code

Enterprise differences expressed as configuration:

| Configuration | Storage | Example |
|--------------|---------|---------|
| Taxonomy mapping | CSV upload → PostgreSQL | GLIC "Claims Processing Specialist I" → Etter "Claims Adjudicator" |
| Industry compliance rules | JSON rulesets | `insurance_us_naic.json` with human-oversight task patterns |
| Technology profiles | PostgreSQL + Neo4j | Copilot capabilities, license cost, adoption curve |
| Adoption parameters | Scenario config | `change_readiness: 62, ai_literacy: 45` |
| Cost model | Enterprise config | `benefits_multiplier: 1.35, location_adjustments: {...}` |

**One codebase, many configurations.**

## 17. API Design (FastAPI)

```
/api/v1/twin/
├── graph/
│   ├── POST   /compose          # Trigger graph composition pipeline
│   ├── GET    /readiness         # Get data readiness score
│   ├── GET    /scope/{level}/{id} # Get subgraph at any taxonomy level
│   └── GET    /metrics/{level}/{id} # Get pre-computed metrics
│
├── simulation/
│   ├── POST   /scenario          # Create scenario
│   ├── GET    /scenario/{id}     # Get scenario details
│   ├── POST   /scenario/{id}/run # Execute simulation
│   ├── GET    /scenario/{id}/status # Poll simulation progress
│   ├── GET    /scenario/{id}/result # Get simulation results
│   └── POST   /compare           # Compare multiple scenarios
│
├── simulation/engines/
│   ├── POST   /role-redesign     # S1: Role redesign simulation
│   ├── POST   /workforce-plan    # S2: Workforce planning
│   ├── POST   /process-optimize  # S3: Process optimization
│   ├── POST   /skills-strategy   # S4: Skills strategy
│   ├── POST   /org-transform     # S5: Org transformation
│   ├── POST   /tech-adoption     # S6: Technology adoption impact
│   ├── POST   /cost-optimize     # S7: Cost optimization
│   └── POST   /risk-assess       # S9: Risk & readiness
│
├── validation/
│   ├── POST   /validate          # Submit SME validation
│   ├── POST   /lock-score        # Lock validated score
│   └── GET    /coverage          # Get validation coverage metrics
│
└── admin/
    ├── POST   /config            # Update enterprise config
    ├── POST   /taxonomy-map      # Upload taxonomy mapping
    └── GET    /health            # Twin health metrics
```

---

# PART V: IMPLEMENTATION TIMELINE

## 18. Master Timeline

```
Week:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22
       ├──────────┤
       Phase 0: Foundation Infrastructure
       Graph Schema, Composer, Scope, Aggregation, Readiness
       
                  ├──────────────────────────┤
                  Phase 1: Minimum Viable Twin
                  Cascade Engine, Role Redesign, Skills, Financial, 
                  Basic UI, Scenario Comparison
                  
                              ├───── GLIC GATE CHECK ─────┤
                              "One Client, Full Value" test
                              
                        ├──────────────────────────────────┤
                        Phase 2: Value Layer
                        Tech Adoption Impact, Cost Optimization,
                        Risk Assessment, Process Optimization
                        
                                          ├── BOARDROOM TEST ──┤
                                          CHRO can answer the question
                                          
                                                ├──────────────────────────┤
                                                Phase 3: Complete Product
                                                Compliance, Spans & Layers,
                                                Benchmarking, Full Dashboard
                                                
                                                                    ├──────→
                                                                    Phase 4+: Moat
```

## 19. Resource Allocation

| Phase | Backend (Python) | Frontend (React) | Data/Graph (Neo4j) | Duration |
|-------|-----------------|-------------------|---------------------|----------|
| 0: Foundation | 1 engineer | — | 1 engineer | 3 weeks |
| 1: MVP Twin | 2 engineers | 1 engineer | 0.5 engineer | 5 weeks |
| 2: Value | 2 engineers | 1 engineer | 0.5 engineer | 8 weeks |
| 3: Complete | 2 engineers | 1.5 engineers | 0.5 engineer | 12 weeks |
| 4: Moat | 1-2 engineers | 1 engineer | 1 engineer | 12+ weeks |

**Minimum viable team: 3 engineers** (2 backend + 1 frontend/graph). Ideal team: 4-5.

---

# PART VI: RISK MITIGATION PLAN

## 20. Implementation Risks

| Risk | Severity | Probability | Mitigation | Detection Metric |
|------|----------|-------------|------------|------------------|
| Graph schema doesn't fit real data | High | Medium | Validate against GLIC data in Week 2; iterate schema before hardening | Schema change count after Week 3 |
| Cascade propagation is too slow | Medium | Medium | Two-pass approach (eager direct + lazy cross-role); profile and optimize | P95 simulation time > 30s |
| Financial simulator integration breaks | High | Low | Write comprehensive integration tests; keep fallback to standalone mode | Financial delta > 5% vs standalone |
| Technology-task matching inaccurate | High | Medium | Human-in-the-loop validation on first 3 tech profiles; iterate prompts | Precision < 80% on SME review |
| Multi-role cascade produces nonsensical results | Critical | Low | Boundary validation at each cascade step; sanity checks (e.g., total headcount can't increase) | Automated sanity check failures |
| Client data quality too poor for meaningful simulation | High | High | Readiness score gates; explicit "low confidence" warnings; fallback to Draup market defaults | Readiness score < 50 for first 3 clients |
| Over-engineering Phase 0 | Medium | Medium | Hard timebox: 3 weeks max for Phase 0; "good enough" schema, iterate later | Phase 0 > 3 weeks |

---

# PART VII: SUCCESS METRICS HIERARCHY

## 21. Metrics at Every Level

### 21.1 System Health Metrics (Is the twin reliable?)

| Metric | Target | Phase Available |
|--------|--------|-----------------|
| Data Readiness Score | ≥ 70 per client | Phase 0 |
| Model Completeness | > 85% roles assessed | Phase 0 |
| Graph State Freshness | < 30 days since last refresh | Phase 1 |
| Validation Coverage | > 80% of scores reviewed by SME | Phase 3 |
| Simulation Confidence (Monte Carlo CI width) | < 30% at 90% level | Phase 1 |
| Cascade Computation Time | < 30s for 100 roles | Phase 1 |
| API Response Time (P95) | < 500ms for queries, < 60s for simulations | Phase 1 |

### 21.2 Business Value Metrics (Is the twin useful?)

| Metric | Target | Phase Available |
|--------|--------|-----------------|
| Time to First Insight | < 3 weeks from engagement | Phase 1 |
| Scenarios Run per Client per Month | > 5 | Phase 1 |
| Decision Influence | ≥ 1 decision/quarter using twin output | Phase 2 |
| Projection Accuracy (vs. actual at 6mo) | ≤ 15% delta | Phase 3+ |
| Client Expansion Rate | 1 scope expansion per quarter | Phase 2 |
| Boardroom Test Pass Rate | 10/10 checklist items | Phase 2 |

### 21.3 Product-Market Metrics (Is the category real?)

| Metric | Target | Phase Available |
|--------|--------|-----------------|
| Client Activation (twin live) | 3 clients in 6 months | Phase 1-2 |
| Client Retention (twin renewed) | > 80% annual retention | Phase 3+ |
| Net Promoter Score (twin-specific) | > 50 | Phase 2+ |
| Cross-Client Intelligence queries | > 10/month (Phase 4) | Phase 4 |
| Category Awareness | "AI Workforce Transformation Simulation" recognized | Phase 3+ |

### 21.4 Engineering Health Metrics

| Metric | Target | Phase Available |
|--------|--------|-----------------|
| Graph Composition Pipeline Reliability | > 99% success rate | Phase 0 |
| Simulation Success Rate | > 95% (no crashes/timeouts) | Phase 1 |
| Test Coverage (cascade engine) | > 90% | Phase 1 |
| Mean Time to Onboard New Client | < 2 weeks (with existing assessment) | Phase 1 |
| Configuration-to-Code Ratio | > 80% enterprise differences as config | Phase 2 |

---

# PART VIII: IMMEDIATE NEXT STEPS

## 22. Week 1 Action Items

| # | Action | Owner | Deliverable | Due |
|---|--------|-------|-------------|-----|
| 1 | Review this document with CEO Vijay | Chandan | Go/No-Go decision on phasing | Day 2 |
| 2 | Validate Neo4j graph schema against GLIC data | Engineering | Schema v0.1 tested with real data | Day 5 |
| 3 | Stand up Graph Composer service skeleton | Engineering | Temporal workflow running (empty steps) | Day 5 |
| 4 | Verify GLIC assessment data accessibility | Engineering | Confirm all assessed roles retrievable via API | Day 3 |
| 5 | Design Cascade Engine interface contracts | Chandan + Eng | Input/Output types for each cascade step | Day 4 |
| 6 | Set up twin-specific Neo4j database/labels | Engineering | Isolated namespace within existing Neo4j | Day 2 |

## 23. Decision Log (To Be Filled During Implementation)

| # | Decision | Options Considered | Chosen | Rationale | Date |
|---|----------|-------------------|--------|-----------|------|
| 1 | Graph schema approach | Strict vs. flexible | Flexible + readiness scoring | Real data is messy; gate on readiness, not schema | Feb 2026 |
| 2 | Simulation execution | Sync vs. async | Async (Temporal) | Multi-role cascades too slow for sync | Feb 2026 |
| 3 | Cascade propagation | Eager vs. lazy vs. two-pass | Two-pass | Fast first response; full depth on demand | Feb 2026 |
| 4 | Multi-tenancy | Separate DBs vs. labeled subgraphs | Labeled subgraphs | Enables cross-client intelligence later | Feb 2026 |

---

*End of Implementation Plan v1.0*
*Phases: 5 | Deliverables: 30+ | Metrics: 25+ | Risks: 7 mitigated*
*Architecture: 5 layers, fractal design, configuration-over-code*
*First milestone: GLIC Claims function twin live — Week 8*
