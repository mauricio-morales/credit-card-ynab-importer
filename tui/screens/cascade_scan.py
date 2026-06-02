"""CascadeScanScreen: clearance check + scan overview."""
from __future__ import annotations

from datetime import date, timedelta

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, LoadingIndicator, Static

from tui.ynab.cascade import (
    build_scan_overview,
    check_clearance,
    format_milliunits,
)
from tui.ynab.client import YNABClient, YNABClientError
from tui.ynab.config import Config


def _lookback_months(n: int = 3) -> list[date]:
    """Return the first-of-month dates for the last n complete calendar months."""
    today = date.today()
    months = []
    first_this_month = date(today.year, today.month, 1)
    for i in range(1, n + 1):
        # Go back i months
        d = first_this_month
        for _ in range(i):
            d = d - timedelta(days=1)
            d = date(d.year, d.month, 1)
        months.append(d)
    return sorted(months)


class CascadeScanScreen(Screen):
    """Runs clearance check and shows scan overview of negative months."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, budget_id: str, config: Config) -> None:
        super().__init__()
        self._budget_id = budget_id
        self._config = config
        self._loan_account_id = config.budgets[budget_id].loan_account_id
        self._initial_scan_balances: dict[date, list] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Monthly Overspend Cascade — Scan", id="scan-title")
        yield LoadingIndicator(id="scan-loading")
        yield Static("", id="scan-status")
        yield Static("", id="scan-error")
        yield DataTable(id="scan-table")
        yield Button("Retry", id="btn-retry", variant="primary")
        yield Button("Start Cascade", id="btn-start", variant="success")
        yield Button("Back", id="btn-back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#btn-retry").display = False
        self.query_one("#btn-start").display = False
        self.run_worker(self._run_scan(), exclusive=True)

    async def _run_scan(self) -> None:
        loading = self.query_one("#scan-loading", LoadingIndicator)
        status = self.query_one("#scan-status", Static)
        error = self.query_one("#scan-error", Static)
        table = self.query_one("#scan-table", DataTable)
        btn_retry = self.query_one("#btn-retry", Button)
        btn_start = self.query_one("#btn-start", Button)

        table.clear(columns=True)
        status.update("")
        error.update("")

        try:
            client = YNABClient(self._config.api_key)

            # 1. Account name lookup — include closed so UUIDs never appear in error messages
            status.update("Loading accounts…")
            accounts = client.get_accounts(self._budget_id, include_closed=True)
            account_name_map = {a.id: a.name for a in accounts}

            # 2. Category catalogue for CC detection
            status.update("Loading categories…")
            categories = client.get_categories(self._budget_id)
            cc_ids = {c.id for c in categories if c.is_credit_card_payment}

            # 3. Clearance check — only transactions through end of last complete month
            lookback_months = _lookback_months(3)
            since_date = lookback_months[0]
            today = date.today()
            first_this_month = date(today.year, today.month, 1)
            end_date = first_this_month - timedelta(days=1)
            date_range_label = f"{since_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}"
            status.update(f"Checking reconciliation for {date_range_label}…")
            transactions = client.get_transactions(self._budget_id, since_date)
            lookback_transactions = [
                t for t in transactions
                if t.get("date") and date.fromisoformat(t["date"]) < first_this_month
            ]
            clearance = check_clearance(lookback_transactions, self._loan_account_id, account_name_map)

            last_month = lookback_months[-1]
            if not clearance.passed:
                loading.remove()
                status.update(
                    f"Checking period: {date_range_label}. "
                    f"The following accounts have unreconciled transactions in that window. "
                    "Reconcile them in YNAB and press Retry."
                )
                table.add_columns("Account", "Unreconciled Txns", "Earliest Unreconciled")
                for issue in clearance.issues:
                    earliest = issue.earliest_unreconciled.strftime("%b %d, %Y") if issue.earliest_unreconciled else "—"
                    table.add_row(issue.account_name, str(issue.unreconciled_count), earliest)
                btn_retry.display = True
                return

            # 4. Fetch month balances and enrich with CC flag
            status.update("Scanning months for negative categories…")
            raw_month_balances: dict[date, list] = {}
            for month in lookback_months:
                balances = client.get_month_balances(self._budget_id, month)
                enriched = []
                for b in balances:
                    from tui.ynab.client import CategoryMonthBalance
                    enriched.append(CategoryMonthBalance(
                        category_id=b.category_id,
                        category_name=b.category_name,
                        group_name=b.group_name,
                        month=b.month,
                        available=b.available,
                        is_credit_card_payment=b.category_id in cc_ids,
                    ))
                raw_month_balances[month] = enriched

            self._initial_scan_balances = raw_month_balances
            overview = build_scan_overview(raw_month_balances)
            loading.remove()

            if not overview:
                status.update("No negative categories found in the last 3 months. Your budget history is clean.")
                btn_retry.display = False
                self.query_one("#btn-back", Button).display = True
                return

            # Show negatives table
            status.update("")
            table.add_columns("Month", "Negative Categories", "Total Deficit")
            for month, neg_cats in overview.items():
                total_deficit = sum(abs(b.available) for b in neg_cats)
                table.add_row(
                    month.strftime("%B %Y"),
                    str(len(neg_cats)),
                    format_milliunits(total_deficit),
                )

            self._overview = overview
            btn_start.display = True

        except YNABClientError as exc:
            try:
                loading.remove()
            except Exception:
                pass
            error.update(f"Error: {exc}")
            btn_retry.display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-retry":
            self.query_one("#btn-retry").display = False
            self.query_one("#scan-table", DataTable).clear(columns=True)
            ldi = LoadingIndicator(id="scan-loading")
            self.mount(ldi, before="#scan-status")
            self.run_worker(self._run_scan(), exclusive=True)
        elif event.button.id == "btn-start":
            self._start_cascade()
        elif event.button.id == "btn-back":
            self.action_go_back()

    def _start_cascade(self) -> None:
        if not hasattr(self, "_overview") or not self._overview:
            return
        from tui.ynab.cascade import build_month_plan
        from tui.screens.cascade_month import CascadeMonthScreen

        months = list(self._overview.keys())
        oldest_month = months[0]
        live_balances = self._initial_scan_balances[oldest_month]
        initial_scan = self._initial_scan_balances[oldest_month]
        plan = build_month_plan(oldest_month, live_balances, initial_scan)
        remaining = months[1:]

        self.app.push_screen(CascadeMonthScreen(
            plan=plan,
            budget_id=self._budget_id,
            config=self._config,
            remaining_months=remaining,
            initial_scan_balances=self._initial_scan_balances,
        ))

    def action_go_back(self) -> None:
        self.app.pop_screen()
