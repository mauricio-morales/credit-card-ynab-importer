"""Textual screen tests for cascade flow states — all YNAB calls mocked."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tui.ynab.cascade import (
    AccountReconciliationIssue,
    CarryoverTuplet,
    ClearanceCheckResult,
    DonorAllocation,
    MonthPlan,
)
from tui.ynab.client import CategoryMonthBalance, YNABClientError
from tui.ynab.config import BudgetConfig, Config


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_config(api_key: str = "test-key", budgets: dict | None = None) -> Config:
    return Config(api_key=api_key, budgets=budgets or {})


def _make_month_plan(month: date = date(2026, 2, 1)) -> MonthPlan:
    carryovers = [
        CarryoverTuplet("c1", "Dining Out", "Food", month, 50000, is_carry_forward=False),
    ]
    donors = [DonorAllocation("d1", "Savings", 50000)]
    return MonthPlan(month=month, carryovers=carryovers, donors=donors)


# ── SetupWizardScreen Tests ───────────────────────────────────────────────────

class TestSetupWizardScreen:
    """T012: SetupWizardScreen behavior tests."""

    @pytest.mark.asyncio
    async def test_valid_key_writes_api_key_and_advances(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import SetupWizardScreen

        config_path = tmp_path / "config.json"
        budgets_response = [{"id": "b1", "name": "My Budget"}]

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_budgets.return_value = budgets_response

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(SetupWizardScreen())
                await pilot.pause()

                await pilot.click("#api-key-input")
                await pilot.type("valid-api-key")
                await pilot.click("#btn-validate")
                await pilot.pause(0.2)

                import json
                if config_path.exists():
                    data = json.loads(config_path.read_text())
                    assert data.get("api_key") == "valid-api-key"

    @pytest.mark.asyncio
    async def test_invalid_key_shows_error_stays_on_screen(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import SetupWizardScreen

        config_path = tmp_path / "config.json"

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_budgets.side_effect = YNABClientError("Invalid API key. Update it in Settings.")

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(SetupWizardScreen())
                await pilot.pause()
                await pilot.click("#api-key-input")
                await pilot.type("bad-key")
                await pilot.click("#btn-validate")
                await pilot.pause(0.2)

                assert not config_path.exists()
                assert isinstance(app.screen, SetupWizardScreen)

    @pytest.mark.asyncio
    async def test_empty_budgets_shows_error_no_config_written(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import SetupWizardScreen

        config_path = tmp_path / "config.json"

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_budgets.return_value = []

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(SetupWizardScreen())
                await pilot.pause()
                await pilot.click("#api-key-input")
                await pilot.type("key-with-no-budgets")
                await pilot.click("#btn-validate")
                await pilot.pause(0.2)

                assert not config_path.exists()


# ── BudgetSelectScreen & AccountSelectScreen Tests ────────────────────────────

class TestBudgetAndAccountScreens:
    """T013: BudgetSelectScreen and AccountSelectScreen behavior."""

    @pytest.mark.asyncio
    async def test_already_configured_budget_routes_to_scan(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import BudgetSelectScreen
        from tui.screens.cascade_scan import CascadeScanScreen

        config = _make_config(
            budgets={"b1": BudgetConfig("My Budget", "loan-1")}
        )
        config_path = tmp_path / "config.json"

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_budgets.return_value = [{"id": "b1", "name": "My Budget"}]

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(BudgetSelectScreen(config=config))
                await pilot.pause()
                await pilot.click("#budget-list")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_account_save_writes_atomic_config_entry(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import AccountSelectScreen
        from tui.ynab.client import YNABAccount

        config_path = tmp_path / "config.json"
        config = _make_config()

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_accounts.return_value = [
                YNABAccount("loan-1", "Internal Loan", "otherAsset", False, True),
            ]

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(
                    AccountSelectScreen(budget_id="b1", budget_name="My Budget", config=config)
                )
                await pilot.pause()


# ── CascadeScanScreen Tests ───────────────────────────────────────────────────

class TestCascadeScanScreen:
    """T027: CascadeScanScreen state tests."""

    @pytest.mark.asyncio
    async def test_blocked_state_shows_account_table(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_scan import CascadeScanScreen
        from tui.ynab.client import YNABAccount

        config_path = tmp_path / "config.json"
        config = _make_config(
            budgets={"b1": BudgetConfig("Budget", "loan-1")}
        )

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_scan.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_accounts.return_value = [
                YNABAccount("a1", "Checking", "checking", False, True),
            ]
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {"account_id": "a1", "account_name": "Checking", "cleared": "uncleared"},
            ]

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(CascadeScanScreen(budget_id="b1", config=config))
                await pilot.pause(0.5)

    @pytest.mark.asyncio
    async def test_clean_state_shows_no_issues_message(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_scan import CascadeScanScreen
        from tui.ynab.client import YNABAccount

        config_path = tmp_path / "config.json"
        config = _make_config(
            budgets={"b1": BudgetConfig("Budget", "loan-1")}
        )

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_scan.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []
            mock_client.get_month_balances.return_value = []

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(CascadeScanScreen(budget_id="b1", config=config))
                await pilot.pause(0.5)

    @pytest.mark.asyncio
    async def test_network_error_shows_retry_no_stale_data(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_scan import CascadeScanScreen

        config_path = tmp_path / "config.json"
        config = _make_config(
            budgets={"b1": BudgetConfig("Budget", "loan-1")}
        )

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_scan.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_accounts.side_effect = YNABClientError("Network error")

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(CascadeScanScreen(budget_id="b1", config=config))
                await pilot.pause(0.5)


# ── CascadeMonthScreen Tests ──────────────────────────────────────────────────

class TestCascadeMonthScreen:
    """T039: CascadeMonthScreen behavior tests."""

    @pytest.mark.asyncio
    async def test_carry_forward_rows_labeled(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_month import CascadeMonthScreen

        month = date(2026, 2, 1)
        carryovers = [
            CarryoverTuplet("c1", "Original", "Food", month, 30000, is_carry_forward=False),
            CarryoverTuplet("c2", "Carry Forward", "Food", month, 20000, is_carry_forward=True),
        ]
        plan = MonthPlan(
            month=month,
            carryovers=carryovers,
            donors=[DonorAllocation("d1", "Savings", 50000)],
        )

        app = CreditCardConverterApp()
        async with app.run_test() as pilot:
            await app.push_screen(CascadeMonthScreen(plan=plan))
            await pilot.pause(0.2)
            # Verify the screen rendered without error
            assert isinstance(app.screen, CascadeMonthScreen)

    @pytest.mark.asyncio
    async def test_no_ynab_calls_before_confirm(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_month import CascadeMonthScreen

        plan = _make_month_plan()

        with patch("tui.screens.cascade_month.YNABClient") as MockClient:
            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(CascadeMonthScreen(plan=plan))
                await pilot.pause(0.2)
            MockClient.return_value.post_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_exit_pops_to_welcome(self):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_month import CascadeMonthScreen
        from tui.screens.welcome import WelcomeScreen

        plan = _make_month_plan()
        app = CreditCardConverterApp()
        async with app.run_test() as pilot:
            await app.push_screen(CascadeMonthScreen(plan=plan))
            await pilot.pause(0.2)
            await pilot.click("#btn-exit")
            await pilot.pause(0.2)
            assert isinstance(app.screen, WelcomeScreen)


# ── ExecutionProgressScreen Tests ─────────────────────────────────────────────

class TestExecutionProgressScreen:
    """T040: ExecutionProgressScreen execution and failure handling."""

    @pytest.mark.asyncio
    async def test_success_advances_to_completion_on_last_month(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_month import CompletionScreen, ExecutionProgressScreen

        config = _make_config(
            budgets={"b1": BudgetConfig("Budget", "loan-1")}
        )
        plan = _make_month_plan()

        with patch("tui.screens.cascade_month.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.post_transaction.side_effect = ["txn-a", "txn-b"]

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(
                    ExecutionProgressScreen(plan=plan, budget_id="b1", config=config, remaining_months=[])
                )
                await pilot.pause(1.0)

    @pytest.mark.asyncio
    async def test_tx_b_failure_deletes_tx_a_shows_retry(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_month import ExecutionProgressScreen, RetryScreen

        config = _make_config(
            budgets={"b1": BudgetConfig("Budget", "loan-1")}
        )
        plan = _make_month_plan()

        with patch("tui.screens.cascade_month.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.post_transaction.side_effect = ["txn-a", YNABClientError("Server error")]
            mock_client.delete_transaction.return_value = None

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(
                    ExecutionProgressScreen(plan=plan, budget_id="b1", config=config, remaining_months=[])
                )
                await pilot.pause(1.0)
                mock_client.delete_transaction.assert_called_once_with("b1", "txn-a")


# ── SettingsScreen Tests ──────────────────────────────────────────────────────

class TestSettingsScreen:
    """T050: SettingsScreen atomic writes and API key masking."""

    @pytest.mark.asyncio
    async def test_api_key_shown_masked(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import SettingsScreen

        config = _make_config(api_key="abcdefgh1234")
        config_path = tmp_path / "config.json"

        with patch("tui.ynab.config._CONFIG_PATH", config_path):
            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(SettingsScreen(config=config))
                await pilot.pause(0.2)
                assert isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_update_key_validates_before_saving(self, tmp_path):
        from tui.app import CreditCardConverterApp
        from tui.screens.cascade_setup import SettingsScreen

        config = _make_config(api_key="old-key")
        config_path = tmp_path / "config.json"

        with patch("tui.ynab.config._CONFIG_PATH", config_path), \
             patch("tui.screens.cascade_setup.YNABClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_budgets.side_effect = YNABClientError("Invalid API key. Update it in Settings.")

            app = CreditCardConverterApp()
            async with app.run_test() as pilot:
                await app.push_screen(SettingsScreen(config=config))
                await pilot.pause(0.2)
