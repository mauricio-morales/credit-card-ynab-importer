# Tasks: Monthly Overspend Cascade

**Input**: Design documents from `specs/002-ynab-negative-carryover/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

Tests are included per plan.md §Project Structure and constitution principle III (Test-First). All YNAB HTTP calls in tests must be mocked — zero real network calls in the test suite.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the `requests` dependency, protect the config file from version control, and create the new `tui/ynab/` package.

- [X] T001 Add `requests>=2.28` to `requirements.txt`
- [X] T002 [P] Add `config.json` to `.gitignore` (belt-and-suspenders precaution per research.md §5)
- [X] T003 [P] Create `tui/ynab/__init__.py` as an empty package initializer

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All data model dataclasses, config I/O, and the YNAB HTTP client base that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Implement `BudgetConfig` and `Config` dataclasses, `load_config() -> Config` (returns empty Config when file missing), and `save_config(config: Config) -> None` (atomic write: write to `.tmp` then rename, preserves existing budget entries) per data-model.md §Persistent Entities in `tui/ynab/config.py`
- [X] T005 [P] Implement `YNABAccount`, `CategoryGroup`, `Category`, and `CategoryMonthBalance` dataclasses per data-model.md §Runtime Entities in `tui/ynab/client.py`
- [X] T006 [P] Implement `DonorAllocation`, `SplitSubtransaction`, `CarryoverTuplet`, `MonthPlan`, `AccountReconciliationIssue`, `ClearanceCheckResult`, and `MonthExecutionResult` dataclasses per data-model.md §Planning Entities in `tui/ynab/cascade.py`
- [X] T007 Implement `YNABClient.__init__(api_key: str)` with `requests.Session` (Bearer auth header, `Content-Type: application/json`, 15 s timeout) and `_request(method, path, **kwargs)` base method with HTTP error dispatch: 400→descriptive error, 401→"Invalid API key", 404→specific "not found" message, 429→parse `X-Rate-Limit` header and pause until reset then retry once, 5xx→show error with retry option; network timeout→show error with retry per contracts/ynab-api.md §Error Handling in `tui/ynab/client.py`
- [X] T008 [P] Implement `format_milliunits(amount: int) -> str` converting YNAB milliunits to human-readable currency string (e.g., `1234560 → "$1,234.56"`; display as positive value per FR-010) in `tui/ynab/cascade.py`

**Checkpoint**: Foundation ready — all user story implementation can now begin.

---

## Phase 3: User Story 1 — Connect to YNAB (Priority: P1) 🎯 MVP

**Goal**: A first-time user navigating to "Monthly Overspend Cascade" sees a setup wizard (API key → budget selection → loan account selection) and has configuration saved to `~/.config/credit-card-ynab-importer/config.json`. On subsequent visits the wizard is skipped and the scan screen loads directly. Existing CSV workflow is completely unaffected (FR-001).

**Independent Test**: Launch the app with no config file. Navigate to cascade. Verify the wizard appears, accepts a valid mocked API key, fetches budgets, allows selection, fetches accounts, allows loan account selection, and writes the config file (with budget ID as key, loan account ID — not name). Restart; verify wizard is skipped and scan screen loads. Launch with CSV only; verify no YNAB prompt appears at any point.

### Tests for User Story 1

- [X] T009 [US1] Write unit tests for `YNABClient.get_budgets()`: 200 with budget list, 401 invalid key, empty budgets array, network timeout — all HTTP calls mocked in `tests/test_ynab_client.py`
- [X] T010 [US1] Write unit tests for `YNABClient.get_accounts(budget_id)`: 200 with account list, filtering (on_budget=True, deleted=False, closed=False applied correctly), network error in `tests/test_ynab_client.py`
- [X] T011 [P] [US1] Write unit tests for `load_config()` and `save_config()`: missing file returns empty Config, api_key-only config (no budgets), multi-budget map preservation after save, atomic write verified (tmp file renamed) in `tests/test_cascade_logic.py`
- [X] T012 [P] [US1] Write Textual screen tests for `SetupWizardScreen`: valid key + submit → advances to BudgetSelectScreen and writes api_key; 401 → inline error, screen stays; network error → inline error with retry; no config written on failure in `tests/test_cascade_screens.py`
- [X] T013 [US1] Write Textual screen tests for `BudgetSelectScreen` and `AccountSelectScreen`: already-configured budget → routes to CascadeScanScreen; unconfigured budget → AccountSelectScreen; single configured budget auto-skips; account save writes atomic config entry; Back navigation works in `tests/test_cascade_screens.py`

### Implementation for User Story 1

- [X] T014 [US1] Add `get_budgets() -> list[dict]` to `YNABClient` calling `GET /v1/budgets`; returns parsed budget list per contracts/ynab-api.md §GET /budgets in `tui/ynab/client.py`
- [X] T015 [US1] Add `get_accounts(budget_id: str) -> list[YNABAccount]` to `YNABClient` calling `GET /v1/budgets/{budget_id}/accounts`; filters to `on_budget=True, deleted=False, closed=False` per contracts/ynab-api.md §GET /accounts in `tui/ynab/client.py`
- [X] T016 [US1] Implement `CascadeEntryScreen` — transparent routing screen (no UI rendered): reads config file without a network call; no api_key in config → replace with `SetupWizardScreen`; api_key present → replace with `BudgetSelectScreen` per screen-flows.md §CascadeEntryScreen in `tui/screens/cascade_setup.py`
- [X] T017 [US1] Implement `SetupWizardScreen` — masked Input widget, "Validate & Continue" button, loading indicator; submit calls `get_budgets()` via Textual worker; 200 with budgets → write `api_key` to config via `save_config()`, push `BudgetSelectScreen`; 401 or empty budgets → inline error, field stays editable; network error → inline error with retry; no config written on any failure per screen-flows.md §SetupWizardScreen in `tui/screens/cascade_setup.py`
- [X] T018 [US1] Implement `BudgetSelectScreen` — fetches budget list via `get_budgets()` in worker; `ListView` with checkmark indicator on already-configured budgets; if exactly one budget and already configured → skip to `CascadeScanScreen` automatically; configured selection → push `CascadeScanScreen` scoped to that budget; unconfigured selection → push `AccountSelectScreen` with budget_id and budget_name; network error → inline retry per screen-flows.md §BudgetSelectScreen in `tui/screens/cascade_setup.py`
- [X] T019 [US1] Implement `AccountSelectScreen` — budget name displayed as context header; fetches accounts via `get_accounts()` in worker; `ListView` of on-budget non-deleted non-closed accounts; Save → write `budgets[budget_id] = {budget_name, loan_account_id}` via `save_config()` (atomic, preserves other budgets) → push `CascadeScanScreen`; Back → pop to `BudgetSelectScreen`; network error → inline retry per screen-flows.md §AccountSelectScreen in `tui/screens/cascade_setup.py`
- [X] T020 [US1] Add "Monthly Overspend Cascade" button (id: `btn-cascade`, key: `3`) and Settings key binding (`s` → push `SettingsScreen`) to `tui/screens/welcome.py`
- [X] T021 [US1] Wire cascade route in `tui/app.py` `on_mount` so that key `3` on `WelcomeScreen` pushes `CascadeEntryScreen`

**Checkpoint**: User Story 1 complete — wizard, config persistence, and routing all independently testable.

---

## Phase 4: User Story 2 — Scan Past Months for Negative Categories (Priority: P1)

**Goal**: With credentials configured, the scan screen performs a clearance check (all non-loan-account transactions in the lookback window must be reconciled — status R), then scans the last 3 complete calendar months for negative non-CC categories, displaying them grouped by month ordered oldest-first.

**Independent Test**: (a) Mock one uncleared transaction in any non-loan account → verify cascade blocks and shows that account name with its unreconciled count. (b) Mock all reconciled → verify scan results contain no credit card payment categories even if they have negative balances. (c) Mock known negatives in Feb and Apr → verify those months appear with correct category names, group names, and positive carryover amounts.

### Tests for User Story 2

- [X] T022 [US2] Write unit tests for `YNABClient.get_categories(budget_id)`: category/group parsing, `is_credit_card_payment=True` set for all categories in a group where `name.lower() == "credit card payments"`, deleted groups and deleted categories excluded in `tests/test_ynab_client.py`
- [X] T023 [US2] Write unit tests for `YNABClient.get_month_balances(budget_id, month)`: returns `CategoryMonthBalance` list with correct `available` (mapped from API `balance` field) and `is_credit_card_payment` flag, deleted categories excluded, month path param formatted as `YYYY-MM-01` in `tests/test_ynab_client.py`
- [X] T024 [US2] Write unit tests for `YNABClient.get_transactions(budget_id, since_date)`: since_date sent as query param, returns list with `cleared`, `account_id`, `account_name` fields, network error handling in `tests/test_ynab_client.py`
- [X] T025 [P] [US2] Write unit tests for `check_clearance(transactions, loan_account_id, account_name_map) -> ClearanceCheckResult`: passes when all non-loan transactions have `cleared == "reconciled"`; blocks when any "cleared" (C) or "uncleared" (U) found; loan_account_id transactions excluded entirely; per-account grouping with correct unreconciled count in `tests/test_cascade_logic.py`
- [X] T026 [US2] Write unit tests for `build_scan_overview(month_balances) -> dict[date, list[CategoryMonthBalance]]`: CC categories (is_credit_card_payment=True) excluded; categories with available>=0 excluded; months with no qualifying negatives omitted; result ordered oldest-first in `tests/test_cascade_logic.py`
- [X] T027 [P] [US2] Write Textual screen tests for `CascadeScanScreen`: loading spinner on mount, blocked-state shows per-account table + Retry button, clean-state shows no-issues message, negatives-found state shows month table + "Start Cascade" button, network error shows retry (no stale data) in `tests/test_cascade_screens.py`

### Implementation for User Story 2

- [X] T028 [US2] Add `get_categories(budget_id: str) -> list[Category]` to `YNABClient` calling `GET /v1/budgets/{budget_id}/categories`; sets `is_credit_card_payment=True` for all categories in groups where `name.lower() == "credit card payments"` per contracts/ynab-api.md §GET /categories and research.md §1 in `tui/ynab/client.py`
- [X] T029 [US2] Add `get_month_balances(budget_id: str, month: date) -> list[CategoryMonthBalance]` to `YNABClient` calling `GET /v1/budgets/{budget_id}/months/{YYYY-MM-01}`; maps API `balance` field to `CategoryMonthBalance.available`; excludes deleted categories per contracts/ynab-api.md §GET /months in `tui/ynab/client.py`
- [X] T030 [US2] Add `get_transactions(budget_id: str, since_date: date) -> list[dict]` to `YNABClient` calling `GET /v1/budgets/{budget_id}/transactions?since_date=YYYY-MM-DD` per contracts/ynab-api.md §GET /transactions in `tui/ynab/client.py`
- [X] T031 [US2] Implement `check_clearance(transactions: list[dict], loan_account_id: str, account_name_map: dict[str, str]) -> ClearanceCheckResult` in `tui/ynab/cascade.py`: exclude transactions where `account_id == loan_account_id`; block on `cleared != "reconciled"`; group blocking transactions by account_id; resolve account names; populate `AccountReconciliationIssue` list per research.md §9
- [X] T032 [US2] Implement `build_scan_overview(month_balances: dict[date, list[CategoryMonthBalance]]) -> dict[date, list[CategoryMonthBalance]]` in `tui/ynab/cascade.py`: filter out `is_credit_card_payment=True` and `available >= 0`; drop months with no qualifying entries; return sorted oldest-first
- [X] T033 [US2] Implement `CascadeScanScreen` in `tui/screens/cascade_scan.py` per screen-flows.md §CascadeScanScreen: async `on_mount` worker runs in sequence — (1) `get_accounts()` for name lookup map, (2) `get_categories()` for CC detection, (3) `get_transactions()` + `check_clearance()`, (4) if passes: `get_month_balances()` for 3 lookback months + `build_scan_overview()`; four rendered states: loading / blocked (per-account table + Retry) / clean (no-issues message + Back) / negatives-found (month table + "Start Cascade" → push `CascadeMonthScreen` with oldest MonthPlan)

**Checkpoint**: User Story 2 complete — clearance check, CC exclusion, and scan display all independently testable.

---

## Phase 5: User Story 3 — Process the Cascade One Month at a Time (Priority: P1)

**Goal**: Starting from the oldest affected month, user reviews a MonthPlan (negative categories + auto-assigned donors), confirms, and the app executes Transaction A and Transaction B as an atomic pair per month. On Tx B failure, Tx A is deleted (rollback). After each successful month the next month's plan is re-derived from live YNAB data with carry-forward labeling. A completion screen appears when all months are done.

**Independent Test**: Mock negatives in Feb and Apr. Verify: (a) wizard starts with Feb, shows categories and donors, no transactions created until Confirm pressed; (b) after Feb executes successfully, next plan is derived from re-fetched YNAB data, any carry-forward categories labeled "[carried from prior month]"; (c) cascade continues through Mar and Apr; (d) CompletionScreen appears with summary. Verify Tx B failure → Tx A deleted → RetryScreen shown.

### Tests for User Story 3

- [X] T034 [US3] Write unit tests for `select_donors(category_balances, total_deficit_milliunits) -> list[DonorAllocation]`: single donor covers full deficit (one allocation); multi-donor largest-first greedy split (multiple allocations, correct amounts); `sum(donor.amount_milliunits) == total_deficit_milliunits` invariant; raises `InsufficientFundsError` when combined balance < deficit in `tests/test_cascade_logic.py`
- [X] T035 [US3] Write unit tests for `build_month_plan(month, live_balances, initial_scan_balances) -> MonthPlan`: `is_carry_forward=True` for categories negative in live but not in initial scan; donor invariant `sum(donors) == sum(carryovers)`; `transaction_a_id=None, transaction_b_id=None` on creation; CC categories excluded in `tests/test_cascade_logic.py`
- [X] T036 [US3] Write unit tests for `build_split_subtransactions(carryovers, donors) -> tuple[list, list]`: Tx A donors are negative amounts, carryover categories are positive; Tx B is element-wise sign-inverse; `sum(tx_a amounts) == 0`, `sum(tx_b amounts) == 0` invariants in `tests/test_cascade_logic.py`
- [X] T037 [P] [US3] Write unit tests for `YNABClient.post_transaction(budget_id, payload) -> str`: 201 returns `data.transaction.id`; 400 shows error without retry; 429 triggers rate-limit pause-and-retry; 5xx shows retry option in `tests/test_ynab_client.py`
- [X] T038 [US3] Write unit tests for `YNABClient.delete_transaction(budget_id, transaction_id) -> None`: 200 success (no exception); DELETE failure surfaces orphaned transaction_id in error message so caller can warn user in `tests/test_ynab_client.py`
- [X] T039 [P] [US3] Write Textual screen tests for `CascadeMonthScreen`: carry-forward rows labeled "[carried from prior month]"; no YNAB calls made before Confirm; Confirm → pushes ExecutionProgressScreen; Exit → pops to WelcomeScreen in `tests/test_cascade_screens.py`
- [X] T040 [US3] Write Textual screen tests for `ExecutionProgressScreen`: Tx A created then Tx B created → row marked Done, advances to next month; Tx B fails → DELETE Tx A called → row marked Failed → pushes RetryScreen; all-success last month → pushes CompletionScreen in `tests/test_cascade_screens.py`

### Implementation for User Story 3

- [X] T041 [US3] Add `post_transaction(budget_id: str, payload: dict) -> str` to `YNABClient` calling `POST /v1/budgets/{budget_id}/transactions`; returns `data.transaction.id` from 201 response per contracts/ynab-api.md §POST /transactions in `tui/ynab/client.py`
- [X] T042 [US3] Add `delete_transaction(budget_id: str, transaction_id: str) -> None` to `YNABClient` calling `DELETE /v1/budgets/{budget_id}/transactions/{transaction_id}`; if DELETE itself fails, raises with the orphaned transaction_id in the message so caller can surface "delete manually in YNAB" warning per contracts/ynab-api.md §DELETE /transactions in `tui/ynab/client.py`
- [X] T043 [US3] Implement `select_donors(category_balances: list[CategoryMonthBalance], total_deficit_milliunits: int) -> list[DonorAllocation]` in `tui/ynab/cascade.py`: greedy largest-first from categories where `available > 0` and `is_credit_card_payment == False`; raises `InsufficientFundsError` if combined balance < total deficit per FR-015, FR-016, spec edge cases
- [X] T044 [US3] Implement `build_split_subtransactions(carryovers: list[CarryoverTuplet], donors: list[DonorAllocation]) -> tuple[list[SplitSubtransaction], list[SplitSubtransaction]]` in `tui/ynab/cascade.py`: Tx A donors get negative amounts, carryover categories get positive amounts; Tx B is element-wise sign-inverse; assert `sum == 0` for both per FR-019, FR-020 and research.md §3
- [X] T045 [US3] Implement `build_month_plan(month: date, live_balances: list[CategoryMonthBalance], initial_scan_balances: list[CategoryMonthBalance]) -> MonthPlan` in `tui/ynab/cascade.py`: filter live_balances to negative non-CC categories; compare against initial_scan_balances to set `is_carry_forward`; call `select_donors()` with total deficit; populate `MonthPlan` with `transaction_a_id=None, transaction_b_id=None` per FR-011, FR-014 and research.md §7
- [X] T046 [US3] Implement `CascadeMonthScreen` in `tui/screens/cascade_month.py` per screen-flows.md §CascadeMonthScreen: receives `MonthPlan`; displays table (Category group/name | Deficit | Donor(s) | Amount(s)) with "[carried from prior month]" annotation on `is_carry_forward=True` rows; "Confirm & Execute" → push `ExecutionProgressScreen`; "Exit (keep completed months)" → pop to WelcomeScreen
- [X] T047 [US3] Implement `ExecutionProgressScreen` in `tui/screens/cascade_month.py` per screen-flows.md §ExecutionProgressScreen: async worker — POST Tx A (store `transaction_a_id`), POST Tx B (store `transaction_b_id`); on Tx B failure: DELETE Tx A, mark failed; progress list with Pending/In Progress/Done/Failed per row; all success + more months → re-fetch YNAB for all remaining months, derive next `MonthPlan`, replace with next `CascadeMonthScreen`; all success + last month → replace with `CompletionScreen`; any failure → replace with `RetryScreen` per FR-021, FR-022, FR-013
- [X] T048 [US3] Implement `RetryScreen` in `tui/screens/cascade_month.py` per screen-flows.md §RetryScreen: lists failed allocations; "Retry Failed" → DELETE any orphaned Tx A first, re-run only failed allocations, return to execution result handling; "Skip & Continue" → advance to next month or CompletionScreen per FR-023
- [X] T049 [US3] Implement `CompletionScreen` in `tui/screens/cascade_month.py` per screen-flows.md §CompletionScreen: summary table (Month | Categories fixed | Donor allocations created); re-runs scan to confirm no qualifying negative categories remain in lookback window; "Back to Main Menu" → pop to WelcomeScreen

**Checkpoint**: User Story 3 complete — full cascade wizard, atomic execution, retry, and completion screen all independently testable.

---

## Phase 6: User Story 4 — Settings Management (Priority: P3)

**Goal**: A user who needs to update their YNAB API key or switch loan accounts for a configured budget can open Settings from the welcome screen at any time without disrupting any session.

**Independent Test**: Open Settings; change the internal loan account; save; navigate to cascade and verify the new account ID appears in the POST transaction payload (via mocked YNAB calls).

### Tests for User Story 4

- [X] T050 [P] [US4] Write Textual screen tests for `SettingsScreen`: API key shown masked (last 4 chars); "Update Key" validates live before saving, shows error on invalid; "Change Account" fetches account list and updates `loan_account_id` in config; "Remove Budget" deletes budget entry preserving others; all writes are atomic per screen-flows.md §SettingsScreen in `tests/test_cascade_screens.py`

### Implementation for User Story 4

- [X] T051 [US4] Implement `SettingsScreen` in `tui/screens/cascade_setup.py` per screen-flows.md §SettingsScreen: masked API key field showing last 4 chars + "Update Key" button (validates via `get_budgets()` before `save_config()`); per-budget table (Budget Name | Loan Account Name | "Change Account" | "Remove Budget"); "Change Account" → `get_accounts()` → inline `ListView` → select → `save_config()`; "Remove Budget" → delete budget entry from config via `save_config()`; "Add Budget" → push `BudgetSelectScreen`; every save is atomic
- [X] T052 [US4] Add `s` key binding on `WelcomeScreen` that pushes `SettingsScreen` in `tui/screens/welcome.py` (alongside the T020 cascade button addition)

**Checkpoint**: All four user stories complete and independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T053 [P] Audit all `YNABClient` error paths: confirm 400, 401, 404 (loan account not found → "offer to reconfigure" message), 429 (pause + retry), 5xx, and 15 s network timeout each produce a descriptive user-facing message per contracts/ynab-api.md §Error Handling table in `tui/ynab/client.py`
- [X] T054 [P] Verify `tui/app.py` cascade entry route wired correctly so key `3` on `WelcomeScreen` reaches `CascadeEntryScreen` (no-op if T021 already did this; verify no import errors)
- [X] T055 [P] Run `pytest tests/test_ynab_client.py tests/test_cascade_logic.py tests/test_cascade_screens.py -v` and confirm all tests pass with zero real network calls
- [X] T056 Validate quickstart.md flow end-to-end using mocked YNAB responses: install deps from updated `requirements.txt`, launch TUI with `python -m tui`, navigate to cascade feature, complete setup wizard, reach CascadeScanScreen, start month wizard

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Stories (Phases 3–6)**: All depend on Phase 2 completion
  - US1 → US2 → US3 are ordered: each story's screens depend on prior story's infrastructure
  - US4 depends only on US1 config infrastructure; can begin after US1 completes
- **Polish (Phase 7)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2/US3/US4
- **US2 (P1)**: Depends on US1 (`YNABClient` and config read complete); adds new client methods and new screen
- **US3 (P1)**: Depends on US1 + US2 (`CascadeScanScreen` triggers the cascade month wizard)
- **US4 (P3)**: Depends on US1 config infrastructure; can be developed after US1, parallel to US2/US3

### Within Each User Story

- Tests are written first and verified to FAIL before implementation begins
- Client endpoint methods added to `tui/ynab/client.py` before business logic that calls them
- Business logic in `tui/ynab/cascade.py` before TUI screens that use it
- Screens in `tui/screens/cascade_setup.py` before routing wired in `tui/app.py`

### Parallel Opportunities

- **Phase 1**: T002, T003 parallel with T001 (different files)
- **Phase 2**: T004, T005, T006 all parallel (different files); T007 sequential after T005 (same file); T008 parallel with T007 (different file, no dep)
- **Phase 3 tests**: T011 parallel with T009/T010 (different file); T012 parallel with T009/T010/T011 (different file)
- **Phase 3 impl**: T014→T015 sequential (same file); T020 and T021 can be parallel with each other (different files) after T016 completes
- **Phase 4 tests**: T025 parallel with T022–T024 (different file); T027 parallel with T022–T026 (different file)
- **Phase 4 impl**: T028→T029→T030 sequential (same file); T031 and T032 can be parallel (different functions, same cascade.py file — sequential)
- **Phase 5 tests**: T037 parallel with T034–T036 (different file); T039 parallel with T034–T038 (different file)
- **Phase 5 impl**: T041→T042 sequential (same file); T043→T044→T045 sequential (same cascade.py, chain of dependencies); T046→T047→T048→T049 sequential (same cascade_month.py)
- **Phase 7**: T053, T054, T055 parallel (different concerns)

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests concurrently (each in a different file or independent block):
Task T009: "Write get_budgets() tests in tests/test_ynab_client.py"
Task T011: "Write load_config/save_config tests in tests/test_cascade_logic.py"  # parallel with T009
Task T012: "Write SetupWizardScreen tests in tests/test_cascade_screens.py"       # parallel with T009/T011
```

