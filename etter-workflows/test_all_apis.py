#!/usr/bin/env python3
"""
Comprehensive API Test Script

Tests all API endpoints with:
- LOCAL endpoints for workflow operations (push, push-batch, retry-failed)
- QA endpoints for data APIs (role taxonomy, documents)

Usage:
    python test_all_apis.py                     # Run all tests
    python test_all_apis.py --health-only       # Health check only
    python test_all_apis.py --workflow-only     # Test workflow endpoints only
    python test_all_apis.py --data-only         # Test QA data APIs only
    python test_all_apis.py --validation-only   # Test document validation only

Prerequisites:
    - Local server running at http://localhost:8000
    - QA API accessible at https://qa-etter.draup.technology
"""

import argparse
import json
import requests
import sys
import time
from typing import Any, Dict, Optional, Tuple

# =============================================================================
# CONFIGURATION
# =============================================================================

# LOCAL API Configuration (for workflow operations)
LOCAL_API_BASE_URL = "http://localhost:8000"
LOCAL_API_PREFIX = "/api/v1/pipeline"

# QA API Configuration (for data APIs)
QA_API_BASE_URL = "https://qa-etter.draup.technology"
QA_API_PREFIX = "/api/v1/pipeline"
QA_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzcxMTQ4MDQ2LCJqdGkiOiI3NTc2NzYxNS1kZDk1LTQ4NmEtYjhjMy1kYzg2ZTMwN2ZhMjUifQ.BrP4aQ2P5ZF2x1jK10vgh015y4amcFyAFKv700roGLI"

# Test Data
TEST_COMPANY = "Acme Corporation"
TEST_ROLE = "Pharmacist"
TEST_JD = """
# Pharmacist

## Overview
The Pharmacist is responsible for dispensing medications and providing pharmaceutical care.

## Responsibilities
- Dispense prescription medications accurately
- Counsel patients on medication use
- Review prescriptions for drug interactions
- Maintain pharmacy inventory

## Requirements
- Doctor of Pharmacy (PharmD) degree
- Valid pharmacist license
- 2+ years experience preferred
- Strong attention to detail
"""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_local_headers():
    return {
        "Authorization": f"Bearer {QA_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


def get_qa_headers():
    return {
        "Authorization": f"Bearer {QA_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


def local_url(path: str) -> str:
    return f"{LOCAL_API_BASE_URL}{LOCAL_API_PREFIX}{path}"


def qa_url(path: str) -> str:
    return f"{QA_API_BASE_URL}{path}"


def print_section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_result(success: bool, message: str):
    icon = "[OK]" if success else "[FAIL]"
    print(f"{icon} {message}")


def safe_json(response) -> Dict:
    try:
        return response.json()
    except:
        return {"raw": response.text[:500] if response.text else "No content"}


# =============================================================================
# LOCAL API TESTS (Workflow Operations)
# =============================================================================

def test_local_health() -> Tuple[bool, Dict]:
    """Test local health endpoint."""
    print_section("LOCAL: Health Check")
    print(f"URL: {local_url('/health')}")

    try:
        response = requests.get(local_url("/health"), headers=get_local_headers(), timeout=10)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print_result(False, f"Health check failed: {data}")
            return False, data

        print(f"Overall: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")

        components = data.get("components", {})
        print("\nComponents:")
        for name, status in components.items():
            icon = "[OK]" if status == "healthy" else "[!!]"
            print(f"  {icon} {name}: {status}")

        print_result(True, "Health check passed")
        return True, data

    except requests.exceptions.ConnectionError:
        print_result(False, "Cannot connect to local server. Is it running?")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_push_validation_no_docs() -> Tuple[bool, Dict]:
    """Test POST /push - should fail validation without documents."""
    print_section("LOCAL: Push Validation (No Documents)")
    print(f"URL: {local_url('/push')}")
    print("Expected: 400 VALIDATION_ERROR (no documents provided)")

    payload = {
        "company_id": TEST_COMPANY,
        "role_name": TEST_ROLE,
        "draup_role_name": "Clinical Pharmacist",
        # NO documents field - should trigger validation error
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
        }
    }

    print(f"\nPayload (no documents):")
    print(f"  company_id: {payload['company_id']}")
    print(f"  role_name: {payload['role_name']}")
    print(f"  documents: NOT PROVIDED")

    try:
        response = requests.post(
            local_url("/push"),
            headers=get_local_headers(),
            json=payload,
            timeout=30
        )

        print(f"\nStatus: {response.status_code}")
        data = safe_json(response)
        print(f"Response: {json.dumps(data, indent=2)}")

        # Should return 400 with VALIDATION_ERROR
        if response.status_code == 400:
            error = data.get("detail", {})
            if error.get("error") == "VALIDATION_ERROR":
                print_result(True, "Correctly rejected request without documents")
                return True, data
            else:
                print_result(False, f"Got 400 but unexpected error type: {error}")
                return False, data
        else:
            print_result(False, f"Expected 400, got {response.status_code}")
            return False, data

    except requests.exceptions.ConnectionError:
        print_result(False, "Cannot connect to local server")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_push_with_docs() -> Tuple[bool, Optional[str], Dict]:
    """Test POST /push - should succeed with documents."""
    print_section("LOCAL: Push with Documents")
    print(f"URL: {local_url('/push')}")
    print("Expected: 200 with workflow_id")

    payload = {
        "company_id": TEST_COMPANY,
        "role_name": TEST_ROLE,
        "draup_role_name": "Clinical Pharmacist",
        "documents": [
            {
                "type": "job_description",
                "content": TEST_JD,
                "name": f"{TEST_ROLE} JD"
            }
        ],
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
        }
    }

    print(f"\nPayload:")
    print(f"  company_id: {payload['company_id']}")
    print(f"  role_name: {payload['role_name']}")
    print(f"  documents: 1 (job_description, {len(TEST_JD)} chars)")

    try:
        response = requests.post(
            local_url("/push"),
            headers=get_local_headers(),
            json=payload,
            timeout=30
        )

        print(f"\nStatus: {response.status_code}")
        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {json.dumps(data, indent=2)}")
            print_result(False, "Failed to push workflow")
            return False, None, data

        workflow_id = data.get("workflow_id")
        message = data.get("message", "")

        print(f"Workflow ID: {workflow_id}")
        print(f"Message: {message}")

        if workflow_id:
            print_result(True, f"Workflow created: {workflow_id}")
            return True, workflow_id, data
        else:
            print_result(False, "No workflow_id in response")
            return False, None, data

    except requests.exceptions.ConnectionError:
        print_result(False, "Cannot connect to local server")
        return False, None, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, None, {}


