import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Sub-task 1: Time helpers
# ---------------------------------------------------------------------------


class TimeHelperTests(unittest.TestCase):
    def test_parse_hhmm_returns_minutes_since_midnight(self):
        from src.domain.time import parse_hhmm

        self.assertEqual(parse_hhmm("19:00"), 1140)
        self.assertEqual(parse_hhmm("00:00"), 0)
        self.assertEqual(parse_hhmm("23:59"), 1439)

    def test_format_minutes_returns_hhmm(self):
        from src.domain.time import format_minutes

        self.assertEqual(format_minutes(1140), "19:00")
        self.assertEqual(format_minutes(0), "00:00")

    def test_time_helpers_round_trip(self):
        from src.domain.time import format_minutes, parse_hhmm

        self.assertEqual(format_minutes(parse_hhmm("20:12")), "20:12")

    def test_parse_hhmm_raises_on_bad_input(self):
        from src.domain.time import parse_hhmm

        with self.assertRaises(ValueError):
            parse_hhmm("")
        with self.assertRaises(ValueError):
            parse_hhmm("abc")
        with self.assertRaises(ValueError):
            parse_hhmm("25:00")
        with self.assertRaises(ValueError):
            parse_hhmm("12:60")


# ---------------------------------------------------------------------------
# Sub-task 2: Route helpers
# ---------------------------------------------------------------------------


class RouteHelperTests(unittest.TestCase):
    def setUp(self):
        from src.domain.models import Route, Segment

        self.route = Route(
            name="Bengaluru-Kochi",
            stops=["Bengaluru", "A", "B", "C", "D", "Kochi"],
            segments=[
                Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                Segment(from_stop="A", to_stop="B", distance_km=120),
                Segment(from_stop="B", to_stop="C", distance_km=100),
                Segment(from_stop="C", to_stop="D", distance_km=120),
                Segment(from_stop="D", to_stop="Kochi", distance_km=100),
            ],
        )

    def test_route_order_for_bengaluru_to_kochi(self):
        from src.domain.route import get_ordered_stops

        stops = get_ordered_stops(self.route, "Bengaluru->Kochi")
        self.assertEqual(stops, ["Bengaluru", "A", "B", "C", "D", "Kochi"])

    def test_route_order_for_kochi_to_bengaluru(self):
        from src.domain.route import get_ordered_stops

        stops = get_ordered_stops(self.route, "Kochi->Bengaluru")
        self.assertEqual(stops, ["Kochi", "D", "C", "B", "A", "Bengaluru"])

    def test_total_distance_matches_assignment(self):
        from src.domain.route import total_distance

        self.assertEqual(total_distance(self.route), 540)

    def test_distance_between_returns_correct_value(self):
        from src.domain.route import distance_between

        self.assertEqual(distance_between(self.route, "Bengaluru", "B"), 220)
        self.assertEqual(distance_between(self.route, "A", "D"), 340)

    def test_distance_between_rejects_invalid_station(self):
        from src.domain.route import distance_between

        with self.assertRaises(ValueError):
            distance_between(self.route, "Bengaluru", "Z")


# ---------------------------------------------------------------------------
# Sub-task 3: Domain models
# ---------------------------------------------------------------------------


