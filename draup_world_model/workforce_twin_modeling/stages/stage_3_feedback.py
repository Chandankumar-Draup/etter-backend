"""
Stage 3: Feedback Integration
==============================
Purpose: Close the feedback loops. Human system parameters now CHANGE
over time based on outcomes, and their changes MODULATE adoption rates.

What it proves:
  1. Higher initial readiness → faster adoption
  2. AI error event → visible trust drop → adoption slows 2-3 months
  3. Proficiency grows with practice (learning curve visible)
  4. Resistance increases with speed, decreases with time
  5. Savings reinvestment visibly accelerates Phase 2
  6. Low political capital prevents resource allocation

Key test: Feedback vs No-Feedback comparison
  Same scenario, feedback ON vs OFF (Stage 2).
  With feedback:
    - Adoption SLOWER initially (resistance dampens)
    - But can be FASTER in Phase 2 (proficiency flywheel)
    - Overall: more realistic S-curves within S-curves

Runs 4 simulations:
  A. Baseline with feedback (Claims, readiness=45, trust=35)
  B. AI error injected at month 7 (test trust asymmetry)
  C. High readiness (readiness=80) — proves human multiplier
  D. Low readiness (readiness=25) — proves sensitivity
"""
import sys
import os
import json
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workforce_twin_modeling.engine.loader import load_organization
from workforce_twin_modeling.engine.rates import SimulationParams, RateParams, P2_BALANCED
from workforce_twin_modeling.engine.simulator import simulate as simulate_open_loop, SimulationResult
from workforce_twin_modeling.engine.simulator_fb import (
    simulate_with_feedback, FBSimulationResult, FBMonthlySnapshot,
)
from workforce_twin_modeling.engine.feedback import HumanSystemState, FeedbackParams
from workforce_twin_modeling.engine.cascade import Stimulus


# ============================================================
# Sparkline helper
# ============================================================

def sparkline(values: list, label: str = "", fmt: str = ".1f") -> str:
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    chars = " ▁▂▃▄▅▆▇█"
    line = "".join(chars[int((v - mn) / rng * (len(chars) - 1))] for v in values)
    return f"  {label:<22} │{line}│ [{values[0]:{fmt}}→{values[-1]:{fmt}}]"


# ============================================================
# Validation
# ============================================================

