"""
Digital Twin UI - Flask application.

Serves the single-page React application and registers the API blueprint.

SAFETY: Uses DTNeo4jConfig (DT_NEO4J_* env vars) so it NEVER
accidentally connects to the production database.

Usage:
    python -m draup_world_model.digital_twin.ui.app
"""

import logging
import os
from pathlib import Path

from flask import Flask

from draup_world_model.digital_twin.config import get_dt_neo4j_connection
from draup_world_model.digital_twin.ui.api import dt_api, init_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

UI_DIR = Path(__file__).parent


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(UI_DIR / "templates"),
        static_folder=str(UI_DIR / "static"),
        static_url_path="/static",
    )
    app.config["JSON_SORT_KEYS"] = False

    # Register API blueprint
    app.register_blueprint(dt_api)

    # Initialize Neo4j connection (uses DT_NEO4J_* env vars, NOT production)
    try:
        conn = get_dt_neo4j_connection()
        init_api(conn)
        logger.info("Neo4j connection established for Digital Twin UI")
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}. API will return errors until connected.")

    # Serve the SPA
    @app.route("/")
    @app.route("/dt")
    @app.route("/dt/<path:path>")
    def serve_spa(path=""):
        from flask import render_template
        return render_template("index.html")

    return app


def main():
    port = int(os.environ.get("DT_UI_PORT", 5001))
    app = create_app()
    logger.info(f"Digital Twin UI starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
