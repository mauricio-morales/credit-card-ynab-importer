# Feature Specification: Monthly Overspend Cascade

**Feature Branch**: `002-ynab-negative-carryover`
**Created**: 2026-05-10
**Status**: Draft

## Overview

Each month, some budget categories in YNAB may end with a negative balance — the user spent more than was allocated, typically on a credit card. By default, YNAB zero-resets these categories at the start of the next month and surfaces the deficit as a global reduction of "Ready to Assign" income. This is not the user's desired behavior: they want the negative balance to persist into the next month so that the overspend is visible and accounted for within the affected category itself, not absorbed silently into overall income.

The user has discovered a manual technique that achieves this: a "carryover tuplet" — two transactions in a dedicated internal loan account that together zero out a negative category at the end of the prior month and re-apply the same deficit at the start of the current month. When multiple past months have negative categories (for example, February, March, and April all have overspent categories), the fix must cascade forward one month at a time: fixing February may create new negatives in March; those March negatives are then fixed, potentially creating new ones in April, and so on up to the current month.

This feature automates that cascading correction workflow. It also introduces the configuration infrastructure (YNAB API credentials and internal loan account selection) required to interact with YNAB — but only prompts for that configuration the first time the user attempts to use this feature. Existing functionality (CSV file conversion) continues to work without any YNAB credentials.

Two hard constraints govern when and what the cascade operates on. First, the cascade must never touch credit card payment categories. These special YNAB categories may show a negative balance as a downstream reflection of overspending in regular categories; once the real categories are corrected, the credit card balance corrects itself automatically. Attempting to apply a carryover tuplet to a credit card payment category would break that self-correction. Second, the cascade must only run when all transactions in the lookback window are fully cleared or reconciled. Uncleared transactions represent spending whose final categorization is not yet known; running the cascade over them risks producing carryover tuplets for negative balances that would vanish once those transactions clear — especially on credit card accounts where pending transactions frequently cause temporary apparent deficits.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Connect to YNAB (First Use of This Feature) (Priority: P1)

A user navigates to the "Monthly Overspend Cascade" feature for the first time. Because no YNAB credentials are configured yet, the app presents a focused setup wizard to collect the API key and select the internal loan account. This wizard is only shown once, when YNAB credentials are first needed; it does not appear on regular app launch for users who only use CSV conversion.

**Why this priority**: Every other story in this feature depends on valid credentials and a known internal loan account. The wizard must be complete before any carryover work can begin.

**Independent Test**: Launch the app with no YNAB credentials configured. Navigate to the cascade feature. Verify the wizard appears, accepts a valid API key, fetches the account list, allows selection, and writes a config file with the account ID (not name). Verify the wizard does not appear when launching the app and only using CSV conversion.

**Acceptance Scenarios**:

1. **Given** the user opens the app with no YNAB credentials configured, **When** they use only the CSV conversion feature, **Then** no YNAB wizard or prompt is shown at any point.
2. **Given** the user navigates to the cascade feature with no YNAB credentials configured, **When** the feature screen opens, **Then** the YNAB setup wizard is shown before any carryover data is loaded.
3. **Given** the wizard is displayed, **When** the user enters a valid YNAB API key and submits, **Then** the app fetches the user's YNAB accounts and presents them by name for selection.
4. **Given** the account list is displayed, **When** the user selects the internal loan account, **Then** the account's unique ID (not its display name) is saved to the local configuration file.
5. **Given** the wizard is completed, **When** the user is returned to the cascade feature screen, **Then** a configuration file exists containing the API key, budget ID, and internal loan account ID; the wizard does not appear again.
6. **Given** the user enters an invalid or expired API key, **When** attempting to fetch accounts, **Then** a descriptive error is shown and the user can correct the key without restarting.
7. **Given** the YNAB service is unreachable during setup, **When** the user submits the API key, **Then** an error is shown with a retry option; no partial configuration is saved.

---

### User Story 2 — Scan Past Months for Negative Categories (Priority: P1)

With YNAB credentials configured, the user opens the cascade feature. Before displaying any category data, the app checks that all transactions in the lookback window are in a cleared or reconciled state. If any uncleared transactions are found, the cascade is blocked and the user is shown which accounts have pending transactions so they can reconcile in YNAB before retrying. Only once the clearance check passes does the app scan the lookback window for negative categories, automatically excluding credit card payment categories from results entirely.

