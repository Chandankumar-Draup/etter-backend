#!/usr/bin/env python3
"""
QA Temporal Test Script - Standalone

Tests the QA API's Temporal integration with hardcoded configuration.
No .env file loading - all values are explicit.

Usage:
    python test_qa_temporal.py                    # Run full test
    python test_qa_temporal.py --health-only      # Health check only
    python test_qa_temporal.py --status <ID>      # Query workflow status from Temporal

Prerequisites:
    - Port-forward to QA Temporal:
      kubectl port-forward svc/qa-etter-temporal-frontend -n etter-temporal 7233:7233
"""

import argparse
import asyncio
import requests
import sys

# =============================================================================
# QA CONFIGURATION - ALL HARDCODED
# =============================================================================

# QA API Configuration
QA_API_BASE_URL = "https://qa-etter.draup.technology"
QA_API_PREFIX = "/api/v1/pipeline"
QA_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzcxMTQ4MDQ2LCJqdGkiOiI3NTc2NzYxNS1kZDk1LTQ4NmEtYjhjMy1kYzg2ZTMwN2ZhMjUifQ.BrP4aQ2P5ZF2x1jK10vgh015y4amcFyAFKv700roGLI"

# QA Temporal Configuration (via port-forward)
QA_TEMPORAL_HOST = "localhost"  # Port-forwarded from QA
QA_TEMPORAL_PORT = "7233"
QA_TEMPORAL_NAMESPACE = "etter-dev"

# Test Data
TEST_COMPANY = "TestCorp"
TEST_ROLE = "QA Engineer"
TEST_JD = """
# QA Engineer

## Overview
The QA Engineer ensures software quality through comprehensive testing.

## Responsibilities
- Design and execute test plans
- Perform manual and automated testing
- Identify and track bugs
- Collaborate with developers

## Requirements
- 3+ years QA experience
- Test automation skills
- Strong analytical abilities
"""

# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_headers():
    return {
        "Authorization": f"Bearer {QA_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


def api_url(path: str) -> str:
    return f"{QA_API_BASE_URL}{QA_API_PREFIX}{path}"


def test_health():
    """Test health endpoint and check Temporal status."""
    print("\n" + "=" * 60)
    print("QA HEALTH CHECK")
    print("=" * 60)

    try:
        response = requests.get(api_url("/health"), headers=get_headers(), timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: {response.text}")
            return False, None

        data = response.json()
        print(f"\nOverall Status: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")

        components = data.get("components", {})
        print("\nComponents:")

        temporal_healthy = False
        for name, status in components.items():
            icon = "[OK]" if status == "healthy" else "[!!]"
            print(f"  {icon} {name}: {status}")
            if name == "temporal" and status == "healthy":
                temporal_healthy = True

        return True, temporal_healthy

    except Exception as e:
        print(f"Error: {e}")
        return False, False


def test_push_workflow():
    """Push a test workflow and return the workflow ID."""
    print("\n" + "=" * 60)
    print("PUSH WORKFLOW TEST")
    print("=" * 60)

    payload = {
        "company_id": TEST_COMPANY,
        "role_name": TEST_ROLE,
        "draup_role_name": "Quality Assurance Engineer",
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
            "notify_on_complete": True
        }
    }

    print(f"Company: {TEST_COMPANY}")
    print(f"Role: {TEST_ROLE}")
    print(f"JD Length: {len(TEST_JD)} chars")

    try:
        response = requests.post(
            api_url("/push?use_mock=true"),
            headers=get_headers(),
            json=payload,
            timeout=30
        )

        print(f"\nStatus Code: {response.status_code}")
        data = response.json()

        if response.status_code != 200:
            print(f"Error: {data}")
            return None

        workflow_id = data.get("workflow_id")
        message = data.get("message", "")

        print(f"Workflow ID: {workflow_id}")
        print(f"Message: {message}")

        # Check if it went to Temporal
        if "Temporal" in message:
            print("\n[OK] Workflow submitted to Temporal!")
            return workflow_id
        elif "standalone" in message:
            print("\n[!!] Running in STANDALONE mode - Temporal not connected!")
            return workflow_id
        else:
            print(f"\n[??] Unknown mode: {message}")
            return workflow_id

    except Exception as e:
        print(f"Error: {e}")
        return None


async def query_temporal_status(workflow_id: str):
    """Query workflow status directly from QA Temporal."""
    print("\n" + "=" * 60)
    print("TEMPORAL STATUS QUERY")
    print("=" * 60)

    print(f"Workflow ID: {workflow_id}")
    print(f"Temporal: {QA_TEMPORAL_HOST}:{QA_TEMPORAL_PORT}")
    print(f"Namespace: {QA_TEMPORAL_NAMESPACE}")

    try:
        from temporalio.client import Client as TemporalClient

        address = f"{QA_TEMPORAL_HOST}:{QA_TEMPORAL_PORT}"
        print(f"\nConnecting to {address}...")

        client = await TemporalClient.connect(address, namespace=QA_TEMPORAL_NAMESPACE)
        handle = client.get_workflow_handle(workflow_id)

        print("Fetching workflow description...")
        desc = await handle.describe()

        print(f"\n{'=' * 40}")
        print("WORKFLOW STATUS")
        print(f"{'=' * 40}")
        print(f"  ID:         {desc.id}")
        print(f"  Run ID:     {desc.run_id}")
        print(f"  Status:     {desc.status.name}")
        print(f"  Type:       {desc.workflow_type}")
        print(f"  Task Queue: {desc.task_queue}")
        print(f"  Started:    {desc.start_time}")

        if desc.close_time:
            print(f"  Closed:     {desc.close_time}")

        # Get result if completed
        if desc.status.name == "COMPLETED":
            print(f"\n{'=' * 40}")
            print("WORKFLOW RESULT")
            print(f"{'=' * 40}")
            try:
                result = await handle.result()
                if hasattr(result, 'success'):
                    print(f"  Success: {result.success}")
                if hasattr(result, 'role_id'):
                    print(f"  Role ID: {result.role_id}")
                if hasattr(result, 'dashboard_url'):
                    print(f"  Dashboard: {result.dashboard_url}")
                if hasattr(result, 'error') and result.error:
                    print(f"  Error: {result.error}")
            except Exception as e:
                print(f"  Could not get result: {e}")

        elif desc.status.name == "FAILED":
            print("\n[!!] Workflow FAILED")
            # Try to get failure info
            try:
                await handle.result()
            except Exception as e:
                print(f"  Failure reason: {e}")

        elif desc.status.name == "RUNNING":
            print("\n[..] Workflow still RUNNING")

        return desc

    except ImportError:
        print("\n[!!] temporalio package not installed")
        print("Install with: pip install temporalio")
        return None
    except Exception as e:
        print(f"\n[!!] Error: {e}")

        if "workflow not found" in str(e).lower():
            print("\nPossible reasons:")
            print("  1. Workflow was submitted to standalone mode (not Temporal)")
            print("  2. Wrong Temporal namespace")
            print("  3. Port-forward not active")
            print("\nMake sure to run:")
            print("  kubectl port-forward svc/qa-etter-temporal-frontend -n etter-temporal 7233:7233")

        return None


def main():
    parser = argparse.ArgumentParser(
        description="Test QA Temporal Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_qa_temporal.py                    # Full test
  python test_qa_temporal.py --health-only      # Health check only
  python test_qa_temporal.py --status <ID>      # Query specific workflow

Prerequisites:
  Port-forward QA Temporal for --status queries:
  kubectl port-forward svc/qa-etter-temporal-frontend -n etter-temporal 7233:7233
        """
    )
    parser.add_argument("--health-only", action="store_true", help="Only run health check")
    parser.add_argument("--status", type=str, metavar="WORKFLOW_ID",
                        help="Query workflow status from Temporal")
    args = parser.parse_args()

    # Print header
    print("=" * 60)
    print("QA TEMPORAL INTEGRATION TEST")
    print("=" * 60)
    print(f"API URL: {QA_API_BASE_URL}{QA_API_PREFIX}")
    print(f"Temporal: {QA_TEMPORAL_HOST}:{QA_TEMPORAL_PORT} ({QA_TEMPORAL_NAMESPACE})")
    print("=" * 60)

    # Handle status query
    if args.status:
        asyncio.run(query_temporal_status(args.status))
        return

    # Run health check
    api_ok, temporal_ok = test_health()

    if not api_ok:
        print("\n[FAIL] API health check failed!")
        sys.exit(1)

    if args.health_only:
        if temporal_ok:
            print("\n[OK] Temporal is healthy!")
        else:
            print("\n[!!] Temporal is NOT healthy - workflows will run in standalone mode")
        sys.exit(0)

    # Push a test workflow
    workflow_id = test_push_workflow()

    if not workflow_id:
        print("\n[FAIL] Failed to push workflow!")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"API Status: OK")
    print(f"Temporal Status: {'OK' if temporal_ok else 'NOT CONNECTED'}")
    print(f"Workflow ID: {workflow_id}")
    print("=" * 60)

    if temporal_ok:
        print("\nTo check workflow status from Temporal:")
        print(f"  1. kubectl port-forward svc/qa-etter-temporal-frontend -n etter-temporal 7233:7233")
        print(f"  2. python test_qa_temporal.py --status {workflow_id}")
    else:
        print("\n[!!] Temporal not connected in QA!")
        print("The QA deployment needs these environment variables:")
        print("  ETTER_TEMPORAL_HOST=<qa-temporal-service>")
        print("  ETTER_TEMPORAL_PORT=7233")
        print("  ETTER_TEMPORAL_NAMESPACE=etter-dev")


if __name__ == "__main__":
    main()
