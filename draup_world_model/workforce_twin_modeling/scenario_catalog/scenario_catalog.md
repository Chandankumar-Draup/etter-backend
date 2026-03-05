# Workforce Twin: Complete Simulation Scenario Catalog
## Every Business Question the Twin Must Answer
*Version 1.0 — March 2026*

---

# PART 0: THE FUNDAMENTAL TAXONOMY

## First Principles: What IS a Simulation?

A simulation is a **stimulus** applied to a **system** that produces **observable change** over **time**.

Strip it further: every simulation answers one of two meta-questions:

**FORWARD:** "If I do X, what happens?" (cause → effect)
**INVERSE:** "If I want Y, what must I do?" (effect → cause)

Everything else is a variation. But these two directions produce radically different engineering — forward simulations propagate change, inverse simulations search parameter space.

## The Stimulus × Question Matrix

**Stimulus Types (What you change):**

| Code | Stimulus | Example |
|------|----------|---------|
| S1 | Technology injection | "Deploy Copilot to Claims" |
| S2 | Headcount target | "Reduce Claims HC by 20%" |
| S3 | Budget constraint | "We have $2M to invest" |
| S4 | Automation target | "Reach 40% automation in Finance" |
| S5 | Output/productivity target | "Process 30% more claims with same or fewer people" |
| S6 | Role-specific change | "Redesign Claims Adjuster role" |
| S7 | Function transformation | "Transform entire Claims function" |
| S8 | Skill intervention | "Launch AI reskilling for 500 people" |
| S9 | Org restructuring | "Merge Claims Processing and Claims Review" |
| S10 | Time constraint | "Achieve $5M savings by month 18" |
| S11 | Risk constraint | "Don't exceed medium risk level" |
| S12 | External shock | "15% attrition spike in Technology" |
| S13 | Competitive pressure | "Competitor automated claims 60%" |
| S14 | Regulatory change | "New regulation makes 30 more tasks compliance-mandated" |
| S15 | Multi-stimulus | Combinations of above |

**Question Directions (What you want to know):**

| Code | Direction | Example |
|------|-----------|---------|
| Q1 | What happens? (Forward projection) | "Show me the 36-month trajectory" |
| Q2 | What's needed? (Inverse/requirements) | "What tools, budget, skills do I need?" |
| Q3 | What's optimal? (Constrained optimization) | "Best outcome given these constraints" |
| Q4 | Which is better? (Comparison) | "Compare path A vs. path B" |
| Q5 | What matters most? (Sensitivity) | "Which parameter swings the outcome most?" |
| Q6 | What breaks? (Stress test / breakpoint) | "At what point does the plan fail?" |
| Q7 | In what order? (Sequencing) | "Should we do Claims before Finance?" |
| Q8 | Who's affected? (Impact mapping) | "Which roles, skills, people are affected?" |
| Q9 | How long? (Timeline) | "When do we break even?" |
| Q10 | What's the risk? (Risk assessment) | "What are the top 5 risks?" |

The full matrix is 15 × 10 = 150 cells. Not all combinations are meaningful. Below is the curated set of ~60 scenarios that ARE meaningful, organized into 12 scenario families.

---

# PART I: THE TWELVE SCENARIO FAMILIES

---

## Family 1: TECHNOLOGY INJECTION (Forward)
*"We're deploying a tool. What happens?"*

### SC-1.1: Single Tool → Single Function
**Stimulus:** Deploy Copilot to Claims Processing
**Question:** Full 36-month forward projection
**Cascade:** Scope → Reclassify tasks addressable by Copilot → Freed capacity → Skill shift → HC impact → Financial → Risk
**Parameters:**
```python
{
    "stimulus_type": "technology_injection",
    "tool": "Microsoft Copilot",
    "target_scope": "Claims Processing",    # sub-function
    "deployment_month": 1,
    "adoption_rate": "s_curve",
    "alpha": 0.6,
}
```
**Key outputs:** Adoption curve, freed FTE-hours, HC reduction trajectory, net savings curve, skill gap timeline, risk heatmap
**Loops activated:** B1 (capacity absorption), B2 (skill valley), B3 (resistance), R1 (trust-adoption), R2 (proficiency)

### SC-1.2: Single Tool → Entire Organization
**Stimulus:** Deploy Copilot organization-wide (all 4 functions)
**Question:** Same as SC-1.1 but at org level — aggregated AND per-function breakdowns
**Key difference:** Functions with higher readiness (Technology: 70) adopt faster than low readiness (Claims: 45). Same tool, same month, dramatically different trajectories.
```python
{
    "stimulus_type": "technology_injection",
    "tool": "Microsoft Copilot",
    "target_scope": "ALL",
    "deployment_month": 1,
}
```
**Critical insight this proves:** Uniform deployment ≠ uniform adoption. Human system IS the variable.

### SC-1.3: Multiple Tools → Single Function (Stacking)
**Stimulus:** Deploy Copilot + Custom Claims AI + UiPath RPA to Claims
**Question:** What's the combined impact? Is it additive or is there overlap/interference?
```python
{
    "stimulus_type": "technology_injection",
    "tools": ["Microsoft Copilot", "Custom Claims AI", "UiPath RPA"],
    "target_scope": "Claims",
    "deployment_months": [1, 1, 1],   # simultaneous
}
```
**Key dynamic:** Tools address overlapping task categories. The simulation must handle: if Task A is already automated by Copilot, UiPath doesn't double-count. But change burden triples because three tools simultaneously → B3 (resistance) amplified.

### SC-1.4: Staggered Multi-Tool Deployment
**Stimulus:** Same 3 tools to Claims, but deployed 3 months apart
**Question:** Does staggering reduce risk while maintaining savings?
```python
{
    "stimulus_type": "technology_injection",
    "tools": ["UiPath RPA", "Custom Claims AI", "Microsoft Copilot"],
    "target_scope": "Claims",
    "deployment_months": [1, 4, 7],   # staggered
}
```
**Critical comparison:** SC-1.3 vs SC-1.4. Same tools, same function, different timing. SC-1.4 should show: lower peak risk, lower change burden, slower initial savings, but potentially HIGHER total savings (less resistance dampening, trust builds between deployments).

