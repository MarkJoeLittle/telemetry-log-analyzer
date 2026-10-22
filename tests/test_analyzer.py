"""Tests for telemetry fault detection."""

import unittest

from analyzer import detect_faults, parse_comms



class TestDetectFaults(unittest.TestCase):
    def test_normal_reading(self):
        self.assertEqual(detect_faults(25.0, 12.0, True), [])

    def test_temperature_at_limit(self):
        self.assertEqual(detect_faults(85.0, 12.0, True), [])

    def test_overtemperature(self):
        self.assertEqual(
            detect_faults(85.1, 12.0, True),
            ["Overtemperature"],
        )

    def test_voltage_at_lower_limit(self):
        self.assertEqual(detect_faults(25.0, 10.5, True), [])

    def test_undervoltage(self):
        self.assertEqual(
            detect_faults(25.0, 10.4, True),
            ["Undervoltage"],
        )

    def test_voltage_at_upper_limit(self):
        self.assertEqual(detect_faults(25.0, 13.5, True), [])

    def test_overvoltage(self):
        self.assertEqual(
            detect_faults(25.0, 13.6, True),
            ["Overvoltage"],
        )

    def test_communications_failure(self):
        self.assertEqual(
            detect_faults(25.0, 12.0, False),
            ["Communications failure"],
        )

    def test_multiple_faults(self):
        self.assertEqual(
            detect_faults(90.0, 10.0, False),
            [
                "Overtemperature",
                "Undervoltage",
                "Communications failure",
            ],
        )

class TestParseComms(unittest.TestCase):
    def test_true(self):
        self.assertIs(parse_comms("true"), True)

    def test_false(self):
        self.assertIs(parse_comms("false"), False)

    def test_capitalization_and_spaces(self):
        self.assertIs(parse_comms(" TRUE "), True)
        self.assertIs(parse_comms(" False "), False)

    def test_invalid_values(self):
        for value in ("", "yes", "1", "tru"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_comms(value)

if __name__ == "__main__":
    unittest.main()