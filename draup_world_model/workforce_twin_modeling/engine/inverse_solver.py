"""
Inverse Solver Engine
=====================
Given a TARGET outcome (e.g., "reduce HC by 15%"), find the adoption parameters
that produce it. Uses binary search on the adoption alpha parameter, running
the forward simulation at each candidate to evaluate the cost function.

Supported inverse modes:
  - headcount_target:   find alpha that produces target HC reduction %
  - budget_constraint:  find max alpha where cumulative investment ≤ budget
  - automation_target:  find alpha that produces target peak adoption %

Design: Each solver wraps the same binary search core with a different
        metric extraction function. The forward sim is called N times
        (typically 8-12 iterations for 2% tolerance).
"""
import math
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from workforce_twin_modeling.engine.cascade import Stimulus
from workforce_twin_modeling.engine.loader import OrganizationData
from workforce_twin_modeling.engine.rates import SimulationParams, RateParams
from workforce_twin_modeling.engine.feedback import FeedbackParams, HumanSystemState
from workforce_twin_modeling.engine.simulator_fb import simulate_with_feedback, FBSimulationResult


# ============================================================
# Solver Result
# ============================================================

@dataclass
class InverseSolveResult:
    """Result of an inverse solve operation."""
    solved: bool                        # True if target was achievable
    solved_alpha: float                 # the alpha that achieves the target
    achieved_value: float               # actual metric value at solved_alpha
    target_value: float                 # requested target
    error_pct: float                    # |achieved - target| / target * 100
    iterations: int                     # binary search iterations used
    simulation_result: FBSimulationResult  # full sim result at solved_alpha
    feasibility_range: Tuple[float, float]  # (min_achievable, max_achievable)
    message: str                        # human-readable explanation


# ============================================================
# Generic Binary Search Solver
# ============================================================

