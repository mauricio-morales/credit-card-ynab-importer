# Contract: YNAB API

**Branch**: `002-ynab-negative-carryover` | **Date**: 2026-05-25

Base URL: `https://api.ynab.com/v1`  
Authentication: `Authorization: Bearer <api_key>` on every request  
All amounts in YNAB API are in milliunits (1,000 = $1.00)

---

## Endpoints Used

### GET /budgets

Used during setup wizard to validate the API key and obtain the budget ID.

**Request**: No body, no query params.

**Response 200**:
```json
{
  "data": {
    "budgets": [
      {
        "id": "uuid",
        "name": "My Budget",
        "last_modified_on": "2026-05-20T12:00:00+00:00",
        "first_month": "2020-01-01",
        "last_month": "2026-05-01",
        "date_format": { "format": "MM/DD/YYYY" },
        "currency_format": { ... }
      }
    ]
  }
}
```

**Consumed fields**: `budgets[0].id` (stored as `budget_id`).  
**Error cases**: 401 (invalid token), empty `budgets[]` array (no budgets for this key).

---

### GET /budgets/{budget_id}/accounts

Used during setup wizard (account selection) and in Settings (change loan account). Also used at cascade scan load for account name lookup.

**Response 200**:
```json
{
  "data": {
    "accounts": [
      {
        "id": "uuid",
        "name": "Internal Loan",
        "type": "otherAsset",
        "on_budget": true,
        "closed": false,
        "deleted": false,
        "balance": 0
      }
    ]
  }
}
```

**Consumed fields**: `id`, `name`, `on_budget`, `closed`, `deleted`.  
**Filtering**: Display only `on_budget == true` and `deleted == false` and `closed == false` in the account picker.

---

### GET /budgets/{budget_id}/categories

Used once at cascade scan load to build the category/group catalogue.

**Response 200**:
```json
{
  "data": {
    "category_groups": [
      {
        "id": "uuid",
        "name": "Credit Card Payments",
        "hidden": false,
        "deleted": false,
        "categories": [
          {
            "id": "uuid",
            "category_group_id": "uuid",
            "name": "Visa Card",
            "hidden": false,
            "deleted": false
          }
        ]
      }
    ]
  }
}
```

**Consumed fields**: `category_groups[].id`, `.name`, `.deleted`; `categories[].id`, `.name`, `.category_group_id`, `.deleted`.  
**Credit card detection**: Groups where `name.lower() == "credit card payments"` → all categories in these groups have `is_credit_card_payment = True`.

---

### GET /budgets/{budget_id}/months/{month}

Used to obtain per-category available balances for a specific month. Called once per month in the lookback window at scan load time.

**Path param**: `month` = `YYYY-MM-DD` (first day of the month, e.g., `2026-02-01`).

**Response 200**:
```json
{
  "data": {
    "month": {
      "month": "2026-02-01",
      "note": null,
      "income": 1200000,
      "budgeted": 1100000,
      "activity": -950000,
      "to_be_budgeted": 100000,
      "age_of_money": 30,
      "deleted": false,
      "categories": [
        {
          "id": "uuid",
          "category_group_id": "uuid",
          "name": "Dining Out",
          "hidden": false,
          "budgeted": 100000,
          "activity": -130000,
          "balance": -30000,
          "goal_type": null,
          "goal_percentage_complete": null,
          "deleted": false
        }
      ]
    }
  }
}
```

**Consumed fields**: `month.categories[].id`, `.balance` (used as `available` for this month — negative means over-spent), `.deleted`.

Note: The `balance` field in this endpoint represents the category's available balance for that month, which is what the cascade operates on.

---

### GET /budgets/{budget_id}/transactions

Used for clearance check. Fetches all transactions since the start of the lookback window.

**Query params**: `since_date=YYYY-MM-DD` (first day of oldest lookback month).

**Response 200**:
```json
{
  "data": {
    "transactions": [
      {
        "id": "uuid",
        "date": "2026-02-15",
        "amount": -45000,
        "cleared": "uncleared",
        "approved": true,
        "account_id": "uuid",
        "account_name": "Chase Visa",
        "category_id": "uuid",
        "category_name": "Groceries",
        "deleted": false
      }
    ]
  }
}
```

**Filtering**: Exclude transactions where `account_id == loan_account_id` before evaluating clearance.

**Consumed fields**: `cleared` (block if `!= "reconciled"` — both `"cleared"` and `"uncleared"` are blocking), `account_id`, `account_name`.

