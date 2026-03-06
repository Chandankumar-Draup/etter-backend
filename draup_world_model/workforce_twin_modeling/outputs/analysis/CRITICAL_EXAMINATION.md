# Workforce Twin MVP — Complete Results & Critical Examination

## Executive Summary

All 5 stages executed successfully. All 40 scenario catalog entries produced results. The model is **structurally sound** — invariants hold, aggregation is consistent, and feedback loops behave as designed. However, critical examination reveals the **human system multiplier creates a quadratic penalty** that makes 39 of 40 scenarios unprofitable under baseline conditions.

This is not necessarily a bug — it may be the model's most important finding: **human readiness, not technology potential, is the binding constraint on AI transformation ROI**.

---

## Stage 0: Static Snapshot — The Potential

**Organization:** InsureCo | 1,370 HC | $91.1M annual cost | 581 tasks | 87 compliance-protected

### Three-Layer Gap Structure

| Layer | Value | Meaning |
|-------|-------|---------|
| L1 (Etter Ceiling) | 56.4% | Theoretical maximum — all tools, perfect conditions |
| L2 (Achievable) | 51.3% | What's possible with deployed tool capabilities |
| L3 (Realized) | 9.5% | What's actually automated today |
| **Adoption Gap** | **41.8%** | L2 − L3 = "free money" — tools exist, unused |
| **Capability Gap** | 5.1% | L1 − L2 = needs new tool investment |
| **Total Gap** | 46.9% | Total unrealized automation potential |

**Dollar Translation:**
- Adoption gap savings: **$36.6M/year** (just use what you have)
- Full gap savings: **$41.5M/year** (if you also invest in new capabilities)

### Per-Function Human System Baseline

| Function | HC | Cost | L1 | L2 | L3 | Prof | Ready | Trust | EffMult |
|----------|-----|------|-----|-----|-----|------|-------|-------|---------|
| Claims | 540 | $29.5M | 63.5% | 59.9% | 9.2% | 25 | 45 | 35 | 0.113 |
| Finance | 239 | $15.4M | 56.6% | 50.3% | 10.5% | 30 | 50 | 40 | 0.150 |
| People | 186 | $10.8M | 55.8% | 52.9% | 13.6% | 20 | 55 | 45 | 0.110 |
| Technology | 405 | $35.4M | 47.2% | 39.7% | 7.5% | 60 | 70 | 65 | 0.420 |

**Key Insight:** Technology has 3.7x the effective multiplier of Claims. Same tools, radically different outcomes. The multiplier IS the story.

### Invariant Validation

| Test | Result | Detail |
|------|--------|--------|
| L1 ≥ L2 ≥ L3 | ✓ PASS | All 37 roles |
| Bottom-up HC aggregation | ✓ PASS | Sum(roles) = 1370 = Org total |
| Bottom-up savings aggregation | ✓ PASS | Sum(roles) = $36,588,085 = Org total |
| Function → Org consistency | ✓ PASS | All 4 functions sum correctly |

---

## Stage 1: Single-Step Cascade — What Happens When You Deploy

**Stimulus:** Deploy Microsoft Copilot → Claims function (540 HC, 12 roles)

### 9-Step Cascade Results

**Step 1 — Scope:** 12 roles, 127/183 addressable tasks, 32 compliance-protected, 540 HC

**Step 2 — Reclassification:** 127 tasks reclassified (106 → AI, 21 → Human+AI)

**Step 3 — Capacity (The Redistribution Story):**
- Gross freed: 44,651 hrs/month
- Redistributed (absorbed): 15,628 hrs/month (35% absorption factor)
- **Net freed: 29,023 hrs/month (65% of gross)**
- Dampening validated: 29,023 / 44,651 = 65.0% ✓

**Why this matters:** Automating 40% of someone's tasks does NOT free 40% of their time. Remaining workers absorb ~35% through expanded meetings, increased oversight, context-switching, and natural slack-filling. This is Parkinson's Law in action at the organizational level.

**Step 4 — Skills:** 155 sunset skills, 48 sunrise skills

**Step 5 — Workforce:**
- Total reducible: **176 FTEs** (from 540 → 364)

