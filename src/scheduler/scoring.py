from collections.abc import Callable

from src.domain.models import Scenario
from src.scheduler.contract import BusPlan, ScheduleResult, ScoreBreakdown

ScoreComponentFn = Callable[[ScheduleResult, Scenario], tuple[str, dict]]


def compute_individual_wait_score(result: ScheduleResult) -> float:
    if result.metrics is None:
        return 0.0
    return float(result.metrics.total_wait_minutes)


def _per_operator_wait_stats(result: ScheduleResult) -> dict[str, dict]:
    operator_data: dict[str, list[float]] = {}
    for plan in result.bus_plans:
        op = plan.operator
        if op not in operator_data:
            operator_data[op] = []
        total_wait = _compute_bus_total_wait(plan, result)
        operator_data[op].append(float(total_wait))

    stats = {}
    for op, waits in operator_data.items():
        stats[op] = {
            "total_wait": sum(waits),
            "bus_count": len(waits),
        }
    return stats


def _compute_bus_total_wait(plan: BusPlan, result: ScheduleResult) -> int:
    reservations_for_bus = [
        res for res in result.station_reservations if res.bus_id == plan.bus_id
    ]
    total_wait = 0
    for res in reservations_for_bus:
        arrival_minutes = _find_arrival_minutes(plan, res.station)
        if arrival_minutes is not None:
            total_wait += res.start_minutes - arrival_minutes
    return total_wait


def _find_arrival_minutes(plan: BusPlan, station_id: str) -> int | None:
    for event in plan.events:
        if event.event_type == "arrival" and event.location == station_id:
            return event.minutes
    return None


def compute_operator_smoothness_score(result: ScheduleResult) -> float:
    stats = _per_operator_wait_stats(result)
    total_wait = sum(op["total_wait"] for op in stats.values())
    total_buses = sum(op["bus_count"] for op in stats.values())
    if total_buses == 0:
        return 0.0
    fleet_avg_wait = total_wait / total_buses

    total_deviation = 0.0
    for op, data in stats.items():
        avg_op_wait = data["total_wait"] / data["bus_count"]
        total_deviation += abs(avg_op_wait - fleet_avg_wait)

    return total_deviation


def _get_bus_departure_minutes(plan: BusPlan) -> int:
    for event in plan.events:
        if event.event_type == "departure":
            return event.minutes
    return 0


def compute_overall_network_score(result: ScheduleResult) -> float:
    total = 0.0
    for plan in result.bus_plans:
        if plan.final_arrival_minutes is not None:
            dep = _get_bus_departure_minutes(plan)
            total += float(plan.final_arrival_minutes - dep)
    return total


def _individual_wait_component(
    result: ScheduleResult, scenario: Scenario
) -> tuple[str, dict]:
    unweighted = compute_individual_wait_score(result)
    return "individual_wait", {
        "unweighted": unweighted,
        "weighted": unweighted * scenario.weights.individual,
        "weight": scenario.weights.individual,
        "description": "Total bus wait minutes across all buses",
    }


def _operator_smoothness_component(
    result: ScheduleResult, scenario: Scenario
) -> tuple[str, dict]:
    unweighted = compute_operator_smoothness_score(result)
    return "operator_smoothness", {
        "unweighted": unweighted,
        "weighted": unweighted * scenario.weights.operator,
        "weight": scenario.weights.operator,
        "description": "Operator wait imbalance penalty",
    }


def _overall_network_component(
    result: ScheduleResult, scenario: Scenario
) -> tuple[str, dict]:
    unweighted = compute_overall_network_score(result)
    return "overall_network", {
        "unweighted": unweighted,
        "weighted": unweighted * scenario.weights.overall,
        "weight": scenario.weights.overall,
        "description": "Total fleet journey time (sum of all bus trip durations)",
    }


SCORE_COMPONENTS: dict[str, ScoreComponentFn] = {
    "individual_wait": _individual_wait_component,
    "operator_smoothness": _operator_smoothness_component,
    "overall_network": _overall_network_component,
}


def compute_score_breakdown(
    result: ScheduleResult, scenario: Scenario
) -> ScoreBreakdown:
    components: dict[str, dict] = {}
    total_weighted = 0.0

    for name, fn in SCORE_COMPONENTS.items():
        comp_name, comp_data = fn(result, scenario)
        components[comp_name] = comp_data
        total_weighted += comp_data["weighted"]

    return ScoreBreakdown(
        components=components,
        total_weighted=total_weighted,
    )
