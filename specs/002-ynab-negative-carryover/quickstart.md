# Quickstart: Monthly Overspend Cascade

**Branch**: `002-ynab-negative-carryover`

---

## Prerequisites

1. Python 3.9+ installed
2. Install dependencies (adds `requests` on top of existing deps):
   ```
   pip install -r requirements.txt
   ```
3. A YNAB Personal Access Token — generate one at [app.ynab.com/settings/developer](https://app.ynab.com/settings/developer)
4. An existing "internal loan account" in your YNAB budget (a manual, on-budget account not linked to any real bank)

---

## First Run (credential setup)

```
python -m tui
```

On the Welcome screen, press `3` or click "Monthly Overspend Cascade".

Because no config exists yet, the app will present the setup wizard:

1. **Enter your YNAB API key** — the app validates it live and retrieves your budget list.
2. **Select a budget** — choose which budget to cascade (e.g., "CRC Budget" or "USD Budget").
3. **Select the internal loan account** — choose from that budget's on-budget accounts.
4. Config is saved to `~/.config/credit-card-ynab-importer/config.json`.

To configure a second budget, navigate to the cascade feature again and select the other budget — the API key step is skipped since it's already stored.

---

## Running the Cascade

After setup (or on any subsequent run):

1. Navigate to "Monthly Overspend Cascade" from the Welcome screen.
2. The app checks that all transactions in the last 3 months are cleared or reconciled.
   - If blocked: reconcile the listed accounts in YNAB, then press Retry.
3. If the check passes, a scan overview shows which months have negative categories.
4. Press "Start Cascade" to begin the month-by-month wizard.
5. Review each month's summary (categories + auto-assigned donors), then press "Confirm & Execute".
6. Repeat for each month. A completion summary is shown when all months are processed.

---

## Updating Settings

Press `s` from the Welcome screen to open Settings. You can update your API key or switch the loan account at any time.

---

## Running Tests

```
pytest tests/
```

YNAB API calls are fully mocked — no real network calls are made in the test suite.

To run only cascade-related tests:
```
pytest tests/test_ynab_client.py tests/test_cascade_logic.py tests/test_cascade_screens.py
```

---

## Config File

Location: `~/.config/credit-card-ynab-importer/config.json`

The file is stored outside the repository and is never committed. Contents:
```json
{
  "api_key": "your-ynab-personal-access-token",
  "budget_id": "ynab-budget-uuid",
  "loan_account_id": "ynab-loan-account-uuid"
}
```

To reset configuration, delete this file and re-run the app.
