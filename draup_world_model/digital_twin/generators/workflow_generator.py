"""
Enriched workflow generator.

Generates cross-role business workflows with rich task-level detail:
- Tasks with impact scores, automation types, time allocations
- Workflow-level analytics: summary, metrics, opportunities, patterns
- References to existing roles and skills from previous generation steps

Two-phase LLM strategy per function (avoids token limit issues):
  Phase 1 (1 call): Generate workflow skeletons (names + metadata)
  Phase 2 (1 call per workflow): Generate tasks for each workflow individually

Derived analytics fields (summary, metrics, quick_wins, opportunities,
patterns, recommendations) are computed deterministically from task data.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import (
    CompanyProfile,
    GenerationConfig,
    LLMConfig,
    OutputConfig,
)
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

# Score dimension values for impact_score computation
SCORE_VALUES = {"low": 1, "medium": 2, "high": 3}

# Phase 1: Lightweight prompt to get workflow names and metadata
SKELETON_PROMPT = """You are an expert in business process design for the {industry} industry.

For the "{function_name}" function at {company_name}, identify {count} key end-to-end business workflows. These should be the most important cross-role processes in this function.

Available roles in this function:
{roles_list}

For each workflow, provide:
- workflow_name: Clear process name (e.g., "Claims FNOL to Settlement", "Policy Underwriting Pipeline")
- description: 1-2 sentence description of the end-to-end process
- objective: What this workflow achieves for the business
- priority: "high", "medium", or "low"
- frequency: "daily", "weekly", "monthly", "quarterly", or "ad_hoc"

Return a JSON array:
[
  {{
    "workflow_name": "...",
    "description": "...",
    "objective": "...",
    "priority": "...",
    "frequency": "..."
  }}
]

Return ONLY the JSON array, no other text.
"""

# Phase 2: Detailed prompt to get tasks for one specific workflow
TASKS_PROMPT = """You are an expert in business process design for the {industry} industry.

Generate the detailed task breakdown for the following workflow in the "{function_name}" function at {company_name}:

Workflow: "{workflow_name}"
Description: {workflow_description}
Objective: {workflow_objective}

Available roles in this function:
{roles_list}

Available skills in this company:
{skills_list}

Generate 10-15 sequential tasks for this workflow. For each task provide:
- task_name: Specific, actionable task name
- description: 1 sentence description
- expected_output: What this task produces
- automation_type: "AI" (fully automatable), "Human+AI" (augmented), or "Human" (requires human judgment)
- time_hours: Estimated hours for this task (realistic for {industry})
- complexity: "simple", "moderate", or "complex"
- workload: "low", "medium", or "high"
- automation_priority: "high", "medium", or "low"
- sequence_number: Position in workflow (1-based)
- dependencies: Array of sequence_numbers this task depends on (empty if none)
- skills_required: Array of 2-4 skill names (use names from skills list above where possible)
- score_breakdown: Object with time_investment, strategic_value, error_reduction, scalability (each "low", "medium", or "high")
- primary_role: Object with "title" (exact role name from list above) and "seniority" (entry/mid/senior/lead/director)
- supporting_roles: Array of 0-2 objects with "title" and "seniority"

Return a JSON array:
[
  {{
    "task_name": "...",
    "description": "...",
    "expected_output": "...",
    "automation_type": "...",
    "time_hours": 0.0,
    "complexity": "...",
    "workload": "...",
    "automation_priority": "...",
    "sequence_number": 1,
    "dependencies": [],
    "skills_required": ["..."],
    "score_breakdown": {{"time_investment": "...", "strategic_value": "...", "error_reduction": "...", "scalability": "..."}},
    "primary_role": {{"title": "...", "seniority": "..."}},
    "supporting_roles": []
  }}
]