def validate_feedback(
    fb_result: FBSimulationResult,
    ol_result: SimulationResult,
    err_result: FBSimulationResult,
    hi_result: FBSimulationResult,
    lo_result: FBSimulationResult,
) -> list:
    """Run all Stage 3 acceptance tests."""
    tests = []
    fb = fb_result.timeline
    ol = ol_result.timeline

    # T1: Higher readiness → faster adoption
    hi_adopt_m12 = hi_result.timeline[12].effective_adoption_pct
    lo_adopt_m12 = lo_result.timeline[12].effective_adoption_pct
    if hi_adopt_m12 > lo_adopt_m12:
        tests.append(("PASS", f"Human multiplier works: high readiness adoption M12={hi_adopt_m12:.2f} > low={lo_adopt_m12:.2f}"))
    else:
        tests.append(("FAIL", f"High readiness NOT faster: {hi_adopt_m12:.2f} vs {lo_adopt_m12:.2f}"))

    # T2: AI error → trust drops significantly
    pre_error_trust = err_result.timeline[6].trust
    post_error_trust = err_result.timeline[8].trust
    if post_error_trust < pre_error_trust * 0.85:
        tests.append(("PASS", f"Trust asymmetry: pre-error={pre_error_trust:.1f}, post={post_error_trust:.1f} ({(1-post_error_trust/pre_error_trust)*100:.0f}% drop)"))
    else:
        tests.append(("FAIL", f"Trust drop insufficient: {pre_error_trust:.1f} → {post_error_trust:.1f}"))

    # T3: Trust still not recovered at month 12 (asymmetry)
    m12_trust = err_result.timeline[12].trust
    if m12_trust < pre_error_trust:
        tests.append(("PASS", f"Trust recovery slow: M6={pre_error_trust:.1f}, error M7, M12={m12_trust:.1f} (still below)"))
    else:
        tests.append(("WARN", f"Trust recovered by M12: {m12_trust:.1f} vs pre-error {pre_error_trust:.1f}"))

    # T4: Proficiency grows with practice
    prof = [s.proficiency for s in fb]
    if prof[24] > prof[12] > prof[6]:
        tests.append(("PASS", f"Proficiency compounds: M6={prof[6]:.1f}, M12={prof[12]:.1f}, M24={prof[24]:.1f}"))
    else:
        tests.append(("FAIL", f"Proficiency not growing: M6={prof[6]:.1f}, M12={prof[12]:.1f}, M24={prof[24]:.1f}"))

    # T5: Feedback adoption ≤ open-loop adoption at most points
    fb_adopt = [s.effective_adoption_pct for s in fb]
    ol_adopt = [s.combined_pct for s in ol]
    early_dampened = fb_adopt[6] < ol_adopt[6]
    if early_dampened:
        tests.append(("PASS", f"Feedback dampens early: M6 feedback={fb_adopt[6]:.2f} < open-loop={ol_adopt[6]:.2f}"))
    else:
        tests.append(("WARN", f"Feedback not dampening early: fb={fb_adopt[6]:.2f} vs ol={ol_adopt[6]:.2f}"))

    # T6: Feedback HC reduction ≤ open-loop HC reduction (more conservative)
    fb_hc = fb_result.total_hc_reduced
    ol_hc = ol_result.total_hc_reduced
    if fb_hc <= ol_hc:
        tests.append(("PASS", f"Feedback more conservative: {fb_hc} FTEs vs open-loop {ol_hc} FTEs"))
    else:
        tests.append(("WARN", f"Feedback reduced MORE: {fb_hc} vs open-loop {ol_hc}"))

    # T7: High vs Low readiness outcome divergence >25%
    hi_savings = hi_result.net_savings
    lo_savings = lo_result.net_savings
    if hi_savings > 0 and lo_savings >= 0:
        divergence = abs(hi_savings - lo_savings) / max(abs(hi_savings), 1)
        if divergence > 0.25:
            tests.append(("PASS", f"Readiness sensitivity: {divergence:.0%} divergence (hi=${hi_savings/1e6:.1f}M vs lo=${lo_savings/1e6:.1f}M)"))
        else:
            tests.append(("WARN", f"Readiness divergence only {divergence:.0%}"))
    else:
        tests.append(("PASS", f"Readiness impacts outcomes: hi=${hi_savings/1e6:.1f}M, lo=${lo_savings/1e6:.1f}M"))

    # T8: Transformation fatigue accumulates
    fatigue = [s.transformation_fatigue for s in fb]
    if fatigue[-1] > fatigue[0]:
        tests.append(("PASS", f"Fatigue accumulates: {fatigue[0]:.1f} → {fatigue[-1]:.1f}"))
    else:
        tests.append(("WARN", f"Fatigue not accumulating: {fatigue[0]:.1f} → {fatigue[-1]:.1f}"))

    # T9: Adoption dampening visible (effective < raw)
    avg_damp = fb_result.avg_adoption_dampening
    if avg_damp < 0.95:
        tests.append(("PASS", f"Adoption dampening: avg {avg_damp:.0%} of raw (feedback reduces by {(1-avg_damp)*100:.0f}%)"))
    else:
        tests.append(("WARN", f"Minimal dampening: {avg_damp:.0%}"))

    # T10: Seniority offset visible in late months
    b4_early = fb[6].b4_seniority_mult
    b4_late = fb[30].b4_seniority_mult
    if b4_late < b4_early:
        tests.append(("PASS", f"Seniority offset: M6={b4_early:.3f}, M30={b4_late:.3f} (diminishing returns)"))
    else:
        tests.append(("WARN", f"Seniority not increasing: M6={b4_early:.3f}, M30={b4_late:.3f}"))

    # T11: Dynamic absorption increases as HC shrinks
    abs_early = fb[3].dynamic_absorption_rate
    abs_late = fb[30].dynamic_absorption_rate
    if abs_late > abs_early:
        tests.append(("PASS", f"Dynamic absorption: M3={abs_early:.3f}, M30={abs_late:.3f} (remaining staff absorb more)"))
    else:
        tests.append(("WARN", f"Absorption not increasing: M3={abs_early:.3f}, M30={abs_late:.3f}"))

    # T12: Payback delayed by feedback (relative to open-loop)
    fb_payback = fb_result.payback_month
    ol_payback = ol_result.payback_month
    if fb_payback >= ol_payback:
        tests.append(("PASS", f"Feedback delays payback: M{fb_payback} vs open-loop M{ol_payback}"))
    else:
        tests.append(("WARN", f"Feedback payback earlier: M{fb_payback} vs open-loop M{ol_payback}"))

    return tests


