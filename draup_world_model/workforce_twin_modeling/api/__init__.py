"""
Workforce Twin Modeling — API Package
======================================
Exposes the combined router for integration with the outer etter_app,
and factory functions for standalone operation.

Integration:
    from workforce_twin_modeling.api import router as workforce_twin_router
    app.include_router(workforce_twin_router)
"""
from workforce_twin_modeling.api.app import router, create_app, get_app

__all__ = ["router", "create_app", "get_app"]
