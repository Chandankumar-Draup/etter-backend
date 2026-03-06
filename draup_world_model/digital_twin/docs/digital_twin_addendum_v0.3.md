# Digital Twin: Taxonomy, Entry Points & Etter Data Prerequisites

**Version:** 0.3 — Comprehensive Data-to-Twin Mapping  
**Date:** February 2026  
**Builds on:** Digital Twin Exploration v0.1, Addendum v0.2

---

## Part 1: First Principles — What Makes a Twin "Live"

### The Irreducible Question

A digital twin is only as good as the **data flowing through it**. Before asking "what can the twin do?" we must ask:

> **What data exists, where does it come from, and how does each piece contribute to making the twin useful?**

### Mental Model: Three Layers of Truth

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: ENTERPRISE CONTEXT (from client)                  │
│  "What does the org look like today?"                       │
│  → Headcount, salary, location, org structure, budgets      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: INTELLIGENCE (Etter produces)                     │
│  "What does AI transformation look like for this org?"      │
│  → Scores, classifications, skills, pathways, simulations   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: STRUCTURAL (client + Etter co-create)             │
│  "What is the skeleton of this organization?"               │
│  → Taxonomy, JDs, process maps, role definitions            │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: Layer 1 is the *skeleton*, Layer 2 is the *intelligence*, Layer 3 is the *flesh*. The twin needs all three, but Etter already generates ~80% of Layer 2. The gap is composition, not generation.

---

## Part 2: Enterprise Taxonomy — The Skeleton

### First Principles: Why Taxonomy IS the Twin's Structure

An organization is a hierarchy. Decisions flow down, metrics roll up. The digital twin must mirror this exactly — otherwise you're simulating a fictional org.

**The actual hierarchy (from enterprise reality):**

```
Enterprise (Acme Corp)
  └── Business Unit (Insurance Operations)
        └── Function (Human Resources)
              └── Job Family Group (HR Operations)
                    └── Job Family (Payroll & Benefits Service Delivery)
                          └── Role (Payroll Specialist)
                                └── Title (Senior Payroll Specialist)
                                      └── Individual (Jane Doe — optional)
```

### What Lives at Each Level

