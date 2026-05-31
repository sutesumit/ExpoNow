import unittest


class SchedulerInvariantTests(unittest.TestCase):
    def test_invariants_hold_for_all_assignment_scenarios(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scheduler = CustomHeuristicStrategy()
        for scenario_id in [
            "scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5",
        ]:
            scenario = load_scenario(scenario_id)
            result = scheduler.schedule(scenario)
            violations = validate_schedule_invariants(scenario, result)
            self.assertEqual(
                violations, [],
                f"{scenario_id} has invariant violations: {violations}",
            )

    def test_invariants_detect_infeasible_input(self):
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.contract import ScheduleResult

        result = ScheduleResult(feasible=False, scenario_id="test")
        violations = validate_schedule_invariants(None, result)  # type: ignore
        self.assertTrue(len(violations) > 0)


if __name__ == "__main__":
    unittest.main()
