import json
import unittest
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture_scenario(fixture_name: str):
    from src.adapters.scenario_loader import _parse_scenario

    path = FIXTURE_DIR / f"{fixture_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_scenario(data)


class EdgeFixtureExactRangeTests(unittest.TestCase):
    def test_exactly_at_range_edge_fixture_is_feasible(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_exact_range")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(
            result.feasible,
            f"Exact range should be feasible, warnings: {result.warnings}",
        )
        self.assertEqual(len(violations), 0)


class EdgeFixtureImpossibleRangeTests(unittest.TestCase):
    def test_impossible_range_fixture_is_infeasible_with_reason(self):
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_impossible_range")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertFalse(result.feasible)
        self.assertTrue(len(result.warnings) > 0)

    def test_impossible_range_inline_remains_infeasible(self):
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_impossible_range")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertIn("Could not schedule", result.warnings[0])


class EdgeFixtureSimultaneousArrivalsTests(unittest.TestCase):
    def test_simultaneous_station_arrivals_are_deterministically_ordered(self):
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_simultaneous_arrivals")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertTrue(result.feasible)

        plans_by_id = {p.bus_id: p for p in result.bus_plans}
        self.assertIn("bus-BK-01", plans_by_id)
        self.assertIn("bus-BK-02", plans_by_id)

        charge_starts_01 = [
            e.minutes
            for e in plans_by_id["bus-BK-01"].events
            if e.event_type == "charge_start" and e.location == "A"
        ]
        charge_starts_02 = [
            e.minutes
            for e in plans_by_id["bus-BK-02"].events
            if e.event_type == "charge_start" and e.location == "A"
        ]

        self.assertTrue(len(charge_starts_01) > 0)
        self.assertTrue(len(charge_starts_02) > 0)
        self.assertLess(
            charge_starts_01[0],
            charge_starts_02[0],
            "bus-BK-01 should charge before bus-BK-02 at station A",
        )


class EdgeFixtureMultiOperatorTests(unittest.TestCase):
    def test_multiple_operator_fixture_scores_without_special_cases(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = _load_fixture_scenario("scenario_multi_operator")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)
        self.assertIsNotNone(result.score_breakdown)
        self.assertIn("operator_smoothness", result.score_breakdown.components)

        operators = {p.operator for p in result.bus_plans}
        self.assertIn("kpn", operators)
        self.assertIn("freshbus", operators)
        self.assertIn("flixbus", operators)


class StaticGuardTests(unittest.TestCase):
    def test_requirements_do_not_include_deferred_solver_dependencies(self):
        req_path = Path("requirements.txt")
        self.assertTrue(req_path.exists())
        content = req_path.read_text(encoding="utf-8")

        solver_packages = ["ortools", "z3", "z3-solver", "pulp", "cvxopt", "scipy"]
        for pkg in solver_packages:
            self.assertNotIn(
                pkg.lower(),
                content.lower(),
                f"requirements.txt should not contain {pkg}",
            )
        self.assertIn("streamlit", content.lower())

    def test_docs_no_longer_contain_stale_open_questions(self):
        docs_dir = Path("docs")
        for path in sorted(docs_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn(
                "tbd", content,
                f"{path.name} contains 'TBD'",
            )
            self.assertNotIn(
                "docs/solver_evaluation.md", content,
                f"{path.name} references non-existent docs/SOLVER_EVALUATION.md",
            )


if __name__ == "__main__":
    unittest.main()
