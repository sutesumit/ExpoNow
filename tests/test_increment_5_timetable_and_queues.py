from pathlib import Path
import unittest

from src.scheduler.contract import (
    BusPlan,
    ScheduleMetrics,
    ScheduleResult,
    StationReservation,
    TimelineEvent,
)


def _make_one_bus_result() -> ScheduleResult:
    events = [
        TimelineEvent("departure", 0, "Bengaluru", "Departure from Bengaluru"),
        TimelineEvent("arrival", 180, "A", "Arrival at A"),
        TimelineEvent("wait", 180, "A", "Wait at A"),
        TimelineEvent("charge_start", 195, "A", "Charge start at A"),
        TimelineEvent("charge_end", 285, "A", "Charge end at A"),
        TimelineEvent("arrival", 345, "Kochi", "Arrival at Kochi"),
    ]
    bus_plan = BusPlan(
        bus_id="bus-BK-01",
        operator="kpn",
        direction="Bengaluru->Kochi",
        events=events,
        final_arrival_minutes=345,
    )
    reservation = StationReservation(
        station="A",
        bus_id="bus-BK-01",
        charger_lane=0,
        start_minutes=195,
        end_minutes=285,
    )
    metrics = ScheduleMetrics(
        total_buses=1,
        total_charge_stops=1,
        total_wait_minutes=15,
        max_wait_minutes=15,
    )
    return ScheduleResult(
        feasible=True,
        scenario_id="test",
        bus_plans=[bus_plan],
        station_reservations=[reservation],
        metrics=metrics,
    )


def _make_three_bus_result() -> ScheduleResult:
    buses_data = [
        ("bus-C", "freshbus", "Kochi->Bengaluru", 600, None),
        ("bus-A", "kpn", "Bengaluru->Kochi", 0, None),
        ("bus-B", "kpn", "Bengaluru->Kochi", 300, None),
    ]
    plans = []
    reservations = []
    for bus_id, operator, direction, dep, _ in buses_data:
        events = [
            TimelineEvent("departure", dep, "Bengaluru" if "Bengaluru" in direction else "Kochi", "Departure"),
        ]
        plans.append(BusPlan(
            bus_id=bus_id,
            operator=operator,
            direction=direction,
            events=events,
        ))
    metrics = ScheduleMetrics(total_buses=3, total_charge_stops=0, total_wait_minutes=0, max_wait_minutes=0)
    return ScheduleResult(
        feasible=True,
        scenario_id="test_3bus",
        bus_plans=plans,
        station_reservations=reservations,
        metrics=metrics,
    )


def _make_same_time_diff_lanes_result() -> ScheduleResult:
    events_a = [
        TimelineEvent("departure", 0, "Bengaluru", "Departure"),
        TimelineEvent("arrival", 180, "A", "Arrival at A"),
        TimelineEvent("charge_start", 185, "A", "Charge start at A"),
        TimelineEvent("charge_end", 275, "A", "Charge end at A"),
        TimelineEvent("arrival", 335, "Kochi", "Arrival at Kochi"),
    ]
    events_b = [
        TimelineEvent("departure", 5, "Bengaluru", "Departure"),
        TimelineEvent("arrival", 185, "A", "Arrival at A"),
        TimelineEvent("charge_start", 185, "A", "Charge start at A"),
        TimelineEvent("charge_end", 275, "A", "Charge end at A"),
        TimelineEvent("arrival", 335, "Kochi", "Arrival at Kochi"),
    ]
    plan_a = BusPlan(bus_id="bus-BK-01", operator="kpn", direction="Bengaluru->Kochi", events=events_a, final_arrival_minutes=335)
    plan_b = BusPlan(bus_id="bus-KB-01", operator="freshbus", direction="Kochi->Bengaluru", events=events_b, final_arrival_minutes=335)
    res_a = StationReservation(station="A", bus_id="bus-BK-01", charger_lane=0, start_minutes=185, end_minutes=275)
    res_b = StationReservation(station="A", bus_id="bus-KB-01", charger_lane=1, start_minutes=185, end_minutes=275)
    metrics = ScheduleMetrics(total_buses=2, total_charge_stops=2, total_wait_minutes=0, max_wait_minutes=0)
    return ScheduleResult(
        feasible=True,
        scenario_id="test_lanes",
        bus_plans=[plan_b, plan_a],
        station_reservations=[res_a, res_b],
        metrics=metrics,
    )


