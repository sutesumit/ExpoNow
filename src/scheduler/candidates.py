import itertools

from src.domain.models import Route
from src.domain.route import distance_between, get_ordered_stops


def generate_candidates(
    route: Route,
    direction: str,
    charging_range_km: int,
) -> list[tuple[str, ...]]:
    ordered_stops = get_ordered_stops(route, direction)
    origin = ordered_stops[0]
    destination = ordered_stops[-1]
    intermediate_stations = ordered_stops[1:-1]

    if not intermediate_stations:
        gap = distance_between(route, origin, destination)
        if gap <= charging_range_km:
            return [()]
        return []

    candidates: list[tuple[str, ...]] = []
    for r in range(1, len(intermediate_stations) + 1):
        for combo in itertools.combinations(intermediate_stations, r):
            if _is_candidate_valid(route, origin, destination, combo, charging_range_km):
                candidates.append(combo)

    return candidates


def _is_candidate_valid(
    route: Route,
    origin: str,
    destination: str,
    candidate: tuple[str, ...],
    charging_range_km: int,
) -> bool:
    prev = origin
    for station in candidate:
        gap = distance_between(route, prev, station)
        if gap > charging_range_km:
            return False
        prev = station
    gap = distance_between(route, prev, destination)
    if gap > charging_range_km:
        return False
    return True
