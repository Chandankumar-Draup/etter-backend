# Workforce Twin Model: Stress Test Analysis & Findings

## Executive Summary

The Workforce Twin model was subjected to comprehensive stress testing across 8 categories (41 individual tests). The model demonstrates strong structural integrity — no crashes, no negative headcounts, consistent financial accounting, and proper value clamping. However, **4 significant behavioral issues** were identified that affect model realism.

**Results: 26 PASS, 1 FAIL, 7 WARN, 7 INFO**

---

## System Model Analysis (Stocks, Flows, Feedback Loops)

### What Works Well

1. **S-curve adoption dynamics** — The logistic function produces realistic adoption curves at all tested steepness values (k=0.1 to k=2.0)
2. **Trust asymmetry** — Multiplicative destruction (30% per error) vs additive building produces correct asymmetric behavior. Trust recovery from a single error takes >29 months, consistent with organizational behavior research
3. **Human multiplier** — Outcome divergence between best-case ($10.3M) and worst-case (-$2.2M) human system states spans $12.5M, proving human factors are the binding constraint
4. **Feedback dampening** — Effective adoption runs at ~30-45% of raw S-curve, which is a realistic range for enterprise AI adoption
5. **Quarterly HC decisions** — Prevents unrealistic smooth reductions, creating staircase pattern
6. **Political capital gating** — Low capital (5/100) blocks HC decisions entirely, producing $0 HC reduction even with tools deployed
7. **Conservation laws** — HC never negative, adoption never exceeds raw, cumulative HC reduction monotonically non-decreasing

### The 4 Critical Findings

---

### Finding 1: Productivity Valley Never Materializes

**Stock affected:** Productivity Index
**Expected behavior:** 5-15% dip lasting 3-8 months (per simulation_mvp_plan.md)
**Actual behavior:** Productivity never dips below 100.0 — stays at 100.3-107.9

**Root cause (first principles):**
The productivity formula is:
```
productivity = 100 + automation_lift - skill_drag - fatigue_drag
```
Where:
- `automation_lift = effective_adoption × 15.0` (up to +15%)
- `skill_drag = (1 - b2_drag) × 20.0` (up to -20%)
- `fatigue_drag = fatigue × 0.05` (up to -5%)

**The problem:** `automation_lift` kicks in immediately with any adoption level (even 4% at M0 produces +0.6% lift), while `skill_drag` is tiny because the skill gap percentage relative to total sunrise skills is small. The net effect is always positive.

**Second-order effect:** Without a productivity dip, the model doesn't capture the "Valley of Despair" that is universally observed in technology transitions. This makes the model overly optimistic about the near-term impact of AI deployment.

**Recommendation:**
Add a temporal delay to automation lift — benefits should lag adoption by 3-6 months:
```python
# Delayed automation lift (benefits take time to materialize)
delayed_adoption = timeline[max(0, month - 3)].effective_adoption_pct
automation_lift = delayed_adoption * 15.0
```
Also increase the skill_drag coefficient from 0.5 to 1.5 to create a realistic early-stage drag.

---

### Finding 2: Fatigue Accumulation Is Near-Zero

**Stock affected:** Transformation Fatigue
**Expected behavior:** Meaningful fatigue buildup, especially in aggressive scenarios
**Actual behavior:** Fatigue reaches 0.023 over 36 months (baseline), 0.047 (aggressive)

**Root cause (first principles):**
```
disruption_level = hc_reduced_this_month / total_hc × 10
fatigue_delta = disruption_level × fatigue_build_rate (0.03)
```
HC reduction happens quarterly with ~5-10 people from ~530.
Disruption = 10/530 × 10 ≈ 0.19. Fatigue delta = 0.19 × 0.03 = 0.006/quarter.
After 12 quarters: total fatigue ≈ 0.06, which rounds to 0.0.

**Second-order effect:** Without fatigue, the model cannot differentiate between sustained transformation programs and one-time changes. In reality, organizations experience "change fatigue" that slows later phases of transformation — this is a key balancing loop that the model currently lacks in practice.

