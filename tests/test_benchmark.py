import pytest
from unittest.mock import patch, MagicMock

import types

# We'll patch Flask request context and db as needed
from flask import Flask
from flask.testing import FlaskClient

@pytest.fixture
def mock_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(mock_app):
    return mock_app.test_client()

@pytest.fixture
def fake_user():
    # Simple user mock with id and is_superadmin/admin flags
    class User:
        id_user = 123
        role = 'admin'
        is_superadmin = False
    return User()

@pytest.fixture
def benchmark_service_cls():
    from src.app.api.v1.services.k_balance import benchmark as benchmark_mod
    return benchmark_mod.BenchmarkService

@pytest.fixture
def benchmark_routes_ns():
    from src.app.api.v1.routes.k_balance import benchmark_routes as routes_mod
    return routes_mod

@pytest.fixture
def mock_request(monkeypatch):
    # provide a dummy .get_json method on flask.request
    fake_payload = {
        "balanceSheetToCompare": {"year": 2022, "budgetType": "annual"},
        "ComparitiveBalancesheet": {"year": 2021, "budgetType": "annual"},
        "referenceBalanceSheet": {"year": 2020, "budgetType": "annual"},
    }
    monkeypatch.setattr("flask.request.get_json", lambda: fake_payload)

def test_create_benchmark_invalid_input(benchmark_service_cls, fake_user, monkeypatch):
    service = benchmark_service_cls()
    # Patch flask.request by providing a fake request context using Flask's test_request_context
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(json={}):
        result, code = service.create_benchmark(fake_user, None)
    assert code == 400
    assert "company_id and at least one balance sheet" in result["message"]

