import json
import unittest
from pathlib import Path

from src.adapters.scenario_loader import _parse_scenario
from src.domain.models import Scenario, Weights
from src.scheduler.contract import (
    BusPlan,
    ScheduleMetrics,
    ScheduleResult,
    StationReservation,
    TimelineEvent,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture_scenario(fixture_name: str) -> Scenario:
    path = FIXTURE_DIR / f"{fixture_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_scenario(data)


def _make_simple_result() -> ScheduleResult:
    events = [
        TimelineEvent("departure", 0, "Origin", "Departure"),
        TimelineEvent("arrival", 30, "A", "Arrival"),
        TimelineEvent("wait", 30, "A", "Wait"),
        TimelineEvent("charge_start", 40, "A", "Charge start"),
        TimelineEvent("charge_end", 65, "A", "Charge end"),
        TimelineEvent("arrival", 105, "Dest", "Final arrival"),
    ]
    bus_plans = [
        BusPlan(
            bus_id="bus-1",
            operator="op_a",
            direction="X->Y",
            events=events,
            final_arrival_minutes=105,
        ),
    ]
    reservations = [
        StationReservation(
            station="A",
            bus_id="bus-1",
            charger_lane=0,
            start_minutes=40,
            end_minutes=65,
        ),
    ]
    return ScheduleResult(
        feasible=True,
        scenario_id="test",
        bus_plans=bus_plans,
        station_reservations=reservations,
        metrics=ScheduleMetrics(
            total_buses=1,
            total_charge_stops=1,
            total_wait_minutes=10,
            max_wait_minutes=10,
        ),
    )


def _make_simple_scenario(weights: Weights) -> Scenario:
    return Scenario(
        schema_version=1,
        id="test",
        name="test",
        description="",
        route=None,
        stations=[],
        buses=[],
        charging_policy=None,
        travel_policy=None,
        weights=weights,
    )


class CustomScoreComponentTests(unittest.TestCase):
    def test_custom_score_component_participates_in_total_and_breakdown(self):
        from src.scheduler.scoring import SCORE_COMPONENTS, compute_score_breakdown

        def my_penalty(result, scenario):
            return "my_penalty", {
                "unweighted": 50.0,
                "weighted": 50.0 * scenario.weights.individual,
                "weight": scenario.weights.individual,
                "description": "Test penalty",
            }

        SCORE_COMPONENTS["my_penalty"] = my_penalty
        try:
            result = _make_simple_result()
            scenario = _make_simple_scenario(weights=Weights(1.0, 1.0, 1.0))
            breakdown = compute_score_breakdown(result, scenario)
            self.assertIn("my_penalty", breakdown.components)
            expected_total = (
                breakdown.components["individual_wait"]["weighted"]
                + breakdown.components["operator_smoothness"]["weighted"]
                + breakdown.components["overall_network"]["weighted"]
                + 50.0
            )
            self.assertEqual(breakdown.total_weighted, expected_total)
        finally:
            del SCORE_COMPONENTS["my_penalty"]


class MultiChargerReservationTests(unittest.TestCase):
    def test_two_charger_station_allows_parallel_reservations(self):
        from src.scheduler.reservations import ReservationManager

        scenario = _load_fixture_scenario("scenario_multi_charger")
        mgr = ReservationManager(scenario.stations)
        slot1 = mgr.request("B", 100, 25)
        slot2 = mgr.request("B", 110, 25)
        self.assertIsNotNone(slot1)
        self.assertIsNotNone(slot2)
        self.assertNotEqual(
            slot1.lane,
            slot2.lane,
            "Two overlapping requests at B with 2 chargers should use different lanes",
        )


class MultiChargerReportingTests(unittest.TestCase):
    def test_reporting_includes_charger_lane_for_multi_charger_fixture(self):
        from src.reporting.tables import (
            build_bus_timetable_rows,
            build_station_queue_rows,
        )
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_multi_charger")
        result = CustomHeuristicStrategy().schedule(scenario)
        timetable = build_bus_timetable_rows(result)
        stations = build_station_queue_rows(result)

        for row in timetable:
            if row["Station"] == "B":
                self.assertIn(row["Charger Lane"], (0, 1))
        self.assertIn("B", stations)
        lanes_at_b = {r["Charger Lane"] for r in stations["B"]}
        self.assertGreaterEqual(len(lanes_at_b), 1)


class NewOperatorTests(unittest.TestCase):
    def test_new_operator_in_fixture_does_not_require_code_change(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_new_operator")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)
        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)
        operators = {p.operator for p in result.bus_plans}
        self.assertIn("express_red", operators)


class DocsCoverageTests(unittest.TestCase):
    def test_docs_explain_weight_change_and_new_rule_extension(self):
        arch = Path("ARCHITECTURE.md").read_text(encoding="utf-8")

        self.assertIn("Changing a Weight", arch)
        self.assertIn("weights", arch.lower())
        self.assertIn("Adding a New Rule", arch)
        self.assertIn("SCORE_COMPONENTS", arch)


if __name__ == "__main__":
    unittest.main()
