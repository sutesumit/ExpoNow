from dataclasses import dataclass

from src.adapters.scenario_catalog import list_scenario_summaries
from src.domain.scenario import ScenarioSummary
from src.scheduler.contract import ScheduleResult
from src.scheduler.stub import StubSchedulerStrategy


@dataclass(frozen=True)
class InitialViewModel:
    scenarios: list[ScenarioSummary]
    selected_scenario: ScenarioSummary
    schedule_result: ScheduleResult


def build_initial_view_model(selected_scenario_id: str | None) -> InitialViewModel:
    scenarios = list_scenario_summaries()
    selected_scenario = _select_scenario(scenarios, selected_scenario_id)
    schedule_result = StubSchedulerStrategy().schedule(selected_scenario)

    return InitialViewModel(
        scenarios=scenarios,
        selected_scenario=selected_scenario,
        schedule_result=schedule_result,
    )


def _select_scenario(
    scenarios: list[ScenarioSummary], selected_scenario_id: str | None
) -> ScenarioSummary:
    if selected_scenario_id is None:
        return scenarios[0]

    for scenario in scenarios:
        if scenario.id == selected_scenario_id:
            return scenario

    raise ValueError(f"Unknown scenario id: {selected_scenario_id}")
