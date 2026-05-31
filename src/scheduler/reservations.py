from dataclasses import dataclass, field

from src.domain.models import Station


@dataclass
class LaneSlot:
    lane: int
    start_minutes: int
    end_minutes: int


@dataclass
class _LaneSchedule:
    reservations: list[tuple[int, int]] = field(default_factory=list)


class ReservationManager:
    def __init__(self, stations: list[Station]):
        self._lanes: dict[str, list[_LaneSchedule]] = {}
        for station in stations:
            self._lanes[station.id] = [
                _LaneSchedule() for _ in range(station.charger_count)
            ]

    def find_slot(
        self, station_id: str, arrival_minutes: int, duration_minutes: int
    ) -> LaneSlot | None:
        if station_id not in self._lanes:
            return None

        lane_schedules = self._lanes[station_id]
        best_slot: LaneSlot | None = None

        for lane_idx, schedule in enumerate(lane_schedules):
            slot = _find_earliest_slot(
                schedule.reservations, arrival_minutes, duration_minutes
            )
            if slot is None:
                continue
            if best_slot is None or slot.start_minutes < best_slot.start_minutes:
                best_slot = LaneSlot(
                    lane=lane_idx,
                    start_minutes=slot.start_minutes,
                    end_minutes=slot.end_minutes,
                )

        return best_slot

    def commit_slot(self, station_id: str, slot: LaneSlot) -> None:
        lane_schedules = self._lanes[station_id]
        lane_schedules[slot.lane].reservations.append(
            (slot.start_minutes, slot.end_minutes)
        )
        lane_schedules[slot.lane].reservations.sort(key=lambda x: x[0])

    def request(
        self, station_id: str, arrival_minutes: int, duration_minutes: int
    ) -> LaneSlot | None:
        slot = self.find_slot(station_id, arrival_minutes, duration_minutes)
        if slot is not None:
            self.commit_slot(station_id, slot)
        return slot


def _find_earliest_slot(
    existing: list[tuple[int, int]],
    arrival_minutes: int,
    duration_minutes: int,
) -> LaneSlot | None:
    if not existing:
        return LaneSlot(lane=0, start_minutes=arrival_minutes, end_minutes=arrival_minutes + duration_minutes)

    candidate_start = arrival_minutes
    for start, end in existing:
        if candidate_start < end and candidate_start + duration_minutes > start:
            candidate_start = end
            continue
        if candidate_start + duration_minutes <= start:
            return LaneSlot(lane=0, start_minutes=candidate_start, end_minutes=candidate_start + duration_minutes)

    return LaneSlot(lane=0, start_minutes=candidate_start, end_minutes=candidate_start + duration_minutes)
