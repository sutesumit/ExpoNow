# Decision Log

## 2026-05-29: Created ExpoNow directory

Created an empty `ExpoNow/` directory at the project root to serve as the application directory for the new project.

## 2026-05-30: Minimal Streamlit app scaffold

Bootstrapped a minimal Streamlit application in `app.py` with:
- `st.set_page_config(page_title="ExpoNow")` — sets the browser tab title
- `st.title("ExpoNow")` — renders the main page heading

Streamlit is set up locally and the app can be launched with `streamlit run app.py`.

## 2026-05-30: Deployed to Streamlit Community Cloud

The app is deployed to Streamlit Community Cloud and available at https://exponow.streamlit.app/.

## 2026-05-30: CI/CD Validated

CI/CD pipeline validated: all live changes pushed to `main` are directly reflected on Streamlit Community Cloud.

## 2026-05-30: Repo architecture established

Established the full repository architecture as documented in `docs/ARCHITECTURE.md` and `docs/repo_architecture.html`. The project follows a modular structure with separation of concerns:

- **`app.py`** — thin Streamlit UI entry point (scenario selector, input display, bus timetables, station views)
- **`src/`** — core application package split into `domain/` (dataclasses: Route, Bus, Scenario, ChargingPlan, etc.), `adapters/` (loading, parsing, defaults, normalization, and validation), `scheduler/` (hard constraints, soft scoring, and timeline building), `reporting/` (display-friendly tables), and `ui/` (Streamlit helpers)
- **`data/scenarios/`** — JSON scenario definitions (routes, buses, weights, and future scenario-level metadata) covering 5 scenarios
- **`docs/`** — design documentation: `ARCHITECTURE.md` (framework rationale, data structures, extensibility for anticipated changes), `DECISION_LOG.md`, `LEARNING_LOG.md`, and the visual architecture diagram `repo_architecture.html`

The chosen approach is **constraint-based optimization with weighted scoring** — balancing three competing soft rules (individual wait time, operator smoothness, overall efficiency) under hard constraints (range limits, single charger per station, route ordering). This was chosen over simulation, genetic algorithms, and linear programming for its determinism, explainability, and ease of adding new rules.

## 2026-05-30: Scheduler engine evolution strategy

**Decision:** Use the strategy pattern (`SchedulerStrategy` protocol) for the scheduler engine, deferring the UI dropdown until ≥2 production-ready strategies exist.

**Context:** We considered two paths for integrating future constraint solvers — replacing the custom engine in-place vs. supporting multiple swappable engines. The strategy pattern was chosen because it enables solver comparison, benchmarking, contract testing, and fallback at near-zero UI cost. The dropdown is intentionally deferred to avoid speculative complexity.

**See:** `docs/SCHEDULER_ENGINE_EVOLUTION.md` for full rationale, phased path, and design constraints.

## 2026-05-30: Implementation plan created

Created `docs/IMPLEMENTATION_PLAN.md` — a detailed, ordered implementation roadmap that follows the dependency graph (domain → adapters → scheduler → reporting → UI). It establishes planning principles (bottom-up builds, vertical slicing, hard/soft rule separation, solver-agnostic boundary), TDD driver rules (red-green-refactor), and defines the full task breakdown across all phases.

## 2026-05-30: Vertical implementation plan created

Created `docs/VERTICAL_IMPLEMENTATION_PLAN.md` as a vertical-slice companion to the original implementation plan. The original plan (`IMPLEMENTATION_PLAN.md`) remains the source-of-truth detail library; this document reorganizes the same work into thin, runnable, testable increments so implementation can proceed end-to-end from the start. Early increments use stubs and handcrafted `ScheduleResult` objects to enable end-to-end testability before every layer is complete, and each increment must leave the repository runnable and compilable.

## 2026-05-30: Scenario-first vertical roadmap adopted

Updated `docs/VERTICAL_IMPLEMENTATION_PLAN.md` to make the assignment demo path the preferred implementation order: list and encode all five scenarios early, render scenario inputs in Streamlit before deep scheduler work, then add feasible scheduling, timetable/station outputs, weighted scoring, and a small extensibility proof.

The earlier layer-first `docs/IMPLEMENTATION_PLAN.md` remains useful as the detailed task library, but it is no longer the preferred execution sequence. Runnable formal solver prototypes (OR-Tools, Z3, PuLP, MILP) are deferred from the initial product; the custom deterministic scheduler remains the default behind `SchedulerStrategy`, with formal solvers documented only as future upgrade paths.

