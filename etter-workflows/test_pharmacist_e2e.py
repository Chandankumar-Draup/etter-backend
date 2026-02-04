#!/usr/bin/env python3
"""
End-to-end test for Pharmacist role at Acme Corporation.

Tests:
1. Health check (API, Temporal, Redis)
2. Role taxonomy API - fetch roles for Acme Corporation
3. Documents API - fetch documents for Pharmacist
4. Push workflow to Temporal
5. Query workflow status from Temporal

Usage:
    python test_pharmacist_e2e.py                    # Full test
    python test_pharmacist_e2e.py --health-only      # Health check only
    python test_pharmacist_e2e.py --status <ID>      # Query workflow status
"""

import argparse
import asyncio
import requests
import sys
import os

# Load .env if available
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[INFO] Loaded .env from {env_path}")
except ImportError:
    pass

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:7071")
PIPELINE_PREFIX = "/v1/pipeline"
AUTH_TOKEN = os.environ.get("ETTER_AUTH_TOKEN", None)

# Test data
COMPANY = "Acme Corporation"
ROLE = "Pharmacist"

# Sample JD for Pharmacist (used if API doesn't return one)
PHARMACIST_JD = """
# Pharmacist

## Overview
The Pharmacist is responsible for dispensing medications, providing drug information,
and ensuring safe and effective medication therapy for patients.

## Key Responsibilities
- Review and verify prescriptions for accuracy and appropriateness
- Dispense medications and provide patient counseling
- Monitor drug interactions and contraindications
- Collaborate with healthcare providers on medication therapy
- Maintain accurate records and comply with regulations
- Supervise pharmacy technicians and staff

## Requirements
- Doctor of Pharmacy (PharmD) degree
- Valid pharmacist license
- 2+ years of pharmacy experience
- Strong attention to detail
- Excellent communication skills
- Knowledge of pharmacy management systems
"""

# Temporal settings (for status queries)
TEMPORAL_HOST = os.environ.get("ETTER_TEMPORAL_HOST", "localhost")
TEMPORAL_PORT = os.environ.get("ETTER_TEMPORAL_PORT", "7233")
TEMPORAL_NAMESPACE = os.environ.get("ETTER_TEMPORAL_NAMESPACE", "etter-dev")


def get_headers():
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers


def api_url(path: str) -> str:
    return f"{BASE_URL}{PIPELINE_PREFIX}{path}"


# =============================================================================
# Test Functions
# =============================================================================

def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 60)
    print("1. HEALTH CHECK")
    print("=" * 60)

    try:
        response = requests.get(api_url("/health"), headers=get_headers(), timeout=10)
        data = response.json()

        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")

        components = data.get("components", {})
        print("\nComponents:")
        for name, status in components.items():
            icon = "[OK]" if status == "healthy" else "[!!]"
            print(f"  {icon} {name}: {status}")

        temporal_ok = components.get("temporal") == "healthy"
        return response.status_code == 200, temporal_ok

    except Exception as e:
        print(f"Error: {e}")
        return False, False


