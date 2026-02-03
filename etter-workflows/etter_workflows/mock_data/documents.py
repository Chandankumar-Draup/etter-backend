"""
Document Provider for Etter Workflows.

Provides document data (JDs, process maps) for role processing.
Currently uses mock data, extensible to real document storage.

Document Types:
- Job Descriptions (JD): Primary input for AI Assessment
- Process Maps: Extended input for process analysis (future)

This module provides:
1. Abstract DocumentProvider interface
2. MockDocumentProvider for development/testing
3. Factory function to get the appropriate provider
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from etter_workflows.models.inputs import DocumentRef, DocumentType
from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class DocumentProvider(ABC):
    """
    Abstract interface for document data providers.

    Implementations can provide documents from:
    - Mock data (development/testing)
    - S3/Blob storage (production)
    - File system (batch processing)
    """

    @abstractmethod
    def get_document(
        self,
        company_name: str,
        role_name: str,
        doc_type: DocumentType,
    ) -> Optional[DocumentRef]:
        """
        Get a document for a role.

        Args:
            company_name: Company name
            role_name: Role name
            doc_type: Type of document

        Returns:
            DocumentRef or None
        """
        pass

    @abstractmethod
    def get_documents_for_role(
        self,
        company_name: str,
        role_name: str,
    ) -> List[DocumentRef]:
        """
        Get all documents for a role.

        Args:
            company_name: Company name
            role_name: Role name

        Returns:
            List of DocumentRef
        """
        pass

    @abstractmethod
    def get_document_content(
        self,
        doc_ref: DocumentRef,
    ) -> Optional[str]:
        """
        Get the content of a document.

        Args:
            doc_ref: Document reference

        Returns:
            Document content string or None
        """
        pass


class MockDocumentProvider(DocumentProvider):
    """
    Mock implementation of DocumentProvider.

    Provides sample document data for development and testing.
    Documents are stored in memory with inline content.
    """

    def __init__(self):
        """Initialize with sample data."""
        # Structure: {company: {role: [DocumentRef, ...]}}
        self._documents: Dict[str, Dict[str, List[DocumentRef]]] = {}
        self._populate_sample_data()

    def _populate_sample_data(self):
        """Populate with sample document data."""

        # Sample JDs for testing
        sample_jds = {
            "Liberty Mutual": {
                "Claims Adjuster": """
# Claims Adjuster

## Overview
The Claims Adjuster investigates insurance claims by interviewing claimants,
witnesses, and experts. They review policy terms, analyze damages, and
determine the extent of the insurance company's liability.

## Key Responsibilities

### Claims Investigation
- Conduct thorough investigations of insurance claims
- Interview claimants, witnesses, and experts
- Gather and analyze evidence related to claims
- Review police reports and medical records

### Policy Analysis
- Review and interpret policy terms and coverage
- Determine applicability of policy provisions
- Identify potential coverage issues or exclusions
- Ensure compliance with regulatory requirements

### Settlement Processing
- Evaluate and calculate claim values
- Negotiate settlements with claimants and attorneys
- Prepare settlement documentation
- Process claim payments accurately

### Documentation & Reporting
- Maintain detailed claim files and documentation
- Prepare comprehensive claim reports
- Document all communications and decisions
- Ensure data accuracy in claims management systems

## Requirements

### Education
- Bachelor's degree in Business, Finance, or related field

### Experience
- 2-5 years experience in insurance claims processing
- Experience with property and casualty claims preferred

### Skills
- Strong analytical and problem-solving abilities
- Excellent communication and negotiation skills
- Attention to detail and accuracy
- Proficiency in claims management software
- Knowledge of insurance regulations and policies

## Working Conditions
- Office-based with occasional field investigations
- Standard business hours with some flexibility
- May require travel for complex claims
                """,
                "Underwriter": """
# Senior Underwriter

## Overview
The Senior Underwriter evaluates insurance applications and determines
coverage amounts and premiums based on risk assessment.

## Key Responsibilities

### Risk Evaluation
- Analyze insurance applications and supporting documentation
- Evaluate risk factors including loss history and financial stability
- Make informed decisions on policy acceptance or rejection
- Determine appropriate coverage limits and deductibles

### Premium Calculation
- Calculate premiums based on risk assessment
- Apply pricing guidelines and rating methodologies
- Ensure competitive and profitable pricing
- Review and approve complex premium calculations

### Relationship Management
- Collaborate with agents and brokers on submissions
- Provide guidance on coverage and underwriting requirements
- Build and maintain productive business relationships
- Support new business development initiatives

## Requirements
- Bachelor's degree in Business, Finance, or related field
- 5+ years underwriting experience
- Professional certifications (CPCU, AU) preferred
- Strong analytical and decision-making skills
                """,
            },
            "Walmart Inc.": {
                "Store Manager": """
# Store Manager

## Overview
The Store Manager oversees all aspects of store operations including sales,
customer service, inventory management, and team leadership.

## Key Responsibilities

### Operations Management
- Manage daily store operations and workflows
- Ensure store meets sales and profit objectives
- Maintain inventory accuracy and stock levels
- Implement merchandising strategies and planograms

### Team Leadership
- Recruit, train, and develop store associates
- Conduct performance evaluations and coaching
- Create work schedules and manage labor costs
- Foster a positive and productive work environment

### Customer Experience
- Ensure exceptional customer service standards
- Resolve customer complaints and issues
- Monitor customer satisfaction metrics
- Implement customer engagement initiatives

### Financial Management
- Manage store budget and expenses
- Analyze sales reports and KPIs
- Implement loss prevention strategies
- Achieve financial targets and goals

## Requirements
- Bachelor's degree in Business or related field preferred
- 5+ years retail management experience
- Proven track record of achieving sales goals
- Strong leadership and communication skills
                """,
                "Software Development Engineer": """
