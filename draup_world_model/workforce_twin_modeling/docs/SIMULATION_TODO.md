# Simulation Lab — TODO Tracker

> Last updated: 2026-03-04
> Branch: `claude/mental-models-systems-fXyh3`

---

## Current Architecture

```
UI (SimulationLab.tsx) → API (simulate.py) → Engine (cascade.py + simulator_fb.py)
```

**Core limitation**: The engine runs a single forward simulation — it takes S-curve adoption params, HC policy, absorption factor, and feedback loop params, then runs a 9-step cascade for N months. It does **NOT** branch on `stimulus_type`. All 17 types run the identical cascade logic. Differentiation is only through preset parameter combinations.

**9-step cascade (no branching):**
1. Scope Resolution → 2. Task Reclassification → 3. Capacity Computation → 4. Skill Impact → 5. Workforce Impact → 6. Financial Impact → 7. Structural Impact → 8. Human System Impact → 9. Risk Assessment

---

## Status Summary

| # | Type | Status | What Works | What's Missing |
|---|------|--------|------------|----------------|
| 1 | Technology Injection | **Ready** | Full forward sim with tools, scope, policy | — |
| 2 | Headcount Target | **Beta** | Runs with aggressive presets | No inverse solver for exact HC target |
| 3 | Budget Constraint | **Beta** | Runs with conservative presets | No budget-aware adoption scaling |
| 4 | Automation Target | **Beta** | Runs with high alpha | No solver to hit exact automation % |
| 5 | Output Target | **Beta** | Runs with balanced presets | No output-maintenance constraint |
| 6 | Role Redesign | **Ready** | Scoped tool deployment per function | — |
| 7 | Function Overhaul | **Ready** | All 3 S-curve phases enabled | — |
| 8 | Skill Intervention | **Ready** | No tools, training cost only | — |
| 9 | Org Restructuring | **Beta** | Runs with rapid_redeployment policy | No restructuring-specific cascade logic |
| 10 | Adoption Gap | **Ready** | No new tools, improves existing adoption | — |
| 11 | Baseline / Do Nothing | **Ready** | Zero adoption (alpha=0.0) | — |
| 12 | Composite Program | **Ready** | Multi-phase with all toggles | — |
| 13 | Sequencing | **Coming Soon** | — | Needs multi-run orchestrator |
| 14 | Sensitivity Analysis | **Coming Soon** | — | Needs parameter sweep + comparison |
| 15 | Stress Test | **Ready** | Extreme params (alpha=0.9) | — |
| 16 | Regulatory Change | **Beta** | Runs with moderate presets | No compliance constraint logic |
| 17 | Competitive Pressure | **Beta** | Runs with aggressive presets | No competitor benchmark input |

**Ready**: 8 types | **Beta**: 6 types | **Coming Soon**: 2 types

---

## TODO Items

---

### Priority 1 — Beta → Ready (Inverse Constraint Solving)

These 4 types collect a user target via slider but the engine ignores it. The slider values never reach the API payload, and even if they did, the engine has no inverse solver.

**Common pattern**: All 4 need binary search on `adoptAlpha` — run forward sim N times, find the alpha that produces the target outcome.

#### TODO 1.1: Headcount Target — Inverse Solver
- **Problem**: User sets "15% HC reduction" but engine just uses `adoptAlpha: 0.7` + `active_reduction` preset. The actual reduction depends on org data, not the target.
- **What's needed**:
  1. **UI** (`SimulationLab.tsx`): Wire `hcTargetPct` into the `simulate.mutate()` payload as `hc_target_pct`
  2. **API** (`simulate.py`): Accept `hc_target_pct: Optional[float]` in `SimulationRequest`
  3. **Engine** (new `engine/inverse_solver.py`): Binary search wrapper:
     - Try different `adoptAlpha` values (0.1 → 0.9)
     - Run forward sim for each
     - Find the alpha that produces closest to target HC reduction %
     - Return that run's results
  4. **Integrate** in `simulator_fb.py`: if `stimulus.target_hc_reduction_pct` is set → call solver first → feed result into normal sim
- **Feasibility check**: If tools only address 20% of tasks, 50% HC reduction is impossible. Solver must return "infeasible" with achievable range.
- **Files**: `SimulationLab.tsx`, `simulate.py`, new `engine/inverse_solver.py`, `cascade.py` (add field to Stimulus), `simulator_fb.py`
- **Complexity**: Medium (5-10 binary search iterations per solve)

