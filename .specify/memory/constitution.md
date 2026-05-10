<!--
SYNC IMPACT REPORT
==================
Version change: (unversioned template) → 1.0.0
New principles added:
  - I. Pipeline-Stage Isolation
  - II. YNAB Output Consistency
  - III. Test-First (NON-NEGOTIABLE)
  - IV. Data Fidelity
  - V. Simplicity (YAGNI)
New sections added:
  - Technical Stack
  - Development Workflow
  - Governance
Templates reviewed:
  - .specify/templates/plan-template.md        ✅ aligned (Constitution Check gate present)
  - .specify/templates/spec-template.md        ✅ aligned (no bank-specific overrides needed)
  - .specify/templates/tasks-template.md       ✅ aligned (test-first discipline reflected)
  - .specify/templates/constitution-template.md ✅ source template, no changes needed
Deferred TODOs: none
-->

# Credit Card → YNAB Importer Constitution

## Core Principles

### I. Pipeline-Stage Isolation

Each bank pipeline MUST be implemented as exactly three discrete, independently
runnable stages:

- **Stage 1** — Raw bank export → cleaned/normalized CSV
- **Stage 2** — Cleaned CSV → split by currency (CRC and USD)
- **Stage 3** — Split CSV → YNAB-format CSV

Stages MUST NOT be coupled: each stage reads from a well-defined input file and
writes to a well-defined output file. An orchestrator script drives stage
execution sequentially. Adding a new bank MUST follow this same three-stage
pattern without exception.

### II. YNAB Output Consistency

All bank pipelines MUST produce identical final output format:

- Columns: `"Date","Payee","Memo","Amount"` (in this order)
- All fields MUST be double-quoted in the CSV
- Dates MUST be formatted as `YYYY/MM/DD`
- Memo MUST be an empty string `""` for BAC; populated from Número de
  Referencia (or empty) for DaviBank

Any deviation from this contract is a breaking change and MUST increment the
MAJOR version of the affected pipeline module.

### III. Test-First (NON-NEGOTIABLE)

Regression tests MUST be written before or alongside implementation — never
after. Tests MUST verify output against known-good sample files.

- Intermediate stages (out1, out2): comparison is **semantic** — same row count,
  same descriptions, same amounts, same row order, dates compared as date
  values (not string equality)
- Final stage (out3): comparison verifies YNAB format compliance including exact
  `YYYY/MM/DD` date formatting and double-quoting

Tests MUST fail on unimplemented code (red) before implementation proceeds
(green).

### IV. Data Fidelity

Transformations MUST preserve source data semantics with zero silent data loss:

- **Number formatting**: trailing `.00` MUST be stripped (`4200.00` → `4200`);
  meaningful decimals MUST be preserved (`3980.50` → `3980.5`)
- **Date normalization**: intermediate stages MUST output `DD/MM/YYYY`
  zero-padded; Stage 3 MUST output `YYYY/MM/DD`; 2-digit years MUST be
  expanded to 4 digits (26 → 2026)
- **Description/Payee text**: MUST be preserved verbatim including internal
  backslashes and whitespace
- **Row ordering**: MUST reflect original source order; no sorting is permitted

### V. Simplicity (YAGNI)

No abstractions beyond what the current two-bank pipeline requires:

- Each stage script MUST be self-contained and independently executable
- Only BAC (`.csv`) and DaviBank (`.xls`) inputs are supported
- No databases, no network calls, no external services
- Complexity MUST be justified; if a simpler approach exists, it MUST be chosen

## Technical Stack

The project MUST use the following technology stack:

- **Language**: Python 3.8+
- **Standard library only** for BAC pipeline: `csv`, `os`, `sys`, `argparse`,
  `re`, `pathlib`
- **xlrd** (≥2.0.1) for DaviBank `.xls` parsing — no other XLS library
- **pytest** (≥7.0) for regression testing
- No databases, no network I/O, no GUI frameworks

Dependencies are declared in `requirements.txt` at the repository root.

## Development Workflow

- The orchestrator (`scripts/orchestrator.py`) auto-detects the bank from the
  file extension: `.csv` → BAC pipeline, `.xls` → DaviBank pipeline
- A trailing `-in` suffix in the input filename MUST be stripped when deriving
  the output base name (`BAC MCB Marzo-in.csv` → base `BAC MCB Marzo`)
- All intermediate files (out1, out2-crc, out2-usd) MUST be written to disk
  alongside the final out3 files — no in-memory-only pipelines
- Output files MUST be written to the same directory as the input file
- The CLI interface MUST accept one or more input file paths as positional
  arguments: `python scripts/orchestrator.py <file1> [file2 ...]`

## Governance

This constitution supersedes all other project practices. Amendments MUST:

1. Update this document with a version bump following semantic versioning:
   - **MAJOR**: removing or redefining a principle; breaking pipeline contracts
   - **MINOR**: adding a new principle, section, or bank pipeline pattern
   - **PATCH**: clarifications, wording refinements, non-semantic changes
2. Document the change in the Sync Impact Report (HTML comment at top)
3. Update `LAST_AMENDED_DATE` to the date of the amendment
4. Verify that all templates and README remain consistent with the updated
   principles

All feature implementations and code reviews MUST verify compliance with the
Core Principles above. The `plan-template.md` Constitution Check gate enforces
this at planning time.

**Version**: 1.0.0 | **Ratified**: 2026-05-10 | **Last Amended**: 2026-05-10
