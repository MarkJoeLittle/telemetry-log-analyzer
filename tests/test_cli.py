"""Tests for the command-line interface."""

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
