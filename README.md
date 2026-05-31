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

## How to Change a Weight

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

## How to Add a Scenario

Add a new JSON file to `data/scenarios/` following the same schema as the existing scenarios. The loader auto-discovers all `scenario_*.json` files.

## How to Add a Soft Rule

Register a scoring function in `SCORE_COMPONENTS` in `src/scheduler/scoring.py`. The registry automatically includes new components in the total weighted score. See `docs/ARCHITECTURE.md` for a detailed example.

## Documentation

- `docs/ARCHITECTURE.md` — design decisions, data structures, scoring components, and extensibility guide
- `docs/DECISION_LOG.md` — chronological decision tracking
- `docs/VERTICAL_IMPLEMENTATION_PLAN.md` — scenario-first vertical build plan

## Assumptions

See `docs/ARCHITECTURE.md` for the full list of assumptions made during implementation.
