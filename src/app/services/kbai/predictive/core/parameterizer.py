"""
Parameterizer - STEP 2

Manages forecast parameters and scenario configuration.
Handles parameter initialization from historical analysis and scenario modifiers.

Reference: STEP 2 from mappa_logica_previsione.md
"""

from typing import Dict, Any, List, Optional
from copy import deepcopy
from ..models.parameters import (
    ForecastParameters,
    MacroParameters,
    RevenueParameters,
    CostParameters,
    PersonnelParameters,
    WorkingCapitalParameters,
    InvestmentParameters,
    FinancialParameters,
    GrowthMode,
)
from ..models.scenario import (
    ScenarioType,
    ScenarioModifiers,
    SCENARIO_PRESETS,
    get_scenario_modifiers,
)
from .historical_analyzer import HistoricalAnalyzer, HistoricalMetrics


class Parameterizer:
    """
    Manages forecast parameters based on historical analysis and scenario configuration.
    """

    def __init__(
        self,
        historical_analyzer: Optional[HistoricalAnalyzer] = None,
        base_parameters: Optional[ForecastParameters] = None
    ):
        """
        Args:
            historical_analyzer: Analyzer with historical metrics
            base_parameters: Base parameters (if None, will be initialized from historical)
        """
        self.historical = historical_analyzer
        self.base_params = base_parameters or ForecastParameters()
        self._warnings: List[str] = []

        if historical_analyzer:
            self._initialize_from_historical()

    @property
    def warnings(self) -> List[str]:
        return self._warnings

    def _initialize_from_historical(self):
        """Initialize base parameters from historical analysis"""
        if not self.historical:
            return

        metrics = self.historical.metrics

        # Set anno_base from historical
        self.base_params.anno_base = self.historical.anno_base

        # Revenue parameters
        if metrics.cagr_ricavi != 0:
            self.base_params.revenue.tasso_crescita = max(
                min(metrics.cagr_ricavi, 0.30),  # Cap at 30%
                -0.20  # Floor at -20%
            )
            self.base_params.revenue.use_cagr_storico = True
        else:
            # Use sector growth rate if no CAGR available
            self.base_params.revenue.tasso_crescita = (
                self.base_params.macro.tasso_crescita_settore
            )

        # Cost parameters - use historical percentages
        if metrics.perc_costi_variabili > 0:
            self.base_params.costs.perc_costi_variabili = metrics.perc_costi_variabili

        # Personnel parameters
        if metrics.n_dipendenti_stimato > 0:
            self.base_params.personnel.n_dipendenti_attuali = metrics.n_dipendenti_stimato
        if metrics.salario_medio_stimato > 0:
            self.base_params.personnel.salario_medio = metrics.salario_medio_stimato

        # Working capital parameters
        self.base_params.working_capital.dso = metrics.dso_medio
        self.base_params.working_capital.dpo = metrics.dpo_medio
        self.base_params.working_capital.doh = metrics.doh_medio

    def get_base_parameters(self) -> ForecastParameters:
        """Get base parameters (copy)"""
        return deepcopy(self.base_params)

    def get_parameters_for_scenario(
        self,
        scenario_type: ScenarioType
    ) -> ForecastParameters:
        """
        Get parameters configured for a specific scenario.

        Args:
            scenario_type: Type of scenario

        Returns:
            ForecastParameters configured for scenario
        """
        modifiers = get_scenario_modifiers(scenario_type)
        return self.apply_modifiers(self.base_params, modifiers)

    def apply_modifiers(
        self,
        params: ForecastParameters,
        modifiers: ScenarioModifiers
    ) -> ForecastParameters:
        """
        Apply scenario modifiers to parameters.

        Args:
            params: Base parameters
            modifiers: Scenario modifiers

        Returns:
            New ForecastParameters with modifiers applied
        """
        new_params = deepcopy(params)

        # Apply revenue modifier
        original_growth = new_params.revenue.tasso_crescita
        modified_growth = original_growth * (1 + modifiers.revenue_growth_modifier)
        new_params.revenue.tasso_crescita = max(min(modified_growth, 0.50), -0.50)

        # Apply cost modifiers
        new_params.costs.variazione_materie = (
            new_params.costs.variazione_materie + modifiers.cost_materie_modifier
        )
        new_params.costs.variazione_servizi = (
            new_params.costs.variazione_servizi + modifiers.cost_servizi_modifier
        )

        # Apply macro modifiers
        original_inflation = new_params.macro.inflazione
        new_params.macro.inflazione = original_inflation * (1 + modifiers.inflation_modifier)

        original_interest = new_params.macro.costo_denaro
        new_params.macro.costo_denaro = original_interest * (1 + modifiers.interest_rate_modifier)

        # Apply personnel modifier
        new_params.personnel.variazione_organico = (
            new_params.personnel.variazione_organico + modifiers.personnel_change
        )

        # Store modifier info
        new_params.custom_overrides["scenario_name"] = modifiers.name
        new_params.custom_overrides["modifiers_applied"] = modifiers.to_dict()

        return new_params

    def create_custom_parameters(
        self,
        **kwargs
    ) -> ForecastParameters:
        """
        Create custom parameters with specific overrides.

        Args:
            **kwargs: Parameter overrides
                - tasso_crescita: Revenue growth rate
                - inflazione: Inflation rate
                - variazione_organico: Personnel change
                - investimento: Investment amount
                - etc.

        Returns:
            ForecastParameters with overrides
        """
        params = deepcopy(self.base_params)

        # Revenue overrides
        if "tasso_crescita" in kwargs:
            params.revenue.tasso_crescita = kwargs["tasso_crescita"]
        if "growth_mode" in kwargs:
            params.revenue.growth_mode = GrowthMode(kwargs["growth_mode"])

        # Macro overrides
        if "inflazione" in kwargs:
            params.macro.inflazione = kwargs["inflazione"]
        if "tasso_crescita_settore" in kwargs:
            params.macro.tasso_crescita_settore = kwargs["tasso_crescita_settore"]
        if "costo_denaro" in kwargs:
            params.macro.costo_denaro = kwargs["costo_denaro"]
        if "aliquota_imposte" in kwargs:
            params.macro.aliquota_imposte = kwargs["aliquota_imposte"]

        # Cost overrides
        if "perc_costi_variabili" in kwargs:
            params.costs.perc_costi_variabili = kwargs["perc_costi_variabili"]
        if "variazione_materie" in kwargs:
            params.costs.variazione_materie = kwargs["variazione_materie"]
        if "variazione_servizi" in kwargs:
            params.costs.variazione_servizi = kwargs["variazione_servizi"]

        # Personnel overrides
        if "n_dipendenti" in kwargs:
            params.personnel.n_dipendenti_attuali = kwargs["n_dipendenti"]
        if "variazione_organico" in kwargs:
            params.personnel.variazione_organico = kwargs["variazione_organico"]
        if "aumento_salariale" in kwargs:
            params.personnel.aumento_salariale = kwargs["aumento_salariale"]
        if "salario_medio" in kwargs:
            params.personnel.salario_medio = kwargs["salario_medio"]

        # Working capital overrides
        if "dso" in kwargs:
            params.working_capital.dso = kwargs["dso"]
        if "dpo" in kwargs:
            params.working_capital.dpo = kwargs["dpo"]
        if "doh" in kwargs:
            params.working_capital.doh = kwargs["doh"]

        # Investment overrides
        if "investimento" in kwargs:
            params.investment.investimento_totale = kwargs["investimento"]
        if "anno_investimento" in kwargs:
            params.investment.anno_investimento = kwargs["anno_investimento"]
        if "vita_utile" in kwargs:
            params.investment.vita_utile = kwargs["vita_utile"]

        # Financial overrides
        if "tasso_interesse_debito" in kwargs:
            params.financial.tasso_interesse_debito = kwargs["tasso_interesse_debito"]

        # Horizon override
        if "orizzonte_anni" in kwargs:
            params.orizzonte_anni = kwargs["orizzonte_anni"]

        return params

    def validate_parameters(
        self,
        params: ForecastParameters
    ) -> List[str]:
        """
        Validate parameters for reasonableness.

        Args:
            params: Parameters to validate

        Returns:
            List of validation warnings
        """
        warnings = []

        # Revenue validation
        if params.revenue.tasso_crescita > 0.50:
            warnings.append(
                f"Tasso crescita ricavi molto alto ({params.revenue.tasso_crescita:.1%})"
            )
        elif params.revenue.tasso_crescita < -0.30:
            warnings.append(
                f"Tasso crescita ricavi molto negativo ({params.revenue.tasso_crescita:.1%})"
            )

        # Inflation validation
        if params.macro.inflazione > 0.20:
            warnings.append(
                f"Inflazione molto alta ({params.macro.inflazione:.1%})"
            )
        elif params.macro.inflazione < 0:
            warnings.append(
                f"Inflazione negativa (deflazione: {params.macro.inflazione:.1%})"
            )

        # Personnel validation
        n_dipendenti = params.personnel.n_dipendenti_attuali + params.personnel.variazione_organico
        if n_dipendenti <= 0:
            warnings.append(
                f"Numero dipendenti risultante <= 0 ({n_dipendenti})"
            )

        # Investment validation
        if params.investment.investimento_totale > 0:
            if params.investment.vita_utile <= 0:
                warnings.append("Vita utile investimento deve essere > 0")
            if params.investment.anno_investimento > params.orizzonte_anni:
                warnings.append(
                    f"Anno investimento ({params.investment.anno_investimento}) "
                    f"oltre orizzonte previsione ({params.orizzonte_anni})"
                )

        # Working capital validation
        if params.working_capital.dso > 180:
            warnings.append(
                f"DSO molto alto ({params.working_capital.dso} giorni)"
            )
        if params.working_capital.dpo > 180:
            warnings.append(
                f"DPO molto alto ({params.working_capital.dpo} giorni)"
            )

        return warnings

    def get_all_scenario_parameters(self) -> Dict[ScenarioType, ForecastParameters]:
        """
        Get parameters for all predefined scenarios.

        Returns:
            Dict mapping ScenarioType to ForecastParameters
        """
        return {
            scenario_type: self.get_parameters_for_scenario(scenario_type)
            for scenario_type in [
                ScenarioType.BASE,
                ScenarioType.OTTIMISTICO,
                ScenarioType.PESSIMISTICO
            ]
        }

    def get_parameters_summary(
        self,
        params: ForecastParameters
    ) -> Dict[str, Any]:
        """
        Get human-readable summary of parameters.

        Args:
            params: Parameters to summarize

        Returns:
            Summary dict
        """
        return {
            "orizzonte": {
                "anno_base": params.anno_base,
                "anni_previsione": params.get_anni_previsione(),
            },
            "ricavi": {
                "tasso_crescita": f"{params.revenue.tasso_crescita:.1%}",
                "modalita": params.revenue.growth_mode.value,
            },
            "macro": {
                "inflazione": f"{params.macro.inflazione:.1%}",
                "costo_denaro": f"{params.macro.costo_denaro:.1%}",
                "aliquota_imposte": f"{params.macro.aliquota_imposte:.1%}",
            },
            "personale": {
                "dipendenti_attuali": params.personnel.n_dipendenti_attuali,
                "variazione": params.personnel.variazione_organico,
                "aumento_salariale": f"{params.personnel.aumento_salariale:.1%}",
            },
            "capitale_circolante": {
                "dso": f"{params.working_capital.dso:.0f} giorni",
                "dpo": f"{params.working_capital.dpo:.0f} giorni",
                "doh": f"{params.working_capital.doh:.0f} giorni",
            },
            "investimento": {
                "importo": f"€{params.investment.investimento_totale:,.0f}",
                "anno": params.investment.anno_investimento,
                "vita_utile": f"{params.investment.vita_utile} anni",
            } if params.investment.investimento_totale > 0 else None,
        }

    @staticmethod
    def get_default_parameters() -> ForecastParameters:
        """Get default parameters without historical data"""
        return ForecastParameters(
            anno_base=2024,
            orizzonte_anni=3,
            macro=MacroParameters(
                inflazione=0.02,
                inflazione_materie=0.03,
                tasso_crescita_settore=0.02,
                costo_denaro=0.04,
                aliquota_imposte=0.24,
            ),
            revenue=RevenueParameters(
                tasso_crescita=0.05,
                growth_mode=GrowthMode.GEOMETRIC,
                use_cagr_storico=False,
            ),
            costs=CostParameters(
                perc_costi_variabili=0.60,
            ),
            personnel=PersonnelParameters(
                n_dipendenti_attuali=10,
                aumento_salariale=0.02,
                salario_medio=35000,
            ),
            working_capital=WorkingCapitalParameters(
                dso=60,
                dpo=45,
                doh=30,
            ),
        )
