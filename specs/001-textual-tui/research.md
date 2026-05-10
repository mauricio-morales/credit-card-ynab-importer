# Research: Textual TUI Implementation

**Phase**: 0 | **Feature**: `001-textual-tui` | **Date**: 2026-05-10

## Decision 1: TUI Framework

**Decision**: Textual ≥0.82.0 (settled by user requirement)
**Rationale**: User explicitly specified Textual. It provides built-in widgets (DirectoryTree, ProgressBar, DataTable, Button, Label), a reactive data model, async worker support, and a first-class Pilot testing API — all needed for this feature.
**Alternatives considered**: `curses` (too low-level, poor UX for non-technical users), `prompt_toolkit` (dialog-style only, no file tree widget), `urwid` (no built-in testing support). All rejected.

## Decision 2: File Picker Approach

**Decision**: Subclass `DirectoryTree` and override `filter_paths()` to show only files with the expected extension (`.csv` for BAC, `.xls`/`.xlsx` for DaviBank). Pair with a `Label` showing the currently highlighted path and a `Button` to confirm.
**Rationale**: Textual has no built-in file picker widget. `DirectoryTree` is the closest native component; `filter_paths(paths: Iterable[Path]) -> Iterable[Path]` is the documented extension point. The `FileSelected` message fires when a leaf node is clicked/activated.
**Alternatives considered**: Using a plain `ListView` with manual `os.listdir` calls — rejected because DirectoryTree handles directory expansion, keyboard navigation, and path display natively.

## Decision 3: Background Conversion Worker

**Decision**: Use `@work(thread=True, exclusive=True)` to run the orchestrator on a background thread, with `self.call_from_thread(self.post_message, ProgressUpdate(...))` to stream progress back to the UI.
**Rationale**: The pipeline stages are CPU-bound synchronous Python; they cannot be `await`-ed. `thread=True` runs them on a `ThreadPoolExecutor`. `exclusive=True` ensures a second conversion cancels any running one. Progress messages are sent via `post_message` from the worker thread using `call_from_thread` — the documented safe pattern for thread → UI communication.
**Alternatives considered**: `asyncio.to_thread` directly — rejected because Textual's `@work` decorator integrates with the Worker lifecycle (cancel, state-changed events) and is the idiomatic approach.

## Decision 4: Screen Navigation Pattern

**Decision**: Use `switch_screen()` for all top-level transitions (Welcome → FilePicker → Progress → Summary → Welcome) to avoid building an unbounded stack. Use `pop_screen()` only for the "back" action from FilePicker to Welcome.
**Rationale**: `push_screen()` accumulates screens on a stack; repeatedly converting would grow it unboundedly. `switch_screen()` replaces the current screen. The only genuine "back" is from the file picker, where we want to preserve the welcome state on the stack — so FilePicker is `push_screen`'d from Welcome, and dismissed with `pop_screen`.
**Alternatives considered**: All `push_screen` — rejected because the stack grows on repeated conversions. All `switch_screen` — rejected because we'd lose the welcome screen state on back-navigation.

## Decision 5: Testing Strategy

**Decision**: Use `App.run_test()` → `Pilot` for headless async pytest tests. Each screen gets at least one test covering the happy path. Tests use `await pilot.press()`, `await pilot.click()`, and `await pilot.pause()`.
**Rationale**: `textual.testing` is the official test harness; it runs the full app in a headless terminal without requiring a real TTY. `asyncio_mode = "auto"` in `pytest.ini` (or `pyproject.toml`) enables async test functions. This satisfies Constitution Principle III (test-first) without external dependencies.
**Alternatives considered**: `pytest-textual-snapshot` for visual regression SVGs — deferred; useful after initial implementation but adds snapshot management overhead not needed for green/red TDD.

## Decision 6: Entry Point

**Decision**: Create `tui/__main__.py` so the app is launchable with `python -m tui` from the repository root. Also document a simple `run.py` shim at the repo root for users who don't know Python module syntax.
**Rationale**: `python -m tui` is idiomatic and doesn't require installation. Non-technical users can follow a one-liner instruction. A `run.py` shim (`import tui; tui.app.run()`) further reduces the barrier for users who might double-click or run `python run.py`.
**Alternatives considered**: `setuptools` entry point (`ynab-convert` command) — deferred; requires `pip install -e .` which is a heavier setup step for a personal-use tool.

## Resolved Unknowns

All NEEDS CLARIFICATION items resolved:

| Unknown | Resolution |
|---------|-----------|
| Textual min Python version | 3.9+ (0.82 series); constitution's 3.8 claim requires MINOR amendment |
| Built-in file picker | None; use `DirectoryTree` subclass with `filter_paths()` override |
| Progress reporting from thread | `call_from_thread(self.post_message, msg)` pattern |
| Screen stack management | `switch_screen` for main flow; `push/pop` for FilePicker back-navigation |
| Test approach | `App.run_test()` + `Pilot`; `asyncio_mode = "auto"` in pytest config |
