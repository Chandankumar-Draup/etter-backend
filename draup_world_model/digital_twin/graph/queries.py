"""
Reusable Cypher query library for the Digital Twin graph.

All queries use parameterized inputs to prevent injection.
Queries are organized by domain: taxonomy, work content, capabilities, simulation.
"""

# ──────────────────────────────────────────────────────────────
# Node creation (MERGE = idempotent)
# ──────────────────────────────────────────────────────────────

MERGE_ORGANIZATION = """
UNWIND $items AS item
MERGE (n:DTOrganization {id: item.id})
SET n.name = item.name,
    n.industry = item.industry,
    n.sub_industry = item.sub_industry,
    n.size = item.size,
    n.revenue_millions = item.revenue_millions,
    n.hq_location = item.hq_location,
    n.description = item.description
"""

MERGE_FUNCTIONS = """
UNWIND $items AS item
MERGE (n:DTFunction {id: item.id})
SET n.name = item.name,
    n.org_id = item.org_id,
    n.headcount = item.headcount,
    n.description = item.description
"""

MERGE_SUB_FUNCTIONS = """
UNWIND $items AS item
MERGE (n:DTSubFunction {id: item.id})
SET n.name = item.name,
    n.function_id = item.function_id,
    n.headcount = item.headcount,
    n.description = item.description
"""

MERGE_JOB_FAMILY_GROUPS = """
UNWIND $items AS item
MERGE (n:DTJobFamilyGroup {id: item.id})
SET n.name = item.name,
    n.sub_function_id = item.sub_function_id,
    n.description = item.description
"""

MERGE_JOB_FAMILIES = """
UNWIND $items AS item
MERGE (n:DTJobFamily {id: item.id})
SET n.name = item.name,
    n.job_family_group_id = item.job_family_group_id,
    n.description = item.description
"""

MERGE_ROLES = """
UNWIND $items AS item
MERGE (n:DTRole {id: item.id})
SET n.name = item.name,
    n.function_id = item.function_id,
    n.job_family_id = item.job_family_id,
    n.description = item.description,
    n.total_headcount = item.total_headcount,
    n.avg_salary = item.avg_salary,
    n.automation_score = item.automation_score
"""

MERGE_JOB_TITLES = """
UNWIND $items AS item
MERGE (n:DTJobTitle {id: item.id})
SET n.name = item.name,
    n.role_id = item.role_id,
    n.function_id = item.function_id,
    n.career_band = item.career_band,
    n.level = item.level,
    n.typical_experience_years = item.typical_experience_years,
    n.headcount = item.headcount,
    n.avg_salary = item.avg_salary
"""

MERGE_WORKLOADS = """
UNWIND $items AS item
MERGE (n:DTWorkload {id: item.id})
SET n.name = item.name,
    n.role_id = item.role_id,
    n.function_id = item.function_id,
    n.description = item.description,
    n.effort_allocation_pct = item.effort_allocation_pct,
    n.automation_level = item.automation_level
"""

MERGE_TASKS = """
UNWIND $items AS item
MERGE (n:DTTask {id: item.id})
SET n.name = item.name,
    n.workload_id = item.workload_id,
    n.function_id = item.function_id,
    n.description = item.description,
    n.classification = item.classification,
    n.time_allocation_pct = item.time_allocation_pct,
    n.automation_potential = item.automation_potential,
    n.automation_level = item.automation_level
"""

MERGE_SKILLS = """
UNWIND $items AS item
MERGE (n:DTSkill {id: item.id})
SET n.name = item.name,
    n.category = item.category,
    n.skill_type = item.skill_type,
    n.lifecycle_status = item.lifecycle_status,
    n.description = item.description,
    n.market_demand_trend = item.market_demand_trend
"""

MERGE_TECHNOLOGIES = """
UNWIND $items AS item
MERGE (n:DTTechnology {id: item.id})
SET n.name = item.name,
    n.category = item.category,
    n.vendor = item.vendor,
    n.description = item.description,
    n.capabilities = item.capabilities,
    n.license_cost_tier = item.license_cost_tier,
    n.adoption_stage = item.adoption_stage
"""

MERGE_WORKFLOWS = """
UNWIND $items AS item
MERGE (n:DTWorkflow {id: item.id})
SET n.name = item.name,
    n.function_id = item.function_id,
    n.description = item.description,
    n.objective = item.objective,
    n.priority = item.priority,
    n.avg_cycle_time_hours = item.avg_cycle_time_hours,
    n.frequency = item.frequency,
    n.ai_optimization_score = item.ai_optimization_score
"""

MERGE_WORKFLOW_TASKS = """
UNWIND $items AS item
MERGE (n:DTWorkflowTask {id: item.id})
SET n.name = item.name,
    n.workflow_id = item.workflow_id,
    n.sequence_number = item.sequence_number,
    n.role_id = item.role_id,
    n.description = item.description,
    n.automation_type = item.automation_type,
    n.time_hours = item.time_hours,
    n.complexity = item.complexity,
    n.workload = item.workload,
    n.impact_score = item.impact_score,
    n.automation_priority = item.automation_priority
"""

# ──────────────────────────────────────────────────────────────
# Relationship creation
# ──────────────────────────────────────────────────────────────

