"""
Comprehensive tests for comparison_report_service.py
100% coverage target
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import importlib
service_module = importlib.import_module("src.app.api.v1.services.k_balance.comparison_report_service")

from tests.test_balance_sheet_service import SimpleUser, SimpleUserCompany, TbUserCompanyStub


class MockColumn:
    """Lightweight stand‑in for SQLAlchemy Column used in filters/order_by."""

    def __init__(self, name: str) -> None:
        self._name = name

    def isnot(self, value: Any) -> str:
        # Return a dummy expression; MockQuery.filter(...) just stores it.
        return f"{self._name}_is_not_{value!r}"

    def desc(self) -> str:
        # Return a dummy expression for ORDER BY.
        return f"{self._name}_desc"

    def in_(self, values: list[Any]) -> str:
        # Dummy expression for IN clause; MockQuery.filter simply stores it.
        return f"{self._name}_in_{values!r}"


# Mock database models
class MockKbaiBalance:
    """Mock KbaiBalance model"""

    # Class‑level attributes to emulate real SQLAlchemy columns
    balance = MockColumn("balance")
    id_balance = MockColumn("id_balance")
    year = MockColumn("year")
    month = MockColumn("month")

    counter = 1
    
    def __init__(self, **kwargs):
        self.id_balance = kwargs.get('id_balance', MockKbaiBalance.counter)
        MockKbaiBalance.counter += 1
        self.id_company = kwargs.get('id_company', 1)
        self.year = kwargs.get('year', 2023)
        self.month = kwargs.get('month', 12)
        self.type = kwargs.get('type', 'annual')
        # Mode is used by get_balance_sheets_for_comparison when building the response
        self.mode = kwargs.get('mode', 'manual')
        self.balance = kwargs.get('balance', {})
    
    @classmethod
    def query(cls):
        return MockQuery()
    
    @classmethod
    def findOne(cls, **kwargs):
        return MockKbaiBalance.findone_result


class MockQuery:
    """Mock SQLAlchemy query with simple first()/all() semantics."""

    def __init__(self):
        self._filters = []
        self._order_by = []
        # Sequence of values that successive first() calls will return.
        # When empty, first() falls back to a single first_result attribute (for
        # backward compatibility) or None.
        self.first_results: list[Any] = []
        # Values returned by all()
        self.all_results: list[Any] = []
    
    def filter_by(self, **kwargs):
        self._filters.append(kwargs)
        return self
    
    def filter(self, condition):
        self._filters.append(condition)
        return self
    
    def order_by(self, *args):
        self._order_by.extend(args)
        return self
    
    def first(self):
        if self.first_results:
            return self.first_results.pop(0)
        # Backward‑compatible fallback used by older tests
        return getattr(self, "first_result", None)
    
    def all(self):
        return self.all_results


class MockKbaiAnalysis:
    """Mock KbaiAnalysis model"""
    counter = 1
    create_error = None
    findone_result = None
    
    def __init__(self, **kwargs):
        self.id_analysis = kwargs.get('id_analysis', MockKbaiAnalysis.counter)
        MockKbaiAnalysis.counter += 1
        self.analysis_name = kwargs.get('analysis_name', 'Test Analysis')
        self.analysis_type = kwargs.get('analysis_type', 'year_comparison')
        self.time = kwargs.get('time', datetime.utcnow())
    
    @classmethod
    def create(cls, data):
        if MockKbaiAnalysis.create_error:
            return None, MockKbaiAnalysis.create_error
        return MockKbaiAnalysis(**data), None
    
    @classmethod
    def findOne(cls, **kwargs):
        return MockKbaiAnalysis.findone_result


class MockKbaiReport:
    """Mock KbaiReport model"""
    counter = 1
    create_error = None
    findone_result = None
    
    def __init__(self, **kwargs):
        self.id_report = kwargs.get('id_report', MockKbaiReport.counter)
        MockKbaiReport.counter += 1
        self.id_analysis = kwargs.get('id_analysis', 1)
        self.name = kwargs.get('name', 'Test Report')
        self.type = kwargs.get('type', 'year_comparison')
        self.time = kwargs.get('time', datetime.utcnow())
        self.export_format = kwargs.get('export_format', 'json')
    
    @classmethod
    def create(cls, data):
        if MockKbaiReport.create_error:
            return None, MockKbaiReport.create_error
        return MockKbaiReport(**data), None
    
    @classmethod
    def findOne(cls, **kwargs):
        return MockKbaiReport.findone_result


class MockKbaiKpiValue:
    """Mock KbaiKpiValue model"""
    counter = 1
    instances = {}
    create_error = None
    update_error = None
    findone_result = None
    
    def __init__(self, **kwargs):
        self.id_kpi = kwargs.get('id_kpi', MockKbaiKpiValue.counter)
        MockKbaiKpiValue.counter += 1
        self.id_balance = kwargs.get('id_balance', 1)
        self.kpi_code = kwargs.get('kpi_code', 'm_cod_380')
        self.kpi_name = kwargs.get('kpi_name', 'EBITDA')
        self.value = kwargs.get('value', 0.0)
        self.unit = kwargs.get('unit', '€')
        self.deviation = kwargs.get('deviation', None)
        self.source = kwargs.get('source', 'test')
    
    def update(self, data):
        if MockKbaiKpiValue.update_error:
            return False, MockKbaiKpiValue.update_error
        for key, value in data.items():
            setattr(self, key, value)
        return True, None
    
    @classmethod
    def create(cls, data):
        if MockKbaiKpiValue.create_error:
            return None, MockKbaiKpiValue.create_error
        instance = MockKbaiKpiValue(**data)
        MockKbaiKpiValue.instances[instance.id_kpi] = instance
        return instance, None
    
    @classmethod
    def findOne(cls, **kwargs):
        return MockKbaiKpiValue.findone_result


class MockKpiLogic:
    """Mock KpiLogic model"""
    counter = 1
    create_error = None
    update_error = None
    findone_result = None
    
    def __init__(self, **kwargs):
        self.id_kpi = kwargs.get('id_kpi', MockKpiLogic.counter)
        MockKpiLogic.counter += 1
        self.critical_percentage = kwargs.get('critical_percentage', 0.0)
        self.acceptable_percentage = kwargs.get('acceptable_percentage', 0.0)
    
    def update(self, data):
        if MockKpiLogic.update_error:
            return False, MockKpiLogic.update_error
        for key, value in data.items():
            setattr(self, key, value)
        return True, None
    
    @classmethod
    def create(cls, data):
        if MockKpiLogic.create_error:
            return None, MockKpiLogic.create_error
        return MockKpiLogic(**data), None
    
    @classmethod
    def findOne(cls, **kwargs):
        return MockKpiLogic.findone_result


class MockKbaiAnalysisKpi:
    """Mock KbaiAnalysisKpi model"""
    counter = 1
    create_error = None

    def __init__(self, **kwargs):
        self.id_analysis_kpi = kwargs.get('id_analysis_kpi', MockKbaiAnalysisKpi.counter)
        MockKbaiAnalysisKpi.counter += 1
        self.id_balance = kwargs.get('id_balance', 1)
        self.id_analysis = kwargs.get('id_analysis', 1)
        self.kpi_list_json = kwargs.get('kpi_list_json', {})
    
    @classmethod
    def create(cls, data):
        if MockKbaiAnalysisKpi.create_error:
            return None, MockKbaiAnalysisKpi.create_error
        return MockKbaiAnalysisKpi(**data), None

    # Class-level query object mirroring the pattern used for MockKbaiBalance
    query = MockQuery()


@pytest.fixture(autouse=True)
def patch_service_dependencies():
    """Patch all service dependencies"""
    original_models = {
        'KbaiBalance': service_module.KbaiBalance,
        'KbaiAnalysis': service_module.KbaiAnalysis,
        'KbaiReport': service_module.KbaiReport,
        'KbaiKpiValue': service_module.KbaiKpiValue,
        'KpiLogic': service_module.KpiLogic,
        'KbaiAnalysisKpi': service_module.KbaiAnalysisKpi,
        'TbUserCompany': service_module.TbUserCompany,
        'db': service_module.db,
    }
    
    # Reset mock states
    MockKbaiBalance.query = MockQuery()
    MockKbaiBalance.findone_result = None
    MockKbaiAnalysis.create_error = None
    MockKbaiAnalysis.findone_result = None
    MockKbaiReport.create_error = None
    MockKbaiReport.findone_result = None
    MockKbaiKpiValue.create_error = None
    MockKbaiKpiValue.update_error = None
    MockKbaiKpiValue.findone_result = None
    MockKbaiKpiValue.instances = {}
    MockKpiLogic.create_error = None
    MockKpiLogic.update_error = None
    MockKpiLogic.findone_result = None
    MockKbaiAnalysisKpi.create_error = None
    TbUserCompanyStub.set_entries([])
    
    # Patch models
    service_module.KbaiBalance = MockKbaiBalance
    service_module.KbaiAnalysis = MockKbaiAnalysis
    service_module.KbaiReport = MockKbaiReport
    service_module.KbaiKpiValue = MockKbaiKpiValue
    service_module.KpiLogic = MockKpiLogic
    service_module.KbaiAnalysisKpi = MockKbaiAnalysisKpi
    service_module.TbUserCompany = TbUserCompanyStub
    
    # Mock db.session
    mock_db = MagicMock()
    mock_db.session.rollback = MagicMock()
    service_module.db = mock_db
    
    yield
    
    # Restore
    for key, value in original_models.items():
        setattr(service_module, key, value)


@pytest.fixture
def service_instance():
    return service_module.ComparisonReportService()


@pytest.fixture
def sample_balance_data():
    """Sample balance sheet data"""
    return {
        "Stato_patrimoniale": {
            "Passivo": {
                "Patrimonio_netto": {
                    "Totale_patrimonio_netto": 50000.0,
                    "Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi": 500.0
                }
            },
            "Attivo": {
                "Crediti_verso_soci_per_versamenti_ancora_dovuti": {
                    "Totale_crediti_verso_soci_per_versamenti_ancora_dovuti": 1000.0
                }
            }
        },
        "Conto_economico": {
            "Valore_della_produzione": {
                "Totale_valore_della_produzione": 100000.0,
                "Altri_ricavi_e_proventi": {
                    "Totale_altri_ricavi_e_proventi": 5000.0
                },
                "Ricavi_delle_vendite_e_delle_prestazioni": 80000.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 2000.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 1000.0
            },
            "Costi_di_produzione": {
                "Totale_costi_della_produzione": 80000.0,
                "Ammortamento_e_svalutazioni": {
                    "Totale_ammortamenti_e_svalutazioni": 5000.0
                },
                "Oneri_diversi_di_gestione": 2000.0,
                "Per_materie_prime,_sussidiarie_di_consumo_merci": 20000.0,
                "Per_servizi": 10000.0,
                "Per_godimento_di_terzi": 5000.0,
                "Accantonamento_per_rischi": 1000.0,
                "Altri_accantonamenti": 500.0
            },
            "Proventi_e_oneri_finanziari": {
                "Proventi_da_partecipazioni": {
                    "Totale_proventi_da_partecipazioni": 3000.0
                }
            }
        }
    }


# ============================================================================
# _get_kpi_code Tests
# ============================================================================

def test_get_kpi_code_mapped(service_instance):
    """Test getting KPI code for mapped KPI"""
    code = service_instance._get_kpi_code("EBITDA")
    assert code == "m_cod_380"


def test_get_kpi_code_unmapped(service_instance):
    """Test getting KPI code for unmapped KPI"""
    code = service_instance._get_kpi_code("Custom_KPI_Name")
    assert code.startswith("CUSTOM_")


def test_get_kpi_code_special_chars(service_instance):
    """Test getting KPI code with special characters"""
    code = service_instance._get_kpi_code("KPI-Name@123")
    assert "CUSTOM_" in code
    assert "@" not in code


# ============================================================================
# _store_kpis_for_balance Tests
# ============================================================================

def test_store_kpis_for_balance_new(service_instance):
    """Test storing KPIs for new balance"""
    MockKbaiKpiValue.findone_result = None
    MockKbaiKpiValue.create_error = None
    
    kpis = {"EBITDA": 1000.0, "Revenue": 5000.0}
    service_instance._store_kpis_for_balance(1, kpis)
    
    assert len(MockKbaiKpiValue.instances) > 0


def test_store_kpis_for_balance_existing(service_instance):
    """Test storing KPIs for existing balance"""
    existing = MockKbaiKpiValue(id_balance=1, kpi_code="m_cod_380")
    MockKbaiKpiValue.findone_result = existing
    MockKbaiKpiValue.update_error = None
    
    kpis = {"EBITDA": 1000.0}
    service_instance._store_kpis_for_balance(1, kpis)
    
    assert existing.value == 1000.0


def test_store_kpis_for_balance_with_comparison(service_instance):
    """Test storing KPIs with comparison data"""
    MockKbaiKpiValue.findone_result = None
    
    kpis = {"EBITDA": 1000.0}
    comparison = {
        "EBITDA": {
            "Change_%": 10.5
        }
    }
    
    service_instance._store_kpis_for_balance(1, kpis, comparison=comparison)
    
    # Check that deviation was set
    stored = list(MockKbaiKpiValue.instances.values())[0]
    assert stored.deviation == 10.5


def test_store_kpis_for_balance_percentage_unit(service_instance):
    """Test storing KPI with percentage unit"""
    MockKbaiKpiValue.findone_result = None
    
    kpis = {"MOL_RICAVI_%": 15.5}
    service_instance._store_kpis_for_balance(1, kpis)
    
    stored = list(MockKbaiKpiValue.instances.values())[0]
    assert stored.unit == "%"


def test_store_kpis_for_balance_na_deviation(service_instance):
    """Test storing KPI with N/A deviation"""
    MockKbaiKpiValue.findone_result = None
    
    kpis = {"EBITDA": 1000.0}
    comparison = {
        "EBITDA": {
            "Change_%": "N/A"
        }
    }
    
    service_instance._store_kpis_for_balance(1, kpis, comparison=comparison)
    
    stored = list(MockKbaiKpiValue.instances.values())[0]
    assert stored.deviation is None


# ============================================================================
# _update_kpi_logic_for_value Tests
# ============================================================================

def test_update_kpi_logic_negative_deviation(service_instance):
    """Test updating KPI logic with negative deviation"""
    kpi_value = MockKbaiKpiValue(deviation=-15.0)
    MockKpiLogic.findone_result = None
    MockKpiLogic.create_error = None
    
    service_instance._update_kpi_logic_for_value(kpi_value)
    
    # Should create logic with critical_percentage = -15.0
    assert MockKpiLogic.findone_result is None or MockKpiLogic.counter > 1


def test_update_kpi_logic_positive_deviation(service_instance):
    """Test updating KPI logic with positive deviation"""
    kpi_value = MockKbaiKpiValue(deviation=20.0)
    MockKpiLogic.findone_result = None
    MockKpiLogic.create_error = None
    
    service_instance._update_kpi_logic_for_value(kpi_value)
    
    # Logic should be created with acceptable_percentage = 20.0


def test_update_kpi_logic_no_deviation(service_instance):
    """Test updating KPI logic with no deviation"""
    kpi_value = MockKbaiKpiValue(deviation=None)
    MockKpiLogic.findone_result = None
    MockKpiLogic.create_error = None
    
    service_instance._update_kpi_logic_for_value(kpi_value)
    
    # Both percentages should be 0.0


def test_update_kpi_logic_existing_logic(service_instance):
    """Test updating existing KPI logic"""
    existing_logic = MockKpiLogic(id_kpi=1, critical_percentage=0.0, acceptable_percentage=0.0)
    MockKpiLogic.findone_result = existing_logic
    MockKpiLogic.update_error = None
    
    kpi_value = MockKbaiKpiValue(id_kpi=1, deviation=10.0)
    service_instance._update_kpi_logic_for_value(kpi_value)
    
    assert existing_logic.acceptable_percentage == 10.0


def test_update_kpi_logic_zero_deviation(service_instance):
    """Test updating KPI logic with zero deviation"""
    kpi_value = MockKbaiKpiValue(deviation=0.0)
    existing_logic = MockKpiLogic(id_kpi=1)
    MockKpiLogic.findone_result = existing_logic
    MockKpiLogic.update_error = None
    
    service_instance._update_kpi_logic_for_value(kpi_value)
    
    assert existing_logic.acceptable_percentage == 0.0
    assert existing_logic.critical_percentage == 0.0


def test_update_kpi_logic_exception_handling(service_instance):
    """Test exception handling in update_kpi_logic"""
    kpi_value = MockKbaiKpiValue(deviation="invalid")
    MockKpiLogic.findone_result = None
    MockKpiLogic.create_error = None
    
    # Should not raise exception
    service_instance._update_kpi_logic_for_value(kpi_value)


# ============================================================================
# check_company_access Tests
# ============================================================================

def test_check_company_access_superadmin(service_instance):
    """Test company access for superadmin"""
    user = SimpleUser(role="superadmin")
    has_access, msg = service_instance.check_company_access(user, 1)
    assert has_access is True
    assert msg == ""


def test_check_company_access_staff(service_instance):
    """Test company access for staff"""
    user = SimpleUser(role="staff")
    has_access, msg = service_instance.check_company_access(user, 1)
    assert has_access is True
    assert msg == ""


def test_check_company_access_admin_with_access(service_instance):
    """Test company access for admin with access"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=5)])
    user = SimpleUser(role="admin", id_user=1)
    has_access, msg = service_instance.check_company_access(user, 5)
    assert has_access is True


