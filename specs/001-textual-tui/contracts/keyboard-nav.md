# Contract: Keyboard Navigation

**Feature**: `001-textual-tui` | **Date**: 2026-05-10

Defines all keyboard bindings for the TUI. Every action must be reachable by keyboard without a mouse (FR-011, SC-005).

---

## Global Bindings (all screens)

| Key | Action |
|-----|--------|
| `ctrl+c` | Quit application immediately |

---

## WelcomeScreen Bindings

| Key | Action |
|-----|--------|
| `Tab` | Move focus between the two conversion option buttons |
| `Enter` / `Space` | Activate focused button → open FilePickerScreen |
| `1` | Shortcut: select BAC option |
| `2` | Shortcut: select Davi/Scotia option |
| `q` | Quit application |

---

## FilePickerScreen Bindings

| Key | Action |
|-----|--------|
| `Up` / `Down` | Navigate items in the DirectoryTree |
| `Right` / `Enter` | Expand directory / select file (native DirectoryTree behaviour) |
| `Left` | Collapse directory (native DirectoryTree behaviour) |
| `Tab` | Move focus between DirectoryTree and the "Select This File" button |
| `Enter` (button focused) | Confirm file selection → go to ProgressScreen |
| `Escape` | Go back to WelcomeScreen |
| `b` | Go back to WelcomeScreen (mnemonic alias for Escape) |

---

## ProgressScreen Bindings

All navigation keys are **disabled** during conversion to prevent accidental interruption.

| Key | Action |
|-----|--------|
| _(none enabled)_ | Conversion runs to completion before any key press is accepted |

Note: `ctrl+c` still quits the process at the OS level, which is acceptable — the worker thread is daemon-based and will be terminated.

---

## SummaryScreen Bindings (success)

| Key | Action |
|-----|--------|
| `Tab` | Move focus between "Convert Another" and "Quit" buttons |
| `Enter` / `Space` | Activate focused button |
| `c` | Shortcut: "Convert Another" → WelcomeScreen |
| `q` | Shortcut: Quit application |

---

## SummaryScreen Bindings (error)

| Key | Action |
|-----|--------|
| `Tab` | Move focus between "Try Again" and "Start Over" buttons |
| `Enter` / `Space` | Activate focused button |
| `r` | Shortcut: "Try Again" → FilePickerScreen (same conversion type) |
| `s` | Shortcut: "Start Over" → WelcomeScreen |

---

## Implementation Notes

- Bindings are declared via `BINDINGS` class variable on each Screen subclass (Textual convention)
- The footer bar automatically renders active bindings as a help legend at the bottom of the screen
- `ProgressScreen` sets `BINDINGS = []` to suppress the footer during conversion
- All bindings use lowercase letters to avoid conflicts with system shortcuts