#### TODO 1.2: Budget Constraint — Budget-Aware Simulation
- **Problem**: User sets "$2M budget" but engine ignores it. Just uses `adoptAlpha: 0.5`.
- **What's needed**:
  1. Wire `budgetAmount` into API payload as `budget_amount`
  2. Binary search wrapper: find max alpha where `cumulative_investment ≤ budget`
  3. The financial model already computes investment (license + training) — just need to invert it
  4. Alternative approach: run forward sim, cap adoption at month where investment hits budget
- **Files**: Same pattern as 1.1
- **Complexity**: Medium

#### TODO 1.3: Automation Target — Target Solver
- **Problem**: User sets "35% automation" but engine just uses `adoptAlpha: 0.7`.
- **What's needed**:
  1. Wire `autoTargetPct` into API payload as `automation_target_pct`
  2. Binary search: find alpha that achieves closest peak adoption to target %
  3. Simpler than HC target because adoption is more directly controlled by alpha
  4. Must check ceiling: if tools only address 40% of tasks, can't reach 50%
- **Complexity**: Low-Medium (simplest of the 4 inverse solvers)

#### TODO 1.4: Output Target — Productivity Constraint
- **Problem**: User sets "maintain 100% output" but engine doesn't model output explicitly.
- **What's needed**:
  1. **Define what "output" means**: `headcount × proficiency × (1 - change_burden)`? Revenue equivalent? Task volume?
  2. Wire `outputTargetPct` into API payload
  3. Build productivity model: `base_output × (1 + automation_boost) × (1 - skill_gap_drag) × (1 - disruption_drag)`
  4. Solver adjusts policy/absorption to maintain output ≥ target
- **Complexity**: **High** — requires new productivity model that doesn't currently exist
- **Recommendation**: Defer to Phase 4, after the simpler inverse solvers prove the pattern

---

### Priority 2 — Beta → Ready (Scenario-Specific Logic)

These types run but don't have scenario-specific engine behavior — they just use different parameter presets.

#### TODO 2.1: Org Restructuring — Restructuring Cascade
- **Problem**: Uses `rapid_redeployment` policy preset but no restructuring-specific logic (role merging, function consolidation, transition costs)
- **What's needed**:
  1. Optional: Add `restructuring_type` enum (merger, split, consolidation, flatten)
  2. Add restructuring-specific cost model (severance, relocation, re-training)
  3. Modify cascade Step 5 (Workforce) to account for role reassignment between functions
  4. Consider: Do we need this, or is the current preset approximation good enough?
- **Files**: `cascade.py` (Step 5), `simulator_fb.py`
- **Complexity**: High (optional enhancement — current approximation may be sufficient)

#### TODO 2.2: Regulatory Change — Compliance Constraints
- **Problem**: No concept of compliance deadlines, mandatory adoption floors, or penalty costs
- **What's needed**:
  1. Add `compliance_deadline_month` — forces minimum adoption by that month
  2. Add `penalty_cost_per_month` for non-compliance after deadline
  3. Engine adjusts adoption curve to meet deadline (floor on alpha)
  4. Task model already has `compliance_mandated_human` flag — could leverage that
- **Complexity**: Medium

#### TODO 2.3: Competitive Pressure — Reuse Automation Solver
- **Problem**: No competitor benchmark data. Just uses aggressive presets.
- **What's needed**:
  1. Map `competitor_automation_pct` → same solver as TODO 1.3 (automation target)
  2. Different UI framing ("match competitor") but same engine logic
  3. Optional: Add competitive lag/lead time parameter
- **Complexity**: **Low** — just reuses TODO 1.3's solver with different label
- **Blocked by**: TODO 1.3

---

### Priority 3 — Coming Soon (Multi-Run Engine)

These need an orchestration layer that runs **multiple simulations** and compares or chains results.

#### TODO 3.1: Sequencing — Multi-Run Orchestrator
- **Problem**: Need to compare "deploy to Finance first → then HR → then IT" vs "all at once"
- **What's needed**:
  1. **UI**: Function ordering UI (drag-and-drop or numbered list with start months)
  2. **API**: New endpoint `/simulate/sequence` accepting ordered function groups + timing
  3. **Engine** (new `engine/sequencer.py`):
     ```
     SequenceRunner:
       - Split functions into phases with timing
       - Run forward sim per phase
       - Carry state between phases (HC level, human system, financials)
       - Compare vs parallel baseline (single run with all functions)
       - Return both results for comparison
     ```
  4. **UI**: Side-by-side comparison chart (sequenced vs parallel)
  5. **State carry-over**: Between phases, must carry human system state (proficiency, readiness, trust), HC level, skill gaps, cumulative financials
- **Files**: new `engine/sequencer.py`, `simulate.py` (new endpoint), `SimulationLab.tsx` (sequence config + comparison view)
- **Complexity**: **High** — requires simulator refactoring for state initialization