**Why this priority**: Both the clearance check and the credit card exclusion are mandatory gates. A scan that runs over uncleared data will produce false negative balances (especially on credit cards), and including credit card payment categories in the cascade would break their automatic self-correction.

**Independent Test**: (a) With an uncleared transaction in any account within the lookback window, verify the cascade is blocked and the affected account is named. (b) With all transactions cleared, verify the scan results include no credit card payment categories even if they have negative balances. (c) With known negative regular categories in February and April, verify those appear correctly.

**Acceptance Scenarios**:

1. **Given** YNAB credentials are configured, **When** the cascade feature screen loads, **Then** the app checks all accounts in the lookback window for uncleared transactions before showing any scan results.
2. **Given** one or more accounts have uncleared transactions in the lookback window, **When** the check runs, **Then** the cascade is blocked, the screen shows which accounts have uncleared transactions, and the user is prompted to reconcile those accounts in YNAB before proceeding.
3. **Given** the user has reconciled their accounts and retries, **When** all transactions are cleared or reconciled, **Then** the clearance check passes and the scan proceeds.
4. **Given** all transactions are cleared and the scan runs, **When** results are displayed, **Then** credit card payment categories are never shown, even if they have a negative balance.
5. **Given** all transactions are cleared and the scan runs, **When** results are displayed, **Then** all non-credit-card categories with a negative balance in the lookback window are listed, grouped by month, ordered oldest-to-most-recent, each showing category name, group name, and carryover amount as a positive value.
6. **Given** a month in the lookback window has no negative non-credit-card categories, **When** displayed, **Then** that month is omitted or marked as "no issues found."
7. **Given** no months in the lookback window have any qualifying negative categories, **When** the screen loads, **Then** a message confirms the budget history is clean and no action is needed.
8. **Given** the YNAB service is unreachable, **When** the scan is attempted, **Then** an error message is shown with a retry option; no stale data is shown silently.

---

### User Story 3 — Plan the Cascade (Preview Before Acting) (Priority: P1)

Before creating any transactions, the user reviews a complete cascade plan. Because fixing February's negatives will cause new negatives to appear in March (which must then be fixed to push them into April, and so on), the app computes the full chain of tuplets needed to cascade all deficits forward to the current month. The app also automatically assigns donor categories to cover each deficit — choosing whichever categories have sufficient available balance. The user sees the full plan for review and confirmation; no manual donor selection is required.

When no single category has enough balance to cover a deficit, the app splits coverage across multiple donors, drawing from each in turn until the full amount is covered. This applies even if a single negative category's deficit is larger than any individual donor's balance — it will be covered by as many donors as needed.

**Why this priority**: The cascade must be computed before execution because each month's fix affects the next. Presenting the plan first prevents surprises, and auto-assigning donors removes the main friction point from the workflow.

**Independent Test**: Given known negatives in February and April, with no single donor covering all amounts, verify the plan shows: February tuplets with auto-assigned donors (possibly split across multiple), projected March negatives from the February carry-forward, March tuplets, and April tuplets — all with correct amounts, dates, and donor assignments. Verify that a deficit larger than any single donor's balance is correctly split.

**Acceptance Scenarios**:

1. **Given** the scan shows negative categories in one or more past months, **When** the user initiates the cascade plan, **Then** the app computes and displays the full chain of carryover tuplets needed, one step per month, from oldest to most recent.
2. **Given** fixing month M creates new negatives in month M+1 (because Transaction B is dated the first day of M+1), **When** the plan is displayed, **Then** those projected M+1 negatives are included in the plan automatically as the next step in the chain.
3. **Given** the plan is displayed, **When** the user reviews a step, **Then** each step shows: the source month being fixed, the target month receiving the carry-forward, the category name, the carryover amount, and the auto-assigned donor(s) with the amount each donor contributes.
4. **Given** one donor category has a balance ≥ the full carryover amount for a step, **When** the plan is computed, **Then** that single donor is assigned to cover the step entirely.
5. **Given** no single donor has a balance ≥ the full carryover amount for a step, **When** the plan is computed, **Then** the app assigns multiple donors, drawing from each in turn (largest available balance first) until the full deficit is covered.
6. **Given** even the combined balance of all available donor categories is less than the carryover amount, **When** the plan is displayed, **Then** that step is flagged with a warning showing how much can be covered and how much remains uncovered; the user can proceed or skip that step.
7. **Given** the full plan is reviewed, **When** the user confirms, **Then** the app proceeds to execute all steps in the plan in chronological order (oldest month first).

