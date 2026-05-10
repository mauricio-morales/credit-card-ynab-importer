# E2E Test Specification: Textual TUI Happy Paths

**Feature**: `001-textual-tui` | **Date**: 2026-05-10
**Relates to**: [screen-flow.md](contracts/screen-flow.md), [data-model.md](data-model.md)

---

## Overview

End-to-end tests drive the full TUI application through real screens using Textual's `Pilot` API. They use copies of the existing fixture files placed in a temporary directory, run all four pipeline stages, and assert that the correct YNAB output files are created alongside the source file.

These tests complement (and are distinct from) the existing pipeline unit tests in `tests/test_bac_pipeline.py` and `tests/test_davi_pipeline.py`:

| Layer | File | What it tests |
|-------|------|---------------|
| Unit | `tests/test_bac_pipeline.py` | Each stage script in isolation |
| Unit | `tests/test_davi_pipeline.py` | Each stage script in isolation |
| **E2E** | **`tests/test_tui_e2e.py`** | **Full TUI screen flow + file output** |

---

## Test Infrastructure

### Required additions before writing tests (test-first order)

1. `FilePickerScreen` must accept an `initial_dir: Path` constructor argument (defaults to `Path.home()`). Tests pass the temp directory as `initial_dir` to avoid navigating the full filesystem.
2. `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`) must set `asyncio_mode = "auto"`.
3. `textual` must be in `requirements.txt` (already planned).

### Fixture helper (conftest.py additions)

```python
@pytest.fixture
def bac_input_copy(tmp_path):
    """Copy BAC Sample-in.csv to a temp dir; return the copy's path."""
    src = FIXTURES_DIR / "BAC Sample-in.csv"
    dst = tmp_path / "BAC Sample-in.csv"
    dst.write_bytes(src.read_bytes())
    return dst

@pytest.fixture
def davi_input_copy(tmp_path):
    """Copy DaviBank Sample-in.xls to a temp dir; return the copy's path."""
    src = FIXTURES_DIR / "DaviBank Sample-in.xls"
    dst = tmp_path / "DaviBank Sample-in.xls"
    dst.write_bytes(src.read_bytes())
    return dst
```

---

## Happy Path 1: BAC CSV Conversion

**Scenario**: User converts a BAC CSV file from start to finish.
**Fixture source**: `tests/fixtures/BAC Sample-in.csv`
**Expected CRC output**: 74 transactions (matches `BAC Sample-out3-crc.csv`)
**Expected USD output**: row count matches `BAC Sample-out3-usd.csv`
**Test file**: `tests/test_tui_e2e.py::test_bac_happy_path`

### Steps

```
1. App launches → WelcomeScreen is visible
2. Press '1' (or click BAC button) → FilePickerScreen opens
3. FilePickerScreen shows only .csv files from initial_dir
4. Navigate to and activate "BAC Sample-in.csv"
5. Press Tab to focus "Select This File", press Enter
6. ProgressScreen appears; worker runs all 4 BAC stages
7. Progress bar advances through steps 1 → 4
8. SummaryScreen appears with success result
9. Press 'q' → app exits
```

### Assertions

| # | What to assert | How |
|---|----------------|-----|
| A1 | WelcomeScreen is the initial screen | `assert isinstance(app.screen, WelcomeScreen)` |
| A2 | FilePickerScreen appears after BAC selection | `assert isinstance(app.screen, FilePickerScreen)` |
| A3 | FilePickerScreen filter shows only `.csv` files | no `.xls` entries visible in the DirectoryTree |
| A4 | ProgressScreen appears after file selection | `assert isinstance(app.screen, ProgressScreen)` |
| A5 | SummaryScreen appears after completion | `assert isinstance(app.screen, SummaryScreen)` |
| A6 | `result.success` is `True` | read from `SummaryScreen.result` |
| A7 | CRC output file exists | `(tmp_path / "BAC Sample-out3-crc.csv").exists()` |
| A8 | USD output file exists | `(tmp_path / "BAC Sample-out3-usd.csv").exists()` |
| A9 | CRC output matches expected fixture | `parse_ynab_rows(out3_crc) == parse_ynab_rows(FIXTURES_DIR / "BAC Sample-out3-crc.csv")` |
| A10 | USD output matches expected fixture | same comparison for USD |
| A11 | Source file is unmodified | `bac_input_copy.read_bytes() == (FIXTURES_DIR / "BAC Sample-in.csv").read_bytes()` |
| A12 | `result.transaction_count` matches Stage 1 output row count | count rows in generated `BAC Sample-out1.csv` |

---

## Happy Path 2: DaviBank XLS Conversion

