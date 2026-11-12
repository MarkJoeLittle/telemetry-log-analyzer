"""Read telemetry logs and report sensor faults."""

import argparse
import csv
import math
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

def analyze_log(file_path: Path) -> None:
    total_readings = 0
    faulty_readings = 0

    with file_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        validate_headers(reader.fieldnames)

        for row in reader:
            validate_row(row, reader.line_num)

            try:
                temperature = parse_number(
                    row["temperature_c"], "temperature_c"
                )
                voltage = parse_number(row["voltage_v"], "voltage_v")
                comms_ok = parse_comms(row["comms_ok"])
            except ValueError as error:
                raise ValueError(
                    f"Line {reader.line_num}: {error}"
                ) from None

            total_readings += 1

            faults = detect_faults(temperature, voltage, comms_ok)

            if faults:
                faulty_readings += 1
                print(f"{row['timestamp']}: {', '.join(faults)}")

    print("\nTelemetry Summary")
    print(f"Total readings: {total_readings}")
    print(f"Readings with faults: {faulty_readings}")
    print(f"Readings without faults: {total_readings - faulty_readings}")


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
    args = parser.parse_args()

    try:
        analyze_log(args.log_file)
    except OSError as error:
        parser.exit(status=1, message=f"Cannot read log file: {error}\n")
    except ValueError as error:
        parser.exit(status=1, message=f"Invalid telemetry data: {error}\n")