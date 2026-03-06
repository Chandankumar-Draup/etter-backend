"""
Data models for the Workforce Twin simulation.
Each class maps to one of the 7 primary stocks.
Principle: dataclasses are the stocks — simple containers with clear boundaries.
"""
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Stock 1: Task Classification State (Three Layers)
# ============================================================

@dataclass
class Task:
    """Single task within a workload. The atomic unit of classification."""
    task_id: str
    workload_id: str
    task_name: str
    category: str                       # directive|feedback_loop|task_iteration|learning|validation|negligibility
    effort_hours_month: float           # hours per person per month on this task
    automatable_by_tool: Optional[str]  # tool name or None
    compliance_mandated_human: bool     # regulatory floor — cannot be automated

    # Three-layer classification (computed by gap engine)
    l1_etter_potential: float = 0.0     # theoretical automation % (from category defaults)
    l2_achievable: float = 0.0         # achievable given org tech stack
    l3_realized: float = 0.0          # actually automated today

    @property
    def adoption_gap(self) -> float:
        """Tool deployed but not fully used. Free money."""
        return max(0.0, self.l2_achievable - self.l3_realized)

    @property
    def capability_gap(self) -> float:
        """Need new tools to reach potential."""
        return max(0.0, self.l1_etter_potential - self.l2_achievable)

    @property
    def total_gap(self) -> float:
        """Total distance from ceiling to floor."""
        return max(0.0, self.l1_etter_potential - self.l3_realized)

    @property
    def freed_hours_at_l2(self) -> float:
        """Hours freed if adoption gap is closed."""
        return self.effort_hours_month * (self.adoption_gap / 100.0)

    @property
    def freed_hours_at_l1(self) -> float:
        """Hours freed if all gaps are closed (theoretical max)."""
        return self.effort_hours_month * (self.total_gap / 100.0)


# ============================================================
# Stock 2: Workforce Capacity
# ============================================================

@dataclass
class Role:
    """A job role with headcount and Etter scores."""
    role_id: str
    role_name: str
    function: str
    sub_function: str
    jfg: str
    job_family: str
    management_level: str
    headcount: int
    avg_salary: float
    automation_score: float         # Etter L1 automation %
    augmentation_score: float       # Etter L1 augmentation %
    quantification_score: float

    @property
    def total_hours_month(self) -> float:
        """Total FTE-hours per month for this role."""
        return self.headcount * 160.0  # 160 hours/month per person

    @property
    def annual_cost(self) -> float:
        """Total annual salary cost for this role."""
        return self.headcount * self.avg_salary

    @property
    def etter_ai_spectrum(self) -> float:
        """Combined AI transformation potential (automation + augmentation)."""
        return self.automation_score + self.augmentation_score


# ============================================================
# Stock 3: Skill Inventory
# ============================================================

@dataclass
class Skill:
    """A skill mapped to a workload with sunrise/sunset classification."""
    skill_id: str
    workload_id: str
    skill_name: str
    skill_type: str             # current|sunrise|sunset
    proficiency_required: int
    is_sunrise: bool
    is_sunset: bool


# ============================================================
# Workload — the bridge between roles and tasks
# ============================================================

@dataclass
class Workload:
    """A workload within a role. Contains tasks, maps to skills."""
    workload_id: str
    role_id: str
    workload_name: str
    time_pct: float             # % of role's total time
    # 6-category distribution (sums to 100)
    directive_pct: float
    feedback_loop_pct: float
    task_iteration_pct: float
    learning_pct: float
    validation_pct: float
    negligibility_pct: float

    @property
    def ai_automatable_pct(self) -> float:
        """% of workload in fully automatable categories (directive + feedback_loop)."""
        return self.directive_pct + self.feedback_loop_pct

    @property
    def augmentable_pct(self) -> float:
        """% in human+AI categories (task_iteration + learning + validation)."""
        return self.task_iteration_pct + self.learning_pct + self.validation_pct

    @property
    def human_only_pct(self) -> float:
        """% that remains human (negligibility)."""
        return self.negligibility_pct


# ============================================================
# Stock 4: Financial Position (computed, not loaded)
# ============================================================

@dataclass
class FinancialSnapshot:
    """Point-in-time financial state for a scope (role, function, org)."""
    scope_id: str
    scope_name: str
    current_annual_cost: float = 0.0
    adoption_gap_savings_potential: float = 0.0  # annual $ if adoption gap closed
    full_gap_savings_potential: float = 0.0      # annual $ if all gaps closed
    investment_required: float = 0.0             # to close adoption gap
    net_opportunity: float = 0.0                 # savings - investment


# ============================================================
# Stock 5: Org Structure (hierarchy for aggregation)
# ============================================================

@dataclass
class OrgNode:
    """A node in the organizational hierarchy. Fractal — same shape at every level."""
    node_id: str
    name: str
    level: str                          # org|function|sub_function|jfg|job_family|role
    parent_id: Optional[str] = None
    children: list = field(default_factory=list)

    # Aggregated metrics (filled during computation)
    headcount: int = 0
    annual_cost: float = 0.0
    avg_automation_score: float = 0.0
    avg_augmentation_score: float = 0.0
    adoption_gap_hours: float = 0.0
    capability_gap_hours: float = 0.0
    total_gap_hours: float = 0.0
    adoption_gap_savings: float = 0.0
    capability_gap_savings: float = 0.0
    compliance_protected_tasks: int = 0
    total_tasks: int = 0


# ============================================================
# Stock 6: Human System
# ============================================================

@dataclass
class HumanSystem:
    """Human readiness state for a function. The binding constraint."""
    function: str
    ai_proficiency: float           # 0-100: can workforce work WITH AI?
    change_readiness: float         # 0-100: willingness to adopt
    trust_level: float              # 0-100: trust in AI tools
    political_capital: float        # 0-100: leadership mandate
    transformation_fatigue: float   # 1-5: how tired of change
    learning_velocity_months: float # months to meaningful proficiency gain

    @property
    def effective_multiplier(self) -> float:
        """Human system multiplier on adoption rates.
        
        Weighted blend (v2): dimensions contribute, not multiply.
        Weights: readiness(0.45) > proficiency(0.35) > trust(0.20)
        Floor at 0.15 — even worst-case orgs have early adopters.
        """
        base = (0.35 * self.ai_proficiency + 0.45 * self.change_readiness + 0.20 * self.trust_level) / 100.0
        return max(0.15, base)


# ============================================================
# Tech Stack
# ============================================================

@dataclass
class Tool:
    """A deployed technology tool."""
    tool_id: str
    tool_name: str
    deployed_to_functions: list      # list of function names (or ["All"])
    task_categories_addressed: list  # list of task categories it can automate
    license_cost_per_user_month: float
    current_adoption_pct: float     # 0-100: how much of deployment is actually used
