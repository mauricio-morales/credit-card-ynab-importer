#!/usr/bin/env python3
"""BAC Stage 1: Raw bank CSV -> cleaned CSV.

Removes header/footer metadata, formats numbers, preserves transactions and card separators.
"""

import sys
from pathlib import Path


def format_number(s):
    """Strip whitespace and trailing .00 from number strings."""
    s = s.strip()
    if not s:
        return s
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


def process(input_path, output_path=None):
    input_path = Path(input_path)
    if output_path is None:
        base = input_path.stem
        if base.endswith('-in'):
            base = base[:-3]
        output_path = input_path.parent / f"{base}-out1.csv"
    else:
        output_path = Path(output_path)

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(input_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
            print(f"[Warning] File {input_path} is not UTF-8 encoded. Read as latin-1.")
        except UnicodeDecodeError:
            print(f"[Error] Could not decode {input_path} as UTF-8 or latin-1. Please check the file encoding.")
            raise

    output_lines = []

    # Line 0: product header (9 fields) - skip
    # Line 1: cardholder info (9 fields) - skip
    # Line 2: data header "Date, , Local, Dollars" - keep
    # Line 3: "Previous balance" - skip
    output_lines.append("Date,,Local,Dollars\n")

    # Process from line 4 onward
    for line in lines[4:]:
        # Stop at footer marker
        if 'REVERSION INTERES CORRIENTES PERIODO' in line:
            break

        parts = line.split(',', 3)
        if len(parts) == 4:
            date = parts[0].strip()
            desc = parts[1]  # preserve leading space
            local = format_number(parts[2])
            dollars = format_number(parts[3])
            output_lines.append(f"{date},{desc},{local},{dollars}\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    return str(output_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python bac_stage1.py <input_file> [output_file]")
        sys.exit(1)
    result = process(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Output: {result}")
