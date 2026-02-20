"""
Historical Analyzer - STEP 1

Analyzes historical balance sheets to calculate:
- CAGR (Compound Annual Growth Rate) for revenues
- Historical trends and averages
- Base ratios for projections

Reference: STEP 1 from mappa_logica_previsione.md
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from ..models.balance_sheet import BalanceSheetData
from .formula_library import (
    calcola_cagr,
    calcola_media,
    calcola_percentuale_su_ricavi,
    calcola_variazione_percentuale,
)


@dataclass
class HistoricalMetrics:
    """Metriche storiche calcolate dall'analisi"""
    # CAGR
    cagr_ricavi: float = 0.0
    cagr_ebitda: float = 0.0
    cagr_utile: float = 0.0

    # Medie storiche
    ros_medio: float = 0.0  # Return on Sales (Utile/Ricavi)
    ebitda_margin_medio: float = 0.0  # EBITDA/Ricavi
    mdc_medio: float = 0.0  # Margine di contribuzione medio

    # Percentuali medie su ricavi
    perc_materie_prime: float = 0.0
    perc_servizi: float = 0.0
    perc_godimento_terzi: float = 0.0
    perc_personale: float = 0.0
    perc_ammortamenti: float = 0.0
    perc_costi_variabili: float = 0.0  # Totale costi variabili

    # Capitale circolante
    dso_medio: float = 60.0  # Days Sales Outstanding
    dpo_medio: float = 45.0  # Days Payable Outstanding
    doh_medio: float = 30.0  # Days On Hand

    # Altri indicatori
    n_dipendenti_stimato: int = 0
    salario_medio_stimato: float = 0.0

    # Serie storiche raw
    anni: List[int] = field(default_factory=list)
    ricavi_storici: List[float] = field(default_factory=list)
    ebitda_storici: List[float] = field(default_factory=list)
    utile_storici: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cagr": {
                "ricavi": round(self.cagr_ricavi, 4),
                "ebitda": round(self.cagr_ebitda, 4),
                "utile": round(self.cagr_utile, 4),
            },
            "medie": {
                "ros": round(self.ros_medio, 4),
                "ebitda_margin": round(self.ebitda_margin_medio, 4),
                "mdc": round(self.mdc_medio, 4),
            },
            "percentuali_ricavi": {
                "materie_prime": round(self.perc_materie_prime, 4),
                "servizi": round(self.perc_servizi, 4),
                "godimento_terzi": round(self.perc_godimento_terzi, 4),
                "personale": round(self.perc_personale, 4),
                "ammortamenti": round(self.perc_ammortamenti, 4),
                "costi_variabili_totale": round(self.perc_costi_variabili, 4),
            },
            "capitale_circolante": {
                "dso": round(self.dso_medio, 1),
                "dpo": round(self.dpo_medio, 1),
                "doh": round(self.doh_medio, 1),
            },
            "personale": {
                "n_dipendenti_stimato": self.n_dipendenti_stimato,
                "salario_medio_stimato": round(self.salario_medio_stimato, 2),
            },
            "serie_storiche": {
                "anni": self.anni,
                "ricavi": [round(r, 2) for r in self.ricavi_storici],
                "ebitda": [round(e, 2) for e in self.ebitda_storici],
                "utile": [round(u, 2) for u in self.utile_storici],
            },
        }


