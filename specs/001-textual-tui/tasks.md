# Tasks: Textual TUI for Credit Card Statement Converter

**Input**: Design documents from `/specs/001-textual-tui/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Test tasks are included — Constitution Principle III (test-first) is a mandatory gate per `plan.md` (TUI tests via Pilot API written before each screen is implemented).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Each description includes an exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependency, create package skeleton, and configure the async test runner.

- [ ] T001 Add `textual>=0.82.0` to `requirements.txt`
- [ ] T002 Create `tui/` package skeleton: `tui/__init__.py` and `tui/screens/__init__.py` (empty files establishing the module hierarchy)
- [ ] T003 [P] Create `tui/__main__.py` entry point: import `CreditCardConverterApp` from `tui.app` and call `.run()` so the tool launches with `python -m tui`
- [ ] T004 [P] Create `run.py` at repo root as a one-liner shim: `from tui.app import CreditCardConverterApp; CreditCardConverterApp().run()`
- [ ] T005 [P] Add `asyncio_mode = "auto"` to `pytest.ini` (create if absent) so all async Pilot tests run without manual `@pytest.mark.asyncio` decoration

**Checkpoint**: Package importable, `python -m tui` path resolves, pytest accepts async tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data model, app shell, and pipeline sign-inversion fix (FR-013) that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Create `tui/models.py` with `ConversionType(Enum)`, `ConversionJob(dataclass)`, `ConversionResult(dataclass)`, and `ProgressUpdate(Message)` exactly as specified in `specs/001-textual-tui/data-model.md`
- [ ] T007 Create `tui/app.py` with `CreditCardConverterApp(App)` class: global `BINDINGS = [("ctrl+c", "quit", "Quit")]`, and `on_mount` that calls `self.push_screen(WelcomeScreen())` as the initial screen (import guard needed to avoid circular import with screens)
- [ ] T008 Fix amount sign inversion in `scripts/bac_stage3.py`: add `negate_amount(raw: str) -> str` helper (as specified in `plan.md` § "Pipeline Fix") and apply it to the amount assignment at line 77 (FR-013)
- [ ] T009 [P] Fix amount sign inversion in `scripts/davi_stage3.py`: add `negate_amount(raw: str) -> str` helper and apply it to the amount assignment at line 73 (FR-013)
- [ ] T010 Regenerate Stage 3 fixture files after the sign-inversion fix by re-running the pipeline against fixture inputs (`tests/fixtures/BAC Sample-out3-crc.csv`, `tests/fixtures/BAC Sample-out3-usd.csv`, `tests/fixtures/BAC Sample2-out3-crc.csv`, `tests/fixtures/BAC Sample2-out3-usd.csv`, `tests/fixtures/DaviBank Sample-out3-crc.csv`, `tests/fixtures/DaviBank Sample-out3-usd.csv`) and confirm existing pipeline tests pass with `pytest tests/test_bac_pipeline.py tests/test_davi_pipeline.py`

**Checkpoint**: Foundation ready — data model exists, app shell boots, pipeline produces sign-inverted amounts, all existing tests pass. User story implementation can now begin.

---

## Phase 3: User Story 1 — Convert BAC Statement to YNAB (Priority: P1) 🎯 MVP

**Goal**: Full 4-screen TUI flow (Welcome → FilePicker → Progress → Summary) working end-to-end for BAC CSV conversion, output file placed next to source.

**Independent Test**: Run `python -m tui`, press `1`, navigate to a BAC CSV fixture, press Tab → Enter to confirm, watch progress bar advance through 4 stages, confirm summary displays transaction count and two output file paths, verify YNAB CSV files appear in the source folder.

### Tests for User Story 1 (TDD — write first, verify they fail, then implement)

- [ ] T011 [P] [US1] Write failing Pilot test `test_welcome_screen_bac_flow` in `tests/test_tui.py`: assert two buttons are visible, `1` key activates BAC button and transitions to `FilePickerScreen`, footer shows expected bindings
- [ ] T012 [P] [US1] Write failing Pilot test `test_file_picker_bac` in `tests/test_tui.py`: assert `FilePickerScreen` shows only `.csv` files, "Select This File" button triggers switch to `ProgressScreen`, `Escape` pops back to `WelcomeScreen`
- [ ] T013 [P] [US1] Write failing Pilot test `test_progress_screen_bac` in `tests/test_tui.py`: mock orchestrator stages, assert `ProgressBar` advances on each `ProgressUpdate` message, screen transitions to `SummaryScreen` after worker completes
- [ ] T014 [P] [US1] Write failing Pilot test `test_summary_screen_success` in `tests/test_tui.py`: construct a successful `ConversionResult`, assert transaction count and output paths are displayed, `c` key switches to `WelcomeScreen`, `q` key calls `app.exit()`

### Implementation for User Story 1

- [ ] T015 [US1] Implement `WelcomeScreen` in `tui/screens/welcome.py`: `BINDINGS = [("1", ...), ("2", ...), ("q", "quit")]`, two `Button` widgets labelled per spec, `on_button_pressed` calling `self.app.push_screen(FilePickerScreen(conversion_type))` per `specs/001-textual-tui/contracts/screen-flow.md`
- [ ] T016 [US1] Implement `FilteredDirectoryTree(DirectoryTree)` in `tui/screens/file_picker.py`: constructor accepts `allowed_extensions: set[str]`, overrides `filter_paths(paths)` to yield only paths whose suffix (lowercased) is in `allowed_extensions` or whose `is_dir()` is True
- [ ] T017 [US1] Implement `FilePickerScreen` in `tui/screens/file_picker.py`: embeds `FilteredDirectoryTree` with `{".csv"}` for BAC, a `Label` showing the currently highlighted file path, a "Select This File" `Button` (disabled until a file is highlighted), `BINDINGS = [("escape", "go_back"), ("b", "go_back")]`, back action calls `self.app.pop_screen()`, confirm action builds `ConversionJob` and calls `self.app.switch_screen(ProgressScreen(job))`
- [ ] T018 [US1] Implement `ProgressScreen` in `tui/screens/progress.py`: `BINDINGS = []`, `ProgressBar` widget, status `Label`, `@work(thread=True, exclusive=True)` method `_run_conversion` that calls BAC orchestrator pipeline stages and posts `ProgressUpdate(text, step, total_steps=4)` via `self.call_from_thread(self.post_message, ...)` after each stage; `on_progress_update` handler advances bar and label; on completion calls `self.app.switch_screen(SummaryScreen(result))`
- [ ] T019 [US1] Implement `SummaryScreen` success view in `tui/screens/summary.py`: displays `ConversionResult.transaction_count`, iterates `output_files` as `Label` rows, lists `warnings`, `BINDINGS = [("c", "convert_another"), ("q", "quit")]`, "Convert Another" button calls `self.app.switch_screen(WelcomeScreen())`, "Quit" button calls `self.app.exit()`
- [ ] T020 [US1] Update `tui/app.py` to import and register all four screens, then run `python -m tui` manually and walk through the BAC happy path with a real or fixture CSV to confirm end-to-end flow works

**Checkpoint**: User Story 1 is fully functional and testable independently. `pytest tests/test_tui.py::test_welcome_screen_bac_flow tests/test_tui.py::test_file_picker_bac tests/test_tui.py::test_progress_screen_bac tests/test_tui.py::test_summary_screen_success` all pass.

---

## Phase 4: User Story 2 — Convert Davi/Scotia Statement to YNAB (Priority: P1)

**Goal**: Same 4-screen flow works for Davi/Scotia XLS conversion with XLS-only file filtering and the Davi pipeline stages.

**Independent Test**: Run `python -m tui`, press `2`, browse to a Davi XLS fixture, confirm selection, watch progress, confirm summary shows transaction count and output YNAB CSV paths, verify files appear next to original XLS.

### Tests for User Story 2

- [ ] T021 [US2] Write failing Pilot test `test_davi_full_flow` in `tests/test_tui.py`: `2` key activates Davi option, `FilePickerScreen` shows only `.xls`/`.xlsx` files (no `.csv`), mocked Davi pipeline stages complete, `SummaryScreen` shows success with correct output paths

### Implementation for User Story 2

- [ ] T022 [US2] Extend `ProgressScreen._run_conversion()` in `tui/screens/progress.py` to branch on `job.conversion_type == ConversionType.DAVI` and call Davi orchestrator stages (`davi_stage1`, `davi_stage2`, `davi_stage3`) posting four `ProgressUpdate` messages identical in structure to BAC
- [ ] T023 [US2] Verify `FilteredDirectoryTree` in `tui/screens/file_picker.py` passes `{".xls", ".xlsx"}` when `ConversionType.DAVI` is passed to `FilePickerScreen` — confirm BAC and Davi paths both use the same `FilteredDirectoryTree` class with the correct extension set

**Checkpoint**: User Stories 1 and 2 both work independently. `pytest tests/test_tui.py::test_davi_full_flow` passes alongside all US1 tests.

---

## Phase 5: User Story 3 — Handle Conversion Errors Gracefully (Priority: P2)

**Goal**: Wrong file type, malformed file, and read/write errors produce plain-language error messages. User can retry or start over without restarting. Source file is never modified.

**Independent Test**: Select a non-CSV file (or a truncated/corrupted fixture) with the BAC option active; confirm `SummaryScreen` shows a plain-language error message (no traceback), "Try Again" returns to `FilePickerScreen`, "Start Over" returns to `WelcomeScreen`, and the original file is unchanged.

### Tests for User Story 3

- [ ] T024 [US3] Write failing Pilot test `test_error_recovery_flow` in `tests/test_tui.py`: mock orchestrator to raise `Exception("bad file")`, assert `SummaryScreen` shows error message text (no traceback), `r` key switches to `FilePickerScreen`, `s` key switches to `WelcomeScreen`, "Try Again" button also works via click

### Implementation for User Story 3

- [ ] T025 [US3] Add exception handler in `ProgressScreen._run_conversion()` in `tui/screens/progress.py`: wrap all orchestrator calls in `try/except Exception as e`, record `source_path.stat().st_size` before running, verify size unchanged after exception, produce `ConversionResult(success=False, error_message=plain_english(e))` and call `self.app.switch_screen(SummaryScreen(result))` (no traceback in message — SC-004)
- [ ] T026 [US3] Implement `SummaryScreen` error view in `tui/screens/summary.py`: conditionally render error `Label` when `result.success == False`, add "Try Again" button that calls `self.app.switch_screen(FilePickerScreen(original_type))` (store `original_type` in result or pass separately), add "Start Over" button calling `self.app.switch_screen(WelcomeScreen())`, extend `BINDINGS` with `r` (try again) and `s` (start over) per `specs/001-textual-tui/contracts/keyboard-nav.md`
- [ ] T027 [US3] Add empty-directory guard in `FilePickerScreen` in `tui/screens/file_picker.py`: disable "Select This File" button when no file is highlighted in `DirectoryTree`, show a dimmed `Label` "No matching files in this folder" if the tree has no visible leaf nodes matching the filter

**Checkpoint**: All three user stories are independently functional and testable. `pytest tests/test_tui.py` passes in full.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, keyboard contract audit, and constitution amendment.

- [ ] T028 [P] Run complete test suite `pytest tests/` and confirm all pipeline tests and TUI tests pass together (no regressions from sign-inversion fix or screen imports)
- [ ] T029 [P] Walk through `specs/001-textual-tui/quickstart.md` step-by-step with `python -m tui` using a real BAC CSV and a real Davi XLS to validate the user-facing narrative matches actual behavior
- [ ] T030 [P] Audit keyboard bindings: verify every key listed in `specs/001-textual-tui/contracts/keyboard-nav.md` has a matching `BINDINGS` entry in the correct screen class (`welcome.py`, `file_picker.py`, `progress.py`, `summary.py`); confirm footer legend renders them
- [ ] T031 Add a PATCH amendment to the project constitution documenting Python 3.9+ minimum and Textual as an allowed terminal UI framework, per the justified deviations in `specs/001-textual-tui/plan.md` § "Constitution Check"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **User Stories (Phases 3–5)**: All depend on Foundational phase
  - US1 (Phase 3) and US2 (Phase 4) are both P1; US2 extends US1's screens so US1 should be completed first
  - US3 (Phase 5) can start after US1 (error views extend the same SummaryScreen)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — builds the entire screen skeleton
- **US2 (P1)**: Depends on US1 screens existing (extends ProgressScreen and verifies FilteredDirectoryTree parameterization) — start after US1 checkpoint
- **US3 (P2)**: Depends on US1 (adds error branch to ProgressScreen and SummaryScreen) — start after US1 checkpoint

### Within Each User Story

- Tests MUST be written and confirmed failing before implementing each screen
- `tui/models.py` (T006) before any screen
- `tui/app.py` (T007) before screen registration (T020)
- `FilteredDirectoryTree` (T016) before `FilePickerScreen` (T017)
- `ProgressScreen` (T018) before `SummaryScreen` (T019) — result flows from Progress to Summary

### Parallel Opportunities

- T003, T004, T005 can run in parallel (different files, no deps)
- T008, T009 can run in parallel (different pipeline scripts)
- T011, T012, T013, T014 can be written in parallel (all write to `tests/test_tui.py` but target different test functions — coordinate to avoid conflicts)
- T021 (US2 test) can start as soon as T011–T014 pattern is established
- T028, T029, T030 can run in parallel in the polish phase

---

## Parallel Example: User Story 1 Test Writing (T011–T014)

```bash
# All four test functions can be drafted simultaneously in tests/test_tui.py:
Task: test_welcome_screen_bac_flow   # T011
Task: test_file_picker_bac           # T012
Task: test_progress_screen_bac       # T013
Task: test_summary_screen_success    # T014
```

## Parallel Example: Pipeline Fix (T008–T009)

```bash
# Sign-inversion fix is independent per pipeline script:
Task: Fix scripts/bac_stage3.py      # T008
Task: Fix scripts/davi_stage3.py     # T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `pytest tests/test_tui.py`, walk through `quickstart.md` BAC path
5. Ship/demo the BAC flow as MVP

### Incremental Delivery

1. Setup + Foundational → package boots, pipeline produces correct signs
2. User Story 1 → BAC end-to-end TUI works → MVP demo
3. User Story 2 → Davi/Scotia flow works → both converters available
4. User Story 3 → error handling added → production-ready robustness
5. Polish → all tests green, quickstart validated, constitution updated

---

## Notes

- **[P]** = different files or functions, no blocking dependencies between them
- **[Story]** label maps each task to its user story for traceability
- Tests use `textual.testing.Pilot` via `App.run_test()` with `asyncio_mode = "auto"` in pytest config
- The existing `scripts/orchestrator.py` is called by `ProgressScreen._run_conversion()` — never modified
- Source files are read-only throughout (FR-012): never pass the source path to anything that opens it for writing
- `switch_screen` for Welcome → Progress → Summary → Welcome; `push_screen`/`pop_screen` only for FilePicker back-navigation (research.md Decision 4)
- Commit after each phase checkpoint to keep history clean and reversible
