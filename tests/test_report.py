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
        self.assertIsNone(report["contract_version"])
        self.assertEqual(report["expected_interval_seconds"], 1.0)
        self.assertEqual(report["sensor_thresholds"], {
            "temperature_c_over": 85.0,
            "voltage_v_below": 10.5,
            "voltage_v_above": 13.5,
        })
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
        self.assertEqual(report["timing"]["minimum_interval_seconds"], 3.0)
        self.assertEqual(report["timing"]["maximum_interval_seconds"], 3.0)

    def test_strict_contract_marks_only_valid_producer_output(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00.000000Z,25.0,12.0,true\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")
            report = collect_report(log_path, strict_contract=True)

        self.assertEqual(report["contract_version"], 1)
        self.assertEqual(report["summary"]["total_readings"], 1)

    def test_strict_contract_rejects_non_utc_timestamp(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00+01:00,25.0,12.0,true\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "six fractional digits"):
                collect_report(log_path, strict_contract=True)

    def test_strict_contract_rejects_timestamp_without_fractional_digits(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00Z,25.0,12.0,true\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "six fractional digits"):
                collect_report(log_path, strict_contract=True)

    def test_strict_contract_rejects_uppercase_comms_value(self):
        contents = (
            "timestamp,temperature_c,voltage_v,comms_ok\n"
            "2026-10-22T10:00:00.000000Z,25.0,12.0,TRUE\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.csv"
            log_path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "lowercase true or false"):
                collect_report(log_path, strict_contract=True)


if __name__ == "__main__":
    unittest.main()
