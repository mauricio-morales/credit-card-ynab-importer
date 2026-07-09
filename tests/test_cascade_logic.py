"""Unit tests for cascade business logic — no network calls."""
from __future__ import annotations

import os
import json
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from tui.ynab.cascade import (
    CarryoverTuplet,
    ClearanceCheckResult,
    DonorAllocation,
    InsufficientFundsError,
    build_month_plan,
    build_scan_overview,
    build_split_subtransactions,
    check_clearance,
    format_milliunits,
    select_donors,
)
from tui.ynab.config import BudgetConfig, Config, load_config, save_config
from tui.ynab.client import CategoryMonthBalance


# ── Helpers ───────────────────────────────────────────────────────────────────

def _balance(
    category_id: str,
    category_name: str,
    available: int,
    is_cc: bool = False,
    group_name: str = "Group",
    month: date = date(2026, 2, 1),
) -> CategoryMonthBalance:
    return CategoryMonthBalance(
        category_id=category_id,
        category_name=category_name,
        group_name=group_name,
        month=month,
        available=available,
        is_credit_card_payment=is_cc,
    )


# ── format_milliunits() ───────────────────────────────────────────────────────

class TestFormatMilliunits:
    def test_positive_value(self):
        assert format_milliunits(1234560) == "$1,234.56"

    def test_zero(self):
        assert format_milliunits(0) == "$0.00"

    def test_negative_value(self):
        assert format_milliunits(-50000) == "-$50.00"

    def test_small_value(self):
        assert format_milliunits(1000) == "$1.00"

    def test_large_value(self):
        assert format_milliunits(10000000) == "$10,000.00"


# ── load_config() / save_config() ─────────────────────────────────────────────

class TestConfigIO:
    def test_missing_file_returns_empty_config(self, tmp_path):
        missing = tmp_path / "config.json"
        with patch("tui.ynab.config._CONFIG_PATH", missing):
            cfg = load_config()
        assert cfg.api_key == ""
        assert cfg.budgets == {}

    def test_api_key_only_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"api_key": "my-key", "budgets": {}}))
        with patch("tui.ynab.config._CONFIG_PATH", path):
            cfg = load_config()
        assert cfg.api_key == "my-key"
        assert cfg.budgets == {}

    def test_multi_budget_map_preserved_after_save(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config(
            api_key="key-123",
            budgets={
                "b1": BudgetConfig(budget_name="CRC Budget", loan_account_id="loan-1"),
                "b2": BudgetConfig(budget_name="USD Budget", loan_account_id="loan-2"),
            },
        )
        with patch("tui.ynab.config._CONFIG_PATH", path):
            save_config(cfg)
            loaded = load_config()
        assert loaded.api_key == "key-123"
        assert loaded.budgets["b1"].budget_name == "CRC Budget"
        assert loaded.budgets["b2"].loan_account_id == "loan-2"

    def test_atomic_write_tmp_then_rename(self, tmp_path):
        path = tmp_path / "config.json"
        tmp_path2 = path.with_suffix(".tmp")
        cfg = Config(api_key="k")
        with patch("tui.ynab.config._CONFIG_PATH", path):
            save_config(cfg)
        assert path.exists()
        assert not tmp_path2.exists()

    def test_save_preserves_existing_budget_entries(self, tmp_path):
        path = tmp_path / "config.json"
        initial = Config(
            api_key="key",
            budgets={"b1": BudgetConfig("Budget 1", "loan-1")},
        )
        with patch("tui.ynab.config._CONFIG_PATH", path):
            save_config(initial)
            loaded = load_config()
            loaded.budgets["b2"] = BudgetConfig("Budget 2", "loan-2")
            save_config(loaded)
            final = load_config()
        assert "b1" in final.budgets
        assert "b2" in final.budgets


# ── check_clearance() ─────────────────────────────────────────────────────────

class TestCheckClearance:
    def test_passes_when_all_reconciled(self):
        txns = [
            {"account_id": "a1", "account_name": "Checking", "cleared": "reconciled"},
            {"account_id": "a2", "account_name": "Visa", "cleared": "reconciled"},
        ]
        result = check_clearance(txns, loan_account_id="loan-1", account_name_map={})
        assert result.passed is True
        assert result.issues == []

    def test_blocks_on_cleared_transactions(self):
        txns = [
            {"account_id": "a1", "account_name": "Checking", "cleared": "cleared"},
        ]
        result = check_clearance(txns, "loan-1", {"a1": "Checking"})
        assert result.passed is False
        assert result.issues[0].account_name == "Checking"
        assert result.issues[0].unreconciled_count == 1

    def test_blocks_on_uncleared_transactions(self):
        txns = [
            {"account_id": "a1", "account_name": "Savings", "cleared": "uncleared"},
        ]
        result = check_clearance(txns, "loan-1", {"a1": "Savings"})
        assert result.passed is False

    def test_loan_account_excluded_entirely(self):
        txns = [
            {"account_id": "loan-1", "account_name": "Loan", "cleared": "cleared"},
        ]
        result = check_clearance(txns, "loan-1", {})
        assert result.passed is True

    def test_per_account_grouping_with_correct_count(self):
        txns = [
            {"account_id": "a1", "cleared": "uncleared"},
            {"account_id": "a1", "cleared": "cleared"},
            {"account_id": "a2", "cleared": "uncleared"},
        ]
        result = check_clearance(txns, "loan-1", {"a1": "Account 1", "a2": "Account 2"})
        assert result.passed is False
        by_name = {i.account_name: i.unreconciled_count for i in result.issues}
        assert by_name["Account 1"] == 2
        assert by_name["Account 2"] == 1

    def test_passes_when_newer_reconciliation_supersedes_unreconciled(self):
        # June unreconciled txn didn't post; user already reconciled in July
        lookback = [
            {"account_id": "a1", "cleared": "uncleared", "date": "2026-06-15"},
        ]
        all_txns = lookback + [
            {"account_id": "a1", "cleared": "reconciled", "date": "2026-07-05"},
        ]
        result = check_clearance(lookback, "loan-1", {"a1": "Checking"}, all_transactions=all_txns)
        assert result.passed is True

    def test_still_blocks_when_no_newer_reconciliation(self):
        # Unreconciled June txn, but latest reconciled is also in June (before it)
        lookback = [
            {"account_id": "a1", "cleared": "uncleared", "date": "2026-06-20"},
        ]
        all_txns = lookback + [
            {"account_id": "a1", "cleared": "reconciled", "date": "2026-06-10"},
        ]
        result = check_clearance(lookback, "loan-1", {"a1": "Checking"}, all_transactions=all_txns)
        assert result.passed is False
        assert result.issues[0].unreconciled_count == 1

    def test_mixed_accounts_only_supersedes_accounts_with_newer_reconciliation(self):
        # a1 has a newer reconciliation → should pass; a2 does not → should still block
        lookback = [
            {"account_id": "a1", "cleared": "uncleared", "date": "2026-06-15"},
            {"account_id": "a2", "cleared": "uncleared", "date": "2026-06-20"},
        ]
        all_txns = lookback + [
            {"account_id": "a1", "cleared": "reconciled", "date": "2026-07-01"},
            {"account_id": "a2", "cleared": "reconciled", "date": "2026-06-01"},
        ]
        result = check_clearance(
            lookback, "loan-1",
            {"a1": "Account 1", "a2": "Account 2"},
            all_transactions=all_txns,
        )
        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].account_name == "Account 2"

    def test_without_all_transactions_behaves_as_before(self):
        # Passing no all_transactions preserves original strict behavior
        lookback = [
            {"account_id": "a1", "cleared": "uncleared", "date": "2026-06-15"},
        ]
        result = check_clearance(lookback, "loan-1", {"a1": "Checking"})
        assert result.passed is False