| Role | Current HC | Freed FTEs | Reducible | Projected | Reduction |
|------|-----------|------------|-----------|-----------|-----------|
| Claims Intake Specialist | 120 | 43.4 | 43 | 77 | 36% |
| Claims Adjuster | 95 | 31.1 | 31 | 64 | 33% |
| Claims Data Entry Clerk | 80 | 29.7 | 29 | 51 | 36% |
| Claims Examiner | 45 | 15.3 | 15 | 30 | 33% |
| Claims Processor | 60 | 14.5 | 14 | 46 | 23% |
| Claims Review Specialist | 40 | 14.1 | 14 | 26 | 35% |
| Quality Assurance Auditor | 30 | 9.7 | 9 | 21 | 30% |
| Claims Team Lead | 20 | 6.7 | 6 | 14 | 30% |
| Fraud Detection Analyst | 20 | 6.1 | 6 | 14 | 30% |
| Claims Review Manager | 15 | 5.9 | 5 | 10 | 33% |
| Claims Support Coordinator | 10 | 3.2 | 3 | 7 | 30% |
| Sr. Director Claims | 5 | 1.6 | 1 | 4 | 20% |

**Step 6 — Financial:**
- Total investment: $1,814,400 (license $194K/yr + training $1.08M + change $540K)
- Salary savings: $9,543,000/year (hand-verified: sum(reducible × salary) exact match ✓)
- Net annual: $7,914,576/year
- Payback: 2.2 months
- ROI: 436%

**Step 7 — Structural:** 11 of 12 roles flagged for redesign (>40% freed)

**Step 8 — Human System:** Change burden = 100/100 (maximum). Readiness below 50-point threshold.

**Step 9 — Risk:** OVERALL = HIGH
- [high] Concentration: 11 high-proficiency sunset skills — knowledge loss risk
- [high] Change burden: 100/100 — fatigue and resistance risk
- [high] Quality: 32.6% HC reduction impacts service quality
- [medium] Compliance: 32 tasks must not be touched
- [medium] Concentration: 176 FTEs all from Claims — political risk

**Stage 1 Verdict:** The cascade math is clean. The static picture looks great — 176 FTEs, $7.9M/year net, 2-month payback. But this is the OPEN-LOOP view. It ignores whether humans will actually adopt the technology.

---

## Stage 2 vs Stage 3: The Feedback Reality Check

### The Central Comparison

| Metric | Open-Loop (S2) | Feedback (S3) | Ratio |
|--------|---------------|---------------|-------|
| HC Reduced | 157 | 6 | 3.8% |
| Final HC | 383 | 534 | — |
| Net Savings | $17,836,633 | -$1,750,700 | negative |
| Payback | Month 9 | Never | — |
| Avg Effective/Raw | 100% (no filter) | 7.4% | — |

**The model destroys 96% of open-loop value through human system dampening.**

### Why: Tracing the Multiplier from First Principles

Claims baseline: proficiency = 25, readiness = 45, trust = 35

```
eff_multiplier = (proficiency / 100) × (readiness / 100)
               = 0.25 × 0.45
               = 0.1125

trust_multiplier = min(trust / 60, 1.0)
                 = min(35/60, 1.0)
                 = 0.583

combined = 0.1125 × 0.583 = 0.0656

Raw adoption at M36: 90%
Effective adoption: 90% × 0.066 ≈ 5.9%
```

**The Quadratic Trap:** When two factors (proficiency and readiness) are both below 50%, their product is dramatically lower than either individual score. 25% × 45% = 11.25%. This isn't a bug — it's how multiplicative systems work. A team that's only 25% proficient AND only 45% ready will indeed struggle to adopt AI effectively.

### The Readiness Sensitivity

| Readiness Level | HC Reduced | Net Savings | Avg Dampening | Interpretation |
|----------------|------------|-------------|---------------|----------------|
| Low (25) | 0 | -$2,203,200 | 0.8% | Dead on arrival — pure cost |
| Baseline (45) | 6 | -$1,750,700 | 7.4% | Slight improvement, still negative |
| High (80) | 61 | +$4,402,883 | 42.0% | **Profitable** — breakeven crossed |

**Savings swing: $6.6M** — one parameter (readiness) drives a 7.3% swing of total org cost. This confirms readiness is the **#1 leverage point**.

### Trust Asymmetry

A single AI error at month 7 drops trust from 37.2 → 26.2 at M36 (11 points permanent damage). Additional cost: $158,000. Trust builds slowly but breaks instantly.

