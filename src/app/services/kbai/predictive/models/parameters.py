"""
Forecast Parameters Data Models

Dataclasses for configurable parameters used in financial projections.
Supports macro-economic, revenue, cost, personnel, and investment parameters.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class GrowthMode(Enum):
    """Modalità di crescita dei ricavi"""
    CONSTANT = "constant"  # Crescita lineare costante
    GEOMETRIC = "geometric"  # Crescita geometrica (composta)
    CAGR_BASED = "cagr_based"  # Basata su CAGR storico


@dataclass
class MacroParameters:
    """
    Parametri macroeconomici esterni.
    Default values represent typical Italian economy assumptions.
    """
    inflazione: float = 0.02  # 2% - Inflazione generale
    inflazione_materie: float = 0.03  # 3% - Inflazione materie prime (settoriale)
    tasso_crescita_settore: float = 0.02  # 2% - Crescita media settore
    costo_denaro: float = 0.04  # 4% - Tasso interesse base
    aliquota_imposte: float = 0.24  # 24% - IRES

    def to_dict(self) -> Dict[str, float]:
        return {
            "inflazione": self.inflazione,
            "inflazione_materie": self.inflazione_materie,
            "tasso_crescita_settore": self.tasso_crescita_settore,
            "costo_denaro": self.costo_denaro,
            "aliquota_imposte": self.aliquota_imposte,
        }


@dataclass
class RevenueParameters:
    """Parametri per proiezione ricavi"""
    tasso_crescita: float = 0.05  # 5% - Tasso crescita ricavi
    growth_mode: GrowthMode = GrowthMode.GEOMETRIC
    use_cagr_storico: bool = True  # Usa CAGR calcolato se disponibile
    variazione_prezzi: float = 0.0  # Variazione prezzi vendita (oltre inflazione)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasso_crescita": self.tasso_crescita,
            "growth_mode": self.growth_mode.value,
            "use_cagr_storico": self.use_cagr_storico,
            "variazione_prezzi": self.variazione_prezzi,
        }


@dataclass
class CostParameters:
    """Parametri per proiezione costi"""
    # Costi variabili
    perc_costi_variabili: Optional[float] = None  # % su ricavi (se None, usa storico)
    variazione_materie: float = 0.0  # Variazione % costi materie (oltre inflazione)
    variazione_servizi: float = 0.0  # Variazione % costi servizi

    # Costi fissi
    indice_costi_fissi_inflazione: bool = True  # Indicizza costi fissi a inflazione
    variazione_oneri_diversi: float = 0.0  # Variazione % oneri diversi

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perc_costi_variabili": self.perc_costi_variabili,
            "variazione_materie": self.variazione_materie,
            "variazione_servizi": self.variazione_servizi,
            "indice_costi_fissi_inflazione": self.indice_costi_fissi_inflazione,
            "variazione_oneri_diversi": self.variazione_oneri_diversi,
        }


@dataclass
class PersonnelParameters:
    """Parametri per proiezione costi del personale"""
    n_dipendenti_attuali: int = 0  # Numero dipendenti attuali (0 = usa storico)
    variazione_organico: int = 0  # +/- dipendenti previsti
    aumento_salariale: float = 0.02  # 2% - Aumento salariale annuo
    salario_medio: Optional[float] = None  # Salario medio (se None, calcola da storico)
    aliquota_oneri: float = 0.30  # 30% - Aliquota oneri sociali
    aliquota_tfr: float = 0.0691  # 6.91% - Quota TFR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_dipendenti_attuali": self.n_dipendenti_attuali,
            "variazione_organico": self.variazione_organico,
            "aumento_salariale": self.aumento_salariale,
            "salario_medio": self.salario_medio,
            "aliquota_oneri": self.aliquota_oneri,
            "aliquota_tfr": self.aliquota_tfr,
        }


@dataclass
class WorkingCapitalParameters:
    """
    Parametri per gestione capitale circolante.
    DSO/DPO/DOH sono espressi in giorni.
    """
    dso: float = 60.0  # Days Sales Outstanding - Giorni incasso crediti
    dpo: float = 45.0  # Days Payable Outstanding - Giorni pagamento fornitori
    doh: float = 30.0  # Days On Hand - Giorni magazzino (rimanenze)

    # Override con valori fissi (se specificati)
    crediti_fissi: Optional[float] = None
    debiti_fornitori_fissi: Optional[float] = None
    magazzino_fisso: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dso": self.dso,
            "dpo": self.dpo,
            "doh": self.doh,
            "crediti_fissi": self.crediti_fissi,
            "debiti_fornitori_fissi": self.debiti_fornitori_fissi,
            "magazzino_fisso": self.magazzino_fisso,
        }


@dataclass
class InvestmentParameters:
    """Parametri per investimenti pianificati"""
    investimento_totale: float = 0.0  # Importo investimento
    anno_investimento: int = 1  # Anno di investimento (1, 2, o 3)
    vita_utile: int = 10  # Anni vita utile (per ammortamento)
    roi_atteso: float = 0.0  # ROI atteso dall'investimento

    # Tipo investimento
    is_materiale: bool = True  # True = materiale, False = immateriale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "investimento_totale": self.investimento_totale,
            "anno_investimento": self.anno_investimento,
            "vita_utile": self.vita_utile,
            "roi_atteso": self.roi_atteso,
            "is_materiale": self.is_materiale,
        }

    @property
    def quota_ammortamento_annua(self) -> float:
        """Calcola quota ammortamento annua lineare"""
        if self.vita_utile <= 0:
            return 0.0
        return self.investimento_totale / self.vita_utile


@dataclass
class FinancialParameters:
    """Parametri finanziari"""
    tasso_interesse_debito: float = 0.05  # 5% - Tasso interesse su debiti finanziari
    variazione_debito_finanziario: float = 0.0  # Variazione % debito finanziario
    distribuzione_dividendi: float = 0.0  # % utile distribuito come dividendi

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasso_interesse_debito": self.tasso_interesse_debito,
            "variazione_debito_finanziario": self.variazione_debito_finanziario,
            "distribuzione_dividendi": self.distribuzione_dividendi,
        }


@dataclass
class ForecastParameters:
    """
    Parametri completi per la previsione.
    Aggregation of all parameter categories.
    """
    # Orizzonte temporale
    anno_base: int = 2024
    orizzonte_anni: int = 3  # 1, 2, o 3 anni di previsione

    # Parameter groups
    macro: MacroParameters = field(default_factory=MacroParameters)
    revenue: RevenueParameters = field(default_factory=RevenueParameters)
    costs: CostParameters = field(default_factory=CostParameters)
    personnel: PersonnelParameters = field(default_factory=PersonnelParameters)
    working_capital: WorkingCapitalParameters = field(default_factory=WorkingCapitalParameters)
    investment: InvestmentParameters = field(default_factory=InvestmentParameters)
    financial: FinancialParameters = field(default_factory=FinancialParameters)

    # Custom overrides (per scenario)
    custom_overrides: Dict[str, Any] = field(default_factory=dict)

    def get_anni_previsione(self) -> list:
        """Ritorna lista anni di previsione"""
        return [self.anno_base + i for i in range(1, self.orizzonte_anni + 1)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            "anno_base": self.anno_base,
            "orizzonte_anni": self.orizzonte_anni,
            "anni_previsione": self.get_anni_previsione(),
            "macro": self.macro.to_dict(),
            "revenue": self.revenue.to_dict(),
            "costs": self.costs.to_dict(),
            "personnel": self.personnel.to_dict(),
            "working_capital": self.working_capital.to_dict(),
            "investment": self.investment.to_dict(),
            "financial": self.financial.to_dict(),
            "custom_overrides": self.custom_overrides,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForecastParameters":
        """Create ForecastParameters from dictionary"""
        params = cls(
            anno_base=data.get("anno_base", 2024),
            orizzonte_anni=data.get("orizzonte_anni", 3),
        )

        if "macro" in data:
            params.macro = MacroParameters(**data["macro"])
        if "revenue" in data:
            rev_data = data["revenue"].copy()
            if "growth_mode" in rev_data:
                rev_data["growth_mode"] = GrowthMode(rev_data["growth_mode"])
            params.revenue = RevenueParameters(**rev_data)
        if "costs" in data:
            params.costs = CostParameters(**data["costs"])
        if "personnel" in data:
            params.personnel = PersonnelParameters(**data["personnel"])
        if "working_capital" in data:
            params.working_capital = WorkingCapitalParameters(**data["working_capital"])
        if "investment" in data:
            params.investment = InvestmentParameters(**data["investment"])
        if "financial" in data:
            params.financial = FinancialParameters(**data["financial"])
        if "custom_overrides" in data:
            params.custom_overrides = data["custom_overrides"]

        return params

    def apply_scenario_modifiers(self, modifiers: "ScenarioModifiers") -> "ForecastParameters":
        """
        Apply scenario modifiers to create a modified copy of parameters.
        Returns new instance, doesn't modify original.
        """
        from copy import deepcopy
        from .scenario import ScenarioModifiers

        new_params = deepcopy(self)

        # Apply revenue modifier
        new_params.revenue.tasso_crescita *= (1 + modifiers.revenue_growth_modifier)

        # Apply cost modifiers
        new_params.costs.variazione_materie += modifiers.cost_materie_modifier
        new_params.costs.variazione_servizi += modifiers.cost_servizi_modifier

        # Apply macro modifiers
        new_params.macro.inflazione *= (1 + modifiers.inflation_modifier)
        new_params.macro.costo_denaro *= (1 + modifiers.interest_rate_modifier)

        # Apply personnel modifier
        new_params.personnel.variazione_organico += modifiers.personnel_change

        # Store custom overrides from scenario
        new_params.custom_overrides.update(modifiers.custom_modifiers)

        return new_params