# ── build_scan_overview() ─────────────────────────────────────────────────────

class TestBuildScanOverview:
    def test_excludes_cc_categories(self):
        feb = date(2026, 2, 1)
        balances = {
            feb: [
                _balance("c1", "Visa Payment", -10000, is_cc=True, month=feb),
                _balance("c2", "Dining", -5000, month=feb),
            ]
        }
        result = build_scan_overview(balances)
        assert len(result[feb]) == 1
        assert result[feb][0].category_id == "c2"

    def test_excludes_non_negative_categories(self):
        feb = date(2026, 2, 1)
        balances = {
            feb: [
                _balance("c1", "Positive", 10000, month=feb),
                _balance("c2", "Negative", -5000, month=feb),
            ]
        }
        result = build_scan_overview(balances)
        assert len(result[feb]) == 1
        assert result[feb][0].category_id == "c2"

    def test_drops_months_with_no_qualifying_negatives(self):
        feb = date(2026, 2, 1)
        mar = date(2026, 3, 1)
        balances = {
            feb: [_balance("c1", "Clean", 1000, month=feb)],
            mar: [_balance("c2", "Negative", -5000, month=mar)],
        }
        result = build_scan_overview(balances)
        assert feb not in result
        assert mar in result

    def test_result_ordered_oldest_first(self):
        apr = date(2026, 4, 1)
        feb = date(2026, 2, 1)
        mar = date(2026, 3, 1)
        balances = {
            apr: [_balance("c3", "Cat", -1000, month=apr)],
            feb: [_balance("c1", "Cat", -1000, month=feb)],
            mar: [_balance("c2", "Cat", -1000, month=mar)],
        }
        result = build_scan_overview(balances)
        assert list(result.keys()) == [feb, mar, apr]


# ── select_donors() ───────────────────────────────────────────────────────────

