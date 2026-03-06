/**
 * TypeScript types mirroring Python engine dataclasses.
 * Single source of truth for all API response shapes.
 */

// ─── Organization ───
export interface Role {
  role_id: string
  role_name: string
  function: string
  sub_function: string
  jfg: string
  job_family: string
  management_level: string
  headcount: number
  avg_salary: number
  annual_cost: number
  automation_score: number
  augmentation_score: number
  quantification_score: number
}

export interface TaskDetail {
  task_id: string
  task_name: string
  category: string
  effort_hours: number
  automatable_by: string | null
  compliance: boolean
  l1: number
  l2: number
  l3: number
}

export interface SkillDetail {
  skill_id: string
  skill_name: string
  skill_type: string
  proficiency_required: number
  is_sunrise: boolean
  is_sunset: boolean
}

export interface ToolInfo {
  tool_id: string
  tool_name: string
  deployed_to_functions: string[]
  task_categories_addressed: string[]
  license_cost: number
  current_adoption_pct: number
}

export interface HumanSystemInfo {
  function: string
  ai_proficiency: number
  change_readiness: number
  trust_level: number
  political_capital: number
  transformation_fatigue: number
  learning_velocity_months: number
  effective_multiplier: number
}

export interface OrgSummary {
  total_headcount: number
  total_annual_cost: number
  functions: string[]
  role_count: number
  task_count: number
  skill_count: number
  tool_count: number
}

// ─── Hierarchy ───
export interface HierarchyNode {
  name: string
  level: string
  children?: HierarchyNode[]
  headcount: number
  annual_cost: number
  role_id?: string
  automation_score?: number
  augmentation_score?: number
  avg_automation?: number
  avg_augmentation?: number
  management_level?: string
}

// ─── Gap Analysis ───
export interface FunctionGap {
  function: string
  headcount: number
  annual_cost: number
  avg_automation_score: number
  weighted_l1: number
  weighted_l2: number
  weighted_l3: number
  total_adoption_gap_hours: number
  total_gap_hours: number
  adoption_gap_savings: number
  full_gap_savings: number
  adoption_gap_fte: number
  compliance_tasks: number
  total_tasks: number
  ai_proficiency: number
  change_readiness: number
  trust_level: number
  roles: RoleGap[]
}

export interface RoleGap {
  role_id: string
  role_name: string
  function: string
  headcount: number
  avg_salary: number
  weighted_l1: number
  weighted_l2: number
  weighted_l3: number
  adoption_gap_savings: number
  full_gap_savings: number
  adoption_gap_fte: number
  redesign_candidate: boolean
  total_tasks: number
}

export interface OrgGap {
  org_name: string
  headcount: number
  annual_cost: number
  weighted_l1: number
  weighted_l2: number
  weighted_l3: number
  total_adoption_gap_hours: number
  total_gap_hours: number
  adoption_gap_savings: number
  full_gap_savings: number
  adoption_gap_fte: number
  compliance_tasks: number
  total_tasks: number
  top_roles_by_adoption_gap: Record<string, unknown>[]
  top_roles_by_savings: Record<string, unknown>[]
  functions: FunctionGap[]
}