#### TODO 3.2: Sensitivity Analysis — Parameter Sweep
- **Problem**: Need to sweep one parameter across a range and show how results change
- **What's needed**:
  1. **UI**: Select parameter to sweep + range (min/max) + step count
  2. **API**: New endpoint `/simulate/sweep` accepting parameter name, range, steps
  3. **Engine** (new `engine/sensitivity_sweep.py`):
     ```
     SweepRunner:
       - Generate parameter space: linspace(min, max, steps)
       - Run forward sim for each value
       - Collect key metrics per run
       - Return array of (param_value → metrics)
     ```
  4. **Sweepable parameters**: adoption alpha, absorption factor, resistance sensitivity, trust build rate, initial readiness, initial proficiency
  5. **UI**: Tornado chart or line chart showing metric vs parameter
  6. **2D sweeps** (stretch): Sweep two parameters simultaneously → heatmap visualization
  7. **Optimization**: Cache cascade ceiling (compute once, reuse across sweep)
- **Files**: new `engine/sensitivity_sweep.py`, `simulate.py` (new endpoint), `SimulationLab.tsx` (sweep config + tornado chart)
- **Complexity**: **Medium-High** (10-20 sim runs per sweep, need aggregation + visualization)

---

### Priority 4 — UI/UX Improvements

#### TODO 4.1: Wire Type-Specific Slider Values to API
- **Problem**: `hcTargetPct`, `budgetAmount`, `autoTargetPct`, `outputTargetPct` are collected in UI state but never included in the `simulate.mutate()` payload
- **Fix**: Add these to the API call payload when their respective field is active
- **File**: `SimulationLab.tsx` → `handleRun()`
- **Complexity**: Low
- **Blocked by**: API needs to accept these fields first (TODOs 1.1-1.4)

#### TODO 4.2: Comparison Mode
- **Problem**: Can only run one simulation at a time. No way to compare scenarios side by side.
- **What's needed**:
  1. "Save Result" button after each run
  2. Result history sidebar with named snapshots
  3. Overlay charts comparing 2-3 saved results
- **Complexity**: Medium

#### TODO 4.3: Preset → Custom Bridging
- **Problem**: Presets (P1-P5) and Custom mode are separate. No way to "start from P3 and tweak."
- **What's needed**:
  1. "Customize" button on each preset card
  2. Switches to Custom mode with that preset's params pre-filled
- **Complexity**: Low

#### TODO 4.4: Export Results
- **Problem**: No way to export simulation results
- **What's needed**: CSV/Excel export button for timeline data + summary metrics
- **Complexity**: Low

#### TODO 4.5: Result Validation for Beta Types
- **Problem**: Beta types run but user has no feedback on how close the result is to their target
- **What's needed**:
  1. Show target vs actual after run: "Target 15% HC reduction → Achieved 17.2%"
  2. Confidence indicator: green (±5%), amber (±15%), red (>15% off)
- **Complexity**: Low (once solvers exist)

---

### Priority 5 — Engine Infrastructure

#### TODO 5.1: Stimulus Type Branching (Decision Needed)
- **Current**: `stimulus_type` stored but never checked in engine
- **Decision**: Should the engine branch on stimulus_type? Or is differentiation-via-parameters sufficient?
- **Recommendation**: Don't over-engineer. Only inverse types (P1) truly need engine changes. Most types are well-served by parameter presets. Add branching only where needed:
  ```python
  match stimulus.stimulus_type:
      case "headcount_target":  adopt = solve_for_hc(target)
      case "budget_constraint": adopt = solve_for_budget(budget)
      case _:                   adopt = params.adoption.alpha
  ```

#### TODO 5.2: Scenario Executor — Respect stimulus_type
- **Problem**: `scenario_executor.py` hardcodes `stimulus_type="technology_injection"` for ALL scenarios
- **Fix**: Map `scenario_family` from CSV → proper `stimulus_type`
- **File**: `stages/scenario_executor.py` line 128
- **Complexity**: Low

#### TODO 5.3: Common Inverse Solver Infrastructure
- **New file**: `engine/inverse_solver.py`
- **Contains**: Generic binary search function parameterized by cost function
  ```python
  def solve_for_target(
      run_sim: Callable,     # forward simulation function
      extract_metric: Callable,  # pull target metric from result
      target_value: float,
      param_range: (float, float),
      tolerance: float = 0.02,
      max_iterations: int = 10,
  ) → (float, SimulationResult):
  ```
- Reused by TODO 1.1, 1.2, 1.3, 1.4, 2.3

#### TODO 5.4: Feedback Loop Visualization with Real Data
- **Problem**: Feedback Loops tab shows static descriptions, not actual loop strengths from the simulation
- **What's needed**:
  1. Engine returns per-month feedback loop contributions (partially in trace)
  2. Chart showing B1-B4 and R1-R4 strength over time
  3. Net system balance (reinforcing vs balancing)
