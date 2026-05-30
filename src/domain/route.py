from src.domain.models import Route


def get_ordered_stops(route: Route, direction: str) -> list[str]:
    origin, destination = direction.split("->")
    origin_idx = route.stops.index(origin)
    destination_idx = route.stops.index(destination)
    if origin_idx < destination_idx:
        return list(route.stops)
    return list(reversed(route.stops))


def total_distance(route: Route) -> int:
    return sum(segment.distance_km for segment in route.segments)


def segment_distances(route: Route) -> list[int]:
    return [segment.distance_km for segment in route.segments]


def distance_between(route: Route, from_stop: str, to_stop: str) -> int:
    if from_stop not in route.stops or to_stop not in route.stops:
        missing = from_stop if from_stop not in route.stops else to_stop
        raise ValueError(f"Station not on route: {missing}")
    from_idx = route.stops.index(from_stop)
    to_idx = route.stops.index(to_stop)
    if from_idx == to_idx:
        return 0
    start = min(from_idx, to_idx)
    end = max(from_idx, to_idx)
    return sum(route.segments[i].distance_km for i in range(start, end))
