from dataclasses import dataclass, field
from typing import Any, Protocol

from src.domain.scenario import ScenarioSummary


@dataclass(frozen=True)
class ScheduleResult:
    feasible: bool
    scenario_id: str
    bus_plans: list[Any] = field(default_factory=list)
    station_reservations: list[Any] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    score_breakdown: dict[str, Any] = field(default_factory=dict)


class SchedulerStrategy(Protocol):
    def schedule(self, scenario: ScenarioSummary) -> ScheduleResult:
        """Build a schedule result for the supplied scenario."""
