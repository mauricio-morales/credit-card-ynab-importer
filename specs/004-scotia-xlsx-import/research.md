# Research: Scotia/DaviBank XLSX Import

**Feature**: 004-scotia-xlsx-import | **Date**: 2026-08-09

## 1. XLSX parsing library

**Decision**: Use `openpyxl` (≥3.1) to read the `.xlsx` workbook, replacing `xlrd`.

**Rationale**:
- `xlrd` dropped all `.xlsx` support at v2.0 (mid-2020) and now only reads legacy `.xls` (OLE2) files — it is structurally incapable of reading the new format, so it cannot be reused for this feature.
- `openpyxl` is the standard pure-Python library for `.xlsx`/OOXML, has no C-extension build requirements (important for a personal macOS tool with no packaging pipeline), and is already present in the project's Python environment.
- `read_only=True` mode streams rows without loading the whole worksheet DOM, which matches Principle V (Simplicity) and keeps behavior close to `xlrd`'s row/col iteration model already used in `davi_stage1.py`.

**Alternatives considered**:
- `pandas` + `openpyxl` engine — rejected: pandas is a large transitive dependency (numpy, etc.) for what is a 6-column, few-dozen-row file; the project has no other pandas usage and Principle V forbids unjustified complexity.
- Keep `xlrd` and add `openpyxl` side-by-side to support both `.xls` and `.xlsx` — rejected: the bank has discontinued `.xls` entirely (FR-009), so dual-format parsing support has no real user, and it doubles the surface area to maintain and test for zero benefit. A `.xls` file is still handled (FR-007), but only by extension-sniffing to produce a clear rejection message, not by actually parsing it.

## 2. Verified sample-file layout (`Scotia Visa.xlsx`)

Inspected directly with `openpyxl` (`docs sample: /Users/mmorales/Downloads/Banks/Scotia Visa.xlsx`, 1 sheet named "Movimientos", 29 rows × 6 columns):

- Row 0 (header): `Número de Referencia | Fecha de Movimiento | Descripción | Monto | Moneda | Tipo` — identical column names/order to the legacy `.xls` format.
- Card-section marker rows: `A = "Tarjeta Número:"`, `B = <card number>`, `C..F` are empty numeric cells (`cell.value is None`, `cell.data_type == 'n'`) rather than the `xlrd.XL_CELL_EMPTY` sentinel used previously — the emptiness check must change accordingly but the row shape is unchanged.
- Data rows: every field (`Monto` included) is stored as a **string** cell (`cell.data_type == 's'`), e.g. `'-181205.07'`, matching how `.xls` stored them as text. No native numeric or native date cell was observed in the reference sample.
- No trailing footer/summary row (e.g. "Rango de fechas") is present in this particular sample, but the legacy `.xls` skip-rule (a row whose first cell is non-empty while the 2nd/3rd cells are empty, and which is not a card marker) is retained defensively per the spec's edge cases and Assumptions.
- Only one worksheet exists in the sample; per spec Assumptions/Edge Cases, only the first/primary sheet (`wb.worksheets[0]`) is read regardless of how many sheets a future export might contain.

**Conclusion**: the transaction schema, card-section markers, and skip-row rules already implemented in `davi_stage1.py` remain correct — only the cell-access layer (xlrd → openpyxl) changes.

## 3. Defensive handling: native date & numeric cells

**Decision**: Even though the reference sample stores every value as text, Stage 1 must handle the case where a cell is a native `datetime.datetime`/`datetime.date` (`cell.data_type == 'd'`) or native number (`cell.data_type == 'n'` with a non-None value), per FR-006 and the spec's edge cases.

- Date cells: if `isinstance(cell.value, (datetime.date, datetime.datetime))`, format as `DD/MM/YYYY` before handing off to Stage 2 (which already expects that shape from `normalize_date`); otherwise treat as a plain string, unchanged from today.
- Amount cells: if a numeric cell arrives instead of a string, convert with a rule equivalent to the existing `format_number()` (strip a trailing `.00`, preserve real decimals) before writing to the intermediate CSV, so Stage 2/3 behavior (which operate on strings) is unaffected.

