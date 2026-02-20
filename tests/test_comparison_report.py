"""
Comprehensive tests for comparison_report.py
100% coverage target
"""

import os
import sys
import tempfile
import json
import pytest
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.app.api.v1.services.k_balance.comparison_report import (
    FuzzyKeyMatcher,
    FinancialKPIAnalyzer,
    compare_kpis,
    analyze_financials
)


@pytest.fixture
def sample_balance_data():
    """Sample balance sheet data for testing"""
    return {
        "Stato_patrimoniale": {
            "Attivo": {
                "Crediti_verso_soci_per_versamenti_ancora_dovuti": {
                    "Totale_crediti_verso_soci_per_versamenti_ancora_dovuti": 1000.0
                },
                "Totale_attivo": 100000.0
            },
            "Passivo": {
                "Patrimonio_netto": {
                    "Totale_patrimonio_netto": 50000.0,
                    "Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi": 500.0
                }
            }
        },
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 80000.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 2000.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 1000.0,
                "Totale_valore_della_produzione": 83000.0,
                "Altri_ricavi_e_proventi": {
                    "Totale_altri_ricavi_e_proventi": 5000.0
                }
            },
            "Costi_di_produzione": {
                "Per_materie_prime,_sussidiarie_di_consumo_merci": 20000.0,
                "Per_servizi": 10000.0,
                "Per_godimento_di_terzi": 5000.0,
                "Totale_costi_della_produzione": 60000.0,
                "Ammortamento_e_svalutazioni": {
                    "Totale_ammortamenti_e_svalutazioni": 5000.0
                },
                "Oneri_diversi_di_gestione": 2000.0,
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
# FuzzyKeyMatcher Tests
# ============================================================================

def test_normalize_key_basic():
    """Test basic key normalization"""
    result = FuzzyKeyMatcher.normalize_key("Test_Key-123")
    assert result == "testkey123"


def test_normalize_key_special_chars():
    """Test normalization with special characters"""
    result = FuzzyKeyMatcher.normalize_key("Key@#$%^&*()")
    assert result == "key"


def test_normalize_key_empty():
    """Test normalization of empty string"""
    result = FuzzyKeyMatcher.normalize_key("")
    assert result == ""


def test_normalize_key_unicode():
    """Test normalization with unicode characters"""
    result = FuzzyKeyMatcher.normalize_key("Café_123")
    assert result == "caf123"


def test_find_key_fuzzy_exact_match():
    """Test finding key with exact match"""
    data = {"exact_key": 100, "other_key": 200}
    result = FuzzyKeyMatcher.find_key_fuzzy(data, "exact_key")
    assert result == "exact_key"


def test_find_key_fuzzy_normalized_match():
    """Test finding key with normalized match"""
    data = {"Test-Key_123": 100, "other": 200}
    result = FuzzyKeyMatcher.find_key_fuzzy(data, "test_key_123")
    assert result == "Test-Key_123"


def test_find_key_fuzzy_close_match():
    """Test finding key with fuzzy matching"""
    data = {"test_key": 100, "other": 200}
    result = FuzzyKeyMatcher.find_key_fuzzy(data, "test_ky", threshold=0.7)
    assert result == "test_key"


def test_find_key_fuzzy_no_match():
    """Test finding key when no match exists"""
    data = {"test_key": 100, "other": 200}
    result = FuzzyKeyMatcher.find_key_fuzzy(data, "nonexistent", threshold=0.9)
    assert result is None


def test_find_key_fuzzy_not_dict():
    """Test finding key when data is not a dict"""
    result = FuzzyKeyMatcher.find_key_fuzzy("not a dict", "key")
    assert result is None


def test_fuzzy_navigate_success():
    """Test successful navigation through nested dict"""
    data = {
        "level1": {
            "level2": {
                "level3": 100.0
            }
        }
    }
    value, found, path = FuzzyKeyMatcher.fuzzy_navigate(data, "level1", "level2", "level3")
    assert value == 100.0
    assert found is True
    assert path == ["level1", "level2", "level3"]


def test_fuzzy_navigate_with_default():
    """Test navigation with default value when key not found"""
    data = {"level1": {"level2": {}}}
    value, found, path = FuzzyKeyMatcher.fuzzy_navigate(data, "level1", "level2", "missing", default=0)
    assert value == 0
    assert found is False
    assert path == ["level1", "level2"]


def test_fuzzy_navigate_not_dict():
    """Test navigation when intermediate value is not a dict"""
    data = {"level1": "not a dict"}
    value, found, path = FuzzyKeyMatcher.fuzzy_navigate(data, "level1", "level2")
    assert value == 0
    assert found is False
    assert path == ["level1"]


def test_fuzzy_navigate_non_numeric_value():
    """Test navigation when value is not numeric"""
    data = {"key": {"nested": "string_value"}}
    value, found, path = FuzzyKeyMatcher.fuzzy_navigate(data, "key", "nested", default=0)
    assert value == "string_value"
    assert found is True


def test_fuzzy_navigate_none_value():
    """Test navigation when value is None"""
    data = {"key": {"nested": None}}
    value, found, path = FuzzyKeyMatcher.fuzzy_navigate(data, "key", "nested", default=0)
    assert value == 0
    assert found is True


# ============================================================================
# FinancialKPIAnalyzer Tests
# ============================================================================

def test_financial_kpi_analyzer_init(sample_balance_data):
    """Test FinancialKPIAnalyzer initialization"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    assert analyzer.data == sample_balance_data
    assert analyzer.year_label == "2023"
    assert analyzer.missing_fields == []
    assert analyzer.matched_paths == {}


def test_safe_get_success(sample_balance_data):
    """Test safe_get with successful navigation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    value = analyzer.safe_get("Conto_economico", "Valore_della_produzione", "Totale_valore_della_produzione")
    assert value == 83000.0
    assert len(analyzer.matched_paths) > 0


def test_safe_get_missing_field(sample_balance_data):
    """Test safe_get with missing field"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    value = analyzer.safe_get("NonExistent", "Path", "Key", default=0)
    assert value == 0
    assert len(analyzer.missing_fields) > 0


def test_calculate_ebitda(sample_balance_data):
    """Test EBITDA calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    ebitda = analyzer.calculate_ebitda()
    assert isinstance(ebitda, float)
    assert 'EBITDA_breakdown' in analyzer.debug_info


def test_calculate_ebit(sample_balance_data):
    """Test EBIT calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    ebit = analyzer.calculate_ebit()
    assert isinstance(ebit, float)
    assert 'EBIT_breakdown' in analyzer.debug_info


def test_get_ricavi_totali(sample_balance_data):
    """Test ricavi totali calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    ricavi = analyzer.get_ricavi_totali()
    assert ricavi == 83000.0  # 80000 + 2000 + 1000
    assert 'Ricavi_Totali_breakdown' in analyzer.debug_info


def test_calculate_mol_ricavi(sample_balance_data):
    """Test MOL/RICAVI calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    mol_ricavi = analyzer.calculate_mol_ricavi()
    assert isinstance(mol_ricavi, float)


def test_calculate_mol_ricavi_zero_revenue():
    """Test MOL/RICAVI with zero revenue"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 0.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    mol_ricavi = analyzer.calculate_mol_ricavi()
    assert mol_ricavi == 0


def test_calculate_ebitda_margin(sample_balance_data):
    """Test EBITDA margin calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    margin = analyzer.calculate_ebitda_margin()
    assert isinstance(margin, float)


def test_calculate_ebitda_margin_zero_denominator():
    """Test EBITDA margin with zero denominator"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Totale_valore_della_produzione": 5000.0,
                "Altri_ricavi_e_proventi": {
                    "Totale_altri_ricavi_e_proventi": 5000.0
                }
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    margin = analyzer.calculate_ebitda_margin()
    assert margin == 0


def test_get_costi_variabili(sample_balance_data):
    """Test costi variabili calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    costi = analyzer.get_costi_variabili()
    assert costi == 35000.0  # 20000 + 10000 + 5000
    assert 'Costi_Variabili_breakdown' in analyzer.debug_info


def test_calculate_mdc_percentage(sample_balance_data):
    """Test margin of contribution percentage calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    mdc = analyzer.calculate_mdc_percentage()
    assert isinstance(mdc, float)


def test_calculate_mdc_percentage_zero_revenue():
    """Test MDC percentage with zero revenue"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 0.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    mdc = analyzer.calculate_mdc_percentage()
    assert mdc == 0


def test_calculate_patrimonio_netto(sample_balance_data):
    """Test patrimonio netto calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    pn = analyzer.calculate_patrimonio_netto()
    assert isinstance(pn, float)
    assert 'Patrimonio_Netto_breakdown' in analyzer.debug_info


def test_calculate_markup(sample_balance_data):
    """Test markup calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    markup = analyzer.calculate_markup()
    assert isinstance(markup, float)


def test_calculate_markup_edge_case():
    """Test markup with edge case (mdc_ratio = 1)"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 100.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0
            },
            "Costi_di_produzione": {
                "Per_materie_prime,_sussidiarie_di_consumo_merci": 0.0,
                "Per_servizi": 0.0,
                "Per_godimento_di_terzi": 0.0
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    markup = analyzer.calculate_markup()
    assert markup == 0  # When (1 - mdc_ratio) == 0


def test_calculate_bep(sample_balance_data):
    """Test BEP (Break Even Point) calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    bep = analyzer.calculate_bep()
    assert isinstance(bep, float)


def test_calculate_bep_zero_mdc():
    """Test BEP with zero MDC ratio"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 100.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0
            },
            "Costi_di_produzione": {
                "Per_materie_prime,_sussidiarie_di_consumo_merci": 100.0,
                "Per_servizi": 0.0,
                "Per_godimento_di_terzi": 0.0,
                "Accantonamento_per_rischi": 0.0,
                "Altri_accantonamenti": 0.0
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    bep = analyzer.calculate_bep()
    assert bep == 0


def test_calculate_spese_generali(sample_balance_data):
    """Test spese generali calculation"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    spese = analyzer.calculate_spese_generali()
    assert isinstance(spese, float)


def test_calculate_spese_generali_zero_revenue():
    """Test spese generali with zero revenue"""
    data = {
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 0.0,
                "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
                "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0
            },
            "Costi_di_produzione": {
                "Per_servizi": 1000.0,
                "Per_godimento_di_terzi": 0.0,
                "Accantonamento_per_rischi": 0.0,
                "Altri_accantonamenti": 0.0
            }
        }
    }
    analyzer = FinancialKPIAnalyzer(data, "2023")
    spese = analyzer.calculate_spese_generali()
    assert spese == 0


def test_calculate_all_kpis(sample_balance_data):
    """Test calculation of all KPIs"""
    analyzer = FinancialKPIAnalyzer(sample_balance_data, "2023")
    kpis = analyzer.calculate_all_kpis()
    
    assert isinstance(kpis, dict)
    assert "EBITDA" in kpis
    assert "EBIT_Reddito_Operativo" in kpis
    assert "MOL_RICAVI_%" in kpis
    assert "EBITDA_Margin_%" in kpis
    assert "Margine_Contribuzione_%" in kpis
    assert "Patrimonio_Netto" in kpis
    assert "Mark_Up" in kpis
    assert "Fatturato_Equilibrio_BEP" in kpis
    assert "Spese_Generali_Ratio" in kpis
    assert "Ricavi_Totali" in kpis
    assert "Costi_Variabili" in kpis
    
    # Check all values are rounded
    for value in kpis.values():
        assert isinstance(value, float)
        # Check rounding (should have at most 4 decimal places)
        assert abs(value - round(value, 4)) < 0.0001


# ============================================================================
# compare_kpis Tests
# ============================================================================

def test_compare_kpis_basic():
    """Test basic KPI comparison"""
    kpis1 = {"EBITDA": 1000.0, "Revenue": 5000.0}
    kpis2 = {"EBITDA": 1200.0, "Revenue": 6000.0}
    
    result = compare_kpis(kpis1, kpis2)
    
    assert "EBITDA" in result
    assert result["EBITDA"]["Year1"] == 1000.0
    assert result["EBITDA"]["Year2"] == 1200.0
    assert result["EBITDA"]["Absolute_Change"] == 200.0
    assert result["EBITDA"]["Change_%"] == 20.0


def test_compare_kpis_negative_change():
    """Test KPI comparison with negative change"""
    kpis1 = {"EBITDA": 1000.0}
    kpis2 = {"EBITDA": 800.0}
    
    result = compare_kpis(kpis1, kpis2)
    
    assert result["EBITDA"]["Absolute_Change"] == -200.0
    assert result["EBITDA"]["Change_%"] == -20.0


def test_compare_kpis_zero_year1():
    """Test KPI comparison when year1 is zero"""
    kpis1 = {"EBITDA": 0.0}
    kpis2 = {"EBITDA": 100.0}
    
    result = compare_kpis(kpis1, kpis2)
    
    assert result["EBITDA"]["Change_%"] == "N/A"  # Should be infinity


def test_compare_kpis_both_zero():
    """Test KPI comparison when both years are zero"""
    kpis1 = {"EBITDA": 0.0}
    kpis2 = {"EBITDA": 0.0}
    
    result = compare_kpis(kpis1, kpis2)
    
    assert result["EBITDA"]["Change_%"] == 0.0


def test_compare_kpis_missing_key():
    """Test KPI comparison when key exists in only one year"""
    kpis1 = {"EBITDA": 1000.0, "Revenue": 5000.0}
    kpis2 = {"EBITDA": 1200.0}
    
    result = compare_kpis(kpis1, kpis2)
    
    assert "Revenue" not in result
    assert "EBITDA" in result


# ============================================================================
# analyze_financials Tests
# ============================================================================

def test_analyze_financials_success(sample_balance_data):
    """Test analyze_financials with valid JSON files"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
        json.dump(sample_balance_data, f1)
        file1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
        json.dump(sample_balance_data, f2)
        file2 = f2.name
    
    try:
        report, analyzer1, analyzer2 = analyze_financials(file1, file2, debug_mode=False)
        
        assert "KPIs_Year1" in report
        assert "KPIs_Year2" in report
        assert "Comparison" in report
        assert "Missing_Fields" in report
        assert "Status" in report
        assert "Debug_Info" not in report
        
        assert isinstance(analyzer1, FinancialKPIAnalyzer)
        assert isinstance(analyzer2, FinancialKPIAnalyzer)
    finally:
        os.remove(file1)
        os.remove(file2)


def test_analyze_financials_with_debug(sample_balance_data):
    """Test analyze_financials with debug mode enabled"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
        json.dump(sample_balance_data, f1)
        file1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
        json.dump(sample_balance_data, f2)
        file2 = f2.name
    
    try:
        report, analyzer1, analyzer2 = analyze_financials(file1, file2, debug_mode=True)
        
        assert "Debug_Info" in report
        assert "Year1" in report["Debug_Info"]
        assert "Year2" in report["Debug_Info"]
    finally:
        os.remove(file1)
        os.remove(file2)


def test_analyze_financials_file_not_found():
    """Test analyze_financials with non-existent file"""
    with pytest.raises(FileNotFoundError):
        analyze_financials("nonexistent1.json", "nonexistent2.json")