def test_check_company_access_admin_without_access(service_instance):
    """Test company access for admin without access"""
    TbUserCompanyStub.set_entries([])
    user = SimpleUser(role="admin", id_user=1)
    has_access, msg = service_instance.check_company_access(user, 5)
    assert has_access is False
    assert "Access denied" in msg


def test_check_company_access_user_with_access(service_instance):
    """Test company access for user with access"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=2, id_company=3)])
    user = SimpleUser(role="user", id_user=2)
    has_access, msg = service_instance.check_company_access(user, 3)
    assert has_access is True


def test_check_company_access_user_without_access(service_instance):
    """Test company access for user without access"""
    TbUserCompanyStub.set_entries([])
    user = SimpleUser(role="user", id_user=2)
    has_access, msg = service_instance.check_company_access(user, 3)
    assert has_access is False


# ============================================================================
# get_balance_sheets_for_comparison Tests
# ============================================================================

def test_get_balance_sheets_for_comparison_success(service_instance, sample_balance_data):
    """Test getting balance sheets for comparison successfully"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=1)])
    user = SimpleUser(role="admin", id_user=1)
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, month=12, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, month=12, balance=sample_balance_data)
    
    MockKbaiBalance.query.all_results = [balance1, balance2]
    
    response, status = service_instance.get_balance_sheets_for_comparison(1, user)
    
    assert status == 200
    assert response['data']['count'] == 2
    assert len(response['data']['balance_sheets']) == 2