class DomainModelTests(unittest.TestCase):
    def test_segment_construction(self):
        from src.domain.models import Segment

        s = Segment(from_stop="A", to_stop="B", distance_km=120)
        self.assertEqual(s.from_stop, "A")
        self.assertEqual(s.to_stop, "B")
        self.assertEqual(s.distance_km, 120)

    def test_route_construction(self):
        from src.domain.models import Route, Segment

        segments = [Segment(from_stop="A", to_stop="B", distance_km=120)]
        r = Route(name="Test", stops=["A", "B"], segments=segments)
        self.assertEqual(r.name, "Test")
        self.assertEqual(r.stops, ["A", "B"])
        self.assertEqual(r.segments, segments)

    def test_station_construction(self):
        from src.domain.models import Station

        s = Station(id="A", charger_count=1)
        self.assertEqual(s.id, "A")
        self.assertEqual(s.charger_count, 1)

    def test_charging_policy_defaults(self):
        from src.domain.models import ChargingPolicy

        cp = ChargingPolicy()
        self.assertEqual(cp.range_km, 240)
        self.assertEqual(cp.full_charge_minutes, 25)

    def test_travel_policy_defaults(self):
        from src.domain.models import TravelPolicy

        tp = TravelPolicy()
        self.assertEqual(tp.speed_kmph, 60)

    def test_weights_construction(self):
        from src.domain.models import Weights

        w = Weights(individual=1.0, operator=2.0, overall=1.0)
        self.assertEqual(w.individual, 1.0)
        self.assertEqual(w.operator, 2.0)
        self.assertEqual(w.overall, 1.0)

    def test_weights_defaults(self):
        from src.domain.models import Weights

        w = Weights()
        self.assertEqual(w.individual, 1.0)
        self.assertEqual(w.operator, 1.0)
        self.assertEqual(w.overall, 1.0)

    def test_bus_construction(self):
        from src.domain.models import Bus

        b = Bus(
            id="bus-BK-01",
            operator="kpn",
            direction="Bengaluru->Kochi",
            departure_minutes=1140,
        )
        self.assertEqual(b.id, "bus-BK-01")
        self.assertEqual(b.operator, "kpn")
        self.assertEqual(b.direction, "Bengaluru->Kochi")
        self.assertEqual(b.departure_minutes, 1140)

    def test_scenario_construction(self):
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
            stops=["A", "B"],
            segments=[Segment(from_stop="A", to_stop="B", distance_km=100)],
        )
        stations = [Station(id="A", charger_count=1)]
        buses = [
            Bus(
                id="bus-01",
                operator="kpn",
                direction="A->B",
                departure_minutes=0,
            )
        ]
        scenario = Scenario(
            schema_version=1,
            id="test",
            name="Test Scenario",
            description="A test",
            route=route,
            stations=stations,
            buses=buses,
            charging_policy=ChargingPolicy(),
            travel_policy=TravelPolicy(),
            weights=Weights(),
        )
        self.assertEqual(scenario.id, "test")
        self.assertEqual(len(scenario.buses), 1)
        self.assertEqual(len(scenario.stations), 1)
        self.assertEqual(scenario.weights.individual, 1.0)

    def test_domain_models_are_frozen(self):
        from src.domain.models import Segment

        s = Segment(from_stop="A", to_stop="B", distance_km=100)
        with self.assertRaises(AttributeError):
            s.distance_km = 200


# ---------------------------------------------------------------------------
# Sub-task 4: Schedule-facing models
# ---------------------------------------------------------------------------


