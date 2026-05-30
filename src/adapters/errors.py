class AdapterError(Exception):
    pass


class ScenarioNotFoundError(AdapterError):
    def __init__(self, scenario_id: str) -> None:
        super().__init__(f"Scenario not found: {scenario_id}")


class MalformedScenarioError(AdapterError):
    def __init__(self, scenario_id: str, detail: str) -> None:
        super().__init__(f"Malformed scenario {scenario_id}: {detail}")