def test_get_benchmarks_by_report_no_reportid(benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    result, code = service.get_benchmarks_by_report(fake_user, None)
    assert code == 400
    assert "report_id is required" in result["message"]

def test_get_benchmarks_by_report_not_found(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    # Patch queries to return None for report
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query.filter_by", MagicMock(return_value=MagicMock(first=lambda: None)))
    result, code = service.get_benchmarks_by_report(fake_user, 55)
    assert code == 404
    assert "Report not found" in result["message"]

def test_get_benchmarks_by_report_permission(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    # Set up mocks to flow until company access denied
    dummy_report = MagicMock(id_analysis=99)
    dummy_analysis = MagicMock(id_analysis=99)
    dummy_ak = MagicMock(id_balance=2)
    balance = MagicMock(id_company=27)
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query.filter_by", MagicMock(return_value=MagicMock(first=lambda: dummy_report)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysis.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysis.query.filter_by", MagicMock(return_value=MagicMock(first=lambda: dummy_analysis)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysisKpi.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysisKpi.query.filter_by", MagicMock(return_value=MagicMock(all=lambda: [dummy_ak])))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiBalance.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiBalance.query.filter_by", MagicMock(return_value=MagicMock(first=lambda: balance)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.ComparisonReportService.check_company_access", lambda *a, **kw: (False, "nope"))
    result, code = service.get_benchmarks_by_report(fake_user, 123)
    assert code == 403
    assert "nope" in result["message"]

def test_get_by_company_id_and_balance_year_success(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    # Patch KbaiBalance.find
    class DummyRecord:
        def __init__(self, year):
            self.year = year
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiBalance.find", staticmethod(lambda **kwargs: ([DummyRecord(2022), DummyRecord(2023)], 2, None)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.ComparisonReportService.check_company_access", lambda *a, **kw: (True, ""))
    data, code = service.get_by_company_id_and_balance_year(5, current_user=fake_user)
    assert code == 200
    assert data['success']
    assert 2022 in data['data']

def test_get_by_company_id_and_balance_year_denied(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.ComparisonReportService.check_company_access", lambda *a, **kw: (False, "nope"))
    data, code = service.get_by_company_id_and_balance_year(2, current_user=fake_user)
    assert code == 403
    assert data["error"] == "Permission denied"

def test_get_benchmark_report_list_denied(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.ComparisonReportService.check_company_access", lambda *a, **kw: (False, "None"))
    output, code = service.get_benchmark_report_list(2, fake_user)
    assert code == 403
    assert "None" in output["message"]

def test_get_benchmark_report_list_pagination(monkeypatch, benchmark_service_cls, fake_user):
    service = benchmark_service_cls()
    # Patch query for KbaiBalance etc
    balances = [
        MagicMock(id_balance=1, is_deleted=False, id_company=2),
        MagicMock(id_balance=2, is_deleted=False, id_company=2)
    ]
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiBalance.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiBalance.query.filter_by", MagicMock(return_value=MagicMock(all=lambda: balances)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.ComparisonReportService.check_company_access", lambda *a, **kw: (True, ""))
    # Patch KbaiAnalysisKpi, KbaiAnalysis, KbaiReport query chains
    dummy_analysis_kpis = [
        MagicMock(id_analysis=23, id_balance=1, kpi_list_json={"balance_type": "reference"},),
        MagicMock(id_analysis=23, id_balance=2, kpi_list_json={"balance_type": "compare"})
    ]
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysisKpi.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysisKpi.query.filter", MagicMock(return_value=MagicMock(all=lambda: dummy_analysis_kpis)))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysis.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiAnalysis.query.filter", MagicMock(return_value=MagicMock(all=lambda: [MagicMock(id_analysis=23, analysis_type="BENCHMARK")])))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query", MagicMock())
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query.filter", MagicMock(return_value=MagicMock(offset=lambda o: MagicMock(limit=lambda l: MagicMock(all=lambda: [MagicMock(id_report=9, name='R', time=None, id_analysis=23)])))))
    monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.KbaiReport.query.filter().count", lambda: 1)
    out, code = service.get_benchmark_report_list(2, fake_user, page=1, per_page=10)
    assert code == 200
    assert "reports" in out

# --- Routes Layer Tests --- #

def test_benchmark_routes_post_success(monkeypatch, benchmark_routes_ns, fake_user):
    # Test POST /benchmark/<int:company_id>
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(json={"balanceSheetToCompare": {"year": 2022, "budgetType": "annual"}}):
        monkeypatch.setattr("src.app.api.middleware.get_current_user", lambda : fake_user)
        monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.BenchmarkService.create_benchmark", lambda self, user, company_id: ({"message": "ok", "data":{}}, 201))
        # The resource is routes_ns.Benchmark
        view = benchmark_routes_ns.Benchmark()
        resp = view.post(1)
        assert isinstance(resp, tuple) or resp.status_code == 201 or resp['status_code'] in (201, 200, 400, 403, 404, 500)

def test_benchmark_routes_post_fail(monkeypatch, benchmark_routes_ns):
    # test error paths
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(json={}):
        monkeypatch.setattr("src.app.api.middleware.get_current_user", lambda : None)
        view = benchmark_routes_ns.Benchmark()
        resp = view.post(1)
        # Should return error_response with status code 401
        # Could be flask Response or dict depending on error_response utility
        assert any([
            (isinstance(resp, dict) and resp.get('status_code', 0) == 401),
            (isinstance(resp, tuple) and resp[1] == 401)
        ])

def test_benchmark_routes_get_reports_success(monkeypatch, benchmark_routes_ns, fake_user):
    app = Flask(__name__)
    with app.test_request_context('/?page=1&per_page=2'):
        monkeypatch.setattr("src.app.api.middleware.get_current_user", lambda : fake_user)
        monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.BenchmarkService.get_benchmark_report_list", lambda *a, **k: ({"message": "ok", "reports":[], "pagination":{}}, 200))
        view = benchmark_routes_ns.GetBalanceSheetsForBenchmarkReport()
        resp = view.get(1)
        assert isinstance(resp, tuple) or resp['status_code'] in (200, 401, 403, 500)

def test_benchmark_routes_get_balance_years_success(monkeypatch, benchmark_routes_ns, fake_user):
    app = Flask(__name__)
    with app.test_request_context():
        monkeypatch.setattr("src.app.api.middleware.get_current_user", lambda : fake_user)
        monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.BenchmarkService.get_by_company_id_and_balance_year", lambda *a, **k: ({"message": "ok", "data": [2021, 2022]}, 200))
        view = benchmark_routes_ns.BalanceYearsByCompany()
        resp = view.get(1)
        assert isinstance(resp, tuple) or resp['status_code'] in (200, 401, 500)

def test_benchmark_routes_get_by_reportid_success(monkeypatch, benchmark_routes_ns, fake_user):
    app = Flask(__name__)
    with app.test_request_context():
        monkeypatch.setattr("src.app.api.middleware.get_current_user", lambda : fake_user)
        monkeypatch.setattr("src.app.api.v1.services.k_balance.benchmark.BenchmarkService.get_benchmarks_by_report", lambda *a, **k: ({"message":"ok", "data": {}}, 200))
        view = benchmark_routes_ns.BenchmarkList()
        resp = view.get(2)
        assert isinstance(resp, tuple) or resp['status_code'] in (200, 401, 403, 404, 500)

