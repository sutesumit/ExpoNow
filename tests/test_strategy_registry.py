import importlib.util
import unittest


class StrategyRegistryTests(unittest.TestCase):
    def test_default_strategy_is_custom_heuristic(self):
        from src.scheduler.strategies.registry import DEFAULT_STRATEGY_ID

        self.assertEqual(DEFAULT_STRATEGY_ID, "custom_heuristic")

    def test_custom_heuristic_is_available(self):
        from src.scheduler.strategies.registry import list_strategy_options

        options = list_strategy_options()
        ids = [option.id for option in options]

        self.assertIn("custom_heuristic", ids)
        self.assertTrue(
            next(option for option in options if option.id == "custom_heuristic").is_available
        )

    def test_cp_sat_visibility_tracks_optional_dependency(self):
        from src.scheduler.strategies.registry import list_strategy_options

        ids = [option.id for option in list_strategy_options()]
        has_ortools = importlib.util.find_spec("ortools") is not None

        if has_ortools:
            self.assertIn("cp_sat", ids)
        else:
            self.assertNotIn("cp_sat", ids)

    def test_can_list_unavailable_strategies_for_diagnostics(self):
        from src.scheduler.strategies.registry import list_strategy_options

        options = list_strategy_options(include_unavailable=True)
        ids = [option.id for option in options]

        self.assertIn("custom_heuristic", ids)
        self.assertIn("cp_sat", ids)

    def test_unknown_strategy_id_raises_clear_error(self):
        from src.scheduler.strategies.registry import get_strategy

        with self.assertRaisesRegex(ValueError, "Unknown scheduler strategy"):
            get_strategy("missing")


class StrategyViewModelTests(unittest.TestCase):
    def test_view_model_preserves_default_strategy_selection(self):
        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model("scenario_1")

        self.assertEqual(view_model.selected_strategy.id, "custom_heuristic")
        self.assertTrue(view_model.schedule_result.feasible)

    def test_view_model_accepts_explicit_custom_strategy_selection(self):
        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model("scenario_1", "custom_heuristic")

        self.assertEqual(view_model.selected_strategy.id, "custom_heuristic")
        self.assertTrue(view_model.schedule_result.feasible)

    def test_unavailable_cp_sat_strategy_returns_warning_when_called_directly(self):
        if importlib.util.find_spec("ortools") is not None:
            self.skipTest("OR-Tools is installed in this environment")

        from src.app_view_model import build_initial_view_model

        view_model = build_initial_view_model("scenario_1", "cp_sat")

        self.assertEqual(view_model.selected_strategy.id, "cp_sat")
        self.assertFalse(view_model.schedule_result.feasible)
        self.assertTrue(
            any("OR-Tools CP-SAT is not available" in warning
                for warning in view_model.schedule_result.warnings)
        )


class AvailableStrategyContractTests(unittest.TestCase):
    def test_available_strategies_produce_valid_results_for_core_scenarios(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.registry import get_strategy, list_strategy_options

        for option in list_strategy_options():
            strategy = get_strategy(option.id)
            for scenario_id in ("scenario_1", "scenario_2", "scenario_5"):
                with self.subTest(strategy=option.id, scenario=scenario_id):
                    scenario = load_scenario(scenario_id)
                    result = strategy.schedule(scenario)
                    violations = validate_schedule_invariants(scenario, result)

                    self.assertTrue(result.feasible, result.warnings)
                    self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
