from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


# ── Planning Entities ────────────────────────────────────────────────────────

@dataclass
class DonorAllocation:
    donor_category_id: str
    donor_category_name: str
    amount_milliunits: int  # positive


@dataclass
class SplitSubtransaction:
    category_id: str
    category_name: str
    amount_milliunits: int
    memo: str


@dataclass
class CarryoverTuplet:
    target_category_id: str
    target_category_name: str
    target_group_name: str
    source_month: date
    deficit_milliunits: int  # positive
    is_carry_forward: bool = False


@dataclass
class MonthPlan:
    month: date
    carryovers: list[CarryoverTuplet]
    donors: list[DonorAllocation]
    transaction_a_id: str | None = None
    transaction_b_id: str | None = None


@dataclass
class AccountReconciliationIssue:
    account_name: str
    unreconciled_count: int
    earliest_unreconciled: date | None = None


@dataclass
class ClearanceCheckResult:
    passed: bool
    issues: list[AccountReconciliationIssue] = field(default_factory=list)


@dataclass
class MonthExecutionResult:
    month: date
    succeeded: bool
    failed: bool
    error: str = ""


# ── Helpers ──────────────────────────────────────────────────────────────────

class InsufficientFundsError(Exception):
    pass


def format_milliunits(amount: int) -> str:
    """Convert YNAB milliunits to a human-readable currency string."""
    abs_amount = abs(amount)
    dollars = abs_amount // 1000
    cents = (abs_amount % 1000) // 10
    formatted = f"${dollars:,}.{cents:02d}"
    if amount < 0:
        return f"-{formatted}"
    return formatted


# ── Business Logic ───────────────────────────────────────────────────────────

def check_clearance(
    transactions: list[dict],
    loan_account_id: str,
    account_name_map: dict[str, str],
    all_transactions: list[dict] | None = None,
) -> ClearanceCheckResult:
    counts: dict[str, int] = {}
    earliest: dict[str, date] = {}
    for txn in transactions:
        if txn.get("account_id") == loan_account_id:
            continue
        if txn.get("cleared") != "reconciled":
            acct_id = txn.get("account_id", "")
            counts[acct_id] = counts.get(acct_id, 0) + 1
            raw_date = txn.get("date")
            if raw_date:
                txn_date = date.fromisoformat(raw_date)
                if acct_id not in earliest or txn_date < earliest[acct_id]:
                    earliest[acct_id] = txn_date

    if not counts:
        return ClearanceCheckResult(passed=True)

    # If a broader transaction set is provided, find the latest reconciled date per account.
    # An account whose latest reconciled transaction is *after* its earliest unreconciled one
    # has already been reconciled past those transactions — they're just late-posting items
    # that will appear on a future statement. Don't block on them.
    if all_transactions is not None:
        latest_reconciled: dict[str, date] = {}
        for txn in all_transactions:
            if txn.get("account_id") == loan_account_id:
                continue
            if txn.get("cleared") == "reconciled":
                acct_id = txn.get("account_id", "")
                raw_date = txn.get("date")
                if raw_date:
                    txn_date = date.fromisoformat(raw_date)
                    if acct_id not in latest_reconciled or txn_date > latest_reconciled[acct_id]:
                        latest_reconciled[acct_id] = txn_date

        counts = {
            acct_id: count
            for acct_id, count in counts.items()
            if not (
                acct_id in latest_reconciled
                and latest_reconciled[acct_id] > earliest.get(acct_id, date.min)
            )
        }

    if not counts:
        return ClearanceCheckResult(passed=True)

    return ClearanceCheckResult(
        passed=False,
        issues=[
            AccountReconciliationIssue(
                account_name=account_name_map.get(acct_id, acct_id),
                unreconciled_count=count,
                earliest_unreconciled=earliest.get(acct_id),
            )
            for acct_id, count in counts.items()
        ],
    )


def build_scan_overview(
    month_balances: dict[date, list],
) -> dict[date, list]:
    """Filter to negative non-CC categories, drop empty months, sort oldest-first."""
    result: dict[date, list] = {}
    for month in sorted(month_balances.keys()):
        qualifying = [
            b for b in month_balances[month]
            if not b.is_credit_card_payment and b.available < 0
        ]
        if qualifying:
            result[month] = qualifying
    return result


def select_donors(
    category_balances: list,
    total_deficit_milliunits: int,
) -> list[DonorAllocation]:
    """Greedy largest-first donor selection from non-CC positive-balance categories."""
    eligible = sorted(
        [
            b for b in category_balances
            if b.available > 0
            and not b.is_credit_card_payment
            and b.category_name != "Inflow: Ready to Assign"
        ],
        key=lambda b: b.available,
        reverse=True,
    )
    total_available = sum(b.available for b in eligible)
    if total_available < total_deficit_milliunits:
        raise InsufficientFundsError(
            f"Need {total_deficit_milliunits} milliunits but only {total_available} available"
        )

    allocations: list[DonorAllocation] = []
    remaining = total_deficit_milliunits
    for b in eligible:
        if remaining <= 0:
            break
        amount = min(b.available, remaining)
        allocations.append(DonorAllocation(
            donor_category_id=b.category_id,
            donor_category_name=b.category_name,
            amount_milliunits=amount,
        ))
        remaining -= amount
    return allocations


def build_split_subtransactions(
    carryovers: list[CarryoverTuplet],
    donors: list[DonorAllocation],
) -> tuple[list[SplitSubtransaction], list[SplitSubtransaction]]:
    """Return (tx_a_subtransactions, tx_b_subtransactions) where tx_b is sign-inverse of tx_a."""
    tx_a: list[SplitSubtransaction] = []
    for donor in donors:
        tx_a.append(SplitSubtransaction(
            category_id=donor.donor_category_id,
            category_name=donor.donor_category_name,
            amount_milliunits=-donor.amount_milliunits,
            memo="donor",
        ))
    for co in carryovers:
        tx_a.append(SplitSubtransaction(
            category_id=co.target_category_id,
            category_name=co.target_category_name,
            amount_milliunits=co.deficit_milliunits,
            memo="carryover",
        ))

    assert sum(s.amount_milliunits for s in tx_a) == 0, "Tx A subtransactions must sum to zero"

    tx_b = [
        SplitSubtransaction(
            category_id=s.category_id,
            category_name=s.category_name,
            amount_milliunits=-s.amount_milliunits,
            memo=s.memo,
        )
        for s in tx_a
    ]
    return tx_a, tx_b


def build_month_plan(
    month: date,
    live_balances: list,
    initial_scan_balances: list,
) -> MonthPlan:
    """Derive a MonthPlan from live YNAB data, using initial scan for carry-forward labeling."""
    initial_negative_ids = {
        b.category_id for b in initial_scan_balances
        if b.available < 0 and not b.is_credit_card_payment
    }
    negative_live = [
        b for b in live_balances
        if b.available < 0 and not b.is_credit_card_payment
    ]
    carryovers = [
        CarryoverTuplet(
            target_category_id=b.category_id,
            target_category_name=b.category_name,
            target_group_name=b.group_name,
            source_month=month,
            deficit_milliunits=abs(b.available),
            is_carry_forward=(b.category_id not in initial_negative_ids),
        )
        for b in negative_live
    ]
    total_deficit = sum(c.deficit_milliunits for c in carryovers)
    donors = select_donors(live_balances, total_deficit)

    return MonthPlan(
        month=month,
        carryovers=carryovers,
        donors=donors,
        transaction_a_id=None,
        transaction_b_id=None,
    )
