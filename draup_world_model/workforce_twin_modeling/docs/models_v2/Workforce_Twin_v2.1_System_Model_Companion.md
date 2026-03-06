# Workforce Twin v2.1 — System Model & Simulation Companion

**A complete technical reference for the five system diagrams**

*Etter AI Transformation Platform · Draup Inc.*

---

## 1. The Problem Statement

Traditional workforce planning treats AI transformation as a technology deployment problem: estimate automation potential, calculate freed capacity, project headcount reductions. This produces an "open-loop" projection — what happens if adoption follows a perfect S-curve and every freed hour converts to savings.

Real organizations are complex adaptive systems. Deploying AI changes how people feel about AI (trust), how well they use it (proficiency), and how ready they are for more change (readiness). These human factors feed back into adoption speed, creating a gap between what technology *could* do and what organizations *actually* realize.

The Workforce Twin exists to model this gap. It answers the question enterprise leaders actually need answered: not "what is the theoretical potential?" but "given our people, our culture, and our deployment strategy, what will actually happen over 36 months?"

### The Core Insight

The system behaves as a **socio-technical feedback system** where human dynamics are the binding constraint, not technology capability. The same technology deployment produces wildly different outcomes depending on organizational readiness — ranging from +$15.1M to -$5.6M across 40 tested scenarios.

---

## 2. First Principles Foundation

The model rests on five irreducible first principles, each derived from observable organizational behavior rather than theoretical assumptions.

**Principle 1: Organizations are interconnected, not decomposable.** Changing one role's workload affects every connected role through capacity redistribution, skill gap creation, and workload absorption. You cannot model roles independently.

**Principle 2: Human factors are the binding constraint.** Technology defines the ceiling (L1/L2 automation potential), but human factors — proficiency, readiness, and trust — determine how much of that ceiling is realized. At the Claims function baseline, the ceiling is 90% but realization is 45%, meaning 55% of potential is lost to human system dynamics.

**Principle 3: Feedback loops determine behavior, not initial conditions.** The same starting conditions produce fundamentally different outcomes depending on which feedback loops dominate. Early in a transformation, balancing loops (resistance, skill gaps, absorption) dominate and the system feels stuck. Later, reinforcing loops (trust, proficiency, savings) can take over and create compounding returns — but only if the organization reaches the tipping point.

**Principle 4: Stocks change slowly, even when flows change suddenly.** Trust doesn't jump when you demonstrate value; it accumulates gradually. Proficiency doesn't spike after a training session; it builds through practice. This inertia means that early results always understate long-term potential (or overstate it, if trust is destroyed early).

**Principle 5: Delays create oscillation and overshoot.** Reskilling takes time. Headcount reduction happens quarterly, not monthly. Training investment today produces proficiency months later. These delays mean the system cannot perfectly track demand, creating temporary valleys and overshoots that planning must account for.

---

## 3. System Architecture — The Six Stocks

The system model contains six stocks (state variables that accumulate over time), twelve flows (rates that change stocks), and nine feedback loops (circular causal chains that either dampen or amplify change).

*Reference: Diagram ① Stock & Flow*

### Stock 1: AI Adoption Level

The central hub of the system. Measures what percentage of addressable work is being performed with AI assistance.

- **Range:** 0% → 90% (technology ceiling for Claims/Copilot deployment)
- **Inflow:** Technology deployment — follows a logistic S-curve with rate parameter k, modified by the effective multiplier from human system state
- **Outflow:** Adoption dampening — represents the gap between raw technology availability and actual usage, driven by skill gaps (B2), seniority effects (B4), and trust resistance

The adoption level at any month t is:

```
raw_adoption(t) = L / (1 + e^(-k × (t - t_mid)))
effective_adoption(t) = raw_adoption(t) × effective_multiplier × trust_multiplier × skill_multiplier
```

Where L = 0.90 (ceiling), k = 0.15 (steepness), t_mid = 12 (inflection month). In the baseline scenario, effective adoption reaches 44.7% at M36 — approximately half the technology ceiling.

### Stock 2: Freed Capacity

Hours per month freed by AI-assisted task completion. This is the raw material that either converts to FTE reductions (creating savings) or gets absorbed into redistribution (creating no savings but preventing overwork).

