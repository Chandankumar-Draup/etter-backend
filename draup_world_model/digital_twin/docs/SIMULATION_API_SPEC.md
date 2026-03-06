# Digital Twin Simulation — API & Interface Specification

> For UI/UX development. Documents every simulation type, its inputs, outputs,
> configuration options, and the REST API endpoints that expose them.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Organizational Scope (Where to Simulate)](#2-organizational-scope)
3. [Simulation Types](#3-simulation-types)
   - 3.1 [Role Redesign](#31-role-redesign)
   - 3.2 [Technology Adoption](#32-technology-adoption)
   - 3.3 [Multi-Technology Adoption](#33-multi-technology-adoption)
   - 3.4 [Task Distribution](#34-task-distribution)
4. [Simulation Engines (v1 vs v2)](#4-simulation-engines)
5. [Configuration Knobs](#5-configuration-knobs)
6. [Output Structures](#6-output-structures)
7. [REST API Reference](#7-rest-api-reference)
8. [Available Technologies](#8-available-technologies)
9. [UI Workflow Recommendations](#9-ui-workflow-recommendations)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  UI Layer (React)                                               │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────┐  │
│  │ Scope    │ │ Simulation   │ │ Results   │ │ Comparison   │  │
│  │ Selector │ │ Configurator │ │ Viewer    │ │ Dashboard    │  │
│  └────┬─────┘ └──────┬───────┘ └─────┬─────┘ └──────┬───────┘  │
│       │              │               │              │           │
├───────┼──────────────┼───────────────┼──────────────┼───────────┤
│  REST API (Flask)    │  /api/dt/*    │              │           │
│       │              │               │              │           │
│  ┌────▼─────┐  ┌─────▼──────┐  ┌────▼─────┐  ┌────▼─────┐    │
│  │ Scope    │  │ Scenario   │  │ Cascade  │  │ Compare  │    │
│  │ Selector │  │ Manager    │  │ Engine   │  │ Engine   │    │
│  └────┬─────┘  └─────┬──────┘  └────┬─────┘  └──────────┘    │
│       │              │               │                          │
│  ┌────▼──────────────▼───────────────▼─────┐                   │
│  │          Neo4j Graph Database           │                   │
│  │  (DT-prefixed labels: DTRole, DTTask…)  │                   │
│  └─────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

**Flow**: User selects scope → chooses simulation type → configures parameters → runs simulation → views results → optionally compares scenarios.

---

## 2. Organizational Scope

Every simulation requires a **scope** — the organizational boundary that defines which roles, tasks, and people are included.

### Scope Types (Hierarchy Levels)

| Scope Type         | Description                         | Example                              | Typical Size   |
|--------------------|-------------------------------------|--------------------------------------|----------------|
| `organization`     | Entire company                      | "Acme Corporation"                   | 15,000 HC      |
| `function`         | Business function                   | "Claims Management"                  | 500-2,000 HC   |
| `sub_function`     | Sub-function within a function      | "Claims Processing"                  | 100-500 HC     |
| `job_family`       | Job family (group of related roles) | "Claims Adjusters"                   | 30-150 HC      |
| `role`             | Single role                         | "Senior Claims Adjuster - P&C"       | 10-80 HC       |

### Hierarchy Tree

```
Organization
  └── Function (e.g., Claims Management)
        └── Sub-Function (e.g., Claims Processing)
              └── Job Family Group (e.g., Claims Operations)
                    └── Job Family (e.g., Claims Adjusters)
                          └── Role (e.g., Senior Claims Adjuster - P&C)
                                ├── Job Titles (with career bands, salaries)
                                ├── Workloads (with effort allocation)
                                │     └── Tasks (with automation levels)
                                ├── Skills (with lifecycle status)
                                └── Technologies
```

### Scope Selection Input

```json
{
  "scope_type": "function",
  "scope_name": "Claims Management"
}
```

### Scope Selection Output

```json
{
  "scope_name": "Claims Management",
  "scope_type": "function",
  "roles": [...],
  "job_titles": [...],
  "workloads": [...],
  "tasks": [...],
  "skills": [...],
  "technologies": [...],
  "task_skill_mappings": { "task_id": [{"skill_id", "skill_name", "relevance"}] },
  "summary": {
    "role_count": 22,
    "title_count": 66,
    "workload_count": 88,
    "task_count": 528,
    "skill_count": 45,
    "tech_count": 12,
    "total_headcount": 1050
  }
}
```

---

## 3. Simulation Types

### 3.1 Role Redesign

**Purpose**: "What happens if we automate tasks in this scope?"

Applies an automation factor to advance task automation levels. Most automatable task categories (directive, feedback_loop) are targeted first.

#### Input Parameters

| Parameter               | Type       | Default                         | Description                                    |
|-------------------------|------------|----------------------------------|------------------------------------------------|
| `automation_factor`     | float      | `0.5`                           | 0–1. How aggressively to automate (0.3=mild, 0.5=moderate, 0.8=aggressive) |
| `target_classifications`| string[]   | `["directive","feedback_loop"]`  | Which Etter categories to automate             |

#### Example Request

```json
{
  "type": "role_redesign",
  "scope_type": "function",
  "scope_name": "Claims Management",
  "parameters": {
    "automation_factor": 0.5
  },
  "timeline_months": 36
}
```

#### Output Summary

| Output Field                      | Type    | Description                                          |
|-----------------------------------|---------|------------------------------------------------------|
| `parameters.tasks_reclassified`   | int     | Number of tasks whose automation level changed       |
| `current.total_headcount`         | int     | Headcount before simulation                          |
| `future.freed_headcount`          | float   | FTEs freed by automation                             |
| `future.redeployable`             | float   | FTEs that can be redeployed internally               |
| `comparison.avg_transformation_index` | float | 0–100, how much roles are transformed             |
| `comparison.roles_needing_redesign`   | string[] | Roles with >40% freed capacity                   |
| `cascade.financial.gross_savings` | float   | Total salary savings ($)                             |
| `cascade.financial.total_cost`    | float   | Implementation + change mgmt + tech + reskilling ($) |
| `cascade.financial.net_impact`    | float   | Savings minus costs ($)                              |
| `cascade.financial.roi_pct`       | float   | Return on investment (%)                             |
| `cascade.financial.payback_months`| int     | Months to break even                                 |
| `cascade.skill_shifts.sunrise_skills` | object[] | New/growing skills needed                        |
| `cascade.skill_shifts.sunset_skills`  | object[] | Declining skills                                 |
| `cascade.risks`                   | object  | Risk assessment (high automation %, workforce reduction, etc.) |
| `skills_strategy`                 | object  | Reskilling plan, build-vs-buy recommendations        |

---

### 3.2 Technology Adoption

**Purpose**: "What happens if we deploy [specific technology]?"

Matches a technology's capabilities to tasks via keyword matching, reclassifies matched tasks, and runs the full cascade including licensing costs.

#### Input Parameters

| Parameter           | Type     | Default              | Description                                      |
|---------------------|----------|----------------------|--------------------------------------------------|
| `technology_name`   | string   | `"Microsoft Copilot"`| Must match a profile name (see Section 8)        |
| `adoption_months`   | int      | `12`                 | Timeline for adoption curve measurement          |
| `custom_profile`    | object   | `null`               | Custom technology profile (overrides built-in)   |

#### Custom Profile Structure (optional)

```json
{
  "name": "My Custom Tool",
  "vendor": "Internal",
  "license_tier": "medium",
  "capabilities": ["document analysis", "report generation"],
  "classification_shift": "shared",
  "task_keywords": ["document", "report", "analyze", "review"],
  "adoption_speed": "moderate",
  "monthly_per_user_override": 45.0
}
```

#### Example Request

```json
{
  "type": "tech_adoption",
  "scope_type": "function",
  "scope_name": "Claims Management",
  "parameters": {
    "technology_name": "Microsoft Copilot",
    "adoption_months": 12
  }
}
```

#### Output Summary

Includes everything from Role Redesign, plus:

| Output Field                         | Type    | Description                                    |
|--------------------------------------|---------|------------------------------------------------|
| `technology.name`                    | string  | Technology deployed                            |
| `technology.vendor`                  | string  | Vendor name                                    |
| `technology.license_tier`            | string  | low/medium/high/enterprise                     |
| `technology.adoption_speed`          | string  | fast/moderate/slow                             |
| `task_matching.tasks_matched`        | int     | Tasks matched by keyword                       |
| `task_matching.total_tasks`          | int     | Total tasks in scope                           |
| `task_matching.match_rate_pct`       | float   | Match percentage                               |
| `task_matching.matched_task_names`   | string[]| Names of matched tasks                         |
| `adoption_curve`                     | object[]| Month-by-month adoption % and realized savings |
| `adoption_discount_factor`           | float   | Weighted-average adoption (discount on savings)|
| `technology_costs`                   | object  | Licensing + implementation breakdown           |
| `recommendation.verdict`             | string  | STRONG_RECOMMEND / RECOMMEND / CONDITIONAL / CAUTIOUS / NOT_RECOMMENDED |
| `recommendation.reasoning`           | string  | Explanation of verdict                         |

---

### 3.3 Multi-Technology Adoption

**Purpose**: "What happens if we deploy multiple technologies simultaneously?"

Deploys multiple technologies together. When two technologies affect the same task, the higher automation level wins. Costs are additive per technology.

#### Input Parameters

| Parameter           | Type     | Default | Description                                         |
|---------------------|----------|---------|-----------------------------------------------------|
| `technology_names`  | string[] | `[]`    | List of technology names to deploy together          |
| `adoption_months`   | int      | `12`    | Timeline for adoption curve                          |
| `custom_profiles`   | object   | `null`  | Dict mapping tech name → custom profile              |

#### Example Request

```json
{
  "type": "multi_tech_adoption",
  "scope_type": "function",
  "scope_name": "Claims Management",
  "parameters": {
    "technology_names": ["Microsoft Copilot", "UiPath", "Claims AI"],
    "adoption_months": 12
  }
}
```

#### Output Summary

Includes everything from Tech Adoption, plus:

| Output Field                         | Type    | Description                                    |
|--------------------------------------|---------|------------------------------------------------|
| `technologies`                       | object[]| List of deployed techs with vendor, speed      |
| `combined_adoption_speed`            | string  | Weighted-average speed across all techs        |
| `task_matching.unique_tasks_matched`  | int     | Unique tasks affected (after dedup)            |
| `task_matching.overlap_tasks`         | int     | Tasks affected by 2+ technologies              |
| `task_matching.per_technology`        | object  | Per-tech task match breakdown                  |
| `per_technology_summary`             | object[]| Per-tech: tasks matched/won, costs             |
| `per_technology_costs`               | object  | Per-tech cost breakdown                        |
| `combined_technology_costs`          | object  | Combined licensing + implementation            |

---

### 3.4 Task Distribution

**Purpose**: "What task automation mix should we target?"

User specifies a target distribution across automation levels (e.g., 10% human_only, 35% shared, 25% ai_led, etc.) and the engine computes the minimum task reclassifications to achieve it.

#### Input Parameters

| Parameter               | Type       | Default                          | Description                                |
|-------------------------|------------|-----------------------------------|--------------------------------------------|
| `distribution_target`   | object     | (see below)                       | Target percentages per automation level    |
| └ `human_only_pct`      | float      | `10.0`                           | % of work-time at human_only level         |
| └ `human_led_pct`       | float      | `25.0`                           | % at human_led                             |
| └ `shared_pct`          | float      | `35.0`                           | % at shared                                |
| └ `ai_led_pct`          | float      | `25.0`                           | % at ai_led                                |
| └ `ai_only_pct`         | float      | `5.0`                            | % at ai_only                               |
| └ `target_classifications` | string[] | `null` (all)                    | Only redistribute these Etter categories   |
| └ `max_steps_per_task`  | int        | `2`                              | Max levels a task can jump (1–4)           |
| └ `min_time_allocation_pct` | float  | `0.0`                           | Skip tasks below this time threshold       |

**Important**: Percentages must sum to 100%.

#### Example Request

```json
{
  "type": "task_distribution",
  "scope_type": "function",
  "scope_name": "Claims Management",
  "parameters": {
    "distribution_target": {
      "human_only_pct": 10,
      "human_led_pct": 20,
      "shared_pct": 35,
      "ai_led_pct": 30,
      "ai_only_pct": 5,
      "max_steps_per_task": 2
    }
  }
}
```

#### Output Summary

| Output Field                | Type    | Description                                       |
|-----------------------------|---------|---------------------------------------------------|
| `current_distribution`      | object  | Current % per automation level                    |
| `target_distribution`       | object  | User's target % per level                         |
| `achieved_distribution`     | object  | What the engine actually achieved                 |
| `distribution_error`        | float   | Mean absolute error (achieved vs target)          |
| `eligible_tasks`            | int     | Tasks eligible for redistribution                 |
| `tasks_moved`               | int     | Tasks reclassified                                |
| `reclassifications`         | object[]| List of {task_id, new_automation_level}           |

Then runs through the cascade engine for full financial/workforce impact.

---

## 4. Simulation Engines

### v1 Engine (Single-Shot Cascade)

The v1 engine runs the 8-step cascade once and produces a theoretical maximum impact assuming 100% adoption on day 1.

**Steps**: Task reclassification → Workload scoring → Role impact → Skill shifts → Workforce impact → Financial model → Risk assessment → Validation

**Best for**: Quick scenario screening, comparing theoretical maximums.

### v2 Engine (Time-Stepped, Recommended)

The v2 engine wraps v1 to produce a **month-by-month trajectory** over 36 months with:

- **Bass Diffusion** adoption S-curve (fast/moderate/slow)
- **Human Factors** evolution (resistance, morale, proficiency, culture readiness)
- **J-Curve** productivity dip in early months
- **Feedback Loops** detection (5 loops: R1 productivity flywheel, R2 capability compounding, B1 change resistance, B2 skill gap brake, B3 knowledge drain)
- **NPV/ROI** with monthly discounting

**Best for**: Realistic projections, board-level presentations, scenario comparison.

### v2 Output Structure

```json
{
  "engine": "v2_time_stepped",
  "simulation_type": "role_redesign",
  "trajectory_summary": {
    "timeline_months": 36,
    "theoretical_max": {
      "freed_headcount": 350,
      "gross_savings": 25000000
    },
    "actual_at_end": {
      "adoption_level": 0.97,
      "effective_freed_hc": 310.5,
      "cumulative_savings": 19500000,
      "cumulative_costs": 6800000,
      "cumulative_net": 12700000,
      "npv": 10200000,
      "roi_pct": 186.8
    },
    "human_factors_final": {
      "resistance": 0.12,
      "morale": 0.78,
      "proficiency": 0.71,
      "culture_readiness": 0.68,
      "composite_multiplier": 0.74
    },
    "payback_month": 18,
    "breakeven_month": 22
  },
  "milestones": [
    {"month": 3, "adoption": {"level": 0.15}, ...},
    {"month": 6, "adoption": {"level": 0.35}, ...},
    {"month": 12, "adoption": {"level": 0.70}, ...},
    {"month": 24, "adoption": {"level": 0.92}, ...},
    {"month": 36, "adoption": {"level": 0.97}, ...}
  ],
  "monthly_snapshots": [
    {
      "month": 1,
      "adoption": {"level": 0.05, "delta": 0.05},
      "workforce": {
        "current_headcount": 1050,
        "effective_freed_hc": 9.2,
        "separated_this_month": 0.8,
        "separated_cumulative": 0.8,
        "redeployed_cumulative": 0.0,
        "attrited_this_month": 10.5
      },
      "financial": {
        "monthly_savings": 65000,
        "monthly_costs": 180000,
        "monthly_net": -115000,
        "cumulative_savings": 65000,
        "cumulative_costs": 180000,
        "cumulative_net": -115000,
        "npv_to_date": -114200
      },
      "human_factors": {
        "resistance": 0.58,
        "morale": 0.69,
        "proficiency": 0.13,
        "culture_readiness": 0.32,
        "composite_multiplier": 0.39
      },
      "productivity_multiplier": 0.85,
      "j_curve_active": true,
      "active_feedback_loops": ["B1_change_resistance", "B2_skill_gap_brake"]
    }
  ],
  "cascade": { ... },
  "skills_strategy": { ... }
}
```

### Monthly Snapshot Fields (for charts)

| Field Path                          | Type    | Chart Use                              |
|-------------------------------------|---------|----------------------------------------|
| `adoption.level`                    | float   | Adoption S-curve line chart            |
| `workforce.effective_freed_hc`      | float   | Freed headcount area chart             |
| `workforce.separated_cumulative`    | float   | Cumulative separations                 |
| `financial.monthly_savings`         | float   | Monthly savings bar chart              |
| `financial.monthly_costs`           | float   | Monthly costs bar chart                |
| `financial.cumulative_net`          | float   | Cumulative net line chart (J-curve!)   |
| `financial.npv_to_date`             | float   | NPV progression                        |
| `human_factors.resistance`          | float   | Resistance decay curve                 |
| `human_factors.morale`              | float   | Morale trajectory                      |
| `human_factors.proficiency`         | float   | Proficiency growth curve               |
| `human_factors.composite_multiplier`| float   | HFM line (overall org effectiveness)   |
| `j_curve_active`                    | bool    | J-curve indicator overlay              |
| `active_feedback_loops`             | string[]| Loop activation timeline               |

---

## 5. Configuration Knobs

These are optional overrides passed via `SimulationConfig`. The UI can expose these as "Advanced Settings".

### Financial Configuration

| Parameter                        | Type  | Default | Description                                    |
|----------------------------------|-------|---------|------------------------------------------------|
| `j_curve_enabled`                | bool  | `false` | Enable productivity J-curve during transition  |
| `j_curve_dip_pct`               | float | `15.0`  | % productivity drop at peak J-curve            |
| `j_curve_duration_months`        | int   | `6`     | Duration of J-curve effect                     |
| `severance_months`               | float | `3.0`   | Months of salary per separated employee        |
| `change_management_pct`          | float | `5.0`   | % of gross savings for change management       |
| `reskilling_cost_per_skill_per_person` | float | `2500.0` | Base reskilling cost per skill          |
| `include_tech_cost_in_role_redesign` | bool | `true` | Include tech tooling cost in role redesign  |
| `default_tech_cost_per_user_month` | float | `25.0` | Tech cost when no specific tech selected     |

### Organization Profile

| Parameter                        | Type  | Default | Description                                    |
|----------------------------------|-------|---------|------------------------------------------------|
| `initial_resistance`             | float | `0.6`   | Starting resistance level (0–1)                |
| `initial_morale`                 | float | `0.7`   | Starting morale (0–1)                          |
| `initial_ai_proficiency`         | float | `0.1`   | Starting AI proficiency (0–1)                  |
| `initial_culture_readiness`      | float | `0.3`   | Starting culture readiness (0–1)               |
| `culture_time_constant_months`   | int   | `24`    | How slowly culture changes (months)            |
| `base_annual_attrition_pct`      | float | `12.0`  | Natural annual employee turnover               |

### Cascade Configuration

| Parameter                        | Type  | Default | Description                                    |
|----------------------------------|-------|---------|------------------------------------------------|
| `redeployability_pct`            | float | `60.0`  | % of freed workers redeployable internally     |

### Constraints (Post-Simulation Limits)

| Parameter                         | Type     | Default | Description                               |
|-----------------------------------|----------|---------|-------------------------------------------|
| `max_headcount_reduction_pct`     | float    | `100.0` | Cap headcount reduction                   |
| `budget_cap`                      | float    | `null`  | Flag when total cost exceeds this amount  |
| `protected_roles`                 | string[] | `[]`    | Roles excluded from headcount impact      |

### Scenario Timeline

| Parameter           | Type | Default | Description                                    |
|---------------------|------|---------|------------------------------------------------|
| `timeline_months`   | int  | `36`    | Simulation duration in months                  |

---

## 6. Output Structures

### Cascade Result (shared across all simulation types)

```json
{
  "task_changes": {
    "total_tasks": 528,
    "tasks_changed": 145,
    "changes": [
      {
        "task_id": "task_001",
        "task_name": "Process initial claims intake",
        "old_level": "human_led",
        "new_level": "shared",
        "workload_id": "wl_001"
      }
    ]
  },
  "workload_changes": {
    "changes": [
      {
        "workload_id": "wl_001",
        "role_id": "role_001",
        "old_level": "human_led",
        "new_level": "shared",
        "new_automation_score": 45.0
      }
    ]
  },
  "role_impacts": {
    "impacts": [
      {
        "role_id": "role_001",
        "role_name": "Claims Adjuster - P&C",
        "freed_capacity_pct": 32.5,
        "transformation_index": 48.8,
        "title_impacts": [
          {
            "title": "Junior Claims Adjuster",
            "career_band": "entry",
            "headcount": 25,
            "avg_salary": 52000,
            "freed_capacity_pct": 45.5,
            "impact_factor": 1.4
          }
        ]
      }
    ]
  },
  "skill_shifts": {
    "sunrise_skills": [
      {"name": "AI Prompt Engineering", "category": "digital", "type": "universal"}
    ],
    "sunset_skills": [
      {"name": "Manual Data Entry", "lifecycle_status": "declining"}
    ]
  },
  "workforce": {
    "current_headcount": 1050,
    "freed_headcount": 350.0,
    "reduction_pct": 33.3,
    "redeployable": 210.0,
    "separations": 140.0,
    "attrition_adjustment": 126.0
  },
  "financial": {
    "gross_savings": 25200000,
    "total_cost": 6800000,
    "net_impact": 18400000,
    "roi_pct": 270.6,
    "payback_months": 10,
    "technology_licensing": 3150000,
    "implementation_cost": 472500,
    "reskilling_cost": 1250000,
    "change_management_cost": 1260000,
    "severance_cost": 667500
  },
  "risks": {
    "risks": [...],
    "risk_count": 3,
    "high_risks": 1,
    "risk_score": 45
  }
}
```

### Skills Strategy Result (always runs post-cascade)

```json
{
  "demand_analysis": {
    "sunrise": [{"name": "AI Prompt Engineering", "category": "digital", "trend": "rising", "priority": "high"}],
    "sunset": [{"name": "Manual Filing", "category": "domain", "trend": "falling", "action": "phase_out"}],
    "stable": [{"name": "Negotiation", "category": "communication", "trend": "stable"}]
  },
  "concentration_risk": {
    "total_roles_in_scope": 22,
    "concentration_threshold": 3,
    "high_risk_count": 4,
    "high_risk_skills": [
      {"skill_name": "Subrogation Law", "role_count": 1, "risk": "critical", "recommendation": "Cross-train immediately"}
    ]
  },
  "reskilling_plan": {
    "skills": [
      {"skill_name": "AI Prompt Engineering", "category": "digital", "timeline_months": 5, "headcount": 45, "cost": 135000}
    ],
    "total_cost": 675000,
    "avg_months": 4.5,
    "headcount_impacted": 45,
    "band_breakdown": {
      "entry": {"headcount": 15, "multiplier": 0.7},
      "mid": {"headcount": 20, "multiplier": 1.0},
      "senior": {"headcount": 10, "multiplier": 1.3}
    }
  },
  "build_vs_buy": {
    "recommendations": [
      {"skill": "AI Prompt Engineering", "action": "build", "reasoning": "Fast reskilling timeline and manageable cost"}
    ]
  }
}
```

### Scenario Comparison Result

```json
{
  "scenarios": [
    {
      "scenario_id": "scenario_baseline_1234",
      "scenario_name": "Baseline",
      "simulation_type": "role_redesign",
      "financial": {
        "gross_savings": 25200000,
        "net_impact": 18400000,
        "roi_pct": 270.6,
        "payback_months": 10,
        "total_cost": 6800000
      },
      "workforce": {
        "freed_headcount": 350,
        "reduction_pct": 33.3,
        "redeployable": 210
      },
      "skills": {
        "sunrise_count": 5,
        "sunset_count": 3,
        "reskilling_cost": 675000
      },
      "risk": {
        "total_risks": 3,
        "high_risks": 1
      }
    }
  ],
  "best_by_roi": "Baseline",
  "lowest_risk": "Conservative",
  "trade_off_summary": "Baseline: ROI=271%, High Risks=1 | Conservative: ROI=164%, High Risks=0"
}
```

---

## 7. REST API Reference

All endpoints are prefixed with `/api/dt`.

### Navigation & Scope

| Method | Endpoint                         | Description                                |
|--------|----------------------------------|--------------------------------------------|
| GET    | `/taxonomy`                      | Full taxonomy tree for navigation sidebar  |
| GET    | `/hierarchy`                     | Full hierarchy with role/task counts        |
| GET    | `/functions`                     | List functions for scope dropdown           |
| GET    | `/scope/<scope_type>/<scope_name>` | Get all entities in a scope              |
| GET    | `/technologies`                  | List available technology profiles          |
| GET    | `/readiness`                     | Graph readiness score                      |

### Simulation Execution

| Method | Endpoint                         | Description                                |
|--------|----------------------------------|--------------------------------------------|
| POST   | `/simulate`                      | Run a simulation and get results           |

**Request Body**:

```json
{
  "type": "role_redesign | tech_adoption | multi_tech_adoption | task_distribution",
  "scope_type": "function",
  "scope_name": "Claims Management",
  "name": "Optional scenario name",
  "parameters": { ... },
  "timeline_months": 36
}
```

**Response**:

```json
{
  "scenario_id": "scenario_role_redesign_claims_management_1234567890",
  "config": { ... },
  "result": { ... }
}
```

### Scenario Management

| Method | Endpoint                         | Description                                |
|--------|----------------------------------|--------------------------------------------|
| GET    | `/scenarios`                     | List all saved scenarios                   |
| GET    | `/scenarios/<scenario_id>`       | Get scenario with full results             |
| DELETE | `/scenarios/<scenario_id>`       | Delete a scenario                          |

### Comparison

| Method | Endpoint                         | Description                                |
|--------|----------------------------------|--------------------------------------------|
| POST   | `/compare`                       | Compare 2+ scenarios side-by-side          |

**Request Body**:

```json
{
  "scenario_ids": ["scenario_id_1", "scenario_id_2"]
}
```

---

## 8. Available Technologies

Pre-built technology profiles for tech adoption simulations:

| Technology          | Vendor           | License Tier | Cost/User/Mo | Adoption Speed | Target Level | Key Capabilities                                    |
|---------------------|------------------|--------------|-------------|----------------|--------------|-----------------------------------------------------|
| Microsoft Copilot   | Microsoft        | medium       | $30         | moderate       | shared       | Document creation, email, reports, spreadsheets      |
| UiPath              | UiPath           | high         | $75         | slow           | ai_led       | Data entry, form processing, invoice automation      |
| ServiceNow AI       | ServiceNow       | high         | $75         | moderate       | ai_led       | Ticket routing, incident categorization              |
| Salesforce Einstein | Salesforce       | high         | $75         | moderate       | shared       | Lead scoring, forecasting, customer segmentation     |
| Claims AI           | Custom/Internal  | enterprise   | $150        | slow           | shared       | Document extraction, fraud detection, triage         |
| GitHub Copilot      | GitHub/Microsoft | low          | $10         | fast           | shared       | Code generation, code review, test generation        |

### License Cost Tiers

| Tier       | Monthly Per User |
|------------|-----------------|
| low        | $10             |
| medium     | $30             |
| high       | $75             |
| enterprise | $150            |

### Adoption Speed Profiles (Bass Diffusion Parameters)

| Speed    | Innovation (p) | Imitation (q) | ~Month 6 | ~Month 12 | ~Month 24 |
|----------|---------------|---------------|----------|-----------|-----------|
| fast     | 0.03          | 0.60          | ~60%     | ~90%      | ~98%      |
| moderate | 0.02          | 0.40          | ~35%     | ~70%      | ~92%      |
| slow     | 0.01          | 0.25          | ~20%     | ~50%      | ~85%      |

---

## 9. UI Workflow Recommendations

### Primary User Flow

```
1. Landing Page
   └── Show organization overview (from /hierarchy)
       ├── Total headcount, role count, function count
       └── "Start Simulation" CTA

2. Scope Selection
   └── Tree navigator (from /taxonomy)
       ├── Click function → shows summary stats
       ├── Drill into sub-function/job-family/role
       └── "Simulate This Scope" button

3. Simulation Configuration
   ├── Choose simulation type (tabs or cards):
   │   ├── Role Redesign — automation factor slider (0.3–0.8)
   │   ├── Tech Adoption — technology picker dropdown
   │   ├── Multi-Tech — multi-select technology picker
   │   └── Task Distribution — 5 percentage sliders (must sum to 100%)
   ├── Advanced Settings (collapsible):
   │   ├── Timeline (12/24/36 months)
   │   ├── J-curve toggle
   │   ├── Organization profile (resistance, morale presets)
   │   └── Constraints (budget cap, protected roles)
   └── "Run Simulation" button

4. Results Dashboard
   ├── Summary Cards:
   │   ├── Adoption % | Freed HC | Net Savings | ROI % | Breakeven Month
   │   └── Verdict badge (for tech adoption)
   ├── Charts (from monthly_snapshots):
   │   ├── Adoption S-curve (line chart)
   │   ├── Financial trajectory (stacked bar: savings vs costs, cumulative net line)
   │   ├── Human factors radar/line chart (R, M, P, C over time)
   │   └── Workforce waterfall (current → freed → redeployed → separated)
   ├── Tables:
   │   ├── Role impact table (sortable by transformation index)
   │   ├── Skill shifts (sunrise/sunset lists)
   │   └── Risk register
   └── Actions:
       ├── "Save Scenario" (auto-saved, name editable)
       ├── "Run Another Scenario" (back to step 3)
       └── "Compare Scenarios" (select 2+ saved scenarios)

5. Comparison View
   ├── Side-by-side summary table (financial, workforce, skills, risk)
   ├── Overlaid charts (adoption curves, financial trajectories)
   ├── Trade-off analysis text
   └── "Best by ROI" / "Lowest Risk" badges
```

### Suggested UI Components

| Component              | Data Source                      | Widget Type                |
|------------------------|----------------------------------|----------------------------|
| Scope Tree             | GET /taxonomy                    | Tree view / accordion       |
| Technology Picker      | GET /technologies                | Dropdown / card selector    |
| Automation Slider      | parameters.automation_factor     | Range slider (0.0–1.0)     |
| Distribution Sliders   | parameters.distribution_target   | 5 linked sliders (sum=100) |
| Adoption Chart         | monthly_snapshots[].adoption     | Line chart                  |
| Financial Chart        | monthly_snapshots[].financial    | Stacked bar + line overlay  |
| Human Factors Chart    | monthly_snapshots[].human_factors| Multi-line or radar chart   |
| Workforce Waterfall    | cascade.workforce                | Waterfall chart             |
| Role Impact Table      | cascade.role_impacts.impacts     | Sortable data table         |
| Skill Shift Lists      | cascade.skill_shifts             | Two-column list (↑ / ↓)    |
| Risk Register          | cascade.risks.risks              | Severity-colored table      |
| Comparison Table       | POST /compare                    | Multi-column comparison     |
| Verdict Badge          | recommendation.verdict           | Colored badge               |
| Milestone Timeline     | milestones                       | Horizontal timeline         |

### Key Metrics for Dashboard Cards

| Metric           | Source (v2)                                          | Format     |
|------------------|------------------------------------------------------|------------|
| Adoption         | trajectory_summary.actual_at_end.adoption_level      | 97%        |
| Freed Headcount  | trajectory_summary.actual_at_end.effective_freed_hc   | 310 FTEs   |
| Net Savings      | trajectory_summary.actual_at_end.cumulative_net       | $12.7M     |
| ROI              | trajectory_summary.actual_at_end.roi_pct              | 187%       |
| Breakeven        | trajectory_summary.breakeven_month                    | Month 22   |
| NPV              | trajectory_summary.actual_at_end.npv                  | $10.2M     |
| Payback          | trajectory_summary.payback_month                      | Month 18   |

---

## Appendix A: Automation Levels

Tasks are classified into 5 automation levels (ordered from least to most automated):

| Level       | Description                            | Automation Fraction |
|-------------|----------------------------------------|---------------------|
| human_only  | No AI involvement                      | 0%                  |
| human_led   | Human leads, AI assists occasionally   | 15%                 |
| shared      | Human and AI collaborate equally       | 40%                 |
| ai_led      | AI leads, human supervises/approves    | 70%                 |
| ai_only     | Fully automated, no human needed       | 95%                 |

## Appendix B: Task Classifications (Etter Framework)

Tasks are categorized by AI automation potential:

| Category        | Description                              | Automation Eligibility |
|-----------------|------------------------------------------|------------------------|
| directive       | Fully automatable, minimal human input   | Highest                |
| feedback_loop   | Automatable with feedback adjustments    | High                   |
| learning        | Requires knowledge acquisition           | Medium                 |
| validation      | AI helps verify and improve work         | Medium                 |
| task_iteration  | Needs human-AI collaboration             | Low                    |
| negligibility   | Cannot be automated using AI             | None                   |

## Appendix C: Career Band Impact Factors

Higher career bands see less automation impact (they supervise AI, not get replaced by it):

| Band      | Impact Factor | Effect                      |
|-----------|---------------|-----------------------------|
| entry     | 1.4x          | Most impacted by automation |
| mid       | 1.2x          |                             |
| senior    | 1.0x          | Baseline                    |
| lead      | 0.8x          |                             |
| principal | 0.6x          |                             |
| director  | 0.4x          |                             |
| vp        | 0.3x          |                             |
| c_suite   | 0.2x          | Least impacted              |

## Appendix D: Human Factor Multiplier (HFM)

```
HFM = 0.30 × (1 - Resistance)
    + 0.25 × Proficiency
    + 0.20 × Morale
    + 0.25 × Culture Readiness

Range: 0.0 (fully blocked) → 1.0 (fully effective)
```

Affects both adoption speed and effective freed capacity throughout the simulation.
