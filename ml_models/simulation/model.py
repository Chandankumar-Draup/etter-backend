from typing import Dict, List, Union
from typing_extensions import TypedDict
from itertools import product

import pandas as pd
from numpy.random import random
from numpy import mean, empty, float64
from mesa import Model, DataCollector

from .role_provider import RoleDataProvider, Workload
from .agent import Employee


# TODO: future categories
# 6 categories:
#     No Imapct
#     Augment
#     Automated


class EmployeeGroupProfile(TypedDict):
    role: str
    count: int
    salary: float


class AutomationImpactOrganizationModel(Model):
    def __init__(
        self,
        role_groups: List[EmployeeGroupProfile],
        role_provider: RoleDataProvider,
        company: str = "",
        automation_factor: float = 0.2,
    ):
        self.automation_factor = automation_factor

        self.employees: Dict[str, List[Employee]] = {}
        self.total_time = 0.0
        self.total_employees = 0
        self.avg_automation_rate = 0.0
        self.avg_total_unit_work = 1.0
        self.total_time_unit_work = 1.0
        self.avg_time_per_employee = 1.0
        self.total_salary_of_employees = 1.0
        self.avg_unused_output_capacity = 0.0
        self.avg_time_unit_work_per_employee = 1.0

        self.company = company
        self.role_provider = role_provider
        assert self.role_provider is not None
        super().__init__()

        self.role_salaries = {
            role_group["role"]: role_group["salary"] for role_group in role_groups
        }

        for role_group in role_groups:
            self.employees[role_group["role"]] = [
                Employee(self, role_group["role"], self.automation_factor)
                for _ in range(role_group["count"])
            ]
            self.total_time += role_group["count"]
            self.total_employees += role_group["count"]

        self.initial_employee_salaries = sum(
            role_group["salary"] * role_group["count"] for role_group in role_groups
        )
        self.initial_employee_population = self.total_employees
        self.total_employees_normalized = self.total_employees / self.initial_employee_population

        # Cache role auto time counts to avoid repeated computation
        self.role_auto_time_count = {
            role_group["role"]: self._compute_auto_time_count(role_group["role"])
            for role_group in role_groups
        }

        report_metrics = {
            "total_time": "total_time",
            "total_employees": "total_employees_normalized",
            "avg_time_per_employee": "avg_time_per_employee",
            "avg_automation_rate": "avg_automation_rate",
            "total_salary_of_employees": "total_salary_of_employees",
            "avg_unused_output_capacity": "avg_unused_output_capacity",
        }

        self.role_metrics: Dict[str, Union[int, float]] = {}
        for group in role_groups:
            self.role_metrics[f"{group['role']}_count"] = group["count"]
            self.role_metrics[f"{group['role']}_total_salary_of_employee"] = (
                group["count"] * group["salary"]
            )
            self.role_metrics[f"{group['role']}_avg_automation_rate"] = 0.0
            self.role_metrics[f"{group['role']}_avg_time_per_employee"] = 1.0
            self.role_metrics[f"{group['role']}_avg_unused_output_capacity"] = 0.0

        self.roles = [group["role"] for group in role_groups]
        self.metrics = [
            "count",
            "total_salary_of_employee",
            "avg_automation_rate",
            "avg_time_per_employee",
            "avg_unused_output_capacity",
        ]

        # Pre-compute all attribute keys to avoid repeated product calculation
        attribute_keys = [f"{role}_{metric}" for role, metric in product(self.roles, self.metrics)]
        for key in attribute_keys:
            setattr(self, key, self.role_metrics[key])
            report_metrics[key] = key

        self.datacollector = DataCollector(model_reporters=report_metrics)

    def _compute_metrics(self):
        """Compute metrics for the model - Optimized version"""

        # Single pass through all employees to collect all metrics
        total_employees = 0
        total_time_unit_work = 0.0
        total_automation_rate = 0.0
        total_time_to_complete = 0.0
        total_unused_output_capacity = 0.0
        total_salary_of_employees = 0.0

        # Pre-allocate arrays for role-specific metrics to avoid repeated allocations
        role_automation_rates = {}
        role_time_to_complete = {}
        role_unused_capacities = {}

        for role, employees in self.employees.items():
            employee_count = len(employees)
            if employee_count == 0:
                continue

            total_employees += employee_count
            total_salary_of_employees += employee_count * self.role_salaries[role]

            # Pre-allocate numpy arrays for vectorized operations
            automation_rates = empty(employee_count, dtype=float64)
            time_to_complete = empty(employee_count, dtype=float64)
            unused_capacities = empty(employee_count, dtype=float64)

            # Single pass through employees to collect all metrics
            for i, emp in enumerate(employees):
                automation_rates[i] = emp.automation_rate
                time_to_complete[i] = emp.time_to_complete
                unused_capacities[i] = emp.unused_output_capacity

                # Accumulate totals
                total_time_unit_work += emp.time_to_complete_unit_work
                total_automation_rate += emp.automation_rate
                total_time_to_complete += emp.time_to_complete
                total_unused_output_capacity += emp.unused_output_capacity

            # Store arrays for later use
            role_automation_rates[role] = automation_rates
            role_time_to_complete[role] = time_to_complete
            role_unused_capacities[role] = unused_capacities

        # Assign computed metrics
        assert self.total_employees >= total_employees
        self.total_employees = total_employees
        self.total_time_unit_work = total_time_unit_work
        self.total_salary_of_employees = total_salary_of_employees / self.initial_employee_salaries

        # Compute avg metrics
        if total_employees > 0:
            self.avg_total_unit_work = total_time_unit_work / total_employees
            self.avg_time_per_employee = total_time_to_complete / total_employees
            self.avg_time_unit_work_per_employee = self.total_time_unit_work / total_employees
            self.avg_automation_rate = total_automation_rate / total_employees
            self.avg_unused_output_capacity = total_unused_output_capacity / total_employees
        else:
            self.avg_total_unit_work = 0.0
            self.avg_time_per_employee = 0.0
            self.avg_time_unit_work_per_employee = 0.0
            self.avg_automation_rate = 0.0
            self.avg_unused_output_capacity = 0.0

        self.total_employees_normalized = total_employees / self.initial_employee_population

        # Update role metrics using vectorized operations
        for role, employees in self.employees.items():
            employee_count = len(employees)
            self.role_metrics[f"{role}_count"] = employee_count
            self.role_metrics[f"{role}_total_salary_of_employee"] = (
                employee_count * self.role_salaries[role]
            )

            if employee_count > 0:
                # Use vectorized numpy operations instead of mean() on lists
                self.role_metrics[f"{role}_avg_automation_rate"] = mean(
                    role_automation_rates[role], dtype=float64
                )
                self.role_metrics[f"{role}_avg_time_per_employee"] = mean(
                    role_time_to_complete[role], dtype=float64
                )
                self.role_metrics[f"{role}_avg_unused_output_capacity"] = mean(
                    role_unused_capacities[role], dtype=float64
                )
            else:
                self.role_metrics[f"{role}_avg_automation_rate"] = 0.0
                self.role_metrics[f"{role}_avg_time_per_employee"] = 0.0
                self.role_metrics[f"{role}_avg_unused_output_capacity"] = 0.0

        # Update model attributes - use pre-computed keys for efficiency
        for key in [f"{role}_{metric}" for role, metric in product(self.roles, self.metrics)]:
            setattr(self, key, self.role_metrics[key])

    def _reduce_workforce(self):
        """Reduce workforce based on time savings and output level - Optimized"""

        for role, employees in self.employees.items():
            if not employees:
                continue

            # Pre-compute employee metrics to avoid repeated attribute access
            employee_data = [
                (emp, emp.time_savings, emp.expected_output, emp.unused_output_capacity)
                for emp in employees
            ]

            # Sort by time_savings and output level (descending)
            employee_data.sort(key=lambda x: (x[1], x[2]), reverse=True)

            # Extract sorted employees
            sorted_employees = [data[0] for data in employee_data]
            self.employees[role] = sorted_employees

            # One to one replacement - optimized
            walker = 0
            bottom_pointer = 0
            total_employees = len(sorted_employees)

            while (
                walker < total_employees - 1 - bottom_pointer
                and sorted_employees[walker].unused_output_capacity
                >= sorted_employees[-1 - bottom_pointer].expected_output
            ):
                sorted_employees[walker].updated_expected_output(
                    sorted_employees[-1 - bottom_pointer].expected_output
                )
                bottom_pointer += 1
                walker += 1

            # Remove bottom employees
            if bottom_pointer > 0:
                self.employees[role] = sorted_employees[:-bottom_pointer]
                sorted_employees = self.employees[role]
                total_employees = len(sorted_employees)

            # Many to one replacement - optimized
            walker = 0
            bottom_pointer = 0
            collective_bucket = []
            collective_unused_output_capacity = 0.0

            while walker < total_employees - 1 - bottom_pointer:
                current_emp = sorted_employees[walker]
                if current_emp.unused_output_capacity >= 0:
                    collective_unused_output_capacity += current_emp.unused_output_capacity
                    collective_bucket.append(current_emp)
                else:
                    break

                if (
                    collective_unused_output_capacity
                    >= sorted_employees[-1 - bottom_pointer].expected_output
                ):
                    # Update all employees in bucket
                    for employee in collective_bucket:
                        employee.updated_expected_output(employee.unused_output_capacity)

                    collective_bucket.clear()
                    collective_unused_output_capacity = 0.0
                    bottom_pointer += 1

                walker += 1

            # Remove bottom employees
            if bottom_pointer > 0:
                self.employees[role] = sorted_employees[:-bottom_pointer]

    def step(self):
        """Advance the model by one step"""
        self.agents.shuffle_do("step")
        self._compute_metrics()
        if random() <= self.automation_factor:
            self._reduce_workforce()
        self.datacollector.collect(self)

    def _compute_auto_time_count(self, role: str) -> float:
        table = self.role_provider.get_responsibilities_from_role(role, self.company)

        auto_time_count = sum(workload["Time"] for workload in table if workload["Type"] == "Auto")
        return auto_time_count

    def responsibilities_from_roles(self, role: str) -> List[Workload]:
        """Get responsibilities from roles

        Args:
            role (str): The role to get responsibilities for
        Returns:
            pd.DataFrame: DataFrame of responsibilities

        Throws:
            ValueError: If the role is not found in the role provider
        """
        responsibilities = self.role_provider.get_responsibilities_from_role(role, self.company)
        if responsibilities is None:
            raise ValueError(f"Role {role} not found in role provider")
        return responsibilities
