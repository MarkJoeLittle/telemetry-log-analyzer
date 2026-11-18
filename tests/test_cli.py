"""Tests for the command-line interface."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = PROJECT_ROOT / "analyzer.py"


class TestCommandLine(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(ANALYZER), *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--expected-interval", result.stdout)
        self.assertIn("--output", result.stdout)

    def test_default_interval(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Total readings: 6", result.stdout)
        self.assertIn("Timing gaps: 0", result.stdout)

    def test_half_second_interval(self):
        result = self.run_cli("--expected-interval", "0.5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("Timing gap:"), 5)
        self.assertIn("Timing gaps: 5", result.stdout)

    def test_two_second_interval(self):
        result = self.run_cli("--expected-interval", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Timing gap:", result.stdout)
        self.assertIn("Timing gaps: 0", result.stdout)

    def test_json_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.json"
            result = self.run_cli(
                "--expected-interval", "2",
                "--output", str(output_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(report["expected_interval_seconds"], 2.0)
        self.assertEqual(report["summary"], {
            "total_readings": 6,
            "faulty_readings": 4,
            "healthy_readings": 2,
            "timing_gaps": 0,
        })
        self.assertEqual(len(report["events"]), 4)
        self.assertTrue(
            all(event["type"] == "sensor_fault" for event in report["events"])
        )
        self.assertIn("JSON report saved to:", result.stdout)

    def test_existing_report_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.json"
            original = '{"keep": "this report"}\n'
            output_path.write_text(original, encoding="utf-8")

            result = self.run_cli("--output", str(output_path))

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(result.stdout, "")
            self.assertIn("Cannot write report:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_invalid_log_does_not_create_report(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "invalid.csv"
            output_path = Path(directory) / "report.json"
            log_path.write_text(
                "timestamp,temperature_c,voltage_v,comms_ok\n"
                "2026-10-22T10:00:00,90.0,12.0,true\n"
                "2026-10-22T10:00:01,unknown,12.0,true\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                str(log_path), "--output", str(output_path)
            )

            self.assertEqual(result.returncode, 1)
            self.assertFalse(output_path.exists())
            self.assertEqual(result.stdout, "")
            self.assertIn("Line 3:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_invalid_intervals(self):
        for value in ("0", "-1", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                result = self.run_cli(f"--expected-interval={value}")
                self.assertEqual(result.returncode, 1)
                self.assertIn("positive, finite number", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_nonnumeric_interval(self):
        result = self.run_cli("--expected-interval", "abc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--expected-interval", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_file = Path(directory) / "missing.csv"
            result = self.run_cli(str(missing_file))

        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot read log file:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