- **Inflow:** Automation frees hours — proportional to effective adoption × hours addressable per person
- **Outflow:** B1 capacity absorption — starts at 30% of freed capacity and grows to 37% as remaining workers absorb redistributed work
- **Key metric:** Gross freed 44,651 hrs/mo → Net freed 29,023 hrs/mo (65% net/gross ratio at cascade completion)

### Stock 3: Headcount

The primary financial lever. HC reduction generates salary savings, which is the largest component of financial returns.

- **Inflow:** Net freed capacity → FTE equivalents (160 hrs/mo = 1 FTE)
- **Outflow:** Quarterly review decisions — HC reductions are not instantaneous but occur in quarterly batches, creating a structural delay
- **Baseline trajectory:** 540 → 474 over 36 months (66 reduced, 12.2% of starting HC)

### Stock 4: Skill Gap

Measures the delta between skills the organization currently has and skills needed to effectively use AI tools. Opens when automation is deployed; closes (slowly) through reskilling investment.

- **Inflow:** Automation opens gap — each technology deployment introduces new skill requirements (155 sunset skills, 48 sunrise skills in the Claims deployment)
- **Outflow:** Reskilling closes gap — with a structural delay of 3-6 months (training delivery and practice time)
- **Feedback:** Skill gap directly dampens effective AI use (B2 loop), creating a valley of reduced productivity during the transition period

### Stock 5: Financial Position

Cumulative net financial impact — savings minus investment.

- **Inflow:** Salary savings from HC reductions
- **Outflow:** License costs ($194K/yr), training ($1.08M), change management ($540K)
- **Baseline trajectory:** $0 → -$1.5M (M6 valley) → $0 (M18 breakeven) → +$4.66M (M36)
- **R3 reinvestment:** After breakeven, accumulated savings create a small but growing boost to adoption investment

### Stock 6: Human System State (Composite)

The most complex stock, containing five sub-dimensions that collectively determine the `effective_multiplier` — the fraction of technology potential that is actually realized.

**Proficiency (weight: 0.35):** How well people actually use the AI tools. Starts at 25 for Claims (low), grows through practice to 45 over 36 months. Driven by the R2 proficiency flywheel: practice → proficiency → better results → more practice.

**Readiness (weight: 0.45):** Willingness to embrace change. The most heavily weighted dimension because it determines *initial* adoption speed — you can't get proficient with tools you refuse to use. Starts at 45, grows to 55. Driven by R5 (adoption success → readiness) and opposed by B3 (disruption → resistance → readiness decline).

**Trust (weight: 0.20):** Confidence that AI tools are reliable and that the transformation process is being managed fairly. Slowest-moving dimension: 35 → 46 over 36 months. Driven by R1 (success → trust → willingness) but highly asymmetric — destroys fast, builds slow. An AI error at M7 drops trust from 35→24 and takes 18+ months to partially recover.

**Political Capital:** Executive willingness to spend organizational goodwill on transformation decisions. Starts at 60, grows to 71. Enables larger or more disruptive moves when high; constrains action when low. Not directly in the multiplier formula but affects the *scope* of what can be attempted.

**Fatigue:** Cumulative change exhaustion. Currently zero in baseline but would activate under sustained aggressive policies. Acts as a hard ceiling: even willing, proficient, trusting employees eventually burn out.

The **effective multiplier** formula (the single most important equation in the model):

```
effective_multiplier = max(0.15, (0.35 × proficiency + 0.45 × readiness + 0.20 × trust) / 100)
```

At Claims baseline: `(0.35 × 25 + 0.45 × 45 + 0.20 × 35) / 100 = 0.360`

The floor of 0.15 ensures that even in worst-case organizations, the approximately 15% early adopters still use available tools regardless of organizational sentiment.

---

## 4. The Nine Feedback Loops

*Reference: Diagram ② Causal Loop*

The system contains 4 balancing loops (which resist change and push toward equilibrium) and 5 reinforcing loops (which amplify change and create exponential growth or decline).

### Balancing Loops (Resist Change)

**B1 — Capacity Absorption (always on, 30→37%)**

When AI frees hours, remaining workers absorb some of that freed capacity through task redistribution, informal scope expansion, and workload rebalancing. This means not all freed hours convert to reducible FTEs.

