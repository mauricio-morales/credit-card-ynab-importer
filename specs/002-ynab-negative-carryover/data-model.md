# Data Model: Monthly Overspend Cascade

**Branch**: `002-ynab-negative-carryover` | **Date**: 2026-05-25

All entities are Python dataclasses unless noted otherwise. Currency values are always stored as integers in YNAB milliunits (1,000 milliunits = $1.00); the UI layer converts to human-readable display strings.

---

## Persistent Entities (stored in `~/.config/credit-card-ynab-importer/config.json`)

### BudgetConfig

```python
@dataclass
class BudgetConfig:
    budget_name: str       # Display name (stored for UI; not used as identifier)
    loan_account_id: str   # Internal loan account UUID for this budget
```

### Config

```python
@dataclass
class Config:
    api_key: str                        # YNAB Personal Access Token (shared across all budgets)
    budgets: dict[str, BudgetConfig]    # keyed by YNAB budget UUID
```

JSON on disk:
```json
{
  "api_key": "...",
  "budgets": {
    "<budget_uuid_crc>": {
      "budget_name": "CRC Budget",
      "loan_account_id": "<account_uuid>"
    },
    "<budget_uuid_usd>": {
      "budget_name": "USD Budget",
      "loan_account_id": "<account_uuid>"
    }
  }
}
```

Validation rules:
- `api_key` must be non-empty; validated live against the YNAB API before saving.
- `budgets` may be empty (API key stored but no budget yet configured).
- Each `BudgetConfig.loan_account_id` must correspond to an existing account in its budget; if missing at cascade load time, surface a specific error and offer to reconfigure.
- Writing config is atomic: write to a `.tmp` file then rename, so a partial write never corrupts existing config.

---

## Runtime Entities (in-memory only; sourced from YNAB API)

### YNABAccount

```python
@dataclass
class YNABAccount:
    id: str
    name: str
    type: str        # e.g. "checking", "savings", "otherAsset", "lineOfCredit", etc.
    deleted: bool
    on_budget: bool
```

Used during setup wizard to display account choices and identify the loan account.

---

### CategoryGroup

```python
@dataclass
class CategoryGroup:
    id: str
    name: str
    is_credit_card_payment: bool  # True when name == "Credit Card Payments" (case-insensitive)
    deleted: bool
```

---

### Category

```python
@dataclass
class Category:
    id: str
    name: str
    group_id: str
    group_name: str
    is_credit_card_payment: bool  # inherited from CategoryGroup.is_credit_card_payment
    deleted: bool
```

Loaded once from `GET /budgets/{id}/categories` and cached for the session. The monthly available balance is separate (see `CategoryMonthBalance`).

---

### CategoryMonthBalance

```python
@dataclass
class CategoryMonthBalance:
    category_id: str
    category_name: str
    group_name: str
    month: date               # first day of the month this balance belongs to
    available: int            # milliunits; negative means over-spent
    is_credit_card_payment: bool
```

Sourced from `GET /budgets/{id}/months/{YYYY-MM-01}`. One instance per category per month in the lookback window. The cascade operates exclusively on records where `available < 0` and `is_credit_card_payment == False`.

---

## Planning Entities (computed in-memory by `tui/ynab/cascade.py`)

### DonorAllocation

```python
@dataclass
class DonorAllocation:
    donor_category_id: str
    donor_category_name: str
    amount_milliunits: int   # positive; this donor's total contribution across all categories it covers
```

One per donor contributing to a month's cascade. All `DonorAllocation` objects across the whole month aggregate into a single Transaction A and a single Transaction B at execution time — there are no per-allocation transaction IDs.

---

### SplitSubtransaction

```python
@dataclass
class SplitSubtransaction:
    category_id: str
    category_name: str
    amount_milliunits: int   # negative for donors in Tx A; positive for carryover categories in Tx A
                             # signs are flipped for Tx B (exact inverse)
    memo: str                # "donor" or "carryover"
```

Describes one line within a YNAB split transaction. Built at execution time from the month's `CarryoverTuplet` list; not stored between sessions.

