import unittest

from src.domain.models import Route, Segment


class CandidateGenerationTests(unittest.TestCase):
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

    def test_candidate_generation_bk_basic(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)

        self.assertTrue(len(candidates) > 0)
        for candidate in candidates:
            self.assertTrue(len(candidate) >= 1)
        for candidate in candidates:
            for station in candidate:
                self.assertIn(station, ("A", "B", "C", "D"))

    def test_candidate_generation_kb_basic(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Kochi->Bengaluru", self.range_km)

        self.assertTrue(len(candidates) > 0)
        for candidate in candidates:
            self.assertTrue(len(candidate) >= 1)

    def test_bk_candidates_respect_route_order(self):
        from src.scheduler.candidates import generate_candidates
        from src.domain.route import get_ordered_stops

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)
        ordered = get_ordered_stops(self.route, "Bengaluru->Kochi")
        intermediates = ordered[1:-1]

        for candidate in candidates:
            filtered = [s for s in intermediates if s in candidate]
            self.assertEqual(list(candidate), filtered)

    def test_kb_candidates_respect_route_order(self):
        from src.scheduler.candidates import generate_candidates
        from src.domain.route import get_ordered_stops

        candidates = generate_candidates(self.route, "Kochi->Bengaluru", self.range_km)
        ordered = get_ordered_stops(self.route, "Kochi->Bengaluru")
        intermediates = ordered[1:-1]

        for candidate in candidates:
            filtered = [s for s in intermediates if s in candidate]
            self.assertEqual(list(candidate), filtered)

    def test_bk_d_station_alone_is_infeasible(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)
        self.assertNotIn(("D",), candidates)

    def test_bk_bd_is_feasible(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)
        self.assertIn(("B", "D"), candidates)

    def test_range_constraint_allows_exact_boundary(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", 220)
        self.assertIn(("B", "D"), candidates)

    def test_range_constraint_rejects_over_range_gap(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", 200)
        self.assertNotIn(("B",), candidates)

    def test_no_candidates_for_very_short_range(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", 50)
        self.assertEqual(candidates, [])

    def test_candidate_count_is_bounded(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)
        self.assertLessEqual(len(candidates), 16)

    def test_all_candidates_unique(self):
        from src.scheduler.candidates import generate_candidates

        candidates = generate_candidates(self.route, "Bengaluru->Kochi", self.range_km)
        self.assertEqual(len(candidates), len(set(candidates)))


if __name__ == "__main__":
    unittest.main()