### SC-1.5: Tool Removal / Shelfware Analysis
**Stimulus:** Current tools are deployed but not adopted (Copilot at 15% adoption)
**Question:** What's the cost of shelfware? What happens if we just fix adoption of what we already have?
```python
{
    "stimulus_type": "adoption_gap_only",
    "tools": "ALL_DEPLOYED",
    "target_scope": "ALL",
    "target": "close_adoption_gap",    # L3 → L2 only
}
```
**Key output:** The "free money" scenario — no new licensing cost, just training and change management. This is always the first recommendation.

---

## Family 2: HEADCOUNT TARGET (Inverse)
*"We need to reduce by X%. What does it take?"*

### SC-2.1: Uniform Headcount Reduction Target
**Stimulus:** "Reduce total headcount by 15% in 24 months"
**Question:** What technology, investment, and change management is needed?
```python
{
    "stimulus_type": "headcount_target",
    "target_reduction_pct": 15,
    "target_months": 24,
    "scope": "ALL",
    "constraints": {
        "policy": "managed_reduction",      # not slash-and-burn
        "max_risk_level": "medium",
        "preserve_compliance_roles": True,
    }
}
```
**Inverse computation:** Work BACKWARD from 15% HC reduction → how many FTE-hours must be freed → which tasks must be automated → which tools address those tasks → what's the deployment cost + timeline → does it fit in 24 months given human system constraints?
**Key output:** Required technology investments, reskilling programs, timeline feasibility, risk assessment, and FEASIBILITY VERDICT (can this target actually be reached given constraints?)

### SC-2.2: Function-Specific Headcount Target
**Stimulus:** "Reduce Claims by 25%, keep Technology flat, reduce Finance by 10%, reduce People by 15%"
**Question:** Differentiated path per function
```python
{
    "stimulus_type": "headcount_target",
    "targets_by_function": {
        "Claims": {"reduction_pct": 25, "months": 24},
        "Technology": {"reduction_pct": 0, "months": 24},
        "Finance": {"reduction_pct": 10, "months": 24},
        "People": {"reduction_pct": 15, "months": 24},
    }
}
```
**Critical insight:** Claims at 25% reduction requires readiness > 50 (currently 45). The simulation should flag: "Claims target is NOT achievable at current readiness without intervention. Required: readiness program investment of $X over Y months BEFORE technology deployment."

### SC-2.3: Role-Level Headcount Target
**Stimulus:** "Eliminate 60 Claims Data Entry Clerks (75% of the role), redistribute work"
**Question:** What's the cascade impact on adjacent roles?
```python
{
    "stimulus_type": "headcount_target",
    "targets_by_role": {
        "CL-003": {"target_headcount": 20, "current": 80},
    },
    "redistribution_policy": "absorb_into_adjacent",
}
```
**Key dynamic:** Eliminating 60 clerks means their non-automated tasks go somewhere. The simulation must: identify which tasks are non-automated, compute redistribution across Claims Intake Specialists, Claims Processors, and Claims Adjusters, then check if those roles can absorb it (B1: capacity absorption).

### SC-2.4: Management Level Reduction
**Stimulus:** "Flatten org — reduce management layers by consolidating Manager and Senior Manager into one level"
**Question:** What's the span-of-control impact? Can remaining managers handle the expanded teams?
```python
{
    "stimulus_type": "headcount_target",
    "target_type": "level_consolidation",
    "levels_to_merge": ["Manager", "Senior Manager"],
    "scope": "ALL",
}
```
**Key output:** New span-of-control ratios, workload impact on remaining managers, change burden score, risk of management overload triggering the inner vicious cycle (B1).

---

## Family 3: BUDGET-CONSTRAINED (Optimization)
*"We have $X to spend. What's the best use?"*