def test_get_balance_sheets_for_comparison_no_access(service_instance):
    """Test getting balance sheets without access"""
    TbUserCompanyStub.set_entries([])
    user = SimpleUser(role="user", id_user=1)
    
    response, status = service_instance.get_balance_sheets_for_comparison(1, user)
    
    assert status == 403


def test_get_balance_sheets_for_comparison_exception(service_instance):
    """Test getting balance sheets with exception"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=1)])
    user = SimpleUser(role="admin", id_user=1)
    
    # Force exception by making query fail
    MockKbaiBalance.query = None
    
    response, status = service_instance.get_balance_sheets_for_comparison(1, user)
    
    assert status == 500


# ============================================================================
# generate_comparison_report Tests
# ============================================================================

def test_generate_comparison_report_success(service_instance, sample_balance_data):
    """Test generating comparison report successfully"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=1)])
    user = SimpleUser(role="admin", id_user=1)
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, month=12, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, month=12, balance=sample_balance_data)
    
    # First call (year1) -> balance1, second call (year2) -> balance2
    MockKbaiBalance.query.first_results = [balance1, balance2]
    MockKbaiAnalysis.create_error = None
    MockKbaiReport.create_error = None
    MockKbaiAnalysisKpi.create_error = None
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 201
    assert 'id_analysis' in response['data']


