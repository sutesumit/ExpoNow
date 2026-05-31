from src.domain.models import Scenario
from src.domain.route import distance_between, get_ordered_stops
from src.scheduler.candidates import generate_candidates
from src.scheduler.constraints import validate_schedule_invariants
from src.scheduler.contract import (
    BusPlan,
    ScheduleMetrics,
    ScheduleResult,
    ScoreBreakdown,
    StationReservation,
    TimelineEvent,
)
from src.scheduler.reservations import LaneSlot, ReservationManager
from src.scheduler.scoring import compute_score_breakdown


class CustomHeuristicStrategy:
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        sorted_buses = sorted(
            scenario.buses, key=lambda b: (b.departure_minutes, b.id)
        )
        reservation_mgr = ReservationManager(scenario.stations)
        bus_plans: list[BusPlan] = []
        all_reservations: list[StationReservation] = []
        warnings: list[str] = []
        total_charge_stops = 0
        total_wait_minutes = 0
        max_wait_minutes = 0

        for bus in sorted_buses:
            ordered = get_ordered_stops(scenario.route, bus.direction)
            origin = ordered[0]
            destination = ordered[-1]

            candidates = list(generate_candidates(
                scenario.route,
                bus.direction,
                scenario.charging_policy.range_km,
            ))

            travel_speed = scenario.travel_policy.speed_kmph
            charge_duration = scenario.charging_policy.full_charge_minutes

            chosen_candidate = None
            chosen_probe_results: list[tuple[str, LaneSlot, int]] = []
            best_score = float('inf')

            for candidate in candidates:
                probe_results: list[tuple[str, LaneSlot, int]] = []
                ok = True
                current_time = bus.departure_minutes
                prev_stop = origin

                for station_id in candidate:
                    dist = distance_between(scenario.route, prev_stop, station_id)
                    travel_minutes = _compute_travel_minutes(dist, travel_speed)
                    arrival_time = current_time + travel_minutes

                    slot = reservation_mgr.find_slot(
                        station_id, arrival_time, charge_duration
                    )
                    if slot is None:
                        ok = False
                        break

                    probe_results.append((station_id, LaneSlot(
                        lane=slot.lane,
                        start_minutes=slot.start_minutes,
                        end_minutes=slot.end_minutes,
                    ), arrival_time))
                    current_time = slot.end_minutes
                    prev_stop = station_id

                if ok:
                    score = _score_candidate(candidate, bus, scenario, probe_results)
                    if score < best_score:
                        best_score = score
                        chosen_candidate = candidate
                        chosen_probe_results = probe_results

            probe_results = chosen_probe_results

            if chosen_candidate is None:
                warnings.append(
                    f"{bus.id}: Could not schedule (no candidate with available charger slots)"
                )
                plan = _build_empty_plan(bus, origin, destination)
                bus_plans.append(plan)
                continue

            reservations: dict[str, LaneSlot] = {}
            for station_id, slot, arrival_time in probe_results:
                reservation_mgr.commit_slot(station_id, slot)
                reservations[station_id] = slot
                all_reservations.append(StationReservation(
                    station=station_id,
                    bus_id=bus.id,
                    charger_lane=slot.lane,
                    start_minutes=slot.start_minutes,
                    end_minutes=slot.end_minutes,
                ))
                total_charge_stops += 1
                wait = slot.start_minutes - arrival_time
                total_wait_minutes += wait
                max_wait_minutes = max(max_wait_minutes, wait)

            if not chosen_candidate:
                dist = distance_between(scenario.route, origin, destination)
                travel_minutes = _compute_travel_minutes(dist, travel_speed)
                final_arrival = bus.departure_minutes + travel_minutes
            else:
                last_station = chosen_candidate[-1]
                dist = distance_between(scenario.route, last_station, destination)
                travel_minutes = _compute_travel_minutes(dist, travel_speed)
                final_arrival = probe_results[-1][1].end_minutes + travel_minutes

            plan = _build_bus_timeline(
                bus, chosen_candidate, reservations, scenario.route,
                travel_speed, charge_duration, origin, destination,
                final_arrival,
            )
            bus_plans.append(plan)

        result = ScheduleResult(
            feasible=len(warnings) == 0,
            scenario_id=scenario.id,
            bus_plans=bus_plans,
            station_reservations=all_reservations,
            metrics=ScheduleMetrics(
                total_buses=len(scenario.buses),
                total_charge_stops=total_charge_stops,
                total_wait_minutes=total_wait_minutes,
                max_wait_minutes=max_wait_minutes,
            ),
            warnings=warnings,
            score_breakdown=ScoreBreakdown(
                components={
                    "weights": {
                        "individual": scenario.weights.individual,
                        "operator": scenario.weights.operator,
                        "overall": scenario.weights.overall,
                    }
                },
                total_weighted=0.0,
            ),
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
        )

        violations = validate_schedule_invariants(scenario, result)
        if violations:
            warnings.extend(violations)
            result = ScheduleResult(
                feasible=False,
                scenario_id=scenario.id,
                bus_plans=bus_plans,
                station_reservations=all_reservations,
                metrics=result.metrics,
                warnings=warnings,
                score_breakdown=result.score_breakdown,
            )

        return result


