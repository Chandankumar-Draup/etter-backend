"""
Settings module for Etter Workflows.

Environment-based configuration with sensible defaults.
All settings can be overridden via environment variables.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Temporal host constants for different environments
TEMPORAL_HOST_QA = "qa-etter-temporal-client-frontend.etter-temporal.svc.cluster.local"
TEMPORAL_HOST_PROD = "prod-etter-temporal-client-frontend.etter-temporal.svc.cluster.local"
TEMPORAL_HOST_LOCAL = "localhost"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings have sensible defaults for development.
    In production, critical settings should be set via environment variables.
    """

    # Environment
    environment: str = Field(
        default="development",
        description="Environment name (development, qa, production)"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )

    # Temporal Configuration
    # Default: localhost for local dev server (temporal server start-dev)
    # SSH Tunnel: localhost:5445 (after SSH tunnel to qa-temporal-client)
    # Production: Direct connection to temporal server
    temporal_host: str = Field(
        default="localhost",
        description="Temporal server host"
    )
    temporal_port: int = Field(
        default=7233,
        description="Temporal server port"
    )
    temporal_namespace: str = Field(
        default="etter-dev",
        description="Temporal namespace"
    )
    temporal_task_queue: str = Field(
        default="etter-workflows",
        description="Temporal task queue name"
    )
    temporal_max_concurrent_activities: int = Field(
        default=5,
        description="Maximum concurrent activities per worker (3-5 for natural throttling)"
    )
    temporal_max_concurrent_workflows: int = Field(
        default=10,
        description="Maximum concurrent workflow task executions"
    )

    # Neo4j Configuration
    # Production Neo4j server for Draup World Model
    neo4j_uri: str = Field(
        default="bolt://draup-world-neo4j.draup.technology:7687",
        description="Neo4j connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: Optional[str] = Field(
        default=None,
        description="Neo4j password (required, set via NEO4J_PASSWORD env var)"
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )
    neo4j_max_connection_lifetime: int = Field(
        default=3600,
        description="Max connection lifetime in seconds"
    )
    neo4j_max_connection_pool_size: int = Field(
        default=50,
        description="Max connection pool size"
    )

    # Redis Configuration
    # Production Redis for status tracking and caching
    redis_host: str = Field(
        default="127.0.0.1",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6390,
        description="Redis port"
    )
    redis_db: int = Field(
        default=3,
        description="Redis database number"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password (set via REDIS_PASSWORD env var)"
    )
    redis_socket_timeout: int = Field(
        default=30,
        description="Redis socket timeout in seconds"
    )
    redis_connect_timeout: int = Field(
        default=30,
        description="Redis connection timeout in seconds"
    )
    redis_retry_on_timeout: bool = Field(
        default=True,
        description="Retry on Redis timeout"
    )
    redis_health_check_interval: int = Field(
        default=30,
        description="Redis health check interval in seconds"
    )
    redis_status_ttl_seconds: int = Field(
        default=86400,
        description="TTL for status cache in Redis (24 hours)"
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8090,
        description="API server port"
    )

    # Workflow API (existing Etter API)
    workflow_api_base_url: str = Field(
        default="http://127.0.0.1:8082",
        description="Base URL for existing workflow API (overridden by draup_world_api_url in qa/prod)"
    )
    workflow_api_timeout: int = Field(
        default=600,
        description="Workflow API timeout in seconds"
    )

    # Automated Workflows API (localhost:8083)
    automated_workflows_api_base_url: str = Field(
        default="http://127.0.0.1:8083",
        description="http://127.0.0.1:8083, Base URL for automated workflows API (overridden by draup_world_api_url in qa/prod)"
    )
    automated_workflows_api_timeout: int = Field(
        default=600,
        description="Automated workflows API timeout in seconds"
    )

    # Draup World API URLs (for qa/prod)
    draup_world_api_prod: str = Field(
        default="https://draup-world.draup.technology/api",
        description="Draup World API URL for production"
    )
    draup_world_api_qa: str = Field(
        default="https://qa-draup-world.draup.technology/api",
        description="Draup World API URL for QA"
    )

    # Etter Backend API URL (for documents, taxonomy endpoints - same server)
    # Since api_providers.py runs inside etter-backend, it calls localhost
    etter_backend_api_url: str = Field(
        default="http://localhost:7071",
        description="Etter Backend API URL for documents/taxonomy (localhost since same server)"
    )

    # Authentication for API calls
    etter_auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for API authentication (ETTER_AUTH_TOKEN)"
    )

    # QA API Configuration (used by api_providers when running locally)
    # In local dev, documents and taxonomy are fetched from QA Etter API
    qa_etter_api_url: str = Field(
        default="https://qa-etter.draup.technology",
        description="QA Etter API URL for documents/taxonomy in local dev"
    )
    qa_auth_token: Optional[str] = Field(
        default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2MywiZXhwIjoxNzczODMwMTQwLCJqdGkiOiIwOTEwMTU2OS05NjNiLTQxOTUtOWMzYi00ZGY3OWMwYWQzMTIifQ.Gtg168kAcxiKrIUpy8GqWxI609tf9pzfrLVGwduxvpY",
        description="QA auth token for local dev API calls (QA_AUTH_TOKEN)"
    )

    # Environment detection (used to determine which API URL to use)
    etter_db_host: str = Field(
        default="",
        description="Database host (used for environment detection)"
    )

    # LLM Configuration
    llm_provider: str = Field(
        default="gemini",
        description="LLM provider (gemini, claude, openai)"
    )
    llm_model: str = Field(
        default="gemini-2.0-flash",
        description="LLM model name"
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="LLM API key"
    )

    # Timeouts (in seconds)
    activity_timeout_short: int = Field(
        default=300,
        description="Timeout for short activities (5 min)"
    )
    activity_timeout_long: int = Field(
        default=1800,
        description="Timeout for long activities (30 min)"
    )
    workflow_timeout: int = Field(
        default=7200,
        description="Timeout for complete workflow (2 hours)"
    )
    heartbeat_timeout: int = Field(
        default=60,
        description="Heartbeat timeout for long-running activities"
    )

    # Rate Limiting
    max_concurrent_workflows_per_company: int = Field(
        default=200,
        description="Max concurrent workflows per company"
    )
    max_queue_depth: int = Field(
        default=1000,
        description="Maximum queue depth before backpressure"
    )

    # Feature Flags
    enable_mock_data: bool = Field(
        default=False,
        description="Use mock data providers instead of real APIs (default: False - use real APIs)"
    )
    enable_status_polling: bool = Field(
        default=True,
        description="Enable status polling endpoints"
    )
    enable_batch_processing: bool = Field(
        default=True,
        description="Enable batch processing endpoint"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars from parent app
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def temporal_address(self) -> str:
        """Get Temporal server address (host:port) using effective host."""
        return f"{self.get_effective_temporal_host()}:{self.temporal_port}"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_temporal_namespace(self) -> str:
        """Get Temporal namespace based on environment."""
        return "etter-dev"
        # if self.is_production:
        #     return "etter-prod"
        # elif self.environment == "qa" or self._is_qa_environment():
        #     return "etter-dev"  # QA uses etter-dev namespace
        # return self.temporal_namespace

    def _is_qa_or_prod_environment(self) -> bool:
        """Check if running in QA or production based on DB host (matches getCurrentEnvironment logic)."""
        db_host = self.etter_db_host.lower() if self.etter_db_host else ""
        # Must have a db_host that is not empty and not localhost
        return bool(db_host and db_host != "localhost" and "127.0.0.1" not in db_host)

    def _is_prod_db(self) -> bool:
        """Check if connected to production database."""
        # First check we're in a deployed environment (not local)
        if not self._is_qa_or_prod_environment():
            return False
        # Then check it's not QA
        db_host = self.etter_db_host.lower()
        return 'dev-gateway' not in db_host and 'qa' not in db_host

    def _is_qa_environment(self) -> bool:
        """Check if running in QA environment based on DB host."""
        # First check we're in a deployed environment (not local)
        if not self._is_qa_or_prod_environment():
            return False
        db_host = self.etter_db_host.lower()
        return 'qa' in db_host or 'dev-gateway' in db_host

    def get_effective_temporal_host(self) -> str:
        """
        Get the effective Temporal host based on environment.

        Priority:
        1. If in production environment (detected via db_host or environment) -> use prod temporal host
        2. If in QA environment (detected via db_host or environment) -> use QA temporal host
        3. Otherwise (local development) -> use temporal_host setting (default: localhost)

        Returns:
            Temporal host string
        """
        # Priority 1: Check for production environment
        if self._is_prod_db() or self.environment == "production":
            return TEMPORAL_HOST_PROD

        # Priority 2: Check for QA environment
        if self._is_qa_environment() or self.environment == "qa":
            return TEMPORAL_HOST_QA

        # Priority 3: Local development - use configured host (default: localhost)
        return self.temporal_host

    def get_temporal_debug_info(self) -> dict:
        """Get debug info about Temporal configuration for logging."""
        return {
            "temporal_host_setting": self.temporal_host,
            "temporal_port": self.temporal_port,
            "effective_temporal_host": self.get_effective_temporal_host(),
            "temporal_address": self.temporal_address,
            "environment": self.environment,
            "etter_db_host": self.etter_db_host,
            "is_qa_environment": self._is_qa_environment(),
            "is_prod_db": self._is_prod_db(),
            "is_qa_or_prod_environment": self._is_qa_or_prod_environment(),
        }

    @property
    def draup_world_api_url(self) -> str:
        """Get Draup World API URL based on environment (matches get_draup_world_api logic)."""
        if self._is_prod_db():
            return self.draup_world_api_prod
        elif self._is_qa_or_prod_environment():
            return self.draup_world_api_qa
        return ""  # Empty means use localhost defaults

    def get_workflow_api_url(self) -> str:
        """Get the effective workflow API URL (Draup World API in qa/prod, localhost in dev)."""
        if self._is_qa_or_prod_environment():
            return self.draup_world_api_url
        return self.workflow_api_base_url

    def get_automated_workflows_api_url(self) -> str:
        """Get the effective automated workflows API URL (Draup World API in qa/prod, localhost in dev)."""
        if self._is_qa_or_prod_environment():
            return self.draup_world_api_url
        return self.automated_workflows_api_base_url

    def get_etter_backend_api_url(self) -> str:
        """
        Get Etter Backend API URL for documents/taxonomy endpoints.

        This is called from within etter-backend itself, so it uses localhost:7071.
        All environments (local, QA, prod) run on the same port.

        Can be overridden via ETTER_BACKEND_API_URL environment variable.
        """
        return self.etter_backend_api_url



@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are cached for performance. To reload, use:
        get_settings.cache_clear()

    Returns:
        Settings instance
    """
    return Settings()


# Convenience function to load settings from env file
def load_settings_from_env(env_file: str = ".env") -> Settings:
    """Load settings from a specific env file."""
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)
    get_settings.cache_clear()
    return get_settings()
