import unittest

from src.domain.models import (
    Bus, ChargingPolicy, Route, Scenario, Segment, Station, TravelPolicy, Weights,
)


class SchedulerIntegrationTests(unittest.TestCase):
    def test_scheduler_produces_feasible_result_for_scenario_1(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
        from src.scheduler.constraints import validate_schedule_invariants

        scenario = load_scenario("scenario_1")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)
        self.assertEqual(len(result.bus_plans), 20)

    def test_scheduler_produces_feasible_result_for_scenario_2(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
        from src.scheduler.constraints import validate_schedule_invariants

        scenario = load_scenario("scenario_2")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)

    def test_scheduler_produces_feasible_result_for_scenario_5(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
        from src.scheduler.constraints import validate_schedule_invariants

        scenario = load_scenario("scenario_5")
        result = CustomHeuristicStrategy().schedule(scenario)
        violations = validate_schedule_invariants(scenario, result)

        self.assertTrue(result.feasible)
        self.assertEqual(len(violations), 0)

    def test_scheduler_returns_infeasible_for_impossible_scenario(self):
        route = Route(
            name="Short",
            stops=["X", "Y"],
            segments=[Segment(from_stop="X", to_stop="Y", distance_km=500)],
        )
        scenario = Scenario(
            schema_version=1,
            id="test_infeasible",
            name="Infeasible",
            description="Range too short",
            route=route,
            stations=[],
            buses=[
                Bus(id="bus-01", operator="kpn", direction="X->Y",
                    departure_minutes=0),
            ],
            charging_policy=ChargingPolicy(range_km=1, full_charge_minutes=25),
            travel_policy=TravelPolicy(speed_kmph=60),
            weights=Weights(),
        )
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertFalse(result.feasible)
        self.assertTrue(len(result.warnings) > 0)

    def test_scheduler_metrics_are_populated(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_1")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertIsNotNone(result.metrics)
        self.assertEqual(result.metrics.total_buses, 20)
        self.assertTrue(result.metrics.total_charge_stops > 0)

    def test_scheduler_score_breakdown_is_present(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_1")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertIsNotNone(result.score_breakdown)
        self.assertIn("individual_wait", result.score_breakdown.components)
        self.assertIn("operator_smoothness", result.score_breakdown.components)
        self.assertIn("overall_network", result.score_breakdown.components)
        self.assertGreater(result.score_breakdown.total_weighted, 0)

    def test_weights_change_weighted_total_without_changing_hard_validity(self):
        import dataclasses
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.constraints import validate_schedule_invariants
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy
        from src.domain.models import Weights

        scenario = load_scenario("scenario_1")
        default_weights = scenario.weights
        altered_weights = Weights(
            individual=5.0,
            operator=default_weights.operator,
            overall=default_weights.overall,
        )
        altered_scenario = dataclasses.replace(scenario, weights=altered_weights)

        default_result = CustomHeuristicStrategy().schedule(scenario)
        altered_result = CustomHeuristicStrategy().schedule(altered_scenario)

        default_violations = validate_schedule_invariants(scenario, default_result)
        altered_violations = validate_schedule_invariants(altered_scenario, altered_result)

        self.assertTrue(default_result.feasible)
        self.assertTrue(altered_result.feasible)
        self.assertEqual(len(default_violations), 0)
        self.assertEqual(len(altered_violations), 0)

        self.assertNotEqual(
            default_result.score_breakdown.total_weighted,
            altered_result.score_breakdown.total_weighted,
        )

    def test_scenario_4_operator_weight_changes_component_contribution(self):
        from src.adapters.scenario_loader import load_scenario
        from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

        scenario = load_scenario("scenario_4")
        result = CustomHeuristicStrategy().schedule(scenario)

        self.assertIsNotNone(result.score_breakdown)
        op_comp = result.score_breakdown.components["operator_smoothness"]
        self.assertEqual(op_comp["weight"], 2.0)
        self.assertEqual(
            op_comp["weighted"],
            op_comp["unweighted"] * 2.0,
        )


if __name__ == "__main__":
    unittest.main()
