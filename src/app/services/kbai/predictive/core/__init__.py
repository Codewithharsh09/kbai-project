"""
Core package for predictive engine prototype.

Contains:
- formula_library: Deterministic financial formulas
- historical_analyzer: Historical analysis and CAGR calculation
- kpi_calculator: KPI calculations (ROI, ROE, ROS, etc.)
- parameterizer: Parameter management and scenario handling
- projection_engine: Main projection engine for CE and SP
"""

from .formula_library import (
    safe_get_nested,
    calcola_ricavi,
    calcola_costi_variabili,
    calcola_costi_fissi,
    calcola_personale,
    calcola_ammortamenti,
    calcola_ebitda,
    calcola_ebit,
    calcola_utile_netto,
    calcola_capitale_circolante,
    calcola_crediti,
    calcola_debiti_fornitori,
    calcola_magazzino,
)
from .historical_analyzer import HistoricalAnalyzer
from .kpi_calculator import KPICalculator
from .parameterizer import Parameterizer
from .projection_engine import ProjectionEngine

__all__ = [
    # Formula library
    "safe_get_nested",
    "calcola_ricavi",
    "calcola_costi_variabili",
    "calcola_costi_fissi",
    "calcola_personale",
    "calcola_ammortamenti",
    "calcola_ebitda",
    "calcola_ebit",
    "calcola_utile_netto",
    "calcola_capitale_circolante",
    "calcola_crediti",
    "calcola_debiti_fornitori",
    "calcola_magazzino",
    # Classes
    "HistoricalAnalyzer",
    "KPICalculator",
    "Parameterizer",
    "ProjectionEngine",
]
