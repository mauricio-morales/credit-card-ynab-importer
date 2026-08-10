# Data Model: Scotia/DaviBank XLSX Import

**Feature**: 004-scotia-xlsx-import | **Date**: 2026-08-09

This pipeline has no persistent storage or ORM entities — "data model" here means the row-level schema and how it is transformed as it moves through the three pipeline stages, per Constitution Principle I (Pipeline-Stage Isolation). This is unchanged from the legacy `.xls` pipeline except for the *source* of the Transaction Record (`.xlsx` sheet instead of `.xls` sheet).

## Entities

### Transaction Record

A single statement line item, sourced from one data row of the `.xlsx` worksheet.

| Field | Source column (header) | Type at Stage 1 | Notes |
|---|---|---|---|
| Reference number | `Número de Referencia` | string (may be empty) | Empty for some `CREDITO` payment rows in the reference sample; becomes the YNAB `Memo`. |
| Transaction date | `Fecha de Movimiento` | string `D/M/YYYY` or `DD/MM/YYYY`, **or** native `datetime.date`/`datetime.datetime` | Normalized to `DD/MM/YYYY` at Stage 1 output regardless of source cell type (research.md §3); further normalized/zero-padded at Stage 2; reformatted to `YYYY/MM/DD` at Stage 3. |
| Description | `Descripción` | string | Preserved verbatim (Constitution Principle IV) — becomes YNAB `Payee`. |
| Amount | `Monto` | string, **or** native numeric | Stage 1 strips a trailing `.00` (`format_number`); Stage 3 negates sign (`negate_amount`) — charges (positive source) become negative YNAB outflows, payments (negative source) become positive inflows. |
| Currency | `Moneda` | string, `CRC` or `USD` | Drives the Stage 2 split into two files. |
| Transaction type | `Tipo` | string, `DEBITO` or `CREDITO` | Passed through unchanged; not otherwise interpreted by the pipeline. |
| Card | *(derived)* | string (card number) | Not a worksheet column — inherited from the most recent preceding Card Section marker row. |

**Validation rules** (FR-008, User Story 3):
- A row is only treated as a Transaction Record if it is not the header row, not fully empty, not a Card Section marker, and not a skipped footer/summary row (see below).
- If the header row (row 0) is missing one or more of the six expected column names, Stage 1 MUST fail with a plain-language "expected columns not found" error rather than silently emitting incomplete rows.

### Card Section

A grouping marker that associates subsequent Transaction Records with a card number, until superseded by the next marker.

- Identified by: first cell (`Número de Referencia` column position) equals literal text `Tarjeta Número:`.
- Second cell holds the card number; remaining cells (`Descripción` … `Tipo` positions) are empty numeric cells in `.xlsx` (`cell.value is None`), versus `xlrd.XL_CELL_EMPTY` in the legacy `.xls` reader — same semantic emptiness, different underlying sentinel.
- A single statement file may contain multiple Card Section markers, and the same card number may reappear later in the file (confirmed in the reference sample: card `4573060030758398` appears, is interrupted by a second card's section, then resumes) — Stage 1 does not merge or dedupe sections; it emits the marker rows through to `out1.csv` as-is (Stage 2 strips them after they've served their associative purpose).

### Non-transaction rows (skipped, not an entity)

Rows that must be recognized and dropped without becoming Transaction Records:
- Fully empty rows (all six cells empty).
- Footer/summary rows: first cell non-empty, `Descripción`/date-adjacent cells empty, and the row is not a Card Section marker (e.g., a "Rango de fechas" note). None appear in the verified reference sample, but the rule is retained defensively per spec edge cases.

### YNAB Output File

Unchanged from the existing pipeline (Constitution Principle II) — one CSV per currency (`CRC`, `USD`), columns `"Date","Payee","Memo","Amount"`, all fields double-quoted, dates `YYYY/MM/DD`, amounts sign-negated relative to source. No field of this entity is affected by the `.xls`→`.xlsx` source-format change.

## State / stage flow

```
.xlsx workbook (1st sheet)
   │  davi_stage1.process()  — openpyxl read; header validation; card-section
   │                           passthrough; native-cell normalization; skip rules
   ▼
out1.csv  (6 cols: ref, date DD/MM/YYYY, desc, amount, currency, type — incl. card markers)
   │  davi_stage2.process()  — strip card markers; normalize date; split by Moneda
   ▼
out2-crc.csv / out2-usd.csv  (same 6 cols, single currency, no markers)
   │  davi_stage3.process()  — YYYY/MM/DD dates; negate_amount(); CSV-quote
   ▼
out3-crc.csv / out3-usd.csv  ("Date","Payee","Memo","Amount" — final YNAB import files)
```

## Error states (new for this feature)

| Condition | Detection point | User-facing behavior (FR-007 / FR-008) |
|---|---|---|
| Selected file has `.xls` extension | Before any parse attempt (extension check) | Plain-language message: legacy format no longer supported, export `.xlsx` from the bank instead. No crash/traceback shown. |
| Selected `.xlsx` file is not a valid/readable spreadsheet (corrupt, wrong file type renamed to `.xlsx`) | `openpyxl.load_workbook()` raises | Plain-language "couldn't read this file" message. No crash/traceback shown. |
| `.xlsx` file opens but header row is missing one or more expected columns | Header validation immediately after opening the sheet | Plain-language "expected transaction data not found" message identifying that the layout looks different than expected. No partial/incorrect output written. |
| `.xlsx` file has a valid header but zero transaction rows | End of Stage 1 row loop | Not an error — Stage 1 emits header-only `out1.csv`; pipeline completes normally through empty `out3-*.csv` files (per spec edge case). |
