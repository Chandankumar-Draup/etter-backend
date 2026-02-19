"""
Capability data models.

Skill: A competency required by roles and tasks.
Technology: A tool or platform used to perform tasks.

These are shared catalogs - many roles reference the same skill/tech entities.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Skill:
    """A workforce skill/competency."""
    id: str
    name: str
    category: str  # technical, analytical, domain, leadership, communication, digital, regulatory
    skill_type: str = "core"  # core or soft
    lifecycle_status: str = "stable"  # emerging, growing, stable, declining
    description: str = ""
    market_demand_trend: str = "stable"  # rising, stable, falling

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(**data)


@dataclass
class Technology:
    """A technology tool or platform."""
    id: str
    name: str
    category: str  # ai_ml, automation_rpa, analytics_bi, etc.
    vendor: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    license_cost_tier: str = "medium"  # low, medium, high, enterprise
    adoption_stage: str = "mainstream"  # emerging, early_adopter, mainstream, mature, legacy

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Technology":
        return cls(**data)
