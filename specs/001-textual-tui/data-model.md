# Data Model: Textual TUI

**Phase**: 1 | **Feature**: `001-textual-tui` | **Date**: 2026-05-10

The TUI introduces no persistent storage. All entities are in-memory Python dataclasses or enums that flow through the screen lifecycle for a single conversion session.

---

## Entity: ConversionType

**Purpose**: Identifies which bank pipeline to run.

```python
from enum import Enum

class ConversionType(Enum):
    BAC = "bac"       # BAC CSV → YNAB CSV
    DAVI = "davi"     # DaviBank/Scotia XLS → YNAB CSV
```

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| value | str | Internal identifier used for display and routing |

**Rules**:
- `BAC` accepts only `.csv` files (FR-004)
- `DAVI` accepts only `.xls` / `.xlsx` files (FR-004)
- The welcome screen presents exactly these two options (FR-002)

---

## Entity: ConversionJob

**Purpose**: Carries the user's selection from WelcomeScreen through FilePickerScreen to ProgressScreen.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ConversionJob:
    conversion_type: ConversionType
    source_path: Path
```

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| conversion_type | ConversionType | Which pipeline to run |
| source_path | Path | Absolute path to the source file chosen by the user |

**Rules**:
- `source_path` must exist and be readable before the job is handed to ProgressScreen
- `source_path` is never modified or deleted at any point (FR-012)
- `source_path.parent` is where output files are written (FR-006)

**State transitions**:

```
[WelcomeScreen]
    user selects ConversionType
        ↓
[FilePickerScreen]
    user selects source_path → ConversionJob created
        ↓
[ProgressScreen]
    job consumed; ConversionResult produced
```

---

## Entity: ConversionResult

**Purpose**: Captures the outcome of a completed (or failed) conversion for display on SummaryScreen.

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ConversionResult:
    success: bool
    transaction_count: int
    output_files: list[Path]
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""
```

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| success | bool | `True` if all three pipeline stages completed without exception |
| transaction_count | int | Number of transaction rows processed by Stage 1 |
| output_files | list[Path] | Absolute paths to generated YNAB CSV files (out3-crc, out3-usd) |
| warnings | list[str] | Non-fatal issues (e.g., skipped rows, zero-amount rows) |
| error_message | str | Human-readable failure description when `success=False`; empty otherwise |

**Rules**:
- `output_files` is populated only when `success=True`
- `error_message` is populated only when `success=False`; it must be in plain language, no tracebacks (SC-004)
- `warnings` may be non-empty even when `success=True`
- `transaction_count` reflects Stage 1 output row count (the normalized CSV)

---

## Entity: ProgressUpdate (Textual Message)

**Purpose**: Carries incremental status text from the background worker thread to the ProgressScreen widget.

```python
from textual.message import Message

class ProgressUpdate(Message):
    def __init__(self, text: str, step: int, total_steps: int) -> None:
        super().__init__()
        self.text = text
        self.step = step
        self.total_steps = total_steps
```

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| text | str | Human-readable label for the current step (e.g., "Running Stage 1…") |
| step | int | Current step number (1-based) |
| total_steps | int | Total number of steps for this pipeline (BAC: 4, DaviBank: 4) |

**Rules**:
- BAC pipeline emits 4 steps: Stage 1, Stage 2, Stage 3-CRC, Stage 3-USD
- DaviBank pipeline emits 4 steps: Stage 1, Stage 2, Stage 3-CRC, Stage 3-USD
- `ProgressBar.update(progress=step/total_steps)` is called on each message receipt

---

## Screen-to-Entity Flow

```
WelcomeScreen
  └─ emits: ConversionType

FilePickerScreen (receives ConversionType)
  └─ emits: ConversionJob

ProgressScreen (receives ConversionJob)
  ├─ consumes: ProgressUpdate (stream from worker)
  └─ emits: ConversionResult

SummaryScreen (receives ConversionResult)
  └─ emits: (nothing — user presses "Convert Another" or "Quit")
```
