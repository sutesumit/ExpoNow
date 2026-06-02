from src.reporting.tables import build_station_queue_rows
from src.scheduler.contract import ScheduleResult, ScoreBreakdown


def build_summary_metrics(result: ScheduleResult) -> list[dict]:
    if result.metrics is None:
        return []

    metrics = []
    metrics.append({"Metric": "Total Buses", "Value": result.metrics.total_buses})
    metrics.append(
        {
            "Metric": "Total Charge Stops",
            "Value": result.metrics.total_charge_stops,
        }
    )
    metrics.append(
        {"Metric": "Total Wait (min)", "Value": result.metrics.total_wait_minutes}
    )
    metrics.append(
        {
            "Metric": "Max Individual Wait (min)",
            "Value": result.metrics.max_wait_minutes,
        }
    )

    station_rows = build_station_queue_rows(result)
    for station_id in sorted(station_rows.keys()):
        total_wait = sum(r["Wait (min)"] for r in station_rows[station_id])
        metrics.append(
            {
                "Metric": f"Station {station_id} Total Wait (min)",
                "Value": total_wait,
            }
        )

    return metrics


_COMPONENT_LABELS = {
    "individual_wait": "Individual Wait",
    "operator_smoothness": "Operator Smoothness",
    "overall_network": "Overall Network",
}


def build_score_rows(score_breakdown: ScoreBreakdown | None) -> list[dict]:
    if score_breakdown is None:
        return []

    rows: list[dict] = []
    component_order = ["individual_wait", "operator_smoothness", "overall_network"]
    for comp_name in component_order:
        comp = score_breakdown.components.get(comp_name)
        if comp is None:
            continue
        label = _COMPONENT_LABELS.get(comp_name, comp_name)
        rows.append(
            {
                "Component": label,
                "Raw Score (min)": _format_optional_number(comp["unweighted"]),
                "Weight": _format_optional_number(comp["weight"]),
                "Weighted Score (min)": _format_optional_number(comp["weighted"]),
                "Description": comp.get("description", ""),
            }
        )

    rows.append(
        {
            "Component": "TOTAL",
            "Raw Score (min)": "",
            "Weight": "",
            "Weighted Score (min)": _format_optional_number(
                score_breakdown.total_weighted
            ),
            "Description": "",
        }
    )
    return rows


_OPTIMALITY_GAP_THRESHOLD = 0.05


def build_solver_diagnostic_rows(result: ScheduleResult) -> list[dict]:
    diagnostics = result.solver_diagnostics
    if diagnostics is None:
        return []

    rows = []
    d = diagnostics

    # CP-SAT Status
    status_note_map = {
        "OPTIMAL": ("good", "Proved the best solution found is globally optimal."),
        "FEASIBLE": (
            "warning",
            "Valid schedule found, but optimality not proven before time ran out.",
        ),
        "INFEASIBLE": ("bad", "No valid schedule exists under current constraints."),
    }
    status_level, note = status_note_map.get(
        d.status_name,
        ("info", "Solver did not finish with a usable answer."),
    )
    rows.append(
        {
            "Metric": "CP-SAT Status",
            "Value": d.status_name,
            "Status": status_level,
            "Note": note,
        }
    )

    # Objective Value
    rows.append(
        {
            "Metric": "Objective Value",
            "Value": _format_optional_number(d.objective_value),
            "Status": "info",
            "Note": "Score of the returned schedule. Lower is better (minimization).",
        }
    )

    # Heuristic Objective Value
    rows.append(
        {
            "Metric": "Heuristic Objective Value",
            "Value": _format_optional_number(d.heuristic_objective_value),
            "Status": "info",
            "Note": "Score of the greedy/custom heuristic used as warm start baseline.",
        }
    )

    # Objective Improvement
    imp = d.objective_improvement
    if imp is None:
        imp_status = "info"
        imp_note = "No heuristic baseline available for comparison."
    elif imp > 0:
        imp_status = "good"
        imp_note = "CP-SAT improved on the heuristic baseline."
    elif imp == 0:
        imp_status = "warning"
        imp_note = "CP-SAT matched the heuristic baseline."
    else:
        imp_status = "bad"
        imp_note = (
            "CP-SAT returned a worse objective than the heuristic — possible red flag."
        )
    rows.append(
        {
            "Metric": "Objective Improvement",
            "Value": _format_optional_number(d.objective_improvement),
            "Status": imp_status,
            "Note": imp_note,
        }
    )

    # Best Objective Bound
    rows.append(
        {
            "Metric": "Best Objective Bound",
            "Value": _format_optional_number(d.best_objective_bound),
            "Status": "info",
            "Note": "Best known lower bound on the true optimal. Closer to Objective Value = more confidence.",
        }
    )

    # Optimality Gap
    gap = d.optimality_gap
    if gap is None:
        gap_status = "info"
        gap_note = "Optimality gap not available."
    elif gap == 0:
        gap_status = "good"
        gap_note = "Proven optimal."
    elif gap <= _OPTIMALITY_GAP_THRESHOLD:
        gap_status = "warning"
        gap_note = "Small unproven gap remains between solution and bound."
    else:
        gap_status = "bad"
        gap_note = "Large unproven gap — solver has not closed the proof gap."
    rows.append(
        {
            "Metric": "Optimality Gap",
            "Value": _format_optional_number(d.optimality_gap),
            "Status": gap_status,
            "Note": gap_note,
        }
    )

    # Wall Time
    rows.append(
        {
            "Metric": "Wall Time (sec)",
            "Value": _format_optional_number(d.wall_time_seconds),
            "Status": "info",
            "Note": "Actual elapsed solver time in seconds.",
        }
    )

    # Conflict Count
    rows.append(
        {
            "Metric": "Conflict Count",
            "Value": str(d.conflict_count),
            "Status": "info",
            "Note": "Times the solver hit a contradiction during search. Higher = more search effort.",
        }
    )

    # Branch Count
    rows.append(
        {
            "Metric": "Branch Count",
            "Value": str(d.branch_count),
            "Status": "info",
            "Note": "Times the solver split search paths. Higher = larger or tougher search.",
        }
    )

    # Search Workers
    rows.append(
        {
            "Metric": "Search Workers",
            "Value": str(d.search_workers),
            "Status": "info",
            "Note": "Solver threads used. 1 = single-threaded. More threads reduce determinism.",
        }
    )

    # Time Limit
    rows.append(
        {
            "Metric": "Time Limit (sec)",
            "Value": _format_optional_number(d.time_limit_seconds),
            "Status": "info",
            "Note": "Maximum time CP-SAT was allowed to search.",
        }
    )

    # Used Heuristic Hint
    hint_status = "good" if d.used_heuristic_hint else "warning"
    hint_note = (
        "CP-SAT started from the heuristic incumbent."
        if d.used_heuristic_hint
        else "Solved from scratch — heuristic schedule could not be cleanly mapped."
    )
    rows.append(
        {
            "Metric": "Used Heuristic Hint",
            "Value": "Yes" if d.used_heuristic_hint else "No",
            "Status": hint_status,
            "Note": hint_note,
        }
    )

    return rows


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}".rstrip("0").rstrip(".")
