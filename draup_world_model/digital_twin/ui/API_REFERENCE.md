# Digital Twin API Reference

> Complete reference for all REST API endpoints.
> Base URL: `http://localhost:5001/api/dt`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Setup](#authentication--setup)
3. [Endpoints](#endpoints)
   - [GET /readiness](#get-readiness)
   - [GET /taxonomy](#get-taxonomy)
   - [GET /functions](#get-functions)
   - [GET /scope/:type/:name](#get-scopetypename)
   - [GET /technologies](#get-technologies)
   - [POST /simulate](#post-simulate)
   - [GET /scenarios](#get-scenarios)
   - [GET /scenarios/:id](#get-scenariosid)
   - [DELETE /scenarios/:id](#delete-scenariosid)
   - [POST /compare](#post-compare)
4. [Error Handling](#error-handling)
5. [Data Type Reference](#data-type-reference)

---

## Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dt/readiness` | Graph readiness score with dimension breakdown |
| GET | `/api/dt/taxonomy` | Full taxonomy tree for navigation |
| GET | `/api/dt/functions` | List all functions (for dropdowns) |
| GET | `/api/dt/scope/:type/:name` | Scoped entity data |
| GET | `/api/dt/technologies` | Available technology profiles |
| POST | `/api/dt/simulate` | Run a simulation |
| GET | `/api/dt/scenarios` | List all scenarios |
| GET | `/api/dt/scenarios/:id` | Get scenario with results |
| DELETE | `/api/dt/scenarios/:id` | Delete a scenario |
| POST | `/api/dt/compare` | Compare multiple scenarios |

All endpoints return JSON. All error responses have the shape `{"error": "message"}`.

---

## Authentication & Setup

No authentication is required (this is a local prototype). The API requires:
1. A running Neo4j database with Digital Twin data loaded
2. The Flask app started via `python -m draup_world_model.digital_twin.ui.app`

The API is initialized at startup by `init_api(neo4j_conn)` which creates a `ScenarioManager` instance shared across all requests.

---

## Endpoints

### GET /readiness

Returns the graph data readiness score (0-100) and validation report.

**Request**: No parameters.

**Response**:
```json
{
  "readiness": {
    "total_score": 75,
    "max_score": 100,
    "status": "READY",
    "dimensions": {
      "taxonomy_completeness": { "score": 25, "max": 25 },
      "role_decomposition":    { "score": 20, "max": 30 },
      "skills_architecture":   { "score": 15, "max": 20 },
      "enterprise_context":    { "score": 10, "max": 15 },
      "validation_trust":      { "score": 5,  "max": 10 }
    }
  },
  "validation": {
    "node_counts": {
      "DTOrganization": 1,
      "DTFunction": 12,
      "DTSubFunction": 33,
      "DTJobFamilyGroup": 56,
      "DTJobFamily": 113,
      "DTRole": 180,
      "DTJobTitle": 350,
      "DTWorkload": 600,
      "DTTask": 2400,
      "DTSkill": 250,
      "DTTechnology": 90
    },
    "relationship_counts": {
      "DT_CONTAINS": 214,
      "DT_HAS_ROLE": 180,
      "DT_HAS_TITLE": 350,
      "DT_HAS_WORKLOAD": 600,
      "DT_CONTAINS_TASK": 2400,
      "DT_REQUIRES_SKILL": 900,
      "DT_USES_TECHNOLOGY": 450
    },
    "orphan_roles": 0,
    "orphan_tasks": 0,
    "roles_without_workloads": 0,
    "roles_without_skills": 0,
    "is_valid": true
  }
}
```

**Readiness dimensions explained**:

| Dimension | Max | Scoring |
|-----------|-----|---------|
| taxonomy_completeness | 25 | 10 pts: all 6 hierarchy levels present; 10 pts: roles exist; 5 pts: titles mapped |
| role_decomposition | 30 | 10 pts: roles have workloads; 10 pts: 4-8 tasks per workload; 10 pts: task classifications present |
| skills_architecture | 20 | 10 pts: role-skill mappings; 5 pts: skill catalog >=50; 5 pts: tech catalog >=20 |
| enterprise_context | 15 | 5 pts: headcount data; 5 pts: salary data; 5 pts: aggregation computed |
| validation_trust | 10 | 5 pts: no orphan nodes; 5 pts: structural validity |

**Status thresholds**: `READY` >= 70, `PARTIAL` >= 50, `NOT_READY` < 50

**Example** (curl):
```bash
curl http://localhost:5001/api/dt/readiness
```

---

### GET /taxonomy

Returns the full organizational taxonomy as a nested tree for UI navigation.

**Request**: No parameters.

**Response**:
```json
{
  "taxonomy": {
    "id": "acme_corporation",
    "name": "Acme Corporation",
    "type": "organization",
    "children": [
      {
        "id": "func_claims_management",
        "name": "Claims Management",
        "type": "function",
        "headcount": 2500,
        "children": [
          {
            "id": "sf_claims_management_claims_processing",
            "name": "Claims Processing",
            "type": "sub_function",
            "children": [
              {
                "id": "jfg_claims_management_claims_operations",
                "name": "Claims Operations",
                "type": "job_family_group",
                "children": [
                  {
                    "id": "jf_claims_adjusters",
                    "name": "Claims Adjusters",
                    "type": "job_family"
                  },
                  {
                    "id": "jf_claims_examiners",
                    "name": "Claims Examiners",
                    "type": "job_family"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Tree node types**: `organization` → `function` → `sub_function` → `job_family_group` → `job_family`

**Implementation note**: The tree is built in Python from 4 separate Cypher queries (functions, sub-functions, JFGs, JFs) and assembled by parent ID.

**Example**:
```bash
curl http://localhost:5001/api/dt/taxonomy
```

---

### GET /functions

Returns a flat list of all DTFunction nodes. Used for scope selection dropdowns.

**Request**: No parameters.

**Response**:
```json
{
  "functions": [
    { "id": "func_actuarial_and_analytics", "name": "Actuarial and Analytics", "headcount": 800 },
    { "id": "func_claims_management", "name": "Claims Management", "headcount": 2500 },
    { "id": "func_customer_service", "name": "Customer Service", "headcount": 2000 },
    { "id": "func_underwriting", "name": "Underwriting", "headcount": 1500 }
  ]
}
```

**Example**:
```bash
curl http://localhost:5001/api/dt/functions
```

---

### GET /scope/:type/:name

Returns all entities within an organizational scope. This is the data the simulation engine operates on.

**URL Parameters**:
| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| type | string | `organization`, `function`, `role` | Scope level |
| name | string | e.g., `Claims Management` | Entity name (URL-encoded) |

**Response** (for scope_type=function):
```json
{
  "scope": {
    "scope_type": "function",
    "scope_name": "Claims Management",
    "summary": {
      "role_count": 15,
      "total_headcount": 2500,
      "task_count": 320,
      "workload_count": 60,
      "skill_count": 45,
      "tech_count": 12
    },
    "roles": [
      {
        "id": "role_claims_adjuster",
        "name": "Claims Adjuster",
        "total_headcount": 350,
        "avg_salary": 55000,
        "automation_score": 0.35,
        "job_family_id": "jf_claims_adjusters"
      }
    ],
    "titles": [
      {
        "id": "title_junior_claims_adjuster",
        "name": "Junior Claims Adjuster",
        "role_id": "role_claims_adjuster",
        "career_band": "entry",
        "level": "entry",
        "headcount": 120,
        "avg_salary": 42000
      }
    ],
    "workloads": [
      {
        "id": "wl_claims_review",
        "name": "Claims Review and Assessment",
        "role_id": "role_claims_adjuster",
        "effort_allocation_pct": 35,
        "automation_level": "human_led"
      }
    ],
    "tasks": [
      {
        "id": "task_review_claim_docs",
        "name": "Review claim documentation",
        "workload_id": "wl_claims_review",
        "classification": "validation",
        "automation_level": "human_led",
        "automation_potential": 0.45,
        "time_allocation_pct": 20
      }
    ],
    "skills": [
      {
        "id": "skill_claims_assessment",
        "name": "Claims Assessment",
        "category": "domain",
        "lifecycle_status": "mature",
        "market_demand_trend": "stable"
      }
    ],
    "technologies": [
      {
        "id": "tech_claims_mgmt_system",
        "name": "Claims Management System",
        "category": "enterprise_software",
        "license_cost_tier": "high"
      }
    ]
  }
}
```

**Example**:
```bash
curl "http://localhost:5001/api/dt/scope/function/Claims%20Management"
```

---

### GET /technologies

Returns available technology profiles for the tech adoption simulation.

**Request**: No parameters.

**Response**:
```json
{
  "technologies": [
    {
      "name": "Microsoft Copilot",
      "vendor": "Microsoft",
      "license_tier": "medium",
      "capabilities": [
        "document_generation", "email_drafting", "data_summarization",
        "meeting_notes", "code_assistance", "presentation_creation"
      ],
      "adoption_speed": "fast"
    },
    {
      "name": "UiPath RPA",
      "vendor": "UiPath",
      "license_tier": "high",
      "capabilities": [
        "data_entry", "form_processing", "system_integration",
        "report_generation", "data_extraction", "reconciliation"
      ],
      "adoption_speed": "moderate"
    },
    {
      "name": "ServiceNow AI",
      "vendor": "ServiceNow",
      "license_tier": "high",
      "capabilities": [
        "ticket_routing", "incident_classification", "knowledge_suggestion",
        "workflow_automation", "predictive_analytics"
      ],
      "adoption_speed": "moderate"
    },
    {
      "name": "Salesforce Einstein",
      "vendor": "Salesforce",
      "license_tier": "medium",
      "capabilities": [
        "lead_scoring", "opportunity_prediction", "email_insights",
        "activity_capture", "forecasting"
      ],
      "adoption_speed": "fast"
    },
    {
      "name": "Claims AI Platform",
      "vendor": "Internal",
      "license_tier": "enterprise",
      "capabilities": [
        "claims_triage", "fraud_detection", "damage_assessment",
        "settlement_recommendation", "document_analysis"
      ],
      "adoption_speed": "slow"
    },
    {
      "name": "GitHub Copilot",
      "vendor": "GitHub",
      "license_tier": "low",
      "capabilities": [
        "code_generation", "code_review", "test_generation",
        "documentation", "debugging_assistance"
      ],
      "adoption_speed": "fast"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:5001/api/dt/technologies
```

---

### POST /simulate

Run a simulation scenario. This is the main endpoint - it creates a scenario, runs the cascade engine, and returns full results.

**Request body**:
```json
{
  "type": "role_redesign | tech_adoption",
  "scope_name": "Claims Management",
  "scope_type": "function",
  "name": "My Scenario Name",
  "parameters": {
    "automation_factor": 0.5,
    "technology_name": "Microsoft Copilot",
    "adoption_months": 12
  },
  "timeline_months": 36
}
```

**Request fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| type | string | No | `role_redesign` | Simulation type |
| scope_name | string | No | `Claims Management` | Function name to scope to |
| scope_type | string | No | `function` | Scope level (`organization`, `function`, `role`) |
| name | string | No | auto-generated | Scenario display name |
| parameters | object | No | `{}` | Simulation-specific parameters |
| timeline_months | integer | No | `36` | Financial projection timeline |

**Parameters for `role_redesign`**:
| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| automation_factor | float | 0.1 - 1.0 | 0.5 | How aggressively to automate (0.3=1 level shift, 0.7=2, 1.0=3) |
| target_classifications | list | | all | Which task classifications to target |

**Parameters for `tech_adoption`**:
| Parameter | Type | Values | Default | Description |
|-----------|------|--------|---------|-------------|
| technology_name | string | One of the 6 profiles | `Microsoft Copilot` | Technology to deploy |
| adoption_months | integer | 1-60 | 12 | Months to full adoption |

**Response** (abbreviated - full response can be very large):
```json
{
  "scenario_id": "scenario_abc123",
  "config": {
    "name": "Microsoft Copilot - Claims Management",
    "type": "tech_adoption",
    "scope": "Claims Management",
    "parameters": { "technology_name": "Microsoft Copilot" },
    "timeline_months": 36
  },
  "result": {
    "simulation_type": "tech_adoption",
    "cascade": {
      "task_changes": {
        "tasks_affected": 145,
        "total_tasks": 320,
        "changes": [
          {
            "task_id": "task_review_claim_docs",
            "task_name": "Review claim documentation",
            "old_level": "human_led",
            "new_level": "shared",
            "automation_delta": 0.25
          }
        ]
      },
      "workload_changes": {
        "workloads_affected": 42,
        "changes": [
          {
            "workload_id": "wl_claims_review",
            "workload_name": "Claims Review",
            "old_level": "human_led",
            "new_level": "shared",
            "automation_score": 0.55
          }
        ]
      },
      "role_impacts": {
        "roles_affected": 12,
        "impacts": [
          {
            "role_id": "role_claims_adjuster",
            "role_name": "Claims Adjuster",
            "freed_capacity_pct": 28.5,
            "transformation_index": 42.3,
            "title_impacts": [
              {
                "title_id": "title_junior_claims_adjuster",
                "title_name": "Junior Claims Adjuster",
                "level": "entry",
                "headcount": 120,
                "freed_capacity_pct": 39.9,
                "level_impact_factor": 1.4
              }
            ]
          }
        ]
      },
      "skill_shifts": {
        "sunrise_skills": ["AI Oversight", "Prompt Engineering"],
        "sunset_skills": ["Manual Data Entry"],
        "net_skill_shift": 1
      },
      "workforce": {
        "current_headcount": 2500,
        "freed_headcount": 47.3,
        "reduction_pct": 1.89,
        "redeployable": 33.1,
        "redeployable_pct": 70.0
      },
      "financial": {
        "gross_savings": 5200000,
        "technology_licensing": 900000,
        "implementation_cost": 450000,
        "reskilling_cost": 125000,
        "total_cost": 1475000,
        "net_impact": 3725000,
        "roi_pct": 252.5,
        "payback_months": 8,
        "title_details": [
          {
            "title": "Junior Claims Adjuster",
            "headcount": 120,
            "avg_salary": 42000,
            "freed_capacity_pct": 39.9,
            "savings": 2012400
          }
        ]
      },
      "risks": {
        "risk_count": 2,
        "high_risks": 0,
        "flags": [
          {
            "type": "broad_change",
            "severity": "medium",
            "detail": "145 of 320 tasks affected (45.3%)",
            "entity": "Claims Management"
          }
        ]
      },
      "summary": {
        "tasks_affected": 145,
        "roles_affected": 12,
        "freed_headcount": 47.3,
        "reduction_pct": 1.89,
        "gross_savings": 5200000,
        "net_impact": 3725000,
        "roi_pct": 252.5
      }
    },
    "skills_strategy": {
      "summary": {
        "sunrise_count": 8,
        "sunset_count": 3,
        "high_risk_skills": 2,
        "total_reskilling_cost": 125000,
        "avg_reskilling_months": 4
      },
      "demand_analysis": {
        "sunrise": [ { "name": "AI Oversight", "priority": "high" } ],
        "sunset": [ { "name": "Manual Data Entry", "priority": "medium" } ],
        "stable": [ { "name": "Claims Assessment", "priority": "low" } ]
      },
      "concentration_analysis": {
        "high_risk": [ { "skill": "Fraud Detection", "role_count": 2 } ]
      },
      "reskilling_plan": {
        "skills": [...],
        "total_cost": 125000,
        "timeline_months": 6
      },
      "build_vs_buy": {
        "recommendations": [
          { "skill": "AI Oversight", "action": "build", "reasoning": "Internal expertise available" },
          { "skill": "Prompt Engineering", "action": "buy_and_build", "reasoning": "..." }
        ]
      }
    },
    "technology": {
      "name": "Microsoft Copilot",
      "vendor": "Microsoft",
      "tasks_matched": 145,
      "total_tasks": 320,
      "match_pct": 45.3
    },
    "recommendation": {
      "verdict": "RECOMMEND",
      "reasoning": "Positive ROI (252.5%) with moderate risk. 145 tasks automated with 8-month payback.",
      "score": 78
    },
    "adoption_curve": {
      "months": [1, 2, 3, 6, 9, 12],
      "adoption_pct": [10, 25, 45, 70, 88, 100]
    }
  }
}
```

**Example**:
```bash
# Role redesign
curl -X POST http://localhost:5001/api/dt/simulate \
  -H "Content-Type: application/json" \
  -d '{"type": "role_redesign", "scope_name": "Claims Management", "parameters": {"automation_factor": 0.5}}'

# Tech adoption
curl -X POST http://localhost:5001/api/dt/simulate \
  -H "Content-Type: application/json" \
  -d '{"type": "tech_adoption", "scope_name": "Underwriting", "parameters": {"technology_name": "Microsoft Copilot"}}'
```

---

### GET /scenarios

List all stored scenarios with their metadata and status.

**Request**: No parameters.

**Response**:
```json
{
  "scenarios": [
    {
      "id": "scenario_abc123",
      "name": "Microsoft Copilot - Claims Management",
      "type": "tech_adoption",
      "status": "completed",
      "scope_type": "function",
      "scope_name": "Claims Management"
    },
    {
      "id": "scenario_def456",
      "name": "Role Redesign - Underwriting",
      "type": "role_redesign",
      "status": "completed",
      "scope_type": "function",
      "scope_name": "Underwriting"
    }
  ]
}
```

**Scenario statuses**: `pending`, `running`, `completed`, `failed`

**Example**:
```bash
curl http://localhost:5001/api/dt/scenarios
```

---

### GET /scenarios/:id

Get a specific scenario with its full results.

**URL Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Scenario ID (from create/simulate response) |

**Response**: Same structure as the `result` field in the `/simulate` response, wrapped in a `scenario` object with config metadata.

```json
{
  "scenario": {
    "id": "scenario_abc123",
    "config": { "name": "...", "type": "...", ... },
    "status": "completed",
    "result": { ... }
  }
}
```

**Error** (404):
```json
{ "error": "Scenario not found" }
```

**Example**:
```bash
curl http://localhost:5001/api/dt/scenarios/scenario_abc123
```

---

### DELETE /scenarios/:id

Delete a stored scenario.

**URL Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Scenario ID to delete |

**Response** (success):
```json
{ "deleted": true }
```

**Response** (not found, 404):
```json
{ "error": "Scenario not found" }
```

**Example**:
```bash
curl -X DELETE http://localhost:5001/api/dt/scenarios/scenario_abc123
```

---

### POST /compare

Compare 2 or more scenarios side-by-side across financial, workforce, skills, and risk dimensions.

**Request body**:
```json
{
  "scenario_ids": ["scenario_abc123", "scenario_def456"]
}
```

**Request fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| scenario_ids | list[string] | Yes | At least 2 scenario IDs |

**Response**:
```json
{
  "comparison": {
    "best_by_roi": "Microsoft Copilot - Claims Management",
    "lowest_risk": "Role Redesign - Underwriting",
    "scenarios": [
      {
        "scenario_id": "scenario_abc123",
        "scenario_name": "Microsoft Copilot - Claims Management",
        "financial": {
          "gross_savings": 5200000,
          "net_impact": 3725000,
          "total_cost": 1475000,
          "roi_pct": 252.5,
          "payback_months": 8
        },
        "workforce": {
          "freed_headcount": 47.3,
          "reduction_pct": 1.89,
          "redeployable": 33.1
        },
        "skills": {
          "sunrise_count": 8,
          "sunset_count": 3
        },
        "risk": {
          "total_risks": 2,
          "high_risks": 0
        }
      },
      {
        "scenario_id": "scenario_def456",
        "scenario_name": "Role Redesign - Underwriting",
        "financial": { ... },
        "workforce": { ... },
        "skills": { ... },
        "risk": { ... }
      }
    ]
  }
}
```

**Error** (400):
```json
{ "error": "Need at least 2 scenario IDs" }
```

**Example**:
```bash
curl -X POST http://localhost:5001/api/dt/compare \
  -H "Content-Type: application/json" \
  -d '{"scenario_ids": ["scenario_abc123", "scenario_def456"]}'
```

---

## Error Handling

All endpoints follow a consistent error pattern:

**Server errors** (500):
```json
{ "error": "Detailed error message from the server" }
```

**Not found** (404):
```json
{ "error": "Scenario not found" }
```

**Bad request** (400):
```json
{ "error": "Need at least 2 scenario IDs" }
```

**API not initialized** (500):
```json
{ "error": "API not initialized - call init_api() first" }
```

Common error scenarios:
- Neo4j is not running → "Neo4j connection failed"
- No data loaded → empty results, zero counts
- Invalid scope name → "No roles found for scope"
- Missing technology name → defaults to "Microsoft Copilot"

---

## Data Type Reference

### Automation Levels
```
human_only → human_led → shared → ai_led → ai_only
```
These are ordered. The cascade engine advances tasks along this spectrum.

### Task Classifications (Etter 6-category AI Automation Potential)
```
directive, feedback_loop, learning,
validation, task_iteration, negligibility
```

### Career Bands / Levels
```
entry, mid, senior, lead, principal, executive
```

### Level Impact Factors (used in cascade)
| Level | Factor | Meaning |
|-------|--------|---------|
| entry | 1.4 | Entry-level roles feel 40% more automation impact |
| mid | 1.2 | Mid-level roles feel 20% more |
| senior | 1.0 | Senior roles feel baseline impact |
| lead | 0.8 | Leads feel 20% less (more strategic work) |
| principal | 0.6 | Principals feel 40% less |
| executive | 0.4 | Executives feel 60% less |

### License Cost Tiers
| Tier | Cost per user/month |
|------|-------------------|
| low | $10 |
| medium | $30 |
| high | $75 |
| enterprise | $150 |

### Technology Adoption Speeds
| Speed | Month 3 | Month 6 | Month 12 |
|-------|---------|---------|----------|
| fast | 45% | 75% | 100% |
| moderate | 25% | 55% | 90% |
| slow | 15% | 35% | 70% |

### Risk Severity Levels
- **high**: Requires immediate attention (>60% automation, >20% workforce reduction)
- **medium**: Monitor closely (>50 tasks affected, >5 new skills needed)
- **low**: Informational

### Recommendation Verdicts
| Verdict | Meaning |
|---------|---------|
| STRONG_RECOMMEND | High ROI, low risk |
| RECOMMEND | Positive ROI, acceptable risk |
| CONDITIONAL | Positive ROI but with significant risks |
| CAUTIOUS | Marginal ROI or high risk |
| NOT_RECOMMENDED | Negative ROI or unacceptable risk |
