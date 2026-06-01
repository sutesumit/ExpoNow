from dataclasses import dataclass, field

from src.adapters.scenario_catalog import list_scenario_summaries
from src.adapters.scenario_loader import load_scenario
from src.adapters.scenario_validator import validate_scenario
from src.domain.models import Scenario
from src.domain.scenario import ScenarioSummary
from src.scheduler.contract import ScheduleResult
from src.scheduler.strategies.registry import (
    DEFAULT_STRATEGY_ID,
    StrategyOption,
    get_strategy,
    get_strategy_option,
    list_strategy_options,
)


@dataclass(frozen=True)
class InitialViewModel:
    scenarios: list[ScenarioSummary]
    selected_scenario: ScenarioSummary
    strategy_options: list[StrategyOption]
    selected_strategy: StrategyOption
    schedule_result: ScheduleResult
    scenario: Scenario
    validation_errors: list[str] = field(default_factory=list)


def build_initial_view_model(
    selected_scenario_id: str | None,
    selected_strategy_id: str | None = None,
) -> InitialViewModel:
    scenarios = list_scenario_summaries()
    selected_scenario = _select_scenario(scenarios, selected_scenario_id)
    strategy_options = list_strategy_options()
    selected_strategy_id = selected_strategy_id or DEFAULT_STRATEGY_ID
    selected_strategy = get_strategy_option(selected_strategy_id)
    scenario = load_scenario(selected_scenario.id)
    validation_errors = validate_scenario(scenario)
    if validation_errors:
        schedule_result = ScheduleResult(
            feasible=False,
            scenario_id=scenario.id,
        )
    else:
        try:
            schedule_result = get_strategy(selected_strategy_id).schedule(scenario)
        except Exception as exc:
            schedule_result = ScheduleResult(
                feasible=False,
                scenario_id=scenario.id,
                warnings=[f"Scheduling failed: {exc}"],
            )

    return InitialViewModel(
        scenarios=scenarios,
        selected_scenario=selected_scenario,
        strategy_options=strategy_options,
        selected_strategy=selected_strategy,
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