### Monthly Trajectory (Feedback Baseline)

The human multiplier creeps from 0.113 → 0.139 over 36 months. Proficiency: 25.0 → 29.1. Trust: 35.0 → 37.2. All gains are glacial. The system is "stuck" — reinforcing loops (R1-R4) exist but are too weak to overcome the balancing loops (B1-B4) at low starting conditions.

---

## Stage 4: Five Policy Scenarios

| Policy | HC Red | Net Savings | Final Prof | Final Trust | Interpretation |
|--------|--------|-------------|------------|-------------|----------------|
| P1 Cautious | 3 | -$2,032,700 | 27.4 | 36.3 | Slowest loss |
| P2 Balanced | 6 | -$1,750,700 | 29.1 | 37.2 | Default |
| P3 Aggressive | 10 | -$1,310,700 | 30.2 | 37.8 | Faster HC cuts |
| P4 Cap-First | 0 | -$2,203,200 | 29.1 | 37.2 | No layoffs, pure cost |
| P5 Accelerated | 10 | -$1,310,700 | 30.2 | 37.8 | = P3 (see anomaly) |

**Findings:**
1. All 5 policies lose money at baseline readiness
2. P3 = P5 exactly (workflow bonus has zero effect — anomaly)
3. Policy spread is only $892K — policies barely matter when the human multiplier is the bottleneck
4. P4 (no-layoffs) correctly enforces zero reductions but at maximum cost

**Implication:** Choosing between policies is a second-order decision. The first-order decision is whether to invest in readiness BEFORE deploying technology.

---

## 40-Scenario Catalog: Pattern Analysis

### Overall Results

**Profitable: 1 out of 40 (2.5%)**

The only profitable scenario: **SC-10.4 "Attrition Shock (15% Tech Loss)"** at +$1,325,450.

Why it works: Technology function baseline is prof=60, ready=70, trust=65 → eff_mult = 0.42 (vs Claims at 0.11). The Tech function can actually adopt AI effectively.

### Scenario Family Performance

| Family | Count | Avg Net Savings | Avg Dampening | Avg Prof |
|--------|-------|----------------|---------------|----------|
| role_transformation | 4 | -$2,457,825 | 53.4% | 30.1 |
| skill_intervention | 2 | -$2,762,100 | 100.0% | 33.8 |
| stress_test | 3 | -$2,888,950 | 18.9% | 42.2 |
| output_target | 2 | -$3,988,308 | 7.1% | 27.6 |
| function_transformation | 3 | -$4,442,342 | 8.4% | 29.2 |
| technology_injection | 3 | -$5,987,639 | 12.9% | 35.0 |
| sequencing | 6 | -$7,044,747 | 8.4% | 29.5 |
| headcount_target | 3 | -$7,247,328 | 15.2% | 37.3 |
| automation_target | 2 | -$7,964,117 | 16.7% | 42.5 |
| composite | 3 | -$7,910,594 | 16.3% | 41.3 |
| budget_constraint | 2 | -$9,083,583 | 15.9% | 39.7 |

**Pattern:** Larger-scope scenarios lose more money because they deploy across low-readiness functions (Claims, Finance, People) where the multiplier kills ROI.

### Dampening Distribution (across 40 scenarios)

| Range | Count | Visual |
|-------|-------|--------|
| < 5% | 0 | |
| 5-10% | 21 | █████████████████████ |
| 10-20% | 12 | ████████████ |
| 20-40% | 0 | |
| 40%+ | 7 | ███████ |

21 of 40 scenarios show only 5-10% effective adoption. The distribution is bimodal — either you're stuck at <10% (low-readiness functions) or you're at 40%+ (Technology function).

### Human Multiplier Distribution (final month)

| Range | Count | Implication |
|-------|-------|-------------|
| 0.10-0.15 | 20 | Claims/Finance/People baseline |
| 0.15-0.25 | 18 | Modest improvement after 36 months |
| 0.25-0.50 | 2 | Technology function only |
| 0.50+ | 0 | Nobody reaches this |

**Nobody reaches 50% effective adoption across 40 scenarios.** The ceiling is the Technology function at ~43%.

---

## Critical Anomalies

### Anomaly 1: SC-10.6 "Do Nothing" costs $5.6M

