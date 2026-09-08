#!/usr/bin/env python3
"""Convert a finished out3 YNAB CSV file into a sibling QIF file.

Output: "!Type:Bank" header followed by one D/P/M/T/^ record per CSV data
row, in source row order. See contracts/qif-output-format.md for the grammar.
"""

import csv
import sys
from pathlib import Path


def _neutralize(text: str) -> str:
    """Collapse embedded \\r\\n, \\r, or \\n into a single space."""
    return text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')


def _reformat_date(date_str: str) -> str:
    """Reformat an out3 YYYY/MM/DD date to QIF's MM/DD/YYYY."""
    year, month, day = date_str.split('/')
    return f"{month}/{day}/{year}"


def convert_csv_to_qif(csv_path, qif_path) -> str:
    """Read a finished out3 YNAB CSV file and write its QIF equivalent.

    Reads `csv_path` (the "Date","Payee","Memo","Amount" file already
    written by bac_stage3.process()/davi_stage3.process()) and writes a
    QIF bank-transaction file to `qif_path`, one record per CSV data row,
    in the same order. Does not read or write `csv_path` itself beyond
    opening it for reading. Returns str(qif_path).
    """
    qif_path = Path(qif_path)

    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        rows = list(reader)

    lines = ['!Type:Bank\n']
    for date, payee, memo, amount in rows:
        lines.append(f'D{_reformat_date(date)}\n')
        lines.append(f'P{_neutralize(payee)}\n')
        if memo:
            lines.append(f'M{_neutralize(memo)}\n')
        lines.append(f'T{amount}\n')
        lines.append('^\n')

    with open(qif_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)

    return str(qif_path)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python qif_export.py <csv_path> <qif_path>")
        sys.exit(1)
    result = convert_csv_to_qif(sys.argv[1], sys.argv[2])
    print(f"Output: {result}")
