from src.domain.models import Scenario
from src.scheduler.contract import ScheduleMetrics, ScheduleResult, ScoreBreakdown


class StubSchedulerStrategy:
    def schedule(self, scenario: Scenario) -> ScheduleResult:
        score_breakdown = ScoreBreakdown(
            components={
                "weights": {
                    "individual": scenario.weights.individual,
                    "operator": scenario.weights.operator,
                    "overall": scenario.weights.overall,
                }
            },
            total_weighted=0.0,
        )
        return ScheduleResult(
            feasible=True,
            scenario_id=scenario.id,
            metrics=ScheduleMetrics(
                total_buses=len(scenario.buses),
                total_charge_stops=0,
                total_wait_minutes=0,
                max_wait_minutes=0,
            ),
            score_breakdown=score_breakdown,
            warnings=[
                "Scheduling is not implemented yet. This is a placeholder result.",
            ],
        )
