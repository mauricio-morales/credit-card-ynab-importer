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

DaviBank XLSX
  - Full card numbers        → 4573099990000001 / 4573099990000002
  - Payment tail (****-7071) → ****-0001

Usage
-----
    python scripts/generate_fixtures.py
"""

from pathlib import Path

import openpyxl

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
    ("4573060030758398", "4573099990000001"),
    ("4573060014128121", "4573099990000002"),
    ("****-8398", "****-0001"),
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


def obfuscate_davi_xlsx(src: Path, dst: Path) -> None:
    src_wb = openpyxl.load_workbook(str(src), read_only=True, data_only=True)
    src_ws = src_wb.worksheets[0]

    dst_wb = openpyxl.Workbook()
    dst_ws = dst_wb.active
    dst_ws.title = "Sheet1"

    for row_idx, row in enumerate(src_ws.iter_rows(), start=1):
        for col_idx, cell in enumerate(row, start=1):
            if cell.value is None:
                dst_ws.cell(row=row_idx, column=col_idx, value="")
            else:
                val = str(cell.value).strip()
                for real, fake in DAVI_SUBS:
                    val = val.replace(real, fake)
                dst_ws.cell(row=row_idx, column=col_idx, value=val)

    dst_wb.save(str(dst))
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
    davi_src = DATA_DIR / "DaviBank Visa-in.xlsx"
    if davi_src.exists():
        obfuscate_davi_xlsx(davi_src, FIXTURES_DIR / "DaviBank Sample-in.xlsx")
    else:
        print("  skipped (not found): DaviBank Visa-in.xlsx")

    print("Done. Now run:  python scripts/generate_expected_outputs.py")


if __name__ == "__main__":
    main()
