"""DaviBank pipeline regression tests.

Compares script output against provided sample files using semantic comparison.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from conftest import (
    FIXTURES_DIR, parse_csv_rows, parse_ynab_rows, assert_rows_match, parse_date_tuple,
)
import davi_stage1
import davi_stage2
import davi_stage3


INPUT_FILE = FIXTURES_DIR / 'DaviBank Sample-in.xls'
EXPECTED_OUT1 = FIXTURES_DIR / 'DaviBank Sample-out1.csv'
EXPECTED_OUT2_CRC = FIXTURES_DIR / 'DaviBank Sample-out2-crc.csv'
EXPECTED_OUT2_USD = FIXTURES_DIR / 'DaviBank Sample-out2-usd.csv'
EXPECTED_OUT3_CRC = FIXTURES_DIR / 'DaviBank Sample-out3-crc.csv'
EXPECTED_OUT3_USD = FIXTURES_DIR / 'DaviBank Sample-out3-usd.csv'


def parse_davi_rows(path):
    """Parse a DaviBank 6-column CSV into semantic tuples.

    The date field (index 1) is normalized to a (year, month, day) tuple to
    allow semantic comparison regardless of whether the sample file has D/M/YY
    (Excel artifact) or DD/MM/YYYY (pipeline output).
    """
    rows = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or i == 0:
                continue
            parts = [p.strip() for p in line.split(',', 5)]
            if len(parts) >= 4:
                # Normalize date in column 1 unless this is a card separator row
                if parts[0] != 'Tarjeta Número:' and parts[1]:
                    parts[1] = parse_date_tuple(parts[1])
                rows.append(tuple(parts))
    return rows


class TestDaviStage1:
    def test_row_count(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        gen = parse_davi_rows(out)
        exp = parse_davi_rows(EXPECTED_OUT1)
        assert len(gen) == len(exp), f"Row count: {len(gen)} vs expected {len(exp)}"

    def test_header_preserved(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            header = f.readline().strip()
        assert 'Número de Referencia' in header
        assert 'Fecha de Movimiento' in header

    def test_card_separators_present(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert 'Tarjeta Número:' in content

    def test_no_empty_trailing_rows(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert 'Rango de fechas' not in content

    def test_content_matches_sample(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        gen = parse_davi_rows(out)
        exp = parse_davi_rows(EXPECTED_OUT1)
        assert_rows_match(gen, exp, "DaviStage1")


class TestDaviStage2:
    @pytest.fixture(autouse=True)
    def run_stage1(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, self.out1)

    def test_crc_row_count(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        gen = parse_davi_rows(crc)
        exp = parse_davi_rows(EXPECTED_OUT2_CRC)
        assert len(gen) == len(exp)

    def test_usd_row_count(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        gen = parse_davi_rows(usd)
        exp = parse_davi_rows(EXPECTED_OUT2_USD)
        assert len(gen) == len(exp)

    def test_no_card_separators(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        for path in [crc, usd]:
            with open(path) as f:
                content = f.read()
            assert 'Tarjeta Número:' not in content

    def test_crc_all_crc_currency(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        rows = parse_davi_rows(crc)
        for row in rows:
            assert row[4] == 'CRC', f"Non-CRC row in CRC file: {row}"

    def test_usd_all_usd_currency(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        rows = parse_davi_rows(usd)
        for row in rows:
            assert row[4] == 'USD', f"Non-USD row in USD file: {row}"

    def test_crc_content_matches(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        gen = parse_davi_rows(crc)
        exp = parse_davi_rows(EXPECTED_OUT2_CRC)
        assert_rows_match(gen, exp, "DaviStage2-CRC")

    def test_usd_content_matches(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage2.process(self.out1, crc, usd)
        gen = parse_davi_rows(usd)
        exp = parse_davi_rows(EXPECTED_OUT2_USD)
        assert_rows_match(gen, exp, "DaviStage2-USD")


class TestDaviStage3:
    @pytest.fixture(autouse=True)
    def run_stages(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        self.out2_crc = tmp_out('out2-crc.csv')
        self.out2_usd = tmp_out('out2-usd.csv')
        davi_stage1.process(INPUT_FILE, self.out1)
        davi_stage2.process(self.out1, self.out2_crc, self.out2_usd)

    def test_crc_ynab_header(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        with open(out) as f:
            header = f.readline().strip()
        assert header == '"Date","Payee","Memo","Amount"'

    def test_crc_dates_yyyy_mm_dd(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        rows = parse_ynab_rows(out)
        for date_tuple, payee, memo, amount in rows:
            assert date_tuple is not None
            assert date_tuple[0] >= 2000

    def test_crc_content_matches(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        gen = parse_ynab_rows(out)
        exp = parse_ynab_rows(EXPECTED_OUT3_CRC)
        assert_rows_match(gen, exp, "DaviStage3-CRC")

    def test_usd_content_matches(self, tmp_out):
        out = tmp_out('out3-usd.csv')
        davi_stage3.process(self.out2_usd, out, currency='usd')
        gen = parse_ynab_rows(out)
        exp = parse_ynab_rows(EXPECTED_OUT3_USD)
        assert_rows_match(gen, exp, "DaviStage3-USD")

    def test_memo_has_reference_numbers(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        rows = parse_ynab_rows(out)
        # At least some rows should have non-empty memos (reference numbers)
        memos = [r[2] for r in rows if r[2]]
        assert len(memos) > 0, "No reference numbers found in Memo column"

    def test_all_fields_quoted(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        with open(out) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('","')
                assert parts[0].startswith('"'), f"First field not quoted: {line}"
                assert parts[-1].endswith('"'), f"Last field not quoted: {line}"
