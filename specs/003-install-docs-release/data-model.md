# Data Model & Contracts: Non-Technical User Setup Guide & GitHub Release Packaging

**Feature**: 003-install-docs-release | **Date**: 2026-06-02

This feature produces no new Python data structures. The "entities" are files — their structure and interface contracts are defined below.

---

## Entity 1: Release Zip

**File**: `credit-card-ynab-importer-{TAG}.zip`
**Published to**: GitHub Releases page

### Contents (must match FR-010)

```text
credit-card-ynab-importer-{TAG}.zip
├── scripts/
│   ├── orchestrator.py
│   ├── bac_stage1.py
│   ├── bac_stage2.py
│   ├── bac_stage3.py
│   ├── davi_stage1.py
│   ├── davi_stage2.py
│   └── davi_stage3.py
├── tui/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── models.py
│   ├── screens/
│   └── ynab/
├── requirements.txt
├── run.py
├── run_windows.bat        ← execute bit not required on Windows
└── run_mac.command        ← execute bit MUST be set (chmod +x before zipping)
```

> `GETTING_STARTED.md` is NOT included in the zip — users who downloaded the zip already have the link to the Releases page, and the Quick Start section in the guide points them there. Including it would add noise without benefit.

### Validation rules

- `run_mac.command` must have Unix execute bit set (verified by `zip -v` output showing mode `0755`)
- Zip must not include `.git/`, `tests/`, `specs/`, `data/`, `.github/`, `.specify/`, `__pycache__/`, `.pytest_cache/`
- Tag format: `v` + `YYYY-MM-DD` (e.g., `v2026-06-02`)

---

## Entity 2: Windows Launcher (`run_windows.bat`)

**Location**: repository root + inside release zip

### Script contract

```bat
@echo off
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.9 or newer from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo Installing/updating dependencies...
pip install -r requirements.txt --quiet
echo Starting the application...
python run.py
pause
```

**Behaviour**:
- If Python is not in PATH → prints a friendly error, pauses (so user can read it), exits
- If Python is found → installs/updates deps silently, then launches the app
- `pause` at end keeps the terminal open after the app exits so errors remain visible

---

## Entity 3: Mac Launcher (`run_mac.command`)

**Location**: repository root + inside release zip
**Required permissions**: `chmod +x` (must be set before committing and before zipping)

### Script contract

```bash
#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "Python 3 not found. Please install Python 3.9 or newer from https://python.org"
    echo "Press any key to exit."
    read -n 1
    exit 1
fi

echo "Installing/updating dependencies..."
pip3 install -r requirements.txt --quiet
echo "Starting the application..."
python3 run.py
echo "Press any key to exit."
read -n 1
```

**Behaviour**:
- `cd "$(dirname "$0")"` ensures relative paths resolve correctly regardless of where Terminal opens
- If `python3` not in PATH → friendly error, waits for keypress, exits
- If found → installs/updates deps silently, launches app
- Terminal stays open after app exits (user must press a key), so errors are readable

---

## Entity 4: Setup Guide (`GETTING_STARTED.md`)

**Location**: repository root (not in release zip)

### Section structure

| Section | Requirement |
|---------|-------------|
| Quick Start | FR-002: first section; one paragraph directing user to GitHub Releases |
| Installing Python — Windows | FR-003: numbered steps from python.org download to PATH checkbox |
| Installing Python — Mac | FR-004: notes Python 2 vs Python 3; points to python.org |
| Getting the Code — Download Zip | FR-005: presented first as recommended path |
| Getting the Code — Clone with Git | FR-005: secondary option for technical users |
| Running the Application | FR-006/FR-007: one line per platform (double-click the launcher) |
| Troubleshooting | FR-012: Gatekeeper, SmartScreen, Python not found |

**Tone constraints** (FR-013):
- No jargon: "terminal" is acceptable (users will see one), "PATH" must be explained in plain language when mentioned, "pip" must not appear in user-facing steps
- Numbered steps for every installation sequence
- Troubleshooting steps use the exact UI text users will see (e.g., "Unidentified Developer")

---

## Entity 5: GitHub Actions Release Workflow (`.github/workflows/release.yml`)

### Trigger

```yaml
on:
  push:
    branches: [main]
```

### Job contract

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write       # required to create tags and releases
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0    # needed for tag history

      - name: Generate version tag
        id: tag
        run: echo "TAG=v$(date +%Y-%m-%d)" >> $GITHUB_OUTPUT

      - name: Set execute permission on Mac launcher
        run: chmod +x run_mac.command

      - name: Create release zip
        run: |
          zip -r credit-card-ynab-importer-${{ steps.tag.outputs.TAG }}.zip \
            scripts/ tui/ requirements.txt run.py \
            run_windows.bat run_mac.command

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ steps.tag.outputs.TAG }}
          name: "Release ${{ steps.tag.outputs.TAG }}"
          body: "Automated release. See GETTING_STARTED.md for setup instructions."
          files: credit-card-ynab-importer-${{ steps.tag.outputs.TAG }}.zip
          allow_updates: true    # handles same-day re-releases
```

**Key properties**:
- `allow_updates: true` satisfies the spec assumption about same-day collisions
- `permissions: contents: write` is required; the default `GITHUB_TOKEN` supports this for public repos
- `fetch-depth: 0` ensures git tag history is available so `softprops` can push the tag
- The zip command excludes test fixtures, specs, CI config, and dev tools automatically (only named paths are included)

---

## Post-Phase-1 Constitution Check

| Principle | Status |
|-----------|--------|
| **I. Pipeline-Stage Isolation** | ✅ No pipeline changes |
| **II. YNAB Output Consistency** | ✅ No pipeline changes |
| **III. Test-First** | ✅ Exception justified (see plan.md Complexity Tracking) |
| **IV. Data Fidelity** | ✅ No data transformation |
| **V. Simplicity (YAGNI)** | ✅ Single workflow job, minimal steps, no matrix, no versioning logic beyond `date` |
