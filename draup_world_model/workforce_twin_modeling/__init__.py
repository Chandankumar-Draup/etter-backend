"""
Workforce Twin Modeling — Enterprise Workforce Digital Twin
============================================================
Systems-thinking-based simulation engine for workforce transformation.

Stocks: Roles, Tasks, Skills, Headcount, Financial Position, Human System
Flows:  Cascade propagation, adoption S-curves, feedback loops
Purpose: Simulate and compare workforce redesign scenarios

Integration:
    # As router in outer FastAPI app
    from workforce_twin_modeling.api import router as workforce_twin_router
    app.include_router(workforce_twin_router)

    # Standalone
    from workforce_twin_modeling.api.app import create_app
    app = create_app()
"""

__version__ = "1.0.0"
__author__ = "Etter Architecture Team"
