"""
Configuration for Digital Twin data generation.

Centralizes all settings: company profile, LLM parameters,
generation batch sizes, and output paths.

IMPORTANT: Neo4j connection uses DT_NEO4J_* env vars (not NEO4J_*).
This prevents accidental writes to the production graph database.
Defaults point to the local Docker Neo4j instance (docker-compose.yml).
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Package root
PACKAGE_DIR = Path(__file__).parent
DATA_DIR = PACKAGE_DIR / "data"
DOCS_DIR = PACKAGE_DIR / "docs"


# ──────────────────────────────────────────────────────────────
# Neo4j connection (isolated from production)
# ──────────────────────────────────────────────────────────────

@dataclass
class DTNeo4jConfig:
    """Neo4j connection config for the Digital Twin.

    Uses DT_NEO4J_* environment variables (NOT the production NEO4J_* vars).
    Defaults match docker-compose.yml so it works out-of-the-box with Docker.

    To override, set these env vars:
        DT_NEO4J_URI=bolt://localhost:7687
        DT_NEO4J_USER=neo4j
        DT_NEO4J_PASSWORD=kg123456
        DT_NEO4J_DATABASE=draup
    """
    uri: str = os.environ.get("DT_NEO4J_URI", "bolt://localhost:7687")
    user: str = os.environ.get("DT_NEO4J_USER", "neo4j")
    password: str = field(default=None, repr=False)
    database: str = os.environ.get("DT_NEO4J_DATABASE", "draup")

    def __post_init__(self):
        if self.password is None:
            self.password = os.environ.get("DT_NEO4J_PASSWORD", "kg123456")

    def log_connection_target(self):
        """Log where this config points — call before any writes."""
        logger.info("=" * 60)
        logger.info("DIGITAL TWIN NEO4J TARGET")
        logger.info(f"  URI:      {self.uri}")
        logger.info(f"  User:     {self.user}")
        logger.info(f"  Database: {self.database}")
        logger.info("=" * 60)


def get_dt_neo4j_connection(config: DTNeo4jConfig = None):
    """Create a Neo4j connection for the Digital Twin.

    Uses DTNeo4jConfig (DT_NEO4J_* env vars) — NOT the production config.
    This ensures load_graph.py never accidentally writes to production.

    Returns:
        A Neo4j driver-based connection object with execute_read_query/
        execute_write_query methods matching the project's Neo4jConnection API.
    """
    from neo4j import GraphDatabase

    cfg = config or DTNeo4jConfig()
    cfg.log_connection_target()

    class _DTNeo4jConnection:
        """Lightweight Neo4j connection matching the project connector API."""

        def __init__(self, cfg: DTNeo4jConfig):
            self._cfg = cfg
            self.driver = GraphDatabase.driver(
                cfg.uri, auth=(cfg.user, cfg.password)
            )
            # Verify connectivity
            with self.driver.session(database=cfg.database) as session:
                session.run("RETURN 1").single()
            logger.info("Digital Twin Neo4j connection verified.")

        def execute_write_query(self, query: str, parameters: dict = None):
            def _run(tx, q, p):
                result = tx.run(q, p or {})
                return [dict(record) for record in result]
            with self.driver.session(database=self._cfg.database) as session:
                return session.execute_write(lambda tx: _run(tx, query, parameters))

        def execute_read_query(self, query: str, parameters: dict = None):
            def _run(tx, q, p):
                result = tx.run(q, p or {})
                return [dict(record) for record in result]
            with self.driver.session(database=self._cfg.database) as session:
                return session.execute_read(lambda tx: _run(tx, query, parameters))

        def close(self):
            if self.driver:
                self.driver.close()
                logger.info("Digital Twin Neo4j connection closed.")

    return _DTNeo4jConnection(cfg)


@dataclass
class CompanyProfile:
    """Demo company configuration."""
    name: str = "Acme Corporation"
    industry: str = "Insurance"
    sub_industry: str = "Multi-line Insurance (Life, Health, P&C)"
    size: int = 15000
    revenue_millions: int = 8000
    hq_location: str = "Chicago, IL"
    description: str = (
        "A mid-large insurance company offering life, health, and property & casualty "
        "insurance products across the United States. Acme is undergoing digital "
        "transformation with AI adoption across claims, underwriting, and customer service."
    )


@dataclass
class LLMConfig:
    """LLM generation settings optimized for cost."""
    provider: str = "anthropic"
    model: str = "claude-haiku-4-5-20251001"
    temperature: float = 0.3
    max_tokens: int = 16384
    api_key: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")


@dataclass
class GenerationConfig:
    """Batch sizes and generation parameters."""
    # Batch sizes per LLM call (cost optimization)
    roles_per_batch: int = 15
    workloads_per_batch: int = 10
    tasks_per_batch: int = 8
    skills_per_batch: int = 50
    technologies_per_batch: int = 40
    workflows_per_batch: int = 4

    # Target counts
    target_roles_per_family: int = 2
    target_titles_per_role: int = 3
    target_workloads_per_role: int = 4
    target_tasks_per_workload: int = 6
    target_skills_total: int = 250
    target_technologies_total: int = 100
    target_workflows_per_function: int = 8
    target_tasks_per_workflow: int = 12


@dataclass
class OutputConfig:
    """Output file paths.

    Uses per-function directory structure for resilient generation:
      roles/func_claims_management.json, tasks/func_underwriting.json, etc.
    Catalogs (skills, technologies) use a single file per directory.
    Legacy flat-file properties retained for backward-compatible loading.
    """
    base_dir: Path = field(default_factory=lambda: DATA_DIR / "acme_corp")

    def entity_dir(self, entity: str) -> Path:
        """Get directory for an entity type (e.g., 'roles', 'tasks')."""
        return self.base_dir / entity

    def function_file(self, entity: str, function_id: str) -> Path:
        """Get file path for a function-specific entity file."""
        return self.entity_dir(entity) / f"{function_id}.json"

    @property
    def taxonomy_file(self) -> Path:
        return self.base_dir / "taxonomy.json"

    @property
    def skills_catalog_file(self) -> Path:
        """Skill catalog in per-entity directory."""
        return self.entity_dir("skills") / "catalog.json"

    @property
    def technologies_catalog_file(self) -> Path:
        """Technology catalog in per-entity directory."""
        return self.entity_dir("technologies") / "catalog.json"

    # Legacy flat-file properties (backward compat for loading old data)
    @property
    def roles_file(self) -> Path:
        return self.base_dir / "roles.json"

    @property
    def job_titles_file(self) -> Path:
        return self.base_dir / "job_titles.json"

    @property
    def workloads_file(self) -> Path:
        return self.base_dir / "workloads.json"

    @property
    def tasks_file(self) -> Path:
        return self.base_dir / "tasks.json"

    @property
    def skills_file(self) -> Path:
        return self.base_dir / "skills.json"

    @property
    def technologies_file(self) -> Path:
        return self.base_dir / "technologies.json"

    @property
    def workflows_file(self) -> Path:
        return self.base_dir / "workflows.json"

    def ensure_dirs(self):
        """Create output directories including per-entity subdirectories."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for entity in ["roles", "job_titles", "workloads", "tasks",
                        "skills", "technologies", "workflows",
                        "role_skill_mapping"]:
            self.entity_dir(entity).mkdir(parents=True, exist_ok=True)