def test_push_batch_validation() -> Tuple[bool, Dict]:
    """Test POST /push-batch - mixed roles with and without documents."""
    print_section("LOCAL: Push Batch Validation")
    print(f"URL: {local_url('/push-batch')}")
    print("Expected: Validation failures for roles without documents")

    payload = {
        "company_id": TEST_COMPANY,
        "roles": [
            {
                "role_name": "Pharmacist",
                "draup_role_name": "Clinical Pharmacist",
                "documents": [
                    {
                        "type": "job_description",
                        "content": "Pharmacist job description content...",
                        "name": "Pharmacist JD"
                    }
                ]
            },
            {
                "role_name": "Nurse",
                "draup_role_name": "Registered Nurse",
                # No documents - should fail validation
            },
            {
                "role_name": "Doctor",
                "draup_role_name": "Physician",
                "documents": []  # Empty documents - should also fail
            }
        ],
        "options": {
            "skip_enhancement_workflows": False,
        }
    }

    print(f"\nPayload:")
    print(f"  company_id: {payload['company_id']}")
    print(f"  roles:")
    print(f"    - Pharmacist: HAS documents")
    print(f"    - Nurse: NO documents (should fail)")
    print(f"    - Doctor: EMPTY documents (should fail)")

    try:
        response = requests.post(
            local_url("/push-batch"),
            headers=get_local_headers(),
            json=payload,
            timeout=60
        )

        print(f"\nStatus: {response.status_code}")
        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {json.dumps(data, indent=2)}")
            print_result(False, "Batch push failed")
            return False, data

        # Check validation_failures
        validation_failures = data.get("validation_failures", [])
        workflows_started = data.get("workflows_started", [])

        print(f"\nResults:")
        print(f"  Workflows started: {len(workflows_started)}")
        print(f"  Validation failures: {len(validation_failures)}")

        if validation_failures:
            print("\n  Validation Failures:")
            for failure in validation_failures:
                print(f"    - {failure.get('role_name')}: {failure.get('errors')}")

        if workflows_started:
            print("\n  Workflows Started:")
            for wf in workflows_started:
                print(f"    - {wf.get('role_name')}: {wf.get('workflow_id')}")

        # Should have 1 success (Pharmacist) and 2 failures (Nurse, Doctor)
        if len(workflows_started) == 1 and len(validation_failures) == 2:
            print_result(True, "Correctly validated batch - 1 success, 2 validation failures")
            return True, data
        else:
            print_result(False, f"Unexpected results: {len(workflows_started)} started, {len(validation_failures)} failed")
            return False, data

    except requests.exceptions.ConnectionError:
        print_result(False, "Cannot connect to local server")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_workflow_status(workflow_id: str) -> Tuple[bool, Dict]:
    """Test GET /status/{workflow_id}."""
    print_section("LOCAL: Workflow Status")
    print(f"URL: {local_url(f'/status/{workflow_id}')}")

    try:
        response = requests.get(
            local_url(f"/status/{workflow_id}"),
            headers=get_local_headers(),
            timeout=10
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "Failed to get workflow status")
            return False, data

        print(f"\nWorkflow Status:")
        print(f"  ID: {data.get('workflow_id')}")
        print(f"  Status: {data.get('status')}")
        print(f"  Created: {data.get('created_at')}")

        print_result(True, f"Status retrieved: {data.get('status')}")
        return True, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_retry_failed() -> Tuple[bool, Dict]:
    """Test POST /retry-failed/{batch_id} with fake batch_id."""
    print_section("LOCAL: Retry Failed (Invalid Batch)")
    fake_batch_id = "fake-batch-12345"
    print(f"URL: {local_url(f'/retry-failed/{fake_batch_id}')}")
    print("Expected: 404 (batch not found)")

    try:
        response = requests.post(
            local_url(f"/retry-failed/{fake_batch_id}"),
            headers=get_local_headers(),
            timeout=10
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)

        if response.status_code == 404:
            print_result(True, "Correctly returned 404 for invalid batch_id")
            return True, data
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
            print_result(False, f"Expected 404, got {response.status_code}")
            return False, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


