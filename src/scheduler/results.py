from src.domain.models import Scenario
from src.scheduler.constraints import validate_schedule_invariants
from src.scheduler.contract import (
    BusPlan,
    ScheduleMetrics,
    ScheduleResult,
    SolverDiagnostics,
    StationReservation,
)
from src.scheduler.scoring import compute_score_breakdown


def compute_schedule_metrics(
    scenario: Scenario,
    bus_plans: list[BusPlan],
    station_reservations: list[StationReservation],
) -> ScheduleMetrics:
    plans_by_bus = {plan.bus_id: plan for plan in bus_plans}
    total_wait_minutes = 0
    max_wait_minutes = 0

    for reservation in station_reservations:
        plan = plans_by_bus.get(reservation.bus_id)
        if plan is None:
            continue
        arrival = _find_arrival_minutes(plan, reservation.station)
        if arrival is None:
            continue
        wait = reservation.start_minutes - arrival
        total_wait_minutes += wait
        max_wait_minutes = max(max_wait_minutes, wait)

    return ScheduleMetrics(
        total_buses=len(scenario.buses),
        total_charge_stops=len(station_reservations),
        total_wait_minutes=total_wait_minutes,
        max_wait_minutes=max_wait_minutes,
    )


def finalize_schedule_result(
    scenario: Scenario,
    bus_plans: list[BusPlan],
    station_reservations: list[StationReservation],
    warnings: list[str] | None = None,
    feasible: bool = True,
    solver_diagnostics: SolverDiagnostics | None = None,
) -> ScheduleResult:
    final_warnings = list(warnings or [])
    metrics = compute_schedule_metrics(scenario, bus_plans, station_reservations)
    result = ScheduleResult(
        feasible=feasible,
        scenario_id=scenario.id,
        bus_plans=bus_plans,
        station_reservations=station_reservations,
        metrics=metrics,
        warnings=final_warnings,
        solver_diagnostics=solver_diagnostics,
    )
    score_breakdown = compute_score_breakdown(result, scenario)
    result = ScheduleResult(
        feasible=result.feasible,
        scenario_id=result.scenario_id,
        bus_plans=result.bus_plans,
        station_reservations=result.station_reservations,
        metrics=result.metrics,
        warnings=result.warnings,
        score_breakdown=score_breakdown,
        solver_diagnostics=result.solver_diagnostics,
    )

    if not result.feasible:
        return result

    violations = validate_schedule_invariants(scenario, result)
    if not violations:
        return result

    return ScheduleResult(
        feasible=False,
        scenario_id=result.scenario_id,
        bus_plans=result.bus_plans,
        station_reservations=result.station_reservations,
        metrics=result.metrics,
        warnings=result.warnings + violations,
        score_breakdown=result.score_breakdown,
        solver_diagnostics=result.solver_diagnostics,
    )


def _find_arrival_minutes(plan: BusPlan, station_id: str) -> int | None:
    for event in plan.events:
        if event.event_type == "arrival" and event.location == station_id:
            return event.minutes
    return None
