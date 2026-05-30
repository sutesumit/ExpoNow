from dataclasses import dataclass, field
from typing import Protocol

from src.domain.models import Scenario


@dataclass(frozen=True)
class ChargingStop:
    station: str
    arrival_minutes: int
    wait_minutes: int
    charge_start_minutes: int
    charge_end_minutes: int
    charger_lane: int


@dataclass(frozen=True)
class TimelineEvent:
    event_type: str
    minutes: int
    location: str
    description: str


@dataclass(frozen=True)
class BusPlan:
    bus_id: str
    operator: str
    direction: str
    events: list[TimelineEvent]
    final_arrival_minutes: int | None = None


@dataclass(frozen=True)
class StationReservation:
    station: str
    bus_id: str
    charger_lane: int
    start_minutes: int
    end_minutes: int


@dataclass(frozen=True)
class ScheduleMetrics:
    total_buses: int
    total_charge_stops: int
    total_wait_minutes: int
    max_wait_minutes: int


@dataclass(frozen=True)
class ScoreBreakdown:
    components: dict[str, dict[str, float]]
    total_weighted: float


@dataclass(frozen=True)
class ScheduleResult:
    feasible: bool
    scenario_id: str
    bus_plans: list[BusPlan] = field(default_factory=list)
    station_reservations: list[StationReservation] = field(default_factory=list)
    metrics: ScheduleMetrics | None = None
    warnings: list[str] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None


class SchedulerStrategy(Protocol):
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        ...
