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

### User Story 3 — Process the Cascade One Month at a Time (Priority: P1)

Once the scan overview confirms there are months to fix, the user enters a month-by-month wizard. The app starts with the oldest affected month, shows that month's negative categories with their auto-assigned donors, and waits for the user to confirm before creating any transactions. After a successful confirmation and execution, the app advances to the next month — which may now include new negatives induced by the previous month's carry-forwards. This repeats until all months are resolved. The user always sees exactly one month's worth of work before committing to it.

**Why this priority**: Processing one month at a time is essential for the user to understand and trust what the app is doing. A single large batch is opaque; the month-by-month wizard makes the cascade legible.

**Independent Test**: With negatives in February and April, verify: (a) the wizard starts with February, shows its categories and donors, does nothing until confirmed; (b) after February's confirmation and execution, the wizard advances to March, now showing the carry-forwards from February alongside any original March negatives; (c) after March is confirmed and executed, April is shown; (d) after April, a completion summary is shown. Verify a deficit split across multiple donors is correctly displayed and executed per month.

**Acceptance Scenarios**:

1. **Given** the scan overview shows one or more affected months, **When** the user starts the cascade, **Then** the app presents the oldest affected month's summary screen: each negative category, its carryover amount, and the auto-assigned donor(s) with the amount each contributes.
2. **Given** a month's summary is displayed, **When** reviewing the donor assignments, **Then** the donor auto-assignment rules apply: one donor if sufficient, multiple donors drawn largest-first if not, with a warning if the combined balance still falls short.
3. **Given** a month's summary is displayed and the user has reviewed it, **When** the user confirms, **Then** the app executes all transaction tuplets for that month only — no transactions for any other month are created at this step.
4. **Given** a month's transactions are created, **When** execution completes successfully, **Then** the app computes the next month's summary, incorporating any carry-forward amounts from the month just executed, and presents it for review.
5. **Given** the next month's summary is presented, **When** the user reviews it, **Then** any categories that appear due to carry-forwards from the previous month are visually distinguished from categories that were already negative in that month.
6. **Given** a month's execution fails for one or more categories, **When** the failure is reported, **Then** the user is shown which categories succeeded and which failed, with a retry option for the failed ones; categories already committed are not re-executed on retry.
7. **Given** the final month in the cascade is confirmed and executed successfully, **When** complete, **Then** a summary screen is shown listing every month and category processed, and a final scan confirms no qualifying negative categories remain in the lookback window.
8. **Given** the user wants to stop mid-cascade after completing some months, **When** they exit, **Then** the months already executed remain in YNAB; the user can re-enter the feature later and the remaining months will still be shown.

---

### User Story 4 — Settings Management (Priority: P3)

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