---

### User Story 4 — Execute the Cascade (Priority: P2)

After confirming the plan, the app executes all carryover tuplets in order, processing one month at a time from oldest to most recent. For each step it creates Transaction A (last day of the source month) and Transaction B (first day of the next month) in the internal loan account. Progress is shown as each step completes. If any step fails, the user is informed with the option to retry that step without re-doing steps already completed.

**Why this priority**: Execution is the core automation payoff, but it cannot run without the plan step first.

**Independent Test**: Execute a two-month cascade plan (February → March → April) and verify: six transactions appear in YNAB (two per month), correctly dated and categorized; February ends at $0 for affected categories; March ends at $0 for its affected categories (including February carry-forwards); April shows the final carried-forward deficit.

**Acceptance Scenarios**:

1. **Given** the user confirms the plan, **When** execution begins, **Then** the app processes each month in the plan in order from oldest to most recent, showing a progress indicator for each step.
2. **Given** a step is being executed, **When** transactions are created, **Then** Transaction A is dated the last day of the source month and Transaction B is dated the first day of the following month, both in the configured internal loan account.
3. **Given** Transactions A and B for a single category must be atomic, **When** Transaction A succeeds but Transaction B fails, **Then** Transaction A is reversed (or deleted) so that no partial tuplet remains in YNAB.
4. **Given** a step fails after retries, **When** the failure is reported, **Then** previously completed steps are not undone; the user is shown which steps succeeded and which failed, and can retry only the failed step.
5. **Given** all steps in the plan complete successfully, **When** execution finishes, **Then** a summary is shown listing every category and month processed, and the user is returned to the cascade feature screen where a new scan confirms no negative categories remain in the lookback window.

---

### User Story 5 — Settings Management (Priority: P3)

A user who needs to update their YNAB API key or switch to a different internal loan account can open the Settings screen from the main navigation at any time. The Settings screen is accessible without disrupting any in-progress cascade session.

**Why this priority**: Infrequent but necessary. Not on the critical path for daily use.

**Independent Test**: Open Settings, change the internal loan account, save, and verify the next cascade session targets the new account in YNAB.

**Acceptance Scenarios**:

1. **Given** YNAB credentials are configured, **When** the user opens Settings, **Then** the API key is shown masked and the current internal loan account name is shown.
2. **Given** the Settings screen is open, **When** the user initiates an account change, **Then** a fresh list of YNAB accounts is fetched using the current API key for selection.
3. **Given** the user updates the API key, **When** saving, **Then** the new key is validated with a live YNAB request before saving; an error is shown if invalid.
4. **Given** valid changes are saved, **When** the user returns to the cascade screen, **Then** all subsequent YNAB requests use the updated configuration.

---

### Edge Cases

