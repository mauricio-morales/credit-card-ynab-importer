# Research: Monthly Overspend Cascade

**Branch**: `002-ynab-negative-carryover` | **Date**: 2026-05-25

All NEEDS CLARIFICATION items from the Technical Context are resolved below.

---

## 1. YNAB API: Identifying Credit Card Payment Categories

**Decision**: Filter by category group name `"Credit Card Payments"` (case-insensitive exact match).

`GET /v1/budgets/{budget_id}/categories` returns `CategoryGroupWithCategories[]`. YNAB automatically creates one group named "Credit Card Payments" per budget, containing one category per linked credit card account. The YNAB public API v1 does not expose a `type` field on category groups; group name is the only stable identifier. All categories belonging to that group are excluded unconditionally from scan results and cascade operations (per spec requirement: exclusion is unconditional).

**Alternatives considered**:
- Undocumented `type: "credit_cards"` field — not in public API schema; fragile.
- Category-level flag — no such flag exists in YNAB API v1.

---

## 2. YNAB API: Budget Selection and Per-Budget Configuration

**Decision**: `GET /v1/budgets` on API key validation to get the budget list; present all budgets by name; store configuration per-budget keyed by `budget_id`.

The user may have multiple YNAB budgets (e.g., a CRC budget and a USD budget). Each budget has its own internal loan account with a different ID and possibly a different name. The config file stores the API key once globally, and a `budgets` map keyed by budget ID where each entry holds `{name, loan_account_id}`.

Setup wizard flow:
1. User enters API key → `GET /v1/budgets` → validate key and populate budget list.
2. User selects a budget → `GET /v1/budgets/{budget_id}/accounts` → populate account list.
3. User selects loan account → write `budgets[budget_id] = {name, loan_account_id}` to config.

On subsequent visits (API key already stored):
- Show budget picker listing all YNAB budgets, marking which are already configured.
- If user picks an already-configured budget → go directly to scan.
- If user picks an unconfigured budget → run step 2–3 above (account selection only; no API key re-entry).
- If only one budget exists and it is already configured → skip the picker entirely, go directly to scan.

If `data.budgets` is empty: surface "No budgets found for this API key."

**Alternatives considered**:
- Take the first budget automatically — rejected because the user explicitly has multiple budgets and cannot choose which one they want to cascade.
- Hard-code a known budget ID — not viable for a general-purpose tool.
- Always show picker even for single-budget users — unnecessary friction; single configured budget auto-selects.

---

## 3. YNAB API: Transaction Format for Carryover Tuplets

**Decision**: Two sequential `POST /v1/budgets/{budget_id}/transactions` calls per **month** — each a single SPLIT transaction covering all donors and all carryover categories for that month.

**Transaction A** (last day of source month, amount = 0):
```json
{
  "transaction": {
    "account_id": "<loan_account_id>",
    "date": "YYYY-04-30",
    "amount": 0,
    "cleared": "cleared",
    "approved": true,
    "payee_name": "Cascade Carryover",
    "subtransactions": [
      { "amount": -200000, "category_id": "<donor_category_id>",       "memo": "donor" },
      { "amount":   50000, "category_id": "<car_category_id>",         "memo": "carryover" },
      { "amount":   80000, "category_id": "<food_category_id>",        "memo": "carryover" },
      { "amount":   40000, "category_id": "<restaurants_category_id>", "memo": "carryover" },
      { "amount":   30000, "category_id": "<supermarket_category_id>", "memo": "carryover" }
    ]
  }
}
```

