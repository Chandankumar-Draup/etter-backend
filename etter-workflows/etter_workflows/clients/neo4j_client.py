"""
Neo4j client for Etter Workflows.

Provides graph database operations for:
- CompanyRole node creation
- Document linking
- Assessment storage
- Query operations

This client is designed to be a thin wrapper that can either:
1. Use the existing Neo4jConnection from draup_world_model (when available)
2. Use a standalone Neo4j connection (for isolated testing/deployment)
"""

import logging
from typing import Any, Dict, List, Optional
from functools import lru_cache

from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j client for workflow operations.

    This client provides methods for common graph operations needed
    by the self-service pipeline.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        use_existing_connection: bool = True,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j URI (defaults to settings)
            user: Neo4j username (defaults to settings)
            password: Neo4j password (defaults to settings)
            database: Neo4j database (defaults to settings)
            use_existing_connection: Try to use existing Neo4jConnection
        """
        settings = get_settings()
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database
        self._driver = None
        self._external_conn = None

        # Try to use existing connection from draup_world_model
        if use_existing_connection:
            try:
                from draup_world_model.connectors.neo4j_connection import Neo4jConnection
                self._external_conn = Neo4jConnection()
                logger.info("Using existing Neo4jConnection from draup_world_model")
            except ImportError:
                logger.info("draup_world_model not available, using standalone connection")
            except Exception as e:
                logger.warning(f"Failed to initialize Neo4jConnection: {e}")

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._external_conn:
            return self._external_conn

        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                settings = get_settings()
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_lifetime=settings.neo4j_max_connection_lifetime,
                    max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                )
                logger.info(f"Connected to Neo4j at {self.uri}")
            except ImportError:
                raise ImportError("neo4j package not installed. Install with: pip install neo4j")

        return self._driver

    def execute_read_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dicts
        """
        if self._external_conn:
            return self._external_conn.execute_read_query(query, parameters or {})

        driver = self._get_driver()
        with driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dicts
        """
        if self._external_conn:
            return self._external_conn.execute_write_query(query, parameters or {})

        driver = self._get_driver()
        with driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def create_company_role(
        self,
        company_name: str,
        role_name: str,
        draup_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create or find a CompanyRole node.

        Args:
            company_name: Company name
            role_name: Role name
            draup_role: Draup standardized role name
            metadata: Additional metadata for the node (flattened to properties)

        Returns:
            CompanyRole ID
        """
        # Generate consistent ID
        company_role_id = f"{company_name}_{role_name}".replace(" ", "_").replace(".", "_").replace(",", "_").lower()

        # Check if exists first
        find_query = """
        MATCH (cr:CompanyRole {company_name: $company_name, role_name: $role_name})
        RETURN cr.id as company_role_id
        """

        result = self.execute_read_query(find_query, {
            "company_name": company_name,
            "role_name": role_name,
        })

        if result:
            logger.info(f"Found existing CompanyRole: {result[0]['company_role_id']}")
            return result[0]["company_role_id"]

        # Extract metadata fields (Neo4j only accepts primitive types, not Maps)
        meta = metadata or {}
        created_by = meta.get("created_by", "system")
        trace_id = meta.get("trace_id", "")
        source = meta.get("source", "self_service_pipeline")

        # Create new CompanyRole with flattened properties
        create_query = """
        MERGE (cr:CompanyRole {id: $company_role_id})
        ON CREATE SET
            cr.company_name = $company_name,
            cr.role_name = $role_name,
            cr.draup_role = $draup_role,
            cr.created_at = datetime(),
            cr.created_by = $created_by,
            cr.trace_id = $trace_id,
            cr.source = $source
        ON MATCH SET
            cr.draup_role = COALESCE($draup_role, cr.draup_role),
            cr.updated_at = datetime()
        RETURN cr.id as company_role_id
        """

        result = self.execute_write_query(create_query, {
            "company_role_id": company_role_id,
            "company_name": company_name,
            "role_name": role_name,
            "draup_role": draup_role or role_name,
            "created_by": created_by,
            "trace_id": trace_id,
            "source": source,
        })

        if result:
            logger.info(f"Created/updated CompanyRole: {company_role_id}")
            return company_role_id
        else:
            raise Exception(f"Failed to create CompanyRole for {role_name} at {company_name}")

    def link_job_description(
        self,
        company_role_id: str,
        jd_content: str,
        jd_title: Optional[str] = None,
        source: str = "self_service",
    ) -> bool:
        """
        Link a job description to a CompanyRole.

        Args:
            company_role_id: CompanyRole ID
            jd_content: Job description content (markdown)
            jd_title: Optional title for the JD
            source: Source of the JD

        Returns:
            True if successful
        """
        query = """
        MATCH (cr:CompanyRole {id: $company_role_id})
        MERGE (jd:JobDescription {company_role_id: $company_role_id})
        ON CREATE SET
            jd.content = $content,
            jd.title = $title,
            jd.source = $source,
            jd.created_at = datetime()
        ON MATCH SET
            jd.content = $content,
            jd.title = COALESCE($title, jd.title),
            jd.updated_at = datetime()
        MERGE (cr)-[:HAS_JOB_DESCRIPTION]->(jd)
        RETURN jd
        """

        result = self.execute_write_query(query, {
            "company_role_id": company_role_id,
            "content": jd_content,
            "title": jd_title,
            "source": source,
        })

        return len(result) > 0

    def get_company_role(
        self,
        company_name: str,
        role_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a CompanyRole by company and role name.

        Args:
            company_name: Company name
            role_name: Role name

        Returns:
            CompanyRole dict or None
        """
        query = """
        MATCH (cr:CompanyRole {company_name: $company_name, role_name: $role_name})
        OPTIONAL MATCH (cr)-[:HAS_JOB_DESCRIPTION]->(jd:JobDescription)
        RETURN cr, jd
        """

        result = self.execute_read_query(query, {
            "company_name": company_name,
            "role_name": role_name,
        })

        if result:
            return result[0]
        return None

    def company_role_exists(self, company_name: str, role_name: str) -> bool:
        """Check if a CompanyRole exists."""
        return self.get_company_role(company_name, role_name) is not None

    def close(self):
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
        if self._external_conn:
            self._external_conn.close()
            self._external_conn = None


# Singleton client instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get the singleton Neo4j client instance.

    Returns:
        Neo4jClient instance
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


def reset_neo4j_client():
    """Reset the singleton client (for testing)."""
    global _neo4j_client
    if _neo4j_client:
        _neo4j_client.close()
    _neo4j_client = None
