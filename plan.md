# Plan: Credit Card → YNAB Import Pipeline

## TL;DR
Build a Python pipeline that converts credit card exports from two banks (BAC as CSV, DaviBank as XLS) through 3 stages into YNAB-compatible CSV files, split by currency (CRC/USD). An orchestrator script drives bank-specific stage scripts, and a test framework validates against provided sample files.

---

## Architecture

```
credit-card-ynab-importer/
├── data/                          # Input/output files (gitignored)
├── scripts/
│   ├── orchestrator.py            # Main CLI entry point
│   ├── bac_stage1.py              # BAC: raw CSV → cleaned CSV
│   ├── bac_stage2.py              # BAC: cleaned → split CRC/USD
│   ├── bac_stage3.py              # BAC: split → YNAB format
│   ├── davi_stage1.py             # DaviBank: XLS → CSV
│   ├── davi_stage2.py             # DaviBank: CSV → split CRC/USD
│   └── davi_stage3.py             # DaviBank: split → YNAB format
├── tests/
│   ├── test_bac_pipeline.py       # BAC regression tests
│   ├── test_davi_pipeline.py      # DaviBank regression tests
│   └── conftest.py                # Shared fixtures (paths, comparison helpers)
├── requirements.txt               # xlrd, pytest
└── .gitignore                     # data/ already excluded
```

---

## Phase 1: BAC Pipeline

### Task 1.1 — BAC Stage 1 (raw CSV → cleaned CSV)

**Input**: Bank-exported CSV (e.g., `BAC MCB Febrero-in.csv`)
**Output**: `{basename}-out1.csv`

**Transformations (in order):**

1. **Strip header** — Remove lines 1–2:
   - Line 1: starts with `Pro000000000000duct` (product/column header, 9 fields)
   - Line 2: card number + cardholder name row (9 fields)

2. **Keep data header** — Line 3 is preserved as output header: `Date, , Local, Dollars`

3. **Remove "Previous balance" row** — Line 4: description field contains `Previous balance`

4. **Keep all transaction rows AND card separator rows** — Card separators are rows where the description matches a masked card number pattern like `5466-37**-****-XXXX`. These have empty date field and `0, 0` for amounts. Keep them as-is (they get removed in Stage 2).

5. **Strip footer** — Remove everything starting from the first line whose description contains `REVERSION INTERES CORRIENTES PERIODO`. This is the invariant footer marker present in every BAC export. The footer includes:
   - 2× REVERSION INTERES lines (CRC and USD)
   - TASA MENSUAL INTERES CORRIENTE
   - MONEDA LOCAL / MONEDA DOLARES rate lines
   - PUNTOS CASH BACK PREMIUM
   - ASIGNADOS ... REDIMIBLE ... 
   - CURRENT Interest MONTH header
   - Final balance values row

6. **Number formatting** — Strip trailing `.00` from whole numbers; preserve meaningful decimals (e.g., `4200.00` → `4200`, `11518.99` → `11518.99`, `3980.50` → `3980.5`). Remove leading/trailing whitespace from numeric fields.

7. **Description field** — Preserve exactly as-is (including internal backslashes, spaces). Keep leading space present in the original.

8. **Date formatting** — Keep in DD/MM/YYYY format as received from the bank. Do NOT replicate the Excel date-shortening artifact (D/M/YY) seen in manual samples — this was a side effect of spreadsheet auto-formatting, not an intentional step. Our scripts normalize consistently.

**Files to reference**: `data/BAC MCB Febrero-in.csv` → `data/BAC MCB Febrero-out1.csv`

---

### Task 1.2 — BAC Stage 2 (cleaned → split by currency)

**Input**: `{basename}-out1.csv`
**Output**: `{basename}-out2-crc.csv`, `{basename}-out2-usd.csv`

**Transformations:**

1. **Rename header column** — `Date, , Local, Dollars` → `Date,Description, Local, Dollars`
   (The empty second column name becomes `Description`)

2. **Remove card separator rows** — Any row where:
   - Date field is empty/blank, AND
   - Description matches masked card number pattern (`5466-37**-****-XXXX` or similar `NNNN-NN**-****-NNNN`)