def _make_infeasible_result() -> ScheduleResult:
    return ScheduleResult(
        feasible=False,
        scenario_id="test_infeasible",
        warnings=["Test warning: no feasible schedule"],
    )


class BusTimetableTests(unittest.TestCase):
    def test_bus_timetable_rows_include_charge_wait_and_final_arrival(self):
        from src.reporting.tables import build_bus_timetable_rows

        result = _make_one_bus_result()
        rows = build_bus_timetable_rows(result)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Bus ID"], "bus-BK-01")
        self.assertEqual(row["Operator"], "kpn")
        self.assertEqual(row["Direction"], "Bengaluru->Kochi")
        self.assertEqual(row["Departure"], "00:00")
        self.assertEqual(row["Station"], "A")
        self.assertEqual(row["Arrival"], "03:00")
        self.assertEqual(row["Wait (min)"], 15)
        self.assertEqual(row["Charge Start"], "03:15")
        self.assertEqual(row["Charge End"], "04:45")
        self.assertEqual(row["Charger Lane"], 0)
        self.assertEqual(row["Final Arrival"], "05:45")

    def test_bus_timetable_rows_sorted_by_departure(self):
        from src.reporting.tables import build_bus_timetable_rows

        result = _make_three_bus_result()
        rows = build_bus_timetable_rows(result)
        self.assertEqual(len(rows), 0)
        # No charge stops -> no rows; test with buses that have charging stops
        # For sort test, create a result with charge stops at different departures
        events_early = [
            TimelineEvent("departure", 0, "Bengaluru", "Departure"),
            TimelineEvent("arrival", 180, "A", "Arrival at A"),
            TimelineEvent("charge_start", 190, "A", "Charge start at A"),
            TimelineEvent("charge_end", 280, "A", "Charge end at A"),
            TimelineEvent("arrival", 340, "Kochi", "Arrival at Kochi"),
        ]
        events_mid = [
            TimelineEvent("departure", 100, "Bengaluru", "Departure"),
            TimelineEvent("arrival", 280, "A", "Arrival at A"),
            TimelineEvent("charge_start", 290, "A", "Charge start at A"),
            TimelineEvent("charge_end", 380, "A", "Charge end at A"),
            TimelineEvent("arrival", 440, "Kochi", "Arrival at Kochi"),
        ]
        events_late = [
            TimelineEvent("departure", 200, "Bengaluru", "Departure"),
            TimelineEvent("arrival", 380, "A", "Arrival at A"),
            TimelineEvent("charge_start", 390, "A", "Charge start at A"),
            TimelineEvent("charge_end", 480, "A", "Charge end at A"),
            TimelineEvent("arrival", 540, "Kochi", "Arrival at Kochi"),
        ]
        plan_early = BusPlan(bus_id="bus-03", operator="kpn", direction="Bengaluru->Kochi", events=events_early, final_arrival_minutes=340)
        plan_mid = BusPlan(bus_id="bus-02", operator="kpn", direction="Bengaluru->Kochi", events=events_mid, final_arrival_minutes=440)
        plan_late = BusPlan(bus_id="bus-01", operator="kpn", direction="Bengaluru->Kochi", events=events_late, final_arrival_minutes=540)
        res_a = StationReservation(station="A", bus_id="bus-01", charger_lane=0, start_minutes=390, end_minutes=480)
        res_b = StationReservation(station="A", bus_id="bus-02", charger_lane=0, start_minutes=290, end_minutes=380)
        res_c = StationReservation(station="A", bus_id="bus-03", charger_lane=0, start_minutes=190, end_minutes=280)
        sort_result = ScheduleResult(
            feasible=True,
            scenario_id="test_sort",
            bus_plans=[plan_late, plan_mid, plan_early],
            station_reservations=[res_a, res_b, res_c],
            metrics=ScheduleMetrics(total_buses=3, total_charge_stops=3, total_wait_minutes=0, max_wait_minutes=0),
        )
        rows = build_bus_timetable_rows(sort_result)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["Bus ID"], "bus-03")
        self.assertEqual(rows[1]["Bus ID"], "bus-02")
        self.assertEqual(rows[2]["Bus ID"], "bus-01")


