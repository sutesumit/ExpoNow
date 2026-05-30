# Learning Log: Streamlit

## 2026-05-29: Streamlit Execution Model & Its Impact on This Project

### How Streamlit Works

Streamlit is a Python framework that turns Python scripts into interactive web apps. The fundamental model:

**Top-to-bottom execution on every interaction.**
- The script (`app.py`) runs from top to bottom every time a user interacts with any widget (selectbox, slider, button).
- Widget state is managed by Streamlit automatically — each widget binds to a Python variable.
- On rerun, the script re-executes with the new widget value.

**Caching for performance.**
- `@st.cache_data` / `@st.cache_resource` memoizes expensive operations (loading a scenario file, running the scheduler) so they don't re-execute on every interaction if inputs haven't changed.
- `@st.cache_resource` is for non-data objects (database connections, model instances).

**No request/response model to write.**
- The developer writes a linear script. Streamlit handles the HTTP server, WebSocket connection, and DOM diffing.
- Input/state is widget-bound, not request-bound.

**Rendering is Python-native.**
- `st.write()`, `st.dataframe()`, `st.markdown()`, `st.selectbox()` — all called from Python.
- No HTML templates, no JSX, no component lifecycle to manage.

### What Streamlit Removes / Eases

| Responsibility | How Streamlit Handles It |
|---|---|
| **Frontend framework** | No React/Vue/Svelte to install, learn, or maintain |
| **HTTP routing** | No Flask/FastAPI routes; one script, one URL |
| **State management** | No Redux, Zustand, or React Context — just Python variables bound to widgets |
| **Client-server protocol** | WebSocket + DOM diffing is built-in and invisible to the developer |
| **Build tooling** | No webpack, Vite, Babel, TypeScript compiler |
| **Hosting/DevOps** | Streamlit Community Cloud: connect GitHub repo → deployed. Reads `requirements.txt`, auto-installs, auto-restarts on push |
| **Authentication** | Not needed for this assignment (no auth, no DB, no maps per spec) |
| **Static assets** | No CSS/JS bundle to manage; Streamlit provides a default theme |
| **Session handling** | Widget state is automatically scoped to the browser session |

### What We Focus On Instead

Because Streamlit absorbs the entire web-app surface area, development effort is redirected to the actual problem:

1. **Scheduling logic** — the constraint engine, objective functions, and search strategy
2. **Data model design** — `models.py`, scenario format, how entities relate and extend
3. **Correctness** — hard constraint validation (range, charger exclusivity, route order)
4. **Tunability** — weights as first-class dataclass fields, not scattered constants
5. **Simulation clarity** — computing timelines, wait times, arrival times — the product

In short: Streamlit eliminates the "make it a website" problem so we can solve the "make it schedule buses" problem.

### Repo Structure

The repo structure is flat by design — one process, one entry point, no build step:

```
bus-charging-scheduler/
│
├── app.py                      # Entry point. Streamlit picks this up.
│                                  Imports scenario loader, runs scheduler,
│                                  calls UI components.
│
├── requirements.txt            # streamlit, pandas (for tables), any OR lib
│
├── README.md                   # How to run, change weights, add rules
├── ARCHITECTURE.md             # Design rationale, data model, anticipated changes
├── DECISION_LOG.md             # Chronological decisions made during development
├── LEARNING_LOG.md             # This file — technical notes about the stack
│
├── scheduler/                  # Core domain logic (no Streamlit imports here)
│   ├── __init__.py
│   ├── engine.py               # Constraint-based scheduling engine
│   ├── models.py               # Dataclasses: Route, Bus, Scenario, Weights, ChargingPlan
│   ├── constraints.py          # Hard-rule validators (range, charger exclusivity)
│   └── objective.py            # Soft-rule objective functions (individual, operator, overall)
│
├── scenarios/                  # One JSON file per scenario — the data layer
│   ├── scenario_01.json
│   ├── scenario_02.json
│   ├── scenario_03.json
│   ├── scenario_04.json
│   └── scenario_05.json
│
└── ui/                         # Streamlit UI components (callable from app.py)
    ├── __init__.py
    ├── scenario_view.py        # Scenario input display
    ├── bus_timetable.py        # Per-bus timeline
    └── station_view.py         # Per-station charging order
```

**Key pattern:** `scheduler/` contains zero Streamlit imports. It is pure Python domain logic, testable without a browser. `ui/` and `app.py` are the only Streamlit-dependent files. This means scheduling logic can be unit-tested with `pytest` alone.

### Deployment: 2 Clicks from GitHub

1. Push repo to GitHub (public)
2. Go to https://share.streamlit.io → sign in with GitHub
3. Deploy → select repo → set entry point to `app.py`
4. Streamlit reads `requirements.txt`, installs deps, hosts at `https://<user>-bus-charging-scheduler.streamlit.app`

No `Dockerfile`, no `Procfile`, no `nginx.conf`. The assignment spec: *"We're not testing UI skills or DevOps here."*
