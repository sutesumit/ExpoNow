from src.scheduler.contract import ScheduleResult, ScoreBreakdown
from src.reporting.tables import build_station_queue_rows


def build_summary_metrics(result: ScheduleResult) -> list[dict]:
    if result.metrics is None:
        return []

    metrics = []
    metrics.append({"Metric": "Total Buses", "Value": result.metrics.total_buses})
    metrics.append({"Metric": "Total Charge Stops", "Value": result.metrics.total_charge_stops})
    metrics.append({"Metric": "Total Wait (min)", "Value": result.metrics.total_wait_minutes})
    metrics.append({"Metric": "Max Individual Wait (min)", "Value": result.metrics.max_wait_minutes})

    station_rows = build_station_queue_rows(result)
    for station_id in sorted(station_rows.keys()):
        total_wait = sum(r["Wait (min)"] for r in station_rows[station_id])
        metrics.append({"Metric": f"Station {station_id} Total Wait (min)", "Value": total_wait})

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
        rows.append({
            "Component": label,
            "Raw Score (min)": comp["unweighted"],
            "Weight": comp["weight"],
            "Weighted Score (min)": comp["weighted"],
            "Description": comp.get("description", ""),
        })

    rows.append({
        "Component": "TOTAL",
        "Raw Score (min)": None,
        "Weight": None,
        "Weighted Score (min)": score_breakdown.total_weighted,
        "Description": "",
    })
    return rows
