# Scheduler Engine Evolution - Context Note

**Current status:** The app includes a "Solver Engine" selector backed by `src/scheduler/strategies/registry.py`. `CustomHeuristicStrategy` remains the default strategy. `CpSatStrategy` is registered as the first experimental alternate strategy and appears when OR-Tools is available.

## The Core Question

The scheduler engine started as a custom deterministic implementation. The project now supports multiple engines with runtime selection, including an experimental OR-Tools CP-SAT strategy. This note records why the strategy pattern was chosen over replacing the engine in-place.

---

## The Two Approaches

| Dimension | In-Place Replacement | Strategy Pattern with Selector |
|---|---|---|
| Mechanism | One engine at a time | Separate strategy classes selected through the registry |
| Code churn per swap | High | Low |
| Ability to compare solvers | Hard without branch hopping | Built in |
| Benchmarking | Requires manual snapshots | Same scenarios can run against all registered strategies |
| UI complexity | Zero initially | Small and already implemented |
| Testing overhead | One concrete engine | Contract tests can run against every available strategy |
| Fallback if solver fails | Revert the engine | Keep the custom heuristic available |
| Hybrid approaches | Awkward | Natural: a strategy can call another strategy internally |

---

## Recommended Approach

Use the strategy pattern and keep the UI selector backed by the strategy registry.

The strategy interface is the critical boundary: every solver implements `schedule(scenario) -> ScheduleResult`. The selector is a thin shell over registered, available strategies. This keeps solver research, fallback behavior, and stakeholder comparison available without rewiring the app.

### Phased Path

**Phase A - Baseline implementation**

- Define the `SchedulerStrategy` protocol in `src/scheduler/contract.py`:

  ```python
  class SchedulerStrategy(Protocol):
      def schedule(self, scenario: Scenario) -> ScheduleResult:
          ...
  ```

- Implement `CustomHeuristicStrategy`.
- Register it as `custom_heuristic`.
- Wire the Streamlit "Solver Engine" selector to `list_strategy_options()`.
- Run contract tests against available strategies.

**Phase B - Experimental CP-SAT strategy**

- Implement CP-SAT behind the same protocol.
- Keep OR-Tools optional and hide CP-SAT from the available strategy list when it cannot be imported.
- Use the custom heuristic result as a warm-start hint when it can be mapped cleanly.
- Return `SolverDiagnostics` so the UI can show status, objective quality, proof gap, runtime, and hint usage.

**Phase C - Production solver adoption**

- Promote a solver to default only after correctness, objective behavior, runtime, and deployment cost are accepted.
- Keep `CustomHeuristicStrategy` available for explainability, fallback, and comparison.
- Change the registry default; no UI or reporting rewrite should be needed.

---

## Key Design Constraints

1. **The contract must be solver-agnostic.** `ScheduleResult` may include diagnostics, but it must not leak CP-SAT variables, intervals, or other solver internals.

2. **Hard constraints are shared.** Every strategy must produce schedules that satisfy range, route order, and charger capacity. `finalize_schedule_result()` remains the post-strategy validation point.

3. **Candidate generation can be shared.** The custom heuristic and CP-SAT strategy both use `src/scheduler/candidates.py` to keep range-feasible station sequence generation consistent.

4. **Strategy metadata belongs in the registry.** `StrategyOption` reports id, label, description, experimental flag, and availability. Strategy classes only need to implement `schedule(scenario)`.

5. **Dependencies are isolated.** Solver libraries should be optional extras. CP-SAT uses `requirements-solver-cpsat.txt`, and `is_ortools_available()` controls whether the strategy appears as available.

---

## Relationship to the Current Implementation

- `src/scheduler/contract.py` defines `SchedulerStrategy`, `ScheduleResult`, and `SolverDiagnostics`.
- `src/scheduler/strategies/registry.py` owns `DEFAULT_STRATEGY_ID`, `StrategyOption`, and the strategy factories.
- `src/app_view_model.py` selects the strategy and runs it.
- `src/ui/layout.py` renders the "Solver Engine" selector.
- `src/reporting/metrics.py` transforms solver diagnostics into UI rows.
- `tests/test_strategy_registry.py` verifies default selection, availability behavior, and contract behavior for available strategies.
- `tests/test_cp_sat_strategy.py` verifies CP-SAT feasibility, invariant validity, diagnostics, and heuristic hint usage when OR-Tools is installed.

The architecture decision is now implemented: strategy selection is explicit, the custom heuristic remains the default baseline, and CP-SAT is an optional experimental optimizer rather than an in-place replacement.
