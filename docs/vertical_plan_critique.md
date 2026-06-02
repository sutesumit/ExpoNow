# Critique: VERTICAL_IMPLEMENTATION_PLAN.md vs. Assignment Requirements

**Review date:** 2026-05-30
**Document reviewed:** `docs/VERTICAL_IMPLEMENTATION_PLAN.md` (1922 lines)
**Reference:** `docs/Bus_Charging_Scheduler_Assignment.md` (345 lines)

---

## Executive Summary

The vertical plan applies sound engineering discipline — TDD, strategy contracts, clean architecture boundaries, incremental slicing — and demonstrates strong system design maturity. However, it misaligns with several of the assignment's expressly stated priorities. The assignment's central thesis is **"the one thing we really care about is that your scheduler is built to scale"** — yet the plan back-loads scalability validation, weight tunability, and data structure foresight into the final third of implementation. The most time-consuming increment (Increment 7: Solver Research) addresses a concern the assignment never raises.

---

## Critical Issues

### 1. The assignment's primary concern is back-loaded

The assignment dedicates its longest and most emphatic section (paragraphs on lines 81–115) to two things:

- **"The one thing we really care about"** (line 81): The scheduler must handle new weights, rules, and world sizes without rewrites.
- **"Designing your data structure (important)"** (line 96): The data model is the strongest signal of how well you understood the problem. The breadth of anticipated changes is a key evaluation criterion.

The vertical plan scatters this across:
- Increment 8: Future-Ready Extension Slices (second-to-last)
- Increment 9: ARCHITECTURE.md updates (last)
- Increment 7: Solver research (irrelevant to extensibility)

**Problem**: If you wait until increments 7–9 to validate that adding a rule is easy and that the data structure handles anticipated changes, fundamental flaws require rewinding multiple increments. The assignment asks you to *design for this upfront*.

**Recommendation**: Either (a) front-load the data structure design and a "prove we can add a new rule" validation into increments 0–1, or (b) add an explicit checkpoint by increment 3: *"adding a new soft rule requires touching at most two files, one of which is data."*

---

### 2. Weight tunability arrives in increment 5 — too late

The assignment says (line 77):
> "These weights should be tunable — engineers will change them as we learn what matters operationally. **Don't hardcode them.** "

The plan produces four increments of deterministic, weight-unaware schedules before scoring is introduced in Increment 5.

| What | When it happens | Gap |
|---|---|---|
| Weights loaded in scenario data | Increment 1 | Not used by anything |
| Scheduler selects schedules | Increments 2–3 | First-feasible, ignores weights |
| Reporting shows timetable | Increment 2 | No weight display |
| Reporting shows metrics | Increment 3 | No weight display |
| Scenario 4 (operator=2.0) | Increment 6 | Cannot validate weight sensitivity |

**Risk**: A design flaw in weight integration (e.g., wrong Weights object propagation, mismatched scoring function signature) is discovered in the last third of implementation, requiring a refactor across multiple increments.

**Recommendation**: Thread weights through the system from Increment 1 — even if the scheduler uses only trivial/default weighting until Increment 5. Reporting should display loaded weights from Increment 2. Scenario 4 (non-default weights) should be loadable by Increment 2 and scheduleable by Increment 3, even if the weights are not yet *active* in selection.

---

### 3. Solver research (Increment 7) is scope creep

The plan devotes an entire increment with 5 tasks (8.1–8.6) to researching OR-Tools CP-SAT, Z3, and PuLP as alternative solver backends. The assignment never asks for this. It asks for a **working, hosted app** in 3–4 days.

Increment 7 tasks:
- 8.1 Benchmark scenarios and evaluation criteria
- 8.2 Alternate strategies behind the interface
- 8.3 Research OR-Tools CP-SAT formulation
- 8.4 Research Z3 formulation
- 8.5 Research PuLP/MILP formulation
- 8.6 Decide and record solver strategy

The plan's own risk table flags "Formal solver dependency hurts deployment" and "Solver chosen too early." Yet it allocates significant work to building prototype solvers. If the custom baseline works for all 5 scenarios (20 buses, 4 stations — a tiny problem), the research yields zero marginal benefit for the submission.