3. **Split by currency**:
   - **CRC file**: Keep rows where `Local != 0` (includes negatives like payments)
   - **USD file**: Keep rows where `Dollars != 0` (and `Local == 0`, which is always the case in practice)
   - Rows where both are 0: these are card separators (already removed in step 2)

4. **Preserve row ordering** — Maintain the original order from out1 (do not sort)

**Files to reference**: `data/BAC MCB Febrero-out1.csv` → `data/BAC MCB Febrero-out2-crc.csv`, `data/BAC MCB Febrero-out2-usd.csv`

---

### Task 1.3 — BAC Stage 3 (split → YNAB format)

**Input**: `{basename}-out2-crc.csv`, `{basename}-out2-usd.csv`
**Output**: `{basename}-out3-crc.csv`, `{basename}-out3-usd.csv`

**Transformations:**

1. **Column mapping**:
   | Source Column | → | YNAB Column |
   |---|---|---|
   | Date | → | Date |
   | Description | → | Payee |
   | *(new)* | → | Memo (always empty `""`) |
   | Local (CRC file) or Dollars (USD file) | → | Amount |

2. **Date format** — Convert to `YYYY/MM/DD` (e.g., `05/01/2026` → `2026/01/05`)
   - Parse DD/MM/YYYY (from stage 1/2 normalized output)
   - Write as YYYY/MM/DD with zero-padding

3. **CSV quoting** — All fields wrapped in double quotes: `"Date","Payee","Memo","Amount"`

4. **Amount** — For CRC file: use the `Local` column value. For USD file: use the `Dollars` column value. Preserve sign (negatives for payments/refunds).

5. **Drop unused columns** — CRC file drops `Dollars`; USD file drops `Local`.

**Files to reference**: `data/BAC MCB Febrero-out2-crc.csv` → `data/BAC MCB Febrero-out3-crc.csv`

---

## Phase 2: DaviBank Pipeline

### Task 2.1 — DaviBank Stage 1 (XLS → CSV)

**Input**: Bank-exported XLS (e.g., `DaviBank Visa-in.xls`)
**Output**: `{basename}-out1.csv`

**Transformations:**

1. **Read XLS** — Use `xlrd` library to read old-format `.xls` file
2. **Write CSV** — Output with columns: `Número de Referencia,Fecha de Movimiento,Descripción,Monto,Moneda,Tipo`
3. **Preserve all rows** — Including card separator rows (`Tarjeta Número:,...`)
4. **Number formatting** — Same rule: strip `.00` trailing zeros, preserve meaningful decimals
5. **Date handling** — Dates may come from Excel as date objects; normalize to DD/MM/YYYY

**Key structural note**: DaviBank files have multiple card sections separated by `Tarjeta Número:,{cardnumber},,,,` rows. These interleave; the same card appears multiple times.

**Dependency**: `xlrd` Python package

**Files to reference**: `data/DaviBank Visa-in.xls` → `data/DaviBank Visa-out1.csv`

---

### Task 2.2 — DaviBank Stage 2 (CSV → split by currency)

**Input**: `{basename}-out1.csv`
**Output**: `{basename}-out2-crc.csv`, `{basename}-out2-usd.csv`

**Transformations:**

1. **Remove card separator rows** — Rows where column 1 is `Tarjeta Número:` (or first field matches this pattern)

2. **Split by Moneda column**:
   - **CRC file**: Rows where `Moneda == "CRC"`
   - **USD file**: Rows where `Moneda == "USD"`

3. **Normalize dates** — Expand short dates (e.g., `1/3/26` → `01/03/2026`, `7/2/26` → `07/02/2026`). All output dates must be DD/MM/YYYY zero-padded.

4. **Keep same column structure** — All 6 columns preserved (Número de Referencia, Fecha de Movimiento, Descripción, Monto, Moneda, Tipo)

**Files to reference**: `data/DaviBank Visa-out1.csv` → `data/DaviBank Visa-out2-crc.csv`, `data/DaviBank Visa-out2-usd.csv`

---

