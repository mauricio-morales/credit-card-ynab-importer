# Feature Specification: Textual TUI for Credit Card Statement Converter

**Feature Branch**: `001-textual-tui`
**Created**: 2026-05-10
**Status**: Draft
**Input**: User description: "Add a TUI using Textual. The flow should resemble: Welcome screen asking what do you want to do (2 options: Convert a BAC credit card statement export file in CSV to YNAB formatted CSV, and Convert a Davi/Scotia credit card statement export file in XLS to YNAB formatted CSV). Next it would prompt a file selection to find the file I want to convert. And after that it shows progress on the conversion until finally producing a summary and producing the files next (in the same folder) as the original file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert BAC Statement to YNAB (Priority: P1)

A user has exported their BAC credit card statement as a CSV file and wants to convert it to a YNAB-compatible CSV. They launch the tool, are greeted by a welcome screen, choose the BAC option, browse to their file, watch the conversion happen, and receive a summary along with the output file placed next to the original.

**Why this priority**: BAC CSV conversion is an existing core capability. Wrapping it in a guided TUI flow delivers the most immediate value and validates the full end-to-end experience.

**Independent Test**: Can be fully tested by launching the tool, selecting the BAC option, choosing a valid BAC CSV file, and confirming that a correctly formatted YNAB CSV appears in the same folder as the source file.

**Acceptance Scenarios**:

1. **Given** the tool is launched, **When** the welcome screen is displayed, **Then** the user sees two clearly labeled conversion options and can select one using keyboard or mouse.
2. **Given** the user selects the BAC option, **When** the file selection screen is shown, **Then** only files compatible with the BAC format (CSV) are browsable and selectable.
3. **Given** a valid BAC CSV file is selected, **When** conversion runs, **Then** a progress indicator is displayed until the conversion completes.
4. **Given** conversion completes successfully, **When** the summary screen is shown, **Then** it displays the number of transactions processed, the output file path, and any skipped or problematic rows.
5. **Given** conversion completes, **When** the user checks the source file's folder, **Then** the YNAB-formatted CSV is present with a recognizable name derived from the source file.

---

### User Story 2 - Convert Davi/Scotia Statement to YNAB (Priority: P1)

A user has exported their Davi/Scotia credit card statement as an XLS file and wants to convert it to YNAB format. The flow mirrors the BAC experience: welcome screen, format selection, file browsing, progress, and summary with output file.

**Why this priority**: Equal in priority to BAC conversion — both are existing capabilities and the TUI should support both from day one.

**Independent Test**: Can be fully tested by launching the tool, selecting the Davi/Scotia option, choosing a valid XLS file, and confirming the YNAB CSV output appears in the same folder.

**Acceptance Scenarios**:

1. **Given** the user selects the Davi/Scotia option on the welcome screen, **When** the file selection screen is shown, **Then** only XLS/XLSX files are browsable and selectable.
2. **Given** a valid Davi/Scotia XLS file is selected, **When** conversion runs, **Then** a progress indicator is displayed.
3. **Given** conversion completes successfully, **When** the summary is shown, **Then** it displays transaction count, output file location, and any warnings.
4. **Given** conversion completes, **When** the user inspects the source folder, **Then** a YNAB-formatted CSV is present alongside the original XLS file.

---

### User Story 3 - Handle Conversion Errors Gracefully (Priority: P2)

A user accidentally selects the wrong file type or a malformed file. The tool informs them clearly, allows them to go back and pick a different file without restarting, and never crashes silently.

**Why this priority**: Error recovery is important for usability but does not block the core conversion flows.

**Independent Test**: Can be tested by selecting an incompatible or empty file and confirming the user is presented with a meaningful error message and a way to retry.

**Acceptance Scenarios**:

1. **Given** the user selects a file that does not match the expected format, **When** the tool attempts to read it, **Then** a clear error message is shown describing the problem.
2. **Given** an error occurs during conversion, **When** the error is displayed, **Then** the user has the option to go back to file selection without restarting the entire application.
3. **Given** an unsupported file is selected, **When** the tool reports the error, **Then** the original file is never modified or deleted.

---

### Edge Cases

- What happens when the source folder is read-only and the output file cannot be written?
- What happens when the selected file is already open in another application (file lock)?
- What happens when a valid file contains zero transactions?
- What happens when a row in the source file has missing or malformed fields?
- What happens if the user navigates away from the progress screen before conversion finishes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST present a welcome/home screen as the first screen when launched, displaying the available conversion options.
- **FR-002**: The welcome screen MUST offer exactly two conversion options: BAC credit card CSV → YNAB CSV, and Davi/Scotia credit card XLS → YNAB CSV.
- **FR-003**: After selecting a conversion type, the tool MUST present a file browser screen allowing the user to navigate their filesystem and select the source file.
- **FR-004**: The file browser MUST filter visible files to only show those compatible with the selected conversion type (CSV files for BAC, XLS/XLSX files for Davi/Scotia).
- **FR-005**: After a file is selected, the tool MUST display a progress screen showing conversion status in real time until the operation completes.
- **FR-006**: Upon successful conversion, the tool MUST save the YNAB-formatted output file in the same directory as the source file.
- **FR-007**: The output file name MUST be derived from the source file name (e.g., same base name with a suffix or modified extension) so the user can easily identify it.
- **FR-008**: After conversion, the tool MUST display a summary screen showing: number of transactions processed, full path of the output file, and any rows that were skipped or produced warnings.
- **FR-009**: The tool MUST allow the user to return to the welcome screen from the summary screen to perform another conversion without restarting.
- **FR-010**: If conversion fails or the file is unreadable, the tool MUST display a descriptive error message and allow the user to select a different file without restarting.
- **FR-011**: The tool MUST be navigable entirely via keyboard in addition to mouse/pointer input.
- **FR-012**: The tool MUST NOT modify or delete the original source file at any point.

### Key Entities

- **Conversion Job**: Represents a single conversion run — includes source file path, conversion type (BAC or Davi/Scotia), status (pending, in progress, complete, failed), and result summary.
- **Transaction Record**: A single financial transaction extracted from the source file, containing date, description, and amount.
- **Conversion Summary**: The outcome of a completed job — transaction count, output file path, skipped rows with reasons.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from launching the tool to having a YNAB-ready output file in under 60 seconds for a typical statement (up to 200 transactions).
- **SC-002**: All conversion results currently produced by the existing command-line scripts are preserved exactly — no data loss or format regression.
- **SC-003**: A user unfamiliar with the existing scripts can successfully complete a conversion on their first attempt without consulting documentation.
- **SC-004**: Error messages are specific enough that the user understands what went wrong and what to do next, without technical jargon.
- **SC-005**: The tool can be fully operated using only the keyboard (no mouse required).

## Assumptions

- The existing BAC CSV and Davi/Scotia XLS processing logic is correct and will be reused without modification; the TUI wraps it rather than replacing it.
- The tool runs on macOS (the user's platform) but should not use macOS-specific APIs that would prevent future cross-platform use.
- A single user operates the tool at a time; no multi-user or concurrent-access scenarios are in scope.
- The output file is always placed in the same directory as the source file; no option to choose a different output location is required for this version.
- Adding support for additional bank formats in the future is a desired extensibility goal, but only the two existing converters are in scope for this feature.
- The file browser does not need to support network drives or cloud storage paths — local filesystem only.
