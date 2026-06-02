# Scenario-First Vertical Implementation Plan: ExpoNow Bus Charging Scheduler

## Overview

This document is the preferred execution order for the bus charging scheduler. The layer-first plan in `docs/IMPLEMENTATION_PLAN.md` remains the detailed task library, but this vertical plan controls the build sequence.

The assignment demo path is simple: open the hosted Streamlit app, choose any of the five scenarios, inspect the input data, inspect each bus timeline, inspect each station queue, and repeat. The implementation order must make that path visible early, then steadily replace stubs with real parsing, scheduling, scoring, and extensibility proof.

The major planning correction is scenario-first execution:

- Encode all five assignment scenarios before deep scheduler work.
- Render the scenario list and readable scenario input immediately.
- Thread scenario weights through the system from the first real domain model.
- Prove the hard scheduling constraints against contention scenarios before polish.
- Prove weight sensitivity with Scenario 4 before delivery.
- Defer formal solver prototypes; keep only the `SchedulerStrategy` upgrade path.

## Fixed Decisions

These decisions replace the previous open questions and should be treated as implementation assumptions unless the assignment source changes.

| Decision | Choice |
| --- | --- |
| Canonical scenario facts | The five schedules in `docs/Bus_Charging_Scheduler_Assignment.md` become the source data in `data/scenarios/`. |
| Internal time representation | Store scenario-local minutes from the service day start; display as `HH:MM`. |
| Default travel speed | `60 km/h`, data/config driven with an assignment default. |
| Charging policy | Default `240 km` range and `25 min` full-charge duration, data/config driven. |
| Weight editing in v1 | No Streamlit weight editor. Weights are read from scenario files and shown in the UI. |
| Initial scheduler | Custom deterministic heuristic behind `SchedulerStrategy`. |
| Formal solvers | No runnable OR-Tools, Z3, PuLP, or MILP prototypes in the initial product. Document them only as upgrade paths. |
| Operator smoothness | Start with operator wait/delay balance in score breakdown. |
| Baseline fallback | The custom scheduler remains the default and fallback even if a formal solver is explored later. |

## Architecture Boundaries

- `app.py` owns Streamlit page setup and high-level composition only.
- `src/scheduler/` must not import Streamlit.
- Scenario loading, defaults, normalization, and validation live in `src/adapters/`.
- Stable nouns and shared constants live in `src/domain/`.
- Candidate generation, hard constraints, reservations, timeline construction, and scoring live in `src/scheduler/`.
- Display table transformation lives in `src/reporting/`.
- Streamlit rendering helpers live in `src/ui/`.
- The scheduler exposes one primary contract: `schedule(scenario: Scenario) -> ScheduleResult`.
- `ScheduleResult` is the stable UI/reporting contract and should include feasibility, bus plans, station reservations, metrics, warnings, and score breakdown.

## Increment Rules

Every increment must leave the repo runnable and compilable. Behavior-changing work follows red-green-refactor:

1. Add the smallest behavior-focused failing test.
2. Implement the minimum code to pass.
3. Refactor while keeping focused tests green.
4. Run focused tests, then the relevant broader check.

Documentation-only tasks may skip red-green-refactor, but must still include explicit review/search verification.

Handcrafted `ScheduleResult` fixtures are allowed for early reporting and UI tests. That decouples UI/reporting shape from scheduler implementation without pretending the real scheduler already exists.

## Detailed Phase Playbook

This section is the execution script for later implementation work. The roadmap below stays intentionally compact; this playbook expands each increment into the exact kind of tasks, red tests, green implementation work, and code-quality review points expected before moving to the next phase.

General rules for every phase:

- Start each behavior-changing task by writing the smallest failing test that describes user-visible or contract-visible behavior.
- Confirm the test fails for the intended reason before editing production code.
- Implement the minimum useful behavior, then refactor only after the focused tests pass.
- Keep each phase reviewable: avoid mixing broad refactors with feature work unless the refactor is needed for the phase acceptance criteria.
- Record any assumption that changes assignment behavior in docs before relying on it in code.
- Do not introduce solver dependencies unless a later plan explicitly reopens that decision.
- Treat Streamlit, JSON files, browser output, and any future uploaded data as untrusted boundaries; validate before scheduling.

### Phase Gate Template

Before a phase starts:

- [ ] Confirm the phase goal and user-visible outcome still match the assignment.
- [ ] List the exact tests that will be written red first.
- [ ] Identify which files are in scope and which files are deliberately out of scope.
- [ ] Note whether the phase changes public contracts such as scenario JSON or `ScheduleResult`.

During the phase:

- [ ] Run the focused red test and capture the failing behavior.
- [ ] Implement one small behavior at a time.
- [ ] Run focused tests after each meaningful production change.
- [ ] Keep Streamlit code limited to page composition and rendering calls.
- [ ] Keep scheduler code free of Streamlit imports and UI-specific table shapes.

Before the phase is considered complete:

- [ ] Run the phase's focused tests.
- [ ] Run `python -m compileall app.py src`.
- [ ] Run the broader relevant test suite.
- [ ] Review the diff for correctness, readability, architecture, security, and performance.
- [ ] Update this plan, `docs/ARCHITECTURE.md`, or `docs/DECISION_LOG.md` if implementation reality changed.

### Increment 0 Detailed Tasks: Harness And Scenario List UI

Intent: create a runnable app shell and stable contracts without building real scheduling. This increment should prove that the demo can open, list scenarios, and render a safe placeholder result.

Tasks:

- Create Python package boundaries: `src/domain`, `src/adapters`, `src/scheduler`, `src/reporting`, and `src/ui`.
- Define a minimal scenario summary object with `id`, `name`, `description`, and `is_placeholder`.
- Define a minimal `ScheduleResult` object with `feasible`, `scenario_id`, `bus_plans`, `station_reservations`, `metrics`, `warnings`, and `score_breakdown`, even if most collections are empty.
- Define a `SchedulerStrategy` protocol or base class with `schedule(scenario) -> ScheduleResult`.
- Add a deterministic stub strategy that returns an empty feasible placeholder result plus a warning that scheduling is not implemented yet.
- Add a scenario catalog function that returns five scenario summaries: Scenario 1 through Scenario 5.
- Add a Streamlit layout function that accepts scenario summaries and a `ScheduleResult`; it should not import scheduler internals directly.
- Keep `app.py` small: page config, title, scenario selection, orchestration call, render call.
- Add baseline project commands to documentation.

Red tests to write first:

- `test_scenario_catalog_lists_five_assignment_scenarios`: expects exactly five scenario summaries, stable ids `scenario_1` through `scenario_5`, and display names containing `Scenario 1` through `Scenario 5`.
- `test_stub_scheduler_returns_schedule_result_contract`: calls the stub strategy with a scenario summary and asserts `feasible is True`, the scenario id is preserved, and placeholder warnings are present.
- `test_app_orchestration_returns_selected_summary_and_result`: exercises a non-Streamlit orchestration function with `scenario_1` and asserts it returns the selected summary and stub result.
- `test_scheduler_package_does_not_import_streamlit`: scans `src/scheduler` Python files and fails if `streamlit` is imported.
- `test_app_imports_without_running_streamlit_side_effects`: imports app-level orchestration helpers without needing a browser session.

Expected red failures:

- Scenario catalog module does not exist.
- Scheduler contract or stub result does not exist.
- App orchestration is still embedded directly in `app.py`.
- Scheduler package boundary cannot yet be verified because files are missing.

Implementation sequence:

1. Add package `__init__.py` files only where Python import behavior needs them.
2. Add minimal dataclasses or typed structures for scenario summary and schedule result.
3. Add the catalog function with hardcoded metadata only; do not encode full assignment data yet.
4. Add the stub scheduler behind the contract.
5. Add an orchestration function such as `build_initial_view_model(selected_scenario_id)`.
6. Update `app.py` to call the orchestration and UI layout helpers.
7. Add requirements only for tools actually needed in this phase.

Green checks:

- `python -m unittest` or `python -m pytest` passes for the focused tests added in this phase.
- `python -m compileall app.py src` passes.
- Manual Streamlit smoke check shows a title, a scenario dropdown, and a clearly labeled placeholder schedule.

Code quality review focus:

- Correctness: the five scenario ids are stable and deterministic.
- Readability: placeholder behavior is clearly named so nobody mistakes it for scheduling.
- Architecture: `app.py` does not own scheduling decisions; `src/scheduler` does not import Streamlit.
- Security: no file paths or user-selected ids are used to read arbitrary files yet.
- Performance: startup does no expensive work; scenario summaries are tiny.
- Review note to leave in PR/change summary: this phase intentionally does not contain real scenario data or scheduling.

### Increment 1 Detailed Tasks: Canonical Scenario Data (done)

Intent: convert the assignment tables into data files before deeper scheduler work. All hard later behavior depends on correct input data.

Tasks:

- Choose the scenario JSON schema and document it in `docs/ARCHITECTURE.md` or an adjacent data-format note.
- Create `data/scenarios/scenario_1.json` through `scenario_5.json`.
- Encode route facts once per scenario or via a defaults section: Bengaluru, A, B, C, D, Kochi with segment distances 100, 120, 100, 120, 100 km.
- Encode charging policy: default battery range 240 km and full charge duration 25 minutes.
- Encode travel policy: default speed 60 km/h.
- Encode stations A, B, C, and D with `charger_count = 1`.
- Encode all bus rows from the assignment with ids, operators, directions, and departure times.
- Encode weights for every scenario; Scenario 4 must use `individual = 1.0`, `operator = 2.0`, and `overall = 1.0`.
- Keep scenario files data-only; no Python-specific logic or derived schedule output.

Red tests to write first:

- `test_all_five_scenario_files_exist`: asserts the five expected JSON files are present.
- `test_scenario_files_have_required_top_level_keys`: checks `id`, `name`, `description`, `route`, `stations`, `buses`, `charging_policy`, `travel_policy`, and `weights`.
- `test_assignment_scenario_fact_counts`: asserts Scenario 1 has 20 buses, Scenario 3 has 14 buses, and Scenarios 2, 4, and 5 match their assignment counts.
- `test_scenario_4_operator_weight_is_two`: asserts the non-default operator weight is encoded.
- `test_scenario_5_departures_fit_72_minute_window`: parses departure times and checks max departure minus min departure is 72 minutes.
- `test_station_and_policy_defaults_match_assignment`: asserts A-D exist, charger counts are one, range is 240 km, charge duration is 25 minutes, and speed is 60 km/h.

Expected red failures:

- `data/scenarios` does not exist.
- Scenario JSON shape is absent or missing required keys.
- Scenario-specific facts are not yet encoded.

Implementation sequence:

1. Add the directory and the five files.
2. Fill shared policies and route data first.
3. Transcribe bus rows exactly from the assignment tables.
4. Add weights last and verify Scenario 4 separately.
5. Run JSON parsing tests before any loader implementation.
6. Manually compare each scenario file against the assignment source.

Green checks:

- JSON parse tests pass over every file.
- Fact tests pass for bus counts, weights, station counts, departure windows, and defaults.
- Search confirms there is no plan guidance saying to add only one scenario first.

Code quality review focus:

- Correctness: transcription fidelity is the highest risk; review bus ids, operators, directions, and times line by line.
- Readability: JSON should be regular enough that a reviewer can inspect and edit it.
- Architecture: scenario files should describe the world, not scheduler decisions.
- Security: later loaders must validate JSON; do not assume trusted data just because files are local.
- Performance: files are small; avoid premature compression or generated formats.
- Review note to leave in PR/change summary: all downstream scheduler behavior is only as credible as these facts.

### Increment 2 Detailed Tasks: Domain Models, Loader, And Weight Threading

Intent: move from raw JSON to typed domain objects and ensure weights travel through the system before they influence optimization.

Tasks:

- Define domain models for `Route`, `Segment`, `Station`, `Bus`, `Scenario`, `Weights`, `ChargingPolicy`, and `TravelPolicy`.
- Define schedule-facing models for `ScheduleResult`, `BusPlan`, `ChargingStop`, `StationReservation`, `TimelineEvent`, `ScheduleMetrics`, and `ScoreBreakdown`.
- Add time helpers for `HH:MM` parsing, scenario-local minute conversion, and display formatting.
- Add route helpers for direction-aware station order and distance between route points.
- Implement scenario discovery from `data/scenarios`.
- Implement `load_scenario(scenario_id)` returning a `Scenario` object.
- Add clear adapter errors for missing scenario, malformed JSON, unknown schema fields if strict mode is chosen, and validation failure.
- Thread `Scenario.weights` into stub schedule results or result metadata so reporting can display them before scoring exists.

Red tests to write first:

- `test_load_scenario_returns_domain_object_not_dict`: asserts the loader returns `Scenario` with typed nested objects.
- `test_discover_scenarios_returns_all_five_in_display_order`: asserts stable ordering and labels.
- `test_missing_scenario_id_raises_adapter_error`: asks for a nonexistent id and expects a clear domain-specific error.
- `test_malformed_json_raises_adapter_error`: uses a fixture with invalid JSON and expects a friendly loader error.
- `test_time_helpers_round_trip_assignment_times`: verifies `19:00`, `20:12`, and boundary values convert to minutes and back.
- `test_route_order_for_bengaluru_to_kochi` and `test_route_order_for_kochi_to_bengaluru`: verify direction-aware station ordering.
- `test_scenario_weights_are_available_to_schedule_result`: stub schedule result exposes the selected scenario's weights.

Expected red failures:

