from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    from_stop: str
    to_stop: str
    distance_km: int


@dataclass(frozen=True)
class Route:
    name: str
    stops: list[str]
    segments: list[Segment]


@dataclass(frozen=True)
class Station:
    id: str
    charger_count: int


@dataclass(frozen=True)
class ChargingPolicy:
    range_km: int = 240
    full_charge_minutes: int = 25


@dataclass(frozen=True)
class TravelPolicy:
    speed_kmph: int = 60


@dataclass(frozen=True)
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0


@dataclass(frozen=True)
class Bus:
    id: str
    operator: str
    direction: str
    departure_minutes: int


@dataclass(frozen=True)
class Scenario:
    schema_version: int
    id: str
    name: str
    description: str
    route: Route
    stations: list[Station]
    buses: list[Bus]
    charging_policy: ChargingPolicy
    travel_policy: TravelPolicy
    weights: Weights
