# Architecture Overview

## Framework / Approach for the Scheduler

### Chosen Approach: Strategy-Based Scheduling with Weighted Scoring

**Framework:** Swappable scheduler strategies behind one `schedule(scenario) -> ScheduleResult` contract.

The default engine is `CustomHeuristicStrategy`, a deterministic greedy scheduler that uses shared candidate generation, reservation, scoring, and timeline helpers. `CpSatStrategy` is an experimental alternate engine that uses OR-Tools CP-SAT when the optional dependency is installed. CP-SAT uses the custom heuristic result as a warm-start hint when that result can be mapped cleanly into the CP-SAT decision variables.

**Why this approach fits:**

1. **Multi-objective optimization:** The problem balances individual wait, operator smoothness, and overall network efficiency with scenario-level weights.
2. **Hard constraints are absolute:** Range limits, route ordering, and charger capacity must always be satisfied.
3. **Swappable engines:** The strategy registry lets the app compare the deterministic heuristic with optional formal solvers without changing UI or reporting code.
4. **Deterministic baseline:** The custom heuristic remains the default, explainable fallback even when experimental solvers are available.

**Alternatives considered:**

- Pure simulation: rejected because contention requires rollback/retry logic that becomes hard to reason about.
- Genetic algorithms: rejected for this scale because they are less interpretable and harder to validate.
- In-place solver replacement: rejected because it makes comparison, fallback, and benchmarking harder than a strategy registry.

### Core Architecture

```text
Streamlit UI Layer
  - Scenario selector
  - Solver Engine selector
  - Input display, bus timetables, station queues, metrics
        |
        v
View Model Orchestration (`src/app_view_model.py`)
  - Loads and validates scenarios
  - Reads available strategies from `src/scheduler/strategies/registry.py`
  - Runs the selected strategy
        |
        v
Scheduler Layer
  - Strategy registry: `custom_heuristic` default, `cp_sat` experimental
  - Strategy implementations: `CustomHeuristicStrategy`, `CpSatStrategy`
  - Shared helpers: candidates, constraints, reservations, results, scoring, timeline
        |
        v
Reporting Layer
  - Transforms `ScheduleResult` into display rows
  - Renders metrics, score breakdown, and solver diagnostics
        |
        v
Data Layer
  - Scenario definitions, routes, stations, policies, weights, buses
```

`ScheduleResult` is the cross-layer contract: scheduler strategies produce it, the reporting layer transforms it, and the UI renders it. No layer below the UI imports Streamlit.

---

## Data Structure Design

### Core Entities (Domain - `src/domain/models.py`)

```python
@dataclass(frozen=True)
class Segment:
    from_stop: str
    to_stop: str
    distance_km: int

@dataclass(frozen=True)
class Route:
    name: str
    stops: list[str]
    segments: list[Segment]

@dataclass(frozen=True)
class Station:
    id: str
    charger_count: int

@dataclass(frozen=True)
class ChargingPolicy:
    range_km: int = 240
    full_charge_minutes: int = 25

@dataclass(frozen=True)
class TravelPolicy:
    speed_kmph: int = 60

@dataclass(frozen=True)
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0

@dataclass(frozen=True)
class Bus:
    id: str
    operator: str
    direction: str
    departure_minutes: int

@dataclass(frozen=True)
class Scenario:
    schema_version: int
    id: str
    name: str
    description: str
    route: Route
    stations: list[Station]
    buses: list[Bus]
    charging_policy: ChargingPolicy
    travel_policy: TravelPolicy
    weights: Weights
```

### Core Entities (Contract - `src/scheduler/contract.py`)

```python
@dataclass(frozen=True)
class TimelineEvent:
    event_type: str
    minutes: int
    location: str
    description: str

@dataclass(frozen=True)
class BusPlan:
    bus_id: str
    operator: str
    direction: str
    events: list[TimelineEvent]
    final_arrival_minutes: int | None = None

@dataclass(frozen=True)
class StationReservation:
    station: str
    bus_id: str
    charger_lane: int
    start_minutes: int
    end_minutes: int

@dataclass(frozen=True)
class ScheduleMetrics:
    total_buses: int
    total_charge_stops: int
    total_wait_minutes: int
    max_wait_minutes: int

@dataclass(frozen=True)
class ScoreBreakdown:
    components: dict[str, dict[str, float]]
    total_weighted: float

@dataclass(frozen=True)
class SolverDiagnostics:
    solver_name: str
    status_name: str
    objective_value: float | None
    best_objective_bound: float | None
    optimality_gap: float | None
    wall_time_seconds: float
    conflict_count: int
    branch_count: int
    search_workers: int
    time_limit_seconds: float
    used_heuristic_hint: bool
    heuristic_objective_value: float | None
    objective_improvement: float | None

@dataclass(frozen=True)
class ScheduleResult:
    feasible: bool
    scenario_id: str
    bus_plans: list[BusPlan] = field(default_factory=list)
    station_reservations: list[StationReservation] = field(default_factory=list)
    metrics: ScheduleMetrics | None = None
    warnings: list[str] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None
    solver_diagnostics: SolverDiagnostics | None = None

class SchedulerStrategy(Protocol):
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        ...
```

