import unittest


class SolverDiagnosticsResultTests(unittest.TestCase):
    def test_finalize_schedule_result_preserves_solver_diagnostics(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.contract import SolverDiagnostics
        from src.scheduler.results import finalize_schedule_result

        scenario = load_scenario("scenario_1")
        diagnostics = SolverDiagnostics(
            solver_name="CP-SAT",
            status_name="FEASIBLE",
            objective_value=1200.0,
            best_objective_bound=1000.0,
            optimality_gap=200.0,
            wall_time_seconds=1.25,
            conflict_count=3,
            branch_count=7,
            search_workers=1,
            time_limit_seconds=60.0,
            used_heuristic_hint=True,
            heuristic_objective_value=1400.0,
            objective_improvement=200.0,
        )

        result = finalize_schedule_result(
            scenario,
            bus_plans=[],
            station_reservations=[],
            feasible=False,
            solver_diagnostics=diagnostics,
        )

        self.assertEqual(result.solver_diagnostics, diagnostics)

    def test_solver_diagnostic_rows_format_optional_values(self):
        from src.reporting.metrics import build_solver_diagnostic_rows
        from src.scheduler.contract import ScheduleResult, SolverDiagnostics

        result = ScheduleResult(
            feasible=False,
            scenario_id="test",
            solver_diagnostics=SolverDiagnostics(
                solver_name="CP-SAT",
                status_name="UNKNOWN",
                objective_value=None,
                best_objective_bound=42.0,
                optimality_gap=None,
                wall_time_seconds=0.125,
                conflict_count=0,
                branch_count=0,
                search_workers=1,
                time_limit_seconds=60.0,
                used_heuristic_hint=False,
                heuristic_objective_value=None,
                objective_improvement=None,
            ),
        )

        rows = build_solver_diagnostic_rows(result)
        by_metric = {row["Metric"]: row for row in rows}

        self.assertEqual(by_metric["CP-SAT Status"]["Value"], "UNKNOWN")
        self.assertEqual(by_metric["CP-SAT Status"]["Status"], "info")
        self.assertNotEqual(by_metric["CP-SAT Status"]["Note"], "")

        self.assertEqual(by_metric["Objective Value"]["Value"], "")
        self.assertEqual(by_metric["Objective Value"]["Status"], "info")

        self.assertEqual(by_metric["Best Objective Bound"]["Value"], "42")
        self.assertEqual(by_metric["Best Objective Bound"]["Status"], "info")

        self.assertEqual(by_metric["Wall Time (sec)"]["Value"], "0.125")

        self.assertEqual(by_metric["Used Heuristic Hint"]["Value"], "No")
        self.assertEqual(by_metric["Used Heuristic Hint"]["Status"], "warning")
        self.assertNotEqual(by_metric["Used Heuristic Hint"]["Note"], "")

        self.assertEqual(by_metric["Objective Improvement"]["Status"], "info")
        self.assertEqual(by_metric["Optimality Gap"]["Status"], "info")


if __name__ == "__main__":
    unittest.main()
