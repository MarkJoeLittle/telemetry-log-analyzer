"""Read telemetry logs and report sensor faults."""

import argparse
import csv
import math
from pathlib import Path
from datetime import datetime


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


def analyze_log(file_path: Path, expected_interval: float = 1.0) -> None:
    validate_interval(expected_interval)

    total_readings = 0
    faulty_readings = 0
    previous_timestamp = None
    timing_gaps = 0

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
                print(
                    f"Timing gap: {previous_timestamp.isoformat()}"
                    f" -> {timestamp.isoformat()}"
                )

            previous_timestamp = timestamp
            total_readings += 1

            faults = detect_faults(temperature, voltage, comms_ok)

            if faults:
                faulty_readings += 1
                print(f"{row['timestamp']}: {', '.join(faults)}")

    print("\nTelemetry Summary")
    print(f"Total readings: {total_readings}")
    print(f"Readings with faults: {faulty_readings}")
    print(f"Readings without faults: {total_readings - faulty_readings}")
    print(f"Timing gaps: {timing_gaps}")


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
    args = parser.parse_args()

    try:
        analyze_log(args.log_file, args.expected_interval)
    except OSError as error:
        parser.exit(status=1, message=f"Cannot read log file: {error}\n")
    except ValueError as error:
        parser.exit(status=1, message=f"Invalid telemetry data: {error}\n")