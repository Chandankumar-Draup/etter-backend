#!/usr/bin/env python3
"""
API Tools for Etter Workflows.

This script provides utilities for:
1. Generating API documentation
2. Testing API endpoints
3. Checking API health
4. Making sample API calls

Usage:
    # Generate OpenAPI spec
    python scripts/api_tools.py docs

    # Run health check
    python scripts/api_tools.py health

    # Test all endpoints
    python scripts/api_tools.py test

    # Push a test workflow
    python scripts/api_tools.py push --company "TestCorp" --role "QA Engineer"

    # Check workflow status
    python scripts/api_tools.py status --id "workflow-id-here"
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    requests = None


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_API_URL = "http://localhost:8090"
API_PREFIX = "/api/v1/pipeline"


def get_api_url(base_url: str = DEFAULT_API_URL) -> str:
    """Get full API URL."""
    return f"{base_url}{API_PREFIX}"


# ============================================================================
# Documentation Generator
# ============================================================================

def generate_openapi_spec():
    """Generate OpenAPI specification from FastAPI app."""
    print("Generating OpenAPI specification...")

    try:
        from etter_workflows.api.routes import app

        # Get OpenAPI schema
        openapi_schema = app.openapi()

        # Pretty print
        print(json.dumps(openapi_schema, indent=2))

        # Save to file
        output_path = "docs/openapi.json"
        with open(output_path, "w") as f:
            json.dump(openapi_schema, f, indent=2)

        print(f"\nSaved to: {output_path}")
        return openapi_schema

    except Exception as e:
        print(f"Error generating OpenAPI spec: {e}")
        return None


def print_endpoint_summary():
    """Print summary of all API endpoints."""
    print("\n" + "=" * 60)
    print("  ETTER WORKFLOWS API - ENDPOINT SUMMARY")
    print("=" * 60)

    endpoints = [
        ("GET", "/health", "Check API and dependency health"),
        ("POST", "/push", "Start a new workflow"),
        ("GET", "/status/{id}", "Get workflow status"),
        ("GET", "/companies", "List available companies"),
        ("GET", "/roles/{company}", "List roles for a company"),
    ]

    print(f"\n  Base URL: {DEFAULT_API_URL}{API_PREFIX}\n")

    for method, path, description in endpoints:
        print(f"  {method:6} {path:20} - {description}")

    print("\n" + "-" * 60)
    print("  Interactive Docs: http://localhost:8090/docs")
    print("  ReDoc: http://localhost:8090/redoc")
    print("=" * 60 + "\n")


# ============================================================================
# API Testing Functions
# ============================================================================

def check_health(base_url: str = DEFAULT_API_URL) -> dict:
    """Check API health."""
    if requests is None:
        print("Error: requests library not installed")
        print("Install with: pip install requests")
        return {}

    url = f"{get_api_url(base_url)}/health"
    print(f"Checking health: {url}")

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        print(f"\nStatus: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")
        print(f"Timestamp: {data.get('timestamp', 'unknown')}")

        if "components" in data:
            print("\nComponents:")
            for name, status in data["components"].items():
                icon = "[OK]" if status in ("healthy", "enabled") else "[!!]"
                print(f"  {icon} {name}: {status}")

        return data

    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to API at {base_url}")
        print("Make sure the API server is running:")
        print("  uvicorn etter_workflows.api.routes:app --host 0.0.0.0 --port 8090")
        return {}
    except Exception as e:
        print(f"\nError: {e}")
        return {}


def list_companies(base_url: str = DEFAULT_API_URL) -> list:
    """List available companies."""
    if requests is None:
        print("Error: requests library not installed")
        return []

    url = f"{get_api_url(base_url)}/companies"
    print(f"Fetching companies: {url}")

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        companies = data.get("companies", [])
        print(f"\nFound {len(companies)} companies:")
        for company in companies:
            print(f"  - {company}")

        return companies

    except Exception as e:
        print(f"\nError: {e}")
        return []


def list_roles(company: str, base_url: str = DEFAULT_API_URL) -> list:
    """List roles for a company."""
    if requests is None:
        print("Error: requests library not installed")
        return []

    url = f"{get_api_url(base_url)}/roles/{company}"
    print(f"Fetching roles for {company}: {url}")

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        roles = data.get("roles", [])
        print(f"\nFound {len(roles)} roles for {company}:")
        for role in roles:
            print(f"  - {role.get('job_title', 'Unknown')}")
            print(f"    Draup Role: {role.get('draup_role', 'N/A')}")

        return roles

    except Exception as e:
        print(f"\nError: {e}")
        return []


def push_workflow(
    company_id: str,
    role_name: str,
    use_mock: bool = True,
    base_url: str = DEFAULT_API_URL,
) -> dict:
    """Push a new workflow."""
    if requests is None:
        print("Error: requests library not installed")
        return {}

    url = f"{get_api_url(base_url)}/push"
    params = {"use_mock": str(use_mock).lower()}

    payload = {
        "company_id": company_id,
        "role_name": role_name,
        "options": {
            "force_rerun": False,
            "notify_on_complete": True,
        }
    }

    print(f"Pushing workflow: {url}")
    print(f"  Company: {company_id}")
    print(f"  Role: {role_name}")
    print(f"  Mock: {use_mock}")

    try:
        response = requests.post(url, json=payload, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"\nWorkflow started successfully!")
            print(f"  Workflow ID: {data.get('workflow_id')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Estimated Duration: {data.get('estimated_duration_seconds')}s")
            return data
        else:
            print(f"\nError: {response.status_code}")
            print(response.json())
            return {}

    except Exception as e:
        print(f"\nError: {e}")
        return {}


def get_status(workflow_id: str, base_url: str = DEFAULT_API_URL) -> dict:
    """Get workflow status."""
    if requests is None:
        print("Error: requests library not installed")
        return {}

    url = f"{get_api_url(base_url)}/status/{workflow_id}"
    print(f"Fetching status: {url}")

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()

            print(f"\nWorkflow Status:")
            print(f"  ID: {data.get('workflow_id')}")
            print(f"  Company: {data.get('company_id')}")
            print(f"  Role: {data.get('role_name')}")
            print(f"  Status: {data.get('status')}")

            if data.get('current_step'):
                print(f"  Current Step: {data.get('current_step')}")

            if data.get('progress'):
                progress = data['progress']
                print(f"  Progress: {progress.get('current')}/{progress.get('total')}")

                if progress.get('steps'):
                    print("  Steps:")
                    for step in progress['steps']:
                        status_icon = {
                            "completed": "[OK]",
                            "running": "[..]",
                            "failed": "[!!]",
                            "pending": "[  ]",
                        }.get(step.get("status"), "[??]")

                        duration = f" ({step.get('duration_ms')}ms)" if step.get('duration_ms') else ""
                        print(f"    {status_icon} {step.get('name')}{duration}")

            if data.get('dashboard_url'):
                print(f"  Dashboard: {data.get('dashboard_url')}")

            if data.get('error'):
                error = data['error']
                print(f"\n  Error:")
                print(f"    Code: {error.get('code')}")
                print(f"    Message: {error.get('message')}")

            return data

        elif response.status_code == 404:
            print(f"\nWorkflow not found: {workflow_id}")
            return {}
        else:
            print(f"\nError: {response.status_code}")
            print(response.json())
            return {}

    except Exception as e:
        print(f"\nError: {e}")
        return {}


def run_all_tests(base_url: str = DEFAULT_API_URL):
    """Run all API tests."""
    print("\n" + "=" * 60)
    print("  RUNNING API TESTS")
    print("=" * 60)

    results = []

    # Test 1: Health check
    print("\n[Test 1] Health Check")
    print("-" * 40)
    health = check_health(base_url)
    results.append(("Health Check", bool(health and health.get("status") == "healthy")))

    # Test 2: List companies
    print("\n[Test 2] List Companies")
    print("-" * 40)
    companies = list_companies(base_url)
    results.append(("List Companies", bool(companies)))

    # Test 3: Push workflow (mock mode)
    print("\n[Test 3] Push Workflow (Mock)")
    print("-" * 40)
    push_result = push_workflow("TestCorp", "QA Engineer", use_mock=True, base_url=base_url)
    results.append(("Push Workflow", bool(push_result and push_result.get("workflow_id"))))

    # Test 4: Get status
    if push_result and push_result.get("workflow_id"):
        print("\n[Test 4] Get Status")
        print("-" * 40)
        status = get_status(push_result["workflow_id"], base_url)
        results.append(("Get Status", bool(status)))
    else:
        results.append(("Get Status", False))

    # Summary
    print("\n" + "=" * 60)
    print("  TEST RESULTS")
    print("=" * 60)

    passed = 0
    for name, success in results:
        icon = "[PASS]" if success else "[FAIL]"
        print(f"  {icon} {name}")
        if success:
            passed += 1

    print(f"\n  Total: {passed}/{len(results)} tests passed")
    print("=" * 60 + "\n")

    return passed == len(results)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="API Tools for Etter Workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/api_tools.py docs              # Generate API docs
  python scripts/api_tools.py health            # Check API health
  python scripts/api_tools.py test              # Run all tests
  python scripts/api_tools.py companies         # List companies
  python scripts/api_tools.py roles TestCorp    # List roles for company
  python scripts/api_tools.py push --company TestCorp --role "QA Engineer"
  python scripts/api_tools.py status --id workflow-123
        """
    )

    parser.add_argument(
        "command",
        choices=["docs", "health", "test", "companies", "roles", "push", "status"],
        help="Command to run"
    )

    parser.add_argument(
        "args",
        nargs="*",
        help="Additional arguments (e.g., company name for roles)"
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})"
    )

    parser.add_argument(
        "--company",
        help="Company ID for push command"
    )

    parser.add_argument(
        "--role",
        help="Role name for push command"
    )

    parser.add_argument(
        "--id",
        help="Workflow ID for status command"
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real mode (not mock) for push"
    )

    args = parser.parse_args()

    # Execute command
    if args.command == "docs":
        print_endpoint_summary()
        generate_openapi_spec()

    elif args.command == "health":
        check_health(args.url)

    elif args.command == "test":
        success = run_all_tests(args.url)
        sys.exit(0 if success else 1)

    elif args.command == "companies":
        list_companies(args.url)

    elif args.command == "roles":
        if args.args:
            list_roles(args.args[0], args.url)
        else:
            print("Error: Company name required")
            print("Usage: python scripts/api_tools.py roles COMPANY_NAME")
            sys.exit(1)

    elif args.command == "push":
        if not args.company or not args.role:
            print("Error: --company and --role required")
            print("Usage: python scripts/api_tools.py push --company TestCorp --role 'QA Engineer'")
            sys.exit(1)
        push_workflow(args.company, args.role, use_mock=not args.real, base_url=args.url)

    elif args.command == "status":
        if not args.id:
            print("Error: --id required")
            print("Usage: python scripts/api_tools.py status --id WORKFLOW_ID")
            sys.exit(1)
        get_status(args.id, args.url)


if __name__ == "__main__":
    main()
