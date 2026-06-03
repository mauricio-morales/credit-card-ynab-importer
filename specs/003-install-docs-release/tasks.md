# Tasks: Non-Technical User Setup Guide & GitHub Release Packaging

**Input**: Design documents from `/specs/003-install-docs-release/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: Not applicable — deliverables are shell scripts, Markdown, and CI/CD YAML (see plan.md Complexity Tracking for justification). Manual acceptance tests from spec.md serve as the verification protocol.

**Organization**: Tasks are grouped by user story to enable independent implementation and verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Audit existing project structure to confirm all files referenced by the release workflow exist

- [x] T001 Audit existing project files — confirm `scripts/`, `tui/`, `run.py`, `requirements.txt`, and `.github/workflows/tests.yml` exist at the repository root per the release zip manifest in data-model.md Entity 1

---

## Phase 2: Foundational

**Purpose**: Confirm no structural conflicts before adding new artifacts

**Note**: All four deliverables (Windows launcher, Mac launcher, setup guide, release workflow) are independent files. There is no shared infrastructure that blocks user story work — phases 3–6 can begin immediately after Phase 1.

- [x] T002 Confirm the main branch is named `main` and review `.github/workflows/tests.yml` trigger to ensure it does not conflict with the planned `release.yml` on push to main

**Checkpoint**: Foundation confirmed — user story phases can proceed

---

## Phase 3: User Story 1 — Windows Launcher (Priority: P1) 🎯 MVP

**Goal**: A non-technical Windows user can download the release zip, extract it, double-click `run_windows.bat`, and the app starts — with a guide that walks them through Python installation if needed.

**Independent Test**: A person with no programming background can follow `GETTING_STARTED.md` on a fresh Windows machine from the "Quick Start" section through double-clicking the launcher and arrive at a running application, without assistance.

### Implementation for User Story 1

- [x] T003 [P] [US1] Create `run_windows.bat` at the repository root with the exact script contract from data-model.md Entity 2 — `@echo off`, Python PATH check with friendly error message and `pause`, quiet `pip install -r requirements.txt`, `python run.py` launch, and `pause` on exit
- [x] T004 [P] [US1] Create `GETTING_STARTED.md` at the repository root with all Windows-path sections: Quick Start (FR-002, one paragraph directing to GitHub Releases), Installing Python — Windows (FR-003, numbered steps from python.org download through PATH checkbox), Getting the Code — Download Zip (FR-005, presented first as recommended path), Running the Application — Windows (double-click `run_windows.bat`), and Troubleshooting — SmartScreen + Python not found (FR-012); apply tone constraints from data-model.md Entity 4 (no jargon, "pip" not in user-facing steps, exact UI text in troubleshooting)

**Checkpoint**: `GETTING_STARTED.md` covers Windows end-to-end and `run_windows.bat` is runnable — US1 acceptance scenarios are independently verifiable

---

## Phase 4: User Story 2 — Mac Launcher (Priority: P2)

**Goal**: A non-technical Mac user can download the release zip, extract it, double-click `run_mac.command`, and the app opens in Terminal — with guide sections for Mac Python installation and Gatekeeper handling.

**Independent Test**: A person with no programming background can follow `GETTING_STARTED.md` on a fresh Mac from the Mac Python installation section through double-clicking the launcher and arrive at a running application, without assistance.

### Implementation for User Story 2

- [x] T005 [P] [US2] Create `run_mac.command` at the repository root with the exact script contract from data-model.md Entity 3 — `#!/bin/bash` shebang, `cd "$(dirname "$0")"`, `python3` PATH check with friendly error and `read -n 1` wait, quiet `pip3 install -r requirements.txt`, `python3 run.py` launch, and press-any-key-to-exit prompt
- [x] T006 [US2] Set execute permission on `run_mac.command` with `chmod +x run_mac.command` at the repository root (required for FR-008; must be applied before committing so the execute bit is tracked in git at mode `100755`)
- [x] T007 [P] [US2] Add Mac-specific sections to `GETTING_STARTED.md`: Installing Python — Mac (FR-004, note Python 2 vs Python 3, numbered steps via python.org installer), Running the Application — Mac (double-click `run_mac.command`, right-click → Open for first run), and Troubleshooting — Gatekeeper / "Unidentified Developer" dialog (FR-012, exact macOS UI text)

**Checkpoint**: `GETTING_STARTED.md` now covers both platforms end-to-end and `run_mac.command` is executable — US2 acceptance scenarios are independently verifiable

---

## Phase 5: User Story 3 — Automatic GitHub Release (Priority: P3)

**Goal**: Every merge to `main` automatically creates a versioned GitHub Release with a downloadable zip containing all files required to run the application.

**Independent Test**: After merging to main, a new GitHub Release appears within 5 minutes with a downloadable zip named `credit-card-ynab-importer-v{DATE}.zip` — visible without a GitHub account on the Releases page.

### Implementation for User Story 3

- [x] T008 [US3] Create `.github/workflows/release.yml` with the full YAML contract from data-model.md Entity 5 — trigger `on: push: branches: [main]`, `permissions: contents: write`, `actions/checkout@v4` with `fetch-depth: 0`, date-based tag generation (`v$(date +%Y-%m-%d)`), `chmod +x run_mac.command`, `zip -r` with only named paths (`scripts/`, `tui/`, `requirements.txt`, `run.py`, `run_windows.bat`, `run_mac.command`), and `softprops/action-gh-release@v2` with `allow_updates: true`

**Checkpoint**: Pushing to main triggers the workflow and publishes a zip — US3 acceptance scenarios are independently verifiable via the GitHub Actions tab

