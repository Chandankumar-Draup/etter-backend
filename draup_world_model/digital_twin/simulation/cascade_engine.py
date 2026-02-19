"""
8-step cascade propagation engine.

This is the core algorithm of the Digital Twin. It models how an intervention
(task reclassification, technology adoption) propagates through the system:

Step 1: Task reclassification       (first-order)
Step 2: Workload recomposition       (second-order)
Step 3: Role & JobTitle impact       (third-order, level-specific)
Step 4: Skill shifts                 (fourth-order)
Step 5: Workforce recalculation      (fifth-order)
Step 6: Financial projection         (sixth-order)
Step 7: Risk assessment              (cross-cutting)
Step 8: Boundary validation          (sanity checks)

Meadows insight: The cascade IS the system's response to a perturbation.
Each step is a feedback path. The order matters because each step feeds the next.
"""

import logging
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import CascadeConfig, FinancialConfig, SimulationConfig
from draup_world_model.digital_twin.simulation.financial import FinancialProjection

logger = logging.getLogger(__name__)

# Classification automation scores (used for freed capacity calculation)
CLASSIFICATION_AUTOMATION_MAP = {
    "human_only": 0.0,
    "human_led": 0.15,
    "shared": 0.40,
    "ai_led": 0.70,
    "ai_only": 0.95,
}

# Shift: current → new, returns the delta in automation fraction
AUTOMATION_SHIFT = {
    ("human_only", "human_led"): 0.15,
    ("human_only", "shared"): 0.40,
    ("human_only", "ai_led"): 0.70,
    ("human_only", "ai_only"): 0.95,
    ("human_led", "shared"): 0.25,
    ("human_led", "ai_led"): 0.55,
    ("human_led", "ai_only"): 0.80,
    ("shared", "ai_led"): 0.30,
    ("shared", "ai_only"): 0.55,
    ("ai_led", "ai_only"): 0.25,
}


