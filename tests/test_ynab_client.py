"""Unit tests for YNABClient — all HTTP calls mocked; zero real network calls."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from tui.ynab.client import YNABClient, YNABClientError


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_client() -> YNABClient:
    return YNABClient("fake-api-key")


def _mock_response(status_code: int, json_body: dict | None = None, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    resp.text = str(json_body)
    resp.headers = headers or {}
    return resp


# ── get_budgets() ─────────────────────────────────────────────────────────────

class TestGetBudgets:
    def test_returns_budget_list_on_200(self):
        client = _make_client()
        budgets_payload = {
            "data": {
                "budgets": [
                    {"id": "budget-1", "name": "My Budget"},
                    {"id": "budget-2", "name": "Other Budget"},
                ]
            }
        }
        with patch.object(client._session, "request", return_value=_mock_response(200, budgets_payload)):
            result = client.get_budgets()
        assert len(result) == 2
        assert result[0]["id"] == "budget-1"
        assert result[1]["name"] == "Other Budget"

    def test_raises_on_401(self):
        client = _make_client()
        with patch.object(client._session, "request", return_value=_mock_response(401)):
            with pytest.raises(YNABClientError, match="Invalid API key"):
                client.get_budgets()

    def test_returns_empty_list_when_budgets_empty(self):
        client = _make_client()
        payload = {"data": {"budgets": []}}
        with patch.object(client._session, "request", return_value=_mock_response(200, payload)):
            result = client.get_budgets()
        assert result == []

    def test_raises_on_network_timeout(self):
        import requests as req
        client = _make_client()
        with patch.object(client._session, "request", side_effect=req.Timeout):
            with pytest.raises(YNABClientError, match="timed out"):
                client.get_budgets()


# ── get_accounts() ───────────────────────────────────────────────────────────

class TestGetAccounts:
    def _make_accounts_payload(self, accounts: list[dict]) -> dict:
        return {"data": {"accounts": accounts}}

    def test_returns_filtered_accounts_on_200(self):
        client = _make_client()
        accounts = [
            {"id": "a1", "name": "Checking", "type": "checking", "on_budget": True, "closed": False, "deleted": False},
            {"id": "a2", "name": "Credit Card", "type": "creditCard", "on_budget": True, "closed": False, "deleted": False},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._make_accounts_payload(accounts))):
            result = client.get_accounts("budget-1")
        assert len(result) == 2
        assert result[0].id == "a1"
        assert result[1].name == "Credit Card"

    def test_filters_out_deleted_accounts(self):
        client = _make_client()
        accounts = [
            {"id": "a1", "name": "Active", "type": "checking", "on_budget": True, "closed": False, "deleted": False},
            {"id": "a2", "name": "Deleted", "type": "checking", "on_budget": True, "closed": False, "deleted": True},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._make_accounts_payload(accounts))):
            result = client.get_accounts("budget-1")
        assert len(result) == 1
        assert result[0].id == "a1"

    def test_filters_out_closed_accounts(self):
        client = _make_client()
        accounts = [
            {"id": "a1", "name": "Open", "type": "checking", "on_budget": True, "closed": False, "deleted": False},
            {"id": "a2", "name": "Closed", "type": "checking", "on_budget": True, "closed": True, "deleted": False},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._make_accounts_payload(accounts))):
            result = client.get_accounts("budget-1")
        assert len(result) == 1
        assert result[0].id == "a1"

    def test_filters_out_off_budget_accounts(self):
        client = _make_client()
        accounts = [
            {"id": "a1", "name": "On Budget", "type": "checking", "on_budget": True, "closed": False, "deleted": False},
            {"id": "a2", "name": "Tracking", "type": "checking", "on_budget": False, "closed": False, "deleted": False},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._make_accounts_payload(accounts))):
            result = client.get_accounts("budget-1")
        assert len(result) == 1
        assert result[0].id == "a1"

    def test_raises_on_network_error(self):
        import requests as req
        client = _make_client()
        with patch.object(client._session, "request", side_effect=req.ConnectionError("no route")):
            with pytest.raises(YNABClientError, match="Network error"):
                client.get_accounts("budget-1")


# ── get_categories() ─────────────────────────────────────────────────────────

class TestGetCategories:
    def _payload(self, groups: list[dict]) -> dict:
        return {"data": {"category_groups": groups}}

    def test_sets_is_credit_card_payment_for_cc_group(self):
        client = _make_client()
        groups = [
            {
                "id": "g1", "name": "Credit Card Payments", "deleted": False,
                "categories": [
                    {"id": "c1", "name": "Visa", "category_group_id": "g1", "deleted": False},
                ],
            },
            {
                "id": "g2", "name": "Groceries Group", "deleted": False,
                "categories": [
                    {"id": "c2", "name": "Grocery", "category_group_id": "g2", "deleted": False},
                ],
            },
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(groups))):
            result = client.get_categories("budget-1")
        cc_cats = [c for c in result if c.id == "c1"]
        non_cc_cats = [c for c in result if c.id == "c2"]
        assert cc_cats[0].is_credit_card_payment is True
        assert non_cc_cats[0].is_credit_card_payment is False

    def test_cc_detection_is_case_insensitive(self):
        client = _make_client()
        groups = [
            {
                "id": "g1", "name": "CREDIT CARD PAYMENTS", "deleted": False,
                "categories": [{"id": "c1", "name": "Visa", "category_group_id": "g1", "deleted": False}],
            }
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(groups))):
            result = client.get_categories("budget-1")
        assert result[0].is_credit_card_payment is True

    def test_excludes_deleted_groups(self):
        client = _make_client()
        groups = [
            {
                "id": "g1", "name": "Deleted Group", "deleted": True,
                "categories": [{"id": "c1", "name": "Cat", "category_group_id": "g1", "deleted": False}],
            }
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(groups))):
            result = client.get_categories("budget-1")
        assert result == []

    def test_excludes_deleted_categories(self):
        client = _make_client()
        groups = [
            {
                "id": "g1", "name": "Group", "deleted": False,
                "categories": [
                    {"id": "c1", "name": "Active", "category_group_id": "g1", "deleted": False},
                    {"id": "c2", "name": "Deleted", "category_group_id": "g1", "deleted": True},
                ],
            }
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(groups))):
            result = client.get_categories("budget-1")
        assert len(result) == 1
        assert result[0].id == "c1"


# ── get_month_balances() ──────────────────────────────────────────────────────

class TestGetMonthBalances:
    def _payload(self, categories: list[dict]) -> dict:
        return {
            "data": {
                "month": {
                    "month": "2026-02-01",
                    "categories": categories,
                }
            }
        }

    def test_returns_category_balances(self):
        client = _make_client()
        categories = [
            {"id": "c1", "name": "Dining Out", "balance": -30000, "deleted": False},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(categories))):
            result = client.get_month_balances("budget-1", date(2026, 2, 1))
        assert len(result) == 1
        assert result[0].category_id == "c1"
        assert result[0].available == -30000
        assert result[0].month == date(2026, 2, 1)

    def test_excludes_deleted_categories(self):
        client = _make_client()
        categories = [
            {"id": "c1", "name": "Active", "balance": 10000, "deleted": False},
            {"id": "c2", "name": "Deleted", "balance": -5000, "deleted": True},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(categories))):
            result = client.get_month_balances("budget-1", date(2026, 2, 1))
        assert len(result) == 1
        assert result[0].category_id == "c1"

    def test_month_path_formatted_as_first_of_month(self):
        client = _make_client()
        mock_req = MagicMock(return_value=_mock_response(200, self._payload([])))
        with patch.object(client._session, "request", mock_req):
            client.get_month_balances("budget-1", date(2026, 3, 15))
        args, kwargs = mock_req.call_args
        assert "/months/2026-03-01" in args[1]


# ── get_transactions() ────────────────────────────────────────────────────────

class TestGetTransactions:
    def _payload(self, transactions: list[dict]) -> dict:
        return {"data": {"transactions": transactions}}

    def test_returns_transaction_list(self):
        client = _make_client()
        txns = [
            {"id": "t1", "cleared": "reconciled", "account_id": "a1", "account_name": "Checking"},
        ]
        with patch.object(client._session, "request", return_value=_mock_response(200, self._payload(txns))):
            result = client.get_transactions("budget-1", date(2026, 2, 1))
        assert len(result) == 1
        assert result[0]["cleared"] == "reconciled"
        assert result[0]["account_id"] == "a1"

    def test_since_date_sent_as_query_param(self):
        client = _make_client()
        mock_req = MagicMock(return_value=_mock_response(200, self._payload([])))
        with patch.object(client._session, "request", mock_req):
            client.get_transactions("budget-1", date(2026, 2, 1))
        _, kwargs = mock_req.call_args
        assert kwargs.get("params", {}).get("since_date") == "2026-02-01"

    def test_raises_on_network_error(self):
        import requests as req
        client = _make_client()
        with patch.object(client._session, "request", side_effect=req.ConnectionError("fail")):
            with pytest.raises(YNABClientError, match="Network error"):
                client.get_transactions("budget-1", date(2026, 2, 1))


# ── post_transaction() ────────────────────────────────────────────────────────

class TestPostTransaction:
    def _payload(self, txn_id: str) -> dict:
        return {"data": {"transaction": {"id": txn_id}, "transaction_ids": [txn_id]}}

    def test_returns_transaction_id_on_201(self):
        client = _make_client()
        with patch.object(client._session, "request", return_value=_mock_response(201, self._payload("txn-abc"))):
            result = client.post_transaction("budget-1", {"transaction": {}})
        assert result == "txn-abc"

    def test_raises_on_400_without_retry(self):
        client = _make_client()
        error_payload = {"error": {"detail": "Subtransactions do not sum to zero"}}
        with patch.object(client._session, "request", return_value=_mock_response(400, error_payload)):
            with pytest.raises(YNABClientError, match="Bad request"):
                client.post_transaction("budget-1", {})

    def test_pauses_and_retries_on_429(self):
        client = _make_client()
        resp_429 = _mock_response(429, {}, {"X-Rate-Limit": "199/200"})
        resp_201 = _mock_response(201, self._payload("txn-retry"))
        with patch.object(client._session, "request", side_effect=[resp_429, resp_201]):
            with patch("tui.ynab.client.time.sleep") as mock_sleep:
                result = client.post_transaction("budget-1", {})
        mock_sleep.assert_called_once()
        assert result == "txn-retry"

    def test_raises_on_5xx(self):
        client = _make_client()
        with patch.object(client._session, "request", return_value=_mock_response(503)):
            with pytest.raises(YNABClientError, match="server error"):
                client.post_transaction("budget-1", {})


# ── delete_transaction() ──────────────────────────────────────────────────────

class TestDeleteTransaction:
    def test_succeeds_on_200(self):
        client = _make_client()
        payload = {"data": {"transaction": {"id": "txn-1", "deleted": True}}}
        with patch.object(client._session, "request", return_value=_mock_response(200, payload)):
            client.delete_transaction("budget-1", "txn-1")  # should not raise

    def test_raises_with_orphaned_id_on_failure(self):
        client = _make_client()
        with patch.object(client._session, "request", return_value=_mock_response(404)):
            with pytest.raises(YNABClientError, match="txn-orphan"):
                client.delete_transaction("budget-1", "txn-orphan")
