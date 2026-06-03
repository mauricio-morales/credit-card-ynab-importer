# Implementation Plan: Non-Technical User Setup Guide & GitHub Release Packaging

**Branch**: `003-install-docs-release` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-install-docs-release/spec.md`

## Summary

Deliver three artifacts that make the app distributable to non-technical users: a dual-platform setup guide (`GETTING_STARTED.md`), a Windows double-click launcher (`run_windows.bat`), a Mac double-click launcher (`run_mac.command`), and a GitHub Actions workflow that auto-packages and publishes a dated release zip on every merge to `main`. No changes to existing Python source code are required.

## Technical Context

**Language/Version**: Python 3.9+ (existing constraint from constitution; launchers target this floor)
**Primary Dependencies**: textual>=0.82.0, xlrd>=2.0.1, requests>=2.28 (no new deps introduced by this feature)
**Storage**: Files on disk; no database
**Testing**: pytest>=7.0 + pytest-asyncio>=0.23 (existing suite unchanged; new artifacts are manually verified per acceptance scenarios)
**Target Platform**: Windows 10+ and macOS 12+ (end-user distribution); ubuntu-latest (GitHub Actions packaging)
**Project Type**: CLI/TUI application — this feature adds distribution packaging and end-user documentation
**Performance Goals**: End-user can go from download link to running app in under 10 minutes (SC-001); GitHub Release published within 5 minutes of merge (SC-002)
**Constraints**: Release zip must be self-sufficient post-Python-install; no PyInstaller bundling; no internet required after initial setup; no system-level C compilers required
**Scale/Scope**: Personal-use tool targeting ~5 non-technical family members; single-developer maintenance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Pipeline-Stage Isolation** | ✅ PASS | No new pipeline stages added; existing 3-stage structure untouched |
| **II. YNAB Output Consistency** | ✅ PASS | No changes to pipeline output format |
| **III. Test-First** | ⚠️ JUSTIFIED EXCEPTION | Deliverables are shell scripts, Markdown, and CI/CD YAML — not Python code. Traditional pytest tests do not apply. Manual acceptance tests from spec (SC-001 through SC-005) serve as the verification protocol. |
| **IV. Data Fidelity** | ✅ PASS | No data transformation logic added or changed |
| **V. Simplicity (YAGNI)** | ✅ PASS | Launchers are the simplest possible scripts (install deps → run app). No bundling. No new abstractions. |

**Post-design re-check**: Required after Phase 1. Confirm the release workflow does not introduce hidden complexity (e.g., matrix builds, multi-Python versions) that violates Principle V.

## Project Structure

### Documentation (this feature)

```text
specs/003-install-docs-release/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
GETTING_STARTED.md       # New: non-technical setup guide (FR-001 through FR-013)
run_windows.bat          # New: Windows double-click launcher (FR-006)
run_mac.command          # New: Mac double-click launcher (FR-007, FR-008)
.github/
└── workflows/
    ├── tests.yml        # Existing: runs pytest on push/PR (unchanged)
    └── release.yml      # New: packages and publishes GitHub Release on merge to main
```

**Structure Decision**: Single-project layout. All new files live at the repository root (launchers and guide) and in `.github/workflows/` (CI/CD). No new source directories required.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle III exception (no automated tests for shell scripts) | `.bat` and `.command` files cannot be meaningfully unit-tested with pytest; GitHub Actions YAML is validated by GitHub's own schema checker | Writing a test that invokes a `.bat` or `.command` on CI would require Windows and macOS runners, adding cost and complexity disproportionate to the simplicity of the scripts (install deps + start app) |
