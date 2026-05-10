#!/usr/bin/env python3
"""Run the full pipeline on fixture inputs to regenerate expected output files.

Expected outputs are stored alongside the input fixtures in tests/fixtures/ and
are committed to the repo so the test suite can run without the real data/ files.

Usage
-----
    python scripts/generate_expected_outputs.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

FIXTURES_DIR = ROOT / "tests" / "fixtures"

import bac_stage1
import bac_stage2
import bac_stage3
import davi_stage1
import davi_stage2
import davi_stage3


def run_bac(prefix: str) -> None:
    infile = FIXTURES_DIR / f"{prefix}-in.csv"
    if not infile.exists():
        print(f"  skipped (not found): {infile.name}")
        return

    out1     = FIXTURES_DIR / f"{prefix}-out1.csv"
    out2_crc = FIXTURES_DIR / f"{prefix}-out2-crc.csv"
    out2_usd = FIXTURES_DIR / f"{prefix}-out2-usd.csv"
    out3_crc = FIXTURES_DIR / f"{prefix}-out3-crc.csv"
    out3_usd = FIXTURES_DIR / f"{prefix}-out3-usd.csv"

    bac_stage1.process(infile, out1)
    bac_stage2.process(out1, out2_crc, out2_usd)
    bac_stage3.process(out2_crc, out3_crc, currency="crc")
    bac_stage3.process(out2_usd, out3_usd, currency="usd")

    for p in [out1, out2_crc, out2_usd, out3_crc, out3_usd]:
        print(f"  written: {p.relative_to(ROOT)}")


def run_davi(prefix: str) -> None:
    infile = FIXTURES_DIR / f"{prefix}-in.xls"
    if not infile.exists():
        print(f"  skipped (not found): {infile.name}")
        return

    out1     = FIXTURES_DIR / f"{prefix}-out1.csv"
    out2_crc = FIXTURES_DIR / f"{prefix}-out2-crc.csv"
    out2_usd = FIXTURES_DIR / f"{prefix}-out2-usd.csv"
    out3_crc = FIXTURES_DIR / f"{prefix}-out3-crc.csv"
    out3_usd = FIXTURES_DIR / f"{prefix}-out3-usd.csv"

    davi_stage1.process(infile, out1)
    davi_stage2.process(out1, out2_crc, out2_usd)
    davi_stage3.process(out2_crc, out3_crc, currency="crc")
    davi_stage3.process(out2_usd, out3_usd, currency="usd")

    for p in [out1, out2_crc, out2_usd, out3_crc, out3_usd]:
        print(f"  written: {p.relative_to(ROOT)}")


def main() -> None:
    print("Generating BAC expected outputs…")
    run_bac("BAC Sample")
    run_bac("BAC Sample2")

    print("Generating DaviBank expected outputs…")
    run_davi("DaviBank Sample")

    print("Done. Commit everything in tests/fixtures/.")


if __name__ == "__main__":
    main()
