# Implementation Plan: ExpoNow Bus Charging Scheduler

## Overview

This plan turns the architecture in `docs/ARCHITECTURE.md` and `docs/repo_architecture.html` into an ordered, verifiable implementation roadmap for the ExpoNow bus charging scheduler. The application starts as a small Python + Streamlit project, but the intended shape is layered: scenario data enters through adapters, domain objects define the shared language, the scheduler produces a deterministic `ScheduleResult`, reporting converts results into display-ready tables, and Streamlit renders those tables without owning scheduling logic.

**Execution note:** `docs/VERTICAL_IMPLEMENTATION_PLAN.md` is the preferred implementation order. This file remains the detailed task library and dependency reference. When the two documents differ on sequencing, follow the scenario-first vertical roadmap: all five scenarios first, readable UI input next, then feasible scheduling, timetable/station rendering, weighted scoring, extensibility proof, and final delivery.

The plan intentionally keeps the scheduling engine behind a small contract. The first implementation can use a custom deterministic feasibility engine with weighted scoring because it is easy to explain, test, and demo. That baseline should still be implemented as a registered `SchedulerStrategy` from the start, so later research can compare OR-Tools CP-SAT, Z3, PuLP, or hybrid approaches without rewiring reporting or UI code. The current phase should prepare for that decision without prematurely locking the codebase to one solver.

## Planning Principles

- Build bottom-up along the dependency graph: domain -> adapters -> scheduler contract -> scheduler implementation -> reporting -> UI.
- Slice vertically where possible so each phase leaves a runnable, inspectable product.
- Keep hard constraints separate from soft scoring rules. Weights can change preference, but never legal validity.
- Preserve a solver-agnostic boundary: UI and reporting depend on `ScheduleResult`, not on the internal scheduling strategy.
- Treat scheduler engines as registered strategies from the baseline implementation onward, even while only one strategy exists.
- Treat scenario files as the canonical home for changeable world facts: routes, buses, stations, charger policy, and weights.
- Keep tasks small enough to implement and verify in a focused session.

## TDD Driver Rules

Every behavior-changing implementation task follows the red-green-refactor loop:

1. **RED:** Add the smallest behavior-focused test that describes the next expected behavior and confirm it fails for the intended reason.
2. **GREEN:** Implement the minimum production code needed to make that test pass.
3. **REFACTOR:** Clean up names, duplication, boundaries, or data shape while keeping the focused tests green.
4. **VERIFY:** Run the focused test file first, then the broader relevant suite or checkpoint command.

For bug fixes and edge cases, use the prove-it pattern: write the reproduction test first, watch it fail, then fix the code. Manual Streamlit checks are useful runtime verification, but they do not replace automated tests for scheduler, adapter, reporting, or domain behavior. Pure documentation, research, and static content tasks may skip red-green-refactor, but they should say so in the task notes or verification.

Task checklists below intentionally name tests before implementation. Treat the acceptance criteria as the behavior specification, and treat verification commands as proof that the red-green-refactor loop completed.

## Dependency Graph

```text
Project configuration
  |
  +-- Domain models and constants
  |     |
  |     +-- Scenario schema and sample data
  |     |     |
  |     |     +-- Adapter parsing and validation
  |     |           |
  |     |           +-- Scheduler contract
  |     |                 |
  |     |                 +-- Candidate generation
  |     |                 |     |
  |     |                 |     +-- Hard constraints
  |     |                 |           |
  |     |                 |           +-- Station reservation and timeline builder
  |     |                 |                 |
  |     |                 |                 +-- Weighted scoring
  |     |                 |                       |
  |     |                 |                       +-- Reporting tables
  |     |                 |                             |
  |     |                 |                             +-- Streamlit UI
  |     |                                   |
  |     |                                   +-- Solver strategy evaluation, later
  |     |
  |     +-- Tests and fixtures
  |
  +-- Documentation and decision log
```

## Target Architecture

```text
ExpoNow/
  app.py
  data/
    scenarios/
      scenario_1.json
      scenario_2.json
      scenario_3.json
      scenario_4.json
      scenario_5.json
  docs/
    ARCHITECTURE.md
    IMPLEMENTATION_PLAN.md
    DECISION_LOG.md
    LEARNING_LOG.md
    repo_architecture.html
  src/
    adapters/
      errors.py
      scenario_catalog.py
      scenario_loader.py
      scenario_validator.py
    domain/
      __init__.py
      models.py
      route.py
      scenario.py
      time.py
    scheduler/
      __init__.py
      candidates.py
      constraints.py
      contract.py
      reservations.py
      scoring.py
      stub.py
      strategies/
        __init__.py
        custom_heuristic.py
    reporting/
      __init__.py
      metrics.py
      tables.py
    ui/
      __init__.py
      components.py
      layout.py
  tests/
    fixtures/
    test_increment_0_harness.py
    test_increment_1_scenario_data.py
    test_increment_2_domain_and_loader.py
    test_increment_3_validation_and_input_rendering.py
    test_increment_5_timetable_and_queues.py
    test_increment_8_review_ready.py
    test_candidates.py
    test_constraints.py
    test_extensibility.py
    test_scheduler_engine.py
    test_scheduler_invariants.py
    test_scoring.py
```

The exact file names may change if implementation reveals a cleaner local pattern, but the ownership boundaries should remain stable.

## Architecture Decisions To Preserve

- `app.py` owns Streamlit page setup and high-level composition only.
- `src/scheduler/` must not import Streamlit.
- Scheduler implementations must satisfy the shared `SchedulerStrategy` contract and be selected through a registry, not direct UI imports.
- Final schedule invariants must be shared checks that run against any strategy output.
- Scenario loading, defaults, normalization, and validation belong in `src/adapters/`.
- Stable domain nouns belong in `src/domain/`.
- Candidate generation, hard constraints, station reservations, timeline construction, and scoring belong in `src/scheduler/`.
- Display table transformation belongs in `src/reporting/`.
- Streamlit rendering helpers belong in `src/ui/`.
- The scheduler exposes one primary contract: `schedule(scenario: Scenario) -> ScheduleResult`.
- The initial engine should be deterministic so reviewer-visible output is reproducible.
- The solver/framework choice is a future decision and should be isolated behind the scheduler contract.

## Phase 0: Repo Baseline and Working Harness

### Goal

Make the repository ready for iterative Python development without changing scheduler behavior yet.

### Task 0.1: Establish Python package layout

**Description:** Create the source package directories and minimal package initialization so modules can be imported consistently from tests and Streamlit.

**Acceptance criteria:**
- [ ] `src/domain`, `src/adapters`, `src/scheduler`, `src/reporting`, and `src/ui` exist as Python packages.
- [ ] `app.py` can import from `src` without path hacks.
- [ ] Empty placeholder files do not contain behavior beyond package setup.

**TDD note:** This is package scaffolding, not scheduler behavior. Use import smoke checks instead of a red-green-refactor loop.

**Verification:**
- [ ] Run `python -m compileall app.py src`.
- [ ] Run a minimal import smoke test for each package.

**Dependencies:** None

**Files likely touched:**
- `src/domain/__init__.py`
- `src/adapters/__init__.py`
- `src/scheduler/__init__.py`
- `src/reporting/__init__.py`
- `src/ui/__init__.py`
- `app.py`

**Estimated scope:** S

### Task 0.2: Add test tooling and baseline commands

**Description:** Add test dependencies and document the core local verification commands.

