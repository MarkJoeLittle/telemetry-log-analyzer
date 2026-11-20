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

            with patch.object(runner.sys, "platform", "linux"):
                self.assertEqual(
                    runner.find_monitor(project_root, None), executable
                )

    def test_wsl_prefers_native_build_when_windows_builds_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "build-wsl" / "rtos_health_monitor"
            for executable in (
                native,
                root / "build" / "rtos_health_monitor",
                root / "build" / "Debug" / "rtos_health_monitor.exe",
                root / "build" / "rtos_health_monitor.exe",
            ):
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.touch()

            with patch.object(runner.sys, "platform", "linux"):
                self.assertEqual(runner.find_monitor(root, None), native)

    def test_linux_does_not_fall_back_to_windows_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "build" / "Debug" / "rtos_health_monitor.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()

            with patch.object(runner.sys, "platform", "linux"):
                with self.assertRaisesRegex(RuntimeError, "native.*build"):
                    runner.find_monitor(root, None)

    def test_windows_finds_native_build_layouts(self):
        for build_directory in ("build/Debug", "build/Release", "build", "build-wsl"):
            with self.subTest(build_directory=build_directory):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    native = root / build_directory / "rtos_health_monitor.exe"
                    native.parent.mkdir(parents=True)
                    native.touch()
                    linux_build = root / "build-wsl" / "rtos_health_monitor"
                    linux_build.parent.mkdir(parents=True, exist_ok=True)
                    linux_build.touch()

                    with patch.object(runner.sys, "platform", "win32"):
                        self.assertEqual(runner.find_monitor(root, None), native)

    def test_windows_does_not_select_linux_only_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "build-wsl" / "rtos_health_monitor"
            executable.parent.mkdir()
            executable.touch()

            with patch.object(runner.sys, "platform", "win32"):
                with self.assertRaisesRegex(RuntimeError, "native.*build"):
                    runner.find_monitor(root, None)

    def test_explicit_monitor_overrides_platform_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "build-wsl" / "rtos_health_monitor"
            native.parent.mkdir()
            native.touch()
            explicit = root / "selected.exe"
            explicit.touch()

            with patch.object(runner.sys, "platform", "linux"):
                self.assertEqual(
                    runner.find_monitor(root, str(explicit)), explicit
                )

    def test_missing_explicit_monitor_does_not_select_another_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "build-wsl" / "rtos_health_monitor"
            native.parent.mkdir()
            native.touch()

            with self.assertRaisesRegex(RuntimeError, "Configured monitor"):
                runner.find_monitor(root, str(root / "missing"))

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
                        "--monitor",
                        str(executable),
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
