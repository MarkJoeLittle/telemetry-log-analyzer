# Telemetry Log Analyzer

A Python command-line tool that reads sensor telemetry from CSV files,
detects sensor faults and timing gaps, and prints a summary.

Built as an embedded-systems and software-testing portfolio project.

## Features

- Detects temperatures above 85 °C
- Detects voltages below 10.5 V or above 13.5 V
- Flags communications failures
- Detects timestamp gaps exceeding a configurable interval (default: one second).
- Rejects duplicate or decreasing timestamps
- Validates required columns, row completeness, numeric values,
  communications values, and timestamps
- Includes line numbers in row-validation errors
- Uses only the Python standard library

Timing gaps are reported separately from sensor faults.

## Requirements

Python 3.14. Development and local verification used Python 3.14.4
on Ubuntu through Windows Subsystem for Linux (WSL).

No third-party packages are required.

## Input Format

Required column names are case-sensitive. Extra named columns are allowed.

```csv
timestamp,temperature_c,voltage_v,comms_ok
2026-10-22T10:00:00,25.0,12.0,true
2026-10-22T10:00:01,90.0,12.0,true
```

- Timestamps must include a date and time separated by `T`.
- Timestamps must consistently include or omit timezone information.
- Temperature and voltage must be finite numbers.
- Communications values must be `true` or `false`, ignoring
  capitalization and surrounding spaces.
- Use --expected-interval SECONDS to set the expected time between readings.

## Run

From the project folder:

```bash
python analyzer.py
```

Analyze a different log:

```bash
python analyzer.py path/to/log.csv
```

Analyze readings expected every two seconds:

```bash
python3 analyzer.py data/sample_telemetry.csv --expected-interval 2
```

The interval must be a positive, finite number. An interval exactly at
the configured threshold does not count as a gap.

Display help:

```bash
python analyzer.py --help
```

## Sample Summary

```text
Telemetry Summary
Total readings: 6
Readings with faults: 4
Readings without faults: 2
Timing gaps: 0
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover fault thresholds, input validation, timestamp ordering,
timing gaps, and file-reading integration.

GitHub Actions runs the automated tests and sample analysis on every push
and pull request using Python 3.14.

## Limitations

- Analysis stops at the first invalid record.
- Earlier warnings may already be printed when an invalid record is found.
- This is an offline analysis tool, not a real-time monitoring system.

## Planned Improvements

- Exportable analysis reports
- Sensor-data charts