## 2026-05-30: Increment 0 — App shell with ports-and-adapters architecture

**Decision:** Implement a full app shell (Increment 0) using frozen dataclasses, a ports-and-adapters package structure, a stub scheduler, and a view model orchestration layer — all before any real scheduling logic.

**Context & Rationale:**

- **Frozen dataclasses** (`ScenarioSummary`, `ScheduleResult`, `InitialViewModel`) — immutability guarantees value semantics across layer boundaries; prevents accidental mutation bugs as the codebase grows.
- **Ports-and-adapters layering** — `domain/` owns pure business concepts with zero infrastructure imports; `adapters/` handles data loading; `scheduler/` implements the scheduling strategy protocol; `ui/` renders Streamlit; `reporting/` formats output. Dependencies point inward (UI → domain, never domain → UI).
- **`SchedulerStrategy` protocol** in `scheduler/contract.py` — structural interface that lets any solver (deterministic, OR-Tools, Z3, etc.) be plugged in without changing callers, enabling A/B comparison and benchmarking.
- **Stub scheduler** — returns `feasible=True` with a placeholder warning; lets the full UI, orchestration, and test harness run end-to-end from Increment 0 without a real solver.
- **View model orchestration** (`build_initial_view_model`) — keeps `app.py` to a thin 3-line `main()`; all wiring lives in a testable function with no Streamlit dependency.
- **Scheduler must not import Streamlit** — architectural boundary enforced by a test (`test_scheduler_package_does_not_import_streamlit`). This prevents accidental coupling and keeps the scheduler layer reusable outside Streamlit (e.g., CLI, API).
- **Test harness** (`test_increment_0_harness.py`) — 6 tests covering: catalog shape, stub contract compliance, orchestration with explicit and default scenario selection, Streamlit-free scheduler enforcement, and import-time side-effect safety.

**Achievements:**
- App launches on Streamlit Cloud with a scenario dropdown and placeholder detail views
- 6 passing tests enforcing contract shape and architectural layering
- Clean package structure ready for real scheduling logic in Increment 1
- `docs/` fully established with architecture docs, decision log, learning log, implementation plans, and visual diagrams

## 2026-05-30: Scenario JSON data structure shape

**Decision:** Encode each assignment scenario as a self-contained JSON file under `data/scenarios/` with a schema that separates physical-world facts (`route`, `stations`, `charging_policy`, `travel_policy`) from the dynamic fleet schedule (`buses`) from tunable optimization knobs (`weights`).

**Context & Rationale:**

- **JSON over Python dicts** — scenario data lives in flat files where non-developers can edit it, version control tracks changes, and the scheduler reads it without a code rebuild. Avoids the anti-pattern of hardcoding data inside `src/adapters/scenario_catalog.py`.

- **Three independent axes of change** — the schema is split so a change in one axis never cascades into another:
  - *Physical world* (`route`, `stations`, `charging_policy`, `travel_policy`) — changes when the route gains a stop, a station gets a second charger, or battery range improves.
  - *Fleet schedule* (`buses`) — the dynamic input unique to each scenario. Adding a scenario means adding a file; the schema never changes.
  - *Optimization weights* (`weights`) — tunable knobs visible at a glance. Scenario 4 overrides `operator` to 2.0 by changing a single number.

- **Key design choices:**
  - `schema_version` — enables backward-compatible schema migrations without breaking existing scenarios.
  - Segments as `{from, to, distance_km}` objects — route order is derived from sequence, not hardcoded indices. Inserting or removing a segment is a data edit.
  - `stations` as objects with `charger_count` — the field already exists at default 1, so multi-charger stations require no schema change.
  - `weights` as a named-key object — adding a new optimization dimension (e.g. `"peak_hour_penalty"`) means adding a key with a default, touching neither fleet schedule nor physical world.
  - Operator as a free-text string — no enum, no registry, no migration. New operators appear in data alone.
  - Direction as `"Bengaluru->Kochi"` / `"Kochi->Bengaluru"` — mirrors route stop names so traversal can derive ordered stop lists without a separate enum.

- **Tests validate the shape** — `tests/test_increment_1_scenario_data.py` (7 tests) proves every file exists, contains all required keys, matches assignment-spec bus counts, has the correct operator weight override in scenario 4, fits scenario 5's 72-minute departure window, and matches all station/policy/segment defaults.

**See:** `docs/repo_architecture.html` — "Scenario Data: Shape, Rationale, and Test Coverage" chapter for full visual diagrams and future-change mapping matrix.

