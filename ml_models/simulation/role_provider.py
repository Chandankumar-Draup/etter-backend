from abc import ABC, abstractmethod
from typing import List, TypedDict, Dict, cast


class Workload(TypedDict):
    Name: str
    Type: str
    Skill: float
    Time: float
    Reason: str


class RoleDataProvider(ABC):
    @abstractmethod
    def get_responsibilities_from_role(self, role: str, company: str = "") -> List[Workload]:
        pass

    async def get_responsibilities_from_role_async(self, role: str, company: str = "") -> List[Workload]:
        return self.get_responsibilities_from_role(role, company)


class InMemoryRoleDataProvider(RoleDataProvider):
    def __init__(self, role_data: Dict[str, Dict[str, List[Workload]]]) -> None:
        """Initialize the in-memory role data provider"""
        self.role_data = role_data
        self.default = cast(Dict[str, List[Workload]], role_data.get("DEFAULT"))

    def get_responsibilities_from_role(self, role: str, company: str = "") -> List[Workload]:
        """Return a list of workload based on the role and company"""
        if company in self.role_data:
            roles_table = cast(Dict[str, List[Workload]], self.role_data.get(company))
        else:
            roles_table = self.default

        if role in roles_table:
            result = cast(List[Workload], roles_table.get(role))
        else:
            result = cast(List[Workload], roles_table.get("DEFAULT"))

        # Ensure we always return a list, never None
        return result if result is not None else []
