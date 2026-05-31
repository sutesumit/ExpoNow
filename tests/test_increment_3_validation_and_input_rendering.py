from pathlib import Path
import unittest


class ScenarioValidatorTests(unittest.TestCase):
    def test_validator_accepts_all_assignment_scenarios(self):
        from src.adapters.scenario_loader import load_scenario
        from src.adapters.scenario_validator import validate_scenario

        for scenario_id in [
            "scenario_1",
            "scenario_2",
            "scenario_3",
            "scenario_4",
            "scenario_5",
        ]:
            scenario = load_scenario(scenario_id)
            errors = validate_scenario(scenario)
            self.assertEqual(
                errors,
                [],
                f"{scenario_id} should have no validation errors, got: {errors}",
            )

    def test_validator_rejects_duplicate_bus_ids(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [
            Station(id="A", charger_count=1),
        ]
        buses = [
            Bus(
                id="bus-BK-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
            Bus(
                id="bus-BK-01",
                operator="freshbus",
                direction="Bengaluru->Kochi",
                departure_minutes=1200,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_dup_bus",
            name="Test",
            description="Duplicate bus id",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("duplicate" in e.lower() or "bus-BK-01" in e for e in errors),
            f"Expected error about duplicate bus id, got: {errors}",
        )

    def test_validator_rejects_unknown_direction(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Mysore",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_dir",
            name="Test",
            description="Invalid direction",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("direction" in e.lower() for e in errors),
            f"Expected error about direction, got: {errors}",
        )

    def test_validator_rejects_negative_distance(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=-50),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_neg_dist",
            name="Test",
            description="Negative distance",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("distance" in e.lower() for e in errors),
            f"Expected error about distance, got: {errors}",
        )

    def test_validator_rejects_disconnected_route_segments(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "B", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="B", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=1), Station(id="B", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_disconnected_route",
            name="Test",
            description="Disconnected route",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("connect" in e.lower() or "route segment" in e.lower() for e in errors),
            f"Expected error about disconnected route segments, got: {errors}",
        )

    def test_validator_rejects_zero_charger_count(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=0)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_z_charger",
            name="Test",
            description="Zero charger count",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("charger" in e.lower() for e in errors),
            f"Expected error about charger count, got: {errors}",
        )

    def test_validator_rejects_negative_weight(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_neg_weight",
            name="Test",
            description="Negative weight",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(individual=1.0, operator=-1.0, overall=1.0),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("weight" in e.lower() for e in errors),
            f"Expected error about weight, got: {errors}",
        )

    def test_validator_rejects_non_positive_policy_values(self):
        from src.adapters.scenario_validator import validate_scenario
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

        route = Route(
            name="Test",
            stops=["Bengaluru", "A", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="Kochi", distance_km=100),
            ],
        )
        stations = [Station(id="A", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="Bengaluru->Kochi",
                departure_minutes=1140,
            ),
        ]
        scenario = Scenario(
            schema_version=1,
            id="test_bad_policy",
            name="Test",
            description="Bad policy values",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(range_km=0, full_charge_minutes=-1),
            travel_policy=TravelPolicy(speed_kmph=0),
            weights=Weights(),
        )

        errors = validate_scenario(scenario)
        self.assertTrue(
            any("range_km" in e for e in errors),
            f"Expected error about range, got: {errors}",
        )
        self.assertTrue(
            any("full_charge_minutes" in e for e in errors),
            f"Expected error about charge duration, got: {errors}",
        )
        self.assertTrue(
            any("speed_kmph" in e for e in errors),
            f"Expected error about speed, got: {errors}",
        )


class ReportingTableTests(unittest.TestCase):
    def test_input_tables_are_built_from_domain_objects(self):
        from src.adapters.scenario_loader import load_scenario
        from src.reporting.tables import build_summary_rows

        scenario = load_scenario("scenario_1")
        rows = build_summary_rows(scenario)
        self.assertIsInstance(rows, list)
        self.assertTrue(all(isinstance(r, dict) for r in rows))
        keys = {k for r in rows for k in r}
        self.assertIn("Field", keys)
        self.assertIn("Value", keys)

    def test_scenario_4_weight_row_displays_operator_two(self):
        from src.adapters.scenario_loader import load_scenario
        from src.reporting.tables import build_weight_rows

        scenario = load_scenario("scenario_4")
        rows = build_weight_rows(scenario)
        operator_row = next(
            (r for r in rows if r.get("Weight") == "Operator"), None
        )
        self.assertIsNotNone(operator_row, "No 'Operator' weight row found")
        self.assertEqual(operator_row["Value"], 2.0)

    def test_scenario_5_bus_departure_table_shows_72_minute_window(self):
        from src.adapters.scenario_loader import load_scenario
        from src.domain.time import parse_hhmm
        from src.reporting.tables import build_bus_departure_table

        scenario = load_scenario("scenario_5")
        rows = build_bus_departure_table(scenario)
        minutes = [parse_hhmm(r["Departure"]) for r in rows]
        self.assertEqual(max(minutes) - min(minutes), 72)


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_reporting_package_does_not_import_streamlit(self):
        reporting_dir = Path("src/reporting")
        python_files = list(reporting_dir.rglob("*.py"))

        self.assertTrue(python_files, "Expected reporting package files to exist")
        for path in python_files:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import streamlit", source)
            self.assertNotIn("from streamlit", source)


if __name__ == "__main__":
    unittest.main()
