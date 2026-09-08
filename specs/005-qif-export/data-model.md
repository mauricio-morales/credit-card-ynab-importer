# Phase 1 Data Model: QIF Export

This feature introduces no new persistent domain objects or state — it adds
one new derived file type per existing currency split. The "entities" below
are the shapes of data flowing through the new conversion step, not database
or class models.

## YNAB CSV Row (existing, input to this feature)

Already produced by `bac_stage3.py` / `davi_stage3.py`, read verbatim as
input — not modified by this feature.

| Field  | Type   | Format                          | Notes                                   |
|--------|--------|----------------------------------|------------------------------------------|
| Date   | string | `YYYY/MM/DD`, double-quoted      | Fully normalized, zero-padded            |
| Payee  | string | double-quoted, `""` escaping     | Verbatim source text                     |
| Memo   | string | double-quoted; `""` when empty   | Empty for BAC; may be populated for Davi |
| Amount | string | double-quoted; sign per Principle II | Charges negative, payments/refunds positive |

## QIF Output File (new)

One per currency split (CRC/USD) per statement, sibling to the corresponding
`out3` CSV file.

| Attribute      | Value                                                        |
|----------------|---------------------------------------------------------------|
| Path           | `{same directory as out3 CSV}/{base}-out3-{currency}.qif`     |
| Header line    | `!Type:Bank` (always present, exactly once, first line)       |
| Body           | Zero or more QIF Transaction Records, in the same order as the source CSV rows |
| Encoding       | UTF-8, `\n` line endings                                       |

**Relationships**: 1:1 with an `out3` CSV file. Derived entirely from that
CSV's rows (see research.md §4) — no relationship to Stage 1/Stage 2
intermediate files.

**Validation / invariants**:
- Row count in the QIF file (number of `^`-terminated records) MUST equal the
  number of data rows in the source CSV (FR-002).
- The file MUST exist even when the source CSV has zero data rows (FR-011) —
  in that case the file contains only the header line.
- Generating this file MUST NOT modify the source CSV file (FR-010).

## QIF Transaction Record (new)

One per source CSV row, in source row order.

| Line prefix | Field  | Required?              | Source                                             | Transform                                             |
|-------------|--------|--------------------------|-----------------------------------------------------|--------------------------------------------------------|
| `D`         | Date   | Always                  | CSV `Date` (`YYYY/MM/DD`)                            | Reformatted to `MM/DD/YYYY` (research.md §2)            |
| `P`         | Payee  | Always                  | CSV `Payee`                                          | Newlines neutralized to spaces (research.md §5)         |
| `M`         | Memo   | **Omitted** when CSV Memo is `""` | CSV `Memo`                                    | Newlines neutralized to spaces; line omitted if empty (FR-007) |
| `T`         | Amount | Always                  | CSV `Amount`                                          | Copied verbatim — no independent sign logic (research.md §3) |
| `^`         | —      | Always, terminates the record | —                                              | Literal end-of-record marker                            |

**Validation / invariants**:
- `T` amount sign MUST exactly match the sign already present in the source
  CSV `Amount` column (FR-005) — no re-derivation from a raw/original amount.
- `D` date MUST represent the same calendar date as the source CSV `Date`
  value, only reformatted (FR-006).
- `M` line MUST be entirely absent (not an empty `M` line) when the source
  Memo is empty (FR-007).
- Embedded `\r`/`\n` characters in `Payee`/`Memo` MUST NOT appear in the
  written field — they are collapsed to a single space (FR-012). No other
  characters (commas, double quotes) are altered.