**Recommendation**: Drop the concrete research tasks entirely. Replace Increment 7 with a single documentation task: *"Document in ARCHITECTURE.md the natural upgrade paths (CP-SAT for global optimization, MILP for linearizable objectives) without building prototypes."* The `SchedulerStrategy` contract already provides the upgrade path in code. Spend saved time on weight tunability, UI polish, or the 5 scenarios.

---

### 4. Only 1 of 5 scenarios exists before Increment 6

| Scenario | What it tests | Available in plan |
|---|---|---|
| 1 (Even spacing, 15 min gaps) | Baseline | Increment 1 |
| 2 (Bunched start, 8 min gaps) | Heavy early contention | Increment 6 |
| 3 (Asymmetric load, 10 BK / 4 KB) | Uneven direction traffic | Increment 6 |
| 4 (Operator-heavy, KPN 8/10 BK, operator=2.0) | Weight sensitivity | Increment 6 |
| 5 (Worst-case, all 20 in 72 min) | Maximum collision at inner stations | Increment 6 |

Scenarios 2 and 5 are the hardest — they create real contention that stress-tests the reservation system and schedule selection logic (Increments 3–4). If the engine is built only against Scenario 1, discovering in Increment 6 that it cannot handle Scenarios 2 or 5 means the core approach may need fundamental changes.

**Recommendation**: Encode all 5 scenarios by Increment 3. They are provided verbatim in the assignment — encoding them is mechanical. Test the scheduler against Scenarios 2 and 5 before proceeding to explainability, invariants, or scoring.

---

### 5. 7 open questions should be decisions

The plan ends with 7 open questions (lines 1877–1886). The assignment explicitly states (line 285):
> "You'll find gaps in this spec — that's intentional. Make your own assumptions, document them, and move forward."

Leaving fundamental design questions open at the planning stage forces ambiguity into every downstream task:

| Open question | Impact of leaving open |
|---|---|
| "Should schedule times be absolute datetimes or minutes-from-start?" | Affects domain models, adapters, reporting, UI — everything. |
| "Should users edit weights interactively?" | Affects UI design and app flow. |
| "Should solver research produce prototypes for all candidates?" | Affects increment scope and dependencies. |

**Recommendation**: Resolve all 7. Example decisions:
- **Time representation**: Minutes-from-start internally for simplicity; convert to absolute for display. (Assignment tables use 24h times, but internal math in minutes avoids timezone/datetime complexity.)
- **Interactive weight editing**: No. The assignment specifies "A dropdown to pick a scenario." Read-only scenario weights; engineer edits via JSON.
- **Solver prototypes**: None. Document upgrade path only.
- **Custom baseline as fallback**: Yes, always. The assignment values explainability.

---

### 6. ARCHITECTURE.md development is back-loaded

The assignment explicitly requires (lines 296–302):
- ARCHITECTURE.md explaining the chosen framework/approach, data structure design, and a list of anticipated future changes
- *"The breadth and quality of this list is one of the strongest signals to us about how you think"*

The plan only updates ARCHITECTURE.md in Increment 9 ("Update architecture docs from implementation reality"). This means:
- The solver decision (Increment 7) is not reflected until delivery.
- The weight integration design (Increment 5) is not captured.
- The "anticipated future changes" list (currently 10 items in ARCHITECTURE.md, which is well-written) is never validated against implementation until the end.

**Recommendation**: Add ARCHITECTURE.md review gates after increments 3, 5, and 7 — or better, keep it evergreen as design decisions are made.

---

### 7. Cross-increment dependencies are contradictory

Several task dependency annotations conflict with the increment ordering:

| Task | Listed in increment | Depends on | Which is in increment |
|---|---|---|---|
| 4.2 Timeline builder | 2 | Task 4.1 | 3 (forward reference — blocks Increment 2) |
| 6.1 Bus timetable rows | 2 | Task 4.4 | 4 (forward reference — blocks Increment 2) |
| 7.3 Render schedule views | 2 | Phase 6, Task 7.1 | 6, 0 (partial) |

The plan mitigates this by using "handcrafted ScheduleResult objects" for reporting before the real scheduler exists — a valid approach. But the dependencies as written are wrong and would mislead a developer or automation agent.

**Recommendation**: Correct the dependency annotations to reflect the handcrafted-fixture decoupling. Separate "code dependencies" from "test/verification dependencies."

---

### 8. Streamlit Cloud deployment validated only at the end