**Recommendation:**
Two changes needed:
1. Increase `fatigue_build_rate` from 0.03 to 0.5
2. Make fatigue accumulate from PACE OF CHANGE (adoption velocity), not just HC disruption events:
```python
adoption_pace = max(0, effective_adoption - prev_effective_adoption) * 10
fatigue_delta = (disruption_level + adoption_pace) * fatigue_build_rate
```
Also add fatigue decay (rest periods reduce fatigue):
```python
fatigue_decay = 0.02 * (1 - adoption_level)  # rest when not changing
```

---

### Finding 3: `rapid_redeployment` Policy Not Implemented

**Flow affected:** HC reduction decision logic
**Expected behavior:** P5 (AI-Age Accelerated) should show distinct behavior from P3 (Aggressive)
**Actual behavior:** P5 produces nearly identical results to P3 (79 vs 80 HC reduction, $6.8M each)

**Root cause:**
The simulator's HC decision logic handles 4 policies:
- `no_layoffs` → reducible = 0
- `natural_attrition` → capped at 2% per quarter
- `moderate_reduction` → floor(net_new)
- `active_reduction` → round(net_new)

`rapid_redeployment` falls through to the `else` clause → `floor(net_new)` → same as `moderate_reduction`.

**Second-order effect:** P5 was designed to show non-linear gains from workflow automation. Without a distinct policy, the scenario comparison cannot demonstrate the value proposition of faster redeployment.

**Recommendation:**
Implement as a distinct policy with monthly (not quarterly) HC reviews:
```python
elif params.policy == "rapid_redeployment":
    reducible = round(net_new)  # round up, like active_reduction
    # Also: consider hc_review_frequency=1 for rapid redeployment
```

---

### Finding 4: `workflow_automation_bonus` Never Applied

**Flow affected:** Freed capacity computation
**Expected behavior:** Extension phase (Phase 3) should multiply freed capacity by 1.3×
**Actual behavior:** The `workflow_automation_bonus` parameter is defined but never referenced in the simulation loop

**Root cause:**
`SimulationParams.workflow_automation_bonus = 1.3` for P5, but `simulator_fb.py` computes freed capacity as:
```python
gross_freed_this_month = ceiling_gross_freed × delta_adoption
```
The bonus is never applied, even when `enable_workflow_automation=True`.

**Second-order effect:** The model cannot demonstrate the non-linear value of workflow-level automation (where automating end-to-end processes frees more capacity than the sum of individual task automations).

**Recommendation:**
Apply bonus when extension phase is active:
```python
if params.enable_workflow_automation and raw_extend > 0:
    gross_freed_this_month *= params.workflow_automation_bonus
```

---

## Compressed Timeframe Analysis

| Horizon | HC Reduced | Net Savings | Payback | Final Adoption | Proficiency |
|---------|-----------|-------------|---------|----------------|-------------|
| 36 mo   | 40        | $2.3M       | M21     | 30.0%          | 40.2        |
| 24 mo   | 36        | $0.4M       | M21     | 27.2%          | 34.4        |
| 18 mo   | 34        | -$0.4M      | Never   | 25.1%          | 31.5        |
| 12 mo   | 27        | -$1.1M      | Never   | 22.3%          | 28.7        |
| 6 mo    | 15        | -$1.5M      | Never   | 14.2%          | 26.2        |

**Key insight:** Payback requires ~21 months regardless of compression. Shorter horizons lose 10-60% of the HC impact due to insufficient time for feedback loops (especially R2 proficiency) to compound. The J-curve is not compressible — you can't speed up trust or proficiency.

---

## Aggressive Headcount Scenarios

| Target | HC Reduced | Net Savings | Trust M36 | Payback |
|--------|-----------|-------------|-----------|---------|
| 20%    | 40        | $2.3M       | 43.5      | M21     |
| 30%    | 75        | $5.2M       | 47.6      | M17     |
| 40%    | 78        | $5.7M       | 48.3      | M17     |
| 50%    | 78        | $5.7M       | 48.9      | M17     |

