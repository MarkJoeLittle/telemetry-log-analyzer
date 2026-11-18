"""Generate reproducible sample telemetry."""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_demo(destination: Path) -> None:
    """Write 180 reproducible readings to a new CSV file."""
    generator = random.Random(2026)
    start = datetime(2026, 10, 22, 10, 0, 0)

    with destination.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "temperature_c",
                "voltage_v",
                "comms_ok",
            ],
        )
        writer.writeheader()

        for index in range(180):
            temperature = round(generator.uniform(25.0, 30.0), 2)
            voltage = round(generator.uniform(11.8, 12.2), 2)
            comms_ok = True

            # Each fault ends automatically, demonstrating recovery.
            if 40 <= index < 50:
                temperature = round(generator.uniform(88.0, 94.0), 2)
            if 80 <= index < 90:
                voltage = round(generator.uniform(9.5, 10.2), 2)
            if 110 <= index < 120:
                voltage = round(generator.uniform(13.8, 14.5), 2)
            if 140 <= index < 145:
                comms_ok = False

            # Skip four expected releases: one five-second interval.
            elapsed_seconds = index + (4 if index >= 120 else 0)
            timestamp = start + timedelta(seconds=elapsed_seconds)
            writer.writerow({
                "timestamp": timestamp.isoformat(),
                "temperature_c": temperature,
                "voltage_v": voltage,
                "comms_ok": str(comms_ok).lower(),
            })


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reproducible sample telemetry."
    )
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "data"
            / "demo_telemetry.csv"
        ),
        help="New CSV destination; its parent folder must exist.",
    )
    args = parser.parse_args()

    try:
        generate_demo(args.destination)
    except OSError as error:
        parser.exit(status=1, message=f"Cannot write demo log: {error}\n")
    print(f"Created 180 telemetry readings: {args.destination}")


if __name__ == "__main__":
    main()