class TestSelectDonors:
    def test_single_donor_covers_full_deficit(self):
        balances = [_balance("d1", "Donor", 50000)]
        donors = select_donors(balances, 30000)
        assert len(donors) == 1
        assert donors[0].amount_milliunits == 30000
        assert sum(d.amount_milliunits for d in donors) == 30000

    def test_multi_donor_largest_first(self):
        balances = [
            _balance("d1", "Small", 20000),
            _balance("d2", "Large", 80000),
        ]
        donors = select_donors(balances, 90000)
        assert donors[0].donor_category_id == "d2"
        assert donors[1].donor_category_id == "d1"
        assert sum(d.amount_milliunits for d in donors) == 90000

    def test_donor_invariant_sum_equals_deficit(self):
        balances = [_balance("d1", "Donor", 100000)]
        deficit = 75000
        donors = select_donors(balances, deficit)
        assert sum(d.amount_milliunits for d in donors) == deficit

    def test_raises_insufficient_funds(self):
        balances = [_balance("d1", "Donor", 5000)]
        with pytest.raises(InsufficientFundsError):
            select_donors(balances, 10000)

    def test_excludes_cc_categories_from_donors(self):
        balances = [
            _balance("d1", "CC Payment", 50000, is_cc=True),
            _balance("d2", "Regular", 50000),
        ]
        donors = select_donors(balances, 10000)
        assert all(d.donor_category_id != "d1" for d in donors)


# ── build_split_subtransactions() ─────────────────────────────────────────────

class TestBuildSplitSubtransactions:
    def _make_carryovers(self) -> list[CarryoverTuplet]:
        return [
            CarryoverTuplet("c1", "Dining", "Food", date(2026, 4, 1), 50000),
            CarryoverTuplet("c2", "Gas", "Transport", date(2026, 4, 1), 30000),
        ]

    def _make_donors(self) -> list[DonorAllocation]:
        return [DonorAllocation("d1", "Savings", 80000)]

    def test_tx_a_donors_are_negative(self):
        tx_a, _ = build_split_subtransactions(self._make_carryovers(), self._make_donors())
        donor_rows = [s for s in tx_a if s.memo == "donor"]
        assert all(s.amount_milliunits < 0 for s in donor_rows)

    def test_tx_a_carryovers_are_positive(self):
        tx_a, _ = build_split_subtransactions(self._make_carryovers(), self._make_donors())
        co_rows = [s for s in tx_a if s.memo == "carryover"]
        assert all(s.amount_milliunits > 0 for s in co_rows)

    def test_tx_b_is_sign_inverse_of_tx_a(self):
        tx_a, tx_b = build_split_subtransactions(self._make_carryovers(), self._make_donors())
        for a, b in zip(tx_a, tx_b):
            assert a.amount_milliunits == -b.amount_milliunits
            assert a.category_id == b.category_id

    def test_tx_a_sums_to_zero(self):
        tx_a, _ = build_split_subtransactions(self._make_carryovers(), self._make_donors())
        assert sum(s.amount_milliunits for s in tx_a) == 0

    def test_tx_b_sums_to_zero(self):
        _, tx_b = build_split_subtransactions(self._make_carryovers(), self._make_donors())
        assert sum(s.amount_milliunits for s in tx_b) == 0


# ── build_month_plan() ────────────────────────────────────────────────────────

class TestBuildMonthPlan:
    def test_is_carry_forward_true_for_new_negatives(self):
        month = date(2026, 3, 1)
        live = [
            _balance("c1", "Original", -20000, month=month),
            _balance("c2", "New Negative", -10000, month=month),
            _balance("d1", "Donor", 50000, month=month),
        ]
        initial = [_balance("c1", "Original", -20000, month=month)]
        plan = build_month_plan(month, live, initial)
        carry_ids = {c.target_category_id for c in plan.carryovers if c.is_carry_forward}
        original_ids = {c.target_category_id for c in plan.carryovers if not c.is_carry_forward}
        assert "c2" in carry_ids
        assert "c1" in original_ids

    def test_donor_invariant_sum_equals_deficit(self):
        month = date(2026, 3, 1)
        live = [
            _balance("c1", "Neg", -20000, month=month),
            _balance("d1", "Donor", 50000, month=month),
        ]
        initial = [_balance("c1", "Neg", -20000, month=month)]
        plan = build_month_plan(month, live, initial)
        total_deficit = sum(c.deficit_milliunits for c in plan.carryovers)
        total_donors = sum(d.amount_milliunits for d in plan.donors)
        assert total_donors == total_deficit

    def test_transaction_ids_none_on_creation(self):
        month = date(2026, 3, 1)
        live = [
            _balance("c1", "Neg", -10000, month=month),
            _balance("d1", "Donor", 20000, month=month),
        ]
        plan = build_month_plan(month, live, [])
        assert plan.transaction_a_id is None
        assert plan.transaction_b_id is None

    def test_excludes_cc_categories(self):
        month = date(2026, 3, 1)
        live = [
            _balance("c1", "CC Payment", -10000, is_cc=True, month=month),
            _balance("c2", "Real Neg", -5000, month=month),
            _balance("d1", "Donor", 20000, month=month),
        ]
        plan = build_month_plan(month, live, [])
        assert all(c.target_category_id != "c1" for c in plan.carryovers)
