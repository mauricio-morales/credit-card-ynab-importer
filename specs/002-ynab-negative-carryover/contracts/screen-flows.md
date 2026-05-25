# Contract: TUI Screen Flows

**Branch**: `002-ynab-negative-carryover` | **Date**: 2026-05-25

This document defines the screen transition contracts for the Monthly Overspend Cascade feature. Each screen section specifies: entry conditions, user actions, exit transitions, and error states.

---

## Navigation Overview

```
WelcomeScreen
├── [key 1 / btn] → BAC CSV flow (existing, unchanged)
├── [key 2 / btn] → DaviBank XLS flow (existing, unchanged)
├── [key 3 / btn] → CascadeEntryScreen
└── [key s / btn] → SettingsScreen (accessible any time)

CascadeEntryScreen
├── [no api_key] → SetupWizardScreen (API key entry)
└── [api_key exists] → BudgetSelectScreen

SetupWizardScreen (step 1: API key)
├── [valid key] → BudgetSelectScreen (step 2)
└── [invalid key] → error inline, stay on screen

BudgetSelectScreen (step 2: budget)
├── [budget already configured] → CascadeScanScreen (for that budget)
├── [budget not yet configured] → AccountSelectScreen (step 3)
└── [back] → SetupWizardScreen (if no api_key yet) or WelcomeScreen

AccountSelectScreen (step 3: loan account)
├── [account selected] → per-budget config entry saved → CascadeScanScreen
└── [back] → BudgetSelectScreen

CascadeScanScreen
├── [uncleared transactions] → blocked state (same screen, retry option)
├── [all clear, negatives found] → scan overview → CascadeMonthScreen (oldest month)
└── [all clear, no negatives] → clean state message

CascadeMonthScreen
├── [confirm] → ExecutionProgressScreen
└── [exit] → WelcomeScreen (completed months remain in YNAB)

ExecutionProgressScreen
├── [all success] → CascadeMonthScreen (next month) or CompletionScreen (last month)
└── [partial failure] → RetryScreen

RetryScreen
├── [retry failed] → ExecutionProgressScreen (failed allocations only)
└── [skip / exit] → CascadeMonthScreen (next month) or CompletionScreen

CompletionScreen
└── [done] → WelcomeScreen

SettingsScreen
├── [save valid changes] → previous screen
└── [cancel] → previous screen
```

---

## Screen Contracts

### WelcomeScreen (modified)

**Entry**: App launch. No YNAB check performed at this point (FR-001, FR-002).

**New element**: "Monthly Overspend Cascade" button (id: `btn-cascade`, key: `3`).

**Exit**:
- Button `btn-cascade` / key `3` → push `CascadeEntryScreen`
- Key `s` → push `SettingsScreen`

**Error states**: None — no YNAB calls made here.

---

### CascadeEntryScreen

**Entry**: Always from WelcomeScreen. Immediately checks for config file existence (no network call).

**Behavior**: Transparent routing screen — no UI rendered. Reads `~/.config/credit-card-ynab-importer/config.json`.

**Exit**:
- No `api_key` in config (or no config file) → replace with `SetupWizardScreen`
- `api_key` present → replace with `BudgetSelectScreen`

---

### SetupWizardScreen — Step 1: API Key

**Entry**: No API key stored. First time a user accesses the cascade feature.

**UI elements**:
- Explanatory label (what an API key is, where to get it)
- `Input` widget for API key (masked)
- "Validate & Continue" button
- Loading indicator while validating

**Actions**:
- Submit: `GET /v1/budgets` with entered key
  - 200 + non-empty budget list → write `api_key` to config; advance to `BudgetSelectScreen`
  - 401 / empty budgets list → inline error message, key field stays editable
  - Network error → inline error with retry option; no config written

**Invariant**: Only `api_key` is written at this step. No budget entry is written yet.

---

### BudgetSelectScreen — Step 2: Budget

**Entry**: API key already stored. Fetches budget list via `GET /v1/budgets` (uses stored key).

**UI elements**:
- `ListView` of all YNAB budgets by name
- Already-configured budgets marked with a checkmark indicator
- Loading indicator during fetch

**Actions**:
- Select already-configured budget → push `CascadeScanScreen` scoped to that budget (no further setup needed)
- Select unconfigured budget → push `AccountSelectScreen` with that budget's id + name
- Back → pop to WelcomeScreen
- Network error → inline error with retry

**Note**: If the user has exactly one budget and it is already configured, this screen is skipped and `CascadeScanScreen` is shown directly.

---

### AccountSelectScreen — Step 3: Loan Account

**Entry**: Budget selected but not yet configured. Account list fetched via `GET /v1/budgets/{budget_id}/accounts`.

**UI elements**:
- Budget name shown as context header
- `ListView` of account names (on-budget, not deleted, not closed)
- "Save" button
- "Back" button

**Actions**:
- Select + Save → write `budgets[budget_id] = {budget_name, loan_account_id}` into config (atomic file write) → push `CascadeScanScreen`
- Back → pop back to `BudgetSelectScreen`
- Network error on account fetch → inline error with retry; user stays on this screen

