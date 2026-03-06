"""
Scenario Manager: CRUD and comparison for simulation scenarios.

A scenario is a parameterized simulation run. The manager:
  - Creates scenarios with specific parameters
  - Runs scenarios through the appropriate simulation
  - Stores results
  - Compares multiple scenarios side-by-side

Meadows insight: Scenarios are thought experiments made rigorous.
By comparing multiple scenarios, we reveal the system's sensitivity
to different interventions (leverage points analysis).
"""

import copy
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from draup_world_model.digital_twin.config import OutputConfig, SimulationConfig
from draup_world_model.digital_twin.simulation.cascade_engine import CascadeEngine
from draup_world_model.digital_twin.simulation.scope_selector import ScopeSelector
from draup_world_model.digital_twin.simulation.simulations.role_redesign import RoleRedesignSimulation
from draup_world_model.digital_twin.simulation.simulations.tech_adoption import TechAdoptionSimulation
from draup_world_model.digital_twin.simulation.simulations.skills_strategy import SkillsStrategySimulation
from draup_world_model.digital_twin.simulation.simulation_engine_v2 import SimulationEngineV2
from draup_world_model.digital_twin.simulation.task_distributor import (
    TaskDistributor,
    TaskDistributionTarget,
)

logger = logging.getLogger(__name__)


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario."""
    name: str
    simulation_type: str  # 'role_redesign', 'tech_adoption'
    scope_type: str = "function"
    scope_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    timeline_months: int = 36


class ScenarioManager:
    """Manages simulation scenarios: create, run, compare."""

    def __init__(
        self,
        neo4j_conn,
        output: OutputConfig = None,
        simulation_config: Optional[SimulationConfig] = None,
    ):
        self.conn = neo4j_conn
        self.output = output or OutputConfig()
        self.sim_config = simulation_config or SimulationConfig()
        self.scope_selector = ScopeSelector(neo4j_conn)
        self._scenarios: Dict[str, Dict] = {}
        self._results_dir = self.output.base_dir / "scenarios"
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._load_existing_scenarios()

    def _load_existing_scenarios(self) -> None:
        """Reload previously saved scenarios from disk (survives Flask restarts)."""
        for path in sorted(self._results_dir.glob("scenario_*.json")):
            try:
                with open(path) as f:
                    data = json.load(f)
                scenario_id = path.stem
                if scenario_id in self._scenarios:
                    continue  # already loaded
                # New format has _metadata key; old format is just the result
                if "_metadata" in data:
                    self._scenarios[scenario_id] = {
                        "id": scenario_id,
                        "config": data["_metadata"]["config"],
                        "status": "completed",
                        "result": data["result"],
                        "created_at": data["_metadata"].get("created_at", 0),
                        "completed_at": data["_metadata"].get("completed_at", 0),
                    }
                else:
                    # Legacy format: result-only JSON
                    self._scenarios[scenario_id] = {
                        "id": scenario_id,
                        "config": {"name": scenario_id, "simulation_type": "unknown"},
                        "status": "completed",
                        "result": data,
                        "created_at": 0,
                    }
                logger.debug(f"Loaded scenario from disk: {scenario_id}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping corrupt scenario file {path}: {e}")
        if self._scenarios:
            logger.info(f"Loaded {len(self._scenarios)} scenarios from disk")

    def create_scenario(self, config: ScenarioConfig) -> str:
        """Create a named scenario. Returns scenario_id."""
        scenario_id = f"scenario_{config.name.lower().replace(' ', '_')}_{int(time.time())}"
        self._scenarios[scenario_id] = {
            "id": scenario_id,
            "config": asdict(config),
            "status": "created",
            "result": None,
            "created_at": time.time(),
        }
        logger.info(f"Created scenario: {scenario_id}")
        return scenario_id

    def run_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Run a scenario and store results."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")

        config = scenario["config"]
        logger.info(f"Running scenario: {scenario_id} ({config['simulation_type']})")
        scenario["status"] = "running"

        # Select scope
        scope_data = self.scope_selector.select(
            config["scope_type"],
            config["scope_name"],
        )

        if scope_data["summary"]["role_count"] == 0:
            scenario["status"] = "failed"
            scenario["result"] = {"error": "No roles found in scope"}
            return scenario["result"]

        # Create cascade engine with simulation config
        cascade = CascadeEngine(
            timeline_months=config["timeline_months"],
            config=self.sim_config,
        )

        # Deep-copy scope_data — simulations mutate tasks in-place via the
        # cascade engine (Step 1 sets task["automation_level"]).  Without a
        # copy the original scope_data is tainted for downstream consumers
        # like skills_strategy that still need the pre-simulation state.
        sim_scope = copy.deepcopy(scope_data)

        # Run the appropriate simulation
        sim_type = config["simulation_type"]
        params = config.get("parameters", {})

        if sim_type == "role_redesign":
            sim = RoleRedesignSimulation(cascade)
            result = sim.run(
                sim_scope,
                automation_factor=params.get("automation_factor", 0.5),
                target_classifications=params.get("target_classifications"),
            )

        elif sim_type == "tech_adoption":
            sim = TechAdoptionSimulation(cascade)
            result = sim.run(
                sim_scope,
                technology_name=params.get("technology_name", "Microsoft Copilot"),
                adoption_months=params.get("adoption_months", 12),
                custom_profile=params.get("custom_profile"),
            )

        elif sim_type == "multi_tech_adoption":
            sim = TechAdoptionSimulation(cascade)
            result = sim.run_multi(
                sim_scope,
                technology_names=params.get("technology_names", []),
                adoption_months=params.get("adoption_months", 12),
                custom_profiles=params.get("custom_profiles"),
            )

        else:
            raise ValueError(f"Unknown simulation type: {sim_type}")

        # Run skills strategy on the cascade result (always runs post-cascade)
        cascade_result = result.get("cascade")
        if cascade_result:
            skills_sim = SkillsStrategySimulation(
                financial_config=self.sim_config.financial,
            )
            skills_result = skills_sim.run(scope_data, cascade_result)
            result["skills_strategy"] = skills_result

        # Attach role-skill mapping for UI cross-referencing
        result["role_skills"] = [
            {"role_id": r["id"], "role_name": r["name"], "skill_ids": r.get("skill_ids", [])}
            for r in scope_data["roles"]
        ]

        # Apply constraints if specified
        constraints = config.get("constraints", {})
        if constraints:
            result = self._apply_constraints(result, constraints)

        # Store result
        scenario["status"] = "completed"
        scenario["result"] = result
        scenario["completed_at"] = time.time()

        # Save to disk
        self._save_result(scenario_id, result)

        logger.info(f"Scenario {scenario_id} completed")
        return result

    def run_scenario_v2(self, scenario_id: str) -> Dict[str, Any]:
        """Run a scenario using the v2 time-stepped engine.

        Returns monthly trajectory instead of a single-shot cascade snapshot.
        Supports all v1 simulation types plus 'task_distribution'.
        """
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")

        config = scenario["config"]
        logger.info(f"Running v2 scenario: {scenario_id} ({config['simulation_type']})")
        scenario["status"] = "running"

        # Select scope
        scope_data = self.scope_selector.select(
            config["scope_type"],
            config["scope_name"],
        )

        if scope_data["summary"]["role_count"] == 0:
            scenario["status"] = "failed"
            scenario["result"] = {"error": "No roles found in scope"}
            return scenario["result"]

        # Deep-copy scope_data for both v1 and v2 engines.
        # The v1 cascade mutates task["automation_level"] in-place (Step 1),
        # so each engine needs its own pristine copy.
        scope_for_v1 = copy.deepcopy(scope_data)
        scope_for_v2 = copy.deepcopy(scope_data)

        # Create cascade engine
        cascade = CascadeEngine(
            timeline_months=config["timeline_months"],
            config=self.sim_config,
        )

        sim_type = config["simulation_type"]
        params = config.get("parameters", {})
        adoption_speed = params.get("adoption_speed", "moderate")

        # Generate reclassifications and tech costs based on sim type
        reclassifications = []
        tech_costs = None

        if sim_type == "role_redesign":
            sim = RoleRedesignSimulation(cascade)
            v1_result = sim.run(
                scope_for_v1,
                automation_factor=params.get("automation_factor", 0.5),
                target_classifications=params.get("target_classifications"),
            )
            # Extract reclassifications from v1 cascade
            cascade_data = v1_result.get("cascade", {})
            for change in cascade_data.get("task_changes", {}).get("changes", []):
                reclassifications.append({
                    "task_id": change["task_id"],
                    "new_automation_level": change["new_level"],
                })
            tech_costs_data = cascade_data.get("financial", {})
            if tech_costs_data.get("technology_licensing", 0) > 0:
                tech_costs = {
                    "total_licensing": tech_costs_data.get("technology_licensing", 0),
                    "implementation": tech_costs_data.get("implementation_cost", 0),
                }

        elif sim_type == "tech_adoption":
            sim = TechAdoptionSimulation(cascade)
            v1_result = sim.run(
                scope_for_v1,
                technology_name=params.get("technology_name", "Microsoft Copilot"),
                adoption_months=params.get("adoption_months", 12),
                custom_profile=params.get("custom_profile"),
            )
            cascade_data = v1_result.get("cascade", {})
            for change in cascade_data.get("task_changes", {}).get("changes", []):
                reclassifications.append({
                    "task_id": change["task_id"],
                    "new_automation_level": change["new_level"],
                })
            tech_costs = v1_result.get("technology_costs")
            adoption_speed = v1_result.get("technology", {}).get(
                "adoption_speed", adoption_speed
            )

        elif sim_type == "multi_tech_adoption":
            sim = TechAdoptionSimulation(cascade)
            v1_result = sim.run_multi(
                scope_for_v1,
                technology_names=params.get("technology_names", []),
                adoption_months=params.get("adoption_months", 12),
                custom_profiles=params.get("custom_profiles"),
            )
            cascade_data = v1_result.get("cascade", {})
            for change in cascade_data.get("task_changes", {}).get("changes", []):
                reclassifications.append({
                    "task_id": change["task_id"],
                    "new_automation_level": change["new_level"],
                })
            tech_costs = v1_result.get("combined_technology_costs")
            adoption_speed = v1_result.get("combined_adoption_speed", adoption_speed)

        elif sim_type == "task_distribution":
            target = TaskDistributionTarget(**params.get("distribution_target", {}))
            distributor = TaskDistributor()
            dist_result = distributor.compute(scope_for_v1["tasks"], target)
            reclassifications = dist_result["reclassifications"]

        else:
            raise ValueError(f"Unknown simulation type: {sim_type}")

        if not reclassifications:
            scenario["status"] = "completed"
            result = {"error": "No task reclassifications generated", "engine": "v2"}
            scenario["result"] = result
            return result

        # Run v2 time-stepped engine (uses the pristine scope_for_v2)
        v2_engine = SimulationEngineV2(
            cascade_engine=CascadeEngine(
                timeline_months=config["timeline_months"],
                config=self.sim_config,
            ),
            config=self.sim_config,
        )
        trajectory = v2_engine.run(
            scope_for_v2, reclassifications,
            technology_costs=tech_costs,
            adoption_speed=adoption_speed,
        )

        # Build result
        result = {
            "engine": "v2_time_stepped",
            "simulation_type": sim_type,
            "trajectory_summary": trajectory.summary(),
            "milestones": trajectory.milestone_months(),
            "monthly_snapshots": [s.to_dict() for s in trajectory.snapshots],
            "cascade": trajectory.cascade_result,
        }

        # Run skills strategy on the cascade result
        if trajectory.cascade_result:
            skills_sim = SkillsStrategySimulation(
                financial_config=self.sim_config.financial,
            )
            skills_result = skills_sim.run(scope_data, trajectory.cascade_result)
            result["skills_strategy"] = skills_result

        # Store result
        scenario["status"] = "completed"
        scenario["result"] = result
        scenario["completed_at"] = time.time()
        self._save_result(scenario_id, result)

        logger.info(f"v2 scenario {scenario_id} completed")
        return result

    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[Dict]:
        """List all scenarios."""
        return [
            {
                "id": s["id"],
                "name": s["config"]["name"],
                "type": s["config"]["simulation_type"],
                "status": s["status"],
                "engine": s.get("result", {}).get("engine", "v1") if s.get("result") else None,
                "scope_name": s["config"].get("scope_name", ""),
                "scope_type": s["config"].get("scope_type", ""),
                "created_at": s.get("created_at", 0),
            }
            for s in self._scenarios.values()
        ]

    def compare_scenarios(self, scenario_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple completed scenarios side-by-side.

        Returns comparison across dimensions:
        - Financial (gross savings, net impact, ROI)
        - Workforce (headcount reduction, redeployable)
        - Skills (sunrise count, reskilling cost)
        - Risk (risk count, high risks)
        """
        comparisons = []

        for sid in scenario_ids:
            scenario = self._scenarios.get(sid)
            if not scenario or scenario["status"] != "completed":
                continue

            result = scenario["result"]
            cascade = result.get("cascade", {})
            if not cascade:
                continue

            financial = cascade.get("financial", {})
            workforce = cascade.get("workforce", {})
            risks = cascade.get("risks", {})
            skills = result.get("skills_strategy", {}).get("summary", {})

            # Include v2 snapshots for adoption overlay if available
            v2_snapshots = result.get("monthly_snapshots", [])

            comparisons.append({
                "scenario_id": sid,
                "scenario_name": scenario["config"]["name"],
                "simulation_type": scenario["config"]["simulation_type"],
                "engine": result.get("engine", "v1"),
                "financial": {
                    "gross_savings": financial.get("gross_savings", 0),
                    "net_impact": financial.get("net_impact", 0),
                    "roi_pct": financial.get("roi_pct", 0),
                    "payback_months": financial.get("payback_months", 0),
                    "total_cost": financial.get("total_cost", 0),
                },
                "workforce": {
                    "freed_headcount": workforce.get("freed_headcount", 0),
                    "reduction_pct": workforce.get("reduction_pct", 0),
                    "redeployable": workforce.get("redeployable", 0),
                },
                "skills": {
                    "sunrise_count": skills.get("sunrise_count", 0),
                    "sunset_count": skills.get("sunset_count", 0),
                    "reskilling_cost": skills.get("total_reskilling_cost", 0),
                },
                "risk": {
                    "total_risks": risks.get("risk_count", 0),
                    "high_risks": risks.get("high_risks", 0),
                },
                "v2_snapshots": v2_snapshots,
            })

        if not comparisons:
            return {"error": "No completed scenarios to compare"}

        # Find the best scenario by ROI
        best_roi = max(comparisons, key=lambda c: c["financial"]["roi_pct"])
        # Find lowest risk
        lowest_risk = min(comparisons, key=lambda c: c["risk"]["high_risks"])

        return {
            "scenarios": comparisons,
            "best_by_roi": best_roi["scenario_name"],
            "lowest_risk": lowest_risk["scenario_name"],
            "trade_off_summary": self._trade_off_summary(comparisons),
        }

    def _apply_constraints(self, result: Dict, constraints: Dict) -> Dict:
        """Apply post-cascade constraints to simulation results.

        Supported constraints:
            max_headcount_reduction_pct: Scale down workforce impact to cap
            budget_cap: Flag when total_cost exceeds budget
            protected_roles: Exclude listed roles from headcount impact
        """
        cascade = result.get("cascade")
        if not cascade:
            return result

        applied = []

        # max_headcount_reduction_pct: Scale down workforce impact to cap
        max_reduction = constraints.get("max_headcount_reduction_pct")
        if max_reduction is not None:
            workforce = cascade.get("workforce", {})
            actual_reduction = workforce.get("reduction_pct", 0)
            if actual_reduction > max_reduction and actual_reduction > 0:
                scale = max_reduction / actual_reduction
                workforce["freed_headcount"] = round(
                    workforce["freed_headcount"] * scale, 1
                )
                workforce["reduction_pct"] = round(max_reduction, 1)
                workforce["redeployable"] = round(
                    workforce["redeployable"] * scale, 1
                )
                # Scale financial savings proportionally
                financial = cascade.get("financial", {})
                financial["gross_savings"] = round(
                    financial.get("gross_savings", 0) * scale, 2
                )
                financial["net_impact"] = round(
                    financial["gross_savings"] - financial.get("total_cost", 0), 2
                )
                applied.append(
                    f"Capped headcount reduction from {actual_reduction:.1f}% "
                    f"to {max_reduction}%"
                )

        # budget_cap: Flag when total_cost exceeds budget
        budget_cap = constraints.get("budget_cap")
        if budget_cap is not None:
            total_cost = cascade.get("financial", {}).get("total_cost", 0)
            if total_cost > budget_cap:
                applied.append(
                    f"WARNING: Total cost ${total_cost:,.0f} exceeds "
                    f"budget cap ${budget_cap:,.0f}"
                )

        # protected_roles: Exclude listed roles from headcount impact
        protected = constraints.get("protected_roles", [])
        if protected:
            impacts = cascade.get("role_impacts", {}).get("impacts", [])
            for impact in impacts:
                if impact["role_name"] in protected:
                    impact["freed_capacity_pct"] = 0
                    impact["title_impacts"] = [
                        {**ti, "freed_capacity_pct": 0}
                        for ti in impact["title_impacts"]
                    ]
                    applied.append(f"Protected role: {impact['role_name']}")

        result["constraints_applied"] = applied
        return result

    def _trade_off_summary(self, comparisons: List[Dict]) -> str:
        """Generate a human-readable trade-off summary."""
        if len(comparisons) < 2:
            return "Need at least 2 scenarios for trade-off analysis."

        lines = []
        for c in comparisons:
            roi = c["financial"]["roi_pct"]
            risk = c["risk"]["high_risks"]
            lines.append(
                f"{c['scenario_name']}: ROI={roi:.0f}%, "
                f"High Risks={risk}, "
                f"Savings=${c['financial']['net_impact']:,.0f}"
            )
        return " | ".join(lines)

    def _save_result(self, scenario_id: str, result: Dict) -> None:
        """Save scenario result with full metadata to JSON file.

        New format includes _metadata for persistence across restarts.
        """
        scenario = self._scenarios.get(scenario_id, {})
        data = {
            "_metadata": {
                "config": scenario.get("config", {}),
                "created_at": scenario.get("created_at", 0),
                "completed_at": scenario.get("completed_at", 0),
            },
            "result": result,
        }
        path = self._results_dir / f"{scenario_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved result to {path}")

    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a scenario."""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            path = self._results_dir / f"{scenario_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False
