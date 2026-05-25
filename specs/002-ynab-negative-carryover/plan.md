# Implementation Plan: Monthly Overspend Cascade

**Branch**: `002-ynab-negative-carryover` | **Date**: 2026-05-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-ynab-negative-carryover/spec.md`

## Summary

Automate YNAB's "carryover tuplet" technique: for each past month with over-spent budget categories, create a pair of internal loan account transactions that zero the category at month-end and re-apply the deficit at month-start. Multiple affected months are processed one at a time through a month-by-month confirmation wizard built in the existing Textual TUI. A setup wizard (API key → budget selection → loan account selection) is shown when first accessing the feature or when accessing a budget that has not yet been configured; each budget stores its own loan account ID. CSV conversion continues to work without any YNAB configuration.

The technical approach: on-demand YNAB API client backed by `requests`, config stored in `~/.config/credit-card-ynab-importer/config.json`, each month's plan derived from a live YNAB re-fetch after the previous month's execution (YNAB is the source of truth at every step), atomic split-transaction pairs per month with rollback on failure.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: textual ≥0.82.0 (existing), requests ≥2.28 (new — YNAB API), pytest ≥7.0 (existing), pytest-asyncio ≥0.23 (existing)  
**Storage**: JSON config at `~/.config/credit-card-ynab-importer/config.json`; global `api_key` + per-budget map `{budget_id → {budget_name, loan_account_id}}`; outside repo, never committed; no database  
**Testing**: pytest + pytest-asyncio; YNAB HTTP calls mocked with `unittest.mock.patch` or `responses` library  
**Target Platform**: macOS terminal (same as existing TUI)  
**Project Type**: TUI application (Textual) — extends existing `tui/` package  
**Performance Goals**: Full 3-month scan display < 10 s (SC-002); per-month plan derivation < 5 s (SC-003)  
**Constraints**: YNAB API rate limit 200 req/hr; CSV sessions must have zero YNAB dependency (FR-001); transaction pairs atomic per month (FR-021); remaining months re-fetched from YNAB after each execution — initial scan data retained only for carry-forward labeling  
**Scale/Scope**: Single user, one YNAB budget, default 3-month lookback window

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Pipeline-Stage Isolation | ✅ PASS | Cascade is a new module; no CSV pipeline stage is modified |
| II. YNAB Output Consistency | ✅ PASS | Feature uses YNAB API, not CSV exports; sign convention N/A here |
| III. Test-First | ✅ PASS | All cascade logic and API client tests written before implementation |
| IV. Data Fidelity | ✅ PASS | YNAB milliunits converted to human-readable display throughout |
| V. Simplicity (YAGNI) | ⚠️ JUSTIFIED | Network I/O is inherent to YNAB API integration — see Complexity Tracking |
| Technical Stack: No network I/O | ⚠️ JUSTIFIED | `requests` required for YNAB HTTPS calls — see Complexity Tracking |

**Gate result: PASS WITH JUSTIFIED VIOLATIONS**

A constitution amendment (MINOR: v1.1.0 → v1.2.0) is required before implementation begins to:
1. Scope Principle V's "no network calls / no external services" restriction to the CSV pipeline only.
2. Add `requests ≥2.28` to the allowed dependency list for the YNAB cascade module.

This is the first feature to introduce network I/O; the restriction was clearly authored for the pipeline stages, not for a future YNAB integration module. Run `/speckit-constitution` to produce the amendment before `/speckit-tasks`.

**Post-Phase-1 re-check**: Design (data-model.md, contracts/) does not introduce any additional violations. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-ynab-negative-carryover/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── screen-flows.md  # Phase 1 — TUI screen transitions and per-screen contracts
│   └── ynab-api.md      # Phase 1 — YNAB API endpoints and request/response shapes
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
tui/
├── app.py                      # existing — add cascade route to on_mount
├── models.py                   # existing — unchanged (CSV models only)
├── screens/
│   ├── welcome.py              # existing — add "Monthly Overspend Cascade" button
│   ├── file_picker.py          # existing — unchanged
│   ├── progress.py             # existing — unchanged
│   ├── summary.py              # existing — unchanged
│   ├── cascade_setup.py        # new — YNAB credentials wizard (Story 1) + Settings screen (Story 4)
│   ├── cascade_scan.py         # new — clearance check + scan overview (Story 2)
│   └── cascade_month.py        # new — month-by-month wizard: summary → confirm → execute (Story 3)
└── ynab/
    ├── __init__.py             # new
    ├── client.py               # new — YNAB API HTTP client (requests wrapper)
    ├── config.py               # new — config file read/write (~/.config/…/config.json)
    └── cascade.py              # new — cascade plan computation; donor selection; offline simulation

tests/
├── test_bac_pipeline.py        # existing — unchanged
├── test_davi_pipeline.py       # existing — unchanged
├── test_tui.py                 # existing — unchanged
├── test_ynab_client.py         # new — YNAB API client unit tests (all HTTP mocked)
├── test_cascade_logic.py       # new — cascade plan, donor selection, carry-forward simulation
└── test_cascade_screens.py     # new — Textual screen tests for cascade flow states

requirements.txt                # add: requests>=2.28
.gitignore                      # add: config.json (precautionary)
```

**Structure Decision**: Single-project layout. All new code lives under `tui/ynab/` (API + business logic) and `tui/screens/` (UI). The `ynab/` subdirectory cleanly separates YNAB API concerns from the TUI layer and from the existing CSV pipeline code. No new top-level package is introduced.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Network I/O (Principle V + Technical Stack) | YNAB API is the only source of budget data and the only way to create carryover transactions; no local-file alternative exists | Feature is API-driven by definition; pure-offline approach cannot satisfy any of Stories 1–3 |
| `requests` dependency (Technical Stack) | HTTPS Bearer auth, JSON bodies, structured error handling | `urllib.request` (stdlib) can do HTTPS but requires 3–5× more boilerplate for auth, JSON parsing, and error handling on every call; the added complexity outweighs the zero-dependency benefit |
