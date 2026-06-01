from src.domain.models import Scenario
from src.domain.route import distance_between, get_ordered_stops
from src.scheduler.candidates import generate_candidates
from src.scheduler.contract import ScheduleResult, StationReservation
from src.scheduler.reservations import LaneSlot, ReservationManager
from src.scheduler.results import finalize_schedule_result
from src.scheduler.timeline import (
    build_bus_timeline,
    build_empty_plan,
    compute_travel_minutes,
)


class CustomHeuristicStrategy:
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        sorted_buses = sorted(
            scenario.buses, key=lambda b: (b.departure_minutes, b.id)
        )
        reservation_mgr = ReservationManager(scenario.stations)
        bus_plans: list[BusPlan] = []
        all_reservations: list[StationReservation] = []
        warnings: list[str] = []

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
                    travel_minutes = compute_travel_minutes(dist, travel_speed)
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
                plan = build_empty_plan(bus, origin, destination)
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

            if not chosen_candidate:
                dist = distance_between(scenario.route, origin, destination)
                travel_minutes = compute_travel_minutes(dist, travel_speed)
                final_arrival = bus.departure_minutes + travel_minutes
            else:
                last_station = chosen_candidate[-1]
                dist = distance_between(scenario.route, last_station, destination)
                travel_minutes = compute_travel_minutes(dist, travel_speed)
                final_arrival = probe_results[-1][1].end_minutes + travel_minutes

            plan = build_bus_timeline(
                bus, chosen_candidate, reservations, scenario.route,
                travel_speed, origin, destination, final_arrival,
            )
            bus_plans.append(plan)

        return finalize_schedule_result(
            scenario,
            bus_plans,
            all_reservations,
            warnings=warnings,
            feasible=len(warnings) == 0,
        )


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
    travel_minutes = compute_travel_minutes(dist, travel_speed)
    final_arrival = probe_results[-1][1].end_minutes + travel_minutes
    total_travel_time = final_arrival - bus.departure_minutes

    return (
        scenario.weights.individual * total_wait
        + scenario.weights.overall * total_travel_time
    )