**Scenario**: User converts a DaviBank XLS file from start to finish.
**Fixture source**: `tests/fixtures/DaviBank Sample-in.xls`
**Expected CRC output**: 23 transactions (matches `DaviBank Sample-out3-crc.csv`)
**Expected USD output**: row count matches `DaviBank Sample-out3-usd.csv`
**Test file**: `tests/test_tui_e2e.py::test_davi_happy_path`

### Steps

```
1. App launches → WelcomeScreen is visible
2. Press '2' (or click Davi/Scotia button) → FilePickerScreen opens
3. FilePickerScreen shows only .xls / .xlsx files from initial_dir
4. Navigate to and activate "DaviBank Sample-in.xls"
5. Press Tab to focus "Select This File", press Enter
6. ProgressScreen appears; worker runs all 4 DaviBank stages
7. SummaryScreen appears with success result
8. Press 'q' → app exits
```

### Assertions

| # | What to assert | How |
|---|----------------|-----|
| A1 | WelcomeScreen is the initial screen | `assert isinstance(app.screen, WelcomeScreen)` |
| A2 | FilePickerScreen appears after Davi selection | `assert isinstance(app.screen, FilePickerScreen)` |
| A3 | FilePickerScreen filter shows only `.xls`/`.xlsx` files | no `.csv` entries visible |
| A4 | SummaryScreen appears after completion | `assert isinstance(app.screen, SummaryScreen)` |
| A5 | `result.success` is `True` | read from `SummaryScreen.result` |
| A6 | CRC output file exists | `(tmp_path / "DaviBank Sample-out3-crc.csv").exists()` |
| A7 | USD output file exists | `(tmp_path / "DaviBank Sample-out3-usd.csv").exists()` |
| A8 | CRC output matches expected fixture | `parse_ynab_rows` comparison |
| A9 | USD output matches expected fixture | `parse_ynab_rows` comparison |
| A10 | Source file is unmodified | byte-for-byte comparison with original `.xls` |

---

## Happy Path 3: Convert Another (chained conversion)

**Scenario**: User completes a BAC conversion, presses "Convert Another", and successfully completes a second DaviBank conversion without restarting the app.
**Test file**: `tests/test_tui_e2e.py::test_convert_another_flow`

### Steps

```
1. App launches → WelcomeScreen
2. Select BAC, pick bac_input_copy, run to SummaryScreen
3. Press 'c' ("Convert Another") → WelcomeScreen reappears
4. Select Davi/Scotia, pick davi_input_copy
5. Progress runs → SummaryScreen for DaviBank
6. Press 'q' → app exits
```

### Assertions

| # | What to assert | How |
|---|----------------|-----|
| A1 | After 'c' press, screen is WelcomeScreen again | `assert isinstance(app.screen, WelcomeScreen)` |
| A2 | No screen stack leak — only one screen on stack | `len(app.screen_stack) == 1` |
| A3 | DaviBank CRC output file exists in davi_input_copy's parent | file existence check |
| A4 | Both conversion result summaries showed `success=True` | captured from each SummaryScreen pass |

---

## Test File Skeleton

The following skeleton defines the structure that `tests/test_tui_e2e.py` must implement. Tests are written **before** the corresponding screen is implemented (Constitution Principle III).

