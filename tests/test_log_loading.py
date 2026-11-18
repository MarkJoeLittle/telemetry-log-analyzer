"""Integration tests for reading and validating telemetry files."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from analyzer import analyze_log


class TestLogLoading(unittest.TestCase):
    def analyze_text(self, contents: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                analyze_log(log_path)

            return output.getvalue()

    def test_valid_log_summary(self):
        output = self.analyze_text(
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00,25.0,12.0,true\n"
            "2026-10-22T10:00:01,90.0,12.0,true\n"
        )
        self.assertIn("Overtemperature", output)
        self.assertIn("Total readings: 2", output)
        self.assertIn("Readings with faults: 1", output)
        self.assertIn("Readings without faults: 1", output)

    def test_timing_gap_warning_and_summary(self):
        output = self.analyze_text(
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00,25.0,12.0,true\n"
            "2026-10-22T10:00:01,26.0,12.0,true\n"
            "2026-10-22T10:00:04,27.0,12.0,true\n"
            "2026-10-22T10:00:05,28.0,12.0,true\n"
        )

        self.assertIn(
            "Timing gap: 2026-10-22T10:00:01"
            " -> 2026-10-22T10:00:04",
            output,
        )
        self.assertEqual(output.count("Timing gap:"), 1)
        self.assertIn("Timing gaps: 1", output)
        self.assertIn("Total readings: 4", output)
        self.assertIn("Readings with faults: 0", output)
        self.assertIn("Readings without faults: 4", output)

    def test_invalid_later_row_does_not_print_partial_results(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00,90.0,12.0,true\n"
            "2026-10-22T10:00:01,invalid,12.0,true\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                with self.assertRaisesRegex(
                    ValueError, "Line 3: temperature_c must be numeric"
                ):
                    analyze_log(log_path)

        self.assertEqual(output.getvalue(), "")

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            self.analyze_text(
                "timestamp,temperature_c,voltage_v\n"
                "2026-10-22T10:00:00,25.0,12.0\n"
            )

    def test_incomplete_row(self):
        with self.assertRaisesRegex(
            ValueError, "Line 2: missing value for comms_ok"
        ):
            self.analyze_text(
                "timestamp,temperature_c,voltage_v,comms_ok\n"
                "2026-10-22T10:00:00,25.0,12.0\n"
            )

    def test_invalid_number_includes_line(self):
        with self.assertRaisesRegex(
            ValueError, "Line 2: temperature_c must be numeric"
        ):
            self.analyze_text(
                "timestamp,temperature_c,voltage_v,comms_ok\n"
                "2026-10-22T10:00:00,unknown,12.0,true\n"
            )

    def test_invalid_comms_includes_line(self):
        with self.assertRaisesRegex(
            ValueError, "Line 2: Invalid comms_ok value"
        ):
            self.analyze_text(
                "timestamp,temperature_c,voltage_v,comms_ok\n"
                "2026-10-22T10:00:00,25.0,12.0,yes\n"
            )


if __name__ == "__main__":
    unittest.main()