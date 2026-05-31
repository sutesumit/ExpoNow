from dataclasses import dataclass, field

from src.adapters.scenario_catalog import list_scenario_summaries
from src.adapters.scenario_loader import load_scenario
from src.adapters.scenario_validator import validate_scenario
from src.domain.models import Scenario
from src.domain.scenario import ScenarioSummary
from src.scheduler.contract import ScheduleResult
from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy


@dataclass(frozen=True)
class InitialViewModel:
    scenarios: list[ScenarioSummary]
    selected_scenario: ScenarioSummary
    schedule_result: ScheduleResult
    scenario: Scenario
    validation_errors: list[str] = field(default_factory=list)


def build_initial_view_model(selected_scenario_id: str | None) -> InitialViewModel:
    scenarios = list_scenario_summaries()
    selected_scenario = _select_scenario(scenarios, selected_scenario_id)
    scenario = load_scenario(selected_scenario.id)
    validation_errors = validate_scenario(scenario)
    if validation_errors:
        schedule_result = ScheduleResult(
            feasible=False,
            scenario_id=scenario.id,
        )
    else:
        try:
            schedule_result = CustomHeuristicStrategy().schedule(scenario)
        except Exception as exc:
            schedule_result = ScheduleResult(
                feasible=False,
                scenario_id=scenario.id,
                warnings=[f"Scheduling failed: {exc}"],
            )

    return InitialViewModel(
        scenarios=scenarios,
        selected_scenario=selected_scenario,
        schedule_result=schedule_result,
        scenario=scenario,
        validation_errors=validation_errors,
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