**Grouping**: Group blocking transactions by `account_id`; count per account → feeds `AccountReconciliationIssue` list in `ClearanceCheckResult`.

---

### POST /budgets/{budget_id}/transactions

Used twice per month: once to create Transaction A, once to create Transaction B. Each is a **split transaction** (top-level `amount = 0`, with a `subtransactions` array).

**Transaction A request** (last day of source month — example: one donor, four carryover categories):
```json
{
  "transaction": {
    "account_id": "<loan_account_id>",
    "date": "2026-04-30",
    "amount": 0,
    "cleared": "cleared",
    "approved": true,
    "payee_name": "Cascade Carryover",
    "subtransactions": [
      { "amount": -200000, "category_id": "<donor_id>",       "memo": "donor" },
      { "amount":   50000, "category_id": "<car_id>",         "memo": "carryover" },
      { "amount":   80000, "category_id": "<food_id>",        "memo": "carryover" },
      { "amount":   40000, "category_id": "<restaurants_id>", "memo": "carryover" },
      { "amount":   30000, "category_id": "<supermarket_id>", "memo": "carryover" }
    ]
  }
}
```

Sub-transaction sign rules for Transaction A:
- Each **donor**: negative amount (draws from donor category; reduces its available balance in the source month)
- Each **carryover category**: positive amount (restores the negative category to $0 in the source month)
- `sum(subtransactions[].amount) == 0` (required by YNAB)
- Multiple donors: one negative sub-transaction per donor

**Transaction B request** (first day of next month — exact sign-inverse of A):
```json
{
  "transaction": {
    "account_id": "<loan_account_id>",
    "date": "2026-05-01",
    "amount": 0,
    "cleared": "cleared",
    "approved": true,
    "payee_name": "Cascade Carryover",
    "subtransactions": [
      { "amount":  200000, "category_id": "<donor_id>",       "memo": "donor" },
      { "amount":  -50000, "category_id": "<car_id>",         "memo": "carryover" },
      { "amount":  -80000, "category_id": "<food_id>",        "memo": "carryover" },
      { "amount":  -40000, "category_id": "<restaurants_id>", "memo": "carryover" },
      { "amount":  -30000, "category_id": "<supermarket_id>", "memo": "carryover" }
    ]
  }
}
```

Every amount is the negation of its Transaction A counterpart. Category assignments are identical. The donor's available balance is restored in the next month; each carryover category carries the deficit forward.

**Response 201** (same shape for both A and B):
```json
{
  "data": {
    "transaction_ids": ["uuid"],
    "transaction": {
      "id": "uuid",
      "date": "2026-04-30",
      "amount": 0,
      "cleared": "cleared",
      "account_id": "uuid",
      "subtransactions": [...]
    },
    "duplicate_import_ids": []
  }
}
```

**Consumed fields**: `data.transaction.id` — stored in `MonthPlan.transaction_a_id` (after A) or `MonthPlan.transaction_b_id` (after B).

---

### DELETE /budgets/{budget_id}/transactions/{transaction_id}

Used for rollback when Transaction B fails after Transaction A was created.

**Response 200**:
```json
{
  "data": {
    "transaction": { "id": "uuid", "deleted": true }
  }
}
```

**Error handling**: If DELETE also fails (e.g., transaction already gone), log the orphaned transaction_id and surface a warning to the user: "Transaction A (id: X) could not be rolled back — please delete it manually in YNAB."

---

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 200 / 201 | Success | Parse response |
| 400 | Bad request | Show error message; do not retry |
| 401 | Unauthorized | Show "Invalid API key" message; prompt to update in Settings |
| 404 | Not found | Specific: loan account not found → offer to reconfigure |
| 429 | Rate limit | Parse `X-Rate-Limit` header; wait until limit resets; retry |
| 5xx | Server error | Show error with retry option |
| Network timeout | — | Show error with retry option; timeout = 15 s per request |

---

## Rate Limit Strategy

Header: `X-Rate-Limit: <used>/<limit>` (e.g., `"190/200"`)  
Limit: 200 requests/hour per token  
On 429: compute `seconds_to_wait = max(60, 3600 - (seconds_elapsed_since_hour_boundary))`; show "Rate limit reached — waiting {N}s before continuing"; retry once after wait.

---

## Request Defaults (applied via `requests.Session`)

```python
session.headers.update({
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
})
session.timeout = 15  # seconds
```
