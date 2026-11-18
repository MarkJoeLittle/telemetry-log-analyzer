"""Generate telemetry charts without opening a graphical window."""

from datetime import datetime
from io import BytesIO
from pathlib import Path


def save_chart(report: dict, destination: Path) -> None:
    """Render a telemetry report to a new PNG file."""
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    except ImportError:
        raise ValueError(
            "Charting requires Matplotlib. Install it with: "
            "python3 -m pip install -r requirements-plot.txt"
        ) from None

    readings = report["readings"]
    timestamps = [
        datetime.fromisoformat(reading["timestamp"])
        for reading in readings
    ]
    elapsed = [
        (timestamp - timestamps[0]).total_seconds()
        for timestamp in timestamps
    ] if timestamps else []
    temperatures = [reading["temperature_c"] for reading in readings]
    voltages = [reading["voltage_v"] for reading in readings]

    figure = Figure(figsize=(10, 7), layout="constrained")
    FigureCanvasAgg(figure)
    temperature_axis, voltage_axis = figure.subplots(2, 1, sharex=True)
    temperature_axis.scatter(
        elapsed, temperatures, color="#2563eb", label="Readings"
    )
    temperature_axis.axhline(
        85.0, color="#dc2626", linestyle="--", label="Upper limit: 85 °C"
    )
    temperature_axis.set_ylabel("Temperature (°C)")
    temperature_axis.set_title("Temperature")
    voltage_axis.scatter(
        elapsed, voltages, color="#0f766e", label="Readings"
    )
    voltage_axis.axhline(
        10.5, color="#dc2626", linestyle="--", label="Lower limit: 10.5 V"
    )
    voltage_axis.axhline(
        13.5, color="#d97706", linestyle="--", label="Upper limit: 13.5 V"
    )
    voltage_axis.set_ylabel("Voltage (V)")
    voltage_axis.set_xlabel("Elapsed time from first reading (seconds)")
    voltage_axis.set_title("Voltage")
    for axis in (temperature_axis, voltage_axis):
        axis.grid(True, alpha=0.25)
        axis.set_axisbelow(True)
        axis.legend(loc="best")
    figure.suptitle(
        f"Telemetry Analysis — {Path(report['source']).name}"
    )

    with BytesIO() as buffer:
        figure.savefig(buffer, format="png", dpi=150)
        image_bytes = buffer.getvalue()

    with destination.open("xb") as file:
        file.write(image_bytes)