**Acceptance criteria:**
- [ ] `pytest` is included in development requirements or `requirements.txt`.
- [ ] A placeholder test proves the test runner works.
- [ ] `docs/README.md` or top-level README lists app, test, and type-check commands.

**TDD note:** This task creates the test harness that later tasks rely on. The placeholder test should be replaced by behavior-focused red tests as soon as Phase 1 starts.

**Verification:**
- [ ] Run `python -m pytest`.
- [ ] Run `streamlit run app.py` manually when UI work begins.

**Dependencies:** Task 0.1

**Files likely touched:**
- `requirements.txt`
- `tests/test_smoke.py`
- `docs/README.md`

**Estimated scope:** S

### Task 0.3: Align documentation structure

**Description:** Reconcile the docs' intended layout with the actual `src/`-based package structure so future agents do not split code between root-level and `src/`-level scheduler folders.

**Acceptance criteria:**
- [ ] Documentation consistently identifies `src/scheduler/` as the scheduler package.
- [ ] Any stale root-level `scheduler/` references are either corrected or explicitly marked historical.
- [ ] `DECISION_LOG.md` records the source layout decision.

**TDD note:** Documentation alignment is a static-content task. Use search and review verification instead of red-green-refactor.

**Verification:**
- [ ] Search docs for conflicting `scheduler/` layout references.
- [ ] Confirm the intended layout in `docs/ARCHITECTURE.md`, `docs/README.md`, and this plan.

**Dependencies:** None

**Files likely touched:**
- `docs/README.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISION_LOG.md`

**Estimated scope:** S

### Checkpoint: Foundation Harness

- [ ] `python -m pytest` passes.
- [ ] `python -m compileall app.py src` passes.
- [ ] Docs agree on the package layout.

## Phase 1: Domain Model and Scenario Data

### Goal

Define the shared vocabulary for buses, stations, routes, scenarios, weights, charging stops, timeline events, and schedule results.

### Task 1.1: Implement domain models

**Description:** Create typed dataclasses and enums for the stable domain nouns described in the architecture.

**Acceptance criteria:**
- [ ] Domain models cover `Route`, `Segment`, `Station`, `Bus`, `Scenario`, `Weights`, `ChargingStop`, `TimelineEvent`, `ChargingPlan`, and `ScheduleResult`.
- [ ] Direction and event type are represented as enums or constrained literals.
- [ ] Configuration-like models are immutable where practical.
- [ ] Constants for default battery range, travel speed, and charging duration have a single source of truth.

**TDD sequence:**
- [ ] RED: Add model-construction tests that fail because the required domain objects and enums do not exist yet.
- [ ] GREEN: Add the smallest dataclasses, enums, and constants needed for those construction tests to pass.
- [ ] REFACTOR: Tighten immutability, naming, and module placement while keeping `tests/test_domain_models.py` green.

**Verification:**
- [ ] Unit tests construct valid model objects.
- [ ] Type checker or compile step catches syntax and import errors.

**Dependencies:** Phase 0

**Files likely touched:**
- `src/domain/models.py`
- `src/domain/route.py`
- `src/domain/time.py`
- `tests/test_domain_models.py`

**Estimated scope:** M

### Task 1.2: Define scenario JSON shape

**Description:** Create scenario files that describe the full input world for each run: route, stations, charger policy, bus departures, and weights.

**Acceptance criteria:**
- [ ] `data/scenarios/` contains the assignment scenarios.
- [ ] Each scenario includes a stable id, name, description, route, stations, buses, charger policy, and weights.
- [ ] Shared constants are either explicit in each scenario or loaded through a clearly documented default.
- [ ] Scenario files use consistent time and station-code formats.

**TDD sequence:**
- [ ] RED: Add fixture/schema tests that fail until the expected scenario files and required keys exist.
- [ ] GREEN: Create the smallest valid scenario JSON set that satisfies the tests.
- [ ] REFACTOR: Remove duplicated fixture details only where readability stays high, then rerun scenario parse tests.

**Verification:**
- [ ] JSON files parse successfully.
- [ ] Each bus references known route endpoints and operators.
- [ ] Manual review confirms the scenario facts match the assignment.

**Dependencies:** Task 1.1

**Files likely touched:**
- `data/scenarios/scenario_1.json`
- `data/scenarios/scenario_2.json`
- `data/scenarios/scenario_3.json`
- `data/scenarios/scenario_4.json`
- `data/scenarios/scenario_5.json`
- `tests/fixtures/`

**Estimated scope:** M

### Task 1.3: Add domain helper functions

**Description:** Add pure helpers for route ordering, travel time derivation, distance between charge points, and direction-aware station traversal.

**Acceptance criteria:**
- [ ] Helpers derive travel minutes from distance and configured speed.
- [ ] Helpers return station order correctly for both Bengaluru-to-Kochi and Kochi-to-Bengaluru directions.
- [ ] Helpers can compute distance since last charge for any candidate stop sequence.

**TDD sequence:**
- [ ] RED: Add route-helper tests for both directions and an endpoint-to-station distance case before creating helper functions.
- [ ] GREEN: Implement only the route/time helpers needed for those tests.
- [ ] REFACTOR: Consolidate shared traversal logic after all route helper tests pass.

**Verification:**
- [ ] Unit tests cover both directions.
- [ ] Unit tests cover endpoint-to-station and station-to-endpoint segments.

**Dependencies:** Task 1.1

**Files likely touched:**
- `src/domain/route.py`
- `src/domain/time.py`
- `tests/test_route_helpers.py`

**Estimated scope:** M

### Checkpoint: Domain and Data

- [ ] Domain models are importable.
- [ ] Scenario JSON exists and parses.
- [ ] Route helper tests pass.
- [ ] No scheduler behavior depends on Streamlit.

## Phase 2: Adapters and Validation

### Goal

Load scenario files into domain objects and reject invalid input before scheduling starts.

### Task 2.1: Implement scenario loader

**Description:** Build a loader that discovers scenario files, parses JSON, applies documented defaults, and returns domain objects.

**Acceptance criteria:**
- [ ] Loader can list available scenarios for the UI dropdown.
- [ ] Loader can load a scenario by id.
- [ ] Loader maps JSON into domain dataclasses without leaking raw dictionaries into scheduler code.
- [ ] Missing optional values receive explicit defaults.

**TDD sequence:**
- [ ] RED: Add loader tests using a minimal fixture that fail because scenario discovery and load-by-id behavior do not exist.
- [ ] GREEN: Implement listing, parsing, defaults, and dataclass mapping in the smallest useful increments.
- [ ] REFACTOR: Separate file access, normalization, and object mapping only after loader tests pass.

**Verification:**
- [ ] Unit tests load every scenario file.
- [ ] Unit tests assert loaded objects match expected ids, bus counts, route stations, and weights.

**Dependencies:** Phase 1

**Files likely touched:**
- `src/adapters/scenario_loader.py`
- `tests/test_scenario_loader.py`

**Estimated scope:** M

### Task 2.2: Implement scenario validation

**Description:** Add validation for malformed world descriptions that would make scheduling impossible or ambiguous.

**Acceptance criteria:**
- [ ] Unknown station codes fail validation.
- [ ] Disconnected route segments fail validation.
- [ ] Negative distances, durations, charger counts, and weights fail validation.
- [ ] Duplicate bus ids fail validation.
- [ ] Bus departures must have parseable timestamps or scenario-local times.
- [ ] Validation errors are human-readable enough for the UI to display.

