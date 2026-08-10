# Contract: DaviBank/Scotia Pipeline I/O

**Feature**: 004-scotia-xlsx-import | **Date**: 2026-08-09

This tool has no network API; its external interfaces are (a) the CLI/TUI entry points a user drives, and (b) the file formats it reads and writes. This contract documents both as they change for this feature. Everything not listed here is unchanged from the current `.xls` behavior.

## 1. Input file contract — Scotia/DaviBank `.xlsx` statement

- **Format**: OOXML `.xlsx` workbook.
- **Sheet**: only `workbook.worksheets[0]` (the first/primary sheet) is read, regardless of how many sheets exist.
- **Header row** (row 1, index 0): MUST contain these six column headers, in this order:
  `Número de Referencia | Fecha de Movimiento | Descripción | Monto | Moneda | Tipo`
  - If any is missing/renamed, Stage 1 raises a header-validation error (see §3) instead of proceeding.
- **Data rows**: one of three shapes —
  1. **Card Section marker**: col A = `Tarjeta Número:`, col B = card number, cols C–F empty.
  2. **Transaction row**: all six columns populated (`Número de Referencia` may legitimately be blank for some `CREDITO` rows).
  3. **Skippable row**: fully empty, or a footer/summary row (col A populated, cols B/C empty, not a Card Section marker).
- **Cell typing**: `Fecha de Movimiento` and `Monto` MAY be plain text or MAY be native OOXML types (date/number respectively); both MUST be accepted and normalized (data-model.md, Error states / research.md §3).

## 2. `davi_stage1.process(input_path, output_path=None) -> str`

**Signature unchanged.** Behavior contract:

- **Preconditions removed**: no longer requires `xlrd`-openable `.xls`; now requires an `openpyxl`-openable `.xlsx`.
- **New failure modes** (raised as exceptions with a `.user_message` plain-language string, caught and surfaced by the orchestrator/TUI — never an unhandled traceback reaching the user):
  - `LegacyFormatError` — input path has a `.xls` extension. Message: states `.xls` is no longer supported and an `.xlsx` export is required.
  - `UnreadableFileError` — `openpyxl.load_workbook()` fails to open the file (not a valid spreadsheet). Message: plain-language "couldn't read this file" explanation.
  - `MissingColumnsError` — header row present but one or more of the six expected column names are absent. Message: names what looks different/missing.
- **Success behavior unchanged**: writes `out1.csv` with the same 6-column shape (including Card Section marker passthrough rows) as the `.xls` pipeline produced, and returns the output path string.
- **Zero-transaction input**: a valid header with no data rows is a success, not an error — produces a header-only `out1.csv`.

## 3. `scripts/orchestrator.py` CLI contract

**Invocation unchanged**: `python scripts/orchestrator.py <file1> [file2 ...]`.

**Extension routing** (`run()`):

| Extension | Current behavior | New behavior |
|---|---|---|
| `.csv` | BAC pipeline | Unchanged |
| `.xls` | DaviBank pipeline (via `xlrd`) | Rejected with plain-language "format no longer supported, use `.xlsx`" message printed to stderr; **non-zero exit**, no partial output files written |
| `.xlsx` | Unsupported — `ERROR: Unsupported file type` | DaviBank pipeline (via `openpyxl`) |

- Any exception raised by a pipeline stage that carries a plain-language `user_message` MUST be printed as that message (not a raw traceback) before exiting non-zero.

## 4. TUI file-picker contract (`tui/screens/file_picker.py`)

- `ConversionType.DAVI` (non-BAC) file picker already allows both `{".xls", ".xlsx"}` extensions in its directory-tree filter — unchanged.
- Header label text updates from `"Select a Davi/Scotia XLS file:"` to reflect that `.xlsx` is now the expected format (exact copy is an implementation detail, not re-specified here).
- Selecting a `.xls` file and confirming MUST surface the same plain-language "no longer supported" message as the CLI path (via whatever error-surfacing mechanism the TUI's progress/summary screens already use for pipeline failures) — not a raw exception/crash screen.

## 5. Output file contract — unchanged

`out1.csv`, `out2-crc.csv`, `out2-usd.csv`, `out3-crc.csv`, `out3-usd.csv` naming, location (alongside input file), and content format are **byte-for-byte unchanged** in shape from the `.xls` pipeline for equivalent input data — this feature changes only how the input is read, not what is produced (Constitution Principle II).