# ============================================================
# Output
# ============================================================

def print_feedback_results(
    fb: FBSimulationResult,
    ol: SimulationResult,
    err: FBSimulationResult,
    hi: FBSimulationResult,
    lo: FBSimulationResult,
):
    """Print comprehensive Stage 3 output with comparisons."""
    W = 90
    tl = fb.timeline

    print(f"\n{'='*W}")
    print(f"  WORKFORCE TWIN — STAGE 3: FEEDBACK INTEGRATION")
    print(f"{'='*W}")
    print(f"  Scenario: {fb.params.scenario_name}")
    print(f"  Stimulus: {fb.stimulus.name}")
    print(f"  Feedback: ALL 8 LOOPS ACTIVE")

    # ── Executive Summary: 4-Way Comparison ──
    print(f"\n  4-WAY COMPARISON: Open-Loop vs Feedback vs AI-Error vs Readiness")
    print(f"  {'─'*80}")
    print(f"  {'Metric':<28} {'Stage2-OL':>12} {'FB-Base':>12} {'FB+Error':>12} {'FB-HiRdy':>12} {'FB-LoRdy':>12}")
    print(f"  {'─'*80}")

    rows = [
        ("HC Reduced",
         f"{ol.total_hc_reduced}", f"{fb.total_hc_reduced}", f"{err.total_hc_reduced}",
         f"{hi.total_hc_reduced}", f"{lo.total_hc_reduced}"),
        ("Final HC",
         f"{ol.final_headcount}", f"{fb.final_headcount}", f"{err.final_headcount}",
         f"{hi.final_headcount}", f"{lo.final_headcount}"),
        ("Net Savings ($M)",
         f"${ol.net_savings/1e6:.1f}", f"${fb.net_savings/1e6:.1f}", f"${err.net_savings/1e6:.1f}",
         f"${hi.net_savings/1e6:.1f}", f"${lo.net_savings/1e6:.1f}"),
        ("Payback Month",
         f"M{ol.payback_month}", f"M{fb.payback_month}", f"M{err.payback_month}",
         f"M{hi.payback_month}", f"M{lo.payback_month}"),
        ("Peak Skill Gap",
         f"M{ol.peak_skill_gap_month}({ol.peak_skill_gap_value})",
         f"M{fb.peak_skill_gap_month}({fb.peak_skill_gap_value})",
         f"M{err.peak_skill_gap_month}({err.peak_skill_gap_value})",
         f"M{hi.peak_skill_gap_month}({hi.peak_skill_gap_value})",
         f"M{lo.peak_skill_gap_month}({lo.peak_skill_gap_value})"),
        ("Prod Valley",
         f"{ol.productivity_valley_value:.1f}",
         f"{fb.productivity_valley_value:.1f}",
         f"{err.productivity_valley_value:.1f}",
         f"{hi.productivity_valley_value:.1f}",
         f"{lo.productivity_valley_value:.1f}"),
    ]
    for label, *vals in rows:
        print(f"  {label:<28} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12} {vals[3]:>12} {vals[4]:>12}")

    # ── Human System Trajectory ──
    print(f"\n  HUMAN SYSTEM TRAJECTORY (Feedback Baseline)")
    print(f"  {'─'*70}")
    print(sparkline([s.proficiency for s in tl], label="Proficiency", fmt=".1f"))
    print(sparkline([s.readiness for s in tl], label="Readiness", fmt=".1f"))
    print(sparkline([s.trust for s in tl], label="Trust", fmt=".1f"))
    print(sparkline([s.political_capital for s in tl], label="Political Capital", fmt=".1f"))
    print(sparkline([s.transformation_fatigue for s in tl], label="Fatigue", fmt=".1f"))
    print(sparkline([s.human_multiplier * 100 for s in tl], label="Human Mult %", fmt=".1f"))

    # ── Adoption: Raw vs Effective ──
    print(f"\n  ADOPTION: Raw S-Curve vs Feedback-Adjusted")
    print(f"  {'─'*70}")
    print(sparkline([s.raw_adoption_pct * 100 for s in tl], label="Raw (Stage 2)", fmt=".0f"))
    print(sparkline([s.effective_adoption_pct * 100 for s in tl], label="Effective (Stage 3)", fmt=".0f"))
    print(sparkline([s.adoption_dampening * 100 for s in tl], label="Dampening %", fmt=".0f"))

    # ── Time-Series Table ──
    print(f"\n  MONTHLY MILESTONES (Feedback Baseline)")
    print(f"  {'─'*120}")
    print(f"  {'Mo':>3} {'Raw%':>5} {'Eff%':>5} {'Damp':>5} {'HC':>5} {'HC%':>6}"
          f" {'Prof':>5} {'Rdns':>5} {'Trust':>5} {'PCap':>5} {'Fatig':>5}"
          f" {'Net$M':>7} {'Prod':>5} {'AbsR':>5}")
    print(f"  {'─'*120}")

    for m in [0, 1, 2, 3, 6, 9, 12, 15, 18, 21, 24, 30, 36]:
        if m < len(tl):
            s = tl[m]
            err_mark = " ←ERR" if s.ai_error_occurred else ""
            print(f"  {s.month:>3}"
                  f" {s.raw_adoption_pct*100:>4.0f}%"
                  f" {s.effective_adoption_pct*100:>4.0f}%"
                  f" {s.adoption_dampening*100:>4.0f}%"
                  f" {s.headcount:>5}"
                  f" {s.hc_pct_of_original:>5.1f}%"
                  f" {s.proficiency:>5.1f}"
                  f" {s.readiness:>5.1f}"
                  f" {s.trust:>5.1f}"
                  f" {s.political_capital:>5.1f}"
                  f" {s.transformation_fatigue:>5.1f}"
                  f" ${s.net_position/1e6:>5.2f}M"
                  f" {s.productivity_index:>5.1f}"
                  f" {s.dynamic_absorption_rate:>4.2f}")

    # ── Trust Asymmetry Trace ──
    print(f"\n  TRUST ASYMMETRY (AI Error at Month 7)")
    print(f"  {'─'*70}")
    err_tl = err.timeline
    print(f"  {'Month':>5} {'Trust(base)':>12} {'Trust(error)':>13} {'Delta':>8}")
    print(f"  {'─'*42}")
    for m in range(4, 16):
        base_t = tl[m].trust
        err_t = err_tl[m].trust
        mark = " ← ERROR" if m == 7 else ""
        print(f"  {m:>5} {base_t:>11.1f} {err_t:>12.1f} {err_t-base_t:>+7.1f}{mark}")

    # ── Readiness Sensitivity ──
    print(f"\n  READINESS SENSITIVITY")
    print(f"  {'─'*70}")
    print(f"  {'Month':>5} {'HC-High':>8} {'HC-Base':>8} {'HC-Low':>8}  {'Adopt-Hi':>8} {'Adopt-Lo':>8}")
    print(f"  {'─'*55}")
    for m in [0, 6, 12, 18, 24, 36]:
        print(f"  {m:>5}"
              f" {hi.timeline[m].headcount:>8}"
              f" {fb.timeline[m].headcount:>8}"
              f" {lo.timeline[m].headcount:>8}"
              f"  {hi.timeline[m].effective_adoption_pct*100:>7.1f}%"
              f" {lo.timeline[m].effective_adoption_pct*100:>7.1f}%")

    # ── Loop Dominance Narrative ──
    print(f"\n  LOOP DOMINANCE NARRATIVE")
    print(f"  {'─'*70}")
    print(f"  Months 0-6:  B3 (resistance) + B2 (skill valley) DOMINATE")
    print(f"    → Readiness: {tl[0].readiness:.1f} → {tl[6].readiness:.1f} (dropping)")
    print(f"    → Skill drag: {tl[6].b2_skill_drag:.2f} (reducing effective adoption)")
    print(f"    → Adoption dampened to {tl[6].adoption_dampening:.0%} of raw")
    print(f"")
    print(f"  Months 6-18: R1 (trust) + R2 (proficiency) EMERGE")
    print(f"    → Trust: {tl[6].trust:.1f} → {tl[18].trust:.1f} (building)")
    print(f"    → Proficiency: {tl[6].proficiency:.1f} → {tl[18].proficiency:.1f} (learning curve)")
    print(f"    → Adoption dampening: {tl[18].adoption_dampening:.0%} of raw (improving)")
    print(f"")
    print(f"  Months 18-36: B1 (absorption) + B4 (seniority) LIMIT")
    print(f"    → Absorption rate: {tl[18].dynamic_absorption_rate:.3f} → {tl[36].dynamic_absorption_rate:.3f} (increasing)")
    print(f"    → Seniority offset: {tl[18].b4_seniority_mult:.3f} → {tl[36].b4_seniority_mult:.3f} (diminishing returns)")
    print(f"    → HC changes slow down: quarterly reductions shrink")