**TDD sequence:**
- [ ] RED: Add one failing validation test per rule, starting with the smallest malformed fixture.
- [ ] GREEN: Implement each validation rule only after its failing test exists.
- [ ] REFACTOR: Normalize error construction and shared validation helpers while preserving message assertions.

**Verification:**
- [ ] Unit tests cover at least one invalid case per validation rule.
- [ ] Valid assignment scenarios pass validation.

**Dependencies:** Task 2.1

**Files likely touched:**
- `src/adapters/scenario_validator.py`
- `src/adapters/scenario_loader.py`
- `tests/test_scenario_validator.py`

**Estimated scope:** M

### Task 2.3: Add adapter-level error model

**Description:** Create a small exception or result type for loader and validation failures so Streamlit can show friendly errors without catching broad exceptions.

**Acceptance criteria:**
- [ ] Loader errors distinguish missing files, malformed JSON, and validation failures.
- [ ] Error messages include scenario id or file path where useful.
- [ ] Tests assert common errors are surfaced cleanly.

**TDD sequence:**
- [ ] RED: Add failing tests for missing scenario id and malformed JSON error surfaces.
- [ ] GREEN: Add the smallest exception/result type and loader integration needed to pass.
- [ ] REFACTOR: Keep error messages consistent without hiding useful file or scenario context.

**Verification:**
- [ ] Unit tests cover malformed JSON fixture and missing scenario id.
- [ ] Manual check confirms UI can eventually show the message without stack traces.

**Dependencies:** Task 2.2

**Files likely touched:**
- `src/adapters/errors.py`
- `src/adapters/scenario_loader.py`
- `tests/test_scenario_loader.py`

**Estimated scope:** S

### Checkpoint: Data Boundary

- [ ] All valid scenarios load.
- [ ] Invalid scenario fixtures fail before reaching the scheduler.
- [ ] Error messages are suitable for display.

## Phase 3: Scheduler Contract and Hard Constraints

### Goal

Define what every scheduler strategy must accept and return, then implement reusable hard-constraint checks.

### Task 3.1: Define scheduler contract

**Description:** Create the public scheduling strategy protocol and result shape that UI, reporting, tests, and future solver strategies will depend on.

**Acceptance criteria:**
- [ ] `SchedulerStrategy` or equivalent protocol accepts `Scenario` and returns `ScheduleResult`.
- [ ] Strategy registry metadata includes id, label, description, experimental flag, and availability.
- [ ] `ScheduleResult` includes bus plans, station reservations, metrics, warnings, and feasibility status.
- [ ] The contract does not reveal whether the implementation is custom heuristic, CP-SAT, Z3, PuLP, or another solver.
- [ ] Contract supports infeasible results with explainable reasons.

**TDD sequence:**
- [ ] RED: Add a contract smoke test that calls a stub strategy and fails because the contract shape is missing.
- [ ] GREEN: Add the smallest strategy protocol and result fields needed for the stub test.
- [ ] REFACTOR: Move shared result objects into stable domain or contract modules without changing the public call shape.

**Verification:**
- [ ] Contract smoke test calls a stub strategy.
- [ ] Reporting tests can be written against a handcrafted `ScheduleResult`.

**Dependencies:** Phase 1

**Files likely touched:**
- `src/scheduler/contract.py`
- `src/scheduler/registry.py`
- `src/domain/models.py`
- `tests/test_scheduler_contract.py`

**Estimated scope:** M

### Task 3.2: Implement route range constraints

**Description:** Implement pure checks that prove a candidate charging stop sequence keeps the bus within the configured battery range.

**Acceptance criteria:**
- [ ] Range is checked between origin, each charging stop, and destination.
- [ ] Exact-boundary cases are accepted.
- [ ] Over-range cases are rejected with a useful reason.
- [ ] Direction-specific route order is respected.

**TDD sequence:**
- [ ] RED: Add failing tests for feasible, exact-boundary, over-range, and reverse-direction stop sequences.
- [ ] GREEN: Implement the smallest pure range-checking function that makes those tests pass.
- [ ] REFACTOR: Extract route-distance helpers or result reason formatting only after the constraint tests are green.

**Verification:**
- [ ] Unit tests cover feasible, boundary, and infeasible stop sequences.
- [ ] Unit tests cover both directions.

**Dependencies:** Task 1.3, Task 3.1

**Files likely touched:**
- `src/scheduler/constraints.py`
- `tests/test_constraints.py`

**Estimated scope:** M

### Task 3.3: Implement station capacity constraints

**Description:** Implement reusable checks for charger exclusivity and future charger counts.

**Acceptance criteria:**
- [ ] One charger cannot serve overlapping charging intervals.
- [ ] Multiple chargers are supported by capacity count even if current data uses one charger.
- [ ] Fixed 25-minute charging duration is enforced through policy, not duplicated literals.
- [ ] Constraint checks are independent of the scheduling algorithm.

**TDD sequence:**
- [ ] RED: Add failing reservation/constraint tests for overlapping, adjacent, default-capacity, and two-lane intervals.
- [ ] GREEN: Implement only the interval and capacity checks needed for those cases.
- [ ] REFACTOR: Move reusable reservation helpers into `reservations.py` once behavior is protected.

**Verification:**
- [ ] Unit tests cover overlapping reservations, adjacent reservations, and two-lane capacity.
- [ ] Unit tests prove capacity defaults to one charger where omitted.

**Dependencies:** Task 3.1

**Files likely touched:**
- `src/scheduler/constraints.py`
- `src/scheduler/reservations.py`
- `tests/test_constraints.py`
- `tests/test_reservations.py`

**Estimated scope:** M

### Task 3.4: Implement candidate stop generation

**Description:** Generate feasible station stop combinations for each bus before scoring station contention.

**Acceptance criteria:**
- [ ] Candidate generation respects route order.
- [ ] Candidate generation filters candidates that fail battery range.
- [ ] Candidate generation is deterministic.
- [ ] Candidate generation remains small enough for assignment-scale scenarios.

**TDD sequence:**
- [ ] RED: Add failing tests that list expected candidates for a tiny route and exclude endpoint-only charger stops.
- [ ] GREEN: Generate the minimum deterministic candidate set that satisfies range filtering.
- [ ] REFACTOR: Improve enumeration clarity or pruning without changing expected candidate lists.

**Verification:**
- [ ] Unit tests list expected candidates for a simple route.
- [ ] Unit tests confirm candidates do not include endpoint chargers as scheduled stops.

**Dependencies:** Task 3.2

**Files likely touched:**
- `src/scheduler/candidates.py`
- `tests/test_candidates.py`

**Estimated scope:** M

### Checkpoint: Feasibility Core

- [ ] Hard constraint tests pass.
- [ ] Candidate generation tests pass.
- [ ] Scheduler strategy contract is stable enough for reporting and UI to begin.

## Phase 4: Baseline Scheduler Engine

### Goal

Produce a valid deterministic schedule using a custom strategy that is understandable, registered, and replaceable.

### Task 4.1: Build station reservation timeline

**Description:** Create a reservation manager that accepts bus arrivals at stations and allocates charging slots according to charger availability.

**Acceptance criteria:**
- [ ] Given arrival time and station id, reservation manager returns charge start, charge end, and wait time.
- [ ] Adjacent slots do not count as overlapping.
- [ ] Multiple charger lanes can be used when capacity is greater than one.
- [ ] Reservation output can be rendered as station queues.

