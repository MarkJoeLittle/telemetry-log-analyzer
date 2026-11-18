"""Tests for optional telemetry chart generation."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

from plotting import save_chart


@unittest.skipUnless(
    importlib.util.find_spec("matplotlib") is not None,
    "Install requirements-plot.txt to run chart rendering tests.",
)
class TestPlotting(unittest.TestCase):
    def setUp(self):
        self.report = {
            "source": "telemetry.csv",
            "readings": [
                {
                    "timestamp": "2026-10-22T10:00:00",
                    "temperature_c": 25.0,
                    "voltage_v": 12.0,
                    "comms_ok": True,
                },
                {
                    "timestamp": "2026-10-22T10:00:03",
                    "temperature_c": 90.0,
                    "voltage_v": 13.8,
                    "comms_ok": False,
                },
            ],
        }

    def test_saves_png_chart(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report.png"
            save_chart(self.report, destination)

            self.assertEqual(destination.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report.png"
            destination.write_bytes(b"existing image")

            with self.assertRaises(FileExistsError):
                save_chart(self.report, destination)

            self.assertEqual(destination.read_bytes(), b"existing image")


if __name__ == "__main__":
    unittest.main()
