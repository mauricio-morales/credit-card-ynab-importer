"""Shared test fixtures and comparison helpers."""

import csv
import os
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / 'data'
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


@pytest.fixture
def data_dir():
    return DATA_DIR


@pytest.fixture
def tmp_out(tmp_path):
    """Return a function that generates temp output paths."""
    def _make(name):
        return tmp_path / name
    return _make


def parse_date_tuple(date_str):
    """Parse a date string (DD/MM/YYYY, D/M/YY, or YYYY/MM/DD) into a (year, month, day) tuple."""
    date_str = date_str.strip()
    parts = date_str.split('/')
    if len(parts) != 3:
        return None
    nums = [int(p) for p in parts]
    if nums[0] > 100:  # YYYY/MM/DD
        return (nums[0], nums[1], nums[2])
    if nums[2] > 100:  # DD/MM/YYYY
        return (nums[2], nums[1], nums[0])
    # D/M/YY
    return (nums[2] + 2000, nums[1], nums[0])


def parse_csv_rows(path, skip_header=True):
    """Parse a CSV file into a list of lists (raw string values, stripped)."""
    rows = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if skip_header and i == 0:
                continue
            parts = line.split(',', 3)
            rows.append([p.strip() for p in parts])
    return rows


def parse_ynab_rows(path):
    """Parse a YNAB CSV file into semantic tuples: (date_tuple, payee, memo, amount)."""
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 4:
                continue
            date_tuple = parse_date_tuple(row[0])
            payee = row[1].strip()
            memo = row[2].strip()
            amount = row[3].strip()
            rows.append((date_tuple, payee, memo, amount))
    return rows


def assert_rows_match(generated_rows, expected_rows, label=""):
    """Assert that two lists of semantic row tuples match."""
    prefix = f"[{label}] " if label else ""
    assert len(generated_rows) == len(expected_rows), \
        f"{prefix}Row count mismatch: {len(generated_rows)} vs {len(expected_rows)}"
    for i, (gen, exp) in enumerate(zip(generated_rows, expected_rows)):
        assert gen == exp, f"{prefix}Row {i} mismatch:\n  Generated: {gen}\n  Expected:  {exp}"
