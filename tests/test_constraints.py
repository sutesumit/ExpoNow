import unittest

from src.domain.models import Route, Segment, Scenario, Bus, Station, ChargingPolicy, TravelPolicy, Weights
from src.scheduler.contract import ChargingStop, BusPlan, TimelineEvent, ScheduleResult, ScheduleMetrics, StationReservation


class RangeConstraintTests(unittest.TestCase):
    def setUp(self):
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
        self.range_km = 240

    def test_range_constraint_allows_exact_boundary(self):
        from src.scheduler.constraints import check_range_constraints

        stops = [
            ChargingStop(station="B", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
            ChargingStop(station="D", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
        ]
        violations = check_range_constraints(self.route, "Bengaluru->Kochi", stops, 220)
        self.assertEqual(violations, [])

    def test_range_constraint_rejects_over_range_gap(self):
        from src.scheduler.constraints import check_range_constraints

        stops = [
            ChargingStop(station="C", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
        ]
        violations = check_range_constraints(self.route, "Bengaluru->Kochi", stops, 240)
        self.assertTrue(len(violations) > 0)

    def test_reverse_direction_candidates_follow_reverse_route_order(self):
        from src.scheduler.constraints import check_range_constraints

        stops = [
            ChargingStop(station="C", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
            ChargingStop(station="A", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
        ]
        violations = check_range_constraints(self.route, "Kochi->Bengaluru", stops, 240)
        self.assertEqual(violations, [])

    def test_empty_stops_detects_when_route_exceeds_range(self):
        from src.scheduler.constraints import check_range_constraints

        violations = check_range_constraints(self.route, "Bengaluru->Kochi", [], 240)
        self.assertTrue(
            any("540" in v for v in violations),
            f"Expected range violation for 540km route with 240km range, got: {violations}",
        )


class RouteOrderTests(unittest.TestCase):
    def test_valid_bk_direction(self):
        from src.scheduler.constraints import check_route_order

        stops = [
            ChargingStop(station="B", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
        ]
        violations = check_route_order(stops, "Bengaluru->Kochi", {"Bengaluru->Kochi", "Kochi->Bengaluru"})
        self.assertEqual(violations, [])

    def test_invalid_direction(self):
        from src.scheduler.constraints import check_route_order

        stops = []
        violations = check_route_order(stops, "Bengaluru->Mysore", {"Bengaluru->Kochi", "Kochi->Bengaluru"})
        self.assertTrue(len(violations) > 0)

    def test_consecutive_duplicate_stop(self):
        from src.scheduler.constraints import check_route_order

        stops = [
            ChargingStop(station="B", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
            ChargingStop(station="B", arrival_minutes=0, wait_minutes=0,
                         charge_start_minutes=0, charge_end_minutes=0, charger_lane=0),
        ]
        violations = check_route_order(stops, "Bengaluru->Kochi", {"Bengaluru->Kochi", "Kochi->Bengaluru"})
        self.assertTrue(len(violations) > 0)


class InvariantValidationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = Scenario(
            schema_version=1,
            id="test",
            name="Test",
            description="Test scenario",
            route=Route(
                name="Bengaluru-Kochi",
                stops=["Bengaluru", "A", "B", "C", "D", "Kochi"],
                segments=[
                    Segment(from_stop="Bengaluru", to_stop="A", distance_km=100),
                    Segment(from_stop="A", to_stop="B", distance_km=120),
                    Segment(from_stop="B", to_stop="C", distance_km=100),
                    Segment(from_stop="C", to_stop="D", distance_km=120),
                    Segment(from_stop="D", to_stop="Kochi", distance_km=100),
                ],
            ),
            stations=[
                Station(id="B", charger_count=1),
                Station(id="D", charger_count=1),
            ],
            buses=[
                Bus(id="bus-01", operator="kpn", direction="Bengaluru->Kochi",
                    departure_minutes=1140),
            ],
            charging_policy=ChargingPolicy(range_km=240, full_charge_minutes=25),
            travel_policy=TravelPolicy(speed_kmph=60),
            weights=Weights(),
        )

    def test_invariants_hold_for_valid_schedule(self):
        from src.scheduler.constraints import validate_schedule_invariants

        plan = BusPlan(
            bus_id="bus-01",
            operator="kpn",
            direction="Bengaluru->Kochi",
            events=[
                TimelineEvent(event_type="departure", minutes=1140, location="Bengaluru",
                              description="Departure from Bengaluru"),
                TimelineEvent(event_type="arrival", minutes=1360, location="B",
                              description="Arrival at B"),
                TimelineEvent(event_type="wait", minutes=1360, location="B",
                              description="Wait at B"),
                TimelineEvent(event_type="charge_start", minutes=1360, location="B",
                              description="Charge start at B"),
                TimelineEvent(event_type="charge_end", minutes=1385, location="B",
                              description="Charge end at B"),
                TimelineEvent(event_type="arrival", minutes=1605, location="D",
                              description="Arrival at D"),
                TimelineEvent(event_type="wait", minutes=1605, location="D",
                              description="Wait at D"),
                TimelineEvent(event_type="charge_start", minutes=1605, location="D",
                              description="Charge start at D"),
                TimelineEvent(event_type="charge_end", minutes=1630, location="D",
                              description="Charge end at D"),
                TimelineEvent(event_type="arrival", minutes=1730, location="Kochi",
                              description="Arrival at Kochi"),
            ],
            final_arrival_minutes=1730,
        )
        result = ScheduleResult(
            feasible=True,
            scenario_id="test",
            bus_plans=[plan],
            station_reservations=[
                StationReservation(station="B", bus_id="bus-01", charger_lane=0,
                                   start_minutes=1360, end_minutes=1385),
                StationReservation(station="D", bus_id="bus-01", charger_lane=0,
                                   start_minutes=1605, end_minutes=1630),
            ],
            metrics=ScheduleMetrics(total_buses=1, total_charge_stops=2,
                                    total_wait_minutes=0, max_wait_minutes=0),
        )
        violations = validate_schedule_invariants(self.scenario, result)
        self.assertEqual(violations, [])

    def test_invariants_detect_range_violation(self):
        from src.scheduler.constraints import validate_schedule_invariants

        plan = BusPlan(
            bus_id="bus-01",
            operator="kpn",
            direction="Bengaluru->Kochi",
            events=[
                TimelineEvent(event_type="departure", minutes=1140, location="Bengaluru",
                              description="Departure"),
                TimelineEvent(event_type="arrival", minutes=1730, location="Kochi",
                              description="Arrival at Kochi"),
            ],
            final_arrival_minutes=1730,
        )
        result = ScheduleResult(
            feasible=True,
            scenario_id="test",
            bus_plans=[plan],
            station_reservations=[],
            metrics=ScheduleMetrics(total_buses=1, total_charge_stops=0,
                                    total_wait_minutes=0, max_wait_minutes=0),
        )
        violations = validate_schedule_invariants(self.scenario, result)
        self.assertTrue(len(violations) > 0)

    def test_invariants_detect_overlapping_reservations(self):
        from src.scheduler.constraints import validate_schedule_invariants

        plan = BusPlan(
            bus_id="bus-01",
            operator="kpn",
            direction="Bengaluru->Kochi",
            events=[],
        )
        result = ScheduleResult(
            feasible=True,
            scenario_id="test",
            bus_plans=[plan],
            station_reservations=[
                StationReservation(station="B", bus_id="bus-01", charger_lane=0,
                                   start_minutes=100, end_minutes=200),
                StationReservation(station="B", bus_id="bus-02", charger_lane=0,
                                   start_minutes=150, end_minutes=250),
            ],
            metrics=ScheduleMetrics(total_buses=2, total_charge_stops=2,
                                    total_wait_minutes=0, max_wait_minutes=0),
        )
        violations = validate_schedule_invariants(self.scenario, result)
        self.assertTrue(
            any("overlapping" in v.lower() for v in violations),
            f"Expected overlapping reservation violation, got: {violations}",
        )


class ReservationManagerTests(unittest.TestCase):
    def test_single_charger_reservations_do_not_overlap(self):
        from src.scheduler.reservations import ReservationManager
        from src.domain.models import Station

        manager = ReservationManager([Station(id="B", charger_count=1)])

        slot1 = manager.request("B", 100, 25)
        self.assertIsNotNone(slot1)
        self.assertEqual(slot1.start_minutes, 100)
        self.assertEqual(slot1.end_minutes, 125)

        slot2 = manager.request("B", 110, 25)
        self.assertIsNotNone(slot2)
        self.assertEqual(slot2.start_minutes, 125)
        self.assertEqual(slot2.end_minutes, 150)

    def test_multiple_charger_reservations_allow_parallel_lanes(self):
        from src.scheduler.reservations import ReservationManager
        from src.domain.models import Station

        manager = ReservationManager([Station(id="B", charger_count=2)])

        slot1 = manager.request("B", 100, 25)
        slot2 = manager.request("B", 100, 25)

        self.assertIsNotNone(slot1)
        self.assertIsNotNone(slot2)
        self.assertNotEqual(slot1.lane, slot2.lane)

    def test_reservation_with_gap_fills_hole(self):
        from src.scheduler.reservations import ReservationManager
        from src.domain.models import Station

        manager = ReservationManager([Station(id="B", charger_count=1)])

        slot1 = manager.request("B", 100, 25)
        self.assertEqual(slot1.start_minutes, 100)
        self.assertEqual(slot1.end_minutes, 125)

        slot2 = manager.request("B", 150, 25)
        self.assertEqual(slot2.start_minutes, 150)
        self.assertEqual(slot2.end_minutes, 175)

        slot3 = manager.request("B", 110, 25)
        self.assertEqual(slot3.start_minutes, 125)
        self.assertEqual(slot3.end_minutes, 150)

    def test_reservation_at_unknown_station_returns_none(self):
        from src.scheduler.reservations import ReservationManager
        from src.domain.models import Station

        manager = ReservationManager([Station(id="B", charger_count=1)])
        slot = manager.request("Z", 100, 25)
        self.assertIsNone(slot)


if __name__ == "__main__":
    unittest.main()
