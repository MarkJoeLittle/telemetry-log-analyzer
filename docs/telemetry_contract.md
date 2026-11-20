# Telemetry CSV Contract

Contract version: 1

The C++ RTOS System Health Monitor writes UTF-8 CSV telemetry for
analysis by `telemetry-log-analyzer`.

## Producer requirements

The header and data fields must use these exact names and order:

```csv
timestamp,temperature_c,voltage_v,comms_ok
```

The C++ producer writes only these columns and in this order.

## Fields

- `timestamp`: ISO 8601 UTC timestamp ending in `Z`, such as
  `2026-11-19T06:30:00.000000Z`.
- `temperature_c`: finite decimal Celsius value.
- `voltage_v`: finite decimal volt value.
- `comms_ok`: lowercase `true` or `false`.

Rows must be strictly timestamp-increasing and contain no missing values.
Sensor thresholds are part of the contract:

| Sensor | Fault condition |
|---|---|
| Temperature | greater than 85 degrees Celsius |
| Voltage | less than 10.5 volts |
| Voltage | greater than 13.5 volts |
| Communications | `comms_ok` is `false` |

The Python analyzer's `--expected-interval` is an analysis tolerance, not a
field in the CSV. The health-monitor default logging period is one second.
Host scheduling can add gaps; it does not imply a real-time guarantee.

## Analyzer input compatibility

The general-purpose analyzer remains permissive by default for backward
compatibility. It accepts reordered columns and additional named columns,
timestamps with UTC offsets or without timezone information, and
case-insensitive `true`/`false` values.

Pass `--strict-contract` to require producer conformance to contract version
1: the exact header and order above, UTC timestamps with six fractional
digits ending in `Z`, and lowercase `true` or `false`. Only strict-mode
reports identify `contract_version` as `1`; permissive reports set it to null.
