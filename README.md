# Credit Card → YNAB Importer

Converts credit card statement exports from **BAC** (CSV) and **DaviBank** (XLS) into YNAB-compatible CSV files, split by currency (CRC and USD).

---

## Setup

**Requirements:** Python 3.8+

Install dependencies:

```bash
pip3 install -r requirements.txt
```

---

## How to Run

Run the orchestrator with one or more input files:

```bash
python3 scripts/orchestrator.py <file1> [file2 ...]
```

The script auto-detects the bank from the file extension:
- `.csv` → BAC pipeline
- `.xls` → DaviBank pipeline

Output files are written to the **same directory as the input file**.

---

## Examples

### BAC — process a single month

```bash
python3 scripts/orchestrator.py "data/BAC MCB Marzo-in.csv"
```

Output files created in `data/`:
```
BAC MCB Marzo-out1.csv        ← cleaned intermediate
BAC MCB Marzo-out2-crc.csv    ← CRC transactions only
BAC MCB Marzo-out2-usd.csv    ← USD transactions only
BAC MCB Marzo-out3-crc.csv    ← YNAB-ready (CRC) ✓ import this
BAC MCB Marzo-out3-usd.csv    ← YNAB-ready (USD) ✓ import this
```

### DaviBank — process a statement

```bash
python3 scripts/orchestrator.py "data/DaviBank Visa.xls"
```

### Process multiple files at once

```bash
python3 scripts/orchestrator.py "data/BAC MCB Febrero-in.csv" "data/BAC MCB Marzo-in.csv"
```

---

## Input File Naming

The orchestrator strips a trailing `-in` suffix from the input filename when naming outputs. Both of these work:

| Input filename          | Base used for outputs |
|-------------------------|-----------------------|
| `BAC MCB Marzo-in.csv`  | `BAC MCB Marzo`       |
| `BAC MCB Marzo.csv`     | `BAC MCB Marzo`       |

---

## Importing into YNAB

After running the script, import the `*-out3-crc.csv` and `*-out3-usd.csv` files into YNAB:

1. Open YNAB and go to the account you want to update.
2. Click **Import** (or the upload icon).
3. Select the `-out3-crc.csv` file for the CRC account.
4. Repeat with `-out3-usd.csv` for the USD account.

The output format matches YNAB's expected columns: `Date`, `Payee`, `Memo`, `Amount`.

---

## Running Tests

```bash
python3 -m pytest tests/
```

---

## Pipeline Overview

Each bank export goes through 3 stages:

| Stage | Input | Output | What happens |
|-------|-------|--------|--------------|
| 1 | Raw bank export | `*-out1.csv` | Strip headers/footers, normalize numbers |
| 2 | `*-out1.csv` | `*-out2-crc.csv`, `*-out2-usd.csv` | Split by currency |
| 3 | `*-out2-*.csv` | `*-out3-*.csv` | Convert to YNAB format |
