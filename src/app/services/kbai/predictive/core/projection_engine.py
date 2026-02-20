"""
Projection Engine - STEP 3-4

Main engine for generating financial projections.
Calculates projected Conto Economico and Stato Patrimoniale for 1-3 years.

Reference: STEP 3-4 from mappa_logica_previsione.md
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy

from ..models.balance_sheet import BalanceSheetData
from ..models.parameters import ForecastParameters, GrowthMode
from ..models.scenario import ScenarioType, ScenarioResult, ScenarioModifiers
from .formula_library import (
    calcola_ricavi,
    calcola_costi_variabili,
    calcola_costi_fissi,
    calcola_materie_prime,
    calcola_servizi,
    calcola_personale,
    calcola_tfr,
    calcola_ammortamenti,
    calcola_ebitda,
    calcola_ebit,
    calcola_utile_ante_imposte,
    calcola_utile_netto,
    calcola_interessi_passivi,
    calcola_crediti,
    calcola_magazzino,
    calcola_debiti_fornitori,
    calcola_capitale_circolante,
)
from .kpi_calculator import KPICalculator
from .historical_analyzer import HistoricalAnalyzer


@dataclass
class YearProjection:
    """Proiezione per un singolo anno"""
    year: int

    # Conto Economico
    ricavi: float = 0.0
    altri_ricavi: float = 0.0
    materie_prime: float = 0.0
    servizi: float = 0.0
    godimento_terzi: float = 0.0
    personale: float = 0.0
    salari: float = 0.0
    oneri_sociali: float = 0.0
    tfr: float = 0.0
    ammortamenti: float = 0.0
    accantonamenti: float = 0.0
    oneri_diversi: float = 0.0
    interessi_passivi: float = 0.0

    # Risultati intermedi
    ebitda: float = 0.0
    ebit: float = 0.0
    utile_ante_imposte: float = 0.0
    imposte: float = 0.0
    utile_netto: float = 0.0

    # Stato Patrimoniale (semplificato)
    immobilizzazioni: float = 0.0
    crediti: float = 0.0
    magazzino: float = 0.0
    liquidita: float = 0.0
    patrimonio_netto: float = 0.0
    debiti_finanziari: float = 0.0
    debiti_fornitori: float = 0.0
    tfr_fondo: float = 0.0

    # Capitale circolante
    ccn: float = 0.0  # Capitale Circolante Netto

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "conto_economico": {
                "ricavi": round(self.ricavi, 2),
                "altri_ricavi": round(self.altri_ricavi, 2),
                "materie_prime": round(self.materie_prime, 2),
                "servizi": round(self.servizi, 2),
                "godimento_terzi": round(self.godimento_terzi, 2),
                "personale": round(self.personale, 2),
                "ammortamenti": round(self.ammortamenti, 2),
                "accantonamenti": round(self.accantonamenti, 2),
                "oneri_diversi": round(self.oneri_diversi, 2),
                "interessi_passivi": round(self.interessi_passivi, 2),
                "ebitda": round(self.ebitda, 2),
                "ebit": round(self.ebit, 2),
                "utile_ante_imposte": round(self.utile_ante_imposte, 2),
                "imposte": round(self.imposte, 2),
                "utile_netto": round(self.utile_netto, 2),
            },
            "stato_patrimoniale": {
                "immobilizzazioni": round(self.immobilizzazioni, 2),
                "crediti": round(self.crediti, 2),
                "magazzino": round(self.magazzino, 2),
                "liquidita": round(self.liquidita, 2),
                "totale_attivo": round(
                    self.immobilizzazioni + self.crediti + self.magazzino + self.liquidita, 2
                ),
                "patrimonio_netto": round(self.patrimonio_netto, 2),
                "debiti_finanziari": round(self.debiti_finanziari, 2),
                "debiti_fornitori": round(self.debiti_fornitori, 2),
                "tfr_fondo": round(self.tfr_fondo, 2),
            },
            "capitale_circolante": round(self.ccn, 2),
        }

    @property
    def totale_attivo(self) -> float:
        return self.immobilizzazioni + self.crediti + self.magazzino + self.liquidita

    @property
    def costi_variabili(self) -> float:
        return self.materie_prime + self.servizi + self.godimento_terzi


class ProjectionEngine:
    """
    Main engine for generating financial projections.
    Implements STEP 3-4 logic from CFO requirements.
    """

    def __init__(
        self,
        historical_analyzer: HistoricalAnalyzer,
        base_values: Optional[Dict[str, float]] = None
    ):
        """
        Args:
            historical_analyzer: Analyzer with historical data
            base_values: Override base values (if None, uses from historical)
        """
        self.historical = historical_analyzer
        self.base_values = base_values or historical_analyzer.get_base_values()
        self.kpi_calculator = KPICalculator()
        self._warnings: List[str] = []

    @property
    def warnings(self) -> List[str]:
        return self._warnings

    def run_scenario(
        self,
        scenario: object # Scenario dataclass
    ) -> ScenarioResult:
        """
        Generate projections for a given scenario.

        Args:
            scenario: Configured Scenario object

        Returns:
            ScenarioResult with projections and KPIs
        """
        params = scenario.parameters
        scenario_name = scenario.name
        
        # Extract modifiers from params if available (set by Parameterizer)
        modifiers_data = params.custom_overrides.get("modifiers_applied")
        if modifiers_data:
            modifiers = ScenarioModifiers.from_dict(modifiers_data)
        else:
            modifiers = ScenarioModifiers(name=scenario_name)

        # Determine scenario type from name
        scenario_type = ScenarioType.BASE
        name_lower = scenario_name.lower()
        if "ottimis" in name_lower:
            scenario_type = ScenarioType.OTTIMISTICO
        elif "pessimis" in name_lower:
            scenario_type = ScenarioType.PESSIMISTICO

        result = ScenarioResult(
            scenario_type=scenario_type,
            scenario_name=scenario_name,
            modifiers=modifiers
        )

        # Get previous year values (start from base)
        prev_projection = self._create_base_projection()

        # Project each year
        for i, year in enumerate(params.get_anni_previsione()):
            anno_n = i + 1  # 1, 2, 3

            projection = self._project_year(
                anno_n=anno_n,
                year=year,
                params=params,
                prev_projection=prev_projection
            )

            # Calculate KPIs for this year
            kpis = self._calculate_kpis(projection)

            # Store results
            # Updated to use new list/dict structure in ScenarioResult
            result.projections.append(projection) # Store full object or dict, let's store object for now as service converts it
            result.kpis[year] = kpis

            # Update previous for next iteration
            prev_projection = projection

        result.warnings = self._warnings.copy()
        return result

    def _create_base_projection(self) -> YearProjection:
        """Create projection from base values (year 0)"""
        base = self.base_values
        return YearProjection(
            year=base.get("anno_base", 2024),
            ricavi=base.get("ricavi", 0),
            altri_ricavi=base.get("altri_ricavi", 0),
            materie_prime=base.get("materie_prime", 0),
            servizi=base.get("servizi", 0),
            godimento_terzi=base.get("godimento_terzi", 0),
            personale=base.get("personale", 0),
            ammortamenti=base.get("ammortamenti", 0),
            accantonamenti=base.get("accantonamenti", 0),
            oneri_diversi=base.get("oneri_diversi", 0),
            interessi_passivi=base.get("interessi_passivi", 0),
            ebitda=base.get("ebitda", 0),
            ebit=base.get("ebit", 0),
            utile_netto=base.get("utile_netto", 0),
            immobilizzazioni=base.get("immobilizzazioni", 0),
            crediti=base.get("crediti", 0),
            magazzino=base.get("magazzino", 0),
            liquidita=base.get("liquidita", 0),
            patrimonio_netto=base.get("patrimonio_netto", 0),
            debiti_finanziari=base.get("debiti_finanziari", 0),
            debiti_fornitori=base.get("debiti_fornitori", 0),
            tfr_fondo=base.get("tfr", 0),
        )

    def _project_year(
        self,
        anno_n: int,
        year: int,
        params: ForecastParameters,
        prev_projection: YearProjection
    ) -> YearProjection:
        """
        Project a single year.

        Args:
            anno_n: Year number (1, 2, 3)
            year: Actual year (e.g., 2025)
            params: Forecast parameters
            prev_projection: Previous year projection

        Returns:
            YearProjection for the year
        """
        proj = YearProjection(year=year)
        base = self.base_values

        # ====================================================================
        # RICAVI
        # ====================================================================
        growth_mode = (
            "geometric" if params.revenue.growth_mode == GrowthMode.GEOMETRIC
            else "constant"
        )
        proj.ricavi = calcola_ricavi(
            ricavi_base=base.get("ricavi", 0),
            tasso_crescita=params.revenue.tasso_crescita,
            anno_n=anno_n,
            growth_mode=growth_mode
        )

        # Altri ricavi (costanti o indicizzati)
        proj.altri_ricavi = base.get("altri_ricavi", 0) * (
            1 + params.macro.inflazione
        ) ** anno_n

        # ====================================================================
        # COSTI VARIABILI
        # ====================================================================
        # Percentuali storiche
        perc_materie = (
            base.get("materie_prime", 0) / base.get("ricavi", 1)
            if base.get("ricavi", 0) > 0 else 0.30
        )
        perc_servizi = (
            base.get("servizi", 0) / base.get("ricavi", 1)
            if base.get("ricavi", 0) > 0 else 0.20
        )
        perc_godimento = (
            base.get("godimento_terzi", 0) / base.get("ricavi", 1)
            if base.get("ricavi", 0) > 0 else 0.05
        )

        proj.materie_prime = calcola_materie_prime(
            ricavi=proj.ricavi,
            perc_materie=perc_materie,
            inflazione_materie=params.macro.inflazione_materie,
            variazione=params.costs.variazione_materie
        )

        proj.servizi = calcola_servizi(
            ricavi=proj.ricavi,
            perc_servizi=perc_servizi,
            inflazione=params.macro.inflazione,
            variazione=params.costs.variazione_servizi
        )

        proj.godimento_terzi = proj.ricavi * perc_godimento * (
            1 + params.macro.inflazione
        )

        # ====================================================================
        # PERSONALE
        # ====================================================================
        n_dipendenti = (
            params.personnel.n_dipendenti_attuali +
            params.personnel.variazione_organico
        )
        salario = params.personnel.salario_medio or base.get("salari", 35000)

        proj.salari, proj.oneri_sociali, proj.personale = calcola_personale(
            n_dipendenti=n_dipendenti,
            salario_medio=salario,
            aumento_salariale=params.personnel.aumento_salariale,
            anno_n=anno_n,
            aliquota_oneri=params.personnel.aliquota_oneri
        )

        proj.tfr = calcola_tfr(
            costo_personale=proj.salari,
            aliquota_tfr=params.personnel.aliquota_tfr
        )

        # ====================================================================
        # AMMORTAMENTI
        # ====================================================================
        proj.ammortamenti = calcola_ammortamenti(
            ammortamenti_storici=base.get("ammortamenti", 0),
            investimento=params.investment.investimento_totale,
            vita_utile=params.investment.vita_utile,
            anno_investimento=params.investment.anno_investimento,
            anno_corrente=anno_n
        )

        # ====================================================================
        # ALTRI COSTI
        # ====================================================================
        proj.accantonamenti = base.get("accantonamenti", 0) * (
            1 + params.macro.inflazione
        ) ** anno_n

        proj.oneri_diversi = calcola_costi_fissi(
            costi_fissi_base=base.get("oneri_diversi", 0),
            anno_n=anno_n,
            inflazione=params.macro.inflazione,
            variazione_aggiuntiva=params.costs.variazione_oneri_diversi
        )

        # ====================================================================
        # RISULTATI CE
        # ====================================================================
        proj.ebitda = calcola_ebitda(
            ricavi=proj.ricavi,
            costi_variabili=proj.costi_variabili,
            costo_personale=proj.personale,
            altri_ricavi=proj.altri_ricavi
        )

        proj.ebit = calcola_ebit(
            ebitda=proj.ebitda,
            ammortamenti=proj.ammortamenti,
            accantonamenti=proj.accantonamenti,
            oneri_diversi=proj.oneri_diversi
        )

        # Interessi passivi
        proj.interessi_passivi = calcola_interessi_passivi(
            debiti_finanziari=prev_projection.debiti_finanziari,
            tasso_interesse=params.financial.tasso_interesse_debito
        )

        proj.utile_ante_imposte = calcola_utile_ante_imposte(
            ebit=proj.ebit,
            oneri_finanziari=proj.interessi_passivi
        )

        proj.imposte = (
            proj.utile_ante_imposte * params.macro.aliquota_imposte
            if proj.utile_ante_imposte > 0 else 0
        )

        proj.utile_netto = proj.utile_ante_imposte - proj.imposte

        # ====================================================================
        # STATO PATRIMONIALE
        # ====================================================================
        # Immobilizzazioni
        proj.immobilizzazioni = (
            prev_projection.immobilizzazioni -
            proj.ammortamenti +
            (params.investment.investimento_totale
             if anno_n == params.investment.anno_investimento else 0)
        )

        # Capitale circolante
        proj.crediti = calcola_crediti(
            ricavi=proj.ricavi,
            dso=params.working_capital.dso
        )

        proj.magazzino = calcola_magazzino(
            costi_diretti=proj.materie_prime,
            doh=params.working_capital.doh
        )

        proj.debiti_fornitori = calcola_debiti_fornitori(
            costi_diretti=proj.materie_prime + proj.servizi,
            dpo=params.working_capital.dpo
        )

        proj.ccn = calcola_capitale_circolante(
            crediti=proj.crediti,
            magazzino=proj.magazzino,
            debiti_fornitori=proj.debiti_fornitori
        )

        # Debiti finanziari (per ora costanti)
        proj.debiti_finanziari = prev_projection.debiti_finanziari * (
            1 + params.financial.variazione_debito_finanziario
        )

        # TFR fondo
        proj.tfr_fondo = prev_projection.tfr_fondo + proj.tfr

        # Patrimonio netto
        dividendi = proj.utile_netto * params.financial.distribuzione_dividendi
        proj.patrimonio_netto = (
            prev_projection.patrimonio_netto +
            proj.utile_netto -
            dividendi
        )

        # Liquidità (residuale per quadratura semplificata)
        proj.liquidita = max(0, (
            proj.patrimonio_netto +
            proj.debiti_finanziari +
            proj.debiti_fornitori +
            proj.tfr_fondo -
            proj.immobilizzazioni -
            proj.crediti -
            proj.magazzino
        ))

        return proj

    def _calculate_kpis(self, projection: YearProjection) -> Dict[str, float]:
        """Calculate KPIs for a projection"""
        kpis = self.kpi_calculator.calculate_all_kpis(
            ricavi=projection.ricavi,
            ebitda=projection.ebitda,
            ebit=projection.ebit,
            utile_netto=projection.utile_netto,
            patrimonio_netto=projection.patrimonio_netto,
            totale_attivo=projection.totale_attivo,
            debiti_finanziari=projection.debiti_finanziari,
            costi_variabili=projection.costi_variabili,
            attivo_circolante=projection.crediti + projection.magazzino + projection.liquidita,
            passivo_corrente=projection.debiti_fornitori,
            immobilizzazioni=projection.immobilizzazioni,
            ccn=projection.ccn,
            totale_debiti=projection.debiti_finanziari + projection.debiti_fornitori,
        )

        return self.kpi_calculator.kpis_to_dict(kpis, include_details=False)

    def project_all_scenarios(
        self,
        base_params: ForecastParameters,
        scenario_params: Dict[ScenarioType, ForecastParameters]
    ) -> Dict[str, ScenarioResult]:
        """
        Project all scenarios.

        Args:
            base_params: Base parameters
            scenario_params: Dict of scenario type to parameters

        Returns:
            Dict of scenario name to results
        """
        results = {}

        for scenario_type, params in scenario_params.items():
            scenario_name = scenario_type.value.capitalize()
            result = self.project(params, scenario_name=scenario_name)
            result.scenario_type = scenario_type
            results[scenario_name] = result

        return results

    def compare_scenarios(
        self,
        results: Dict[str, ScenarioResult]
    ) -> Dict[str, Any]:
        """
        Compare results across scenarios.

        Args:
            results: Dict of scenario results

        Returns:
            Comparison analysis
        """
        if "Base" not in results:
            return {}

        base = results["Base"]
        comparison = {}

        # Get final year
        final_year = max(base.previsioni.keys())

        for scenario_name, scenario_result in results.items():
            if scenario_name == "Base":
                continue

            scenario_final = scenario_result.previsioni.get(final_year, {})
            base_final = base.previsioni.get(final_year, {})

            comparison[f"Base_vs_{scenario_name}"] = {
                "delta_ricavi": (
                    scenario_final.get("conto_economico", {}).get("ricavi", 0) -
                    base_final.get("conto_economico", {}).get("ricavi", 0)
                ),
                "delta_ebitda": (
                    scenario_final.get("conto_economico", {}).get("ebitda", 0) -
                    base_final.get("conto_economico", {}).get("ebitda", 0)
                ),
                "delta_utile": (
                    scenario_final.get("conto_economico", {}).get("utile_netto", 0) -
                    base_final.get("conto_economico", {}).get("utile_netto", 0)
                ),
                "delta_patrimonio": (
                    scenario_final.get("stato_patrimoniale", {}).get("patrimonio_netto", 0) -
                    base_final.get("stato_patrimoniale", {}).get("patrimonio_netto", 0)
                ),
            }

        return {
            "anno_confronto": final_year,
            "confronti": comparison
        }
