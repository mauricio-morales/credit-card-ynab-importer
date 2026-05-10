# Contract: Screen Flow

**Feature**: `001-textual-tui` | **Date**: 2026-05-10

Defines the navigation contract between all TUI screens: which screen follows which, what data is passed, and how back-navigation works.

---

## Screen Inventory

| Screen Class | File | Role |
|--------------|------|------|
| `WelcomeScreen` | `tui/screens/welcome.py` | Entry point; user picks conversion type |
| `FilePickerScreen` | `tui/screens/file_picker.py` | User browses and selects source file |
| `ProgressScreen` | `tui/screens/progress.py` | Runs conversion; shows live progress |
| `SummaryScreen` | `tui/screens/summary.py` | Shows result; offers next action |

---

## Navigation Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        WelcomeScreen                         │
│                                                              │
│  [ Convert BAC CSV ]      [ Convert Davi/Scotia XLS ]        │
└──────────────┬───────────────────────────────────────────────┘
               │ push_screen(FilePickerScreen, conversion_type)
               ▼
┌──────────────────────────────────────────────────────────────┐
│                      FilePickerScreen                        │
│                                                              │
│  [← Back]   DirectoryTree (filtered by extension)            │
│             [Select This File]                               │
└──────┬───────────────────────────────────────────────────────┘
       │ Esc / Back → pop_screen()  ──────────────────────────▶ WelcomeScreen
       │ Select → switch_screen(ProgressScreen, job)
       ▼
┌──────────────────────────────────────────────────────────────┐
│                       ProgressScreen                         │
│                                                              │
│  Converting: [filename]                                      │
│  ████████░░░░░░░░  Stage 2 of 4: Running Stage 2…            │
└──────┬───────────────────────────────────────────────────────┘
       │ Success → switch_screen(SummaryScreen, result)
       │ Failure → switch_screen(SummaryScreen, result{success=False})
       ▼
┌──────────────────────────────────────────────────────────────┐
│                       SummaryScreen                          │
│                                                              │
│  ✓ 47 transactions converted                                 │
│  Output: /path/to/file-out3-crc.csv                         │
│          /path/to/file-out3-usd.csv                         │
│                                                              │
│  [ Convert Another ]          [ Quit ]                       │
└──────┬───────────────────────────────────────────────────────┘
       │ "Convert Another" → switch_screen(WelcomeScreen)
       │ "Quit" → app.exit()
       ▼ (on error summary)
       │ "Try Again" → switch_screen(FilePickerScreen, same type)
       │ "Start Over" → switch_screen(WelcomeScreen)
```

---

## Screen Contracts

### WelcomeScreen

**Receives**: nothing (initial screen)
**Emits**: pushes `FilePickerScreen` with `conversion_type: ConversionType`
**Textual method**: `self.app.push_screen(FilePickerScreen(conversion_type))`
**Invariant**: always the first screen in the stack; never switched away from by others

---

### FilePickerScreen

**Constructor**: `FilePickerScreen(conversion_type: ConversionType)`
**Receives**: `ConversionType` to determine file filter
**Emits on confirm**: calls `self.app.switch_screen(ProgressScreen(job))` where `job = ConversionJob(conversion_type, selected_path)`
**Emits on back**: calls `self.app.pop_screen()` → returns to WelcomeScreen
**File filter rules**:

| ConversionType | Allowed extensions |
|----------------|--------------------|
| BAC | `.csv` |
| DAVI | `.xls`, `.xlsx` |

**Invariant**: `ConversionJob.source_path` is a file (not a directory) that passes the extension filter before `switch_screen` is called.

---

### ProgressScreen

**Constructor**: `ProgressScreen(job: ConversionJob)`
**Receives**: `ConversionJob` with validated source path
**Behavior**: starts `@work(thread=True, exclusive=True)` worker on mount; worker calls orchestrator stages and posts `ProgressUpdate` messages; screen handles `on_progress_update` to advance the progress bar and status label
**Emits on success**: `self.app.switch_screen(SummaryScreen(result))` where `result.success=True`
**Emits on failure**: `self.app.switch_screen(SummaryScreen(result))` where `result.success=False`
**Invariant**: worker runs to completion (or raises) before switching screen; no way to navigate away mid-conversion (keyboard navigation disabled during progress)

---

### SummaryScreen

**Constructor**: `SummaryScreen(result: ConversionResult)`
**Receives**: `ConversionResult`
**On success display**:
- Transaction count
- List of output file paths
- Any warnings (collapsible if >3 items)
- Buttons: "Convert Another", "Quit"

**On failure display**:
- Error message (plain language, no traceback)
- Buttons: "Try Again" (same file picker type), "Start Over" (welcome)

**Emits**:
- "Convert Another" / "Start Over" → `self.app.switch_screen(WelcomeScreen())`
- "Try Again" → `self.app.switch_screen(FilePickerScreen(original_type))`
- "Quit" → `self.app.exit()`

---

## Error Handling Contract

Any unhandled exception from the worker thread is caught in `ProgressScreen._run_conversion()`. The exception message is mapped to a plain-English string and wrapped in `ConversionResult(success=False, error_message=...)`. The screen then transitions to `SummaryScreen`. The original source file is verified to be unmodified after any failure.
