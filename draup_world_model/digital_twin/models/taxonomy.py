"""
Taxonomy data models.

6-level organizational hierarchy:
Organization -> Function -> SubFunction -> JobFamilyGroup -> JobFamily

This is the structural skeleton of the Digital Twin.
Each level serves a specific simulation purpose (see docs).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Organization:
    """Root node - the enterprise itself."""
    id: str
    name: str
    industry: str
    sub_industry: str
    size: int
    revenue_millions: int
    hq_location: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Organization":
        return cls(**data)


@dataclass
class Function:
    """Level 1 - Major business functions (e.g., Claims, Underwriting)."""
    id: str
    name: str
    org_id: str
    description: str = ""
    headcount: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Function":
        return cls(**data)


@dataclass
class SubFunction:
    """Level 2 - Divisions within functions (e.g., Claims Processing, Claims Investigation)."""
    id: str
    name: str
    function_id: str
    description: str = ""
    headcount: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubFunction":
        return cls(**data)


@dataclass
class JobFamilyGroup:
    """Level 3 - Groups of related job families (e.g., Claims Operations)."""
    id: str
    name: str
    sub_function_id: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobFamilyGroup":
        return cls(**data)


@dataclass
class JobFamily:
    """Level 4 - The atomic twin unit. A coherent group of roles (e.g., Claims Adjusters)."""
    id: str
    name: str
    job_family_group_id: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobFamily":
        return cls(**data)