- Loader returns raw dictionaries or does not exist.
- Time and route helpers do not exist.
- Weight data is loaded but not threaded into scheduling/reporting contracts.

Implementation sequence:

1. Add dataclasses or equivalent simple typed models.
2. Implement time helpers first because loader validation depends on them.
3. Implement route helpers with direction as an explicit input.
4. Implement loader discovery and load-by-id.
5. Convert JSON dictionaries into domain objects at the adapter boundary.
6. Update the stub scheduler to accept a full `Scenario`.
7. Update UI/reporting placeholders to use domain objects.

Green checks:

- Domain construction tests pass.
- Loader tests pass for all five scenarios.
- Missing and malformed scenario tests pass.
- `python -m compileall app.py src` passes.

Code quality review focus:

- Correctness: no raw dicts should leak past adapters.
- Readability: model names should match assignment language.
- Architecture: domain models should not import adapters, scheduler strategies, reporting, or Streamlit.
- Security: parsing errors should not expose stack traces in UI paths.
- Performance: loader should read only the selected scenario for detail views, while discovery may read lightweight metadata.
- Review note to leave in PR/change summary: weights are now part of the contract even though optimization is still later.

### Increment 3 Detailed Tasks: Validation And Readable Input Rendering

Intent: make scenario input trustworthy and reviewer-readable before scheduling output becomes complex.

Tasks:

- Add scenario validation for required fields, positive distances, positive charger counts, positive charging duration, positive battery range, positive speed, non-negative weights, duplicate bus ids, unknown station names, invalid directions, and unparseable departure times.
- Validate route connectivity and ensure route endpoints are Bengaluru and Kochi unless deliberately generalized later.
- Validate each station referenced by policy or route exists in the station list.
- Build reporting transformations for scenario summary, route table, station table, policy values, weight values, and bus departure table.
- Add UI components that render those tables without scheduling logic.
- Display friendly validation errors in app flow.
- Ensure Scenario 4 visibly shows operator weight `2.0`.
- Ensure Scenario 5 visibly shows high-contention departure clustering.

Red tests to write first:

- `test_validator_accepts_all_assignment_scenarios`: runs validation on all five loaded scenarios.
- `test_validator_rejects_duplicate_bus_ids`: invalid fixture with repeated bus id fails before scheduling.
- `test_validator_rejects_unknown_direction`: invalid direction fails with a helpful message.
- `test_validator_rejects_negative_distance`: invalid segment distance fails.
- `test_validator_rejects_zero_charger_count`: station with zero chargers fails.
- `test_validator_rejects_negative_weight`: negative operator or overall weight fails.
- `test_input_tables_are_built_from_domain_objects`: reporting function accepts `Scenario`, not raw JSON.
- `test_scenario_4_weight_row_displays_operator_two`: reporting output includes the non-default weight.
- `test_scenario_5_bus_departure_table_shows_72_minute_window`: reporting output preserves the clustered departures.

Expected red failures:

- Invalid data reaches scheduler unchanged.
- Reporting has no domain-backed input tables.
- UI cannot show validation errors cleanly.

Implementation sequence:

1. Implement validator with one rule at a time, keeping messages specific.
2. Wire validation into loader or orchestration so invalid scenarios stop before scheduler calls.
3. Add reporting table functions for scenario input views.
4. Add UI rendering helpers that consume already-shaped reporting rows.
5. Update `app.py` composition to show input before schedule output.
6. Add invalid fixtures under tests only; do not pollute assignment data.

Green checks:

- Validator tests pass for all valid and invalid fixtures.
- Reporting tests pass for input tables.
- Manual Streamlit check cycles through all five scenario input views.
- `python -m compileall app.py src` passes.

Code quality review focus:

- Correctness: validation should fail close to the boundary and before scheduling.
- Readability: validation errors should name the scenario and offending field.
- Architecture: reporting owns table shape; UI renders tables only.
- Security: malformed JSON and invalid field values should never produce raw tracebacks in the app.
- Performance: validation is linear in route segments, stations, and buses.
- Review note to leave in PR/change summary: this phase is the data quality gate for all later engine work.

### Increment 4 Detailed Tasks: Feasible Baseline Scheduler

Intent: produce deterministic, hard-valid schedules for all assignment scenarios before adding soft scoring.

Tasks:

- Generate candidate charging stop sequences for each bus based on route order and range.
- Reject candidate sequences that exceed battery range between charge opportunities.
- Reject candidates that backtrack or skip required direction order.
- Implement station reservation logic with `charger_count` lanes from the start.
- Build timeline events for departure, travel, arrival at station, wait, charge start, charge end, and final arrival.
- Implement a deterministic heuristic strategy behind `SchedulerStrategy`.
- Add invariant helpers that validate any `ScheduleResult`: range, route order, capacity, charge duration, and chronological timeline.
- Return infeasible results with explicit reasons rather than raising in normal scheduling paths.
- Use Scenarios 2 and 5 as contention gates, not late surprises.

Red tests to write first:

- `test_candidate_generation_includes_feasible_inner_station_sequences`: proves candidate generation can find plans for the 540 km route with 240 km range.
- `test_range_constraint_allows_exact_boundary`: distance exactly equal to range is valid.
- `test_range_constraint_rejects_over_range_gap`: any gap above range is invalid.
- `test_reverse_direction_candidates_follow_reverse_route_order`: Kochi-to-Bengaluru buses never backtrack.
- `test_single_charger_reservations_do_not_overlap`: overlapping requests at a one-charger station are serialized.
- `test_multiple_charger_reservations_allow_parallel_lanes`: non-assignment fixture proves capacity is data-driven.
- `test_timeline_uses_25_minute_charge_duration`: assignment default charge duration is respected.
- `test_scheduler_produces_feasible_result_for_scenario_1`: baseline happy path.
- `test_scheduler_produces_feasible_result_for_scenario_2`: bunched contention gate.
- `test_scheduler_produces_feasible_result_for_scenario_5`: worst-case convergence gate.
- `test_invariants_hold_for_all_assignment_scenarios`: broad guard after focused engine tests.

Expected red failures:

- No candidate generation exists.
- Reservations cannot serialize charger contention.
- Stub scheduler returns empty placeholder output.
- Invariants fail because real timelines are absent.

Implementation sequence:

1. Implement pure range and route-order checks first.
2. Implement candidate generation independent of reservations.
3. Implement station reservation data structures and lane assignment.
4. Build a single-bus timeline without contention.
5. Add multi-bus scheduling with deterministic bus processing order.
6. Add wait calculations when a charger is occupied.
7. Add invariant checks and call them in tests.
8. Replace placeholder scheduler result for loaded scenarios with real schedule output.

Green checks:

- Candidate, constraint, reservation, engine, and invariant tests pass.
- All five assignment scenarios produce feasible results.
- `python -m compileall app.py src` passes.
- Manual Streamlit check shows real, non-empty schedule output for at least Scenarios 1, 2, and 5.

