#!/usr/bin/env python3
"""
===============================================================================
ETTER SELF-SERVICE PIPELINE - DEMO SCRIPT
===============================================================================

This demo script demonstrates the Etter Self-Service Pipeline functionality.
It provides a safe way to test the workflow system before connecting to
production databases.

IMPORTANT - DATABASE IMPACT:
============================
1. MOCK MODE (default, --mock flag):
   - Uses MOCK data providers (no real database connections)
   - Creates MOCK assessment results (random scores)
   - NO changes are made to Neo4j or any database
   - Safe to run repeatedly for testing

2. REAL MODE (--real flag):
   - Connects to the REAL Neo4j database
   - Creates/updates CompanyRole nodes in Neo4j
   - Calls the REAL AI Assessment API
   - WILL make changes to your database
   - Use with caution in production

WHAT THIS DEMO DOES:
====================
1. Lists available test companies and roles (from mock data)
2. Creates a test company and role dynamically
3. Executes the role onboarding workflow:
   a. Role Setup: Creates CompanyRole node (mock or real)
   b. AI Assessment: Runs AI assessment (mock or real)
4. Displays workflow results and assessment scores

BATCH MODE (--batch flag):
==========================
- Submits multiple roles at once using the batch API
- Demonstrates batch status polling and retry functionality
- Creates 3 test roles: 2 with JD, 1 without JD (to show validation)

TESTING RECOMMENDATIONS:
========================
- First, test with --mock to verify the workflow logic works
- Then, test with --dry-run to see what would happen with real connections
- Finally, use --real only when ready for actual database changes

Usage:
    # Safe mock mode (no database changes)
    python demo.py --mock

    # Custom test company (still mock mode)
    python demo.py --company "TestCorp" --role "QA Engineer"

    # Batch mode - submit multiple roles
    python demo.py --batch --company "TestCorp"

    # Real mode (WILL modify database)
    python demo.py --real --company "TestCorp" --role "QA Engineer"

    # Run via Temporal (requires worker running)
    python demo.py --real --temporal --company "TestCorp" --role "QA Engineer"

    # Show verbose output
    python demo.py --mock --verbose

===============================================================================
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import Optional

# ============================================================================
# LOGGING SETUP
# ============================================================================
# Configure logging based on verbosity level
# In verbose mode, we show DEBUG logs from all modules
# In normal mode, we show INFO logs from the demo only

def setup_logging(verbose: bool = False):
    """
    Configure logging for the demo.

    Args:
        verbose: If True, show DEBUG level logs from all modules.
                 If False, only show INFO from demo script.
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from other loggers unless verbose
    if not verbose:
        logging.getLogger("etter_workflows").setLevel(logging.WARNING)
        logging.getLogger("temporalio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ============================================================================
# DISPLAY HELPERS
# ============================================================================
# Helper functions to format output nicely in the terminal

def print_banner():
    """Print welcome banner with important warnings."""
    print("\n" + "=" * 70)
    print("  ETTER SELF-SERVICE PIPELINE DEMO")
    print("  Phase 1: MVP - Role Onboarding + AI Assessment")
    print("=" * 70)
    print()
    print("  [!] This demo helps you understand the workflow system.")
    print("  [!] By default, it runs in MOCK mode (no database changes).")
    print("  [!] Use --real flag only when ready for actual database changes.")
    print()


def print_section(title: str):
    """Print section header."""
    print("\n" + "-" * 60)
    print(f"  {title}")
    print("-" * 60)


def print_mode_warning(use_mock: bool, use_temporal: bool = False):
    """Print warning about current mode."""
    if use_mock:
        print("\n  [MOCK MODE] Using mock data providers. No database changes.")
    else:
        print("\n  [REAL MODE] Using real database connections.")
        print("              Changes WILL be made to Neo4j database!")

    if use_temporal:
        print("\n  [TEMPORAL MODE] Running via Temporal orchestration.")
        print("                  Workflow will be visible in Temporal UI.")
        print("                  Requires: temporal server + etter worker running.")


# ============================================================================
# TEST DATA GENERATION
# ============================================================================
# Functions to create test companies and roles dynamically

def create_test_role_data(company_name: str, role_name: str) -> dict:
    """
    Create test role data with a sample job description.

    This generates realistic-looking test data that can be used
    to test the workflow without needing real company data.

    Args:
        company_name: Name of the test company
        role_name: Name of the test role

    Returns:
        Dictionary with role taxonomy and job description data
    """
    # Generate a unique job ID based on company and role names
    job_id = f"test-{company_name[:4].lower()}-{role_name[:4].lower()}-001"

    # Create a sample job description
    # This format mirrors what real JDs look like in the system
    job_description = f"""
# {role_name}

## Company: {company_name}

## Overview
The {role_name} is responsible for ensuring quality standards are met
across all products and services. This role involves designing test
strategies, executing test plans, and collaborating with development
teams to deliver high-quality software.

## Key Responsibilities

### Test Planning & Design
- Design comprehensive test strategies and plans
- Create test cases covering functional and non-functional requirements
- Develop automated test scripts for regression testing
- Define quality metrics and acceptance criteria

### Test Execution
- Execute manual and automated test cases
- Perform functional, integration, and system testing
- Conduct performance and load testing
- Document and track defects using issue tracking systems

### Quality Assurance
- Review requirements for testability
- Participate in code reviews from a testing perspective
- Monitor and report on quality metrics
- Recommend process improvements

### Collaboration
- Work closely with developers to resolve issues
- Collaborate with product managers on requirements
- Communicate testing status to stakeholders
- Mentor junior team members on testing best practices

## Requirements

### Education
- Bachelor's degree in Computer Science or related field

### Experience
- 3+ years of experience in software testing
- Experience with test automation frameworks
- Familiarity with CI/CD pipelines

### Skills
- Strong analytical and problem-solving skills
- Excellent attention to detail
- Good communication and documentation skills
- Proficiency in Python, Java, or JavaScript for automation
- Experience with Selenium, pytest, or similar tools

## Working Conditions
- Remote-friendly position
- Standard business hours with flexibility
- Occasional on-call support during releases
    """

    # Create role taxonomy entry (mirrors the format from push_to_platform.py)
    role_taxonomy = {
        "job_id": job_id,
        "job_role": role_name,
        "job_title": role_name,
        "occupation": "Software and Mathematics",
        "job_family": "Software Quality Assurance Analysts and Testers",
        "draup_role": role_name,
        "general_summary": f"The {role_name} ensures quality standards across products.",
        "status": "pending",
    }

    return {
        "role_taxonomy": role_taxonomy,
        "job_description": job_description.strip(),
    }


def register_test_data(company_name: str, role_name: str):
    """
    Register test company and role in the mock data providers.

    This function adds the test data to the in-memory mock providers
    so that the workflow can find and use it. This is only needed
    when running in mock mode.

    Args:
        company_name: Name of the test company
        role_name: Name of the test role

    Returns:
        The test data that was registered
    """
    # Import providers (these are singletons)
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider
    from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType

    # Get the mock providers
    taxonomy_provider = get_role_taxonomy_provider()
    doc_provider = get_document_provider()

    # Generate test data
    test_data = create_test_role_data(company_name, role_name)

    # Create and register the role taxonomy entry
    role_entry = RoleTaxonomyEntry(
        job_id=test_data["role_taxonomy"]["job_id"],
        job_role=test_data["role_taxonomy"]["job_role"],
        job_title=test_data["role_taxonomy"]["job_title"],
        occupation=test_data["role_taxonomy"]["occupation"],
        job_family=test_data["role_taxonomy"]["job_family"],
        draup_role=test_data["role_taxonomy"]["draup_role"],
        general_summary=test_data["role_taxonomy"]["general_summary"],
        status=test_data["role_taxonomy"]["status"],
    )

    # Add to taxonomy provider (uses add_role method)
    taxonomy_provider.add_role(company_name, role_entry)

    # Create and register the job description document
    jd_document = DocumentRef(
        type=DocumentType.JOB_DESCRIPTION,
        name=f"{role_name} - Job Description",
        content=test_data["job_description"],
        metadata={
            "company": company_name,
            "role": role_name,
            "source": "demo_generated",
            "created_at": datetime.now().isoformat(),
        },
    )

    # Add to document provider
    doc_provider.add_document(company_name, role_name, jd_document)

    print(f"\n  [+] Registered test data for: {company_name} / {role_name}")
    print(f"      Job ID: {test_data['role_taxonomy']['job_id']}")
    print(f"      JD Length: {len(test_data['job_description'])} characters")

    return test_data


# ============================================================================
# DATA LISTING
# ============================================================================
# Functions to display available companies and roles

async def list_available_data():
    """
    List all available companies and roles from mock data.

    This shows what test data is available to use with the workflow.
    You can use any of these company/role combinations for testing.
    """
    print_section("Available Companies and Roles (Mock Data)")

    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider
    from etter_workflows.models.inputs import DocumentType

    # Get provider instances
    taxonomy = get_role_taxonomy_provider()
    docs = get_document_provider()

    # Get all companies
    companies = taxonomy.get_companies()

    if not companies:
        print("\n  No companies found in mock data.")
        return

    for company in companies:
        print(f"\n  Company: {company}")
        print("  " + "-" * 40)

        # Get roles for this company
        roles = taxonomy.get_roles_for_company(company)

        for role in roles:
            # Check if JD exists for this role
            jd = docs.get_document(company, role.job_title, DocumentType.JOB_DESCRIPTION)
            jd_status = "JD Available" if jd else "No JD"

            # Display role info
            print(f"    - {role.job_title}")
            print(f"      Draup Role: {role.draup_role}")
            print(f"      Status: {jd_status}")


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================
# Functions to run the actual workflow

async def run_workflow_demo(
    company_id: str,
    role_name: str,
    use_mock_assessment: bool = True,
):
    """
    Run the role onboarding workflow.

    This is the main function that executes the self-service pipeline.
    It will:
    1. Create/find a CompanyRole node in Neo4j
    2. Link the job description to the role
    3. Run AI Assessment (mock or real)
    4. Return the assessment results

    Args:
        company_id: Company name/identifier
        role_name: Role name to process
        use_mock_assessment: If True, use mock AI assessment (random scores)
                            If False, call real AI Assessment API

    Returns:
        WorkflowResult object with status and outputs
    """
    print_section(f"Running Workflow: {role_name} at {company_id}")

    # Import the workflow execution function
    from etter_workflows.workflows.role_onboarding import execute_role_onboarding

    # Display what we're about to do
    print(f"\n  Workflow Configuration:")
    print(f"  - Company: {company_id}")
    print(f"  - Role: {role_name}")
    print(f"  - Assessment Mode: {'MOCK (random scores)' if use_mock_assessment else 'REAL (API call)'}")
    print()

    # Start timing
    start_time = datetime.now()
    print(f"  Starting at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("  " + "." * 40)

    try:
        # Execute the workflow
        # This runs the following steps:
        # 1. role_setup: Create CompanyRole node, link JD
        # 2. ai_assessment: Run AI assessment (mock or real)
        result = await execute_role_onboarding(
            company_id=company_id,
            role_name=role_name,
            use_mock_assessment=use_mock_assessment,
        )

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Display results
        print()
        print("  " + "=" * 50)
        print("  WORKFLOW RESULT")
        print("  " + "=" * 50)
        print()
        print(f"  Workflow ID: {result.workflow_id}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")

        if result.success:
            # Display success details
            print()
            print("  Role Information:")
            print(f"    - Role ID: {result.role_id}")
            print(f"    - Dashboard URL: {result.dashboard_url}")

            # Display assessment outputs if available
            if result.outputs:
                print()
                print("  AI Assessment Results:")
                print(f"    - AI Automation Score: {result.outputs.final_score:.2f}%")

                # Task analysis details
                if result.outputs.task_analysis:
                    task_count = result.outputs.task_analysis.get('task_count', 0)
                    print(f"    - Tasks Analyzed: {task_count}")

                # Impact analysis if available
                if result.outputs.impact_analysis:
                    print(f"    - Impact Analysis: Available")

            # Display completed steps
            print()
            print("  Steps Completed:")
            for step in result.steps_completed:
                status_icon = "[OK]" if step.status.value == "success" else "[FAIL]"
                duration_str = f"{step.duration_ms}ms" if step.duration_ms else "N/A"
                print(f"    {status_icon} {step.name}: {duration_str}")

        else:
            # Display error details
            print()
            print("  Error Details:")
            if result.error:
                print(f"    - Code: {result.error.code}")
                print(f"    - Message: {result.error.message}")
                print(f"    - Recoverable: {result.error.recoverable}")
            else:
                print("    - Unknown error")

        return result

    except Exception as e:
        # Handle unexpected errors
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("  WORKFLOW FAILED WITH EXCEPTION")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Error Type: {type(e).__name__}")
        print(f"  Error Message: {str(e)}")

        logger.exception("Workflow execution failed")
        raise


# ============================================================================
# TEMPORAL WORKFLOW EXECUTION
# ============================================================================
# Functions to run workflows via Temporal (visible in Temporal UI)

async def run_workflow_via_temporal(
    company_id: str,
    role_name: str,
    use_mock_assessment: bool = True,
):
    """
    Run the role onboarding workflow via Temporal.

    This executes the workflow through Temporal's orchestration system,
    making it visible in the Temporal UI. Requires:
    1. Temporal server running (temporal server start-dev)
    2. Etter worker running (python -m etter_workflows.worker)

    Args:
        company_id: Company name/identifier
        role_name: Role name to process
        use_mock_assessment: If True, use mock AI assessment

    Returns:
        WorkflowResult object with status and outputs
    """
    print_section(f"Running Workflow via Temporal: {role_name} at {company_id}")

    # Import Temporal client and workflow
    try:
        from temporalio.client import Client
        from temporalio.common import WorkflowIDReusePolicy
    except ImportError:
        print("\n  [ERROR] temporalio package not installed.")
        print("  Install with: pip install temporalio")
        return None

    from etter_workflows.config.settings import get_settings
    from etter_workflows.models.inputs import (
        RoleOnboardingInput,
        WorkflowOptions,
        DocumentType,
    )
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider

    settings = get_settings()

    # Display configuration
    print(f"\n  Temporal Configuration:")
    print(f"  - Host: {settings.temporal_host}")
    print(f"  - Namespace: {settings.get_temporal_namespace()}")
    print(f"  - Task Queue: {settings.temporal_task_queue}")
    print()
    print(f"  Workflow Configuration:")
    print(f"  - Company: {company_id}")
    print(f"  - Role: {role_name}")
    print(f"  - Assessment Mode: {'MOCK' if use_mock_assessment else 'REAL'}")
    print()

    # Connect to Temporal
    print("  Connecting to Temporal server...")
    try:
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.get_temporal_namespace(),
        )
        print(f"  [OK] Connected to Temporal")
    except Exception as e:
        print(f"\n  [ERROR] Failed to connect to Temporal: {e}")
        print()
        print("  Make sure Temporal server is running:")
        print("    temporal server start-dev")
        print()
        print("  Or check your ETTER_TEMPORAL_HOST environment variable.")
        return None

    # Build workflow input
    # Get documents from mock data providers
    taxonomy_provider = get_role_taxonomy_provider()
    doc_provider = get_document_provider()

    documents = []
    jd_doc = doc_provider.get_document(company_id, role_name, DocumentType.JOB_DESCRIPTION)
    if jd_doc:
        documents.append(jd_doc)

    taxonomy_entry = taxonomy_provider.get_role(company_id, role_name)
    draup_role_name = taxonomy_entry.get_draup_role() if taxonomy_entry else role_name

    workflow_input = RoleOnboardingInput(
        company_id=company_id,
        role_name=role_name,
        documents=documents,
        draup_role_name=draup_role_name,
        taxonomy_entry=taxonomy_entry,
        options=WorkflowOptions(
            force_rerun=False,
            notify_on_complete=True,
        ),
    )

    # Generate a unique but readable workflow ID
    import uuid
    workflow_id = f"demo-{company_id.lower().replace(' ', '-')}-{role_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"

    # Start timing
    start_time = datetime.now()
    print(f"\n  Starting workflow at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Workflow ID: {workflow_id}")
    print()
    print("  [!] You should now see this workflow in the Temporal UI:")
    print(f"      http://localhost:8233/namespaces/{settings.get_temporal_namespace()}/workflows")
    print()
    print("  Waiting for workflow to complete...")
    print("  " + "." * 40)

    try:
        # Start the workflow and wait for result
        # We need to import the workflow class for type hints
        from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

        result = await client.execute_workflow(
            RoleOnboardingWorkflow.execute,
            workflow_input,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Display results
        print()
        print("  " + "=" * 50)
        print("  TEMPORAL WORKFLOW RESULT")
        print("  " + "=" * 50)
        print()
        print(f"  Workflow ID: {workflow_id}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")

        if result.success:
            print()
            print("  Role Information:")
            print(f"    - Role ID: {result.role_id}")
            print(f"    - Dashboard URL: {result.dashboard_url}")

            if result.outputs:
                print()
                print("  AI Assessment Results:")
                print(f"    - AI Automation Score: {result.outputs.final_score:.2f}%")
                if result.outputs.task_analysis:
                    task_count = result.outputs.task_analysis.get('task_count', 0)
                    print(f"    - Tasks Analyzed: {task_count}")

            print()
            print("  Steps Completed:")
            for step in result.steps_completed:
                status_icon = "[OK]" if step.status.value == "success" else "[FAIL]"
                duration_str = f"{step.duration_ms}ms" if step.duration_ms else "N/A"
                print(f"    {status_icon} {step.name}: {duration_str}")
        else:
            print()
            print("  Error Details:")
            if result.error:
                print(f"    - Code: {result.error.code}")
                print(f"    - Message: {result.error.message}")

        print()
        print("  [!] View workflow history in Temporal UI:")
        print(f"      http://localhost:8233/namespaces/{settings.get_temporal_namespace()}/workflows/{workflow_id}")

        return result

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("  TEMPORAL WORKFLOW FAILED")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Error: {e}")
        print()
        print("  Common issues:")
        print("    1. Worker not running - Start with: python -m etter_workflows.worker")
        print("    2. Wrong namespace - Check ETTER_TEMPORAL_NAMESPACE env var")
        print("    3. Wrong task queue - Check ETTER_TEMPORAL_TASK_QUEUE env var")

        logger.exception("Temporal workflow execution failed")
        return None


# ============================================================================
# API USAGE DEMO
# ============================================================================
# Shows how to use the REST API endpoints

async def demo_api_usage(company_id: str, role_name: str):
    """
    Demonstrate how to use the REST API.

    This shows the request/response formats for the API endpoints.
    The API can be started separately using uvicorn.

    Args:
        company_id: Company name to use in examples
        role_name: Role name to use in examples
    """
    print_section("REST API Usage")

    from etter_workflows.api.schemas import PushRequest, PushOptions

    # Create a sample push request
    request = PushRequest(
        company_id=company_id,
        role_name=role_name,
        options=PushOptions(
            skip_enhancement_workflows=False,
            notify_on_complete=True,
        ),
    )

    print("\n  API Endpoints:")
    print("  " + "-" * 40)
    print("  POST /api/v1/pipeline/push    - Start a workflow")
    print("  GET  /api/v1/pipeline/status/{id} - Check status")
    print("  GET  /api/v1/health           - Health check")
    print("  GET  /api/v1/roles/available  - List available roles")

    print("\n  Sample Push Request:")
    print("  " + "-" * 40)

    # Format the JSON nicely
    import json
    request_json = json.loads(request.model_dump_json())
    for line in json.dumps(request_json, indent=4).split('\n'):
        print(f"  {line}")

    print("\n  To start the API server:")
    print("  " + "-" * 40)
    print("  uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090")
    print()
    print("  Then POST to: http://localhost:8090/api/v1/pipeline/push")


# ============================================================================
# BATCH PROCESSING DEMO
# ============================================================================
# Functions to demonstrate batch role processing

# Define batch roles for demo: 2 with JD, 1 without
BATCH_DEMO_ROLES = [
    {
        "role_name": "Software Engineer",
        "draup_role_name": "Software Developer",
        "has_jd": True,
        "job_description": """
# Software Engineer

## Overview
The Software Engineer designs, develops, and maintains software applications.
This role involves writing clean, efficient code and collaborating with
cross-functional teams to deliver high-quality products.

## Key Responsibilities
- Design and implement software solutions
- Write clean, maintainable, and efficient code
- Participate in code reviews and provide constructive feedback
- Debug and fix software defects
- Collaborate with product managers and designers
- Write technical documentation

## Requirements
- Bachelor's degree in Computer Science or related field
- 3+ years of software development experience
- Proficiency in Python, Java, or JavaScript
- Experience with version control (Git)
- Strong problem-solving skills
        """,
    },
    {
        "role_name": "Data Analyst",
        "draup_role_name": "Business Intelligence Analyst",
        "has_jd": True,
        "job_description": """
# Data Analyst

## Overview
The Data Analyst collects, processes, and analyzes data to help the organization
make informed business decisions. This role requires strong analytical skills
and the ability to communicate insights effectively.

## Key Responsibilities
- Collect and clean data from various sources
- Perform statistical analysis and create reports
- Build dashboards and visualizations
- Identify trends and patterns in data
- Present findings to stakeholders
- Collaborate with business teams on data needs

## Requirements
- Bachelor's degree in Statistics, Mathematics, or related field
- 2+ years of experience in data analysis
- Proficiency in SQL and Python
- Experience with visualization tools (Tableau, Power BI)
- Strong communication skills
        """,
    },
    {
        "role_name": "Product Manager",
        "draup_role_name": "Product Manager",
        "has_jd": False,  # No JD - to demonstrate validation handling
        "job_description": None,
    },
]


def register_batch_test_data(company_name: str):
    """
    Register batch test data for the demo.

    Creates test roles with varying data completeness:
    - 2 roles with complete JD (should succeed)
    - 1 role without JD (should show validation handling)

    Args:
        company_name: Company name to register roles under

    Returns:
        List of registered role data
    """
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider
    from etter_workflows.models.inputs import RoleTaxonomyEntry, DocumentRef, DocumentType

    taxonomy_provider = get_role_taxonomy_provider()
    doc_provider = get_document_provider()

    registered_roles = []

    print_section("Registering Batch Test Data")
    print(f"\n  Company: {company_name}")
    print(f"  Roles to register: {len(BATCH_DEMO_ROLES)}")
    print()

    for role_data in BATCH_DEMO_ROLES:
        role_name = role_data["role_name"]
        job_id = f"batch-{company_name[:4].lower()}-{role_name[:4].lower()}-001"

        # Create taxonomy entry
        role_entry = RoleTaxonomyEntry(
            job_id=job_id,
            job_role=role_name,
            job_title=role_name,
            occupation="Technology",
            job_family="Information Technology",
            draup_role=role_data["draup_role_name"],
            general_summary=f"The {role_name} role at {company_name}.",
            status="pending",
        )

        # Register taxonomy entry
        taxonomy_provider.add_role(company_name, role_entry)

        # Register JD if available
        if role_data["has_jd"] and role_data["job_description"]:
            jd_document = DocumentRef(
                type=DocumentType.JOB_DESCRIPTION,
                name=f"{role_name} - Job Description",
                content=role_data["job_description"].strip(),
                metadata={
                    "company": company_name,
                    "role": role_name,
                    "source": "batch_demo",
                    "created_at": datetime.now().isoformat(),
                },
            )
            doc_provider.add_document(company_name, role_name, jd_document)
            jd_status = "JD registered"
        else:
            jd_status = "NO JD (will test validation)"

        print(f"  [+] {role_name}")
        print(f"      Draup Role: {role_data['draup_role_name']}")
        print(f"      Status: {jd_status}")

        registered_roles.append({
            "role_name": role_name,
            "draup_role_name": role_data["draup_role_name"],
            "has_jd": role_data["has_jd"],
        })

    return registered_roles


async def run_batch_demo(
    company_id: str,
    use_mock_assessment: bool = True,
):
    """
    Run the batch processing demo.

    This demonstrates:
    1. Submitting multiple roles via push-batch endpoint
    2. Polling batch status
    3. Displaying aggregated results

    Args:
        company_id: Company name/identifier
        use_mock_assessment: If True, use mock AI assessment

    Returns:
        Final batch status
    """
    import json
    import time

    print_section(f"Running Batch Demo for: {company_id}")

    # Import workflow and status client
    from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow
    from etter_workflows.clients.status_client import get_status_client
    from etter_workflows.models.status import RoleStatus, WorkflowState
    from etter_workflows.models.inputs import (
        RoleOnboardingInput,
        WorkflowOptions,
        DocumentType,
        DocumentRef,
    )
    from etter_workflows.models.batch import BatchRecord
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider

    status_client = get_status_client()
    taxonomy_provider = get_role_taxonomy_provider()
    doc_provider = get_document_provider()

    # Build batch submission
    print("\n  Building batch submission...")
    print("  " + "-" * 40)

    batch = BatchRecord(
        company_id=company_id,
        role_count=len(BATCH_DEMO_ROLES),
        created_by="demo_script",
    )

    workflows_to_run = []
    skipped_roles = []

    for role_data in BATCH_DEMO_ROLES:
        role_name = role_data["role_name"]

        # Get documents from mock data
        documents = []
        jd_doc = doc_provider.get_document(company_id, role_name, DocumentType.JOB_DESCRIPTION)
        if jd_doc:
            documents.append(jd_doc)

        # Get taxonomy entry
        taxonomy_entry = taxonomy_provider.get_role(company_id, role_name)

        # Create workflow input
        input_data = RoleOnboardingInput(
            company_id=company_id,
            role_name=role_name,
            documents=documents,
            draup_role_name=role_data["draup_role_name"],
            taxonomy_entry=taxonomy_entry,
            options=WorkflowOptions(
                force_rerun=False,
                notify_on_complete=True,
            ),
        )

        # Validate input
        validation_errors = input_data.validate_for_processing()

        if validation_errors:
            print(f"  [!] {role_name}: Validation failed")
            print(f"      Errors: {validation_errors}")
            skipped_roles.append({
                "role_name": role_name,
                "errors": validation_errors,
            })
            continue

        # Create workflow
        workflow = RoleOnboardingWorkflow(use_mock_assessment=use_mock_assessment)
        batch.add_workflow(workflow.workflow_id)

        # Create initial status
        initial_status = RoleStatus(
            workflow_id=workflow.workflow_id,
            company_id=company_id,
            role_name=role_name,
            state=WorkflowState.QUEUED,
            progress=workflow._create_progress_info(),
            queued_at=datetime.now(),
            estimated_duration_seconds=600,
            metadata={"batch_id": batch.batch_id},
        )
        status_client.set_status(initial_status)

        workflows_to_run.append({
            "workflow": workflow,
            "input": input_data,
            "role_name": role_name,
        })

        print(f"  [+] {role_name}: Queued (workflow_id: {workflow.workflow_id[:20]}...)")

    # Store batch record
    status_client.set_batch(batch)

    print()
    print(f"  Batch ID: {batch.batch_id}")
    print(f"  Total roles: {len(BATCH_DEMO_ROLES)}")
    print(f"  Queued: {len(workflows_to_run)}")
    print(f"  Skipped (validation): {len(skipped_roles)}")

    if not workflows_to_run:
        print("\n  [!] No roles to process. Check validation errors above.")
        return None

    # Execute workflows concurrently
    print_section("Executing Batch Workflows")
    print(f"\n  Starting {len(workflows_to_run)} workflows concurrently...")
    print("  " + "." * 50)

    start_time = datetime.now()

    # Create tasks for all workflows
    async def execute_workflow(wf_data):
        try:
            result = await wf_data["workflow"].execute(wf_data["input"])
            return {"role_name": wf_data["role_name"], "success": True, "result": result}
        except Exception as e:
            logger.error(f"Workflow failed for {wf_data['role_name']}: {e}")
            return {"role_name": wf_data["role_name"], "success": False, "error": str(e)}

    # Run all workflows concurrently
    tasks = [execute_workflow(wf_data) for wf_data in workflows_to_run]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Display results
    print_section("Batch Results")
    print(f"\n  Total Duration: {duration:.2f} seconds")
    print()

    succeeded = 0
    failed = 0

    for result in results:
        if isinstance(result, Exception):
            print(f"  [FAIL] Exception: {result}")
            failed += 1
        elif result["success"]:
            wf_result = result["result"]
            print(f"  [OK] {result['role_name']}")
            if wf_result.outputs:
                print(f"       AI Score: {wf_result.outputs.final_score:.1f}%")
            if wf_result.dashboard_url:
                print(f"       Dashboard: {wf_result.dashboard_url}")
            succeeded += 1
        else:
            print(f"  [FAIL] {result['role_name']}: {result['error']}")
            failed += 1

    # Get final batch status
    batch_status = status_client.get_batch_status(batch.batch_id)

    print()
    print("  " + "=" * 50)
    print("  BATCH SUMMARY")
    print("  " + "=" * 50)
    print()
    print(f"  Batch ID: {batch.batch_id}")
    print(f"  Company: {company_id}")
    print(f"  Duration: {duration:.2f} seconds")
    print()
    print(f"  Results:")
    print(f"    - Total Submitted: {len(BATCH_DEMO_ROLES)}")
    print(f"    - Validation Skipped: {len(skipped_roles)}")
    print(f"    - Succeeded: {succeeded}")
    print(f"    - Failed: {failed}")
    print()

    if skipped_roles:
        print("  Validation Failures:")
        for skip in skipped_roles:
            print(f"    - {skip['role_name']}: {skip['errors']}")
        print()

    print("  [!] To check batch status via API:")
    print(f"      GET /api/v1/pipeline/batch-status/{batch.batch_id}")
    print()
    print("  [!] To retry failed roles via API:")
    print(f"      POST /api/v1/pipeline/retry-failed/{batch.batch_id}")

    return batch_status


async def run_batch_via_temporal(
    company_id: str,
    use_mock_assessment: bool = True,
):
    """
    Run batch workflows via Temporal.

    This submits workflows to Temporal so they're visible in the Temporal UI.
    Requires:
    1. Temporal server running (temporal server start-dev)
    2. Etter worker running (python -m etter_workflows.worker)

    Args:
        company_id: Company name/identifier
        use_mock_assessment: If True, use mock AI assessment

    Returns:
        List of workflow handles
    """
    import uuid

    print_section(f"Running Batch via Temporal: {company_id}")

    # Import Temporal client
    try:
        from temporalio.client import Client
        from temporalio.common import WorkflowIDReusePolicy
    except ImportError:
        print("\n  [ERROR] temporalio package not installed.")
        print("  Install with: pip install temporalio")
        return None

    from etter_workflows.config.settings import get_settings
    from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow
    from etter_workflows.models.inputs import (
        RoleOnboardingInput,
        WorkflowOptions,
        DocumentType,
    )
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    from etter_workflows.mock_data.documents import get_document_provider

    settings = get_settings()
    taxonomy_provider = get_role_taxonomy_provider()
    doc_provider = get_document_provider()

    # Display Temporal configuration
    print(f"\n  Temporal Configuration:")
    print(f"  - Host: {settings.temporal_host}")
    print(f"  - Namespace: {settings.get_temporal_namespace()}")
    print(f"  - Task Queue: {settings.temporal_task_queue}")
    print()

    # Connect to Temporal
    print("  Connecting to Temporal server...")
    try:
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.get_temporal_namespace(),
        )
        print(f"  [OK] Connected to Temporal")
    except Exception as e:
        print(f"\n  [ERROR] Failed to connect to Temporal: {e}")
        print()
        print("  Make sure Temporal server is running:")
        print("    temporal server start-dev")
        return None

    # Build batch of workflow inputs
    print()
    print("  Building batch submission...")
    print("  " + "-" * 40)

    batch_id = f"batch-{uuid.uuid4().hex[:12]}"
    workflow_handles = []
    skipped_roles = []

    for role_data in BATCH_DEMO_ROLES:
        role_name = role_data["role_name"]

        # Get documents from mock data
        documents = []
        jd_doc = doc_provider.get_document(company_id, role_name, DocumentType.JOB_DESCRIPTION)
        if jd_doc:
            documents.append(jd_doc)

        # Get taxonomy entry
        taxonomy_entry = taxonomy_provider.get_role(company_id, role_name)

        # Create workflow input
        workflow_input = RoleOnboardingInput(
            company_id=company_id,
            role_name=role_name,
            documents=documents,
            draup_role_name=role_data["draup_role_name"],
            taxonomy_entry=taxonomy_entry,
            options=WorkflowOptions(
                force_rerun=False,
                notify_on_complete=True,
            ),
        )

        # Validate input
        validation_errors = workflow_input.validate_for_processing()
        if validation_errors:
            print(f"  [!] {role_name}: Validation failed - {validation_errors}")
            skipped_roles.append({"role_name": role_name, "errors": validation_errors})
            continue

        # Generate workflow ID
        workflow_id = f"batch-{company_id.lower().replace(' ', '-')}-{role_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"

        try:
            # Start workflow (non-blocking)
            handle = await client.start_workflow(
                RoleOnboardingWorkflow.execute,
                workflow_input,
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            workflow_handles.append({
                "role_name": role_name,
                "workflow_id": workflow_id,
                "handle": handle,
            })
            print(f"  [+] {role_name}: Started (workflow_id: {workflow_id})")
        except Exception as e:
            print(f"  [!] {role_name}: Failed to start - {e}")
            skipped_roles.append({"role_name": role_name, "errors": [str(e)]})

    print()
    print(f"  Batch ID: {batch_id}")
    print(f"  Total roles: {len(BATCH_DEMO_ROLES)}")
    print(f"  Started: {len(workflow_handles)}")
    print(f"  Skipped: {len(skipped_roles)}")

    if not workflow_handles:
        print("\n  [!] No workflows started. Check errors above.")
        return None

    # Show where to view workflows
    print()
    print("  " + "=" * 50)
    print("  WORKFLOWS SUBMITTED TO TEMPORAL")
    print("  " + "=" * 50)
    print()
    print("  [!] View workflows in Temporal UI:")
    print(f"      http://localhost:8233/namespaces/{settings.get_temporal_namespace()}/workflows")
    print()
    print("  Individual workflow URLs:")
    for wf in workflow_handles:
        print(f"    - {wf['role_name']}:")
        print(f"      http://localhost:8233/namespaces/{settings.get_temporal_namespace()}/workflows/{wf['workflow_id']}")
    print()

    # Ask if user wants to wait for results
    print("  The workflows are now running in Temporal.")
    print("  You can monitor them in the Temporal UI.")
    print()
    print("  Waiting for workflows to complete...")
    print("  (Press Ctrl+C to stop waiting - workflows will continue in background)")
    print()

    # Wait for all workflows to complete
    start_time = datetime.now()
    results = []

    for wf in workflow_handles:
        try:
            print(f"  Waiting for {wf['role_name']}...", end=" ", flush=True)
            result = await wf["handle"].result()
            print(f"{'SUCCESS' if result.success else 'FAILED'}")
            results.append({
                "role_name": wf["role_name"],
                "success": result.success,
                "result": result,
            })
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "role_name": wf["role_name"],
                "success": False,
                "error": str(e),
            })

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Display results
    print()
    print("  " + "=" * 50)
    print("  BATCH RESULTS (via Temporal)")
    print("  " + "=" * 50)
    print()
    print(f"  Total Duration: {duration:.2f} seconds")
    print()

    succeeded = 0
    failed = 0

    for r in results:
        if r["success"]:
            wf_result = r["result"]
            print(f"  [OK] {r['role_name']}")
            if wf_result.outputs:
                print(f"       AI Score: {wf_result.outputs.final_score:.1f}%")
            if wf_result.dashboard_url:
                print(f"       Dashboard: {wf_result.dashboard_url}")
            succeeded += 1
        else:
            error_msg = r.get("error", "Unknown error")
            if "result" in r and r["result"].error:
                error_msg = r["result"].error.message
            print(f"  [FAIL] {r['role_name']}: {error_msg}")
            failed += 1

    print()
    print(f"  Summary:")
    print(f"    - Succeeded: {succeeded}")
    print(f"    - Failed: {failed}")
    print(f"    - Skipped (validation): {len(skipped_roles)}")

    if skipped_roles:
        print()
        print("  Validation Failures:")
        for skip in skipped_roles:
            print(f"    - {skip['role_name']}: {skip['errors']}")

    return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main(args):
    """
    Main demo function that orchestrates everything.

    Args:
        args: Parsed command line arguments
    """
    # Setup logging
    setup_logging(args.verbose)

    # Print welcome banner
    print_banner()

    # Print mode warning
    use_mock = not args.real
    print_mode_warning(use_mock, args.temporal)

    # Get company from args
    company_id = args.company

    # Check if batch mode
    if args.batch:
        # Batch mode: process multiple roles
        print("\n  [BATCH MODE] Processing multiple roles at once.")
        if args.temporal:
            print("  [TEMPORAL MODE] Workflows will be visible in Temporal UI.")
        else:
            print("  [STANDALONE MODE] Running workflows directly (not via Temporal).")
            print("  Use --temporal flag to submit to Temporal and see in UI.")

        # Register batch test data
        register_batch_test_data(company_id)

        # List available data
        await list_available_data()

        # Run batch demo
        try:
            if args.temporal:
                # Run via Temporal (visible in Temporal UI)
                results = await run_batch_via_temporal(
                    company_id=company_id,
                    use_mock_assessment=use_mock,
                )
                # Print summary
                print("\n" + "=" * 70)
                print("  BATCH DEMO COMPLETE (via Temporal)")
                print("=" * 70)

                if results:
                    succeeded = sum(1 for r in results if r["success"])
                    print(f"\n  Processed batch for '{company_id}'")
                    print(f"  Success Rate: {succeeded}/{len(results)}")
            else:
                # Run standalone (direct execution)
                batch_status = await run_batch_demo(
                    company_id=company_id,
                    use_mock_assessment=use_mock,
                )
                # Print summary
                print("\n" + "=" * 70)
                print("  BATCH DEMO COMPLETE")
                print("=" * 70)

                if batch_status:
                    print(f"\n  Processed batch for '{company_id}'")
                    print(f"  Batch ID: {batch_status.batch_id}")
                    print(f"  Success Rate: {batch_status.success_rate:.1f}%")

        except Exception as e:
            print(f"\n  [ERROR] Batch processing failed: {e}")
            logger.exception("Batch demo failed")
            return

        if use_mock:
            print("\n  [MOCK MODE] No actual database changes were made.")
            print("  To run with real database, use: python demo.py --batch --real")

        print()
        return

    # Single role mode
    role_name = args.role

    # Check if the company/role exists in mock data and register if needed
    # This is needed for BOTH mock and real modes because the workflow
    # looks up documents from mock data providers
    from etter_workflows.mock_data.role_taxonomy import get_role_taxonomy_provider
    taxonomy = get_role_taxonomy_provider()

    existing_role = taxonomy.get_role(company_id, role_name)

    if not existing_role:
        print_section("Creating Test Data")
        print(f"\n  Company '{company_id}' / Role '{role_name}' not found in mock data.")
        print("  Creating test data automatically...")
        register_test_data(company_id, role_name)

    # List available data
    await list_available_data()

    # Run the workflow
    try:
        if args.temporal:
            # Run via Temporal (visible in Temporal UI)
            result = await run_workflow_via_temporal(
                company_id=company_id,
                role_name=role_name,
                use_mock_assessment=use_mock,
            )
        else:
            # Run directly (standalone mode)
            result = await run_workflow_demo(
                company_id=company_id,
                role_name=role_name,
                use_mock_assessment=use_mock,
            )
    except Exception as e:
        print(f"\n  [ERROR] Workflow failed: {e}")
        print("  Check the error details above for more information.")
        return

    # Show API usage
    await demo_api_usage(company_id, role_name)

    # Print summary
    print("\n" + "=" * 70)
    print("  DEMO COMPLETE")
    print("=" * 70)

    if result and result.success:
        print("\n  The workflow completed successfully!")
        print(f"  Role '{role_name}' at '{company_id}' has been processed.")
        if use_mock:
            print("\n  [MOCK MODE] No actual database changes were made.")
            print("  To run with real database, use: python demo.py --real")
    else:
        print("\n  The workflow encountered an error.")
        print("  Check the error details above for more information.")

    print()