```python
"""E2E tests: full TUI screen flow using Textual Pilot."""
import pytest
from pathlib import Path
from tui.app import CreditCardConverterApp
from tui.screens.welcome import WelcomeScreen
from tui.screens.file_picker import FilePickerScreen
from tui.screens.progress import ProgressScreen
from tui.screens.summary import SummaryScreen
from tests.conftest import FIXTURES_DIR, parse_ynab_rows


async def test_bac_happy_path(bac_input_copy):
    """BAC CSV → YNAB: full TUI flow produces correct output files."""
    tmp_dir = bac_input_copy.parent
    async with CreditCardConverterApp(initial_dir=tmp_dir).run_test() as pilot:
        # A1: starts on WelcomeScreen
        assert isinstance(pilot.app.screen, WelcomeScreen)

        # Step: select BAC
        await pilot.press("1")
        await pilot.pause()

        # A2: FilePickerScreen opens
        assert isinstance(pilot.app.screen, FilePickerScreen)

        # Step: select file + confirm
        # (implementation detail: activate the file node, then Tab + Enter)
        await pilot.app.screen.select_file(bac_input_copy)  # test helper method
        await pilot.pause()

        # A4: ProgressScreen
        assert isinstance(pilot.app.screen, ProgressScreen)
        await pilot.pause(delay=10.0)  # allow worker to complete

        # A5: SummaryScreen
        assert isinstance(pilot.app.screen, SummaryScreen)
        result = pilot.app.screen.result

        # A6–A12: output assertions
        assert result.success is True
        crc = tmp_dir / "BAC Sample-out3-crc.csv"
        usd = tmp_dir / "BAC Sample-out3-usd.csv"
        assert crc.exists()
        assert usd.exists()
        assert parse_ynab_rows(crc) == parse_ynab_rows(
            FIXTURES_DIR / "BAC Sample-out3-crc.csv"
        )
        assert parse_ynab_rows(usd) == parse_ynab_rows(
            FIXTURES_DIR / "BAC Sample-out3-usd.csv"
        )
        src_bytes = bac_input_copy.read_bytes()
        assert src_bytes == (FIXTURES_DIR / "BAC Sample-in.csv").read_bytes()

        await pilot.press("q")


async def test_davi_happy_path(davi_input_copy):
    """DaviBank XLS → YNAB: full TUI flow produces correct output files."""
    tmp_dir = davi_input_copy.parent
    async with CreditCardConverterApp(initial_dir=tmp_dir).run_test() as pilot:
        assert isinstance(pilot.app.screen, WelcomeScreen)

        await pilot.press("2")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FilePickerScreen)

        await pilot.app.screen.select_file(davi_input_copy)
        await pilot.pause()

        assert isinstance(pilot.app.screen, ProgressScreen)
        await pilot.pause(delay=10.0)

        assert isinstance(pilot.app.screen, SummaryScreen)
        result = pilot.app.screen.result

        assert result.success is True
        crc = tmp_dir / "DaviBank Sample-out3-crc.csv"
        usd = tmp_dir / "DaviBank Sample-out3-usd.csv"
        assert crc.exists()
        assert usd.exists()
        assert parse_ynab_rows(crc) == parse_ynab_rows(
            FIXTURES_DIR / "DaviBank Sample-out3-crc.csv"
        )
        src_bytes = davi_input_copy.read_bytes()
        assert src_bytes == (FIXTURES_DIR / "DaviBank Sample-in.xls").read_bytes()

        await pilot.press("q")


async def test_convert_another_flow(bac_input_copy, davi_input_copy):
    """After converting BAC, 'Convert Another' returns to WelcomeScreen for a second conversion."""
    bac_dir = bac_input_copy.parent
    davi_dir = davi_input_copy.parent
    async with CreditCardConverterApp(initial_dir=bac_dir).run_test() as pilot:
        # First conversion: BAC
        await pilot.press("1")
        await pilot.pause()
        await pilot.app.screen.select_file(bac_input_copy)
        await pilot.pause()
        await pilot.pause(delay=10.0)
        assert isinstance(pilot.app.screen, SummaryScreen)
        assert pilot.app.screen.result.success is True

        # A1: back to WelcomeScreen
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WelcomeScreen)

        # A2: no screen stack leak
        assert len(pilot.app.screen_stack) == 1

        # Second conversion: DaviBank
        pilot.app.screen_stack[0]._initial_dir = davi_dir  # update dir for second pick
        await pilot.press("2")
        await pilot.pause()
        await pilot.app.screen.select_file(davi_input_copy)
        await pilot.pause()
        await pilot.pause(delay=10.0)
        assert isinstance(pilot.app.screen, SummaryScreen)
        assert pilot.app.screen.result.success is True

        await pilot.press("q")
```

> **Implementation note**: `FilePickerScreen.select_file(path)` is a test-only helper method that programmatically sets the selected path and fires the confirmation, bypassing DirectoryTree navigation. It must be a no-op guard when called outside test mode (i.e., only usable in `run_test()` context).

---

## Acceptance Criteria Traceability

| Acceptance scenario (spec.md) | Covered by |
|-------------------------------|-----------|
| US1-AC1: welcome screen shows two options | `test_bac_happy_path` A1 |
| US1-AC2: BAC picker shows only CSV files | `test_bac_happy_path` A3 |
| US1-AC3: progress shown during conversion | `test_bac_happy_path` A4 |
| US1-AC4: summary shows transaction count + output path | `test_bac_happy_path` A5, A6, A12 |
| US1-AC5: output file in source folder | `test_bac_happy_path` A7, A8 |
| US2-AC1: Davi picker shows only XLS files | `test_davi_happy_path` A3 |
| US2-AC2: progress shown for DaviBank | `test_davi_happy_path` A4 |
| US2-AC3: summary for DaviBank | `test_davi_happy_path` A5 |
| US2-AC4: DaviBank output in source folder | `test_davi_happy_path` A6, A7 |
| FR-012: source file never modified | `test_bac_happy_path` A11, `test_davi_happy_path` A10 |
| FR-009: return to welcome without restart | `test_convert_another_flow` A1 |
| SC-002: output matches existing pipeline output exactly | `test_bac_happy_path` A9, A10; `test_davi_happy_path` A8 |
