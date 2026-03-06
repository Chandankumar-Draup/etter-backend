"""
Phase 2 orchestration: Load generated data into Neo4j.

SAFETY: Uses DTNeo4jConfig (DT_NEO4J_* env vars) so it NEVER
accidentally connects to the production database.  Defaults target
the local Docker Neo4j instance (docker-compose.yml).

Usage:
    python -m draup_world_model.digital_twin.scripts.load_graph
    python -m draup_world_model.digital_twin.scripts.load_graph --drop-first
    python -m draup_world_model.digital_twin.scripts.load_graph --validate-only
    python -m draup_world_model.digital_twin.scripts.load_graph --neo4j-uri bolt://host:7687
"""

import argparse
import json
import logging
import sys

from draup_world_model.digital_twin.config import (
    DTNeo4jConfig,
    OutputConfig,
    get_dt_neo4j_connection,
)
from draup_world_model.digital_twin.graph.loader import GraphLoader
from draup_world_model.digital_twin.graph.aggregation import AggregationEngine
from draup_world_model.digital_twin.graph.validator import GraphValidator
from draup_world_model.digital_twin.graph.schema import drop_all_dt_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Load Digital Twin data into Neo4j")
    parser.add_argument("--drop-first", action="store_true", help="Drop all DT data before loading")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation, no loading")
    parser.add_argument("--skip-aggregation", action="store_true", help="Skip aggregation step")

    # Neo4j connection overrides (defaults → Docker compose values)
    parser.add_argument("--neo4j-uri", default=None, help="Neo4j bolt URI (default: DT_NEO4J_URI or bolt://localhost:7687)")
    parser.add_argument("--neo4j-user", default=None, help="Neo4j user (default: DT_NEO4J_USER or neo4j)")
    parser.add_argument("--neo4j-password", default=None, help="Neo4j password (default: DT_NEO4J_PASSWORD or kg123456)")
    parser.add_argument("--neo4j-database", default=None, help="Neo4j database (default: DT_NEO4J_DATABASE or draup)")

    args = parser.parse_args()

    # Build connection config from CLI args (override env vars if provided)
    cfg = DTNeo4jConfig()
    if args.neo4j_uri:
        cfg.uri = args.neo4j_uri
    if args.neo4j_user:
        cfg.user = args.neo4j_user
    if args.neo4j_password:
        cfg.password = args.neo4j_password
    if args.neo4j_database:
        cfg.database = args.neo4j_database

    try:
        conn = get_dt_neo4j_connection(cfg)
    except Exception as e:
        logger.error(f"Cannot connect to Neo4j: {e}")
        logger.error("Is Docker Neo4j running?  →  cd draup_world_model/digital_twin && docker compose up -d")
        sys.exit(1)

    try:
        output = OutputConfig()

        if args.validate_only:
            validator = GraphValidator(conn)
            report = validator.validate()
            readiness = validator.compute_readiness_score()
            print(json.dumps({"validation": report, "readiness": readiness}, indent=2))
            return

        if args.drop_first:
            drop_all_dt_data(conn)

        # Load data
        loader = GraphLoader(conn, output)
        stats = loader.load_all()

        # Aggregation
        if not args.skip_aggregation:
            agg = AggregationEngine(conn)
            agg.run()

        # Validation
        validator = GraphValidator(conn)
        report = validator.validate()
        readiness = validator.compute_readiness_score()

        logger.info(f"Load stats: {json.dumps(stats, indent=2)}")
        logger.info(f"Readiness: {readiness['total_score']}/{readiness['max_score']} ({readiness['status']})")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
