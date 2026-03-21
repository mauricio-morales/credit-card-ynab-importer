#!/usr/bin/env python3
"""BAC Stage 2: Split cleaned CSV into CRC and USD files.

Removes card separator rows and splits transactions by currency.
"""

import re
import sys
from pathlib import Path

CARD_PATTERN = re.compile(r'^\d{4}-\d{2}\*\*-\*\*\*\*-\d{4}$')


def is_card_separator(desc):
    """Check if description is a masked card number."""
    return bool(CARD_PATTERN.match(desc.strip()))


def process(input_path, output_crc_path=None, output_usd_path=None):
    input_path = Path(input_path)
    base = input_path.stem
    if base.endswith('-out1'):
        base = base[:-5]

    if output_crc_path is None:
        output_crc_path = input_path.parent / f"{base}-out2-crc.csv"
    else:
        output_crc_path = Path(output_crc_path)

    if output_usd_path is None:
        output_usd_path = input_path.parent / f"{base}-out2-usd.csv"
    else:
        output_usd_path = Path(output_usd_path)

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header = "Date,Description,Local,Dollars\n"
    crc_lines = [header]
    usd_lines = [header]

    # Skip header line (line 0)
    for line in lines[1:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        parts = line.split(',', 3)
        if len(parts) != 4:
            continue

        desc = parts[1]
        local_str = parts[2].strip()
        dollars_str = parts[3].strip()

        # Skip card separator rows
        if is_card_separator(desc):
            continue

        local = float(local_str) if local_str else 0.0
        dollars = float(dollars_str) if dollars_str else 0.0

        if local != 0:
            crc_lines.append(line if line.endswith('\n') else line + '\n')
        elif dollars != 0:
            usd_lines.append(line if line.endswith('\n') else line + '\n')

    with open(output_crc_path, 'w', encoding='utf-8') as f:
        f.writelines(crc_lines)

    with open(output_usd_path, 'w', encoding='utf-8') as f:
        f.writelines(usd_lines)

    return str(output_crc_path), str(output_usd_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python bac_stage2.py <input_file>")
        sys.exit(1)
    crc, usd = process(sys.argv[1])
    print(f"CRC output: {crc}")
    print(f"USD output: {usd}")
