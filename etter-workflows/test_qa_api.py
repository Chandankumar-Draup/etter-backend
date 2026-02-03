"""
Test script for Etter Workflows API on QA environment.

Usage:
    python test_qa_api.py
"""

import requests
import time

# QA Configuration
BASE_URL = "https://qa-etter.draup.technology"
PIPELINE_PREFIX = "/api/v1/pipeline"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzcxMTQ4MDQ2LCJqdGkiOiI3NTc2NzYxNS1kZDk1LTQ4NmEtYjhjMy1kYzg2ZTMwN2ZhMjUifQ.BrP4aQ2P5ZF2x1jK10vgh015y4amcFyAFKv700roGLI"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Test Company
TEST_COMPANY = "TestCorp"

# =============================================================================
# Sample Job Descriptions for Testing
# =============================================================================

JD_QA_ENGINEER = """
# QA Engineer

## Overview
The QA Engineer is responsible for ensuring the quality of software products through
comprehensive testing strategies. This role involves designing test plans, executing
test cases, and collaborating with development teams.

## Key Responsibilities
- Design and execute test plans and test cases
- Perform manual and automated testing
- Identify, document, and track bugs
- Collaborate with developers to resolve issues
- Develop and maintain automated test scripts
- Participate in code reviews from a quality perspective

## Requirements
- Bachelor's degree in Computer Science or related field
- 3+ years of experience in software QA
- Experience with test automation frameworks (Selenium, Cypress)
- Knowledge of CI/CD pipelines
- Strong analytical and problem-solving skills
- Experience with API testing tools (Postman, REST Assured)
"""

JD_SOFTWARE_ENGINEER = """
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
- Experience with cloud platforms (AWS, GCP, Azure)
"""

JD_DATA_ANALYST = """
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
- Knowledge of statistical methods and machine learning basics
"""

JD_PRODUCT_MANAGER = """
# Product Manager

## Overview
The Product Manager is responsible for the strategy, roadmap, and feature definition
of a product or product line. This role bridges business strategy and technology
to deliver customer value.

## Key Responsibilities
- Define product vision and strategy
- Gather and prioritize product requirements
- Work closely with engineering, design, and marketing teams
- Conduct market research and competitive analysis
- Define and track product metrics
- Manage product backlog and sprint planning

## Requirements
- Bachelor's degree in Business, Computer Science, or related field
- 3+ years of product management experience
- Strong understanding of software development processes
- Excellent communication and presentation skills
- Experience with agile methodologies
- Data-driven decision making skills
"""

# Test Data with Job Descriptions
TEST_SINGLE_ROLE = {
    "role_name": "QA Engineer",
    "draup_role_name": "Quality Assurance Engineer",
    "job_description": JD_QA_ENGINEER,
}

TEST_BATCH_ROLES = [
    {
        "role_name": "Software Engineer",
        "draup_role_name": "Software Developer",
        "job_description": JD_SOFTWARE_ENGINEER,
    },
    {
        "role_name": "Data Analyst",
        "draup_role_name": "Business Intelligence Analyst",
        "job_description": JD_DATA_ANALYST,
    },
    {
        "role_name": "Product Manager",
        "draup_role_name": "Product Manager",
        "job_description": JD_PRODUCT_MANAGER,
    },
]


def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 60)
    print("HEALTH CHECK")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}{PIPELINE_PREFIX}/health", headers=HEADERS)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")

    # Show component status
    if "components" in result:
        print("\nComponent Status:")
        for comp, status in result["components"].items():
            print(f"  - {comp}: {status}")

    return response.status_code == 200


def test_single_role():
    """Test single role push and status polling."""
    print("\n" + "=" * 60)
    print("SINGLE ROLE TEST")
    print("=" * 60)

    payload = {
        "company_id": TEST_COMPANY,
        "role_name": TEST_SINGLE_ROLE["role_name"],
        "draup_role_name": TEST_SINGLE_ROLE["draup_role_name"],
        "documents": [
            {
                "type": "job_description",
                "content": TEST_SINGLE_ROLE["job_description"],
                "name": f"{TEST_SINGLE_ROLE['role_name']} JD"
            }
        ],
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        }
    }

    print(f"\nPushing role: {payload['role_name']} at {payload['company_id']}")
    print(f"JD Length: {len(TEST_SINGLE_ROLE['job_description'])} chars")

    response = requests.post(
        f"{BASE_URL}{PIPELINE_PREFIX}/push?use_mock=true",
        headers=HEADERS,
        json=payload
    )

    print(f"\nStatus: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")

    if response.status_code != 200:
        print("Failed to push role!")
        return None

    workflow_id = result.get("workflow_id")
    print(f"\nWorkflow ID: {workflow_id}")

    # Poll status
    print("\nPolling status...")
    for i in range(10):
        time.sleep(5)
        status_response = requests.get(
            f"{BASE_URL}{PIPELINE_PREFIX}/status/{workflow_id}",
            headers=HEADERS
        )

        if status_response.status_code != 200:
            print(f"  [{i+1}/10] Error: {status_response.status_code}")
            continue

        status = status_response.json()
        state = status.get("status", "unknown")
        step = status.get("current_step", "N/A")
        progress = status.get("progress", {})

        print(f"  [{i+1}/10] State: {state}, Step: {step}, "
              f"Progress: {progress.get('current', 0)}/{progress.get('total', 0)}")

        if state in ["ready", "failed", "validation_error"]:
            print(f"\nFinal status: {state}")
            if status.get("error"):
                print(f"Error: {status['error']}")
            if status.get("role_id"):
                print(f"Role ID: {status['role_id']}")
            break

    return workflow_id