## 2026-05-30: Increment 2 — Domain models, file-backed loader, and weight threading

**Decision:** Replace hardcoded placeholder data with fully typed domain objects, a file-based scenario loader, and a stub scheduler that threads real weights from JSON files into `ScoreBreakdown`.

**Context & Rationale:**

- **Domain models** (`Segment`, `Route`, `Station`, `Bus`, `ChargingPolicy`, `TravelPolicy`, `Weights`, `Scenario`) — all frozen dataclasses in `src/domain/models.py`. Every noun from the JSON schema has a typed, immutable counterpart. No raw `dict` escapes `scenario_loader.py`, keeping the scheduler layer type-safe.

- **Time helpers** (`parse_hhmm`, `format_minutes`) — pure functions with no project dependencies. Loader validation depends on them. They live in `src/domain/time.py` as the foundation layer.

- **Route helpers** (`get_ordered_stops`, `total_distance`, `distance_between`) — direction-aware stop ordering. Accepts `Route` and direction string (`"Bengaluru->Kochi"`) and returns stops in traversal order. Distance is computed by summing segment distances between the two stops. Rejects stations not on route.

- **Anchored path over CWD-relative** — `SCENARIO_DIR` resolves via `Path(__file__).resolve().parents[2] / "data" / "scenarios"` instead of `Path("data/scenarios")`. This ensures the loader works regardless of the current working directory, at the cost of a fragile `parents[2]` if the file moves.

- **Loader security** — `load_scenario(scenario_id)` first validates the id against `discover_scenario_ids()`, which globs `data/scenarios/scenario_*.json`. This prevents path traversal attacks where a crafted id like `../../etc/passwd` could read arbitrary files. If the id isn't in the discovered list, `ScenarioNotFoundError` is raised before any file path is constructed.

- **Contract types** — `BusPlan`, `ChargingStop`, `StationReservation`, `TimelineEvent`, `ScheduleMetrics`, and `ScoreBreakdown` are all frozen dataclasses in `src/scheduler/contract.py`. `ScheduleResult` fields changed from `list[Any]` / `dict[str, Any]` to typed lists and `ScheduleMetrics | None` / `ScoreBreakdown | None`. `SchedulerStrategy.schedule()` now accepts `Scenario` instead of `ScenarioSummary`.

- **Weight threading** — `StubSchedulerStrategy.schedule(scenario)` populates `ScoreBreakdown(components={"weights": scenario.weights})`, putting real data into `ScheduleResult` for display before scoring exists. This verifies the pipeline end-to-end.

- **Catalog update** — `list_scenario_summaries()` now calls `load_scenario()` internally and returns `ScenarioSummary(is_placeholder=False)` with real names and descriptions. Catalogue performance is acceptable since each JSON file is <5 KB and there are only 5 files.

- **Architecture rules enforced:**
  - `src/domain/` imports nothing from the project.
  - `src/adapters/` imports only from `src.domain` and stdlib.
  - `src/scheduler/` imports from `src.domain.models`, never from adapters.
  - `src/ui/layout.py` imports streamlit only inside function bodies.

**Achievements:**
- 6 new files created, 8 files modified
- 44 new focused tests (57 total across all increments) — all pass
- `python -m compileall app.py src` passes clean
- Full test suite runs in under 100 ms
- Weights from all 5 scenarios travel from JSON → typed `Scenario` → `ScoreBreakdown` → UI display
- Route helpers and time helpers are pure, independently testable functions
- Loader path-traversal prevented by discover-then-load pattern
- Architecture documented in `docs/repo_architecture.html` — new "Increment 2" chapter with 8 visual sections

**See:** `docs/VERTICAL_IMPLEMENTATION_PLAN.md` — Increment 2 section (marked done). `docs/repo_architecture.html` — "Increment 2 — Typed Domain Models, File Loader, and Weight Threading" chapter.

## 2026-05-31: Increment 4 — Feasible Baseline Scheduler

**Decision:** Replace the stub scheduler with a deterministic greedy heuristic that generates feasible, hard-valid schedules for all five assignment scenarios. The scheduler core is split into four independently testable modules: `candidates.py`, `constraints.py`, `reservations.py`, and `strategies/custom_heuristic.py`.

**Context & Rationale:**

- **Candidate generation** (`candidates.py`) — enumerates all non-empty subsets of intermediate stations (max 16 per bus) that respect battery range. Pure functions with zero state, using `route.distance_between()` for all gap checks.

