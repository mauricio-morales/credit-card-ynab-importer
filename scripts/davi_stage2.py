#!/usr/bin/env python3
"""DaviBank Stage 2: Split CSV into CRC and USD files.

Removes card separator rows, normalizes dates to DD/MM/YYYY, and splits by Moneda column.
"""

import csv
import sys
from pathlib import Path


def normalize_date(date_str):
    """Normalize D/M/YY or DD/MM/YYYY to DD/MM/YYYY."""
    date_str = date_str.strip()
    if not date_str:
        return date_str
    parts = date_str.split('/')
    if len(parts) != 3:
        return date_str
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if year < 100:
        year += 2000
    return f"{day:02d}/{month:02d}/{year:04d}"


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

    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))

    header = rows[0] if rows else []
    crc_rows = [header]
    usd_rows = [header]

    for parts in rows[1:]:
        if not parts:
            continue
        if len(parts) < 6:
            continue

        ref, date, desc, amount, currency, txn_type = [p.strip() for p in parts[:6]]

        # Skip card separator rows
        if ref == 'Tarjeta Número:':
            continue

        # Normalize date
        date = normalize_date(date)

        rebuilt = [ref, date, desc, amount, currency, txn_type]

        if currency == 'CRC':
            crc_rows.append(rebuilt)
        elif currency == 'USD':
            usd_rows.append(rebuilt)

    with open(output_crc_path, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, lineterminator='\n').writerows(crc_rows)

    with open(output_usd_path, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, lineterminator='\n').writerows(usd_rows)

    return str(output_crc_path), str(output_usd_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python davi_stage2.py <input_file>")
        sys.exit(1)
    crc, usd = process(sys.argv[1])
    print(f"CRC output: {crc}")
    print(f"USD output: {usd}")
