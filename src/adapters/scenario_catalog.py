from src.adapters.scenario_loader import discover_scenario_ids, load_scenario
from src.domain.scenario import ScenarioSummary


def list_scenario_summaries() -> list[ScenarioSummary]:
    ids = discover_scenario_ids()
    summaries: list[ScenarioSummary] = []
    for scenario_id in ids:
        scenario = load_scenario(scenario_id)
        summaries.append(
            ScenarioSummary(
                id=scenario.id,
                name=scenario.name,
                description=scenario.description,
                is_placeholder=False,
            )
        )
    return summaries
