"""
Test script for Etter Workflows API.

Supports both local development and QA environment testing.

Usage:
    # Local testing (default)
    python test_api.py

    # QA testing
    python test_api.py --qa

    # Custom URL
    python test_api.py --url http://localhost:7071
"""

import argparse
import requests
import time
import sys

# =============================================================================
# Configuration
# =============================================================================

# Environment configurations
ENVIRONMENTS = {
    "local": {
        "base_url": "http://localhost:7071",
        "pipeline_prefix": "/api/v1/pipeline",
        "token": None,  # No auth for local
    },
    "qa": {
        "base_url": "https://qa-etter.draup.technology",
        "pipeline_prefix": "/api/v1/pipeline",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzcxMTQ4MDQ2LCJqdGkiOiI3NTc2NzYxNS1kZDk1LTQ4NmEtYjhjMy1kYzg2ZTMwN2ZhMjUifQ.BrP4aQ2P5ZF2x1jK10vgh015y4amcFyAFKv700roGLI",
    },
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

# Test Data
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
]


class APITester:
    """API testing helper class."""

    def __init__(self, base_url: str, pipeline_prefix: str, token: str = None):
        self.base_url = base_url
        self.pipeline_prefix = pipeline_prefix
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.pipeline_prefix}{path}"

    def test_health(self) -> bool:
        """Test health endpoint."""
        print("\n" + "=" * 60)
        print("HEALTH CHECK")
        print("=" * 60)

        try:
            response = requests.get(self._url("/health"), headers=self.headers, timeout=10)
            print(f"Status: {response.status_code}")
            result = response.json()
            print(f"Response: {result}")

            if "components" in result:
                print("\nComponent Status:")
                for comp, status in result["components"].items():
                    status_icon = "[OK]" if status == "healthy" else "[!!]"
                    print(f"  {status_icon} {comp}: {status}")

            return response.status_code == 200
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: Could not connect to {self.base_url}")
            print(f"  {e}")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def test_single_role(self, use_mock: bool = True) -> str:
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
        print(f"Mock mode: {use_mock}")

        try:
            response = requests.post(
                self._url(f"/push?use_mock={str(use_mock).lower()}"),
                headers=self.headers,
                json=payload,
                timeout=30
            )

            print(f"\nStatus: {response.status_code}")
            result = response.json()
            print(f"Response: {result}")

            if response.status_code != 200:
                print("Failed to push role!")
                return None

            workflow_id = result.get("workflow_id")
            message = result.get("message", "")
            print(f"\nWorkflow ID: {workflow_id}")
            print(f"Message: {message}")

            # Check if submitted to Temporal
            if "Temporal" in message:
                print("\n[OK] Workflow submitted to Temporal!")
            elif "standalone" in message:
                print("\n[!!] Running in standalone mode (Temporal not available)")

            return workflow_id

        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: {e}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def poll_status(self, workflow_id: str, max_attempts: int = 5, interval: int = 3):
        """Poll workflow status."""
        print(f"\nPolling status for {workflow_id}...")

        for i in range(max_attempts):
            time.sleep(interval)
            try:
                response = requests.get(
                    self._url(f"/status/{workflow_id}"),
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 404:
                    print(f"  [{i+1}/{max_attempts}] Status: 404 (not found in Redis - normal for Temporal mode)")
                    continue

                if response.status_code != 200:
                    print(f"  [{i+1}/{max_attempts}] Error: {response.status_code}")
                    continue

                status = response.json()
                state = status.get("status", "unknown")
                step = status.get("current_step", "N/A")
                progress = status.get("progress", {})

                print(f"  [{i+1}/{max_attempts}] State: {state}, Step: {step}, "
                      f"Progress: {progress.get('current', 0)}/{progress.get('total', 0)}")

                if state in ["ready", "failed", "validation_error"]:
                    print(f"\nFinal status: {state}")
                    if status.get("error"):
                        print(f"Error: {status['error']}")
                    if status.get("role_id"):
                        print(f"Role ID: {status['role_id']}")
                    return status

            except Exception as e:
                print(f"  [{i+1}/{max_attempts}] Error: {e}")

        print("\nStatus polling completed (workflow may still be running)")
        return None

    def test_companies(self) -> bool:
        """Test companies endpoint."""
        print("\n" + "=" * 60)
        print("COMPANIES LIST")
        print("=" * 60)

        try:
            response = requests.get(self._url("/companies"), headers=self.headers, timeout=10)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"Companies: {result.get('companies', [])}")
                print(f"Total: {result.get('total_count', 0)}")
            else:
                print(f"Error: {response.text}")

            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Test Etter Workflows API")
    parser.add_argument("--qa", action="store_true", help="Use QA environment")
    parser.add_argument("--url", type=str, help="Custom base URL (e.g., http://localhost:7071)")
    parser.add_argument("--no-mock", action="store_true", help="Run real workflows (not mock)")
    parser.add_argument("--health-only", action="store_true", help="Only run health check")
    parser.add_argument("--no-poll", action="store_true", help="Skip status polling")
    args = parser.parse_args()

    # Determine configuration
    if args.url:
        config = {
            "base_url": args.url,
            "pipeline_prefix": "/api/v1/pipeline",
            "token": ENVIRONMENTS["qa"]["token"] if args.qa else None,
        }
        env_name = f"Custom ({args.url})"
    elif args.qa:
        config = ENVIRONMENTS["qa"]
        env_name = "QA"
    else:
        config = ENVIRONMENTS["local"]
        env_name = "Local"

    # Print header
    print("=" * 60)
    print("ETTER WORKFLOWS API TEST")
    print("=" * 60)
    print(f"Environment: {env_name}")
    print(f"Base URL: {config['base_url']}{config['pipeline_prefix']}")
    print(f"Auth: {'Yes' if config.get('token') else 'No'}")
    print(f"Company: {TEST_COMPANY}")
    print("=" * 60)

    # Create tester
    tester = APITester(
        base_url=config["base_url"],
        pipeline_prefix=config["pipeline_prefix"],
        token=config.get("token"),
    )

    # Run tests
    health_ok = tester.test_health()

    if not health_ok:
        print("\n[!!] Health check failed!")
        if not args.qa:
            print("\nMake sure the server is running:")
            print("  cd /home/user/etter-backend")
            print("  python -m uvicorn settings.server:etter_app --host 0.0.0.0 --port 7071")
        sys.exit(1)

    if args.health_only:
        print("\n[OK] Health check passed!")
        sys.exit(0)

    # Test companies
    tester.test_companies()

    # Test single role push
    print("\n\nStarting single role test...")
    use_mock = not args.no_mock
    workflow_id = tester.test_single_role(use_mock=use_mock)

    # Poll status (if requested and workflow was created)
    if workflow_id and not args.no_poll:
        tester.poll_status(workflow_id)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Environment: {env_name}")
    print(f"Health: {'OK' if health_ok else 'FAILED'}")
    print(f"Workflow ID: {workflow_id or 'N/A'}")
    print("=" * 60)

    if workflow_id:
        print("\nTo check workflow status in Temporal UI:")
        if args.qa:
            print("  kubectl port-forward svc/qa-etter-temporal-client-web -n etter-temporal 8080:8080")
        else:
            print("  Open http://localhost:8080 (if Temporal UI is running)")
        print(f"  Look for workflow ID: {workflow_id}")


if __name__ == "__main__":
    main()