The absorption rate starts at 30% (base organizational elasticity) and grows toward 37% as HC reductions increase workload per remaining person. This is the single most persistent loop — it never turns off and always reduces the conversion of freed capacity to savings.

**B2 — Skill Valley (peaks M6, fades by M18)**

Deploying AI creates a gap between existing skills and needed skills. Until reskilling catches up (with a 3-6 month delay), this gap reduces effective AI use — people have the tools but not the knowledge to use them well. This loop peaks early (M6) as the skill gap is largest, then fades as training and practice close it.

**B3 — Change Resistance (strong early, fading)**

Disruption from AI deployment and HC reductions creates organizational resistance, which pushes readiness down and slows adoption. In v2.1, this loop is counterbalanced by R5 (readiness boost from success), creating a tug-of-war that the reinforcing side gradually wins.

The critical dynamic: resistance is proportional to the *rate of change*, not the level of change. Fast deployments create more resistance per unit of change than gradual ones.

**B4 — Seniority Offset (slow, growing)**

As entry-level and junior roles are automated first, the remaining workforce becomes more senior on average. Senior roles are harder to automate (more judgment, less routine), so the marginal automation opportunity decreases over time. This creates a natural ceiling on how far automation can go in any single deployment cycle.

### Reinforcing Loops (Amplify Change)

**R1 — Trust Flywheel (slow start, compounds)**

Successful AI use → demonstrates value → builds trust → increases willingness → more adoption → more success. The slowest reinforcing loop because trust builds incrementally and asymmetrically. A single high-visibility failure (the M7 error scenario) can undo months of trust building.

**R2 — Proficiency Flywheel (strongest reinforcing loop)**

Practice with AI tools → improved proficiency → more effective use → better results → more practice. This is the most powerful reinforcing loop because proficiency is the most learnable dimension of the human system. Once people start using tools, practice naturally drives improvement.

Growth rate: +19.8 points over 36 months (25 → 45).

**R3 — Savings Reinvestment (activates after breakeven)**

Accumulated savings → increased training/tooling budget → more capability → more automation → more savings. This loop was structurally disconnected in v1 (the function existed but was never called). In v2.1, it provides a small but growing boost after M18 breakeven — approximately +1-2% adoption acceleration.

**R4 — Political Capital (enables scope expansion)**

Transformation success → builds executive confidence → more resources allocated → bigger scope → more potential success. This loop doesn't directly affect the math but determines the *boundary conditions* — what the organization is willing to attempt.

**R5 — Readiness Boost (NEW in v2.1)**

Adoption success → people see it working → become more willing to adopt → faster adoption. This is the loop that was structurally missing in v1, causing readiness to be a one-way drain. Its addition was the most architecturally significant fix because it created an entirely new circular causal path.

The formula:

```
readiness_ceiling = max(0.1, 1.0 - readiness/100)
adoption_boost = 1.5 × effective_adoption_level × readiness_ceiling
delta_readiness = -resistance_drain + base_recovery(0.08) + adoption_boost
```

The ceiling term ensures readiness growth slows as it approaches 100 (diminishing returns on further adoption success).

---

## 5. Simulation Mechanics

*Reference: Diagram ③ Behavior*

The simulation runs as a discrete monthly timestep model over a 36-month horizon. Each month, every stock is updated based on its inflows and outflows from the previous month's state.

### The Simulation Loop (Each Month)

1. **Compute raw adoption** — logistic S-curve at month t
2. **Compute human system state** — update proficiency, readiness, trust from previous month
3. **Compute effective multiplier** — weighted blend of human dimensions
4. **Compute trust multiplier** — smooth threshold function of trust level
5. **Compute skill multiplier** — gap between needed and available skills
6. **Compute effective adoption** — raw × effective_multiplier × trust_multiplier × skill_multiplier
7. **Compute freed capacity** — effective adoption × addressable hours per person × headcount
8. **Compute absorption** — dynamic absorption rate × gross freed
9. **Compute net freed** — gross freed − absorbed − redistributed
10. **Compute HC reduction** — net freed / 160 (quarterly batching)
11. **Compute financial impact** — salary savings − license cost − amortized training
12. **Update all stocks** — write new values for next month's computation

### Phase Behavior