# Task classification categories (Etter 6-category AI automation potential)
# Categories ordered from most automatable to least automatable
TASK_CLASSIFICATIONS = [
    "directive",        # Fully automatable tasks with minimal human input
    "feedback_loop",    # Automatable tasks requiring feedback adjustments
    "learning",         # Tasks requiring knowledge acquisition and understanding
    "validation",       # Tasks where AI helps verify and improve work
    "task_iteration",   # Tasks needing human-AI collaboration
    "negligibility",    # Tasks that cannot be automated using AI
]

# Automation levels
AUTOMATION_LEVELS = [
    "human_only",
    "human_led",
    "shared",
    "ai_led",
    "ai_only",
]

# Skill lifecycle stages
SKILL_LIFECYCLE = [
    "emerging",     # sunrise - growing demand
    "growing",      # accelerating adoption
    "stable",       # mature, steady demand
    "declining",    # sunset - decreasing relevance
]

# Career bands for job titles
CAREER_BANDS = [
    "entry",        # 0-2 years
    "mid",          # 2-5 years
    "senior",       # 5-10 years
    "lead",         # 8-15 years
    "principal",    # 12-20 years
    "director",     # 15+ years
    "vp",           # 18+ years
    "c_suite",      # 20+ years
]

# Skill categories
SKILL_CATEGORIES = [
    "technical",
    "analytical",
    "domain",
    "leadership",
    "communication",
    "digital",
    "regulatory",
]

# Technology categories
TECHNOLOGY_CATEGORIES = [
    "ai_ml",
    "automation_rpa",
    "analytics_bi",
    "cloud_infrastructure",
    "crm_customer",
    "erp_enterprise",
    "communication_collaboration",
    "security_compliance",
    "industry_specific",
    "development_tools",
]


# ──────────────────────────────────────────────────────────────
# Simulation Configuration (Phase 3.9)
# ──────────────────────────────────────────────────────────────
# Every previously-hardcoded constant is now a configurable parameter
# with a sensible default that matches the original v1 behavior.