Code quality review focus:

- Correctness: hard constraints must be enforced before scoring or reporting.
- Readability: timeline event names should make schedule reconstruction obvious.
- Architecture: heuristic strategy should depend on scheduler primitives, not UI/reporting tables.
- Security: no user-controlled scenario id should create arbitrary file reads.
- Performance: candidate generation must stay bounded for 20 buses and remain obviously extensible for larger inputs.
- Review note to leave in PR/change summary: hard-valid deterministic scheduling exists, but soft scoring is not active yet.

### Increment 5 Detailed Tasks: Timetable And Station Queue Rendering

Intent: turn real `ScheduleResult` objects into the exact output views requested by the assignment.

Tasks:

- Transform each bus plan into display-ready timetable rows.
- Transform station reservations into chronological station queue rows.
- Include bus id, operator, direction, station, arrival, wait, charge start, charge end, charger lane, and final arrival where relevant.
- Include empty-state and infeasible-state table behavior.
- Ensure station queues at B and C interleave buses from both directions by actual charge start time.
- Keep sorting deterministic when two events share the same timestamp.
- Surface schedule summary metrics without hiding the detailed rows.

Red tests to write first:

- `test_bus_timetable_rows_include_charge_wait_and_final_arrival`: handcrafted result fixture produces complete rows.
- `test_station_queue_rows_sort_by_charge_start_then_lane_then_bus`: deterministic station ordering.
- `test_station_queue_interleaves_both_directions_for_scenario_2`: real scheduler output includes both directions in chronological station queues.
- `test_station_queue_interleaves_both_directions_for_scenario_5`: worst-case convergence output is rendered correctly.
- `test_infeasible_result_renders_friendly_message_rows`: no traceback or empty crash path.
- `test_streamlit_components_accept_reporting_rows_not_scheduler_internals`: UI boundary test or import-level check.

Expected red failures:

- Reporting only has input tables or handcrafted placeholders.
- Station queues are grouped by direction instead of chronological charging order.
- Infeasible results have no friendly display path.

Implementation sequence:

1. Add reporting row types or simple dictionaries for bus timetable output.
2. Add station queue transformation from reservations.
3. Add deterministic sort keys.
4. Add UI components for timetable and station queues.
5. Wire UI layout to show input view first, then timetable, then station queues.
6. Add friendly rendering for infeasible schedules and warnings.

Green checks:

- Reporting tests pass for handcrafted fixtures and real outputs.
- Manual Streamlit check cycles through all five scenarios and shows input, bus timetable, and station queue views.
- `python -m compileall app.py src` passes.

Code quality review focus:

- Correctness: displayed waits and charge windows must match schedule result facts.
- Readability: reporting transformation code should be easy to audit without Streamlit knowledge.
- Architecture: UI should not compute waits, sort reservations, or infer station order.
- Security: UI should render values, not execute or parse them.
- Performance: table transformation should be linear or near-linear over schedule events.
- Review note to leave in PR/change summary: assignment-required output views are now present.

### Increment 6 Detailed Tasks: Weighted Scoring And Tunable Optimization (done)

Intent: make scenario weights meaningful after hard validity is guaranteed.

Tasks:

- [x] Define score components for individual bus wait, operator smoothness, and overall network time.
- [x] Represent unweighted component values and weighted component contributions separately.
- [x] Score only schedules that already pass hard invariants.
- [x] Add score breakdown to `ScheduleResult`.
- [x] Use Scenario 4 as the required non-default operator-weight gate.
- [x] Add sensitivity fixtures that create at least two valid alternatives so weight changes can affect chosen order or total score.
- [x] Document the v1 operator smoothness assumption: balance operator wait/delay, not a full fairness optimizer.
- [x] Keep weight changes editable through scenario data, not through hardcoded constants.

Red tests to write first:

- [x] `test_individual_wait_component_sums_bus_wait_minutes`: scoring component is transparent.
- [x] `test_overall_network_component_tracks_total_completion_or_wait_metric`: chosen overall metric is explicit and stable.
- [x] `test_operator_smoothness_component_penalizes_operator_imbalance`: operator-heavy imbalance changes component value.
- [x] `test_score_breakdown_includes_unweighted_and_weighted_values`: reviewable score output.
- [x] `test_weights_change_weighted_total_without_changing_hard_validity`: changing weights affects score, not invariants.
- [x] `test_scenario_4_operator_weight_changes_component_contribution`: Scenario 4 proves non-default weight threading.
- [x] `test_scheduler_scores_only_hard_valid_candidates`: invalid candidate is rejected before scoring.

Expected red failures:

- [x] Weights are loaded but not used.
- [x] Score breakdown is empty or only a total.
- [x] Scheduler may select first feasible result without scoring alternatives.

Implementation sequence:

- [x] 1. Add pure scoring functions with handcrafted schedule fixtures.
- [x] 2. Add score breakdown model fields if not already present.
- [x] 3. Integrate scoring into the heuristic after hard-valid candidate construction.
- [x] 4. Add deterministic tie-breaking.
- [x] 5. Add Scenario 4 sensitivity tests.
- [x] 6. Update reporting metrics to show score components.
- [x] 7. Document the score semantics in architecture docs.

Green checks:

- [x] Scoring unit tests pass.
- [x] Scenario 4 sensitivity tests pass.
- [x] Invariant tests still pass for all five scenarios.
- [x] Manual Streamlit check shows readable score breakdown.
- [x] `python -m compileall app.py src` passes.

Code quality review focus:

- Correctness: weights must never permit illegal schedules.
- Readability: score component names should explain what they measure.
- Architecture: scoring components should be composable and testable without Streamlit.
- Security: no expression evaluation or dynamic code loading for weights.
- Performance: avoid scoring a combinatorial explosion without caps or pruning.
- Review note to leave in PR/change summary: scoring is now active and Scenario 4 is the proof point.

### Increment 7 Detailed Tasks: Extensibility Proof And Architecture Sync (done)

Intent: prove the data model and scoring architecture can absorb likely assignment interview changes without rewiring the app.

Tasks:

- Add a test-only soft scoring component through the same composition path as real components.
- Add a non-assignment fixture with changed station capacity, such as two chargers at station B.
- Add a non-assignment fixture that changes a route segment distance or adds an operator if it remains small and useful.
- Prove multiple chargers affect reservations and reporting without code changes outside scheduler/reporting.
- Document how to change weights in scenario data.
- Document how to add a new scenario.
- Document how to add a new soft rule.
- Update `docs/ARCHITECTURE.md` to match actual module names and contracts.
- Update `docs/DECISION_LOG.md` for any decisions made since Increment 0.
- Document formal solver upgrade paths without adding runtime solver dependencies.

Red tests to write first:

- `test_custom_score_component_participates_in_total_and_breakdown`: test-only component proves extensibility.
- `test_two_charger_station_allows_parallel_reservations`: data-driven station capacity proof.
- `test_reporting_includes_charger_lane_for_multi_charger_fixture`: output remains intelligible with multiple chargers.
- `test_new_operator_in_fixture_does_not_require_code_change`: operator names are data, not enum locks, unless deliberately constrained.
- `test_docs_explain_weight_change_and_new_rule_extension`: static doc search for required handoff sections.

Expected red failures:

- Scoring may be hardcoded to built-in components.
- Reservation capacity may be effectively fixed at one charger.
- Docs may describe intended architecture rather than actual implementation.

Implementation sequence:

1. Add the smallest non-assignment fixtures needed for extension proof.
2. Add scoring composition hook or registry only if the tests show hardcoding.
3. Verify station capacity comes from data.
4. Update reporting if multi-lane station output is ambiguous.
5. Update architecture, decision log, and run/test docs.
6. Search for stale module names, stale solver prototype guidance, and stale scenario-order guidance.

Green checks:

- Extensibility tests pass.
- Multi-charger reservation/reporting tests pass.
- Documentation search checks pass.
- `python -m compileall app.py src` passes.

Code quality review focus:

- Correctness: extension fixtures must not mutate assignment scenario expectations.
- Readability: extension points should be discoverable, not magical.
- Architecture: adding a soft rule should be localized and should not touch Streamlit.
- Security: do not load arbitrary scoring code from scenario JSON.
- Performance: extension hook should not add overhead to normal scheduling beyond simple component iteration.
- Review note to leave in PR/change summary: this phase exists because the assignment evaluates future-change readiness.

### Increment 8 Detailed Tasks: Review-Ready Delivery

Intent: make the repository, app, docs, and verification story ready for assignment handoff.

Tasks:

- Finalize top-level README or docs README with local run, test, deployment, weight-change, scenario-addition, and rule-addition instructions.
- Verify `requirements.txt` includes runtime dependencies and any agreed test dependency, but no unused solver packages.
- Add final edge fixtures for exactly-at-range, impossible range, simultaneous station arrivals, and multiple operators.
- Run a documentation consistency pass across `docs/ARCHITECTURE.md`, `docs/DECISION_LOG.md`, `docs/IMPLEMENTATION_PLAN.md`, and this vertical plan.
- Confirm hosted app status or provide exact Streamlit Community Cloud deployment steps.
- Perform final manual app walkthrough: open app, select each scenario, inspect input, inspect per-bus timetable, inspect per-station queue.
- Prepare a short review note describing assumptions, constraints, test coverage, and known future work.

Red tests to write first:

- `test_exactly_at_range_edge_fixture_is_feasible`: boundary behavior remains valid.
- `test_impossible_range_fixture_is_infeasible_with_reason`: impossible data produces explainable infeasible result.
- `test_simultaneous_station_arrivals_are_deterministically_ordered`: stable tie-breaking.
- `test_multiple_operator_fixture_scores_without_special_cases`: operator logic generalizes.
- `test_requirements_do_not_include_deferred_solver_dependencies`: static dependency guard.
- `test_docs_no_longer_contain_stale_open_questions`: static search for resolved assumptions.

Expected red failures:

- Edge fixtures may reveal hidden assumptions in scheduler or reporting.
- Requirements may include unused packages after experimentation.
- Docs may drift from implemented contracts.

Implementation sequence:

1. Add edge fixtures and focused tests.
2. Fix only real defects exposed by final fixtures.
3. Remove unused dependencies if any were added.
4. Update run/test/deploy docs.
5. Run full verification.
6. Do the final code-quality review.

Green checks:

- Full test suite passes.
- `python -m compileall app.py src` passes.
- `streamlit run app.py` works from repo root.
- Manual app check cycles through all five scenarios.
- Docs search confirms solver prototypes are deferred, open questions are resolved, and no stale "one scenario first, rest later" guidance remains.

Code quality review focus:

- Correctness: all assignment scenarios produce defensible schedules and all edge fixtures behave intentionally.
- Readability: README and architecture docs should let a reviewer understand the system without a live walkthrough.
- Architecture: contracts should be stable and future changes should have obvious homes.
- Security: invalid input paths, malformed JSON, and bad scenario values should fail cleanly.
- Performance: final demo should load quickly and avoid expensive recomputation where simple caching is appropriate.
- Review note to leave in PR/change summary: this is the release-candidate gate, not a feature-development phase.

### Cross-Phase Code Quality Review Checklist

Use this checklist after each implementation phase and before any merge or handoff:

- Correctness:
  - [ ] Does the implemented behavior match the phase acceptance criteria?
  - [ ] Do tests cover happy path, boundary values, and at least one failure path?
  - [ ] Are scenario facts transcribed from the assignment without drift?
  - [ ] Are hard constraints enforced before scoring and reporting?

- Readability:
  - [ ] Are model, function, and test names aligned with assignment nouns?
  - [ ] Can a reviewer understand each module without reading unrelated layers?
  - [ ] Are comments limited to non-obvious decisions or gotchas?
  - [ ] Is placeholder behavior clearly labeled and removed when real behavior lands?

- Architecture:
  - [ ] Does `app.py` remain composition-only?
  - [ ] Does `src/scheduler/` remain free of Streamlit imports?
  - [ ] Do adapters convert untrusted input into domain objects before scheduler use?
  - [ ] Does reporting own table shape while UI owns rendering?
  - [ ] Are scoring components separate from hard constraints?

- Security and robustness:
  - [ ] Are malformed scenario files handled with friendly adapter errors?
  - [ ] Are user-selected scenario ids resolved through a catalog, not direct file paths?
  - [ ] Are scenario values validated before scheduling?
  - [ ] Are no secrets, tokens, absolute local-only paths, or deployment credentials committed?

- Performance:
  - [ ] Is work bounded for the small assignment scenarios?
  - [ ] Is candidate generation pruned enough to avoid accidental combinatorial growth?
  - [ ] Are repeated display transformations simple and deterministic?
  - [ ] Is any caching explicit and safe for scenario selection?

- Verification story:
  - [ ] Which red tests failed first?
  - [ ] Which focused tests now pass?
  - [ ] Which broader checks were run?
  - [ ] Was a manual Streamlit check needed, and what was inspected?
  - [ ] What risks remain for the next phase?

## Vertical Roadmap

### Increment 0: Harness And Scenario List UI

**Goal:** Keep the app runnable and make the assignment's five-scenario shape visible immediately.

**User-visible outcome:**

- [x] `streamlit run app.py` opens the app.
- [x] A scenario dropdown lists Scenario 1 through Scenario 5 from lightweight metadata or parsed files.
- [x] The page can render a stub/empty result without real scheduling logic.

**Implementation work:**