The simulation naturally produces three behavioral phases, visible in the time-series charts:

**Phase 1: Startup (M0-M12) — Balancing Dominant**

The system feels stuck. Investment is flowing out but returns haven't arrived. The adoption S-curve is climbing but the effective multiplier is low (0.36), so only about a third of raw adoption translates to effective use. Skill gaps are at their widest (B2 peak at M6). Resistance is highest (B3). The financial position is negative, reaching its valley at M6 (-$1.5M).

The organization experiences this phase as "AI isn't working." In reality, the reinforcing loops are slowly activating, but they haven't yet reached the strength to overcome the balancing forces.

**Phase 2: Acceleration (M12-M24) — Tipping Point**

Around M12-M18, the balance of forces shifts. R2 (proficiency) has been building steadily and now produces noticeable improvement. R5 (readiness) has been counteracting B3 (resistance) and readiness is climbing past 50. The skill valley (B2) has largely closed. Financially, the system crosses breakeven at M18.

This is the critical period. If the organization has maintained investment through Phase 1, the reinforcing loops now have enough strength to generate self-sustaining momentum. If trust was destroyed (the M7 error scenario delays breakeven to M21), or if readiness started too low (Lo-Ready scenario never reaches breakeven), the system may stall in this phase.

**Phase 3: Maturity (M24-M36) — Reinforcing Dominant**

The reinforcing loops clearly dominate. Proficiency is high enough that most users are effective. Readiness has crossed 50, meaning more than half the organization is willing adopters. Trust is building steadily if slowly. Financial returns are compounding. The system reaches +$4.66M by M36.

However, B1 (absorption) never turns off and B4 (seniority) is slowly growing, so the rate of improvement is decelerating — this is the diminishing returns phase. The system is approaching its practical equilibrium for this deployment.

### Key Metrics (Baseline Reference Mode)

| Metric | M0 | M6 | M12 | M18 | M24 | M30 | M36 |
|--------|-----|-----|------|------|------|------|------|
| Raw adoption | 13.9% | 45.7% | 74.4% | 86.6% | 89.4% | 89.9% | 90.0% |
| Effective adoption | 4.0% | 16.6% | 28.3% | 35.1% | 39.1% | 41.9% | 44.7% |
| Headcount | 540 | 519 | 502 | 490 | 481 | 477 | 474 |
| Proficiency | 25.1 | 26.3 | 29.2 | 33.0 | 37.0 | 41.0 | 44.9 |
| Readiness | 45.1 | 45.6 | 46.9 | 48.7 | 50.7 | 52.8 | 55.1 |
| Trust | 35.0 | 35.7 | 37.2 | 39.3 | 41.6 | 44.0 | 46.4 |
| Net savings (cum.) | $0 | -$1,501K | -$863K | +$179K | +$1,525K | +$3,056K | +$4,657K |

### The Dampening Gap

The most important single metric is the **average dampening**: the fraction of raw adoption that is lost to human system dynamics. In the baseline scenario, this is 35.3% — meaning the organization captures about 65% of what a perfect-adoption model would predict.

This dampening varies dramatically by readiness:

| Variant | Avg Dampening | Net 36mo | Interpretation |
|---------|--------------|----------|----------------|
| Open-loop (no feedback) | 0% | +$17.8M | Theoretical ceiling |
| High readiness (p=60,r=70,t=65) | 31.1% | +$11.0M | Best realistic case |
| **Baseline (p=25,r=45,t=35)** | **35.3%** | **+$4.7M** | **Moderate org** |
| Low readiness (p=15,r=30,t=25) | 92.8% | -$1.4M | Unprepared org |

The difference between high-readiness and low-readiness is $12.3M over 36 months — 13.5% of the Claims function's annual cost. Readiness alone accounts for more variance than any technology choice, deployment speed, or policy decision.

---

## 6. Loop Dominance Analysis

*Reference: Diagram ④ Dominance*

At any given time, some feedback loops dominate the system's behavior while others are dormant or weak. The loop dominance analysis traces which loops control outcomes at each phase of the transformation.

### Phase 1 Dominance (M0-M12)