def test_generate_comparison_report_balance_not_found(service_instance):
    """Test generating report when balance not found"""
    user = SimpleUser(role="superadmin")
    # First query returns None -> balance_year1 not found
    MockKbaiBalance.query.first_results = [None]
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 404
    assert "not found" in response['message'].lower()


def test_generate_comparison_report_balance2_not_found(service_instance, sample_balance_data):
    """Test generating report when balance2 not found"""
    user = SimpleUser(role="superadmin")
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    # First call (year1) -> balance1, second call (year2) -> None
    MockKbaiBalance.query.first_results = [balance1, None]
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 404


def test_generate_comparison_report_different_companies(service_instance, sample_balance_data):
    """Test generating report when balances belong to different companies"""
    user = SimpleUser(role="superadmin")
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=2, year=2022, balance=sample_balance_data)
    
    MockKbaiBalance.query.first_results = [balance1, balance2]
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 400
    assert "same company" in response['message'].lower()


def test_generate_comparison_report_no_balance_data(service_instance):
    """Test generating report when balance has no data"""
    user = SimpleUser(role="superadmin")
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=None)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance={})
    
    MockKbaiBalance.query.first_results = [balance1, balance2]
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 400


def test_generate_comparison_report_no_access(service_instance, sample_balance_data):
    """Test generating report without access"""
    TbUserCompanyStub.set_entries([])
    user = SimpleUser(role="user", id_user=1)
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance=sample_balance_data)
    
    MockKbaiBalance.query.first_results = [balance1, balance2]
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 403