def test_roles_api():
    """Test role taxonomy API for Acme Corporation."""
    print("\n" + "=" * 60)
    print("2. ROLE TAXONOMY API")
    print("=" * 60)

    try:
        response = requests.get(
            api_url(f"/roles/{COMPANY}"),
            headers=get_headers(),
            timeout=30
        )

        print(f"GET /roles/{COMPANY}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            roles = data.get("roles", [])
            print(f"Found {len(roles)} roles")

            # Look for Pharmacist
            pharmacist_role = None
            for role in roles:
                print(f"  - {role.get('job_title', 'N/A')} ({role.get('job_role', 'N/A')})")
                if "pharmacist" in role.get("job_title", "").lower():
                    pharmacist_role = role

            if pharmacist_role:
                print(f"\n[OK] Found Pharmacist role:")
                print(f"  Job ID: {pharmacist_role.get('job_id')}")
                print(f"  Draup Role: {pharmacist_role.get('draup_role')}")
                return True, pharmacist_role
            else:
                print(f"\n[!!] Pharmacist role not found in taxonomy")
                return True, None
        else:
            print(f"Error: {response.text}")
            return False, None

    except Exception as e:
        print(f"Error: {e}")
        return False, None


def test_documents_api():
    """Test documents API for Pharmacist role."""
    print("\n" + "=" * 60)
    print("3. DOCUMENTS API")
    print("=" * 60)

    # Note: The documents API uses a different base URL
    # For now, we'll just indicate this step
    print(f"Looking for documents for {ROLE} at {COMPANY}")
    print("[INFO] Documents API integration pending - using sample JD")

    return True, PHARMACIST_JD


def test_push_workflow(jd_content: str, role_data: dict = None):
    """Push a workflow for Pharmacist role."""
    print("\n" + "=" * 60)
    print("4. PUSH WORKFLOW")
    print("=" * 60)

    payload = {
        "company_id": COMPANY,
        "role_name": ROLE,
        "draup_role_name": role_data.get("draup_role") if role_data else "Pharmacist",
        "documents": [
            {
                "type": "job_description",
                "content": jd_content,
                "name": f"{ROLE} Job Description"
            }
        ],
        "options": {
            "skip_enhancement_workflows": False,
            "force_rerun": False,
            "notify_on_complete": True
        }
    }

    print(f"Company: {COMPANY}")
    print(f"Role: {ROLE}")
    print(f"JD Length: {len(jd_content)} chars")

    try:
        response = requests.post(
            api_url("/push?use_mock=false"),
            headers=get_headers(),
            json=payload,
            timeout=30
        )

        print(f"\nStatus: {response.status_code}")
        data = response.json()

        if response.status_code == 200:
            workflow_id = data.get("workflow_id")
            message = data.get("message", "")

            print(f"Workflow ID: {workflow_id}")
            print(f"Message: {message}")

            if "Temporal" in message:
                print("\n[OK] Workflow submitted to Temporal!")
            elif "standalone" in message:
                print("\n[!!] Running in standalone mode")

            return workflow_id
        else:
            print(f"Error: {data}")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None


async def query_temporal_status(workflow_id: str):
    """Query workflow status from Temporal."""
    print("\n" + "=" * 60)
    print("5. TEMPORAL STATUS")
    print("=" * 60)

    print(f"Workflow ID: {workflow_id}")
    print(f"Temporal: {TEMPORAL_HOST}:{TEMPORAL_PORT}")
    print(f"Namespace: {TEMPORAL_NAMESPACE}")

    try:
        from temporalio.client import Client as TemporalClient

        address = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
        print(f"\nConnecting to {address}...")

        client = await TemporalClient.connect(address, namespace=TEMPORAL_NAMESPACE)
        handle = client.get_workflow_handle(workflow_id)

        desc = await handle.describe()

        print(f"\nWorkflow Status:")
        print(f"  ID:         {desc.id}")
        print(f"  Run ID:     {desc.run_id}")
        print(f"  Status:     {desc.status.name}")
        print(f"  Type:       {desc.workflow_type}")
        print(f"  Task Queue: {desc.task_queue}")
        print(f"  Started:    {desc.start_time}")

        if desc.close_time:
            print(f"  Closed:     {desc.close_time}")

        if desc.status.name == "COMPLETED":
            print("\n[OK] Workflow completed successfully!")
            try:
                result = await handle.result()
                if hasattr(result, 'success'):
                    print(f"  Success: {result.success}")
                if hasattr(result, 'role_id'):
                    print(f"  Role ID: {result.role_id}")
                if hasattr(result, 'dashboard_url'):
                    print(f"  Dashboard: {result.dashboard_url}")
            except Exception as e:
                print(f"  Result: {e}")

        elif desc.status.name == "FAILED":
            print("\n[!!] Workflow FAILED")

        elif desc.status.name == "RUNNING":
            print("\n[..] Workflow still running...")

        return desc

    except ImportError:
        print("\n[!!] temporalio package not installed")
        return None
    except Exception as e:
        print(f"\n[!!] Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="E2E test for Pharmacist role")
    parser.add_argument("--health-only", action="store_true", help="Only run health check")
    parser.add_argument("--status", type=str, metavar="WORKFLOW_ID",
                        help="Query workflow status from Temporal")
    parser.add_argument("--skip-push", action="store_true", help="Skip workflow push")
    args = parser.parse_args()

    print("=" * 60)
    print("E2E TEST: Pharmacist @ Acme Corporation")
    print("=" * 60)
    print(f"API: {BASE_URL}{PIPELINE_PREFIX}")
    print(f"Temporal: {TEMPORAL_HOST}:{TEMPORAL_PORT} ({TEMPORAL_NAMESPACE})")
    print("=" * 60)

    # Handle status query
    if args.status:
        asyncio.run(query_temporal_status(args.status))
        return

    # 1. Health check
    api_ok, temporal_ok = test_health()

    if not api_ok:
        print("\n[FAIL] API health check failed!")
        sys.exit(1)

    if args.health_only:
        print("\n" + "=" * 60)
        print(f"Health: {'OK' if api_ok else 'FAIL'}")
        print(f"Temporal: {'OK' if temporal_ok else 'NOT CONNECTED'}")
        print("=" * 60)
        sys.exit(0)

    # 2. Test role taxonomy API
    roles_ok, role_data = test_roles_api()

    # 3. Test documents API
    docs_ok, jd_content = test_documents_api()

    # 4. Push workflow
    workflow_id = None
    if not args.skip_push:
        workflow_id = test_push_workflow(jd_content, role_data)

    # 5. Query Temporal status (if workflow was pushed)
    if workflow_id and temporal_ok:
        print("\nWaiting 3 seconds before checking status...")
        import time
        time.sleep(3)
        asyncio.run(query_temporal_status(workflow_id))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Company: {COMPANY}")
    print(f"Role: {ROLE}")
    print(f"API Health: {'OK' if api_ok else 'FAIL'}")
    print(f"Temporal: {'OK' if temporal_ok else 'NOT CONNECTED'}")
    print(f"Role Taxonomy: {'OK' if roles_ok else 'FAIL'}")
    print(f"Workflow ID: {workflow_id or 'N/A'}")
    print("=" * 60)

    if workflow_id:
        print(f"\nTo check status later:")
        print(f"  python test_pharmacist_e2e.py --status {workflow_id}")


if __name__ == "__main__":
    main()