Subtransaction rules for Transaction A:
- Each **donor** gets a **negative** sub-transaction (amount = -(that donor's total contribution across all categories it covers). The donor's available balance decreases in the source month — it "spends" into the loan account.
- Each **carryover category** gets a **positive** sub-transaction (amount = its deficit). The category receives an inflow that zeroes its negative balance in the source month.
- Multiple donors are supported: add one negative sub-transaction per donor.
- `sum(all subtransaction amounts) == 0` is required by YNAB.

**Transaction B** (first day of next month, exact sign-inverse of A):
```json
{
  "transaction": {
    "account_id": "<loan_account_id>",
    "date": "YYYY-05-01",
    "amount": 0,
    "cleared": "cleared",
    "approved": true,
    "payee_name": "Cascade Carryover",
    "subtransactions": [
      { "amount":  200000, "category_id": "<donor_category_id>",       "memo": "donor" },
      { "amount":  -50000, "category_id": "<car_category_id>",         "memo": "carryover" },
      { "amount":  -80000, "category_id": "<food_category_id>",        "memo": "carryover" },
      { "amount":  -40000, "category_id": "<restaurants_category_id>", "memo": "carryover" },
      { "amount":  -30000, "category_id": "<supermarket_category_id>", "memo": "carryover" }
    ]
  }
}
```

Every amount is negated, category assignments are identical. The donor gets its money back in the following month (positive inflow); each carryover category now has a deficit in the new month equal to what it overspent in the prior month — that is the carryover taking effect.

**Net effect per budget**: Each carryover category ends the source month at $0 (covered by the donor via Transaction A). In the following month each carryover category starts with a deficit equal to its original overspend (applied by Transaction B), and the donor's balance is restored.

**Atomicity**: If Transaction B's `POST` fails, issue `DELETE /v1/budgets/{budget_id}/transactions/{transaction_a_id}` to roll back Transaction A. There is exactly one A+B pair per month. Store `data.transaction.id` from each 201 response before proceeding.

**Alternatives considered**:
- One transaction pair per donor-category combination (original design) — rejected because YNAB's split transaction feature makes this unnecessary; the new design produces 2 API calls per month instead of 2 × N_donors × N_categories calls.
- Bulk `transactions[]` array — still creates individual (non-split) transactions; does not achieve the single-split model.

---

## 4. YNAB API: Rate Limit Handling

**Decision**: On 429 response, read `X-Rate-Limit` header (format: `"<used>/<limit>"`), compute wait time as `(60 - seconds_into_current_minute) * 60` or default to 60 seconds, surface a status message, and retry once after waiting.

YNAB allows 200 requests/hour per Personal Access Token. A full 3-month cascade (3 months × 5 categories × 1 donor each) produces ~36 API calls (3 month-fetches + 1 accounts fetch + 1 categories fetch + 30 transaction POSTs). Rate limit should never be hit in normal use. The handler exists as a safeguard for edge cases (many categories, multi-donor splits, retries).

**Alternatives considered**:
- Fail immediately on 429 and ask user to retry later — poor UX given the handler is trivial to implement.
- Parse `Retry-After` header — YNAB does not consistently include this; computing from the hour boundary is more reliable.

---

## 5. Config File Location

**Decision**: `~/.config/credit-card-ynab-importer/config.json`

Computed as `pathlib.Path.home() / ".config" / "credit-card-ynab-importer" / "config.json"`. No extra library needed. Directory is created on first write. File is outside the git repository, satisfying FR-006. As a belt-and-suspenders measure, `config.json` is added to `.gitignore` in case users run the tool from inside the repo directory.

Config JSON schema:
```json
{
  "api_key": "string",
  "budgets": {
    "<budget_uuid>": {
      "budget_name": "string",
      "loan_account_id": "string"
    }
  }
}
```

`api_key` is global (shared across all budgets). `budgets` is a dictionary keyed by YNAB budget UUID; each entry holds the budget's display name (stored for UI labels) and the loan account ID configured for that budget. A newly stored API key leaves `budgets` as an empty object `{}` until at least one budget is configured.

**Alternatives considered**:
- `platformdirs` library for OS-standard config path — adds a dependency; `~/.config` is sufficient for the single macOS target platform.
- Store in repo root — violates FR-006.
- `.env` file — no standard library parser; adds dependency or manual parsing.

---

## 6. HTTP Client: `requests` vs `urllib.request`

**Decision**: `requests ≥2.28` (add to `requirements.txt`).

The YNAB API client needs: Bearer auth header on every call, JSON response parsing, structured error inspection (status code + error body), session-level configuration (base URL, timeout). `requests.Session` provides all of this with ~10 lines of setup. The equivalent with `urllib.request` requires manual `Request` objects, `urllib.error.HTTPError` catching with body re-read, and custom header management — approximately 3× the code for the same behavior.

This is the first external network dependency in the project. The constitution requires an amendment to allow it (see plan.md Constitution Check).

**Alternatives considered**:
- `httpx` (async) — async HTTP is not needed; Textual workers run sync code in a thread pool. Adds complexity with no benefit.
- `urllib.request` — viable but produces fragile, verbose code for an API client.

---

## 7. Cascade Plan Computation (Live Re-fetch Per Month)

**Decision**: YNAB is the authoritative source of truth at every step. After executing a month's transactions, re-fetch all remaining months fresh from YNAB before computing the next plan. Each month's plan is derived from live YNAB data, not an in-memory simulation.

Algorithm:
1. **Initial scan** (for the overview screen): `GET /v1/budgets/{budget_id}/months/{YYYY-MM-01}` for each of the 3 lookback months → identify affected months → display overview. This data is retained only for carry-forward labeling (see below); it is not used for calculations.
2. **Before processing month M**: re-fetch `GET /v1/budgets/{budget_id}/months/{YYYY-MM-01}` fresh to get current category balances. Build `MonthPlan` from this live data.
3. **After executing month M**: re-fetch all remaining months (M+1 through the lookback end) fresh from YNAB. Recompute the affected-months list from this live data. Advance to the next affected month.
4. Repeat from step 2 for the next month.

**Carry-forward labeling**: To display which categories in month M+1 are "new" due to the month M fix (Story 3, scenario 5), compare the fresh re-fetch against the initial scan data for that month. A category that was not negative in the initial scan but is negative in the re-fetch is labeled as a carry-forward. The initial scan results serve no other purpose — all calculations use the re-fetched data.

**Why not offline simulation**: A bug in the carry-forward calculation could silently produce a wrong plan for month M+1. By the time the error surfaces in month M+2, the simulated state may have drifted further from reality with each month. Re-fetching from YNAB after each execution ensures that any error in month M's transactions is immediately visible in the real YNAB state that drives month M+1's plan — no compounding.

**API call budget per month** (in addition to the 2 POST calls for execution):
- 1 re-fetch per remaining month after execution (at most 2 extra calls for a 3-month window)
- Well within the 200 req/hr rate limit.

**SC-003 compliance**: Each re-fetch is 1–2 `GET /months` calls. At < 1 s per call on a stable connection, the 5 s budget for per-month plan derivation is met comfortably.

**Alternatives considered**:
- In-memory offline simulation — rejected because a calculation bug compounds silently across months; YNAB data is authoritative and cheap to re-fetch.
- Re-fetch only the immediately next month — rejected because fixing month M can affect multiple downstream months; fetching all remaining months ensures the affected-months list is always accurate.

---

## 8. Duplicate Detection — Not Implemented

**Decision**: No duplicate detection is performed. If a month shows a negative balance, a new carryover transaction is created regardless of whether a prior carryover was already done for that category and month.

**Rationale**: A negative balance in YNAB is the trigger for action. If a prior carryover was created and the category is still negative (because new spending arrived after the first carryover), the correct response is to create another carryover — not to warn or block. Checking for prior carryovers would require an extra API call per month, add UI friction, and produce false positives in exactly the cases where action is needed. The cascade simply operates on what YNAB reports now.

The `payee_name` field on created transactions is `"Cascade Carryover"` for all transactions. Sequential numbering is not implemented; YNAB timestamps provide a sufficient audit trail.

---

## 9. Clearance Check

**Decision**: `GET /v1/budgets/{budget_id}/transactions?since_date={lookback_start}` fetches all transactions since the start of the lookback window. Filter out transactions where `account_id == loan_account_id` (the loan account is excluded — the cascade itself creates cleared transactions there, and requiring those to be reconciled before the next month would make the tool self-blocking). For all remaining transactions: block if `cleared != "reconciled"` — both `"cleared"` (C) and `"uncleared"` (U) are blocking states. Group blocking transactions by `account_id`, resolve account names, and count per account.

YNAB `cleared` field values: `"uncleared"` (U), `"cleared"` (C), `"reconciled"` (R). Only R is acceptable. The cascade requires fully reconciled accounts because reconciliation is the signal that the month is closed and no further transactions will arrive — only then are negative balances final and safe to carry forward.

The UI shows each blocking account name and its unreconciled transaction count so the user knows exactly what to reconcile in YNAB before retrying.
