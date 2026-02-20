"""
KPI Calculator

Calculates financial KPIs:
- ROI (Return on Investment)
- ROE (Return on Equity)
- ROS (Return on Sales)
- EBITDA Margin
- Leverage
- Other profitability and solvency ratios

Reference: STEP 5 from mappa_logica_previsione.md
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class KPIResult:
    """Risultato calcolo KPI con metadata"""
    value: float
    unit: str  # "%" o "ratio" o "€"
    description: str
    formula: str
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "value": round(self.value, 4),
            "unit": self.unit,
            "description": self.description,
            "formula": self.formula,
        }
        if self.warning:
            result["warning"] = self.warning
        return result


class KPICalculator:
    """
    Calculator for financial KPIs.
    All calculations are deterministic and traceable.
    """

    def __init__(self):
        self._warnings: list = []

    @property
    def warnings(self) -> list:
        return self._warnings

    # ========================================================================
    # PROFITABILITY RATIOS (Indici di Redditività)
    # ========================================================================

    def calcola_roi(
        self,
        ebit: float,
        totale_attivo: float,
        capitale_circolante_netto: Optional[float] = None,
        immobilizzazioni: Optional[float] = None
    ) -> KPIResult:
        """
        Calcola ROI (Return on Investment).

        Formula standard:
            ROI = EBIT / Totale Attivo

        Formula alternativa (Capitale Investito):
            ROI = EBIT / (Immobilizzazioni + CCN)

        Args:
            ebit: EBIT (Reddito Operativo)
            totale_attivo: Totale Attivo di bilancio
            capitale_circolante_netto: CCN (opzionale per formula alternativa)
            immobilizzazioni: Immobilizzazioni (opzionale per formula alternativa)

        Returns:
            KPIResult con ROI
        """
        warning = None

        # Usa formula alternativa se disponibile
        if capitale_circolante_netto is not None and immobilizzazioni is not None:
            capitale_investito = immobilizzazioni + capitale_circolante_netto
            if capitale_investito > 0:
                roi = ebit / capitale_investito
                formula = "EBIT / (Immobilizzazioni + CCN)"
            else:
                roi = 0.0
                warning = "Capitale investito <= 0"
                formula = "N/A"
        else:
            # Formula standard
            if totale_attivo > 0:
                roi = ebit / totale_attivo
                formula = "EBIT / Totale Attivo"
            else:
                roi = 0.0
                warning = "Totale attivo <= 0"
                formula = "N/A"

        # Warning per valori anomali
        if roi < 0:
            warning = "ROI negativo - l'azienda genera perdite operative"
        elif roi > 0.50:
            warning = "ROI molto alto (>50%) - verificare dati"

        return KPIResult(
            value=roi,
            unit="%",
            description="Return on Investment - Rendimento del capitale investito",
            formula=formula,
            warning=warning
        )

    def calcola_roe(
        self,
        utile_netto: float,
        patrimonio_netto: float
    ) -> KPIResult:
        """
        Calcola ROE (Return on Equity).

        Formula:
            ROE = Utile Netto / Patrimonio Netto

        Args:
            utile_netto: Utile netto dell'esercizio
            patrimonio_netto: Patrimonio netto

        Returns:
            KPIResult con ROE
        """
        warning = None

        if patrimonio_netto > 0:
            roe = utile_netto / patrimonio_netto
            formula = "Utile Netto / Patrimonio Netto"
        elif patrimonio_netto < 0:
            roe = 0.0
            warning = "Patrimonio netto negativo - deficit patrimoniale"
            formula = "N/A"
        else:
            roe = 0.0
            warning = "Patrimonio netto = 0"
            formula = "N/A"

        if roe < 0 and not warning:
            warning = "ROE negativo - l'azienda genera perdite"
        elif roe > 0.40:
            warning = "ROE molto alto (>40%) - verificare dati"

        return KPIResult(
            value=roe,
            unit="%",
            description="Return on Equity - Rendimento del capitale proprio",
            formula=formula,
            warning=warning
        )

    def calcola_ros(
        self,
        utile_netto: float,
        ricavi: float
    ) -> KPIResult:
        """
        Calcola ROS (Return on Sales).

        Formula:
            ROS = Utile Netto / Ricavi

        Args:
            utile_netto: Utile netto dell'esercizio
            ricavi: Ricavi totali

        Returns:
            KPIResult con ROS
        """
        warning = None

        if ricavi > 0:
            ros = utile_netto / ricavi
            formula = "Utile Netto / Ricavi"
        else:
            ros = 0.0
            warning = "Ricavi <= 0"
            formula = "N/A"

        if ros < 0 and not warning:
            warning = "ROS negativo - margine netto in perdita"

        return KPIResult(
            value=ros,
            unit="%",
            description="Return on Sales - Margine netto sulle vendite",
            formula=formula,
            warning=warning
        )

    def calcola_ebitda_margin(
        self,
        ebitda: float,
        ricavi: float
    ) -> KPIResult:
        """
        Calcola EBITDA Margin.

        Formula:
            EBITDA Margin = EBITDA / Ricavi

        Args:
            ebitda: EBITDA
            ricavi: Ricavi totali

        Returns:
            KPIResult con EBITDA Margin
        """
        warning = None

        if ricavi > 0:
            margin = ebitda / ricavi
            formula = "EBITDA / Ricavi"
        else:
            margin = 0.0
            warning = "Ricavi <= 0"
            formula = "N/A"

        if margin < 0.05 and not warning:
            warning = "EBITDA Margin basso (<5%) - margine operativo compresso"
        elif margin > 0.40:
            warning = "EBITDA Margin molto alto (>40%) - verificare dati"

        return KPIResult(
            value=margin,
            unit="%",
            description="EBITDA Margin - Margine operativo lordo",
            formula=formula,
            warning=warning
        )

    def calcola_mdc(
        self,
        ricavi: float,
        costi_variabili: float
    ) -> KPIResult:
        """
        Calcola Margine di Contribuzione %.

        Formula:
            MdC % = (Ricavi - Costi Variabili) / Ricavi

        Args:
            ricavi: Ricavi totali
            costi_variabili: Costi variabili totali

        Returns:
            KPIResult con MdC %
        """
        warning = None

        if ricavi > 0:
            mdc = (ricavi - costi_variabili) / ricavi
            formula = "(Ricavi - Costi Variabili) / Ricavi"
        else:
            mdc = 0.0
            warning = "Ricavi <= 0"
            formula = "N/A"

        if mdc < 0.20 and not warning:
            warning = "MdC basso (<20%) - margine di contribuzione ridotto"

        return KPIResult(
            value=mdc,
            unit="%",
            description="Margine di Contribuzione - Copertura costi fissi",
            formula=formula,
            warning=warning
        )

    # ========================================================================
    # LEVERAGE & SOLVENCY RATIOS (Indici di Solvibilità)
    # ========================================================================

    def calcola_leverage(
        self,
        debiti_finanziari: float,
        patrimonio_netto: float
    ) -> KPIResult:
        """
        Calcola Leverage (Debt to Equity).

        Formula:
            Leverage = Debiti Finanziari / Patrimonio Netto

        Args:
            debiti_finanziari: Debiti verso banche
            patrimonio_netto: Patrimonio netto

        Returns:
            KPIResult con Leverage
        """
        warning = None

        if patrimonio_netto > 0:
            leverage = debiti_finanziari / patrimonio_netto
            formula = "Debiti Finanziari / Patrimonio Netto"
        elif patrimonio_netto < 0:
            leverage = float('inf')
            warning = "Patrimonio netto negativo - deficit patrimoniale grave"
            formula = "N/A"
        else:
            leverage = float('inf') if debiti_finanziari > 0 else 0.0
            warning = "Patrimonio netto = 0"
            formula = "N/A"

        if leverage > 3.0 and not warning:
            warning = "Leverage alto (>3) - elevato indebitamento"
        elif leverage > 5.0:
            warning = "Leverage molto alto (>5) - rischio solvibilità"

        return KPIResult(
            value=leverage if leverage != float('inf') else 999.99,
            unit="ratio",
            description="Leverage - Rapporto debiti/equity",
            formula=formula,
            warning=warning
        )

    def calcola_indice_indebitamento(
        self,
        totale_debiti: float,
        totale_attivo: float
    ) -> KPIResult:
        """
        Calcola Indice di Indebitamento.

        Formula:
            Indice Indebitamento = Totale Debiti / Totale Attivo

        Args:
            totale_debiti: Totale debiti
            totale_attivo: Totale attivo

        Returns:
            KPIResult con Indice Indebitamento
        """
        warning = None

        if totale_attivo > 0:
            indice = totale_debiti / totale_attivo
            formula = "Totale Debiti / Totale Attivo"
        else:
            indice = 0.0
            warning = "Totale attivo <= 0"
            formula = "N/A"

        if indice > 0.80 and not warning:
            warning = "Indice indebitamento alto (>80%) - struttura finanziaria debole"

        return KPIResult(
            value=indice,
            unit="%",
            description="Indice di Indebitamento - Peso debiti su attivo",
            formula=formula,
            warning=warning
        )

    # ========================================================================
    # LIQUIDITY RATIOS (Indici di Liquidità)
    # ========================================================================

    def calcola_current_ratio(
        self,
        attivo_circolante: float,
        passivo_corrente: float
    ) -> KPIResult:
        """
        Calcola Current Ratio.

        Formula:
            Current Ratio = Attivo Circolante / Passivo Corrente

        Args:
            attivo_circolante: Totale attivo circolante
            passivo_corrente: Debiti a breve termine

        Returns:
            KPIResult con Current Ratio
        """
        warning = None

        if passivo_corrente > 0:
            ratio = attivo_circolante / passivo_corrente
            formula = "Attivo Circolante / Passivo Corrente"
        else:
            ratio = float('inf') if attivo_circolante > 0 else 0.0
            warning = "Passivo corrente = 0"
            formula = "N/A"

        if ratio < 1.0 and not warning:
            warning = "Current Ratio < 1 - possibili tensioni di liquidità"
        elif ratio > 3.0:
            warning = "Current Ratio molto alto (>3) - possibile inefficienza"

        return KPIResult(
            value=ratio if ratio != float('inf') else 999.99,
            unit="ratio",
            description="Current Ratio - Liquidità corrente",
            formula=formula,
            warning=warning
        )

    # ========================================================================
    # AGGREGATE CALCULATION
    # ========================================================================

    def calculate_all_kpis(
        self,
        ricavi: float,
        ebitda: float,
        ebit: float,
        utile_netto: float,
        patrimonio_netto: float,
        totale_attivo: float,
        debiti_finanziari: float,
        costi_variabili: float,
        attivo_circolante: Optional[float] = None,
        passivo_corrente: Optional[float] = None,
        immobilizzazioni: Optional[float] = None,
        ccn: Optional[float] = None,
        totale_debiti: Optional[float] = None,
    ) -> Dict[str, KPIResult]:
        """
        Calcola tutti i KPI principali.

        Returns:
            Dict con tutti i KPI calcolati
        """
        kpis = {}

        # Profitability
        kpis["ROI"] = self.calcola_roi(
            ebit, totale_attivo, ccn, immobilizzazioni
        )
        kpis["ROE"] = self.calcola_roe(utile_netto, patrimonio_netto)
        kpis["ROS"] = self.calcola_ros(utile_netto, ricavi)
        kpis["EBITDA_Margin"] = self.calcola_ebitda_margin(ebitda, ricavi)
        kpis["MdC"] = self.calcola_mdc(ricavi, costi_variabili)

        # Leverage
        kpis["Leverage"] = self.calcola_leverage(debiti_finanziari, patrimonio_netto)

        if totale_debiti is not None:
            kpis["Indice_Indebitamento"] = self.calcola_indice_indebitamento(
                totale_debiti, totale_attivo
            )

        # Liquidity
        if attivo_circolante is not None and passivo_corrente is not None:
            kpis["Current_Ratio"] = self.calcola_current_ratio(
                attivo_circolante, passivo_corrente
            )

        return kpis

    def kpis_to_dict(
        self,
        kpis: Dict[str, KPIResult],
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Converte KPI results in dizionario.

        Args:
            kpis: Dict di KPIResult
            include_details: Se includere descrizione e formula

        Returns:
            Dict con valori KPI
        """
        if include_details:
            return {name: result.to_dict() for name, result in kpis.items()}
        else:
            return {name: result.value for name, result in kpis.items()}

    def get_kpi_summary(
        self,
        kpis: Dict[str, KPIResult]
    ) -> Dict[str, Any]:
        """
        Genera summary dei KPI con valutazioni.

        Returns:
            Summary con valutazioni qualitative
        """
        summary = {
            "valori": self.kpis_to_dict(kpis, include_details=False),
            "warnings": [],
            "valutazioni": {},
        }

        # Raccogli warnings
        for name, result in kpis.items():
            if result.warning:
                summary["warnings"].append(f"{name}: {result.warning}")

        # Valutazioni qualitative
        if "ROI" in kpis:
            roi = kpis["ROI"].value
            if roi > 0.15:
                summary["valutazioni"]["redditivita_investimenti"] = "alta"
            elif roi > 0.08:
                summary["valutazioni"]["redditivita_investimenti"] = "media"
            else:
                summary["valutazioni"]["redditivita_investimenti"] = "bassa"

        if "Leverage" in kpis:
            leverage = kpis["Leverage"].value
            if leverage < 1.0:
                summary["valutazioni"]["struttura_finanziaria"] = "solida"
            elif leverage < 3.0:
                summary["valutazioni"]["struttura_finanziaria"] = "equilibrata"
            else:
                summary["valutazioni"]["struttura_finanziaria"] = "rischiosa"

        if "EBITDA_Margin" in kpis:
            margin = kpis["EBITDA_Margin"].value
            if margin > 0.15:
                summary["valutazioni"]["margine_operativo"] = "alto"
            elif margin > 0.08:
                summary["valutazioni"]["margine_operativo"] = "medio"
            else:
                summary["valutazioni"]["margine_operativo"] = "basso"

        return summary
