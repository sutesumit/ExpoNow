# Bus Charging Scheduler

A Python + Streamlit application that schedules electric bus charging across 4 stations on a fixed route, optimizing for individual wait times, operator smoothness, and overall network efficiency.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Or deploy to [Streamlit Community Cloud](https://streamlit.io/cloud) by connecting your GitHub repo.

## Project Structure

```
.
├── app.py              # Streamlit UI entry point
├── scheduler/          # Core scheduling logic
│   ├── __init__.py
│   ├── engine.py       # Main scheduler engine
│   ├── constraints.py  # Hard constraint validators
│   ├── objective.py    # Soft rule objective function
│   └── models.py       # Data models (Route, Bus, Scenario, etc.)
├── scenarios/          # Scenario definition files (JSON)
│   ├── scenario_1.json
│   ├── scenario_2.json
│   ├── scenario_3.json
│   ├── scenario_4.json
│   └── scenario_5.json
├── ARCHITECTURE.md     # Design decisions and scalability rationale
└── DECISION_LOG.md     # Chronological decision tracking
```

## How to Change a Weight

Edit the `weights` object in any scenario JSON file:

```json
{
  "name": "Scenario 4 - Operator-heavy",
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 1.0
  },
  "buses": [...]
}
```

Weights are applied at runtime - no code changes needed.

## How to Add a New Rule

1. Add the rule to `scheduler/objective.py` as a new penalty function
2. Add the weight to the `Weights` dataclass in `scheduler/models.py`
3. Include the new penalty in `compute_objective()`

See ARCHITECTURE.md for detailed code examples.

## Assumptions

See ARCHITECTURE.md for full list of assumptions made during implementation.