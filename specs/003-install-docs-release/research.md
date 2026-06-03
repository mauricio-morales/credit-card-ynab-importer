# Research: Non-Technical User Setup Guide & GitHub Release Packaging

**Feature**: 003-install-docs-release | **Date**: 2026-06-02

---

## 1. Zip Executable Permissions for `.command` Files on macOS

**Decision**: Build the release zip on `ubuntu-latest` using the Unix `zip` command with the `-r` flag. Unix `zip` embeds the Unix execute bit in the zip's external file attributes. When macOS's Archive Utility unzips the file, it restores these attributes — so `run_mac.command` will be executable immediately after extraction, without the user running `chmod`.

**Rationale**: This satisfies FR-008 at zero cost. The GitHub Actions runner already runs on Linux, and `zip` is pre-installed on `ubuntu-latest`. No cross-platform zip tool or post-processing step is needed.

**Alternatives considered**:
- *Python `zipfile` module*: Does not preserve Unix permissions (uses only the MS-DOS compatibility attributes by default). Rejected.
- *`tar.gz` archive*: Would preserve permissions but is an unusual format for non-technical Windows users who expect `.zip`. Rejected for Windows compatibility.
- *Separate zip per platform*: Unnecessary complexity — a single zip with correct Unix permissions works on both platforms. Rejected (Principle V).

**How to apply**: In the GitHub Actions workflow, use `zip -r release.zip <files>` after `chmod +x run_mac.command`.

---

## 2. GitHub Actions Release Workflow Pattern

**Decision**: Use the `softprops/action-gh-release@v2` action to create the GitHub Release. Tag via a preceding `git tag` step using `date +v%Y-%m-%d`. Use `on: push: branches: [main]` as the workflow trigger.

**Rationale**: `softprops/action-gh-release` is the de-facto standard for release creation in GitHub Actions. It creates the tag/release atomically with the asset upload in one step. The workflow already has `contents: write` permission available via `GITHUB_TOKEN`.

**Alternatives considered**:
- *`gh release create` CLI*: Valid alternative, but requires more shell scripting. The action abstracts error handling cleanly. Rejected for simplicity.
- *`actions/create-release` + `actions/upload-release-asset`*: The older two-step approach. Deprecated by GitHub in favor of unified actions. Rejected.

**Same-day collision**: Per the spec assumption, if two merges happen on the same calendar day, the second run will attempt to create a tag that already exists. Resolution: use `softprops/action-gh-release` with `allow_updates: true` — the second run updates the existing same-day release's asset rather than failing. This satisfies the spec assumption ("second will overwrite or append to first release").

**How to apply**: See `data-model.md` → Release Workflow Contract for the full YAML pattern.

---

## 3. Windows Batch Launcher (`run_windows.bat`)

**Decision**: Use a `.bat` file that: (1) checks for `python` in PATH and errors with a friendly message if not found, (2) runs `pip install -r requirements.txt --quiet`, (3) launches `python run.py`. Store the file at the repository root.

**Rationale**: `.bat` files are natively double-clickable on Windows with no additional configuration. The simplest possible implementation that satisfies FR-006.

**Key details**:
- `@echo off` suppresses command echoing for a clean terminal appearance
- `python --version >nul 2>&1 || (echo Python not found... & pause & exit /b 1)` gracefully handles the "Python not found" error case
- `pip install -r requirements.txt --quiet` on first run is fast (<5s on a typical connection) and idempotent on subsequent runs
- `pause` at end keeps the terminal open on exit so users can see any error messages

**Alternatives considered**:
- *PowerShell launcher*: More capable but requires execution policy changes on some Windows machines. More hostile for non-technical users. Rejected.
- *PyInstaller bundle*: Eliminates the Python dependency entirely, but violates the spec assumption ("does not need to be a fully self-contained executable"). Rejected.

---

## 4. Mac Launcher (`run_mac.command`)

**Decision**: A `.command` shell script (she-bang `#!/bin/bash`) that: (1) `cd`s to its own directory, (2) checks for `python3` in PATH, (3) runs `pip3 install -r requirements.txt --quiet`, (4) launches `python3 run.py`. The `.command` extension is macOS-specific and causes Terminal to open when double-clicked in Finder.

**Rationale**: `.command` files are the standard macOS mechanism for making shell scripts double-clickable. No `launchd` plist or `.app` wrapper needed.

**Key details**:
- `cd "$(dirname "$0")"` is required — without it, the script runs from the user's home directory, and relative paths to `requirements.txt` and `run.py` break
- Use `python3` (not `python`) — on modern macOS, `python` may not exist or may be Python 2
- The Gatekeeper block (first-run "unidentified developer" dialog) is handled via documentation in the guide's troubleshooting section (right-click → Open), not in the script itself
- The script must be `chmod +x` before zipping (enforced in the GitHub Actions workflow)

**Alternatives considered**:
- *Homebrew Python path hardcoding*: Breaks for users who installed Python from python.org. Rejected.
- *`.app` bundle*: Too complex and requires code signing for smooth Gatekeeper experience. Rejected (Principle V).

---

## 5. Python Detection and `python` vs `python3` Naming

**Decision**: Windows batch uses `python` (the Windows installer creates a `python` entry in PATH, not `python3`). Mac script uses `python3` (macOS ships without `python` in PATH on modern versions; `python3` is the convention post-macOS 12.3).

**Rationale**: These naming conventions match what the respective platform's Python installer sets up, minimizing user configuration.

**Guide note**: FR-003 and FR-004 require step-by-step installation instructions. The guide must instruct Windows users to check "Add Python to PATH" during installation — this is the single most common installation error.

---

## 6. `GETTING_STARTED.md` Structure

**Decision**: Single Markdown file with sections:
1. Quick Start (download link → extract → double-click; one paragraph, prominent)
2. Installing Python — Windows (numbered steps, screenshots described in words)
3. Installing Python — Mac (numbered steps)
4. Getting the Code — Option A: Download Release Zip (presented first)
5. Getting the Code — Option B: Clone with Git (for technical users)
6. Troubleshooting (three scenarios: Gatekeeper, SmartScreen, Python not found)

**Rationale**: FR-002 requires Quick Start at the top. FR-005 requires both code-access options with zip presented first. FR-012 requires troubleshooting. FR-013 requires non-technical language throughout.

**Alternatives considered**:
- *Separate Windows and Mac guides*: Avoids conditional language but requires maintaining two files. Rejected (Principle V).
- *Wiki-based guide*: Not version-controlled alongside the code. Rejected.