class CascadeEngine:
    """
    Executes the 8-step cascade propagation.

    Input: Scoped data + task reclassifications (from a simulation trigger)
    Output: Full cascade result with per-step metrics
    """

    def __init__(self, timeline_months: int = 36, config: Optional[SimulationConfig] = None):
        self.timeline_months = timeline_months
        self.config = config or SimulationConfig()
        self.cascade_cfg = self.config.cascade
        self.financial = FinancialProjection(
            timeline_months, financial_config=self.config.financial
        )

    def run(
        self,
        scope_data: Dict[str, Any],
        task_reclassifications: List[Dict[str, Any]],
        technology_costs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full 8-step cascade.

        Args:
            scope_data: Output from ScopeSelector.select()
            task_reclassifications: List of {task_id, new_automation_level}
            technology_costs: Optional tech cost data for financial projection
        """
        logger.info(f"Running cascade: {len(task_reclassifications)} task changes")

        # Build lookup tables — use shared dicts so Step 1 mutations are
        # visible to Step 2.  Previously tasks_by_id used dict(t) copies
        # while tasks_by_workload used originals, causing Step 2 to read
        # unmutated automation_level values (delta = 0, freed capacity = 0).
        tasks_by_id = {t["id"]: t for t in scope_data["tasks"]}
        workloads_by_id = {wl["id"]: wl for wl in scope_data["workloads"]}
        roles_by_id = {r["id"]: r for r in scope_data["roles"]}
        titles_by_role = {}
        for jt in scope_data["job_titles"]:
            titles_by_role.setdefault(jt["role_id"], []).append(jt)
        tasks_by_workload = {}
        for t in scope_data["tasks"]:
            tasks_by_workload.setdefault(t.get("workload_id", ""), []).append(t)
        workloads_by_role = {}
        for wl in scope_data["workloads"]:
            workloads_by_role.setdefault(wl.get("role_id", ""), []).append(wl)

        # Step 1: Task reclassification
        step1 = self._step1_task_reclassification(tasks_by_id, task_reclassifications)

        # Step 2: Workload recomposition
        step2 = self._step2_workload_recomposition(workloads_by_id, tasks_by_workload, step1)

        # Step 3: Role & JobTitle impact
        step3 = self._step3_role_impact(roles_by_id, workloads_by_role, titles_by_role, step2)

        # Step 4: Skill shifts (uses task-skill mappings when available)
        step4 = self._step4_skill_shifts(
            scope_data["skills"], step1, scope_data.get("task_skill_mappings")
        )

        # Step 5: Workforce recalculation
        step5 = self._step5_workforce_recalculation(step3)

        # Step 6: Financial projection
        step6 = self._step6_financial(step3, technology_costs, step4)

        # Step 7: Risk assessment
        step7 = self._step7_risk_assessment(step1, step3, step4, step5)

        # Step 8: Boundary validation
        step8 = self._step8_validation(scope_data, step3, step5)

        result = {
            "task_changes": step1,
            "workload_changes": step2,
            "role_impacts": step3,
            "skill_shifts": step4,
            "workforce": step5,
            "financial": step6,
            "risks": step7,
            "validation": step8,
            "summary": self._build_summary(step1, step3, step5, step6),
        }

        logger.info(f"Cascade complete: {result['summary']}")
        return result

    # ──────────────────────────────────────────────────────────
    # Step 1: Task Reclassification
    # ──────────────────────────────────────────────────────────
    def _step1_task_reclassification(
        self,
        tasks_by_id: Dict[str, Dict],
        reclassifications: List[Dict],
    ) -> Dict[str, Any]:
        """Apply task reclassifications and compute deltas."""
        changes = []
        for reclass in reclassifications:
            task_id = reclass["task_id"]
            new_level = reclass["new_automation_level"]
            task = tasks_by_id.get(task_id)
            if not task:
                continue

            old_level = task.get("automation_level", "human_led")
            delta = AUTOMATION_SHIFT.get((old_level, new_level), 0)

            changes.append({
                "task_id": task_id,
                "task_name": task.get("name", ""),
                "workload_id": task.get("workload_id", ""),
                "old_level": old_level,
                "new_level": new_level,
                "automation_delta": delta,
                "time_allocation_pct": task.get("time_allocation_pct", 0),
            })

            # Update the in-memory task
            task["automation_level"] = new_level

        return {
            "tasks_affected": len(changes),
            "changes": changes,
        }

    # ──────────────────────────────────────────────────────────
    # Step 2: Workload Recomposition
    # ──────────────────────────────────────────────────────────
    def _step2_workload_recomposition(
        self,
        workloads_by_id: Dict[str, Dict],
        tasks_by_workload: Dict[str, List],
        step1: Dict,
    ) -> Dict[str, Any]:
        """Recompute workload automation breakdown from changed tasks.

        Stores both old and new continuous automation scores so Step 3
        can compute precise freed capacity without quantization loss.
        """
        affected_wl_ids = set(c["workload_id"] for c in step1["changes"])
        # Build task_id → old_level from Step 1 (tasks already mutated in-place)
        task_old_levels = {c["task_id"]: c["old_level"] for c in step1["changes"]}
        changes = []

        for wl_id in affected_wl_ids:
            wl = workloads_by_id.get(wl_id)
            if not wl:
                continue

            tasks = tasks_by_workload.get(wl_id, [])
            if not tasks:
                continue

            total_time = sum(t.get("time_allocation_pct", 0) for t in tasks)

            # Compute OLD automation score (using pre-change task levels)
            old_automation_weighted = 0.0
            for t in tasks:
                tid = t.get("id", "")
                # Use original level for changed tasks, current for unchanged
                level = task_old_levels.get(tid, t.get("automation_level", "human_led"))
                old_automation_weighted += (
                    CLASSIFICATION_AUTOMATION_MAP.get(level, 0)
                    * t.get("time_allocation_pct", 0)
                )
            old_auto_score = (
                old_automation_weighted / total_time * 100
            ) if total_time > 0 else 0

            # Compute NEW automation score (tasks already updated by Step 1)
            automation_weighted = sum(
                CLASSIFICATION_AUTOMATION_MAP.get(t.get("automation_level", "human_led"), 0)
                * t.get("time_allocation_pct", 0)
                for t in tasks
            )
            new_auto_score = (automation_weighted / total_time * 100) if total_time > 0 else 0
            old_auto_level = wl.get("automation_level", "human_led")

            # Determine new level
            if new_auto_score >= 80:
                new_level = "ai_led"
            elif new_auto_score >= 50:
                new_level = "shared"
            elif new_auto_score >= 20:
                new_level = "human_led"
            else:
                new_level = "human_only"

            changes.append({
                "workload_id": wl_id,
                "workload_name": wl.get("name", ""),
                "role_id": wl.get("role_id", ""),
                "old_level": old_auto_level,
                "new_level": new_level,
                "old_automation_score": round(old_auto_score, 1),
                "automation_score": round(new_auto_score, 1),
            })

            wl["automation_level"] = new_level

        return {
            "workloads_affected": len(changes),
            "changes": changes,
        }

    # ──────────────────────────────────────────────────────────
    # Step 3: Role & JobTitle Impact
    # ──────────────────────────────────────────────────────────
    def _step3_role_impact(
        self,
        roles_by_id: Dict[str, Dict],
        workloads_by_role: Dict[str, List],
        titles_by_role: Dict[str, List],
        step2: Dict,
    ) -> Dict[str, Any]:
        """Compute per-role and per-title freed capacity.

        Uses the DELTA in continuous automation scores (not quantized levels)
        for affected workloads only. Unaffected workloads contribute zero.
        """
        affected_role_ids = set(c["role_id"] for c in step2["changes"])
        # Build lookup: workload_id → change record from step2
        wl_changes = {c["workload_id"]: c for c in step2["changes"]}
        role_impacts = []

        for role_id in affected_role_ids:
            role = roles_by_id.get(role_id)
            if not role:
                continue

            # Compute freed capacity from continuous automation score delta
            workloads = workloads_by_role.get(role_id, [])
            total_freed = 0.0
            for wl in workloads:
                wl_id = wl.get("id", "")
                change = wl_changes.get(wl_id)
                if not change:
                    continue  # unaffected workload — no freed capacity
                wl_effort = wl.get("effort_allocation_pct", 0) / 100.0
                # Use continuous scores (0-100) for precision, not quantized levels
                old_score = change.get("old_automation_score", 0)
                new_score = change.get("automation_score", 0)
                total_freed += wl_effort * max(new_score - old_score, 0) / 100.0

            freed_pct = min(total_freed * 100, 100)

            # Per-title impact (level-specific: entry roles see more impact)
            titles = titles_by_role.get(role_id, [])
            title_impacts = []
            impact_factors = self.cascade_cfg.level_impact_factors
            for jt in titles:
                band = jt.get("career_band", "mid")
                level_factor = impact_factors.get(band, 1.0)
                title_freed = min(freed_pct * level_factor, 100)
                title_impacts.append({
                    "name": jt.get("name", ""),
                    "career_band": band,
                    "headcount": jt.get("headcount", 0),
                    "avg_salary": jt.get("avg_salary", 0),
                    "freed_capacity_pct": round(title_freed, 1),
                })

            ti_mult = self.cascade_cfg.transformation_index_multiplier
            role_impacts.append({
                "role_id": role_id,
                "role_name": role.get("name", ""),
                "freed_capacity_pct": round(freed_pct, 1),
                "title_impacts": title_impacts,
                "transformation_index": min(round(freed_pct * ti_mult, 1), 100),
            })

        return {
            "roles_affected": len(role_impacts),
            "impacts": role_impacts,
        }

    # ──────────────────────────────────────────────────────────
    # Step 4: Skill Shifts
    # ──────────────────────────────────────────────────────────
    def _step4_skill_shifts(
        self,
        skills: List[Dict],
        step1: Dict,
        task_skill_mappings: Optional[Dict[str, List[Dict]]] = None,
    ) -> Dict[str, Any]:
        """Identify skill shifts based on task reclassifications.

        Uses three signal sources:
        1. Lifecycle status (declining → sunset, emerging → sunrise)
        2. Task-skill mappings (PRIMARY skills of automated tasks → sunset candidate)
        3. Universal AI skills (always sunrise when tasks are automated)
        """
        sunset_skills = []
        sunrise_skills = []

        # Source 1: Lifecycle-based shifts
        for skill in skills:
            lifecycle = skill.get("lifecycle_status", "stable")
            if lifecycle == "declining":
                sunset_skills.append({
                    "skill_id": skill.get("id", ""),
                    "name": skill.get("name", ""),
                    "reason": "Declining lifecycle + automation increase",
                    "source": "lifecycle",
                })
            elif lifecycle == "emerging":
                sunrise_skills.append({
                    "skill_id": skill.get("id", ""),
                    "name": skill.get("name", ""),
                    "reason": "Emerging skill needed for AI-augmented work",
                    "source": "lifecycle",
                })

        # Source 2: Task-skill mapping analysis
        # Skills that are PRIMARY for many automated tasks see decreasing demand
        if task_skill_mappings and step1["tasks_affected"] > 0:
            affected_task_ids = {c["task_id"] for c in step1["changes"]}
            # Count how many affected tasks each PRIMARY skill is tied to
            skill_affected_count: Dict[str, int] = {}
            skill_name_lookup: Dict[str, str] = {}
            for task_id in affected_task_ids:
                for mapping in task_skill_mappings.get(task_id, []):
                    if mapping.get("relevance") == "PRIMARY":
                        sid = mapping["skill_id"]
                        skill_affected_count[sid] = skill_affected_count.get(sid, 0) + 1
                        skill_name_lookup[sid] = mapping["skill_name"]

            # Skills PRIMARY for >N% of affected tasks → sunset candidate
            threshold = max(1, int(
                len(affected_task_ids) * self.cascade_cfg.sunset_skill_task_fraction
            ))
            sunset_ids = {s["skill_id"] for s in sunset_skills}
            for sid, count in skill_affected_count.items():
                if count >= threshold and sid not in sunset_ids:
                    sunset_skills.append({
                        "skill_id": sid,
                        "name": skill_name_lookup.get(sid, sid),
                        "reason": f"PRIMARY skill for {count} automated tasks",
                        "source": "task_mapping",
                    })
                    sunset_ids.add(sid)

        # Source 3: Universal AI skills when tasks are automated
        if step1["tasks_affected"] > 0:
            sunrise_skills.append({
                "skill_id": "skill_ai_literacy",
                "name": "AI Literacy & Prompt Engineering",
                "reason": "Required for effective human-AI collaboration",
                "source": "universal",
            })
            sunrise_skills.append({
                "skill_id": "skill_ai_oversight",
                "name": "AI Output Validation",
                "reason": "Quality assurance for AI-generated outputs",
                "source": "universal",
            })

        return {
            "sunset_skills": sunset_skills,
            "sunrise_skills": sunrise_skills,
            "net_skill_shift": len(sunrise_skills) - len(sunset_skills),
        }

    # ──────────────────────────────────────────────────────────
    # Step 5: Workforce Recalculation
    # ──────────────────────────────────────────────────────────
    def _step5_workforce_recalculation(self, step3: Dict) -> Dict[str, Any]:
        """Aggregate workforce impact from role-level changes."""
        total_current_hc = 0
        total_freed_hc = 0
        total_redeployable = 0
        redeploy_rate = self.cascade_cfg.redeployability_pct / 100.0

        for impact in step3["impacts"]:
            for ti in impact["title_impacts"]:
                hc = ti["headcount"]
                freed_pct = ti["freed_capacity_pct"] / 100.0
                freed_hc = hc * freed_pct
                total_current_hc += hc
                total_freed_hc += freed_hc
                total_redeployable += freed_hc * redeploy_rate

        return {
            "current_headcount": total_current_hc,
            "freed_headcount": round(total_freed_hc, 1),
            "reduction_pct": round(total_freed_hc / total_current_hc * 100, 1) if total_current_hc > 0 else 0,
            "redeployable": round(total_redeployable, 1),
            "redeployable_pct": round(total_redeployable / total_freed_hc * 100, 1) if total_freed_hc > 0 else 0,
        }

    # ──────────────────────────────────────────────────────────
    # Step 6: Financial Projection
    # ──────────────────────────────────────────────────────────
    def _step6_financial(
        self,
        step3: Dict,
        technology_costs: Optional[Dict],
        step4: Dict,
    ) -> Dict[str, Any]:
        """Compute financial projection from cascade results."""
        # Flatten all title impacts
        all_title_impacts = []
        for impact in step3["impacts"]:
            all_title_impacts.extend(impact["title_impacts"])

        # Compute reskilling costs
        reskilling = None
        if step4["sunrise_skills"]:
            total_hc = sum(ti["headcount"] for ti in all_title_impacts)
            reskilling_hc = int(total_hc * self.cascade_cfg.reskilling_fraction)
            reskilling = self.financial.compute_reskilling_costs(
                step4["sunrise_skills"], reskilling_hc
            )

        return self.financial.compute(
            all_title_impacts,
            technology_costs,
            reskilling,
            redeployability_pct=self.cascade_cfg.redeployability_pct,
        )

    # ──────────────────────────────────────────────────────────
    # Step 7: Risk Assessment
    # ──────────────────────────────────────────────────────────
    def _step7_risk_assessment(
        self,
        step1: Dict,
        step3: Dict,
        step4: Dict,
        step5: Dict,
    ) -> Dict[str, Any]:
        """Identify risks from cascade results."""
        risk_flags = []
        cfg = self.cascade_cfg

        # High automation roles
        for impact in step3["impacts"]:
            if impact["freed_capacity_pct"] > cfg.risk_high_automation_pct:
                risk_flags.append({
                    "type": "high_automation",
                    "severity": "high",
                    "entity": impact["role_name"],
                    "detail": f"Role has {impact['freed_capacity_pct']}% freed capacity - needs complete redesign",
                })

        # Large workforce reduction
        if step5["reduction_pct"] > cfg.risk_workforce_reduction_pct:
            risk_flags.append({
                "type": "workforce_reduction",
                "severity": "high",
                "entity": "workforce",
                "detail": f"Projected {step5['reduction_pct']}% headcount reduction - change management critical",
            })

        # Skill gap
        if step4["net_skill_shift"] > cfg.risk_skill_gap_count:
            risk_flags.append({
                "type": "skill_gap",
                "severity": "medium",
                "entity": "skills",
                "detail": f"Net {step4['net_skill_shift']} new skills needed - significant reskilling required",
            })

        # Many tasks affected
        if step1["tasks_affected"] > cfg.risk_broad_change_tasks:
            risk_flags.append({
                "type": "broad_change",
                "severity": "medium",
                "entity": "tasks",
                "detail": f"{step1['tasks_affected']} tasks affected - phased rollout recommended",
            })

        return {
            "risk_count": len(risk_flags),
            "high_risks": sum(1 for r in risk_flags if r["severity"] == "high"),
            "flags": risk_flags,
        }

    # ──────────────────────────────────────────────────────────
    # Step 8: Boundary Validation
    # ──────────────────────────────────────────────────────────
    def _step8_validation(
        self,
        scope_data: Dict,
        step3: Dict,
        step5: Dict,
    ) -> Dict[str, Any]:
        """Sanity checks on cascade results."""
        checks = []

        # Headcount can't increase
        original_hc = scope_data["summary"]["total_headcount"]
        if step5["freed_headcount"] < 0:
            checks.append({"check": "headcount_non_negative", "passed": False, "detail": "Freed headcount is negative"})
        else:
            checks.append({"check": "headcount_non_negative", "passed": True})

        # Freed capacity bounded 0-100%
        all_valid = True
        for impact in step3["impacts"]:
            if impact["freed_capacity_pct"] > 100 or impact["freed_capacity_pct"] < 0:
                all_valid = False
                break
        checks.append({"check": "freed_capacity_bounded", "passed": all_valid})

        # At least one impact produced
        has_impact = step3["roles_affected"] > 0
        checks.append({"check": "has_impact", "passed": has_impact})

        all_passed = all(c["passed"] for c in checks)
        return {"valid": all_passed, "checks": checks}

    # ──────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────
    def _build_summary(self, step1, step3, step5, step6) -> Dict[str, Any]:
        return {
            "tasks_affected": step1["tasks_affected"],
            "roles_affected": step3["roles_affected"],
            "freed_headcount": step5["freed_headcount"],
            "reduction_pct": step5["reduction_pct"],
            "gross_savings": step6["gross_savings"],
            "net_impact": step6["net_impact"],
            "roi_pct": step6["roi_pct"],
        }