| Loop | M0 | M6 | M12 | Trend |
|------|-----|-----|------|-------|
| B1: Absorption | 30% | 31% | 32% | Always present |
| B2: Skill Valley | 5% | 22% | 15% | Peaks M6 |
| B3: Resistance | 15% | 28% | 25% | High early |
| B4: Seniority | 0% | 2% | 5% | Barely active |
| R1: Trust | 3% | 8% | 15% | Starting |
| R2: Proficiency | 5% | 12% | 22% | Building |
| R3: Savings | 0% | 0% | 0% | Not yet |
| R4: Capital | 6% | 10% | 18% | Growing |
| R5: Readiness | 3% | 10% | 20% | Activating |

**Net balance: B ≫ R (system feels stuck)**

### Phase 2 Dominance (M12-M24)

The tipping point. At M12, balancing forces roughly equal reinforcing forces. By M18, the reinforcing side has taken a clear lead. R2 (proficiency) emerges as the strongest single reinforcing loop at 35% strength. R5 (readiness) reaches 30%, successfully counterbalancing B3 (resistance) which has declined to 19%.

**Net balance: B ≈ R → R > B (tipping to growth)**

### Phase 3 Dominance (M24-M36)

| Loop | M24 | M30 | M36 | Trend |
|------|------|------|------|-------|
| B1: Absorption | 34% | 35% | 35% | Persistent |
| B2: Skill Valley | 8% | 5% | 5% | Nearly gone |
| B3: Resistance | 14% | 5% | 5% | R5 wins |
| B4: Seniority | 10% | 13% | 13% | Growing slowly |
| R1: Trust | 32% | 40% | 40% | Strong |
| R2: Proficiency | 42% | 45% | 45% | Dominant |
| R3: Savings | 10% | 18% | 18% | Active |
| R4: Capital | 30% | 35% | 35% | Strong |
| R5: Readiness | 35% | 38% | 38% | Stable |

**Net balance: R > B (growing) → R ≥ B (stable growth)**

### Strategic Implication

The dominance analysis reveals the fundamental strategic insight of the model: **the organization must survive Phase 1 to reach Phase 2.** The first 12 months produce negative financial returns, visible resistance, and modest adoption gains. Leaders who evaluate the transformation during this period will see a system that appears to be failing.

In reality, the reinforcing loops are silently building strength. The decision to continue investing through Phase 1 — maintaining training budgets, sustaining change management, and not declaring failure — is the single most consequential strategic choice.

---

## 7. The Five Variant Scenarios

The model is validated against five variants that test different initial conditions while holding the scenario constant (Claims function, Copilot deployment, P2-Balanced policy).

### Variant 1: Open-Loop (No Human Feedback)

All human system dynamics disabled. Adoption follows the raw S-curve. This produces $17.84M in savings — the theoretical ceiling. It represents what a naive automation assessment would project.

### Variant 2: Feedback Baseline (Claims p=25, r=45, t=35)

The reference scenario. Produces $4.66M — 26% of the open-loop projection. This 74% reduction is the "realistic adjustment" that accounts for human system dynamics. It is substantial but not fatal — moderate-readiness organizations still achieve positive returns.

### Variant 3: Error at Month 7

An AI system produces a high-visibility incorrect result at M7, triggering a trust crisis. Trust drops from 35→24 and recovers slowly. Net savings fall to $2.66M (43% less than baseline). Breakeven delays from M18 to M21. This scenario validates the trust asymmetry: fast destroy, slow build.

### Variant 4: High Readiness (p=60, r=70, t=65)

The Technology function's human system parameters applied to the Claims deployment. Produces $10.97M with M11 breakeven. Proficiency reaches 68, readiness 87. Dampening is only 31.1%. This represents a best-case realistic scenario — an organization that has invested in change management before deployment.

### Variant 5: Low Readiness (p=15, r=30, t=25)

An unprepared organization. Produces -$1.37M (negative returns). Never reaches breakeven. Dampening is 92.8% — almost all technology potential is lost. However, it still generates $835K in gross savings (vs $0 in v1), confirming that even low-readiness organizations extract some value, just not enough to cover investment.

---

## 8. The Five Policy Scenarios

Holding the scenario and initial conditions constant, five HR policies are tested:

