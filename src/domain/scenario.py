from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioSummary:
    id: str
    name: str
    description: str
