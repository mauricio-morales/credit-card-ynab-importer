#!/usr/bin/env python3
"""BAC Stage 3: Convert CRC/USD split files to YNAB import format.

Output: "Date","Payee","Memo","Amount" with YYYY/MM/DD dates.
"""

import sys
from pathlib import Path


def parse_date(date_str):
    """Parse DD/MM/YYYY or D/M/YY date string, return YYYY/MM/DD."""
    date_str = date_str.strip()
    if not date_str:
        return date_str
    parts = date_str.split('/')
    if len(parts) != 3:
        return date_str
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if year < 100:
        year += 2000
    return f"{year:04d}/{month:02d}/{day:02d}"


def csv_quote(s):
    """Wrap string in double quotes, escaping any inner quotes."""
    return '"' + s.replace('"', '""') + '"'


def negate_amount(raw: str) -> str:
    """Flip the sign of an amount string, preserving decimal precision."""
    raw = raw.strip().strip('"')
    try:
        value = -float(raw)
    except ValueError:
        return raw
    if value == int(value):
        return str(int(value))
    return str(value)


def process(input_path, output_path=None, currency=None):
    input_path = Path(input_path)
    stem = input_path.stem

    # Auto-detect currency from filename
    if currency is None:
        if '-out2-usd' in stem or '-usd' in stem.lower():
            currency = 'usd'
        else:
            currency = 'crc'

    use_dollars = currency.lower() == 'usd'

    if output_path is None:
        if '-out2-crc' in stem:
            new_stem = stem.replace('-out2-crc', '-out3-crc')
        elif '-out2-usd' in stem:
            new_stem = stem.replace('-out2-usd', '-out3-usd')
        else:
            new_stem = f"{stem}-out3-{currency}"
        output_path = input_path.parent / f"{new_stem}.csv"
    else:
        output_path = Path(output_path)

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output_lines = ['"Date","Payee","Memo","Amount"\n']

    for line in lines[1:]:  # skip header
        line_stripped = line.strip()
        if not line_stripped:
            continue

        parts = line.split(',', 3)
        if len(parts) != 4:
            continue

        date_raw = parts[0].strip()
        payee = parts[1].strip()
        local = parts[2].strip()
        dollars = parts[3].strip()

        if not date_raw and not payee:
            continue

        date = parse_date(date_raw)
        amount = negate_amount(dollars if use_dollars else local)

        output_lines.append(
            f'{csv_quote(date)},{csv_quote(payee)},{csv_quote("")},{csv_quote(amount)}\n'
        )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    return str(output_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python bac_stage3.py <input_file> [crc|usd]")
        sys.exit(1)
    currency = sys.argv[2] if len(sys.argv) >= 3 else None
    result = process(sys.argv[1], currency=currency)
    print(f"Output: {result}")