# Software Development Engineer

## Overview
Design, develop, and maintain software applications that power retail
operations and e-commerce platforms at scale.

## Key Responsibilities

### Software Development
- Design and implement software solutions using modern technologies
- Write clean, maintainable, and well-documented code
- Develop RESTful APIs and microservices
- Build responsive web and mobile applications

### Technical Excellence
- Participate in code reviews and technical discussions
- Write unit and integration tests
- Troubleshoot and debug complex issues
- Optimize application performance

### Collaboration
- Work with product managers to define requirements
- Collaborate with UX designers on user experience
- Partner with DevOps for deployment and monitoring
- Mentor junior developers

### Innovation
- Research and evaluate new technologies
- Propose technical improvements
- Contribute to architecture decisions
- Stay current with industry trends

## Requirements
- Bachelor's degree in Computer Science or related field
- 3+ years software development experience
- Proficiency in Java, Python, or JavaScript
- Experience with cloud platforms (AWS, Azure, GCP)
- Familiarity with agile development practices
                """,
            },
            "Acme Corporation": {
                "Product Manager": """
# Senior Product Manager

## Overview
Lead product strategy and roadmap development, working closely with
engineering, design, and marketing teams to deliver successful products.

## Key Responsibilities

### Strategy & Vision
- Define product vision, strategy, and roadmap
- Conduct market research and competitive analysis
- Identify opportunities for growth and innovation
- Align product direction with business objectives

### Product Development
- Gather and prioritize product requirements
- Create detailed product specifications
- Work with engineering on technical feasibility
- Manage product backlog and sprint planning

### Go-to-Market
- Coordinate product launches with marketing
- Develop positioning and messaging
- Train sales teams on product features
- Gather customer feedback and iterate

### Analytics
- Define and track product metrics
- Analyze user behavior and feedback
- Make data-driven product decisions
- Report on product performance

## Requirements
- Bachelor's degree in Business or technical field
- 5+ years product management experience
- Strong analytical and communication skills
- Experience with agile methodologies
                """,
                "Data Scientist": """
# Data Scientist

## Overview
Develop machine learning models and perform advanced analytics to drive
business insights and decision-making.

## Key Responsibilities

### Machine Learning
- Build and deploy predictive models
- Develop recommendation systems
- Implement natural language processing solutions
- Optimize model performance and accuracy

### Data Analysis
- Perform exploratory data analysis
- Create data visualizations and dashboards
- Conduct A/B tests and experiments
- Generate insights from complex datasets

### Collaboration
- Partner with business stakeholders
- Translate business problems into data solutions
- Present findings to technical and non-technical audiences
- Work with engineering on data pipelines

### Research
- Stay current with ML research and techniques
- Evaluate new tools and technologies
- Document methodologies and best practices
- Contribute to internal knowledge sharing

## Requirements
- Master's degree in Data Science, Statistics, or related field
- 3+ years data science experience
- Proficiency in Python, SQL, and ML frameworks
- Experience with cloud ML platforms
                """,
            },
        }

        # Convert to DocumentRef objects
        for company, roles in sample_jds.items():
            self._documents[company] = {}
            for role_name, jd_content in roles.items():
                doc = DocumentRef(
                    type=DocumentType.JOB_DESCRIPTION,
                    name=f"{role_name} - Job Description",
                    content=jd_content.strip(),
                    metadata={
                        "company": company,
                        "role": role_name,
                        "source": "mock_data",
                    },
                )
                self._documents[company][role_name] = [doc]

    def get_document(
        self,
        company_name: str,
        role_name: str,
        doc_type: DocumentType,
    ) -> Optional[DocumentRef]:
        """Get a document for a role."""
        docs = self.get_documents_for_role(company_name, role_name)
        for doc in docs:
            if doc.type == doc_type:
                return doc
        return None

    def get_documents_for_role(
        self,
        company_name: str,
        role_name: str,
    ) -> List[DocumentRef]:
        """Get all documents for a role."""
        company_docs = self._documents.get(company_name, {})
        return company_docs.get(role_name, [])

    def get_document_content(
        self,
        doc_ref: DocumentRef,
    ) -> Optional[str]:
        """Get the content of a document."""
        if doc_ref.content:
            return doc_ref.content

        if doc_ref.uri:
            # TODO: Implement URI-based content retrieval
            logger.warning(f"URI-based content retrieval not implemented: {doc_ref.uri}")
            return None

        return None

    def add_document(
        self,
        company_name: str,
        role_name: str,
        document: DocumentRef,
    ) -> None:
        """Add a document (for testing)."""
        if company_name not in self._documents:
            self._documents[company_name] = {}
        if role_name not in self._documents[company_name]:
            self._documents[company_name][role_name] = []
        self._documents[company_name][role_name].append(document)

    def get_companies(self) -> List[str]:
        """Get list of companies with documents."""
        return list(self._documents.keys())


# Singleton provider instance
_document_provider: Optional[DocumentProvider] = None


def get_document_provider() -> DocumentProvider:
    """
    Get the document provider.

    Returns MockDocumentProvider when enable_mock_data is True,
    otherwise would return a real storage provider (to be implemented).

    Returns:
        DocumentProvider instance
    """
    global _document_provider
    if _document_provider is None:
        settings = get_settings()
        if settings.enable_mock_data:
            _document_provider = MockDocumentProvider()
            logger.info("Using MockDocumentProvider")
        else:
            # TODO: Implement real storage provider (S3, etc.)
            logger.warning("Real storage provider not implemented, using mock")
            _document_provider = MockDocumentProvider()

    return _document_provider


def reset_document_provider():
    """Reset the singleton provider (for testing)."""
    global _document_provider
    _document_provider = None