| Policy | Description | HC Reduced | Net 36mo | Breakeven |
|--------|-------------|-----------|----------|-----------|
| P1 Cautious | Attrition-only, no layoffs | 34 | +$1.2M | M26 |
| P2 Balanced | Moderate reduction, phased | 66 | +$4.7M | M18 |
| P3 Aggressive | Maximum reduction, fast | 80 | +$6.8M | M13 |
| P4 Capability-First | No HC reduction, reinvest | 0 | -$2.2M | Never |
| P5 Accelerated | Front-loaded investment | 79 | +$6.8M | M13 |

**Policy spread: $9.0M** (P3 at +$6.8M vs P4 at -$2.2M). In v1, policies barely mattered ($892K spread) because the broken multiplier killed everything. In v2.1, policy is a consequential choice.

The P4 result (no HC reduction = negative returns) is not a model bug — it is the correct answer to "what happens if we deploy AI but don't reduce staff." Without salary savings, the investment in licenses, training, and change management has no financial return mechanism.

---

## 9. 40-Scenario Catalog

The model is validated against 40 scenarios spanning 10 families: technology injection, scope expansion, sequencing, headcount targets, budget constraints, regulatory changes, structural changes, HR programs, stress tests, and composite multi-year programs.

### Results Summary

| Outcome | Count | % |
|---------|-------|---|
| Profitable | 25 | 62% |
| Unprofitable (model issues) | 9 | 23% |
| Unprofitable (executor gaps) | 6 | 15% |

The 6 executor-gap scenarios (Do Nothing, Skills Academy, Reskill, Create Role, Vacancy, Merge Roles) are unprofitable because the scenario executor lacks specialized handlers for these transformation types — they aren't model calibration failures.

### Profitable Scenario Families

| Family | Win Rate | Avg Net$ | Key Insight |
|--------|----------|----------|-------------|
| automation_target | 2/2 | +$15.1M | Clear targets with broad scope drive highest returns |
| composite | 3/3 | +$12.0M | Multi-year programs compound human system growth |
| budget_constraint | 2/2 | +$6.5M | Even constrained budgets yield positive returns |
| stress_test | 2/3 | +$3.5M | System resilient to most shocks |
| regulatory | 2/2 | +$2.9M | New permissions unlock value |
| sequencing | 5/6 | +$2.5M | Order matters less than starting |
| headcount_target | 2/3 | +$1.5M | Moderate targets achievable |

---

## 10. Model Evolution — v1 → v2 → v2.1

*Reference: Diagram ⑤ Evolution*

The model went through three versions, with each version correcting fundamental first-principles errors discovered through careful examination of simulation results.

### v1: The Broken Model (1/40 profitable)

The original model was structurally correct — all six stocks, twelve flows, and the basic feedback architecture were sound. But five mathematical errors in how human factors translate to adoption rates caused the model to systematically destroy value.

The core symptom: 39 out of 40 scenarios showed negative ROI, with a total portfolio value of -$213.6M. Even the most favorable scenario (Technology function, high readiness) barely broke even. The model predicted that AI transformation is economically non-viable for virtually all organizations — a conclusion that contradicts observed reality.

### v2: The Multiplier Fix (16/40 profitable)

The first fix addressed the most destructive error: the `effective_multiplier` used a joint probability formula `(p/100) × (r/100)` that assumed proficiency and readiness are independent events. At Claims baseline values (p=25, r=45), this product is 0.1125 — destroying 89% of adoption potential in a single operation.

The corrected weighted blend `(0.35p + 0.45r + 0.20t)/100` produces 0.3600 — a 3.2× increase. This single fix moved 15 scenarios from unprofitable to profitable.

### v2.1: The Five Surgical Fixes (25/40 profitable)

Four additional fixes addressed the remaining errors:

**Fix 1 (effective_multiplier):** Product → weighted blend. 3.2× increase. *First Principle: Correlated dimensions are not independent events.*

**Fix 2 (trust_multiplier):** Linear penalty → smooth threshold bands. 1.4× increase. *Second-Order: Trust=35 doesn't mean 42% of people refuse to work.*

**Fix 3 (R5 readiness boost):** Added the missing reinforcing loop. 5× faster readiness growth. *Meadows: Every stock needs both inflows and outflows.*

**Fix 4 (B1 absorption):** Off-by-one error in overload signal. 13% more capacity freed. *First Principle: Zero HC reduction = zero additional workload.*