**TDD sequence:**
- [ ] RED: Add failing tests for an empty station, an occupied station, adjacent slots, multi-lane station, and tie arrivals.
- [ ] GREEN: Implement reservation allocation just enough to satisfy each test in sequence.
- [ ] REFACTOR: Isolate lane selection and sorting after reservation tests pass.

**Verification:**
- [ ] Unit tests cover empty station, occupied station, multi-lane station, and tie arrival times.

**Dependencies:** Task 3.3

**Files likely touched:**
- `src/scheduler/reservations.py`
- `tests/test_reservations.py`

**Estimated scope:** M

### Task 4.2: Implement timeline builder for one bus

**Description:** Convert a bus and chosen stop sequence into ordered timeline events, including travel, waits, and charging stops.

**Acceptance criteria:**
- [ ] Timeline starts at the bus departure and ends at destination arrival.
- [ ] Events are chronological.
- [ ] Charging events include station, start time, end time, and wait time.
- [ ] Travel duration comes from route segment data.

**TDD sequence:**
- [ ] RED: Add failing one-bus timeline tests for no-queue travel, queued charging, and monotonic event times.
- [ ] GREEN: Build the smallest timeline function that emits the expected event sequence.
- [ ] REFACTOR: Separate travel-event construction from charge-event construction after tests pass.

**Verification:**
- [ ] Unit tests build a timeline with no queueing.
- [ ] Unit tests build a timeline with queueing delay.
- [ ] Unit tests verify event times are monotonic.

**Dependencies:** Task 4.1

**Files likely touched:**
- `src/scheduler/engine.py`
- `src/scheduler/reservations.py`
- `tests/test_scheduler_engine.py`

**Estimated scope:** M

### Task 4.3: Implement baseline schedule selection

**Description:** Implement a deterministic baseline strategy that selects feasible candidates and reserves station slots across all buses.

**Acceptance criteria:**
- [ ] Engine returns feasible schedules for valid assignment scenarios where feasible schedules exist.
- [ ] Engine returns infeasible status and reasons when no candidate can satisfy hard constraints.
- [ ] Bus processing order is deterministic and documented.
- [ ] No output violates battery range, route order, or charger capacity.
- [ ] Baseline engine implements `SchedulerStrategy` and is registered as the default strategy.

**TDD sequence:**
- [ ] RED: Add a small feasible scenario test and a small infeasible scenario test before implementing engine selection.
- [ ] GREEN: Implement deterministic candidate selection and station reservation only enough to pass the focused scenarios.
- [ ] REFACTOR: Extract orchestration helpers and strategy wrapper/metadata while invariant tests continue to pass.

**Verification:**
- [ ] Integration tests run the engine against every scenario file.
- [ ] Hard-constraint assertions are applied to the final `ScheduleResult`.
- [ ] Contract tests run against the registered default strategy.

**Dependencies:** Task 3.4, Task 4.2

**Files likely touched:**
- `src/scheduler/engine.py`
- `src/scheduler/contract.py`
- `src/scheduler/registry.py`
- `src/scheduler/strategies/custom_heuristic.py`
- `tests/test_scheduler_engine.py`

**Estimated scope:** M

### Task 4.4: Add explainability metadata

**Description:** Include enough diagnostic detail in schedule output for reviewers to understand why the chosen schedule was selected.

**Acceptance criteria:**
- [ ] Result includes total wait, per-bus wait, per-operator wait, and station utilization metrics.
- [ ] Result includes warnings for bottleneck stations or infeasible candidates.
- [ ] Result can identify which hard constraints were evaluated.

**TDD sequence:**
- [ ] RED: Add failing tests that assert metrics and warnings from a handcrafted schedule result.
- [ ] GREEN: Compute only the required metrics and warning data.
- [ ] REFACTOR: Move metric calculations into named helpers once expected outputs are locked.

**Verification:**
- [ ] Unit tests assert metrics are computed from schedule events.
- [ ] Manual review of a sample schedule is understandable without reading engine internals.

**Dependencies:** Task 4.3

**Files likely touched:**
- `src/scheduler/engine.py`
- `src/domain/models.py`
- `tests/test_scheduler_engine.py`

**Estimated scope:** M

### Checkpoint: First Valid Scheduler

- [ ] Every assignment scenario can be loaded and scheduled or clearly marked infeasible.
- [ ] No final schedule violates hard constraints.
- [ ] Schedule results contain enough metrics for reporting.

## Phase 5: Weighted Scoring and Optimization Behavior

### Goal

Make the baseline engine responsive to individual, operator, and overall weights while keeping hard constraints absolute.

### Task 5.1: Implement scoring functions

**Description:** Add isolated scoring functions for individual wait, operator smoothness, and overall network efficiency.

**Acceptance criteria:**
- [ ] Individual score penalizes high per-bus waiting.
- [ ] Operator score captures fleet-level imbalance or smoothness for each operator.
- [ ] Overall score captures total network wait or total schedule delay.
- [ ] Weighted total score is computed from named components.
- [ ] Score breakdown is included in `ScheduleResult`.

**TDD sequence:**
- [ ] RED: Add failing tests for each score component and weighted total using tiny handcrafted schedules.
- [ ] GREEN: Implement the minimum scoring functions needed for those examples.
- [ ] REFACTOR: Clarify component names and score breakdown structure after `tests/test_scoring.py` passes.

**Verification:**
- [ ] Unit tests cover each scoring component independently.
- [ ] Unit tests confirm changing weights changes total score without changing hard validity.

**Dependencies:** Task 4.4

**Files likely touched:**
- `src/scheduler/scoring.py`
- `src/domain/models.py`
- `tests/test_scoring.py`

**Estimated scope:** M

### Task 5.2: Integrate scoring into candidate choice

**Description:** Use weighted scoring to rank feasible schedule alternatives within the baseline engine.

**Acceptance criteria:**
- [ ] Candidate choice uses score ranking rather than first-feasible selection where alternatives exist.
- [ ] Tie-breaking is deterministic.
- [ ] Schedule result records selected score components.
- [ ] Hard constraints still filter before scoring.

**TDD sequence:**
- [ ] RED: Add a failing test with two feasible candidates where the lower weighted score should win.
- [ ] RED: Add a failing test proving an invalid candidate cannot win even with a favorable score.
- [ ] GREEN: Integrate scoring into candidate choice only far enough to pass both tests.
- [ ] REFACTOR: Extract ranking and tie-break helpers after behavior is protected.

**Verification:**
- [ ] Tests use a small scenario where two candidates are feasible and the lower score is selected.
- [ ] Tests prove an invalid candidate cannot win even with favorable score.

**Dependencies:** Task 5.1

**Files likely touched:**
- `src/scheduler/engine.py`
- `src/scheduler/scoring.py`
- `tests/test_scheduler_engine.py`

**Estimated scope:** M

### Task 5.3: Add scenario weight sensitivity tests

**Description:** Add tests showing that scenario weights affect the output or score in visible, explainable ways.

**Acceptance criteria:**
- [ ] At least one fixture demonstrates individual-heavy behavior.
- [ ] At least one fixture demonstrates operator-heavy behavior.
- [ ] At least one fixture demonstrates overall-network-heavy behavior.
- [ ] Tests assert score or schedule differences, not implementation details.

