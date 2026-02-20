"""
Models package for predictive engine prototype.

Contains dataclasses for:
- BalanceSheet: Financial statement structures (CE + SP)
- Parameters: Configurable forecast parameters
- Scenario: Scenario templates (Base, Optimistic, Pessimistic)
"""

from .balance_sheet import (
    BalanceSheetData,
    ContoEconomico,
    StatoPatrimoniale,
    ValoreProduzione,
    CostiProduzione,
    AttivoCircolante,
    Passivo,
)
from .parameters import (
    ForecastParameters,
    MacroParameters,
    RevenueParameters,
    CostParameters,
    PersonnelParameters,
    WorkingCapitalParameters,
    InvestmentParameters,
    FinancialParameters,
)
from .scenario import (
    ScenarioType,
    ScenarioModifiers,
    SCENARIO_PRESETS,
)

__all__ = [
    # Balance Sheet
    "BalanceSheetData",
    "ContoEconomico",
    "StatoPatrimoniale",
    "ValoreProduzione",
    "CostiProduzione",
    "AttivoCircolante",
    "Passivo",
    # Parameters
    "ForecastParameters",
    "MacroParameters",
    "RevenueParameters",
    "CostParameters",
    "PersonnelParameters",
    "WorkingCapitalParameters",
    "InvestmentParameters",
    "FinancialParameters",
    # Scenario
    "ScenarioType",
    "ScenarioModifiers",
    "SCENARIO_PRESETS",
]