- Establish or finish package layout: `src/domain`, `src/adapters`, `src/scheduler`, `src/reporting`, and `src/ui`.
- Add test tooling and a smoke test.
- Define the minimal `SchedulerStrategy` and `ScheduleResult` contract needed by stubs.
- Add a small non-Streamlit orchestration seam that app code can call.
- Avoid a solver dropdown unless there are at least two production-ready strategies.

**Acceptance criteria:**

- [x] `app.py` imports from `src` without path hacks.
- [x] App logic does not contain scheduling decisions.
- [x] Scenario names are visible before real scheduling exists.
- [x] The deployment already recorded in `docs/DECISION_LOG.md` remains valid; no new deployment task blocks this increment.

**Verification:**

- [x] `python -m compileall app.py src`
- [x] `python -m unittest`
- [x] Manual Streamlit smoke check shows the dropdown and stub output.

**Likely files:**

- `app.py`
- `src/scheduler/contract.py`
- `src/ui/layout.py`
- `tests/test_smoke.py`
- `requirements.txt`

### Increment 1: Canonical Scenario Data (done)

**Goal:** Encode all five assignment scenarios as the canonical input world before scheduler depth increases.

**User-visible outcome:**

- [x] Every scenario in the dropdown corresponds to real scenario data.
- [x] Scenario 4 carries `operator = 2.0`.
- [x] Scenario 5 carries the worst-case 72-minute convergence schedule.

**Implementation work:**

- [x] Define the scenario JSON shape for route, stations, charger policy, buses, directions, departures, operators, and weights.
- [x] Create `data/scenarios/scenario_1.json` through `scenario_5.json`.
- [x] Store `Station.charger_count`, battery range, charge duration, and speed as data/config values with assignment defaults.
- [x] Add fixture/schema tests that assert the five files exist and include required top-level keys.

**Acceptance criteria:**

- [x] All five assignment scenarios are present.
- [x] Each scenario has stable `id`, `name`, `description`, `route`, `stations`, `buses`, `charging_policy`, `travel_policy`, and `weights`.
- [x] Scenario 1 has 20 buses, Scenario 2 has bunched departures, Scenario 3 has 14 buses, Scenario 4 has non-default operator weight, and Scenario 5 has all departures within 72 minutes.
- [x] Manual review confirms scenario facts match the assignment tables.

**Verification:**

- [x] JSON parse test over every scenario file.
- [x] Scenario fact tests for bus counts, weights, station count, and departure windows.
- [x] Search confirms there is no stale guidance that delays most scenario data until a later increment.

**Likely files:**

- `data/scenarios/scenario_1.json`
- `data/scenarios/scenario_2.json`
- `data/scenarios/scenario_3.json`
- `data/scenarios/scenario_4.json`
- `data/scenarios/scenario_5.json`
- `tests/test_scenario_files.py`

### Increment 2: Domain Models, Loader, And Weight Threading (done)

**Goal:** Parse all scenario files into domain objects and thread weights through the system before they influence schedule choice.

**User-visible outcome:**

- [x] Selecting any scenario loads domain-backed data instead of placeholder metadata.
- [x] The app can display route, stations, buses, charger policy, travel policy, and weights.

**Implementation work:**

- [x] Define frozen domain dataclasses for `Segment`, `Route`, `Station`, `Bus`, `ChargingPolicy`, `TravelPolicy`, `Weights`, and `Scenario`.
- [x] Add time helpers (`parse_hhmm`, `format_minutes`) for HH:MM parsing and display.
- [x] Add route helpers (`get_ordered_stops`, `total_distance`, `distance_between`) for direction-aware station order and distance calculations.
- [x] Implement scenario discovery (`discover_scenario_ids`) and load-by-id (`load_scenario`).
- [x] Add adapter-level errors (`AdapterError`, `ScenarioNotFoundError`, `MalformedScenarioError`).
- [x] Update contract types: `BusPlan`, `ChargingStop`, `StationReservation`, `TimelineEvent`, `ScheduleMetrics`, `ScoreBreakdown`; `ScheduleResult` fields from `list[Any]` to typed lists.
- [x] Update `SchedulerStrategy.schedule()` to accept `Scenario` instead of `ScenarioSummary`.
- [x] Thread `Weights` through stub `ScoreBreakdown.components["weights"]` so they reach the UI.
- [x] Update catalog to be backed by real `load_scenario()`, returning `is_placeholder=False`.
- [x] Update `app_view_model.py` to pass full `Scenario` into scheduler.
- [x] Update `layout.py` to display weight info from `score_breakdown`.

**Acceptance criteria:**

- [x] Loader lists and loads all five scenarios.
- [x] Raw dictionaries do not leak into scheduler code — `scenario_loader.py` is the only file that touches `dict`.
- [x] Defaults (speed 60 km/h, range 240 km, charge duration 25 min) live in `ChargingPolicy` / `TravelPolicy` dataclass defaults.
- [x] Direction-aware helpers work for Bengaluru-to-Kochi and Kochi-to-Bengaluru buses.
- [x] Weights are visible in loaded `Scenario` and, when a schedule is produced, in `ScoreBreakdown.components["weights"]`.

**Verification:**

- [x] 10 domain construction tests pass.
- [x] 5 route helper tests pass (both directions, total distance, distance_between, invalid station).
- [x] 4 time helper tests pass (parse, format, round-trip, invalid input).
- [x] 8 loader tests pass (discovery, all 5 scenarios, error cases).
- [x] 7 contract type tests pass (all new typed models).
- [x] 3 adapter error tests pass.
- [x] 5 stub weight-threading tests pass.
- [x] 2 catalog integration tests pass.
- [x] `python -m compileall app.py src` passes.
- [x] Full test suite: 57 tests pass in under 100 ms.

**Likely files:**

- `src/domain/models.py`
- `src/domain/route.py`
- `src/domain/time.py`
- `src/domain/__init__.py`
- `src/adapters/scenario_loader.py`
- `src/adapters/errors.py`
- `src/adapters/scenario_catalog.py`
- `src/scheduler/contract.py`
- `src/scheduler/__init__.py`
- `src/scheduler/stub.py`
- `src/app_view_model.py`
- `src/ui/layout.py`
- `tests/test_increment_2_domain_and_loader.py`
- `tests/test_increment_0_harness.py`

### Increment 3: Validation And Readable Input Rendering (done)

**Goal:** Harden the data boundary and make the reviewer-facing input view useful for all scenarios.

**User-visible outcome:**

- [x] The app shows the selected scenario's input in readable tables/sections.
- [x] Friendly validation errors appear without stack traces.

**Implementation work:**

- [x] Validate unknown stations, disconnected route segments, negative distances/durations/charger counts/weights, duplicate bus ids, invalid directions, and unparseable departure times.
- [x] Render scenario summary, route table, station table, policy values, weights, and bus departure table.
- [x] Keep UI components display-only; no scheduling logic in Streamlit.

