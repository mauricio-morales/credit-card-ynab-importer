"""DaviBank pipeline regression tests.

Compares script output against provided sample files using semantic comparison.
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from conftest import (
    FIXTURES_DIR, parse_csv_rows, parse_ynab_rows, assert_rows_match, parse_date_tuple,
    parse_qif_records,
)
import davi_stage1
import davi_stage2
import davi_stage3
import qif_export


INPUT_FILE = FIXTURES_DIR / 'DaviBank Sample-in.xlsx'
EXPECTED_OUT1 = FIXTURES_DIR / 'DaviBank Sample-out1.csv'
EXPECTED_OUT2_CRC = FIXTURES_DIR / 'DaviBank Sample-out2-crc.csv'
EXPECTED_OUT2_USD = FIXTURES_DIR / 'DaviBank Sample-out2-usd.csv'
EXPECTED_OUT3_CRC = FIXTURES_DIR / 'DaviBank Sample-out3-crc.csv'
EXPECTED_OUT3_USD = FIXTURES_DIR / 'DaviBank Sample-out3-usd.csv'
EXPECTED_QIF_CRC = FIXTURES_DIR / 'DaviBank Sample-out3-crc.qif'
EXPECTED_QIF_USD = FIXTURES_DIR / 'DaviBank Sample-out3-usd.qif'


def parse_davi_rows(path):
    """Parse a DaviBank 6-column CSV into semantic tuples.

    The date field (index 1) is normalized to a (year, month, day) tuple to
    allow semantic comparison regardless of whether the sample file has D/M/YY
    (Excel artifact) or DD/MM/YYYY (pipeline output).
    """
    rows = []
    with open(path, encoding='utf-8', newline='') as f:
        for i, parts in enumerate(csv.reader(f)):
            if not parts or i == 0:
                continue
            parts = [p.strip() for p in parts[:6]]
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

    def test_multi_card_section_passthrough(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        with open(out, encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f if line.strip()]
        card_marker_lines = [l for l in lines if l.startswith('Tarjeta Número:,')]
        card_numbers = [l.split(',')[1] for l in card_marker_lines]
        # The reference sample's first card is interrupted by a second card's
        # section and then resumes (data-model.md § Card Section).
        assert len(card_marker_lines) >= 3
        assert card_numbers[0] == card_numbers[2]
        assert card_numbers[0] != card_numbers[1]

    def test_debit_credit_source_signs(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(INPUT_FILE, out)
        with open(out, encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        debit_amounts, credit_amounts = [], []
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) < 6 or parts[0] == 'Tarjeta Número:':
                continue
            if parts[5] == 'DEBITO':
                debit_amounts.append(float(parts[3]))
            elif parts[5] == 'CREDITO':
                credit_amounts.append(float(parts[3]))
        assert debit_amounts, "no DEBITO rows found"
        assert credit_amounts, "no CREDITO rows found"
        assert all(a > 0 for a in debit_amounts), "DEBITO amounts should be positive at source"
        assert all(a < 0 for a in credit_amounts), "CREDITO amounts should be negative at source"

    def test_empty_transactions_header_only(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank EmptyTransactions-in.xlsx'
        out = tmp_out('out1.csv')
        davi_stage1.process(infile, out)
        with open(out, encoding='utf-8') as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 1
        assert 'Número de Referencia' in lines[0]

    def test_footer_row_skipped(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank FooterRow-in.xlsx'
        out = tmp_out('out1.csv')
        davi_stage1.process(infile, out)
        with open(out, encoding='utf-8') as f:
            content = f.read()
        assert 'Rango de fechas' not in content
        rows = parse_davi_rows(out)
        # 1 card marker + 2 data rows; footer row must not become a 3rd data row
        assert len(rows) == 3

    def test_multi_sheet_only_first_sheet(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank MultiSheet-in.xlsx'
        out = tmp_out('out1.csv')
        davi_stage1.process(infile, out)
        with open(out, encoding='utf-8') as f:
            content = f.read()
        assert 'SHOULD NOT APPEAR' not in content
        assert '200001' in content

    def test_native_cells_normalize(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank NativeCells-in.xlsx'
        out = tmp_out('out1.csv')
        davi_stage1.process(infile, out)
        rows = parse_davi_rows(out)
        by_ref = {r[0]: r for r in rows if r[0] != 'Tarjeta Número:'}
        assert by_ref['300001'][1] == (2026, 7, 6)          # string date, unchanged
        assert by_ref['300002'][1] == (2026, 7, 7)          # native datetime normalized
        assert by_ref['300002'][3] == '500'                 # string amount, unchanged
        assert by_ref['300003'][3] == '250'                 # native numeric amount, trailing .00 stripped
        assert by_ref['300004'][1] == (2026, 7, 9)          # native date
        assert by_ref['300004'][3] == '-75.5'                # native numeric amount, real decimal kept


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

    def test_debit_credit_signs_negated(self, tmp_out):
        out = tmp_out('out3-crc.csv')
        davi_stage3.process(self.out2_crc, out, currency='crc')
        rows = parse_ynab_rows(out)
        amounts = [float(r[3]) for r in rows]
        # DEBITO (positive at source) -> negative YNAB outflow;
        # CREDITO (negative at source) -> positive YNAB inflow.
        assert any(a < 0 for a in amounts), "expected at least one negative (outflow) amount"
        assert any(a > 0 for a in amounts), "expected at least one positive (inflow) amount"


class TestDaviErrorHandling:
    def test_legacy_xls_rejected(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank Sample-in.xls'
        out = tmp_out('out1.csv')
        with pytest.raises(davi_stage1.LegacyFormatError) as exc_info:
            davi_stage1.process(infile, out)
        assert exc_info.value.user_message
        assert not out.exists()

    def test_unreadable_file_rejected(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank NotASpreadsheet-in.xlsx'
        out = tmp_out('out1.csv')
        with pytest.raises(davi_stage1.UnreadableFileError) as exc_info:
            davi_stage1.process(infile, out)
        assert exc_info.value.user_message
        assert not out.exists()

    def test_missing_columns_rejected(self, tmp_out):
        infile = FIXTURES_DIR / 'DaviBank MissingColumn-in.xlsx'
        out = tmp_out('out1.csv')
        with pytest.raises(davi_stage1.MissingColumnsError) as exc_info:
            davi_stage1.process(infile, out)
        assert 'Monto' in exc_info.value.user_message
        assert not out.exists()


class TestDaviEmbeddedCommaDescription:
    """Regression test: a Descripción containing commas (e.g. "City, Country"
    suffixes on foreign-purchase rows) must not be silently dropped by the
    CRC/USD currency split (davi_stage2) or the YNAB conversion (davi_stage3).
    """

    INPUT_FILE = FIXTURES_DIR / 'DaviBank EmbeddedComma-in.xlsx'

    def test_stage1_preserves_full_description(self, tmp_out):
        out = tmp_out('out1.csv')
        davi_stage1.process(self.INPUT_FILE, out)
        rows = parse_davi_rows(out)
        descriptions = [r[2] for r in rows if r[0] != 'Tarjeta Número:']
        assert 'The Golden Arch (1203), Schiphol, NL' in descriptions
        assert 'SKANSEN SMAKOW, CHOLERZYN, PL' in descriptions

    def test_stage2_does_not_drop_comma_rows(self, tmp_out):
        out1 = tmp_out('out1.csv')
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        davi_stage1.process(self.INPUT_FILE, out1)
        davi_stage2.process(out1, crc, usd)

        usd_rows = parse_davi_rows(usd)
        descriptions = [r[2] for r in usd_rows]
        assert 'The Golden Arch (1203), Schiphol, NL' in descriptions
        assert 'SKANSEN SMAKOW, CHOLERZYN, PL' in descriptions
        assert 'Normal Description No Comma' in descriptions
        # every row must have ended up in exactly one currency file
        assert len(usd_rows) == 3

    def test_stage3_yields_correct_amount_and_payee(self, tmp_out):
        out1 = tmp_out('out1.csv')
        crc = tmp_out('out2-crc.csv')
        usd = tmp_out('out2-usd.csv')
        out3 = tmp_out('out3-usd.csv')
        davi_stage1.process(self.INPUT_FILE, out1)
        davi_stage2.process(out1, crc, usd)
        davi_stage3.process(usd, out3, currency='usd')

        rows = parse_ynab_rows(out3)
        by_payee = {r[1]: r for r in rows}
        assert 'The Golden Arch (1203), Schiphol, NL' in by_payee
        assert by_payee['The Golden Arch (1203), Schiphol, NL'][3] == '-33.3'
        assert 'SKANSEN SMAKOW, CHOLERZYN, PL' in by_payee
        assert by_payee['SKANSEN SMAKOW, CHOLERZYN, PL'][3] == '-44.42'


class TestDaviQIFExport:
    @pytest.fixture(autouse=True)
    def run_stages(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        self.out2_crc = tmp_out('out2-crc.csv')
        self.out2_usd = tmp_out('out2-usd.csv')
        davi_stage1.process(INPUT_FILE, self.out1)
        davi_stage2.process(self.out1, self.out2_crc, self.out2_usd)

    def test_crc_qif_matches_fixture(self, tmp_out):
        out3 = tmp_out('out3-crc.csv')
        qif = tmp_out('out3-crc.qif')
        davi_stage3.process(self.out2_crc, out3, currency='crc')
        qif_export.convert_csv_to_qif(out3, qif)

        with open(qif) as f:
            assert f.readline().strip() == '!Type:Bank'

        gen = parse_qif_records(qif)
        exp_csv = parse_ynab_rows(out3)
        exp_qif = parse_qif_records(EXPECTED_QIF_CRC)
        assert len(gen) == len(exp_csv)
        assert_rows_match(gen, exp_qif, "Davi-QIF-CRC")

    def test_usd_qif_matches_fixture(self, tmp_out):
        out3 = tmp_out('out3-usd.csv')
        qif = tmp_out('out3-usd.qif')
        davi_stage3.process(self.out2_usd, out3, currency='usd')
        qif_export.convert_csv_to_qif(out3, qif)

        with open(qif) as f:
            assert f.readline().strip() == '!Type:Bank'

        gen = parse_qif_records(qif)
        exp_csv = parse_ynab_rows(out3)
        exp_qif = parse_qif_records(EXPECTED_QIF_USD)
        assert len(gen) == len(exp_csv)
        assert_rows_match(gen, exp_qif, "Davi-QIF-USD")


class TestDaviCsvUnchangedByQifExport:
    """User Story 2: QIF generation must not alter the out3 CSV (FR-010, SC-003)."""

    @pytest.fixture(autouse=True)
    def run_stages(self, tmp_out):
        self.out1 = tmp_out('out1.csv')
        self.out2_crc = tmp_out('out2-crc.csv')
        self.out2_usd = tmp_out('out2-usd.csv')
        davi_stage1.process(INPUT_FILE, self.out1)
        davi_stage2.process(self.out1, self.out2_crc, self.out2_usd)

    def test_crc_csv_bytes_unchanged_after_qif_export(self, tmp_out):
        out3 = tmp_out('out3-crc.csv')
        qif = tmp_out('out3-crc.qif')
        davi_stage3.process(self.out2_crc, out3, currency='crc')
        qif_export.convert_csv_to_qif(out3, qif)
        assert out3.read_bytes() == EXPECTED_OUT3_CRC.read_bytes()

    def test_usd_csv_bytes_unchanged_after_qif_export(self, tmp_out):
        out3 = tmp_out('out3-usd.csv')
        qif = tmp_out('out3-usd.qif')
        davi_stage3.process(self.out2_usd, out3, currency='usd')
        qif_export.convert_csv_to_qif(out3, qif)
        assert out3.read_bytes() == EXPECTED_OUT3_USD.read_bytes()