# =============================================================================
# QA API TESTS (Data APIs)
# =============================================================================

def test_qa_role_taxonomy() -> Tuple[bool, Dict]:
    """Test QA GET /api/taxonomy/roles."""
    print_section("QA: Role Taxonomy API")
    url = qa_url(f"/api/taxonomy/roles?company_id={TEST_COMPANY}&page_size=10")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=30)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "Failed to fetch role taxonomy")
            return False, data

        roles = data.get("data", [])
        total = data.get("total", len(roles))

        print(f"\nTotal roles: {total}")
        print(f"Returned: {len(roles)}")

        if roles:
            print("\nSample roles:")
            for role in roles[:5]:
                print(f"  - {role.get('job_title', 'N/A')} (draup: {role.get('draup_role', 'N/A')})")

        print_result(True, f"Fetched {len(roles)} roles from taxonomy API")
        return True, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_qa_documents_list() -> Tuple[bool, Dict]:
    """Test QA GET /api/documents/."""
    print_section("QA: Documents List API")
    url = qa_url(f"/api/documents/?company_instance_name={TEST_COMPANY}&limit=10")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=30)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "Failed to fetch documents")
            return False, data

        docs = data.get("data", {}).get("documents", [])
        total = data.get("data", {}).get("total", len(docs))

        print(f"\nTotal documents: {total}")
        print(f"Returned: {len(docs)}")

        if docs:
            print("\nSample documents:")
            for doc in docs[:5]:
                print(f"  - {doc.get('original_filename', 'N/A')} (id: {doc.get('id', 'N/A')[:8]}...)")

        print_result(True, f"Fetched {len(docs)} documents from API")
        return True, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_qa_document_detail(doc_id: str = None) -> Tuple[bool, Dict]:
    """Test QA GET /api/documents/{id}."""
    print_section("QA: Document Detail API")

    if not doc_id:
        # First fetch list to get a document ID
        response = requests.get(
            qa_url(f"/api/documents/?limit=1"),
            headers=get_qa_headers(),
            timeout=30
        )
        if response.status_code == 200:
            docs = response.json().get("data", {}).get("documents", [])
            if docs:
                doc_id = docs[0].get("id")

    if not doc_id:
        print("No document ID available to test")
        print_result(False, "Skipped - no documents available")
        return False, {}

    url = qa_url(f"/api/documents/{doc_id}?generate_download_url=true")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=30)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "Failed to fetch document detail")
            return False, data

        print(f"\nDocument:")
        print(f"  ID: {data.get('id')}")
        print(f"  Filename: {data.get('original_filename')}")
        print(f"  Status: {data.get('status')}")

        download = data.get("download", {})
        if download.get("url"):
            print(f"  Download URL: Available (expires: {download.get('expires_at', 'N/A')})")
        else:
            print(f"  Download URL: Not available")

        print_result(True, f"Fetched document detail: {data.get('original_filename')}")
        return True, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_qa_health() -> Tuple[bool, Dict]:
    """Test QA health endpoint."""
    print_section("QA: Health Check")
    url = qa_url(f"{QA_API_PREFIX}/health")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=10)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "QA health check failed")
            return False, data

        print(f"Overall: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")

        components = data.get("components", {})
        if components:
            print("\nComponents:")
            for name, status in components.items():
                icon = "[OK]" if status == "healthy" else "[!!]"
                print(f"  {icon} {name}: {status}")

        print_result(True, "QA health check passed")
        return True, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all tests."""
    results = {
        "local": {},
        "qa": {},
    }

    # Local Health
    success, _ = test_local_health()
    results["local"]["health"] = success

    if not success:
        print("\n[!!] Local server not available. Skipping local tests.")
    else:
        # Push validation tests
        success, _ = test_push_validation_no_docs()
        results["local"]["push_validation"] = success

        success, workflow_id, _ = test_push_with_docs()
        results["local"]["push_with_docs"] = success

        if workflow_id:
            time.sleep(1)  # Brief wait
            success, _ = test_workflow_status(workflow_id)
            results["local"]["workflow_status"] = success

        # Batch tests
        success, _ = test_push_batch_validation()
        results["local"]["push_batch"] = success

        # Retry test
        success, _ = test_retry_failed()
        results["local"]["retry_failed"] = success

    # QA Health
    success, _ = test_qa_health()
    results["qa"]["health"] = success

    # QA Data APIs
    success, _ = test_qa_role_taxonomy()
    results["qa"]["role_taxonomy"] = success

    success, _ = test_qa_documents_list()
    results["qa"]["documents_list"] = success

    success, _ = test_qa_document_detail()
    results["qa"]["document_detail"] = success

    return results


def print_summary(results: Dict):
    """Print test summary."""
    print_section("TEST SUMMARY")

    total_passed = 0
    total_failed = 0

    print("\nLOCAL API Tests:")
    for test, passed in results.get("local", {}).items():
        icon = "[OK]" if passed else "[FAIL]"
        print(f"  {icon} {test}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1

    print("\nQA API Tests:")
    for test, passed in results.get("qa", {}).items():
        icon = "[OK]" if passed else "[FAIL]"
        print(f"  {icon} {test}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1

    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print(f"{'=' * 70}")

    return total_failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive API Test Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_all_apis.py                     # Run all tests
  python test_all_apis.py --health-only       # Health checks only
  python test_all_apis.py --workflow-only     # Local workflow tests only
  python test_all_apis.py --data-only         # QA data API tests only
  python test_all_apis.py --validation-only   # Document validation tests only

Configuration:
  LOCAL API: http://localhost:8000/api/v1/pipeline
  QA API:    https://qa-etter.draup.technology
        """
    )
    parser.add_argument("--health-only", action="store_true", help="Only run health checks")
    parser.add_argument("--workflow-only", action="store_true", help="Only run local workflow tests")
    parser.add_argument("--data-only", action="store_true", help="Only run QA data API tests")
    parser.add_argument("--validation-only", action="store_true", help="Only run document validation tests")
    args = parser.parse_args()

    # Print header
    print("=" * 70)
    print("COMPREHENSIVE API TEST SCRIPT")
    print("=" * 70)
    print(f"LOCAL API:  {LOCAL_API_BASE_URL}{LOCAL_API_PREFIX}")
    print(f"QA API:     {QA_API_BASE_URL}")
    print(f"Company:    {TEST_COMPANY}")
    print(f"Role:       {TEST_ROLE}")
    print("=" * 70)

    results = {"local": {}, "qa": {}}

    if args.health_only:
        success, _ = test_local_health()
        results["local"]["health"] = success
        success, _ = test_qa_health()
        results["qa"]["health"] = success

    elif args.workflow_only:
        success, _ = test_local_health()
        results["local"]["health"] = success
        if success:
            success, _ = test_push_validation_no_docs()
            results["local"]["push_validation"] = success
            success, workflow_id, _ = test_push_with_docs()
            results["local"]["push_with_docs"] = success
            if workflow_id:
                time.sleep(1)
                success, _ = test_workflow_status(workflow_id)
                results["local"]["workflow_status"] = success
            success, _ = test_push_batch_validation()
            results["local"]["push_batch"] = success
            success, _ = test_retry_failed()
            results["local"]["retry_failed"] = success

    elif args.data_only:
        success, _ = test_qa_health()
        results["qa"]["health"] = success
        success, _ = test_qa_role_taxonomy()
        results["qa"]["role_taxonomy"] = success
        success, _ = test_qa_documents_list()
        results["qa"]["documents_list"] = success
        success, _ = test_qa_document_detail()
        results["qa"]["document_detail"] = success

    elif args.validation_only:
        success, _ = test_local_health()
        results["local"]["health"] = success
        if success:
            success, _ = test_push_validation_no_docs()
            results["local"]["push_validation_no_docs"] = success
            success, _ = test_push_batch_validation()
            results["local"]["push_batch_validation"] = success

    else:
        results = run_all_tests()

    # Print summary
    all_passed = print_summary(results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
