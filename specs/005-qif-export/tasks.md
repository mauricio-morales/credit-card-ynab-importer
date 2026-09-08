---

description: "Task list for QIF Export Alongside YNAB CSV Output"
---

# Tasks: QIF Export Alongside YNAB CSV Output

**Input**: Design documents from `/specs/005-qif-export/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/qif-output-format.md](./contracts/qif-output-format.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are included — `plan.md`'s Testing section and `quickstart.md` explicitly call for `tests/test_qif_export.py` plus extensions to `tests/test_bac_pipeline.py` / `tests/test_davi_pipeline.py`, and Constitution Principle III (Test-First) is NON-NEGOTIABLE for this project.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project layout (existing repo structure): `scripts/`, `tests/`, `tests/fixtures/` at repository root — see `plan.md` Project Structure.

---

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

Not applicable to this feature — no new dependency, no new CLI flag, no new top-level structure (`plan.md` Technical Context: "None new"). Proceed directly to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

Not applicable — this feature has a single shared artifact, `scripts/qif_export.py`, which is itself the P1 deliverable (User Story 1 below). There is no separate infrastructure layer that US2/US3 need ahead of US1; both build directly on US1's module. Proceed to Phase 3.

---

## Phase 3: User Story 1 - Get a QIF file alongside every YNAB CSV (Priority: P1) 🎯 MVP

**Goal**: For every final `out3` CSV the BAC and DaviBank pipelines write, produce a sibling `.qif` file with the same transactions, automatically, with no new CLI flag.

**Independent Test**: Run `python scripts/orchestrator.py` against a sample BAC `.csv` and a sample DaviBank `.xlsx` statement; confirm a matching `-out3-crc.qif` / `-out3-usd.qif` exists next to each `-out3-crc.csv` / `-out3-usd.csv`, containing the same transactions.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation** (Constitution Principle III)

- [X] T001 [P] [US1] In `tests/test_qif_export.py`, write contract tests for `scripts/qif_export.py`'s `convert_csv_to_qif(csv_path, qif_path)` against `contracts/qif-output-format.md` §1–§2: output starts with exactly one `!Type:Bank` header line; one `D`/`P`/`M`/`T`/`^` record per CSV data row, in source row order; `D` line reformats the CSV's `YYYY/MM/DD` date to `MM/DD/YYYY`; `T` line copies the CSV `Amount` value verbatim (no sign changes). Use the contract's worked example (§2: `AMAZON.COM, INC.` / `SOME MERCHANT` rows) as one of the fixture cases. The module does not exist yet, so these tests MUST fail on a bare `import scripts.qif_export` (or fail at call time) until T003 lands.
- [X] T002 [P] [US1] In `tests/test_qif_export.py`, write a contract test asserting `convert_csv_to_qif()` returns `str(qif_path)`, and a second test asserting the source `csv_path` file's content/mtime is unchanged after the call (module opens it read-only per the contract's Postconditions).

### Implementation for User Story 1

- [X] T003 [US1] Create `scripts/qif_export.py` implementing `convert_csv_to_qif(csv_path: str | Path, qif_path: str | Path) -> str` per `contracts/qif-output-format.md` §1 and §3: read the out3 CSV with `csv.reader` (header row `"Date","Payee","Memo","Amount"` + zero or more data rows), write `qif_path` with a `!Type:Bank` header line followed by one record per data row (`D{MM/DD/YYYY}`, `P{payee}`, `M{memo}` only when memo is non-empty, `T{amount}`, `^`), UTF-8 encoding, `\n` line endings. Stdlib-only (`csv`, `pathlib`). Must make T001 and T002 pass. (Depends on T001, T002 existing and failing.)
- [X] T004 [US1] In `scripts/orchestrator.py`, add `import qif_export` and wire `run_bac()`: immediately after each `bac_stage3.process(...)` call, compute the sibling QIF path (`out3_crc.with_suffix('.qif')` / `out3_usd.with_suffix('.qif')`) and call `qif_export.convert_csv_to_qif(out3_crc, qif_crc)` / `...(out3_usd, qif_usd)`; update the `[BAC] Done.` print line to also mention the `.qif` files. (Depends on T003.)
- [X] T005 [US1] In `scripts/orchestrator.py`, wire `run_davi()` the same way as T004: after each `davi_stage3.process(...)` call, call `qif_export.convert_csv_to_qif()` on the resulting `out3_crc` / `out3_usd` paths and update the `[DaviBank] Done.` print line. (Depends on T003.)
- [X] T006 [P] [US1] In `scripts/generate_expected_outputs.py`, import `qif_export` and extend `run_bac()` and `run_davi()`: after each `bac_stage3.process()` / `davi_stage3.process()` call, also call `qif_export.convert_csv_to_qif()` to write a sibling `{prefix}-out3-{currency}.qif` fixture, and add the new paths to each function's `for p in [...]` print/report list. (Depends on T003.)
- [X] T007 [US1] Run `python scripts/generate_expected_outputs.py` to generate the six expected QIF regression fixtures: `tests/fixtures/BAC Sample-out3-crc.qif`, `tests/fixtures/BAC Sample-out3-usd.qif`, `tests/fixtures/BAC Sample2-out3-crc.qif`, `tests/fixtures/BAC Sample2-out3-usd.qif`, `tests/fixtures/DaviBank Sample-out3-crc.qif`, `tests/fixtures/DaviBank Sample-out3-usd.qif`. Spot-check each file against its corresponding `-out3-*.csv` fixture (same row count, same order) before committing. (Depends on T006.)
- [X] T008 [P] [US1] In `tests/test_bac_pipeline.py`, add a `TestBACQIFExport` class (mirroring `TestBACStage3`'s `run_stages` fixture): for both CRC and USD, run `bac_stage3.process()` into a tmp CSV, then `qif_export.convert_csv_to_qif()` into a tmp QIF, and assert the result matches `tests/fixtures/BAC Sample-out3-crc.qif` / `-usd.qif` — same `!Type:Bank` header, same record count as CSV data rows, same date/payee/memo/amount values per record, in order. (Depends on T007.)
- [X] T009 [P] [US1] In `tests/test_davi_pipeline.py`, add a `TestDaviQIFExport` class following the same pattern as T008, asserting against `tests/fixtures/DaviBank Sample-out3-crc.qif` / `-usd.qif`. (Depends on T007.)

**Checkpoint**: User Story 1 is fully functional and independently testable — running the orchestrator on a sample file produces correct sibling `.qif` files for both pipelines and both currency splits.

---

## Phase 4: User Story 2 - Existing CSV output is untouched (Priority: P2)

**Goal**: Adding QIF export introduces zero regression to the existing `out3` CSV output.

**Independent Test**: Run the pipeline against the existing regression fixtures and diff the resulting `-out3-*.csv` files against the pre-feature fixtures; they must be identical.

### Tests for User Story 2

- [X] T010 [P] [US2] In `tests/test_bac_pipeline.py`, add a regression test that runs `bac_stage3.process()` followed by `qif_export.convert_csv_to_qif()` (as in T008) and then asserts the CSV output file's bytes are byte-for-byte identical to `tests/fixtures/BAC Sample-out3-crc.csv` / `-usd.csv` — proving QIF generation does not mutate or re-touch the CSV file (FR-010, SC-003).
- [X] T011 [P] [US2] In `tests/test_davi_pipeline.py`, add the same byte-for-byte CSV regression test as T010, using `tests/fixtures/DaviBank Sample-out3-crc.csv` / `-usd.csv`.

**Checkpoint**: User Stories 1 AND 2 both work independently — QIF files are produced correctly, and CSV output is provably unchanged.

---

## Phase 5: User Story 3 - Transactions with no memo or special characters export cleanly (Priority: P3)

**Goal**: Empty memos and payee/memo text containing commas, quotes, or embedded newlines produce well-formed QIF records with no data loss or corruption.

**Independent Test**: Feed `convert_csv_to_qif()` a CSV row with an empty memo and one with a comma/quote in the payee, and confirm the resulting QIF records are well-formed.

### Tests for User Story 3

- [X] T012 [P] [US3] In `tests/test_qif_export.py`, add a test: a CSV row with `Memo` = `""` produces a QIF record with `D`/`P`/`T`/`^` lines only — no `M` line is emitted at all (not an empty one) (FR-007, contract §1).
- [X] T013 [P] [US3] In `tests/test_qif_export.py`, add a test: a CSV row whose `Payee` contains a comma and a double quote (e.g. `AMAZON.COM, INC.`, matching the contract §2 example) is preserved verbatim on the `P` line with no escaping or truncation (FR-012, spec Acceptance Scenario US3.2).
- [X] T014 [P] [US3] In `tests/test_qif_export.py`, add a test: a CSV row whose `Payee` or `Memo` contains an embedded `\r\n`, `\r`, or `\n` is written with that sequence collapsed to a single space on its QIF line, and no other characters in the field are altered (FR-012, research.md §5).
- [X] T015 [P] [US3] In `tests/test_qif_export.py`, add a test: converting a CSV containing only the header row (zero data rows) produces a QIF file whose entire content is exactly `!Type:Bank\n` (FR-011, contract §1).

**Checkpoint**: All user stories are independently functional. T012–T015 validate edge-case behavior already implemented by T003's contract-complete `qif_export.py` — no additional production code is expected to be needed here; if any of T012–T015 fail, fix `scripts/qif_export.py` (T003) to match the contract rather than special-casing in the tests.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full-suite validation and manual sign-off

- [X] T016 [P] Run `pytest tests/test_qif_export.py tests/test_bac_pipeline.py tests/test_davi_pipeline.py -v` and confirm all tests (existing and new) pass.
- [X] T017 Follow `quickstart.md` manually: run `python scripts/orchestrator.py` against a real BAC `.csv` and DaviBank `.xlsx` statement, confirm the described `-out3-*.qif` files appear alongside the `-out3-*.csv` files, and `cat` one to eyeball the expected `!Type:Bank` / `D`/`P`/`T`/`^` structure.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A for this feature.
- **Foundational (Phase 2)**: N/A for this feature.
- **User Story 1 (Phase 3)**: No dependencies on other stories — this is the ground-floor implementation (`qif_export.py` + orchestrator wiring + fixtures).
- **User Story 2 (Phase 4)**: Depends on US1's T008/T009 pattern (reuses the same `bac_stage3.process()` → `qif_export.convert_csv_to_qif()` call shape) and on the fixtures from T007, but is a separate, independently-checkable assertion (CSV bytes unchanged) — no US1 test needs to pass for US2's claim to be meaningful, though in practice run after US1 is wired.
- **User Story 3 (Phase 5)**: Depends on T003 (`qif_export.py` existing) but not on orchestrator wiring (T004/T005) or fixtures (T007) — it tests the converter module directly with hand-built CSV inputs.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within User Story 1

- T001, T002 (tests) before T003 (implementation) — Constitution Principle III.
- T003 before T004, T005, T006 (all depend on `qif_export` existing).
- T006 before T007 (fixture generation needs the extended script).
- T007 before T008, T009 (pipeline tests compare against generated fixtures).

### Parallel Opportunities

- T001 and T002 can be written in parallel (same file, non-overlapping test functions — treat as logically parallel work, land together).
- T004, T005, T006 can proceed in parallel once T003 lands (different files: `orchestrator.py` twice — actually same file for T004/T005, so those two are sequential within `orchestrator.py`; T006 touches a different file and is safely parallel with T004/T005).
- T008 and T009 can run in parallel (different files) once T007 completes.
- T010 and T011 can run in parallel (different files).
- T012, T013, T014, T015 can all run in parallel (same file, independent test functions, no shared state).

---

## Parallel Example: User Story 1

```bash
# Tests first (write together):
Task: "Contract tests for convert_csv_to_qif header/order/date/amount in tests/test_qif_export.py"
Task: "Contract tests for return value and CSV-untouched in tests/test_qif_export.py"

