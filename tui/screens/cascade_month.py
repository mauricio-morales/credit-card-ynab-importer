"""Month-by-month cascade wizard: plan summary → confirm → execute → retry/completion."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, LoadingIndicator, Static

from tui.ynab.cascade import (
    CarryoverTuplet,
    DonorAllocation,
    MonthPlan,
    build_month_plan,
    build_split_subtransactions,
    format_milliunits,
)
from tui.ynab.client import YNABClient, YNABClientError
from tui.ynab.config import Config


def _last_day_of_month(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _first_day_of_next_month(d: date) -> date:
    last = _last_day_of_month(d)
    return last + timedelta(days=1)


# ── CascadeMonthScreen ────────────────────────────────────────────────────────

class CascadeMonthScreen(Screen):
    """Shows the plan for one month and waits for user confirmation."""

    BINDINGS = [("escape", "exit_cascade", "Exit")]

    def __init__(
        self,
        plan: MonthPlan,
        budget_id: str = "",
        config: Config | None = None,
        remaining_months: list[date] | None = None,
        initial_scan_balances: dict[date, list] | None = None,
    ) -> None:
        super().__init__()
        self._plan = plan
        self._budget_id = budget_id
        self._config = config
        self._remaining_months = remaining_months or []
        self._initial_scan_balances = initial_scan_balances or {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        n_cats = len(self._plan.carryovers)
        yield Label(
            f"Fixing {self._plan.month.strftime('%B %Y')} — {n_cats} categor{'y' if n_cats == 1 else 'ies'}",
            id="month-header",
        )
        yield DataTable(id="month-table")
        yield Static("", id="month-warning")
        yield Button("Confirm & Execute", id="btn-confirm", variant="success")
        yield Button("Exit (keep completed months)", id="btn-exit", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#month-table", DataTable)
        table.add_columns("Category (Group / Name)", "Deficit", "Donor(s)", "Amount(s)")
        for co in self._plan.carryovers:
            suffix = "  [carried from prior month]" if co.is_carry_forward else ""
            cat_label = f"{co.target_group_name} / {co.target_category_name}{suffix}"
            donor_names = ", ".join(d.donor_category_name for d in self._plan.donors)
            donor_amounts = ", ".join(format_milliunits(d.amount_milliunits) for d in self._plan.donors)
            table.add_row(
                cat_label,
                format_milliunits(co.deficit_milliunits),
                donor_names,
                donor_amounts,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.app.push_screen(ExecutionProgressScreen(
                plan=self._plan,
                budget_id=self._budget_id,
                config=self._config,
                remaining_months=self._remaining_months,
                initial_scan_balances=self._initial_scan_balances,
            ))
        elif event.button.id == "btn-exit":
            self.action_exit_cascade()

    def action_exit_cascade(self) -> None:
        from tui.screens.welcome import WelcomeScreen
        while len(self.app.screen_stack) > 1 and not isinstance(self.app.screen_stack[-1], WelcomeScreen):
            self.app.pop_screen()
        if isinstance(self.app.screen_stack[-1], WelcomeScreen):
            self.app.switch_screen(WelcomeScreen())


# ── ExecutionProgressScreen ───────────────────────────────────────────────────

class ExecutionProgressScreen(Screen):
    """Executes the atomic Tx A + Tx B pair and shows progress."""

    def __init__(
        self,
        plan: MonthPlan,
        budget_id: str,
        config: Config | None,
        remaining_months: list[date],
        initial_scan_balances: dict[date, list] | None = None,
    ) -> None:
        super().__init__()
        self._plan = plan
        self._budget_id = budget_id
        self._config = config or Config()
        self._remaining_months = remaining_months
        self._initial_scan_balances = initial_scan_balances or {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label(f"Executing {self._plan.month.strftime('%B %Y')}…", id="exec-header")
        yield DataTable(id="exec-table")
        yield Static("", id="exec-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#exec-table", DataTable)
        table.add_column("Step", key="step")
        table.add_column("Status", key="status")
        table.add_row("Create Transaction A", "Pending…", key="tx-a")
        table.add_row("Create Transaction B", "Pending…", key="tx-b")
        self.run_worker(self._execute(), exclusive=True)

    async def _execute(self) -> None:
        table = self.query_one("#exec-table", DataTable)
        status = self.query_one("#exec-status", Static)
        client = YNABClient(self._config.api_key)

        tx_a_subs, tx_b_subs = build_split_subtransactions(
            self._plan.carryovers, self._plan.donors
        )

        month = self._plan.month
        loan_id = self._config.budgets[self._budget_id].loan_account_id

        payload_a = {
            "transaction": {
                "account_id": loan_id,
                "date": _last_day_of_month(month).isoformat(),
                "amount": 0,
                "cleared": "cleared",
                "approved": True,
                "payee_name": "Cascade Carryover",
                "subtransactions": [
                    {"amount": s.amount_milliunits, "category_id": s.category_id, "memo": s.memo}
                    for s in tx_a_subs
                ],
            }
        }

        payload_b = {
            "transaction": {
                "account_id": loan_id,
                "date": _first_day_of_next_month(month).isoformat(),
                "amount": 0,
                "cleared": "cleared",
                "approved": True,
                "payee_name": "Cascade Carryover",
                "subtransactions": [
                    {"amount": s.amount_milliunits, "category_id": s.category_id, "memo": s.memo}
                    for s in tx_b_subs
                ],
            }
        }

        # POST Transaction A
        table.update_cell("tx-a", "status", "In Progress…")
        try:
            txn_a_id = client.post_transaction(self._budget_id, payload_a)
            self._plan.transaction_a_id = txn_a_id
            table.update_cell("tx-a", "status", "✓ Done")
        except YNABClientError as exc:
            table.update_cell("tx-a", "status", "✗ Failed")
            status.update(f"Transaction A failed: {exc}")
            self.app.switch_screen(RetryScreen(
                plan=self._plan,
                budget_id=self._budget_id,
                config=self._config,
                remaining_months=self._remaining_months,
                error=str(exc),
                initial_scan_balances=self._initial_scan_balances,
            ))
            return

        # POST Transaction B
        table.update_cell("tx-b", "status", "In Progress…")
        try:
            txn_b_id = client.post_transaction(self._budget_id, payload_b)
            self._plan.transaction_b_id = txn_b_id
            table.update_cell("tx-b", "status", "✓ Done")
        except YNABClientError as exc:
            table.update_cell("tx-b", "status", "✗ Failed")
            # Rollback Tx A
            try:
                client.delete_transaction(self._budget_id, txn_a_id)
                self._plan.transaction_a_id = None
            except YNABClientError as del_exc:
                status.update(str(del_exc))
            self.app.switch_screen(RetryScreen(
                plan=self._plan,
                budget_id=self._budget_id,
                config=self._config,
                remaining_months=self._remaining_months,
                error=str(exc),
                initial_scan_balances=self._initial_scan_balances,
            ))
            return

        # Success — advance
        if self._remaining_months:
            await self._advance_to_next_month(client)
        else:
            self.app.switch_screen(CompletionScreen(
                completed_plans=[self._plan],
                budget_id=self._budget_id,
                config=self._config,
            ))

    async def _advance_to_next_month(self, client: YNABClient) -> None:
        next_month = self._remaining_months[0]
        remaining = self._remaining_months[1:]
        try:
            live = client.get_month_balances(self._budget_id, next_month)
            from tui.ynab.client import CategoryMonthBalance
            categories = client.get_categories(self._budget_id)
            cc_ids = {c.id for c in categories if c.is_credit_card_payment}
            enriched = [
                CategoryMonthBalance(
                    category_id=b.category_id,
                    category_name=b.category_name,
                    group_name=b.group_name,
                    month=b.month,
                    available=b.available,
                    is_credit_card_payment=b.category_id in cc_ids,
                )
                for b in live
            ]
            initial = self._initial_scan_balances.get(next_month, [])
            next_plan = build_month_plan(next_month, enriched, initial)
            self.app.switch_screen(CascadeMonthScreen(
                plan=next_plan,
                budget_id=self._budget_id,
                config=self._config,
                remaining_months=remaining,
                initial_scan_balances=self._initial_scan_balances,
            ))
        except YNABClientError as exc:
            self.query_one("#exec-status", Static).update(f"Error loading next month: {exc}")


# ── RetryScreen ───────────────────────────────────────────────────────────────

class RetryScreen(Screen):
    """Shows failed allocations with retry or skip options."""

    def __init__(
        self,
        plan: MonthPlan,
        budget_id: str,
        config: Config | None,
        remaining_months: list[date],
        error: str,
        initial_scan_balances: dict[date, list] | None = None,
    ) -> None:
        super().__init__()
        self._plan = plan
        self._budget_id = budget_id
        self._config = config or Config()
        self._remaining_months = remaining_months
        self._error = error
        self._initial_scan_balances = initial_scan_balances or {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Execution Failed", id="retry-header")
        yield Static(f"Error: {self._error}", id="retry-error")
        yield Label("Options:", id="retry-options-label")
        yield Button("Retry Failed", id="btn-retry-failed", variant="warning")
        yield Button("Skip & Continue", id="btn-skip", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-retry-failed":
            # Clean up any orphaned Tx A before retry
            if self._plan.transaction_a_id:
                client = YNABClient(self._config.api_key)
                try:
                    client.delete_transaction(self._budget_id, self._plan.transaction_a_id)
                    self._plan.transaction_a_id = None
                except YNABClientError:
                    pass
            self.app.switch_screen(ExecutionProgressScreen(
                plan=self._plan,
                budget_id=self._budget_id,
                config=self._config,
                remaining_months=self._remaining_months,
                initial_scan_balances=self._initial_scan_balances,
            ))
        elif event.button.id == "btn-skip":
            self._skip_and_continue()

    def _skip_and_continue(self) -> None:
        if self._remaining_months:
            next_month = self._remaining_months[0]
            remaining = self._remaining_months[1:]
            try:
                client = YNABClient(self._config.api_key)
                live = client.get_month_balances(self._budget_id, next_month)
                initial = self._initial_scan_balances.get(next_month, [])
                next_plan = build_month_plan(next_month, live, initial)
                self.app.switch_screen(CascadeMonthScreen(
                    plan=next_plan,
                    budget_id=self._budget_id,
                    config=self._config,
                    remaining_months=remaining,
                    initial_scan_balances=self._initial_scan_balances,
                ))
            except YNABClientError as exc:
                self.query_one("#retry-error", Static).update(f"Error loading next month: {exc}")
        else:
            self.app.switch_screen(CompletionScreen(
                completed_plans=[],
                budget_id=self._budget_id,
                config=self._config,
            ))


# ── CompletionScreen ──────────────────────────────────────────────────────────

class CompletionScreen(Screen):
    """Shows summary and re-scans to confirm no negatives remain."""

    def __init__(
        self,
        completed_plans: list[MonthPlan],
        budget_id: str,
        config: Config | None,
    ) -> None:
        super().__init__()
        self._completed_plans = completed_plans
        self._budget_id = budget_id
        self._config = config or Config()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Cascade Complete!", id="completion-header")
        yield Static("All done! Your YNAB budget has been updated.", id="completion-msg")
        yield DataTable(id="completion-table")
        yield LoadingIndicator(id="completion-loading")
        yield Static("", id="completion-scan-status")
        yield Button("Back to Main Menu", id="btn-done", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#completion-table", DataTable)
        table.add_columns("Month", "Categories Fixed", "Donor Allocations")
        for plan in self._completed_plans:
            table.add_row(
                plan.month.strftime("%B %Y"),
                str(len(plan.carryovers)),
                str(len(plan.donors)),
            )
        self.run_worker(self._verify_clean(), exclusive=True)

    async def _verify_clean(self) -> None:
        loading = self.query_one("#completion-loading", LoadingIndicator)
        scan_status = self.query_one("#completion-scan-status", Static)
        try:
            from tui.screens.cascade_scan import _lookback_months
            from tui.ynab.cascade import build_scan_overview
            client = YNABClient(self._config.api_key)
            categories = client.get_categories(self._budget_id)
            cc_ids = {c.id for c in categories if c.is_credit_card_payment}

            from tui.ynab.client import CategoryMonthBalance
            all_balances: dict[date, list] = {}
            for month in _lookback_months(3):
                raw = client.get_month_balances(self._budget_id, month)
                enriched = [
                    CategoryMonthBalance(
                        category_id=b.category_id,
                        category_name=b.category_name,
                        group_name=b.group_name,
                        month=b.month,
                        available=b.available,
                        is_credit_card_payment=b.category_id in cc_ids,
                    )
                    for b in raw
                ]
                all_balances[month] = enriched

            overview = build_scan_overview(all_balances)
            loading.remove()
            if overview:
                scan_status.update(
                    f"Note: {sum(len(v) for v in overview.values())} negative categories still remain "
                    "(may be from new spending after the cascade ran)."
                )
            else:
                scan_status.update("✓ Confirmed: no negative categories remain in the lookback window.")
        except YNABClientError as exc:
            try:
                loading.remove()
            except Exception:
                pass
            scan_status.update(f"Could not re-scan: {exc}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            from tui.screens.welcome import WelcomeScreen
            while len(self.app.screen_stack) > 1 and not isinstance(self.app.screen_stack[-1], WelcomeScreen):
                self.app.pop_screen()
            if isinstance(self.app.screen_stack[-1], WelcomeScreen):
                self.app.switch_screen(WelcomeScreen())