- **Range/route-order constraints** (`constraints.py`) — pure validation functions plus `validate_schedule_invariants()` which performs a full-schedule self-check: range gaps, route order, charge duration, chronological events, and non-overlapping reservations. Called automatically as a self-check before returning.

- **Reservation manager** (`reservations.py`) — mutable per-station lane tracker using `_LaneSchedule` dataclass. `request()` implements first-available-lane-fit: scans each lane for the earliest gap at or after arrival that fits the charge duration. Outputs frozen `StationReservation` objects for the final result.

- **Custom heuristic** (`strategies/custom_heuristic.py`) — deterministic greedy algorithm: sort buses by departure then ID, pick first feasible candidate, reserve each station, build timeline with travel/wait/charge events, then self-validate via invariants. ~120 lines.

- **Results** — all 5 scenarios produce feasible schedules with 0 invariant violations. Scenario 5 (worst-case 72-min convergence) has highest contention: 1530 min total wait, 153 min max wait. All 103 tests pass in ~100ms.

- **Stub retained** — `StubSchedulerStrategy` remains importable and tested. `app_view_model.py` now defaults to `CustomHeuristicStrategy`.

**See:** `docs/repo_architecture.html` — "Increment 4 — Feasible Baseline Scheduler" chapter with 11 sections including architecture overview, algorithm flow, candidate/reservation visualizations, and ownership model.

## 2026-05-31: Increment 3 — Scenario validation and input rendering

**Decision:** Add a scenario validator, reporting tables module, and UI components module to enable full scenario input display before scheduling, with graceful error handling when validation fails.

**Context & Rationale:**

- **Validator in `src/adapters/scenario_validator.py`** — validates metadata (schema version, id, name, description), route structure (stops begin/end at terminals, segments connect in order, positive distances, no gaps), station coverage (every non-terminal stop exists in station list with segment start/end coverage), station charger count (positive), policy values (positive range/charge time/speed), weights (non-negative), bus IDs (no duplicates), and directions (must be `Bengaluru->Kochi` or `Kochi->Bengaluru`). Returns a list of error strings; empty list means valid.

- **Validation in the orchestration layer** — `build_initial_view_model()` calls `validate_scenario()` after loading. If errors are returned, a minimal `ScheduleResult(feasible=False)` is created and the scheduler is skipped entirely. The errors are threaded through `InitialViewModel.validation_errors` to the UI.

- **Reporting tables in `src/reporting/tables.py`** — pure functions that transform `Scenario` domain objects into lists of dicts or Graphviz DOT strings. No Streamlit dependency, keeping the layer reusable outside the UI.

- **UI components in `src/ui/components.py`** — one Streamlit rendering function per visual section (summary table, route diagram, route/station/policy/weight tables, bus departures, validation errors). Streamlit is imported only inside function bodies following the existing `layout.py` pattern.

- **App flow restructured** — `app.py` now calls `render_input_view(view_model)` first, which either shows validation errors or the full scenario input (route diagram, station/policy/weight tables, bus departures collapsed under an expander). `render_initial_view()` (schedule results) is only called when there are no validation errors.

- **Architecture boundary enforced** — test `test_reporting_package_does_not_import_streamlit` ensures `src/reporting/` stays free of Streamlit imports, keeping it usable from CLI or API contexts.

- **Test coverage** — 11 tests added covering: validator acceptance of all 5 assignment scenarios, rejection of duplicates, invalid directions, negative distances, disconnected segments, zero chargers, negative weights, non-positive policy values, reporting table shape, scenario 4 weight override display, scenario 5 departure window, and the Streamlit-free reporting boundary.

**Achievements:**
- 4 new files, 3 files modified
- 11 new tests (68 total across all increments)
- Full scenario input displayed in Streamlit: route diagram, stations, policies, weights, bus departures
- Validation errors shown before any scheduling attempt
- `src/reporting/` verifiably Streamlit-free
- All 5 assignment scenarios pass validation without errors

**See:** `docs/repo_architecture.html` — "Increment 3 — Scenario Validation and Input Rendering" chapter.

## 2026-05-31: Increment 5 — Timetable & Station Queue Rendering

**Decision:** Build reporting tables from `ScheduleResult` (not from scheduler internals), sort station queues chronologically by charge start → lane → bus id, and handle infeasible results gracefully with friendly messages.

**Context & Rationale:**