**Rationale**: Excel/OOXML permits either representation for the same visual value, and `.xls`→`.xlsx` migrations are a common time a bank's export tooling silently switches from text-formatted to natively-typed cells. Handling both now avoids a repeat of this exact migration pain if Scotia changes its export tooling again.

**Alternatives considered**: Ignore native types and assume text-only, matching only the current sample — rejected: FR-006 explicitly requires both to work, and the cost of handling both is a few lines in Stage 1.

## 4. `.xls` rejection strategy (FR-007)

**Decision**: Detect legacy files by extension (`Path(input_path).suffix.lower() == '.xls'`) in `davi_stage1.process()`/the orchestrator, and raise a dedicated `UnsupportedLegacyFormatError` (or equivalent) with a plain-language message *before* attempting to open the file with any XLS/XLSX library.

**Rationale**: The goal is a friendly message, not a best-effort legacy parse. Actually opening `.xls` files would require reintroducing `xlrd` (or another OLE2 reader) purely to fail gracefully, which is unjustified complexity (Principle V) for a format the bank no longer issues. Extension-based detection is also the same technique the orchestrator already uses to route BAC vs. DaviBank files (`scripts/orchestrator.py:95`), so this is consistent with the existing pattern, not a new one.

**Alternatives considered**: Attempt to open with `openpyxl` and catch the resulting exception (openpyxl raises `zipfile.BadZipFile` on a `.xls`/OLE2 file since it isn't a ZIP) — rejected as the primary mechanism because the resulting message would be generic/technical and wouldn't distinguish "this is an old .xls file" from "this file is corrupt" (which FR-008 also requires distinguishing, with its own plain-language message). Extension sniffing gives an exact, deliberate message for the known legacy case; the generic corrupt/unreadable-file path (FR-008) is handled separately by catching `openpyxl`/`zipfile` errors when a `.xlsx`-named file fails to open.

## 5. Dependency & constitution impact

**Decision**: `requirements.txt` drops `xlrd>=2.0.1` and `xlwt>=1.3` (the latter was fixture-generation-only, used to *write* `.xls` fixtures — no longer needed once fixtures are `.xlsx`), and adds `openpyxl>=3.1`.

**Constitution impact** (flagged for the user, not silently resolved): `.specify/memory/constitution.md`'s **Technical Stack** section currently states *"xlrd (≥2.0.1) for DaviBank `.xls` parsing — no other XLS library"* and Principle V states *"Only BAC (`.csv`) and DaviBank (`.xls`) inputs are supported"*. Both sentences are now factually wrong for this feature and require a constitution amendment (MINOR bump — this changes an allowed-dependency/format list, not a Core Principle's meaning). This plan proceeds because the deviation is externally forced (the bank discontinued `.xls`) and the feature spec (already approved) assumes it; see `Complexity Tracking` in `plan.md`. **Action required**: run `/speckit-constitution` to update these two references (`.xls`→`.xlsx`, `xlrd`→`openpyxl`) either alongside or immediately after this feature ships.

## 6. Fixture strategy

**Decision**:
- Add a new obfuscated `.xlsx` fixture (`tests/fixtures/DaviBank Sample-in.xlsx`) generated the same way the existing `.xls` fixture was: copy the real reference file into the git-ignored `data/` directory, then extend `scripts/generate_fixtures.py` to write an obfuscated `.xlsx` copy (via `openpyxl`, replacing the `xlwt`-based `obfuscate_davi_xls`) using the same `DAVI_SUBS` card-number substitutions already defined.
- Keep the existing committed `tests/fixtures/DaviBank Sample-in.xls` file as-is; it is reused (not regenerated) as the input for the "legacy `.xls` file is rejected" regression test (User Story 2).
- Hand-author small synthetic (non-real-data) fixtures for the negative/edge-case tests that have no real-world counterpart to obfuscate: a file missing the `Monto` column (US3), a header-only file with zero transaction rows (edge case), a file with a trailing footer/summary row (edge case), a file with a native-`datetime` date cell (edge case), and a two-sheet workbook (edge case).

**Rationale**: This mirrors the project's existing "obfuscate real data, hand-author edge cases" fixture pattern (`scripts/generate_fixtures.py`) instead of inventing a new one, and avoids ever committing the user's real transaction data (merchant names, real amounts) from `Scotia Visa.xlsx` directly into the repository.
