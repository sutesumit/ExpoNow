import unittest

from src.domain.models import Scenario, Weights
from src.scheduler.contract import (
    BusPlan,
    ScheduleMetrics,
    ScheduleResult,
    StationReservation,
    TimelineEvent,
)
from src.scheduler.scoring import (
    compute_individual_wait_score,
    compute_operator_smoothness_score,
    compute_overall_network_score,
    compute_score_breakdown,
)


def _make_timeline(
    departure_minutes: int,
    arrival_station: str,
    arrival_minutes: int,
    wait_minutes: int,
    charge_duration: int,
    destination: str,
    final_arrival_minutes: int,
) -> list[TimelineEvent]:
    charge_start = arrival_minutes + wait_minutes
    charge_end = charge_start + charge_duration
    return [
        TimelineEvent("departure", departure_minutes, "Origin", "Departure"),
        TimelineEvent("arrival", arrival_minutes, arrival_station, "Arrival"),
        TimelineEvent("wait", arrival_minutes, arrival_station, "Wait"),
        TimelineEvent("charge_start", charge_start, arrival_station, "Charge start"),
        TimelineEvent("charge_end", charge_end, arrival_station, "Charge end"),
        TimelineEvent("arrival", final_arrival_minutes, destination, "Final arrival"),
    ]


class IndividualWaitScoreTests(unittest.TestCase):
    def test_individual_wait_component_sums_bus_wait_minutes(self):
        result = ScheduleResult(
            feasible=True,
            scenario_id="test",
            metrics=ScheduleMetrics(
                total_buses=2,
                total_charge_stops=2,
                total_wait_minutes=100,
                max_wait_minutes=60,
            ),
        )
        score = compute_individual_wait_score(result)
        self.assertEqual(score, 100.0)

    def test_individual_wait_returns_zero_when_metrics_none(self):
        result = ScheduleResult(feasible=True, scenario_id="test")
        score = compute_individual_wait_score(result)
        self.assertEqual(score, 0.0)


class OperatorSmoothnessScoreTests(unittest.TestCase):
    def _make_result_with_operator_waits(
        self, operator_waits: dict[str, list[int]]
    ) -> ScheduleResult:
        bus_plans = []
        reservations = []
        for op_name, waits in operator_waits.items():
            for i, wait in enumerate(waits):
                bus_id = f"{op_name}-{i}"
                station = "A"
                charge_duration = 25
                arrival = 30
                departure = 0
                charge_start = arrival + wait
                charge_end = charge_start + charge_duration
                travel_from_station_to_dest = 40
                final_arrival = charge_end + travel_from_station_to_dest

                events = [
                    TimelineEvent("departure", departure, "Origin", "Departure"),
                    TimelineEvent("arrival", arrival, station, "Arrival"),
                ]
                if wait > 0:
                    events.append(
                        TimelineEvent("wait", arrival, station, "Wait")
                    )
                events.extend([
                    TimelineEvent("charge_start", charge_start, station, "Charge start"),
                    TimelineEvent("charge_end", charge_end, station, "Charge end"),
                    TimelineEvent("arrival", final_arrival, "Dest", "Final arrival"),
                ])

                bus_plans.append(BusPlan(
                    bus_id=bus_id,
                    operator=op_name,
                    direction="Origin->Dest",
                    events=events,
                    final_arrival_minutes=final_arrival,
                ))
                reservations.append(StationReservation(
                    station=station,
                    bus_id=bus_id,
                    charger_lane=0,
                    start_minutes=charge_start,
                    end_minutes=charge_end,
                ))

        total_wait = sum(sum(w) for w in operator_waits.values())
        return ScheduleResult(
            feasible=True,
            scenario_id="test",
            bus_plans=bus_plans,
            station_reservations=reservations,
            metrics=ScheduleMetrics(
                total_buses=len(bus_plans),
                total_charge_stops=len(reservations),
                total_wait_minutes=total_wait,
                max_wait_minutes=max(max(w) for w in operator_waits.values()),
            ),
        )

    def test_operator_smoothness_penalizes_imbalance(self):
        balanced = self._make_result_with_operator_waits({
            "op_a": [10, 10],
            "op_b": [10, 10],
        })
        imbalanced = self._make_result_with_operator_waits({
            "op_a": [10, 10],
            "op_b": [50, 50],
        })

        balanced_score = compute_operator_smoothness_score(balanced)
        imbalanced_score = compute_operator_smoothness_score(imbalanced)

        self.assertLess(balanced_score, imbalanced_score)

    def test_operator_smoothness_returns_zero_for_empty_result(self):
        result = ScheduleResult(
            feasible=True, scenario_id="test",
            metrics=ScheduleMetrics(total_buses=0, total_charge_stops=0, total_wait_minutes=0, max_wait_minutes=0),
        )
        score = compute_operator_smoothness_score(result)
        self.assertEqual(score, 0.0)


