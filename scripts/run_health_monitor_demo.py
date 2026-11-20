"""Build-independent runner for a health-monitor telemetry/analyzer demo."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_monitor(project_root: Path, configured: str | None) -> Path:
    """Find a native build, or use an explicitly selected executable."""
    if configured:
        executable = Path(configured).resolve()
        if executable.is_file():
            return executable
        raise RuntimeError(f"Configured monitor does not exist: {executable}")

    if sys.platform == "win32":
        candidates = (
            project_root / "build" / "Debug" / "rtos_health_monitor.exe",
            project_root / "build" / "Release" / "rtos_health_monitor.exe",
            project_root / "build" / "rtos_health_monitor.exe",
            project_root / "build-wsl" / "rtos_health_monitor.exe",
        )
    else:
        # WSL reports itself as Linux. Do not automatically launch a Windows
        # build: it may be blocked or interpret generated paths differently.
        candidates = (
            project_root / "build-wsl" / "rtos_health_monitor",
            project_root / "build" / "rtos_health_monitor",
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "Could not find a native rtos_health_monitor build; "
        "build it for this platform or pass --monitor."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the sibling health monitor and analyze its CSV."
    )
    parser.add_argument(
        "--monitor",
        help="Path to rtos_health_monitor.",
    )
    parser.add_argument(
        "--monitor-root",
        type=Path,
        help="Health-monitor checkout (default: sibling directory).",
    )
    parser.add_argument(
        "--expected-interval",
        type=float,
        default=1.05,
        help="Analyzer timing threshold (default: 1.05 seconds).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=20,
        help="Capture duration in seconds (default: 20).",
    )
    parser.add_argument(
        "--telemetry-interval-ms",
        type=int,
        default=1000,
        help="Telemetry snapshot interval in milliseconds (default: 1000).",
    )
    args = parser.parse_args()

    monitor_root = (
        args.monitor_root.resolve()
        if args.monitor_root
        else PROJECT_ROOT.parent / "rtos-system-health-monitor"
    )

    try:
        monitor = find_monitor(monitor_root, args.monitor)
    except RuntimeError as error:
        parser.exit(status=1, message=f"Error: {error}\n")

    run_directory = monitor_root / "logs"
    run_directory.mkdir(parents=True, exist_ok=True)
    run_name = datetime.now(timezone.utc).strftime(
        "session-%Y%m%dT%H%M%S.%fZ"
    )
    telemetry_path = run_directory / f"{run_name}.csv"
    report_path = run_directory / f"{run_name}-report.json"
    manifest_path = run_directory / f"{run_name}-manifest.json"

    monitor_revision = git_revision(monitor_root)
    analyzer_revision = git_revision(PROJECT_ROOT)
    started_at = datetime.now(timezone.utc)
    monitor_result = subprocess.run(
        [
            str(monitor),
            "--telemetry",
            str(telemetry_path),
            "--duration",
            str(args.duration),
            "--telemetry-interval-ms",
            str(args.telemetry_interval_ms),
        ],
        cwd=monitor_root,
        check=False,
    )
    if monitor_result.returncode != 0:
        return monitor_result.returncode

    capture_completed_at = datetime.now(timezone.utc)
    analyzer = PROJECT_ROOT / "analyzer.py"
    analyzer_result = subprocess.run(
        [
            sys.executable,
            str(analyzer),
            str(telemetry_path),
            "--expected-interval",
            str(args.expected_interval),
            "--strict-contract",
            "--output",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    completed_at = datetime.now(timezone.utc)
    if analyzer_result.returncode == 0:
        manifest = {
            "contract_version": 1,
            "started_at_utc": started_at.isoformat(),
            "capture_completed_at_utc": capture_completed_at.isoformat(),
            "completed_at_utc": completed_at.isoformat(),
            "capture_duration_seconds": args.duration,
            "telemetry_interval_milliseconds": (
                args.telemetry_interval_ms
            ),
            "expected_interval_seconds": args.expected_interval,
            "monitor_executable": str(monitor),
            "monitor_revision": monitor_revision,
            "analyzer_revision": analyzer_revision,
            "telemetry_csv": str(telemetry_path),
            "analysis_report": str(report_path),
            "host_platform": sys.platform,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return analyzer_result.returncode


def git_revision(repository: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