**Exit invariant**: Config entry for this budget is written atomically (temp file → rename). Existing entries for other budgets are preserved.

---

### CascadeScanScreen

**Entry**: Valid config present.

**On mount (async worker)**:
1. `GET /v1/budgets/{budget_id}/accounts` — build account name lookup
2. `GET /v1/budgets/{budget_id}/categories` — build category/group list, identify CC payment groups
3. `GET /v1/budgets/{budget_id}/transactions?since_date={lookback_start}` — clearance check
4. If clearance passes: `GET /v1/budgets/{budget_id}/months/{YYYY-MM-01}` for each of 3 lookback months

**States**:

*Loading*: Spinner with "Checking transactions…" status.

*Blocked (unreconciled transactions)*:
- Show per-account table: Account Name | Unreconciled Transactions
- Show: "All accounts must be fully reconciled before the cascade can run. Reconcile these accounts in YNAB and press Retry."
- "Retry" button → re-run clearance check (re-fetch transactions only)
- Note: the internal loan account is never listed here even if it has cleared (non-reconciled) transactions

*Clean (no negatives)*:
- Show: "No negative categories found in the last 3 months. Your budget history is clean."
- "Back" button → WelcomeScreen

*Negatives found*:
- Table: Month | Negative categories count | Total deficit
- Rows ordered oldest-to-most-recent
- "Start Cascade" button → push `CascadeMonthScreen` with oldest MonthPlan

*Error (network)*:
- Show error message + "Retry" button; no stale data displayed

---

### CascadeMonthScreen

**Entry**: Receives a `MonthPlan`.

**UI elements**:
- Month header: "Fixing [Month YYYY] — [N categories]"
- Table per carryover tuplet:
  - Category (group / name) | Deficit | Donor(s) | Amount(s)
  - Rows induced by carry-forward are marked "[carried from prior month]"
- Warning banner if donor balance shortfall detected (should not occur per spec, but surfaced if it does)
- "Confirm & Execute" button
- "Exit (keep completed months)" button

**Exit**:
- Confirm → push `ExecutionProgressScreen` with this month's `MonthPlan`
- Exit → pop to WelcomeScreen (completed months are already persisted in YNAB)

---

### ExecutionProgressScreen

**Entry**: Receives a `MonthPlan`. Runs execution as async workers.

**UI elements**:
- Progress list: one row per `CarryoverTuplet` → Pending / In Progress / ✓ Done / ✗ Failed
- Each row shows donor allocations and their status

**Execution**:
- For each `CarryoverTuplet`, for each `DonorAllocation`:
  - POST Transaction A → store `transaction_a_id`
  - POST Transaction B → store `transaction_b_id`
  - If Transaction B fails: DELETE Transaction A (rollback), mark allocation Failed
- Category marked Done when all its allocations complete. Failed when any allocation fails after rollback.

**Exit**:
- All done → if more months: replace with `CascadeMonthScreen` (next month)
- All done → if last month: replace with `CompletionScreen`
- Any failures → replace with `RetryScreen`

---

### RetryScreen

**Entry**: Receives list of failed `DonorAllocation` objects.

**UI elements**:
- "These allocations failed: [list]"
- "Retry Failed" button
- "Skip & Continue" button (advances to next month, failed categories are not re-attempted)

**Exit**:
- Retry → re-run failed allocations only, then back to `ExecutionProgressScreen` result handling
- Skip → advance to next month or `CompletionScreen`

---

### CompletionScreen

**Entry**: All months processed (or user skipped remaining).

**UI elements**:
- Summary table: Month | Categories fixed | Donor allocations created
- "All done! Your YNAB budget has been updated."
- "Back to Main Menu" button → WelcomeScreen

---

### SettingsScreen

**Entry**: From any screen via key `s` or main menu.

**UI elements**:
- API key field (masked, shows last 4 chars); "Update Key" button
- Per-budget table: Budget Name | Loan Account Name | Actions
  - Each row: "Change Account" button, "Remove Budget" button
- "Add Budget" button → triggers `BudgetSelectScreen` flow for an unconfigured budget
- "Cancel" button

**Actions**:
- Update API key: validate live (`GET /v1/budgets`); if valid, overwrite `api_key` in config; if invalid, inline error
- Change account for a budget: `GET /v1/budgets/{budget_id}/accounts` → inline `ListView` → select → update that budget's `loan_account_id` in config
- Remove budget: delete that budget's entry from the `budgets` map in config (does not affect other budgets or the API key)
- Add budget: navigate to `BudgetSelectScreen`; on completion return to SettingsScreen

**Exit**:
- Any saved change writes atomically to config
- Cancel → pop back (no pending unsaved changes; each action saves immediately)

---

## Key Bindings (new additions)

| Key | Screen | Action |
|-----|--------|--------|
| `3` | WelcomeScreen | Navigate to cascade feature |
| `s` | WelcomeScreen | Open Settings |
| `ctrl+c` | All | Quit (existing binding, unchanged) |
| `q` | WelcomeScreen | Quit (existing binding, unchanged) |
| `escape` | Cascade screens | Exit to WelcomeScreen |
