#!/usr/bin/env python3
"""DaviBank Stage 1: XLS -> CSV conversion.

Reads old-format .xls file and outputs CSV preserving all rows including card separators.
"""

import sys
from pathlib import Path

import xlrd


def format_number(s):
    """Strip trailing .00 from number strings."""
    s = s.strip()
    if not s:
        return s
    if '.' in s:
        try:
            float(s)
            s = s.rstrip('0').rstrip('.')
        except ValueError:
            pass
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

    book = xlrd.open_workbook(str(input_path))
    sheet = book.sheet_by_index(0)

    output_lines = []

    for row_idx in range(sheet.nrows):
        cells = []
        for col_idx in range(sheet.ncols):
            cell = sheet.cell(row_idx, col_idx)
            if cell.ctype == xlrd.XL_CELL_EMPTY:
                cells.append('')
            else:
                cells.append(str(cell.value).strip())

        # Row 0 is the header
        if row_idx == 0:
            output_lines.append(','.join(cells) + '\n')
            continue

        # Skip fully empty rows
        if all(c == '' for c in cells):
            continue

        # Skip footer/metadata rows (e.g., "Rango de fechas")
        if cells[0] and not cells[1] and not cells[2] and cells[0] != 'Tarjeta Número:':
            continue

        # Card separator rows: first cell is "Tarjeta Número:"
        if cells[0] == 'Tarjeta Número:':
            output_lines.append(f"{cells[0]},{cells[1]},,,,\n")
            continue

        # Data rows: format the amount (col 3)
        ref = cells[0]
        date = cells[1]
        desc = cells[2]
        amount = format_number(cells[3])
        currency = cells[4]
        txn_type = cells[5]
        output_lines.append(f"{ref},{date},{desc},{amount},{currency},{txn_type}\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    return str(output_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python davi_stage1.py <input_file> [output_file]")
        sys.exit(1)
    result = process(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Output: {result}")
