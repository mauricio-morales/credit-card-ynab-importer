# Feature Specification: QIF Export Alongside YNAB CSV Output

**Feature Branch**: `005-qif-export`
**Created**: 2026-08-09
**Status**: Draft
**Input**: User description: "For the BAC and Davi bank formatting flows, I want to add 1 more output format: QIF. this is the bank account standard format, so search for the specification online. I need you to continue outputting the out3 format we have, but also export the .qif file for each output file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a QIF file alongside every YNAB CSV (Priority: P1)

As the person running the importer against a BAC or DaviBank/Scotia statement, when the pipeline finishes, I want a QIF file produced next to each final YNAB CSV file so I can import the same transactions into any QIF-compatible finance tool without a separate conversion step.

**Why this priority**: This is the entire feature — without it, there is no new output format at all.

**Independent Test**: Run the existing orchestrator against a sample BAC `.csv` statement and a sample DaviBank `.xlsx` statement. Confirm that for every final `-out3-crc.csv` / `-out3-usd.csv` file produced, a matching `-out3-crc.qif` / `-out3-usd.qif` file now also exists, containing the same transactions.

**Acceptance Scenarios**:

1. **Given** a BAC statement with both CRC and USD transactions, **When** the pipeline runs to completion, **Then** four final files exist: `-out3-crc.csv`, `-out3-crc.qif`, `-out3-usd.csv`, `-out3-usd.qif`.
2. **Given** a DaviBank/Scotia statement with only CRC transactions, **When** the pipeline runs to completion, **Then** `-out3-crc.csv` and `-out3-crc.qif` both exist and contain the same set of transactions in the same order.
3. **Given** a QIF file produced by the tool, **When** it is opened in a standard QIF-compatible personal-finance application, **Then** it is recognized as a valid bank-transaction QIF file and every transaction imports with the correct date, payee, memo, and amount.

---

### User Story 2 - Existing CSV output is untouched (Priority: P2)

As someone who already relies on the current `out3` CSV files for YNAB import, I want that CSV output to remain byte-for-byte identical to today's behavior, so adding QIF export introduces no regression to my existing workflow.

**Why this priority**: The user was explicit that CSV output must continue exactly as-is; breaking it would be a regression on top of an addition.

**Independent Test**: Run the pipeline against the existing regression fixtures before and after this feature is implemented and diff the resulting `-out3-*.csv` files; they must be identical.

**Acceptance Scenarios**:

1. **Given** any existing BAC or DaviBank sample statement, **When** the pipeline runs after this feature is added, **Then** the generated `-out3-*.csv` files are byte-for-byte identical to the files produced before this feature existed.

---

### User Story 3 - Transactions with no memo or special characters export cleanly (Priority: P3)

As a user, I want transactions that have an empty memo, or a payee/memo containing characters like commas or quotes, to appear correctly formed in the QIF file, so the import doesn't produce garbled or misaligned records.

**Why this priority**: Correctness on the common edge cases (BAC always has empty memo; DaviBank sometimes has punctuation in descriptions) protects data fidelity, but the core P1 flow already delivers value without it being called out separately.

**Independent Test**: Run the pipeline against a statement containing a transaction with an empty reference/memo and one with a comma or quote in the payee/description, and confirm the resulting QIF record is well-formed (correct field lines, no broken records, no data loss).

**Acceptance Scenarios**:

1. **Given** a BAC transaction (memo always empty), **When** its QIF record is generated, **Then** the record has no memo line, but valid date, payee, and amount lines.
2. **Given** a DaviBank transaction whose payee/description contains a comma or double quote, **When** its QIF record is generated, **Then** those characters are preserved verbatim in the payee line.

---

### Edge Cases

