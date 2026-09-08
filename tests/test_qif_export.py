"""Unit tests for scripts/qif_export.py against contracts/qif-output-format.md."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import qif_export


def write_csv(path, rows):
    """Write an out3-format CSV: header + data rows (each a (date, payee, memo, amount) tuple)."""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['Date', 'Payee', 'Memo', 'Amount'])
        for row in rows:
            writer.writerow(row)


class TestConvertCsvToQifContract:
    """T001: header/order/date/amount contract, using contract §2's worked example."""

    def test_header_line(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/03/05', 'SOME MERCHANT', '', '1200')])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        content = qif_path.read_text(encoding='utf-8')
        assert content.startswith('!Type:Bank\n')
        assert content.count('!Type:Bank') == 1

    def test_record_order_and_fields(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [
            ('2026/03/05', 'AMAZON.COM, INC.', 'REF123', '-4500'),
            ('2026/03/07', 'SOME MERCHANT', '', '1200'),
        ])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        expected = (
            '!Type:Bank\n'
            'D03/05/2026\n'
            'PAMAZON.COM, INC.\n'
            'MREF123\n'
            'T-4500\n'
            '^\n'
            'D03/07/2026\n'
            'PSOME MERCHANT\n'
            'T1200\n'
            '^\n'
        )
        assert qif_path.read_text(encoding='utf-8') == expected

    def test_date_reformatted_yyyy_mm_dd_to_mm_dd_yyyy(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/12/31', 'PAYEE', '', '100')])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        lines = qif_path.read_text(encoding='utf-8').splitlines()
        assert 'D12/31/2026' in lines

    def test_amount_copied_verbatim(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [
            ('2026/01/01', 'PAYEE A', '', '-4500'),
            ('2026/01/02', 'PAYEE B', '', '1200.50'),
        ])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        lines = qif_path.read_text(encoding='utf-8').splitlines()
        assert 'T-4500' in lines
        assert 'T1200.50' in lines


class TestConvertCsvToQifReturnAndCsvUntouched:
    """T002: return value and read-only-CSV postcondition."""

    def test_returns_str_qif_path(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/03/05', 'PAYEE', '', '100')])
        result = qif_export.convert_csv_to_qif(csv_path, qif_path)
        assert result == str(qif_path)

    def test_source_csv_unmodified(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/03/05', 'PAYEE', '', '100')])
        before_content = csv_path.read_bytes()
        before_mtime = csv_path.stat().st_mtime_ns
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        assert csv_path.read_bytes() == before_content
        assert csv_path.stat().st_mtime_ns == before_mtime


class TestConvertCsvToQifEdgeCases:
    """T012-T015: empty memo, punctuation, embedded newlines, zero-row CSV."""

    def test_empty_memo_omits_m_line(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/03/07', 'SOME MERCHANT', '', '1200')])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        lines = qif_path.read_text(encoding='utf-8').splitlines()
        record_lines = [l for l in lines if l != '!Type:Bank']
        assert record_lines == ['D03/07/2026', 'PSOME MERCHANT', 'T1200', '^']
        assert not any(l.startswith('M') for l in record_lines)

    def test_payee_with_comma_and_quote_preserved_verbatim(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [('2026/03/05', 'AMAZON.COM, INC.', 'REF123', '-4500')])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        lines = qif_path.read_text(encoding='utf-8').splitlines()
        assert 'PAMAZON.COM, INC.' in lines

    def test_embedded_newlines_collapsed_to_space(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [
            ('2026/03/05', 'MULTI\r\nLINE PAYEE', 'MULTI\nLINE MEMO', '100'),
            ('2026/03/06', 'CR ONLY\rPAYEE', '', '200'),
        ])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        lines = qif_path.read_text(encoding='utf-8').splitlines()
        assert 'PMULTI LINE PAYEE' in lines
        assert 'MMULTI LINE MEMO' in lines
        assert 'PCR ONLY PAYEE' in lines

    def test_header_only_csv_produces_header_only_qif(self, tmp_path):
        csv_path = tmp_path / 'in.csv'
        qif_path = tmp_path / 'out.qif'
        write_csv(csv_path, [])
        qif_export.convert_csv_to_qif(csv_path, qif_path)
        assert qif_path.read_text(encoding='utf-8') == '!Type:Bank\n'
