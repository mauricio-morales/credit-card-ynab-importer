# Feature Specification: Non-Technical User Setup Guide & GitHub Release Packaging

**Feature Branch**: `003-install-docs-release`
**Created**: 2026-06-02
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Download and Run on Windows (Priority: P1)

A non-technical Windows user receives a link to the application (shared via WhatsApp or email). They download the release zip from GitHub, extract it, double-click a batch file, and the application opens in a terminal window ready to use — without ever manually opening a command prompt.

**Why this priority**: This is the primary distribution path for non-technical users. If a user cannot go from "I have a link" to "the app is running" without technical help, the feature has failed.

**Independent Test**: A person with no programming background can follow the written guide starting from zero and arrive at a running application on a fresh Windows machine, without assistance.

**Acceptance Scenarios**:

1. **Given** a Windows user has the release zip downloaded, **When** they extract it and double-click `run_windows.bat`, **Then** a terminal window opens and the application starts without any additional configuration
2. **Given** a Windows user who does not have Python installed, **When** they follow the Python installation section of the guide, **Then** they can successfully install Python and proceed to run the app
3. **Given** a user who already has Python, **When** they double-click the launcher, **Then** the app installs its dependencies automatically on first run and then starts

---

### User Story 2 - Download and Run on Mac (Priority: P2)

A non-technical Mac user downloads the release zip, extracts it, and double-clicks a launcher file. The application opens in Terminal.

**Why this priority**: Mac users tend to be slightly more comfortable with Terminal, but the friction-free experience is still a core goal.

**Independent Test**: A person with no programming background can follow the written guide on a fresh Mac and arrive at a running application, without assistance.

**Acceptance Scenarios**:

1. **Given** a Mac user has the release zip extracted, **When** they double-click `run_mac.command`, **Then** Terminal opens and the application starts
2. **Given** a Mac user who does not have Python installed, **When** they follow the Mac Python installation section, **Then** they can install Python via the official installer and proceed
3. **Given** a Mac user whose system blocks the `.command` file the first time, **When** they follow the guide's troubleshooting step (right-click → Open), **Then** the launcher runs successfully

---

### User Story 3 - Automatic GitHub Release on Merge (Priority: P3)

When a developer merges a pull request into the main branch, GitHub automatically creates a versioned release and publishes a zip file that end users can download — no manual packaging step required.

**Why this priority**: This is the delivery mechanism that makes P1 and P2 sustainable. Without it, every new version requires manual effort to distribute.

**Independent Test**: After merging to main, a new GitHub Release appears within 5 minutes with a downloadable zip named with the version identifier.

**Acceptance Scenarios**:

1. **Given** a pull request is merged into the main branch, **When** the automated workflow runs, **Then** a new GitHub Release is created with a versioned zip attachment
2. **Given** a new release exists, **When** a user visits the GitHub Releases page, **Then** they see a downloadable zip file without needing a GitHub account
3. **Given** two consecutive merges, **When** both complete, **Then** two separate releases exist with distinct version identifiers

---

### User Story 4 - Technical User Clones Repository (Priority: P4)

A tech-savvy helper (e.g., a family member setting things up) clones the repository from GitHub and can keep it up-to-date via `git pull`.

**Why this priority**: Optional path; the guide should cover it, but non-technical users do not need it.

**Independent Test**: A user with basic git knowledge can follow the "clone" section of the guide to set up and update the app from source.

**Acceptance Scenarios**:

1. **Given** a user with git installed, **When** they follow the "clone" section of the guide, **Then** they can clone, install dependencies, and run the app from source
2. **Given** a user who previously cloned, **When** a new version is released, **Then** running `git pull` followed by the dependency install command is sufficient to update

---

### Edge Cases

