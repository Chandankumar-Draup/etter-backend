"""
Simulation Traceability Engine
================================
When trace=True, the simulator captures a detailed decomposition of every
computation at every timestep. This makes the model fully explainable:

  - WHY did adoption reach X% at month Y?
  - WHICH feedback loop dominated?
  - HOW did each improvement (T1/T2) contribute?
  - WHAT was the HC decision reasoning per role?

Enable:
    result = simulate_with_feedback(..., trace=True)

Access:
    result.trace  → SimulationTrace object

Format:
    from engine.trace import format_trace
    print(format_trace(result.trace))

Export:
    json_str = result.trace.to_json()

Design: Traces are STRUCTURED DATA (dicts), formatted on demand.
  MonthTrace:       per-month decomposition of all computation steps
  SimulationTrace:  full trace + metadata + summaries
  format_trace():   renders human-readable explainability report
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json


# ============================================================
# Data Structures
# ============================================================

@dataclass
class MonthTrace:
    """Complete computation trace for one simulation month.

    Each section is a dict with 'value' and 'detail' keys for structured access.
    The dict format allows adding new trace fields without breaking consumers.
    """
    month: int = 0

    # Section 1: S-Curve input (3 phases + combined)
    s_curve: Dict[str, Any] = field(default_factory=dict)

    # Section 2: Feedback multiplier breakdown (5 multipliers with reasoning)
    multipliers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Section 3: Effective adoption computation
    adoption: Dict[str, Any] = field(default_factory=dict)

    # Section 4: Capacity pipeline state [T2-#10]
    capacity: Dict[str, Any] = field(default_factory=dict)

    # Section 5: Feedback loop deltas (8 loops with component decomposition)
    loop_deltas: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Section 6: HC decision reasoning (per-role detail)
    hc_decision: Dict[str, Any] = field(default_factory=dict)

    # Section 7: Productivity formula decomposition [T1-#1]
    productivity: Dict[str, Any] = field(default_factory=dict)

    # Section 8: Financial breakdown
    financial: Dict[str, Any] = field(default_factory=dict)

    # Section 9: Active improvement annotations
    improvements: List[str] = field(default_factory=list)

    # Which feedback mechanism had the most impact this month
    dominant_loop: str = ""


@dataclass
class SimulationTrace:
    """Full simulation trace with metadata and analysis summaries."""
    scenario_id: str = ""
    scenario_name: str = ""
    stimulus_name: str = ""
    policy: str = ""
    time_horizon: int = 36

    # Initial conditions snapshot
    initial_conditions: Dict[str, Any] = field(default_factory=dict)

    # Per-month traces (one MonthTrace per simulation month)
    months: List[MonthTrace] = field(default_factory=list)

    # Phase dominance analysis (early/mid/late)
    phase_summary: Dict[str, str] = field(default_factory=dict)

    # Per-improvement aggregate impact summary
    improvement_summary: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Export as JSON-serializable dict."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "stimulus": self.stimulus_name,
            "policy": self.policy,
            "time_horizon": self.time_horizon,
            "initial_conditions": self.initial_conditions,
            "months": [
                {
                    "month": mt.month,
                    "s_curve": mt.s_curve,
                    "multipliers": mt.multipliers,
                    "adoption": mt.adoption,
                    "capacity": mt.capacity,
                    "loop_deltas": mt.loop_deltas,
                    "hc_decision": mt.hc_decision,
                    "productivity": mt.productivity,
                    "financial": mt.financial,
                    "improvements": mt.improvements,
                    "dominant_loop": mt.dominant_loop,
                }
                for mt in self.months
            ],
            "phase_summary": self.phase_summary,
            "improvement_summary": self.improvement_summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export as formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ============================================================
# Band Determination Helpers
# ============================================================

def trust_band(trust: float) -> str:
    """Map trust level to regime band name."""
    if trust < 20:
        return "CRISIS(<20)"
    elif trust < 40:
        return "SKEPTICISM(20-40)"
    elif trust < 60:
        return "CAUTIOUS(40-60)"
    return "ENABLER(>=60)"


def capital_band(capital: float) -> str:
    """Map political capital to regime band name."""
    if capital < 20:
        return "BLOCKED(<20)"
    elif capital < 40:
        return "CONSTRAINED(20-40)"
    return "GREEN(>=40)"


# ============================================================
# Dominant Loop Detection
# ============================================================

def determine_dominant_loop(mt: MonthTrace) -> str:
    """Identify which feedback mechanism had the most impact this month.

    Compares multiplier deviations from 1.0 (how much they're constraining/enabling)
    and loop delta magnitudes (how fast state is changing).
    """
    impacts = {}

    # Multiplier deviation from 1.0 (larger = more constraining)
    for name, data in mt.multipliers.items():
        if isinstance(data, dict) and "value" in data:
            impacts[name] = abs(1.0 - data["value"])

    # Loop delta absolute magnitude
    for name, data in mt.loop_deltas.items():
        if isinstance(data, dict) and "value" in data:
            impacts[name] = abs(data["value"])

    if not impacts:
        return "none"
    return max(impacts, key=impacts.get)


# ============================================================
# Phase Summary Computation
# ============================================================

def compute_phase_summary(trace: SimulationTrace) -> Dict[str, str]:
    """Compute loop dominance by phase (early/mid/late).

    Identifies the top 3 mechanisms in each phase by cumulative impact.
    This tells the story of HOW the simulation unfolded.
    """
    n = len(trace.months)

    def _phase_dominant(start: int, end: int) -> str:
        agg: Dict[str, float] = {}
        count = 0
        for i in range(start, min(end + 1, n)):
            mt = trace.months[i]
            for name, data in mt.multipliers.items():
                if isinstance(data, dict) and "value" in data:
                    agg[name] = agg.get(name, 0) + abs(1.0 - data["value"])
            for name, data in mt.loop_deltas.items():
                if isinstance(data, dict) and "value" in data:
                    agg[name] = agg.get(name, 0) + abs(data["value"])
            count += 1
        if not agg:
            return "no data"
        top = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:3]
        return ", ".join(f"{k} ({v / max(count, 1):.3f}/mo)" for k, v in top)

    return {
        "M0-6 (Early — resistance dominates)": _phase_dominant(0, 6),
        "M6-18 (Mid — reinforcing loops emerge)": _phase_dominant(6, 18),
        "M18-36 (Late — diminishing returns)": _phase_dominant(18, min(36, n - 1)),
    }


# ============================================================
# Improvement Impact Summary
# ============================================================

def compute_improvement_summary(trace: SimulationTrace) -> Dict[str, str]:
    """Aggregate per-improvement impact across the full simulation.

    For each T1/T2 improvement, computes how many months it was active
    and its aggregate effect on the simulation.
    """
    summaries = {}
    n = len(trace.months)

    # T1-#1: Productivity Valley
    prod_vals = [mt.productivity.get("index", 100) for mt in trace.months if mt.productivity]
    if prod_vals:
        min_prod = min(prod_vals)
        min_month = next(
            (mt.month for mt in trace.months if mt.productivity.get("index", 100) == min_prod),
            0,
        )
        summaries["T1-#1"] = (
            f"Productivity Valley: low={min_prod:.1f} at M{min_month}"
        )

    # T1-#2: Fatigue from Pace
    peak_fatigue_delta = max(
        (mt.loop_deltas.get("B3_fatigue", {}).get("value", 0) for mt in trace.months),
        default=0,
    )
    fatigue_active = sum(
        1 for mt in trace.months
        if any("T1-#2" in imp for imp in mt.improvements)
    )
    summaries["T1-#2"] = (
        f"Fatigue from pace: peak delta={peak_fatigue_delta:.3f}/mo, "
        f"active {fatigue_active}/{n} months"
    )

    # T1-#3: Rapid Redeployment
    rapid = sum(1 for mt in trace.months if any("T1-#3" in imp for imp in mt.improvements))
    if rapid > 0:
        summaries["T1-#3"] = f"Rapid redeployment: monthly HC reviews active {rapid} months"
    else:
        summaries["T1-#3"] = "Rapid redeployment: inactive (policy != rapid_redeployment)"

    # T1-#4: Workflow Automation Bonus
    bonus_months = sum(
        1 for mt in trace.months if mt.capacity.get("workflow_bonus_active", False)
    )
    if bonus_months > 0:
        bonus_val = trace.months[0].capacity.get("workflow_bonus_value", 1.3) if trace.months else 1.3
        summaries["T1-#4"] = (
            f"Workflow automation bonus: x{bonus_val:.1f} active {bonus_months} months"
        )
    else:
        summaries["T1-#4"] = "Workflow automation bonus: inactive (no extension phase)"

    # T1-#5: License Cost Scaling
    factors = [
        mt.financial.get("license_scale_factor", 1.0) for mt in trace.months
        if mt.financial.get("license_scale_factor") is not None
    ]
    if factors:
        avg_factor = sum(factors) / len(factors)
        summaries["T1-#5"] = f"License cost scaling: avg factor={avg_factor:.3f} (1.0=full cost)"

    # T1-#6: Learning Velocity
    lv = trace.initial_conditions.get("learning_velocity_factor", 1.0)
    summaries["T1-#6"] = f"Learning velocity factor: {lv:.2f} (1.0=baseline, >1.0=faster)"

    # T2-#7: Trust Veto
    veto_months = sum(
        1 for mt in trace.months
        if mt.multipliers.get("human_system", {}).get("veto", False)
    )
    summaries["T2-#7"] = (
        f"Trust veto: active {veto_months} months"
        if veto_months > 0 else "Trust veto: never triggered"
    )

    # T2-#8: Productive Hours
    summaries["T2-#8"] = "Productive hours by level: active all months (IC=128h, Mgr=96h, Dir=72h)"

    # T2-#9: Min Staffing Floor
    floor_hits = sum(
        1 for mt in trace.months
        for rd in mt.hc_decision.get("roles", [])
        if rd.get("floor_hit", False)
    )
    summaries["T2-#9"] = (
        f"Min staffing floor: hit {floor_hits} role-months"
        if floor_hits > 0 else "Min staffing floor: never hit (headcount above 20% floor)"
    )

    # T2-#10: Capacity Delay Pipeline
    delay = trace.initial_conditions.get("capacity_delay", 2)
    summaries["T2-#10"] = f"Capacity delay pipeline: {delay}-month delay on freed hours"

    # T2-#11: Shadow Work Tax
    tax = trace.initial_conditions.get("shadow_work_tax", 10)
    summaries["T2-#11"] = f"Shadow work tax: {tax}% applied to all freed percentages"

    return summaries


# ============================================================
# Human-Readable Formatter
# ============================================================

def format_trace(
    trace: SimulationTrace,
    months: List[int] = None,
    verbose: bool = True,
) -> str:
    """Render simulation trace as a human-readable explainability report.

    Args:
        trace: Full simulation trace data.
        months: Which months to show detail for (None = milestone months).
        verbose: If True, show all sections per month. If False, compact view.

    Returns:
        Multi-line formatted string.
    """
    lines = []
    W = 90

    # ── Header ──
    lines.append(f"\n{'=' * W}")
    lines.append(f"  SIMULATION TRACE: {trace.scenario_id} {trace.scenario_name}")
    lines.append(f"  Stimulus: {trace.stimulus_name}")
    lines.append(f"  Policy: {trace.policy} | Horizon: {trace.time_horizon} months | trace=True")
    lines.append(f"{'=' * W}")

    # ── Initial Conditions ──
    ic = trace.initial_conditions
    if ic:
        lines.append(f"\n  INITIAL CONDITIONS")
        lines.append(f"  {'─' * 70}")
        lines.append(
            f"  Proficiency: {ic.get('proficiency', 0):.1f}  "
            f"Readiness: {ic.get('readiness', 0):.1f}  "
            f"Trust: {ic.get('trust', 0):.1f}"
        )
        lines.append(
            f"  Political Capital: {ic.get('political_capital', 0):.1f}  "
            f"Fatigue: {ic.get('fatigue', 0):.1f}"
        )
        lines.append(
            f"  Learning Velocity Factor: {ic.get('learning_velocity_factor', 1.0):.2f}"
        )
        lines.append(
            f"  Ceiling Freed Hours: {ic.get('ceiling_freed', 0):,.1f}  "
            f"Original HC: {ic.get('original_hc', 0)}"
        )
        lines.append(
            f"  Capacity Delay: {ic.get('capacity_delay', 2)} months [T2-#10]  "
            f"Shadow Work Tax: {ic.get('shadow_work_tax', 10)}% [T2-#11]"
        )

    # ── Select months ──
    if months is None:
        months = [0, 1, 3, 6, 9, 12, 18, 24, 30, 36]
    months = [m for m in months if m < len(trace.months)]

    # ── Per-month detail ──
    for m_idx in months:
        mt = trace.months[m_idx]
        lines.append(f"\n{'─' * W}")
        lines.append(f"  MONTH {mt.month}  |  Dominant: {mt.dominant_loop}")
        lines.append(f"{'─' * W}")

        # S-curve
        sc = mt.s_curve
        if sc:
            lines.append(f"\n  S-CURVE INPUT")
            lines.append(
                f"    Adopt: {sc.get('adopt', 0):.4f}  "
                f"Expand: {sc.get('expand', 0):.4f}  "
                f"Extend: {sc.get('extend', 0):.4f}  "
                f"-> Combined: {sc.get('combined', 0):.4f}"
            )

        # Multipliers
        mults = mt.multipliers
        if mults:
            lines.append(f"\n  FEEDBACK MULTIPLIERS")
            for name, data in mults.items():
                if isinstance(data, dict):
                    lines.append(
                        f"    {name:<18} {data.get('value', 0):.4f}  "
                        f"{data.get('detail', '')}"
                    )

        # Adoption
        ad = mt.adoption
        if ad:
            lines.append(f"\n  EFFECTIVE ADOPTION")
            lines.append(f"    {ad.get('formula', '')}")
            lines.append(
                f"    Effective: {ad.get('effective', 0):.4f}  "
                f"Dampening: {ad.get('dampening_pct', 0):.1f}% of raw"
            )
            lines.append(
                f"    Delta: {ad.get('delta', 0):+.4f}  "
                f"Velocity: {ad.get('velocity', 0):.4f}"
            )
            if ad.get("r3_boost", 0) > 0:
                lines.append(
                    f"    R3 boost: +{ad['r3_boost']:.4f}  "
                    f"Post-R3: {ad.get('effective_post_r3', 0):.4f}"
                )

        # Capacity pipeline (verbose only)
        cap = mt.capacity
        if cap and verbose:
            lines.append(f"\n  CAPACITY PIPELINE [T2-#10]")
            lines.append(
                f"    Gross freed (delta): {cap.get('gross_delta', 0):,.1f}h"
            )
            if cap.get('workflow_bonus_active'):
                lines.append(
                    f"    Workflow bonus: x{cap.get('workflow_bonus_value', 1.0):.1f} applied [T1-#4]"
                )
            lines.append(
                f"    Pipeline: in={cap.get('pipeline_in', 0):,.1f}  "
                f"out={cap.get('pipeline_out', 0):,.1f}  "
                f"(delayed {cap.get('delay', 2)}mo)"
            )
            lines.append(
                f"    Absorption: {cap.get('absorption_rate', 0):.4f}  "
                f"Redistributed: {cap.get('redistributed', 0):,.1f}h  "
                f"Net freed: {cap.get('net_freed', 0):,.1f}h"
            )

        # Loop deltas (verbose only)
        ld = mt.loop_deltas
        if ld and verbose:
            lines.append(f"\n  FEEDBACK LOOP DELTAS (applied to next month)")
            for loop_name, data in ld.items():
                if isinstance(data, dict):
                    lines.append(
                        f"    {loop_name:<18} {data.get('value', 0):+.4f}  "
                        f"{data.get('detail', '')}"
                    )

        # HC Decision
        hc = mt.hc_decision
        if hc and verbose:
            lines.append(f"\n  HC DECISION")
            if hc.get('review_month'):
                lines.append(
                    f"    Review: YES (freq={hc.get('freq', 3)}, "
                    f"policy={hc.get('policy', '?')})"
                )
                cap_ok = hc.get('capital_check')
                if cap_ok is not None:
                    lines.append(
                        f"    Capital: {hc.get('capital_value', 0):.1f} "
                        f"{'≥' if cap_ok else '<'} "
                        f"threshold {hc.get('capital_threshold', 30):.0f} "
                        f"-> {'APPROVED' if cap_ok else 'BLOCKED'}"
                    )
                for rd in hc.get('roles', []):
                    if rd.get('reduced', 0) > 0 or rd.get('floor_hit', False):
                        floor_tag = " FLOOR-HIT" if rd.get('floor_hit') else ""
                        lines.append(
                            f"    {rd.get('role_name', '?')[:40]}: "
                            f"freed={rd.get('fte_freed', 0):.2f} FTE, "
                            f"policy->{rd.get('policy_reducible', 0)}, "
                            f"min_staff={rd.get('min_staffing', 0)}[T2-#9]{floor_tag}, "
                            f"reduced={rd.get('reduced', 0)} "
                            f"({rd.get('hc_before', 0)}->{rd.get('hc_after', 0)})"
                        )
                lines.append(f"    Total reduced this month: {hc.get('total_reduced', 0)}")
            else:
                reason = hc.get('reason', 'not review month')
                lines.append(f"    No action: {reason}")

        # Productivity
        prod = mt.productivity
        if prod:
            lines.append(f"\n  PRODUCTIVITY [T1-#1]")
            lines.append(f"    {prod.get('formula', '')}")

        # Financial (verbose only)
        fin = mt.financial
        if fin and verbose:
            lines.append(f"\n  FINANCIAL")
            lines.append(
                f"    Investment: ${fin.get('monthly_investment', 0):,.0f}  "
                f"({fin.get('investment_detail', '')})"
            )
            lines.append(
                f"    Savings: ${fin.get('monthly_savings', 0):,.0f}/mo  "
                f"Cumulative net: ${fin.get('cumulative_net', 0):,.0f}"
            )

        # Improvements
        impr = mt.improvements
        if impr:
            lines.append(f"\n  ACTIVE IMPROVEMENTS")
            for imp in impr:
                lines.append(f"    {imp}")

    # ── Phase Summary ──
    ps = trace.phase_summary
    if ps:
        lines.append(f"\n{'=' * W}")
        lines.append(f"  LOOP DOMINANCE BY PHASE")
        lines.append(f"  {'─' * 70}")
        for phase, desc in ps.items():
            lines.append(f"  {phase}")
            lines.append(f"    {desc}")

    # ── Improvement Summary ──
    ims = trace.improvement_summary
    if ims:
        lines.append(f"\n{'=' * W}")
        lines.append(f"  IMPROVEMENT IMPACT SUMMARY")
        lines.append(f"  {'─' * 70}")
        for imp_id in sorted(ims.keys()):
            lines.append(f"  {imp_id}: {ims[imp_id]}")

    lines.append(f"\n{'=' * W}")
    lines.append(f"  END OF TRACE")
    lines.append(f"{'=' * W}")

    return "\n".join(lines)