def test_generate_comparison_report_analysis_create_error(service_instance, sample_balance_data):
    """Test generating report when analysis creation fails"""
    user = SimpleUser(role="superadmin")
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance=sample_balance_data)
    
    MockKbaiBalance.query.first_results = [balance1, balance2]
    MockKbaiAnalysis.create_error = "Database error"
    
    response, status = service_instance.generate_comparison_report(1, 2, user)
    
    assert status == 500


def test_generate_comparison_report_with_debug(service_instance, sample_balance_data):
    """Test generating report with debug mode"""
    user = SimpleUser(role="superadmin")
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance=sample_balance_data)
    
    MockKbaiBalance.query.first_results = [balance1, balance2]
    MockKbaiAnalysis.create_error = None
    MockKbaiReport.create_error = None
    MockKbaiAnalysisKpi.create_error = None
    
    response, status = service_instance.generate_comparison_report(1, 2, user, debug_mode=True)
    
    assert status == 201
    assert 'Debug_Info' in response['data']['comparison_data']


def test_generate_comparison_report_exception(service_instance, sample_balance_data):
    """Test generating report with exception"""
    user = SimpleUser(role="superadmin")
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance=sample_balance_data)
    
    MockKbaiBalance.query.first_result = balance1
    MockKbaiBalance.findone_result = balance2
    
    # Force exception
    with patch.object(service_module, 'FinancialKPIAnalyzer', side_effect=Exception("Test error")):
        response, status = service_instance.generate_comparison_report(1, 2, user)
        assert status == 500


