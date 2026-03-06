"""
Phase 3.10: Task Distribution Controls.

Users set a TARGET automation distribution (e.g. 10% human_only, 30% human_led,
35% shared, 20% ai_led, 5% ai_only) and the engine computes the minimum set
of task reclassifications to reach that target.

This replaces the blunt "automation_factor=0.5 advances everything by 1 step"
with a principled, user-controllable mechanism.

Algorithm:
  1. Compute current distribution across all tasks (weighted by time_allocation_pct)
  2. Compare to target distribution — find surplus/deficit per level
  3. Greedily move tasks from surplus levels toward deficit levels
  4. Respect constraints: max_steps_per_task, classification filters
  5. Return task reclassifications ready for the cascade engine
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import AUTOMATION_LEVELS

logger = logging.getLogger(__name__)


@dataclass
class TaskDistributionTarget:
    """User-defined target task distribution by automation level.

    All percentages are time-allocation-weighted and must sum to 100%.
    """
    human_only_pct: float = 10.0
    human_led_pct: float = 25.0
    shared_pct: float = 35.0
    ai_led_pct: float = 25.0
    ai_only_pct: float = 5.0

    # Which task classification categories to include in redistribution.
    # None means all categories are eligible.
    target_classifications: Optional[List[str]] = None

    # Constraints
    max_steps_per_task: int = 2          # Max levels a task can jump (1-4)
    min_time_allocation_pct: float = 0.0  # Skip tiny tasks below this threshold

    def as_dict(self) -> Dict[str, float]:
        """Return target distribution as {level: pct} dict."""
        return {
            "human_only": self.human_only_pct,
            "human_led": self.human_led_pct,
            "shared": self.shared_pct,
            "ai_led": self.ai_led_pct,
            "ai_only": self.ai_only_pct,
        }

    def validate(self) -> bool:
        """Check that percentages sum to ~100."""
        total = sum(self.as_dict().values())
        return abs(total - 100.0) < 0.5


class TaskDistributor:
    """Computes task reclassifications to reach a target distribution.

    Usage:
        distributor = TaskDistributor()
        result = distributor.compute(tasks, target)
        # result["reclassifications"] → ready for CascadeEngine
    """

    def compute(
        self,
        tasks: List[Dict[str, Any]],
        target: TaskDistributionTarget,
    ) -> Dict[str, Any]:
        """Compute minimum reclassifications to reach target distribution.

        Args:
            tasks: List of task dicts from scope_data["tasks"]
            target: User-defined target distribution

        Returns:
            Dict with current/target distributions, reclassifications, and summary.
        """
        if not target.validate():
            raise ValueError(
                f"Target distribution sums to {sum(target.as_dict().values()):.1f}%, "
                f"must be ~100%"
            )

        # Filter eligible tasks
        eligible = self._filter_eligible(tasks, target)
        if not eligible:
            return self._empty_result(tasks, target)

        # Compute current distribution (time-allocation-weighted)
        current_dist = self._compute_distribution(eligible)
        target_dist = target.as_dict()

        # Compute surplus/deficit per level
        total_time = sum(t.get("time_allocation_pct", 0) for t in eligible)
        level_surplus = {}  # positive = surplus (need to move tasks OUT)
        for level in AUTOMATION_LEVELS:
            current_pct = current_dist.get(level, 0)
            target_pct = target_dist.get(level, 0)
            level_surplus[level] = current_pct - target_pct

        # Greedily assign moves
        reclassifications = self._greedy_assign(
            eligible, level_surplus, target, total_time
        )

        # Compute achieved distribution
        achieved_dist = self._compute_achieved_distribution(
            eligible, reclassifications
        )

        return {
            "current_distribution": current_dist,
            "target_distribution": target_dist,
            "achieved_distribution": achieved_dist,
            "eligible_tasks": len(eligible),
            "total_tasks": len(tasks),
            "reclassifications": reclassifications,
            "tasks_moved": len(reclassifications),
            "distribution_error": self._distribution_error(
                achieved_dist, target_dist
            ),
        }

    def _filter_eligible(
        self,
        tasks: List[Dict],
        target: TaskDistributionTarget,
    ) -> List[Dict]:
        """Filter tasks eligible for redistribution."""
        eligible = []
        for t in tasks:
            # Skip tiny tasks
            if t.get("time_allocation_pct", 0) < target.min_time_allocation_pct:
                continue
            # Filter by classification category if specified
            if target.target_classifications:
                classification = t.get("classification", "")
                if classification not in target.target_classifications:
                    continue
            eligible.append(t)
        return eligible

    def _compute_distribution(
        self, tasks: List[Dict]
    ) -> Dict[str, float]:
        """Compute time-allocation-weighted distribution across automation levels."""
        total_time = sum(t.get("time_allocation_pct", 0) for t in tasks)
        if total_time == 0:
            return {level: 0.0 for level in AUTOMATION_LEVELS}

        dist = {level: 0.0 for level in AUTOMATION_LEVELS}
        for t in tasks:
            level = t.get("automation_level", "human_led")
            if level not in dist:
                level = "human_led"
            dist[level] += t.get("time_allocation_pct", 0)

        # Convert to percentages
        return {level: round(time / total_time * 100, 1) for level, time in dist.items()}

    def _greedy_assign(
        self,
        tasks: List[Dict],
        level_surplus: Dict[str, float],
        target: TaskDistributionTarget,
        total_time: float,
    ) -> List[Dict[str, Any]]:
        """Greedily move tasks from surplus levels toward deficit levels.

        Strategy: For each surplus level (highest surplus first), pick tasks
        and move them to the nearest deficit level respecting max_steps.
        """
        if total_time == 0:
            return []

        max_steps = target.max_steps_per_task
        reclassifications = []
        moved_task_ids = set()

        # Sort tasks by time_allocation_pct descending (move big tasks first
        # for fewer total moves)
        sorted_tasks = sorted(
            tasks, key=lambda t: t.get("time_allocation_pct", 0), reverse=True
        )

        # Work through surplus levels (largest surplus first)
        surplus_levels = sorted(
            [(lvl, surplus) for lvl, surplus in level_surplus.items() if surplus > 0.5],
            key=lambda x: -x[1],
        )

        # Track remaining surplus/deficit as we assign
        remaining = dict(level_surplus)

        for source_level, _ in surplus_levels:
            source_idx = AUTOMATION_LEVELS.index(source_level)

            # Find deficit levels reachable within max_steps
            candidate_targets = []
            for step in range(1, max_steps + 1):
                up_idx = source_idx + step
                if up_idx < len(AUTOMATION_LEVELS):
                    up_level = AUTOMATION_LEVELS[up_idx]
                    if remaining.get(up_level, 0) < -0.5:
                        candidate_targets.append((up_level, up_idx, step))

            if not candidate_targets:
                continue

            # Move tasks from source_level to best target
            for task in sorted_tasks:
                if task["id"] in moved_task_ids:
                    continue
                task_level = task.get("automation_level", "human_led")
                if task_level != source_level:
                    continue

                # Pick the best target (nearest deficit)
                best_target = None
                for tgt_level, tgt_idx, steps in candidate_targets:
                    if remaining.get(tgt_level, 0) < -0.5:
                        best_target = tgt_level
                        break

                if best_target is None:
                    continue

                task_pct = task.get("time_allocation_pct", 0) / total_time * 100
                reclassifications.append({
                    "task_id": task["id"],
                    "new_automation_level": best_target,
                })
                moved_task_ids.add(task["id"])

                # Update remaining surplus/deficit
                remaining[source_level] -= task_pct
                remaining[best_target] += task_pct

                # Check if source is no longer surplus
                if remaining[source_level] <= 0.5:
                    break

        return reclassifications

    def _compute_achieved_distribution(
        self,
        tasks: List[Dict],
        reclassifications: List[Dict],
    ) -> Dict[str, float]:
        """Compute what the distribution would be after reclassifications."""
        reclass_map = {r["task_id"]: r["new_automation_level"] for r in reclassifications}
        total_time = sum(t.get("time_allocation_pct", 0) for t in tasks)
        if total_time == 0:
            return {level: 0.0 for level in AUTOMATION_LEVELS}

        dist = {level: 0.0 for level in AUTOMATION_LEVELS}
        for t in tasks:
            level = reclass_map.get(t["id"], t.get("automation_level", "human_led"))
            if level not in dist:
                level = "human_led"
            dist[level] += t.get("time_allocation_pct", 0)

        return {level: round(time / total_time * 100, 1) for level, time in dist.items()}

    def _distribution_error(
        self,
        achieved: Dict[str, float],
        target: Dict[str, float],
    ) -> float:
        """Mean absolute error between achieved and target distributions."""
        errors = [abs(achieved.get(lvl, 0) - target.get(lvl, 0)) for lvl in AUTOMATION_LEVELS]
        return round(sum(errors) / len(errors), 2)

    def _empty_result(
        self, tasks: List[Dict], target: TaskDistributionTarget
    ) -> Dict[str, Any]:
        current_dist = self._compute_distribution(tasks)
        return {
            "current_distribution": current_dist,
            "target_distribution": target.as_dict(),
            "achieved_distribution": current_dist,
            "eligible_tasks": 0,
            "total_tasks": len(tasks),
            "reclassifications": [],
            "tasks_moved": 0,
            "distribution_error": self._distribution_error(
                current_dist, target.as_dict()
            ),
        }