### Task 2.3 — DaviBank Stage 3 (split → YNAB format)

**Input**: `{basename}-out2-crc.csv`, `{basename}-out2-usd.csv`
**Output**: `{basename}-out3-crc.csv`, `{basename}-out3-usd.csv`

**Transformations:**

1. **Column mapping**:
   | Source Column | → | YNAB Column |
   |---|---|---|
   | Fecha de Movimiento | → | Date |
   | Descripción | → | Payee |
   | Número de Referencia | → | Memo (empty `""` if blank) |
   | Monto | → | Amount |
   | Moneda | → | *(dropped)* |
   | Tipo | → | *(dropped)* |

2. **Date format** — Convert `DD/MM/YYYY` → `YYYY/MM/DD` (same as BAC Stage 3)

3. **CSV quoting** — All fields double-quoted: `"Date","Payee","Memo","Amount"`

4. **Amount** — Use Monto value directly. Sign is already correct (negative for CREDITO, positive for DEBITO).

**Note**: Both BAC and DaviBank Stage 3 output the same YNAB format: `"Date","Payee","Memo","Amount"` with YYYY/MM/DD dates.

**Files to reference**: `data/DaviBank Visa-out2-crc.csv` → `data/DaviBank Visa-out3-crc.csv`

---

## Phase 3: Orchestrator

### Task 3.1 — Orchestrator Script

**Input**: One or more file paths via CLI arguments
**Output**: All stage files written to the same directory as input

**Features:**
1. **Bank auto-detection**:
   - `.xls` extension → DaviBank pipeline
   - `.csv` extension → BAC pipeline
2. **Filename handling**:
   - Strip `-in` suffix if present before appending stage suffixes
   - Example: `BAC MCB Febrero-in.csv` → base = `BAC MCB Febrero`
   - Example: `BAC MCB Marzo.csv` → base = `BAC MCB Marzo`
   - Outputs: `{base}-out1.csv`, `{base}-out2-crc.csv`, `{base}-out2-usd.csv`, `{base}-out3-crc.csv`, `{base}-out3-usd.csv`
3. **Stage sequencing**: Stage 1 → Stage 2 → Stage 3 (feed output of each stage to next)
4. **All intermediate files written to disk** (not just final out3)
5. **CLI interface**: `python scripts/orchestrator.py <file1> [file2] ...`

---

## Phase 4: Testing Framework

### Task 4.1 — Test Infrastructure & BAC Tests

**Approach**: pytest-based. Compare script output against provided sample files.

**Testing strategy for handling date format differences**:
- The manual sample files (out1, out2) have Excel-artifact date formats (some D/M/YY, some DD/MM/YYYY mixed). Our scripts produce consistent DD/MM/YYYY.
- **Intermediate stages (out1, out2)**: Semantic comparison — same number of rows, same descriptions, same amounts, same row order. Dates parsed and compared as actual date values, not string equality.
- **Final stage (out3)**: Content comparison — same rows with same semantic content. Dates must be in YYYY/MM/DD format. The existing sample out3 files have old date formats, so the test verifies row content matches while separately asserting YYYY/MM/DD formatting.

**BAC test cases**:
1. Run full pipeline on `BAC MCB Febrero-in.csv`
2. Verify out1: correct row count (88 in → ~82 out — header/footer stripped), no "Previous balance", no "REVERSION" lines, card separator rows present
3. Verify out2-crc: no card separators, no USD-only rows, header has "Description", correct row count
4. Verify out2-usd: only USD transactions, correct 6 rows
5. Verify out3-crc: YNAB header, all quoted, dates YYYY/MM/DD, Amount = Local values, Memo empty
6. Verify out3-usd: YNAB header, all quoted, dates YYYY/MM/DD, Amount = Dollars values, Memo empty

### Task 4.2 — DaviBank Tests

**DaviBank test cases**:
1. Run full pipeline on `DaviBank Visa-in.xls`
2. Verify out1: valid CSV, correct columns, all rows from XLS, card separators present
3. Verify out2-crc: no card separators, only CRC rows, dates DD/MM/YYYY, 23 rows
4. Verify out2-usd: only USD rows, 7 rows
5. Verify out3-crc: YNAB format, Memo = Número de Referencia (or empty), dates YYYY/MM/DD
6. Verify out3-usd: YNAB format, same mapping