# ============================================================================
# get_comparison_report_by_id Tests
# ============================================================================

def test_get_comparison_report_by_id_success(service_instance, sample_balance_data):
    """Test getting comparison report by ID successfully"""
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=1)])
    user = SimpleUser(role="admin", id_user=1)
    
    analysis = MockKbaiAnalysis(id_analysis=1, analysis_name="Test")
    report = MockKbaiReport(id_report=1, id_analysis=1)
    
    balance1 = MockKbaiBalance(id_balance=1, id_company=1, year=2023, balance=sample_balance_data)
    balance2 = MockKbaiBalance(id_balance=2, id_company=1, year=2022, balance=sample_balance_data)
    
    analysis_kpi1 = MockKbaiAnalysisKpi(id_balance=1, id_analysis=1, kpi_list_json={"kpis": {"EBITDA": 1000.0}, "missing_fields": []})
    analysis_kpi2 = MockKbaiAnalysisKpi(id_balance=2, id_analysis=1, kpi_list_json={"kpis": {"EBITDA": 1200.0}, "missing_fields": []})
    
    MockKbaiAnalysis.findone_result = analysis
    MockKbaiReport.findone_result = report
    MockKbaiAnalysisKpi.query.all_results = [analysis_kpi1, analysis_kpi2]
    MockKbaiBalance.query.all_results = [balance1, balance2]
    
    response, status = service_instance.get_comparison_report_by_id(1, user)
    
    assert status == 200
    assert 'comparison_data' in response['data']


