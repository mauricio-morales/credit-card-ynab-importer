# Phase 0 Research: QIF Export Alongside YNAB CSV Output

All items from the feature spec's Assumptions section already resolve the open
questions a normal Phase 0 pass would raise (QIF type, date convention, one
file per currency split, always-on, no `!Account` block). This document
records the concrete format/implementation decisions derived from those
assumptions and from the standard QIF specification.

## 1. QIF file structure

**Decision**: Each QIF file uses the QIF "Bank" transaction type:

```
!Type:Bank
D{MM/DD/YYYY}
P{payee}
M{memo}
T{amount}
^
D{MM/DD/YYYY}
P{payee}
T{amount}
^
```

- `!Type:Bank` is the single header line, written once per file, always
  present (even for a currency split with zero transactions — matching
  today's header-only CSV behavior for empty splits, FR-011).
- One record block per transaction: `D` (date), `P` (payee), `M` (memo,
  **omitted** when empty per FR-007), `T` (amount), terminated by `^`.
- Field order within a record (`D`, `P`, `M`, `T`) is not significant to QIF
  parsers (each line is self-identifying by its leading letter), but a fixed,
  consistent order is used for readability and testability.

**Rationale**: This is the minimal, universally-recognized QIF bank-account
record shape (`D`/`T`/`P`/`M`/`^`), satisfying FR-003/FR-004 and the "opens
without error in standard QIF-compatible software" success criterion
(SC-004). No category (`L`), cleared status (`C`), or account block (`N`,
`!Account`) is emitted — the spec's Assumptions explicitly rule out account
metadata, and the functional requirements don't call for category/cleared
fields.

**Alternatives considered**:
- `!Type:CCard` (credit-card QIF type) — rejected per the spec's explicit
  Assumption that "bank account standard format" (`!Type:Bank`) is what the
  user asked for and it's the more broadly compatible type.
- Emitting an empty `M` line when memo is blank — rejected; FR-007 requires
  omitting the line entirely, not emitting an empty one (this mirrors how
  the CSV still writes `""` for empty memo, but QIF's line-based format
  makes "line absent" the more natural way to signal "no memo").

## 2. Date format

**Decision**: `MM/DD/YYYY`, converted from the out3 CSV's already-normalized
`YYYY/MM/DD` value (e.g. `2026/03/05` → `03/05/2026`).

**Rationale**: FR-006 and the spec's Assumptions require the standard QIF
date convention, independent of the CSV's format. Since Stage 3 has already
fully normalized and zero-padded the date (2-digit years expanded, DD/MM/YYYY
→ YYYY/MM/DD) before QIF generation runs, this is a pure reformat with no new
parsing/normalization logic — reusing Constitution Principle IV's existing
date-normalization guarantees rather than re-deriving them.

## 3. Amount sign and formatting

**Decision**: Copy the `Amount` value verbatim from the out3 CSV row — no
independent sign computation, no reformatting.

**Rationale**: FR-005 explicitly requires reusing the CSV's existing
charge/payment sign convention (Constitution Principle II's `negate_amount()`
result) rather than re-implementing sign logic in the QIF path. Since QIF
generation is designed as a post-processing step over the finished out3 CSV
(see §5), the amount string is already correct and needs no transformation.

## 4. Source of truth: derive QIF from the written out3 CSV, not from raw pipeline data

**Decision**: QIF generation reads the just-written `out3` CSV file (the one
already on disk with `"Date","Payee","Memo","Amount"` rows) and converts each
row into a QIF record. It is invoked once per currency split, immediately
after that split's CSV is written, from `orchestrator.py`.

**Rationale**:
- The spec's Key Entities section describes the QIF Transaction Record as
  "derived one-to-one from the same transaction already represented as a row
  in the out3 CSV" — the spec itself frames QIF as a CSV-derived, not
  pipeline-derived, artifact.
- Guarantees FR-002 (identical transactions, same order) and FR-010 (CSV is
  never touched) essentially for free: the CSV is read-only input, never
  mutated, and the QIF rows are structurally the same rows already verified
  correct by existing Stage 3 tests.
- Keeps Constitution Principle I (Pipeline-Stage Isolation) intact: QIF
  export is not a 4th pipeline stage with its own input/output contract
  feeding downstream stages — it's an additional, independent output
  artifact produced from Stage 3's finished result. `bac_stage3.py` and
  `davi_stage3.py` remain completely unchanged.
- Avoids duplicating amount-sign / date-normalization / quoting logic between
  two code paths (CSV writer and QIF writer) that would otherwise need to be
  kept in sync by hand.

**Alternatives considered**:
- Generating QIF in-process alongside the CSV inside `bac_stage3.py` /
  `davi_stage3.py` (shared in-memory row list) — rejected: couples two
  independent output formats inside the CSV-writing stage, increases the
  risk of a change to QIF logic accidentally affecting CSV output (violates
  FR-010's isolation requirement), and doesn't match the spec's framing of
  QIF as CSV-derived.
- A separate CLI/opt-in QIF conversion script the user runs manually —
  rejected: spec Assumptions state QIF generation "is automatic and
  always-on... not a separate opt-in feature or new CLI flag."

## 5. Character neutralization

**Decision**: Before writing a field (`payee` or `memo`), replace any `\r\n`,
`\r`, or `\n` with a single space. No other characters (commas, double
quotes) are altered — QIF is not comma-delimited, so those characters need no
escaping.

**Rationale**: FR-012 requires neutralizing characters that would break the
single-line-per-field QIF record structure. In QIF, each field is exactly one
line starting with its type letter; an embedded newline would split a field
across multiple lines and corrupt the record structure (e.g. a stray line
with no leading letter, or a line prefix like `M` swallowed into to the
previous field). Commas and quotes (called out in User Story 3 / FR
Acceptance Scenario 2) are ordinary characters in QIF's line-oriented format
and require no special handling, unlike in the comma-delimited CSV output.

## 6. File naming and location

**Decision**: `{base}-out3-{currency}.qif`, written to the same directory as
`{base}-out3-{currency}.csv`, generated in the same orchestrator run
immediately after that CSV is written.

**Rationale**: Directly satisfies FR-008/FR-009 and mirrors the existing
`out1`/`out2-*`/`out3-*` naming convention already used throughout the
pipeline (Development Workflow section of the constitution).

## 7. Empty-split handling

**Decision**: When the out3 CSV for a split contains only the header row (no
transactions), the QIF converter still writes the `!Type:Bank` header line
and produces a valid, empty QIF file with zero transaction records.

**Rationale**: FR-011 requires mirroring the CSV's existing header-only
behavior for empty splits. Since QIF generation always writes the `!Type:Bank`
header unconditionally and then iterates zero times over an empty CSV row
set, this falls out naturally from the CSV-driven design in §4 with no
special-case branch needed.
