from pathlib import Path
import unittest


class IncrementZeroHarnessTests(unittest.TestCase):
    def test_scenario_catalog_lists_five_assignment_scenarios(self):
        from src.adapters.scenario_catalog import list_scenario_summaries

        summaries = list_scenario_summaries()

        self.assertEqual(len(summaries), 5)
        self.assertEqual(
            [summary.id for summary in summaries],
            ["scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5"],
        )
        self.assertEqual(
            [summary.name for summary in summaries],
            [
                "Scenario 1 - Even spacing",
                "Scenario 2 - Bunched start",
                "Scenario 3 - Asymmetric load",
                "Scenario 4 - Operator-heavy",
                "Scenario 5 - Worst case convergence",
            ],
        )
        self.assertFalse(any(summary.is_placeholder for summary in summaries))

    def test_stub_scheduler_returns_schedule_result_contract(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.contract import ScheduleMetrics, ScoreBreakdown
        from src.scheduler.stub import StubSchedulerStrategy

        scenario = load_scenario("scenario_1")
        result = StubSchedulerStrategy().schedule(scenario)

        self.assertTrue(result.feasible)
        self.assertEqual(result.scenario_id, "scenario_1")
        self.assertEqual(result.bus_plans, [])
        self.assertEqual(result.station_reservations, [])
        self.assertIsInstance(result.metrics, ScheduleMetrics)
        self.assertEqual(result.metrics.total_buses, 20)
        self.assertIsInstance(result.score_breakdown, ScoreBreakdown)
        self.assertIn("weights", result.score_breakdown.components)

    def test_real_scheduler_returns_populated_schedule_result(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.contract import ScheduleMetrics, ScoreBreakdown
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_1")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertTrue(result.feasible)
        self.assertEqual(result.scenario_id, "scenario_1")
        self.assertTrue(len(result.bus_plans) > 0)
        self.assertTrue(len(result.station_reservations) > 0)
        self.assertIsInstance(result.metrics, ScheduleMetrics)
        self.assertEqual(result.metrics.total_buses, 20)
        self.assertIsInstance(result.score_breakdown, ScoreBreakdown)
        self.assertIn("individual_wait", result.score_breakdown.components)
        self.assertIn("operator_smoothness", result.score_breakdown.components)
        self.assertIn("overall_network", result.score_breakdown.components)
        self.assertFalse(
            any(
                "Scheduling is not implemented yet" in warning
                for warning in result.warnings
            )
        )

    def test_app_orchestration_returns_selected_summary_and_result(self):
        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model("scenario_1")

        self.assertEqual(view_model.selected_scenario.id, "scenario_1")
        self.assertEqual(len(view_model.scenarios), 5)
        self.assertEqual(view_model.schedule_result.scenario_id, "scenario_1")
        self.assertTrue(view_model.schedule_result.feasible)

    def test_app_orchestration_defaults_to_first_scenario(self):
        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model(None)

        self.assertEqual(view_model.selected_scenario.id, "scenario_1")
        self.assertEqual(view_model.schedule_result.scenario_id, "scenario_1")

    def test_scheduler_package_does_not_import_streamlit(self):
        scheduler_dir = Path("src/scheduler")
        python_files = list(scheduler_dir.rglob("*.py"))

        self.assertTrue(python_files, "Expected scheduler package files to exist")
        for path in python_files:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import streamlit", source)
            self.assertNotIn("from streamlit", source)

    def test_app_orchestration_imports_without_streamlit_side_effects(self):
        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model("scenario_2")

        self.assertEqual(view_model.selected_scenario.id, "scenario_2")
        self.assertEqual(view_model.schedule_result.scenario_id, "scenario_2")


if __name__ == "__main__":
    unittest.main()