### Solver Diagnostics

`SolverDiagnostics` is optional and solver-specific in content but solver-agnostic in shape. The custom heuristic leaves it empty. CP-SAT populates it with:

- solver status (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, etc.)
- objective value, best objective bound, and optimality gap
- wall time, conflict count, branch count, search worker count, and time limit
- whether the custom heuristic result was accepted as a warm-start hint
- the heuristic objective value and objective improvement when comparison is possible

Reporting renders these diagnostics as display rows. Solver internals such as CP-SAT variables and intervals never leave the strategy implementation.

### Folder Meaning

- `data/scenarios/` is the canonical home for assignment scenarios and future scenario variants.
- `src/domain/` holds stable value objects used across the system.
- `src/adapters/` handles loading, parsing, normalization, defaults, and validation of external input.
- `src/scheduler/` contains reusable scheduling logic and must stay free of Streamlit imports.
- `src/scheduler/strategies/` contains concrete scheduler engines.
- `src/reporting/` transforms schedule objects into tables and display-ready rows.
- `src/ui/` contains Streamlit rendering helpers only.

---

## Scenario Data

Each scenario file under `data/scenarios/` is self-contained and data-only:

- `schema_version`: integer version for future migrations
- `id`, `name`, `description`: scenario identity and display metadata
- `route`: ordered route stops plus segment distances
- `stations`: scheduling stations with `charger_count`
- `charging_policy`: scenario-level battery range and full-charge duration
- `travel_policy`: scenario travel speed
- `weights`: individual, operator, and overall weights
- `buses`: bus rows with `id`, `operator`, `direction`, and `departure`

Current supported operational knobs are scenario-level `charging_policy.range_km`, scenario-level `charging_policy.full_charge_minutes`, and station-level `charger_count`. Per-bus battery range and per-station charge duration are not currently modeled.

---

## Anticipated Future Changes & Handling

### Multiple Chargers Per Station

**Status:** Already supported.

Change `charger_count` in station data. `ReservationManager` creates that many lane schedules per station, strategies reserve lane-specific charger slots, and reporting surfaces station queues by lane. This is proven by the `scenario_multi_charger.json` fixture.

### Station Outages or Maintenance Windows

Add availability windows or status flags to station data, validate them in the adapter layer, and teach each strategy to treat those intervals as unavailable. Reporting can remain driven by `ScheduleResult`.

### Priority Buses

Add a priority field to `Bus`, then add a scoring component or strategy-specific objective term. The default scoring path should remain centralized in `src/scheduler/scoring.py`.

### Time-of-Day Electricity Costs

Add a cost matrix to scenario data and register a new scoring component. If a solver should optimize it directly, add a matching objective term in the relevant strategy.

### Driver Shifts

Add driver availability windows to scenario data and enforce them as hard constraints in validation and strategy logic. Final invariant validation should still run after strategy output.

### Multiple Routes or Shared Stations

Represent routes and station identifiers in data. A shared station remains one resource with one set of lane reservations, regardless of which route produced the arrival.

### New Operators

`Bus.operator` is free text. New operators are data-only unless new operator-specific business rules are introduced.

### Variable Charging Times

Current support is scenario-level only through `charging_policy.full_charge_minutes`. If bus-specific or station-specific duration is needed later, add a duration field to the domain model, update the loader and validator, and update every strategy to use that duration consistently.

---

## Changing a Weight

Weights are defined in each scenario JSON file:

```json
{
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 1.0
  }
}
```

Weights can also be changed programmatically with immutable dataclass replacement:

```python
from dataclasses import replace
from src.domain.models import Weights

new_weights = Weights(individual=0.5, operator=3.0, overall=1.5)
updated_scenario = replace(scenario, weights=new_weights)
```

The scoring components read `scenario.weights.individual`, `scenario.weights.operator`, and `scenario.weights.overall`.

---

## Scoring Components