---

## Implementation Strategy

### MVP First (User Stories 1–3 Only)

1. Complete Phase 1: Setup (≈ 30 min)
2. Complete Phase 2: Foundational — CRITICAL, blocks everything
3. Write US1 tests → verify failing → implement US1
4. **STOP and VALIDATE**: Setup wizard + config persistence work
5. Write US2 tests → verify failing → implement US2
6. **STOP and VALIDATE**: Clearance check + scan display work
7. Write US3 tests → verify failing → implement US3
8. **STOP and VALIDATE**: Full cascade wizard end-to-end (MVP complete)

### Incremental Delivery

1. Setup + Foundational → data model and HTTP client ready
2. User Story 1 → YNAB credentials flow, CSV still works (FR-001 verified)
3. User Story 2 → scan overview, clearance gate working
4. User Story 3 → month-by-month wizard functional (shippable MVP)
5. User Story 4 → settings management (non-critical path)
6. Phase 7 → test confirmation and error hardening

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks within the same phase
- [US1]/[US2]/[US3]/[US4] label maps task to spec.md user story for traceability
- Config file: `~/.config/credit-card-ynab-importer/config.json` — never committed to git
- All currency stored as milliunits (int); displayed via `format_milliunits()` helper from T008
- Loan account excluded from clearance check — cascade creates cleared transactions there during execution
- Tx A + Tx B are an atomic pair: Tx B failure must trigger DELETE Tx A before reporting failure
- Credit card payment categories identified by group name `"Credit Card Payments"` (case-insensitive, unconditional per research.md §1)
- YNAB is source of truth at every step: re-fetch all remaining months after each month's execution (research.md §7)
