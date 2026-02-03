from unittest import TestCase

from ml_models.simulation.role_lookup import DEFAULT_ROLES
from ml_models.simulation import (
    AutomationImpactOrganizationModel,
    EmployeeGroupProfile,
    InMemoryRoleDataProvider,
)


class TestAIAutomationModel(TestCase):
    def setUp(self):
        role_provider = InMemoryRoleDataProvider(DEFAULT_ROLES)
        self.role_groups = [
            EmployeeGroupProfile(role="Engineer", count=5, salary=1000.0),
            EmployeeGroupProfile(role="Manager", count=2, salary=2000.0),
        ]
        self.model = AutomationImpactOrganizationModel(
            role_groups=self.role_groups,
            role_provider=role_provider,
            automation_factor=0.2,
        )

    def test_initialization(self):
        self.assertEqual(len(self.model.employees), 2)
        self.assertEqual(self.model.total_employees, 7)
        self.assertEqual(self.model.initial_employee_salaries, 9000.0)
        self.assertEqual(self.model.initial_employee_population, 7)

    def test_compute_metrics(self):
        self.model._compute_metrics()
        self.assertEqual(self.model.total_employees, 7)
        self.assertAlmostEqual(self.model.total_salary_of_employees, 1.0)
        self.assertAlmostEqual(self.model.avg_time_per_employee, 1.0)
        self.assertAlmostEqual(self.model.avg_automation_rate, 0.0)

    def test_reduce_workforce(self):
        self.model._reduce_workforce()
        self.assertEqual(len(self.model.employees), 2)
        self.assertEqual(len(self.model.employees["Engineer"]), 5)
        self.assertEqual(len(self.model.employees["Manager"]), 2)

        self.model.employees["Engineer"][0].time_savings = 0.5
        self.model.employees["Engineer"][0].unused_output_capacity = 1.0

        self.model._reduce_workforce()
        self.assertEqual(len(self.model.employees), 2)
        self.assertEqual(len(self.model.employees["Engineer"]), 3)
        self.assertEqual(len(self.model.employees["Manager"]), 2)