| Level | Contains | Twin's Use | Example |
|-------|----------|-----------|---------|
| **Enterprise** | All BUs, strategic vision | Portfolio-level simulation | "Guardian Life" |
| **Business Unit** | Functions aligned to business line | BU-level transformation roadmap | "Group Benefits" |
| **Function** | Cross-cutting organizational function | Function-level automation strategy | "Human Resources" |
| **Job Family Group** | Cluster of related job families | Cross-family skill flow analysis | "HR Operations" |
| **Job Family** | Roles sharing workflow/skills | ⭐ **Atomic twin unit** — full workflow visibility | "Payroll & Benefits Service Delivery" |
| **Role** | Workloads → Tasks → Skills | Core assessment unit (Etter's primary target) | "Payroll Specialist" |
| **Title** | Seniority/level variant of a role | Career ladder modeling | "Senior Payroll Specialist" |

### The Fractal Property (Self-Similarity)

The same five questions apply at EVERY level of the hierarchy:

1. **What is the automation potential?** (aggregate of children)
2. **What skills are shifting?** (union of sunrise/sunset from children)
3. **What is the financial impact?** (sum of cost effects from children)
4. **What are the risks?** (max risk from children — conservative)
5. **What should we do first?** (prioritized by impact × feasibility)

This is the fractal: the twin's interface is identical at every zoom level. Only the granularity of answers changes.

### Aggregation Rules (How Metrics Roll Up)

```
Role Level (atomic):
  ai_impact_score = 72         (direct from Etter assessment)
  headcount = 15               (from enterprise)
  avg_salary = $65,000         (from enterprise)
  
Job Family Level (aggregate):
  ai_impact_score = Σ(role_score × role_headcount) / Σ(headcount)   ← weighted avg
  headcount = Σ(role_headcount)                                       ← sum
  total_cost = Σ(role_headcount × role_avg_salary)                    ← sum
  unique_skills = ∪(role_skills)                                      ← union
  sunset_skills = ∪(role_sunset_skills) with frequency count          ← union+count
  risk_score = max(role_risk_scores)                                  ← conservative
  skill_concentration = count(roles needing skill X) / total_roles    ← ratio

Job Family Group / Function / BU / Enterprise:
  Same formulas, just one level higher aggregation.
```

---

## Part 3: Entry Points — Where to Start the Twin

### Second-Order Thinking: Why Job Family is the Right Starting Point

**Thought experiment**: What if we start at Enterprise level?

```
Enterprise → Need 200+ role assessments → 6+ months → No feedback loop
           → Client loses interest before seeing value
           → First-order: "Comprehensive!" Second-order: "Dead before launch."
```

**What if we start at single Role level?**

```
Role → One assessment → 1 day → But no workflow context
     → Can't see cascade effects → Can't see skill flows
     → First-order: "Quick!" Second-order: "Not useful enough to sell."
```

**What if we start at Job Family level?** ⭐

```
Job Family → 3-8 role assessments → 2-3 weeks → Full workflow visible
           → Cross-role cascades visible → Skill concentration detectable
           → Career mobility within family → Financial impact meaningful
           → First-order: "Right-sized." Second-order: "Proves value, expands naturally."
```

### Concentric Ring Expansion Strategy

```
Ring 0: Job Family (prove value)           ← START HERE
  ↓ expansion trigger: Model completeness >85%, usage >5 scenarios/month
Ring 1: Job Family Group (cross-family)    
  ↓ expansion trigger: 3+ families active, stakeholder requesting cross-view
Ring 2: Function (function strategy)       
  ↓ expansion trigger: CHRO/CFO engagement, budget allocated
Ring 3: Cross-Function (enterprise)        
  ↓ expansion trigger: CEO/Board engagement, multi-year commitment
Ring 4: Enterprise (all-in)
```

### What Each Ring Unlocks

**Ring 0 — Job Family (Director/VP buyer)**
- Workflow bottleneck detection
- Skill concentration risk within the family
- Career mobility paths between roles
- Headcount projection (12/24/36mo)
- Role vacuum detection (orphaned tasks → new role suggestion)
- **Metric**: Time-to-value < 3 weeks, ROI visible within 1 quarter

**Ring 1 — Job Family Group (VP/SVP buyer)**
- Cross-family skill transfer potential
- Shared reskilling investment opportunities  
- Workforce rebalancing across families
- Aggregate financial impact
- **Metric**: Reskilling cost reduction through shared programs

**Ring 2 — Function (CHRO/CFO/CTO buyer)**
- Function-level automation roadmap with sequencing
- Total reskilling budget with break-even timeline
- New org structure design (future-state)
- Competitive benchmarking against industry peers
- **Metric**: Total function-level savings projection, organizational fragility index

**Ring 3+ — Enterprise (CEO/Board buyer)**
- Cross-function prioritization matrix
- Enterprise skill portfolio view
- Total transformation cost and multi-year roadmap
- Risk portfolio across all functions
- **Metric**: Enterprise transformation ROI, strategic readiness score

---

## Part 4: Complete Etter Data Inventory for the Digital Twin

This is the comprehensive mapping: every Etter capability → what data it produces → how the twin uses it.

### 4.1 AI Assessment (Primary Intelligence Source)

**What Etter produces** (per role, from `/api/v1/ai-assessment`):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| `ai_impact_score` (0-100) | float | Core metric at every hierarchy level. The "temperature" of a role. Rolls up via weighted average. |
| `automation_score` (0-100) | float | % of tasks fully automatable. Drives headcount projection models. |
| `augmentation_score` (0-100) | float | % requiring Human+AI. Drives reskilling pathway identification. |
| `task_analysis.workloads[]` | array | Each workload with tasks — the decomposition that makes simulation granular. |
| `workload.tasks[]` | array | Individual tasks — the atomic unit the simulator operates on. |
| `task.classification` | enum | AI / Human+AI / Human — determines automation timeline per task. |
| `task.time_hours` | float | Time allocation per task — feeds financial simulator's capacity model. |
| `task.automation_priority` | string | HIGH/MEDIUM/LOW — drives sequencing in transformation roadmap. |
| `task.confidence` | float | Model's confidence in classification — surfaces uncertainty to stakeholders. |
| `task.impact_score` | object | TIME_INVESTMENT, STRATEGIC_VALUE, ERROR_REDUCTION, SCALABILITY (1-5 each). Multi-dimensional prioritization. |
| `task.skills_required` | array | Skills per task — connects tasks to skills architecture for gap analysis. |
| `task.rationale` | string | Explanation of why classified this way — decision provenance for trust. |
| `impact_metrics[]` | array | Before/after productivity metrics per role — benchmark data for ROI. |
| `impact_summary` | markdown | Narrative summary — client-facing explanation layer. |
| `quantification_report` | markdown | Quantified scores summary — feeds executive dashboards. |

**Twin usage**: This is the *primary intelligence layer*. Every simulation scenario starts from these scores. Without assessment, you have a skeleton with no intelligence.

**Readiness signal**: Assessment complete for all roles in scope → twin intelligence layer is populated.

### 4.2 Dynamic Skills Architecture

**What Etter produces** (per role, from `/api/v1/dynamic-skills-architecture`):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| **Current Skills** | | |
| `core_skills[]` | array | Skill inventory per role — maps to graph nodes, enables overlap detection. |
| `digital_tech_stack[]` | array | Tools/platforms in use — technology dependency mapping. |
| `soft_skills[]` | array | Interpersonal skills — filtered from automation analysis but retained for role design. |
| `skill.skill_id` | string | Unique identifier — enables cross-role matching and deduplication. |
| `skill.is_root_skill` | boolean | Foundational skill flag — root skills persist through transformation (invariants). |
| `skill.is_tech_stack` | boolean | Tool/technology flag — subject to vendor obsolescence risk. |
| `skill.jd_count` | integer | Market demand signal — how many JDs mention this skill. Proxy for talent availability. |
| `skill.relevance` | string | PRIMARY/SECONDARY — weighted differently in overlap calculations. |
| **Futuristic Skills** | | |
| `futuristic_skills[]` | array | Sunrise skills for the AI-transformed role — defines the target state. |
| `futuristic_skill.description` | string | What the skill involves — feeds reskilling program design. |
| `futuristic_skill.resource` | object | Research source with title and link — credibility/provenance for stakeholders. |
| **Task-Skills Mapping** | | |
| `task_skills_mapping` | object | Which skills each task requires — enables task→skill→role traversal in graph. |

**Twin usage**: Skills are the *connective tissue* of the twin. They connect roles to each other (overlap), tasks to learning paths (reskilling), and present to future (sunrise/sunset).

**Emergent properties at family level**:
- **Skill concentration risk**: If 4 of 5 roles require a sunset skill → high organizational fragility
- **Skill overlap coefficient**: Roles sharing 70%+ skills → natural redeployment corridor
- **Talent availability signal**: Low jd_count for sunrise skills → harder to hire, must build internally

### 4.3 Reskilling & Sunrise/Sunset Classification

**What Etter produces** (per role, within dynamic-skills response):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| `workload_transformations[]` | array | Per-workload sunrise/sunset mapping — context-dependent, not absolute. |
| `sunset_skills[]` per workload | array | Skills declining *in this workload context* — drives retraining urgency. |
| `sunrise_skills[]` per workload | array | Skills emerging *in this workload context* — defines learning targets. |
| `sunset_skill.reason` | string | Why declining — feeds change management communication. |
| `sunrise_skill.reason` | string | Why emerging — justifies investment in specific training. |
| `courses[]` | array | Recommended learning resources — actionable reskilling program. |
| `course.platform` | string | Where to learn (Coursera, LinkedIn Learning, etc.) — procurement info. |
| `insights.skill_demand_trends` | object | Quantified trends (e.g., "15-20% annual decline") — forecasting input. |
| `insights.reskilling_pathways` | object | Immediate (0-6mo), Short-term (6-12mo), Medium (12-24mo), Long-term (24+mo). |
| `insights.quick_wins` | array | Actionable items to start immediately — drives Phase 1 of transformation. |

**Twin usage**: Reskilling data drives the *transformation pathway* dimension of the twin. Without it, the twin can diagnose ("this role is 72% automatable") but can't prescribe ("here's how to transition the humans").

**Critical insight (from Etter's architecture)**: A skill's sunrise/sunset status is CONTEXT-DEPENDENT. Python might be "sunrise" for a data entry workload (replacing Excel macros) but "core" for legacy system maintenance. The twin must preserve this workload-bounded granularity, not flatten to role-level averages.

### 4.4 Financial Simulator

**What Etter produces** (per simulation run):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| **Inputs** | | |
| `role_groups[].role` | string | Role being simulated — scopes the simulation. |
| `role_groups[].count` | integer | Headcount — from enterprise context. |
| `role_groups[].salary` | float | Average salary — from enterprise context. |
| `automation_factor` (0.0-1.0) | float | Adoption speed control — scenario parameter. |
| **Time-Series Outputs** (per simulation step/month) | | |
| `total_employees_normalized` | float | Headcount as % of starting — the primary headcount curve. |
| `total_salary_of_employees` | float | Cost as % of starting — the primary savings curve. |
| `avg_automation_rate` | float | % of tasks now AI-handled — adoption progress. |
| `avg_time_per_employee` | float | Actual work hours per person — capacity utilization. |
| `avg_unused_output_capacity` | float | Spare capacity available — redistribution potential. |
| `{role}_count` | float | Per-role headcount over time — role-specific projections. |
| `{role}_avg_automation_rate` | float | Per-role automation adoption — role-specific progress. |
| **Monte Carlo Outputs** (from batch runs) | | |
| Confidence intervals | range | 5th/25th/50th/75th/95th percentile bands — uncertainty quantification. |

**Twin usage**: The financial simulator IS the twin's *scenario engine*. It's what makes the twin dynamic rather than a static dashboard. The key differentiators:

- **Agent-based** (Mesa framework) — models individual employees, emergent behavior
- **Task-level granularity** — not role-level assumptions
- **Learning curves** — knowledge increases probabilistically over time  
- **Work redistribution** — freed capacity absorbs eliminated roles' work
- **Adoption resistance** — automation_factor controls organizational inertia

**For the twin, the simulator must extend from single-role to multi-role within a family**:

```
Current:   SimulationEngine.run(role_groups=[...])  → per-role time series
Twin need: SimulationEngine.run(job_family="Payroll & Benefits") 
           → per-role + cross-role cascades + work redistribution across roles
```

This is the primary engineering extension needed. The simulator already handles multi-role, but the twin needs it to understand *inter-role* task flows.

### 4.5 Workflow Analysis

**What Etter produces** (per function/workflow, from `/api/v1/workflows`):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| `function_areas[].function_name` | string | Business function context — maps to taxonomy. |
| `workflows[].workflow_name` | string | End-to-end process — the "thread" connecting roles. |
| `workflow.description` | string | What the process accomplishes — business context. |
| `workflow.frequency` | string | daily/weekly/monthly/quarterly — urgency weighting. |
| `workflow.priority` | string | HIGH/MEDIUM/LOW — business criticality. |
| `workflow.ai_optimization_score` (0-1) | float | AI opportunity score at workflow level — same methodology as role-level. |
| `workflow.tasks[]` | array | Tasks within this workflow — connects to role-level task decomposition. |
| `task.task_name` | string | Task identifier — join key with assessment tasks. |
| `task.classification` | string | AI/Human+AI/Human — workflow-level classification. |
| `task.confidence_score` | float | Classification confidence — uncertainty flag. |
| `task.estimated_time_hours` | float | Time per task — workflow efficiency calculation. |
| `workflow.workflow_metrics` | object | Quantified impact metrics — before/after projections. |
| `workflow.insights.markdown` | string | Complete analysis report — includes executive summary, automation landscape. |

**Twin usage**: Workflows are the *horizontal connections* the twin needs. Assessment gives vertical depth (role → workloads → tasks). Workflow analysis gives horizontal breadth (how tasks flow across roles).

**This is where the twin creates unique value**: By connecting assessment (vertical) with workflow (horizontal), the twin can answer questions neither can answer alone:

- "If I automate Task X in Role A, what happens to the downstream task in Role B?"
- "Where is the bottleneck — the automatable task or the human task it feeds?"
- "Which workflow should I automate first for maximum cross-role impact?"

### 4.6 Top Tasks for Automation

**What Etter produces** (from `/api/v1/top-tasks`):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| `top_tasks[]` | array | Prioritized list across all assessed roles — drives transformation sequencing. |
| `task.role_name` | string | Which role owns this task — cross-reference to assessment. |
| `task.workload_name` | string | Which workload — context for impact calculation. |
| `task.classification` | string | AI/Human+AI/Human — redundant with assessment but pre-prioritized. |
| `task.impact_score` | object | Multi-dimensional scoring — same 4 dimensions as assessment. |

**Twin usage**: Pre-prioritized transformation queue. The twin's "what to do first" view pulls from this directly rather than re-computing priorities from raw assessment data.

### 4.7 AI-Transformed Job Description

**What Etter produces** (per role, from `/api/v1/ai-transformed-jd`):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| `transformed_jd` | markdown | The future-state JD — defines what the role becomes after AI transformation. |
| Current vs. future responsibilities | text | Delta between today and tomorrow — the "change document" for each role. |

**Twin usage**: The transformed JD is the twin's **future-state definition** for each role. When the twin shows "what does this family look like in 24 months?" the transformed JDs provide the concrete role descriptions.

### 4.8 Role Adjacency & Ecosystem (from Etter Methodology)

**What Etter produces** (from adjacency and ecosystem models):

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| Role adjacency scores | float | Similarity between roles — career mobility paths. |
| Shared skill profiles | array | Skills in common — redeployment feasibility. |
| Transition feasibility | float | How viable is moving from Role A → Role B — practical mobility. |
| Ecosystem blueprint | object | AI-augmented role ecosystem design — future org structure. |
| New role recommendations | array | Roles that should exist but don't yet (Prompt Engineer, AI Product Trainer). |
| Redesigned role profiles | array | How existing roles should evolve — augmented role definitions. |

**Twin usage**: Adjacency is the *mobility layer*. When the twin recommends "reduce Payroll Specialist headcount by 30%, reskill to Benefits Analyst," adjacency data validates that this transition is feasible based on shared skill profiles.

### 4.9 Risk Framework Simulator (In Development)

**What Etter will produce:**

| Data Element | Type | Twin Uses It For |
|-------------|------|-----------------|
| **Inputs** | | |
| Data Quality score | 0-100 | Accuracy, completeness, consistency of enterprise data. |
| Data Integration score | 0-100 | System connectivity, API availability. |
| Data Governance score | 0-100 | Access controls, compliance, security posture. |
| Analytics Maturity score | 0-100 | Existing BI/analytics capabilities. |
| Process Documentation score | 0-100 | Clarity and completeness of workflows. |
| Team Capability score | 0-100 | Internal expertise for transformation execution. |
| Skill Levels score | 0-100 | Current vs required workforce competencies. |
| Tech Stack Availability score | 0-100 | Existing tools and infrastructure readiness. |
| Organization Culture score | 0-100 | Change readiness, AI adoption mindset. |
| **Outputs** | | |
| Risk Score by dimension | 0-100 each | Quantified risk levels — the twin's risk overlay. |
| Readiness Assessment | Go/No-Go | Decision framework for activation. |
| Mitigation Priorities | ranked list | Where to invest before transforming. |
| Timeline Impact | multiplier | How risks slow transformation — adjusts simulator timelines. |
| Investment Requirements | cost | Resources needed for risk mitigation — adds to total cost of transformation. |

**Twin usage**: The risk framework is the twin's **reality check**. Without it, the twin assumes "if we automate Task X, savings happen." With it, the twin says "if we automate Task X, and data quality is 40/100, actual savings are reduced by Y% and timeline extends by Z months."

### 4.10 Draup's Proprietary Intelligence (Background Layer)

**What Draup provides** (not per-client, but as platform intelligence):

| Data Element | Scale | Twin Uses It For |
|-------------|-------|-----------------|
| Skills Library | 21,000+ standardized skills | Universal skill vocabulary — enables cross-client benchmarking. |
| Task Engine | 500,000+ tasks | Peer task datasets — fills gaps when client JDs are sparse. |
| Professional Profiles | 850M+ | Market intelligence — talent availability, hiring difficulty. |
| Job Descriptions | 600M+ | Industry benchmarks — how other orgs structure similar roles. |
| Skill Convergence Patterns | cross-industry | Which skills are merging/splitting — predictive signals. |
| Complexity & Cognitive Load Scores | per task | Task difficulty calibration — refines automation feasibility. |
| Task Adjacency Networks | cross-task | Which tasks frequently co-occur — workflow inference. |
| Skill Transferability Scores | skill-pair | How easy to transfer between skills — reskilling time estimation. |

**Twin usage**: This is the *intelligence baseline*. When a client's data is sparse, Draup's proprietary data fills gaps with industry defaults. As more clients validate, the library becomes a pre-validated starting point for new clients.

---

## Part 5: Enterprise Data Requirements (What the Client Must Provide)

### Minimum Viable Data (Must Have)

| Data Element | Source | Why Required | Without It |
|-------------|--------|-------------|------------|
| **Organization Taxonomy** | HRIS (Workday/SAP) | The skeleton — defines hierarchy for the twin | Twin has no structure to attach intelligence to |
| **Job Descriptions** | HRIS or manual | Etter's primary input — drives all assessments | No assessment possible, no intelligence layer |
| **Headcount per Role** | HRIS | Financial projections need population data | Can't calculate cost impact, only show percentages |

### Should Have (Significantly Improves Twin)

| Data Element | Source | Why Valuable | Fallback Without It |
|-------------|--------|-------------|---------------------|
| **Salary/Cost per Role** | HRIS / Finance | Enables financial simulator — real dollar projections | Use market average data (less accurate but functional) |
| **Process Maps / SOPs** | Operations teams | Enrich task decomposition — better automation scoring | Etter generates from JDs (good but not as complete) |
| **Location Data** | HRIS | Location-based cost modeling, geo-risk analysis | Assume single-location (loses optimization opportunity) |

### Nice to Have (Enhances Later Rings)

| Data Element | Source | Ring Needed | What It Enables |
|-------------|--------|-------------|-----------------|
| Training History | LMS | Ring 1+ | Existing skill evidence, learning velocity estimation |
| Internal Mobility Data | HRIS | Ring 1+ | Validates adjacency model, actual transition patterns |
| Hiring Pipeline | ATS (Greenhouse, etc.) | Ring 2+ | Buy vs build decision — if you can't hire sunrise skills, must reskill |
| Budget Constraints | Finance | Ring 2+ | Realistic transformation phasing — what's affordable when |
| Change Readiness Surveys | OD/HR | Ring 2+ | Risk framework calibration — culture factor |
| Vendor/Tool Costs | Procurement | Ring 2+ | Total cost of transformation including tooling |
| Performance Reviews | HRIS | Ring 3+ | Skill proficiency evidence — validates competency models |

---

## Part 6: Data Readiness Score

### Scoring Framework (0-100)

Each dimension scores on specific, measurable criteria:

**Taxonomy Completeness (25 points)**

| Criterion | Max Points | Measurement |
|-----------|-----------|-------------|
| Hierarchy defined through Job Family level | 10 | All levels present and named |
| All roles within scope identified | 8 | Count of roles vs. estimated total |
| Titles mapped to roles | 4 | Title → Role relationship exists |
| Location data attached | 3 | Roles have location attribute |

**Role Decomposition — Etter Intelligence (30 points)**

| Criterion | Max Points | Measurement |
|-----------|-----------|-------------|
| JDs available for all in-scope roles | 10 | JD count / role count |
| Etter assessment complete | 10 | Assessment exists per role |
| Workloads extracted per role | 5 | Avg workloads per role ≥ 3 |
| Tasks classified (AI/Human+AI/Human) | 5 | Classification coverage = 100% |

**Skills Architecture — Etter Intelligence (20 points)**

| Criterion | Max Points | Measurement |
|-----------|-----------|-------------|
| Core skills mapped per role | 8 | Skills list exists per role |
| Sunrise/Sunset identified per workload | 6 | Reskilling data populated |
| Skill-skill mapping generated | 3 | Adjacency relationships exist |
| Market demand signals available (jd_count) | 3 | jd_count populated for skills |

**Enterprise Context (15 points)**

| Criterion | Max Points | Measurement |
|-----------|-----------|-------------|
| Headcount per role | 6 | All roles have headcount |
| Salary/cost per role | 4 | All roles have cost data |
| Process maps available | 3 | SOPs/process docs uploaded |
| Location data available | 2 | Geographic distribution known |

**Validation & Trust (10 points)**

| Criterion | Max Points | Measurement |
|-----------|-----------|-------------|
| Human validation of scores | 4 | SME reviewed and approved |
| Scores locked (not fluctuating) | 3 | Version pinned, no recalculation |
| Stakeholder sign-off on taxonomy | 3 | Business owner confirmed structure |

### Readiness Thresholds

| Score | Status | What It Means |
|-------|--------|--------------|
| **≥ 70** | ✅ READY | Twin can be activated. Directional accuracy is high. |
| **50-69** | ⚠️ PARTIAL | Twin can show directional insights but must flag gaps clearly. |
| **< 50** | ❌ NOT READY | Complete Etter assessment pipeline first. Twin would be misleading. |

### Quick Diagnostic (Per Scope Level)

| Requirement | Job Family | Job Family Group | Function | Enterprise |
|:------------|:----------:|:----------------:|:--------:|:----------:|
| JDs needed | 3-8 | 15-30 | 50-150 | 200+ |
| Etter assessments | 3-8 roles | 15-30 roles | All roles | All roles |
| Workflow connections | Within family | Cross-family | Cross-group | Cross-function |
| HRIS integration | Nice to have | Recommended | Required | Required |
| Headcount data | Must have | Must have | Must have | Must have |
| Salary data | Should have | Must have | Must have | Must have |
| Setup time | 2-3 weeks | 4-6 weeks | 8-12 weeks | 16-24 weeks |
| Simulation value | MEDIUM-HIGH | HIGH | VERY HIGH | STRATEGIC |

---

## Part 7: Etter Data → Twin Graph Composition

### From Flat APIs to Connected Model

**Current state**: Etter produces separate API responses per capability (assessment, skills, workflows, simulator). Each is valuable independently.

**Twin requirement**: All data connected in a single graph where traversal reveals emergent insights.

### Neo4j Graph Schema (How It All Connects)

```
TAXONOMY LAYER (Layer 1):
(Enterprise)-[:HAS_BU]->(BusinessUnit)
(BusinessUnit)-[:HAS_FUNCTION]->(Function)
(Function)-[:HAS_JFG]->(JobFamilyGroup)
(JobFamilyGroup)-[:HAS_JF]->(JobFamily)
(JobFamily)-[:CONTAINS_ROLE]->(Role)
(Role)-[:HAS_TITLE]->(Title)

INTELLIGENCE LAYER (Layer 2 — from Etter):
(Role {ai_impact_score, automation_score, augmentation_score})
  -[:HAS_WORKLOAD]->(Workload {name, ai_pct, human_ai_pct, human_pct})
    -[:CONTAINS_TASK]->(Task {classification, time_hours, priority, confidence})
      -[:REQUIRES_SKILL]->(Skill {id, name, is_root, jd_count})
      -[:CAN_BE_AUTOMATED_BY]->(AITool {name, capability})

(Role)-[:CURRENT_SKILL]->(Skill)
(Role)-[:NEEDS_SUNRISE_SKILL]->(Skill)     ← from reskilling
(Role)-[:LOSING_SUNSET_SKILL]->(Skill)     ← from reskilling
(Role)-[:ADJACENT_TO {score}]->(Role)       ← from adjacency model
(Role)-[:TRANSFORMS_TO]->(TransformedRole)  ← from AI-transformed JD

WORKFLOW LAYER (horizontal connections):
(Workflow {name, frequency, priority, ai_optimization_score})
  -[:HAS_STEP {order}]->(Task)
(Role)-[:PARTICIPATES_IN]->(Workflow)

CONTEXT LAYER (Layer 3 — from enterprise):
(Role)-[:HAS_HEADCOUNT {count, location}]->(Snapshot {date})
(Role)-[:HAS_COST {avg_salary}]->(Snapshot {date})

SIMULATION LAYER (dynamic):
(Scenario {automation_factor, time_horizon})
  -[:PRODUCES]->(SimulationResult {headcount_curve, cost_curve, automation_curve})
(SimulationResult)-[:FOR_ROLE]->(Role)
```

### Emergent Properties (What the Graph Reveals That APIs Cannot)

When Etter outputs are composed into a connected graph, new insights emerge that aren't visible in any single API response:

| Emergent Property | How Detected | Business Value |
|-------------------|-------------|----------------|
| **Skill Concentration Risk** | Query: "Skills required by >60% of roles in this family that are classified as sunset" | Early warning: if this skill dies, the whole family is disrupted |
| **Workflow Bottleneck Shift** | Traverse: High-automation task → next task in workflow → low-automation task | Automation doesn't help if the human task downstream can't keep up |
| **Career Mobility Corridors** | Query: Role pairs with skill overlap >70% AND adjacency score >0.7 | Natural redeployment paths — lowest friction career transitions |
| **Role Vacuum Detection** | Orphaned tasks from 3+ automated roles sharing a skill cluster → no existing role owns them | New composite role needed — proactive org design |
| **Reskilling Efficiency** | Sunrise skills shared across multiple roles in family → single training program serves many | Cost per reskilled employee drops with shared investment |
| **Cascade Impact** | Simulate: Automate Task X in Role A → freed capacity → absorb Task Y from Role B → Role B headcount reducible | Cross-role savings that single-role analysis misses |

---

## Part 8: Activation Sequence — Bringing a Job Family Twin Online

### 8-Step Process

```
Step 1: TAXONOMY LOCK (Day 1-2)
  Input:  Client org chart / HRIS export
  Action: Confirm hierarchy, select Job Family, verify all roles identified
  Output: Locked taxonomy nodes in graph
  Gate:   Business owner confirms "this is our structure"

Step 2: ROLE DECOMPOSITION (Day 3-10) — Etter Assessment Pipeline
  Input:  JDs for all roles in family
  Action: Run Etter AI Assessment on each role
  Output: ai_impact_score, workloads, tasks, classifications per role
  Gate:   Assessment complete for 100% of roles

Step 3: SKILLS ARCHITECTURE (Day 3-10, parallel) — Etter Skills Pipeline
  Input:  Assessment results + Draup skill library
  Action: Run Dynamic Skills Architecture
  Output: Current skills, sunrise/sunset per workload, courses
  Gate:   Skills mapped for all roles, reskilling data populated

Step 4: ENTERPRISE CONTEXT (Day 5-12)
  Input:  HRIS data, finance data
  Action: Map headcount, salary, location to each role
  Output: Context layer populated in graph
  Gate:   Headcount confirmed, salary data available (or market defaults applied)

Step 5: GRAPH COMPOSITION (Day 10-14)
  Input:  All Etter outputs + enterprise context
  Action: Load into Neo4j with full relationship schema
  Output: Connected graph with all layers
  Gate:   Graph query returns correct aggregations at family level

Step 6: HUMAN VALIDATION (Day 12-16)
  Input:  Twin dashboard showing scores, skills, projections
  Action: SME review with business owner
  Output: Validated scores, locked versions, corrections applied
  Gate:   Business owner signs off on accuracy

Step 7: SIMULATION CALIBRATION (Day 14-18)
  Input:  Validated graph
  Action: Run baseline simulation, compare with historical data if available
  Output: Calibrated simulation parameters
  Gate:   Simulation directionally matches business intuition

Step 8: TWIN ACTIVATION (Day 18-20)
  Input:  Calibrated, validated twin
  Action: Open Scenario Builder for client
  Output: Live twin accepting "what-if" queries
  Gate:   First client scenario run successfully
```

### For Clients with Existing Etter Assessment (e.g., GLIC)

Steps 2-3 collapse to "retrieve existing data" → **Timeline: 1.5-2 weeks** instead of 3-4 weeks.

---

## Part 9: Metrics at Every Level

### Twin Health Metrics (Is the twin reliable?)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Data Readiness Score | ≥ 70 | Composite from Part 6 framework |
| Model Completeness | > 85% | Roles assessed / total roles in scope |
| State Freshness | < 30 days | Time since last data refresh |
| Validation Coverage | > 80% | Scores reviewed by SME / total scores |
| Simulation Confidence | Monte Carlo CI width < 30% | 75th - 25th percentile range |

### Business Value Metrics (Is the twin useful?)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Scenarios Run / Month | > 5 | Active usage indicator |
| Time-to-First-Insight | < 3 weeks | From data ingestion to first usable output |
| Decision Influence | ≥ 1 decision/quarter | Client reports using twin output in actual decisions |
| Accuracy Delta | ≤ 15% | Predicted outcome vs. actual outcome after 6 months |
| Expansion Rate | 1 ring/quarter | Client expanding scope of twin |

### Capability-Specific Metrics (Per Etter module feeding the twin)

| Etter Module | Key Metric | Target | Why It Matters |
|-------------|-----------|--------|---------------|
| AI Assessment | Classification accuracy | > 85% | Wrong classification → wrong simulation |
| Skills Architecture | Skill coverage rate | > 90% | Missing skills → blind spots in mobility paths |
| Reskilling | Sunrise/Sunset relevance | > 80% rated "useful" by SME | Bad reskilling recommendations → lost trust |
| Financial Simulator | Projection accuracy (vs actual) | Within 25% at 12mo | Bad projections → twin loses credibility |
| Workflow Analysis | Workflow completeness | > 70% of known processes captured | Missing workflows → blind spots in cascades |
| Risk Framework | Risk score correlation with outcomes | > 0.6 Spearman's ρ | Low correlation → risk overlay not trustworthy |

---

## Part 10: What This Means Practically

### The 80/20 Insight

Etter already produces ~80% of the data the twin needs. The gap is NOT data generation — it's:

1. **Graph composition** — connecting existing outputs into a unified model (engineering effort: ~2 weeks)
2. **Simulation extension** — generalizing financial simulator for multi-role cascades within a family (engineering effort: ~3 weeks)
3. **Taxonomy management** — UI/pipeline for client to define and lock their hierarchy (engineering effort: ~1 week, partially exists)

### What Makes This a Product (Not a Consulting Exercise)

The same Job Family twin model works for ANY enterprise, industry, or function because:

- **Taxonomy hierarchy is universal** — every org has BU → Function → Family → Role
- **Etter's intelligence pipeline is universal** — JD in, scores out, for any role
- **Simulation rules are configurable** — automation_factor, time_horizon are parameters
- **Graph schema is universal** — same node types, same relationships, different data
- **Only data changes** — and Etter's pipeline already generates it

### Immediate Next Step

Pick one Job Family from an existing client (GLIC "Payroll & Benefits" or Hartford equivalent):

1. Verify data readiness (taxonomy locked, assessments done, headcount available)
2. Score readiness using the framework in Part 6
3. Compose existing Etter outputs into connected graph (Part 7 schema)
4. Run first simulation scenario
5. Present to stakeholder: *"Here's what happens if you automate this family over 24 months."*

**Timeline for first prototype: 1.5-2 weeks for a client with existing Etter assessment.**

---

## Appendix: Complete Data Dependency Map

```
WHAT THE TWIN NEEDS          ← WHERE IT COMES FROM         ← RAW SOURCE

Hierarchy structure           ← Taxonomy Lock step           ← Client HRIS
Role-level AI scores          ← AI Assessment API            ← Etter engine (from JDs)
Task decomposition            ← AI Assessment API            ← Etter engine (from JDs)
Task classifications          ← AI Assessment API            ← Etter engine (from JDs)
Current skills per role       ← Dynamic Skills API           ← Etter engine + Draup library
Sunrise/Sunset per workload   ← Reskilling (within Skills)   ← Etter engine + market signals
Skill market demand           ← Dynamic Skills API           ← Draup (850M+ profiles)
Course recommendations        ← Reskilling capability        ← Etter engine + web search
Workflow connections           ← Workflow Analysis API        ← Etter engine (from process maps/JDs)
Role adjacency scores         ← Adjacency Model              ← Etter engine + Draup role graph
Future-state JDs              ← Transformed JD API           ← Etter engine
New role recommendations      ← Ecosystem Model              ← Etter engine
Headcount & salary            ← Enterprise Context step      ← Client HRIS / Finance
Financial projections         ← Financial Simulator           ← Etter engine (from tasks + headcount)
Risk scores                   ← Risk Framework (roadmap)     ← Client self-assessment + Etter
Industry benchmarks           ← Draup Intelligence           ← Draup proprietary data
```

**Every arrow (←) is a data pipeline that either exists today or is on the immediate roadmap. No new science needed — just composition.**
