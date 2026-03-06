# Etter Digital Twin: Expanded Capability Catalog & Priority Framework

## Addendum to Digital Twin Exploration v1.0

*Version 1.1 — February 2026*

---

## SECTION A: ETTER'S DATA BOUNDARY — First Principles

### What Etter Knows vs. What It Doesn't

Before expanding simulation domains, we must be precise about the data envelope. This is the governing constraint for everything that follows.

**Etter operates at the ROLE level, not the INDIVIDUAL level.**

This is a fundamental architectural choice that differentiates Etter from Visier, Workday analytics, or any PII-based platform. It has consequences:

```
ETTER HAS (Role-Level, Aggregate)          ETTER DOES NOT HAVE (Individual, PII)
─────────────────────────────────           ─────────────────────────────────────
✅ Job Titles & Role Names                  ❌ Employee names
✅ Role Taxonomy (Family, Group, Function)  ❌ Individual performance ratings
✅ Headcount per role                       ❌ Individual compensation
✅ Average salary / cost per role           ❌ Individual engagement scores
✅ Location distribution per role           ❌ Individual career history
✅ Task decomposition & classification      ❌ Individual learning records
✅ Skill requirements per role              ❌ Individual attrition risk scores
✅ Automation / augmentation scores         ❌ Demographic data (age, gender, etc.)
✅ Workflow & process maps                  ❌ Manager-employee relationships
✅ Technology / tool mapping per role        ❌ Individual time tracking
✅ Peer benchmarks & industry data          ❌ Employee sentiment / survey responses
✅ Compensation benchmarks (market)         ❌ Individual 360° feedback
✅ Location insights (cost, talent pool)    ❌ Attendance / leave patterns
✅ Sunrise/sunset skills with trends        ❌ Individual skill assessments
✅ Role adjacency & similarity scores       ❌ Social network / collaboration data
✅ Risk framework dimensions                ❌ Succession pipeline (named individuals)
```

### Why This Matters for Twin Design

**Strength:** No PII means faster enterprise adoption (lower compliance burden, no GDPR/privacy friction, no data residency issues). An enterprise can share role-level data with Etter in weeks, not months.

**Constraint:** Etter simulates STRUCTURAL and FUNCTIONAL transformation — what happens to roles, workflows, skills, and costs. It does NOT simulate individual employee journeys, engagement impact, or person-level attrition.

**Design Rule:** Every simulation domain must be answerable with role-level aggregate data. If a capability requires individual-level data to be meaningful, it either needs a data enrichment path (enterprise provides aggregate inputs) or it's out of scope.

### Data That Etter Can Request From Enterprises (Without PII)

These are aggregate data points enterprises can safely share to enrich the twin:

```
ENRICHMENT DATA (no PII, role-level aggregates):
├── Headcount by role × location × band level
├── Average salary by role × location (not individual)
├── Vacancy rate by role (open positions / total)
├── Average tenure by role (aggregate, not per-person)
├── Average time-to-fill by role
├── Training budget per function
├── Attrition rate by role/function (aggregate %)
├── Current technology stack per function
├── Planned technology investments
├── Process SLA performance (not per-person)
├── Budget constraints and targets
├── Strategic priorities (which functions to transform first)
└── Regulatory constraints (which roles are compliance-sensitive)
```

This enrichment data is what unlocks the extended simulation domains.

---

## SECTION B: THE COMPLETE SIMULATION DOMAIN CATALOG

### Priority Framework

Every capability is scored on three dimensions:

1. **Data Readiness** — Can Etter support this with current + reasonable enrichment data?
2. **Value Impact** — How much does this move the needle for enterprise decision-makers?
3. **Differentiation** — Does this create distance from competitors, or is it table stakes?

Priority tiers:

| Tier | Label | Meaning |
|:-----|:------|:--------|
| **P0** | CORE IDENTITY | This IS the twin. Without it, there's no product |
| **P1** | HIGH VALUE | Directly drives enterprise buying decisions |
| **P2** | COMPLETE PRODUCT | Expected by sophisticated buyers, fills competitive gaps |
| **P3** | MOAT BUILDER | Creates long-term defensibility, network effects |
| **P4** | HORIZON | Future vision. Requires new data sources or partnerships |

---

### P0: CORE IDENTITY — The Twin Doesn't Exist Without These

These are the five domains from the original exploration. They define what makes this an "Etter Twin" vs. a generic workforce planning tool.

#### 0.1 Role Redesign Simulation

**Question:** "What should this role become after AI transformation?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Task decomposition, AI classification, skill mapping, headcount |
| Data Readiness | ✅ Fully supported by existing Etter outputs |
| Value Impact | ⭐⭐⭐⭐⭐ — This is the #1 use case every CHRO asks about |
| Differentiation | ⭐⭐⭐⭐⭐ — Task-level precision is Etter's unique capability |
| Buyer | VP/Director level, function heads |

