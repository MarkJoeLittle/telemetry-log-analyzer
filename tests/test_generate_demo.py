"""Tests for reproducible demo telemetry generation."""

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.generate_demo import generate_demo


class TestGenerateDemo(unittest.TestCase):
    def test_generates_reproducible_telemetry_with_faults_and_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.csv"
            second_path = Path(directory) / "second.csv"

            generate_demo(first_path)
            generate_demo(second_path)

            first_contents = first_path.read_bytes()
            self.assertEqual(first_contents, second_path.read_bytes())

            with first_path.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 180)
        self.assertGreater(float(rows[45]["temperature_c"]), 85.0)
        self.assertLess(float(rows[85]["voltage_v"]), 10.5)
        self.assertGreater(float(rows[115]["voltage_v"]), 13.5)
        self.assertEqual(rows[142]["comms_ok"], "false")

        before_gap = datetime.fromisoformat(rows[119]["timestamp"])
        after_gap = datetime.fromisoformat(rows[120]["timestamp"])
        self.assertEqual((after_gap - before_gap).total_seconds(), 5.0)

    def test_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "existing.csv"
            destination.write_text("keep this file", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                generate_demo(destination)

            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "keep this file",
            )


if __name__ == "__main__":
    unittest.main()