class OverallNetworkScoreTests(unittest.TestCase):
    def test_overall_network_tracks_total_fleet_journey_time(self):
        bus_plans = [
            BusPlan(
                bus_id="bus-1", operator="op_a", direction="X->Y",
                events=[
                    TimelineEvent("departure", 0, "X", "Dep"),
                    TimelineEvent("arrival", 100, "Y", "Arr"),
                ],
                final_arrival_minutes=100,
            ),
            BusPlan(
                bus_id="bus-2", operator="op_b", direction="X->Y",
                events=[
                    TimelineEvent("departure", 10, "X", "Dep"),
                    TimelineEvent("arrival", 150, "Y", "Arr"),
                ],
                final_arrival_minutes=150,
            ),
        ]
        result = ScheduleResult(
            feasible=True, scenario_id="test",
            bus_plans=bus_plans,
            metrics=ScheduleMetrics(total_buses=2, total_charge_stops=0, total_wait_minutes=0, max_wait_minutes=0),
        )

        score = compute_overall_network_score(result)
        expected = (100 - 0) + (150 - 10)
        self.assertEqual(score, float(expected))


class ScoreBreakdownTests(unittest.TestCase):
    def test_score_breakdown_includes_unweighted_and_weighted_values(self):
        events = [
            TimelineEvent("departure", 0, "X", "Dep"),
            TimelineEvent("arrival", 30, "A", "Arr"),
            TimelineEvent("charge_start", 40, "A", "Start"),
            TimelineEvent("charge_end", 65, "A", "End"),
            TimelineEvent("arrival", 105, "Y", "Arr"),
        ]
        bus_plans = [
            BusPlan(
                bus_id="bus-1", operator="op_a", direction="X->Y",
                events=events, final_arrival_minutes=105,
            ),
        ]
        reservations = [
            StationReservation(station="A", bus_id="bus-1", charger_lane=0, start_minutes=40, end_minutes=65),
        ]
        result = ScheduleResult(
            feasible=True, scenario_id="test",
            bus_plans=bus_plans,
            station_reservations=reservations,
            metrics=ScheduleMetrics(
                total_buses=1, total_charge_stops=1,
                total_wait_minutes=10, max_wait_minutes=10,
            ),
        )
        scenario = Scenario(
            schema_version=1, id="test", name="test", description="",
            route=None, stations=[], buses=[],
            charging_policy=None, travel_policy=None,
            weights=Weights(individual=1.0, operator=2.0, overall=1.0),
        )

        breakdown = compute_score_breakdown(result, scenario)

        self.assertIn("individual_wait", breakdown.components)
        self.assertIn("operator_smoothness", breakdown.components)
        self.assertIn("overall_network", breakdown.components)

        for comp_name in ("individual_wait", "operator_smoothness", "overall_network"):
            comp = breakdown.components[comp_name]
            self.assertIn("unweighted", comp)
            self.assertIn("weighted", comp)
            self.assertIn("weight", comp)
            self.assertIn("description", comp)

        self.assertEqual(
            breakdown.components["individual_wait"]["unweighted"], 10.0
        )
        self.assertEqual(
            breakdown.components["individual_wait"]["weighted"], 10.0
        )
        self.assertEqual(
            breakdown.components["operator_smoothness"]["weighted"],
            breakdown.components["operator_smoothness"]["unweighted"] * 2.0,
        )

        expected_total = (
            breakdown.components["individual_wait"]["weighted"]
            + breakdown.components["operator_smoothness"]["weighted"]
            + breakdown.components["overall_network"]["weighted"]
        )
        self.assertEqual(breakdown.total_weighted, expected_total)

    def test_scheduler_scores_only_hard_valid_candidates(self):
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
        from src.scheduler.constraints import validate_schedule_invariants
        from src.adapters.scenario_loader import load_scenario

        scenario = load_scenario("scenario_1")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)
        self.assertIsNotNone(result.score_breakdown)
        self.assertGreater(result.score_breakdown.total_weighted, 0)
