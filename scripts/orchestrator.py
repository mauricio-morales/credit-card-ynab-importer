"""Orchestrator: run a credit card export file through all 3 pipeline stages.

Usage:
    python scripts/orchestrator.py <file1> [file2 ...]

Bank detection:
    .xls  -> DaviBank pipeline
    .csv  -> BAC pipeline

Output naming:
    Input:   "BAC MCB Marzo-in.csv"  or  "BAC MCB Marzo.csv"
    Stage 1: "BAC MCB Marzo-out1.csv"
    Stage 2: "BAC MCB Marzo-out2-crc.csv" / "BAC MCB Marzo-out2-usd.csv"
    Stage 3: "BAC MCB Marzo-out3-crc.csv" / "BAC MCB Marzo-out3-usd.csv"

All output files are written to the same directory as the input file.
"""

import sys
from pathlib import Path

# Allow importing stage scripts from the same directory
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import bac_stage1
import bac_stage2
import bac_stage3
import davi_stage1
import davi_stage2
import davi_stage3


def base_name(input_path: Path) -> str:
    """Return the base name without a trailing '-in' suffix and without extension."""
    stem = input_path.stem
    if stem.endswith('-in'):
        stem = stem[:-3]
    return stem


def run_bac(input_path: Path):
    """Run a BAC CSV file through all 3 stages."""
    d = input_path.parent
    base = base_name(input_path)

    out1 = d / f"{base}-out1.csv"
    out2_crc = d / f"{base}-out2-crc.csv"
    out2_usd = d / f"{base}-out2-usd.csv"
    out3_crc = d / f"{base}-out3-crc.csv"
    out3_usd = d / f"{base}-out3-usd.csv"

    print(f"[BAC] Stage 1: {input_path.name} -> {out1.name}")
    bac_stage1.process(input_path, out1)

    print(f"[BAC] Stage 2: {out1.name} -> {out2_crc.name}, {out2_usd.name}")
    bac_stage2.process(out1, out2_crc, out2_usd)

    print(f"[BAC] Stage 3 CRC: {out2_crc.name} -> {out3_crc.name}")
    bac_stage3.process(out2_crc, out3_crc, currency='crc')

    print(f"[BAC] Stage 3 USD: {out2_usd.name} -> {out3_usd.name}")
    bac_stage3.process(out2_usd, out3_usd, currency='usd')

    print(f"[BAC] Done. YNAB files: {out3_crc.name}, {out3_usd.name}")


def run_davi(input_path: Path):
    """Run a DaviBank XLS file through all 3 stages."""
    d = input_path.parent
    base = base_name(input_path)

    out1 = d / f"{base}-out1.csv"
    out2_crc = d / f"{base}-out2-crc.csv"
    out2_usd = d / f"{base}-out2-usd.csv"
    out3_crc = d / f"{base}-out3-crc.csv"
    out3_usd = d / f"{base}-out3-usd.csv"

    print(f"[DaviBank] Stage 1: {input_path.name} -> {out1.name}")
    davi_stage1.process(input_path, out1)

    print(f"[DaviBank] Stage 2: {out1.name} -> {out2_crc.name}, {out2_usd.name}")
    davi_stage2.process(out1, out2_crc, out2_usd)

    print(f"[DaviBank] Stage 3 CRC: {out2_crc.name} -> {out3_crc.name}")
    davi_stage3.process(out2_crc, out3_crc, currency='crc')

    print(f"[DaviBank] Stage 3 USD: {out2_usd.name} -> {out3_usd.name}")
    davi_stage3.process(out2_usd, out3_usd, currency='usd')

    print(f"[DaviBank] Done. YNAB files: {out3_crc.name}, {out3_usd.name}")


def run(input_path: Path):
    ext = input_path.suffix.lower()
    if ext == '.xls':
        run_davi(input_path)
    elif ext == '.csv':
        run_bac(input_path)
    else:
        print(f"ERROR: Unsupported file type '{ext}' for {input_path.name}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/orchestrator.py <file1> [file2 ...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        run(path)