### SC-3.1: Fixed Budget Optimization
**Stimulus:** "$2M total transformation budget for 24 months"
**Question:** Optimal allocation across tools, functions, and phases to maximize net savings
```python
{
    "stimulus_type": "budget_constraint",
    "total_budget": 2000000,
    "time_horizon_months": 24,
    "objective": "maximize_net_savings",
    "constraints": {
        "max_risk": "medium",
        "min_readiness_maintained": 40,
    }
}
```
**Optimization logic:** Rank all possible interventions by ROI (net savings per dollar invested). Start with highest ROI (adoption gap closure — nearly free). Allocate budget until exhausted. Account for dependencies (can't expand before adopting).
**Key output:** Prioritized investment roadmap, expected savings trajectory, sensitivity of outcome to budget ±20%.

### SC-3.2: Budget Allocation Comparison
**Stimulus:** "Compare: $2M all on technology vs. $1M technology + $1M reskilling vs. $500K technology + $1.5M change management"
**Question:** Which allocation produces the best 36-month outcome?
```python
{
    "stimulus_type": "budget_allocation_comparison",
    "allocations": [
        {"name": "Tech-heavy", "technology": 2000000, "reskilling": 0, "change_mgmt": 0},
        {"name": "Balanced", "technology": 1000000, "reskilling": 500000, "change_mgmt": 500000},
        {"name": "People-heavy", "technology": 500000, "reskilling": 750000, "change_mgmt": 750000},
    ],
    "time_horizon_months": 36,
}
```
**Critical insight this proves:** The "People-heavy" allocation often wins at 36 months because it builds the human system (R2 proficiency, R1 trust) which MULTIPLIES all subsequent technology adoption. The "Tech-heavy" approach hits resistance walls earlier.

### SC-3.3: Phased Budget with Gates
**Stimulus:** "$500K now. Release next $1M only if Phase 1 achieves $X savings"
**Question:** What can Phase 1 achieve? What triggers the gate?
```python
{
    "stimulus_type": "budget_gated",
    "phases": [
        {"budget": 500000, "gate_condition": "net_savings > 300000 AND risk < medium"},
        {"budget": 1000000, "gate_condition": "net_savings > 1500000"},
        {"budget": 1500000, "gate_condition": None},  # final phase, unconditional
    ],
}
```
**Key dynamic:** Phase 1 MUST produce visible wins (R4: political capital) to unlock Phase 2. The simulation shows: if Phase 1 targets are set too aggressively, there's a risk of gate failure → entire program stalls.

---

## Family 4: AUTOMATION TARGET (Inverse)
*"We want X% automation. How do we get there?"*

### SC-4.1: Organization-Wide Automation Target
**Stimulus:** "Reach 35% overall automation (currently ~10-15% realized)"
**Question:** What's the roadmap?
```python
{
    "stimulus_type": "automation_target",
    "target_automation_pct": 35,
    "current_realized_pct": 12,     # estimated from adoption gaps
    "time_horizon_months": 36,
    "scope": "ALL",
}
```
**Inverse computation:** 35% automation → how many tasks must be reclassified → gap analysis per function → which tools needed → investment required → human system requirements → timeline → feasibility.
**Key output:** Phase-by-phase roadmap showing which functions should reach what automation level by when.

### SC-4.2: Function-Specific Automation Targets
**Stimulus:** "Claims to 40%, Technology to 25%, Finance to 35%, People to 30%"
**Question:** Differentiated roadmaps with cross-function dependencies
```python
{
    "stimulus_type": "automation_target",
    "targets_by_function": {
        "Claims": 40,
        "Technology": 25,
        "Finance": 35,
        "People": 30,
    },
    "time_horizon_months": 36,
}
```
**Critical insight:** Claims at 40% is achievable (Etter ceiling avg 26.2% automation + 20.5% augmentation = 46.7% total potential). People at 30% is HARD (ceiling is 24.3% + 20.0% = 44.3% potential, but starts from lowest readiness at 20).

### SC-4.3: Task Category Automation Target
**Stimulus:** "Automate 90% of all Directive tasks, 80% of Feedback Loop tasks, 50% of Task Iteration, leave Negligibility untouched"
**Question:** What's the resulting org shape?
```python
{
    "stimulus_type": "automation_target",
    "targets_by_category": {
        "directive": 90,
        "feedback_loop": 80,
        "task_iteration": 50,
        "learning": 30,
        "validation": 40,
        "negligibility": 0,
    },
    "time_horizon_months": 36,
}
```
**Key output:** Per-role impact map showing which roles survive, which need redesign, which are eliminated. This is the "true shape of future work."

---

## Family 5: OUTPUT/PRODUCTIVITY TARGET (Inverse)
*"We want to do more with the same or fewer people"*

### SC-5.1: Same Headcount, More Output
**Stimulus:** "Process 30% more claims annually without adding headcount"
**Question:** What automation is needed? Where does the freed capacity go?
```python
{
    "stimulus_type": "output_target",
    "function": "Claims",
    "current_output": 120000,           # claims per year
    "target_output": 156000,            # +30%
    "headcount_change": 0,              # hold flat
    "time_horizon_months": 18,
}
```
**Inverse computation:** 30% more output → need 30% more capacity → free 30% of current task hours through automation → which tasks → which tools → investment → timeline.
**Key output:** Technology roadmap, reskilling needs, and a feasibility assessment. If 30% is beyond Etter ceiling, flag it.

### SC-5.2: Reduced Headcount, Maintain Output
**Stimulus:** "Maintain current claims volume but with 20% fewer people"
**Question:** Where does automation replace human hours while maintaining quality?
```python
{
    "stimulus_type": "output_target",
    "function": "Claims",
    "current_output": 120000,
    "target_output": 120000,            # same
    "headcount_change_pct": -20,        # 20% fewer
    "time_horizon_months": 24,
}
```
**Critical dynamic:** Quality maintenance requires careful task selection — can't just automate the easiest tasks if quality depends on them. Compliance-mandated tasks create a hard floor. The simulation must check: after removing 20% HC, can remaining staff + AI handle the non-automatable work without triggering the vicious cycle (B1)?

### SC-5.3: Reduced Headcount, Increased Output
**Stimulus:** "Process 20% more claims with 15% fewer people"
**Question:** Is this even possible? What's the required automation level?
```python
{
    "stimulus_type": "output_target",
    "function": "Claims",
    "current_output": 120000,
    "target_output": 144000,            # +20%
    "headcount_change_pct": -15,
    "time_horizon_months": 24,
}
```
**This is the hardest scenario.** Requires freeing capacity for BOTH output growth and headcount reduction. The simulation should: compute total capacity needed, check against Etter ceiling, flag if impossible, or show the narrow path if feasible. This is where the Adoption Gap becomes critical — it's the only near-free capacity source.

---

## Family 6: ROLE TRANSFORMATION (Forward)
*"How should this role change?"*

### SC-6.1: Single Role Redesign
**Stimulus:** "Redesign Claims Adjuster — 40%+ tasks automatable"
**Question:** What does the future Claims Adjuster look like?
```python
{
    "stimulus_type": "role_redesign",
    "role_id": "CL-002",               # Claims Adjuster
    "threshold": 40,                     # % freed capacity that triggers redesign
}
```
**Key outputs:**
- Current task composition vs. future task composition
- Sunset skills (what they stop doing)
- Sunrise skills (what they need to learn)
- Transition timeline and reskilling path
- New job description outline
- Adjacent role impacts (who absorbs/loses tasks)

### SC-6.2: Role Elimination Impact
**Stimulus:** "Eliminate Claims Data Entry Clerk entirely"
**Question:** What happens to the work? The skills? The adjacent roles?
```python
{
    "stimulus_type": "role_elimination",
    "role_id": "CL-003",               # Claims Data Entry Clerk, 80 people
    "timeline_months": 12,
    "redistribution": "automate_first_then_redistribute",
}
```
**Cascade:**
1. Which tasks can be fully automated? (Directive: yes. Validation: partially. Negligibility: NO.)
2. Which tasks MUST go to other roles? (Non-automatable tasks redistributed)
3. Can adjacent roles absorb? (Check capacity)
4. What's the financial impact? (80 × $38K = $3.04M annual savings minus automation cost)
5. What skills are lost? (check if any critical skills are concentrated here)
6. What's the risk? (Concentration risk if tasks are critical)

### SC-6.3: Role Creation Simulation
**Stimulus:** "Create new role: AI Operations Specialist — handles monitoring, tuning, and oversight of all AI tools"
**Question:** What tasks from other roles should migrate here? How many FTEs needed?
```python
{
    "stimulus_type": "role_creation",
    "new_role_name": "AI Operations Specialist",
    "task_sources": ["validation tasks currently in Claims", "monitoring tasks in Technology"],
    "skill_requirements": ["AI output validation", "automation oversight", "prompt engineering"],
}
```
**Key output:** FTE sizing based on migrated task hours, required skills, hiring vs. reskilling analysis.

### SC-6.4: Role Vacancy Impact (What If Nobody Does This?)
**Stimulus:** "What tasks become orphaned if Claims Examiner headcount drops to zero?"
**Question:** Identify homeless tasks and role vacuums
```python
{
    "stimulus_type": "role_vacancy_analysis",
    "role_id": "CL-004",
    "scenario": "complete_attrition",
}
```
**Key concept from the model:** "Role vacuums" where orphaned tasks and homeless skills emerge that don't map to existing positions.

---

## Family 7: FUNCTION TRANSFORMATION (Forward, Comparison)
*"Transform an entire function"*

### SC-7.1: Phased Function Transformation
**Stimulus:** "Transform Claims end-to-end over 36 months"
**Question:** What's the optimal phase plan?
```python
{
    "stimulus_type": "function_transformation",
    "function": "Claims",
    "phases": [
        {"name": "Quick wins", "months": "1-6", "focus": "adoption_gap"},
        {"name": "Expansion", "months": "7-18", "focus": "deploy_new_tools"},
        {"name": "Redesign", "months": "19-30", "focus": "role_restructuring"},
        {"name": "Optimization", "months": "31-36", "focus": "fine_tuning"},
    ],
}
```
**Key output:** Phase-by-phase: tasks automated, HC trajectory, savings curve, skill gap evolution, risk heatmap, human system state over time.

### SC-7.2: Function Comparison — Transform Which One First?
**Stimulus:** "We can only start with one function. Which gives the best ROI?"
**Question:** Compare Claims-first vs. Finance-first vs. People-first
```python
{
    "stimulus_type": "function_comparison",
    "candidates": ["Claims", "Finance", "People"],
    "evaluation_criteria": ["net_savings_12mo", "risk_score", "political_capital_generated", "learning_value"],
    "time_horizon_months": 36,
}
```
**Critical insight:** Claims has the highest automation potential BUT lowest readiness. Finance has moderate potential with moderate readiness. People has lowest potential but highest readiness. The "best" choice depends on objective: maximum savings → Claims; lowest risk → People; best learning → Technology.
**This is where R4 (Political Capital) matters most.** Success in Function 1 generates capital for Function 2.

### SC-7.3: Cross-Function Workflow Transformation
**Stimulus:** "Automate the entire claims-to-payment workflow spanning Claims + Finance"
**Question:** What's the non-linear impact of workflow automation vs. task automation?
```python
{
    "stimulus_type": "workflow_transformation",
    "workflow_name": "Claims-to-Payment",
    "functions_involved": ["Claims", "Finance"],
    "roles_involved": ["CL-001", "CL-002", "CL-005", "FI-001", "FI-002"],
    "current_handoffs": 8,
    "enable_agent_automation": True,     # AI agents handle entire workflow
}
```
**Key dynamic:** Workflow automation eliminates HANDOFFS between roles, not just tasks within roles. Each handoff eliminated saves coordination time (hidden work from the Workload Iceberg). The impact is non-linear: automating 5 tasks across 3 roles in a workflow > automating the same 5 tasks independently.

### SC-7.4: Function Merger Simulation
**Stimulus:** "Merge Claims Processing and Claims Review into single unit"
**Question:** What's the structural impact? Can merged function operate with fewer managers?
```python
{
    "stimulus_type": "org_restructuring",
    "action": "merge",
    "source_sub_functions": ["Claims Processing", "Claims Review"],
    "new_name": "Claims Operations (Unified)",
}
```
**Key outputs:** Combined headcount, eliminated management overlap, new reporting structure, combined automation potential, change burden assessment.

---

## Family 8: SKILLS & RESKILLING (Forward)
*"What happens to our people's capabilities?"*

### SC-8.1: Reskilling Program Impact
**Stimulus:** "Launch 6-month AI proficiency program for all Claims staff"
**Question:** How does this change adoption rates and outcomes?
```python
{
    "stimulus_type": "skill_intervention",
    "program_name": "Claims AI Academy",
    "target_function": "Claims",
    "target_headcount": 450,
    "program_duration_months": 6,
    "expected_proficiency_lift": 25,     # from 25 to 50
    "investment": 500000,
    "start_month": 1,
}
```
**Key dynamic:** This fires R2 (proficiency flywheel). The simulation should show: proficiency rises → effective AI use increases → results improve → trust builds (R1) → more adoption → more practice → MORE proficiency. The flywheel effect means the lift is > 25 points at month 18.

### SC-8.2: Reskilling vs. Hiring Trade-off
**Stimulus:** "We need 30 people with AI Operations skills. Reskill existing or hire new?"
**Question:** Cost, time, risk, and cultural impact comparison
```python
{
    "stimulus_type": "skill_gap_closure",
    "skill_needed": "AI Operations",
    "quantity_needed": 30,
    "options": [
        {"method": "reskill", "source_pool": "Claims Data Entry Clerks", "duration_months": 8, "cost_per_person": 8000, "success_rate": 0.75},
        {"method": "hire", "time_to_fill_months": 4, "cost_per_person": 15000, "salary_premium": 12000},
        {"method": "contract", "hourly_rate": 85, "ramp_time_months": 1},
    ],
}
```
**Key output:** 36-month total cost comparison, capability availability timeline, risk of skill gap during transition, cultural impact (reskilling builds trust and loyalty; layoff+hire destroys trust).

### SC-8.3: Sunrise/Sunset Skill Migration Map
**Stimulus:** "Show me the complete skill shift over 24 months under scenario P2 (Balanced)"
**Question:** Which skills are growing? Shrinking? What's the reskilling roadmap?
```python
{
    "stimulus_type": "skill_trajectory",
    "scenario": "P2",
    "time_horizon_months": 24,
    "output": "skill_migration_map",
}
```
**Key output:** Per-function skill heat map showing sunrise skills (demand growing), sunset skills (demand declining), and the CRITICAL skills that are sunset for one workload but sunrise for another (the "same skill, different direction" insight from Etter).

---

## Family 9: SEQUENCING & PATH DEPENDENCY (Comparison)
*"Does the order matter? YES."*

### SC-9.1: Function Sequencing
**Stimulus:** "Compare: Claims→Finance→People vs. People→Finance→Claims vs. Finance→Claims→People"
**Question:** Do we end up in the same place? (No.)
```python
{
    "stimulus_type": "sequencing_comparison",
    "sequences": [
        ["Claims", "Finance", "People"],
        ["People", "Finance", "Claims"],
        ["Finance", "Claims", "People"],
    ],
    "phase_duration_months": 12,        # 12 months per function
    "total_horizon": 36,
}
```
**Critical insight this proves:** PATH DEPENDENCY IS REAL. Starting with Claims (hard, risky) may produce higher raw savings but risks early failure → R4 (political capital) collapses → Functions 2 and 3 get fewer resources. Starting with People (easy, safe) builds capital → Claims gets more support when its turn comes.
**Expected result:** The "hard first" sequence produces highest variance (either great or terrible). The "easy first" sequence produces lower variance but often higher EXPECTED value.

### SC-9.2: Tool Sequencing Within Function
**Stimulus:** "In Claims: UiPath first vs. Copilot first vs. Custom AI first"
**Question:** Which tool produces the fastest initial wins?
```python
{
    "stimulus_type": "tool_sequencing",
    "function": "Claims",
    "tools": ["UiPath RPA", "Microsoft Copilot", "Custom Claims AI"],
    "sequences": [
        ["UiPath RPA", "Microsoft Copilot", "Custom Claims AI"],
        ["Microsoft Copilot", "Custom Claims AI", "UiPath RPA"],
        ["Custom Claims AI", "UiPath RPA", "Microsoft Copilot"],
    ],
    "stagger_months": 4,
}
```
**Key dynamic:** UiPath addresses Directive tasks (data entry, form processing) — high automation, visible impact, builds R4 quickly. Copilot addresses broader categories but less dramatic per-task. Custom AI has highest potential but longest deployment. The sequence UiPath → Copilot → Custom AI likely wins because it front-loads visible wins.

### SC-9.3: Phase Reordering Within Transformation
**Stimulus:** "Compare: Reskill→Deploy→Reduce vs. Deploy→Reskill→Reduce vs. Deploy→Reduce→Reskill"
**Question:** Does investing in people BEFORE technology improve outcomes?
```python
{
    "stimulus_type": "phase_sequencing",
    "function": "Claims",
    "phases_to_order": ["reskilling", "technology_deployment", "headcount_reduction"],
    "sequences": [
        ["reskilling", "technology_deployment", "headcount_reduction"],
        ["technology_deployment", "reskilling", "headcount_reduction"],
        ["technology_deployment", "headcount_reduction", "reskilling"],
    ],
}
```
**Expected result:** "Reskill first" has slower start but avoids skill valley (B2). "Deploy first" has faster start but hits skill valley AND resistance (B3). "Reduce first" is catastrophic — people leave before automation is ready, remaining staff overwhelmed (B1 vicious cycle triggers).

---

## Family 10: SENSITIVITY & STRESS TESTS (Analysis)
*"What matters most? What breaks?"*

### SC-10.1: Single-Parameter Sensitivity
**Stimulus:** "Vary change readiness from 20 to 90 in steps of 10, holding everything else constant"
**Question:** How sensitive is net savings to this parameter?
```python
{
    "stimulus_type": "sensitivity_analysis",
    "base_scenario": "P2",
    "parameter": "change_readiness",
    "range": [20, 30, 40, 50, 60, 70, 80, 90],
    "output_metrics": ["net_savings_36mo", "headcount_change", "risk_score", "adoption_speed"],
}
```
**Expected output:** Tornado chart showing nonlinear relationship. Below 40: near-zero adoption. 40-70: steep climb. Above 70: diminishing returns. The BREAKPOINT at ~40 is the critical insight.

### SC-10.2: Multi-Parameter Sensitivity (Interaction Effects)
**Stimulus:** "Vary both readiness AND proficiency simultaneously"
**Question:** Are there interaction effects? (Yes — they MULTIPLY.)
```python
{
    "stimulus_type": "sensitivity_analysis",
    "base_scenario": "P2",
    "parameters": {
        "change_readiness": [30, 50, 70],
        "ai_proficiency": [20, 40, 60],
    },
    "output_metric": "net_savings_36mo",
}
```
**Expected output:** 3×3 matrix showing that low readiness + low proficiency ≈ zero outcome, while high readiness + high proficiency ≈ 4× the medium-medium outcome. Multiplicative, not additive.

### SC-10.3: Trust Destruction Stress Test
**Stimulus:** "A high-profile AI error occurs at month 6. A second error at month 10."
**Question:** What's the impact on adoption trajectory?
```python
{
    "stimulus_type": "stress_test",
    "base_scenario": "P2",
    "events": [
        {"month": 6, "type": "ai_error", "severity": "high", "visibility": "public"},
        {"month": 10, "type": "ai_error", "severity": "medium", "visibility": "internal"},
    ],
}
```
**Key dynamic:** R1 (trust-adoption flywheel) is disrupted. Trust drops sharply → adoption slows → proficiency stalls → less practice → slower recovery. The ASYMMETRY means recovery from two errors takes 6-12 months.
**Critical output:** "With zero errors, 36-month savings = $10M. With two errors, savings = $6M. Each high-profile AI error costs ~$2M in delayed transformation."

### SC-10.4: Attrition Shock
**Stimulus:** "15% voluntary attrition spike in Technology at month 8 (competitors poaching AI talent)"
**Question:** Impact on all in-flight transformation programs
```python
{
    "stimulus_type": "stress_test",
    "base_scenario": "P2",
    "events": [
        {"month": 8, "type": "attrition_spike", "function": "Technology", "magnitude_pct": 15},
    ],
}
```
**Cascade:** Loss of key technical staff → proficiency drops → in-flight deployments slow → maintenance burden on remaining staff (B1) → more attrition risk (reinforcing). Plus: the people who leave are often the highest-skilled (B4: seniority offset reversed — most capable leave first).

### SC-10.5: Breakpoint Analysis
**Stimulus:** "At what headcount reduction percentage does risk become unacceptable?"
**Question:** Find the threshold where system behavior changes qualitatively
```python
{
    "stimulus_type": "breakpoint_analysis",
    "parameter": "headcount_reduction_pct",
    "range": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    "function": "Claims",
    "risk_threshold": "high",
    "quality_threshold": 0.85,          # min service quality
}
```
**Expected output:** Nonlinear risk curve. Below 20%: manageable. 20-30%: increasing but controlled. Above 30%: risk spikes exponentially as remaining staff can't absorb redistributed work → quality drops → vicious cycle (B1). The BREAKPOINT is the maximum reduction before the system destabilizes.

### SC-10.6: "Do Nothing" Baseline (Competitive Erosion)
**Stimulus:** "What happens if we don't transform at all over 36 months?"
**Question:** The cost of inaction (D6: Moving Ceiling)
```python
{
    "stimulus_type": "baseline",
    "scenario": "do_nothing",
    "time_horizon_months": 36,
    "assumptions": {
        "natural_attrition_pct_annual": 8,
        "salary_inflation_pct_annual": 3,
        "competitor_automation_growth_pct_annual": 10,
        "ai_capability_growth_rate": "accelerating",
    },
}
```
**Key output:** Growing automation gap, increasing competitive exposure, rising opportunity cost. "Doing nothing costs $X over 36 months in competitive disadvantage and missed savings."

---

## Family 11: REGULATORY & COMPLIANCE (Constraint)
*"Rules change. How does the plan adapt?"*

### SC-11.1: New Regulation — More Tasks Mandated Human
**Stimulus:** "New regulation: all claims above $50K require human review at 3 stages (previously 1)"
**Question:** Impact on current transformation plan
```python
{
    "stimulus_type": "regulatory_change",
    "new_constraint": {
        "scope": "Claims",
        "condition": "claim_value > 50000",
        "mandated_human_tasks": ["initial_review", "damage_assessment", "final_approval"],
    },
    "impact_on_scenario": "P2",
}
```
**Key output:** Revised automation ceiling (lower for affected tasks), revised headcount trajectory (more people needed for compliance), revised savings (lower). The "compliance floor" rises, reducing the addressable gap.

### SC-11.2: Regulation Relaxation — AI Now Permitted
**Stimulus:** "Regulation change: AI-assisted claims triage now permitted for all claim values"
**Question:** How much new potential unlocked?
```python
{
    "stimulus_type": "regulatory_change",
    "relaxation": {
        "scope": "Claims",
        "previously_mandated": ["claims_triage"],
        "now_permitted": "ai_assisted",
    },
    "impact_on_scenario": "P2",
}
```
**Key output:** Expanded automation ceiling, additional savings potential, revised roadmap.

---

## Family 12: COMPOSITE & WHAT-IF SCENARIOS
*"The real world doesn't change one thing at a time"*

### SC-12.1: Full Transformation Program Simulation
**Stimulus:** Complete transformation program with multiple concurrent workstreams
```python
{
    "stimulus_type": "composite_program",
    "workstreams": [
        {"name": "Claims Quick Wins", "start": 1, "end": 6, "type": "adoption_gap", "function": "Claims"},
        {"name": "Org-wide Copilot", "start": 3, "end": 12, "type": "technology_injection", "tool": "Copilot", "scope": "ALL"},
        {"name": "Claims AI Deep", "start": 7, "end": 18, "type": "technology_injection", "tool": "Custom Claims AI", "scope": "Claims"},
        {"name": "Finance Automation", "start": 10, "end": 24, "type": "function_transformation", "function": "Finance"},
        {"name": "People Simplification", "start": 13, "end": 24, "type": "function_transformation", "function": "People"},
        {"name": "Reskilling Wave 1", "start": 1, "end": 12, "type": "skill_intervention", "scope": "Claims,Finance"},
        {"name": "Reskilling Wave 2", "start": 13, "end": 24, "type": "skill_intervention", "scope": "People,Technology"},
        {"name": "Org Restructure", "start": 19, "end": 30, "type": "role_redesign", "scope": "ALL"},
    ],
    "total_budget": 8000000,
    "time_horizon_months": 36,
}
```
**This is the full simulation.** Multiple concurrent, interacting workstreams. The simulation must handle: overlapping tool deployments, shared human system (readiness consumed by multiple workstreams), compounding savings, cumulative risk, and the interaction effects where workstream 1's success boosts workstream 2 (R4).

### SC-12.2: "What Would It Take?" Meta-Scenario
**Stimulus:** "We want $15M savings in 24 months, max risk medium, maintain quality above 90%"
**Question:** What's the minimum transformation program that achieves this? Is it even possible?
```python
{
    "stimulus_type": "inverse_optimization",
    "targets": {
        "net_savings": 15000000,
        "time_horizon_months": 24,
        "max_risk": "medium",
        "min_quality": 0.90,
        "min_trust_level": 30,
    },
    "search_space": {
        "tools": "ALL_AVAILABLE",
        "functions": "ALL",
        "phases": "ALL",
        "budget": "unbounded",           # find minimum required
    },
}
```
**Inverse output:** "To achieve $15M in 24 months: Deploy UiPath + Copilot + Custom AI to Claims and Finance, invest $3.2M in technology + $1.1M in reskilling + $0.8M in change management, reduce Claims by 22% and Finance by 15%, requires readiness ≥ 55 (currently 45 in Claims — need readiness intervention first). Feasibility: CONDITIONAL on readiness intervention."

### SC-12.3: Year-Over-Year Transformation with Moving Ceiling
**Stimulus:** "3-year program with annual Etter reassessment (ceiling rises each year)"
**Question:** How does the rising ceiling change the roadmap?
```python
{
    "stimulus_type": "multi_year_with_refresh",
    "years": 3,
    "etter_refresh_months": [12, 24],
    "ceiling_growth_rate_annual": 8,     # 8% more tasks become automatable per year
    "base_scenario": "P2",
}
```
**Key dynamic:** Year 1 plan is stable. Year 2 reassessment reveals 8% more automatable tasks → new adoption gap opens → free money again → R3 (savings flywheel) restarts. The Twin must handle this "moving target" natively.

### SC-12.4: Competitive Response Scenario
**Stimulus:** "Competitor publicly announces 50% claims automation and 30% cost reduction"
**Question:** What's the minimum response to maintain competitive position?
```python
{
    "stimulus_type": "competitive_response",
    "competitor_achievement": {
        "function": "Claims",
        "automation_pct": 50,
        "cost_reduction_pct": 30,
    },
    "our_target": "match_or_exceed",
    "urgency": "high",
    "time_constraint_months": 18,
}
```
**Key output:** Accelerated roadmap, required investment, risk assessment. Urgency compresses timelines → resistance increases (B3) → need MORE change management investment, not less.

---

# PART II: SCENARIO PARAMETER SPECIFICATION

## Extended `simulation_params.csv` Schema

The current 5-scenario params file must be extended to support all families. New schema:

```
scenario_id           — unique identifier
scenario_family       — which of the 12 families
scenario_name         — human-readable name
stimulus_type         — technology_injection | headcount_target | budget_constraint | ...
direction             — forward | inverse | comparison | sensitivity | stress_test

# Scope
target_scope          — ALL | function name | sub-function | role_id | workflow
target_functions      — comma-separated list (if multi-function)
target_roles          — comma-separated role_ids (if role-specific)

# Targets (for inverse scenarios)
target_metric         — net_savings | headcount_reduction | automation_pct | output_volume
target_value          — numeric value for the target
target_months         — timeline for achieving target

# Technology
tools                 — comma-separated tool names
deployment_months     — comma-separated deployment start months
adoption_phases       — adoption | expansion | extension (comma-separated)

# Rate Parameters
alpha_adopt           — adoption rate multiplier (0-1)
alpha_expand          — expansion rate multiplier (0-1)
alpha_extend          — extension rate multiplier (0-1)
s_curve_k             — S-curve steepness
s_curve_midpoint      — S-curve midpoint (months)

# Policy
hc_policy             — natural_attrition | moderate_reduction | active_reduction | no_layoffs | rapid_redeployment
redistribution_mode   — absorb_adjacent | automate_first | hybrid
readiness_threshold   — minimum readiness to proceed

# Human System Overrides
initial_proficiency   — override per function (JSON or use default)
initial_readiness     — override per function
initial_trust         — override per function

# Financial
budget_total          — total available budget ($)
budget_allocation     — JSON: {technology: %, reskilling: %, change_mgmt: %}

# Constraints
max_risk_level        — low | medium | high | critical
min_quality           — minimum service quality (0-1)
compliance_override   — JSON: additional mandated-human tasks

# Events (for stress tests)
events                — JSON: [{month, type, severity, scope}]

# Sensitivity
sweep_parameter       — parameter to vary
sweep_range           — JSON: [values to test]

# Comparison
compare_with          — comma-separated scenario_ids to compare against

# Meta
time_horizon_months   — simulation duration
objective             — maximize_savings | minimize_risk | maximize_automation | balanced
notes                 — free text description
```

---

# PART III: THE 60 SCENARIO INSTANCES

Below are the concrete scenario parameter sets for the MVP. Organized in priority order for implementation.

## Priority 1: Core Forward Simulations (8 scenarios)

| ID | Family | Name | Stimulus | Key Question |
|----|--------|------|----------|-------------|
| SC-1.1 | Tech Inject | Copilot → Claims | Deploy 1 tool to 1 function | Basic cascade validation |
| SC-1.2 | Tech Inject | Copilot → All | Deploy 1 tool org-wide | Human system variation across functions |
| SC-1.5 | Tech Inject | Adoption Gap Only | Fix adoption of deployed tools | The "free money" scenario |
| SC-5.2 | Output Target | Maintain Output, -20% HC | Hold volume, reduce people | Core transformation business case |
| SC-7.1 | Function Transform | Claims Phased | Full function transformation | End-to-end cascade |
| SC-10.6 | Baseline | Do Nothing | No transformation | Cost of inaction |
| SC-6.1 | Role Redesign | Redesign Claims Adjuster | Single role deep dive | Future-of-work output |
| SC-8.1 | Skills | Claims AI Academy | Reskilling program | Human system flywheel |

## Priority 2: Inverse & Optimization Simulations (8 scenarios)

| ID | Family | Name | Stimulus | Key Question |
|----|--------|------|----------|-------------|
| SC-2.1 | HC Target | Reduce 15% org-wide | HC reduction target | What does it take? |
| SC-2.2 | HC Target | Function-specific targets | Differentiated reduction | Feasibility per function |
| SC-4.1 | Automation Target | Reach 35% automation | Automation target | Roadmap generation |
| SC-3.1 | Budget | $2M optimized | Budget constraint | Best allocation |
| SC-3.2 | Budget | Allocation comparison | 3 budget splits | Tech vs. people investment |
| SC-5.3 | Output | +20% output, -15% HC | Dual target | Feasibility assessment |
| SC-12.2 | Meta | $15M in 24mo | Multi-constraint target | Minimum viable program |
| SC-4.3 | Automation | By task category | Category-level targets | Future shape of work |

## Priority 3: Comparison & Sequencing (8 scenarios)

| ID | Family | Name | Stimulus | Key Question |
|----|--------|------|----------|-------------|
| SC-9.1 | Sequencing | Function order (3 paths) | Claims/Finance/People order | Path dependency proof |
| SC-9.2 | Sequencing | Tool order in Claims | 3 tool sequences | Which tool first? |
| SC-9.3 | Sequencing | Phase order | Reskill/Deploy/Reduce order | People-first vs. tech-first |
| SC-1.3 vs SC-1.4 | Tech Inject | Simultaneous vs. staggered | Same tools, different timing | Risk/reward trade-off |
| SC-7.2 | Function Compare | Which function first? | 3 function starts | Best starting point |
| SC-3.3 | Budget | Phased with gates | Gated budget release | Phase 1 success criteria |
| SC-8.2 | Skills | Reskill vs. hire | 3 skill gap options | Build vs. buy vs. borrow |
| SC-2.3 | HC Target | Role-level elimination | Single role removal | Adjacent role impact |

## Priority 4: Sensitivity & Stress Tests (8 scenarios)

| ID | Family | Name | Stimulus | Key Question |
|----|--------|------|----------|-------------|
| SC-10.1 | Sensitivity | Readiness sweep | CR 20→90 | Most sensitive parameter |
| SC-10.2 | Sensitivity | Readiness × Proficiency | 3×3 matrix | Interaction effects |
| SC-10.3 | Stress | Trust destruction | 2 AI errors | Recovery dynamics |
| SC-10.4 | Stress | Attrition shock | 15% tech attrition | Resilience test |
| SC-10.5 | Breakpoint | HC reduction limit | 5%→50% sweep | Where does it break? |
| SC-11.1 | Regulatory | More compliance tasks | 30 new mandated tasks | Ceiling compression |
| SC-11.2 | Regulatory | Regulation relaxation | AI now permitted | Ceiling expansion |
| SC-12.4 | Competitive | Competitor response | Match 50% automation | Urgency simulation |

## Priority 5: Composite & Advanced (8 scenarios)

| ID | Family | Name | Stimulus | Key Question |
|----|--------|------|----------|-------------|
| SC-12.1 | Composite | Full 36-month program | 8 concurrent workstreams | Real-world complexity |
| SC-12.3 | Multi-year | Moving ceiling | Annual reassessment | AI age dynamics |
| SC-7.3 | Workflow | Claims-to-Payment | Cross-function workflow | Non-linear impact |
| SC-7.4 | Restructure | Merge Claims sub-functions | Org restructuring | Structural change |
| SC-6.2 | Role | Eliminate Data Entry Clerk | Full role elimination | Cascade mapping |
| SC-6.3 | Role | Create AI Ops Specialist | New role creation | Role vacuum filling |
| SC-6.4 | Role | Role vacancy analysis | What if nobody does this? | Orphaned tasks |
| SC-2.4 | HC Target | Management level reduction | Flatten hierarchy | Span-of-control |

---

# PART IV: WHAT EACH SCENARIO MUST PRODUCE

## Universal Output Schema

Every scenario, regardless of family, produces:

### 1. Trajectory Data (time-series, monthly for 36 months)
```
month, adoption_pct, freed_hours, headcount, net_position,
skill_gap, productivity, trust_level, readiness, proficiency,
political_capital, risk_score, change_burden
```

### 2. Summary Metrics
```
net_savings_12mo, net_savings_24mo, net_savings_36mo,
total_investment, payback_month, peak_risk_month, peak_risk_score,
skill_valley_depth, skill_valley_duration_months,
hc_change_pct, roles_redesigned, roles_eliminated, roles_created,
sunrise_skills_count, sunset_skills_count,
compliance_tasks_protected, breakeven_month
```

### 3. Impact Map (per entity)
```
role_id, current_hc, projected_hc_12mo, projected_hc_24mo, projected_hc_36mo,
freed_pct, redesign_triggered, elimination_triggered,
top_sunset_skills, top_sunrise_skills,
risk_flags
```

### 4. Comparison Data (for multi-scenario)
```
scenario_id, metric, value, rank, vs_baseline_pct
```

### 5. Decision Trace (explainability)
```
month, decision, reasoning, parameters_used, confidence,
dominant_loop, loop_direction
```

---

# PART V: MAPPING SCENARIOS TO FEEDBACK LOOPS

Which loops are activated by which scenarios — critical for validation.

| Scenario Family | B1 Capacity | B2 Skill Valley | B3 Resistance | B4 Seniority | R1 Trust | R2 Proficiency | R3 Savings | R4 Capital |
|----------------|:-----------:|:---------------:|:-------------:|:------------:|:--------:|:--------------:|:----------:|:----------:|
| 1. Tech Inject | ● | ● | ● | ○ | ● | ● | ● | ● |
| 2. HC Target | ● | ○ | ● | ● | ○ | ○ | ● | ● |
| 3. Budget | ○ | ● | ○ | ○ | ○ | ● | ● | ● |
| 4. Auto Target | ● | ● | ● | ● | ● | ● | ● | ● |
| 5. Output Target | ● | ● | ● | ● | ● | ● | ● | ● |
| 6. Role Transform | ● | ● | ● | ○ | ○ | ○ | ○ | ● |
| 7. Function Transform | ● | ● | ● | ● | ● | ● | ● | ● |
| 8. Skills | ○ | ● | ○ | ○ | ● | ● | ○ | ● |
| 9. Sequencing | ● | ● | ● | ● | ● | ● | ● | ● |
| 10. Sensitivity | ALL — depends on parameter swept |
| 11. Regulatory | ● | ○ | ● | ○ | ● | ○ | ● | ● |
| 12. Composite | ● | ● | ● | ● | ● | ● | ● | ● |

● = strongly activated | ○ = weakly or conditionally activated

---

# PART VI: IMPLEMENTATION SEQUENCE FOR SIMULATION ENGINE

## Which Scenario Families Require Which Engine Capabilities

| Engine Capability | Required By Families | Stage |
|------------------|---------------------|-------|
| Static gap computation | 1, 4, 5 | Stage 0 |
| Single-step cascade (9 steps) | 1, 6, 7 | Stage 1 |
| S-curve adoption over time | 1, 4, 5, 7 | Stage 2 |
| Human system feedback loops | 1, 5, 7, 8, 9, 10, 12 | Stage 3 |
| Multi-scenario comparison | 3, 7, 9 | Stage 4 |
| Inverse solver (target → requirements) | 2, 4, 5, 12 | Stage 5 (new) |
| Sensitivity sweep | 10 | Stage 5 |
| Event injection (stress test) | 10 | Stage 5 |
| Multi-stimulus composition | 12 | Stage 5 |
| Workflow-level automation | 7 (SC-7.3) | Stage 5 |
| Regulatory constraint modification | 11 | Stage 5 |

### Stage 5 Addition: Inverse Solver

The existing 5 stages handle FORWARD simulation. Families 2, 4, 5, 12 require INVERSE simulation — working backward from targets to requirements. This needs a solver:

```
INVERSE_SOLVE(target_metric, target_value, constraints):
    for each parameter combination in search_space:
        result = FORWARD_SIMULATE(parameters)
        if result[target_metric] >= target_value AND satisfies(constraints):
            yield (parameters, result)
    return ranked by efficiency (min cost, min risk, min time)
```

---

# SUMMARY

## Complete Scenario Catalog

| Priority | Families | Scenarios | Engine Stage Required |
|----------|----------|-----------|---------------------|
| P1: Core Forward | 1, 5, 6, 7, 8, 10 | 8 | Stage 0-3 |
| P2: Inverse & Optimization | 2, 3, 4, 5, 12 | 8 | Stage 3-5 |
| P3: Comparison & Sequencing | 1, 2, 3, 7, 8, 9 | 8 | Stage 3-4 |
| P4: Sensitivity & Stress | 10, 11, 12 | 8 | Stage 3-5 |
| P5: Composite & Advanced | 6, 7, 12 | 8 | Stage 5 |
| **Total** | **12 families** | **40 named scenarios** | **Stages 0-5** |

## The Two Meta-Questions Every Scenario Answers

1. **"What happens if...?"** → Forward simulation. 24 scenarios.
2. **"What does it take to...?"** → Inverse simulation. 16 scenarios.

## Validation: A Scenario is Working When...

1. Forward scenarios produce S-curve adoption (not linear)
2. Inverse scenarios return feasibility verdicts (not just numbers)
3. Comparison scenarios show meaningful divergence (>20% on key metrics)
4. Sensitivity scenarios identify nonlinear breakpoints
5. Stress tests show recovery dynamics (not instant bounce-back)
6. Composite scenarios show interaction effects (non-additive)
7. ALL scenarios produce decision traces (explainability)
8. ALL scenarios respect compliance floors (hard constraints)
9. Human system multiplier visibly affects all adoption rates
10. Path dependency is demonstrable (different sequence → different outcome)
