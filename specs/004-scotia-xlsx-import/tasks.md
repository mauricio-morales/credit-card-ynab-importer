---

description: "Task list for Scotia/DaviBank XLSX Import"
---

# Tasks: Scotia/DaviBank XLSX Import

**Input**: Design documents from `/specs/004-scotia-xlsx-import/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [research.md](./research.md), [contracts/davi-pipeline-io.md](./contracts/davi-pipeline-io.md), [quickstart.md](./quickstart.md)

**Tests**: Included. Constitution Principle III (Test-First, NON-NEGOTIABLE) and plan.md commit to writing/updating regression tests before the Stage 1 rewrite lands, so each story's tests are listed before its implementation tasks.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

Single project. All changes are confined to `scripts/`, `tui/screens/`, `tests/`, and `requirements.txt` — no new top-level structure (see plan.md § Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Swap the XLSX-reading dependency before any code references it

- [X] T001 Update requirements.txt: remove `xlrd>=2.0.1` and `xlwt>=1.3`, add `openpyxl>=3.1`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error types and the openpyxl file-opening path that every user story's behavior (success, rejection, validation) is built on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add `LegacyFormatError`, `UnreadableFileError`, and `MissingColumnsError` exception classes (each carrying a `.user_message` plain-language string, per contracts/davi-pipeline-io.md §2) at the top of scripts/davi_stage1.py
- [X] T003 Add a `_load_worksheet(input_path)` helper in scripts/davi_stage1.py: raise `LegacyFormatError` when `input_path.suffix.lower() == '.xls'` (before attempting to open the file); otherwise call `openpyxl.load_workbook(str(input_path), read_only=True, data_only=True)`, catching open failures (e.g. `zipfile.BadZipFile`, `OSError`, `openpyxl` exceptions) and raising `UnreadableFileError`; return `worksheet[0]` (first/primary sheet), per data-model.md and contracts/davi-pipeline-io.md §1 (depends on T002)

**Checkpoint**: `davi_stage1.py` can open a workbook (or fail with one of the three typed errors) via openpyxl. Ready for story-specific behavior.

---

## Phase 3: User Story 1 - Import a current-format statement (Priority: P1) 🎯 MVP

**Goal**: A Scotia/DaviBank `.xlsx` statement converts to the same YNAB-ready output the `.xls` pipeline produced — same transaction count, dates, descriptions, amounts, currency splits, and card-section handling.

**Independent Test**: Select a real Scotia/DaviBank `.xlsx` statement (via `python scripts/orchestrator.py <file>.xlsx` or the TUI) and verify the resulting `out3-crc.csv`/`out3-usd.csv` match the transaction count and values the `.xls`-based process produced for equivalent data.

### Tests for User Story 1 ⚠️

> Write these first; they should fail against the current xlrd-based Stage 1 (or fail to collect for missing fixtures) until the implementation tasks below land.

- [X] T004 [P] [US1] Update tests/test_davi_pipeline.py fixture-path constants (`INPUT_FILE`, `EXPECTED_OUT1`, `EXPECTED_OUT2_CRC`, `EXPECTED_OUT2_USD`, `EXPECTED_OUT3_CRC`, `EXPECTED_OUT3_USD`) to point at the `.xlsx`-sourced `DaviBank Sample-*` fixture set (input extension changes from `.xls` to `.xlsx`; output filenames unchanged)
- [X] T005 [P] [US1] Add tests in tests/test_davi_pipeline.py for multi-card-section passthrough (transactions from every card section appear, including a card number that reappears after being interrupted by another card's section) and correctly signed debit/credit amounts (spec Acceptance Scenarios 2–3)
- [X] T006 [P] [US1] Hand-author edge-case fixture tests/fixtures/DaviBank EmptyTransactions-in.xlsx (valid 6-column header, zero data rows) via openpyxl, and add a test in tests/test_davi_pipeline.py asserting `davi_stage1.process()` produces a header-only `out1.csv` without error
- [X] T007 [P] [US1] Hand-author edge-case fixture tests/fixtures/DaviBank FooterRow-in.xlsx (header + data rows + a trailing footer/summary row, e.g. a "Rango de fechas" note) via openpyxl, and add a test in tests/test_davi_pipeline.py asserting the footer row is skipped and not emitted as a transaction
- [X] T008 [P] [US1] Hand-author edge-case fixture tests/fixtures/DaviBank MultiSheet-in.xlsx (two worksheets; transaction data only on the first) via openpyxl, and add a test in tests/test_davi_pipeline.py asserting only the first sheet's transactions appear in `out1.csv`
- [X] T009 [P] [US1] Hand-author edge-case fixture tests/fixtures/DaviBank NativeCells-in.xlsx (at least one row with a native `datetime` date cell and one row with a native numeric `Monto` cell, alongside normal string-cell rows) via openpyxl, and add a test in tests/test_davi_pipeline.py asserting both native cell types normalize to the same shape as their string-cell equivalents (FR-006)

### Implementation for User Story 1

- [X] T010 [US1] Rewrite the row-iteration loop in `davi_stage1.process()` (scripts/davi_stage1.py) to use `_load_worksheet()` (T003) and `worksheet.iter_rows()` instead of `xlrd`, preserving header passthrough (row 0), fully-empty-row skip, footer/summary-row skip, and card-section-marker (`Tarjeta Número:`) passthrough logic; update the emptiness check from `xlrd.XL_CELL_EMPTY` to `cell.value is None` (depends on T003)
- [X] T011 [US1] Add native-cell normalization in scripts/davi_stage1.py: format `Fecha de Movimiento` as `DD/MM/YYYY` when the cell value is a `datetime.date`/`datetime.datetime`; apply `format_number()`-equivalent handling (strip trailing `.00`, preserve real decimals) when `Monto` arrives as a native numeric value, per research.md §3 (depends on T010)
- [X] T012 [US1] Update `run()` in scripts/orchestrator.py to also route `.xlsx` files to `run_davi()` (alongside the existing `.xls` branch), per contracts/davi-pipeline-io.md §3
- [X] T013 [US1] Update `_header_text()` in tui/screens/file_picker.py: change the DaviBank label from `"Select a Davi/Scotia XLS file:"` to reflect `.xlsx` as the expected format
- [X] T014 [US1] Replace `obfuscate_davi_xls` (xlwt-based) in scripts/generate_fixtures.py with an openpyxl-based `obfuscate_davi_xlsx`, reading `data/DaviBank Visa-in.xlsx` and writing an obfuscated `tests/fixtures/DaviBank Sample-in.xlsx` using the existing `DAVI_SUBS` substitutions; update `main()`'s DaviBank block and drop the `xlwt` import/`ImportError` guard
- [X] T015 [US1] Update `run_davi()` in scripts/generate_expected_outputs.py to read `{prefix}-in.xlsx` instead of `{prefix}-in.xls`
- [X] T016 [US1] Regenerate committed fixtures: place a real `.xlsx` statement at `data/DaviBank Visa-in.xlsx` (git-ignored, never committed), then run `python scripts/generate_fixtures.py` and `python scripts/generate_expected_outputs.py` to produce `tests/fixtures/DaviBank Sample-in.xlsx` and refreshed `DaviBank Sample-out{1,2,3}*.csv` (depends on T010, T011, T014, T015)

**Checkpoint**: `pytest tests/test_davi_pipeline.py` passes against the `.xlsx` fixture set; `python scripts/orchestrator.py "<real>.xlsx"` produces correct YNAB output files. User Story 1 is independently functional — this is the MVP.

---

## Phase 4: User Story 2 - Clear feedback on legacy or invalid files (Priority: P2)

**Goal**: A legacy `.xls` file or an unreadable/malformed file selected in the Scotia/DaviBank flow produces a plain-language message, never a raw crash.

**Independent Test**: Select a legacy `.xls` file, and separately a non-spreadsheet file, in the Scotia/DaviBank flow (CLI or TUI) and confirm each produces an understandable message rather than a crash or traceback.

### Tests for User Story 2 ⚠️

- [X] T017 [P] [US2] Add `test_legacy_xls_rejected` in tests/test_davi_pipeline.py asserting `davi_stage1.process()` raises `LegacyFormatError` with a plain-language `.user_message` for `tests/fixtures/DaviBank Sample-in.xls` (existing fixture, kept as-is per research.md §6 — not regenerated)
- [X] T018 [P] [US2] Hand-author fixture tests/fixtures/DaviBank NotASpreadsheet-in.xlsx (non-spreadsheet content saved with an `.xlsx` extension) and add `test_unreadable_file_rejected` in tests/test_davi_pipeline.py asserting `davi_stage1.process()` raises `UnreadableFileError` with a plain-language `.user_message`

### Implementation for User Story 2

- [X] T019 [US2] Update `run()` in scripts/orchestrator.py to catch exceptions exposing a `.user_message` attribute around the `run_davi()`/`run_bac()` calls, print `.user_message` to stderr, and exit non-zero without writing partial output files, per contracts/davi-pipeline-io.md §3 (depends on T002)

**Checkpoint**: CLI on a legacy `.xls` file or a corrupt `.xlsx` file prints a plain-language message and exits non-zero with no output files written. The TUI already catches all conversion exceptions generically (`tui/screens/progress.py` `_run_conversion`/`_plain_english`) and renders `error_message` on the summary screen without crashing, so `LegacyFormatError`/`UnreadableFileError`'s plain-language text (from T002) surfaces there with no further TUI code changes needed — confirm this manually per quickstart.md step 5.

---

## Phase 5: User Story 3 - Validation of unexpected file layout (Priority: P3)

**Goal**: A `.xlsx` file with a missing/renamed/reordered expected column is flagged clearly instead of silently producing incomplete or incorrect YNAB data.

**Independent Test**: Feed the importer a `.xlsx` file missing an expected column (e.g., no `Monto` column) and confirm it flags the problem rather than emitting incomplete or incorrect transactions.

### Tests for User Story 3 ⚠️

- [X] T020 [P] [US3] Hand-author fixture tests/fixtures/DaviBank MissingColumn-in.xlsx (header row missing the `Monto` column) via openpyxl
- [X] T021 [P] [US3] Add `test_missing_columns_rejected` in tests/test_davi_pipeline.py asserting `davi_stage1.process()` raises `MissingColumnsError` naming the missing column via `.user_message`, and that no `out1.csv` is written, for `DaviBank MissingColumn-in.xlsx`

### Implementation for User Story 3

- [X] T022 [US3] Add header-row validation in `davi_stage1.process()` (scripts/davi_stage1.py): immediately after loading the worksheet, verify row 0 contains all six expected headers (`Número de Referencia`, `Fecha de Movimiento`, `Descripción`, `Monto`, `Moneda`, `Tipo`) in order; raise `MissingColumnsError` naming what's missing/different before any row is written, per data-model.md Validation rules (depends on T010)

**Checkpoint**: A `.xlsx` file missing a required column is rejected with a clear message instead of producing incomplete output. All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Update the module docstring in scripts/davi_stage1.py ("XLS -> CSV conversion") to describe `.xlsx` input
- [X] T024 [P] Update the `.xls`-era bank-detection comment/docstring in scripts/orchestrator.py to mention `.xlsx`
- [X] T025 Run specs/004-scotia-xlsx-import/quickstart.md steps 1–5 end-to-end: regenerate fixtures, `pytest tests/test_davi_pipeline.py -v`, CLI run against a real `.xlsx` and a legacy `.xls`, and manual TUI verification of both the success and legacy-rejection paths
- [X] T026 Run the full suite `pytest` to confirm the BAC (`.csv`) pipeline has no regression

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (needs `openpyxl` installed) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only (T019 needs T002's exception types); independent of US1's row-parsing logic, though sharing `davi_stage1.py` means merging both stories' edits to that file
- **User Story 3 (Phase 5)**: Depends on Foundational (T002) and on US1's row-loop (T010, for T022's placement); independent of US2
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on US2/US3 — deliverable alone as the MVP
- **User Story 2 (P2)**: No functional dependency on US1, but T019 and US1's T010/T011 both edit scripts/davi_stage1.py and scripts/orchestrator.py — sequence to avoid merge conflicts if working solo
- **User Story 3 (P3)**: T022 is inserted into the row-loop built by US1's T010 — implement after T010 lands

### Within Each User Story

- Tests written first (T004–T009, T017–T018, T020–T021), expected to fail before their story's implementation tasks land
- Fixture authoring and test-writing within a story are parallelizable ([P]); implementation tasks touching the same file (`scripts/davi_stage1.py`) are sequential

### Parallel Opportunities

- T002 has no same-file conflict at Setup/Foundational boundary but T003 depends on it
- All US1 test/fixture tasks (T004–T009) can run in parallel — different files
- All US2 test/fixture tasks (T017–T018) can run in parallel
- All US3 test/fixture tasks (T020–T021) can run in parallel
- T023 and T024 (Polish docstrings) can run in parallel — different files

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test/fixture tasks together:
Task: "Update fixture-path constants in tests/test_davi_pipeline.py"
Task: "Add multi-card-section and signed-amount tests in tests/test_davi_pipeline.py"
Task: "Hand-author DaviBank EmptyTransactions-in.xlsx + zero-row test"
Task: "Hand-author DaviBank FooterRow-in.xlsx + footer-skip test"
Task: "Hand-author DaviBank MultiSheet-in.xlsx + first-sheet-only test"
Task: "Hand-author DaviBank NativeCells-in.xlsx + native-cell test"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T003) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T004–T016)
4. **STOP and VALIDATE**: `pytest tests/test_davi_pipeline.py`, then run a real `.xlsx` statement through `scripts/orchestrator.py` and confirm output matches prior `.xls` behavior
5. This alone restores the tool's core, currently-broken functionality

### Incremental Delivery

1. Setup + Foundational → openpyxl-backed file opening with typed errors
2. Add User Story 1 → test independently → this is the MVP (importer works again)
3. Add User Story 2 → test independently → legacy `.xls`/corrupt-file users get a clear message instead of a crash
4. Add User Story 3 → test independently → future layout drift is caught, not silently corrupted
5. Polish → docstrings, quickstart validation, full-suite regression check

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All three stories converge on scripts/davi_stage1.py — implement in priority order (US1 → US2 → US3) to minimize merge friction within that one file
- Verify each story's tests fail before implementing that story
- The Constitution's Technical Stack section (`xlrd` for `.xls`) and Principle V's "Only BAC `.csv` and DaviBank `.xls`" statement are now inaccurate (plan.md § Constitution Check, research.md §5) — run `/speckit-constitution` to amend them; this is a separate governance action, not one of the tasks above