def _binary_search_alpha(
    run_forward: Callable[[float], FBSimulationResult],
    extract_metric: Callable[[FBSimulationResult], float],
    target_value: float,
    alpha_lo: float = 0.05,
    alpha_hi: float = 0.95,
    tolerance: float = 0.02,
    max_iterations: int = 15,
    monotonic: str = "increasing",
) -> InverseSolveResult:
    """
    Binary search on adoption alpha to find the value that produces the target metric.

    Args:
        run_forward: function that takes alpha and returns a simulation result
        extract_metric: function that pulls the target metric from a sim result
        target_value: the desired metric value
        alpha_lo: lower bound of search range
        alpha_hi: upper bound of search range
        tolerance: acceptable relative error (0.02 = 2%)
        max_iterations: max binary search iterations
        monotonic: "increasing" if metric grows with alpha, "decreasing" if it shrinks

    Returns:
        InverseSolveResult with the best alpha found
    """
    # First, establish feasibility range by evaluating at boundaries
    result_lo = run_forward(alpha_lo)
    result_hi = run_forward(alpha_hi)
    metric_lo = extract_metric(result_lo)
    metric_hi = extract_metric(result_hi)

    feasibility_range = (
        min(metric_lo, metric_hi),
        max(metric_lo, metric_hi),
    )

    # Check feasibility
    if monotonic == "increasing":
        if target_value > metric_hi * (1 + tolerance):
            return InverseSolveResult(
                solved=False,
                solved_alpha=alpha_hi,
                achieved_value=metric_hi,
                target_value=target_value,
                error_pct=abs(metric_hi - target_value) / max(abs(target_value), 0.01) * 100,
                iterations=2,
                simulation_result=result_hi,
                feasibility_range=feasibility_range,
                message=(
                    f"Target {target_value:.1f} exceeds maximum achievable "
                    f"{metric_hi:.1f} at alpha={alpha_hi}. "
                    f"Returning best-effort result at maximum adoption."
                ),
            )
        if target_value < metric_lo * (1 - tolerance):
            return InverseSolveResult(
                solved=True,
                solved_alpha=alpha_lo,
                achieved_value=metric_lo,
                target_value=target_value,
                error_pct=abs(metric_lo - target_value) / max(abs(target_value), 0.01) * 100,
                iterations=2,
                simulation_result=result_lo,
                feasibility_range=feasibility_range,
                message=(
                    f"Target {target_value:.1f} is below minimum "
                    f"{metric_lo:.1f} at alpha={alpha_lo}. "
                    f"Even minimal adoption exceeds the target."
                ),
            )
    else:  # decreasing
        if target_value < metric_hi * (1 - tolerance):
            return InverseSolveResult(
                solved=False,
                solved_alpha=alpha_hi,
                achieved_value=metric_hi,
                target_value=target_value,
                error_pct=abs(metric_hi - target_value) / max(abs(target_value), 0.01) * 100,
                iterations=2,
                simulation_result=result_hi,
                feasibility_range=feasibility_range,
                message=f"Target {target_value:.1f} not achievable. Best: {metric_hi:.1f}.",
            )

    # Binary search
    best_result = result_lo
    best_alpha = alpha_lo
    best_metric = metric_lo
    best_error = abs(metric_lo - target_value)

    lo, hi = alpha_lo, alpha_hi
    iterations = 2  # already did 2 boundary evaluations

    for i in range(max_iterations):
        mid = (lo + hi) / 2.0
        result_mid = run_forward(mid)
        metric_mid = extract_metric(result_mid)
        iterations += 1

        error = abs(metric_mid - target_value)
        if error < best_error:
            best_error = error
            best_result = result_mid
            best_alpha = mid
            best_metric = metric_mid

        # Check convergence
        rel_error = error / max(abs(target_value), 0.01)
        if rel_error <= tolerance:
            return InverseSolveResult(
                solved=True,
                solved_alpha=mid,
                achieved_value=metric_mid,
                target_value=target_value,
                error_pct=rel_error * 100,
                iterations=iterations,
                simulation_result=result_mid,
                feasibility_range=feasibility_range,
                message=f"Solved: alpha={mid:.3f} achieves {metric_mid:.1f} (target {target_value:.1f}, error {rel_error:.1%})",
            )

        # Narrow the search
        if monotonic == "increasing":
            if metric_mid < target_value:
                lo = mid
            else:
                hi = mid
        else:
            if metric_mid > target_value:
                lo = mid
            else:
                hi = mid

    # Exhausted iterations — return best found
    rel_error = best_error / max(abs(target_value), 0.01)
    return InverseSolveResult(
        solved=rel_error <= tolerance * 2,  # lenient on final check
        solved_alpha=best_alpha,
        achieved_value=best_metric,
        target_value=target_value,
        error_pct=rel_error * 100,
        iterations=iterations,
        simulation_result=best_result,
        feasibility_range=feasibility_range,
        message=(
            f"Best after {iterations} iterations: alpha={best_alpha:.3f} "
            f"achieves {best_metric:.1f} (target {target_value:.1f}, "
            f"error {rel_error:.1%})"
        ),
    )


# ============================================================
# Helper: Build a forward sim runner for a given alpha
# ============================================================