**Key insight:** HC reduction plateaus at ~78 FTEs (14.4% of Claims) even with 50% target. The model correctly identifies the ceiling: automation potential × adoption rate × (1 - absorption) × human multiplier caps the achievable reduction. Pushing harder doesn't yield more — the seniority offset (B4) and absorption ceiling (B1) create a hard upper bound.

This is the RIGHT behavior. The model proves that headline targets of "50% reduction" are not achievable through automation alone — the system self-limits.

---

## Human Factor Sensitivity

| Configuration | HC Reduced | Net Savings | Final Adoption | Trust |
|--------------|-----------|-------------|----------------|-------|
| Zero everything | 0 | -$2.2M | 0.9% | 5.5 |
| Baseline | 40 | $2.3M | 30.0% | 43.5 |
| Max everything | 95 | $10.3M | 60.0% | 98.2 |
| Zero trust, high rest | 34 | $2.0M | 25.2% | 16.8 |
| High trust, zero readiness | 54 | $4.2M | 37.1% | 91.9 |
| High fatigue | 38 | $2.2M | 29.4% | 43.4 |
| Zero capital | 0 | -$2.2M | 6.6% | 51.7 |

**Key findings:**
1. **Zero capital is as blocking as zero everything** — political capital threshold (30) prevents ANY HC decisions, even with good adoption. The model correctly captures executive buy-in as a prerequisite.
2. **Trust floor is too permissive** — Zero trust (trust=5) still allows 25% adoption when readiness/proficiency are high (80). In reality, trust < 10 should be a hard blocker. The `trust_multiplier` floor of 0.50 may be too high.
3. **Readiness > Trust in the model** — "High trust, zero readiness" (54 HC, $4.2M) outperforms "Zero trust, high readiness" (34 HC, $2.0M). This is because readiness has 0.45 weight vs trust's 0.20. Real-world data suggests trust may need more weight when it's very low.

---

## New Stress Test Scenarios Added to Catalog

10 scenarios added (SC-ST.1 through SC-ST.10):

| ID | Scenario | Horizon | Key Parameter |
|----|----------|---------|---------------|
| SC-ST.1 | Compressed: 24 months | 24mo | k=0.35, active reduction |
| SC-ST.2 | Compressed: 12 months | 12mo | k=0.5, steep S-curve |
| SC-ST.3 | 50% HC (Claims) | 36mo | alpha=0.9, active reduction |
| SC-ST.4 | 50% HC (All Functions) | 36mo | Full org stress |
| SC-ST.5 | Rapid automation k=1.0 | 36mo | Near-instant adoption |
| SC-ST.6 | Low readiness + fast | 36mo | readiness=20, k=0.4 |
| SC-ST.7 | Triple AI error | 36mo | Errors at M5, M10, M15 |
| SC-ST.8 | 30% in 18 months | 18mo | Common executive target |
| SC-ST.9 | Best case human system | 36mo | readiness=90, prof=80 |
| SC-ST.10 | Zero budget | 36mo | No investment, attrition only |

---

## Recommendations (Priority Order)

1. **Fix productivity formula** — Add delayed automation lift (3-month lag) and increase skill drag coefficient. This is the highest-impact fix for model realism.
2. **Fix fatigue accumulation** — Increase build rate and add adoption-pace-driven fatigue. This enables the model to differentiate sustained vs one-time changes.
3. **Implement rapid_redeployment** — Add as distinct policy to differentiate P5 from P3. This enables the AI-Age Accelerated scenario to show its intended non-linear gains.
4. **Apply workflow_automation_bonus** — Simple fix: multiply freed capacity by bonus when extension phase is active.
5. **Consider trust floor adjustment** — Reduce trust_multiplier floor from 0.50 to 0.30 when trust < 10, or increase trust weight from 0.20 to 0.30 in the effective_multiplier formula.
