"""Cascade feature: setup wizard (API key → budget → loan account) + Settings screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, LoadingIndicator, Static
from textual.worker import Worker, WorkerState

from tui.ynab.client import YNABClient, YNABClientError
from tui.ynab.config import BudgetConfig, Config, load_config, save_config


# ── CascadeEntryScreen ────────────────────────────────────────────────────────

class CascadeEntryScreen(Screen):
    """Transparent routing: checks config and directs to wizard or budget picker."""

    def on_mount(self) -> None:
        cfg = load_config()
        if not cfg.api_key:
            self.app.switch_screen(SetupWizardScreen())
        else:
            self.app.switch_screen(BudgetSelectScreen(config=cfg))

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()


# ── SetupWizardScreen ─────────────────────────────────────────────────────────

class SetupWizardScreen(Screen):
    """Step 1: User enters YNAB API key."""

    BINDINGS = [("escape", "exit_cascade", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Monthly Overspend Cascade — Setup", id="wizard-title")
        yield Label(
            "Enter your YNAB Personal Access Token. "
            "Find it at app.ynab.com → Account Settings → Developer Settings.",
            id="wizard-help",
        )
        yield Input(placeholder="YNAB API key", password=True, id="api-key-input")
        yield Button("Validate & Continue", id="btn-validate", variant="primary")
        yield Static("", id="wizard-error")
        yield Footer()

    def action_exit_cascade(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-validate":
            self._validate_key()

    def _validate_key(self) -> None:
        key = self.query_one("#api-key-input", Input).value.strip()
        if not key:
            self._show_error("Please enter an API key.")
            return
        self._show_error("")
        self.query_one("#btn-validate").disabled = True
        self.run_worker(self._fetch_budgets(key), exclusive=True)

    async def _fetch_budgets(self, key: str) -> None:
        error_widget = self.query_one("#wizard-error", Static)
        btn = self.query_one("#btn-validate", Button)
        try:
            client = YNABClient(key)
            budgets = client.get_budgets()
            if not budgets:
                self._show_error("No budgets found for this API key.")
                btn.disabled = False
                return
            cfg = load_config()
            cfg.api_key = key
            save_config(cfg)
            self.app.push_screen(BudgetSelectScreen(config=load_config()))
        except YNABClientError as exc:
            self._show_error(str(exc))
            btn.disabled = False

    def _show_error(self, msg: str) -> None:
        self.query_one("#wizard-error", Static).update(msg)


# ── BudgetSelectScreen ────────────────────────────────────────────────────────

class BudgetSelectScreen(Screen):
    """Step 2: Select a YNAB budget."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._budgets: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Select a Budget", id="budget-select-title")
        yield LoadingIndicator(id="budget-loading")
        yield ListView(id="budget-list")
        yield Static("", id="budget-error")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_budgets(), exclusive=True)

    async def _load_budgets(self) -> None:
        loading = self.query_one("#budget-loading", LoadingIndicator)
        error = self.query_one("#budget-error", Static)
        lv = self.query_one("#budget-list", ListView)
        try:
            client = YNABClient(self._config.api_key)
            self._budgets = client.get_budgets()

            # Single budget already configured → skip directly to scan
            if len(self._budgets) == 1 and self._budgets[0]["id"] in self._config.budgets:
                loading.remove()
                from tui.screens.cascade_scan import CascadeScanScreen
                self.app.push_screen(CascadeScanScreen(
                    budget_id=self._budgets[0]["id"],
                    config=self._config,
                ))
                return

            for budget in self._budgets:
                configured = budget["id"] in self._config.budgets
                label = f"{'✓ ' if configured else ''}{budget['name']}"
                lv.append(ListItem(Label(label), id=f"budget-{budget['id']}"))
            loading.remove()
        except YNABClientError as exc:
            loading.remove()
            error.update(f"Error: {exc}  [Press R to retry]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        budget_id = item_id.removeprefix("budget-")
        budget = next((b for b in self._budgets if b["id"] == budget_id), None)
        if budget is None:
            return
        if budget_id in self._config.budgets:
            from tui.screens.cascade_scan import CascadeScanScreen
            self.app.push_screen(CascadeScanScreen(budget_id=budget_id, config=self._config))
        else:
            self.app.push_screen(
                AccountSelectScreen(
                    budget_id=budget_id,
                    budget_name=budget["name"],
                    config=self._config,
                )
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── AccountSelectScreen ───────────────────────────────────────────────────────

class AccountSelectScreen(Screen):
    """Step 3: Select the internal loan account for a budget."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, budget_id: str, budget_name: str, config: Config) -> None:
        super().__init__()
        self._budget_id = budget_id
        self._budget_name = budget_name
        self._config = config
        self._accounts: list = []
        self._selected_account_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label(f"Budget: {self._budget_name}", id="account-budget-label")
        yield Label("Select the internal loan account for cascade transactions:", id="account-help")
        yield LoadingIndicator(id="account-loading")
        yield ListView(id="account-list")
        yield Button("Save", id="btn-save-account", variant="primary", disabled=True)
        yield Button("Back", id="btn-back-account")
        yield Static("", id="account-error")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_accounts(), exclusive=True)

    async def _load_accounts(self) -> None:
        loading = self.query_one("#account-loading", LoadingIndicator)
        error = self.query_one("#account-error", Static)
        lv = self.query_one("#account-list", ListView)
        try:
            client = YNABClient(self._config.api_key)
            self._accounts = client.get_accounts(self._budget_id)
            for acc in self._accounts:
                lv.append(ListItem(Label(acc.name), id=f"account-{acc.id}"))
            loading.remove()
        except YNABClientError as exc:
            loading.remove()
            error.update(f"Error: {exc}  [Press R to retry]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        self._selected_account_id = item_id.removeprefix("account-")
        self.query_one("#btn-save-account", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-account":
            self._save()
        elif event.button.id == "btn-back-account":
            self.action_go_back()

    def _save(self) -> None:
        if not self._selected_account_id:
            return
        self._config.budgets[self._budget_id] = BudgetConfig(
            budget_name=self._budget_name,
            loan_account_id=self._selected_account_id,
        )
        save_config(self._config)
        from tui.screens.cascade_scan import CascadeScanScreen
        self.app.push_screen(CascadeScanScreen(budget_id=self._budget_id, config=self._config))

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── SettingsScreen ────────────────────────────────────────────────────────────

class SettingsScreen(Screen):
    """Settings: update API key, change loan accounts, remove budgets."""

    BINDINGS = [("escape", "go_back", "Cancel")]

    def __init__(self, config: Config | None = None) -> None:
        super().__init__()
        self._config = config or load_config()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Settings", id="settings-title")

        masked = self._mask_key(self._config.api_key)
        yield Label(f"API Key: {masked}", id="settings-api-key-label")
        yield Input(placeholder="New API key", password=True, id="settings-api-key-input")
        yield Button("Update Key", id="btn-update-key", variant="primary")
        yield Static("", id="settings-key-error")

        if self._config.budgets:
            yield Label("Configured Budgets:", id="settings-budgets-label")
            for budget_id, bc in self._config.budgets.items():
                yield Static(
                    f"{bc.budget_name} | Loan: {bc.loan_account_id}",
                    id=f"settings-budget-{budget_id}",
                )
                yield Button(
                    "Remove Budget",
                    id=f"btn-remove-{budget_id}",
                    variant="warning",
                )

        yield Button("Add Budget", id="btn-add-budget")
        yield Button("Cancel", id="btn-cancel")
        yield Footer()

    @staticmethod
    def _mask_key(key: str) -> str:
        if len(key) <= 4:
            return "****"
        return f"****{key[-4:]}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-update-key":
            self._update_key()
        elif btn_id.startswith("btn-remove-"):
            budget_id = btn_id.removeprefix("btn-remove-")
            self._remove_budget(budget_id)
        elif btn_id == "btn-add-budget":
            self.app.push_screen(BudgetSelectScreen(config=self._config))
        elif btn_id == "btn-cancel":
            self.action_go_back()

    def _update_key(self) -> None:
        new_key = self.query_one("#settings-api-key-input", Input).value.strip()
        if not new_key:
            self.query_one("#settings-key-error", Static).update("Please enter a key.")
            return
        self.query_one("#btn-update-key", Button).disabled = True
        self.run_worker(self._validate_and_save_key(new_key), exclusive=True)

    async def _validate_and_save_key(self, new_key: str) -> None:
        error = self.query_one("#settings-key-error", Static)
        btn = self.query_one("#btn-update-key", Button)
        try:
            client = YNABClient(new_key)
            client.get_budgets()
            self._config.api_key = new_key
            save_config(self._config)
            masked = self._mask_key(new_key)
            self.query_one("#settings-api-key-label", Label).update(f"API Key: {masked}")
            error.update("Key updated successfully.")
        except YNABClientError as exc:
            error.update(str(exc))
        finally:
            btn.disabled = False

    def _remove_budget(self, budget_id: str) -> None:
        if budget_id in self._config.budgets:
            del self._config.budgets[budget_id]
            save_config(self._config)
            self.refresh(recompose=True)

    def action_go_back(self) -> None:
        self.app.pop_screen()
