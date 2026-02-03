import os
import asyncio
from typing import List, Optional, Tuple, Dict

from mesa.batchrunner import batch_run
from pandas import DataFrame

from .role_lookup import DEFAULT_ROLES
from .role_provider import RoleDataProvider, Workload
from .role_provider import InMemoryRoleDataProvider
from .model import (
    EmployeeGroupProfile,
    AutomationImpactOrganizationModel,
)


class SimulationEngine:
    def __init__(
        self,
        role_provider: Optional[RoleDataProvider] = None,
        number_of_months: int = 120,
    ):
        """Initialize the simulation engine"""
        self.n_months: int = number_of_months
        self.role_provider: RoleDataProvider
        if role_provider is None:
            self.role_provider = InMemoryRoleDataProvider(DEFAULT_ROLES)
        else:
            self.role_provider = role_provider

    def update_role_provider(self, role_provider: RoleDataProvider):
        self.role_provider = role_provider

    def run_single_simulation(
        self,
        role_groups: List[EmployeeGroupProfile],
        company: str = "",
        automation_factor: float = 0.2,
    ) -> Tuple[DataFrame, List[Dict[str, str | List[Workload]]]]:
        assert self.role_provider is not None
        role_workload_map: List[Dict[str, str | List[Workload]]] = [
            {
                "role": group["role"],
                "workloads": self.role_provider.get_responsibilities_from_role(
                    group["role"], company
                ),
            }
            for group in role_groups
        ]

        model = AutomationImpactOrganizationModel(
            company=company,
            role_groups=role_groups,
            role_provider=self.role_provider,
            automation_factor=automation_factor,
        )

        for _ in range(self.n_months):
            model.step()

        results = model.datacollector.get_model_vars_dataframe()
        return results, role_workload_map

    def get_role_workload_map(
        self, role_groups: List[EmployeeGroupProfile], company: str = ""
    ) -> List[Dict[str, str | List[Workload]]]:
        role_workload_map: List[Dict[str, str | List[Workload]]] = [
            {
                "role": group["role"],
                "workloads": self.role_provider.get_responsibilities_from_role(
                    group["role"], company
                ),
            }
            for group in role_groups
        ]
        return role_workload_map

    async def get_role_workload_map_async(
        self, role_groups: List[EmployeeGroupProfile], company: str = ""
    ) -> List[Dict[str, str | List[Workload]]]:
        role_workload_map: List[Dict[str, str | List[Workload]]] = []

        tasks = [
            self.role_provider.get_responsibilities_from_role_async(group["role"], company)
            for group in role_groups
        ]
        results = await asyncio.gather(*tasks)
        role_workload_map = [
            {
                "role": role_groups[i]["role"],
                "workloads": results[i],
            }
            for i in range(len(role_groups))
        ]
        return role_workload_map

    def run_multiple_simulations(
        self,
        role_groups: List[EmployeeGroupProfile],
        company: str = "",
        automation_factor: float = 0.2,
        n_simulations: int = 10,
        data_collection_period: int = 1,
    ) -> Tuple[DataFrame]:
        role_workload_map = {
            company: {
                group["role"]: self.role_provider.get_responsibilities_from_role(
                    group["role"], company
                )
                for group in role_groups
            }
        }
        local_role_provider = InMemoryRoleDataProvider(role_workload_map)
        fixed_params = {
            "role_groups": [role_groups],
            "role_provider": local_role_provider,
            "automation_factor": automation_factor,
            "company": company,
        }

        # Use all available CPU cores for parallel processing
        num_processes = min(n_simulations, os.cpu_count() or 1)

        results = batch_run(
            AutomationImpactOrganizationModel,
            parameters=fixed_params,
            iterations=n_simulations,
            max_steps=self.n_months,
            data_collection_period=data_collection_period,
            display_progress=False,
            number_processes=num_processes,
        )

        results = DataFrame(results)
        return results


# Module-level singleton instance
_engine_instance: Optional[SimulationEngine] = None


def get_simulation_engine(role_provider: str = "local") -> SimulationEngine:
    """
    TODO: Adding the logic of choosing different role provider based on the initial setup
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SimulationEngine()
    return _engine_instance