Three built-in score components are computed for finalized schedules:

1. **Individual Wait (`individual_wait`)**: total bus wait minutes, weighted by `weights.individual`.
2. **Operator Smoothness (`operator_smoothness`)**: imbalance between each operator's average wait and the fleet average, weighted by `weights.operator`.
3. **Overall Network (`overall_network`)**: total journey time from departure to final arrival for all buses, weighted by `weights.overall`.

Lower scores are better. `ScoreBreakdown.total_weighted` is the sum of all weighted component values.

### Scoring Component Registry

`src/scheduler/scoring.py` owns the `SCORE_COMPONENTS` registry. Each component function receives `(ScheduleResult, Scenario)` and returns `(name, component_dict)`.

### Adding a New Rule

To add a soft rule:

1. Write a component function in `src/scheduler/scoring.py`.
2. Register it in `SCORE_COMPONENTS`.
3. Add a weight to `Weights` and scenario JSON only if the new rule needs its own tunable weight.

`compute_score_breakdown()` iterates the registry, so registered components automatically participate in the total weighted score.

### Per-Bus Candidate Scoring in the Heuristic

`CustomHeuristicStrategy` scores feasible candidates per bus using:

```text
weights.individual * candidate_wait_minutes
+ weights.overall * candidate_travel_time
```

Operator smoothness is computed after the full schedule because it depends on global operator-level averages. After all buses are scheduled, `finalize_schedule_result()` computes metrics, scoring, and invariant validation.

---

## Swappable Scheduler Engines

The scheduler is behind one contract:

```python
def schedule(scenario: Scenario) -> ScheduleResult:
    ...
```

The current registry lives in `src/scheduler/strategies/registry.py`.

- `DEFAULT_STRATEGY_ID` is `custom_heuristic`.
- `custom_heuristic` is always available and non-experimental.
- `cp_sat` is experimental and available only when OR-Tools can be imported.
- `list_strategy_options()` returns available strategies for the UI selector.
- `list_strategy_options(include_unavailable=True)` exposes unavailable strategies for diagnostics and tests.

To add a scheduler:

1. Create a strategy class with `schedule(scenario) -> ScheduleResult`.
2. Add a `StrategyOption` factory and strategy factory to the registry.
3. Guard optional dependencies so unavailable solvers return a clear warning rather than breaking imports.
4. Add contract tests that run the strategy against representative scenarios and validate invariants.

The UI and reporting code should only depend on `ScheduleResult`, not on the internal solver strategy.

### CP-SAT Strategy

`CpSatStrategy` is the first experimental alternate strategy.

- **Dependency:** OR-Tools is optional; if unavailable, the strategy returns an infeasible `ScheduleResult` with an installation warning.
- **Candidate space:** uses shared `generate_candidates()` so range-feasible station sequences stay consistent with the custom heuristic.
- **Objective:** minimizes scaled individual wait plus scaled overall journey time. Operator smoothness remains part of post-hoc score reporting, not the CP-SAT objective.
- **Warm start:** runs `CustomHeuristicStrategy` first and maps its chosen candidate, charge starts, and charger lanes into CP-SAT hints when possible.
- **Validation:** decoded CP-SAT solutions still go through `finalize_schedule_result()`, which computes metrics, scoring, and hard invariant validation.
- **Diagnostics:** records CP-SAT status, objective/bound/gap, runtime/search effort, time limit, hint usage, heuristic objective, and objective improvement.

See `docs/scheduler_engine_evolution.md` for the solver strategy rationale.

---

## Architecture Review Checkpoints

- After scenario data changes, confirm the scenario schema and defaults are still documented accurately.
- After scheduler contract changes, confirm `ScheduleResult`, `SolverDiagnostics`, and hard invariant validation are documented.
- After scoring changes, confirm `SCORE_COMPONENTS` and weight examples match the implementation.
- After strategy changes, confirm the registry, selector visibility, dependency behavior, and contract tests are documented.
- After CP-SAT changes, confirm optional OR-Tools behavior, warm-start hints, objective terms, and diagnostics match the implementation.

---

## Assumptions Made

1. Speed is constant for all buses within a scenario.
2. Charging uses full-charge sessions only.
3. Scenario range and charge duration apply globally unless the domain model is extended.
4. Buses do not charge at route endpoints.
5. Wait time includes queueing from station arrival until charger availability.
6. Hard constraints are validated after each strategy returns a schedule.
7. The custom heuristic remains the default strategy and fallback baseline.
8. CP-SAT remains experimental until performance, deployment, and objective behavior are accepted.
