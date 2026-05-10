# Implementation Plan: Textual TUI for Credit Card Statement Converter

**Branch**: `001-textual-tui` | **Date**: 2026-05-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-textual-tui/spec.md`

## Summary

Add a Textual-based terminal user interface that guides non-technical users through converting BAC (CSV) or DaviBank/Scotia (XLS) credit card statements to YNAB-formatted CSVs. The TUI wraps the existing three-stage pipeline orchestrator without modifying it, presenting a **Welcome → File Picker → Progress → Summary** flow. All conversion logic remains in the existing `scripts/` modules; the TUI adds only a guided shell around them.

## Technical Context

**Language/Version**: Python 3.9+ (Textual requires 3.9; constitution declares 3.8+ — see Complexity Tracking)
**Primary Dependencies**: `textual>=0.82.0`, `xlrd>=2.0.1` (existing), `pytest>=7.0` (existing)
**Storage**: Files only — YNAB CSVs written adjacent to source file; no database
**Testing**: `pytest` + `textual.testing.Pilot` (async headless TUI tests)
**Target Platform**: macOS (primary); cross-platform terminal emulator compatible
**Project Type**: CLI/TUI desktop tool (launched from terminal)
**Performance Goals**: Conversion completes in <60s for 200 transactions (SC-001); existing pipeline already meets this
**Constraints**: Source file must never be modified (FR-012); output in same folder as source (FR-006); fully keyboard-navigable (FR-011)
**Scale/Scope**: Single user; two bank formats (BAC CSV, DaviBank XLS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Pipeline-Stage Isolation | ✅ PASS | TUI delegates to `orchestrator.py`; no stage coupling introduced |
| II. YNAB Output Consistency | ✅ PASS | Output format entirely owned by existing stages; TUI never touches output data |
| III. Test-First | ✅ PASS | TUI tests via Pilot API written before screens are implemented |
| IV. Data Fidelity | ✅ PASS | TUI passes file paths to orchestrator; no data transformation |
| V. Simplicity (YAGNI) | ⚠️ JUSTIFIED | Textual adds one new dependency; no abstractions beyond four screens |
| Technical Stack — "No GUI frameworks" | ⚠️ JUSTIFIED | Textual is a terminal (TUI) framework, not a windowed GUI. The constitution targets native OS GUI frameworks. This feature's entire purpose is a TUI; no simpler terminal approach satisfies the file-browser + progress UX requirements for non-technical users. Requires a MINOR constitution amendment adding Textual to the allowed stack. |

**Gate result**: PASS WITH JUSTIFICATION — deviations are documented in Complexity Tracking below and require a constitution MINOR amendment before implementation begins.

## Project Structure

### Documentation (this feature)

```
specs/001-textual-tui/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output (/speckit-plan)
├── data-model.md        # Phase 1 output (/speckit-plan)
├── e2e-tests.md         # E2E test specification (/speckit-plan)
├── quickstart.md        # Phase 1 output (/speckit-plan)
├── contracts/           # Phase 1 output (/speckit-plan)
│   ├── screen-flow.md
│   └── keyboard-nav.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```
tui/
├── __init__.py
├── app.py              # Main App class; registers screens; entry point
└── screens/
    ├── __init__.py
    ├── welcome.py      # WelcomeScreen — two-option conversion type selector
    ├── file_picker.py  # FilePickerScreen — filtered DirectoryTree + Confirm button
    ├── progress.py     # ProgressScreen — Worker thread + ProgressBar
    └── summary.py      # SummaryScreen — results table + "Convert Another" / Quit

scripts/
├── orchestrator.py     # Existing — no changes
├── bac_stage1.py       # Existing — no changes
├── bac_stage2.py       # Existing — no changes
├── bac_stage3.py       # Existing — no changes
├── davi_stage1.py      # Existing — no changes
├── davi_stage2.py      # Existing — no changes
└── davi_stage3.py      # Existing — no changes

tests/
├── test_bac_pipeline.py  # Existing — no changes
├── test_davi_pipeline.py # Existing — no changes
└── test_tui.py           # New — Pilot API integration tests for all screens

requirements.txt          # Add: textual>=0.82.0
```

**Structure Decision**: Single project layout. TUI code lives in `tui/` at the repository root alongside the existing `scripts/` directory, mirroring the existing flat layout. No `src/` restructure; no new packaging layer. The `tui/` module is invokable with `python -m tui`.

## Pipeline Fix: Amount Sign Inversion (FR-013)

The existing Stage 3 scripts write amounts verbatim from the source file. YNAB requires the opposite sign convention: positive source amounts (charges) must be negative in YNAB (outflow), and negative source amounts (payments/refunds) must be positive (inflow).

### Files to change

| File | Location | Change |
|------|----------|--------|
| `scripts/bac_stage3.py` | line 77 — `amount = dollars if use_dollars else local` | negate the amount string before writing |
| `scripts/davi_stage3.py` | line 73 — `amount = parts[3].strip()` | negate the amount string before writing |

### Negation helper (shared logic)

Both scripts need the same negation: parse the raw amount string as a float, multiply by -1, then reformat preserving the existing number-formatting rules (strip trailing `.00`, preserve meaningful decimals). A small helper function handles this:

```python
def negate_amount(raw: str) -> str:
    """Flip the sign of an amount string, preserving decimal precision."""
    raw = raw.strip().strip('"')
    try:
        value = -float(raw)
    except ValueError:
        return raw  # leave malformed amounts unchanged
    if value == int(value):
        return str(int(value))
    return str(value)
```

### Fixture files that must be regenerated

All Stage 3 expected output fixtures need regeneration after the fix (run `python scripts/generate_expected_outputs.py` or re-run each pipeline against the fixture inputs):

```
tests/fixtures/BAC Sample-out3-crc.csv
tests/fixtures/BAC Sample-out3-usd.csv
tests/fixtures/BAC Sample2-out3-crc.csv
tests/fixtures/BAC Sample2-out3-usd.csv
tests/fixtures/DaviBank Sample-out3-crc.csv
tests/fixtures/DaviBank Sample-out3-usd.csv
```

The `data/` directory output files (`*-out3-*.csv`) are derived outputs and will be regenerated when the user re-runs the tool.

### Constitution alignment

This fix brings Stage 3 into compliance with Constitution Principle II (YNAB Output Consistency). The constitution does not currently document the sign convention; a PATCH amendment to that principle should be added when this fix is implemented.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Textual dependency (new framework, "no GUI frameworks" principle) | Feature explicitly requires file-browser + progress + summary TUI for non-technical users (SC-003, FR-003–FR-008) | `argparse` CLI cannot satisfy file-browser UX; `curses` or `prompt_toolkit` require equivalent or more complexity for the same screens without Textual's built-in widgets |
| Python 3.9+ minimum (constitution says 3.8+) | Textual 0.82 requires Python 3.9; 3.8 reached EOL October 2024 | Pinning an older Textual version to keep 3.8 support would forgo worker improvements and file-widget stability; user's macOS ships with Python 3.9+ |
