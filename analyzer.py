"""Read telemetry logs and report sensor faults."""

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path


def parse_comms(value: str) -> bool:
    """Accept true or false, ignoring capitalization and surrounding spaces."""
    normalized = value.strip().lower()

    if normalized == "true":
        return True
    if normalized == "false":
        return False

    raise ValueError(
        f"Invalid comms_ok value: {value!r}; expected true or false."
    )


def detect_faults(
    temperature: float,
    voltage: float,
    comms_ok: bool,
) -> list[str]:
    """Return all faults detected in one telemetry reading."""
    faults = []

    if temperature > 85.0:
        faults.append("Overtemperature")

    if voltage < 10.5:
        faults.append("Undervoltage")
    elif voltage > 13.5:
        faults.append("Overvoltage")

    if not comms_ok:
        faults.append("Communications failure")

    return faults


def parse_number(value: str, field_name: str) -> float:
    """Convert a sensor value into a finite number."""
    try:
        number = float(value)
    except ValueError:
        raise ValueError(
            f"{field_name} must be numeric; got {value!r}."
        ) from None

    if not math.isfinite(number):
        raise ValueError(
            f"{field_name} must be finite; got {value!r}."
        )

    return number


def validate_headers(headers: list[str] | None) -> None:
    """Check that the log contains all required columns."""
    required = {"timestamp", "temperature_c", "voltage_v", "comms_ok"}

    if not headers:
        raise ValueError("The log is empty or has no header.")

    if len(headers) != len(set(headers)):
        raise ValueError("The log contains duplicate column names.")

    missing = required - set(headers)

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}."
        )


def validate_row(row: dict, line_number: int) -> None:
    """Reject extra values and missing or blank required values."""
    if None in row:
        raise ValueError(f"Line {line_number}: too many values.")

    for field in ("timestamp", "temperature_c", "voltage_v", "comms_ok"):
        value = row.get(field)

        if value is None or not value.strip():
            raise ValueError(
                f"Line {line_number}: missing value for {field}."
            )


def parse_timestamp(value: str) -> datetime:
    """Parse a date and time in ISO 8601 format."""
    normalized = value.strip()

    if "T" not in normalized:
        raise ValueError(
            f"Timestamp must include a date and time separated by T; got {value!r}."
        )

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        raise ValueError(
            f"Invalid timestamp: {value!r}."
        ) from None


def validate_interval(seconds: float) -> None:
    """Require a positive, finite reading interval."""
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Expected interval must be a positive, finite number.")


def has_timestamp_gap(
    previous: datetime,
    current: datetime,
    expected_interval: float = 1.0,
) -> bool:
    """Detect gaps exceeding the expected reading interval."""
    validate_interval(expected_interval)

    previous_has_zone = previous.utcoffset() is not None
    current_has_zone = current.utcoffset() is not None

    if previous_has_zone != current_has_zone:
        raise ValueError(
            "Timestamps must consistently include or omit timezone information."
        )

    elapsed = (current - previous).total_seconds()

    if elapsed <= 0:
        raise ValueError("Timestamps must be strictly increasing.")

    return elapsed > expected_interval


def collect_report(
    file_path: Path,
    expected_interval: float = 1.0,
) -> dict:
    """Validate the complete log and return a report without printing."""
    validate_interval(expected_interval)

    total_readings = 0
    faulty_readings = 0
    previous_timestamp: datetime | None = None
    timing_gaps = 0
    events: list[dict] = []
    readings: list[dict] = []

    with file_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        validate_headers(reader.fieldnames)

        for row in reader:
            validate_row(row, reader.line_num)

            try:
                timestamp = parse_timestamp(row["timestamp"])
                temperature = parse_number(
                    row["temperature_c"], "temperature_c"
                )
                voltage = parse_number(row["voltage_v"], "voltage_v")
                comms_ok = parse_comms(row["comms_ok"])
                gap_detected = (
                    previous_timestamp is not None
                    and has_timestamp_gap(
                        previous_timestamp, timestamp, expected_interval
                    )
                )
            except ValueError as error:
                raise ValueError(
                    f"Line {reader.line_num}: {error}"
                ) from None

            if gap_detected:
                timing_gaps += 1
                events.append({
                    "type": "timing_gap",
                    "line": reader.line_num,
                    "previous_timestamp": previous_timestamp.isoformat(),
                    "timestamp": timestamp.isoformat(),
                    "elapsed_seconds": (
                        timestamp - previous_timestamp
                    ).total_seconds(),
                })

            readings.append({
                "timestamp": timestamp.isoformat(),
                "temperature_c": temperature,
                "voltage_v": voltage,
                "comms_ok": comms_ok,
            })
            previous_timestamp = timestamp
            total_readings += 1

            faults = detect_faults(temperature, voltage, comms_ok)

            if faults:
                faulty_readings += 1
                events.append({
                    "type": "sensor_fault",
                    "line": reader.line_num,
                    "timestamp": row["timestamp"],
                    "faults": faults,
                })

    return {
        "source": str(file_path),
        "expected_interval_seconds": expected_interval,
        "summary": {
            "total_readings": total_readings,
            "faulty_readings": faulty_readings,
            "healthy_readings": total_readings - faulty_readings,
            "timing_gaps": timing_gaps,
        },
        "events": events,
        "readings": readings,
    }


def analyze_log(
    file_path: Path,
    expected_interval: float = 1.0,
) -> None:
    """Print a report only after the complete log validates."""
    print_report(collect_report(file_path, expected_interval))


def print_report(report: dict) -> None:
    """Display a structured report in the terminal."""
    for event in report["events"]:
        if event["type"] == "timing_gap":
            print(
                f"Timing gap: {event['previous_timestamp']}"
                f" -> {event['timestamp']}"
            )
        elif event["type"] == "sensor_fault":
            print(f"{event['timestamp']}: {', '.join(event['faults'])}")

    summary = report["summary"]
    print("\nTelemetry Summary")
    print(f"Total readings: {summary['total_readings']}")
    print(f"Readings with faults: {summary['faulty_readings']}")
    print(f"Readings without faults: {summary['healthy_readings']}")
    print(f"Timing gaps: {summary['timing_gaps']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze sensor telemetry and report faults."
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "sample_telemetry.csv",
        help="Path to a telemetry CSV file; defaults to the sample log.",
    )
    parser.add_argument(
        "--expected-interval",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Expected time between readings in seconds (default: 1.0).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        help="Save a JSON report to a new file.",
    )
    parser.add_argument(
        "--plot",
        type=Path,
        metavar="PNG_FILE",
        help="Save temperature and voltage charts to a new PNG file.",
    )
    args = parser.parse_args()

    try:
        report = collect_report(args.log_file, args.expected_interval)
    except OSError as error:
        parser.exit(status=1, message=f"Cannot read log file: {error}\n")
    except ValueError as error:
        parser.exit(status=1, message=f"Invalid telemetry data: {error}\n")
    if args.output is not None:
        try:
            serialized = json.dumps(report, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as file:
                file.write(serialized + "\n")
        except OSError as error:
            parser.exit(
                status=1,
                message=f"Cannot write report: {error}\n",
            )
    if args.plot is not None:
        from plotting import save_chart

        try:
            save_chart(report, args.plot)
        except (OSError, ValueError) as error:
            parser.exit(
                status=1,
                message=f"Cannot save chart: {error}\n",
            )
    print_report(report)
    if args.output is not None:
        print(f"\nJSON report saved to: {args.output}")
    if args.plot is not None:
        print(f"\nChart saved to: {args.plot}")