class StationQueueTests(unittest.TestCase):
    def test_station_queue_rows_sort_by_charge_start_then_lane_then_bus(self):
        from src.reporting.tables import build_station_queue_rows

        result = _make_same_time_diff_lanes_result()
        station_rows = build_station_queue_rows(result)

        self.assertIn("A", station_rows)
        rows = station_rows["A"]
        self.assertEqual(len(rows), 2)
        # Both have same Charge Start "03:05" -> sort by lane (0 < 1) -> then bus_id
        self.assertEqual(rows[0]["Charger Lane"], 0)
        self.assertEqual(rows[0]["Bus ID"], "bus-BK-01")
        self.assertEqual(rows[1]["Charger Lane"], 1)
        self.assertEqual(rows[1]["Bus ID"], "bus-KB-01")

    def test_station_queue_interleaves_both_directions_for_scenario_2(self):
        from src.adapters.scenario_loader import load_scenario
        from src.reporting.tables import build_station_queue_rows
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_2")
        result = CustomHeuristicStrategy().schedule(scenario)
        self.assertTrue(result.feasible, f"Scenario 2 should be feasible, warnings: {result.warnings}")

        station_rows = build_station_queue_rows(result)

        for sid in ("B", "C"):
            self.assertIn(sid, station_rows, f"Station {sid} should have queue rows")
            rows = station_rows[sid]
            self.assertGreater(len(rows), 1, f"Station {sid} should have multiple entries")

            directions = [r["Direction"] for r in rows]
            has_bk = any("Bengaluru" in d for d in directions)
            has_kb = any("Kochi" in d for d in directions)
            self.assertTrue(has_bk, f"Station {sid} should have Bengaluru->Kochi buses")
            self.assertTrue(has_kb, f"Station {sid} should have Kochi->Bengaluru buses")

            charge_starts = [r["Charge Start"] for r in rows]
            self.assertEqual(charge_starts, sorted(charge_starts),
                             f"Station {sid} charge starts should be sorted chronologically")

    def test_station_queue_interleaves_both_directions_for_scenario_5(self):
        from src.adapters.scenario_loader import load_scenario
        from src.reporting.tables import build_station_queue_rows
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_5")
        result = CustomHeuristicStrategy().schedule(scenario)
        self.assertTrue(result.feasible, f"Scenario 5 should be feasible, warnings: {result.warnings}")

        station_rows = build_station_queue_rows(result)

        for sid in ("B", "C"):
            self.assertIn(sid, station_rows, f"Station {sid} should have queue rows")
            rows = station_rows[sid]
            self.assertGreater(len(rows), 1, f"Station {sid} should have multiple entries")

            directions = [r["Direction"] for r in rows]
            has_bk = any("Bengaluru" in d for d in directions)
            has_kb = any("Kochi" in d for d in directions)
            self.assertTrue(has_bk, f"Station {sid} should have Bengaluru->Kochi buses")
            self.assertTrue(has_kb, f"Station {sid} should have Kochi->Bengaluru buses")

            charge_starts = [r["Charge Start"] for r in rows]
            self.assertEqual(charge_starts, sorted(charge_starts),
                             f"Station {sid} charge starts should be sorted chronologically")


class InfeasibleResultTests(unittest.TestCase):
    def test_infeasible_result_handled_gracefully(self):
        from src.reporting.metrics import build_summary_metrics
        from src.reporting.tables import build_bus_timetable_rows, build_station_queue_rows

        result = _make_infeasible_result()

        timetable_rows = build_bus_timetable_rows(result)
        self.assertEqual(timetable_rows, [])

        station_rows = build_station_queue_rows(result)
        self.assertEqual(station_rows, {})

        metrics_rows = build_summary_metrics(result)
        self.assertEqual(metrics_rows, [])


class ScheduleMetricsTests(unittest.TestCase):
    def test_schedule_metrics_are_computed(self):
        from src.reporting.metrics import build_summary_metrics

        result = _make_one_bus_result()
        metrics = build_summary_metrics(result)

        metric_map = {m["Metric"]: m["Value"] for m in metrics}
        self.assertEqual(metric_map["Total Buses"], 1)
        self.assertEqual(metric_map["Total Charge Stops"], 1)
        self.assertEqual(metric_map["Total Wait (min)"], 15)
        self.assertEqual(metric_map["Max Individual Wait (min)"], 15)
        self.assertEqual(metric_map["Station A Total Wait (min)"], 15)


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_streamlit_components_accept_reporting_rows_not_scheduler_internals(self):
        import ast
        ui_dir = Path("src/ui")
        for path in ui_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("src.scheduler") and "contract" not in alias.name:
                            self.fail(f"{path} imports scheduler internals: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("src.scheduler") and "contract" not in node.module:
                        self.fail(f"{path} imports scheduler internals: {node.module}")


if __name__ == "__main__":
    unittest.main()