---

## Phase 6: User Story 4 — Technical User Clone Section (Priority: P4)

**Goal**: A tech-savvy helper with git installed can follow the guide to clone the repository, install dependencies, and run the app from source — and knows how to update it via `git pull`.

**Independent Test**: A user with basic git knowledge can follow the "Clone with Git" section of `GETTING_STARTED.md` to set up and run the app from source, and understands how to update it.

### Implementation for User Story 4

- [x] T009 [US4] Add Getting the Code — Clone with Git section to `GETTING_STARTED.md` (FR-005, secondary option after Download Zip): `git clone` command, dependency install step (described without exposing "pip" in user-facing text per FR-013), and update instructions (`git pull` followed by re-running the dependency install step)

**Checkpoint**: `GETTING_STARTED.md` covers all four user scenarios — US4 acceptance scenarios are independently verifiable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate all artifacts against requirements before the feature is complete

- [x] T010 [P] Review complete `GETTING_STARTED.md` against FR-001 through FR-013 — verify: single file at root (FR-001), Quick Start at top (FR-002), numbered Windows steps with PATH checkbox note (FR-003), Python 2/3 note for Mac (FR-004), zip option presented first (FR-005), launcher run instructions per platform (FR-006/FR-007), troubleshooting covers all three scenarios — Gatekeeper, SmartScreen, Python not found (FR-012), and no jargon / "pip" visible to end users (FR-013)
- [x] T011 [P] Validate the `zip` command in `.github/workflows/release.yml` against data-model.md Entity 1 validation rules — confirm zip includes only `scripts/`, `tui/`, `requirements.txt`, `run.py`, `run_windows.bat`, `run_mac.command` and excludes `.git/`, `tests/`, `specs/`, `data/`, `.github/`, `.specify/`, `__pycache__/`, `.pytest_cache/`, and `GETTING_STARTED.md`
- [x] T012 [P] Confirm `run_mac.command` has the execute bit set in git by running `git ls-files --stage run_mac.command` and verifying the mode is `100755`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion
- **US1 (Phase 3)**: Depends on Phase 2 — creates `run_windows.bat` and `GETTING_STARTED.md`
- **US2 (Phase 4)**: Depends on Phase 3 — adds `run_mac.command` and Mac sections to `GETTING_STARTED.md`
- **US3 (Phase 5)**: Depends on Phase 4 — `release.yml` references `run_mac.command` which must exist and be chmod'd
- **US4 (Phase 6)**: Depends on Phase 3 (`GETTING_STARTED.md` must exist) — can run in parallel with Phases 4 and 5
- **Polish (Phase 7)**: Depends on all user story phases completing

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — MVP deliverable
- **US2 (P2)**: Extends `GETTING_STARTED.md` created in US1; `run_mac.command` must be chmod'd before US3 can include it in a zip
- **US3 (P3)**: References both launchers from US1 and US2 in the release zip command
- **US4 (P4)**: Extends `GETTING_STARTED.md` — can start once US1 completes, in parallel with US2/US3

### Within Each User Story

- T003 and T004 (US1) can run in parallel — different files
- T005 and T007 (US2) can run in parallel — different files; T006 (chmod) depends on T005
- T010, T011, T012 (Polish) can all run in parallel — independent checks

---

## Parallel Example: User Story 1

```bash
# T003 and T004 can be launched together (different files):
Task T003: "Create run_windows.bat at repository root"
Task T004: "Create GETTING_STARTED.md with Windows sections"
```

## Parallel Example: User Story 2

```bash
# T005 and T007 can be launched together (different files):
Task T005: "Create run_mac.command at repository root"
Task T007: "Add Mac-specific sections to GETTING_STARTED.md"
# T006 must follow T005:
Task T006: "chmod +x run_mac.command"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup audit
2. Complete Phase 2: Foundational check
3. Complete Phase 3: US1 — Windows launcher + guide (Windows sections)
4. **STOP and VALIDATE**: Can a Windows user follow the guide from zero to running app?
5. Commit and share if ready

### Incremental Delivery

1. Setup + Foundational → Infrastructure confirmed
2. US1 (Windows) → `run_windows.bat` + Windows guide → MVP for Windows users
3. US2 (Mac) → `run_mac.command` + Mac guide sections → Full dual-platform guide
4. US3 (GitHub Release) → `release.yml` → Automated distribution on every merge
5. US4 (Clone section) → Complete guide for technical helpers

### Note on US4 Parallelism

US4 (adding the clone section to `GETTING_STARTED.md`) only requires the file to exist from US1. It can be worked on in parallel with US2 and US3, as long as edits to `GETTING_STARTED.md` are merged carefully.

---

## Notes

- **No automated tests**: Deliverables are shell scripts, Markdown, and CI/CD YAML. Manual acceptance testing per spec.md applies.
- **chmod critical for US2/US3**: `run_mac.command` must be `chmod +x` before committing (T006) AND before zipping in CI (handled by the `chmod +x` step in T008's `release.yml`).
- **Same-day release collision**: Handled by `allow_updates: true` in `softprops/action-gh-release@v2` — the second merge on the same calendar day updates the existing release rather than failing.
- **Python naming convention**: Windows uses `python`, Mac uses `python3` — do not swap (research.md Decision 5).
- **`GETTING_STARTED.md` NOT in zip**: Per data-model.md Entity 1, the guide is intentionally omitted from the release zip.
- [P] tasks = different files, no dependencies between them
- [Story] label maps each task to a specific user story for traceability
