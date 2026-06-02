import importlib.util
import json
import unittest
from pathlib import Path


ORTOOLS_AVAILABLE = importlib.util.find_spec("ortools") is not None
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture_scenario(fixture_name: str):
    from src.adapters.scenario_loader import _parse_scenario

    path = FIXTURE_DIR / f"{fixture_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_scenario(data)


@unittest.skipUnless(ORTOOLS_AVAILABLE, "OR-Tools is not installed")
class CpSatStrategyTests(unittest.TestCase):
    def test_exact_range_fixture_is_feasible(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.cp_sat_strategy import CpSatStrategy

        scenario = _load_fixture_scenario("scenario_exact_range")
        result = CpSatStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible, result.warnings)
        self.assertEqual(violations, [])

    def test_feasible_result_includes_solver_diagnostics_and_hint_usage(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.cp_sat_strategy import (
            CP_SAT_TIME_LIMIT_SECONDS,
            CpSatStrategy,
        )

        scenario = _load_fixture_scenario("scenario_multi_charger")
        result = CpSatStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible, result.warnings)
        self.assertEqual(violations, [])
        self.assertIsNotNone(result.solver_diagnostics)
        diagnostics = result.solver_diagnostics
        self.assertEqual(diagnostics.solver_name, "CP-SAT")
        self.assertIn(diagnostics.status_name, {"OPTIMAL", "FEASIBLE"})
        self.assertIsNotNone(diagnostics.objective_value)
        self.assertIsNotNone(diagnostics.best_objective_bound)
        self.assertIsNotNone(diagnostics.optimality_gap)
        self.assertGreaterEqual(diagnostics.wall_time_seconds, 0.0)
        self.assertGreaterEqual(diagnostics.conflict_count, 0)
        self.assertGreaterEqual(diagnostics.branch_count, 0)
        self.assertEqual(diagnostics.search_workers, 1)
        self.assertEqual(diagnostics.time_limit_seconds, CP_SAT_TIME_LIMIT_SECONDS)
        self.assertTrue(diagnostics.used_heuristic_hint)
        self.assertIsNotNone(diagnostics.heuristic_objective_value)
        self.assertIsNotNone(diagnostics.objective_improvement)

    def test_impossible_range_fixture_is_infeasible(self):
        from src.scheduler.strategies.cp_sat_strategy import CpSatStrategy

        scenario = _load_fixture_scenario("scenario_impossible_range")
        result = CpSatStrategy().schedule(scenario)

        self.assertFalse(result.feasible)
        self.assertTrue(result.warnings)

    def test_multi_charger_fixture_produces_valid_lane_assignments(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.cp_sat_strategy import CpSatStrategy

        scenario = _load_fixture_scenario("scenario_multi_charger")
        result = CpSatStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible, result.warnings)
        self.assertEqual(violations, [])
        self.assertTrue(any(res.charger_lane == 1 for res in result.station_reservations))

    def test_assignment_scenarios_return_complete_schedule_results(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.cp_sat_strategy import CpSatStrategy

        for scenario_id in ("scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5"):
            with self.subTest(scenario=scenario_id):
                scenario = load_scenario(scenario_id)
                result = CpSatStrategy().schedule(scenario)
                violations = validate_schedule_invariants(scenario, result)

                self.assertTrue(result.feasible, result.warnings)
                self.assertEqual(violations, [])
                self.assertIsNotNone(result.metrics)
                self.assertIsNotNone(result.score_breakdown)
                self.assertEqual(len(result.bus_plans), len(scenario.buses))


if __name__ == "__main__":
    unittest.main()
