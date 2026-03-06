"""
Workforce data models.

Role: The assessment unit - what a person does.
JobTitle: Career-banded positions within a role.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Role:
    """A job role within a job family. The core entity for simulation."""
    id: str
    name: str
    job_family_id: str
    description: str = ""
    total_headcount: int = 0
    avg_salary: int = 0
    automation_score: float = 0.0  # 0-100, overall AI automation potential
    skill_ids: List[str] = field(default_factory=list)
    technology_ids: List[str] = field(default_factory=list)
    adjacency_role_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        return cls(**data)


@dataclass
class JobTitle:
    """A specific job title within a role, with career band."""
    id: str
    name: str
    role_id: str
    career_band: str  # entry, mid, senior, lead, principal, director, vp
    level: int = 0  # numeric level within the band
    typical_experience_years: int = 0
    headcount: int = 0
    avg_salary: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobTitle":
        return cls(**data)