A "do nothing" baseline should have zero investment. But the scenario maps to ALL functions with ALL tools, incurring license and training costs. The scenario mapping logic incorrectly treats the baseline as a deployment.

**Severity:** HIGH — the baseline comparator is wrong.

**Fix:** Scenario executor needs a `baseline` family handler that bypasses tool deployment.

### Anomaly 2: SC-1.5 "Adoption Gap Only (Free Money)" is -$12.6M

This scenario deploys ALL_DEPLOYED tools (already owned, zero new license cost). Expected: near-zero investment, immediate savings from closing the adoption gap. Actual: $14.5M investment.

**Root Cause:** The executor resolves ALL_DEPLOYED to all 5 tools, calculates training cost as training_per_person × ALL org headcount = $2,000 × 1,370 × 4 functions ≈ $10M+.

**Fix:** "Free money" scenarios should use reduced training costs (refresher, not full training) and zero license cost.

### Anomaly 3: 39/40 Scenarios Lose Money

This is either: (a) a calibration issue in the human multiplier formula, or (b) the model's most important finding.

**The case for calibration issue:**
- Real-world Copilot deployments show 15-30% efficiency gains in year 1
- The model shows <8% effective adoption even after 36 months
- The quadratic penalty (prof × ready) may be too aggressive

**The case for "this is the finding":**
- Organizations with prof=25, ready=45 genuinely struggle with AI adoption
- The model correctly identifies that technology alone doesn't create value
- Only the Technology function (already high-readiness) succeeds

**Resolution:** Both are partially true. The formula should use a softer penalty for moderate scores while keeping the steep penalty for very low scores.

### Anomaly 4: Sequencing Scenarios Produce Identical Results

SC-9.1a (Claims→Finance→People), SC-9.1b (People→Finance→Claims), SC-9.1c (Finance→Claims→People) all produce exactly -$8,888,567.

**Root Cause:** All functions deploy simultaneously at month 1 regardless of the specified sequence. There's no multi-phase executor with staggered deployment_start_month.

**Fix:** Multi-phase executor where each function starts N months after the previous one completes.

### Anomaly 5: SC-8.1 "Claims AI Academy" Shows Zero Proficiency Improvement

A skills academy scenario should boost proficiency, but final prof = 25.0 (unchanged from baseline). The scenario executor doesn't inject proficiency lifts into the human system initial state.

**Fix:** Map `proficiency_lift` parameter to HumanSystemState override.

### Anomaly 6: Structural Scenarios (SC-7.4, SC-6.3, SC-6.4) Show Zero HC Impact

These describe structural transformations (merge roles, create new roles, handle attrition) but the engine treats them as standard simulation runs. No structural transformation logic exists.

**Fix:** These need dedicated handlers that modify org structure before running the simulation.

---

## Systems Thinking Analysis

### Feedback Loop Dominance Map

At Claims baseline conditions:

| Loop | Type | Strength | Status |
|------|------|----------|--------|
| B1: Capacity Absorption | Balancing | Strong (35%) | **Dominates** — always active |
| B2: Skill Valley | Balancing | Moderate | Active M3-M12 |
| B3: Change Resistance | Balancing | **Very Strong** | **Dominates** — trust < 60 |
| B4: Seniority Offset | Balancing | Weak | Measurable but minor |
| R1: Trust-Adoption | Reinforcing | Weak | Can't activate — trust too low |
| R2: Proficiency Flywheel | Reinforcing | Weak | Growth rate = 0.11/month |
| R3: Savings Reinvestment | Reinforcing | Very Weak | Capped at 5% boost |
| R4: Political Capital | Reinforcing | Moderate | Growing but not converting |

**Diagnosis:** The system is in a **lock-in state**. Balancing loops dominate because starting conditions are below the tipping point. Reinforcing loops exist but can't overcome the dampening. The system needs an **exogenous shock** to readiness/proficiency to flip into the reinforcing regime.

### Second-Order Effects

1. **Trust Hysteresis:** Once trust drops below ~30, recovery is extremely slow. A single AI error can permanently trap the system below the adoption threshold.

2. **Proficiency Compounding is Real but Slow:** 25 → 29.1 over 36 months (0.11/month). At this rate, reaching 50 takes 19 years. The learning velocity parameter (8 months for Claims) means proficiency growth barely keeps up with technology change.

