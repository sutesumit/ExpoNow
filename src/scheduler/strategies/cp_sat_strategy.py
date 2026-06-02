import importlib.util
from dataclasses import dataclass
from typing import Any

from src.domain.models import Scenario
from src.domain.route import distance_between, get_ordered_stops, total_distance
from src.scheduler.candidates import generate_candidates
from src.scheduler.contract import ScheduleResult, SolverDiagnostics, StationReservation
from src.scheduler.reservations import LaneSlot
from src.scheduler.results import finalize_schedule_result
from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
from src.scheduler.timeline import build_bus_timeline, compute_travel_minutes

CP_SAT_TIME_LIMIT_SECONDS = 60.0
WEIGHT_SCALE = 1000


@dataclass(frozen=True)
class _StopDecision:
    station_id: str
    start: Any
    wait: Any
    lane_selectors: list[Any]


@dataclass(frozen=True)
class _CandidateDecision:
    candidate: tuple[str, ...]
    selected: Any
    stops: list[_StopDecision]
    journey: Any


@dataclass(frozen=True)
class _BusDecision:
    bus: Any
    origin: str
    destination: str
    candidates: list[_CandidateDecision]


@dataclass(frozen=True)
class _HeuristicStopHint:
    station_id: str
    start_minutes: int
    charger_lane: int


@dataclass(frozen=True)
class _HeuristicBusHint:
    candidate: tuple[str, ...]
    stops: list[_HeuristicStopHint]


def is_ortools_available() -> bool:
    return importlib.util.find_spec("ortools") is not None


class CpSatStrategy:
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        if not is_ortools_available():
            return ScheduleResult(
                feasible=False,
                scenario_id=scenario.id,
                warnings=[
                    "OR-Tools CP-SAT is not available. Install requirements-solver-cpsat.txt to enable this strategy."
                ],
            )

        from ortools.sat.python import cp_model

        return _schedule_with_cp_sat(scenario, cp_model)


