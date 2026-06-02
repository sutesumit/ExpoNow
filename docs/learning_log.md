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
├── data/
│   └── data/scenarios/         # One JSON file per scenario — the data layer
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

## 2026-05-30: Increment 0 — Junior Developer Learning Targets

### Python Fundamentals

| Concept | Where | Why It Matters |
|---|---|---|
| **`@dataclass(frozen=True)`** | `scenario.py`, `contract.py`, `app_view_model.py` | Immutability guarantees value semantics across layer boundaries; prevents accidental mutation bugs; enables use as dict keys and safe sharing across threads. |
| **`Protocol` (structural subtyping)** | `scheduler/contract.py` | Duck typing enforced at the type-checker level. Any class with a `schedule(scenario)` method satisfies `SchedulerStrategy` — no `extends`, no `ABC`, no inheritance tax. |
| **Generic type annotations** | `list[ScenarioSummary]`, `dict[str, Any]` | Makes function signatures self-documenting; caught by `pyright`/`mypy` before tests run. |
| **`__init__.py` with `__all__`** | `src/domain/__init__.py`, `src/scheduler/__init__.py` | Explicit public API vs. implicit package exports — consumers know exactly what's available without spelunking submodules. |
| **`if __name__ == "__main__"` guard** | `app.py` | Ensures a file is both safely importable (no side effects) and runnable as a script. |

### Testing Patterns

- **`unittest.TestCase`** — `self.assertEqual` gives better failure messages than bare `assert`, integrates with test runners and CI reporting.
- **Test without Streamlit** — `build_initial_view_model` is tested purely; no Streamlit import needed. Tests run in milliseconds, not seconds.
- **Boundary enforcement tests** — `test_scheduler_package_does_not_import_streamlit` greps source files for forbidden imports. This architectural rule is automated and can't be violated silently.
- **Contract tests** — `test_stub_scheduler_returns_schedule_result_contract` validates every field of `ScheduleResult`. When a real scheduler is written, it must pass the same contract test.

### Design Patterns

| Pattern | Where | What It Teaches |
|---|---|---|
| **Strategy pattern** (via `Protocol`) | `SchedulerStrategy` | Swap algorithms without touching callers. The stub is a strategy; the real solver will be another. No `if-else` branching on algorithm type. |
| **Ports-and-adapters (Hexagonal)** | Full `src/` layout | The domain has zero imports from infrastructure. Tests can run the scheduler without a browser. Swapping Streamlit for a CLI means changing `ui/` and nothing else. |
| **View model** | `app_view_model.py` | Transforms domain data into a UI-ready shape. Keeps `app.py` thin (3 lines of `main()`) and makes render logic separately testable. |
| **Stub** | `scheduler/stub.py` | A placeholder that lets the full system run end-to-end before the real component exists. Enables parallel work on UI and engine. |

### Architecture to Own

```
src/
  domain/       # pure business concepts, zero infrastructure imports
  adapters/     # I/O, parsing, external data — depends on domain
  scheduler/    # algorithmic core behind a Protocol — depends on domain
  ui/           # Streamlit rendering — depends on domain
  reporting/    # display transformations — depends on domain
```

Key rules:
- **Depend inward** — `ui/` → `domain/`, `adapters/` → `domain/`, `scheduler/` → `domain/`. Never the reverse.
- **Frozen by default** — ask "can this be immutable?" before adding setters.
- **Protocol over inheritance** — structural typing means zero coupling to base classes.
- **Tests enforce architecture** — a test that greps for `import streamlit` in scheduler files is replicable for any layering rule.

### What This Unlocks

A junior developer who owns this codebase walks away able to:
1. Organize a Python project beyond a single `main.py`
2. Use immutability as a default design choice
3. Write tests that verify behavior *and* enforce architectural boundaries
4. Apply the strategy pattern to make algorithms swappable without call-site changes
5. Separate orchestration from rendering (view model pattern)
6. Explain why layering matters — and prove it with passing/failing tests