class ScheduleContractTests(unittest.TestCase):
    def test_bus_plan_fields(self):
        from src.scheduler.contract import BusPlan

        bp = BusPlan(
            bus_id="bus-BK-01",
            operator="kpn",
            direction="Bengaluru->Kochi",
            events=[],
            final_arrival_minutes=None,
        )
        self.assertEqual(bp.bus_id, "bus-BK-01")
        self.assertEqual(bp.events, [])
        self.assertIsNone(bp.final_arrival_minutes)

    def test_charging_stop_fields(self):
        from src.scheduler.contract import ChargingStop

        cs = ChargingStop(
            station="B",
            arrival_minutes=200,
            wait_minutes=5,
            charge_start_minutes=205,
            charge_end_minutes=230,
            charger_lane=0,
        )
        self.assertEqual(cs.station, "B")
        self.assertEqual(cs.arrival_minutes, 200)
        self.assertEqual(cs.charger_lane, 0)

    def test_station_reservation_fields(self):
        from src.scheduler.contract import StationReservation

        sr = StationReservation(
            station="B",
            bus_id="bus-BK-01",
            charger_lane=0,
            start_minutes=205,
            end_minutes=230,
        )
        self.assertEqual(sr.station, "B")
        self.assertEqual(sr.bus_id, "bus-BK-01")
        self.assertEqual(sr.start_minutes, 205)

    def test_timeline_event_fields(self):
        from src.scheduler.contract import TimelineEvent

        te = TimelineEvent(
            event_type="departure",
            minutes=1140,
            location="Bengaluru",
            description="Departure from Bengaluru",
        )
        self.assertEqual(te.event_type, "departure")
        self.assertEqual(te.minutes, 1140)
        self.assertEqual(te.location, "Bengaluru")

    def test_schedule_metrics_fields(self):
        from src.scheduler.contract import ScheduleMetrics

        sm = ScheduleMetrics(
            total_buses=20,
            total_charge_stops=40,
            total_wait_minutes=120,
            max_wait_minutes=15,
        )
        self.assertEqual(sm.total_buses, 20)
        self.assertEqual(sm.total_charge_stops, 40)
        self.assertEqual(sm.max_wait_minutes, 15)

    def test_score_breakdown_fields(self):
        from src.scheduler.contract import ScoreBreakdown

        sb = ScoreBreakdown(
            components={
                "individual": {"unweighted": 100.0, "weight": 1.0, "weighted": 100.0}
            },
            total_weighted=100.0,
        )
        self.assertIn("individual", sb.components)
        self.assertEqual(sb.total_weighted, 100.0)

    def test_schedule_result_typed_fields(self):
        from src.scheduler.contract import (
            BusPlan,
            ScheduleMetrics,
            ScheduleResult,
            ScoreBreakdown,
            StationReservation,
        )

        sr = ScheduleResult(
            feasible=True,
            scenario_id="test",
            bus_plans=[
                BusPlan(bus_id="b1", operator="op", direction="A->B", events=[])
            ],
            station_reservations=[
                StationReservation(
                    station="A",
                    bus_id="b1",
                    charger_lane=0,
                    start_minutes=0,
                    end_minutes=10,
                )
            ],
            metrics=ScheduleMetrics(
                total_buses=1,
                total_charge_stops=1,
                total_wait_minutes=5,
                max_wait_minutes=5,
            ),
            score_breakdown=ScoreBreakdown(components={}, total_weighted=0.0),
        )
        self.assertTrue(sr.feasible)
        self.assertEqual(len(sr.bus_plans), 1)
        self.assertEqual(len(sr.station_reservations), 1)
        self.assertIsNotNone(sr.metrics)
        self.assertEqual(sr.metrics.total_buses, 1)
        self.assertIsNotNone(sr.score_breakdown)
        self.assertEqual(sr.score_breakdown.total_weighted, 0.0)


# ---------------------------------------------------------------------------
# Sub-task 5: Adapter errors
# ---------------------------------------------------------------------------


class AdapterErrorTests(unittest.TestCase):
    def test_adapter_error_is_base(self):
        from src.adapters.errors import AdapterError

        e = AdapterError("msg")
        self.assertIsInstance(e, Exception)
        self.assertEqual(str(e), "msg")

    def test_scenario_not_found_error(self):
        from src.adapters.errors import ScenarioNotFoundError

        e = ScenarioNotFoundError("scenario_99")
        self.assertIn("scenario_99", str(e))

    def test_malformed_scenario_error(self):
        from src.adapters.errors import MalformedScenarioError

        e = MalformedScenarioError("scenario_1", "Invalid JSON")
        self.assertIn("scenario_1", str(e))
        self.assertIn("Invalid JSON", str(e))


# ---------------------------------------------------------------------------
# Sub-task 6: Scenario loader
# ---------------------------------------------------------------------------