class HistoricalAnalyzer:
    """
    Analizzatore storico per bilanci.
    Calcola CAGR, trend, medie e indicatori base.
    """

    def __init__(self, balances: List[BalanceSheetData]):
        """
        Args:
            balances: Lista bilanci ordinata dal più vecchio al più recente
        """
        # Ordina per anno
        self.balances = sorted(balances, key=lambda b: b.year)
        self.metrics = HistoricalMetrics()
        self._warnings: List[str] = []

    @property
    def warnings(self) -> List[str]:
        return self._warnings

    @property
    def n_years(self) -> int:
        return len(self.balances)

    @property
    def anno_base(self) -> int:
        """Anno più recente (base per proiezioni)"""
        if not self.balances:
            return 2024
        return self.balances[-1].year

    @property
    def bilancio_base(self) -> Optional[BalanceSheetData]:
        """Bilancio più recente"""
        if not self.balances:
            return None
        return self.balances[-1]

    def analyze(self) -> HistoricalMetrics:
        """
        Esegue l'analisi storica completa.

        Returns:
            HistoricalMetrics con tutti gli indicatori calcolati
        """
        if not self.balances:
            self._warnings.append("Nessun bilancio fornito per l'analisi")
            return self.metrics

        if len(self.balances) < 2:
            self._warnings.append(
                "Almeno 2 bilanci richiesti per calcolare CAGR. "
                "Verranno usati solo i valori dell'ultimo anno."
            )

        # Estrai serie storiche
        self._extract_time_series()

        # Calcola CAGR
        self._calculate_cagr()

        # Calcola medie e percentuali
        self._calculate_averages()

        # Calcola indicatori capitale circolante
        self._calculate_working_capital_metrics()

        # Stima personale
        self._estimate_personnel()

        return self.metrics

    def _extract_time_series(self):
        """Estrae le serie storiche dai bilanci"""
        self.metrics.anni = []
        self.metrics.ricavi_storici = []
        self.metrics.ebitda_storici = []
        self.metrics.utile_storici = []

        for balance in self.balances:
            self.metrics.anni.append(balance.year)

            # Ricavi totali
            ricavi = balance.conto_economico.valore_produzione.ricavi_totali
            self.metrics.ricavi_storici.append(ricavi)

            # EBITDA
            ebitda = balance.conto_economico.ebitda
            self.metrics.ebitda_storici.append(ebitda)

            # Utile netto
            utile = balance.conto_economico.utile_netto
            self.metrics.utile_storici.append(utile)

    def _calculate_cagr(self):
        """Calcola CAGR per ricavi, EBITDA e utile"""
        if len(self.balances) < 2:
            # Con un solo anno, usa tasso di crescita settore default
            self.metrics.cagr_ricavi = 0.02  # 2% default
            self.metrics.cagr_ebitda = 0.02
            self.metrics.cagr_utile = 0.02
            return

        # CAGR Ricavi
        ricavi_positivi = [r for r in self.metrics.ricavi_storici if r > 0]
        if len(ricavi_positivi) >= 2:
            self.metrics.cagr_ricavi = calcola_cagr(ricavi_positivi)
        else:
            self.metrics.cagr_ricavi = 0.02

        # CAGR EBITDA
        ebitda_positivi = [e for e in self.metrics.ebitda_storici if e > 0]
        if len(ebitda_positivi) >= 2:
            self.metrics.cagr_ebitda = calcola_cagr(ebitda_positivi)
        else:
            self.metrics.cagr_ebitda = self.metrics.cagr_ricavi

        # CAGR Utile
        utile_positivi = [u for u in self.metrics.utile_storici if u > 0]
        if len(utile_positivi) >= 2:
            self.metrics.cagr_utile = calcola_cagr(utile_positivi)
        else:
            self.metrics.cagr_utile = self.metrics.cagr_ricavi

        # Sanity check: CAGR troppo alto o troppo basso
        for cagr_name, cagr_value in [
            ("ricavi", self.metrics.cagr_ricavi),
            ("ebitda", self.metrics.cagr_ebitda),
            ("utile", self.metrics.cagr_utile),
        ]:
            if cagr_value > 0.50:  # > 50%
                self._warnings.append(
                    f"CAGR {cagr_name} molto alto ({cagr_value:.1%}). "
                    "Verificare dati storici."
                )
            elif cagr_value < -0.30:  # < -30%
                self._warnings.append(
                    f"CAGR {cagr_name} molto negativo ({cagr_value:.1%}). "
                    "Possibile trend discendente."
                )

    def _calculate_averages(self):
        """Calcola medie storiche e percentuali"""
        ros_values = []
        ebitda_margin_values = []
        mdc_values = []

        perc_materie = []
        perc_servizi = []
        perc_godimento = []
        perc_personale = []
        perc_ammortamenti = []

        for balance in self.balances:
            ricavi = balance.conto_economico.valore_produzione.ricavi_totali
            if ricavi <= 0:
                continue

            # ROS = Utile / Ricavi
            ros = balance.conto_economico.utile_netto / ricavi
            ros_values.append(ros)

            # EBITDA Margin = EBITDA / Ricavi
            ebitda_m = balance.conto_economico.ebitda / ricavi
            ebitda_margin_values.append(ebitda_m)

            # MdC = (Ricavi - Costi variabili) / Ricavi
            costi_var = balance.conto_economico.costi_produzione.costi_variabili
            mdc = (ricavi - costi_var) / ricavi
            mdc_values.append(mdc)

            # Percentuali costi su ricavi
            cp = balance.conto_economico.costi_produzione
            perc_materie.append(cp.materie_prime / ricavi if ricavi > 0 else 0)
            perc_servizi.append(cp.servizi / ricavi if ricavi > 0 else 0)
            perc_godimento.append(cp.godimento_terzi / ricavi if ricavi > 0 else 0)
            perc_personale.append(cp.personale / ricavi if ricavi > 0 else 0)
            perc_ammortamenti.append(cp.ammortamenti / ricavi if ricavi > 0 else 0)

        # Calcola medie
        self.metrics.ros_medio = calcola_media(ros_values)
        self.metrics.ebitda_margin_medio = calcola_media(ebitda_margin_values)
        self.metrics.mdc_medio = calcola_media(mdc_values)

        self.metrics.perc_materie_prime = calcola_media(perc_materie)
        self.metrics.perc_servizi = calcola_media(perc_servizi)
        self.metrics.perc_godimento_terzi = calcola_media(perc_godimento)
        self.metrics.perc_personale = calcola_media(perc_personale)
        self.metrics.perc_ammortamenti = calcola_media(perc_ammortamenti)

        # Costi variabili totali
        self.metrics.perc_costi_variabili = (
            self.metrics.perc_materie_prime +
            self.metrics.perc_servizi +
            self.metrics.perc_godimento_terzi
        )

    def _calculate_working_capital_metrics(self):
        """Calcola metriche capitale circolante (DSO, DPO, DOH)"""
        dso_values = []
        dpo_values = []
        doh_values = []

        for balance in self.balances:
            ricavi = balance.conto_economico.valore_produzione.ricavi_totali
            if ricavi <= 0:
                continue

            # DSO = Crediti / Ricavi * 365
            crediti = balance.stato_patrimoniale.attivo.circolante.crediti_commerciali
            if crediti > 0:
                dso = crediti / ricavi * 365
                dso_values.append(dso)

            # DPO = Debiti fornitori / Costi diretti * 365
            debiti_forn = balance.stato_patrimoniale.passivo.debiti_fornitori
            costi_diretti = balance.conto_economico.costi_produzione.materie_prime
            if debiti_forn > 0 and costi_diretti > 0:
                dpo = debiti_forn / costi_diretti * 365
                dpo_values.append(dpo)

            # DOH = Magazzino / Costi diretti * 365
            magazzino = balance.stato_patrimoniale.attivo.circolante.rimanenze
            if magazzino > 0 and costi_diretti > 0:
                doh = magazzino / costi_diretti * 365
                doh_values.append(doh)

        # Usa medie o default
        self.metrics.dso_medio = calcola_media(dso_values) if dso_values else 60.0
        self.metrics.dpo_medio = calcola_media(dpo_values) if dpo_values else 45.0
        self.metrics.doh_medio = calcola_media(doh_values) if doh_values else 30.0

        # Sanity check
        if self.metrics.dso_medio > 180:
            self._warnings.append(
                f"DSO medio molto alto ({self.metrics.dso_medio:.0f} giorni). "
                "Possibili problemi di incasso."
            )

    def _estimate_personnel(self):
        """Stima numero dipendenti e salario medio dall'ultimo bilancio"""
        if not self.bilancio_base:
            return

        cp = self.bilancio_base.conto_economico.costi_produzione

        # Stima numero dipendenti da TFR (approssimazione)
        # TFR annuo medio ~ 2.000 EUR per dipendente
        if cp.tfr > 0:
            self.metrics.n_dipendenti_stimato = max(1, int(cp.tfr / 2000))
        elif cp.personale > 0:
            # Stima da costo personale totale / salario medio tipico (35.000)
            self.metrics.n_dipendenti_stimato = max(1, int(cp.personale / 35000))
        else:
            self.metrics.n_dipendenti_stimato = 1

        # Salario medio
        if self.metrics.n_dipendenti_stimato > 0 and cp.salari_stipendi > 0:
            self.metrics.salario_medio_stimato = (
                cp.salari_stipendi / self.metrics.n_dipendenti_stimato
            )
        elif cp.personale > 0 and self.metrics.n_dipendenti_stimato > 0:
            # Stima: personale include oneri (~30%), quindi salario = personale / 1.3
            self.metrics.salario_medio_stimato = (
                cp.personale / self.metrics.n_dipendenti_stimato / 1.3
            )
        else:
            self.metrics.salario_medio_stimato = 35000  # Default

    def get_base_values(self) -> Dict[str, float]:
        """
        Ritorna i valori base (ultimo anno) per le proiezioni.

        Returns:
            Dict con valori base del bilancio più recente
        """
        if not self.bilancio_base:
            return {}

        balance = self.bilancio_base
        return {
            "anno_base": balance.year,
            "ricavi": balance.conto_economico.valore_produzione.ricavi_totali,
            "altri_ricavi": balance.conto_economico.valore_produzione.altri_ricavi,
            "materie_prime": balance.conto_economico.costi_produzione.materie_prime,
            "servizi": balance.conto_economico.costi_produzione.servizi,
            "godimento_terzi": balance.conto_economico.costi_produzione.godimento_terzi,
            "personale": balance.conto_economico.costi_produzione.personale,
            "ammortamenti": balance.conto_economico.costi_produzione.ammortamenti,
            "accantonamenti": (
                balance.conto_economico.costi_produzione.accantonamento_rischi +
                balance.conto_economico.costi_produzione.altri_accantonamenti
            ),
            "oneri_diversi": balance.conto_economico.costi_produzione.oneri_diversi,
            "interessi_passivi": balance.conto_economico.proventi_oneri_finanziari.interessi_passivi,
            "ebitda": balance.conto_economico.ebitda,
            "ebit": balance.conto_economico.ebit,
            "utile_netto": balance.conto_economico.utile_netto,
            # Stato Patrimoniale
            "immobilizzazioni": balance.stato_patrimoniale.attivo.immobilizzato.totale,
            "crediti": balance.stato_patrimoniale.attivo.circolante.crediti_commerciali,
            "magazzino": balance.stato_patrimoniale.attivo.circolante.rimanenze,
            "liquidita": balance.stato_patrimoniale.attivo.circolante.disponibilita_liquide,
            "patrimonio_netto": balance.stato_patrimoniale.passivo.patrimonio_netto.totale,
            "debiti_finanziari": balance.stato_patrimoniale.passivo.totale_debiti_finanziari,
            "debiti_fornitori": balance.stato_patrimoniale.passivo.debiti_fornitori,
            "tfr": balance.stato_patrimoniale.passivo.tfr,
        }

    def get_trend_analysis(self) -> Dict[str, Any]:
        """
        Analisi del trend storico.

        Returns:
            Dict con analisi qualitativa del trend
        """
        if len(self.balances) < 2:
            return {"status": "insufficient_data", "trend": "unknown"}

        # Determina trend ricavi
        var_ricavi = calcola_variazione_percentuale(
            self.metrics.ricavi_storici[0],
            self.metrics.ricavi_storici[-1]
        )

        if var_ricavi > 0.10:
            trend_ricavi = "crescita"
        elif var_ricavi < -0.10:
            trend_ricavi = "contrazione"
        else:
            trend_ricavi = "stabile"

        # Determina trend margini
        if self.metrics.ebitda_margin_medio > 0.15:
            trend_margini = "alto"
        elif self.metrics.ebitda_margin_medio > 0.08:
            trend_margini = "medio"
        else:
            trend_margini = "basso"

        return {
            "status": "complete",
            "trend_ricavi": trend_ricavi,
            "variazione_ricavi_periodo": round(var_ricavi, 4),
            "trend_margini": trend_margini,
            "cagr_ricavi": round(self.metrics.cagr_ricavi, 4),
            "ebitda_margin_medio": round(self.metrics.ebitda_margin_medio, 4),
            "ros_medio": round(self.metrics.ros_medio, 4),
        }
