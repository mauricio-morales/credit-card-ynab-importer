from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

import requests


# ── Runtime Entities ─────────────────────────────────────────────────────────

@dataclass
class YNABAccount:
    id: str
    name: str
    type: str
    deleted: bool
    on_budget: bool


@dataclass
class CategoryGroup:
    id: str
    name: str
    is_credit_card_payment: bool
    deleted: bool


@dataclass
class Category:
    id: str
    name: str
    group_id: str
    group_name: str
    is_credit_card_payment: bool
    deleted: bool


@dataclass
class CategoryMonthBalance:
    category_id: str
    category_name: str
    group_name: str
    month: date
    available: int
    is_credit_card_payment: bool


# ── HTTP Client ───────────────────────────────────────────────────────────────

_BASE_URL = "https://api.ynab.com/v1"


class YNABClientError(Exception):
    pass


class YNABClient:
    def __init__(self, api_key: str) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        self._timeout = 15

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{_BASE_URL}{path}"
        kwargs.setdefault("timeout", self._timeout)
        try:
            response = self._session.request(method, url, **kwargs)
        except requests.Timeout:
            raise YNABClientError("Request timed out. Check your connection and retry.")
        except requests.ConnectionError as exc:
            raise YNABClientError(f"Network error: {exc}") from exc

        if response.status_code in (200, 201):
            return response.json()

        if response.status_code == 400:
            try:
                detail = response.json().get("error", {}).get("detail", response.text)
            except Exception:
                detail = response.text
            raise YNABClientError(f"Bad request: {detail}")

        if response.status_code == 401:
            raise YNABClientError("Invalid API key. Update it in Settings.")

        if response.status_code == 404:
            raise YNABClientError("Resource not found. The loan account may have been deleted — reconfigure in Settings.")

        if response.status_code == 429:
            rate_header = response.headers.get("X-Rate-Limit", "")
            wait = 60
            if rate_header:
                try:
                    used, limit = (int(x) for x in rate_header.split("/"))
                    wait = max(60, 3600 - (int(time.time()) % 3600))
                except (ValueError, AttributeError):
                    pass
            time.sleep(wait)
            # retry once
            try:
                retry = self._session.request(method, url, **kwargs)
            except requests.Timeout:
                raise YNABClientError("Request timed out after rate-limit wait.")
            except requests.ConnectionError as exc:
                raise YNABClientError(f"Network error after rate-limit wait: {exc}") from exc
            if retry.status_code in (200, 201):
                return retry.json()
            raise YNABClientError(f"Rate limit retry failed ({retry.status_code}).")

        if response.status_code >= 500:
            raise YNABClientError(f"YNAB server error ({response.status_code}). Retry or try again later.")

        raise YNABClientError(f"Unexpected response ({response.status_code}).")

    # ── Endpoints ────────────────────────────────────────────────────────────

    def get_budgets(self) -> list[dict]:
        data = self._request("GET", "/budgets")
        return data["data"]["budgets"]

    def get_accounts(self, budget_id: str, include_closed: bool = False) -> list[YNABAccount]:
        data = self._request("GET", f"/budgets/{budget_id}/accounts")
        accounts = []
        for a in data["data"]["accounts"]:
            if a.get("deleted"):
                continue
            if not include_closed and (not a.get("on_budget") or a.get("closed")):
                continue
            accounts.append(YNABAccount(
                id=a["id"],
                name=a["name"],
                type=a.get("type", ""),
                deleted=a.get("deleted", False),
                on_budget=a.get("on_budget", False),
            ))
        return accounts

    def get_categories(self, budget_id: str) -> list[Category]:
        data = self._request("GET", f"/budgets/{budget_id}/categories")
        categories: list[Category] = []
        for group in data["data"]["category_groups"]:
            if group.get("deleted"):
                continue
            is_cc = group["name"].lower() == "credit card payments"
            for cat in group.get("categories", []):
                if cat.get("deleted"):
                    continue
                categories.append(Category(
                    id=cat["id"],
                    name=cat["name"],
                    group_id=group["id"],
                    group_name=group["name"],
                    is_credit_card_payment=is_cc,
                    deleted=cat.get("deleted", False),
                ))
        return categories

    def get_month_balances(self, budget_id: str, month: date) -> list[CategoryMonthBalance]:
        month_str = month.strftime("%Y-%m-01")
        data = self._request("GET", f"/budgets/{budget_id}/months/{month_str}")
        balances: list[CategoryMonthBalance] = []
        month_data = data["data"]["month"]
        for cat in month_data.get("categories", []):
            if cat.get("deleted"):
                continue
            balances.append(CategoryMonthBalance(
                category_id=cat["id"],
                category_name=cat["name"],
                group_name="",  # not returned by this endpoint; enriched by caller if needed
                month=month,
                available=cat["balance"],
                is_credit_card_payment=False,  # enriched by caller using get_categories
            ))
        return balances

    def get_transactions(self, budget_id: str, since_date: date) -> list[dict]:
        since_str = since_date.strftime("%Y-%m-%d")
        data = self._request("GET", f"/budgets/{budget_id}/transactions", params={"since_date": since_str})
        return data["data"]["transactions"]

    def post_transaction(self, budget_id: str, payload: dict) -> str:
        data = self._request("POST", f"/budgets/{budget_id}/transactions", json=payload)
        return data["data"]["transaction"]["id"]

    def delete_transaction(self, budget_id: str, transaction_id: str) -> None:
        try:
            self._request("DELETE", f"/budgets/{budget_id}/transactions/{transaction_id}")
        except YNABClientError as exc:
            raise YNABClientError(
                f"Failed to delete transaction {transaction_id} — delete it manually in YNAB. Original error: {exc}"
            ) from exc