def _schedule_with_cp_sat(scenario: Scenario, cp_model) -> ScheduleResult:
    prepared_candidates: dict[str, list[tuple[str, ...]]] = {}
    for bus in scenario.buses:
        candidates = list(
            generate_candidates(
                scenario.route,
                bus.direction,
                scenario.charging_policy.range_km,
            )
        )
        if not candidates:
            return ScheduleResult(
                feasible=False,
                scenario_id=scenario.id,
                warnings=[
                    f"{bus.id}: CP-SAT found no range-feasible charging candidates"
                ],
            )
        prepared_candidates[bus.id] = candidates

    model = cp_model.CpModel()
    charge_duration = scenario.charging_policy.full_charge_minutes
    travel_speed = scenario.travel_policy.speed_kmph
    station_chargers = {
        station.id: station.charger_count for station in scenario.stations
    }
    sorted_buses = sorted(scenario.buses, key=lambda b: (b.departure_minutes, b.id))
    horizon = _compute_horizon(scenario, prepared_candidates)
    intervals_by_lane: dict[tuple[str, int], list[Any]] = {
        (station.id, lane): []
        for station in scenario.stations
        for lane in range(station.charger_count)
    }
    bus_decisions: list[_BusDecision] = []
    wait_terms: list[Any] = []
    journey_terms: list[Any] = []

    for bus_idx, bus in enumerate(sorted_buses):
        ordered = get_ordered_stops(scenario.route, bus.direction)
        origin = ordered[0]
        destination = ordered[-1]
        candidate_decisions: list[_CandidateDecision] = []

        for candidate_idx, candidate in enumerate(prepared_candidates[bus.id]):
            prefix = f"b{bus_idx}_c{candidate_idx}"
            selected = model.NewBoolVar(f"{prefix}_selected")
            stop_decisions: list[_StopDecision] = []
            current_time_expr: Any = bus.departure_minutes
            prev_stop = origin

            for stop_idx, station_id in enumerate(candidate):
                travel_minutes = compute_travel_minutes(
                    distance_between(scenario.route, prev_stop, station_id),
                    travel_speed,
                )
                arrival_expr = current_time_expr + travel_minutes
                start = model.NewIntVar(0, horizon, f"{prefix}_s{stop_idx}_start")
                wait = model.NewIntVar(0, horizon, f"{prefix}_s{stop_idx}_wait")
                lane_selectors: list[Any] = []

                model.Add(start >= arrival_expr).OnlyEnforceIf(selected)
                model.Add(wait == start - arrival_expr).OnlyEnforceIf(selected)
                model.Add(wait == 0).OnlyEnforceIf(selected.Not())

                for lane in range(station_chargers[station_id]):
                    lane_selected = model.NewBoolVar(f"{prefix}_s{stop_idx}_lane{lane}")
                    end = model.NewIntVar(
                        0, horizon, f"{prefix}_s{stop_idx}_lane{lane}_end"
                    )
                    interval = model.NewOptionalIntervalVar(
                        start,
                        charge_duration,
                        end,
                        lane_selected,
                        f"{prefix}_s{stop_idx}_lane{lane}_interval",
                    )
                    intervals_by_lane[(station_id, lane)].append(interval)
                    lane_selectors.append(lane_selected)

                model.Add(sum(lane_selectors) == 1).OnlyEnforceIf(selected)
                model.Add(sum(lane_selectors) == 0).OnlyEnforceIf(selected.Not())

                stop_decisions.append(
                    _StopDecision(
                        station_id=station_id,
                        start=start,
                        wait=wait,
                        lane_selectors=lane_selectors,
                    )
                )
                wait_terms.append(wait)
                current_time_expr = start + charge_duration
                prev_stop = station_id

            final_travel_minutes = compute_travel_minutes(
                distance_between(scenario.route, prev_stop, destination),
                travel_speed,
            )
            journey = model.NewIntVar(0, horizon, f"{prefix}_journey")
            journey_expr = (
                current_time_expr + final_travel_minutes - bus.departure_minutes
            )
            model.Add(journey == journey_expr).OnlyEnforceIf(selected)
            model.Add(journey == 0).OnlyEnforceIf(selected.Not())
            journey_terms.append(journey)

            candidate_decisions.append(
                _CandidateDecision(
                    candidate=candidate,
                    selected=selected,
                    stops=stop_decisions,
                    journey=journey,
                )
            )

        model.Add(sum(candidate.selected for candidate in candidate_decisions) == 1)
        bus_decisions.append(
            _BusDecision(
                bus=bus,
                origin=origin,
                destination=destination,
                candidates=candidate_decisions,
            )
        )

    for intervals in intervals_by_lane.values():
        if intervals:
            model.AddNoOverlap(intervals)

    model.Minimize(
        _scaled_weight(scenario.weights.individual) * sum(wait_terms)
        + _scaled_weight(scenario.weights.overall) * sum(journey_terms)
    )

    heuristic_result = CustomHeuristicStrategy().schedule(scenario)
    heuristic_objective = _compute_result_objective(scenario, heuristic_result)
    heuristic_hints, hint_warnings = _build_heuristic_hints(
        heuristic_result,
        bus_decisions,
    )
    used_heuristic_hint = False
    if heuristic_hints is not None:
        _add_heuristic_hints(model, bus_decisions, heuristic_hints)
        used_heuristic_hint = True

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = CP_SAT_TIME_LIMIT_SECONDS
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    diagnostics = _build_solver_diagnostics(
        solver,
        status,
        cp_model,
        used_heuristic_hint,
        heuristic_objective,
    )
    warnings = hint_warnings + _warnings_for_status(status, cp_model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ScheduleResult(
            feasible=False,
            scenario_id=scenario.id,
            warnings=warnings,
            solver_diagnostics=diagnostics,
        )

    bus_plans, reservations = _decode_solution(
        scenario,
        bus_decisions,
        solver,
        charge_duration,
        travel_speed,
    )
    return finalize_schedule_result(
        scenario,
        bus_plans,
        reservations,
        warnings=warnings,
        feasible=True,
        solver_diagnostics=diagnostics,
    )


def _build_heuristic_hints(
    heuristic_result: ScheduleResult,
    bus_decisions: list[_BusDecision],
) -> tuple[dict[str, _HeuristicBusHint] | None, list[str]]:
    if not heuristic_result.feasible:
        return None, [
            "CP-SAT skipped heuristic hint because the custom heuristic did not produce a feasible schedule."
        ]

    plans_by_bus = {plan.bus_id: plan for plan in heuristic_result.bus_plans}
    reservations_by_bus_station = {
        (reservation.bus_id, reservation.station): reservation
        for reservation in heuristic_result.station_reservations
    }
    hints: dict[str, _HeuristicBusHint] = {}

    for bus_decision in bus_decisions:
        plan = plans_by_bus.get(bus_decision.bus.id)
        if plan is None:
            return None, [
                f"CP-SAT skipped heuristic hint because {bus_decision.bus.id} has no heuristic bus plan."
            ]

        candidate = tuple(
            event.location
            for event in plan.events
            if event.event_type == "charge_start"
        )
        if candidate not in {
            candidate_decision.candidate
            for candidate_decision in bus_decision.candidates
        }:
            return None, [
                "CP-SAT skipped heuristic hint because the heuristic station sequence "
                f"for {bus_decision.bus.id} does not match a CP-SAT candidate."
            ]

        stop_hints: list[_HeuristicStopHint] = []
        for station_id in candidate:
            reservation = reservations_by_bus_station.get(
                (bus_decision.bus.id, station_id)
            )
            if reservation is None:
                return None, [
                    "CP-SAT skipped heuristic hint because the heuristic reservation "
                    f"for {bus_decision.bus.id} at {station_id} is missing."
                ]
            stop_hints.append(
                _HeuristicStopHint(
                    station_id=station_id,
                    start_minutes=reservation.start_minutes,
                    charger_lane=reservation.charger_lane,
                )
            )

        hints[bus_decision.bus.id] = _HeuristicBusHint(
            candidate=candidate,
            stops=stop_hints,
        )

    return hints, []


def _add_heuristic_hints(
    model,
    bus_decisions: list[_BusDecision],
    hints: dict[str, _HeuristicBusHint],
) -> None:
    for bus_decision in bus_decisions:
        hint = hints[bus_decision.bus.id]
        for candidate_decision in bus_decision.candidates:
            candidate_selected = candidate_decision.candidate == hint.candidate
            model.AddHint(candidate_decision.selected, int(candidate_selected))
            if not candidate_selected:
                continue

            for stop_decision, stop_hint in zip(candidate_decision.stops, hint.stops):
                model.AddHint(stop_decision.start, stop_hint.start_minutes)
                for lane, lane_selected in enumerate(stop_decision.lane_selectors):
                    model.AddHint(lane_selected, int(lane == stop_hint.charger_lane))


def _compute_result_objective(
    scenario: Scenario,
    result: ScheduleResult,
) -> float | None:
    if not result.feasible or result.metrics is None:
        return None

    buses_by_id = {bus.id: bus for bus in scenario.buses}
    total_journey_minutes = 0
    for plan in result.bus_plans:
        bus = buses_by_id.get(plan.bus_id)
        if bus is None or plan.final_arrival_minutes is None:
            return None
        total_journey_minutes += plan.final_arrival_minutes - bus.departure_minutes

    return float(
        _scaled_weight(scenario.weights.individual) * result.metrics.total_wait_minutes
        + _scaled_weight(scenario.weights.overall) * total_journey_minutes
    )


def _build_solver_diagnostics(
    solver,
    status: int,
    cp_model,
    used_heuristic_hint: bool,
    heuristic_objective: float | None,
) -> SolverDiagnostics:
    objective_value = None
    best_objective_bound = None
    optimality_gap = None
    objective_improvement = None

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        objective_value = float(solver.ObjectiveValue())
        best_objective_bound = float(solver.BestObjectiveBound())
        optimality_gap = objective_value - best_objective_bound
        if heuristic_objective is not None:
            objective_improvement = heuristic_objective - objective_value
    else:
        best_objective_bound = float(solver.BestObjectiveBound())

    return SolverDiagnostics(
        solver_name="CP-SAT",
        status_name=solver.StatusName(status),
        objective_value=objective_value,
        best_objective_bound=best_objective_bound,
        optimality_gap=optimality_gap,
        wall_time_seconds=float(solver.WallTime()),
        conflict_count=int(solver.NumConflicts()),
        branch_count=int(solver.NumBranches()),
        search_workers=1,
        time_limit_seconds=CP_SAT_TIME_LIMIT_SECONDS,
        used_heuristic_hint=used_heuristic_hint,
        heuristic_objective_value=heuristic_objective,
        objective_improvement=objective_improvement,
    )


def _compute_horizon(
    scenario: Scenario,
    prepared_candidates: dict[str, list[tuple[str, ...]]],
) -> int:
    max_departure = max((bus.departure_minutes for bus in scenario.buses), default=0)
    route_minutes = compute_travel_minutes(
        total_distance(scenario.route),
        scenario.travel_policy.speed_kmph,
    )
    max_candidate_len = max(
        (
            len(candidate)
            for candidates in prepared_candidates.values()
            for candidate in candidates
        ),
        default=0,
    )
    serial_charge_minutes = (
        max(1, len(scenario.buses))
        * max(1, max_candidate_len)
        * scenario.charging_policy.full_charge_minutes
    )
    return max_departure + route_minutes + serial_charge_minutes + 60


def _decode_solution(
    scenario: Scenario,
    bus_decisions: list[_BusDecision],
    solver,
    charge_duration: int,
    travel_speed: int,
) -> tuple[list, list[StationReservation]]:
    bus_plans = []
    station_reservations: list[StationReservation] = []

    for bus_decision in bus_decisions:
        selected_candidate = _selected_candidate(bus_decision, solver)
        reservations_by_station: dict[str, LaneSlot] = {}

        for stop_decision in selected_candidate.stops:
            start = solver.Value(stop_decision.start)
            lane = _selected_lane(stop_decision, solver)
            slot = LaneSlot(
                lane=lane,
                start_minutes=start,
                end_minutes=start + charge_duration,
            )
            reservations_by_station[stop_decision.station_id] = slot
            station_reservations.append(
                StationReservation(
                    station=stop_decision.station_id,
                    bus_id=bus_decision.bus.id,
                    charger_lane=lane,
                    start_minutes=slot.start_minutes,
                    end_minutes=slot.end_minutes,
                )
            )

        final_arrival = _compute_final_arrival(
            scenario,
            bus_decision,
            selected_candidate.candidate,
            reservations_by_station,
            travel_speed,
        )
        bus_plans.append(
            build_bus_timeline(
                bus_decision.bus,
                selected_candidate.candidate,
                reservations_by_station,
                scenario.route,
                travel_speed,
                bus_decision.origin,
                bus_decision.destination,
                final_arrival,
            )
        )

    return bus_plans, station_reservations


def _selected_candidate(
    bus_decision: _BusDecision,
    solver,
) -> _CandidateDecision:
    for candidate in bus_decision.candidates:
        if solver.Value(candidate.selected) == 1:
            return candidate
    raise ValueError(f"CP-SAT did not select a candidate for {bus_decision.bus.id}")


def _selected_lane(stop_decision: _StopDecision, solver) -> int:
    for lane, lane_selected in enumerate(stop_decision.lane_selectors):
        if solver.Value(lane_selected) == 1:
            return lane
    raise ValueError(f"CP-SAT did not select a lane for {stop_decision.station_id}")


def _compute_final_arrival(
    scenario: Scenario,
    bus_decision: _BusDecision,
    candidate: tuple[str, ...],
    reservations_by_station: dict[str, LaneSlot],
    travel_speed: int,
) -> int:
    if not candidate:
        dist = distance_between(
            scenario.route,
            bus_decision.origin,
            bus_decision.destination,
        )
        return bus_decision.bus.departure_minutes + compute_travel_minutes(
            dist, travel_speed
        )

    last_station = candidate[-1]
    last_slot = reservations_by_station[last_station]
    dist = distance_between(scenario.route, last_station, bus_decision.destination)
    return last_slot.end_minutes + compute_travel_minutes(dist, travel_speed)


def _scaled_weight(weight: float) -> int:
    return int(round(weight * WEIGHT_SCALE))


def _warnings_for_status(status: int, cp_model) -> list[str]:
    if status == cp_model.OPTIMAL:
        return []
    if status == cp_model.FEASIBLE:
        return [
            "CP-SAT found a feasible solution but did not prove optimality "
            f"within {CP_SAT_TIME_LIMIT_SECONDS:.1f} seconds."
        ]
    if status == cp_model.INFEASIBLE:
        return ["CP-SAT proved the scenario infeasible."]
    if status == cp_model.MODEL_INVALID:
        return ["CP-SAT model is invalid."]
    return ["CP-SAT did not find a solution before the limit."]
