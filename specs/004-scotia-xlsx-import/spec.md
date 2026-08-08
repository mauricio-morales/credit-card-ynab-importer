# Feature Specification: Scotia/DaviBank XLSX Import

**Feature Branch**: `004-scotia-xlsx-import`
**Created**: 2026-08-08
**Status**: Draft
**Input**: User description: "This tool was built to import Scotia/DaviBank files in .xls format, but the bank changed it to .xlsx. I need you to build the spec to replace the Scotia convert feature from .xls to .xlsx. Reference sample file: 'Scotia Visa.xlsx'"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a current-format statement (Priority: P1)

A user downloads their monthly Scotia/DaviBank credit card statement, which the bank now delivers as an .xlsx file instead of the old .xls file. They select the file in the importer and expect it to convert successfully into YNAB-ready transaction files, exactly as it did with .xls files before the bank's change.

**Why this priority**: This is the core, blocking need. Since the bank stopped producing .xls files, the importer currently cannot process any new statement at all — this story restores basic functionality.

**Independent Test**: Select a real Scotia/DaviBank .xlsx statement in the tool and verify it produces YNAB-ready output with the same transaction count, dates, descriptions, amounts, and currency splits that the .xls-based process produced for equivalent data.

**Acceptance Scenarios**:

1. **Given** a valid Scotia/DaviBank .xlsx statement file, **When** the user selects it for import, **Then** the tool converts it into YNAB-ready transaction files split by currency (CRC/USD) that match the transaction count and values found in the source file.
2. **Given** a Scotia/DaviBank .xlsx statement containing multiple cards in one file (separated by card-number section markers), **When** imported, **Then** transactions from every card section are included in the output.
3. **Given** a Scotia/DaviBank .xlsx statement with both purchase (debit) and payment (credit) entries, **When** imported, **Then** amounts are correctly signed as outflows/inflows in the YNAB output, consistent with current behavior.

---

### User Story 2 - Clear feedback on legacy or invalid files (Priority: P2)

A user still has an old .xls statement on their computer, or accidentally selects the wrong file, in the Scotia/DaviBank import flow. Instead of a crash or a confusing technical error, they see a plain explanation of what went wrong and what to do about it.

**Why this priority**: Prevents confusing failures during the transition period and improves trust in the tool, but is secondary to restoring the core conversion capability.

**Independent Test**: Select a legacy .xls file, and separately a non-statement file, in the Scotia/DaviBank flow, and confirm each produces an understandable message rather than a raw crash.

**Acceptance Scenarios**:

1. **Given** a legacy .xls Scotia/DaviBank file, **When** the user attempts to import it, **Then** the tool clearly states that format is no longer supported and that an .xlsx export from the bank is needed.
2. **Given** a file that is not a valid, readable spreadsheet selected in the Scotia/DaviBank flow, **When** the user attempts to import it, **Then** the tool shows a plain-language error rather than a technical crash.

---

### User Story 3 - Validation of unexpected file layout (Priority: P3)

If Scotia/DaviBank further changes the layout of their .xlsx export (columns reordered, renamed, or missing) in the future, the user is told clearly what looks wrong instead of silently getting incomplete or incorrect YNAB data.

**Why this priority**: Protects against silent data corruption, but only matters if the bank's export deviates from the confirmed current layout, so it is the lowest priority of the three.

**Independent Test**: Feed the importer a .xlsx file missing an expected column (e.g., no amount column) and confirm it flags the problem rather than emitting incomplete or incorrect transactions.

**Acceptance Scenarios**:

1. **Given** a .xlsx file missing one or more expected transaction fields, **When** imported, **Then** the tool reports that expected data could not be found rather than silently producing an empty or incorrect result.

---

### Edge Cases

- What happens when a .xlsx statement includes trailing footer/summary rows (e.g., a date-range note) similar to the old .xls format? These MUST be skipped and not treated as transactions.
- What happens when the workbook contains more than one sheet? The transaction data on the primary sheet MUST be used, consistent with current single-sheet handling.
- What happens with a statement file that has a header row but zero transactions? The tool MUST produce empty YNAB output files rather than erroring.
- What happens when transaction dates are stored as native spreadsheet date values instead of plain text (a difference between how .xls and .xlsx can store dates)? Dates MUST be parsed correctly in either case.
- Detecting or de-duplicating transactions that overlap between a previously-imported .xls statement and a new .xlsx statement covering the same period is out of scope for this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept Scotia/DaviBank credit card statement files in .xlsx format for import.
- **FR-002**: The system MUST extract the same transaction fields from .xlsx files that it extracted from .xls files: reference number, transaction date, description, amount, currency, and transaction type.
- **FR-003**: The system MUST associate each transaction with the correct card, using the same card-section markers used in the legacy format.
- **FR-004**: The system MUST skip non-transaction rows present in the .xlsx file (e.g., section headers, footer/summary rows, blank rows), matching current handling of the .xls format.
- **FR-005**: The system MUST convert extracted .xlsx transactions into the existing YNAB-ready output files, split by currency, with no change to the output format, field values, or file-naming convention.
- **FR-006**: The system MUST correctly interpret transaction dates whether they are stored as plain text or as native spreadsheet date values within the .xlsx file.
- **FR-007**: When a user selects a legacy .xls Scotia/DaviBank file, the system MUST show a clear, plain-language message stating that format is no longer supported and that an .xlsx export is required, instead of crashing or failing silently.
- **FR-008**: When a selected .xlsx file does not contain the expected transaction data (e.g., missing required columns or an unreadable file), the system MUST show a clear, plain-language error identifying the problem rather than crashing or producing incomplete/incorrect results.
- **FR-009**: The system MUST no longer require .xls files for Scotia/DaviBank imports, since the bank has discontinued that format for new statements.

### Key Entities

- **Transaction Record**: A single statement line item — reference number, date, description, amount, currency, transaction type (purchase/payment), and the card it belongs to.
- **Card Section**: A grouping of transactions under one card number within a single statement file.
- **YNAB Output File**: A currency-specific export file (CRC or USD) containing the finished, YNAB-ready transaction data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can import a current Scotia/DaviBank .xlsx statement and receive correct YNAB-ready files with no additional manual steps compared to the previous .xls workflow.
- **SC-002**: 100% of transactions present in a valid Scotia/DaviBank .xlsx statement appear correctly in the resulting YNAB output, matching count, dates, and amounts.
- **SC-003**: Users who attempt to import an outdated .xls file receive an understandable explanation, with zero raw technical crash messages, 100% of the time.
- **SC-004**: Existing Scotia/DaviBank users can resume their monthly import routine with no new instructions needed beyond selecting their (now .xlsx) file.

## Assumptions

- The new Scotia/DaviBank .xlsx export preserves the same column layout, header names, card-section markers, and transaction semantics observed in the reference sample file (`Scotia Visa.xlsx`): columns for reference number, transaction date, description, amount, currency, and type.
- The bank will no longer provide .xls exports going forward, so backward-compatible .xls parsing is not required — only a clear "no longer supported" message for any legacy files a user might still have.
- The relevant transaction data is on the first/primary sheet of the workbook, consistent with current .xls handling.
- No changes are needed to the resulting YNAB CSV output format, currency-splitting behavior, or downstream YNAB import process — only the source file format changes.
- This feature covers the Scotia/DaviBank import path only; the separate BAC CSV import path is unaffected.