- What if fixing February's negatives causes a March category to go negative — but March has already been partially fixed in a prior run? This is why we run from the back... if March needs fixing, we fix it. It's ok to create a new tuple to do the fix.
- What if a transaction clears between the clearance check and the moment execution is triggered — should the check be re-run at execution time? won't happen, at least for me there are no race conditions cause transaction clearance is manual (my accounts are not linked), so I clear them all once a month once the month ended. Still, it's irrelevant, cause if any transaction is uncleared and the account is not reconciled by the time we run this, we can't run this process... it's not just about cleared transactions, it's about all accounts being reconciled AFTER the month-to-fix ended. 
- What if a credit card payment category is negative for a reason unrelated to overspending (e.g., a manual adjustment) — should the exclusion rule still apply unconditionally? unconditionally... it's not our job to fix all problems! just to carry over negative balances from month to month. 
- What happens when a negative category is deleted in YNAB between when the scan runs and when execution is triggered? No changes will happen while our process is running... this isn't a long running process, the user will manually trigger it and no other changes will happen until it's done. 
- What if two categories in the same month have the same name but belong to different groups? R/ what about it? you shouldn't be confused, cause all categories are uniquely named with group+name.
- What if the internal loan account is deleted from YNAB after it was saved in the configuration? a failure to find that loan account should error out, and offer the user to exit or clear the config and reconfigure the loan account. BUT the error handling should be specific about the loan account not existing. 
- What if the lookback scan reveals negatives from more than six months ago — is there a hard limit on how far back to cascade? R/ a responsible user won't need to go that far back, this should be a monthly practice. Don't worry about this. 
- What if a carryover amount is extremely small (e.g., -$0.01) — should trivially small negatives be filtered out or shown? Yes, we need all green balances. 
- What happens when a donor category balance exactly equals the carryover amount (boundary condition — donor is fully drained)? use it. The donor is a temporary donor. i doesn't matter which account is the donnor, cause it'll get the money back on the 2nd transaction of the tuple.
- What if a deficit is split across many donors and one of those donor transactions fails mid-execution — how are the partial donor allocations handled atomically?There's no partial allocation. The transactions are 2 only. That's it. All categories are added to a single 0 balanced transaction. The only partial would be that transaction 1 is created but 2 fails... we can fall back to deleting (roll back'ish) the 1st transaction if the 2nd can't be created. 
- What if the combined balance of all available donors is still less than the deficit amount — can a partial carryover be created, or must the entire category be skipped? this should never happen. If it does, then cancel the entire thing... this means the user genuinely spent more than they had, and the error should remain evident to them. 
- What if the YNAB API rate limit (200 requests/hour) is reached during a large multi-month cascade with many donor-split transactions? shouldn't happen, but recognize the rate limit error and pause for whatever time is left of the hour before continuing. 
- What if the user runs the cascade mid-month — are source/target dates still calculated correctly from the previous calendar month boundary? This will almost certainly run mid-month, but for the previous month. So we are mid May now, I'd run it now to bring the April negative balances into May. And yes, the transactions should still be Apr/30 and May/1. 

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
- **FR-011**: System MUST compute each month's plan (negative categories + auto-assigned donors) immediately before presenting that month's summary screen; upfront planning of all months at once is not required.
- **FR-012**: Each month's summary MUST be presented to the user for review and explicit confirmation before any transactions for that month are submitted; no transactions for future months are created until those months are individually confirmed.
- **FR-013**: After successfully executing month M's transactions, system MUST derive month M+1's plan by incorporating the carry-forward amounts from M's execution and present that plan as the next month's summary screen before any action is taken.
- **FR-014**: System MUST automatically select donor categories without requiring user input; donor selection is part of plan computation, not a separate user action.
- **FR-015**: When selecting a donor for a deficit, system MUST first attempt to find a single category whose available balance covers the entire deficit amount.
- **FR-016**: When no single category can cover a deficit, system MUST split coverage across multiple donors, drawing from each in descending balance order until the full deficit is covered.
- **FR-017**: System MUST support donor-splitting at the sub-category level: a single negative category's deficit may be partially funded by each of several donors, with each donor contributing a separate transaction pair.
- **FR-018**: System MUST process months in chronological order, oldest first; the user cannot skip ahead to a later month without completing or explicitly skipping the current one.
- **FR-019**: For each donor allocation in a step, system MUST create Transaction A in the internal loan account dated the last day of the source month, assigned to that donor category, for the donor's contribution amount.
- **FR-020**: For each donor allocation in a step, system MUST create the corresponding Transaction B in the internal loan account dated the first day of the following month, assigned to the negative (carryover) category, for the same contribution amount.
- **FR-021**: All Transaction A and Transaction B pairs for a single donor allocation MUST be atomic: if either fails, neither is left persisted in YNAB. For a multi-donor step, each donor allocation is atomic independently; a failed allocation does not roll back allocations already committed for the same category.
- **FR-022**: System MUST show execution progress within each month's step and report which donor allocations succeeded and which failed before advancing to the next month.
- **FR-023**: System MUST allow the user to retry failed donor allocations within the current month without re-executing already-completed allocations for that month.
- **FR-024**: System MUST warn before executing a month if it detects existing transactions suggesting a carryover for the same category and month was already performed.
- **FR-025**: A Settings screen MUST be accessible from the main navigation and MUST allow updating the YNAB API key and internal loan account.
- **FR-026**: System MUST display clear, actionable error messages for all YNAB connectivity failures, with a retry option.

### Key Entities

- **Budget**: The user's top-level YNAB financial plan. Has a unique ID and display name. All categories and accounts belong to a budget.
- **Category**: A budget allocation line item with a name, a parent group name, and a monthly available balance. Balance may be negative when more was spent than allocated.
- **Category Group**: A named collection of related categories (e.g., "Transportation" containing "Gas", "Parking").
- **Credit Card Payment Category**: A special system-managed category automatically created by YNAB for each credit card account. Its balance reflects what is owed to the card and adjusts automatically when other categories are corrected. These categories are always excluded from cascade operations.
- **Transaction Clearance State**: Whether a transaction is uncleared (pending, final category not confirmed), cleared (confirmed by the user or imported), or reconciled (locked after account reconciliation). The cascade requires all transactions in the lookback window to be in the cleared or reconciled state before it may run.
- **Internal Loan Account**: A YNAB account not linked to any real bank account, used exclusively to record carryover transactions. Identified by its unique ID stored in local config.
- **Donor Allocation**: A single donor's contribution toward covering a negative category's deficit. Consists of Transaction A (draws from the donor on the last day of the source month) and Transaction B (restores the donor via the carryover category on the first day of the following month). A deficit may require one or more donor allocations to be fully covered.
- **Carryover Tuplet**: The complete set of donor allocations for a single negative category and month. If one donor covers the full deficit, the tuplet contains one allocation (two transactions). If multiple donors are needed, the tuplet contains one allocation per donor (two transactions each).
- **Cascade Plan**: The month-by-month sequence of carryover tuplets processed one month at a time. Each month's plan is computed immediately before that month's summary is shown; carry-forward amounts from month M are incorporated into month M+1's plan after M's execution completes.
- **Donor Category**: Any budget category with available balance that the system automatically selects to fund one or more carryover allocations. A donor does not need to cover any full deficit on its own; it may contribute a partial amount as part of a multi-donor split.
- **Configuration**: A local, non-committed file storing: YNAB API key, budget ID, and internal loan account ID.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has never configured YNAB credentials can complete the setup wizard and begin their first cascade scan in under 3 minutes.
- **SC-002**: The multi-month scan of the last three calendar months completes and displays results within 10 seconds of the cascade screen loading (on a stable internet connection).
- **SC-003**: Each individual month's summary — including carry-forward amounts from the previous month's execution — is computed and displayed within 5 seconds of advancing to that month.
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
