"""Read telemetry logs and report sensor faults."""

import argparse
import csv
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

def analyze_log(file_path: Path) -> None:
    total_readings = 0
    faulty_readings = 0

    with file_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            total_readings += 1
            temperature = float(row["temperature_c"])
            voltage = float(row["voltage_v"])
            comms_ok = parse_comms(row["comms_ok"])

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