**Capabilities within this domain:**
- Automate a role (remove AI tasks, project future profile)
- Merge/split roles (combine tasks, check feasibility)
- Design new roles (orphaned task synthesis, "Model a New Role")
- Role evolution pathway (current → transition → future state)
- Future-state JD generation (Etter's AI-Ready JD model)

---

#### 0.2 Workforce Planning Simulation

**Question:** "How many people, where, with what skills, at what cost?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Headcount, cost, attrition rates, role adjacency |
| Data Readiness | ✅ Etter + basic enterprise enrichment (attrition %, vacancy rate) |
| Value Impact | ⭐⭐⭐⭐⭐ — Direct P&L impact, CFO-level decisions |
| Differentiation | ⭐⭐⭐⭐ — Orgvue/Visier do this, but without task-level grounding |
| Buyer | CHRO, CFO, Head of Workforce Planning |

**Capabilities within this domain:**
- Headcount trajectory modeling (with automation rollout)
- Attrition-adjusted planning (natural attrition absorbs some reduction)
- Redeployment pathway mapping (using role adjacency scores)
- Build vs. buy analysis (reskill existing vs. hire new)
- Budget-constrained optimization (maximize transformation within $X)

---

#### 0.3 Process Optimization Simulation

**Question:** "Which processes should we automate, in what order?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Workflow builder output, task scores, role assignments |
| Data Readiness | ✅ Fully supported by Etter's Workflow Builder |
| Value Impact | ⭐⭐⭐⭐⭐ — COOs and process owners live for this |
| Differentiation | ⭐⭐⭐⭐⭐ — Combining process view WITH workforce impact is unique |
| Buyer | COO, VP Operations, Process Excellence teams |

**Capabilities within this domain:**
- Workflow automation sequencing (optimal order with dependencies)
- Bottleneck migration modeling (where does bottleneck shift?)
- Cross-workflow cascade analysis (automate AP → impacts Reporting)
- Process redesign simulation (current → AI-first future state)
- SLA impact projection (does automation improve or risk service levels?)

---

#### 0.4 Skills Strategy Simulation

**Question:** "What capabilities do we need to build, and how?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Skills architecture, sunrise/sunset, proficiency gaps, courses |
| Data Readiness | ✅ Fully supported by Etter's Dynamic Skills Architecture |
| Value Impact | ⭐⭐⭐⭐ — L&D and talent leaders need this |
| Differentiation | ⭐⭐⭐⭐⭐ — Draup's 21K+ skill taxonomy is unmatched |
| Buyer | CLO, VP Talent, L&D Directors |

**Capabilities within this domain:**
- Skill demand forecasting (which skills needed in 12/24/36 months)
- Training ROI modeling (which investments cover most roles)
- Concentration risk analysis (dangerous single-points-of-failure)
- Build vs. buy skills analysis (reskill vs. hire)
- Skill portfolio health dashboard (enterprise-wide)

---

#### 0.5 Organizational Transformation Simulation

**Question:** "What should the org structure look like in 3 years?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | All of the above, cross-functional, taxonomy, role adjacency |
| Data Readiness | ✅ Supported, but requires function-wide Etter assessment |
| Value Impact | ⭐⭐⭐⭐⭐ — CEO/Board level strategic decisions |
| Differentiation | ⭐⭐⭐⭐ — Orgvue does org design, but without AI impact intelligence |
| Buyer | CEO, CHRO, Board, Transformation Office |

**Capabilities within this domain:**
- AI-first org design (redesign function assuming max automation)
- Role vacuum detection (new roles from orphaned tasks)
- Spans & layers optimization (how AI changes management structure)
- Function merger simulation (combine Operations + IT)
- Future org chart generation (visual future-state structure)

---

### P1: HIGH VALUE — Directly Drives Enterprise Buying Decisions

These domains extend the core into areas that enterprise buyers explicitly ask for.

#### 1.1 Technology Adoption Impact Simulation ⭐ NEW

**Question:** "What happens if we adopt [specific technology/platform] across [scope]?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Etter's tool mapping per task, task classifications, current tech stack |
| Data Readiness | ✅ Etter already maps AI tools to tasks. Extend with enterprise tech input |
| Value Impact | ⭐⭐⭐⭐⭐ — CTOs and CIOs make $10M+ technology decisions on this |
| Differentiation | ⭐⭐⭐⭐⭐ — Nobody else connects tech adoption → task impact → workforce effect |
| Buyer | CTO, CIO, VP Digital Transformation |

**Why this is P1:** Every technology purchase has workforce consequences. A CIO buying ServiceNow or UiPath or Copilot needs to know: how many tasks does this automate? Which roles are affected? What skills become necessary? What's the true total cost (license + workforce change)? Currently, nobody answers this — Etter can.

**Scenario Examples:**

```
"What if we deploy Microsoft Copilot across Finance?"
→ Tasks affected: 127 of 340 (37%) gain AI augmentation
→ Roles impacted: 12 of 18 roles in Finance
→ Time saved: 2,400 hours/month across function
→ New skills needed: Prompt engineering, AI output validation
→ Sunset skills accelerated: Manual report formatting, data compilation
→ True cost: $180K/yr license + $200K reskilling = $380K
→ True savings: $1.2M/yr labor efficiency
→ Net: +$820K/yr (216% ROI)

"What if we implement UiPath RPA for Claims Processing?"
→ Tasks fully automatable: 23 of 45
→ But: 8 of those 23 are already marked Human+AI (partial overlap)
→ Net NEW automation: 15 tasks → 1,800 hours/month freed
→ Roles affected: Claims Processor, Claims Coordinator
→ Headcount impact: -12 FTEs over 18 months
→ Risk: 4 tasks have data quality issues → RPA will fail without cleanup
→ Prerequisite: Data quality program ($150K, 3 months)

"What if we adopt Workday AI across HR?"
→ Re-classifies 40% of current "Human" tasks to "Human+AI"
→ AI impact scores shift: HR Coordinator 45→72, HR Generalist 38→58
→ Effect: accelerates the automation timeline by 12-18 months
→ Skills shift: HRIS administration → AI-enabled HR operations
→ Budget implication: Workday AI license offsets by labor savings in Month 14
```

**How Etter supports this:**
- Etter already classifies tasks and maps tools → extend to map SPECIFIC technologies
- Task classifications can be re-run with "assume this tool exists" parameter
- Financial simulator already projects savings → add technology license costs
- Skills architecture already tracks sunrise/sunset → technology adoption shifts these

---

#### 1.2 Cost Optimization Simulation ⭐ NEW

**Question:** "How do we reduce operating costs by $X without destroying capability?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Headcount, salary/cost, automation scores, role adjacency |
| Data Readiness | ✅ Core Etter data + salary data from enterprise |
| Value Impact | ⭐⭐⭐⭐⭐ — CFO's primary question in every downturn |
| Differentiation | ⭐⭐⭐⭐ — Orgvue does cost analysis; Etter adds task-level intelligence |
| Buyer | CFO, COO, CEO |

**Scenario Examples:**

```
"Reduce HR operating cost by 20% over 24 months"
→ Twin calculates optimal path: 
   - Phase 1 (Mo 1-6): Automate high-score tasks → saves 8% 
   - Phase 2 (Mo 7-12): Merge 2 overlapping roles → saves 5%
   - Phase 3 (Mo 13-18): Offshore 3 roles to India → saves 7%
   - Phase 4 (Mo 19-24): Natural attrition absorbs remaining gap
→ Vs. naive approach: lay off 20% across the board
→ Twin shows: targeted approach saves same cost with 60% less capability loss

"What's the minimum we can spend on this function?"
→ Twin calculates: automate everything possible, reduce to human-only tasks
→ Floor cost: $X (irreducible human work × salary)
→ Current cost: $Y 
→ Maximum possible savings: $Y - $X = $Z
→ But: reaching floor requires $A investment over B months
→ Realistic target: 60-70% of maximum savings
```

---

#### 1.3 Location Strategy Simulation ⭐ NEW

**Question:** "Where should these roles be located for optimal cost/talent/risk?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Etter's Location Insights model, headcount × location, compensation benchmarks |
| Data Readiness | ✅ Etter has Location Insights. Enterprise provides current distribution |
| Value Impact | ⭐⭐⭐⭐ — Major cost lever, especially for global enterprises |
| Differentiation | ⭐⭐⭐ — Location planning exists, but connecting to AI impact is new |
| Buyer | CFO, COO, Global HR Head |

**Scenario Examples:**

```
"What if we move Claims Processing to India?"
→ Twin calculates:
   - Cost arbitrage: 60% salary reduction for relocated roles
   - BUT: 35% of tasks are already automatable → don't offshore, automate
   - Optimal: automate 35%, offshore remaining manual 40%, keep 25% onshore
   - Net savings: $4.2M/yr (vs. $3.1M from pure offshoring)
   - Risk: timezone-dependent tasks flagged (12% of workload needs overlap hours)

"Where should we build our AI Center of Excellence?"
→ Twin maps: skill availability × cost × existing headcount × timezone
→ Recommendations ranked by composite score
→ Considers: which locations already have adjacent skills
```

---

#### 1.4 Risk & Readiness Assessment Simulation

**Question:** "Are we ready to transform? What could go wrong?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Etter's Risk Framework (data maturity, team capability, tech stack, culture) |
| Data Readiness | ✅ Etter's Risk Framework Simulator (in development) |
| Value Impact | ⭐⭐⭐⭐ — De-risks $M transformation investments |
| Differentiation | ⭐⭐⭐⭐⭐ — Nobody else has multi-dimensional risk scoring FOR AI transformation |
| Buyer | CTO, CHRO, Transformation PMO |

**Scenario Examples:**

```
"What's our readiness to automate Finance?"
→ Risk Framework output:
   Data Quality: 72/100 (READY)
   Data Integration: 45/100 (NOT READY — SAP and Oracle not connected)
   Team Capability: 68/100 (PARTIAL — need AI literacy training)
   Process Documentation: 82/100 (READY)
   Tech Stack: 55/100 (PARTIAL — legacy systems need middleware)
   Culture: 61/100 (PARTIAL — mixed leadership buy-in)
→ Overall: PARTIAL READINESS (61/100)
→ Blocker: Data Integration must be resolved first ($250K, 4 months)
→ Recommendation: fix data integration, run AI literacy program, then transform

"What's the risk of automating too fast?"
→ Twin simulates aggressive timeline vs. moderate timeline:
   Aggressive (12 months): 40% risk of rollback, $800K potential waste
   Moderate (24 months): 12% risk of rollback, $200K potential waste
→ Expected value: moderate timeline delivers 85% of savings at 30% of risk
```

---

### P2: COMPLETE PRODUCT — Expected by Sophisticated Buyers

These are capabilities that mature buyers will expect. Without them, the twin feels incomplete.

#### 2.1 Vendor/Outsourcing Simulation ⭐ NEW

**Question:** "Should we build this capability internally, outsource it, or use AI?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Task decomposition, cost data, vendor/tool intelligence |
| Data Readiness | ⚠️ Needs extension — vendor cost benchmarks from Draup market data |
| Value Impact | ⭐⭐⭐⭐ — Procurement and sourcing teams need this |
| Differentiation | ⭐⭐⭐ — Some consulting firms do this, but not as a product |
| Buyer | CPO, VP Shared Services, VP Operations |

**The Make-Buy-Automate Decision:**

```
For each process/role, the twin calculates three paths:

Path A: KEEP IN-HOUSE + AUTOMATE
  Cost: current_cost × (1 - automation_savings) + implementation_cost
  Timeline: 12-18 months
  Risk: technology risk, change management
  Control: HIGH
  
Path B: OUTSOURCE (BPO/offshore)
  Cost: vendor_cost + management_overhead
  Timeline: 6-12 months  
  Risk: vendor dependency, quality control, IP exposure
  Control: MEDIUM
  
Path C: HYBRID (automate what you can, outsource the rest)
  Cost: optimal blend
  Timeline: 12-24 months
  Risk: complexity of managing both
  Control: MEDIUM-HIGH

Twin recommendation: ranked by total cost of ownership over 3 years
```

---

#### 2.2 Compliance & Regulatory Impact Simulation ⭐ NEW

**Question:** "If we automate these roles, do we violate any regulatory requirements?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Task classification, industry regulatory flags, human-oversight requirements |
| Data Readiness | ⚠️ Needs extension — regulatory tagging per task/industry |
| Value Impact | ⭐⭐⭐⭐ — Existential for healthcare, financial services, insurance |
| Differentiation | ⭐⭐⭐⭐ — Nobody else connects automation planning to compliance |
| Buyer | Chief Compliance Officer, General Counsel, CHRO |

**Scenario Examples:**

```
"Which automated tasks require human oversight by regulation?"
→ Twin flags:
   - Claims adjudication > $50K: requires licensed adjuster sign-off
   - Patient data handling: HIPAA requires human accountability chain
   - Credit decisions: Fair lending requires explainability (human review)
→ These tasks can be AI-AUGMENTED but NOT fully automated
→ Twin adjusts automation scores and financial projections accordingly

"What happens if EU AI Act classifies our HR tools as high-risk?"
→ Twin re-classifies: 23 tasks in recruitment flagged "high-risk AI"
→ Requires: human oversight, audit trails, bias testing for each
→ Cost implication: +$350K/yr for compliance infrastructure
→ Headcount implication: need 2-3 "AI Governance Specialists" (new role)
```

---

#### 2.3 Spans & Layers Optimization ⭐ NEW

**Question:** "How should our management structure change as AI transforms work?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Role hierarchy (levels/bands), headcount per level, automation scores |
| Data Readiness | ✅ Taxonomy + headcount data. Enterprise provides band/level info |
| Value Impact | ⭐⭐⭐⭐ — Classic org design question, now with AI twist |
| Differentiation | ⭐⭐⭐ — Orgvue's forte, but without AI impact lens |
| Buyer | CHRO, VP Org Development, Consulting partners |

**What the Twin Calculates:**

```
Current state:
  Function: HR (200 people)
  Layers: 6 (IC → Senior IC → Manager → Sr Manager → Director → VP)
  Avg span of control: 1:7
  Manager headcount: 35 (17.5% of function)
  
After AI transformation (twin projection):
  Headcount: 130 people (70 positions automated/redeployed)
  BUT: most reduction is in IC/Senior IC (hands-on task roles)
  Manager headcount: still 30 (only 5 managers freed)
  → Span of control drops to 1:3.3 — overmanaged!
  
  Recommendation:
  - Flatten from 6 to 4 layers
  - Increase span to 1:10 (AI tools reduce management overhead)
  - Manager headcount: 13 (from 35) — 22 managers freed for redeployment
  - Net savings: $2.8M/yr additional from management layer reduction
  - Risk: requires significant change management for affected managers
```

---

#### 2.4 Scenario Comparison & Trade-off Analysis ⭐ NEW

**Question:** "Show me 3 different transformation paths side-by-side"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Multiple scenario runs from other domains |
| Data Readiness | ✅ This is an OUTPUT layer on top of existing simulation |
| Value Impact | ⭐⭐⭐⭐⭐ — Decision-makers NEED comparative views |
| Differentiation | ⭐⭐⭐⭐ — Turns simulations into decision-quality intelligence |
| Buyer | ALL buyers — this is how scenarios become decisions |

**Example Output:**

```
SCENARIO COMPARISON: Finance Function Transformation

                     | Conservative  | Moderate      | Aggressive
─────────────────────|───────────────|───────────────|──────────────
Timeline             | 36 months     | 24 months     | 12 months
Automation factor    | 0.5           | 0.75          | 1.0
─────────────────────|───────────────|───────────────|──────────────
Headcount (current)  | 150           | 150           | 150
Headcount (end)      | 128           | 108           | 85
Reduction            | -22 (-15%)    | -42 (-28%)    | -65 (-43%)
─────────────────────|───────────────|───────────────|──────────────
Cost savings (3yr)   | $4.2M         | $8.8M         | $14.5M
Investment required  | $0.8M         | $1.6M         | $3.2M
Net value (3yr)      | $3.4M         | $7.2M         | $11.3M
─────────────────────|───────────────|───────────────|──────────────
Reskilling needed    | 18 people     | 35 people     | 60 people
New roles created    | 1             | 3             | 7
─────────────────────|───────────────|───────────────|──────────────
Risk score           | LOW (28)      | MODERATE (52) | HIGH (78)
Confidence interval  | ±12%          | ±18%          | ±32%
─────────────────────|───────────────|───────────────|──────────────
RECOMMENDATION: Moderate path — best risk-adjusted return
```

---

#### 2.5 Competitive Benchmarking Simulation ⭐ NEW

**Question:** "How does our transformation compare to industry peers?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Anonymized cross-client data, industry benchmarks from Draup |
| Data Readiness | ⚠️ Grows with client base — needs 10+ clients per industry |
| Value Impact | ⭐⭐⭐⭐ — "Are we ahead or behind?" is a Board-level question |
| Differentiation | ⭐⭐⭐⭐⭐ — Network effect moat — gets stronger with every client |
| Buyer | CEO, Board, Strategy team |

**What the Twin Shows:**

```
Your HR Function vs. Insurance Industry Benchmark:
  Automation score: 52 (you) vs. 48 (industry avg) → AHEAD
  Skills readiness: 61 (you) vs. 67 (industry avg) → BEHIND
  AI investment: $1.2M (you) vs. $2.1M (industry avg) → UNDERINVESTED
  Speed of transformation: 18 months (you) vs. 14 months (leaders) → SLOWER
  
Insight: You're ahead on identifying automation opportunities but behind 
on investing to capture them. Risk of losing competitive advantage.
```

---

### P3: MOAT BUILDERS — Long-Term Defensibility

These don't drive immediate purchase decisions but build insurmountable competitive advantages over time.

#### 3.1 Transformation Sequencing Optimizer ⭐ NEW

**Question:** "Across the entire enterprise, what's the optimal order of transformation?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Multi-function Etter assessments, workflow dependencies across functions |
| Data Readiness | ⚠️ Requires enterprise-wide assessment (few clients have this today) |
| Value Impact | ⭐⭐⭐⭐⭐ — Multi-million dollar sequencing decisions |
| Differentiation | ⭐⭐⭐⭐⭐ — Only possible with task-level data ACROSS functions |
| Buyer | CEO, Chief Transformation Officer |

**What the Twin Calculates:**

```
Enterprise: 8 functions, 2,000 roles

Optimal sequence (considering dependencies + compounding benefits):
1. Finance (Quarter 1-4) — foundational data infrastructure benefits others
2. HR Operations (Quarter 3-6) — depends on Finance automation for reporting
3. Procurement (Quarter 5-8) — leverages Finance + HR platform investments
4. Customer Service (Quarter 7-10) — benefits from all upstream automation
5. Sales Operations (Quarter 8-12) — parallel with CS, shared CRM automation
6. Legal (Quarter 10-14) — high risk, needs mature AI governance from earlier phases
7. R&D Support (Quarter 12-16) — complex, benefits from lessons learned
8. Executive Office (Quarter 14-18) — last, smallest, highest judgment content

WHY this order matters:
- Doing #4 before #1 wastes $2M on redundant data infrastructure
- Doing #6 before governance matures from phases 1-4 risks compliance failure
- Each phase builds skills and confidence for the next
- Total savings from optimal sequencing: $8M more than random order
```

---

#### 3.2 Decision Provenance Engine ⭐ NEW

**Question:** "What did similar organizations do, and what happened?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Historical scenario data from all clients (anonymized) |
| Data Readiness | ❌ Requires time — builds as more clients use the twin |
| Value Impact | ⭐⭐⭐⭐ — "Evidence-based transformation" is incredibly compelling |
| Differentiation | ⭐⭐⭐⭐⭐ — Impossible to replicate without the client base |
| Buyer | CHRO, CEO, Consulting partners |

**Future Capability:**

```
"Organizations that automated Claims Processing with these parameters:"
- Used moderate automation factor (0.7)
- Invested in reskilling before automation
- Phased over 18-24 months

"Achieved on average:"
- 23% cost reduction (vs. 18% for aggressive, 15% for conservative)
- 82% employee retention through transition (vs. 65% for aggressive)
- 7-month break-even (vs. 14-month for conservative)

"Based on: 14 transformations across 8 insurance companies"
```

---

#### 3.3 Cross-Client Learning & Industry Intelligence

**Question:** "What are the emerging patterns across our industry?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Aggregated anonymized data from twin usage across clients |
| Data Readiness | ❌ Network effect — value grows with client count |
| Value Impact | ⭐⭐⭐⭐ — Strategic intelligence that gets better over time |
| Differentiation | ⭐⭐⭐⭐⭐ — Pure network effect moat |
| Buyer | Strategy teams, Board advisors |

---

### P4: HORIZON — Future Vision

These require new data partnerships, emerging technology, or market maturation.

#### 4.1 M&A Workforce Integration Simulation

**Question:** "We're acquiring Company X. How do we combine workforces?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Both organizations' role data in Etter (acquirer + target) |
| Data Readiness | ❌ Requires both companies onboarded, or fast-assessment capability |
| Value Impact | ⭐⭐⭐⭐⭐ — M&A integration destroys billions when done wrong |
| Differentiation | ⭐⭐⭐⭐ — Orgvue is used here, but without AI transformation layer |
| Buyer | M&A integration team, CHRO, CFO |

---

#### 4.2 External Labor Market Simulation

**Question:** "If we need 50 AI engineers, where can we find them and at what cost?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Draup's external talent intelligence, job market data |
| Data Readiness | ⚠️ Draup has talent data — needs integration with twin |
| Value Impact | ⭐⭐⭐⭐ — Connects internal planning to external reality |
| Differentiation | ⭐⭐⭐⭐ — Unique because it links workforce planning to talent supply |
| Buyer | Talent Acquisition, HR Strategy |

---

#### 4.3 Culture & Change Readiness Modeling

**Question:** "Will our people actually adopt these changes?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | Aggregate engagement data, change readiness surveys (from enterprise) |
| Data Readiness | ❌ Requires new data collection mechanism (Etter survey expansion) |
| Value Impact | ⭐⭐⭐⭐ — Transformation fails 70% of the time due to culture |
| Differentiation | ⭐⭐⭐ — Soft, hard to quantify, but immensely valuable |
| Buyer | CHRO, Change Management Office |

---

#### 4.4 Sustainability & ESG Workforce Impact

**Question:** "How does our AI transformation affect our ESG commitments?"

| Dimension | Detail |
|:----------|:-------|
| Data Required | DEI metrics at aggregate level, ESG framework mapping |
| Data Readiness | ⚠️ Enterprise provides aggregate DEI data, Etter adds AI impact layer |
| Value Impact | ⭐⭐⭐ — Growing importance, especially for European markets |
| Differentiation | ⭐⭐⭐ — Unique angle, but niche |
| Buyer | Chief Sustainability Officer, Board ESG committee |

---

## SECTION C: PRIORITY MAP — The Complete View

### Capability Priority Matrix

```
                          DATA READINESS
                   HIGH ←──────────────────→ LOW
                    │                         │
          ┌─────────┼─────────────────────────┼─────────┐
  HIGH    │  ★ P0   │                         │  P4     │
          │  Role Redesign                    │  M&A    │
  V       │  Process Optimization             │  Integ. │
  A       │  Skills Strategy                  │         │
  L       │  ★ P1                             │  P3     │
  U       │  Tech Adoption Impact ←KEY        │  Decision│
  E       │  Cost Optimization                │  Proven.│
          │  Risk & Readiness                 │         │
  I       │  Workforce Planning               │  P4     │
  M       │  ★ P2                             │  Culture │
  P       │  Location Strategy                │  Modeling│
  A       │  Scenario Comparison              │         │
  C       │  Spans & Layers                   │  P4     │
  T       │  Compliance/Regulatory            │  ESG    │
          │  Vendor/Outsourcing               │  Impact │
          │                                   │         │
  LOW     │  P3                               │         │
          │  Cross-Client Learning            │         │
          │  Industry Intelligence            │         │
          └───────────────────────────────────┘
```

### Recommended Build Sequence

| Phase | Timeline | Capabilities | Why This Order |
|:------|:---------|:-------------|:---------------|
| **Phase 1** | Weeks 1-8 | P0: Core 5 (Role, Workforce, Process, Skills, Org) | The product doesn't exist without these |
| **Phase 2** | Weeks 6-14 | P1: Technology Adoption + Cost Optimization | Biggest "aha" for CTO/CFO buyers. Tech adoption is the differentiator |
| **Phase 3** | Weeks 10-18 | P1: Location Strategy + Risk Assessment | Completes the strategic planning suite |
| **Phase 4** | Weeks 14-22 | P2: Scenario Comparison + Spans & Layers | Makes all previous capabilities 2x more useful |
| **Phase 5** | Weeks 18-28 | P2: Compliance + Vendor/Outsourcing + Benchmarking | Fills competitive gaps, attracts regulated industries |
| **Phase 6** | Ongoing | P3: Sequencing + Provenance + Cross-Client | Builds moat. Value compounds with client count |
| **Phase 7** | 12+ months | P4: M&A + Labor Market + Culture + ESG | Horizon capabilities. Market must mature first |

---

## SECTION D: TECHNOLOGY ADOPTION — Deep Dive

This deserves special attention because it's Etter's most differentiated P1 capability.

### The "Technology Impact Scenario" Model

```python
@dataclass
class TechnologyScenario:
    """
    Simulates: "What happens if we adopt technology X across scope Y?"
    
    This is Etter's unique capability — no competitor connects
    technology adoption → task impact → workforce effect → financial outcome.
    """
    
    # What technology
    technology_name: str          # "Microsoft Copilot", "UiPath", "ServiceNow AI"
    technology_category: str      # "GenAI Assistant", "RPA", "ITSM AI"
    license_cost_annual: float    # Per-user or flat
    implementation_cost: float    # One-time setup
    
    # Where to apply
    scope: TwinCellSet            # Which roles/functions
    
    # How it affects tasks (the key intelligence)
    task_reclassifications: Dict[str, str]  
    # Maps: current_classification → new_classification
    # Example: {"Human": "Human+AI", "Human+AI": "AI"}
    # Applied only to tasks matching technology's capability profile
    
    # Technology capability profile
    capabilities: List[str]       
    # What this tech can do: "document generation", "data entry", 
    # "meeting scheduling", "code review", etc.
    # Matched against task descriptions to determine affected tasks
```

### How Technology Impact Flows Through the Twin

```
Technology Defined
    │
    ▼
Match capabilities to tasks in scope
(semantic matching: tech capabilities ↔ task descriptions)
    │
    ▼
Reclassify affected tasks
(Human → Human+AI, Human+AI → AI, based on tech capability)
    │
    ▼
Recalculate automation scores per role
(scores change because task classifications changed)
    │
    ▼
Recalculate financial projections
(more automation → more savings, minus license + implementation costs)
    │
    ▼
Recalculate skill shifts
(new skills needed: tech-specific + AI collaboration skills)
    │
    ▼
Recalculate workflow impact
(bottleneck shifts, throughput changes)
    │
    ▼
Generate Technology Adoption Report:
├── Affected roles and tasks (specifics)
├── Score changes (before → after)
├── Financial case (costs vs. savings, break-even)
├── Skill requirements (new skills needed)
├── Risk assessment (what could go wrong)
├── Implementation timeline recommendation
└── Comparison: adopt vs. don't adopt vs. alternatives
```

### Pre-Built Technology Profiles

Over time, Etter builds a library of technology impact profiles:

| Technology | Category | Task Types Affected | Typical Reclassification |
|:-----------|:---------|:-------------------|:-------------------------|
| Microsoft Copilot | GenAI Assistant | Document creation, email drafting, meeting summarization, data analysis | Human → Human+AI |
| UiPath | RPA | Data entry, form processing, system-to-system transfer, report generation | Human → AI (structured tasks only) |
| ServiceNow AI | ITSM AI | Ticket routing, incident categorization, knowledge search, SLA monitoring | Human → AI (tier 1), Human → Human+AI (tier 2) |
| Salesforce Einstein | CRM AI | Lead scoring, forecast updating, activity logging, email personalization | Human → Human+AI |
| SAP Joule | ERP AI | Invoice processing, purchase order matching, financial close tasks | Human → AI (transactional), Human → Human+AI (analytical) |
| GitHub Copilot | Code AI | Code writing, code review, documentation, testing | Human → Human+AI |
| Custom/Generic GenAI | LLM Wrapper | Content creation, research, summarization, translation | Human → Human+AI |

Each profile is refined as more clients simulate with that technology.

---

## SECTION E: KEY INSIGHT — The Data Supportability Rule

### The Governing Principle

> **A simulation domain is valid if and only if the answer can be derived from role-level aggregate data (Etter's + reasonable enterprise enrichment), without requiring individual-level PII.**

### Applying the Rule

| Capability | Can It Be Role-Level? | Verdict |
|:-----------|:---------------------|:--------|
| Role Redesign | ✅ Yes — tasks, skills, scores are all role-level | IN |
| Individual Career Pathing | ❌ No — requires individual skill assessments | OUT (Visier territory) |
| Headcount Planning | ✅ Yes — aggregate counts per role | IN |
| Individual Attrition Prediction | ❌ No — requires individual engagement, tenure, performance | OUT |
| Skill Strategy | ✅ Yes — skills attached to roles, not individuals | IN |
| Learning Recommendations | ⚠️ Partial — role-level course recommendations (yes), individual learning path (no) | IN at role level |
| Technology Impact | ✅ Yes — tech maps to tasks, tasks map to roles | IN |
| Team Dynamics Modeling | ❌ No — requires individual interaction data | OUT |
| Cost Optimization | ✅ Yes — aggregate cost per role × headcount | IN |
| Individual Compensation Optimization | ❌ No — requires individual salary data | OUT |
| Manager Effectiveness | ❌ No — requires individual 360° data | OUT |
| Process Efficiency | ✅ Yes — workflow steps, task times, role assignments | IN |
| Spans & Layers | ✅ Yes — aggregate headcount by level | IN |
| Location Strategy | ✅ Yes — headcount by role × location, market benchmarks | IN |
| Engagement Impact | ❌ No — requires individual survey data | OUT |

### The Bridge Pattern: When Role-Level Isn't Enough

For some P4 capabilities (like change readiness or culture), Etter doesn't have the data — but it can accept aggregate inputs from the enterprise:

```
Enterprise provides (aggregate, no PII):
  "HR function average engagement score: 72/100"
  "Finance function change readiness: 58/100"
  "Engineering AI adoption willingness: 81/100"

Etter uses as scenario parameter:
  If change_readiness < 65:
      reskilling_success_rate = 0.55 (instead of default 0.70)
      implementation_timeline × 1.3 (slower adoption)
      risk_score += 15 (cultural resistance premium)
```

This way, Etter doesn't store PII, but can incorporate human-provided context to improve simulation accuracy.

---

## SUMMARY: The 16 Simulation Domains by Priority

| Priority | # | Domain | Data Ready? | Primary Buyer |
|:---------|:--|:-------|:------------|:--------------|
| **P0** | 0.1 | Role Redesign | ✅ | VP/Director |
| **P0** | 0.2 | Workforce Planning | ✅ | CHRO/CFO |
| **P0** | 0.3 | Process Optimization | ✅ | COO |
| **P0** | 0.4 | Skills Strategy | ✅ | CLO/L&D |
| **P0** | 0.5 | Org Transformation | ✅ | CEO/CHRO |
| **P1** | 1.1 | **Technology Adoption Impact** | ✅ | **CTO/CIO** |
| **P1** | 1.2 | Cost Optimization | ✅ | CFO/COO |
| **P1** | 1.3 | Location Strategy | ✅ | CFO/Global HR |
| **P1** | 1.4 | Risk & Readiness | ✅ | CTO/CHRO |
| **P2** | 2.1 | Vendor/Outsourcing | ⚠️ | CPO/VP Ops |
| **P2** | 2.2 | Compliance & Regulatory | ⚠️ | CCO/Legal |
| **P2** | 2.3 | Spans & Layers | ✅ | CHRO/VP OD |
| **P2** | 2.4 | Scenario Comparison | ✅ | All |
| **P2** | 2.5 | Competitive Benchmarking | ⚠️ | CEO/Board |
| **P3** | 3.1 | Transformation Sequencing | ⚠️ | CTO/CEO |
| **P3** | 3.2 | Decision Provenance | ❌ | All (over time) |
| **P3** | 3.3 | Cross-Client Intelligence | ❌ | Strategy |
| **P4** | 4.1 | M&A Integration | ❌ | M&A team |
| **P4** | 4.2 | External Labor Market | ⚠️ | Talent Acq |
| **P4** | 4.3 | Culture & Change Readiness | ❌ | CHRO |
| **P4** | 4.4 | ESG/Sustainability Impact | ⚠️ | CSO/Board |

**The product story:** Start with P0 (this IS Etter's twin), add P1 for enterprise buying power (especially Technology Adoption — that's the killer feature nobody else has), build P2 for completeness, and let P3-P4 emerge from accumulated data and market demand.
