from src.domain.models import Scenario

VALID_DIRECTIONS = {"Bengaluru->Kochi", "Kochi->Bengaluru"}


def validate_scenario(scenario: Scenario) -> list[str]:
    errors = []
    sid = scenario.id

    if not isinstance(scenario.schema_version, int) or scenario.schema_version <= 0:
        errors.append(f"{sid}: schema_version must be a positive integer")
    if not scenario.id:
        errors.append(f"{sid}: id is required")
    if not scenario.name:
        errors.append(f"{sid}: name is required")
    if not scenario.description:
        errors.append(f"{sid}: description is required")

    if len(scenario.route.stops) < 2:
        errors.append(
            f"{sid}: route must have at least 2 stops, got {len(scenario.route.stops)}"
        )
    if len(scenario.route.segments) < 1:
        errors.append(
            f"{sid}: route must have at least 1 segment, got {len(scenario.route.segments)}"
        )

    if scenario.route.stops:
        if scenario.route.stops[0] != "Bengaluru":
            errors.append(
                f"{sid}: route must start at Bengaluru, got '{scenario.route.stops[0]}'"
            )
        if scenario.route.stops[-1] != "Kochi":
            errors.append(
                f"{sid}: route must end at Kochi, got '{scenario.route.stops[-1]}'"
            )

    station_ids = {s.id for s in scenario.stations}
    terminals = {"Bengaluru", "Kochi"}

    for seg in scenario.route.segments:
        if seg.distance_km <= 0:
            errors.append(
                f"{sid}: segment {seg.from_stop}->{seg.to_stop} has "
                f"non-positive distance {seg.distance_km}"
            )

    for stop in scenario.route.stops:
        if stop not in station_ids and stop not in terminals:
            errors.append(
                f"{sid}: route stop '{stop}' not found in station list"
            )

    for seg in scenario.route.segments:
        if seg.from_stop not in station_ids and seg.from_stop not in terminals:
            errors.append(
                f"{sid}: segment start '{seg.from_stop}' not found in station list"
            )
        if seg.to_stop not in station_ids and seg.to_stop not in terminals:
            errors.append(
                f"{sid}: segment end '{seg.to_stop}' not found in station list"
            )

    for seg in scenario.route.segments:
        if seg.from_stop not in scenario.route.stops:
            errors.append(
                f"{sid}: segment start '{seg.from_stop}' not found in route stops"
            )
        if seg.to_stop not in scenario.route.stops:
            errors.append(
                f"{sid}: segment end '{seg.to_stop}' not found in route stops"
            )

    expected_segments = list(zip(scenario.route.stops, scenario.route.stops[1:]))
    actual_segments = [(seg.from_stop, seg.to_stop) for seg in scenario.route.segments]
    if expected_segments and actual_segments != expected_segments:
        expected = ", ".join(f"{start}->{end}" for start, end in expected_segments)
        actual = ", ".join(f"{start}->{end}" for start, end in actual_segments)
        errors.append(
            f"{sid}: route segments must connect in route stop order; "
            f"expected [{expected}], got [{actual}]"
        )

    for station in scenario.stations:
        if station.charger_count <= 0:
            errors.append(
                f"{sid}: station '{station.id}' has non-positive "
                f"charger_count {station.charger_count}"
            )

    cp = scenario.charging_policy
    if cp.range_km <= 0:
        errors.append(
            f"{sid}: charging_policy.range_km must be positive, got {cp.range_km}"
        )
    if cp.full_charge_minutes <= 0:
        errors.append(
            f"{sid}: charging_policy.full_charge_minutes must be positive, "
            f"got {cp.full_charge_minutes}"
        )

    tp = scenario.travel_policy
    if tp.speed_kmph <= 0:
        errors.append(
            f"{sid}: travel_policy.speed_kmph must be positive, got {tp.speed_kmph}"
        )

    w = scenario.weights
    if w.individual < 0:
        errors.append(f"{sid}: weight 'individual' is negative ({w.individual})")
    if w.operator < 0:
        errors.append(f"{sid}: weight 'operator' is negative ({w.operator})")
    if w.overall < 0:
        errors.append(f"{sid}: weight 'overall' is negative ({w.overall})")

    bus_ids = [b.id for b in scenario.buses]
    if len(bus_ids) != len(set(bus_ids)):
        seen = set()
        for b in scenario.buses:
            if b.id in seen:
                errors.append(f"{sid}: duplicate bus id '{b.id}'")
            seen.add(b.id)

    for bus in scenario.buses:
        if bus.direction not in VALID_DIRECTIONS:
            errors.append(
                f"{sid}: bus '{bus.id}' has invalid direction '{bus.direction}'"
            )

    return errors
