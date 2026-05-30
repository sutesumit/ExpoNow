from src.domain.scenario import ScenarioSummary


def list_scenario_summaries() -> list[ScenarioSummary]:
    """Return lightweight assignment scenario metadata for the app shell."""
    return [
        ScenarioSummary(
            id="scenario_1",
            name="Scenario 1",
            description="Assignment scenario 1. Full input data arrives in Increment 1.",
        ),
        ScenarioSummary(
            id="scenario_2",
            name="Scenario 2",
            description="Assignment scenario 2. Full input data arrives in Increment 1.",
        ),
        ScenarioSummary(
            id="scenario_3",
            name="Scenario 3",
            description="Assignment scenario 3. Full input data arrives in Increment 1.",
        ),
        ScenarioSummary(
            id="scenario_4",
            name="Scenario 4",
            description="Assignment scenario 4. Full input data arrives in Increment 1.",
        ),
        ScenarioSummary(
            id="scenario_5",
            name="Scenario 5",
            description="Assignment scenario 5. Full input data arrives in Increment 1.",
        ),
    ]
