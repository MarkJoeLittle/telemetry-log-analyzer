"""Tests for structured analysis reports."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from analyzer import collect_report


class TestReport(unittest.TestCase):
    def test_report_data_and_no_printing(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00,25.0,12.0,true\n"
            "2026-10-22T10:00:03,90.0,12.0,true\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                report = collect_report(log_path)

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(report["expected_interval_seconds"], 1.0)
        self.assertEqual(report["summary"], {
            "total_readings": 2,
            "faulty_readings": 1,
            "healthy_readings": 1,
            "timing_gaps": 1,
        })
        self.assertEqual(report["readings"], [
            {
                "timestamp": "2026-10-22T10:00:00",
                "temperature_c": 25.0,
                "voltage_v": 12.0,
                "comms_ok": True,
            },
            {
                "timestamp": "2026-10-22T10:00:03",
                "temperature_c": 90.0,
                "voltage_v": 12.0,
                "comms_ok": True,
            },
        ])
        self.assertEqual(len(report["events"]), 2)

        gap, fault = report["events"]
        self.assertEqual(gap["type"], "timing_gap")
        self.assertEqual(gap["line"], 3)
        self.assertEqual(gap["elapsed_seconds"], 3.0)
        self.assertEqual(fault["type"], "sensor_fault")
        self.assertEqual(fault["faults"], ["Overtemperature"])


if __name__ == "__main__":
    unittest.main()