- What if fixing February's negatives causes a March category to go negative — but March has already been partially fixed in a prior run?
- What if a transaction clears between the clearance check and the moment execution is triggered — should the check be re-run at execution time?
- What if a credit card payment category is negative for a reason unrelated to overspending (e.g., a manual adjustment) — should the exclusion rule still apply unconditionally?
- What happens when a negative category is deleted in YNAB between when the scan runs and when execution is triggered?
- What if two categories in the same month have the same name but belong to different groups?
- What if the internal loan account is deleted from YNAB after it was saved in the configuration?
- What if the lookback scan reveals negatives from more than six months ago — is there a hard limit on how far back to cascade?
- What if a carryover amount is extremely small (e.g., -$0.01) — should trivially small negatives be filtered out or shown?
- What happens when a donor category balance exactly equals the carryover amount (boundary condition — donor is fully drained)?
- What if a deficit is split across many donors and one of those donor transactions fails mid-execution — how are the partial donor allocations handled atomically?
- What if the combined balance of all available donors is still less than the deficit amount — can a partial carryover be created, or must the entire category be skipped?
- What if the YNAB API rate limit (200 requests/hour) is reached during a large multi-month cascade with many donor-split transactions?
- What if the user runs the cascade mid-month — are source/target dates still calculated correctly from the previous calendar month boundary?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST NOT require YNAB credentials to launch or to use CSV file conversion functionality.
- **FR-002**: System MUST prompt for YNAB credentials only when the user first navigates to the cascade feature and no credentials are stored.
- **FR-003**: YNAB credentials wizard MUST validate the API key with a live YNAB request before accepting it.
- **FR-004**: YNAB credentials wizard MUST fetch the user's accounts from YNAB and allow selection by name, storing the account's ID (not name) in the local configuration file.
- **FR-005**: YNAB credentials wizard MUST store the budget ID along with the API key and account ID so all subsequent requests are scoped to the correct budget.
- **FR-006**: Configuration file MUST be excluded from version control and MUST NOT be committed to the repository.
- **FR-007**: Before performing any scan, system MUST verify that all transactions in the lookback window are in a cleared or reconciled state; if any uncleared transactions exist, the cascade MUST be blocked and the screen MUST list the affected account names so the user knows what to reconcile.
- **FR-008**: System MUST exclude all credit card payment categories from scan results and cascade operations; these categories MUST never appear as carryover candidates regardless of their balance.
- **FR-009**: Cascade feature screen MUST scan the last three calendar months by default and display all qualifying months (months with at least one negative non-credit-card category), grouped by month, ordered oldest-first.
- **FR-010**: Each displayed negative category MUST show the category name, group name, and carryover amount as a positive value.
- **FR-011**: System MUST compute a full cascade plan before any transactions are created, simulating the carry-forward effect month by month so that all necessary tuplets (including those induced by earlier months' fixes) are identified up front.
- **FR-012**: Cascade plan MUST be presented to the user for review before any transactions are submitted to YNAB; the plan MUST show auto-assigned donors for every step.
- **FR-013**: System MUST automatically select donor categories without requiring user input; donor selection is part of plan computation, not a separate user action.
- **FR-014**: When selecting a donor for a deficit, system MUST first attempt to find a single category whose available balance covers the entire deficit amount.
- **FR-015**: When no single category can cover a deficit, system MUST split coverage across multiple donors, drawing from each in descending balance order until the full deficit is covered.
- **FR-016**: System MUST support donor-splitting at the sub-category level: a single negative category's deficit may be partially funded by each of several donors, with each donor contributing a separate transaction pair.
- **FR-017**: System MUST execute the cascade plan in chronological order, oldest month first.
- **FR-018**: For each donor allocation in a step, system MUST create Transaction A in the internal loan account dated the last day of the source month, assigned to that donor category, for the donor's contribution amount.
- **FR-019**: For each donor allocation in a step, system MUST create the corresponding Transaction B in the internal loan account dated the first day of the following month, assigned to the negative (carryover) category, for the same contribution amount.
- **FR-020**: All Transaction A and Transaction B pairs for a single donor allocation MUST be atomic: if either fails, neither is left persisted in YNAB. For a multi-donor step, each donor allocation is atomic independently; a failed allocation does not roll back allocations already committed for the same category.
- **FR-021**: System MUST show execution progress step by step and report which donor allocations succeeded and which failed.
- **FR-022**: System MUST allow the user to retry a failed donor allocation without re-executing already-completed allocations.
- **FR-023**: System MUST warn before executing if it detects existing transactions suggesting a carryover for the same category and month was already performed.
- **FR-024**: A Settings screen MUST be accessible from the main navigation and MUST allow updating the YNAB API key and internal loan account.
- **FR-025**: System MUST display clear, actionable error messages for all YNAB connectivity failures, with a retry option.

### Key Entities

- **Budget**: The user's top-level YNAB financial plan. Has a unique ID and display name. All categories and accounts belong to a budget.
- **Category**: A budget allocation line item with a name, a parent group name, and a monthly available balance. Balance may be negative when more was spent than allocated.
- **Category Group**: A named collection of related categories (e.g., "Transportation" containing "Gas", "Parking").
- **Credit Card Payment Category**: A special system-managed category automatically created by YNAB for each credit card account. Its balance reflects what is owed to the card and adjusts automatically when other categories are corrected. These categories are always excluded from cascade operations.
- **Transaction Clearance State**: Whether a transaction is uncleared (pending, final category not confirmed), cleared (confirmed by the user or imported), or reconciled (locked after account reconciliation). The cascade requires all transactions in the lookback window to be in the cleared or reconciled state before it may run.
- **Internal Loan Account**: A YNAB account not linked to any real bank account, used exclusively to record carryover transactions. Identified by its unique ID stored in local config.
- **Donor Allocation**: A single donor's contribution toward covering a negative category's deficit. Consists of Transaction A (draws from the donor on the last day of the source month) and Transaction B (restores the donor via the carryover category on the first day of the following month). A deficit may require one or more donor allocations to be fully covered.
- **Carryover Tuplet**: The complete set of donor allocations for a single negative category and month. If one donor covers the full deficit, the tuplet contains one allocation (two transactions). If multiple donors are needed, the tuplet contains one allocation per donor (two transactions each).
- **Cascade Plan**: The full ordered sequence of carryover tuplets computed before execution, auto-assigned with donor allocations. Accounts for carry-forward effects: a tuplet in month M induces new negatives in month M+1, which are included in the plan automatically.
- **Donor Category**: Any budget category with available balance that the system automatically selects to fund one or more carryover allocations. A donor does not need to cover any full deficit on its own; it may contribute a partial amount as part of a multi-donor split.
- **Configuration**: A local, non-committed file storing: YNAB API key, budget ID, and internal loan account ID.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has never configured YNAB credentials can complete the setup wizard and begin their first cascade scan in under 3 minutes.
- **SC-002**: The multi-month scan of the last three calendar months completes and displays results within 10 seconds of the cascade screen loading (on a stable internet connection).
- **SC-003**: The full cascade plan — including induced carry-forwards across all affected months — is computed and displayed within 5 seconds of the user initiating plan generation.
- **SC-004**: A user can review the plan, confirm, and execute a cascade covering three months with up to five negative categories per month in a single session without leaving the app.
- **SC-005**: All carryover transaction tuplets are visible and correctly reflected in YNAB within 20 seconds of the user confirming execution.
- **SC-006**: Zero duplicate tuplets are created when the same cascade is attempted more than once for the same categories and months.
- **SC-007**: The CSV conversion feature continues to work without any YNAB configuration present; no YNAB prompt or error appears during a CSV-only session.
- **SC-008**: 100% of created tuplets produce the correct budget impact: the source month's category balance is restored to $0 and the following month's category balance is reduced by the carryover amount.

---

## Assumptions

- The user operates a single active YNAB budget; multi-budget selection is out of scope for this feature.
- The internal loan account already exists in YNAB before setup is run; account creation within the app is out of scope.
- Authentication uses a YNAB Personal Access Token; OAuth2 application flow is out of scope.
- The local configuration file is stored in the user's home config directory (platform-standard) or the app's working directory; the exact path is an implementation decision.
- The lookback window defaults to the last three complete calendar months; extending this beyond three months is a configuration option, not a primary workflow.
- "Last day of the source month" and "first day of the following month" are computed from the calendar boundaries of the month being corrected, not from the system clock's current date.
- Donor categories are selected automatically by the system; no user interaction is required to choose them. The system uses whatever categories have available balance, prioritizing those with the largest balance first.
- The cascade plan is computed offline (without additional YNAB requests) by simulating the carry-forward effects on the data already loaded during the scan.
- This feature extends the existing terminal UI (Textual TUI); no web, mobile, or separate desktop GUI is in scope.
- YNAB API currency values are in milliunits (1,000 milliunits = $1.00); the UI displays human-readable currency values throughout.
- The user is solely responsible for ensuring that the donor category used does not disrupt their own budget intent; the app only warns when balance is insufficient, it does not enforce budget rules.
- Credit card payment categories are identified by a YNAB-specific designation (category group type or flag); the exact mechanism is an implementation detail, but the exclusion is unconditional — no credit card payment category is ever a carryover candidate.
- "Uncleared" means a transaction with YNAB status U (uncleared/pending); cleared (C) and reconciled (R) statuses are both acceptable for the cascade to proceed. The clearance check covers all accounts in the lookback window, not only those with negative categories.