**TDD sequence:**
- [ ] RED: Add failing sensitivity tests that compare outcomes or score breakdowns under different weights.
- [ ] GREEN: Adjust scoring integration until weight changes produce explainable differences.
- [ ] REFACTOR: Keep fixtures small and named by behavior rather than implementation detail.

**Verification:**
- [ ] Run `python -m pytest tests/test_scoring.py tests/test_scheduler_engine.py`.
- [ ] Manually inspect score breakdown for a weighted scenario.

**Dependencies:** Task 5.2

**Files likely touched:**
- `tests/fixtures/`
- `tests/test_scoring.py`
- `tests/test_scheduler_engine.py`

**Estimated scope:** M

### Checkpoint: Tunable Baseline

- [ ] Weight changes affect ranking predictably.
- [ ] Score breakdown is visible in results.
- [ ] Hard constraints remain non-negotiable.

## Phase 6: Reporting Layer

### Goal

Transform schedule objects into clear tables and metrics that Streamlit can render without knowing scheduling internals.

### Task 6.1: Build bus timetable rows

**Description:** Convert each bus plan into display rows showing departure, station arrivals, charging starts, charging ends, waits, and destination arrival.

**Acceptance criteria:**
- [ ] Rows are stable and sorted by departure time, direction, and bus id.
- [ ] Times are formatted consistently.
- [ ] Wait time and charging duration are visible.
- [ ] Rows can be converted directly to a pandas dataframe if desired.

**TDD sequence:**
- [ ] RED: Add a failing reporting test that compares a handcrafted `ScheduleResult` to expected bus timetable rows.
- [ ] GREEN: Implement the smallest row transformation that passes the expected table.
- [ ] REFACTOR: Extract formatting helpers only after row ordering and values are locked by tests.

**Verification:**
- [ ] Unit tests compare handcrafted schedule result to expected rows.

**Dependencies:** Task 4.4

**Files likely touched:**
- `src/reporting/tables.py`
- `tests/test_reporting.py`

**Estimated scope:** S

### Task 6.2: Build station queue rows

**Description:** Convert station reservations into per-station queue tables.

**Acceptance criteria:**
- [ ] Station rows are grouped by station and sorted by charge start time.
- [ ] Each row includes bus id, operator, arrival time, charge start, charge end, wait, and charger lane if applicable.
- [ ] Empty stations render as empty but valid tables.

**TDD sequence:**
- [ ] RED: Add failing station-queue row tests for multiple reservations and an empty station.
- [ ] GREEN: Implement grouping and sorting only far enough to pass those examples.
- [ ] REFACTOR: Share time formatting with timetable rows after both reporting tests pass.

**Verification:**
- [ ] Unit tests cover one station with multiple reservations and one empty station.

**Dependencies:** Task 4.4

**Files likely touched:**
- `src/reporting/tables.py`
- `tests/test_reporting.py`

**Estimated scope:** S

### Task 6.3: Build summary metrics

**Description:** Create summary cards and warning data for high-level review.

**Acceptance criteria:**
- [ ] Metrics include bus count, station count, total wait, max individual wait, per-operator wait, and bottleneck station.
- [ ] Infeasible schedules provide reasons instead of empty metrics.
- [ ] Warnings remain data objects, not Streamlit calls.

**TDD sequence:**
- [ ] RED: Add failing summary tests for a feasible handcrafted result and an infeasible result with reasons.
- [ ] GREEN: Implement only the metrics and warning data those tests assert.
- [ ] REFACTOR: Keep metric calculations independent from Streamlit and pandas.

**Verification:**
- [ ] Unit tests cover feasible and infeasible result summaries.

**Dependencies:** Task 4.4

**Files likely touched:**
- `src/reporting/metrics.py`
- `tests/test_reporting.py`

**Estimated scope:** S

### Checkpoint: Display Data Ready

- [ ] Reporting tests pass.
- [ ] Reporting output is independent of Streamlit.
- [ ] UI can be built from reporting rows and metrics alone.

## Phase 7: Streamlit Application

### Goal

Create a usable Streamlit app for selecting scenarios, running the scheduler, and inspecting the schedule.

### Task 7.1: Wire scenario selection and run flow

**Description:** Replace the placeholder app with a page that lists scenarios and available scheduler engines, loads the selected scenario, runs the selected strategy, and handles errors gracefully.

**Acceptance criteria:**
- [ ] Scenario dropdown uses the adapter scenario list.
- [ ] Solver engine dropdown uses the scheduler strategy registry and defaults to the custom heuristic.
- [ ] The engine dropdown is present even when only one strategy exists.
- [ ] Selected scenario loads and validates before scheduling.
- [ ] Run flow returns a schedule result or friendly error message.
- [ ] No scheduling logic is implemented in `app.py`.

**TDD sequence:**
- [ ] RED: Add a small app-flow or composition test around the non-Streamlit orchestration seam before wiring the page.
- [ ] GREEN: Implement the minimum orchestration function and Streamlit call site needed for scenario and strategy selection.
- [ ] REFACTOR: Keep scheduling calls out of `app.py` internals and rerun unit tests before manual Streamlit checks.

**Verification:**
- [ ] Manual check in Streamlit: select each scenario and run with the default engine.
- [ ] Existing unit tests still pass.

**Dependencies:** Phase 2, Phase 4

**Files likely touched:**
- `app.py`
- `src/scheduler/registry.py`
- `src/ui/layout.py`
- `src/ui/components.py`

**Estimated scope:** M

### Task 7.2: Render scenario input summary

**Description:** Show the selected scenario's buses, route, station configuration, and weights before or alongside the schedule output.

**Acceptance criteria:**
- [ ] User can inspect bus departures and operators.
- [ ] User can inspect route stations and charger counts.
- [ ] User can inspect current weights.
- [ ] Input display is derived from loaded scenario objects.

**TDD sequence:**
- [ ] RED: Add failing table/summary transformation tests for scenario input display data.
- [ ] GREEN: Implement the reporting or UI data helper needed by the component.
- [ ] REFACTOR: Keep display helpers pure where possible so Streamlit remains a thin renderer.

**Verification:**
- [ ] Manual Streamlit check against scenario JSON.

**Dependencies:** Task 7.1

**Files likely touched:**
- `src/ui/components.py`
- `src/reporting/tables.py`

**Estimated scope:** S

### Task 7.3: Render schedule output views

**Description:** Render bus timetable, station queues, metrics, score breakdown, and warnings.

**Acceptance criteria:**
- [ ] Bus timetable is visible and sortable enough for review.
- [ ] Station queues show serialized charger use.
- [ ] Metrics summarize wait, utilization, and bottlenecks.
- [ ] Score breakdown explains weighted objective result.
- [ ] Infeasible schedules show reasons clearly.

**TDD sequence:**
- [ ] RED: Add failing data-shape tests for the schedule output view inputs, including infeasible result data.
- [ ] GREEN: Wire the UI to existing reporting outputs without adding scheduler logic.
- [ ] REFACTOR: Simplify component boundaries after data-shape tests and reporting tests pass.

**Verification:**
- [ ] Manual Streamlit check for feasible and infeasible fixtures.
- [ ] Confirm no UI text overlaps or unreadable tables in default browser width.

**Dependencies:** Phase 6, Task 7.1

**Files likely touched:**
- `src/ui/components.py`
- `src/ui/layout.py`
- `app.py`

**Estimated scope:** M

### Task 7.4: Add lightweight visual timeline

