import json
from pathlib import Path

from src.adapters.errors import MalformedScenarioError, ScenarioNotFoundError
from src.domain.models import (
    Bus,
    ChargingPolicy,
    Route,
    Scenario,
    Segment,
    Station,
    TravelPolicy,
    Weights,
)
from src.domain.time import parse_hhmm

SCENARIO_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"


def discover_scenario_ids() -> list[str]:
    files = sorted(SCENARIO_DIR.glob("scenario_*.json"))
    return [f.stem for f in files]


def load_scenario(scenario_id: str) -> Scenario:
    valid_ids = discover_scenario_ids()
    if scenario_id not in valid_ids:
        raise ScenarioNotFoundError(scenario_id)

    path = SCENARIO_DIR / f"{scenario_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MalformedScenarioError(scenario_id, str(e))

    try:
        return _parse_scenario(data)
    except (KeyError, ValueError, TypeError) as e:
        raise MalformedScenarioError(scenario_id, str(e))


def _parse_scenario(data: dict) -> Scenario:
    route_data = data["route"]
    segments = [
        Segment(
            from_stop=s["from"],
            to_stop=s["to"],
            distance_km=s["distance_km"],
        )
        for s in route_data["segments"]
    ]
    route = Route(
        name=route_data["name"],
        stops=list(route_data["stops"]),
        segments=segments,
    )
    stations = [
        Station(id=s["id"], charger_count=s["charger_count"])
        for s in data["stations"]
    ]
    cp = data["charging_policy"]
    charging_policy = ChargingPolicy(
        range_km=cp["range_km"],
        full_charge_minutes=cp["full_charge_minutes"],
    )
    tp = data["travel_policy"]
    travel_policy = TravelPolicy(speed_kmph=tp["speed_kmph"])
    w = data["weights"]
    weights = Weights(
        individual=float(w["individual"]),
        operator=float(w["operator"]),
        overall=float(w["overall"]),
    )
    buses = [
        Bus(
            id=b["id"],
            operator=b["operator"],
            direction=b["direction"],
            departure_minutes=parse_hhmm(b["departure"]),
        )
        for b in data["buses"]
    ]
    return Scenario(
        schema_version=data["schema_version"],
        id=data["id"],
        name=data["name"],
        description=data["description"],
        route=route,
        stations=stations,
        buses=buses,
        charging_policy=charging_policy,
        travel_policy=travel_policy,
        weights=weights,
    )
