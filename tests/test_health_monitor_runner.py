"""Tests for health-monitor executable discovery."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import run_health_monitor_demo as runner


class TestHealthMonitorRunner(unittest.TestCase):
    def test_discovers_linux_build_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            executable = project_root / "build" / "rtos_health_monitor"
            executable.parent.mkdir()
            executable.touch()

            self.assertEqual(runner.find_monitor(project_root, None), executable)

    def test_configured_relative_executable_is_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            executable = project_root / "rtos_health_monitor"
            executable.touch()

            original_directory = Path.cwd()
            os.chdir(project_root)
            try:
                selected = runner.find_monitor(
                    project_root, "rtos_health_monitor"
                )
            finally:
                os.chdir(original_directory)

            self.assertTrue(selected.is_absolute())
            self.assertEqual(selected, executable.resolve())

    def test_manifest_records_capture_and_completion_times(self):
        with tempfile.TemporaryDirectory() as directory:
            monitor_root = Path(directory)
            executable = monitor_root / "build" / "rtos_health_monitor"
            executable.parent.mkdir()
            executable.touch()

            with (
                patch(
                    "sys.argv",
                    [
                        "run_health_monitor_demo.py",
                        "--monitor-root",
                        str(monitor_root),
                        "--duration",
                        "3",
                        "--telemetry-interval-ms",
                        "250",
                    ],
                ),
                patch.object(
                    runner,
                    "git_revision",
                    side_effect=["monitor-revision", "analyzer-revision"],
                ),
                patch.object(
                    runner.subprocess,
                    "run",
                    return_value=SimpleNamespace(returncode=0),
                ) as run_process,
            ):
                self.assertEqual(runner.main(), 0)

            manifest_path = next(
                (monitor_root / "logs").glob("*-manifest.json")
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )

        self.assertLessEqual(
            manifest["started_at_utc"],
            manifest["capture_completed_at_utc"],
        )
        self.assertLessEqual(
            manifest["capture_completed_at_utc"],
            manifest["completed_at_utc"],
        )
        self.assertEqual(manifest["capture_duration_seconds"], 3)
        self.assertEqual(manifest["telemetry_interval_milliseconds"], 250)
        self.assertEqual(manifest["monitor_revision"], "monitor-revision")
        self.assertEqual(manifest["analyzer_revision"], "analyzer-revision")
        self.assertEqual(run_process.call_count, 2)


if __name__ == "__main__":
    unittest.main()
