"""
Scenario Templates and Modifiers

Defines scenario types (Base, Optimistic, Pessimistic) and their modifiers.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from .parameters import ForecastParameters


class ScenarioType(Enum):
    """Tipi di scenario predefiniti"""
    BASE = "base"
    OTTIMISTICO = "ottimistico"
    PESSIMISTICO = "pessimistico"
    CUSTOM = "custom"


@dataclass
class ScenarioModifiers:
    """
    Modificatori per uno scenario.
    Tutti i valori sono espressi come variazioni rispetto al caso base.
    """
    name: str = "Base"
    description: str = "Scenario base con parametri di default"

    # Revenue modifiers
    revenue_growth_modifier: float = 0.0  # +/- % rispetto a tasso base

    # Cost modifiers
    cost_materie_modifier: float = 0.0  # +/- % variazione costi materie
    cost_servizi_modifier: float = 0.0  # +/- % variazione costi servizi

    # Macro modifiers
    inflation_modifier: float = 0.0  # +/- % rispetto a inflazione base
    interest_rate_modifier: float = 0.0  # +/- % rispetto a tasso interesse

    # Personnel modifiers
    personnel_change: int = 0  # +/- dipendenti rispetto a organico

    # Custom modifiers (for flexibility)
    custom_modifiers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "revenue_growth_modifier": self.revenue_growth_modifier,
            "cost_materie_modifier": self.cost_materie_modifier,
            "cost_servizi_modifier": self.cost_servizi_modifier,
            "inflation_modifier": self.inflation_modifier,
            "interest_rate_modifier": self.interest_rate_modifier,
            "personnel_change": self.personnel_change,
            "custom_modifiers": self.custom_modifiers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioModifiers":
        return cls(
            name=data.get("name", "Custom"),
            description=data.get("description", ""),
            revenue_growth_modifier=data.get("revenue_growth_modifier", 0.0),
            cost_materie_modifier=data.get("cost_materie_modifier", 0.0),
            cost_servizi_modifier=data.get("cost_servizi_modifier", 0.0),
            inflation_modifier=data.get("inflation_modifier", 0.0),
            interest_rate_modifier=data.get("interest_rate_modifier", 0.0),
            personnel_change=data.get("personnel_change", 0),
            custom_modifiers=data.get("custom_modifiers", {}),
        )

@dataclass
class Scenario:
    """
    A configured Scenario ready for projection.
    Wraps the parameters and metadata.
    """
    name: str
    parameters: ForecastParameters
    type: ScenarioType = ScenarioType.BASE
    description: str = ""

# ============================================================================
# SCENARIO PRESETS
# ============================================================================

SCENARIO_BASE = ScenarioModifiers(
    name="Base",
    description="Scenario base con parametri di default e trend storico",
    revenue_growth_modifier=0.0,
    cost_materie_modifier=0.0,
    cost_servizi_modifier=0.0,
    inflation_modifier=0.0,
    interest_rate_modifier=0.0,
    personnel_change=0,
)

SCENARIO_OTTIMISTICO = ScenarioModifiers(
    name="Ottimistico",
    description="Scenario di espansione: +30% crescita ricavi, -5% costi materie, +3 dipendenti",
    revenue_growth_modifier=0.30,  # +30% rispetto a tasso base
    cost_materie_modifier=-0.05,  # -5% costi materie prime
    cost_servizi_modifier=-0.02,  # -2% costi servizi (efficienza)
    inflation_modifier=-0.10,  # -10% inflazione (scenario favorevole)
    interest_rate_modifier=-0.10,  # -10% tassi interesse
    personnel_change=3,  # +3 dipendenti per crescita
)

SCENARIO_PESSIMISTICO = ScenarioModifiers(
    name="Pessimistico",
    description="Scenario di contrazione: -30% crescita, +50% inflazione costi, +25% costo denaro",
    revenue_growth_modifier=-0.30,  # -30% rispetto a tasso base
    cost_materie_modifier=0.10,  # +10% costi materie prime (scarsità)
    cost_servizi_modifier=0.05,  # +5% costi servizi
    inflation_modifier=0.50,  # +50% inflazione (shock)
    interest_rate_modifier=0.25,  # +25% tassi interesse
    personnel_change=0,  # Organico invariato (no licenziamenti nel breve)
)

# Dictionary for easy access by ScenarioType
SCENARIO_PRESETS: Dict[ScenarioType, ScenarioModifiers] = {
    ScenarioType.BASE: SCENARIO_BASE,
    ScenarioType.OTTIMISTICO: SCENARIO_OTTIMISTICO,
    ScenarioType.PESSIMISTICO: SCENARIO_PESSIMISTICO,
}


def get_scenario_modifiers(scenario_type: ScenarioType) -> ScenarioModifiers:
    """Get scenario modifiers by type"""
    if scenario_type == ScenarioType.CUSTOM:
        # Return empty modifiers for custom scenario
        return ScenarioModifiers(name="Custom", description="Scenario personalizzato")
    return SCENARIO_PRESETS.get(scenario_type, SCENARIO_BASE)


def create_custom_scenario(
    name: str,
    description: str = "",
    **kwargs
) -> ScenarioModifiers:
    """
    Create a custom scenario with specified modifiers.

    Args:
        name: Nome dello scenario
        description: Descrizione
        **kwargs: Modificatori (revenue_growth_modifier, cost_materie_modifier, etc.)

    Returns:
        ScenarioModifiers instance
    """
    return ScenarioModifiers(
        name=name,
        description=description,
        **kwargs
    )


@dataclass
class ScenarioResult:
    """
    Risultato di uno scenario simulato.
    Contiene le previsioni per tutti gli anni dell'orizzonte.
    """
    scenario_type: ScenarioType
    scenario_name: str
    modifiers: ScenarioModifiers
    # Changed from 'previsioni' to 'projections' to match usage in service
    projections: List[Any] = field(default_factory=list)
    # Changed from 'kpi' to 'kpis' to match usage in service
    kpis: Dict[int, Dict[str, float]] = field(default_factory=dict)
    # Warnings/notes
    warnings: list = field(default_factory=list)

    @property
    def previsioni(self) -> Dict[int, Dict[str, Any]]:
        """Compatibility property for legacy code expecting a dict of years"""
        return {
            p.year: p.to_dict() if hasattr(p, "to_dict") else p
            for p in self.projections
        }

    @property
    def kpi(self) -> Dict[int, Dict[str, float]]:
        """Compatibility property for legacy code expecting 'kpi' instead of 'kpis'"""
        return self.kpis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "scenario_name": self.scenario_name,
            "modifiers": self.modifiers.to_dict(),
            "previsioni": self.previsioni,
            "kpi": self.kpi,
            "warnings": self.warnings,
        }