**Acceptance criteria:**

- [x] Every valid assignment scenario passes validation.
- [x] Invalid fixture tests fail before reaching the scheduler.
- [x] Scenario 4 visibly shows operator weight `2.0`.
- [x] Scenario 5 visibly shows the high-contention departure window.
- [x] UI input tables are produced from domain objects, not raw file text.

**Verification:**

- [x] Validator tests for at least one invalid case per rule.
- [x] Reporting/UI composition tests using loaded scenarios.
- [x] Manual Streamlit check: cycle through all five scenarios and inspect input views.

**Likely files:**

- `src/adapters/scenario_validator.py`
- `src/reporting/tables.py`
- `src/ui/components.py`
- `src/ui/layout.py`
- `tests/test_scenario_validator.py`
- `tests/test_reporting.py`

### Increment 4: Feasible Baseline Scheduler (done)

**Goal:** Produce deterministic hard-valid schedules for all assignment scenarios before adding soft optimization.

**User-visible outcome:**

- [x] Selecting any scenario produces a feasible baseline schedule.
- [x] Each bus has charging stations, waits, and final arrival.

**Implementation work:**

- [x] Generate candidate charging stop sequences per bus.
- [x] Reject candidates that violate range or route order.
- [x] Reserve station charger intervals with `charger_count` support from the start, defaulting to one.
- [x] Build bus timelines using travel time, wait time, charge start/end, and arrival.
- [x] Add invariant helpers that can validate any strategy output.
- [x] Return infeasible results with explainable reasons if no valid plan exists.

**Acceptance criteria:**

- [x] Every final schedule respects 240 km range, route order, and station capacity.
- [x] Charging duration is exactly 25 minutes under assignment defaults.
- [x] Buses never backtrack.
- [x] Scenarios 2 and 5 run through the reservation system early as contention gates.
- [x] Hard constraints are checked before scoring can choose between candidates.

**Verification:**

- [x] Candidate generation tests.
- [x] Range constraint tests for feasible, exact-boundary, over-range, and reverse-direction sequences.
- [x] Station capacity tests for overlapping and non-overlapping reservations.
- [x] Engine tests for Scenarios 1, 2, and 5.
- [x] Invariant tests against every assignment scenario.

**Likely files:**

- `src/scheduler/candidates.py`
- `src/scheduler/constraints.py`
- `src/scheduler/reservations.py`
- `src/scheduler/strategies/custom_heuristic.py`
- `src/scheduler/registry.py`
- `tests/test_candidates.py`
- `tests/test_constraints.py`
- `tests/test_scheduler_engine.py`
- `tests/test_scheduler_invariants.py`

### Increment 5: Timetable And Station Queue Rendering (done)

**Goal:** Render the assignment's required output views from real schedule results.

**User-visible outcome:**

- [x] Per-bus timetable shows full timeline, charging stations, wait at each stop, and final arrival.
- [x] Per-station view shows the order in which buses charged at A, B, C, and D.

**Implementation work:**

- Transform `ScheduleResult` into display-ready bus timetable rows.
- Transform station reservations into station queue rows.
- Include direction, operator, arrival, charge start, charge end, wait, and charger lane where relevant.
- Ensure stations B and C correctly interleave BK and KB buses by actual charge order.
- Surface feasibility, warnings, and summary metrics without hiding schedule details.

**Acceptance criteria:**

- [x] Reporting layer owns table shape; Streamlit only renders it.
- [x] Station queues include buses from both directions in chronological charge order.
- [x] Scenarios 2 and 5 have explicit verification for directional interleaving.
- [x] Empty/infeasible schedules render friendly messages.

**Verification:**

- [x] Reporting tests with handcrafted `ScheduleResult` fixtures.
- [x] Reporting tests with real scheduler outputs for Scenarios 2 and 5.
- [x] Manual Streamlit check: input, per-bus timetable, and per-station views for all five scenarios.

**Likely files:**

- `src/reporting/tables.py`
- `src/reporting/metrics.py`
- `src/ui/components.py`
- `src/ui/layout.py`
- `tests/test_reporting.py`

### Increment 6: Weighted Scoring And Tunable Optimization (done)

**Goal:** Make individual, operator, and overall weights visible and meaningful after hard validity is guaranteed.

**User-visible outcome:**

- [x] Score breakdown explains the active components.
- [x] Scenario 4 demonstrates non-default operator weighting.

**Implementation work:**

- [x] Define named scoring components for individual bus wait, operator smoothness, and overall network time.
- [x] Score only hard-valid candidate schedules.
- [x] Include score breakdown in `ScheduleResult`.
- [x] Add sensitivity tests proving changed weights change component totals and, where available candidate alternatives permit, selected schedule order/choice.
- [x] Keep weight changes as one obvious scenario-data edit.

**Acceptance criteria:**

- [x] Changing scenario weights does not affect hard validity checks.
- [x] Scenario 4 is the required weight validation gate.
- [x] Score breakdown reports every active component and the weighted total.
- [x] Operator smoothness starts with operator wait/delay balance and is documented as the v1 assumption.

**Verification:**

- [x] Scoring unit tests for each component.
- [x] Sensitivity tests comparing Scenario 4 under default and operator-heavy weights.
- [x] Invariant tests still pass for all assignment scenarios after weighted selection.

**Likely files:**

- `src/scheduler/scoring.py`
- `src/scheduler/strategies/custom_heuristic.py`
- `src/domain/models.py`
- `src/reporting/metrics.py`
- `tests/test_scoring.py`
- `tests/test_scheduler_engine.py`

### Increment 7: Extensibility Proof And Architecture Sync (done)

**Goal:** Prove the design can absorb expected future changes without rewriting the engine.

**User-visible outcome:**

- [x] Assignment behavior is unchanged.
- [x] Docs can honestly show how to change weights and add a rule.

**Implementation work:**

- [x] Add a test-only soft scoring component through the same composition/registry path as built-in components.
- [x] Add a small non-assignment fixture with multiple chargers or a changed station capacity to prove capacity is data-driven.
- [x] Add or update docs that show how to change a weight and how to add a new soft rule.
- [x] Update `docs/ARCHITECTURE.md` with reality checks after scenario data, baseline scheduler, and weighted scoring.
- [x] Record major choices in `docs/DECISION_LOG.md`.

**Acceptance criteria:**

- [x] Adding a soft rule is localized to scoring registration/composition and tests.
- [x] Multiple charger capacity works through station data without changing assignment scenarios.
- [x] Architecture docs match actual module names and contracts.
- [x] Formal solver upgrade path is documented without adding runtime dependencies.

**Verification:**

- [x] Test-only score component participates in total score and score breakdown.
- [x] Multi-charger fixture passes reservation and reporting checks.
- [x] Docs search finds no stale module names or outdated scenario-order guidance.