def test_batch():
    """Test batch push and status polling."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING TEST")
    print("=" * 60)

    # Build roles with documents
    roles = []
    for role in TEST_BATCH_ROLES:
        roles.append({
            "company_id": TEST_COMPANY,
            "role_name": role["role_name"],
            "draup_role_name": role["draup_role_name"],
            "documents": [
                {
                    "type": "job_description",
                    "content": role["job_description"],
                    "name": f"{role['role_name']} JD"
                }
            ]
        })

    payload = {
        "company_id": TEST_COMPANY,
        "roles": roles,
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        },
        "created_by": "test_qa_api"
    }

    print(f"\nPushing batch: {len(payload['roles'])} roles")
    for role in payload['roles']:
        jd_len = len(role['documents'][0]['content']) if role['documents'] else 0
        print(f"  - {role['role_name']} (JD: {jd_len} chars)")

    response = requests.post(
        f"{BASE_URL}{PIPELINE_PREFIX}/push-batch?use_mock=true",
        headers=HEADERS,
        json=payload
    )

    print(f"\nStatus: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")

    if response.status_code != 200:
        print("Failed to push batch!")
        return None

    batch_id = result.get("batch_id")
    workflow_ids = result.get("workflow_ids", [])

    print(f"\nBatch ID: {batch_id}")
    print(f"Workflow IDs ({len(workflow_ids)}): {workflow_ids}")

    if not workflow_ids:
        print("\nNo workflows started - check validation errors above")
        return batch_id

    # Poll batch status
    print("\nPolling batch status...")
    for i in range(20):
        time.sleep(10)
        status_response = requests.get(
            f"{BASE_URL}{PIPELINE_PREFIX}/batch-status/{batch_id}",
            headers=HEADERS
        )

        if status_response.status_code != 200:
            print(f"  [{i+1}/20] Error getting status: {status_response.status_code}")
            continue

        status = status_response.json()
        state = status.get("state", "unknown")
        total = status.get("total", 0)
        completed = status.get("completed", 0)
        failed = status.get("failed", 0)
        in_progress = status.get("in_progress", 0)
        progress_pct = status.get("progress_percent", 0)

        print(f"  [{i+1}/20] State: {state}, Progress: {progress_pct:.1f}% "
              f"(Completed: {completed}, Failed: {failed}, In Progress: {in_progress}, Total: {total})")

        if state == "completed":
            print(f"\nBatch completed!")
            print(f"Success rate: {status.get('success_rate', 0):.1f}%")

            print("\nRole statuses:")
            for role in status.get("roles", []):
                print(f"  - {role['role_name']}: {role['status']}")
                if role.get("error"):
                    print(f"    Error: {role['error']}")
                if role.get("dashboard_url"):
                    print(f"    Dashboard: {role['dashboard_url']}")
            break

    return batch_id


def test_companies():
    """Test companies endpoint."""
    print("\n" + "=" * 60)
    print("COMPANIES LIST")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}{PIPELINE_PREFIX}/companies", headers=HEADERS)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Companies: {result.get('companies', [])}")
        print(f"Total: {result.get('total_count', 0)}")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200


def main():
    """Run all tests."""
    print("=" * 60)
    print("ETTER WORKFLOWS QA API TEST")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}{PIPELINE_PREFIX}")
    print(f"Company: {TEST_COMPANY}")
    print("=" * 60)

    # Test health
    health_ok = test_health()
    if not health_ok:
        print("\nHealth check returned non-200. Continuing anyway...")

    # Test companies (optional)
    test_companies()

    # Test single role
    print("\n\nStarting single role test...")
    workflow_id = test_single_role()

    # Test batch
    print("\n\nStarting batch test...")
    batch_id = test_batch()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Company: {TEST_COMPANY}")
    print(f"Single Role Workflow ID: {workflow_id}")
    print(f"Batch ID: {batch_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
