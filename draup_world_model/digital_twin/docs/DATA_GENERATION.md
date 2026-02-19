# Phase 1: Data Generation — Complete Reference

> **Purpose**: This document is the definitive reference for all generated data entities,
> their fields, relationships, generation pipeline, and output structure.
> Simulation (Phase 3) and UI (Phase 4) use this as the source of truth for
> what data exists in the system.

---

## Table of Contents

1. [Company Profile](#company-profile)
2. [Entity Data Model](#entity-data-model)
3. [Taxonomy (Seed Data)](#taxonomy-seed-data)
4. [Workforce Entities (LLM-Generated)](#workforce-entities-llm-generated)
5. [Work Content Entities (LLM-Generated)](#work-content-entities-llm-generated)
6. [Capability Entities (LLM-Generated)](#capability-entities-llm-generated)
7. [Workflow Entities (LLM-Generated)](#workflow-entities-llm-generated)
8. [Generation Pipeline](#generation-pipeline)
9. [Output File Structure](#output-file-structure)
10. [Current Data Statistics](#current-data-statistics)
11. [Enums & Constants](#enums--constants)

---

## Company Profile

| Field | Value |
|-------|-------|
| Name | Acme Corporation |
| Industry | Insurance |
| Sub-Industry | Multi-line Insurance (Life, Health, P&C) |
| Total Employees | 15,000 |
| Revenue | $8 billion |
| HQ | Chicago, IL |

---

## Entity Data Model

### Entity Hierarchy (Parent → Child)

```
Organization (1)
 └─ Function (12)
     └─ SubFunction (~33)
         └─ JobFamilyGroup (~56)
             └─ JobFamily (~113)
                 └─ Role (~42 generated, ~200 target)
                     ├─ JobTitle (~126 generated, ~600 target)
                     ├─ Workload (~168 generated, ~800 target)
                     │   └─ Task (~675 generated, ~3000 target)
                     │       └─ Skill (many-to-many via RoleSkillMapping, with relevance)
                     ├─ Skill (many-to-many, 197 in catalog)
                     └─ Technology (many-to-many, 71 in catalog)

Workflow (~256 generated, per function)
 └─ WorkflowTask (10-15 per workflow)
     └─ Role (references existing roles)
```

> **Two distinct Skill links exist:**
> - **Role → Skill** (coarse): Which skills a role needs overall (5-12 per role, from SkillGenerator)
> - **Task → Skill** (granular): Which skills each task requires, with PRIMARY/SECONDARY relevance
>   (3-8 per task, from `assemble_role_skill_map.py`)

### Entity Relationship Summary

| Parent | Relationship | Child | Cardinality |
|--------|-------------|-------|-------------|
| Organization | contains | Function | 1:12 |
| Function | contains | SubFunction | 1:2-4 |
| SubFunction | contains | JobFamilyGroup | 1:1-3 |
| JobFamilyGroup | contains | JobFamily | 1:1-3 |
| JobFamily | has_role | Role | 1:2 |
| Role | has_title | JobTitle | 1:3-6 |
| Role | has_workload | Workload | 1:4-5 |
| Workload | contains_task | Task | 1:5-8 |
| Role | requires_skill | Skill | many:many (5-12 per role) |
| Role | uses_technology | Technology | many:many (3-8 per role) |
| Role | adjacent_to | Role | many:many |
| WorkflowTask | part_of | Workflow | many:1 |
| WorkflowTask | uses_role | Role | many:1 |

---

## Taxonomy (Seed Data)

> **Not LLM-generated** — hardcoded domain expertise for consistency.

### Organization

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `"org_acme"` |
| `name` | string | `"Acme Corporation"` |
| `industry` | string | `"Insurance"` |
| `sub_industry` | string | `"Multi-line Insurance (Life, Health, P&C)"` |
| `size` | int | `15000` |
| `revenue_millions` | int | `8000` |
| `hq_location` | string | `"Chicago, IL"` |
| `description` | string | Company background text |

### Function (12 total)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `"func_claims_management"` etc. |
| `name` | string | Human-readable name |
| `org_id` | string | Foreign key to Organization |
| `description` | string | Function description |
| `headcount` | int | Assigned employee count |

**Functions with Headcount:**

| # | Function | ID | Headcount |
|---|----------|-----|-----------|
| 1 | Claims Management | `func_claims_management` | 2,500 |
| 2 | Underwriting | `func_underwriting` | 1,500 |
| 3 | Actuarial and Analytics | `func_actuarial_and_analytics` | 800 |
| 4 | Sales and Distribution | `func_sales_and_distribution` | 2,000 |
| 5 | Policy Administration | `func_policy_administration` | 1,200 |
| 6 | Customer Service | `func_customer_service` | 2,000 |
| 7 | Information Technology | `func_information_technology` | 1,500 |
| 8 | Finance and Accounting | `func_finance_and_accounting` | 1,000 |
| 9 | Legal and Compliance | `func_legal_and_compliance` | 600 |
| 10 | Human Resources | `func_human_resources` | 500 |
| 11 | Marketing and Communications | `func_marketing_and_communications` | 400 |
| 12 | Operations and Strategy | `func_operations_and_strategy` | 1,000 |

### SubFunction (~33 total)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `"sf_claims_processing"` etc. |
| `name` | string | Human-readable name |
| `function_id` | string | Foreign key to Function |
| `description` | string | (optional) |
| `headcount` | int | (optional, computed by aggregation) |

### JobFamilyGroup (~56 total)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `"jfg_claims_adjusters"` etc. |
| `name` | string | Human-readable name |
| `sub_function_id` | string | Foreign key to SubFunction |
| `description` | string | (optional) |

### JobFamily (~113 total)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `"jf_pc_claims_adjusters"` etc. |
| `name` | string | Human-readable name |
| `job_family_group_id` | string | Foreign key to JobFamilyGroup |
| `description` | string | (optional) |

---

## Workforce Entities (LLM-Generated)

### Role

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"role_<snake_case_name>"` |
| `name` | string | — | Role title |
| `job_family_id` | string | — | FK to JobFamily |
| `description` | string | `""` | Role responsibilities |
| `total_headcount` | int | `0` | Number of employees |
| `avg_salary` | int | `0` | Average annual salary USD |
| `automation_score` | float | `0.0` | AI automation potential (0-100) |
| `skill_ids` | list[str] | `[]` | FK to Skill catalog (populated by SkillGenerator) |
| `technology_ids` | list[str] | `[]` | FK to Technology catalog (populated by TechnologyGenerator) |
| `adjacency_role_ids` | list[str] | `[]` | FKs to related roles |

**Generation**: 1 LLM call per function, generates ~2 roles per JobFamily.
**Target**: ~200 roles total across 12 functions.

**Example** (Claims Management):
```
Senior Claims Adjuster - P&C
  headcount: 285, avg_salary: $68,000, automation_score: 35
  skills: [Claims Processing, Loss Adjustment, P&C Insurance, ...]
  technologies: [Guidewire ClaimCenter, Copilot, Tableau, ...]
```

### JobTitle

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"title_<snake_case_name>"` |
| `name` | string | — | Specific job title |
| `role_id` | string | — | FK to Role |
| `career_band` | string | — | One of CAREER_BANDS |
| `level` | int | `0` | Numeric level within band |
| `typical_experience_years` | int | `0` | Years of experience |
| `headcount` | int | `0` | Employees with this title |
| `avg_salary` | int | `0` | Salary for this level |

**Generation**: ~10-15 roles per LLM call. 3-6 titles per role across career levels.
**Target**: ~600 job titles total.

---

## Work Content Entities (LLM-Generated)

### Workload

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"wl_<role>_<name>"` |
| `name` | string | — | Workload name |
| `role_id` | string | — | FK to Role |
| `description` | string | `""` | What this block of work covers |
| `effort_allocation_pct` | float | `0.0` | % of role's time (sum ~100% per role) |
| `automation_level` | string | `"human_led"` | One of AUTOMATION_LEVELS |
| `skill_ids` | list[str] | `[]` | Skills needed |

**Generation**: ~10 roles per LLM call. 4-5 workloads per role.
**Target**: ~800 workloads total.

### Task

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"task_<workload>_<name>"` |
| `name` | string | — | Atomic task name |
| `workload_id` | string | — | FK to Workload |
| `description` | string | `""` | What this task does |
| `classification` | string | `"task_iteration"` | Etter 6-category framework |
| `time_allocation_pct` | float | `0.0` | % of workload time |
| `automation_potential` | float | `0.0` | 0-100 score |
| `automation_level` | string | `"human_led"` | One of AUTOMATION_LEVELS |
| `current_tool_ids` | list[str] | `[]` | Current tools used |
| `future_tool_ids` | list[str] | `[]` | Future AI tools possible |
| `skill_ids` | list[str] | `[]` | Skills needed |

**Task Classification (Etter 6-Category AI Automation Framework):**

| Classification | Description | Automation Potential |
|---------------|-------------|---------------------|
| `directive` | Fully automatable, minimal human input | Highest |
| `feedback_loop` | Automatable with feedback adjustments | High |
| `learning` | Knowledge acquisition required | Medium |
| `validation` | AI verification/review needed | Medium |
| `task_iteration` | Human-AI collaboration required | Low-Medium |
| `negligibility` | Cannot be meaningfully automated | Lowest |

**Generation**: ~5 workloads per LLM call. 5-8 tasks per workload.
**Target**: ~3,000+ tasks total.

---

## Capability Entities (LLM-Generated)

### Skill (Global Catalog)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"skill_<snake_case_name>"` |
| `name` | string | — | Skill name |
| `category` | string | — | One of SKILL_CATEGORIES |
| `skill_type` | string | `"core"` | `"core"` or `"soft"` |
| `lifecycle_status` | string | `"stable"` | One of SKILL_LIFECYCLE |
| `description` | string | `""` | What this skill covers |
| `market_demand_trend` | string | `"stable"` | `"rising"`, `"stable"`, `"falling"` |

**Skill Categories**: `technical`, `analytical`, `domain`, `leadership`, `communication`, `digital`, `regulatory`

**Skill Lifecycle**: `emerging`, `growing`, `stable`, `declining`

**Generation**: 3 LLM calls covering category groups. Then mapping calls to assign 5-12 skills per role.
**Current Catalog**: 197 skills.

### Technology (Global Catalog)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"tech_<snake_case_name>"` |
| `name` | string | — | Technology/platform name |
| `category` | string | — | One of TECHNOLOGY_CATEGORIES |
| `vendor` | string | `""` | Vendor name |
| `description` | string | `""` | What it does |
| `capabilities` | list[str] | `[]` | 2-4 capability descriptions |
| `license_cost_tier` | string | `"medium"` | `"low"`, `"medium"`, `"high"`, `"enterprise"` |
| `adoption_stage` | string | `"mainstream"` | `"emerging"`, `"early_adopter"`, `"mainstream"`, `"mature"`, `"legacy"` |

**Technology Categories**: `ai_ml`, `automation_rpa`, `analytics_bi`, `cloud_infrastructure`, `crm_customer`, `erp_enterprise`, `communication_collaboration`, `security_compliance`, `industry_specific`, `development_tools`

**Generation**: 3 LLM calls covering category groups. Then mapping calls to assign 3-8 technologies per role.
**Current Catalog**: 71 technologies.

---

## Workflow Entities (LLM-Generated)

### Workflow

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"wf_<func>_<name>"` |
| `name` | string | — | End-to-end process name |
| `function_id` | string | — | FK to Function |
| `description` | string | `""` | Process description |
| `objective` | string | `""` | Business objective |
| `priority` | string | `"high"` | `"high"`, `"medium"`, `"low"` |
| `frequency` | string | `"daily"` | `"daily"`, `"weekly"`, `"monthly"`, `"quarterly"`, `"ad_hoc"` |
| `avg_cycle_time_hours` | float | `0.0` | Time to complete |
| `ai_optimization_score` | float | `0.0` | 0-1 AI potential |
| `tasks` | list[WorkflowTask] | `[]` | Ordered sequence of tasks |
| `summary` | dict | `{}` | Computed: total_tasks, total_hours, automation_level |
| `workflow_metrics` | dict | `{}` | Computed: fte_impact, time_savings, roi_potential |
| `quick_wins` | list[dict] | `[]` | Computed: easy automation wins |
| `opportunities` | list[dict] | `[]` | Computed: strategic opportunities |
| `patterns` | list[dict] | `[]` | Computed: AI Task Cluster, Augmentation, Bottleneck patterns |
| `recommendations` | dict | `{}` | Computed: primary_strategy, key_actions, risks |

### WorkflowTask

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | — | `"wft_<wf>_<name>"` |
| `workflow_id` | string | — | FK to Workflow |
| `sequence_number` | int | — | Order in workflow (1-based) |
| `name` | string | — | Task name |
| `role_id` | string | `""` | FK to Role performing this task |
| `description` | string | `""` | What happens |
| `expected_output` | string | `""` | Deliverable |
| `automation_type` | string | `"Human+AI"` | `"AI"`, `"Human+AI"`, `"Human"` |
| `time_hours` | float | `1.0` | Duration |
| `complexity` | string | `"moderate"` | `"simple"`, `"moderate"`, `"complex"` |
| `workload` | string | `"medium"` | `"low"`, `"medium"`, `"high"` |
| `impact_score` | float | `0.0` | Computed 0-20 score |
| `score_breakdown` | dict | `{...}` | time_investment, strategic_value, error_reduction, scalability |
| `automation_priority` | string | `"medium"` | `"high"`, `"medium"`, `"low"` |
| `dependencies` | list[int] | `[]` | Sequence numbers of prerequisites |
| `skills_required` | list[str] | `[]` | Skill names |
| `primary_role` | dict | `{}` | `{title, seniority, role_id}` |
| `supporting_roles` | list[dict] | `[]` | `[{title, seniority, role_id}]` |

**Generation**: Two-phase per function. Phase 1: workflow skeletons (1 call). Phase 2: detailed tasks per workflow (1 call each, ~10-15 tasks).
**Target**: ~8 workflows per function, ~12 tasks per workflow.

---

## Role-Skill Mapping — Task-Level Skill Assignment (LLM-Generated)

> **Script**: `scripts/assemble_role_skill_map.py`
> **Purpose**: Create granular Task→Skill mappings with PRIMARY/SECONDARY relevance.
> This is the **critical link** that connects individual tasks to the skills they require,
> powering the `(DTTask)-[:DT_REQUIRES_SKILL {relevance}]->(DTSkill)` relationship in Neo4j.

### Why This Exists (Two-Level Skill Mapping)

The system has **two distinct skill mapping levels**:

| Level | Source | Granularity | Purpose |
|-------|--------|-------------|---------|
| **Role → Skill** | `SkillGenerator` (Step 6) | Coarse: 5-12 skills per role | "What skills does this role need overall?" |
| **Task → Skill** | `assemble_role_skill_map.py` (Step 9) | Granular: 3-8 skills per task, with relevance | "Which specific skills does this exact task require, and how critical are they?" |

The task-level mapping is essential for simulation accuracy: when a task's automation level
changes, the engine needs to know which skills are affected and whether they're PRIMARY
(the skill becomes less needed) or SECONDARY (the skill remains useful elsewhere).

### Output Structure — RoleSkillMapping

Each output file contains an array of role mappings. Each role contains its full
workload→task→skill decomposition:

```json
{
  "role_id": "role_senior_claims_adjuster_pc",
  "role_name": "Senior Claims Adjuster - P&C",
  "description": "...",
  "total_headcount": 285,
  "workloads": [
    {
      "workload_name": "Complex Claim Investigation and Valuation",
      "workload_id": "wl_..._complex_claim_investigation",
      "effort_allocation_pct": 45.0,
      "tasks": [
        {
          "task_name": "Scene Investigation and Evidence Documentation",
          "task_id": "task_..._scene_investigation",
          "automation_type": "human",
          "classification": "negligibility",
          "time_allocation_pct": 25.0,
          "mapped_skills": [
            {
              "skill_name": "Loss Adjustment",
              "skill_id": "skill_loss_adjustment",
              "relevance": "PRIMARY",
              "skill_category": "domain",
              "skill_type": "core"
            },
            {
              "skill_name": "Communication Skills",
              "skill_id": "skill_communication_skills",
              "relevance": "SECONDARY",
              "skill_category": "domain",
              "skill_type": "soft"
            }
          ]
        }
      ],
      "automation_summary": { "ai": 0, "human_ai": 2, "human": 3 }
    }
  ],
  "summary": {
    "total_workloads": 4,
    "total_tasks": 22,
    "total_mappings": 132,
    "avg_skills_per_task": 6.0,
    "unique_skills_used": 18
  }
}
```

### Field Reference — MappedSkill (per task)

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | string | Exact skill name from catalog |
| `skill_id` | string | FK to Skill catalog |
| `relevance` | string | `"PRIMARY"` (essential/core) or `"SECONDARY"` (helpful/supporting) |
| `skill_category` | string | domain/technical/analytical/etc. |
| `skill_type` | string | `"core"` or `"soft"` |

### LLM Prompt

The LLM receives the role's full skill set and all tasks grouped by workload,
then assigns 3-8 skills per task with relevance:

```
For EACH task, select the skills from the role's skill set that are required.
Mark each skill as:
- PRIMARY: The skill is essential/core for performing this task
- SECONDARY: The skill is helpful/supporting but not essential

Rules:
- Map 3-8 skills per task (at least 1 PRIMARY)
- Use EXACT skill names from the list
- Every task must have at least one mapped skill
```

### Generation Details

| Aspect | Value |
|--------|-------|
| Script | `scripts/assemble_role_skill_map.py` |
| LLM Calls | 1 per role (~42 calls for 2 functions, ~200 for all 12) |
| Input | Role's skills + all tasks grouped by workload |
| Output | Per-function JSON: `role_skill_mapping/func_*.json` |
| Skills per task | 3-8 (at least 1 PRIMARY) |
| Fallback (no LLM) | All role skills assigned as SECONDARY to every task |

### How It's Loaded into Neo4j

The graph loader (`graph/loader.py`) reads these files and creates relationships:

```cypher
UNWIND $mappings AS mapping
MATCH (t:DTTask {id: mapping.task_id})
MATCH (s:DTSkill {id: mapping.skill_id})
MERGE (t)-[rel:DT_REQUIRES_SKILL]->(s)
SET rel.relevance = mapping.relevance
```

This creates `(DTTask)-[:DT_REQUIRES_SKILL {relevance: "PRIMARY"|"SECONDARY"}]->(DTSkill)`.

---

## Generation Pipeline

### Execution Order (Dependencies)

```
Step 1: Taxonomy ────────── seed data, no LLM
          ↓
Step 2: Roles ───────────── needs: taxonomy/job_families
          ↓
Step 3: Job Titles ──────── needs: roles
          ↓
Step 4: Workloads ───────── needs: roles
          ↓
Step 5: Tasks ───────────── needs: workloads
          ↓
Step 6: Skills ──────────── catalog generation + role→skill mapping
          ↓
Step 7: Technologies ────── catalog generation + role→tech mapping
          ↓
Step 8: Workflows ───────── needs: roles, skills
          ↓
Step 9: Role-Skill Map ─── needs: roles, workloads, tasks, skills
                            (assemble_role_skill_map.py)
                            Produces: task-level skill assignments
                            with PRIMARY/SECONDARY relevance
```

### LLM Configuration

| Setting | Value |
|---------|-------|
| Provider | Anthropic |
| Model | claude-haiku-4-5 |
| Temperature | 0.3 |
| Max Tokens | 16,384 |
| Retry | 3 attempts, exponential backoff |

### Batch Sizes (GenerationConfig)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `roles_per_batch` | 15 | Roles per LLM call for mapping |
| `workloads_per_batch` | 10 | Roles per workload generation call |
| `tasks_per_batch` | 8 | Workloads per task generation call |
| `skills_per_batch` | 50 | Skills per catalog generation group |
| `technologies_per_batch` | 40 | Technologies per catalog generation group |
| `workflows_per_batch` | 4 | Workflows processed together |
| `target_roles_per_family` | 2 | Roles generated per JobFamily |
| `target_titles_per_role` | 3 | JobTitles per Role |
| `target_workloads_per_role` | 4 | Workloads per Role |
| `target_tasks_per_workload` | 6 | Tasks per Workload |
| `target_skills_total` | 250 | Total skill catalog size |
| `target_technologies_total` | 100 | Total technology catalog size |
| `target_workflows_per_function` | 8 | Workflows per function |
| `target_tasks_per_workflow` | 12 | Tasks per workflow |

### Estimated LLM Calls (Full Generation)

| Step | Calls | Notes |
|------|-------|-------|
| 1. Taxonomy | 0 | Seed data |
| 2. Roles | ~12 | 1 per function |
| 3. Job Titles | ~15 | ~10-15 roles per batch |
| 4. Workloads | ~20 | ~10 roles per batch |
| 5. Tasks | ~100 | ~5 workloads per batch |
| 6. Skills Catalog | 3 | 3 category groups |
| 6. Skill→Role Mapping | ~15 | ~15 roles per batch |
| 7. Tech Catalog | 3 | 3 category groups |
| 7. Tech→Role Mapping | ~15 | ~15 roles per batch |
| 8. Workflows | ~108 | 12 skeleton + 96 detail |
| 9. **Role-Skill Map** | **~200** | **1 per role (task-level skill assignment)** |
| **Total** | **~490** | |

### Resumability

All generators support incremental execution:
- Per-function output files — functions already generated are skipped
- Global catalogs (skills, technologies) are deduplicated on reload
- Failed batches are retried with smaller batch sizes
- CLI supports `--resume-from <step>`, `--functions "Fn1,Fn2"`, `--num-functions N`

---

## Output File Structure

```
data/acme_corp/
├── taxonomy.json                      # Full org structure (all 12 functions + hierarchy)
├── generation_stats.json              # Metadata and generation tracking
│
├── skills/
│   └── catalog.json                   # Global: 197 skill definitions
│
├── technologies/
│   └── catalog.json                   # Global: 71 technology definitions
│
├── roles/
│   ├── func_claims_management.json    # 22 roles
│   └── func_underwriting.json         # 20 roles
│
├── job_titles/
│   ├── func_claims_management.json    # 66 job titles
│   └── func_underwriting.json         # 60 job titles
│
├── workloads/
│   ├── func_claims_management.json    # 88 workloads
│   └── func_underwriting.json         # 80 workloads
│
├── tasks/
│   ├── func_claims_management.json    # 335 tasks
│   └── func_underwriting.json         # 340 tasks
│
├── workflows/
│   ├── func_claims_management.json    # 128 workflows
│   └── func_underwriting.json         # 128 workflows
│
└── role_skill_mapping/
    ├── func_claims_management.json    # Skill assignments
    └── func_underwriting.json         # Skill assignments
```

---

## Current Data Statistics

### Generated Data (2 of 12 functions complete)

| Entity | Claims Mgmt | Underwriting | Total Generated | Target (all 12) |
|--------|-------------|-------------|-----------------|-----------------|
| Roles | 22 | 20 | 42 | ~200 |
| Job Titles | 66 | 60 | 126 | ~600 |
| Workloads | 88 | 80 | 168 | ~800 |
| Tasks | 335 | 340 | 675 | ~3,000 |
| Workflows | 128 | 128 | 256 | ~960 |
| Skills (global) | — | — | 197 | 250 |
| Technologies (global) | — | — | 71 | 100 |
| **Task-Skill Mappings** | **22 roles mapped** | **20 roles mapped** | **42 roles** | **~200** |

### Data Quality Observations

- **Headcount Distribution**: Roles have realistic headcount spread (285 senior adjusters down to 15 specialists)
- **Salary Ranges**: $35,000 (entry clerk) to $180,000+ (director-level)
- **Automation Scores**: Range from 20% (complex legal/compliance) to 72% (routine data entry)
- **Task Classifications**: Mix across all 6 Etter categories
- **Skill Coverage**: 7 categories, lifecycle from emerging (GenAI) to declining (manual filing)

---

## Enums & Constants

### TASK_CLASSIFICATIONS
```
directive, feedback_loop, learning, validation, task_iteration, negligibility
```

### AUTOMATION_LEVELS
```
human_only, human_led, shared, ai_led, ai_only
```

### SKILL_LIFECYCLE
```
emerging, growing, stable, declining
```

### CAREER_BANDS
```
entry, mid, senior, lead, principal, director, vp, c_suite
```

### SKILL_CATEGORIES
```
technical, analytical, domain, leadership, communication, digital, regulatory
```

### TECHNOLOGY_CATEGORIES
```
ai_ml, automation_rpa, analytics_bi, cloud_infrastructure, crm_customer,
erp_enterprise, communication_collaboration, security_compliance,
industry_specific, development_tools
```

---

## How to Generate Data

```bash
# Generate all 12 functions (full run)
python -m draup_world_model.digital_twin.scripts.generate_all

# Generate specific functions only
python -m draup_world_model.digital_twin.scripts.generate_all --functions "Claims Management,Underwriting"

# Generate first N functions (cost-effective testing)
python -m draup_world_model.digital_twin.scripts.generate_all --num-functions 3

# Resume from a specific step (after failure)
python -m draup_world_model.digital_twin.scripts.generate_all --resume-from workloads

# Regenerate a specific step (force clean)
python -m draup_world_model.digital_twin.scripts.generate_all --step roles --clean
```
