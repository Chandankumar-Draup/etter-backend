from typing import List
import numpy as np
from mesa import Agent, Model

from .role_provider import Workload


class Employee(Agent):
    """Employee Agent - Optimized Version"""

    def __init__(self, model: Model, role: str, automation_incentive: float = 1.0):
        """Employee Agent Construction"""

        self.knowledge_gaining_rate = 2  # It takes 2 weeks to learn a skill so  2 skills per month
        self.role = role
        self.type = "employee"
        super().__init__(model)

        self.expected_output = 1.0
        self.automation_incentive = automation_incentive

        self.workloads: List[Workload] = self.model.responsibilities_from_roles(role)
        # Cache frequently used arrays for faster access - convert to numpy arrays
        self._workload_types = np.array([workload["Type"] for workload in self.workloads])
        self._workload_skills = np.array([workload["Skill"] for workload in self.workloads])
        self._workload_times = np.array([workload["Time"] for workload in self.workloads])
        self._workload_knowledge = np.array([0.0 for _ in self.workloads])

        # Pre-compute auto mask (this won't change)
        self._auto_mask = self._workload_types == "Auto"

        # Initialize metrics
        self.time_savings = 0.0
        self.automation_rate = 0.0
        self.time_to_complete = 1.0
        self.unused_output_capacity = 0.0
        self.time_to_complete_unit_work = 1.0

        # Cache for boolean masks to avoid repeated computation
        self._is_automated = np.zeros(len(self.workloads), dtype=bool)
        self._manual_mask = np.ones(len(self.workloads), dtype=bool)

    def update_task(self):
        """Update the task for the employee - Optimized"""

        # Vectorized boolean operations
        self._is_automated = self._auto_mask & (self._workload_skills <= self._workload_knowledge)
        self._manual_mask = ~self._is_automated

    def complete_workloads(self):
        """Complete workloads calculation - Optimized"""

        # Use cached values for calculations
        total_workloads = len(self.workloads)
        automated_count = np.sum(self._is_automated)

        self.automation_rate = automated_count / total_workloads if total_workloads > 0 else 0.0

        # Vectorized time calculation for manual workloads
        self.time_to_complete_unit_work = np.sum(self._workload_times[self._manual_mask])

        self.time_to_complete = self.time_to_complete_unit_work * self.expected_output
        self.time_savings = 1.0 - self.time_to_complete

        if self.time_to_complete_unit_work > 0:
            self.unused_output_capacity = (
                1.0 / self.time_to_complete_unit_work
            ) - self.expected_output
        else:
            self.unused_output_capacity = 0.0

    def updated_expected_output(self, increment: float):
        """Update expected output"""
        self.expected_output += increment

    def gain_knowledge(self):
        """Gain knowledge - Optimized"""

        # Find automatable workloads among manual ones
        automatable_mask = self._manual_mask & self._auto_mask

        if not np.any(automatable_mask):
            return

        # Use numpy random for consistency and potential speed
        if np.random.random() > self.automation_incentive:
            return

        # Find index of max time among automatable workloads
        automatable_times = self._workload_times.copy()
        automatable_times[~automatable_mask] = -1  # Mask non-automatable
        max_index = np.argmax(automatable_times)

        # Update knowledge with bounds checking
        current_knowledge = self._workload_knowledge[max_index]
        new_knowledge = min(current_knowledge + 0.20, 1.0)
        self._workload_knowledge[max_index] = new_knowledge

        # Note: Since Workload TypedDict doesn't include Knowledge field,
        # we only track knowledge in the numpy array for performance.
        # The original workloads list remains unchanged as it represents
        # the base workload data without dynamic knowledge updates.

    def step(self):
        """Advance the employee by one step"""
        self.update_task()
        self.complete_workloads()
        if np.random.poisson(lam=self.knowledge_gaining_rate) > self.knowledge_gaining_rate:
            self.gain_knowledge()
