"""Cross-repository integration test for the C++ telemetry producer."""

import csv
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from analyzer import collect_report
from scripts.run_health_monitor_demo import find_monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONITOR_ROOT = PROJECT_ROOT.parent / "rtos-system-health-monitor"


class TestHealthMonitorIntegration(unittest.TestCase):
    def setUp(self):
        configured = os.environ.get("RTOS_HEALTH_MONITOR_EXECUTABLE")
        try:
            self.monitor = find_monitor(MONITOR_ROOT, configured)
        except RuntimeError:
            if configured:
                raise
            self.skipTest(
                "Build rtos_health_monitor or set "
                "RTOS_HEALTH_MONITOR_EXECUTABLE."
            )

    def test_generated_csv_is_valid_for_analyzer(self):
        self.assertTrue(self.monitor.is_absolute())
        with tempfile.TemporaryDirectory() as directory:
            telemetry = Path(directory) / "session.csv"
            result = subprocess.run(
                [
                    str(self.monitor),
                    "--telemetry",
                    str(telemetry),
                    "--duration",
                    "3",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with telemetry.open(
                newline="", encoding="utf-8"
            ) as telemetry_file:
                reader = csv.DictReader(telemetry_file)
                self.assertEqual(
                    reader.fieldnames,
                    [
                        "timestamp",
                        "temperature_c",
                        "voltage_v",
                        "comms_ok",
                    ],
                )

            report = collect_report(
                telemetry,
                expected_interval=1.05,
                strict_contract=True,
            )

        self.assertEqual(report["contract_version"], 1)
        self.assertGreater(report["summary"]["total_readings"], 0)
        self.assertIn("timing", report)


if __name__ == "__main__":
    unittest.main()
