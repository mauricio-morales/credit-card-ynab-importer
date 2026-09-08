# Contract: QIF Output File Format

This is not a network/API contract — it's the file-format and
module-interface contract this feature exposes: (1) the QIF file grammar any
QIF-compatible finance tool will parse, and (2) the internal `qif_export`
module interface `orchestrator.py` and both bank pipelines depend on.

## 1. File grammar

```
qif-file      = header, { record } ;
header        = "!Type:Bank", NEWLINE ;
record        = date-line, payee-line, [ memo-line ], amount-line, end-line ;
date-line     = "D", MM, "/", DD, "/", YYYY, NEWLINE ;
payee-line    = "P", payee-text, NEWLINE ;
memo-line     = "M", memo-text, NEWLINE ;
amount-line   = "T", amount-text, NEWLINE ;
end-line      = "^", NEWLINE ;
```

- `payee-text` / `memo-text`: source text with any `\r\n`, `\r`, or `\n`
  collapsed to a single space. No other escaping.
- `amount-text`: copied verbatim from the source CSV's `Amount` field
  (already sign-adjusted and decimal-trimmed per Constitution Principle IV).
- `memo-line` is emitted **if and only if** the source memo is non-empty.
- A file with zero transactions is exactly one line: `!Type:Bank\n`.
- Line endings: `\n`. Encoding: UTF-8.

## 2. Example

Given this out3 CSV (DaviBank, one row with a comma in the payee, one with
empty memo):

```csv
"Date","Payee","Memo","Amount"
"2026/03/05","AMAZON.COM, INC.","REF123","-4500"
"2026/03/07","SOME MERCHANT","","1200"
```

The generated `.qif` file is:

```
!Type:Bank
D03/05/2026
PAMAZON.COM, INC.
MREF123
T-4500
^
D03/07/2026
PSOME MERCHANT
T1200
^
```

## 3. Module interface: `scripts/qif_export.py`

```python
def convert_csv_to_qif(csv_path: str | Path, qif_path: str | Path) -> str:
    """Read a finished out3 YNAB CSV file and write its QIF equivalent.

    Reads `csv_path` (the "Date","Payee","Memo","Amount" file already
    written by bac_stage3.process()/davi_stage3.process()) and writes a
    QIF bank-transaction file to `qif_path`, one record per CSV data row,
    in the same order. Does not read or write `csv_path` itself beyond
    opening it for reading. Returns str(qif_path).
    """
```

**Callers**: `orchestrator.py`'s `run_bac()` and `run_davi()`, once per
currency split, immediately after that split's `out3` CSV is written by
`bac_stage3.process()` / `davi_stage3.process()`.

**Preconditions**: `csv_path` exists and is a valid out3-format CSV (header
row + zero or more `"Date","Payee","Memo","Amount"` rows).

**Postconditions**:
- `qif_path` exists and satisfies the grammar in §1.
- `csv_path` is unmodified (opened read-only).
- Number of QIF records in `qif_path` == number of data rows in `csv_path`.

**Failure behavior**: If `csv_path` cannot be read or `qif_path` cannot be
written, the exception propagates to the orchestrator's existing
`try/except` error-reporting path (same pattern already used for stage
failures — see `orchestrator.run()`), and the CSV file already on disk is
left untouched (per FR-010 and the spec's Edge Cases).
