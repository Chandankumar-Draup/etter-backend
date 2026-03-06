# Phase 2: Neo4j Graph Schema — Complete Reference

> **Purpose**: This document is the definitive reference for all graph nodes,
> relationships, properties, constraints, indexes, aggregation pipeline,
> and validation logic in the Digital Twin Neo4j database.
> Simulation (Phase 3) and UI (Phase 4) use this as the source of truth
> for querying and understanding the graph structure.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Node Labels & Properties](#node-labels--properties)
3. [Relationship Types & Properties](#relationship-types--properties)
4. [Graph Schema Diagram](#graph-schema-diagram)
5. [Constraints & Indexes](#constraints--indexes)
6. [Data Loading Pipeline](#data-loading-pipeline)
7. [Aggregation Pipeline](#aggregation-pipeline)
8. [Read Queries (Simulation Engine)](#read-queries-simulation-engine)
9. [Validation & Readiness Scoring](#validation--readiness-scoring)
10. [Computed Properties Reference](#computed-properties-reference)

---

## Design Principles

1. **DT-Prefix Isolation**: All node labels start with `DT` and all relationship types
   start with `DT_` to prevent collision with the main Draup graph database.
2. **MERGE Idempotency**: All write queries use `MERGE` (not `CREATE`) so the load
   pipeline can be re-run safely without duplicating data.
3. **Batch UNWIND**: Bulk writes use `UNWIND $items AS item` for performance.
4. **Bottom-Up Aggregation**: Headcount, cost, and automation scores are computed
   bottom-up from tasks → workloads → roles → job families → functions → org.
5. **Separate Database**: Uses `DT_NEO4J_*` environment variables, never the
   production connection.

---

## Node Labels & Properties

### 1. DTOrganization

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | seed | Unique identifier (`"org_acme"`) |
| `name` | string | seed | `"Acme Corporation"` |
| `industry` | string | seed | `"Insurance"` |
| `sub_industry` | string | seed | `"Multi-line Insurance (Life, Health, P&C)"` |
| `size` | int | seed | 15000 |
| `revenue_millions` | int | seed | 8000 |
| `hq_location` | string | seed | `"Chicago, IL"` |
| `description` | string | seed | Company background |
| `computed_headcount` | int | **aggregated** | Sum from functions |
| `computed_total_cost` | int | **aggregated** | Total salary cost |
| `automation_score` | float | **aggregated** | Avg across functions |

### 2. DTFunction

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | seed | `"func_claims_management"` etc. |
| `name` | string | seed | Function name |
| `org_id` | string | seed | FK to DTOrganization |
| `headcount` | int | seed | Assigned headcount |
| `description` | string | seed | Function description |
| `computed_headcount` | int | **aggregated** | Sum from sub-functions |
| `computed_total_cost` | int | **aggregated** | Total salary cost |
| `automation_score` | float | **aggregated** | Avg automation score |

### 3. DTSubFunction

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | seed | `"sf_claims_processing"` etc. |
| `name` | string | seed | SubFunction name |
| `function_id` | string | seed | FK to DTFunction |
| `headcount` | int | seed | (optional) |
| `description` | string | seed | (optional) |
| `total_headcount` | int | **aggregated** | Sum from JFGs |
| `total_cost` | int | **aggregated** | Total salary cost |
| `automation_score` | float | **aggregated** | Avg automation score |

### 4. DTJobFamilyGroup

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | seed | `"jfg_claims_adjusters"` etc. |
| `name` | string | seed | Group name |
| `sub_function_id` | string | seed | FK to DTSubFunction |
| `description` | string | seed | (optional) |
| `total_headcount` | int | **aggregated** | Sum from JFs |
| `total_cost` | int | **aggregated** | Total salary cost |
| `automation_score` | float | **aggregated** | Avg automation score |

### 5. DTJobFamily

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | seed | `"jf_pc_claims_adjusters"` etc. |
| `name` | string | seed | Family name |
| `job_family_group_id` | string | seed | FK to DTJobFamilyGroup |
| `description` | string | seed | (optional) |
| `total_headcount` | int | **aggregated** | Sum from roles |
| `total_cost` | int | **aggregated** | Total salary cost |
| `avg_salary` | int | **aggregated** | Weighted average |
| `automation_score` | float | **aggregated** | Avg from roles |

### 6. DTRole

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"role_senior_claims_adjuster_pc"` |
| `name` | string | LLM | Role name |
| `function_id` | string | LLM | FK to DTFunction |
| `job_family_id` | string | LLM | FK to DTJobFamily |
| `description` | string | LLM | Role responsibilities |
| `total_headcount` | int | LLM | Employee count |
| `avg_salary` | int | LLM | Average salary |
| `automation_score` | float | LLM | 0-100 automation potential |
| `computed_automation_score` | float | **aggregated** | From workload averages |
| `computed_headcount` | int | **aggregated** | Sum from job titles |
| `computed_total_cost` | int | **aggregated** | headcount * salary |
| `computed_avg_salary` | int | **aggregated** | Weighted from titles |
| `workload_count` | int | **aggregated** | Number of workloads |

### 7. DTJobTitle

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"title_senior_claims_adjuster"` |
| `name` | string | LLM | Job title |
| `role_id` | string | LLM | FK to DTRole |
| `function_id` | string | LLM | FK to DTFunction |
| `career_band` | string | LLM | entry/mid/senior/lead/principal/director/vp/c_suite |
| `level` | int | LLM | Numeric level within band |
| `typical_experience_years` | int | LLM | Years experience |
| `headcount` | int | LLM | Employees with this title |
| `avg_salary` | int | LLM | Salary for this level |

### 8. DTWorkload

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"wl_role_name_workload_name"` |
| `name` | string | LLM | Workload name |
| `role_id` | string | LLM | FK to DTRole |
| `function_id` | string | LLM | FK to DTFunction |
| `description` | string | LLM | What this work covers |
| `effort_allocation_pct` | float | LLM | % of role's time |
| `automation_level` | string | LLM | human_only/human_led/shared/ai_led/ai_only |
| `computed_automation_score` | float | **aggregated** | Avg from tasks |
| `task_count` | int | **aggregated** | Number of tasks |

### 9. DTTask

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"task_workload_name_task_name"` |
| `name` | string | LLM | Task name |
| `workload_id` | string | LLM | FK to DTWorkload |
| `function_id` | string | LLM | FK to DTFunction |
| `description` | string | LLM | What this task does |
| `classification` | string | LLM | Etter 6-category (see below) |
| `time_allocation_pct` | float | LLM | % of workload time |
| `automation_potential` | float | LLM | 0-100 score |
| `automation_level` | string | LLM | human_only/human_led/shared/ai_led/ai_only |

**Task Classifications (Etter Framework):**
| Value | Meaning |
|-------|---------|
| `directive` | Fully automatable |
| `feedback_loop` | Automatable with feedback |
| `learning` | Knowledge acquisition |
| `validation` | AI verification needed |
| `task_iteration` | Human-AI collaboration |
| `negligibility` | Cannot be automated |

### 10. DTSkill

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"skill_claims_processing"` |
| `name` | string | LLM | Skill name |
| `category` | string | LLM | technical/analytical/domain/leadership/communication/digital/regulatory |
| `skill_type` | string | LLM | `"core"` or `"soft"` |
| `lifecycle_status` | string | LLM | emerging/growing/stable/declining |
| `description` | string | LLM | What this skill covers |
| `market_demand_trend` | string | LLM | rising/stable/falling |

### 11. DTTechnology

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"tech_guidewire_claimcenter"` |
| `name` | string | LLM | Technology/platform name |
| `category` | string | LLM | ai_ml/automation_rpa/analytics_bi/etc. |
| `vendor` | string | LLM | Vendor name |
| `description` | string | LLM | What it does |
| `capabilities` | list[str] | LLM | 2-4 capability strings |
| `license_cost_tier` | string | LLM | low/medium/high/enterprise |
| `adoption_stage` | string | LLM | emerging/early_adopter/mainstream/mature/legacy |

### 12. DTWorkflow

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"wf_func_name_wf_name"` |
| `name` | string | LLM | Workflow name |
| `function_id` | string | LLM | FK to DTFunction |
| `description` | string | LLM | Process description |
| `objective` | string | LLM | Business objective |
| `priority` | string | LLM | high/medium/low |
| `avg_cycle_time_hours` | float | LLM | Execution duration |
| `frequency` | string | LLM | daily/weekly/monthly/quarterly/ad_hoc |
| `ai_optimization_score` | float | computed | 0-1 AI optimization score |

> **Note**: Complex workflow fields (summary, metrics, quick_wins, opportunities,
> patterns, recommendations) are stored in JSON files only, NOT in Neo4j properties.

### 13. DTWorkflowTask

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `id` | string | LLM | `"wft_wf_name_task_name"` |
| `name` | string | LLM | Task name |
| `workflow_id` | string | LLM | FK to DTWorkflow |
| `sequence_number` | int | LLM | Order (1-based) |
| `role_id` | string | LLM | FK to DTRole |
| `description` | string | LLM | What happens |
| `automation_type` | string | LLM | AI/Human+AI/Human |
| `time_hours` | float | LLM | Duration |
| `complexity` | string | LLM | simple/moderate/complex |
| `workload` | string | LLM | low/medium/high |
| `impact_score` | float | computed | 0-20 importance score |
| `automation_priority` | string | LLM | high/medium/low |

> **Note**: Complex fields (score_breakdown, skills_required, primary_role,
> supporting_roles, dependencies, expected_output) are stripped before Neo4j
> loading and stored in JSON files only.

### 14-16. Simulation Labels (reserved)

| Label | Purpose |
|-------|---------|
| `DTScenario` | Simulation scenario configuration |
| `DTSimulationResult` | Simulation output data |

---

## Relationship Types & Properties

### Containment Hierarchy

| Relationship | Source | Target | Properties |
|-------------|--------|--------|------------|
| `DT_CONTAINS` | DTOrganization | DTFunction | — |
| `DT_CONTAINS` | DTFunction | DTSubFunction | — |
| `DT_CONTAINS` | DTSubFunction | DTJobFamilyGroup | — |
| `DT_CONTAINS` | DTJobFamilyGroup | DTJobFamily | — |

### Workforce Structure

| Relationship | Source | Target | Properties |
|-------------|--------|--------|------------|
| `DT_HAS_ROLE` | DTJobFamily | DTRole | — |
| `DT_HAS_TITLE` | DTRole | DTJobTitle | — |
| `DT_HAS_WORKLOAD` | DTRole | DTWorkload | — |
| `DT_CONTAINS_TASK` | DTWorkload | DTTask | — |

### Capability Mappings

| Relationship | Source | Target | Properties | Data Source |
|-------------|--------|--------|------------|-------------|
| `DT_REQUIRES_SKILL` | DTRole | DTSkill | — | `SkillGenerator` (role-level, coarse) |
| `DT_REQUIRES_SKILL` | DTTask | DTSkill | `relevance` (string: `"PRIMARY"` or `"SECONDARY"`) | `assemble_role_skill_map.py` (task-level, granular) |
| `DT_USES_TECHNOLOGY` | DTRole | DTTechnology | — | `TechnologyGenerator` |
| `DT_AFFECTED_BY` | DTTask | DTTechnology | `shift` (string), `time_reduction` (float) | Simulation engine |

> **Two-level skill mapping**: The same `DT_REQUIRES_SKILL` relationship type is used at two
> levels. Role→Skill captures which skills a role generally needs. Task→Skill is more granular:
> it tells the simulation engine exactly which skills each task requires and whether they're
> PRIMARY (essential — automation removes the need) or SECONDARY (supporting — skill still
> useful elsewhere). The task-level mapping is produced by `assemble_role_skill_map.py`
> which uses LLM to intelligently assign 3-8 skills per task from the role's skill set.
> See [`DATA_GENERATION.md`](DATA_GENERATION.md#role-skill-mapping--task-level-skill-assignment-llm-generated) for details.

### Role Adjacency

| Relationship | Source | Target | Properties |
|-------------|--------|--------|------------|
| `DT_ADJACENT_TO` | DTRole | DTRole | `score` (float) |

### Workflow Structure

| Relationship | Source | Target | Properties |
|-------------|--------|--------|------------|
| `DT_PART_OF_WORKFLOW` | DTWorkflowTask | DTWorkflow | — |
| `DT_TASK_USES_ROLE` | DTWorkflowTask | DTRole | — |

### Simulation (reserved)

| Relationship | Source | Target | Properties |
|-------------|--------|--------|------------|
| `DT_APPLIED_TO` | DTScenario | DTOrganization/DTFunction/DTRole | — |
| `DT_PRODUCES` | DTScenario | DTSimulationResult | — |

---

## Graph Schema Diagram

```
                    ┌──────────────────┐
                    │ DTOrganization   │
                    │ (Acme Corp)      │
                    └────────┬─────────┘
                             │ DT_CONTAINS
                    ┌────────▼─────────┐
                    │ DTFunction (12)  │
                    │ Claims, UW, ...  │
                    └────────┬─────────┘
                             │ DT_CONTAINS
                    ┌────────▼─────────┐
                    │ DTSubFunction    │
                    │ (~33 total)      │
                    └────────┬─────────┘
                             │ DT_CONTAINS
                    ┌────────▼─────────┐
                    │ DTJobFamilyGroup │
                    │ (~56 total)      │
                    └────────┬─────────┘
                             │ DT_CONTAINS
                    ┌────────▼─────────┐
                    │ DTJobFamily      │
                    │ (~113 total)     │
                    └────────┬─────────┘
                             │ DT_HAS_ROLE
         ┌───────────────────▼───────────────────┐
         │             DTRole (~42)               │
         │  headcount, salary, automation_score   │
         └──┬────┬────┬─────────┬───────┬────────┘
            │    │    │         │       │
 DT_HAS_   │    │    │  DT_    │       │ DT_USES_
 TITLE     │    │    │ REQUIRES│       │ TECHNOLOGY
            │    │    │ _SKILL  │       │
   ┌────────▼┐ ┌▼────▼──┐  ┌──▼───┐ ┌─▼──────────┐
   │DTJobTitle│ │DTWork- │  │DTSkill│ │DTTechnology│
   │  (~126) │ │load    │  │(197)  │ │   (71)     │
   │career_  │ │(~168)  │  └───────┘ └────────────┘
   │band,    │ │effort_%│
   │headcount│ │auto_lvl│
   └─────────┘ └───┬────┘
                    │ DT_CONTAINS_TASK
              ┌─────▼─────┐
              │ DTTask    │
              │ (~675)    │
              │classify,  │
              │auto_%,    │
              │auto_level │
              └─────┬─────┘
                    │ DT_REQUIRES_SKILL
                    │ (with relevance)
              ┌─────▼─────┐
              │ DTSkill   │
              └───────────┘

  ┌───────────────┐     DT_PART_OF_WORKFLOW    ┌────────────┐
  │DTWorkflowTask │ ───────────────────────►   │ DTWorkflow │
  │sequence, time,│                            │ priority,  │
  │automation_type│ ─── DT_TASK_USES_ROLE ──► │ frequency  │
  └───────────────┘        to DTRole           └────────────┘
```

---

## Constraints & Indexes

### Uniqueness Constraints (16 total)

One per node label, ensuring `id` is unique:

```cypher
CREATE CONSTRAINT constraint_dtorganization_id IF NOT EXISTS
  FOR (n:DTOrganization) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtfunction_id IF NOT EXISTS
  FOR (n:DTFunction) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtsubfunction_id IF NOT EXISTS
  FOR (n:DTSubFunction) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtjobfamilygroup_id IF NOT EXISTS
  FOR (n:DTJobFamilyGroup) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtjobfamily_id IF NOT EXISTS
  FOR (n:DTJobFamily) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtrole_id IF NOT EXISTS
  FOR (n:DTRole) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtjobtitle_id IF NOT EXISTS
  FOR (n:DTJobTitle) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtworkload_id IF NOT EXISTS
  FOR (n:DTWorkload) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dttask_id IF NOT EXISTS
  FOR (n:DTTask) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtskill_id IF NOT EXISTS
  FOR (n:DTSkill) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dttechnology_id IF NOT EXISTS
  FOR (n:DTTechnology) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtworkflow_id IF NOT EXISTS
  FOR (n:DTWorkflow) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtworkflowtask_id IF NOT EXISTS
  FOR (n:DTWorkflowTask) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtscenario_id IF NOT EXISTS
  FOR (n:DTScenario) REQUIRE n.id IS UNIQUE

CREATE CONSTRAINT constraint_dtsimulationresult_id IF NOT EXISTS
  FOR (n:DTSimulationResult) REQUIRE n.id IS UNIQUE
```

### Indexes (13 total)

```cypher
-- Name lookups (used by API and scope selector)
CREATE INDEX idx_dt_role_name IF NOT EXISTS FOR (n:DTRole) ON (n.name)
CREATE INDEX idx_dt_function_name IF NOT EXISTS FOR (n:DTFunction) ON (n.name)
CREATE INDEX idx_dt_skill_name IF NOT EXISTS FOR (n:DTSkill) ON (n.name)
CREATE INDEX idx_dt_tech_name IF NOT EXISTS FOR (n:DTTechnology) ON (n.name)
CREATE INDEX idx_dt_workflow_name IF NOT EXISTS FOR (n:DTWorkflow) ON (n.name)
CREATE INDEX idx_dt_scenario_name IF NOT EXISTS FOR (n:DTScenario) ON (n.name)

-- Simulation queries (classification and automation lookups)
CREATE INDEX idx_dt_task_classification IF NOT EXISTS FOR (n:DTTask) ON (n.classification)
CREATE INDEX idx_dt_task_automation IF NOT EXISTS FOR (n:DTTask) ON (n.automation_potential)
CREATE INDEX idx_dt_role_automation IF NOT EXISTS FOR (n:DTRole) ON (n.automation_score)

-- Workflow task lookup by parent workflow
CREATE INDEX idx_dt_wftask_workflow IF NOT EXISTS FOR (n:DTWorkflowTask) ON (n.workflow_id)
```

---

## Data Loading Pipeline

### Load Order

```
1. Apply schema (constraints + indexes)
2. Load taxonomy nodes:
   a. Organization (1 node)
   b. Functions (12 nodes)
   c. SubFunctions (~33 nodes)
   d. JobFamilyGroups (~56 nodes)
   e. JobFamilies (~113 nodes)
3. Load work entities:
   a. Roles (~42+ nodes)
   b. JobTitles (~126+ nodes)
   c. Workloads (~168+ nodes)
   d. Tasks (~675+ nodes)
4. Load capability entities:
   a. Skills (197 nodes)
   b. Technologies (71 nodes)
5. Load workflow entities:
   a. Workflows (~256+ nodes)
   b. WorkflowTasks (~3000+ nodes)
6. Create relationships:
   a. Containment hierarchy (org → func → sf → jfg → jf)
   b. Role structure (jf → role → title, role → workload → task)
   c. Role → Skill mappings (coarse, from roles/*.json skill_ids)
   d. Task → Skill mappings (granular, from role_skill_mapping/*.json)
      - Source: assemble_role_skill_map.py LLM output
      - Loader function: _create_task_skill_mappings()
      - Creates DT_REQUIRES_SKILL with relevance: "PRIMARY"|"SECONDARY"
   e. Technology mappings (role → technology)
   f. Role adjacency (role → role with score)
   g. Workflow structure (wf_task → workflow, wf_task → role)
7. Run aggregation pipeline (bottom-up metrics)
```

### Command

```bash
python -m draup_world_model.digital_twin.scripts.load_graph
```

### Key Detail: Two-Level Skill Mapping Loading

The loader creates skill relationships from **two distinct data sources**:

**Level 1 — Role → Skill (coarse)**
- Source files: `data/acme_corp/roles/func_*.json` → each role's `skill_ids[]`
- Cypher (`LINK_ROLE_TO_SKILLS`):
  ```cypher
  UNWIND $mappings AS mapping
  MATCH (r:DTRole {id: mapping.role_id})
  MATCH (s:DTSkill {id: mapping.skill_id})
  MERGE (r)-[:DT_REQUIRES_SKILL]->(s)
  ```
- Result: 5–12 skills per role, no relevance property

**Level 2 — Task → Skill (granular, with relevance)**
- Source files: `data/acme_corp/role_skill_mapping/func_*.json`
- Generated by: `assemble_role_skill_map.py` (LLM-driven, Step 9 of generation pipeline)
- Loader function: `loader._create_task_skill_mappings()`
- Cypher (`LINK_TASK_TO_SKILLS`):
  ```cypher
  UNWIND $mappings AS mapping
  MATCH (t:DTTask {id: mapping.task_id})
  MATCH (s:DTSkill {id: mapping.skill_id})
  MERGE (t)-[rel:DT_REQUIRES_SKILL]->(s)
  SET rel.relevance = mapping.relevance
  ```
- Result: 3–8 skills per task, with `relevance: "PRIMARY"` or `"SECONDARY"`

> **Cross-reference**: See [DATA_GENERATION.md — Role-Skill Mapping](DATA_GENERATION.md#role-skill-mapping--task-level-skill-assignment) for complete details on how the LLM determines relevance.

---

## Aggregation Pipeline

Bottom-up computation running after all data is loaded. 8 steps:

### Step 1: Workloads ← Tasks

```cypher
MATCH (wl:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
WITH wl, avg(t.automation_potential) AS avg_automation, count(t) AS task_count
SET wl.computed_automation_score = avg_automation,
    wl.task_count = task_count
```

### Step 2: Roles ← Workloads

```cypher
MATCH (r:DTRole)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
WHERE wl.computed_automation_score IS NOT NULL
WITH r, avg(wl.computed_automation_score) AS avg_automation, count(wl) AS workload_count
SET r.computed_automation_score = avg_automation,
    r.workload_count = workload_count
```

### Step 3: Roles ← Titles (Cost)

```cypher
MATCH (r:DTRole)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
WITH r, sum(jt.headcount) AS total_hc, sum(jt.headcount * jt.avg_salary) AS total_cost
SET r.computed_headcount = total_hc,
    r.computed_total_cost = total_cost,
    r.computed_avg_salary = CASE WHEN total_hc > 0 THEN total_cost / total_hc ELSE 0 END
```

### Step 4: JobFamilies ← Roles

```cypher
MATCH (jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
WITH jf, sum(coalesce(r.computed_headcount, r.total_headcount, 0)) AS total_hc,
         sum(coalesce(r.computed_total_cost, 0)) AS total_cost,
         avg(coalesce(r.computed_automation_score, r.automation_score, 0)) AS avg_auto
SET jf.total_headcount = total_hc, jf.total_cost = total_cost,
    jf.avg_salary = CASE WHEN total_hc > 0 THEN total_cost / total_hc ELSE 0 END,
    jf.automation_score = avg_auto
```

### Step 5: JobFamilyGroups ← JobFamilies

```cypher
MATCH (jfg:DTJobFamilyGroup)-[:DT_CONTAINS]->(jf:DTJobFamily)
WHERE jf.total_headcount IS NOT NULL
WITH jfg, sum(jf.total_headcount) AS total_hc, sum(jf.total_cost) AS total_cost,
          avg(jf.automation_score) AS avg_auto
SET jfg.total_headcount = total_hc, jfg.total_cost = total_cost,
    jfg.automation_score = avg_auto
```

### Step 6: SubFunctions ← JobFamilyGroups

```cypher
MATCH (sf:DTSubFunction)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
WHERE jfg.total_headcount IS NOT NULL
WITH sf, sum(jfg.total_headcount) AS total_hc, sum(jfg.total_cost) AS total_cost,
         avg(jfg.automation_score) AS avg_auto
SET sf.total_headcount = total_hc, sf.total_cost = total_cost,
    sf.automation_score = avg_auto
```

### Step 7: Functions ← SubFunctions

```cypher
MATCH (f:DTFunction)-[:DT_CONTAINS]->(sf:DTSubFunction)
WHERE sf.total_headcount IS NOT NULL
WITH f, sum(sf.total_headcount) AS total_hc, sum(sf.total_cost) AS total_cost,
        avg(sf.automation_score) AS avg_auto
SET f.computed_headcount = total_hc, f.computed_total_cost = total_cost,
    f.automation_score = avg_auto
```

### Step 8: Organization ← Functions

```cypher
MATCH (org:DTOrganization)-[:DT_CONTAINS]->(f:DTFunction)
WHERE f.computed_headcount IS NOT NULL
WITH org, sum(f.computed_headcount) AS total_hc, sum(f.computed_total_cost) AS total_cost,
          avg(f.automation_score) AS avg_auto
SET org.computed_headcount = total_hc, org.computed_total_cost = total_cost,
    org.automation_score = avg_auto
```

---

## Read Queries (Simulation Engine)

### Scope Selection

**GET_SCOPE_BY_FUNCTION** — Used by ScopeSelector to load all entities within a function:

```cypher
MATCH (f:DTFunction {name: $function_name})
OPTIONAL MATCH (f)-[:DT_CONTAINS]->(sf:DTSubFunction)
OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
OPTIONAL MATCH (role)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
RETURN f, sf, jfg, jf, role, jt, wl, task, skill, tech
```

**GET_SCOPE_BY_ROLE** — Single-role scope:

```cypher
MATCH (role:DTRole {name: $role_name})
OPTIONAL MATCH (role)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
RETURN role, jt, wl, task, skill, tech
```

### Role Analysis

**GET_ROLE_WITH_FULL_DECOMPOSITION** — Complete role breakdown:

```cypher
MATCH (role:DTRole {id: $role_id})
OPTIONAL MATCH (role)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
RETURN role, collect(DISTINCT jt) AS titles,
       collect(DISTINCT wl) AS workloads,
       collect(DISTINCT task) AS tasks,
       collect(DISTINCT skill) AS skills,
       collect(DISTINCT tech) AS technologies
```

**GET_ROLE_WORKLOAD_TASK_SKILLS** — Role → workload → task → skill chain:

```cypher
MATCH (role:DTRole {id: $role_id})
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (task)-[rs:DT_REQUIRES_SKILL]->(skill:DTSkill)
RETURN role, wl, task, skill, rs.relevance AS relevance
ORDER BY wl.name, task.name
```

### Graph Statistics

**COUNT_NODES** — All DT-prefixed node counts:

```cypher
MATCH (n) WHERE any(label IN labels(n) WHERE label STARTS WITH 'DT')
RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label
```

**COUNT_RELATIONSHIPS** — All DT-prefixed relationship counts:

```cypher
MATCH ()-[r]->() WHERE type(r) STARTS WITH 'DT_'
RETURN type(r) AS rel_type, count(r) AS count ORDER BY rel_type
```

---

## Validation & Readiness Scoring

### Integrity Checks

| Check | Query | Meaning |
|-------|-------|---------|
| Orphan Roles | `MATCH (r:DTRole) WHERE NOT (:DTJobFamily)-[:DT_HAS_ROLE]->(r)` | Roles not linked to any job family |
| Orphan Tasks | `MATCH (t:DTTask) WHERE NOT (:DTWorkload)-[:DT_CONTAINS_TASK]->(t)` | Tasks not linked to any workload |
| Roles w/o Workloads | `MATCH (r:DTRole) WHERE NOT (r)-[:DT_HAS_WORKLOAD]->()` | Roles missing work decomposition |
| Roles w/o Skills | `MATCH (r:DTRole) WHERE NOT (r)-[:DT_REQUIRES_SKILL]->()` | Roles missing capability data |

### Readiness Score (100 points)

| Dimension | Max | Criteria |
|-----------|-----|----------|
| **Taxonomy Completeness** | 25 | All 6 hierarchy levels (10), Roles exist (10), Titles mapped (5) |
| **Role Decomposition** | 30 | Workloads attached (10), Avg 4-8 tasks/workload (10), Classifications set (10) |
| **Skills Architecture** | 20 | Role-skill links (10), Skill catalog >=50 (5), Tech catalog >=20 (5) |
| **Enterprise Context** | 15 | Headcount data (5), Salary data (5), Aggregation computed (5) |
| **Validation & Trust** | 10 | No orphan nodes (5), Graph structurally valid (5) |

**Status Thresholds:**
- **READY**: >= 70 points
- **PARTIAL**: 50-69 points
- **NOT_READY**: < 50 points

---

## Computed Properties Reference

Properties added by the aggregation pipeline (not present in raw data):

| Node | Property | Computed From |
|------|----------|---------------|
| DTWorkload | `computed_automation_score` | avg(task.automation_potential) |
| DTWorkload | `task_count` | count(tasks) |
| DTRole | `computed_automation_score` | avg(workload.computed_automation_score) |
| DTRole | `workload_count` | count(workloads) |
| DTRole | `computed_headcount` | sum(title.headcount) |
| DTRole | `computed_total_cost` | sum(title.headcount * title.avg_salary) |
| DTRole | `computed_avg_salary` | total_cost / headcount |
| DTJobFamily | `total_headcount`, `total_cost`, `avg_salary`, `automation_score` | From roles |
| DTJobFamilyGroup | `total_headcount`, `total_cost`, `automation_score` | From job families |
| DTSubFunction | `total_headcount`, `total_cost`, `automation_score` | From JFGs |
| DTFunction | `computed_headcount`, `computed_total_cost`, `automation_score` | From sub-functions |
| DTOrganization | `computed_headcount`, `computed_total_cost`, `automation_score` | From functions |

---

## How to Load Data

```bash
# Start Neo4j
cd draup_world_model/digital_twin && docker compose up -d && cd ../..

# Load all generated data into graph
python -m draup_world_model.digital_twin.scripts.load_graph

# Drop all DT data (clean reset)
python -c "
from draup_world_model.digital_twin.config import get_dt_neo4j_connection
from draup_world_model.digital_twin.graph.schema import drop_all_dt_data
conn = get_dt_neo4j_connection()
drop_all_dt_data(conn)
"
```

### Environment Variables

```bash
DT_NEO4J_URI=bolt://localhost:7687    # Default
DT_NEO4J_USER=neo4j                   # Default
DT_NEO4J_PASSWORD=kg123456            # From .env or DT_NEO4J_PASSWORD
DT_NEO4J_DATABASE=draup               # Default
```
