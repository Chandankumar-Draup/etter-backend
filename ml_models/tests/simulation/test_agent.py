from unittest.mock import Mock, MagicMock
from unittest.mock import patch
from unittest import TestCase

import numpy as np

from ml_models.simulation import Employee


class TestEmployee(TestCase):
    def setUp(self):
        self.workloads = [
            {"Name": "Task1", "Type": "Non-Auto", "Time": 0.5, "Skill": 0.5},
            {"Name": "Task2", "Type": "Auto", "Time": 0.5, "Skill": 0.3},
        ]

    def test_initialization(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.5)
        self.assertEqual(self.employee.role, "Engineer")
        self.assertEqual(self.employee.type, "employee")
        self.assertEqual(self.employee.automation_incentive, 0.5)
        self.assertEqual(len(self.employee.workloads), 2)
        self.assertTrue(all(self.employee._workload_knowledge == 0.0))

    def test_update_task_with_no_change(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.5)

        self.employee.update_task()
        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 0.0)

        self.assertEqual(self.employee._manual_mask[0], np.True_)
        self.assertEqual(self.employee._manual_mask[1], np.True_)

        self.assertEqual(self.employee._is_automated[0], np.False_)
        self.assertEqual(self.employee._is_automated[1], np.False_)

    def test_update_task_with_change(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.5)

        self.employee._workload_knowledge[1] = 1.0
        self.employee.update_task()
        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 1.0)

        self.assertEqual(self.employee._manual_mask[0], np.True_)
        self.assertEqual(self.employee._manual_mask[1], np.False_)

        self.assertEqual(self.employee._is_automated[0], np.False_)
        self.assertEqual(self.employee._is_automated[1], np.True_)

    def test_complete_work_all_manual(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.5)
        self.employee._workload_knowledge = np.zeros((2,), dtype=np.float32)

        self.employee._auto_mask = np.zeros((2,), dtype=np.bool)
        self.employee._manual_mask = np.ones((2,), dtype=np.bool)
        self.employee._is_automated = np.zeros((2,), dtype=np.bool)

        self.employee.complete_workloads()

        self.assertEqual(self.employee.time_to_complete, 1.0)
        self.assertEqual(self.employee.time_to_complete_unit_work, 1.0)

        self.assertEqual(self.employee.time_savings, 0.0)
        self.assertEqual(self.employee.unused_output_capacity, 0.0)

    def test_complete_half_saving(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.5)
        self.employee._workload_knowledge = np.zeros((2,), dtype=np.float32)
        self.employee._workload_knowledge[1] = 1.0
        self.employee._auto_mask = np.zeros((2,), dtype=np.bool)
        self.employee._auto_mask[1] = np.True_
        self.employee._manual_mask = np.ones((2,), dtype=np.bool)
        self.employee._manual_mask[1] = np.False_
        self.employee._is_automated = np.zeros((2,), dtype=np.bool)
        self.employee._is_automated[1] = np.True_

        self.employee.complete_workloads()

        self.assertEqual(self.employee.time_to_complete, 0.5)
        self.assertEqual(self.employee.time_to_complete_unit_work, 0.5)

        self.assertEqual(self.employee.time_savings, 0.5)
        self.assertEqual(self.employee.unused_output_capacity, 1.0)

    def test_gain_knowledge_no_learning(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=0.0)

        self.employee._auto_mask = np.zeros((2,), dtype=np.bool)
        self.employee._auto_mask[1] = np.True_
        self.employee._manual_mask = np.ones((2,), dtype=np.bool)
        self.employee._is_automated = np.zeros((2,), dtype=np.bool)
        self.employee.gain_knowledge()

        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 0.0)

    def test_gain_knowledge_learning(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=1.0)

        self.employee._auto_mask = np.zeros((2,), dtype=np.bool)
        self.employee._auto_mask[1] = np.True_
        self.employee._manual_mask = np.ones((2,), dtype=np.bool)
        self.employee._is_automated = np.zeros((2,), dtype=np.bool)
        self.employee.gain_knowledge()

        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 0.2)

    @patch("ml_models.simulation.agent.np.random.poisson", return_value=7)
    def test_step_all_manual(self, mock_poisson):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=1.0)

        self.employee.step()

        self.assertEqual(self.employee.time_to_complete, 1.0)
        self.assertEqual(self.employee.time_to_complete_unit_work, 1.0)

        self.assertEqual(self.employee.time_savings, 0.0)
        self.assertEqual(self.employee.unused_output_capacity, 0.0)

        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 0.2)

    def test_step_half_manual(self):
        model = Mock()
        model.responsibilities_from_roles = MagicMock(return_value=self.workloads)
        self.employee = Employee(model=model, role="Engineer", automation_incentive=1.0)
        self.employee._workload_knowledge[1] = 1.0
        self.employee.step()

        self.assertEqual(self.employee.time_to_complete, 0.5)
        self.assertEqual(self.employee.time_to_complete_unit_work, 0.5)

        self.assertEqual(self.employee.time_savings, 0.5)
        self.assertEqual(self.employee.unused_output_capacity, 1.0)

        self.assertEqual(self.employee._workload_knowledge[0], 0.0)
        self.assertEqual(self.employee._workload_knowledge[1], 1.0)
