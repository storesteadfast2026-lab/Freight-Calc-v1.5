# ADR 0001 - Excel is the functional source of truth

## Status

Accepted.

## Context

The Django freight calculator is a migration of an existing Excel workbook. The Excel workbook contains business logic distributed across `Calculator`, `CalcLines`, `BrokerTotals`, `FuelSurcharge`, `ZONES`, `RATES`, `SKUs`, and `SettingFlags`.

## Decision

Excel remains the functional source of truth until enough independent production evidence proves the Django implementation.

Django must be validated against Excel using independent input cases and visible Excel outputs.

## Consequences

- Expected outputs must come from Excel, not Django.
- `Calculator` visible cells are the expected source for user-facing outputs.
- `CalcLines` can be used for internal diagnosis, but not as a replacement for visible expected outputs.
- Every calculation fix must be backed by an Excel-vs-Django battery run.
