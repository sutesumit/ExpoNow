from src.domain.models import Route, Scenario
from src.domain.route import distance_between, get_ordered_stops
from src.scheduler.contract import ChargingStop, ScheduleResult


def check_range_constraints(
    route: Route,
    direction: str,
    charging_stops: list[ChargingStop],
    range_km: int,
) -> list[str]:
    ordered = get_ordered_stops(route, direction)
    origin = ordered[0]
    destination = ordered[-1]
    violations: list[str] = []

    prev = origin
    for stop in charging_stops:
        gap = distance_between(route, prev, stop.station)
        if gap > range_km:
            violations.append(
                f"Range exceeded: {prev} -> {stop.station} = {gap}km > {range_km}km"
            )
        prev = stop.station

    gap = distance_between(route, prev, destination)
    if gap > range_km:
        violations.append(
            f"Range exceeded: {prev} -> {destination} = {gap}km > {range_km}km"
        )

    return violations


def check_route_order(
    charging_stops: list[ChargingStop],
    direction: str,
    valid_directions: set[str],
) -> list[str]:
    violations: list[str] = []
    if direction not in valid_directions:
        violations.append(f"Invalid direction: {direction}")
    if not charging_stops:
        return violations
    stations = [s.station for s in charging_stops]
    for i in range(len(stations) - 1):
        if stations[i] == stations[i + 1]:
            violations.append(
                f"Consecutive duplicate stop: {stations[i]}"
            )
    return violations


def validate_schedule_invariants(
    scenario: Scenario, result: ScheduleResult
) -> list[str]:
    if not result.feasible:
        return ["Schedule is not feasible"]

    violations: list[str] = []

    for plan in result.bus_plans:
        bus = _find_bus(scenario, plan.bus_id)
        if bus is None:
            violations.append(f"Bus {plan.bus_id} not found in scenario")
            continue

        charging_stops = _extract_charging_stops(plan)
        range_violations = check_range_constraints(
            scenario.route,
            bus.direction,
            charging_stops,
            scenario.charging_policy.range_km,
        )
        violations.extend(
            f"{plan.bus_id}: {v}" for v in range_violations
        )

        order_violations = check_route_order(
            charging_stops,
            bus.direction,
            {f"{scenario.route.stops[0]}->{scenario.route.stops[-1]}",
             f"{scenario.route.stops[-1]}->{scenario.route.stops[0]}"},
        )
        violations.extend(
            f"{plan.bus_id}: {v}" for v in order_violations
        )

        violations.extend(
            f"{plan.bus_id}: {v}"
            for v in _check_charge_durations(plan.events, scenario.charging_policy.full_charge_minutes)
        )

        event_times = [e.minutes for e in plan.events]
        for i in range(len(event_times) - 1):
            if event_times[i] > event_times[i + 1]:
                violations.append(
                    f"{plan.bus_id}: Non-chronological events at index {i}"
                )
                break

    seen: set[tuple[str, int, int, int]] = set()
    for res in result.station_reservations:
        key = (res.station, res.charger_lane, res.start_minutes, res.end_minutes)
        if key in seen:
            violations.append(
                f"Duplicate reservation: {res.station} lane {res.charger_lane} "
                f"{res.start_minutes}-{res.end_minutes}"
            )
        seen.add(key)

    for i, r1 in enumerate(result.station_reservations):
        for r2 in result.station_reservations[i + 1:]:
            if (r1.station == r2.station and
                    r1.charger_lane == r2.charger_lane and
                    r1.start_minutes < r2.end_minutes and
                    r2.start_minutes < r1.end_minutes):
                violations.append(
                    f"Overlapping reservations at {r1.station} lane {r1.charger_lane}: "
                    f"{r1.start_minutes}-{r1.end_minutes} and "
                    f"{r2.start_minutes}-{r2.end_minutes}"
                )

    return violations


def _find_bus(scenario: Scenario, bus_id: str):
    for bus in scenario.buses:
        if bus.id == bus_id:
            return bus
    return None


def _extract_charging_stops(plan) -> list[ChargingStop]:
    stations: list[str] = []
    for event in plan.events:
        if event.event_type == "charge_start":
            stations.append(event.location)
    return [
        ChargingStop(station=s, arrival_minutes=0, wait_minutes=0,
                     charge_start_minutes=0, charge_end_minutes=0, charger_lane=0)
        for s in stations
    ]


def _check_charge_durations(events: list, expected_duration: int) -> list[str]:
    violations: list[str] = []
    for event in events:
        if event.event_type == "charge_start":
            for j in range(events.index(event) + 1, len(events)):
                if events[j].event_type == "charge_end" and events[j].location == event.location:
                    actual = events[j].minutes - event.minutes
                    if actual != expected_duration:
                        violations.append(
                            f"Charge duration {actual}min != expected {expected_duration}min "
                            f"at {event.location}"
                        )
                    break
    return violations
