"""
Role Taxonomy Provider for Etter Workflows.

Provides role taxonomy data in the format expected by the platform API.
Based on the format from push_to_platform.py:

API Format:
{
    "job_id": "1",
    "job_role": "Data Engineer",
    "job_title": "Data Engineer",
    "occupation": "Software and Mathematics",
    "job_family": "Database and systems administrators",
    "draup_role": "Data Engineer",
    "general_summary": "...",
    "source": "etter",
    "status": "pending"
}

This module provides:
1. Abstract RoleTaxonomyProvider interface
2. MockRoleTaxonomyProvider for development/testing
3. Factory function to get the appropriate provider
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from etter_workflows.models.inputs import RoleTaxonomyEntry
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class RoleTaxonomyProvider(ABC):
    """
    Abstract interface for role taxonomy data providers.

    Implementations can provide data from:
    - Mock data (development/testing)
    - Platform API (production)
    - File-based data (batch processing)
    """

    @abstractmethod
    def get_roles_for_company(
        self,
        company_name: str,
        status_filter: Optional[str] = None,
    ) -> List[RoleTaxonomyEntry]:
        """
        Get all roles for a company.

        Args:
            company_name: Company name
            status_filter: Optional status filter (pending, approved, rejected)

        Returns:
            List of RoleTaxonomyEntry
        """
        pass

    @abstractmethod
    def get_role(
        self,
        company_name: str,
        job_title: str,
    ) -> Optional[RoleTaxonomyEntry]:
        """
        Get a specific role by company and job title.

        Args:
            company_name: Company name
            job_title: Job title

        Returns:
            RoleTaxonomyEntry or None
        """
        pass

    @abstractmethod
    def get_role_by_id(self, job_id: str) -> Optional[RoleTaxonomyEntry]:
        """
        Get a role by its job ID.

        Args:
            job_id: Job ID

        Returns:
            RoleTaxonomyEntry or None
        """
        pass


class MockRoleTaxonomyProvider(RoleTaxonomyProvider):
    """
    Mock implementation of RoleTaxonomyProvider.

    Provides sample role data for development and testing.
    Data format mirrors the platform API as used in push_to_platform.py.
    """

    def __init__(self):
        """Initialize with sample data."""
        self._data: Dict[str, Dict[str, RoleTaxonomyEntry]] = {}
        self._populate_sample_data()

    def _populate_sample_data(self):
        """Populate with sample role data for testing."""

        # Sample companies with roles
        sample_data = {
            "Liberty Mutual": [
                {
                    "job_id": "lm-001",
                    "job_role": "Claims Adjuster",
                    "job_title": "Claims Adjuster",
                    "occupation": "Business and Finance",
                    "job_family": "Claims Adjusters, Examiners, and Investigators",
                    "draup_role": "Claims Adjuster",
                    "general_summary": """
                        The Claims Adjuster investigates insurance claims by interviewing
                        claimants, witnesses, and experts. They review policy terms,
                        analyze damages, and determine the extent of the insurance
                        company's liability. Key responsibilities include:

                        **Responsibilities:**
                        - Investigate insurance claims through interviews and research
                        - Review and analyze policy terms and coverage
                        - Assess property damage and personal injury claims
                        - Negotiate settlements with claimants
                        - Prepare detailed claim reports and documentation
                        - Coordinate with legal counsel on disputed claims

                        **Requirements:**
                        - Bachelor's degree in Business, Finance, or related field
                        - 2-5 years experience in insurance claims
                        - Strong analytical and negotiation skills
                        - Knowledge of insurance regulations and policies
                    """,
                    "status": "pending",
                },
                {
                    "job_id": "lm-002",
                    "job_role": "Underwriter",
                    "job_title": "Senior Underwriter",
                    "occupation": "Business and Finance",
                    "job_family": "Insurance Underwriters",
                    "draup_role": "Underwriter",
                    "general_summary": """
                        The Senior Underwriter evaluates insurance applications and
                        determines coverage amounts and premiums. They assess risk
                        factors and make decisions on policy acceptance.

                        **Responsibilities:**
                        - Review and analyze insurance applications
                        - Evaluate risk factors and determine premiums
                        - Make decisions on policy acceptance or rejection
                        - Collaborate with agents and brokers
                        - Maintain compliance with underwriting guidelines

                        **Requirements:**
                        - Bachelor's degree in Business, Finance, or related field
                        - 5+ years underwriting experience
                        - Strong analytical and decision-making skills
                    """,
                    "status": "pending",
                },
                {
                    "job_id": "lm-003",
                    "job_role": "Risk Analyst",
                    "job_title": "Risk Analyst",
                    "occupation": "Business and Finance",
                    "job_family": "Financial Analysts",
                    "draup_role": "Risk Analyst",
                    "general_summary": """
                        The Risk Analyst identifies and analyzes potential risks that
                        could threaten the organization's capital or earnings.

                        **Responsibilities:**
                        - Analyze risk data and market trends
                        - Develop risk assessment models
                        - Prepare risk reports for management
                        - Recommend risk mitigation strategies

                        **Requirements:**
                        - Bachelor's degree in Finance, Mathematics, or Statistics
                        - 3+ years experience in risk analysis
                        - Proficiency in statistical software
                    """,
                    "status": "pending",
                },
            ],
            "Walmart Inc.": [
                {
                    "job_id": "wm-001",
                    "job_role": "Store Manager",
                    "job_title": "Store Manager",
                    "occupation": "Management",
                    "job_family": "General and Operations Managers",
                    "draup_role": "Store Manager",
                    "general_summary": """
                        The Store Manager oversees all store operations including
                        sales, customer service, inventory management, and staff
                        supervision.

                        **Responsibilities:**
                        - Manage daily store operations
                        - Lead and develop store team
                        - Achieve sales and profit goals
                        - Ensure customer satisfaction
                        - Manage inventory and merchandising

                        **Requirements:**
                        - Bachelor's degree preferred
                        - 5+ years retail management experience
                        - Strong leadership and communication skills
                    """,
                    "status": "pending",
                },
                {
                    "job_id": "wm-002",
                    "job_role": "Software Development Engineer",
                    "job_title": "Software Development Engineer",
                    "occupation": "Software and Mathematics",
                    "job_family": "Software Developers",
                    "draup_role": "Software Engineer",
                    "general_summary": """
                        The Software Development Engineer designs, develops, and
                        maintains software applications for retail operations and
                        e-commerce platforms.

                        **Responsibilities:**
                        - Design and implement software solutions
                        - Write clean, maintainable code
                        - Collaborate with cross-functional teams
                        - Participate in code reviews
                        - Troubleshoot and debug applications

                        **Requirements:**
                        - Bachelor's degree in Computer Science or related field
                        - 3+ years software development experience
                        - Proficiency in multiple programming languages
                    """,
                    "status": "pending",
                },
                {
                    "job_id": "wm-003",
                    "job_role": "Supply Chain Analyst",
                    "job_title": "Supply Chain Analyst",
                    "occupation": "Business and Finance",
                    "job_family": "Logisticians",
                    "draup_role": "Supply Chain Analyst",
                    "general_summary": """
                        The Supply Chain Analyst optimizes supply chain operations
                        through data analysis, forecasting, and process improvement.

                        **Responsibilities:**
                        - Analyze supply chain data and metrics
                        - Develop demand forecasts
                        - Identify process improvement opportunities
                        - Coordinate with vendors and logistics partners

                        **Requirements:**
                        - Bachelor's degree in Supply Chain, Business, or related field
                        - 2+ years supply chain experience
                        - Strong analytical skills
                    """,
                    "status": "pending",
                },
            ],
            "Acme Corporation": [
                {
                    "job_id": "acme-001",
                    "job_role": "Product Manager",
                    "job_title": "Senior Product Manager",
                    "occupation": "Management",
                    "job_family": "Marketing Managers",
                    "draup_role": "Product Manager",
                    "general_summary": """
                        The Senior Product Manager leads product strategy and roadmap
                        development, working closely with engineering, design, and
                        marketing teams.

                        **Responsibilities:**
                        - Define product vision and strategy
                        - Manage product roadmap and backlog
                        - Gather and prioritize requirements
                        - Collaborate with cross-functional teams
                        - Analyze market trends and competition

                        **Requirements:**
                        - Bachelor's degree in Business or technical field
                        - 5+ years product management experience
                        - Strong analytical and communication skills
                    """,
                    "status": "pending",
                },
                {
                    "job_id": "acme-002",
                    "job_role": "Data Scientist",
                    "job_title": "Data Scientist",
                    "occupation": "Software and Mathematics",
                    "job_family": "Data Scientists",
                    "draup_role": "Data Scientist",
                    "general_summary": """
                        The Data Scientist develops machine learning models and
                        performs advanced analytics to drive business decisions.

                        **Responsibilities:**
                        - Build and deploy ML models
                        - Perform statistical analysis
                        - Create data visualizations
                        - Collaborate with stakeholders on data needs

                        **Requirements:**
                        - Master's degree in Data Science, Statistics, or related field
                        - 3+ years data science experience
                        - Proficiency in Python, SQL, and ML frameworks
                    """,
                    "status": "pending",
                },
            ],
        }

        # Convert to RoleTaxonomyEntry objects
        for company, roles in sample_data.items():
            self._data[company] = {}
            for role_data in roles:
                entry = RoleTaxonomyEntry(
                    job_id=role_data["job_id"],
                    job_role=role_data["job_role"],
                    job_title=role_data["job_title"],
                    occupation=role_data.get("occupation"),
                    job_family=role_data.get("job_family"),
                    draup_role=role_data.get("draup_role"),
                    general_summary=role_data.get("general_summary", "").strip(),
                    status=role_data.get("status", "pending"),
                )
                self._data[company][role_data["job_title"]] = entry

    def get_roles_for_company(
        self,
        company_name: str,
        status_filter: Optional[str] = None,
    ) -> List[RoleTaxonomyEntry]:
        """Get all roles for a company."""
        company_roles = self._data.get(company_name, {})
        roles = list(company_roles.values())

        if status_filter:
            roles = [r for r in roles if r.status == status_filter]

        return roles

    def get_role(
        self,
        company_name: str,
        job_title: str,
    ) -> Optional[RoleTaxonomyEntry]:
        """Get a specific role by company and job title."""
        company_roles = self._data.get(company_name, {})
        return company_roles.get(job_title)

    def get_role_by_id(self, job_id: str) -> Optional[RoleTaxonomyEntry]:
        """Get a role by its job ID."""
        for company_roles in self._data.values():
            for role in company_roles.values():
                if role.job_id == job_id:
                    return role
        return None

    def add_role(self, company_name: str, entry: RoleTaxonomyEntry) -> None:
        """Add a role to the mock data (for testing)."""
        if company_name not in self._data:
            self._data[company_name] = {}
        self._data[company_name][entry.job_title] = entry

    def get_companies(self) -> List[str]:
        """Get list of companies with roles."""
        return list(self._data.keys())


# Singleton provider instance
_role_taxonomy_provider: Optional[RoleTaxonomyProvider] = None


def get_role_taxonomy_provider() -> RoleTaxonomyProvider:
    """
    Get the role taxonomy provider.

    Returns MockRoleTaxonomyProvider when enable_mock_data is True,
    otherwise would return a real API provider (to be implemented).

    Returns:
        RoleTaxonomyProvider instance
    """
    global _role_taxonomy_provider
    if _role_taxonomy_provider is None:
        settings = get_settings()
        if settings.enable_mock_data:
            _role_taxonomy_provider = MockRoleTaxonomyProvider()
            logger.info("Using MockRoleTaxonomyProvider")
        else:
            # TODO: Implement real API provider
            logger.warning("Real API provider not implemented, using mock")
            _role_taxonomy_provider = MockRoleTaxonomyProvider()

    return _role_taxonomy_provider


def reset_role_taxonomy_provider():
    """Reset the singleton provider (for testing)."""
    global _role_taxonomy_provider
    _role_taxonomy_provider = None
