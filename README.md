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
| **New scheduling algorithm** | Create a class with a `schedule(scenario)` method in `strategies/`. Swap the import in `app_view_model.py`. |
| **Variable battery range per bus** | Add `range_km` to the bus object in JSON; the scheduler reads per-bus range with a policy default fallback. |
| **Different charge time per station** | Add `charge_minutes` to the station object in JSON; the scheduler uses it with a policy default fallback. |
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

## Documentation

- `docs/ARCHITECTURE.md` — design decisions, data structures, scoring components, and extensibility guide
- `docs/DECISION_LOG.md` — chronological decision tracking
- `docs/VERTICAL_IMPLEMENTATION_PLAN.md` — scenario-first vertical build plan

## Assumptions

See `docs/ARCHITECTURE.md` for the full list of assumptions made during implementation.
