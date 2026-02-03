"""
Test script for Etter Workflows API on QA environment.

Usage:
    python test_qa_api.py
"""

import requests
import time

# QA Configuration
BASE_URL = "https://qa-etter.draup.technology/api/v1/pipeline"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzcxMTQ4MDQ2LCJqdGkiOiI3NTc2NzYxNS1kZDk1LTQ4NmEtYjhjMy1kYzg2ZTMwN2ZhMjUifQ.BrP4aQ2P5ZF2x1jK10vgh015y4amcFyAFKv700roGLI"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Test Data (matches demo.py)
TEST_COMPANY = "TestCorp"
TEST_SINGLE_ROLE = "QA Engineer"
TEST_BATCH_ROLES = [
    {"role_name": "Software Engineer", "draup_role_name": "Software Developer"},
    {"role_name": "Data Analyst", "draup_role_name": "Business Intelligence Analyst"},
    {"role_name": "Product Manager", "draup_role_name": "Product Manager"},
]


def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 60)
    print("HEALTH CHECK")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_single_role():
    """Test single role push and status polling."""
    print("\n" + "=" * 60)
    print("SINGLE ROLE TEST")
    print("=" * 60)

    payload = {
        "company_id": TEST_COMPANY,
        "role_name": TEST_SINGLE_ROLE,
        "draup_role_name": "Quality Assurance Engineer",
        "documents": [],
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        }
    }

    print(f"\nPushing role: {payload['role_name']} at {payload['company_id']}")
    response = requests.post(
        f"{BASE_URL}/push?use_mock=true",
        headers=HEADERS,
        json=payload
    )

    print(f"Status: {response.status_code}")
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
            f"{BASE_URL}/status/{workflow_id}",
            headers=HEADERS
        )
        status = status_response.json()
        state = status.get("status", "unknown")
        step = status.get("current_step", "N/A")
        progress = status.get("progress", {})

        print(f"  [{i+1}/10] State: {state}, Step: {step}, Progress: {progress.get('current', 0)}/{progress.get('total', 0)}")

        if state in ["ready", "failed", "validation_error"]:
            print(f"\nFinal status: {state}")
            if status.get("error"):
                print(f"Error: {status['error']}")
            break

    return workflow_id


def test_batch():
    """Test batch push and status polling."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING TEST")
    print("=" * 60)

    payload = {
        "company_id": TEST_COMPANY,
        "roles": [
            {
                "company_id": TEST_COMPANY,
                "role_name": role["role_name"],
                "draup_role_name": role["draup_role_name"],
                "documents": []
            }
            for role in TEST_BATCH_ROLES
        ],
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        },
        "created_by": "test_qa_api"
    }

    print(f"\nPushing batch: {len(payload['roles'])} roles")
    for role in payload['roles']:
        print(f"  - {role['role_name']} ({role['company_id']})")

    response = requests.post(
        f"{BASE_URL}/push-batch?use_mock=true",
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
    print(f"\nBatch ID: {batch_id}")
    print(f"Workflow IDs: {result.get('workflow_ids', [])}")

    # Poll batch status
    print("\nPolling batch status...")
    for i in range(20):
        time.sleep(10)
        status_response = requests.get(
            f"{BASE_URL}/batch-status/{batch_id}",
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
            break

    return batch_id


def main():
    """Run all tests."""
    print("=" * 60)
    print("ETTER WORKFLOWS QA API TEST")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Company: {TEST_COMPANY}")
    print("=" * 60)

    # Test health
    if not test_health():
        print("\nHealth check failed! Aborting.")
        return

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