Return ONLY the JSON array, no other text.
"""


class WorkflowGenerator(BaseGenerator):
    """Generates enriched business workflows with task-level analytics.

    Two-phase LLM approach per function:
      Phase 1 (1 call): Generate workflow skeletons (names, descriptions,
        metadata). Lightweight output, no truncation risk.
      Phase 2 (N calls): Generate tasks for each workflow individually.
        One LLM call per workflow keeps output small (~12 task objects).
      Phase 3 (Computed): Derive summary, metrics, quick_wins,
        opportunities, patterns, recommendations from task data.

    For 8 workflows per function, this makes 9 LLM calls per function
    (1 skeleton + 8 task calls) instead of 2 large calls.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        gen_config: Optional[GenerationConfig] = None,
        company: Optional[CompanyProfile] = None,
        output: Optional[OutputConfig] = None,
    ):
        super().__init__(llm_config)
        self.gen_config = gen_config or GenerationConfig()
        self.company = company or CompanyProfile()
        self.output = output or OutputConfig()

    def generate(
        self,
        taxonomy: Dict[str, Any],
        roles: List[Dict[str, Any]],
        tasks: Optional[List[Dict[str, Any]]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        job_titles: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate enriched workflows for all functions.

        Args:
            taxonomy: Full taxonomy with functions, sub_functions, etc.
            roles: All generated roles.
            tasks: All generated tasks (for context).
            skills: Skill catalog (for skills_required references).
            job_titles: Job titles (for role seniority context).

        Returns:
            List of enriched workflow dicts with tasks and analytics.
        """
        self.output.ensure_dirs()
        all_workflows = []

        # Build lookups
        role_name_to_id = {r["name"]: r["id"] for r in roles}
        skill_names = sorted({s["name"] for s in (skills or [])})

        # Group roles by function_id
        roles_by_func: Dict[str, List[Dict]] = {}
        for r in roles:
            roles_by_func.setdefault(r.get("function_id", ""), []).append(r)

        target = self.gen_config.target_workflows_per_function

        for func in taxonomy["functions"]:
            # Per-function resumability: skip if file already exists
            func_file = self.output.function_file("workflows", func["id"])
            if func_file.exists():
                existing = self.load_json(func_file)
                all_workflows.extend(existing)
                logger.info(
                    f"Loaded {len(existing)} existing workflows "
                    f"for {func['name']}"
                )
                continue

            func_roles = roles_by_func.get(func["id"], [])
            if not func_roles:
                logger.warning(
                    f"No roles found for function {func['name']}, skipping"
                )
                continue

            roles_str = "\n".join(
                f"- {r['name']}: {r.get('description', '')}"
                for r in func_roles
            )
            skills_str = ", ".join(skill_names[:80])

            func_workflows = self._generate_for_function(
                func, roles_str, skills_str, role_name_to_id, target,
            )

            if func_workflows:
                self.save_json(func_workflows, func_file)
            all_workflows.extend(func_workflows)

        logger.info(
            f"Generated {len(all_workflows)} workflows across "
            f"{len(taxonomy['functions'])} functions"
        )
        return all_workflows

    def _generate_for_function(
        self,
        func: Dict[str, Any],
        roles_str: str,
        skills_str: str,
        role_name_to_id: Dict[str, str],
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """Generate all workflows for one function using two-phase approach.

        Phase 1: One lightweight call to get workflow names + metadata.
        Phase 2: One call per workflow to get detailed tasks.
        """
        # Phase 1: Generate workflow skeletons
        skeletons = self._generate_workflow_skeletons(
            func, roles_str, target_count,
        )
        if not skeletons:
            logger.error(
                f"Failed to generate workflow skeletons for {func['name']}"
            )
            return []

        logger.info(
            f"Phase 1 complete: {len(skeletons)} workflow skeletons "
            f"for {func['name']}"
        )

        # Phase 2: Generate tasks for each workflow
        func_workflows = []
        for i, skeleton in enumerate(skeletons, 1):
            wf_name = skeleton.get("workflow_name", f"Workflow {i}")
            logger.info(
                f"Phase 2: Generating tasks for workflow {i}/{len(skeletons)}"
                f": {wf_name}"
            )

            raw_tasks = self._generate_workflow_tasks(
                func, skeleton, roles_str, skills_str,
            )

            skeleton["tasks"] = raw_tasks
            workflow = self._build_workflow(skeleton, func, role_name_to_id)
            func_workflows.append(workflow)

        return func_workflows

    def _generate_workflow_skeletons(
        self,
        func: Dict[str, Any],
        roles_str: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Phase 1: Generate lightweight workflow skeletons (names + metadata).

        Single LLM call with small output (~500 chars for 8 workflows).
        """
        prompt = SKELETON_PROMPT.format(
            company_name=self.company.name,
            industry=self.company.industry,
            function_name=func["name"],
            count=count,
            roles_list=roles_str,
        )

        logger.info(
            f"Generating {count} workflow skeletons for: {func['name']}"
        )

        try:
            return self.generate_batch(prompt)
        except Exception as e:
            logger.error(
                f"Failed to generate workflow skeletons "
                f"for {func['name']}: {e}"
            )
            return []

    def _generate_workflow_tasks(
        self,
        func: Dict[str, Any],
        skeleton: Dict[str, Any],
        roles_str: str,
        skills_str: str,
    ) -> List[Dict[str, Any]]:
        """Phase 2: Generate detailed tasks for one workflow.

        Single LLM call with moderate output (~3-4K chars for 12 tasks).
        """
        prompt = TASKS_PROMPT.format(
            company_name=self.company.name,
            industry=self.company.industry,
            function_name=func["name"],
            workflow_name=skeleton.get("workflow_name", ""),
            workflow_description=skeleton.get("description", ""),
            workflow_objective=skeleton.get("objective", ""),
            roles_list=roles_str,
            skills_list=skills_str,
        )

        try:
            return self.generate_batch(prompt)
        except Exception as e:
            logger.error(
                f"Failed to generate tasks for workflow "
                f"'{skeleton.get('workflow_name', '')}': {e}"
            )
            return []

    def _build_workflow(
        self,
        wf_data: Dict[str, Any],
        func: Dict[str, Any],
        role_name_to_id: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build an enriched workflow dict from raw LLM output.

        Processes tasks, maps role names to IDs, computes impact scores,
        and derives workflow-level analytics.
        """
        wf_name = wf_data.get("workflow_name", "Unnamed Workflow")
        wf_id = self.make_id("wf", func["name"], wf_name)

        # Build tasks
        tasks = []
        for task_data in wf_data.get("tasks", []):
            task = self._build_task(task_data, wf_id, role_name_to_id)
            tasks.append(task)

        # Sort tasks by sequence_number
        tasks.sort(key=lambda t: t["sequence_number"])

        # Compute workflow-level analytics
        total_hours = sum(t["time_hours"] for t in tasks)
        ai_count = sum(1 for t in tasks if t["automation_type"] == "AI")
        human_ai_count = sum(
            1 for t in tasks if t["automation_type"] == "Human+AI"
        )
        human_count = sum(
            1 for t in tasks if t["automation_type"] == "Human"
        )
        total_tasks = len(tasks)

        ai_optimization_score = round(
            (ai_count + 0.5 * human_ai_count) / max(total_tasks, 1), 3
        )

        if ai_count > total_tasks * 0.6:
            automation_level = "Automated"
        elif human_count > total_tasks * 0.6:
            automation_level = "Manual"
        else:
            automation_level = "Augmented"

        estimated_time_savings = round(
            sum(
                t["time_hours"] * (
                    0.9 if t["automation_type"] == "AI"
                    else 0.4 if t["automation_type"] == "Human+AI"
                    else 0
                )
                for t in tasks
            ), 1
        )
        estimated_fte_impact = round(estimated_time_savings / 8.0, 2)

        return {
            "id": wf_id,
            "name": wf_name,
            "function_id": func["id"],
            "description": wf_data.get("description", ""),
            "objective": wf_data.get("objective", ""),
            "priority": wf_data.get("priority", "high"),
            "frequency": wf_data.get("frequency", "daily"),
            "avg_cycle_time_hours": round(total_hours, 1),
            "ai_optimization_score": ai_optimization_score,
            "tasks": tasks,
            "summary": {
                "total_tasks": total_tasks,
                "total_hours": round(total_hours, 1),
                "automation_level": automation_level,
                "ai_task_count": ai_count,
                "human_ai_task_count": human_ai_count,
                "human_task_count": human_count,
            },
            "workflow_metrics": {
                "estimated_fte_impact": estimated_fte_impact,
                "estimated_time_savings": estimated_time_savings,
                "implementation_timeline": self._estimate_timeline(
                    ai_optimization_score
                ),
                "roi_potential": (
                    "HIGH" if ai_optimization_score > 0.5
                    else "MEDIUM" if ai_optimization_score > 0.3
                    else "LOW"
                ),
            },
            "quick_wins": self._identify_quick_wins(tasks),
            "opportunities": self._identify_opportunities(tasks),
            "patterns": self._detect_patterns(tasks),
            "recommendations": self._generate_recommendations(tasks),
        }

    def _build_task(
        self,
        task_data: Dict[str, Any],
        wf_id: str,
        role_name_to_id: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build an enriched task dict from raw LLM output."""
        # Map primary role name to ID
        primary_role = task_data.get("primary_role", {})
        role_title = primary_role.get("title", "")
        role_id = self._match_role_id(role_title, role_name_to_id)
        if role_id:
            primary_role["role_id"] = role_id
            for name, rid in role_name_to_id.items():
                if rid == role_id:
                    primary_role["title"] = name
                    break

        # Map supporting roles
        supporting_roles = []
        for sr in task_data.get("supporting_roles", []):
            sr_id = self._match_role_id(
                sr.get("title", ""), role_name_to_id
            )
            if sr_id:
                sr["role_id"] = sr_id
                for name, rid in role_name_to_id.items():
                    if rid == sr_id:
                        sr["title"] = name
                        break
            supporting_roles.append(sr)

        # Validate automation_type
        automation_type = task_data.get("automation_type", "Human+AI")
        if automation_type not in ("AI", "Human+AI", "Human"):
            automation_type = "Human+AI"

        # Compute impact_score from score_breakdown
        breakdown = task_data.get("score_breakdown", {})
        impact_score = self._compute_impact_score(breakdown)

        task_name = task_data.get("task_name", "Unnamed Task")
        return {
            "id": self.make_id("wft", wf_id[:40], task_name),
            "workflow_id": wf_id,
            "sequence_number": task_data.get("sequence_number", 1),
            "name": task_name,
            "description": task_data.get("description", ""),
            "expected_output": task_data.get("expected_output", ""),
            "automation_type": automation_type,
            "time_hours": task_data.get("time_hours", 1.0),
            "complexity": task_data.get("complexity", "moderate"),
            "workload": task_data.get("workload", "medium"),
            "impact_score": impact_score,
            "score_breakdown": {
                "time_investment": breakdown.get(
                    "time_investment", "medium"
                ),
                "strategic_value": breakdown.get(
                    "strategic_value", "medium"
                ),
                "error_reduction": breakdown.get(
                    "error_reduction", "medium"
                ),
                "scalability": breakdown.get("scalability", "medium"),
            },
            "automation_priority": task_data.get(
                "automation_priority", "medium"
            ),
            "dependencies": task_data.get("dependencies", []),
            "skills_required": task_data.get("skills_required", []),
            "primary_role": primary_role,
            "supporting_roles": supporting_roles,
            "role_id": role_id,
        }

    @staticmethod
    def _match_role_id(
        role_title: str, role_name_to_id: Dict[str, str]
    ) -> str:
        """Match a role title to an existing role ID (exact or fuzzy)."""
        if not role_title:
            return ""
        role_id = role_name_to_id.get(role_title, "")
        if role_id:
            return role_id
        title_lower = role_title.lower()
        for name, rid in role_name_to_id.items():
            if name.lower() in title_lower or title_lower in name.lower():
                return rid
        return ""

    @staticmethod
    def _compute_impact_score(breakdown: Dict[str, str]) -> float:
        """Compute impact score from score_breakdown dimensions.

        Formula: (error_reduction + scalability + strategic_value) * cost_efficiency
        Scaled to 0-20 range matching the reference format.
        """
        sv = SCORE_VALUES
        benefit = (
            sv.get(breakdown.get("error_reduction", "medium"), 2)
            + sv.get(breakdown.get("scalability", "medium"), 2)
            + sv.get(breakdown.get("strategic_value", "medium"), 2)
        )
        cost_efficiency = 4 - sv.get(
            breakdown.get("time_investment", "medium"), 2
        )
        return round(benefit * cost_efficiency * 20.0 / 27.0, 1)

    @staticmethod
    def _estimate_timeline(ai_score: float) -> str:
        """Estimate implementation timeline from AI optimization score."""
        if ai_score > 0.7:
            return "3-6 months"
        elif ai_score > 0.4:
            return "6-12 months"
        return "12-18 months"

    @staticmethod
    def _identify_quick_wins(
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify tasks that can be automated quickly."""
        quick_wins = []
        for t in tasks:
            if t["automation_type"] == "AI" and t["complexity"] == "simple":
                quick_wins.append({
                    "task": t["name"],
                    "type": "Full Automation",
                    "hours_saved": round(t["time_hours"] * 0.9, 1),
                    "confidence": 92.0,
                    "complexity": "simple",
                })
            elif (
                t["automation_type"] == "AI"
                and t["complexity"] == "moderate"
            ):
                quick_wins.append({
                    "task": t["name"],
                    "type": "Full Automation",
                    "hours_saved": round(t["time_hours"] * 0.8, 1),
                    "confidence": 82.0,
                    "complexity": "moderate",
                })
        return quick_wins

    @staticmethod
    def _identify_opportunities(
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify automation opportunities grouped by type."""
        ai_tasks = [t for t in tasks if t["automation_type"] == "AI"]
        augmented = [
            t for t in tasks if t["automation_type"] == "Human+AI"
        ]

        opportunities = []
        if ai_tasks:
            hours = round(sum(t["time_hours"] for t in ai_tasks), 1)
            opportunities.append({
                "opportunity_type": "Quick Win",
                "estimated_hours_saved": round(hours * 0.9, 1),
                "implementation_complexity": "LOW",
                "priority": 5,
                "recommendation": (
                    f"Automate {len(ai_tasks)} fully automatable tasks "
                    f"to save ~{hours} hours per cycle"
                ),
                "tasks": [t["name"] for t in ai_tasks],
            })
        if augmented:
            hours = round(sum(t["time_hours"] for t in augmented), 1)
            opportunities.append({
                "opportunity_type": "Augmentation",
                "estimated_hours_saved": round(hours * 0.4, 1),
                "implementation_complexity": "MEDIUM",
                "priority": 3,
                "recommendation": (
                    f"Augment {len(augmented)} human-AI collaborative "
                    f"tasks for partial automation"
                ),
                "tasks": [t["name"] for t in augmented],
            })
        return opportunities

    @staticmethod
    def _detect_patterns(
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect workflow patterns from task sequences."""
        patterns = []
        sorted_tasks = sorted(
            tasks, key=lambda t: t["sequence_number"]
        )

        # AI Task Cluster: 2+ consecutive AI tasks
        consecutive_ai: List[str] = []
        for t in sorted_tasks:
            if t["automation_type"] == "AI":
                consecutive_ai.append(t["name"])
            else:
                if len(consecutive_ai) >= 2:
                    patterns.append({
                        "pattern_name": "AI Task Cluster",
                        "description": (
                            f"Cluster of {len(consecutive_ai)} "
                            f"consecutive AI-automatable tasks"
                        ),
                        "affected_tasks": consecutive_ai[:3],
                        "impact": "POSITIVE",
                        "recommendation": (
                            "Consider end-to-end automation "
                            "of this cluster"
                        ),
                    })
                consecutive_ai = []
        if len(consecutive_ai) >= 2:
            patterns.append({
                "pattern_name": "AI Task Cluster",
                "description": (
                    f"Cluster of {len(consecutive_ai)} "
                    f"consecutive AI-automatable tasks"
                ),
                "affected_tasks": consecutive_ai[:3],
                "impact": "POSITIVE",
                "recommendation": (
                    "Consider end-to-end automation of this cluster"
                ),
            })

        # Augmentation Workflow: majority Human+AI tasks
        human_ai = [
            t for t in tasks if t["automation_type"] == "Human+AI"
        ]
        if len(human_ai) > len(tasks) * 0.5:
            patterns.append({
                "pattern_name": "Augmentation Workflow",
                "description": (
                    f"{len(human_ai)} of {len(tasks)} tasks are "
                    f"human-AI collaborative"
                ),
                "affected_tasks": [t["name"] for t in human_ai[:3]],
                "impact": "POSITIVE",
                "recommendation": (
                    "Invest in AI copilot tools to maximize "
                    "augmentation benefits"
                ),
            })

        # Human Task Bottleneck: human tasks with high time
        bottlenecks = [
            t for t in tasks
            if t["automation_type"] == "Human" and t["time_hours"] >= 2.0
        ]
        if bottlenecks:
            patterns.append({
                "pattern_name": "Human Task Bottleneck",
                "description": (
                    f"{len(bottlenecks)} human-only tasks consuming "
                    f"significant time"
                ),
                "affected_tasks": [
                    t["name"] for t in bottlenecks[:3]
                ],
                "impact": "NEGATIVE",
                "recommendation": (
                    "Investigate augmentation opportunities to "
                    "reduce bottleneck"
                ),
            })

        # High Sequential Dependency
        high_dep = [
            t for t in tasks if len(t.get("dependencies", [])) >= 3
        ]
        if high_dep:
            patterns.append({
                "pattern_name": "High Sequential Dependency",
                "description": (
                    "Tasks with many dependencies may create "
                    "workflow bottlenecks"
                ),
                "affected_tasks": [t["name"] for t in high_dep[:3]],
                "impact": "NEUTRAL",
                "recommendation": (
                    "Review dependency chains for "
                    "parallelization opportunities"
                ),
            })

        return patterns

    @staticmethod
    def _generate_recommendations(
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate strategic recommendations based on task analysis."""
        ai_tasks = [t for t in tasks if t["automation_type"] == "AI"]
        human_tasks = [
            t for t in tasks if t["automation_type"] == "Human"
        ]
        augmented = [
            t for t in tasks if t["automation_type"] == "Human+AI"
        ]

        total = len(tasks)
        ai_pct = len(ai_tasks) / max(total, 1) * 100

        if ai_pct > 50:
            strategy = (
                "Focus on end-to-end automation of highly automatable "
                "tasks while maintaining human oversight for complex "
                "decisions"
            )
        elif ai_pct > 25:
            strategy = (
                "Implement a phased AI augmentation approach, starting "
                "with quick wins and progressively automating more tasks"
            )
        else:
            strategy = (
                "Invest in AI augmentation tools to support human-led "
                "tasks, focusing on efficiency gains and error reduction"
            )

        return {
            "primary_strategy": strategy,
            "key_actions": [
                (
                    f"Prioritize automation of {len(ai_tasks)} fully "
                    f"automatable tasks"
                ),
                (
                    f"Implement AI augmentation for {len(augmented)} "
                    f"human-AI collaborative tasks"
                ),
                (
                    f"Review {len(human_tasks)} human-only tasks for "
                    f"future augmentation potential"
                ),
            ],
            "risks": [
                "Change management resistance from workforce "
                "transitioning to AI-augmented workflows",
                "Data quality issues may impact AI automation "
                "effectiveness",
                "Integration complexity with existing systems "
                "and processes",
            ],
            "success_factors": [
                "Executive sponsorship and clear communication "
                "of AI strategy",
                "Phased implementation with regular feedback loops",
                "Robust training programs for workforce upskilling",
            ],
        }
