"""Tests for telemetry fault detection."""

import unittest

from analyzer import detect_faults, parse_comms, parse_number, validate_headers

from analyzer import validate_row


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

class TestParseNumber(unittest.TestCase):
    def test_valid_number(self):
        self.assertEqual(parse_number("12.5", "voltage_v"), 12.5)

    def test_spaces_and_negative_number(self):
        self.assertEqual(parse_number(" -5.0 ", "temperature_c"), -5.0)

    def test_invalid_text(self):
        for value in ("", " ", "unknown", "12 volts"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_number(value, "voltage_v")

    def test_nonfinite_numbers(self):
        for value in ("nan", "inf", "-inf", "1e999"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_number(value, "temperature_c")

class TestValidateHeaders(unittest.TestCase):
    def test_required_columns(self):
        validate_headers(
            ["timestamp", "temperature_c", "voltage_v", "comms_ok"]
        )

    def test_extra_column_allowed(self):
        validate_headers(
            ["timestamp", "temperature_c", "voltage_v", "comms_ok", "device_id"]
        )

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns: comms_ok"):
            validate_headers(["timestamp", "temperature_c", "voltage_v"])

    def test_empty_or_duplicate_headers(self):
        for headers in (
            None,
            [],
            ["timestamp", "temperature_c", "voltage_v", "comms_ok", "comms_ok"],
        ):
            with self.subTest(headers=headers):
                with self.assertRaises(ValueError):
                    validate_headers(headers)

class TestValidateRow(unittest.TestCase):
    def setUp(self):
        self.row = {
            "timestamp": "2026-10-22T10:00:00",
            "temperature_c": "25.0",
            "voltage_v": "12.0",
            "comms_ok": "true",
        }

    def test_valid_row(self):
        validate_row(self.row, 2)

    def test_missing_or_blank_values(self):
        for field in self.row:
            for value in (None, "", " "):
                with self.subTest(field=field, value=value):
                    row = self.row.copy()
                    row[field] = value
                    with self.assertRaisesRegex(
                        ValueError, f"Line 3: missing value for {field}"
                    ):
                        validate_row(row, 3)

    def test_absent_field(self):
        del self.row["voltage_v"]
        with self.assertRaisesRegex(ValueError, "missing value for voltage_v"):
            validate_row(self.row, 4)

    def test_extra_values(self):
        self.row[None] = ["unexpected"]
        with self.assertRaisesRegex(ValueError, "Line 5: too many values"):
            validate_row(self.row, 5)

if __name__ == "__main__":
    unittest.main()