def _make_forward_runner(
    stimulus: Stimulus,
    org: OrganizationData,
    base_params: SimulationParams,
    fb_params: FeedbackParams,
    initial_hs: Optional[HumanSystemState] = None,
) -> Callable[[float], FBSimulationResult]:
    """
    Returns a function that runs the forward simulation with a given alpha.
    All other parameters are fixed (captured from the closure).
    """
    def run(alpha: float) -> FBSimulationResult:
        # Clone params with new adoption alpha
        adopt = RateParams(
            alpha=alpha,
            k=base_params.adoption.k if base_params.adoption else 0.3,
            midpoint=base_params.adoption.midpoint if base_params.adoption else 4.0,
            delay_months=base_params.adoption.delay_months if base_params.adoption else 0,
        )

        # Scale expansion and extension proportionally if they exist
        expand = None
        if base_params.expansion:
            scale = alpha / max(0.01, base_params.adoption.alpha) if base_params.adoption else 1.0
            expand = RateParams(
                alpha=min(1.0, base_params.expansion.alpha * scale),
                k=base_params.expansion.k,
                midpoint=base_params.expansion.midpoint,
                delay_months=base_params.expansion.delay_months,
            )

        extend = None
        if base_params.extension:
            scale = alpha / max(0.01, base_params.adoption.alpha) if base_params.adoption else 1.0
            extend = RateParams(
                alpha=min(1.0, base_params.extension.alpha * scale),
                k=base_params.extension.k,
                midpoint=base_params.extension.midpoint,
                delay_months=base_params.extension.delay_months,
            )

        params = SimulationParams(
            scenario_id=base_params.scenario_id,
            scenario_name=base_params.scenario_name,
            adoption=adopt,
            expansion=expand,
            extension=extend,
            policy=base_params.policy,
            absorption_factor=base_params.absorption_factor,
            training_cost_per_person=base_params.training_cost_per_person,
            time_horizon_months=base_params.time_horizon_months,
            hc_review_frequency=base_params.hc_review_frequency,
            reskilling_delay_months=base_params.reskilling_delay_months,
            reskilling_rate=base_params.reskilling_rate,
            enable_workflow_automation=base_params.enable_workflow_automation,
            workflow_automation_bonus=base_params.workflow_automation_bonus,
        )

        return simulate_with_feedback(
            stimulus=stimulus,
            org=org,
            params=params,
            fb_params=fb_params,
            initial_hs=initial_hs,
            trace=False,  # no tracing during search iterations
        )

    return run


# ============================================================
# Solver 1: Headcount Target
# ============================================================

def solve_for_headcount_target(
    target_hc_reduction_pct: float,
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
    fb_params: FeedbackParams = None,
    initial_hs: Optional[HumanSystemState] = None,
    tolerance: float = 0.02,
) -> InverseSolveResult:
    """
    Find the adoption alpha that produces a specific HC reduction percentage.

    Args:
        target_hc_reduction_pct: desired HC reduction as percentage (e.g., 15.0 for 15%)
        stimulus: the stimulus configuration (tools, scope, policy)
        org: organization data
        params: base simulation parameters (alpha will be varied)
        fb_params: feedback loop parameters
        tolerance: acceptable relative error (default 2%)

    Returns:
        InverseSolveResult with the alpha that achieves the target
    """
    if fb_params is None:
        fb_params = FeedbackParams()

    runner = _make_forward_runner(stimulus, org, params, fb_params, initial_hs)

    def extract_hc_reduction(result: FBSimulationResult) -> float:
        """Extract HC reduction % from simulation result."""
        if result.timeline and result.timeline[0].headcount > 0:
            original = result.timeline[0].headcount
            final = result.final_headcount
            return (original - final) / original * 100.0
        return 0.0

    return _binary_search_alpha(
        run_forward=runner,
        extract_metric=extract_hc_reduction,
        target_value=target_hc_reduction_pct,
        alpha_lo=0.05,
        alpha_hi=0.95,
        tolerance=tolerance,
        monotonic="increasing",  # higher alpha → more HC reduction
    )


# ============================================================
# Solver 2: Budget Constraint
# ============================================================

def solve_for_budget_constraint(
    budget_amount: float,
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
    fb_params: FeedbackParams = None,
    initial_hs: Optional[HumanSystemState] = None,
    tolerance: float = 0.02,
) -> InverseSolveResult:
    """
    Find the maximum adoption alpha where cumulative investment stays within budget.

    The solver finds the highest alpha where total_investment ≤ budget_amount.
    This is a constraint satisfaction problem: maximize alpha subject to budget.

    Args:
        budget_amount: maximum total investment allowed ($)
        stimulus: the stimulus configuration
        org: organization data
        params: base simulation parameters
        fb_params: feedback loop parameters
        tolerance: acceptable relative error (default 2%)

    Returns:
        InverseSolveResult with the maximum alpha within budget
    """
    if fb_params is None:
        fb_params = FeedbackParams()

    runner = _make_forward_runner(stimulus, org, params, fb_params, initial_hs)

    def extract_investment(result: FBSimulationResult) -> float:
        """Extract total cumulative investment from simulation result."""
        return result.total_investment

    # For budget: we want investment ≤ budget. Investment increases with alpha.
    # So we search for the alpha where investment = budget (the max affordable alpha).
    return _binary_search_alpha(
        run_forward=runner,
        extract_metric=extract_investment,
        target_value=budget_amount,
        alpha_lo=0.05,
        alpha_hi=0.95,
        tolerance=tolerance,
        monotonic="increasing",  # higher alpha → more investment
    )