**Description:** Add a compact visual representation of bus or station timelines if it can be done without overcomplicating the app.

**Acceptance criteria:**
- [ ] Timeline uses schedule result data, not duplicated calculations.
- [ ] Timeline helps inspect charging order or wait time.
- [ ] Table views remain available as the source of detailed truth.

**TDD sequence:**
- [ ] RED: Add a failing pure transformation test for timeline marks derived from a handcrafted schedule result.
- [ ] GREEN: Implement the timeline data transformation before adding visual rendering.
- [ ] REFACTOR: Keep visual code free of duplicated scheduling calculations.

**Verification:**
- [ ] Manual Streamlit check on desktop and narrow viewport.
- [ ] Compare visual timeline against station queue table for one scenario.

**Dependencies:** Task 7.3

**Files likely touched:**
- `src/ui/components.py`
- `src/reporting/tables.py`

**Estimated scope:** S-M

### Checkpoint: Usable App

- [ ] `streamlit run app.py` opens a working app.
- [ ] User can select and schedule all assignment scenarios.
- [ ] UI renders input, schedule, station queues, metrics, score breakdown, and warnings.

## Phase 8: Solver/Framework Research Spike

**Note: This phase is deferred per `docs/VERTICAL_IMPLEMENTATION_PLAN.md`. Solver prototypes are not part of the initial product. The `SchedulerStrategy` contract is ready for upgrade when this decision is revisited. See `docs/SCHEDULER_ENGINE_EVOLUTION.md` for the documented upgrade path.**

### Goal

Evaluate whether the baseline scheduler should remain custom or be replaced/enhanced by a formal optimization framework. This is deliberately separate from the baseline implementation so the repo first has a clear strategy contract, tests, fixtures, and a default registered engine.

### Candidate Approaches

- **Custom deterministic heuristic:** Good explainability and low dependency risk; may miss globally optimal schedules.
- **Custom greedy with backtracking:** More complete than pure greedy; still understandable; can become complex.
- **OR-Tools CP-SAT:** Strong fit for discrete scheduling, capacity constraints, and weighted objectives; additional dependency and modeling effort.
- **Z3:** Strong for satisfiability and constraint reasoning; optimization is possible but may be less natural for scheduling objectives than CP-SAT.
- **PuLP / linear or mixed-integer programming:** Useful if the model becomes linear; discrete route/order choices and interval constraints may require careful formulation.
- **Hybrid approach:** Use custom generation for candidate stop sequences and a solver for station reservation/order optimization.

### Task 8.1: Define benchmark scenarios and evaluation criteria

**Description:** Create a small benchmark suite and rubric for solver comparison.

**Acceptance criteria:**
- [ ] Benchmark scenarios include normal, bunched departure, high contention, infeasible, and multi-charger cases.
- [ ] Evaluation criteria include correctness, objective quality, runtime, explainability, dependency cost, Streamlit deployment compatibility, and implementation complexity.
- [ ] Baseline engine results are recorded for comparison.

**TDD sequence:**
- [ ] RED: Add failing benchmark fixture tests for each named scenario class before using them for solver comparison.
- [ ] GREEN: Create the smallest fixtures and benchmark command that run against the baseline engine.
- [ ] REFACTOR: Keep benchmark setup reusable without hiding what each scenario is proving.

**Verification:**
- [ ] Run benchmark script or test command against baseline engine.
- [ ] Save comparison template in docs.

**Dependencies:** Phase 5

**Files likely touched:**
- `tests/fixtures/`
- `tests/test_scheduler_engine.py`
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`

**Estimated scope:** M

### Task 8.2: Add alternate strategies behind the existing interface

**Description:** Add the first alternate strategy adapter or proof-of-concept wrapper behind the existing `SchedulerStrategy` contract and registry.

**Acceptance criteria:**
- [ ] The existing `SchedulerStrategy` protocol is reused without changing UI or reporting contracts.
- [ ] Baseline custom engine remains registered as the default.
- [ ] Registry can expose more than one strategy by name.
- [ ] App selection works by strategy name and does not import concrete solver classes.
- [ ] Strategy registry metadata includes id, label, description, experimental flag, and availability.

**TDD sequence:**
- [ ] RED: Add failing contract tests that run the same scenario through every registered strategy.
- [ ] GREEN: Register the smallest alternate strategy wrapper or test double that satisfies the existing protocol.
- [ ] REFACTOR: Keep strategy metadata, optional dependency checks, and selection separate from scheduling behavior.

**Verification:**
- [ ] Contract tests run against every registered strategy.
- [ ] No reporting or UI changes are required when swapping strategy.

**Dependencies:** Task 3.1, Phase 5

**Files likely touched:**
- `src/scheduler/contract.py`
- `src/scheduler/registry.py`
- `src/scheduler/strategies/`
- `tests/test_scheduler_contract.py`

**Estimated scope:** M

### Task 8.3: Research OR-Tools CP-SAT formulation

**Description:** Investigate whether CP-SAT can naturally model candidate stop selection, charger interval allocation, wait minimization, and weighted operator/network objectives.

**Acceptance criteria:**
- [ ] Document variables, constraints, and objective formulation.
- [ ] Identify whether optional intervals, no-overlap, and weighted sums fit the problem cleanly.
- [ ] Record dependency and deployment implications for Streamlit.
- [ ] Decide whether to build a proof of concept.

**Verification:**
- [ ] `docs/SCHEDULER_ENGINE_EVOLUTION.md` includes CP-SAT findings.
- [ ] If a proof of concept is built, it passes the strategy contract tests on small fixtures.

**TDD note:** Research-only documentation does not require red-green-refactor. Any runnable proof of concept must start by adding or reusing failing strategy contract tests for the behavior it claims to support.

**Dependencies:** Task 8.1, Task 8.2

**Files likely touched:**
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`
- Optional: `src/scheduler/strategies/cpsat_engine.py`
- Optional: `tests/test_cpsat_engine.py`

**Estimated scope:** M

### Task 8.4: Research Z3 formulation

**Description:** Investigate whether Z3 is useful for feasibility checking, proof-style constraint validation, or full optimization.

**Acceptance criteria:**
- [ ] Document boolean/integer variables and constraint encoding.
- [ ] Identify where optimization objectives become awkward or expressive.
- [ ] Compare explainability and runtime against baseline and CP-SAT.
- [ ] Decide whether Z3 belongs as a full engine, validator, or not at all.

**Verification:**
- [ ] `docs/SCHEDULER_ENGINE_EVOLUTION.md` includes Z3 findings.

**TDD note:** Research-only documentation does not require red-green-refactor. Any runnable proof of concept must start by adding or reusing failing strategy contract tests for the behavior it claims to support.

**Dependencies:** Task 8.1, Task 8.2

**Files likely touched:**
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`
- Optional: `src/scheduler/strategies/z3_engine.py`

**Estimated scope:** S-M

### Task 8.5: Research PuLP or MILP formulation

**Description:** Investigate whether the scheduling problem can be represented as linear or mixed-integer optimization without excessive modeling complexity.

**Acceptance criteria:**
- [ ] Document decision variables and linear constraints.
- [ ] Identify any nonlinear or interval-ordering issues.
- [ ] Compare dependency footprint and solver availability.
- [ ] Decide whether PuLP is a viable option.

**Verification:**
- [ ] `docs/SCHEDULER_ENGINE_EVOLUTION.md` includes PuLP/MILP findings.

**TDD note:** Research-only documentation does not require red-green-refactor. Any runnable proof of concept must start by adding or reusing failing strategy contract tests for the behavior it claims to support.

**Dependencies:** Task 8.1, Task 8.2

**Files likely touched:**
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`
- Optional: `src/scheduler/strategies/milp_engine.py`

