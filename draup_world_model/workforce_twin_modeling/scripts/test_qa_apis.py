#!/usr/bin/env python3
"""
Test script — Verify Workforce Twin APIs on QA backend.

Usage:
    python scripts/test_qa_apis.py
    python scripts/test_qa_apis.py --base https://qa-etter.draup.technology --token <jwt>
    python scripts/test_qa_apis.py --base https://qa-etter.draup.technology --token <jwt> --company "NTT Data"
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error

# ── Defaults ──
DEFAULT_BASE = "https://qa-etter.draup.technology"
API_PREFIX = "/api/v1/workforce-twin"

# Endpoints to test: (method, path, body_or_None)
ENDPOINTS = [
    ("GET",  "/health",                None),
    ("GET",  "/companies",             None),
    ("GET",  "/org/functions",         None),
    ("GET",  "/org",                   None),
    ("GET",  "/org/hierarchy",         None),
    ("GET",  "/org/tools",             None),
    ("GET",  "/snapshot",              None),
    ("GET",  "/snapshot/opportunities", None),
    ("GET",  "/simulate/presets",      None),
    ("GET",  "/scenarios/catalog",     None),
]


def test_endpoint(base_url: str, method: str, path: str, body: dict | None,
                  token: str | None, company: str | None) -> dict:
    """Hit one endpoint and return result dict."""
    url = f"{base_url}{API_PREFIX}{path}"

    # Append ?company= if specified (overrides token-based resolution)
    if company:
        sep = "&" if "?" in url else "?"
        url += f"{sep}company={urllib.request.quote(company)}"

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            resp_body = resp.read().decode()
            elapsed = time.time() - t0
            parsed = json.loads(resp_body)
            preview = json.dumps(parsed, indent=2)[:300]
            return {
                "path": path, "status": status, "ok": True,
                "elapsed_ms": round(elapsed * 1000),
                "preview": preview,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        err_body = ""
        try:
            err_body = e.read().decode()[:300]
        except Exception:
            pass
        return {
            "path": path, "status": e.code, "ok": False,
            "elapsed_ms": round(elapsed * 1000),
            "error": f"HTTP {e.code}: {e.reason}",
            "detail": err_body,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "path": path, "status": 0, "ok": False,
            "elapsed_ms": round(elapsed * 1000),
            "error": str(e),
        }


def diagnose(base_url: str, token: str | None, company: str | None):
    """Run diagnostic checks before the main test suite."""
    print("── Diagnostics ──\n")

    # 1. Check /companies to see what data folders exist
    result = test_endpoint(base_url, "GET", "/companies", None, token, None)
    if result["ok"]:
        companies = json.loads(
            json.dumps(json.loads(result["preview"])) if isinstance(result["preview"], str)
            else result["preview"]
        )
        # re-fetch full response
        url = f"{base_url}{API_PREFIX}/companies"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                available = data.get("companies", [])
                print(f"  Available companies on server: {available}")
        except Exception:
            available = []
            print(f"  Available companies: (could not parse)")
    else:
        available = []
        print(f"  /companies failed: {result.get('error')}")

    # 2. Check what company the token resolves to (via /health without company override)
    if token:
        result = test_endpoint(base_url, "GET", "/health", None, token, None)
        if result["ok"]:
            print(f"  Token resolves to: (health OK)")
        else:
            detail = result.get("detail", "")
            if "No data for company" in detail:
                # Extract company name from error
                try:
                    err = json.loads(detail)
                    msg = err.get("errors", [err.get("detail", "")])[0]
                    print(f"  Token company mismatch: {msg}")
                except Exception:
                    print(f"  Token issue: {detail}")
            else:
                print(f"  /health failed: {result.get('error')}")

    # 3. If company override is set, check it exists
    if company:
        if company in available:
            print(f"  Company override '{company}' exists on server")
        else:
            print(f"  WARNING: Company override '{company}' NOT in server data: {available}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Test Workforce Twin QA APIs")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Backend base URL")
    parser.add_argument("--token", default=None, help="Bearer token for auth")
    parser.add_argument("--company", default=None,
                        help="Company name override (appends ?company=X to requests)")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  Workforce Twin API Test")
    print(f"  Base:    {args.base}")
    print(f"  Auth:    {'token provided' if args.token else 'no token'}")
    print(f"  Company: {args.company or '(from token / server default)'}")
    print(f"{'='*60}\n")

    # Run diagnostics first
    diagnose(args.base, args.token, args.company)

    # Run endpoint tests
    print("── Endpoint Tests ──\n")
    passed = 0
    failed = 0

    for method, path, body in ENDPOINTS:
        result = test_endpoint(args.base, method, path, body, args.token, args.company)
        icon = "PASS" if result["ok"] else "FAIL"
        print(f"[{icon}] {method:4s} {path}")
        print(f"       Status: {result['status']}  |  {result['elapsed_ms']}ms")
        if result["ok"]:
            print(f"       Response: {result['preview']}")
            passed += 1
        else:
            print(f"       Error: {result.get('error', 'unknown')}")
            if result.get("detail"):
                print(f"       Detail: {result['detail']}")
            failed += 1
        print()

    print(f"{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed and not args.company:
        print()
        print(f"  HINT: The token's company may not match server data.")
        print(f"  Try: --company <name>  to override company resolution.")
        print(f"  Check available companies in diagnostics output above.")
    print(f"{'='*60}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