def parse_args():
    """
    Parse command line arguments.

    Returns:
        Parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description="Etter Self-Service Pipeline Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with mock data (safe, no database changes)
  python demo.py --mock

  # Run with custom test company and role
  python demo.py --company "TestCorp" --role "QA Engineer"

  # Run batch processing (multiple roles)
  python demo.py --batch --company "TestCorp"

  # Run with real database (WILL make changes!)
  python demo.py --real --company "TestCorp" --role "QA Engineer"

  # Run via Temporal (visible in Temporal UI, requires worker)
  python demo.py --real --temporal --company "TestCorp" --role "QA Engineer"

  # Run with verbose logging
  python demo.py --mock --verbose

Batch Mode (--batch flag):
  Submits 3 test roles:
  - Software Engineer (with JD) - should succeed
  - Data Analyst (with JD) - should succeed
  - Product Manager (no JD) - demonstrates validation handling

Temporal Setup (for --temporal flag):
  1. Start Temporal server: temporal server start-dev
  2. Start Etter worker: python -m etter_workflows.worker
  3. Run demo with --temporal flag
  4. View workflows at: http://localhost:8233
        """,
    )

    parser.add_argument(
        "--company",
        default="TestCorp",
        help="Company name (default: TestCorp)",
    )

    parser.add_argument(
        "--role",
        default="QA Engineer",
        help="Role name for single-role mode (default: QA Engineer)",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch mode: submit multiple roles at once",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock data providers (default, safe mode)",
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real database connections (WILL make changes!)",
    )

    parser.add_argument(
        "--temporal",
        action="store_true",
        help="Run workflow via Temporal (requires worker running)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging output",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\n\n  Demo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception("Demo failed with unexpected error")
        print(f"\n  Demo failed: {e}")
        sys.exit(1)