**Estimated scope:** S-M

### Task 8.6: Decide and record solver strategy

**Description:** Choose the production/default scheduler strategy based on evidence from benchmarks and prototypes.

**Acceptance criteria:**
- [ ] Decision includes chosen approach, rejected alternatives, and rationale.
- [ ] Decision is recorded in `docs/DECISION_LOG.md`.
- [ ] If a new solver is chosen, migration tasks are created before replacement.
- [ ] Baseline custom engine remains available as fallback and comparison until replacement passes all contract tests and benchmarks.
- [ ] If a new solver becomes the production choice, it is promoted by changing the registry default, not by rewiring app/reporting code.

**TDD note:** The decision record itself is documentation. Any migration task created from the decision must follow the TDD driver rules before replacing the baseline engine.

**Verification:**
- [ ] Human review of `docs/SCHEDULER_ENGINE_EVOLUTION.md` and `docs/DECISION_LOG.md`.
- [ ] Contract tests pass for chosen strategy.

**Dependencies:** Tasks 8.3, 8.4, 8.5

**Files likely touched:**
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`
- `docs/DECISION_LOG.md`
- Optional scheduler strategy files

**Estimated scope:** S

### Checkpoint: Solver Decision

- [ ] Solver decision is evidence-based.
- [ ] Scheduler contract survived at least one alternative strategy review.
- [ ] Any solver dependency is justified by measurable benefit.

## Phase 9: Future-Ready Extensions

### Goal

Add extension points anticipated by the architecture without creating speculative complexity.

### Task 9.1: Generalize charger counts

**Description:** Ensure station capacity is data-driven and multiple chargers work through the same reservation code.

**Acceptance criteria:**
- [ ] `Station.charger_count` or equivalent is read from scenario data.
- [ ] Reservation manager supports multiple lanes.
- [ ] Reporting identifies charger lane when more than one exists.

**TDD sequence:**
- [ ] RED: Add a multi-charger fixture test that fails under single-lane assumptions.
- [ ] GREEN: Thread `charger_count` through loading, reservation, and reporting just enough to pass.
- [ ] REFACTOR: Remove duplicated capacity defaults and keep assignment scenarios unchanged.

**Verification:**
- [ ] Multi-charger fixture passes.
- [ ] Station queue output remains readable.

**Dependencies:** Phase 4

**Files likely touched:**
- `src/domain/models.py`
- `src/adapters/scenario_loader.py`
- `src/scheduler/reservations.py`
- `src/reporting/tables.py`
- `tests/fixtures/`

**Estimated scope:** M

### Task 9.2: Add station availability windows

**Description:** Support future charger outages or maintenance windows as hard constraints.

**Acceptance criteria:**
- [ ] Scenario data can express station or charger unavailable windows.
- [ ] Validation rejects malformed windows.
- [ ] Scheduler does not allocate charging during unavailable windows.
- [ ] UI/reporting can show availability warnings.

**TDD sequence:**
- [ ] RED: Add failing validation and scheduling tests for an outage window fixture.
- [ ] GREEN: Add availability-window parsing, validation, and reservation avoidance only as needed.
- [ ] REFACTOR: Keep outage logic as a hard constraint independent of scoring.

**Verification:**
- [ ] Fixture with outage shifts charging to another valid time or station.
- [ ] Infeasible outage case returns clear reasons.

**Dependencies:** Phase 4

**Files likely touched:**
- `src/domain/models.py`
- `src/adapters/scenario_validator.py`
- `src/scheduler/constraints.py`
- `src/scheduler/reservations.py`
- `tests/fixtures/`

**Estimated scope:** M

### Task 9.3: Add new soft rule plug-in pattern

**Description:** Make scoring rules extensible without rewriting the engine for each new policy.

**Acceptance criteria:**
- [ ] Scoring functions are named components.
- [ ] Adding a new score component requires minimal changes.
- [ ] Weights can include future optional components with defaults.
- [ ] Score breakdown reports every active component.

**TDD sequence:**
- [ ] RED: Add a failing test-only score component test that proves a new component participates in total score and breakdown.
- [ ] GREEN: Introduce the smallest scoring registry or composition pattern needed for that test.
- [ ] REFACTOR: Preserve simple direct scoring calls for current built-in components.

**Verification:**
- [ ] Add a tiny test-only scoring component and prove it participates in total score.

**Dependencies:** Phase 5

**Files likely touched:**
- `src/scheduler/scoring.py`
- `src/domain/models.py`
- `tests/test_scoring.py`

**Estimated scope:** S-M

### Task 9.4: Add variable charging policy

**Description:** Replace fixed charging duration and range constants with policy lookups while preserving current defaults.

**Acceptance criteria:**
- [ ] Scenario or bus type can define battery range and charge duration.
- [ ] Default remains 240 km range and 25 minute charge.
- [ ] Hard constraints use policy values instead of literals.
- [ ] Reporting shows the applied policy when it varies.

**TDD sequence:**
- [ ] RED: Add failing policy tests for non-default charge duration and default assignment behavior.
- [ ] GREEN: Add policy lookups only where constraints, reservations, and reporting need them.
- [ ] REFACTOR: Centralize default policy values after existing and non-default fixtures pass.

**Verification:**
- [ ] Fixture with non-default charging duration produces expected reservation length.
- [ ] Existing assignment scenarios remain unchanged.

**Dependencies:** Phase 4

**Files likely touched:**
- `src/domain/models.py`
- `src/adapters/scenario_loader.py`
- `src/scheduler/constraints.py`
- `src/scheduler/reservations.py`
- `src/reporting/tables.py`

**Estimated scope:** M

### Checkpoint: Extension Confidence

- [ ] Multiple chargers work.
- [ ] At least one new hard constraint can be added cleanly.
- [ ] At least one new soft rule can be added cleanly.
- [ ] Defaults preserve original assignment behavior.

## Phase 10: Quality, Documentation, and Delivery

### Goal

Prepare the project for review, handoff, and deployment.

### Task 10.1: Strengthen invariant tests

**Description:** Add tests that verify final schedules never violate the important invariants, independent of implementation strategy.

**Acceptance criteria:**
- [ ] Every final schedule is checked for range validity.
- [ ] Every final schedule is checked for station capacity validity.
- [ ] Every final schedule is checked for route ordering.
- [ ] Invariant helper tests can run against any scheduler strategy.

**TDD sequence:**
- [ ] RED: Add invariant tests around a deliberately invalid handcrafted schedule to prove the helpers catch violations.
- [ ] GREEN: Implement invariant helpers and wire them against scheduler outputs.
- [ ] REFACTOR: Make helpers strategy-agnostic and reusable by solver prototypes.

**Verification:**
- [ ] Run complete test suite.
- [ ] Run invariant tests against every assignment scenario.

**Dependencies:** Phase 4

**Files likely touched:**
- `tests/test_scheduler_invariants.py`
- `tests/helpers.py`

**Estimated scope:** M

### Task 10.2: Add edge case fixtures

**Description:** Add small fixtures for boundary and failure cases that are easy to reason about.

**Acceptance criteria:**
- [ ] Fixture covers exactly-at-range route.
- [ ] Fixture covers impossible range.
- [ ] Fixture covers simultaneous station arrivals.
- [ ] Fixture covers multiple operators.
- [ ] Fixture covers infeasible charger outage if outages are implemented.

**TDD sequence:**
- [ ] RED: Add one failing test per edge fixture that names the expected scheduler behavior.
- [ ] GREEN: Add the smallest fixture data and implementation adjustment needed for each behavior.
- [ ] REFACTOR: Keep fixtures tiny and behavior-labeled so failures are easy to diagnose.

**Verification:**
- [ ] Fixture tests pass.
- [ ] Fixture names make the intended behavior obvious.

**Dependencies:** Phase 4

**Files likely touched:**
- `tests/fixtures/`
- `tests/test_scheduler_engine.py`
- `tests/test_scheduler_invariants.py`

**Estimated scope:** M

### Task 10.3: Update architecture docs from implementation reality

**Description:** Keep architecture documentation accurate after implementation choices have been made.

**Acceptance criteria:**
- [ ] `docs/ARCHITECTURE.md` reflects actual module names and contracts.
- [ ] `docs/repo_architecture.html` remains accurate or is marked as conceptual.
- [ ] `docs/DECISION_LOG.md` records major implementation decisions.
- [ ] Solver evaluation status is referenced from architecture docs.

**TDD note:** Documentation updates do not require red-green-refactor. If docs reveal missing behavior, create a separate behavior task with a failing test first.

**Verification:**
- [ ] Search docs for stale module names.
- [ ] Manual read-through confirms docs and repo agree.

**Dependencies:** Phases 7 and 8

**Files likely touched:**
- `docs/ARCHITECTURE.md`
- `docs/repo_architecture.html`
- `docs/DECISION_LOG.md`
- `docs/SCHEDULER_ENGINE_EVOLUTION.md`

**Estimated scope:** M

### Task 10.4: Prepare deployment instructions

**Description:** Document local run, test, and Streamlit deployment steps.

**Acceptance criteria:**
- [ ] README includes install, run, test, and troubleshooting commands.
- [ ] Requirements include only needed runtime dependencies.
- [ ] Optional solver dependencies are clearly separated if used.
- [ ] Streamlit Community Cloud setup is documented if deployment is needed.

**TDD note:** Deployment instructions are documentation/configuration. Verify commands in a fresh environment where practical; do not add behavior without a failing test.

**Verification:**
- [ ] Fresh environment install command succeeds.
- [ ] `streamlit run app.py` works from repository root.

**Dependencies:** Phase 7

**Files likely touched:**
- `docs/README.md`
- `requirements.txt`
- Optional: `requirements-dev.txt`
- Optional: `requirements-solver.txt`

**Estimated scope:** S

### Checkpoint: Review Ready

- [ ] Full test suite passes.
- [ ] App runs locally.
- [ ] Docs match implementation.
- [ ] Solver decision is either completed or explicitly deferred with a documented path.

## Parallelization Opportunities

### Safe To Parallelize

- Domain model tests and scenario JSON drafting after model shape is agreed.
- Reporting layer tests using handcrafted `ScheduleResult` fixtures while scheduler engine is still being implemented.
- Streamlit UI layout sketches after reporting output shape is stable.
- Documentation updates that do not depend on unsettled solver decisions.
- Solver research branches after the scheduler strategy contract exists.

### Must Stay Sequential

- Domain model shape before adapter parsing.
- Adapter validation before scheduler consumes scenario data.
- Scheduler contract before reporting and UI depend on schedule results.
- Hard constraints before weighted scoring can safely choose between candidates.
- Benchmark criteria before solver/framework comparison.

### Needs Coordination

- Any change to `ScheduleResult` affects scheduler, reporting, UI, and tests.
- Any change to scenario JSON schema affects adapters, fixtures, docs, and UI input summary.
- Any solver dependency affects requirements, deployment, and documentation.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scheduler contract changes repeatedly | High | Define contract early with handcrafted result fixtures before UI work. |
| Custom baseline becomes too complex | Medium | Keep it behind strategy interface and move solver research into Phase 8. |
| Solver chosen too early | Medium | Defer OR-Tools/Z3/PuLP decision until benchmark fixtures and objective criteria exist. |
| Hard constraints and scoring become tangled | High | Keep `constraints.py` pure and ensure invalid candidates never reach scoring. |
| Scenario schema drifts from docs | Medium | Add loader tests for every scenario and update docs during delivery phase. |
| Streamlit grows business logic | High | Keep UI limited to adapter calls, scheduler invocation, and reporting render functions. |
| Weighted objective is hard to explain | Medium | Always expose score component breakdown in `ScheduleResult` and UI. |
| Multiple charger support is bolted on later | Medium | Design station reservations around capacity from the start, defaulting to one. |
| Formal solver dependency hurts deployment | Medium | Evaluate Streamlit deploy compatibility before adopting any solver as default. |
| Infeasible scenarios fail unclearly | Medium | Represent infeasible results explicitly with reasons and tested UI handling. |

## Resolved Planning Decisions

These decisions are fixed by the scenario-first vertical roadmap in `docs/VERTICAL_IMPLEMENTATION_PLAN.md`:

- The five schedules in `docs/Bus_Charging_Scheduler_Assignment.md` are the canonical scenario facts.
- The initial engine uses a custom deterministic heuristic with hard-constraint validation before weighted selection.
- Operator smoothness starts as operator wait/delay balance and is shown in score breakdown.
- Internal schedule math uses scenario-local minutes from the service day start; UI/reporting display `HH:MM`.
- Streamlit does not edit weights in v1; weights are read from scenario data and displayed.
- Formal solver prototypes are deferred from the initial product; document upgrade paths only.
- The custom baseline remains the default and fallback behind `SchedulerStrategy`.

## Definition of Done For Initial Product

- [ ] Valid scenario data lives in `data/scenarios/`.
- [ ] Scenario loader and validator reject malformed input before scheduling.
- [ ] Scheduler produces a deterministic `ScheduleResult` through a stable contract.
- [ ] Final schedules satisfy range, route order, and charger capacity constraints.
- [ ] Weighted scoring includes individual, operator, and overall components.
- [ ] Reporting produces bus timetable, station queue, metrics, warnings, and score breakdown data.
- [ ] Streamlit app lets a user select a scenario and inspect results.
- [ ] Tests cover domain helpers, adapters, constraints, engine behavior, scoring, reporting, and final invariants.
- [ ] Every behavior-changing task has an automated test that was observed failing before implementation and passing after.
- [ ] No tests are skipped or weakened to make the suite pass.
- [ ] Docs explain how to run, test, change weights, add rules, and evaluate solver alternatives.

## Suggested Implementation Order Summary

1. Phase 0: Repo baseline and testing harness.
2. Phase 1: Domain models and scenario data.
3. Phase 2: Scenario loader and validation.
4. Phase 3: Scheduler contract and hard constraints.
5. Phase 4: Baseline deterministic scheduler.
6. Phase 5: Weighted scoring.
7. Phase 6: Reporting layer.
8. Phase 7: Streamlit app.
9. Phase 8: Solver/framework research and strategy decision.
10. Phase 9: Future-ready extensions.
11. Phase 10: Quality, docs, and delivery.

This order gives the project an explainable working scheduler before solver research, while ensuring the later solver decision has the contract, fixtures, benchmarks, and acceptance criteria needed to be made responsibly.
