# How the Simulation Works: A First-Principles Guide

> **Audience**: Business users, HR leaders, and transformation strategists who want
> to understand what the simulation computes, why, and how to interpret results.
> No programming knowledge required.

---

## Table of Contents

1. [The Core Question](#1-the-core-question)
2. [The Mental Model: A Bathtub](#2-the-mental-model-a-bathtub)
3. [What Gets Simulated](#3-what-gets-simulated)
4. [Step-by-Step: How a Simulation Runs](#4-step-by-step-how-a-simulation-runs)
5. [When Do People Get "Freed"?](#5-when-do-people-get-freed)
6. [The Three Scenarios](#6-the-three-scenarios)
7. [The Adoption Curve: Why Results Take Time](#7-the-adoption-curve-why-results-take-time)
8. [Human Factors: The Invisible Forces](#8-human-factors-the-invisible-forces)
9. [The J-Curve: It Gets Worse Before It Gets Better](#9-the-j-curve-it-gets-worse-before-it-gets-better)
10. [How Costs Work](#10-how-costs-work)
11. [Feedback Loops: The System Talks Back](#11-feedback-loops-the-system-talks-back)
12. [Reading the Results](#12-reading-the-results)
13. [Key Configuration Knobs](#13-key-configuration-knobs)
14. [Worked Example: 50-Person Team](#14-worked-example-50-person-team)

---

## 1. The Core Question

The simulation answers one question:

> **"If we change how work is done in this part of the organization, what
> happens to the people, the costs, and the risks -- month by month, over
> the next 3 years?"**

It does NOT predict the future. It computes the *consequences* of a specific
intervention, given a set of assumptions. Think of it as a flight simulator
for organizational transformation.

---

## 2. The Mental Model: A Bathtub

Imagine a bathtub. Water flows in through a faucet (hiring, redeployment)
and flows out through a drain (separations, attrition). The water level is
your headcount.

```
        HIRING / REDEPLOYMENT
              |
              v
    +---------+----------+
    |                      |   <-- Headcount (water level)
    |     WORKFORCE        |
    |                      |
    +---------+------------+
              |
              v
       SEPARATIONS / ATTRITION
```

When you introduce AI automation, you're essentially saying: "Some of this
work can now be done by machines." This doesn't instantly drain the bathtub.
Instead, it creates **freed capacity** -- people whose work has been partially
or fully automated.

What happens to those people is a choice:
- **Redeployed** (60% by default): Moved to other valuable work
- **Separated** (remaining 40%): Leave the organization (with severance)
- **Attrited naturally**: Leave through normal turnover (12% per year)

---

## 3. What Gets Simulated

The simulation tracks 5 interconnected systems ("stocks") every month:

| Stock | What It Tracks | Example |
|-------|---------------|---------|
| **Workforce** | Headcount, separations, redeployment | "142 people freed, 85 redeployed" |
| **Adoption** | How many people are actually using the new tools | "Month 6: 15% have adopted" |
| **Skills** | Which skills are growing, declining, or emerging | "Prompt engineering is sunrise" |
| **Financial** | Monthly savings, costs, cumulative ROI | "Breakeven at month 14" |
| **Human Factors** | Resistance, morale, proficiency, culture | "Resistance peaked at month 3" |

These are not independent. They form **feedback loops** -- changes in one
stock affect the others.

---

## 4. Step-by-Step: How a Simulation Runs

### Phase A: "What Could Change?" (The Cascade -- runs once)

Before simulating month-by-month, we first compute the **theoretical maximum**
impact -- what would happen if everything were adopted instantly and perfectly.
This runs through 8 cascading steps:

```
Step 1: TASK CHANGES
  "Which tasks can be automated, and to what level?"
    |
Step 2: WORKLOAD SHIFTS
    "How does each role's workload mix change?"
    |
Step 3: ROLE IMPACT
    "How much capacity is freed in each role?"
    |
Step 4: SKILL IMPACT
    "Which skills are sunrise (growing) vs sunset (declining)?"
    |
Step 5: WORKFORCE CHANGES
    "How many people are freed? How many can be redeployed?"
    |
Step 6: FINANCIAL PROJECTION
    "What are the savings and costs?"
    |
Step 7: RISK ASSESSMENT
    "What could go wrong?"
    |
Step 8: VALIDATION
    "Do the numbers pass sanity checks?"
```

This gives us the *ceiling* -- the maximum possible impact. But reality
doesn't work like that.

### Phase B: "How Does It Actually Play Out?" (The Monthly Loop)

Now we simulate reality. Starting from month 1, for each month we compute:

1. **How many people have adopted the tool this month?** (Bass diffusion curve)
2. **How effectively can they use it?** (Proficiency, with a floor of 50%)
3. **How much capacity is actually freed?** (Adoption x Proficiency x Theoretical Max)
4. **What does that cost this month?** (Categorized by type)
5. **What are people feeling?** (Resistance, morale, culture shift)
6. **Are any feedback loops kicking in?** (Positive or negative spirals)

This produces a **trajectory** -- 36 monthly snapshots showing how the
transformation evolves over time.

---

## 5. When Do People Get "Freed"?

This is the most important question. Here's exactly how it works:

### Step 1: Task Automation Level

Every task in the organization has an **automation score** (0-100). The
simulation changes this score based on the intervention:

| Automation Score | Classification | What It Means |
|-----------------|----------------|--------------|
| 0-19 | **Human Only** | Requires full human judgment |
| 20-49 | **Human Led** | Human does most work, AI assists |
| 50-79 | **Shared** | Human and AI split the work |
| 80-99 | **AI Led** | AI does most work, human oversees |
| 100 | **AI Only** | Fully automated |

> **Example**: "Process insurance claim" might move from score 35 (Human Led)
> to score 65 (Shared) after introducing Claims AI.

### Step 2: Workload Change

When a task's automation level changes, it shifts the **workload mix** for
every role that performs that task. Each role's work is categorized into
these same buckets (Human Only, Human Led, Shared, AI Led).

> **Example**: A Claims Adjuster who spent 60% of time on now-automated tasks
> sees their workload shift from "mostly Human Led" to "mostly Shared."

### Step 3: Freed Capacity

The freed capacity for each role depends on how much work shifted to higher
automation AND the person's career level:

```
Freed Capacity = Workload Shift x Level Impact Factor
```

**Level impact factors** (this is crucial):

| Career Band | Impact Factor | Why |
|-------------|--------------|-----|
| Entry-level | 1.4x | Routine work, most automatable |
| Mid-level | 1.2x | Mix of routine and judgment |
| Senior | 1.0x | Baseline |
| Lead | 0.8x | More coordination, less routine |
| Principal | 0.6x | Strategic work, less automatable |
| Director | 0.4x | Leadership-heavy |
| VP | 0.3x | Almost entirely strategic |
| C-Suite | 0.2x | Minimal direct task impact |

> **Example**: If automation frees 30% of workload for a role:
> - An entry-level person in that role: 30% x 1.4 = **42% freed**
> - A senior person in that role: 30% x 1.0 = **30% freed**
> - A director in that role: 30% x 0.4 = **12% freed**
>
> Entry-level workers are most affected because their work tends to be
> more routine and repetitive.

### Step 4: Does This "Free" the Person?

Having freed capacity does NOT automatically mean the person loses their job.
Here's what the model computes:

- **Freed headcount** = Sum of all (freed_capacity_pct x headcount) across titles
- This is expressed as **full-time equivalents (FTEs)**, not whole people

> **Example with 50 people**:
> - 20 entry-level, each 42% freed = 8.4 FTE freed
> - 15 mid-level, each 25% freed = 3.75 FTE freed
> - 10 senior, each 15% freed = 1.5 FTE freed
> - 5 leads, each 8% freed = 0.4 FTE freed
> - **Total: 14.05 FTE freed** out of 50 people (28%)

### Step 5: What Happens to Freed Capacity

Of those 14.05 freed FTEs:
- **60% redeployed** (default): 8.4 FTEs moved to other work (new projects,
  higher-value tasks, filling vacancies elsewhere)
- **40% separated**: 5.6 FTEs reduced through separation + natural attrition
- Natural attrition (12%/year) absorbs some reductions without layoffs

**Key insight**: "Freed" does not mean "fired." It means the organization has
surplus capacity that can be redirected.

---

## 6. The Three Scenarios

### Scenario A: Role Redesign

> "What if we redesign roles to automate routine tasks?"

- Takes an **automation factor** (default 0.5 = moderate automation push)
- Evaluates every task and shifts automatable ones to higher levels
- No specific technology -- assumes a general AI tooling mix
- Best for: Strategic workforce planning, understanding automation exposure

> **Example**: "Redesign Claims Processing roles. Target: automate 50% of
> automatable work."

### Scenario B: Technology Adoption

> "What happens when we deploy a specific AI tool?"

- Picks a named technology (e.g., Microsoft Copilot, UiPath, ServiceNow AI)
- Each technology has a **profile** defining which task types it impacts and
  how strongly
- Includes technology licensing and implementation costs
- Best for: Build-vs-buy decisions, technology ROI analysis

> **Example**: "Deploy Microsoft Copilot across the IT department. What's the
> 3-year ROI?"

**Built-in technology profiles**:

| Technology | Best For | Typical Impact |
|------------|---------|----------------|
| Microsoft Copilot | Knowledge work, documents, communication | Moderate, broad |
| UiPath | Repetitive process automation | High on routine tasks |
| ServiceNow AI | IT service management, workflows | Moderate, focused |
| Salesforce Einstein | CRM, customer analytics | Moderate, focused |
| GitHub Copilot | Software development | High on coding tasks |

### Scenario C: Task Distribution

> "What if we redistribute tasks across career levels?"

- Defines a **target distribution** (e.g., "30% entry, 25% mid, 20% senior...")
- Computes the minimum task reclassifications needed to reach that target
- Best for: Organizational restructuring, span-of-control optimization

---

## 7. The Adoption Curve: Why Results Take Time

When you deploy a new technology, people don't adopt it overnight. The simulation
uses the **Bass Diffusion Model** -- the same math used to predict how TVs,
smartphones, and social media spread through populations.

```
New adopters this month = [Innovation + Imitation x Current%] x Remaining x HFM
```

Where:
- **Innovation** (p): People who adopt because it's available (early adopters)
- **Imitation** (q): People who adopt because colleagues are using it (word of mouth)
- **Remaining**: People who haven't adopted yet
- **HFM**: Human Factor Multiplier (resistance, morale slow it down or speed it up)

This creates an **S-curve**:

```
100% |                              ___________
     |                           __/
     |                        __/
     |                     __/
     |                   _/
     |                 _/
     |               _/
     |             _/
     |           /
     |         /
     |       /
     |     /
     |   _/
     | _/
  0% |/________________________________
     Month 1    6    12    18    24    36
```

**Three speeds**:

| Speed | Innovation (p) | Imitation (q) | 50% Adoption By | Best For |
|-------|---------------|---------------|-----------------|----------|
| **Fast** | 0.03 | 0.60 | ~Month 10 | Tech-savvy teams, strong leadership |
| **Moderate** | 0.02 | 0.40 | ~Month 14 | Typical enterprise (default) |
| **Slow** | 0.01 | 0.25 | ~Month 20 | Conservative orgs, complex tools |

### Why This Matters

In Month 1, with moderate adoption, only about **2%** of people are using the
tool. So:
- Theoretical freed capacity = 14 FTE
- **Actual freed capacity = 14 x 2% x 55% = 0.15 FTE**
- Monthly savings = barely anything

By Month 18, about **70%** have adopted:
- **Actual freed capacity = 14 x 70% x 80% = 7.8 FTE**
- Monthly savings = substantial

This is why transformations take time to pay off.

---

## 8. Human Factors: The Invisible Forces

People are not machines. The simulation tracks 4 human dimensions that
influence how fast adoption happens and how much value is actually captured:

### Resistance (starts at 60%)

People naturally resist change. Resistance **slows adoption**.

```
Resistance goes DOWN when:
  - Time passes (people adapt, -5% per month natural decay)
  - Good communication (leadership messaging)
  - Training is available

Resistance goes UP when:
  - Change is happening fast (pace shock)
  - Layoffs occur (fear spreads)
```

> Think of it like this: If 60% of the organization is resistant, the
> adoption S-curve stretches out. Things take longer.

### Morale (starts at 70%)

How people feel about the transformation.

```
Morale goes UP when:
  - People learn new skills (growth signals)
  - Career paths are visible (reskilling programs)
  - Adoption is succeeding (momentum)

Morale goes DOWN when:
  - Layoffs happen (survivor guilt)
  - Uncertainty is high (no clear communication)
  - The change drags on without visible wins
```

### Proficiency (starts at 10%)

How well people can actually use the new tools. This is critical because
it determines how much value the automation delivers.

```
Proficiency = 0.5 + 0.5 x raw_proficiency
```

**Why the 50% floor?** Even a beginner using an AI tool gets significant
benefit -- the tool does the heavy lifting. Full proficiency adds the
remaining benefit. This prevents the unrealistic scenario where month-1
automation delivers zero value.

> **Example**:
> - Month 1, proficiency = 10%: Effectiveness = 0.5 + 0.5 x 0.1 = **55%**
> - Month 12, proficiency = 50%: Effectiveness = 0.5 + 0.5 x 0.5 = **75%**
> - Month 36, proficiency = 90%: Effectiveness = 0.5 + 0.5 x 0.9 = **95%**

### Culture Readiness (starts at 30%)

How ready the organization's culture is for AI-driven change. This evolves
slowly -- culture shifts take 24 months (configurable) to settle.

### Combined Effect: Human Factor Multiplier (HFM)

These four factors combine into a single number that scales adoption speed:

```
HFM = 0.30 x (1 - Resistance) + 0.25 x Proficiency + 0.20 x Morale + 0.25 x Culture
```

| Factor | Weight | Why This Weight |
|--------|--------|----------------|
| Low Resistance | 30% | Largest barrier to adoption |
| Proficiency | 25% | Can people use the tool? |
| Morale | 20% | Will they want to? |
| Culture | 25% | Does the environment support it? |

> **Month 1 HFM** (typical): 0.30 x 0.4 + 0.25 x 0.1 + 0.20 x 0.7 + 0.25 x 0.3
> = 0.12 + 0.025 + 0.14 + 0.075 = **0.36**
>
> This means adoption in month 1 happens at only 36% of its theoretical speed.
> By month 24, HFM might rise to 0.70+, accelerating adoption.

---

## 9. The J-Curve: It Gets Worse Before It Gets Better

When a company introduces AI automation, **productivity temporarily drops**
before it improves. This is the J-curve -- a well-documented phenomenon in
organizational change.

```
Productivity
     |
100% |----\
     |     \              ____________
     |      \           _/
     |       \        _/
     |        \     _/
  85%|         \___/         <-- The "dip" (15% default)
     |
     |________________________________
     Month 1   3    6    12    24   36
```

**Why does productivity dip?**
- People spend time learning new tools instead of doing work
- Existing processes break before new ones are established
- Meetings, training sessions, change management activities
- Anxiety and uncertainty reduce focus

**Default settings**:
- Dip magnitude: **15%** productivity loss
- Dip duration: **6 months** (tapers linearly to zero)
- The dip is a cost applied to ALL affected employees, not just adopters
  (because the entire organization feels the disruption)

> **Example (50-person team, avg salary $80K)**:
> - Month 1 J-curve cost: 50 x $80K x 15% x 1.0 / 12 = **$50,000**
> - Month 3 J-curve cost: 50 x $80K x 15% x 0.5 / 12 = **$25,000**
> - Month 7 onward: $0 (dip is over)
> - Total J-curve cost: ~$175,000

---

## 10. How Costs Work

The simulation categorizes costs into three types based on when they occur:

### Committed Costs (fixed schedule, happen regardless of adoption)

| Cost | Duration | What It Is |
|------|----------|-----------|
| **Implementation** | First 12 months | Infrastructure, integration, setup |
| **Change management** | First 24 months | Communication, stakeholder engagement |
| **J-curve** | First 6 months | Productivity dip (see above) |

These are "sunk costs" -- you pay them as part of launching the initiative,
whether adoption is at 5% or 95%.

### Adoption-Proportional Costs (scale with how many people are using the tool)

| Cost | Duration | How It Scales |
|------|----------|--------------|
| **Tech licensing** | Full timeline | Pay for licenses as people adopt |
| **Reskilling** | First 18 months | Train people as they onboard |

> **Why this matters**: In month 1, only 2% have adopted, so you're paying
> for 2% of licenses and 2% of training -- not 100%. This is realistic.
> You don't buy 1000 licenses on day 1 when only 20 people are using the tool.

### Separation-Proportional Costs (scale with actual departures)

| Cost | Trigger | How It Scales |
|------|---------|--------------|
| **Severance** | When people actually leave | 3 months salary per separation |

> Severance is not front-loaded. If 5 FTEs separate over the entire timeline,
> the severance is spread across the months they actually leave, proportional
> to the adoption level that month.

### Monthly Cost Example (50-person team)

| Month | Adoption | J-curve | Implementation | Licensing | Reskilling | Severance | Total |
|-------|----------|---------|---------------|-----------|-----------|-----------|-------|
| 1 | 2% | $50K | $8K | $0.3K | $0.5K | $0.1K | **$59K** |
| 6 | 12% | $8K | $8K | $1.7K | $2.8K | $0.5K | **$21K** |
| 12 | 40% | $0 | $8K | $5.6K | $9.3K | $1.7K | **$25K** |
| 18 | 65% | $0 | $0 | $9.1K | $15.2K | $2.8K | **$27K** |
| 24 | 82% | $0 | $0 | $11.5K | $0 | $3.5K | **$15K** |
| 36 | 95% | $0 | $0 | $13.3K | $0 | $4.1K | **$17K** |

*(Numbers are illustrative, not from an actual run)*

Notice: J-curve dominates early months, then disappears. Other costs
ramp up with adoption, which matches reality.

---

## 11. Feedback Loops: The System Talks Back

The simulation detects 5 feedback loops -- patterns where one outcome amplifies
or dampens another:

### Reinforcing Loops (accelerators -- things that speed up the transformation)

**R1: Productivity Flywheel**
```
More adoption --> More savings --> More budget for AI --> More adoption
```
Activates when: savings exceed costs AND adoption > 30%.
This is the "virtuous cycle" -- once it kicks in, things accelerate.

**R2: Capability Compounding**
```
More adoption --> More proficiency --> Better tool usage --> Even more adoption
```
Activates when: proficiency > 40% AND adoption > 20%.
People who use the tool get better at it, which encourages others to adopt.

### Balancing Loops (brakes -- things that slow down the transformation)

**B1: Change Resistance**
```
Fast pace of change --> Anxiety --> Resistance --> Slower adoption
```
Activates when: resistance > 50%.
Push too hard, and the organization pushes back.

**B2: Skill Gap Brake**
```
Fast deployment --> Skill gaps --> People can't use tools --> Slower adoption
```
Activates when: proficiency < 30% AND adoption > 10%.
If you deploy faster than people can learn, adoption stalls.

**B3: Knowledge Drain**
```
Separations --> Lost institutional knowledge --> Quality problems
```
Activates when: monthly separation rate > 1%.
Losing too many people too fast damages organizational capability.

### What This Means in Practice

Early months: B1 and B2 are active (resistance is high, proficiency is low).
Adoption is slow. This is normal.

Middle months: R2 starts kicking in (proficiency improves). Adoption accelerates.

Late months: R1 activates (savings exceed costs). The transformation becomes
self-funding. B1 and B2 fade as resistance drops and proficiency grows.

---

## 12. Reading the Results

### The Trajectory Table

The simulation produces a monthly snapshot table. Key columns:

| Column | What to Look For |
|--------|-----------------|
| **Adoption** | Should follow S-curve. If it flattens early, check human factors. |
| **Effective Freed HC** | Grows with adoption. This is the ACTUAL freed capacity, not theoretical. |
| **Monthly Savings** | Should grow as adoption grows. |
| **Monthly Costs** | Should peak early (J-curve) then taper. |
| **Cumulative Net** | Starts negative (investment phase), should turn positive (payoff phase). |
| **NPV** | Risk-adjusted value. Discounts future savings at 10%/year. |

### Key Metrics

| Metric | Good | Warning | Concerning |
|--------|------|---------|-----------|
| **ROI** | > 100% | 30-100% | < 30% |
| **Breakeven Month** | < 12 | 12-24 | > 24 |
| **Final Adoption** | > 85% | 60-85% | < 60% |
| **Final Resistance** | < 0.3 | 0.3-0.5 | > 0.5 |
| **Morale** | > 0.6 | 0.4-0.6 | < 0.4 |

### Milestones to Watch

- **Month 6**: J-curve should be ending. Monthly costs start declining.
- **Month 12**: Implementation costs end. Adoption should be 30-50%.
- **Month 18**: Reskilling costs end. Proficiency should be high enough
  for the R2 loop to activate.
- **Month 24**: Change management costs end. Only licensing and severance
  remain as ongoing costs.

---

## 13. Key Configuration Knobs

These are the parameters you can adjust to model different scenarios:

### Workforce & Organization

| Parameter | Default | Range | What It Controls |
|-----------|---------|-------|-----------------|
| Redeployability | 60% | 0-100% | What fraction of freed workers get new roles |
| Attrition rate | 12%/yr | 5-25% | Natural annual turnover |
| Severance months | 3 | 1-12 | Months of salary per separated employee |
| Max headcount reduction | 100% | 5-50% | Cap on total workforce reduction |

### Financial

| Parameter | Default | What It Controls |
|-----------|---------|-----------------|
| Change management | 5% of savings | Investment in communication & stakeholder programs |
| Reskilling cost | $2,500/skill/person | Cost to retrain each employee per skill |
| Implementation factor | 15% of licensing | Infrastructure and integration overhead |
| J-curve dip | 15% | Severity of productivity drop during transition |
| J-curve duration | 6 months | How long the productivity dip lasts |

### Human Factors (organizational starting conditions)

| Parameter | Default | What It Represents |
|-----------|---------|-------------------|
| Initial resistance | 60% | How much the org resists change at day 0 |
| Initial morale | 70% | Baseline employee morale |
| Initial AI proficiency | 10% | How skilled employees are with AI tools today |
| Culture readiness | 30% | How ready the culture is for AI transformation |
| Culture time constant | 24 months | How long culture takes to shift (inertia) |

### Adoption Speed

| Setting | Best For |
|---------|---------|
| **Fast** | Tech-forward companies, strong executive sponsorship, simple tools |
| **Moderate** | Typical enterprise transformation (default) |
| **Slow** | Regulated industries, complex tools, weak change management |

---

## 14. Worked Example: 50-Person Team

Let's trace through a complete simulation for a small team.

### Setup

- **Team**: Customer Support (50 people)
- **Scenario**: Deploy ServiceNow AI for ticket automation
- **Mix**: 20 entry, 15 mid, 10 senior, 3 leads, 2 principals
- **Average salary**: $80,000
- **Timeline**: 36 months

### Step 1: Task Analysis (Cascade)

The simulation examines every task the team performs. ServiceNow AI is
strong at ticket routing, knowledge lookup, and response drafting.

| Task | Before | After | Change |
|------|--------|-------|--------|
| Route incoming tickets | Human Led (35) | AI Led (85) | +50 |
| Draft response templates | Human Led (40) | Shared (65) | +25 |
| Complex case resolution | Human Only (15) | Human Led (25) | +10 |
| Quality review | Human Led (30) | Human Led (30) | No change |
| Team coaching | Human Only (5) | Human Only (5) | No change |

### Step 2: Freed Capacity

Based on workload shifts and level factors:

| Level | People | Freed % | FTEs Freed |
|-------|--------|---------|-----------|
| Entry | 20 | 38% (27% x 1.4) | 7.6 |
| Mid | 15 | 22% | 3.3 |
| Senior | 10 | 12% | 1.2 |
| Lead | 3 | 6% | 0.2 |
| Principal | 2 | 3% | 0.1 |
| **Total** | **50** | | **12.4 FTE** |

### Step 3: Month-by-Month Trajectory

| Month | Adoption | Effective Freed HC | Monthly Savings | Monthly Cost | Cumulative Net |
|-------|----------|-------------------|-----------------|-------------|----------------|
| 1 | 2% | 0.1 | $700 | $52K | -$51K |
| 3 | 5% | 0.4 | $2.8K | $32K | -$123K |
| 6 | 12% | 1.2 | $8K | $15K | -$173K |
| 12 | 40% | 4.5 | $30K | $11K | -$65K |
| 18 | 65% | 8.0 | $53K | $7K | +$189K |
| 24 | 82% | 10.0 | $67K | $5K | +$604K |
| 36 | 95% | 11.5 | $77K | $5K | +$1.5M |

*(Numbers are illustrative based on model defaults)*

### Step 4: Summary

- **Total savings over 36 months**: ~$1.8M
- **Total costs**: ~$350K
- **Net impact**: ~$1.5M
- **ROI**: ~420%
- **Breakeven month**: ~14
- **People redeployed**: 7.4 FTE (to higher-value work)
- **People separated**: 5.0 FTE (spread over 3 years, mostly via attrition)

### What This Tells the Decision Maker

1. **The first 6 months will cost more than they save.** This is expected.
   Budget accordingly.
2. **Breakeven happens around month 14.** After that, the project pays for itself.
3. **Only ~5 FTEs are actually separated**, mostly through natural attrition (12%/year
   means 6 people leave naturally per year anyway). Minimal involuntary layoffs.
4. **7.4 FTEs get redeployed** to higher-value work -- this is where the real
   organizational benefit lies.
5. **ROI of 420%** means for every $1 invested, you get $4.20 back over 3 years.

---

## Summary: The Model in One Paragraph

The simulation takes an organizational scope (department, function, or role
group), applies an intervention (role redesign, technology adoption, or task
redistribution), and computes the theoretical maximum impact via an 8-step
cascade. It then runs a month-by-month time-stepped loop using Bass diffusion
for adoption, human factors for organizational dynamics, categorized costs
(committed, adoption-proportional, separation-proportional), and feedback
loop detection. The result is a 36-month trajectory showing exactly when
costs peak, when savings overtake costs, when breakeven occurs, and what
the final ROI looks like -- giving decision-makers a realistic, evidence-based
view of the transformation's financial and human impact.