The assignment requires hosting on Streamlit Community Cloud (line 10). The plan's deployment task (10.4) is in Increment 9, the last increment. Any deployment issue (dependency conflicts, missing requirements, large package sizes) is discovered at the last minute.

**Recommendation**: Deploy a stub (even just `app.py` with `st.title(...)`) to Streamlit Community Cloud in Increment 0 or 1. Verify the dependency chain works on the target platform early. This is a 5-minute task.

---

### 9. Travel speed constant is unspecified

The assignment says "use a consistent speed in your simulation — e.g. 60 km/h" (line 46). ARCHITECTURE.md correctly assumes 60 km/h. But the vertical plan never references this. Task 1.3 mentions "configured speed" without specifying the default value or where the constant lives.

**Recommendation**: Add a named constant (e.g., `DEFAULT_SPEED_KMPH = 60` in `src/domain/constants.py`) and reference it in the plan's Task 1.3 scope.

---

### 10. Per-station directional interleaving is unaddressed

The assignment requires a per-station view showing the order in which buses charged there (line 268). Since buses travel both directions and share stations, stations B and C see buses from both directions arriving interleaved. The plan's Task 6.2 covers station queue rows generically, but does not:
- Call out directional interleaving as a specific complexity
- Provide a verification case for it
- Address that Scenario 5 (maximum convergence) stress-tests this specifically

**Recommendation**: Add a note to Task 6.2 that station queue rendering must correctly interleave BK and KB buses, and include a verification step checking this for Scenarios 2 and 5.

---

## Minor Issues

### Infeasibility handling over-engineered (Increment 4)
The plan dedicates a full increment to infeasible schedules and explainability. The assignment problem is designed to be feasible (240 km range, 540 km route, 4 stations). The effort could be better spent on weight tunability, the 5 scenarios, or UI polish.

### Parallelization overstated for 3–4 days
The plan identifies parallel work opportunities, but for a 3–4 day assignment the coordination overhead (branches, merging) likely exceeds the benefit. Single-threaded sequential execution is simpler and faster at this scale.

### Scenario 4 not called out as weight-validation gate
Scenario 4 has `operator=2.0` specifically to test weight sensitivity. The plan does not flag it as the key validation case for Increment 5.

---

## What the plan does well

- **Strategy pattern**: `SchedulerStrategy` protocol is exactly right. Already exists at `src/scheduler/contract.py:37`.
- **Streamlit isolation**: Correctly mandates that `src/scheduler/` never imports Streamlit, and `app.py` owns only composition.
- **TDD discipline**: Red-green-refactor for all behavioral tasks. "Prove-it" pattern for edge cases.
- **Risk awareness**: The risk table (lines 1862–1874) is honest about the biggest dangers (contract churn, tangled constraints/scoring, Streamlit growing logic).
- **Traceability**: Full traceability matrix (lines 1784–1826) from original plan to vertical slices is excellent for maintainability.
- **Incremental testability**: Every increment has a concrete checkpoint with verification steps.

---

## Recommended priority-ordered fixes

| Priority | Issue | Fix |
|---|---|---|
| P0 | Weight tunability arrives in Increment 5 | Thread weights through the system from Increment 1. Validate Scenario 4 by Increment 3. |
| P0 | Only 1/5 scenarios exist before Increment 6 | Encode all 5 by Increment 3. Test against Scenarios 2 and 5 early. |
| P1 | Solver research (Increment 7) is scope creep | Replace with single doc task. Drop OR-Tools/Z3/PuLP prototypes. |
| P1 | Data structure foresight back-loaded to Increments 8–9 | Add a "prove we can add a new rule" check in Increment 3 or 4. |
| P1 | 7 open questions should be decisions | Resolve all 7. Document assumptions. |
| P2 | ARCHITECTURE.md updated only in Increment 9 | Add review gates after increments 3, 5, and 7. Keep it evergreen. |
| P2 | Streamlit Cloud validated only in Increment 9 | Deploy a stub in Increment 0 or 1. |
| P2 | Cross-increment dependency annotations contradict ordering | Correct dependencies to reflect handcrafted-fixture decoupling. |
| P3 | Per-station directional interleaving unaddressed | Add verification step for Scenarios 2 and 5 station views. |
| P3 | Travel speed constant unspecified | Add `DEFAULT_SPEED_KMPH = 60` to domain constants. Reference in Task 1.3. |
