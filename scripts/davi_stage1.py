#!/usr/bin/env python3
"""DaviBank Stage 1: XLSX -> CSV conversion.

Reads a Scotia/DaviBank .xlsx statement export and outputs CSV preserving all
rows including card separators.
"""

import csv
import datetime
import sys
import zipfile
from pathlib import Path

import openpyxl

EXPECTED_HEADERS = [
    'Número de Referencia',
    'Fecha de Movimiento',
    'Descripción',
    'Monto',
    'Moneda',
    'Tipo',
]


class LegacyFormatError(Exception):
    """Raised when the selected file is a legacy .xls export."""

    def __init__(self, message=None):
        self.user_message = message or (
            ".xls files are no longer supported — Scotia/DaviBank now exports "
            "statements as .xlsx. Please re-export the statement as .xlsx and try again."
        )
        super().__init__(self.user_message)


class UnreadableFileError(Exception):
    """Raised when the selected file cannot be opened as a valid .xlsx workbook."""

    def __init__(self, message=None):
        self.user_message = message or (
            "Couldn't read this file as a Scotia/DaviBank .xlsx statement — it "
            "may be corrupted or not a spreadsheet at all."
        )
        super().__init__(self.user_message)


class MissingColumnsError(Exception):
    """Raised when the header row doesn't contain the expected six columns."""

    def __init__(self, message=None):
        self.user_message = message or (
            "This file's layout doesn't match the expected Scotia/DaviBank "
            "statement columns."
        )
        super().__init__(self.user_message)


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


def _text_value(value):
    """Render a generic (non-date, non-amount) cell value as stripped text."""
    if value is None:
        return ''
    return str(value).strip()


def _format_date_value(value):
    """Normalize a Fecha de Movimiento cell value to DD/MM/YYYY."""
    if value is None:
        return ''
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime('%d/%m/%Y')
    return str(value).strip()


def _format_amount_value(value):
    """Normalize a Monto cell value (native numeric or text) to a number string."""
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        return format_number(f"{value:.2f}")
    return format_number(str(value).strip())


def _load_worksheet(input_path):
    """Open a Scotia/DaviBank .xlsx workbook and return its first worksheet."""
    if input_path.suffix.lower() == '.xls':
        raise LegacyFormatError()

    try:
        workbook = openpyxl.load_workbook(str(input_path), read_only=True, data_only=True)
    except (zipfile.BadZipFile, OSError, KeyError, ValueError) as exc:
        raise UnreadableFileError() from exc

    return workbook.worksheets[0]


def process(input_path, output_path=None):
    input_path = Path(input_path)
    if output_path is None:
        base = input_path.stem
        if base.endswith('-in'):
            base = base[:-3]
        output_path = input_path.parent / f"{base}-out1.csv"
    else:
        output_path = Path(output_path)

    worksheet = _load_worksheet(input_path)

    rows = []

    for row_idx, row in enumerate(worksheet.iter_rows()):
        values = [cell.value for cell in row]
        if len(values) < 6:
            values = values + [None] * (6 - len(values))

        # Row 0 is the header
        if row_idx == 0:
            header = [_text_value(v) for v in values[:6]]
            if header != EXPECTED_HEADERS:
                missing = [h for h in EXPECTED_HEADERS if h not in header]
                if missing:
                    detail = f"missing column(s): {', '.join(missing)}"
                else:
                    detail = f"expected {EXPECTED_HEADERS}, found {header}"
                raise MissingColumnsError(
                    "This file's layout doesn't match the expected Scotia/DaviBank "
                    f"statement columns ({detail})."
                )
            rows.append(header)
            continue

        # Skip fully empty rows
        if all(v is None for v in values[:6]):
            continue

        cell0 = _text_value(values[0])

        # Skip footer/metadata rows (e.g., "Rango de fechas")
        if cell0 and values[1] is None and values[2] is None and cell0 != 'Tarjeta Número:':
            continue

        # Card separator rows: first cell is "Tarjeta Número:"
        if cell0 == 'Tarjeta Número:':
            card_num = _text_value(values[1])
            rows.append([cell0, card_num, '', '', '', ''])
            continue

        # Data rows
        ref = cell0
        date = _format_date_value(values[1])
        desc = _text_value(values[2])
        amount = _format_amount_value(values[3])
        currency = _text_value(values[4])
        txn_type = _text_value(values[5])
        rows.append([ref, date, desc, amount, currency, txn_type])

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerows(rows)

    return str(output_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python davi_stage1.py <input_file> [output_file]")
        sys.exit(1)
    result = process(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Output: {result}")