@dataclass
class CascadeConfig:
    """Parameters for the 8-step cascade engine.

    Controls how automation scores are computed, how freed capacity
    propagates to roles, and how risks are assessed.
    """
    # Step 2: Workload automation score thresholds
    workload_level_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "ai_led": 80.0,
        "shared": 50.0,
        "human_led": 20.0,
    })

    # Step 3: Career-band impact factors (entry roles see more automation impact)
    level_impact_factors: Dict[str, float] = field(default_factory=lambda: {
        "entry": 1.4,
        "mid": 1.2,
        "senior": 1.0,
        "lead": 0.8,
        "principal": 0.6,
        "director": 0.4,
        "vp": 0.3,
        "c_suite": 0.2,
    })

    # Step 3: Transformation index multiplier (freed_pct × this, capped at 100)
    transformation_index_multiplier: float = 1.5

    # Step 4: Sunset skill threshold (fraction of affected tasks)
    sunset_skill_task_fraction: float = 0.3

    # Step 5: Redeployability rate (fraction of freed workers that can be redeployed)
    redeployability_pct: float = 60.0

    # Step 6: Fraction of affected headcount needing reskilling
    reskilling_fraction: float = 0.3

    # Step 7: Risk thresholds
    risk_high_automation_pct: float = 60.0
    risk_workforce_reduction_pct: float = 20.0
    risk_skill_gap_count: int = 5
    risk_broad_change_tasks: int = 50


@dataclass
class FinancialConfig:
    """Financial model parameters.

    Controls cost estimation including technology costs, reskilling,
    change management, severance, and the productivity J-curve.
    """
    # Reskilling
    reskilling_cost_per_skill_per_person: float = 2500.0
    reskilling_timeline_months: Dict[str, int] = field(default_factory=lambda: {
        "technical": 6,
        "analytical": 4,
        "domain": 3,
        "leadership": 8,
        "communication": 2,
        "digital": 5,
        "regulatory": 4,
    })

    # Band cost multipliers for reskilling (senior costs more to retrain)
    band_cost_multiplier: Dict[str, float] = field(default_factory=lambda: {
        "entry": 0.7,
        "mid": 1.0,
        "senior": 1.3,
        "lead": 1.5,
        "principal": 1.8,
        "director": 2.0,
        "vp": 2.5,
    })

    # Technology licensing cost tiers (USD per user per month)
    license_cost_tiers: Dict[str, float] = field(default_factory=lambda: {
        "low": 10.0,
        "medium": 30.0,
        "high": 75.0,
        "enterprise": 150.0,
    })
    implementation_cost_factor: float = 0.15  # fraction of total licensing

    # Change management (fraction of gross savings allocated to change mgmt)
    change_management_pct: float = 5.0

    # Severance (months of salary per separated employee)
    severance_months: float = 3.0

    # Productivity J-curve (temporary dip during transition)
    j_curve_dip_pct: float = 15.0        # % productivity drop
    j_curve_duration_months: int = 6      # months of dip
    j_curve_enabled: bool = False         # off by default for v1 compat

    # Technology cost for role redesign (when no specific tech is selected)
    # Estimated as: affected_headcount × this rate × timeline_months
    default_tech_cost_per_user_month: float = 25.0
    include_tech_cost_in_role_redesign: bool = True


@dataclass
class OrganizationProfile:
    """Organization-specific parameters.

    Models the human and organizational factors that affect how
    automation interventions actually play out in an enterprise.
    """
    # Workforce dynamics
    base_annual_attrition_pct: float = 12.0
    avg_hiring_time_months: float = 3.0

    # Human factors initial conditions (for v2 time-stepping)
    initial_resistance: float = 0.6
    initial_morale: float = 0.7
    initial_ai_proficiency: float = 0.1
    initial_culture_readiness: float = 0.3
    culture_time_constant_months: int = 24

    # Risk appetite
    max_headcount_reduction_pct: float = 100.0  # no cap by default
    max_roles_redesigned_pct: float = 100.0     # no cap by default
    protected_roles: List[str] = field(default_factory=list)


@dataclass
class SimulationConfig:
    """Master configuration for all simulation parameters.

    Pass this to ScenarioManager or individual simulations to override
    any default. All fields have sensible defaults matching v1 behavior.

    Usage:
        # Use all defaults (v1 behavior)
        config = SimulationConfig()

        # Override specific parameters
        config = SimulationConfig(
            cascade=CascadeConfig(redeployability_pct=50.0),
            financial=FinancialConfig(change_management_pct=8.0),
        )

        # Pass to scenario manager
        manager = ScenarioManager(conn, simulation_config=config)
    """
    cascade: CascadeConfig = field(default_factory=CascadeConfig)
    financial: FinancialConfig = field(default_factory=FinancialConfig)
    organization: OrganizationProfile = field(default_factory=OrganizationProfile)
    timeline_months: int = 36