- **Complexity**: Medium

---

## Implementation Roadmap (Recommended)

```
Phase 1 — Quick Wins (1 week):
  ├── TODO 4.1: Wire slider values to API payload
  ├── TODO 4.3: Preset → Custom bridging
  ├── TODO 4.4: Export results
  └── TODO 5.2: Fix scenario_executor stimulus_type

Phase 2 — Inverse Solvers (2-3 weeks):
  ├── TODO 5.3: Common solver infrastructure
  ├── TODO 1.3: Automation Target solver (simplest)
  ├── TODO 1.1: Headcount Target solver
  ├── TODO 1.2: Budget Constraint solver
  └── TODO 2.3: Competitive Pressure (reuses 1.3)

Phase 3 — Scenario Enhancements (1-2 weeks):
  ├── TODO 2.2: Regulatory compliance constraints
  ├── TODO 2.1: Org Restructuring (if needed)
  └── TODO 4.5: Result validation for Beta types

Phase 4 — Multi-Run Engine (3-4 weeks):
  ├── TODO 3.2: Sensitivity parameter sweep
  └── TODO 3.1: Sequencing orchestrator

Phase 5 — Hard Problems + Polish (4-6 weeks):
  ├── TODO 1.4: Output Target (needs productivity model)
  ├── TODO 4.2: Comparison mode
  └── TODO 5.4: Feedback loop visualization
```

---

## Key Files Reference

| File | Purpose | Changes Needed |
|------|---------|---------------|
| `engine/cascade.py` | 9-step cascade, Stimulus dataclass | Add target fields to Stimulus |
| `engine/simulator_fb.py` | Main sim loop with feedback | Integrate inverse solvers |
| `engine/rates.py` | S-curve params, presets P1-P5 | May need new fields |
| `engine/feedback.py` | 8 feedback loops, HumanSystemState | No changes needed |
| `api/routes/simulate.py` | API endpoint, SimulationRequest | Expand request model |
| `stages/scenario_executor.py` | CSV → engine params | Fix hardcoded stimulus_type |
| `ui/src/pages/SimulationLab.tsx` | Main UI | Wire slider values, comparison mode |
| **New: `engine/inverse_solver.py`** | Binary search solver | Create |
| **New: `engine/sequencer.py`** | Multi-run orchestrator | Create |
| **New: `engine/sensitivity_sweep.py`** | Parameter sweep | Create |

---

## Completed Items

- [x] Redesign SimulationLab with systems perspective (17 stimulus types)
- [x] Dynamic per-type configuration (fields change with stimulus type)
- [x] Show More/Show Less for primary (10) + extended (7) types
- [x] Adaptive grid layout for types with/without Column 1 content
- [x] Fix org_restructuring and adoption_gap empty config panels
- [x] Add status badges (Beta amber, Coming Soon muted)
- [x] Fix handleRun() to respect noTools flag (empty tools for baseline, skill_intervention, adoption_gap)
- [x] Fix Adoption Ceiling slider min=0 for baseline type
- [x] Disable Run button for coming_soon types with explanation
- [x] Beta warning next to Run button for approximate types
- [x] Honest descriptions for all types (what they actually do vs claim)
- [x] Advanced settings with 4 key feedback tuning knobs
- [x] S-curve phase toggles (Adopt/Expand/Extend)
- [x] **Inverse propagation engine** (`engine/inverse_solver.py`) — binary search solver
- [x] **TODO 5.3**: Common inverse solver infrastructure (generic binary search + 3 specific solvers)
- [x] **TODO 1.1**: Headcount Target solver (15% → alpha=0.753, 7 iterations, 1.7% error)
- [x] **TODO 1.2**: Budget Constraint solver ($4.35M → alpha=0.275, 4 iterations, 0.2% error)
- [x] **TODO 1.3**: Automation Target solver (35% → alpha=0.444, 6 iterations, 1.4% error)
- [x] **TODO 2.3**: Competitive Pressure solver (reuses automation_target solver)
- [x] **TODO 4.1**: Wire UI slider values (hcTargetPct, budgetAmount, autoTargetPct) to API payload
- [x] **TODO 5.1**: Stimulus type branching — API routes to inverse solver for target-based types
- [x] Stimulus dataclass gains target fields (target_hc_reduction_pct, target_budget_amount, target_automation_pct)
- [x] SimulationRequest expanded with inverse target fields
- [x] TypeScript InverseSolveResult interface + SimulationResult.inverse_solve field
- [x] UI inverse solve result banner (green/amber) with solver metadata
