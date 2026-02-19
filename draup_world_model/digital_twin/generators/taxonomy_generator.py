"""
Taxonomy generator for Acme Corporation (Insurance).

The taxonomy is the structural skeleton - defined by domain expertise,
not LLM generation. This ensures consistency and alignment with the
6-level hierarchy from the design docs.

Organization -> Function -> SubFunction -> JobFamilyGroup -> JobFamily
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from draup_world_model.digital_twin.config import CompanyProfile, OutputConfig
from draup_world_model.digital_twin.generators.base_generator import BaseGenerator
from draup_world_model.digital_twin.models.taxonomy import (
    Organization,
    Function,
    SubFunction,
    JobFamilyGroup,
    JobFamily,
)

logger = logging.getLogger(__name__)


# Insurance company taxonomy seed data.
# Structure: {function_name: (headcount, {subfunc: {jfg: [job_families]}})}
ACME_TAXONOMY: Dict[str, Tuple[int, Dict[str, Dict[str, List[str]]]]] = {
    "Claims Management": (2500, {
        "Claims Processing": {
            "Claims Operations": [
                "Claims Adjusters",
                "Claims Examiners",
                "Claims Support Specialists",
            ],
            "Claims Intake": [
                "Claims Intake Coordinators",
                "First Notice of Loss Agents",
            ],
        },
        "Claims Investigation": {
            "Special Investigations": [
                "Fraud Investigators",
                "Claims Analysts",
            ],
            "Subrogation": [
                "Subrogation Specialists",
                "Recovery Analysts",
            ],
        },
        "Claims Leadership": {
            "Claims Management": [
                "Claims Team Leads",
                "Claims Operations Managers",
            ],
        },
    }),
    "Underwriting": (1500, {
        "Risk Assessment": {
            "Risk Analysis": [
                "Risk Analysts",
                "Pricing Analysts",
            ],
            "Risk Engineering": [
                "Loss Control Engineers",
                "Risk Surveyors",
            ],
        },
        "Policy Underwriting": {
            "Commercial Underwriting": [
                "Commercial Lines Underwriters",
                "Specialty Lines Underwriters",
            ],
            "Personal Underwriting": [
                "Personal Lines Underwriters",
                "Auto Insurance Underwriters",
            ],
        },
        "Reinsurance": {
            "Reinsurance Operations": [
                "Reinsurance Analysts",
                "Treaty Underwriters",
            ],
        },
    }),
    "Actuarial and Analytics": (800, {
        "Actuarial Science": {
            "Pricing Actuarial": [
                "Pricing Actuaries",
                "Product Actuaries",
            ],
            "Reserving": [
                "Reserving Actuaries",
                "Loss Reserve Analysts",
            ],
        },
        "Data Analytics": {
            "Business Intelligence": [
                "BI Analysts",
                "Data Visualization Specialists",
            ],
            "Predictive Analytics": [
                "Data Scientists",
                "Predictive Modelers",
            ],
        },
    }),
    "Sales and Distribution": (2000, {
        "Agency Management": {
            "Agent Relations": [
                "Agency Managers",
                "Agent Support Specialists",
            ],
            "Agency Operations": [
                "Agency Coordinators",
                "Commission Analysts",
            ],
        },
        "Direct Sales": {
            "Inside Sales": [
                "Sales Representatives",
                "Sales Account Executives",
            ],
            "Enterprise Sales": [
                "Enterprise Account Managers",
                "Key Account Executives",
            ],
        },
        "Digital Sales": {
            "Digital Distribution": [
                "Digital Sales Specialists",
                "E-Commerce Analysts",
            ],
        },
    }),
    "Policy Administration": (1200, {
        "Policy Servicing": {
            "Policy Operations": [
                "Policy Administrators",
                "Policy Change Processors",
            ],
            "Policy Issuance": [
                "Policy Issuance Specialists",
                "Document Specialists",
            ],
        },
        "Billing and Collections": {
            "Premium Billing": [
                "Billing Specialists",
                "Premium Auditors",
            ],
            "Collections": [
                "Collections Specialists",
                "Accounts Receivable Analysts",
            ],
        },
    }),
    "Customer Service": (2000, {
        "Contact Center": {
            "Customer Support": [
                "Customer Service Representatives",
                "Senior Service Advisors",
            ],
            "Technical Support": [
                "Technical Support Analysts",
                "Escalation Specialists",
            ],
        },
        "Customer Experience": {
            "CX Strategy": [
                "Customer Experience Analysts",
                "Voice of Customer Specialists",
            ],
            "Quality Assurance": [
                "Quality Analysts",
                "Training Specialists",
            ],
        },
    }),
    "Information Technology": (1500, {
        "Application Development": {
            "Software Engineering": [
                "Software Engineers",
                "Full Stack Developers",
            ],
            "Quality Assurance": [
                "QA Engineers",
                "Test Automation Engineers",
            ],
        },
        "Infrastructure and Cloud": {
            "Cloud Operations": [
                "Cloud Engineers",
                "DevOps Engineers",
            ],
            "Network and Security": [
                "Network Engineers",
                "Cybersecurity Analysts",
            ],
        },
        "Data Engineering": {
            "Data Platform": [
                "Data Engineers",
                "Database Administrators",
            ],
            "AI and ML Engineering": [
                "ML Engineers",
                "AI Solutions Architects",
            ],
        },
        "IT Operations": {
            "Service Desk": [
                "IT Support Specialists",
                "Systems Administrators",
            ],
            "IT Project Management": [
                "IT Project Managers",
                "Scrum Masters",
            ],
        },
    }),
    "Finance and Accounting": (1000, {
        "Financial Planning": {
            "FP&A": [
                "Financial Analysts",
                "Budget Analysts",
            ],
            "Investment Management": [
                "Investment Analysts",
                "Portfolio Managers",
            ],
        },
        "Accounting": {
            "General Accounting": [
                "Accountants",
                "Accounts Payable Specialists",
            ],
            "Financial Reporting": [
                "Financial Reporting Analysts",
                "Regulatory Reporting Specialists",
            ],
        },
        "Treasury": {
            "Treasury Operations": [
                "Treasury Analysts",
                "Cash Management Specialists",
            ],
        },
    }),
    "Legal and Compliance": (600, {
        "Legal": {
            "Corporate Legal": [
                "Corporate Attorneys",
                "Contract Specialists",
            ],
            "Claims Legal": [
                "Litigation Attorneys",
                "Legal Assistants",
            ],
        },
        "Regulatory Compliance": {
            "Compliance Operations": [
                "Compliance Analysts",
                "Regulatory Affairs Specialists",
            ],
            "Audit": [
                "Internal Auditors",
                "Compliance Auditors",
            ],
        },
    }),
    "Human Resources": (500, {
        "Talent Acquisition": {
            "Recruiting": [
                "Recruiters",
                "Talent Sourcing Specialists",
            ],
        },
        "Learning and Development": {
            "Training": [
                "Learning Designers",
                "Training Coordinators",
            ],
        },
        "HR Operations": {
            "HR Services": [
                "HR Generalists",
                "HRIS Analysts",
            ],
            "Compensation and Benefits": [
                "Compensation Analysts",
                "Benefits Administrators",
            ],
        },
    }),
    "Marketing and Communications": (400, {
        "Brand Marketing": {
            "Brand Strategy": [
                "Brand Managers",
                "Creative Specialists",
            ],
        },
        "Digital Marketing": {
            "Online Marketing": [
                "Digital Marketing Specialists",
                "SEO SEM Analysts",
            ],
            "Content and Social": [
                "Content Strategists",
                "Social Media Managers",
            ],
        },
        "Product Marketing": {
            "Insurance Product Marketing": [
                "Product Marketing Managers",
                "Market Research Analysts",
            ],
        },
    }),
    "Operations and Strategy": (1000, {
        "Business Operations": {
            "Process Improvement": [
                "Business Process Analysts",
                "Lean Six Sigma Specialists",
            ],
            "Vendor Management": [
                "Vendor Managers",
                "Procurement Specialists",
            ],
        },
        "Corporate Strategy": {
            "Strategy and Planning": [
                "Strategy Analysts",
                "Business Planners",
            ],
        },
        "Risk Management": {
            "Enterprise Risk": [
                "Enterprise Risk Analysts",
                "Operational Risk Managers",
            ],
        },
    }),
}


class TaxonomyGenerator(BaseGenerator):
    """Generates the organizational taxonomy from seed data."""

    def __init__(self, company: CompanyProfile = None, output: OutputConfig = None):
        super().__init__()
        self.company = company or CompanyProfile()
        self.output = output or OutputConfig()

    def generate(self) -> Dict:
        """Generate the full taxonomy and save to JSON."""
        logger.info(f"Generating taxonomy for {self.company.name}")
        self.output.ensure_dirs()

        org = Organization(
            id=self.make_id(self.company.name),
            name=self.company.name,
            industry=self.company.industry,
            sub_industry=self.company.sub_industry,
            size=self.company.size,
            revenue_millions=self.company.revenue_millions,
            hq_location=self.company.hq_location,
            description=self.company.description,
        )

        functions = []
        sub_functions = []
        job_family_groups = []
        job_families = []

        for func_name, (headcount, subfuncs) in ACME_TAXONOMY.items():
            func_id = self.make_id("func", func_name)
            functions.append(Function(
                id=func_id,
                name=func_name,
                org_id=org.id,
                headcount=headcount,
            ))

            for sf_name, jfgs in subfuncs.items():
                sf_id = self.make_id("sf", func_name, sf_name)
                sub_functions.append(SubFunction(
                    id=sf_id,
                    name=sf_name,
                    function_id=func_id,
                ))

                for jfg_name, jf_list in jfgs.items():
                    jfg_id = self.make_id("jfg", func_name, jfg_name)
                    job_family_groups.append(JobFamilyGroup(
                        id=jfg_id,
                        name=jfg_name,
                        sub_function_id=sf_id,
                    ))

                    for jf_name in jf_list:
                        jf_id = self.make_id("jf", jf_name)
                        job_families.append(JobFamily(
                            id=jf_id,
                            name=jf_name,
                            job_family_group_id=jfg_id,
                        ))

        taxonomy_data = {
            "organization": org.to_dict(),
            "functions": [f.to_dict() for f in functions],
            "sub_functions": [sf.to_dict() for sf in sub_functions],
            "job_family_groups": [jfg.to_dict() for jfg in job_family_groups],
            "job_families": [jf.to_dict() for jf in job_families],
        }

        self.save_json(taxonomy_data, self.output.taxonomy_file)

        logger.info(
            f"Taxonomy generated: {len(functions)} functions, "
            f"{len(sub_functions)} sub-functions, "
            f"{len(job_family_groups)} job family groups, "
            f"{len(job_families)} job families"
        )
        return taxonomy_data