- **Reporting tables** (`src/reporting/tables.py`) — `build_bus_timetable_rows()` (11 columns, sorted by departure→bus_id) and `build_station_queue_rows()` (grouped by station, sorted by charge_start→lane→bus_id, interleaving both directions). Pure functions accepting `ScheduleResult` — keeps reporting Streamlit-free and reusable.
- **Station queue sort order** — entries sorted by charge start time, then charger lane, then bus ID. This makes the queue view predictable and debuggable.
- **Infeasible results** — `build_bus_timetable_rows` returns `[]` and `build_station_queue_rows` returns `{}` when `result.feasible` is `False`, allowing the UI to display "No feasible schedule" without crashes.
- **UI components** — added 4 rendering functions (`render_bus_timetable`, `render_station_queues`, `render_schedule_metrics`, `render_infeasible_message`) in `src/ui/components.py`; `render_schedule_output()` in `src/ui/layout.py` gates on feasibility then renders metrics→timetable→queues.
- **Time domain fix** — removed `minutes > 1439` upper bound in `src/domain/time.py` to support times past midnight.
- **Streamlit boundary enforced** — a test (`test_streamlit_components_accept_reporting_rows_not_scheduler_internals`) verifies that `src/reporting/` imports no Streamlit packages.
- **Sort key design** — formatted `HH:MM` strings (zero-padded → chronological via string comparison) plus lane int and bus_id string for tie-breaking.

## 2026-05-31: Increment 6 — Weighted Scoring & Tunable Optimization

**Decision:** Implement three score components (individual wait, operator smoothness, overall network), apply scoring only to hard-valid candidates, and use Scenario 4 as the operator-weight gate. Score breakdown table uses human-readable component labels, explicit units in column headers (`Raw Score (min)`, `Weighted Score (min)`), and `None` for TOTAL row numeric cells to maintain Arrow-compatible column types for Streamlit dataframe serialization.

**Context & Rationale:**

- **Three score components:**
  - `individual_wait` — total bus wait minutes across all buses, weighted by `weights.individual`
  - `operator_smoothness` — operator wait imbalance penalty (sum of absolute deviations from fleet average), weighted by `weights.operator`
  - `overall_network` — total fleet journey time, weighted by `weights.overall`
- **Scoring only on hard-valid candidates** — scores are computed after invariant validation passes. Infeasible schedules have no score breakdown.
- **Scenario 4 (operator weight = 2.0)** — proves weight threading: operator smoothness penalty is doubled in Scenario 4, making the scheduler prefer schedules that balance wait times across operators.
- **Operator smoothness is post-hoc only** — `operator_smoothness` is computed globally after all buses are scheduled. It is not used during per-bus candidate scoring in the heuristic.
- **Per-bus candidate scoring** (`_score_candidate`) uses only `individual` and `overall` weights. Operator smoothness requires global statistics and cannot be evaluated per candidate.
- **All 5 assignment scenarios** produce feasible schedules with weighted score breakdowns.

## 2026-05-31: Increment 7 — Extensibility Proof & Architecture Sync

**Decision:** Add a scoring component registry (`SCORE_COMPONENTS` dict) for adding new soft rules without engine changes, prove multi-charger station capacity is data-driven, confirm operators are free-text strings, and synchronize all documentation with the actual implementation.

**Context & Rationale:**

- **Scoring component registry** (`SCORE_COMPONENTS` in `src/scheduler/scoring.py`) — a module-level `dict[str, ScoreComponentFn]` that `compute_score_breakdown()` iterates. Adding a new soft rule = registering a function. No plugin loading, no over-engineering. The registry is deliberately minimal.
- **Multi-charger stations** — `ReservationManager` already creates `charger_count` lane schedules per station. The `scenario_multi_charger.json` fixture proves `charger_count: 2` at station B works with zero code changes. Two overlapping reservation requests at B get different lanes.
- **Operator names are free-text strings** — the `scenario_new_operator.json` fixture contains `"express_red"` (not in assignment scenarios) and works without enums, registries, or migrations.
- **Documentation sync** — `ARCHITECTURE.md` updated to replace stale models (`ChargingPlan`, `EventType`, `Direction` enum, `datetime` fields) with current code, update weight-change and new-rule examples to use `SCORE_COMPONENTS`, and add a cross-reference to `docs/SCHEDULER_ENGINE_EVOLUTION.md`.
- **Formal solver upgrade path** — documented and deferred. `docs/SCHEDULER_ENGINE_EVOLUTION.md` already covers the strategy pattern, phased approach, and design rationale.
