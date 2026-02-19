"""
S6: Technology Adoption Impact Simulation (P1 - Killer Feature).

Answers: "What happens when we deploy [Copilot/UiPath/etc.]?"

Flow:
  1. Load pre-built technology profile
  2. Match tech capabilities to tasks (keyword matching)
  3. Determine classification shifts per matched task
  4. Run full cascade: tech → task → workload → role → financial
  5. Model adoption curve over months
  6. Compute net ROI = savings - licensing - implementation - reskilling

This is the highest-value simulation because it answers the CxO question:
"Should we invest in [technology X]? What's the real impact?"
"""

import logging
import re
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import AUTOMATION_LEVELS
from draup_world_model.digital_twin.simulation.cascade_engine import CascadeEngine

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Pre-built technology profiles
# ──────────────────────────────────────────────────────────────
TECHNOLOGY_PROFILES = {
    "Microsoft Copilot": {
        "name": "Microsoft Copilot",
        "vendor": "Microsoft",
        "license_tier": "medium",
        "capabilities": [
            "document creation", "email drafting", "meeting summarization",
            "data analysis", "report generation", "presentation creation",
            "spreadsheet analysis", "content editing",
        ],
        "classification_shift": "shared",  # Human → Human+AI
        "task_keywords": [
            "document", "report", "email", "draft", "write", "create",
            "summarize", "analyze", "spreadsheet", "presentation",
            "review", "compile", "format", "edit", "memo", "correspondence",
        ],
        "adoption_speed": "moderate",
    },
    "UiPath": {
        "name": "UiPath",
        "vendor": "UiPath",
        "license_tier": "high",
        "capabilities": [
            "data entry automation", "form processing", "report generation",
            "system migration", "invoice processing", "data extraction",
        ],
        "classification_shift": "ai_led",  # Human → AI (structured)
        "task_keywords": [
            "data entry", "form", "process", "extract", "invoice",
            "input", "copy", "transfer", "migrate", "reconcile",
            "validate", "check", "verify", "match", "filing",
        ],
        "adoption_speed": "slow",
    },
    "ServiceNow AI": {
        "name": "ServiceNow AI",
        "vendor": "ServiceNow",
        "license_tier": "high",
        "capabilities": [
            "ticket routing", "incident categorization", "knowledge base",
            "service request automation", "change management",
        ],
        "classification_shift": "ai_led",
        "task_keywords": [
            "ticket", "incident", "request", "route", "categorize",
            "service", "support", "help desk", "issue", "escalat",
        ],
        "adoption_speed": "moderate",
    },
    "Salesforce Einstein": {
        "name": "Salesforce Einstein",
        "vendor": "Salesforce",
        "license_tier": "high",
        "capabilities": [
            "lead scoring", "forecast updating", "opportunity analysis",
            "customer segmentation", "next best action",
        ],
        "classification_shift": "shared",
        "task_keywords": [
            "lead", "forecast", "opportunity", "customer", "sales",
            "pipeline", "account", "prospect", "crm", "segment",
        ],
        "adoption_speed": "moderate",
    },
    "Claims AI": {
        "name": "Claims AI (Custom)",
        "vendor": "Custom/Internal",
        "license_tier": "enterprise",
        "capabilities": [
            "document extraction", "fraud detection", "coverage verification",
            "damage assessment", "claims triage", "settlement recommendation",
        ],
        "classification_shift": "shared",
        "task_keywords": [
            "claim", "fraud", "coverage", "damage", "assessment",
            "settlement", "triage", "extract", "document", "verify",
            "adjudicate", "investigate", "subrogation", "loss",
        ],
        "adoption_speed": "slow",
    },
    "GitHub Copilot": {
        "name": "GitHub Copilot",
        "vendor": "GitHub/Microsoft",
        "license_tier": "low",
        "capabilities": [
            "code generation", "code review", "documentation generation",
            "test generation", "bug detection",
        ],
        "classification_shift": "shared",
        "task_keywords": [
            "code", "develop", "program", "test", "debug",
            "deploy", "review", "documentation", "api", "software",
        ],
        "adoption_speed": "fast",
    },
}

# Adoption curves (monthly adoption factor: 0.0 to 1.0)
ADOPTION_CURVES = {
    "fast": {1: 0.10, 3: 0.35, 6: 0.60, 9: 0.80, 12: 0.90, 18: 0.95, 24: 0.98},
    "moderate": {1: 0.05, 3: 0.15, 6: 0.35, 9: 0.55, 12: 0.70, 18: 0.85, 24: 0.92},
    "slow": {1: 0.02, 3: 0.08, 6: 0.20, 9: 0.35, 12: 0.50, 18: 0.70, 24: 0.85},
}