### Task 4.3 — Run BAC MCB Marzo through pipeline
- Input: `BAC MCB Marzo.csv` (or `BAC MCB Marzo-in.csv`)
- Generate all output files for manual review
- No expected output files to compare against (this is a new month)

---

## Key Technical Details

### BAC Footer Detection (invariant across months)
The footer starts at the first row whose description field contains `REVERSION INTERES CORRIENTES PERIODO`. Everything from this row to end-of-file is stripped in Stage 1. Verified identical structure in both Febrero and Marzo files.

### BAC Header Structure (invariant)
- Line 1: `Pro000000000000duct, Name, Date, ...` (9 columns)
- Line 2: Card number, cardholder name, dates, amounts (9 columns)
- Line 3: `Date, , Local, Dollars` (4 columns — DATA HEADER, kept)
- Line 4: `, Previous balance, ...` (removed)

### BAC Card Separator Pattern
- Empty date field
- Description matches card number: `5466-37**-****-NNNN`
- Local and Dollars both = 0
- Regex: `^\d{4}-\d{2}\*\*-\*\*\*\*-\d{4}$`

### DaviBank Card Separator Pattern
- First column = `Tarjeta Número:`
- Second column = full card number
- Remaining columns empty

### Number Formatting Rule (both banks)
- `4200.00` → `4200` (strip .00)
- `11518.99` → `11518.99` (keep meaningful decimals)
- `3980.50` → `3980.5` (strip trailing zero after decimal)
- `0.00` → `0`
- Implementation: convert to float, then format — if integer-valued, output as int; otherwise strip trailing zeros.

### Date Parsing Rules
Input dates come in mixed formats due to Excel artifacts:
- `DD/MM/YYYY` (e.g., `14/01/2026`) — standard
- `D/M/YY` (e.g., `5/1/26`) — Excel-shortened
- All dates are in DD/MM/YYYY order (day first, NOT month first)
- 2-digit years: assume 2000s (26 → 2026)
- Output for intermediate stages: `DD/MM/YYYY`
- Output for Stage 3 (YNAB): `YYYY/MM/DD`

### YNAB Output Format (final Stage 3 for both banks)
```csv
"Date","Payee","Memo","Amount"
"2026/01/05","MINISUPER TIERRAS DEL\HEREDIA\     C","","4200"
```

---

## Dependencies

- **Python 3.8+** (standard library: csv, os, sys, argparse, re, pathlib)
- **xlrd** — for reading .xls files (DaviBank)
- **pytest** — for test framework

`requirements.txt`:
```
xlrd>=2.0.1
pytest>=7.0
```

---

## Decisions & Scope

- **Date normalization**: Scripts produce consistent DD/MM/YYYY in stages 1-2 (not replicating Excel's random D/M/YY shortening). Tests compare semantically.
- **Out3 date format**: `YYYY/MM/DD` as requested (differs from existing manual samples which use D/M/YY or DD/MM/YYYY). This is an improvement over the manual process.
- **Description/Payee text**: Preserved verbatim including backslashes, internal whitespace. Leading space before description kept.
- **BAC Memo column**: Always empty in YNAB output (BAC has no reference numbers in their export)
- **DaviBank Memo column**: Populated with Número de Referencia if present; empty string otherwise
- **Language**: Python (has xlrd for XLS, good CSV support, cross-platform)
- **All intermediate files written to disk**: out1, out2-crc, out2-usd, out3-crc, out3-usd

## Implementation Order

1. Task 1.1 → Task 1.2 → Task 1.3 (BAC pipeline, sequential — each depends on previous)
2. Task 4.1 (BAC tests — can validate as each task completes)
3. Task 2.1 → Task 2.2 → Task 2.3 (DaviBank pipeline, sequential)
4. Task 4.2 (DaviBank tests)
5. Task 3.1 (Orchestrator — depends on all stage scripts)
6. Task 4.3 (Run Marzo through pipeline)