LINK_ORG_TO_FUNCTIONS = """
MATCH (org:DTOrganization), (f:DTFunction)
WHERE f.org_id = org.id
MERGE (org)-[:DT_CONTAINS]->(f)
"""

LINK_FUNCTION_TO_SUBFUNCTIONS = """
MATCH (f:DTFunction), (sf:DTSubFunction)
WHERE sf.function_id = f.id
MERGE (f)-[:DT_CONTAINS]->(sf)
"""

LINK_SUBFUNCTION_TO_JFG = """
MATCH (sf:DTSubFunction), (jfg:DTJobFamilyGroup)
WHERE jfg.sub_function_id = sf.id
MERGE (sf)-[:DT_CONTAINS]->(jfg)
"""

LINK_JFG_TO_JF = """
MATCH (jfg:DTJobFamilyGroup), (jf:DTJobFamily)
WHERE jf.job_family_group_id = jfg.id
MERGE (jfg)-[:DT_CONTAINS]->(jf)
"""

LINK_JF_TO_ROLES = """
MATCH (jf:DTJobFamily), (r:DTRole)
WHERE r.job_family_id = jf.id
MERGE (jf)-[:DT_HAS_ROLE]->(r)
"""

LINK_ROLE_TO_TITLES = """
MATCH (r:DTRole), (jt:DTJobTitle)
WHERE jt.role_id = r.id
MERGE (r)-[:DT_HAS_TITLE]->(jt)
"""

LINK_ROLE_TO_WORKLOADS = """
MATCH (r:DTRole), (wl:DTWorkload)
WHERE wl.role_id = r.id
MERGE (r)-[:DT_HAS_WORKLOAD]->(wl)
"""

LINK_WORKLOAD_TO_TASKS = """
MATCH (wl:DTWorkload), (t:DTTask)
WHERE t.workload_id = wl.id
MERGE (wl)-[:DT_CONTAINS_TASK]->(t)
"""

LINK_ROLE_TO_SKILLS = """
UNWIND $mappings AS mapping
MATCH (r:DTRole {id: mapping.role_id})
MATCH (s:DTSkill {id: mapping.skill_id})
MERGE (r)-[:DT_REQUIRES_SKILL]->(s)
"""

LINK_TASK_TO_SKILLS = """
UNWIND $mappings AS mapping
MATCH (t:DTTask {id: mapping.task_id})
MATCH (s:DTSkill {id: mapping.skill_id})
MERGE (t)-[rel:DT_REQUIRES_SKILL]->(s)
SET rel.relevance = mapping.relevance
"""

LINK_ROLE_TO_TECHNOLOGIES = """
UNWIND $mappings AS mapping
MATCH (r:DTRole {id: mapping.role_id})
MATCH (t:DTTechnology {id: mapping.tech_id})
MERGE (r)-[:DT_USES_TECHNOLOGY]->(t)
"""

LINK_ADJACENT_ROLES = """
UNWIND $mappings AS mapping
MATCH (r1:DTRole {id: mapping.role_id})
MATCH (r2:DTRole {id: mapping.adjacent_role_id})
MERGE (r1)-[:DT_ADJACENT_TO]->(r2)
"""

LINK_WORKFLOW_TASKS = """
MATCH (wf:DTWorkflow), (wt:DTWorkflowTask)
WHERE wt.workflow_id = wf.id
MERGE (wt)-[:DT_PART_OF_WORKFLOW]->(wf)
"""

LINK_WORKFLOW_TASK_ROLES = """
MATCH (wt:DTWorkflowTask), (r:DTRole)
WHERE wt.role_id = r.id
MERGE (wt)-[:DT_TASK_USES_ROLE]->(r)
"""

# ──────────────────────────────────────────────────────────────
# Read queries (for simulation engine)
# ──────────────────────────────────────────────────────────────

GET_SCOPE_BY_FUNCTION = """
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
"""

GET_SCOPE_BY_ROLE = """
MATCH (role:DTRole {name: $role_name})
OPTIONAL MATCH (role)-[:DT_HAS_TITLE]->(jt:DTJobTitle)
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
RETURN role, jt, wl, task, skill, tech
"""

GET_ALL_ROLES_IN_FUNCTION = """
MATCH (f:DTFunction {name: $function_name})
      -[:DT_CONTAINS]->(:DTSubFunction)
      -[:DT_CONTAINS]->(:DTJobFamilyGroup)
      -[:DT_CONTAINS]->(:DTJobFamily)
      -[:DT_HAS_ROLE]->(role:DTRole)
RETURN role
"""

GET_ROLE_WITH_FULL_DECOMPOSITION = """
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
"""

GET_TASKS_BY_CLASSIFICATION = """
MATCH (task:DTTask)
WHERE task.classification = $classification
RETURN task
"""

GET_ROLE_WORKLOAD_TASK_SKILLS = """
MATCH (role:DTRole {id: $role_id})
OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
OPTIONAL MATCH (task)-[rs:DT_REQUIRES_SKILL]->(skill:DTSkill)
RETURN role, wl, task, skill, rs.relevance AS relevance
ORDER BY wl.name, task.name
"""

COUNT_NODES = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label STARTS WITH 'DT')
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY label
"""

COUNT_RELATIONSHIPS = """
MATCH ()-[r]->()
WHERE type(r) STARTS WITH 'DT_'
RETURN type(r) AS rel_type, count(r) AS count
ORDER BY rel_type
"""