**Fix 5 (R3 savings connected):** Wired the disconnected savings reinvestment. +1-2% late boost. *Systems Thinking: A disconnected loop is the same as no loop.*

### Combined Impact

| Metric | v1 | v2.1 | Δ |
|--------|-----|------|---|
| Profitable scenarios | 1/40 (2.5%) | 25/40 (62%) | +24 scenarios |
| Total portfolio value | -$213.6M | +$113.6M | +$327.2M swing |
| Baseline net savings | -$1.75M | +$4.66M | +$6.41M |
| Breakeven | Never | Month 18 | Achievable |
| Year 3 adoption | 8% | 45% | 5.6× |
| Readiness growth (36mo) | +1.9 pts | +10.0 pts | 5.3× |

All five fixes together changed approximately 50 lines of code across 2 files. The architecture, cascade logic, rate equations, scenario mapping, and validation tests remained unchanged. The fixes were surgical — correcting the mathematical translation of human factors to adoption rates, not changing the system structure.

---

## 11. Real-World Benchmark Alignment

The v2.1 model was validated against observed enterprise AI adoption patterns:

| Metric | v2.1 Model | Real-World Range | Status |
|--------|-----------|-------------------|--------|
| Year 1 adoption (moderate org) | 28% | 20-35% | Aligned |
| Year 3 adoption | 45% | 40-60% | Aligned |
| Proficiency growth per year | +6.6 pts | +5-10 pts | Aligned |
| Breakeven timeline | M18 | M12-M24 | Aligned |
| Readiness growth (successful) | +10 pts/3yr | +8-15 pts | Aligned |
| Trust recovery from major error | Slow, partial | Slow, partial | Aligned |
| Low-readiness org outcome | Negative ROI | Negative or minimal | Aligned |
| Open-loop vs feedback gap | 74% reduction | 60-80% reduction | Aligned |

---

## 12. Diagram Reference Guide

### Diagram ① Stock & Flow

**What it shows:** The structural skeleton — what exists (stocks), what changes them (flows), and where delays occur.

**How to read it:** Rectangles are stocks (accumulate over time). Solid arrows are flows (rates of change). Dashed arrows are feedback connections. Red "DELAY" boxes mark structural delays. The thick brown arrow from Human System to Adoption (via effective_multiplier) is the most important connection — the binding constraint.

**Key insight:** The Human System composite stock at the bottom determines the effective_multiplier that controls how much of the technology ceiling is realized. Everything else flows from this single bottleneck.

### Diagram ② Causal Loop

**What it shows:** The complete causal structure with all 9 feedback loops, S/O polarity markings, and subsystem boundaries.

**How to read it:** "S" means same direction (A↑ causes B↑). "O" means opposite direction (A↑ causes B↓). Blue circles are balancing loops (odd number of O links). Red circles are reinforcing loops (even number of O links, or all S). Dashed lines are cross-system connections. The R5 loop (marked "NEW") is the v2.1 addition.

**Key insight:** The system has two competing forces — balancing loops trying to maintain the status quo and reinforcing loops trying to accelerate change. Which side wins determines whether the transformation succeeds or fails.

### Diagram ③ Behavior (Reference Mode)

**What it shows:** How the six stocks actually evolve over 36 months in the baseline scenario.

**How to read it:** Three time-series charts showing adoption (top), human system dimensions (middle), and financial position (bottom). Phase backgrounds (red/green/blue) show startup/acceleration/maturity. The gap between raw and effective adoption is the dampening — the cost of human factors.

**Key insight:** The M18 breakeven is the pivot. Financial returns are negative for 18 months, then compound positively. Organizations that stop investing before M18 never reach the payoff.

### Diagram ④ Loop Dominance

**What it shows:** Which loops control system behavior at each phase, and how the balance shifts from balancing-dominant to reinforcing-dominant.

**How to read it:** Horizontal bars show each loop's relative strength at 6-month intervals. Wider/darker bars mean stronger influence. The bottom summary shows the net balance: B ≫ R (stuck) → B ≈ R (tipping) → R > B (growing) → R ≥ B (stable).

