#!/usr/bin/env python3
"""
Workforce Twin — Start API Server
===================================
Launches the FastAPI backend on port 8000.
Frontend dev server runs separately via `cd ui && npm run dev`.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    import uvicorn
    print("\n  Workforce Twin by Etter — Starting API Server")
    print("  " + "=" * 50)
    print(f"  API:     http://localhost:8000/api/health")
    print(f"  Docs:    http://localhost:8000/docs")
    print(f"  UI Dev:  cd ui && npm run dev")
    print("  " + "=" * 50 + "\n")
    uvicorn.run("workforce_twin_modeling.api.app:get_app", host="0.0.0.0", port=8000, reload=True, factory=True)
