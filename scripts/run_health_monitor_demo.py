"""Build-independent runner for a health-monitor telemetry/analyzer demo."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_monitor(project_root: Path, configured: str | None) -> Path:
    candidates = []
    if configured:
        candidates.append(Path(configured).resolve())

    candidates.extend(
        (
            project_root / "build" / "Debug" / "rtos_health_monitor.exe",
            project_root / "build" / "rtos_health_monitor.exe",
            project_root / "build-wsl" / "rtos_health_monitor",
            project_root / "build-wsl" / "rtos_health_monitor.exe",
        )
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise RuntimeError(
        "Could not find rtos_health_monitor; build it or pass --monitor."
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
    run_name = datetime.now(timezone.utc).strftime("session-%Y%m%dT%H%M%SZ")
    telemetry_path = run_directory / f"{run_name}.csv"
    report_path = run_directory / f"{run_name}-report.json"
    manifest_path = run_directory / f"{run_name}-manifest.json"

    monitor_result = subprocess.run(
        [str(monitor), "--telemetry", str(telemetry_path)],
        cwd=monitor_root,
        check=False,
    )
    if monitor_result.returncode != 0:
        return monitor_result.returncode

    analyzer = PROJECT_ROOT / "analyzer.py"
    analyzer_result = subprocess.run(
        [
            sys.executable,
            str(analyzer),
            str(telemetry_path),
            "--expected-interval",
            str(args.expected_interval),
            "--output",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if analyzer_result.returncode == 0:
        manifest = {
            "contract_version": 1,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "expected_interval_seconds": args.expected_interval,
            "monitor_executable": str(monitor),
            "telemetry_csv": str(telemetry_path),
            "analysis_report": str(report_path),
            "host_platform": sys.platform,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return analyzer_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