# After T003 (qif_export.py) lands, these can proceed together:
Task: "Extend scripts/generate_expected_outputs.py to emit .qif fixtures"
# (orchestrator.py wiring for BAC and DaviBank is sequential — same file)

# After fixtures (T007) exist:
Task: "Add TestBACQIFExport to tests/test_bac_pipeline.py"
Task: "Add TestDaviQIFExport to tests/test_davi_pipeline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 3 (User Story 1): tests → `qif_export.py` → orchestrator wiring → fixtures → pipeline tests.
2. **STOP and VALIDATE**: run `pytest tests/test_qif_export.py tests/test_bac_pipeline.py::TestBACQIFExport tests/test_davi_pipeline.py::TestDaviQIFExport -v`; run the orchestrator by hand against a sample file per quickstart.md.
3. This alone satisfies the feature's core value (SC-001, SC-002).

### Incremental Delivery

1. User Story 1 → QIF files are produced correctly (MVP).
2. User Story 2 → byte-for-byte CSV regression proof added (SC-003) — cheap, additive, no new production code.
3. User Story 3 → edge-case regression tests added (empty memo, punctuation, newlines) — confirms the contract-complete T003 implementation handles them; no new production code expected.
4. Polish → full-suite run + manual quickstart walkthrough.

---

## Notes

- [P] tasks = different files, no dependencies (or independent functions within `tests/test_qif_export.py` where noted).
- [Story] label maps task to specific user story for traceability.
- This feature's constitution check (`plan.md`) found zero violations — no complexity tracking entries, no new dependency, no new CLI flag.
- Commit after each task or logical group.
- Stop at any checkpoint to validate the story independently.
