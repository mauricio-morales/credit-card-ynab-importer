# Quickstart: QIF Export Alongside YNAB CSV Output

## Run the pipeline (unchanged command)

```bash
python scripts/orchestrator.py "BAC MCB Marzo-in.csv"
# or
python scripts/orchestrator.py "DaviBank Statement-in.xlsx"
```

No new flag is needed — QIF output is automatic.

## What's new on disk

Alongside the existing files:

```
BAC MCB Marzo-out3-crc.csv
BAC MCB Marzo-out3-usd.csv
```

you'll now also get:

```
BAC MCB Marzo-out3-crc.qif
BAC MCB Marzo-out3-usd.qif
```

(same for the DaviBank/Scotia pipeline).

## Verify a QIF file by hand

```bash
cat "BAC MCB Marzo-out3-crc.qif"
```

Expect:

```
!Type:Bank
D03/05/2026
PSOME MERCHANT
T-4500
^
...
```

## Run the regression tests

```bash
pytest tests/test_qif_export.py -v
pytest tests/test_bac_pipeline.py tests/test_davi_pipeline.py -v
```

- `test_qif_export.py` covers the `qif_export.convert_csv_to_qif()` contract
  directly: header line, per-record field order, memo omission when empty,
  newline neutralization, and header-only output for an empty CSV.
- The existing pipeline test files gain assertions that running the
  orchestrator produces a sibling `.qif` file for every `.csv` file it
  produces, with matching transaction count/date/payee/memo/amount, and that
  the `.csv` output itself is byte-for-byte unchanged from before this
  feature (User Story 2 / SC-003).