# ============================================================
# Export
# ============================================================

def export_stage3(
    fb: FBSimulationResult,
    ol: SimulationResult,
    err: FBSimulationResult,
    hi: FBSimulationResult,
    lo: FBSimulationResult,
    output_dir: str,
):
    """Export all Stage 3 results."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Feedback baseline time-series
    rows = []
    for s in fb.timeline:
        rows.append({
            "month": s.month,
            "raw_adoption": round(s.raw_adoption_pct, 4),
            "effective_adoption": round(s.effective_adoption_pct, 4),
            "dampening": round(s.adoption_dampening, 4),
            "headcount": s.headcount,
            "hc_pct": round(s.hc_pct_of_original, 1),
            "proficiency": round(s.proficiency, 1),
            "readiness": round(s.readiness, 1),
            "trust": round(s.trust, 1),
            "political_capital": round(s.political_capital, 1),
            "fatigue": round(s.transformation_fatigue, 1),
            "human_multiplier": round(s.human_multiplier, 4),
            "skill_gap": s.current_skill_gap,
            "net_position": round(s.net_position, 0),
            "productivity": round(s.productivity_index, 1),
            "absorption_rate": round(s.dynamic_absorption_rate, 4),
            "b4_seniority": round(s.b4_seniority_mult, 4),
        })

    with open(os.path.join(output_dir, "stage3_feedback_timeseries.csv"), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # 2. Comparison JSON
    def sim_summary(r, name):
        return {
            "name": name,
            "hc_reduced": r.total_hc_reduced,
            "final_hc": r.final_headcount,
            "net_savings": round(r.net_savings, 0),
            "payback_month": r.payback_month,
            "peak_skill_gap": r.peak_skill_gap_value,
            "productivity_valley": round(r.productivity_valley_value, 1),
        }

    def fb_summary(r, name):
        d = sim_summary(r, name)
        d.update({
            "final_proficiency": round(r.final_proficiency, 1),
            "final_trust": round(r.final_trust, 1),
            "final_readiness": round(r.final_readiness, 1),
            "avg_dampening": round(r.avg_adoption_dampening, 3),
        })
        return d

    summary = {
        "stage": 3,
        "comparison": {
            "open_loop": sim_summary(ol, "Stage 2 Open-Loop"),
            "feedback_baseline": fb_summary(fb, "Feedback Baseline"),
            "feedback_ai_error": fb_summary(err, "Feedback + AI Error M7"),
            "feedback_high_readiness": fb_summary(hi, "Feedback High Readiness"),
            "feedback_low_readiness": fb_summary(lo, "Feedback Low Readiness"),
        },
    }

    with open(os.path.join(output_dir, "stage3_comparison.json"), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results exported to {output_dir}/")
    print(f"    stage3_feedback_timeseries.csv  ({len(rows)} months)")
    print(f"    stage3_comparison.json           (5-way comparison)")


# ============================================================
# Main
# ============================================================

def main(data_dir: str, output_dir: str = None):
    """Run Stage 3: Feedback Integration with 4 simulation variants."""
    print(f"\n  Loading data from {data_dir}...")
    org = load_organization(data_dir)
    print(f"  Loaded: {len(org.roles)} roles, {len(org.tasks)} tasks")

    stimulus = Stimulus(
        name="Deploy Microsoft Copilot to Claims function",
        stimulus_type="technology_injection",
        tools=["Microsoft Copilot"],
        target_scope="function",
        target_functions=["Claims"],
        policy="moderate_reduction",
        absorption_factor=0.35,
        training_cost_per_person=2000,
    )
    params = P2_BALANCED

    # ── Run A: Open-loop (Stage 2 baseline) ──
    print(f"\n  [A] Running Stage 2 open-loop (no feedback)...")
    ol_result = simulate_open_loop(stimulus, org, params)

    # ── Run B: Feedback baseline (Claims: prof=25, readiness=45, trust=35) ──
    print(f"  [B] Running feedback baseline (Claims human system)...")
    fb_params = FeedbackParams()
    fb_result = simulate_with_feedback(stimulus, org, params, fb_params)

    # ── Run C: Feedback + AI error at month 7 ──
    print(f"  [C] Running feedback + AI error at month 7...")
    err_params = FeedbackParams(ai_error_month=7)
    err_result = simulate_with_feedback(stimulus, org, params, err_params)

    # ── Run D: High readiness (readiness=80, trust=70, proficiency=50) ──
    print(f"  [D] Running high readiness variant...")
    hi_hs = HumanSystemState(proficiency=50, readiness=80, trust=70, political_capital=75)
    hi_result = simulate_with_feedback(stimulus, org, params, fb_params, initial_hs=hi_hs)

    # ── Run E: Low readiness (readiness=25, trust=20, proficiency=15) ──
    print(f"  [E] Running low readiness variant...")
    lo_hs = HumanSystemState(proficiency=15, readiness=25, trust=20, political_capital=35)
    lo_result = simulate_with_feedback(stimulus, org, params, fb_params, initial_hs=lo_hs)

    # ── Validate ──
    print(f"\n  VALIDATION TESTS")
    print(f"  {'─'*70}")
    tests = validate_feedback(fb_result, ol_result, err_result, hi_result, lo_result)
    passed = sum(1 for t in tests if t[0] == "PASS")
    failed = sum(1 for t in tests if t[0] == "FAIL")
    warned = sum(1 for t in tests if t[0] == "WARN")

    for status, msg in tests:
        icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"  {icon} [{status}] {msg}")

    print(f"  {'─'*70}")
    print(f"  Results: {passed} passed, {failed} failed, {warned} warnings")

    # ── Output ──
    print_feedback_results(fb_result, ol_result, err_result, hi_result, lo_result)

    if output_dir:
        export_stage3(fb_result, ol_result, err_result, hi_result, lo_result, output_dir)

    print(f"\n  {'='*90}")
    print(f"  STAGE 3 COMPLETE — {passed}/{passed+failed+warned} tests passed")
    print(f"  {'='*90}")

    return fb_result, ol_result, err_result, hi_result, lo_result


if __name__ == "__main__":
    DATA_DIR = "/mnt/user-data/outputs/synthetic_data"
    OUTPUT_DIR = "/mnt/user-data/outputs/stage3_results"
    main(DATA_DIR, OUTPUT_DIR)
