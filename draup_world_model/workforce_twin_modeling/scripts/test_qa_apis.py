#!/usr/bin/env python3
"""
Test script — Verify Workforce Twin APIs on QA backend.

Usage:
    python scripts/test_qa_apis.py
    python scripts/test_qa_apis.py --base https://qa-etter.draup.technology
    python scripts/test_qa_apis.py --base https://qa-etter.draup.technology --token <jwt>
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
    ("GET",  "/health",              None),
    ("GET",  "/companies",           None),
    ("GET",  "/org/functions",       None),
    ("GET",  "/org",                 None),
    ("GET",  "/org/hierarchy",       None),
    ("GET",  "/org/tools",          None),
    ("GET",  "/snapshot",            None),
    ("GET",  "/snapshot/opportunities", None),
    ("GET",  "/simulate/presets",    None),
    ("GET",  "/scenarios/catalog",   None),
]


def test_endpoint(base_url: str, method: str, path: str, body: dict | None,
                  token: str | None) -> dict:
    """Hit one endpoint and return result dict."""
    url = f"{base_url}{API_PREFIX}{path}"
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
            # Parse to verify valid JSON
            parsed = json.loads(resp_body)
            preview = json.dumps(parsed, indent=2)[:200]
            return {
                "path": path, "status": status, "ok": True,
                "elapsed_ms": round(elapsed * 1000),
                "preview": preview,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        err_body = ""
        try:
            err_body = e.read().decode()[:200]
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


def main():
    parser = argparse.ArgumentParser(description="Test Workforce Twin QA APIs")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Backend base URL")
    parser.add_argument("--token", default=None, help="Bearer token for auth")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  Workforce Twin API Test")
    print(f"  Base: {args.base}")
    print(f"  Auth: {'token provided' if args.token else 'no token'}")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    for method, path, body in ENDPOINTS:
        result = test_endpoint(args.base, method, path, body, args.token)
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
    print(f"{'='*60}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
