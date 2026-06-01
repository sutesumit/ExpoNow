from src.domain.route import distance_between
from src.scheduler.contract import BusPlan, TimelineEvent
from src.scheduler.reservations import LaneSlot


def compute_travel_minutes(distance_km: int, speed_kmph: int) -> int:
    return max(1, round(distance_km * 60 / speed_kmph))


def build_bus_timeline(
    bus,
    candidate: tuple[str, ...],
    reservations: dict[str, LaneSlot],
    route,
    travel_speed: int,
    origin: str,
    destination: str,
    final_arrival: int,
) -> BusPlan:
    events: list[TimelineEvent] = [
        TimelineEvent(
            event_type="departure",
            minutes=bus.departure_minutes,
            location=origin,
            description=f"Departure from {origin}",
        )
    ]

    current_time = bus.departure_minutes
    prev_stop = origin

    for station_id in candidate:
        dist = distance_between(route, prev_stop, station_id)
        travel_minutes = compute_travel_minutes(dist, travel_speed)
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


def build_empty_plan(bus, origin: str, destination: str) -> BusPlan:
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