// ─── Cascade ───
export interface CascadeResult {
  stimulus: Record<string, unknown>
  step1_scope: {
    affected_roles: string[]
    total_tasks_in_scope: number
    addressable_tasks: number
    compliance_protected: number
    total_headcount: number
    total_hours_month: number
    functions_affected: string[]
  }
  step2_reclassification: {
    tasks_to_ai: number
    tasks_to_human_ai: number
    tasks_unchanged: number
    total_freed_hours_per_person: number
    reclassified_tasks: {
      task_id: string
      task_name: string
      role_id: string
      category: string
      new_state: string
      automation_pct: number
      freed_hours: number
      tool_used: string
    }[]
  }
  step3_capacity: {
    total_gross_freed_hours: number
    total_net_freed_hours: number
    absorption_factor: number
    dampening_ratio: number
    role_capacities: {
      role_id: string
      role_name: string
      headcount: number
      freed_pct: number
      total_net_freed: number
    }[]
  }
  step4_skills: {
    sunset_skills: { skill_name: string; direction: string; reason: string }[]
    sunrise_skills: { skill_name: string; direction: string; reason: string }[]
    net_skill_gap: number
  }
  step5_workforce: {
    total_current_hc: number
    total_reducible_ftes: number
    total_projected_hc: number
    total_reduction_pct: number
    policy_applied: string
    role_impacts: {
      role_id: string
      role_name: string
      current_hc: number
      projected_hc: number
      reducible_ftes: number
      reduction_pct: number
    }[]
  }
  step6_financial: {
    license_cost_annual: number
    training_cost: number
    change_management_cost: number
    total_investment: number
    salary_savings_annual: number
    productivity_savings_annual: number
    total_savings_annual: number
    net_annual: number
    payback_months: number
    roi_pct: number
    role_savings: Record<string, unknown>
  }
  step7_structural: {
    redesign_candidates: Record<string, unknown>[]
    elimination_candidates: Record<string, unknown>[]
    total_roles_affected: number
    total_roles_redesign: number
    total_roles_elimination: number
  }
  step8_human_system: {
    proficiency_direction: string
    readiness_direction: string
    trust_direction: string
    political_capital_direction: string
    change_burden_score: number
    narrative: string
  }
  step9_risk: {
    overall_risk_level: string
    risk_count_by_severity: Record<string, number>
    risks: {
      risk_type: string
      severity: string
      description: string
      affected_scope: string
      mitigation: string
    }[]
  }
}

// ─── Simulation ───
export interface TimelinePoint {
  month: number
  adoption_rate: number
  raw_adoption_pct: number
  effective_adoption_pct: number
  adoption_dampening: number
  headcount: number
  hc_reduced_this_month: number
  cumulative_hc_reduced: number
  hc_pct_of_original: number
  cumulative_investment: number
  cumulative_savings: number
  net_position: number
  monthly_savings_rate: number
  hours_freed_this_month: number
  productivity_index: number
  proficiency: number
  readiness: number
  trust: number
  morale: number
  change_burden: number
  political_capital: number
  transformation_fatigue: number
  human_multiplier: number
  trust_multiplier: number
  current_skill_gap: number
  skill_gap_pct: number
}

export interface SimulationSummary {
  total_months: number
  initial_headcount: number
  final_headcount: number
  total_hc_reduced: number
  total_investment: number
  total_savings: number
  net_savings: number
  roi_pct: number
  payback_month: number
  peak_adoption: number
  peak_skill_gap_month: number
  productivity_valley_month: number
  productivity_valley_value: number
  final_proficiency: number
  final_trust: number
  final_readiness: number
  avg_adoption_dampening: number
}

export interface InverseSolveResult {
  solved: boolean
  solved_alpha: number
  target_value: number
  achieved_value: number
  error_pct: number
  iterations: number
  feasibility_range: [number, number]
  message: string
}

export interface SimulationResult {
  summary: SimulationSummary
  timeline: TimelinePoint[]
  cascade: CascadeResult
  trace: Record<string, unknown> | null
  inverse_solve?: InverseSolveResult
}

// ─── Presets ───
export interface PresetScenario {
  id: string
  name: string
  policy: string
  description: string
  params: {
    scenario_name: string
    adoption: { alpha: number; k: number; midpoint: number } | null
    expansion: { alpha: number; k: number; midpoint: number; delay_months: number } | null
    extension: { alpha: number; k: number; midpoint: number; delay_months: number } | null
    time_horizon_months: number
  }
}

// ─── Scenario Catalog ───
export interface ScenarioResult {
  scenario_id: string
  scenario_name: string
  family: string
  status: string
  hc_reduced: number
  final_hc: number
  net_savings: number
  total_investment: number
  total_savings: number
  payback_month: number
  final_proficiency: number
  final_trust: number
}

// ─── Compare ───
export interface ComparisonData {
  scenarios: { name: string; result: SimulationResult }[]
  comparison_matrix: {
    metric_names: string[]
    scenario_names: string[]
    values: Record<string, number[]>
  }
}
