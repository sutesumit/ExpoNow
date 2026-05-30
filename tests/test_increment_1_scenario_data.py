from __future__ import annotations

import json
from pathlib import Path
import unittest


SCENARIO_DIR = Path("data/scenarios")
EXPECTED_FILES = [SCENARIO_DIR / f"scenario_{index}.json" for index in range(1, 6)]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _minutes_since_midnight(hhmm: str) -> int:
    hour, minute = map(int, hhmm.split(":"))
    return hour * 60 + minute


class IncrementOneScenarioDataTests(unittest.TestCase):
    def test_all_five_scenario_files_exist(self):
        for path in EXPECTED_FILES:
            self.assertTrue(path.exists(), f"Missing expected scenario file: {path}")

    def test_scenario_files_have_required_top_level_keys(self):
        required_keys = {
            "schema_version",
            "id",
            "name",
            "description",
            "route",
            "stations",
            "buses",
            "charging_policy",
            "travel_policy",
            "weights",
        }

        for path in EXPECTED_FILES:
            data = _load(path)
            self.assertTrue(required_keys.issubset(data.keys()), path)

    def test_assignment_scenario_fact_counts(self):
        expected_counts = {
            "scenario_1": 20,
            "scenario_2": 20,
            "scenario_3": 14,
            "scenario_4": 20,
            "scenario_5": 20,
        }

        for path in EXPECTED_FILES:
            data = _load(path)
            self.assertEqual(len(data["buses"]), expected_counts[data["id"]], path)

    def test_scenario_4_operator_weight_is_two(self):
        data = _load(SCENARIO_DIR / "scenario_4.json")

        self.assertEqual(data["weights"]["individual"], 1.0)
        self.assertEqual(data["weights"]["operator"], 2.0)
        self.assertEqual(data["weights"]["overall"], 1.0)

    def test_scenario_5_departures_fit_72_minute_window(self):
        data = _load(SCENARIO_DIR / "scenario_5.json")
        departures = [_minutes_since_midnight(bus["departure"]) for bus in data["buses"]]

        self.assertEqual(min(departures), _minutes_since_midnight("19:00"))
        self.assertEqual(max(departures), _minutes_since_midnight("20:12"))
        self.assertEqual(max(departures) - min(departures), 72)

    def test_station_and_policy_defaults_match_assignment(self):
        for path in EXPECTED_FILES:
            data = _load(path)

            self.assertEqual([station["id"] for station in data["stations"]], ["A", "B", "C", "D"])
            self.assertTrue(all(station["charger_count"] == 1 for station in data["stations"]))
            self.assertEqual(data["charging_policy"]["range_km"], 240)
            self.assertEqual(data["charging_policy"]["full_charge_minutes"], 25)
            self.assertEqual(data["travel_policy"]["speed_kmph"], 60)

            segment_distances = [segment["distance_km"] for segment in data["route"]["segments"]]
            self.assertEqual(segment_distances, [100, 120, 100, 120, 100])

    def test_bus_rows_have_assignment_fields(self):
        for path in EXPECTED_FILES:
            data = _load(path)
            for bus in data["buses"]:
                self.assertIn("id", bus)
                self.assertIn("operator", bus)
                self.assertIn("direction", bus)
                self.assertIn("departure", bus)


if __name__ == "__main__":
    unittest.main()
