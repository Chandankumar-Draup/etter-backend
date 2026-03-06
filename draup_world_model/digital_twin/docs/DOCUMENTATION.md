# Digital Twin for Enterprise - Complete Documentation

> A workforce simulation platform that models an entire enterprise as a graph,
> then lets you ask "what if?" questions about automation, technology, and skills.

---

## Table of Contents

1. [What This Is (First Principles)](#1-what-this-is-first-principles)
2. [Prerequisites & Installation](#2-prerequisites--installation)
3. [Architecture Overview](#3-architecture-overview)
4. [Phase 1: Data Foundation](#4-phase-1-data-foundation)
5. [Phase 2: Neo4j Graph Loading](#5-phase-2-neo4j-graph-loading)
6. [Phase 3: Simulation Engine](#6-phase-3-simulation-engine)
7. [Phase 4: UI & Integration](#7-phase-4-ui--integration)
8. [Configuration Reference](#8-configuration-reference)
9. [Troubleshooting](#9-troubleshooting)
10. [Systems Thinking Notes](#10-systems-thinking-notes)

---

## 1. What This Is (First Principles)

### The Core Idea

Every enterprise is a **system of interconnected parts**: people do work, work requires skills, skills evolve with technology, technology changes costs. Change one thing, and effects cascade through the entire system.

This package builds a **digital twin** - a model of that system - and lets you simulate changes before they happen in reality.

### The Mental Model

Think of it as three layers:

```
┌─────────────────────────────────────────────────────────┐
│  UI Layer            (Phase 4)                          │
│  "What does the user see?"                              │
│  Flask + React SPA → Dashboard, Explorer, Simulator     │
├─────────────────────────────────────────────────────────┤
│  Simulation Layer    (Phase 3)                          │
│  "What happens when things change?"                     │
│  Scope → Cascade Engine → Financial → Risk → Compare    │
├─────────────────────────────────────────────────────────┤
│  Data Layer          (Phase 1 + 2)                      │
│  "What does the enterprise look like today?"            │
│  LLM Generators → JSON → Neo4j Graph                   │
└─────────────────────────────────────────────────────────┘
```

### Why a Graph?

An enterprise isn't a spreadsheet. It's a **network**:
- An Organization *contains* Functions
- Functions *contain* Sub-Functions, which *contain* Job Families
- Job Families *have* Roles, Roles *have* Job Titles
- Roles *decompose into* Workloads, Workloads *contain* Tasks
- Roles *require* Skills and *use* Technologies

A graph database (Neo4j) models these relationships natively. When you ask "what happens if we automate Claims tasks?", the graph lets you trace the cascade: tasks → workloads → roles → skills → costs.

### The Acme Corporation Demo

The prototype models **Acme Corporation**, a fictional insurance company:
- **Industry**: Insurance (Property & Casualty)
- **Size**: 15,000 employees
- **Revenue**: $8B
- **Functions**: 12 (Claims, Underwriting, Actuarial, IT, etc.)
- **Structure**: 33 sub-functions, 56 job family groups, 113 job families

---

## 2. Prerequisites & Installation

### System Requirements

| Component | Required | Purpose |
|-----------|----------|---------|
| Python | 3.9+ | Runtime |
| Neo4j | 4.4+ or 5.x | Graph database |
| Anthropic API Key | Yes (for Phase 1 data generation) | LLM-generated workforce data |
| Flask | 3.x | Web UI server |
| pip | Latest | Package management |

### Step-by-Step Installation

```bash
# 1. Clone the repository (if not already)
git clone <repo-url>
cd draup_world_model_graph

# 2. Start Neo4j (Docker Compose - recommended)
cd draup_world_model/digital_twin
docker compose up -d
cd ../..
# Neo4j Browser: http://localhost:7474  (neo4j / kg123456)

# 3. Install the main package (includes all dependencies)
pip install -e .

# 4. Install Flask for the UI (if not already installed)
pip install flask

# 5. Set your Anthropic API key (only needed for Phase 1 data generation)
export ANTHROPIC_API_KEY="sk-ant-..."
```

The docker-compose file handles Neo4j with the correct credentials, database name, and memory settings. No other environment variables are needed - the defaults match.

### Verifying Installation

```bash
# Check Python imports work
python -c "from draup_world_model.digital_twin.config import CompanyProfile; print('OK')"

# Check Neo4j connection (requires running Neo4j via docker compose)
python -c "
from draup_world_model.digital_twin.config import get_dt_neo4j_connection
conn = get_dt_neo4j_connection()
print('Neo4j connected')
conn.close()
"

# Check Flask UI imports
python -c "from draup_world_model.digital_twin.ui.app import create_app; print('UI OK')"
```

### Neo4j Setup

**Recommended: use the included docker-compose** (see above). If you prefer a different approach:

```bash
# Option A: Docker Compose (included, recommended)
cd draup_world_model/digital_twin
docker compose up -d
# Credentials: neo4j / kg123456, database: draup
# Browser: http://localhost:7474, Bolt: bolt://localhost:7687

# Option B: Standalone Docker container
docker run -d \
  --name neo4j-dt \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/kg123456 \
  neo4j:5.15

# Option B: Neo4j Desktop
# Download from https://neo4j.com/download/
# Create a new database and start it

# Option C: Neo4j Aura (cloud)
# Create a free instance at https://neo4j.com/cloud/aura/
```

After Neo4j is running, open `http://localhost:7474` in your browser to verify.

### Neo4j Connection Safety

**The Digital Twin uses its own connection config (`DTNeo4jConfig`) — completely isolated from production.**

| Setting | Env Var | Default (matches docker-compose.yml) |
|---------|---------|--------------------------------------|
| URI | `DT_NEO4J_URI` | `bolt://localhost:7687` |
| User | `DT_NEO4J_USER` | `neo4j` |
| Password | `DT_NEO4J_PASSWORD` | `kg123456` |
| Database | `DT_NEO4J_DATABASE` | `draup` |

**Why separate env vars?** The main application uses `NEO4J_URI`, `NEO4J_PASSWORD`, etc. (from `draup_world_model/config.py`). If you set those for production in a `.env` file, the Digital Twin will **not** inherit them — it only reads `DT_NEO4J_*` variables.

All three Digital Twin entry points use this isolated connection:
- `scripts/load_graph.py` — graph loading (Phase 2)
- `scripts/run_simulation.py` — simulation engine (Phase 3)
- `ui/app.py` — Flask dashboard (Phase 4)

```python
# CLI override is also available:
python -m draup_world_model.digital_twin.scripts.load_graph \
    --neo4j-uri bolt://custom-host:7687 \
    --neo4j-password my_password
```

---

## 3. Architecture Overview

### Package Structure

```
draup_world_model/digital_twin/
│
├── __init__.py                          # Package init, version = "0.1.0"
├── config.py                            # All config + DTNeo4jConfig (isolated connection)
│
├── models/                              # Data models (pure Python dataclasses)
│   ├── taxonomy.py                     #   Organization, Function, SubFunction, JFG, JF
│   ├── workforce.py                    #   Role, JobTitle
│   ├── work_content.py                 #   Workload, Task
│   ├── capabilities.py                 #   Skill, Technology
│   └── workflow.py                     #   Workflow, WorkflowTask
│
├── generators/                          # LLM-powered data generation (Phase 1)
│   ├── base_generator.py              #   Base class: LLM calls, JSON parsing, retry
│   ├── taxonomy_generator.py          #   Seed data (no LLM needed)
│   ├── role_generator.py              #   LLM: roles + job titles per function
│   ├── workload_generator.py          #   LLM: workloads per role
│   ├── task_generator.py              #   LLM: tasks per workload
│   ├── skill_generator.py             #   LLM: skill catalog + role mappings
│   ├── technology_generator.py        #   LLM: technology catalog + role mappings
│   └── workflow_generator.py          #   LLM: workflows per function
│
├── graph/                               # Neo4j graph operations (Phase 2)
│   ├── schema.py                      #   Node labels, relationships, constraints
│   ├── queries.py                     #   Cypher query library (MERGE, LINK, GET)
│   ├── loader.py                      #   JSON → Neo4j batch loader
│   ├── aggregation.py                 #   Bottom-up metric computation
│   └── validator.py                   #   Integrity checks + readiness scoring
│
├── simulation/                          # Simulation engine (Phase 3)
│   ├── scope_selector.py              #   Select organizational scope from graph
│   ├── cascade_engine.py              #   8-step cascade propagation
│   ├── financial.py                   #   Financial projection (savings, ROI)
│   ├── scenario_manager.py            #   Scenario CRUD + comparison
│   └── simulations/                   #   Specific simulation implementations
│       ├── role_redesign.py           #     S1: Automation impact on roles
│       ├── tech_adoption.py           #     S6: Technology deployment impact
│       └── skills_strategy.py         #     S4: Skills sunrise/sunset analysis
│
├── ui/                                  # Enterprise UI (Phase 4)
│   ├── __init__.py
│   ├── app.py                         #   Flask application
│   ├── api.py                         #   REST API Blueprint (10 endpoints)
│   ├── templates/
│   │   └── index.html                 #   Single-page app shell
│   └── static/js/
│       ├── app.js                     #   Main React app + router
│       ├── components.js              #   Shared UI components
│       └── views/
│           ├── Dashboard.js           #   Readiness + overview
│           ├── Explorer.js            #   Taxonomy navigation
│           ├── Simulator.js           #   Config + run simulations
│           ├── Results.js             #   Cascade results display
│           └── Comparison.js          #   Multi-scenario comparison
│
├── scripts/                             # CLI orchestration
│   ├── generate_all.py                #   Phase 1: run all generators
│   ├── assemble_role_skill_map.py     #   Phase 1.5: task-skill mapping (LLM)
│   ├── load_graph.py                  #   Phase 2: load into Neo4j
│   └── run_simulation.py             #   Phase 3: run simulations
│
├── data/acme_corp/                      # Generated data (per-function dirs)
│   ├── taxonomy.json                  #   Seed taxonomy (single file)
│   ├── roles/                         #   Per-function role files
│   │   ├── func_claims_management.json
│   │   └── ...
│   ├── job_titles/                    #   Per-function title files
│   ├── workloads/                     #   Per-function workload files
│   ├── tasks/                         #   Per-function task files
│   ├── skills/
│   │   └── catalog.json               #   Single catalog file
│   ├── technologies/
│   │   └── catalog.json               #   Single catalog file
│   ├── workflows/                     #   Per-function workflow files
│   └── role_skill_mapping/            #   Per-function task→skill mapping
│
└── docs/                                # Design documents
    ├── implementation_progress.md
    ├── digital_twin_implementation_plan.md
    ├── digital_twin_comprehensive_v2_1.md
    ├── digital_twin_expanded_capabilities_v1.1.md
    └── digital_twin_addendum_v0.3.md
```

### Data Flow (End to End)

```
Step 1: Generate Data (per-function directory output)
  taxonomy_generator.py → taxonomy.json (seed, no LLM)
  role_generator.py → roles/{func_id}.json + job_titles/{func_id}.json (LLM)
  workload_generator.py → workloads/{func_id}.json (LLM)
  task_generator.py → tasks/{func_id}.json (LLM)
  skill_generator.py → skills/catalog.json (LLM)
  technology_generator.py → technologies/catalog.json (LLM)
  workflow_generator.py → workflows/{func_id}.json (LLM)
  assemble_role_skill_map.py → role_skill_mapping/{func_id}.json (LLM)

Step 2: Load into Neo4j
  loader.py reads JSON → MERGE (idempotent) into Neo4j
  aggregation.py computes bottom-up metrics
  validator.py checks integrity + readiness score

Step 3: Simulate
  scope_selector.py pulls entities from graph
  cascade_engine.py propagates changes (8 steps)
  financial.py computes $$ impact
  scenario_manager.py stores + compares results

Step 4: Visualize
  api.py exposes REST endpoints
  app.py serves React SPA
  Browser renders Dashboard → Explorer → Simulator → Results → Comparison
```

### The Graph Data Model

```
(DTOrganization)
    ─[DT_CONTAINS]→ (DTFunction)
        ─[DT_CONTAINS]→ (DTSubFunction)
            ─[DT_CONTAINS]→ (DTJobFamilyGroup)
                ─[DT_CONTAINS]→ (DTJobFamily)
                    ─[DT_HAS_ROLE]→ (DTRole)
                        ─[DT_HAS_TITLE]→ (DTJobTitle)
                        ─[DT_HAS_WORKLOAD]→ (DTWorkload)
                        │   └─[DT_CONTAINS_TASK]→ (DTTask)
                        │                           └─[DT_REQUIRES_SKILL {relevance}]→ (DTSkill)
                        ─[DT_REQUIRES_SKILL]→ (DTSkill)
                        ─[DT_USES_TECHNOLOGY]→ (DTTechnology)
                        ─[DT_ADJACENT_TO]→ (DTRole)  # career adjacency

(DTWorkflowTask)
    ─[DT_PART_OF_WORKFLOW]→ (DTWorkflow)
    ─[DT_TASK_USES_ROLE]→ (DTRole)

(DTScenario)
    ─[DT_APPLIED_TO]→ (DTFunction|DTRole|DTOrganization)
    ─[DT_PRODUCES]→ (DTSimulationResult)
```

**Key design decision**: All labels are prefixed with `DT` (e.g., `DTRole` not `Role`). This isolates the digital twin data from any existing data in the same Neo4j database.

### Node Properties Quick Reference

| Node | Key Properties |
|------|---------------|
| DTOrganization | id, name, industry, size, revenue_millions |
| DTFunction | id, name, headcount, org_id |
| DTSubFunction | id, name, function_id |
| DTJobFamilyGroup | id, name, sub_function_id |
| DTJobFamily | id, name, job_family_group_id |
| DTRole | id, name, function_id, job_family_id, total_headcount, avg_salary, automation_score |
| DTJobTitle | id, name, role_id, function_id, career_band, level, headcount, avg_salary, typical_experience_years |
| DTWorkload | id, name, role_id, function_id, effort_allocation_pct, automation_level |
| DTTask | id, name, workload_id, function_id, classification, time_allocation_pct, automation_potential, automation_level |
| DTSkill | id, name, category, skill_type, lifecycle_status, market_demand_trend |
| DTTechnology | id, name, category, vendor, capabilities, license_cost_tier, adoption_stage |
| DTWorkflow | id, name, function_id, description, objective, priority, avg_cycle_time_hours, frequency, ai_optimization_score |
| DTWorkflowTask | id, name, workflow_id, sequence_number, role_id, automation_type, time_hours, complexity, impact_score, automation_priority |

### Workflow Data Model (JSON vs Neo4j)

Workflows are the richest data entity. Each workflow JSON file contains 16 top-level fields and each workflow task has 18 fields. Only a subset is stored in Neo4j — complex nested objects remain in the JSON files only.

**Workflow (16 fields)**:

| Field | Stored in Neo4j | Type |
|-------|:-:|------|
| id, name, function_id, description | Yes | string |
| objective, priority, frequency | Yes | string |
| avg_cycle_time_hours, ai_optimization_score | Yes | float |
| tasks | Loaded as DTWorkflowTask nodes | array |
| summary | JSON only | `{total_tasks, total_hours, automation_level, ai/human_ai/human_task_count}` |
| workflow_metrics | JSON only | `{estimated_fte_impact, estimated_time_savings, implementation_timeline, roi_potential}` |
| quick_wins | JSON only | array of quick-win opportunities |
| opportunities | JSON only | `[{opportunity_type, estimated_hours_saved, priority, recommendation, tasks}]` |
| patterns | JSON only | `[{pattern_name, description, affected_tasks, impact, recommendation}]` |
| recommendations | JSON only | `{primary_strategy, key_actions, risks, success_factors}` |

**Workflow Task (18 fields)**:

| Field | Stored in Neo4j | Type |
|-------|:-:|------|
| id, name, workflow_id, description, role_id | Yes | string |
| sequence_number | Yes | int |
| automation_type, complexity, workload, automation_priority | Yes | string |
| time_hours, impact_score | Yes | float |
| expected_output | JSON only | string |
| score_breakdown | JSON only | `{time_investment, strategic_value, error_reduction, scalability}` |
| skills_required | JSON only | array of skill names |
| primary_role | JSON only | `{title, seniority, role_id}` |
| supporting_roles | JSON only | `[{title, seniority, role_id}]` |
| dependencies | JSON only | array of sequence numbers |

### Generated Data Statistics (Acme Corp - 2 Functions)

| Entity | Count | Source |
|--------|------:|--------|
| Functions | 2 | Claims Management, Underwriting |
| Roles | 42 | 22 + 20 |
| Job Titles | 126 | ~3 per role |
| Workloads | 168 | ~4 per role |
| Tasks | 675 | ~4 per workload |
| Skills | 197 | Shared catalog |
| Technologies | 71 | Shared catalog |
| Workflows | 16 | 8 per function |
| Workflow Tasks | 240 | ~15 per workflow |
| Task-Skill Mappings | 3,094 | ~4.6 skills per task |

---

## 4. Phase 1: Data Foundation

### What This Phase Does

Generates realistic workforce data for Acme Corporation using a combination of:
- **Seed data** (taxonomy structure - hardcoded domain expertise)
- **LLM generation** (roles, workloads, tasks, skills, technologies, workflows)

### Running Data Generation

```bash
# Generate everything (requires ANTHROPIC_API_KEY)
python -m draup_world_model.digital_twin.scripts.generate_all

# Generate only taxonomy (no LLM needed)
python -m draup_world_model.digital_twin.scripts.generate_all --step taxonomy

# Resume from a specific step (if previous run was interrupted)
python -m draup_world_model.digital_twin.scripts.generate_all --resume-from workloads

# Force-clean and regenerate a specific step
python -m draup_world_model.digital_twin.scripts.generate_all --step roles --clean

# Generate for only a few functions first (saves LLM cost for testing)
python -m draup_world_model.digital_twin.scripts.generate_all --num-functions 3
python -m draup_world_model.digital_twin.scripts.generate_all --functions "Claims Management,Underwriting"

# Use a specific model
python -m draup_world_model.digital_twin.scripts.generate_all --model claude-haiku-4-5-20251001

# Adjust temperature (0.0 = deterministic, 1.0 = creative)
python -m draup_world_model.digital_twin.scripts.generate_all --temperature 0.3
```

### Generation Pipeline (Per-Function Directory Output)

Each entity type is stored in its own directory with per-function files.
This provides failure resilience (partial progress is preserved) and smaller files.

```
Step 1: Taxonomy          (seed)              →  taxonomy.json
Step 2: Roles             (LLM, per function) →  roles/{func_id}.json + job_titles/{func_id}.json
Step 3: Workloads         (LLM, per function) →  workloads/{func_id}.json
Step 4: Tasks             (LLM, per function) →  tasks/{func_id}.json
Step 5: Skills            (LLM, catalog)      →  skills/catalog.json
Step 6: Technologies      (LLM, catalog)      →  technologies/catalog.json
Step 7: Workflows         (LLM, per function) →  workflows/{func_id}.json
Step 8: Role Skill Mapping (LLM, per role)    →  role_skill_mapping/{func_id}.json
```

**Resumability**: Role and workflow generators automatically skip functions that
already have output files. If generation fails midway through (e.g., function 8 of 12),
re-running the step picks up from function 9. Use `--clean` to force fresh generation.

**Partial generation**: Use `--num-functions N` or `--functions "name1,name2"` to generate
data for a subset of functions. This lets you test the full pipeline end-to-end with
minimal LLM cost, then expand later by re-running without the filter.

Each step reads the output of previous steps. You can run them individually or all at once.

### LLM Cost Optimization

The generation pipeline is designed to minimize LLM API costs:
- **Batch prompting**: Multiple items generated per call (e.g., all roles for a function in one call)
- **Default model**: `claude-haiku-4-5-20251001` (cheapest, fastest)
- **Low temperature**: 0.3 (more deterministic, less variation)
- **Total estimated calls**: ~105 (vs 500+ if done one-at-a-time)

| Step | Calls | Items per Call |
|------|-------|---------------|
| Taxonomy | 0 | Seed data |
| Roles | ~12 | 1 call per function |
| Workloads | ~15-20 | ~10 roles per call |
| Tasks | ~30-40 | ~15 workloads per call |
| Skills | ~2-3 | Full catalog + mapping |
| Technologies | ~2-3 | Full catalog + mapping |
| Workflows | ~24 | 1 skeleton + 8 task calls per function |
| Role Skill Mapping | ~150+ | 1 call per role (all tasks) |

### The Taxonomy (Seed Data)

The taxonomy is **not LLM-generated**. It's hardcoded domain expertise in `taxonomy_generator.py`:

| Function | Headcount | Sub-Functions |
|----------|-----------|---------------|
| Claims Management | 2,500 | Claims Processing, Claims Investigation, Claims Leadership |
| Underwriting | 1,500 | Risk Assessment, Policy Underwriting, Reinsurance |
| Customer Service | 2,000 | Contact Center, Customer Experience |
| Sales and Distribution | 2,000 | Agency Management, Direct Sales, Digital Sales |
| Information Technology | 1,500 | App Dev, Infrastructure, Data Eng, IT Ops |
| Policy Administration | 1,200 | Policy Servicing, Billing and Collections |
| Finance and Accounting | 1,000 | Financial Planning, Accounting, Treasury |
| Operations and Strategy | 1,000 | Business Ops, Corporate Strategy, Risk Management |
| Actuarial and Analytics | 800 | Actuarial Science, Data Analytics |
| Legal and Compliance | 600 | Legal, Regulatory Compliance |
| Human Resources | 500 | Talent Acquisition, L&D, HR Operations |
| Marketing and Communications | 400 | Brand, Digital, Product Marketing |
| **TOTAL** | **15,000** | **33 sub-functions** |

### Data Model Reference

#### Task Classification System (Etter 6-category AI Automation Potential)
```python
TASK_CLASSIFICATIONS = [
    "directive",        # Fully automatable tasks with minimal human input
    "feedback_loop",    # Automatable tasks requiring feedback adjustments
    "learning",         # Tasks requiring knowledge acquisition and understanding
    "validation",       # Tasks where AI helps verify and improve work
    "task_iteration",   # Tasks needing human-AI collaboration
    "negligibility",    # Tasks that cannot be automated using AI
]
```

#### Automation Levels (5-level)
```python
AUTOMATION_LEVELS = [
    "human_only",    # No automation possible
    "human_led",     # Human primary, AI assists
    "shared",        # Human and AI collaborate equally
    "ai_led",        # AI primary, human supervises
    "ai_only",       # Fully automated
]
```

#### Career Bands
```python
CAREER_BANDS = [
    "entry",         # 0-2 years experience
    "mid",           # 3-5 years experience
    "senior",        # 6-10 years experience
    "lead",          # 10-15 years experience
    "principal",     # 15+ years experience
    "executive",     # C-suite / VP
]
```

---

## 5. Phase 2: Neo4j Graph Loading

### What This Phase Does

Takes the JSON files generated in Phase 1 and loads them into Neo4j as a connected graph. Then computes aggregate metrics bottom-up through the hierarchy.

### Running the Graph Loader

```bash
# Load everything (schema + nodes + relationships + aggregation + validation)
python -m draup_world_model.digital_twin.scripts.load_graph

# Drop existing DT data first, then reload
python -m draup_world_model.digital_twin.scripts.load_graph --drop-first

# Only run validation (no loading)
python -m draup_world_model.digital_twin.scripts.load_graph --validate-only

# Skip aggregation step
python -m draup_world_model.digital_twin.scripts.load_graph --skip-aggregation
```

### Load Order

The loader respects the dependency graph:

```
1. Apply schema (constraints + indexes)
2. Taxonomy nodes: Organization → Function → SubFunction → JFG → JF
3. Work entities: Roles → JobTitles → Workloads → Tasks
4. Capability entities: Skills → Technologies
5. Workflows: Workflows → WorkflowTasks
6. Relationships: all DT_CONTAINS, DT_HAS_*, DT_REQUIRES_*, etc.
   - Includes: role→skill, role→tech, task→skill (from role_skill_mapping data)
```

### Idempotency

All load operations use `MERGE` (not `CREATE`). This means:
- **Safe to re-run**: Running the loader twice produces the same result
- **No duplicates**: MERGE creates a node only if it doesn't already exist
- **Update in place**: If a node exists, MERGE updates its properties

### Bottom-Up Aggregation

After loading, the `AggregationEngine` computes metrics upward through the hierarchy:

```
Task (automation_potential)
  ↑ avg()
Workload (computed_automation_score, task_count)
  ↑ avg()
Role (computed_automation_score, workload_count, computed_headcount, computed_total_cost)
  ↑ sum(headcount), sum(cost), avg(automation)
JobFamily → JobFamilyGroup → SubFunction → Function → Organization
```

This means every level in the taxonomy has up-to-date aggregate metrics.

### Readiness Score (100-point scale)

The validator computes a readiness score across 5 dimensions:

| Dimension | Max Points | What It Measures |
|-----------|-----------|------------------|
| Taxonomy Completeness | 25 | All 6 hierarchy levels present, roles exist, titles mapped |
| Role Decomposition | 30 | Roles have workloads, workloads have 4-8 tasks, classifications present |
| Skills Architecture | 20 | Role-skill mappings, skill catalog (50+), tech catalog (20+) |
| Enterprise Context | 15 | Headcount data, salary data, aggregation computed |
| Validation & Trust | 10 | No orphan nodes, structural validity |

**Status thresholds**: >= 70 = READY, 50-69 = PARTIAL, < 50 = NOT_READY

### Schema Details

**15 Node Labels** (all DT-prefixed):
DTOrganization, DTFunction, DTSubFunction, DTJobFamilyGroup, DTJobFamily, DTRole, DTJobTitle, DTWorkload, DTTask, DTSkill, DTTechnology, DTWorkflow, DTWorkflowTask, DTScenario, DTSimulationResult

**13 Relationship Types**:
DT_CONTAINS, DT_HAS_ROLE, DT_HAS_TITLE, DT_HAS_WORKLOAD, DT_CONTAINS_TASK, DT_REQUIRES_SKILL, DT_USES_TECHNOLOGY, DT_AFFECTED_BY, DT_ADJACENT_TO, DT_PART_OF_WORKFLOW, DT_TASK_USES_ROLE, DT_APPLIED_TO, DT_PRODUCES

**10 Indexes** for performance:
- Name indexes on DTRole, DTFunction, DTSkill, DTTechnology, DTWorkflow
- Classification index on DTTask
- Automation score indexes on DTTask and DTRole
- Workflow task lookup on DTWorkflowTask (workflow_id)
- Scenario name index on DTScenario

**Relationship Properties**:
- `DT_REQUIRES_SKILL` (from DTTask): `relevance` property (PRIMARY or SECONDARY)

---

## 6. Phase 3: Simulation Engine

> This is the heart of the system. See also: [Simulation Deep-Dive Guide](../simulation/SIMULATION_GUIDE.md)

### Core Concept: The 8-Step Cascade

When you change something (e.g., "automate 50% of Claims tasks"), the effect cascades through 8 steps:

```
Step 1: TASK RECLASSIFICATION
  Which tasks change automation level? (e.g., human_led → shared)

Step 2: WORKLOAD RECOMPOSITION
  How do workloads shift when their tasks change?

Step 3: ROLE/TITLE IMPACT
  How much capacity is freed per role?
  (Entry-level roles feel 1.4x the impact of senior roles)

Step 4: SKILL SHIFTS
  Which skills become sunrise (needed more) vs. sunset (needed less)?

Step 5: WORKFORCE RECALCULATION
  How many FTEs are freed? How many can be redeployed?

Step 6: FINANCIAL PROJECTION
  What are the savings? What are the costs? What's the ROI?

Step 7: RISK ASSESSMENT
  What risks does this change introduce?
  (high automation >60%, workforce reduction >20%, skill gaps, broad changes)

Step 8: BOUNDARY VALIDATION
  Are all values within acceptable ranges?
```

### Running Simulations (CLI)

```bash
# Role redesign: automate 50% of Claims tasks
python -m draup_world_model.digital_twin.scripts.run_simulation \
  --type role_redesign \
  --scope "Claims Management" \
  --factor 0.5

# Technology adoption: deploy Microsoft Copilot to Underwriting
python -m draup_world_model.digital_twin.scripts.run_simulation \
  --type tech_adoption \
  --scope "Underwriting" \
  --tech "Microsoft Copilot"

# List available technology profiles
python -m draup_world_model.digital_twin.scripts.run_simulation --list-tech
```

### Available Simulations

| Simulation | Code | Description |
|-----------|------|-------------|
| Role Redesign (S1) | `role_redesign.py` | Apply an automation factor (0-1) to reclassify tasks and compute cascade |
| Technology Adoption (S6) | `tech_adoption.py` | Deploy a specific technology, match tasks by keywords, compute impact |
| Skills Strategy (S4) | `skills_strategy.py` | Analyze sunrise/sunset skills, concentration risk, build-vs-buy |

### Technology Profiles (6 Pre-Built)

| Technology | Vendor | Task Keywords | Speed |
|-----------|--------|--------------|-------|
| Microsoft Copilot | Microsoft | document, draft, summarize, email, report, analysis | fast |
| UiPath RPA | UiPath | process, enter, validate, extract, reconcile, transfer | moderate |
| ServiceNow AI | ServiceNow | ticket, request, incident, workflow, approve, escalate | moderate |
| Salesforce Einstein | Salesforce | lead, opportunity, forecast, customer, pipeline, engage | fast |
| Claims AI Platform | Internal | claim, assess, evaluate, investigate, adjudicate, detect | slow |
| GitHub Copilot | GitHub | code, develop, test, review, debug, deploy, script | fast |

### Scenario Manager

The `ScenarioManager` stores simulation runs and lets you compare them:

```python
from draup_world_model.digital_twin.simulation.scenario_manager import (
    ScenarioManager, ScenarioConfig
)

# Create scenarios
config1 = ScenarioConfig(
    name="Conservative", simulation_type="role_redesign",
    scope_type="function", scope_name="Claims Management",
    parameters={"automation_factor": 0.2}, timeline_months=36,
)
config2 = ScenarioConfig(
    name="Aggressive", simulation_type="role_redesign",
    scope_type="function", scope_name="Claims Management",
    parameters={"automation_factor": 0.8}, timeline_months=36,
)

manager = ScenarioManager(neo4j_conn)
id1 = manager.create_scenario(config1)
id2 = manager.create_scenario(config2)

# Run both
manager.run_scenario(id1)
manager.run_scenario(id2)

# Compare side-by-side
comparison = manager.compare_scenarios([id1, id2])
# → {best_by_roi: "Aggressive", lowest_risk: "Conservative", scenarios: [...]}
```

---

## 7. Phase 4: UI & Integration

> For detailed UI setup, see: [UI Guide](../ui/README.md)
> For API endpoint reference, see: [API Reference](../ui/API_REFERENCE.md)

### Quick Start

```bash
# Start the UI server
python -m draup_world_model.digital_twin.ui.app

# Open in browser
open http://localhost:5001
```

### Tech Stack (No Build Step)

The UI intentionally avoids a build pipeline (no webpack, no npm, no node_modules). Everything loads from CDN:

| Library | Version | Purpose | CDN |
|---------|---------|---------|-----|
| React | 18 | UI framework | unpkg.com |
| ReactDOM | 18 | DOM rendering | unpkg.com |
| htm | 3 | JSX alternative (tagged templates) | unpkg.com |
| Tailwind CSS | 3 | Utility-first CSS | cdn.tailwindcss.com |
| Chart.js | 4.4 | Charts and visualizations | cdn.jsdelivr.net |

**Why no build step?** This is a prototype. Build tooling (webpack, vite, etc.) adds complexity without adding value at this stage. When the UI matures, you can migrate to a proper build setup.

### Views

| View | Purpose | URL Path |
|------|---------|----------|
| Dashboard | Readiness score, graph overview, quick actions | `/` |
| Explorer | Taxonomy tree navigation, entity details | `#explorer` |
| Simulator | Configure and run simulations | `#simulator` |
| Results | View cascade results (financial, workforce, skills, risk) | `#results` |
| Comparison | Multi-scenario side-by-side with radar chart | `#comparison` |

### Architecture

```
Browser (React SPA)
    ↕ JSON (fetch API)
Flask App (app.py)
    ├── Serves index.html → loads React + all JS
    └── Registers API Blueprint (api.py)
        ├── /api/dt/readiness → GraphValidator
        ├── /api/dt/taxonomy → Cypher queries → tree
        ├── /api/dt/simulate → ScenarioManager.run_scenario()
        └── /api/dt/compare → ScenarioManager.compare_scenarios()
            ↕
        Neo4j (graph database)
```

---

## 8. Configuration Reference

All configuration lives in `config.py` as dataclasses:

### CompanyProfile
```python
@dataclass
class CompanyProfile:
    name: str = "Acme Corporation"
    industry: str = "Insurance"
    sub_industry: str = "Property & Casualty"
    size: int = 15000
    revenue_millions: int = 8000
    hq_location: str = "Hartford, CT"
    description: str = "..."
```

### LLMConfig
```python
@dataclass
class LLMConfig:
    model: str = "claude-haiku-4-5-20251001"  # Cheapest Claude model
    temperature: float = 0.3                   # Low = more deterministic
    max_tokens: int = 4096                     # Max response length
```

### GenerationConfig
```python
@dataclass
class GenerationConfig:
    roles_per_function_batch: int = 1    # 1 LLM call per function
    workloads_per_batch: int = 10        # 10 roles per batch call
    tasks_per_batch: int = 15            # 15 workloads per batch call
```

### OutputConfig
```python
@dataclass
class OutputConfig:
    base_dir: Path = Path("draup_world_model/digital_twin/data/acme_corp")
    taxonomy_file: Path    # base_dir / "taxonomy.json"
    roles_file: Path       # base_dir / "roles.json"
    job_titles_file: Path  # base_dir / "job_titles.json"
    workloads_file: Path   # base_dir / "workloads.json"
    tasks_file: Path       # base_dir / "tasks.json"
    skills_file: Path      # base_dir / "skills.json"
    technologies_file: Path # base_dir / "technologies.json"
    workflows_file: Path   # base_dir / "workflows.json"
```

### Environment Variables
```bash
ANTHROPIC_API_KEY     # Required for LLM data generation
NEO4J_URI             # Neo4j connection URI (default: bolt://localhost:7687)
NEO4J_USERNAME        # Neo4j username (default: neo4j)
NEO4J_PASSWORD        # Neo4j password
DT_UI_PORT            # UI server port (default: 5001)
```

---

## 9. Troubleshooting

### "Neo4j connection failed"
- Check Neo4j is running: `curl http://localhost:7474`
- Check environment variables: `echo $NEO4J_URI`
- Check credentials: try logging into Neo4j Browser at `http://localhost:7474`

### "ANTHROPIC_API_KEY not set"
- Set it: `export ANTHROPIC_API_KEY="sk-ant-..."`
- This is only needed for Phase 1 (data generation)

### "File not found: taxonomy.json"
- Run taxonomy generation first: `python -m draup_world_model.digital_twin.scripts.generate_all --step taxonomy`
- Check the data directory: `ls draup_world_model/digital_twin/data/acme_corp/`

### "No tasks matched" (empty simulation)
- The scope might not have data. Check: `python -m draup_world_model.digital_twin.scripts.load_graph --validate-only`
- Make sure you've loaded data into Neo4j (Phase 2) before running simulations (Phase 3)

### "Port 5001 already in use"
- Change the port: `DT_UI_PORT=5002 python -m draup_world_model.digital_twin.ui.app`

### UI loads but shows errors
- Check browser console (F12 → Console tab) for JavaScript errors
- Check the Flask terminal for API errors
- Make sure Neo4j is running and loaded with data

---

## 10. Systems Thinking Notes

This package is designed with Donella Meadows' systems thinking principles in mind:

### "Structure determines behavior" (Schema Design)
The graph schema is the structural contract. It determines what questions the twin can answer. If you don't model role-skill relationships, you can't simulate skill gaps.

### "Stocks accumulate flows" (Aggregation)
The aggregation engine computes "stocks" (headcount, cost, automation score) at every taxonomy level. These accumulated values are what make dashboard views possible.

### "Information flows are the lifeblood" (The Cascade)
The 8-step cascade *is* the information flow. When tasks change, the signal propagates through workloads → roles → skills → workforce → financials → risk. If you cut any connection, the cascade breaks.

### "Leverage points" (Simulation Parameters)
The automation_factor and technology selection are leverage points. A small change (0.3 factor) has proportionally smaller effects. A large change (0.9 factor) can trigger risk flags and fundamental role redesign. The system responds non-linearly.

### "Bounded rationality" (Level-Specific Impact)
Entry-level roles experience 1.4x the automation impact of senior roles. This models the real-world pattern: routine tasks (more common in entry roles) are more automatable than strategic tasks (more common in senior roles).

### "System boundaries matter" (DT Prefix)
The DT prefix on all labels is a boundary decision. It keeps the digital twin isolated from the rest of the graph. Without this boundary, simulation data could corrupt real organizational data.

---

## Quick Reference: All Commands

```bash
# Phase 1: Generate data (per-function directory output)
python -m draup_world_model.digital_twin.scripts.generate_all
python -m draup_world_model.digital_twin.scripts.generate_all --step taxonomy
python -m draup_world_model.digital_twin.scripts.generate_all --resume-from workloads
python -m draup_world_model.digital_twin.scripts.generate_all --step roles --clean  # force-regenerate
python -m draup_world_model.digital_twin.scripts.generate_all --step role_skill_mapping  # task→skill mapping

# Task-skill mapping (standalone)
python -m draup_world_model.digital_twin.scripts.assemble_role_skill_map
python -m draup_world_model.digital_twin.scripts.assemble_role_skill_map --no-llm  # testing mode

# Phase 2: Load into Neo4j
python -m draup_world_model.digital_twin.scripts.load_graph
python -m draup_world_model.digital_twin.scripts.load_graph --drop-first
python -m draup_world_model.digital_twin.scripts.load_graph --validate-only

# Phase 3: Run simulations (CLI)
python -m draup_world_model.digital_twin.scripts.run_simulation --type role_redesign --scope "Claims Management" --factor 0.5
python -m draup_world_model.digital_twin.scripts.run_simulation --type tech_adoption --scope "Underwriting" --tech "Microsoft Copilot"
python -m draup_world_model.digital_twin.scripts.run_simulation --list-tech

# Phase 4: Launch UI
python -m draup_world_model.digital_twin.ui.app
```
