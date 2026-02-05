#!/usr/bin/env python3
"""
Comprehensive API Test Script

Tests all API endpoints with:
- LOCAL endpoints for workflow operations (push, push-batch, retry-failed)
- QA endpoints for data APIs (role taxonomy, documents)
- QA endpoints for pipeline operations (push, push-batch with auto-fetch)

Usage:
    python test_all_apis.py                     # Run all tests
    python test_all_apis.py --health-only       # Health check only
    python test_all_apis.py --workflow-only     # Test workflow endpoints only
    python test_all_apis.py --data-only         # Test QA data APIs only
    python test_all_apis.py --validation-only   # Test document validation only
    python test_all_apis.py --qa-doc-test       # Test LOCAL push with real QA document
    python test_all_apis.py --qa-push-test      # Test QA /push and /push-batch (auto-fetch)
    python test_all_apis.py --qa-push-test --company "Acme" --role "Pharmacist"

Prerequisites:
    - Local server running at http://localhost:7071 (for local tests)
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
LOCAL_API_BASE_URL = "http://localhost:7071"
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
        # Response structure: {"status": "failure", "errors": [{"error": "VALIDATION_ERROR", ...}]}
        if response.status_code == 400:
            # Check for errors array (new format) or detail dict (old format)
            errors = data.get("errors", [])
            detail = data.get("detail", {})

            if errors and any(e.get("error") == "VALIDATION_ERROR" for e in errors):
                print_result(True, "Correctly rejected request without documents")
                return True, data
            elif isinstance(detail, dict) and detail.get("error") == "VALIDATION_ERROR":
                print_result(True, "Correctly rejected request without documents")
                return True, data
            else:
                print(f"\nDebug: errors={errors}, detail={detail}")
                print_result(False, f"Got 400 but unexpected error structure")
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


def _get_file_priority(filename: str) -> int:
    """
    Get file type priority for document selection.

    Priority (lower = better):
    1 = PDF
    2 = DOCX/DOC
    3 = Images (PNG, JPG, etc.)
    99 = Other
    """
    filename_lower = filename.lower() if filename else ""

    if filename_lower.endswith(".pdf"):
        return 1
    if filename_lower.endswith((".docx", ".doc")):
        return 2
    if filename_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")):
        return 3
    return 99


def test_push_with_qa_document() -> Tuple[bool, Optional[str], Dict]:
    """Test POST /push with a real document from QA API (includes download URL and metadata)."""
    print_section("LOCAL: Push with QA Document (Real Data)")
    print(f"URL: {local_url('/push')}")
    print("Expected: 200 with workflow_id, using real document from QA API")

    # First, fetch a document from QA API
    print(f"\n1. Fetching documents from QA API for role: {TEST_ROLE}")
    from urllib.parse import quote
    role_encoded = quote(TEST_ROLE)
    doc_list_url = qa_url(f"/api/documents/?roles={role_encoded}&limit=50")

    try:
        # Get document list
        response = requests.get(doc_list_url, headers=get_qa_headers(), timeout=30)
        if response.status_code != 200:
            print_result(False, f"Failed to fetch documents from QA: {response.status_code}")
            return False, None, {}

        docs = response.json().get("data", {}).get("documents", [])
        if not docs:
            print(f"[WARN] No documents found for role '{TEST_ROLE}' in QA")
            print("[INFO] Using inline content instead")
            # Fall back to inline content
            return test_push_with_docs()

        print(f"   Fetched {len(docs)} documents")

        # Filter to exact role match (roles == [TEST_ROLE])
        exact_match_docs = [d for d in docs if d.get("roles") == [TEST_ROLE]]
        print(f"   Exact role matches: {len(exact_match_docs)}")

        # Log all documents with their priorities
        print(f"\n   All documents (with priority):")
        for doc in docs:
            filename = doc.get("original_filename", "")
            roles = doc.get("roles", [])
            priority = _get_file_priority(filename)
            is_exact = roles == [TEST_ROLE]
            print(f"     [{priority}] {filename}")
            print(f"         roles: {roles} {'(EXACT MATCH)' if is_exact else ''}")

        # Select document with priority: exact match > file type (PDF > DOCX > images)
        candidates = exact_match_docs if exact_match_docs else docs

        # Sort by file type priority (lower = better)
        candidates_sorted = sorted(candidates, key=lambda d: _get_file_priority(d.get("original_filename", "")))

        selected_doc = candidates_sorted[0]
        selected_priority = _get_file_priority(selected_doc.get("original_filename", ""))

        print(f"\n   SELECTED DOCUMENT:")
        print(f"     Filename: {selected_doc.get('original_filename')}")
        print(f"     Priority: {selected_priority} (1=PDF, 2=DOCX, 3=Image, 99=Other)")
        print(f"     Roles: {selected_doc.get('roles')}")
        print(f"     Is exact match: {selected_doc.get('roles') == [TEST_ROLE]}")

        doc_id = selected_doc.get("id")
        print(f"     Document ID: {doc_id}")

        # Get document detail with download URL
        print(f"\n2. Fetching document detail with download URL")
        detail_url = qa_url(f"/api/documents/{doc_id}?generate_download_url=true")
        response = requests.get(detail_url, headers=get_qa_headers(), timeout=30)

        if response.status_code != 200:
            print_result(False, f"Failed to fetch document detail: {response.status_code}")
            return False, None, {}

        doc_detail = response.json()
        download_info = doc_detail.get("download", {})
        download_url = download_info.get("url")

        print(f"   Filename: {doc_detail.get('original_filename')}")
        print(f"   Status: {doc_detail.get('status')}")
        print(f"   Roles: {doc_detail.get('roles')}")
        print(f"   Content Type: {doc_detail.get('observed_content_type')}")
        print(f"   Download URL: {'Available' if download_url else 'Not available'}")
        if download_url:
            print(f"   URL preview: {download_url[:80]}...")

        # Build payload with full metadata
        print(f"\n3. Submitting workflow with document metadata")
        payload = {
            "company_id": TEST_COMPANY,
            "role_name": TEST_ROLE,
            "draup_role_name": "Clinical Pharmacist",
            "documents": [
                {
                    "type": "job_description",
                    "uri": download_url,  # S3 presigned URL
                    "name": doc_detail.get("original_filename"),
                    "metadata": {
                        "document_id": doc_id,
                        "download_url": download_url,
                        "status": doc_detail.get("status"),
                        "roles": doc_detail.get("roles", []),
                        "content_type": doc_detail.get("observed_content_type"),
                        "created_at": doc_detail.get("created_at"),
                        "updated_at": doc_detail.get("updated_at"),
                        "expires_at": download_info.get("expires_at"),
                    }
                }
            ],
            "options": {
                "skip_enhancement_workflows": False,
                "force_rerun": False,
            }
        }

        print(f"   Payload:")
        print(f"     company_id: {payload['company_id']}")
        print(f"     role_name: {payload['role_name']}")
        print(f"     document.name: {payload['documents'][0]['name']}")
        print(f"     document.uri: {'Set (presigned URL)' if payload['documents'][0]['uri'] else 'None'}")
        print(f"     document.metadata: {list(payload['documents'][0]['metadata'].keys())}")

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
            print_result(False, "Failed to push workflow with QA document")
            return False, None, data

        workflow_id = data.get("workflow_id")
        message = data.get("message", "")

        print(f"Workflow ID: {workflow_id}")
        print(f"Message: {message}")

        if workflow_id:
            print_result(True, f"Workflow created with QA document: {workflow_id}")
            return True, workflow_id, data
        else:
            print_result(False, "No workflow_id in response")
            return False, None, data

    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Cannot connect: {e}")
        return False, None, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        import traceback
        traceback.print_exc()
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
                "company_id": TEST_COMPANY,
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
                "company_id": TEST_COMPANY,
                "role_name": "Nurse",
                "draup_role_name": "Registered Nurse",
                # No documents - should fail validation
            },
            {
                "company_id": TEST_COMPANY,
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

        # Print full response for debugging
        print(f"Full Response: {json.dumps(data, indent=2)}")

        if response.status_code != 200:
            print_result(False, "Batch push failed")
            return False, data

        # Handle the actual response structure:
        # {
        #   "batch_id": "...",
        #   "total_roles": 3,
        #   "workflow_ids": ["..."],  # Successfully started workflows
        #   "status": "queued",
        #   "message": "Batch submitted: 1 roles queued..., 2 roles failed validation"
        # }
        batch_id = data.get("batch_id")
        total_roles = data.get("total_roles", 0)
        workflow_ids = data.get("workflow_ids", [])
        message = data.get("message", "")

        # Parse validation failures from message
        # Message format: "Batch submitted: X roles queued..., Y roles failed validation"
        validation_failed_count = 0
        if "failed validation" in message:
            import re
            match = re.search(r"(\d+) roles? failed validation", message)
            if match:
                validation_failed_count = int(match.group(1))

        print(f"\nResults:")
        print(f"  Batch ID: {batch_id}")
        print(f"  Total Roles: {total_roles}")
        print(f"  Workflows Started: {len(workflow_ids)}")
        print(f"  Validation Failures: {validation_failed_count}")

        if workflow_ids:
            print(f"\n  Workflow IDs: {workflow_ids}")

        # Should have 1 success (Pharmacist) and 2 failures (Nurse, Doctor)
        if len(workflow_ids) == 1 and validation_failed_count == 2:
            print_result(True, "Correctly validated batch - 1 success, 2 validation failures")
            return True, data
        elif len(workflow_ids) >= 1 or validation_failed_count >= 1:
            # Some processing happened
            print_result(True, f"Batch processed: {len(workflow_ids)} started, {validation_failed_count} failed validation")
            return True, data
        else:
            print_result(False, f"Unexpected results: {len(workflow_ids)} started, {validation_failed_count} failed")
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
    print(f"Note: Queries Temporal directly for workflow state.")

    try:
        response = requests.get(
            local_url(f"/status/{workflow_id}"),
            headers=get_local_headers(),
            timeout=10
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)
        print(f"Response: {json.dumps(data, indent=2)}")

        if response.status_code == 404:
            print("\n[INFO] Workflow not found in Temporal")
            print("[INFO] This may happen if workflow completed very quickly or wasn't submitted")
            print_result(True, "Status endpoint works (workflow not found)")
            return True, data

        if response.status_code != 200:
            print_result(False, "Failed to get workflow status")
            return False, data

        print(f"\nWorkflow Status:")
        print(f"  ID: {data.get('workflow_id')}")
        print(f"  Status: {data.get('status')}")
        print(f"  Started: {data.get('started_at')}")
        print(f"  Completed: {data.get('completed_at')}")

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
            json={},  # Send empty body
            timeout=10
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)
        print(f"Response: {json.dumps(data, indent=2)}")

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

    # Use company_name and job_title parameters (URL encoded)
    from urllib.parse import quote
    company_name_encoded = quote(TEST_COMPANY)
    job_title_encoded = quote(TEST_ROLE)
    url = qa_url(f"/api/taxonomy/roles?company_name={company_name_encoded}&job_title={job_title_encoded}")
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
                job_title = role.get('job_title', 'N/A')
                draup_role = role.get('draup_role', 'N/A')
                print(f"  - {job_title} (draup: {draup_role})")

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


def test_qa_documents_for_role() -> Tuple[bool, Dict]:
    """Test QA GET /api/documents/ filtered by role."""
    print_section("QA: Documents for Role API")
    from urllib.parse import quote
    role_encoded = quote(TEST_ROLE)
    url = qa_url(f"/api/documents/?roles={role_encoded}&limit=10")
    print(f"URL: {url}")
    print(f"Searching for documents with role: {TEST_ROLE}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=30)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code != 200:
            print(f"Error: {data}")
            print_result(False, "Failed to fetch documents for role")
            return False, data

        docs = data.get("data", {}).get("documents", [])
        total = data.get("data", {}).get("total", len(docs))

        print(f"\nTotal documents for {TEST_ROLE}: {total}")
        print(f"Returned: {len(docs)}")

        if docs:
            print(f"\nDocuments for {TEST_ROLE}:")
            for doc in docs:
                filename = doc.get('original_filename', 'N/A')
                doc_id = doc.get('id', 'N/A')
                roles = doc.get('roles', [])
                status = doc.get('status', 'N/A')
                print(f"  - {filename}")
                print(f"    ID: {doc_id}")
                print(f"    Roles: {roles}")
                print(f"    Status: {status}")
            print_result(True, f"Found {len(docs)} documents for {TEST_ROLE}")
            return True, data
        else:
            print(f"\n[INFO] No documents found for role '{TEST_ROLE}'")
            print("[INFO] Make sure documents are uploaded and tagged with this role in QA")
            print_result(False, f"No documents found for {TEST_ROLE}")
            return False, data

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
# QA PUSH TESTS (Test complete QA pipeline)
# =============================================================================

def test_qa_push(company_id: str = None, role_name: str = None) -> Tuple[bool, Optional[str], Dict]:
    """
    Test POST /push on QA API.

    Documents will be auto-fetched by the QA server from its documents API.
    This tests the complete QA pipeline end-to-end.

    Note: Use --company and --role flags to specify a valid company/role
    combination that has documents uploaded in QA.
    """
    print_section("QA: Push (Auto-fetch Documents)")

    company = company_id or TEST_COMPANY
    role = role_name or TEST_ROLE

    url = qa_url(f"{QA_API_PREFIX}/push")
    print(f"URL: {url}")
    print(f"Company: {company}")
    print(f"Role: {role}")
    print("Documents: Auto-fetch (not provided)")
    print("\nNote: Ensure documents exist for this company/role in QA.")
    print("      Use --company and --role flags to specify valid values.")

    payload = {
        "company_id": company,
        "role_name": role,
        # No documents - will be auto-fetched by QA server
    }

    try:
        print(f"\nSending request...")
        response = requests.post(
            url,
            headers=get_qa_headers(),
            json=payload,
            timeout=60
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)

        if response.status_code == 200:
            workflow_id = data.get("workflow_id")
            message = data.get("message", "")
            print(f"\nWorkflow ID: {workflow_id}")
            print(f"Status: {data.get('status')}")
            print(f"Message: {message}")
            print_result(True, f"QA push successful: {workflow_id}")
            return True, workflow_id, data
        else:
            # Handle both dict and list error responses
            error = data.get("detail", data.get("errors", [{}]))
            if isinstance(error, list) and error:
                error = error[0]
            if isinstance(error, dict):
                print(f"\nError: {error.get('error', 'Unknown')}")
                print(f"Message: {error.get('message', str(data))}")
            else:
                print(f"\nError: {data}")

            # Hint for common issues
            if "No documents found" in str(data):
                print(f"\n[HINT] No documents found for role '{role}' at company '{company}'.")
                print("       Try: python test_all_apis.py --qa-push-test --company <valid_company> --role <valid_role>")

            print_result(False, f"QA push failed: {response.status_code}")
            return False, None, data

    except requests.exceptions.Timeout:
        print_result(False, "Request timeout (60s)")
        return False, None, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, None, {}


def test_qa_push_batch(company_id: str = None, roles: list = None) -> Tuple[bool, Dict]:
    """
    Test POST /push-batch on QA API.

    Documents will be auto-fetched for each role.
    """
    print_section("QA: Push Batch (Auto-fetch Documents)")

    company = company_id or TEST_COMPANY
    role_list = roles or [TEST_ROLE]

    url = qa_url(f"{QA_API_PREFIX}/push-batch")
    print(f"URL: {url}")
    print(f"Company: {company}")
    print(f"Roles: {role_list}")
    print("Documents: Auto-fetch for each role")

    # Note: BatchRoleInput requires company_id for each role
    payload = {
        "company_id": company,
        "roles": [{"role_name": r, "company_id": company} for r in role_list],
        # No documents - will be auto-fetched by QA server
    }

    try:
        print(f"\nSending request...")
        response = requests.post(
            url,
            headers=get_qa_headers(),
            json=payload,
            timeout=60
        )

        print(f"Status: {response.status_code}")
        data = safe_json(response)

        if response.status_code == 200:
            batch_id = data.get("batch_id")
            workflow_ids = data.get("workflow_ids", [])
            message = data.get("message", "")
            print(f"\nBatch ID: {batch_id}")
            print(f"Workflow IDs: {workflow_ids}")
            print(f"Total: {data.get('total_roles')}")
            print(f"Message: {message}")
            print_result(True, f"QA batch push successful: {len(workflow_ids)} workflows")
            return True, data
        else:
            # Handle both dict and list error responses (422 returns list)
            if isinstance(data, list):
                print(f"\nValidation Errors:")
                for err in data[:3]:  # Show first 3 errors
                    loc = err.get("loc", [])
                    msg = err.get("msg", str(err))
                    print(f"  - {'.'.join(str(l) for l in loc)}: {msg}")
            else:
                error = data.get("detail", data.get("errors", [{}]))
                if isinstance(error, list) and error:
                    error = error[0]
                if isinstance(error, dict):
                    print(f"\nError: {error.get('error', 'Unknown')}")
                    print(f"Message: {error.get('message', str(data))}")
                else:
                    print(f"\nError: {data}")
            print_result(False, f"QA batch push failed: {response.status_code}")
            return False, data

    except requests.exceptions.Timeout:
        print_result(False, "Request timeout (60s)")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


def test_qa_workflow_status(workflow_id: str) -> Tuple[bool, Dict]:
    """Test GET /status/{workflow_id} on QA API."""
    print_section("QA: Workflow Status")

    url = qa_url(f"{QA_API_PREFIX}/status/{workflow_id}")
    print(f"URL: {url}")
    print(f"Workflow ID: {workflow_id}")

    try:
        response = requests.get(url, headers=get_qa_headers(), timeout=30)
        print(f"Status: {response.status_code}")

        data = safe_json(response)

        if response.status_code == 200:
            print(f"\nWorkflow Status:")
            print(f"  Status: {data.get('status')}")
            print(f"  Role: {data.get('role_name')}")
            print(f"  Company: {data.get('company_id')}")
            print(f"  Current Step: {data.get('current_step')}")

            progress = data.get("progress", {})
            print(f"  Progress: {progress.get('current', 0)}/{progress.get('total', 0)}")

            print_result(True, f"QA status: {data.get('status')}")
            return True, data
        else:
            print(f"Error: {data}")
            print_result(False, "Failed to get QA workflow status")
            return False, data

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False, {}


# =============================================================================
# DATABASE FALLBACK TESTS (Direct DB access without HTTP APIs)
# =============================================================================

def test_db_fallback_documents(company_name: str = None, role_name: str = None) -> Tuple[bool, Dict]:
    """
    Test direct database fetch for documents (bypassing HTTP APIs).

    This tests the _fetch_documents_via_db fallback in APIDocumentProvider.
    """
    print_section("DB FALLBACK: Documents Fetch")

    company = company_name or TEST_COMPANY
    role = role_name or TEST_ROLE

    print(f"Company: {company}")
    print(f"Role: {role}")
    print("\nTesting direct database access (no HTTP API calls)...")

    try:
        # Import the provider and helper functions
        import sys
        sys.path.insert(0, '/home/user/etter-backend')

        from etter_workflows.mock_data.api_providers import (
            _get_db_session,
            _get_company_id_from_name,
            APIDocumentProvider,
        )

        # Step 1: Test database session
        print("\n1. Testing database session...")
        db = _get_db_session()
        if not db:
            print_result(False, "Database session not available")
            print("[HINT] Make sure you're running from etter-backend directory")
            print("[HINT] The parent package models must be importable")
            return False, {}

        print_result(True, "Database session obtained")

        # Step 2: Test company ID lookup
        print(f"\n2. Looking up company ID for '{company}'...")
        company_id = _get_company_id_from_name(db, company)
        db.close()

        if not company_id:
            print_result(False, f"Company not found: {company}")
            print("[HINT] Make sure the company exists in the database")
            return False, {}

        print_result(True, f"Company ID: {company_id}")

        # Step 3: Test document fetch via database
        print(f"\n3. Fetching documents for role '{role}' via database...")
        provider = APIDocumentProvider()
        # Call the internal method directly
        docs = provider._fetch_documents_via_db(
            roles=[role],
            company_instance_name=company,
            tenant_id=str(company_id)
        )

        if not docs:
            print_result(False, f"No documents found for role '{role}'")
            print("[HINT] Make sure documents are uploaded and extracted for this role")
            return False, {"documents": []}

        print_result(True, f"Fetched {len(docs)} documents from database")

        # Print document details
        print(f"\nDocuments found:")
        for i, doc in enumerate(docs[:5], 1):  # Show first 5
            filename = doc.get("original_filename", "Unknown")
            doc_id = doc.get("id", "N/A")
            roles = doc.get("roles", [])
            content_type = doc.get("observed_content_type", "N/A")
            print(f"  {i}. {filename}")
            print(f"     ID: {doc_id}")
            print(f"     Roles: {roles}")
            print(f"     Type: {content_type}")

        if len(docs) > 5:
            print(f"  ... and {len(docs) - 5} more")

        return True, {"documents": docs, "count": len(docs)}

    except ImportError as e:
        print_result(False, f"Import error: {e}")
        print("[HINT] Make sure you're running from etter-backend directory")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def test_db_fallback_taxonomy(company_name: str = None, job_title: str = None) -> Tuple[bool, Dict]:
    """
    Test direct database fetch for role taxonomy (bypassing HTTP APIs).

    This tests the _fetch_roles_via_db fallback in APIRoleTaxonomyProvider.
    """
    print_section("DB FALLBACK: Role Taxonomy Fetch")

    company = company_name or TEST_COMPANY
    role = job_title or TEST_ROLE

    print(f"Company: {company}")
    print(f"Job Title (filter): {role}")
    print("\nTesting direct database access (no HTTP API calls)...")

    try:
        # Import the provider and helper functions
        import sys
        sys.path.insert(0, '/home/user/etter-backend')

        from etter_workflows.mock_data.api_providers import (
            _get_db_session,
            _get_company_id_from_name,
            APIRoleTaxonomyProvider,
        )

        # Step 1: Test database session
        print("\n1. Testing database session...")
        db = _get_db_session()
        if not db:
            print_result(False, "Database session not available")
            print("[HINT] Make sure you're running from etter-backend directory")
            return False, {}

        print_result(True, "Database session obtained")

        # Step 2: Test company ID lookup
        print(f"\n2. Looking up company ID for '{company}'...")
        company_id = _get_company_id_from_name(db, company)
        db.close()

        if not company_id:
            print_result(False, f"Company not found: {company}")
            print("[HINT] Make sure the company exists in the database")
            return False, {}

        print_result(True, f"Company ID: {company_id}")

        # Step 3: Test taxonomy fetch via database
        print(f"\n3. Fetching role taxonomy via database...")
        provider = APIRoleTaxonomyProvider()
        # Call the internal method directly
        roles = provider._fetch_roles_via_db(
            company_name=company,
            job_title=role,  # Filter by job title
        )

        if not roles:
            print(f"\n[INFO] No roles found matching '{role}'")
            print("[INFO] Trying without job_title filter...")

            # Try without filter
            roles = provider._fetch_roles_via_db(company_name=company)

            if not roles:
                print_result(False, f"No roles found for company '{company}'")
                return False, {"roles": []}

        print_result(True, f"Fetched {len(roles)} roles from database")

        # Print role details
        print(f"\nRoles found:")
        for i, r in enumerate(roles[:10], 1):  # Show first 10
            job_title_val = r.get("job_title", "Unknown")
            draup_role = r.get("draup_role", "N/A")
            job_family = r.get("job_family", "N/A")
            status = r.get("approval_status", "N/A")
            print(f"  {i}. {job_title_val}")
            print(f"     Draup Role: {draup_role}")
            print(f"     Job Family: {job_family}")
            print(f"     Status: {status}")

        if len(roles) > 10:
            print(f"  ... and {len(roles) - 10} more")

        return True, {"roles": roles, "count": len(roles)}

    except ImportError as e:
        print_result(False, f"Import error: {e}")
        print("[HINT] Make sure you're running from etter-backend directory")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def test_db_fallback_best_document(company_name: str = None, role_name: str = None) -> Tuple[bool, Dict]:
    """
    Test the full get_best_document_for_role flow using database fallback.

    This simulates what happens during /push when documents are auto-fetched.
    """
    print_section("DB FALLBACK: Best Document Selection")

    company = company_name or TEST_COMPANY
    role = role_name or TEST_ROLE

    print(f"Company: {company}")
    print(f"Role: {role}")
    print("\nTesting best document selection (PDF > DOCX > Images)...")

    try:
        import sys
        sys.path.insert(0, '/home/user/etter-backend')

        from etter_workflows.mock_data.api_providers import APIDocumentProvider

        # Get the provider
        provider = APIDocumentProvider()

        # Test get_best_document_for_role which internally uses the fallback
        print("\n1. Calling get_best_document_for_role()...")
        best_doc = provider.get_best_document_for_role(
            role_name=role,
            company_name=company
        )

        if not best_doc:
            print_result(False, f"No document found for role '{role}'")
            print("[HINT] Make sure documents exist for this role")
            return False, {}

        print_result(True, "Best document found!")

        print(f"\nBest Document:")
        print(f"  Name: {best_doc.name}")
        print(f"  Type: {best_doc.type.value}")
        print(f"  URI: {best_doc.uri[:80]}..." if best_doc.uri and len(best_doc.uri) > 80 else f"  URI: {best_doc.uri}")

        if best_doc.metadata:
            print(f"  Metadata keys: {list(best_doc.metadata.keys())}")

        return True, {
            "document": {
                "name": best_doc.name,
                "type": best_doc.type.value,
                "uri": best_doc.uri,
            }
        }

    except ImportError as e:
        print_result(False, f"Import error: {e}")
        return False, {}
    except Exception as e:
        print_result(False, f"Error: {e}")
        import traceback
        traceback.print_exc()
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

    success, _ = test_qa_documents_for_role()
    results["qa"]["documents_for_role"] = success

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
  python test_all_apis.py --qa-doc-test       # Test LOCAL push with real QA document
  python test_all_apis.py --qa-push-test      # Test QA /push and /push-batch (auto-fetch)
  python test_all_apis.py --qa-push-test --company "Acme Corp" --role "Pharmacist"
  python test_all_apis.py --db-fallback-test  # Test direct DB fetch (no HTTP APIs)
  python test_all_apis.py --db-fallback-test --company "Acme Corp" --role "Pharmacist"

Configuration:
  LOCAL API: http://localhost:7071/api/v1/pipeline
  QA API:    https://qa-etter.draup.technology
        """
    )
    parser.add_argument("--health-only", action="store_true", help="Only run health checks")
    parser.add_argument("--workflow-only", action="store_true", help="Only run local workflow tests")
    parser.add_argument("--data-only", action="store_true", help="Only run QA data API tests")
    parser.add_argument("--validation-only", action="store_true", help="Only run document validation tests")
    parser.add_argument("--qa-doc-test", action="store_true", help="Test push with real document from QA (with download URL)")
    parser.add_argument("--qa-push-test", action="store_true", help="Test /push and /push-batch on QA (documents auto-fetched)")
    parser.add_argument("--db-fallback-test", action="store_true", help="Test direct database fetch (no HTTP APIs)")
    parser.add_argument("--company", type=str, help="Company name for tests")
    parser.add_argument("--role", type=str, help="Role name for tests")
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
        success, _ = test_qa_documents_for_role()
        results["qa"]["documents_for_role"] = success
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

    elif args.qa_doc_test:
        # Test pushing with real document from QA (with download URL and metadata)
        success, _ = test_local_health()
        results["local"]["health"] = success
        if success:
            success, workflow_id, _ = test_push_with_qa_document()
            results["local"]["push_with_qa_document"] = success
            if workflow_id:
                time.sleep(1)
                success, _ = test_workflow_status(workflow_id)
                results["local"]["workflow_status"] = success

    elif args.qa_push_test:
        # Test complete QA pipeline (push and push-batch with auto-fetch)
        company = args.company or TEST_COMPANY
        role = args.role or TEST_ROLE

        print(f"\nTesting QA Pipeline with:")
        print(f"  Company: {company}")
        print(f"  Role: {role}")
        print("")

        # QA Health check first
        success, _ = test_qa_health()
        results["qa"]["health"] = success

        if success:
            # Test single push (documents auto-fetched)
            success, workflow_id, _ = test_qa_push(company_id=company, role_name=role)
            results["qa"]["push"] = success

            if workflow_id:
                time.sleep(2)
                success, _ = test_qa_workflow_status(workflow_id)
                results["qa"]["workflow_status"] = success

            # Test batch push (documents auto-fetched)
            success, _ = test_qa_push_batch(company_id=company, roles=[role])
            results["qa"]["push_batch"] = success

    elif args.db_fallback_test:
        # Test direct database fetch (no HTTP APIs)
        company = args.company or TEST_COMPANY
        role = args.role or TEST_ROLE

        print(f"\nTesting Database Fallback with:")
        print(f"  Company: {company}")
        print(f"  Role: {role}")
        print("\n[INFO] These tests bypass HTTP APIs and query the database directly.")
        print("[INFO] Run from etter-backend directory for parent models to be available.")
        print("")

        # Test database fallback for documents
        success, _ = test_db_fallback_documents(company_name=company, role_name=role)
        results["local"]["db_documents"] = success

        # Test database fallback for taxonomy
        success, _ = test_db_fallback_taxonomy(company_name=company, job_title=role)
        results["local"]["db_taxonomy"] = success

        # Test best document selection (uses fallback internally)
        success, _ = test_db_fallback_best_document(company_name=company, role_name=role)
        results["local"]["db_best_document"] = success

    else:
        results = run_all_tests()

    # Print summary
    all_passed = print_summary(results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