**Likely files:**

- `src/scheduler/scoring.py`
- `src/scheduler/reservations.py`
- `tests/fixtures/`
- `tests/test_scoring.py`
- `tests/test_scheduler_engine.py`
- `docs/ARCHITECTURE.md`
- `docs/DECISION_LOG.md`

### Increment 8: Review-Ready Delivery

**Goal:** Make the repository, app, and docs match the assignment handoff expectations.

**User-visible outcome:**

- [ ] Hosted app and local app both support the full assignment demo flow.
- [ ] README and architecture docs explain how to run, test, change weights, add scenarios, and add rules.

**Implementation work:**

- Finalize README run/test/deploy instructions.
- Verify `requirements.txt` includes only needed runtime dependencies.
- Keep optional solver dependencies out of the initial runtime.
- Add final edge fixtures for exactly-at-range, impossible range, simultaneous station arrivals, and multiple operators.
- Do a final documentation consistency pass.

**Acceptance criteria:**

- [ ] Opening the app shows the scenario dropdown immediately.
- [ ] Every scenario shows readable input, per-bus timetable, and per-station queue.
- [ ] All five scenarios produce sensible, defensible results.
- [ ] Docs explain assumptions, framework choice, data structure design, anticipated future changes, weight changes, and new-rule additions.
- [ ] Streamlit Community Cloud status is checked or deployment instructions explain the hosted handoff.

**Verification:**

- [ ] Full test suite passes.
- [ ] `python -m compileall app.py src` passes.
- [ ] `streamlit run app.py` works from repo root.
- [ ] Manual app check cycles through all five scenarios.
- [ ] Docs search confirms solver prototypes are deferred, open questions are resolved, and no stale "one scenario first, rest later" guidance remains.

**Likely files:**

- `README.md` or `docs/README.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISION_LOG.md`
- `requirements.txt`
- `tests/fixtures/`

## Original Task Mapping

The original task ids in `docs/IMPLEMENTATION_PLAN.md` are preserved as the detailed library. Their vertical execution moves as follows:

| Original task area | Scenario-first increment |
| --- | --- |
| 0.1, 0.2, 0.3 harness and docs alignment | Increment 0 |
| 3.1 scheduler contract stub | Increment 0 |
| 7.1 scenario selection shell | Increment 0, completed across Increments 2-5 |
| 1.2 scenario JSON shape and all assignment scenarios | Increment 1 |
| 1.1, 1.3 domain models and route/time helpers | Increment 2 |
| 2.1, 2.3 loader and adapter errors | Increment 2 |
| 2.2 validation | Increment 3 |
| 7.2 scenario input rendering | Increment 3 |
| 3.2, 3.3, 3.4 hard constraints and final invariants | Increment 4 |
| 4.1, 4.2, 4.3, 4.4 baseline scheduler and timelines | Increment 4 |
| 10.1 invariant tests | Increment 4 |
| 6.1, 6.2, 6.3 reporting tables and metrics | Increment 5 |
| 7.3, 7.4 schedule and station views | Increment 5 |
| 5.1, 5.2, 5.3 weighted scoring and sensitivity | Increment 6 |
| 9.1, 9.3 selected extensibility proofs | Increment 7 |
| 8.1-8.6 solver research/prototypes | Deferred; document upgrade path only for initial product |
| 9.2, 9.4 broader future extensions | Deferred unless needed by implementation reality |
| 10.2 edge fixtures | Increment 8 |
| 10.3, 10.4 docs and delivery | Increment 8 |

## Parallelization Guidance

Safe to parallelize:

- Scenario JSON transcription after the schema is agreed.
- Reporting tests using handcrafted `ScheduleResult` fixtures after the contract shape exists.
- Documentation updates that record decisions already made.

Must stay sequential:

- Scenario schema before loader/domain mapping.
- Loader validation before scheduler consumes scenario data.
- Hard constraints before weighted scoring can select between candidates.
- Real schedule result shape before final UI/reporting polish.

Needs coordination:

- Any `ScheduleResult` shape change touches scheduler, reporting, UI, and tests.
- Any scenario schema change touches data files, adapters, docs, and input rendering.
- Any scoring component change touches scoring, result breakdown, and docs.

## Risks And Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scenario data transcription errors | High | Encode all scenarios early and test bus counts, weights, and departure windows. |
| Streamlit grows scheduling logic | High | Keep an orchestration seam and render only domain/reporting objects in UI. |
| Hard constraints and scoring become tangled | High | Reject invalid candidates before scoring; invariant-test every final result. |
| Weight sensitivity is invisible | Medium | Make Scenario 4 the scoring gate and expose score breakdown. |
| Station queues miss directional interleaving | Medium | Test Scenarios 2 and 5 station views with both directions. |
| Data structure lacks extensibility proof | Medium | Add one soft-rule plug-in test and one capacity fixture before delivery. |
| Formal solver work consumes assignment time | Medium | Defer prototypes; keep the strategy interface and document upgrade paths. |
| Docs drift from implementation | Medium | Update architecture and decision log at scenario data, scheduler, and scoring checkpoints. |

## Definition Of Done For Initial Product

- [ ] All five assignment scenarios live in `data/scenarios/`.
- [ ] Scenario loader and validator reject malformed input before scheduling.
- [ ] Scenario weights are loaded, displayed, and included in schedule scoring/reporting.
- [ ] Scheduler produces deterministic `ScheduleResult` objects through a stable contract.
- [ ] Final schedules satisfy range, route order, and charger capacity constraints.
- [ ] Per-bus timetable shows charging stations, waits, and final arrival.
- [ ] Per-station view shows chronological bus order at A, B, C, and D, including interleaved directions.
- [ ] Weighted scoring includes individual, operator, and overall components with breakdown.
- [ ] Scenario 4 proves non-default operator weighting is handled.
- [ ] Scenarios 2 and 5 prove contention and interleaving behavior.
- [ ] Tests cover domain helpers, adapters, constraints, engine behavior, scoring, reporting, and invariants.
- [ ] Docs explain how to run, test, change weights, add a scenario, add a rule, and understand assumptions.
- [ ] The app supports the assignment demo flow: open app, choose scenario, inspect input, inspect per-bus timetable, inspect per-station order, repeat for all five scenarios.

## Deferred Work

The following items are intentionally out of initial-product scope unless implementation reality requires them:

- Runnable OR-Tools CP-SAT, Z3, PuLP, or MILP prototypes.
- A Streamlit solver selection dropdown.
- Interactive Streamlit weight editing.
- Station outage windows.
- Variable charging policies beyond data/default threading.
- Multiple routes or shared-route networks beyond data model foresight.

These remain natural future paths because the scheduler contract, scenario data model, hard-constraint modules, and scoring composition are designed to accept them without rewriting the UI/reporting surface.