# ============================================================
# Solver 3: Automation Target
# ============================================================

def solve_for_automation_target(
    target_automation_pct: float,
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
    fb_params: FeedbackParams = None,
    initial_hs: Optional[HumanSystemState] = None,
    tolerance: float = 0.02,
) -> InverseSolveResult:
    """
    Find the adoption alpha that produces a target peak effective adoption percentage.

    Automation % is measured as the peak effective adoption rate achieved during
    the simulation, which represents the maximum share of addressable work
    that is actually automated.

    Args:
        target_automation_pct: desired automation level (e.g., 35.0 for 35%)
        stimulus: the stimulus configuration
        org: organization data
        params: base simulation parameters
        fb_params: feedback loop parameters
        tolerance: acceptable relative error (default 2%)

    Returns:
        InverseSolveResult with the alpha that achieves the target
    """
    if fb_params is None:
        fb_params = FeedbackParams()

    runner = _make_forward_runner(stimulus, org, params, fb_params, initial_hs)

    def extract_peak_adoption(result: FBSimulationResult) -> float:
        """Extract peak effective adoption % from simulation timeline."""
        if not result.timeline:
            return 0.0
        peak = max(s.effective_adoption_pct for s in result.timeline)
        return peak * 100.0  # convert 0-1 to percentage

    return _binary_search_alpha(
        run_forward=runner,
        extract_metric=extract_peak_adoption,
        target_value=target_automation_pct,
        alpha_lo=0.05,
        alpha_hi=0.95,
        tolerance=tolerance,
        monotonic="increasing",  # higher alpha → higher peak adoption
    )


# ============================================================
# Dispatcher: Route by stimulus_type
# ============================================================

def solve_inverse(
    stimulus_type: str,
    target_value: float,
    stimulus: Stimulus,
    org: OrganizationData,
    params: SimulationParams,
    fb_params: FeedbackParams = None,
    initial_hs: Optional[HumanSystemState] = None,
    tolerance: float = 0.02,
) -> Optional[InverseSolveResult]:
    """
    Dispatch to the appropriate inverse solver based on stimulus_type.

    Args:
        stimulus_type: one of "headcount_target", "budget_constraint",
                       "automation_target", "competitive"
        target_value: the numeric target (%, $, or % depending on type)
        stimulus: stimulus configuration
        org: organization data
        params: base simulation parameters
        fb_params: feedback parameters
        initial_hs: optional initial human system state
        tolerance: convergence tolerance

    Returns:
        InverseSolveResult if the type supports inverse solving, None otherwise
    """
    # Map stimulus_type → (solver_fn, target_kwarg_name)
    solver_map = {
        "headcount_target": (solve_for_headcount_target, "target_hc_reduction_pct"),
        "budget_constraint": (solve_for_budget_constraint, "budget_amount"),
        "automation_target": (solve_for_automation_target, "target_automation_pct"),
        "competitive": (solve_for_automation_target, "target_automation_pct"),
    }

    entry = solver_map.get(stimulus_type)
    if entry is None:
        return None

    solver_fn, target_kwarg = entry
    return solver_fn(
        **{target_kwarg: target_value},
        stimulus=stimulus,
        org=org,
        params=params,
        fb_params=fb_params,
        initial_hs=initial_hs,
        tolerance=tolerance,
    )