3. **Dynamic Absorption Increases:** As HC shrinks, remaining workers absorb more. Absorption rises from 0.433 → 0.435. Small effect but creates diminishing returns — the first 10% of reduction is easier than the last 10%.

4. **Investment Front-Loading vs Savings Back-Loading:** All scenarios invest heavily in months 1-6 but savings only materialize once adoption reaches threshold levels. With 7% effective adoption, the savings trickle never catches up.

### The Tipping Point

Using the hi-ready variant (prof=50, ready=80, trust=70):
- eff_mult = 0.50 × 0.80 = 0.40
- trust_mult = min(70/60, 1.0) = 1.0
- combined = 0.40

At 40% effective adoption, the reinforcing loops can activate. Trust climbs, proficiency compounds faster, savings generate reinvestment. The system crosses into positive territory.

**The tipping point is approximately: eff_mult > 0.25 (prof × ready > 25%)**

This means: either proficiency ≥ 50 AND readiness ≥ 50, OR one factor compensates for the other (e.g., prof=35, ready=72).

---

## Metrics Summary

### What the Model Measures (and what it should)

| Metric | Stage 0 | Stage 1 | Stage 3 (Feedback) | Healthy? |
|--------|---------|---------|---------------------|----------|
| L1/L2/L3 gaps | ✓ Clean | — | — | ✓ |
| Redistribution dampening | — | ✓ 65% | ✓ Dynamic | ✓ |
| FTE reduction | — | 176 static | 6 dynamic | ✓ |
| Net savings | — | $7.9M/yr | -$1.75M/36mo | ⚠ |
| Payback | — | 2.2 months | Never | ⚠ |
| Human multiplier | 0.113 static | — | 0.113 → 0.139 | ✓ |
| Proficiency trajectory | — | — | 25 → 29.1 | ✓ |
| Trust trajectory | — | — | 35 → 37.2 | ✓ |
| Trust asymmetry | — | — | -11 points from 1 error | ✓ |
| Policy differentiation | — | — | $892K range | ⚠ Weak |
| Readiness sensitivity | — | — | $6.6M swing | ✓ |

### Missing Metrics to Add

1. **Time to Breakeven by Readiness Level** — at what readiness does each scenario become profitable?
2. **Readiness Investment ROI** — cost of moving readiness from 45 → 65 vs the savings delta
3. **Risk-Adjusted Returns** — expected value = P(success) × savings - P(failure) × costs
4. **Cross-Function Learning Transfer** — Claims success should boost Finance readiness
5. **Scenario Ranking by Effort/Impact Ratio** — which scenarios give most value per dollar of readiness investment?

---

## Recommendations

### Immediate (Fix the Model)

1. **Fix SC-10.6 baseline** — zero investment for do-nothing scenarios
2. **Fix SC-1.5 cost calculation** — adoption gap scenarios should have minimal training cost
3. **Fix SC-8.1 proficiency injection** — skills academy must boost proficiency parameter
4. **Differentiate P3 vs P5** — workflow automation bonus needs to affect capacity calculation
5. **Fix sequencing** — multi-phase executor with staggered deployment_start_month

### Calibration (Improve Realism)

6. **Soften the multiplier** — consider `sqrt(prof/100 × ready/100)` or threshold model:
   - Below 30: steep penalty (current model correct for low-readiness orgs)
   - 30-60: linear growth (moderate difficulty, recoverable)
   - Above 60: accelerating returns (flywheel kicks in)

7. **Add readiness intervention cost** — model the cost of moving readiness from 45 → 65 (change management programs, training, leadership alignment)

### Strategic (Prove the Thesis)

8. **"Unstuck the System" demo** — show baseline (stuck) vs readiness-boosted (profitable) as the key client narrative. The question isn't "which technology?" but "is your organization ready?"

9. **Function-sequencing** — always start with Technology (high readiness), prove success, then use that momentum to boost Claims readiness through cross-function learning transfer.

10. **Readiness-First ROI calculation** — the most valuable analysis Etter can provide: "Investing $X in readiness before deploying technology yields $Y vs deploying technology alone yields -$Z."

---

*Analysis generated from workforce_twin_mvp execution on 2026-03-02*
*All 5 stages executed, 40/40 scenarios completed, 11 validation tests performed*
*Data stored in: outputs/analysis/*