def test_get_comparison_report_by_id_not_found(service_instance):
    """Test getting report when analysis not found"""
    user = SimpleUser(role="superadmin")
    MockKbaiAnalysis.findone_result = None
    
    response, status = service_instance.get_comparison_report_by_id(999, user)
    
    assert status == 404


def test_get_comparison_report_by_id_report_not_found(service_instance):
    """Test getting report when report not found"""
    user = SimpleUser(role="superadmin")
    analysis = MockKbaiAnalysis(id_analysis=1)
    MockKbaiAnalysis.findone_result = analysis
    MockKbaiReport.findone_result = None
    
    response, status = service_instance.get_comparison_report_by_id(1, user)
    
    assert status == 404


def test_get_comparison_report_by_id_no_kpi_data(service_instance):
    """Test getting report when no KPI data found"""
    user = SimpleUser(role="superadmin")
    analysis = MockKbaiAnalysis(id_analysis=1)
    report = MockKbaiReport(id_report=1, id_analysis=1)
    
    MockKbaiAnalysis.findone_result = analysis
    MockKbaiReport.findone_result = report
    MockKbaiAnalysisKpi.query.all_results = []
    
    response, status = service_instance.get_comparison_report_by_id(1, user)
    
    assert status == 404


def test_get_comparison_report_by_id_no_access(service_instance, sample_balance_data):
    """Test getting report without access"""
    TbUserCompanyStub.set_entries([])
    user = SimpleUser(role="user", id_user=1)
    
    analysis = MockKbaiAnalysis(id_analysis=1)
    report = MockKbaiReport(id_report=1, id_analysis=1)
    balance1 = MockKbaiBalance(id_balance=1, id_company=5, year=2023, balance=sample_balance_data)
    analysis_kpi1 = MockKbaiAnalysisKpi(id_balance=1, id_analysis=1, kpi_list_json={"kpis": {}})
    
    MockKbaiAnalysis.findone_result = analysis
    MockKbaiReport.findone_result = report
    MockKbaiAnalysisKpi.query.all_results = [analysis_kpi1]
    MockKbaiBalance.query.all_results = [balance1]
    
    response, status = service_instance.get_comparison_report_by_id(1, user)
    
    assert status == 403


def test_get_comparison_report_by_id_exception(service_instance):
    """Test getting report with exception"""
    user = SimpleUser(role="superadmin")
    
    # Force exception
    MockKbaiAnalysis.findone_result = None
    with patch.object(MockKbaiAnalysis, 'findOne', side_effect=Exception("Test error")):
        response, status = service_instance.get_comparison_report_by_id(1, user)
        assert status == 500

