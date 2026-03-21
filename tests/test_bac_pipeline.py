"""BAC pipeline regression tests.

Compares script output against provided sample files using semantic comparison
(dates parsed as tuples, amounts compared as strings, descriptions matched exactly).
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from conftest import (
    DATA_DIR, parse_csv_rows, parse_ynab_rows, assert_rows_match, parse_date_tuple,
)
import bac_stage1
import bac_stage2
import bac_stage3


INPUT_FILE = DATA_DIR / 'BAC MCB Febrero-in.csv'
EXPECTED_OUT1 = DATA_DIR / 'BAC MCB Febrero-out1.csv'
EXPECTED_OUT2_CRC = DATA_DIR / 'BAC MCB Febrero-out2-crc.csv'
EXPECTED_OUT2_USD = DATA_DIR / 'BAC MCB Febrero-out2-usd.csv'
EXPECTED_OUT3_CRC = DATA_DIR / 'BAC MCB Febrero-out3-crc.csv'
EXPECTED_OUT3_USD = DATA_DIR / 'BAC MCB Febrero-out3-usd.csv'


class TestBACStage1:
    def test_row_count(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        gen = parse_csv_rows(out)
        exp = parse_csv_rows(EXPECTED_OUT1)
        assert len(gen) == len(exp), f"Row count: {len(gen)} vs expected {len(exp)}"

    def test_no_header_rows(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert 'Pro000000000000duct' not in content
        assert 'MAURICIO/MORALES ZUMBADO' not in content

    def test_no_previous_balance(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert 'Previous balance' not in content

    def test_no_footer(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert 'REVERSION INTERES' not in content
        assert 'TASA MENSUAL' not in content
        assert 'PUNTOS CASH BACK' not in content
        assert 'CURRENT Interest' not in content

    def test_card_separators_present(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        assert '5466-37**-****-7287' in content
        assert '5466-37**-****-2972' in content
        assert '5466-37**-****-6469' in content
        assert '5466-37**-****-7619' in content

    def test_number_formatting(self, tmp_out):
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        with open(out) as f:
            content = f.read()
        # .00 should be stripped
        assert ',4200,' in content  # was 4200.00
        assert ',0\n' in content    # was 0.00
        # meaningful decimals kept
        assert ',11518.99,' in content

    def test_content_matches_sample(self, tmp_out):
        """Semantic comparison: descriptions and amounts must match sample."""
        out = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, out)
        gen = parse_csv_rows(out)
        exp = parse_csv_rows(EXPECTED_OUT1)

        gen_semantic = [(r[1].strip(), r[2], r[3]) for r in gen if len(r) >= 4]
        exp_semantic = [(r[1].strip(), r[2], r[3]) for r in exp if len(r) >= 4]
        assert_rows_match(gen_semantic, exp_semantic, "Stage1")


class TestBACStage2:
    @pytest.fixture(autouse=True)
    def run_stage1(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        bac_stage1.process(INPUT_FILE, self.out1)

    def test_crc_row_count(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        gen = parse_csv_rows(crc)
        exp = parse_csv_rows(EXPECTED_OUT2_CRC)
        assert len(gen) == len(exp)

    def test_usd_row_count(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        gen = parse_csv_rows(usd)
        exp = parse_csv_rows(EXPECTED_OUT2_USD)
        assert len(gen) == len(exp)

    def test_no_card_separators_in_crc(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        with open(crc) as f:
            content = f.read()
        assert '5466-37**-****-' not in content

    def test_no_card_separators_in_usd(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        with open(usd) as f:
            content = f.read()
        assert '5466-37**-****-' not in content

    def test_crc_content_matches(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        gen = parse_csv_rows(crc)
        exp = parse_csv_rows(EXPECTED_OUT2_CRC)
        gen_semantic = [(r[1].strip(), r[2], r[3]) for r in gen if len(r) >= 4]
        exp_semantic = [(r[1].strip(), r[2], r[3]) for r in exp if len(r) >= 4]
        assert_rows_match(gen_semantic, exp_semantic, "Stage2-CRC")

    def test_usd_content_matches(self, tmp_out):
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        bac_stage2.process(self.out1, crc, usd)
        gen = parse_csv_rows(usd)
        exp = parse_csv_rows(EXPECTED_OUT2_USD)
        gen_semantic = [(r[1].strip(), r[2], r[3]) for r in gen if len(r) >= 4]
        exp_semantic = [(r[1].strip(), r[2], r[3]) for r in exp if len(r) >= 4]
        assert_rows_match(gen_semantic, exp_semantic, "Stage2-USD")


class TestBACStage3:
    @pytest.fixture(autouse=True)
    def run_stages(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        self.out2_crc = tmp_out('out2-crc.csv')
        self.out2_usd = tmp_out('out2-usd.csv')
        bac_stage1.process(INPUT_FILE, self.out1)
        bac_stage2.process(self.out1, self.out2_crc, self.out2_usd)

    def test_crc_ynab_header(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        bac_stage3.process(self.out2_crc, out, currency='crc')
        with open(out) as f:
            header = f.readline().strip()
        assert header == '"Date","Payee","Memo","Amount"'

    def test_usd_ynab_header(self, tmp_out):
        out = tmp_out('out3-usd.csv')
        bac_stage3.process(self.out2_usd, out, currency='usd')
        with open(out) as f:
            header = f.readline().strip()
        assert header == '"Date","Payee","Memo","Amount"'

    def test_crc_dates_yyyy_mm_dd(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        bac_stage3.process(self.out2_crc, out, currency='crc')
        rows = parse_ynab_rows(out)
        for date_tuple, payee, memo, amount in rows:
            assert date_tuple is not None, f"Unparseable date for {payee}"
            assert date_tuple[0] >= 2000, f"Year not YYYY: {date_tuple}"

    def test_usd_dates_yyyy_mm_dd(self, tmp_out):
        out = tmp_out('out3-usd.csv')
        bac_stage3.process(self.out2_usd, out, currency='usd')
        rows = parse_ynab_rows(out)
        for date_tuple, payee, memo, amount in rows:
            assert date_tuple is not None
            assert date_tuple[0] >= 2000

    def test_crc_content_matches(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        bac_stage3.process(self.out2_crc, out, currency='crc')
        gen = parse_ynab_rows(out)
        exp = parse_ynab_rows(EXPECTED_OUT3_CRC)
        assert_rows_match(gen, exp, "Stage3-CRC")

    def test_usd_content_matches(self, tmp_out):
        out = tmp_out('out3-usd.csv')
        bac_stage3.process(self.out2_usd, out, currency='usd')
        gen = parse_ynab_rows(out)
        exp = parse_ynab_rows(EXPECTED_OUT3_USD)
        assert_rows_match(gen, exp, "Stage3-USD")

    def test_crc_memo_empty(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        bac_stage3.process(self.out2_crc, out, currency='crc')
        rows = parse_ynab_rows(out)
        for _, _, memo, _ in rows:
            assert memo == '', f"Memo should be empty, got: {memo}"

    def test_all_fields_quoted(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        bac_stage3.process(self.out2_crc, out, currency='crc')
        with open(out) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Each field should be quoted
                parts = line.split('","')
                assert parts[0].startswith('"'), f"First field not quoted: {line}"
                assert parts[-1].endswith('"'), f"Last field not quoted: {line}"