class TechAdoptionSimulation:
    """
    Simulates the impact of adopting a specific technology.

    Usage:
        sim = TechAdoptionSimulation(cascade_engine)
        result = sim.run(scope_data, technology_name="Microsoft Copilot")
    """

    def __init__(self, cascade_engine: CascadeEngine):
        self.cascade = cascade_engine

    def run(
        self,
        scope_data: Dict[str, Any],
        technology_name: str,
        adoption_months: int = 12,
        custom_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run technology adoption impact simulation.

        Args:
            scope_data: Output from ScopeSelector.select()
            technology_name: Name of the technology (must be in TECHNOLOGY_PROFILES
                or provided via custom_profile)
            adoption_months: Timeline for adoption measurement (default: 12)
            custom_profile: Optional user-defined technology profile dict with:
                name, vendor, license_tier, capabilities, classification_shift,
                task_keywords, adoption_speed, monthly_per_user_override (optional)
        """
        profile = custom_profile or TECHNOLOGY_PROFILES.get(technology_name)
        if not profile:
            available = list(TECHNOLOGY_PROFILES.keys())
            raise ValueError(f"Unknown technology: {technology_name}. Available: {available}")

        logger.info(f"Running tech adoption simulation: {technology_name}")

        # Step 1: Match technology capabilities to tasks
        matched_tasks = self._match_tasks(scope_data["tasks"], profile)

        if not matched_tasks:
            logger.info(f"No tasks matched for {technology_name}")
            return {
                "simulation_type": "tech_adoption",
                "technology": technology_name,
                "tasks_matched": 0,
                "cascade": None,
            }

        # Step 2: Generate task reclassifications
        reclassifications = []
        for task_id, match_info in matched_tasks.items():
            reclassifications.append({
                "task_id": task_id,
                "new_automation_level": profile["classification_shift"],
            })

        # Step 3: Compute technology costs
        total_hc = scope_data["summary"]["total_headcount"]
        tech_costs = self.cascade.financial.compute_tech_costs(
            technology_name,
            profile["license_tier"],
            total_hc,
            self.cascade.timeline_months,
            monthly_per_user_override=profile.get("monthly_per_user_override"),
        )

        # Step 4: Run cascade
        cascade_result = self.cascade.run(scope_data, reclassifications, tech_costs)

        # Step 5: Build adoption curve (uses unadjusted savings for month-by-month view)
        adoption_curve = self._build_adoption_curve(
            profile["adoption_speed"],
            cascade_result["financial"]["gross_savings"],
            adoption_months,
        )

        # Step 6: Apply adoption-curve discount to financial summary.
        # The cascade assumes 100% adoption from day 1. Adjust savings to
        # reflect the gradual adoption curve (weighted average over timeline).
        adoption_discount = self._compute_adoption_discount(
            profile["adoption_speed"],
            self.cascade.timeline_months,
        )
        unadjusted_savings = cascade_result["financial"]["gross_savings"]
        adjusted_savings = round(unadjusted_savings * adoption_discount, 2)
        cascade_result["financial"]["unadjusted_gross_savings"] = unadjusted_savings
        cascade_result["financial"]["gross_savings"] = adjusted_savings
        cascade_result["financial"]["adoption_discount_factor"] = round(
            adoption_discount, 3
        )
        # Recalculate derived financial metrics
        total_cost = cascade_result["financial"]["total_cost"]
        net_impact = adjusted_savings - total_cost
        cascade_result["financial"]["net_impact"] = round(net_impact, 2)
        roi_pct = (net_impact / total_cost * 100) if total_cost > 0 else (
            9999.0 if adjusted_savings > 0 else 0)
        cascade_result["financial"]["roi_pct"] = round(roi_pct, 1)
        monthly_savings = (
            adjusted_savings / self.cascade.timeline_months
            if self.cascade.timeline_months > 0 else 0
        )
        cascade_result["financial"]["payback_months"] = (
            int(total_cost / monthly_savings) if monthly_savings > 0 else 0
        )
        # Update cascade summary to match adjusted financials
        if "summary" in cascade_result:
            cascade_result["summary"]["gross_savings"] = adjusted_savings
            cascade_result["summary"]["net_impact"] = round(net_impact, 2)
            cascade_result["summary"]["roi_pct"] = round(roi_pct, 1)

        return {
            "simulation_type": "tech_adoption",
            "technology": {
                "name": technology_name,
                "vendor": profile["vendor"],
                "capabilities": profile["capabilities"],
                "license_tier": profile["license_tier"],
                "adoption_speed": profile["adoption_speed"],
            },
            "task_matching": {
                "tasks_matched": len(matched_tasks),
                "total_tasks": len(scope_data["tasks"]),
                "match_rate_pct": round(
                    len(matched_tasks) / len(scope_data["tasks"]) * 100, 1
                ) if scope_data["tasks"] else 0,
                "matched_task_names": [m["task_name"] for m in matched_tasks.values()],
            },
            "cascade": cascade_result,
            "adoption_curve": adoption_curve,
            "adoption_discount_factor": round(adoption_discount, 3),
            "technology_costs": tech_costs,
            "recommendation": self._generate_recommendation(cascade_result, tech_costs),
        }

    def _match_tasks(
        self,
        tasks: List[Dict],
        profile: Dict,
    ) -> Dict[str, Dict]:
        """Match technology capabilities to tasks using word-boundary keyword matching.

        Uses regex word boundaries instead of substring matching to avoid
        false positives (e.g. 'data' matching inside 'validate').
        Matches against both task name and description.
        """
        keywords = profile["task_keywords"]
        matched = {}

        # Pre-compile word-boundary patterns for each keyword
        patterns = []
        for kw in keywords:
            pat = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            patterns.append((kw, pat))

        for task in tasks:
            task_name = task.get("name", "").lower()
            task_desc = task.get("description", "").lower()
            task_text = f"{task_name} {task_desc}"

            # Word-boundary matching
            matching_keywords = [kw for kw, pat in patterns if pat.search(task_text)]
            if matching_keywords:
                # Don't match tasks already at or above the target level
                current_level = task.get("automation_level", "human_led")
                target_level = profile["classification_shift"]
                if AUTOMATION_LEVELS.index(current_level) < AUTOMATION_LEVELS.index(target_level):
                    confidence = min(
                        len(matching_keywords) / max(len(keywords) * 0.3, 1), 1.0
                    )
                    matched[task["id"]] = {
                        "task_name": task.get("name", ""),
                        "keywords_matched": matching_keywords,
                        "match_confidence": round(confidence, 2),
                        "current_level": current_level,
                        "new_level": target_level,
                    }

        logger.info(f"Matched {len(matched)}/{len(tasks)} tasks for {profile['name']}")
        return matched

    def _build_adoption_curve(
        self,
        speed: str,
        total_savings: float,
        months: int,
    ) -> List[Dict[str, Any]]:
        """Build month-by-month adoption curve with projected savings."""
        curve_data = ADOPTION_CURVES.get(speed, ADOPTION_CURVES["moderate"])
        result = []
        sorted_months = sorted(curve_data.keys())

        for month in sorted_months:
            if month > months:
                break
            adoption_pct = curve_data[month]
            realized_savings = total_savings * adoption_pct * (month / self.cascade.timeline_months)
            result.append({
                "month": month,
                "adoption_pct": round(adoption_pct * 100, 1),
                "realized_savings": round(realized_savings, 2),
            })

        return result

    def _compute_adoption_discount(self, speed: str, timeline_months: int) -> float:
        """Compute weighted-average adoption factor over the timeline.

        The cascade assumes 100% adoption from day 1. This discount factor
        adjusts gross savings to reflect the gradual adoption curve.
        Uses trapezoidal integration over the adoption curve data points.
        """
        curve_data = ADOPTION_CURVES.get(speed, ADOPTION_CURVES["moderate"])
        sorted_months = sorted(curve_data.keys())

        # Build points starting from (month 0, adoption 0%)
        points = [(0, 0.0)]
        for m in sorted_months:
            if m <= timeline_months:
                points.append((m, curve_data[m]))
        # Extend to timeline end at last known adoption level
        if points[-1][0] < timeline_months:
            points.append((timeline_months, points[-1][1]))

        # Trapezoidal integration for average adoption
        total_area = 0.0
        for i in range(1, len(points)):
            dt = points[i][0] - points[i - 1][0]
            avg_adoption = (points[i][1] + points[i - 1][1]) / 2.0
            total_area += dt * avg_adoption

        return total_area / timeline_months if timeline_months > 0 else 1.0

    @staticmethod
    def _generate_recommendation(cascade: Dict, tech_costs: Dict) -> Dict[str, Any]:
        """Generate go/no-go recommendation based on results."""
        roi = cascade["financial"]["roi_pct"]
        risk_count = cascade["risks"]["high_risks"]
        payback = cascade["financial"]["payback_months"]

        if roi > 200 and risk_count == 0:
            verdict = "STRONG_RECOMMEND"
            reasoning = "High ROI with no high risks. Proceed with standard implementation plan."
        elif roi > 100 and risk_count <= 1:
            verdict = "RECOMMEND"
            reasoning = "Good ROI with manageable risks. Address identified risks before full rollout."
        elif roi > 50:
            verdict = "CONDITIONAL"
            reasoning = "Moderate ROI. Recommend pilot program before full deployment."
        elif roi > 0:
            verdict = "CAUTIOUS"
            reasoning = "Low ROI. Consider if strategic value justifies investment."
        else:
            verdict = "NOT_RECOMMENDED"
            reasoning = "Negative ROI. Technology cost exceeds projected savings."

        return {
            "verdict": verdict,
            "reasoning": reasoning,
            "roi_pct": roi,
            "payback_months": payback,
            "high_risk_count": risk_count,
        }

    def run_multi(
        self,
        scope_data: Dict[str, Any],
        technology_names: List[str],
        adoption_months: int = 12,
        custom_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run multi-technology adoption simulation.

        Deploys multiple technologies simultaneously. When two technologies
        affect the same task, the higher automation level wins.

        Args:
            scope_data: Output from ScopeSelector.select()
            technology_names: List of technology names to deploy together
            adoption_months: Timeline for adoption measurement
            custom_profiles: Optional dict mapping tech name → custom profile

        Returns:
            Combined result with per-technology breakdown and merged cascade.
        """
        custom_profiles = custom_profiles or {}
        logger.info(f"Running multi-tech simulation: {technology_names}")

        # Step 1: Load and validate all profiles
        profiles = []
        for tech_name in technology_names:
            profile = custom_profiles.get(tech_name) or TECHNOLOGY_PROFILES.get(tech_name)
            if not profile:
                available = list(TECHNOLOGY_PROFILES.keys())
                raise ValueError(
                    f"Unknown technology: {tech_name}. Available: {available}"
                )
            profiles.append((tech_name, profile))

        # Step 2: Match tasks for each technology independently
        per_tech_matches = {}
        all_matched_tasks = {}  # task_id → {tech_name, new_level, ...}

        for tech_name, profile in profiles:
            matched = self._match_tasks(scope_data["tasks"], profile)
            per_tech_matches[tech_name] = matched

            for task_id, match_info in matched.items():
                new_level = profile["classification_shift"]
                new_level_idx = AUTOMATION_LEVELS.index(new_level)

                if task_id in all_matched_tasks:
                    # Higher automation level wins
                    existing_idx = AUTOMATION_LEVELS.index(
                        all_matched_tasks[task_id]["new_level"]
                    )
                    if new_level_idx > existing_idx:
                        all_matched_tasks[task_id]["new_level"] = new_level
                        all_matched_tasks[task_id]["winning_tech"] = tech_name
                    all_matched_tasks[task_id]["contributing_techs"].append(tech_name)
                else:
                    all_matched_tasks[task_id] = {
                        "task_name": match_info["task_name"],
                        "new_level": new_level,
                        "winning_tech": tech_name,
                        "contributing_techs": [tech_name],
                        "current_level": match_info["current_level"],
                    }

        if not all_matched_tasks:
            return {
                "simulation_type": "multi_tech_adoption",
                "technologies": technology_names,
                "tasks_matched": 0,
                "cascade": None,
            }

        # Step 3: Generate merged reclassifications (max level per task)
        reclassifications = []
        for task_id, info in all_matched_tasks.items():
            reclassifications.append({
                "task_id": task_id,
                "new_automation_level": info["new_level"],
            })

        # Step 4: Compute combined technology costs (additive per tech)
        total_hc = scope_data["summary"]["total_headcount"]
        per_tech_costs = {}
        combined_licensing = 0.0
        combined_implementation = 0.0

        for tech_name, profile in profiles:
            tc = self.cascade.financial.compute_tech_costs(
                tech_name,
                profile["license_tier"],
                total_hc,
                self.cascade.timeline_months,
                monthly_per_user_override=profile.get("monthly_per_user_override"),
            )
            per_tech_costs[tech_name] = tc
            combined_licensing += tc["total_licensing"]
            combined_implementation += tc["implementation"]

        combined_tech_costs = {
            "total_licensing": round(combined_licensing, 2),
            "implementation": round(combined_implementation, 2),
            "total": round(combined_licensing + combined_implementation, 2),
        }

        # Step 5: Run cascade with merged reclassifications and combined costs
        cascade_result = self.cascade.run(
            scope_data, reclassifications, combined_tech_costs
        )

        # Step 6: Determine combined adoption speed (weighted by tasks matched)
        # Each technology adopts at its own speed. The overall adoption speed
        # is the weighted average by number of tasks matched (i.e., the tech
        # that affects the most work has the most influence on overall pace).
        speed_values = {"slow": 0, "moderate": 1, "fast": 2}
        speed_labels = {0: "slow", 1: "moderate", 2: "fast"}
        weighted_sum = 0.0
        total_matched = 0
        for tech_name, profile in profiles:
            matched_count = len(per_tech_matches.get(tech_name, {}))
            tech_speed = profile.get("adoption_speed", "moderate")
            weighted_sum += speed_values.get(tech_speed, 1) * matched_count
            total_matched += matched_count
        avg_speed = weighted_sum / total_matched if total_matched > 0 else 1
        # Round to nearest speed category
        slowest_speed = speed_labels[round(avg_speed)]

        # Step 7: Apply adoption discount
        adoption_discount = self._compute_adoption_discount(
            slowest_speed, self.cascade.timeline_months
        )
        unadjusted_savings = cascade_result["financial"]["gross_savings"]
        adjusted_savings = round(unadjusted_savings * adoption_discount, 2)
        cascade_result["financial"]["unadjusted_gross_savings"] = unadjusted_savings
        cascade_result["financial"]["gross_savings"] = adjusted_savings
        cascade_result["financial"]["adoption_discount_factor"] = round(
            adoption_discount, 3
        )
        total_cost = cascade_result["financial"]["total_cost"]
        net_impact = adjusted_savings - total_cost
        cascade_result["financial"]["net_impact"] = round(net_impact, 2)
        roi_pct = (net_impact / total_cost * 100) if total_cost > 0 else (
            9999.0 if adjusted_savings > 0 else 0)
        cascade_result["financial"]["roi_pct"] = round(roi_pct, 1)
        monthly_savings = (
            adjusted_savings / self.cascade.timeline_months
            if self.cascade.timeline_months > 0 else 0
        )
        cascade_result["financial"]["payback_months"] = (
            int(total_cost / monthly_savings) if monthly_savings > 0 else 0
        )
        if "summary" in cascade_result:
            cascade_result["summary"]["gross_savings"] = adjusted_savings
            cascade_result["summary"]["net_impact"] = round(net_impact, 2)
            cascade_result["summary"]["roi_pct"] = round(roi_pct, 1)

        # Step 8: Per-technology breakdown
        per_tech_summary = []
        for tech_name, profile in profiles:
            matched = per_tech_matches[tech_name]
            tc = per_tech_costs[tech_name]
            # Count tasks where this tech was the winner
            winning_tasks = sum(
                1 for info in all_matched_tasks.values()
                if info["winning_tech"] == tech_name
            )
            per_tech_summary.append({
                "technology": tech_name,
                "vendor": profile["vendor"],
                "license_tier": profile["license_tier"],
                "adoption_speed": profile["adoption_speed"],
                "tasks_matched": len(matched),
                "tasks_won": winning_tasks,
                "licensing_cost": tc["total_licensing"],
                "implementation_cost": tc["implementation"],
            })

        # Count overlapping tasks
        overlap_count = sum(
            1 for info in all_matched_tasks.values()
            if len(info["contributing_techs"]) > 1
        )

        return {
            "simulation_type": "multi_tech_adoption",
            "technologies": [
                {"name": n, "vendor": p["vendor"], "adoption_speed": p["adoption_speed"]}
                for n, p in profiles
            ],
            "combined_adoption_speed": slowest_speed,
            "task_matching": {
                "total_tasks": len(scope_data["tasks"]),
                "unique_tasks_matched": len(all_matched_tasks),
                "overlap_tasks": overlap_count,
                "per_technology": {
                    tech_name: {
                        "tasks_matched": len(matches),
                        "matched_task_names": [m["task_name"] for m in matches.values()],
                    }
                    for tech_name, matches in per_tech_matches.items()
                },
            },
            "cascade": cascade_result,
            "per_technology_costs": per_tech_costs,
            "per_technology_summary": per_tech_summary,
            "combined_technology_costs": combined_tech_costs,
            "adoption_discount_factor": round(adoption_discount, 3),
            "recommendation": self._generate_recommendation(cascade_result, combined_tech_costs),
        }

    @classmethod
    def available_technologies(cls) -> List[str]:
        """List available technology profiles."""
        return list(TECHNOLOGY_PROFILES.keys())
