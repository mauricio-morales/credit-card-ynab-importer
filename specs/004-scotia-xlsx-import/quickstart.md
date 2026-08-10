# Quickstart: Scotia/DaviBank XLSX Import

**Feature**: 004-scotia-xlsx-import | **Date**: 2026-08-09

## Prerequisites

```bash
pip install -r requirements.txt   # now installs openpyxl instead of xlrd/xlwt
```

## 1. Regenerate fixtures (once, after implementation)

```bash
# Place a real (never-committed) Scotia/DaviBank .xlsx statement at:
#   data/DaviBank Visa-in.xlsx
python scripts/generate_fixtures.py            # writes obfuscated tests/fixtures/DaviBank Sample-in.xlsx
python scripts/generate_expected_outputs.py    # regenerates out1/out2/out3 fixtures from it
```

## 2. Run the regression suite

```bash
pytest tests/test_davi_pipeline.py -v
```

Expected: all DaviBank stage tests pass against the `.xlsx` fixture; new tests cover `.xls` rejection, missing-column rejection, empty-transaction success, footer-row skipping, native-date-cell parsing, and multi-sheet handling.

## 3. Manually import a real statement (CLI)

```bash
python scripts/orchestrator.py "/path/to/Scotia Visa.xlsx"
```

Expected output (same directory as the input file):
```
Scotia Visa-out1.csv
Scotia Visa-out2-crc.csv
Scotia Visa-out2-usd.csv
Scotia Visa-out3-crc.csv     <- import this into YNAB (CRC budget)
Scotia Visa-out3-usd.csv     <- import this into YNAB (USD budget)
```

## 4. Verify legacy `.xls` rejection

```bash
python scripts/orchestrator.py "/path/to/old-statement.xls"
```

Expected: a plain-language stderr message stating `.xls` is no longer supported and that an `.xlsx` export is needed — non-zero exit, **no** `-out1.csv`/etc. files written.

## 5. Manually verify via the TUI

```bash
python -m tui.app   # or however the app is currently launched — see tui/app.py
```

- Choose the Davi/Scotia conversion flow, select a real `.xlsx` statement, confirm the progress/summary screens complete successfully and the five output files listed in step 3 exist.
- Repeat selecting a `.xls` file and confirm a plain-language error is shown instead of a crash.
