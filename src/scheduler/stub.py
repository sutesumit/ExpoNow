from src.domain.scenario import ScenarioSummary
from src.scheduler.contract import ScheduleResult


class StubSchedulerStrategy:
    def schedule(self, scenario: ScenarioSummary) -> ScheduleResult:
        return ScheduleResult(
            feasible=True,
            scenario_id=scenario.id,
            warnings=[
                "Scheduling is not implemented yet. This is a placeholder result."
            ],
        )