def _compute_travel_minutes(distance_km: int, speed_kmph: int) -> int:
    return max(1, round(distance_km * 60 / speed_kmph))


def _score_candidate(
    candidate: tuple[str, ...],
    bus,
    scenario: Scenario,
    probe_results: list[tuple[str, LaneSlot, int]],
) -> float:
    ordered = get_ordered_stops(scenario.route, bus.direction)
    destination = ordered[-1]
    travel_speed = scenario.travel_policy.speed_kmph

    total_wait = sum(
        slot.start_minutes - arrival_time
        for _, slot, arrival_time in probe_results
    )

    last_station = candidate[-1]
    dist = distance_between(scenario.route, last_station, destination)
    travel_minutes = _compute_travel_minutes(dist, travel_speed)
    final_arrival = probe_results[-1][1].end_minutes + travel_minutes
    total_travel_time = final_arrival - bus.departure_minutes

    return (
        scenario.weights.individual * total_wait
        + scenario.weights.overall * total_travel_time
    )


def _build_bus_timeline(
    bus,
    candidate: tuple[str, ...],
    reservations: dict[str, LaneSlot],
    route,
    travel_speed: int,
    charge_duration: int,
    origin: str,
    destination: str,
    final_arrival: int,
) -> BusPlan:
    events: list[TimelineEvent] = []
    events.append(TimelineEvent(
        event_type="departure",
        minutes=bus.departure_minutes,
        location=origin,
        description=f"Departure from {origin}",
    ))

    current_time = bus.departure_minutes
    prev_stop = origin

    for station_id in candidate:
        dist = distance_between(route, prev_stop, station_id)
        travel_minutes = _compute_travel_minutes(dist, travel_speed)
        arrival_time = current_time + travel_minutes
        slot = reservations[station_id]

        events.append(TimelineEvent(
            event_type="arrival",
            minutes=arrival_time,
            location=station_id,
            description=f"Arrival at {station_id}",
        ))

        wait = slot.start_minutes - arrival_time
        if wait > 0:
            events.append(TimelineEvent(
                event_type="wait",
                minutes=arrival_time,
                location=station_id,
                description=f"Wait at {station_id}",
            ))

        events.append(TimelineEvent(
            event_type="charge_start",
            minutes=slot.start_minutes,
            location=station_id,
            description=f"Charge start at {station_id}",
        ))
        events.append(TimelineEvent(
            event_type="charge_end",
            minutes=slot.end_minutes,
            location=station_id,
            description=f"Charge end at {station_id}",
        ))

        current_time = slot.end_minutes
        prev_stop = station_id

    dist = distance_between(route, prev_stop, destination)
    travel_minutes = _compute_travel_minutes(dist, travel_speed)
    events.append(TimelineEvent(
        event_type="arrival",
        minutes=final_arrival,
        location=destination,
        description=f"Arrival at {destination}",
    ))

    return BusPlan(
        bus_id=bus.id,
        operator=bus.operator,
        direction=bus.direction,
        events=events,
        final_arrival_minutes=final_arrival,
    )


def _build_empty_plan(bus, origin: str, destination: str) -> BusPlan:
    return BusPlan(
        bus_id=bus.id,
        operator=bus.operator,
        direction=bus.direction,
        events=[
            TimelineEvent(
                event_type="departure",
                minutes=bus.departure_minutes,
                location=origin,
                description=f"Departure from {origin}",
            ),
        ],
    )