- What happens when a currency split (CRC or USD) has zero transactions? The corresponding QIF file MUST still be created, containing only the format header, mirroring today's header-only CSV behavior for empty splits.
- What happens if a source description/memo contains a line break or the QIF field-terminator character? These MUST be neutralized (e.g., collapsed to a space) so they cannot break the single-line-per-field QIF record structure.
- What happens to amount sign for refunds/payments (negative source amounts) versus charges (positive source amounts)? The QIF amount MUST use the exact same sign convention already applied to the CSV `Amount` column (charges negative, payments/refunds positive).
- What happens if QIF generation fails for one currency split but the CSV for that split already succeeded? The CSV output already on disk MUST NOT be deleted or altered; the failure MUST be reported the same way other stage failures are reported today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a QIF file for every final `out3` CSV file produced by the BAC pipeline and the DaviBank/Scotia pipeline, for both the CRC and USD currency splits.
- **FR-002**: The QIF file for a given currency split MUST contain exactly the same transactions, in the same order, as its corresponding `out3` CSV file — no additions, omissions, or reordering.
- **FR-003**: Each QIF file MUST begin with the standard QIF bank-account transaction type header line.
- **FR-004**: Each transaction record in the QIF file MUST encode, at minimum, the transaction date, payee, memo (when present), and amount, using the standard QIF field-line format, and MUST be terminated by the standard QIF end-of-record marker.
- **FR-005**: The amount sign in the QIF record MUST match the sign already produced for that transaction in the CSV `Amount` column (i.e., reuse the existing charge/payment sign convention — no independent sign logic).
- **FR-006**: QIF dates MUST use the standard QIF date convention, independent of the `YYYY/MM/DD` format used in the CSV output.
- **FR-007**: When a transaction's memo is empty, the QIF record MUST omit the memo line rather than emitting an empty one.
- **FR-008**: QIF output file names MUST mirror the corresponding CSV output file's name, replacing only the file extension (e.g., `{base}-out3-crc.csv` pairs with `{base}-out3-crc.qif`).
- **FR-009**: QIF output files MUST be written to the same directory as the CSV output files, as part of the same pipeline run — no separate command or opt-in step is required to get QIF output.
- **FR-010**: Generating the QIF file MUST NOT change the content, format, or naming of the existing `out3` CSV file in any way.
- **FR-011**: If a currency split produces zero transactions, the system MUST still produce a QIF file for that split containing only the header (matching current CSV behavior for empty splits).
- **FR-012**: Characters that would break the single-line QIF record structure (e.g., embedded newlines) in a payee or memo field MUST be neutralized before being written, without altering any other content of the field.

### Key Entities

- **QIF Output File**: The new deliverable per currency split (CRC/USD) per statement, sibling to the existing `out3` CSV file; holds one QIF transaction record per source transaction plus the format header.
- **QIF Transaction Record**: The QIF representation of a single transaction — date, payee, memo (optional), and amount — derived one-to-one from the same transaction already represented as a row in the `out3` CSV.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pipeline runs (BAC and DaviBank/Scotia) that produce a final CSV file for a currency split also produce a matching QIF file for that same split, with no manual step beyond the existing import command.
- **SC-002**: 100% of transactions present in a given `out3` CSV file are also present, with matching date, payee, memo, and amount, in the corresponding QIF file.
- **SC-003**: Existing `out3` CSV output is unchanged: 0 differences when comparing CSV output produced before and after this feature against the same source statements.
- **SC-004**: QIF files produced by the tool open without error in standard QIF-compatible personal-finance software and every transaction imports with correct date, payee, memo, and amount.

## Assumptions

- QIF's bank-account transaction type (rather than, e.g., a credit-card-specific QIF type) is used for all generated files, matching the user's framing of QIF as "the bank account standard format" and maximizing compatibility with generic QIF importers.
- QIF dates are written in the standard QIF date convention (`MM/DD/YYYY`), independent of the CSV's `YYYY/MM/DD` convention; this is the default documented by the QIF specification and does not need to match the CSV date format.
- One QIF file is generated per currency split, mirroring the existing `out3-crc` / `out3-usd` CSV pairing, rather than one combined multi-currency QIF file.
- QIF generation is automatic and always-on for both the BAC and DaviBank/Scotia pipelines — it is additive output produced in the same run that already produces the CSV, not a separate opt-in feature or new CLI flag.
- This feature applies to pipeline runs performed after it ships; it does not retroactively generate QIF files for CSV outputs already sitting on disk from prior runs.
- No account name/number metadata is embedded in the QIF file (no `!Account` block); each file represents a single account's transactions for a single currency, consistent with how the CSV files are already scoped.