- What if Python is already installed but below version 3.9?
- What if the user's antivirus blocks the `.bat` or `.command` launcher?
- What if the extracted folder path contains spaces or accented characters?
- What if the user is on macOS and Python is installed via Homebrew but not in the system PATH used by double-click launchers?
- What if the GitHub Action fails mid-run — does a partial or empty release artifact get published?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a single `GETTING_STARTED.md` file in the repository root written in plain, non-technical language covering both Mac and Windows setup
- **FR-002**: The guide MUST include a "Quick Start" section at the top directing non-technical users straight to the GitHub Releases page to download the zip
- **FR-003**: The guide MUST include step-by-step Python installation instructions for Windows (via python.org), covering Python 3.9 or newer, with numbered steps clear enough for a first-time user
- **FR-004**: The guide MUST include step-by-step Python installation instructions for Mac (via python.org), noting that macOS may ship with Python 2 and that Python 3 must be installed separately
- **FR-005**: The guide MUST explain both options for getting the code: (a) downloading the release zip (presented first, as the recommended path) and (b) cloning via git
- **FR-006**: A Windows launcher file (`run_windows.bat`) MUST be included in the repository and in the release zip; double-clicking it MUST install dependencies if not already installed, then start the application
- **FR-007**: A Mac launcher file (`run_mac.command`) MUST be included in the repository and in the release zip; double-clicking it MUST install dependencies if not already installed, then start the application
- **FR-008**: The Mac launcher MUST have correct executable permissions preserved inside the zip so it works after extraction without the user needing to run `chmod`
- **FR-009**: A GitHub Actions workflow MUST automatically create a new GitHub Release whenever a commit is merged to the main branch
- **FR-010**: The release zip MUST include all files required to run the application: Python source files, `requirements.txt`, both launchers, and `GETTING_STARTED.md`
- **FR-011**: Each release MUST have a distinct version identifier (date-based tag, e.g., `v2026-06-02`) so users can tell versions apart
- **FR-012**: The guide MUST include a troubleshooting section covering: macOS Gatekeeper blocking the `.command` file, Windows SmartScreen warnings on the `.bat` file, and "Python not found" errors
- **FR-013**: The guide's language MUST be accessible to users with no programming background; no assumed knowledge of terminals, file paths, or package managers

### Key Entities

- **Release Zip**: A versioned archive containing all runnable application files and the setup guide; published to GitHub Releases on each main-branch merge
- **Windows Launcher** (`run_windows.bat`): A double-clickable file that installs dependencies on first run and starts the application
- **Mac Launcher** (`run_mac.command`): A double-clickable file that installs dependencies on first run and starts the application
- **Setup Guide** (`GETTING_STARTED.md`): A single markdown document with dual-platform setup instructions written for non-technical users
- **GitHub Actions Workflow**: An automated pipeline that packages and publishes a new release on every merge to main

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A non-technical user with zero programming experience can go from "I have the download link" to "the app is running" in under 10 minutes on either platform, following only the guide
- **SC-002**: 100% of merges to main result in a published GitHub Release within 5 minutes, with no manual developer intervention
- **SC-003**: The release zip can be extracted and run without an internet connection after Python and dependencies are installed (i.e., the zip is self-sufficient for offline use post-setup)
- **SC-004**: The guide covers every required installation step so a user never needs to search for additional instructions outside the document
- **SC-005**: The Windows and Mac launchers handle first-run dependency installation silently, requiring zero terminal interaction beyond double-clicking

## Assumptions

- The application remains a Python terminal/TUI application; users will see a terminal window, which is acceptable to the target audience
- Python 3.9+ is the version floor; the launchers and guide will specify this
- The GitHub repository is or will be public, so anyone can download releases without a GitHub account
- The main branch is named `main`; the GitHub Action targets `main`
- Dependency installation via `pip install -r requirements.txt` is the only setup step; no system-level C compilers or other native dependencies are required
- The release zip does not need to be a fully self-contained executable (e.g., PyInstaller bundle); it assumes Python is pre-installed by the user following the guide
- Version numbering uses date-based tags (e.g., `v2026-06-02`) to avoid maintaining a semantic version number for a personal-use tool
- If two merges happen on the same day, the second will overwrite or append to the first release; this is acceptable for now