Helper: `build_split_subtransactions(carryovers, donors) -> tuple[list[SplitSubtransaction], list[SplitSubtransaction]]` returns `(tx_a_subtransactions, tx_b_subtransactions)` where `tx_b` is the element-wise sign-inverse of `tx_a`.

Invariant: `sum(s.amount_milliunits for s in tx_a_subtransactions) == 0`

---

### CarryoverTuplet

```python
@dataclass
class CarryoverTuplet:
    target_category_id: str
    target_category_name: str
    target_group_name: str
    source_month: date              # month being corrected (e.g., 2026-04-01)
    deficit_milliunits: int         # positive; total amount to carry forward
    is_carry_forward: bool = False  # True if induced by a prior month's execution
```

`is_carry_forward` is used by the UI to visually distinguish "originally negative" categories from those that appeared due to carry-forward simulation (Story 3, acceptance scenario 5).

Donors are computed at the `MonthPlan` level, not per tuplet, because the single Transaction A pools all donors together.

---

### MonthPlan

```python
@dataclass
class MonthPlan:
    month: date                       # first day of the month being processed
    carryovers: list[CarryoverTuplet]
    donors: list[DonorAllocation]     # auto-selected; covers the total deficit across all carryovers
    transaction_a_id: str | None      # set after Transaction A POST succeeds
    transaction_b_id: str | None      # set after Transaction B POST succeeds
```

One `MonthPlan` per month presented to the user. The plan for month M+1 is derived by taking the initial scan data for M+1 and merging in the carry-forward amounts produced by executing month M.

Invariant: `sum(d.amount_milliunits for d in donors) == sum(c.deficit_milliunits for c in carryovers)`

State transitions:
- Before execution: both IDs are `None`
- After Transaction A created: `transaction_a_id = "<uuid>"`
- After Transaction B created: `transaction_b_id = "<uuid>"` → month complete
- On Transaction B failure: `DELETE transaction_a_id` → both IDs reset to `None`; user may retry

---

### ClearanceCheckResult

```python
@dataclass
class AccountReconciliationIssue:
    account_name: str
    unreconciled_count: int   # number of non-reconciled transactions in lookback window

@dataclass
class ClearanceCheckResult:
    passed: bool
    issues: list[AccountReconciliationIssue]  # empty when passed == True
```

The loan account is never included in `issues` — it is excluded from the check entirely. Both cleared (C) and uncleared (U) transactions count toward `unreconciled_count`; only reconciled (R) transactions are acceptable.

---

### MonthExecutionResult

```python
@dataclass
class MonthExecutionResult:
    month: date
    succeeded: bool   # True if Transaction A and Transaction B both posted successfully
    failed: bool      # True if either transaction failed (Transaction A rolled back)
    error: str        # error message if failed; empty string otherwise
```

---

## State Transitions (cascade session lifecycle)

```
[App launch]
    │
    ├─ CSV only (no YNAB) ──────────────────────────────→ [CSV screens, unchanged]
    │
    └─ Navigate to Cascade
            │
            ├─ No config ──→ [SetupWizardScreen] ──→ [Config saved] ──┐
            │                                                           │
            └─ Config exists ────────────────────────────────────────┘
                        │
                        ↓
            [CascadeScanScreen: clearance check]
                        │
                        ├─ Uncleared transactions ──→ [Blocked state, show accounts]
                        │
                        └─ All clear ──→ [Scan overview: affected months listed]
                                    │
                                    └─ User starts cascade
                                                │
                                    [CascadeMonthScreen: month M summary]
                                                │
                                    User confirms ──→ Execute tuplets
                                                │
                                    ├─ Partial failure ──→ Retry screen
                                    │
                                    └─ All success ──→ derive month M+1 plan
                                                │
                                    [CascadeMonthScreen: month M+1 summary]
                                                ...
                                    [Completion screen: summary + final scan confirm]
```

---

## Currency Display Convention

All amounts stored in milliunits. Display helper converts to strings:
- `1234560` → `"$1,234.56"`
- `-50000` → `-`$50.00` (shown as positive value in UI per FR-010: "carryover amount as a positive value")
- Milliunits are integers; no floating point arithmetic is used at any point.
