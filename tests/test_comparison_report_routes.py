"""
Client-based tests for comparison_report_routes.py
100% coverage target
"""

import os
import sys
from typing import Any

import pytest
from unittest.mock import MagicMock
from flask import json

# Add src to path so tests can import application modules without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import src.app.api.v1.routes.k_balance.comparison_report_routes as cr
import src.app.api.middleware.auth0_verify as av


@pytest.fixture
def auth_bypass(monkeypatch: pytest.MonkeyPatch):
    """
    Bypass Auth0 middleware so we can call routes through the shared Flask
    test client and still have a valid current_user inside the route.
    """

    def identity(*_args: Any, **_kwargs: Any):
        def _wrap(f):
            return f
        return _wrap

    dummy_user = type(
        "User",
        (object,),
        {"id_user": 10, "role": "admin", "email": "test@example.com"},
    )()

    # Replace auth decorators with no-ops
    monkeypatch.setattr(cr, "require_auth0", identity, raising=False)
    monkeypatch.setattr(av, "require_auth0", identity, raising=False)

    # Ensure any get_current_user call returns our dummy user
    monkeypatch.setattr(cr, "get_current_user", lambda: dummy_user, raising=False)
    monkeypatch.setattr(av, "get_current_user", lambda: dummy_user, raising=False)

    # Short-circuit token handling in the original middleware
    monkeypatch.setattr(av, "_extract_token_from_request", lambda: ("tok", None), raising=False)
    monkeypatch.setattr(av, "_verify_and_get_user", lambda _t: (dummy_user, None), raising=False)

    return dummy_user


@pytest.fixture
def service_mock(monkeypatch: pytest.MonkeyPatch):
    """
    Patch comparison_report_service used by the routes with a MagicMock so we
    can control responses and avoid touching the real DB/business logic.
    """
    service = MagicMock()
    monkeypatch.setattr(cr, "comparison_report_service", service, raising=False)
    return service


def _get_json(resp):
    try:
        return json.loads(resp.data or b"{}")
    except Exception:
        return {}


class TestComparisonReportRoutes:
    # ======================================================================
    # GetBalanceSheetsForBenchmarkReport routes
    # ======================================================================

    def test_get_balances_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/kbai-balance/comparison/balances/1")
        assert resp.status_code in [401, 403]

    def test_get_balances_success(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_balance_sheets_for_comparison.return_value = (
            {"message": "ok", "data": {"balance_sheets": [{"id_balance": 1}]}},
            200,
        )

        resp = client.get(
            "/api/v1/kbai-balance/comparison/balances/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 200
        data = _get_json(resp)
        assert data["data"]["balance_sheets"][0]["id_balance"] == 1

    def test_get_balances_service_error(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_balance_sheets_for_comparison.return_value = (
            {"message": "error"},
            500,
        )

        resp = client.get(
            "/api/v1/kbai-balance/comparison/balances/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 500

    def test_get_balances_exception(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_balance_sheets_for_comparison.side_effect = RuntimeError("boom")

        resp = client.get(
            "/api/v1/kbai-balance/comparison/balances/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 500
        data = _get_json(resp)
        assert data["message"] == "Failed to retrieve balance sheets"

    def test_get_balances_forbidden(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_balance_sheets_for_comparison.return_value = (
            {"message": "Access denied"},
            403,
        )

        resp = client.get(
            "/api/v1/kbai-balance/comparison/balances/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 403
        data = _get_json(resp)
        assert data["success"] is False

    # ======================================================================
    # ComparisonReport POST /comparison routes
    # ======================================================================

    def test_generate_comparison_requires_auth(self, client: Any) -> None:
        resp = client.post("/api/v1/kbai-balance/comparison", json={})
        assert resp.status_code in [401, 403]

    def test_generate_comparison_requires_body(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "Request body is required" in data.get("message", "")

    def test_generate_comparison_requires_id_balance_year1(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "id_balance_year1 is required" in data.get("message", "")

    def test_generate_comparison_requires_id_balance_year2(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "id_balance_year2 is required" in data.get("message", "")

    def test_generate_comparison_validates_id_balance_year1_type(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": "invalid", "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "positive integer" in data.get("message", "")

    def test_generate_comparison_validates_id_balance_year1_zero(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 0, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "id_balance_year1 is required" in data.get("message", "")

    def test_generate_comparison_validates_id_balance_year1_negative(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": -1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "positive integer" in data.get("message", "")

    def test_generate_comparison_validates_id_balance_year2_type(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 0},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "id_balance_year2 is required" in data.get("message", "")

    def test_generate_comparison_validates_id_balance_year2_negative(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": -5},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "positive integer" in data.get("message", "")

    def test_generate_comparison_validates_different_ids(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 1},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400
        data = _get_json(resp)
        assert "different" in data.get("message", "").lower()

    def test_generate_comparison_success(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.return_value = (
            {"message": "ok", "data": {"id_analysis": 5}},
            201,
        )
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={
                "id_balance_year1": 1,
                "id_balance_year2": 2,
                "analysis_name": "Test",
                "debug_mode": True,
            },
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 201
        data = _get_json(resp)
        assert data["data"]["id_analysis"] == 5

    def test_generate_comparison_success_default_debug_mode(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.return_value = (
            {"message": "ok", "data": {"id_analysis": 1}},
            201,
        )
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 201
        service_mock.generate_comparison_report.assert_called_once()

    def test_generate_comparison_service_error(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.return_value = (
            {"message": "error"},
            404,
        )
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 404

    def test_generate_comparison_service_validation_error(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.return_value = (
            {"message": "Validation error"},
            400,
        )
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400

    def test_generate_comparison_service_forbidden(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.return_value = (
            {"message": "Access denied"},
            403,
        )
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 403

    def test_generate_comparison_exception(
        self,
        client: Any,
        auth_bypass,
        service_mock,
    ) -> None:
        service_mock.generate_comparison_report.side_effect = RuntimeError("boom")
        resp = client.post(
            "/api/v1/kbai-balance/comparison",
            json={"id_balance_year1": 1, "id_balance_year2": 2},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 500

    # ======================================================================
    # GetComparisonReportById routes
    # ======================================================================

    def test_get_report_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/kbai-balance/comparison/report/1")
        assert resp.status_code in [401, 403]

    def test_get_report_success(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_comparison_report_by_id.return_value = (
            {"message": "ok", "data": {"id_analysis": 1, "comparison_data": {}}},
            200,
        )
        resp = client.get(
            "/api/v1/kbai-balance/comparison/report/5",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 200
        data = _get_json(resp)
        assert "comparison_data" in data.get("data", {})

    def test_get_report_not_found(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_comparison_report_by_id.return_value = (
            {"message": "not found"},
            404,
        )
        resp = client.get(
            "/api/v1/kbai-balance/comparison/report/999",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 404

    def test_get_report_forbidden(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_comparison_report_by_id.return_value = (
            {"message": "Access denied"},
            403,
        )
        resp = client.get(
            "/api/v1/kbai-balance/comparison/report/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 403

    def test_get_report_exception(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_comparison_report_by_id.side_effect = RuntimeError("boom")
        resp = client.get(
            "/api/v1/kbai-balance/comparison/report/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 500

    def test_get_report_service_error(self, client: Any, auth_bypass, service_mock) -> None:
        service_mock.get_comparison_report_by_id.return_value = (
            {"message": "Internal error"},
            500,
        )
        resp = client.get(
            "/api/v1/kbai-balance/comparison/report/1",
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 500


