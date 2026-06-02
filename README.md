# Bus Charging Scheduler

A Python + Streamlit application that schedules electric bus charging across 4 stations on a fixed route, optimizing for individual wait times, operator smoothness, and overall network efficiency.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Commands

```bash
# Run the app
streamlit run app.py

# Run tests
python -m unittest

# Verify compilation
python -m compileall app.py src
```

## Project Structure

```
.
├── app.py              # Streamlit UI entry point
├── src/                # Python source root
│   ├── domain/         # Stable domain models and helpers
│   ├── adapters/       # Data loading, validation, errors
│   ├── scheduler/      # Scheduling engine and constraints
│   ├── reporting/      # Display transformation of results
│   └── ui/             # Streamlit render helpers
├── data/
│   └── scenarios/      # Scenario definition files (JSON)
│       ├── scenario_1.json
│       ├── scenario_2.json
│       ├── scenario_3.json
│       ├── scenario_4.json
│       └── scenario_5.json
├── tests/              # Test suite (130+ tests)
│   └── fixtures/       # Edge-case scenario fixtures
├── README.md           # Project root README
├── ARCHITECTURE.md     # Design decisions, data structures, extensibility
└── docs/               # Decision log, implementation plans
    ├── decision_log.md
    ├── implementation_plan.md
    ├── vertical_implementation_plan.md
    └── ...
```

## Deployment

Deploy to [Streamlit Community Cloud](https://streamlit.io/cloud) by connecting your GitHub repository. The app is currently hosted at https://exponow.streamlit.app/.

## Extensibility

The architecture is designed so that common future changes require data edits or small module additions — never rewrites.

### Change Matrix

| Change | What it takes |
|---|---|
| **New scenario** | Create a new JSON file in `data/scenarios/`. The catalog discovers files by filename convention (`scenario_*.json`). |
| **New station** | Add a station entry to the JSON and update route segments. Data-only. |
| **Multiple chargers at a station** | Change `charger_count` in the station object. The `ReservationManager` already supports per-lane scheduling. |
| **New operator** | Write the operator name in bus data. Operators are free-text strings. |
| **New scoring rule** | Write one scoring function, register it in `SCORE_COMPONENTS`, add its weight to the scenario JSON. |
| **New scheduling algorithm** | Create a strategy class with `schedule(scenario)`, then register it in `src/scheduler/strategies/registry.py`. The solver selector reads registered available strategies. |
| **Scenario battery range** | Change `charging_policy.range_km` in the scenario JSON. Per-bus range is not currently modeled. |
| **Scenario charge time** | Change `charging_policy.full_charge_minutes` in the scenario JSON. Per-station charge duration is not currently modeled. |
| **Replace Streamlit with CLI** | Rewrite `src/ui/` and `app.py`. Domain, adapters, scheduler, and reporting remain untouched. |

### Weight tuning (no code change)

Edit the `weights` object in any scenario JSON file under `data/scenarios/`. Weights are applied at runtime — no code changes needed.

```json
{
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 1.0
  }
}
```

### Adding a scoring rule

1. Write a scoring function in `src/scheduler/scoring.py` (see `compute_individual_wait_score` for a pattern).
2. Wrap it in a component function that returns `(name, {"unweighted": …, "weighted": …, "weight": …, "description": …})`.
3. Register the component in `SCORE_COMPONENTS` — the registry automatically includes new components in the total weighted score.
4. Add the corresponding weight key to each scenario JSON (or use a default in `Weights`).

### Adding a scheduler strategy

1. Create a strategy class with `schedule(scenario) -> ScheduleResult`
2. Register its option and factory in `src/scheduler/strategies/registry.py`
3. Keep optional solver dependencies guarded so unavailable strategies are not shown in the Streamlit selector

The app view model selects strategies through the registry, and the UI renders the available options as the "Solver Engine" selector.

## Documentation

- `ARCHITECTURE.md` — design decisions, data structures, scoring components, and extensibility guide
- `docs/decision_log.md` — chronological decision tracking
- `docs/vertical_implementation_plan.md` — scenario-first vertical build plan

## Assumptions

See `ARCHITECTURE.md` for the full list of assumptions made during implementation.