class ScenarioLoaderTests(unittest.TestCase):
    def test_discover_scenarios_returns_all_five_in_display_order(self):
        from src.adapters.scenario_loader import discover_scenario_ids

        ids = discover_scenario_ids()
        self.assertEqual(
            ids, ["scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5"]
        )

    def test_load_scenario_returns_domain_object_not_dict(self):
        from src.adapters.scenario_loader import load_scenario
        from src.domain.models import Scenario

        scenario = load_scenario("scenario_1")
        self.assertIsInstance(scenario, Scenario)
        self.assertNotIsInstance(scenario, dict)

    def test_load_scenario_populates_correct_data(self):
        from src.adapters.scenario_loader import load_scenario
        from src.domain.route import total_distance

        scenario = load_scenario("scenario_1")
        self.assertEqual(scenario.id, "scenario_1")
        self.assertEqual(scenario.name, "Scenario 1 - Even spacing")
        self.assertEqual(len(scenario.buses), 20)
        self.assertEqual(len(scenario.stations), 4)
        self.assertEqual(total_distance(scenario.route), 540)
        self.assertEqual(scenario.weights.individual, 1.0)
        self.assertEqual(scenario.weights.operator, 1.0)
        self.assertEqual(scenario.weights.overall, 1.0)

    def test_load_scenario_4_has_operator_weight_two(self):
        from src.adapters.scenario_loader import load_scenario

        scenario = load_scenario("scenario_4")
        self.assertEqual(scenario.weights.operator, 2.0)

    def test_load_scenario_5_buses_have_72_minute_window(self):
        from src.adapters.scenario_loader import load_scenario

        scenario = load_scenario("scenario_5")
        minutes = [bus.departure_minutes for bus in scenario.buses]
        self.assertEqual(min(minutes), 1140)
        self.assertEqual(max(minutes), 1212)
        self.assertEqual(max(minutes) - min(minutes), 72)

    def test_missing_scenario_id_raises_adapter_error(self):
        from src.adapters.errors import ScenarioNotFoundError
        from src.adapters.scenario_loader import load_scenario

        with self.assertRaises(ScenarioNotFoundError):
            load_scenario("nonexistent")

    def test_malformed_json_raises_adapter_error(self):
        from src.adapters.errors import MalformedScenarioError
        from src.adapters.scenario_loader import load_scenario

        bad_path = Path("data/scenarios/scenario_malformed.json")
        try:
            bad_path.write_text("{bad json}", encoding="utf-8")
            with self.assertRaises(MalformedScenarioError):
                load_scenario("scenario_malformed")
        finally:
            bad_path.unlink(missing_ok=True)

    def test_scenario_weights_are_available_to_schedule_result(self):
        from src.adapters.scenario_loader import load_scenario
        from src.domain.models import Weights

        scenario = load_scenario("scenario_1")
        self.assertIsInstance(scenario.weights, Weights)
        self.assertEqual(scenario.weights.individual, 1.0)


# ---------------------------------------------------------------------------
# Sub-task 7: Updated catalog integration
# ---------------------------------------------------------------------------


class CatalogIntegrationTests(unittest.TestCase):
    def test_list_scenario_summaries_returns_five_real_summaries(self):
        from src.adapters.scenario_catalog import list_scenario_summaries

        summaries = list_scenario_summaries()
        self.assertEqual(len(summaries), 5)
        self.assertEqual(
            [s.id for s in summaries],
            ["scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5"],
        )

    def test_build_view_model_uses_loaded_scenario(self):
        from src.app_view_model import build_initial_view_model

        vm = build_initial_view_model("scenario_1")
        sb = vm.schedule_result.score_breakdown
        self.assertIsNotNone(sb)
        self.assertIn("individual_wait", sb.components)
        self.assertIn("operator_smoothness", sb.components)
        self.assertIn("overall_network", sb.components)
        self.assertEqual(sb.components["individual_wait"]["weight"], 1.0)
        self.assertEqual(sb.components["operator_smoothness"]["weight"], 1.0)
        self.assertEqual(sb.components["overall_network"]["weight"], 1.0)


if __name__ == "__main__":
    unittest.main()
