#!/usr/bin/env python3
"""Generate obfuscated test fixtures from real data files.

Reads from data/ and writes sanitized copies to tests/fixtures/. All PII is
replaced with clearly fake values so the fixture files are safe to commit.

Replacements applied
--------------------
BAC CSV
  - Cardholder name          → SAMPLE/USER FIXTURE
  - Card last-4 digits       → 1001–1004
  - ICE phone numbers        → 55551234 / 55559876
  - Pension reference        → OPPC 10001
  - Medical policy           → CLI010101
  - Insurance policy         → PRFCD10001

DaviBank XLS
  - Full card numbers        → 4573099990000001 / 4573099990000002
  - Payment tail (****-7071) → ****-0001

Usage
-----
    python scripts/generate_fixtures.py

Requires xlwt for the DaviBank XLS output:
    pip install xlwt
"""

import sys
from pathlib import Path

import xlrd

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

# ── BAC CSV substitutions (applied in order) ──────────────────────────────────

BAC_SUBS = [
    ("MAURICIO/MORALES ZUMBADO", "SAMPLE/USER FIXTURE"),
    ("5466-37**-****-7619", "5466-37**-****-1001"),
    ("5466-37**-****-7287", "5466-37**-****-1002"),
    ("5466-37**-****-2972", "5466-37**-****-1003"),
    ("5466-37**-****-6469", "5466-37**-****-1004"),
    ("I.C.E. PAGUELO 17992258", "I.C.E. PAGUELO 55551234"),
    ("I.C.E. PAGUELO 83838789", "I.C.E. PAGUELO 55559876"),
    ("OPPC 48975", "OPPC 10001"),
    ("CLI022187", "CLI010101"),
    ("PRFCD94952", "PRFCD10001"),
]

# ── DaviBank XLS substitutions ────────────────────────────────────────────────

DAVI_SUBS = [
    ("4573060082607071", "4573099990000001"),
    ("4573060070460988", "4573099990000002"),
    ("****-7071", "****-0001"),
]


def obfuscate_bac_csv(src: Path, dst: Path) -> None:
    try:
        text = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = src.read_text(encoding="latin-1")

    for real, fake in BAC_SUBS:
        text = text.replace(real, fake)

    dst.write_text(text, encoding="utf-8")
    print(f"  written: {dst.relative_to(ROOT)}")


def obfuscate_davi_xls(src: Path, dst: Path) -> None:
    try:
        import xlwt
    except ImportError:
        print("ERROR: xlwt is required. Install with:  pip install xlwt", file=sys.stderr)
        sys.exit(1)

    book = xlrd.open_workbook(str(src))
    sheet = book.sheet_by_index(0)

    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Sheet1")

    for row_idx in range(sheet.nrows):
        for col_idx in range(sheet.ncols):
            cell = sheet.cell(row_idx, col_idx)
            if cell.ctype == xlrd.XL_CELL_EMPTY:
                ws.write(row_idx, col_idx, "")
            else:
                val = str(cell.value).strip()
                for real, fake in DAVI_SUBS:
                    val = val.replace(real, fake)
                ws.write(row_idx, col_idx, val)

    wb.save(str(dst))
    print(f"  written: {dst.relative_to(ROOT)}")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating BAC fixtures…")
    for src_name, dst_name in [
        ("BAC MCB Febrero-in.csv", "BAC Sample-in.csv"),
        ("BAC MCB Marzo-in.csv",   "BAC Sample2-in.csv"),
    ]:
        src = DATA_DIR / src_name
        if src.exists():
            obfuscate_bac_csv(src, FIXTURES_DIR / dst_name)
        else:
            print(f"  skipped (not found): {src_name}")

    print("Generating DaviBank fixture…")
    davi_src = DATA_DIR / "DaviBank Visa-in.xls"
    if davi_src.exists():
        obfuscate_davi_xls(davi_src, FIXTURES_DIR / "DaviBank Sample-in.xls")
    else:
        print("  skipped (not found): DaviBank Visa-in.xls")

    print("Done. Now run:  python scripts/generate_expected_outputs.py")


if __name__ == "__main__":
    main()