**Key insight:** The system flips from balancing-dominant to reinforcing-dominant around M12-M18. Before: the organization feels stuck (resistance, skill gaps, absorption dominate). After: momentum builds on itself (proficiency, trust, readiness compound). The strategic imperative is to survive Phase 1 to reach Phase 2.

### Diagram ⑤ Model Evolution

**What it shows:** The five fixes from v1 to v2.1, each traced to a specific first-principles error, with before/after formulas and impact metrics.

**How to read it:** Three version boxes (red/amber/green) show the progression. Each fix row shows the original formula, the corrected formula, and the impact. The combined result bar at the bottom shows the total improvement across all key metrics.

**Key insight:** Small mathematical errors in how human factors translate to adoption rates produced enormous distortions in output. The model's behavior was dominated by a few key parameters — getting those parameters right (from first principles, not curve-fitting) was the difference between a model that predicted universal failure and one that predicts realistic, nuanced outcomes.

---

## 13. System Boundaries and Limitations

The model makes several simplifying assumptions that bound its applicability:

**Single-function scope.** The current simulation models one function at a time (e.g., Claims). Cross-function effects (a successful Claims deployment increasing Technology's readiness) are not yet modeled.

**Monthly granularity.** Daily or weekly fluctuations (a bad demo, a positive news article) are averaged into monthly timesteps. This means the model cannot capture acute events shorter than ~2 weeks.

**Homogeneous human system parameters.** All individuals within a function share the same proficiency, readiness, and trust scores. In reality, there is significant within-function variance (early adopters vs. resistors).

**Fixed technology ceiling.** L1/L2 automation potential is static over the simulation horizon. In reality, AI capabilities are improving, which would raise the ceiling during the 36-month period.

**No external labor market.** The model doesn't account for competitive dynamics — if you reduce HC, your best people may leave, changing the composition of the remaining workforce.

These limitations define the roadmap for v3.0: cross-function effects, individual-level modeling, dynamic technology ceilings, and labor market integration.

---

## 14. Metrics Summary

### Input Parameters (per function)

| Parameter | Description | Claims Baseline |
|-----------|-------------|----------------|
| headcount | Starting HC | 540 |
| annual_cost | Total salary cost | $29.5M |
| weighted_l1 | Technology ceiling | 63.5% |
| weighted_l2 | Available with current tech | 59.9% |
| weighted_l3 | Currently realized | 9.2% |
| ai_proficiency | Starting proficiency | 25 |
| change_readiness | Starting readiness | 45 |
| trust_level | Starting trust | 35 |

### Simulation Parameters

| Parameter | Value | Role |
|-----------|-------|------|
| S-curve L (ceiling) | Function's L2 | Maximum adoption |
| S-curve k (steepness) | 0.15 | How fast raw adoption grows |
| S-curve t_mid | 12 | Inflection month |
| Effective multiplier weights | p=0.35, r=0.45, t=0.20 | How human dims combine |
| Effective multiplier floor | 0.15 | Minimum adoption (early adopters) |
| Base absorption rate | 0.30 | B1 starting capacity absorption |
| Max absorption rate | 0.50 | B1 ceiling |
| Trust bands | <20: 0.5, 20-40: 0.5-0.9, 40-60: 0.9-1.0 | Trust to behavior mapping |
| R5 boost factor | 1.5 | Adoption success → readiness rate |
| Simulation horizon | 36 months | Time frame |
| Quarterly HC review | Every 3 months | Reduction delay |

### Output Metrics (per scenario)

| Metric | Description | Baseline v2.1 |
|--------|-------------|---------------|
| final_effective_adoption | Realized adoption at M36 | 44.7% |
| total_hc_reduced | FTEs removed over 36mo | 66 |
| net_savings_36mo | Cumulative net financial impact | +$4,657K |
| breakeven_month | When cumulative net turns positive | M18 |
| avg_dampening | Mean effective/raw ratio | 35.3% |
| final_proficiency | Proficiency at M36 | 44.9 |
| final_readiness | Readiness at M36 | 55.1 |
| final_trust | Trust at M36 | 46.4 |
| profitable | Boolean: net > 0 at M36 | Yes |

---

*"A system is an interconnected set of elements that is coherently organized in a way that achieves something. A system must consist of three kinds of things: elements, interconnections, and a function or purpose."*

*— Donella Meadows, Thinking in Systems*
