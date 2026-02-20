"""
Balance Sheet Data Models

Dataclasses representing financial statement structures compatible with KBAI format.
Supports both Conto Economico (Income Statement) and Stato Patrimoniale (Balance Sheet).

Following KBAI JSON structure patterns from existing comparison_report.py
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class ValoreProduzione:
    """Valore della Produzione (Production Value) - CE section"""
    ricavi_vendite: float = 0.0  # Ricavi delle vendite e delle prestazioni
    variazione_rimanenze: float = 0.0  # Variazioni delle rimanenze
    variazione_lavorazioni: float = 0.0  # Variazione delle lavorazioni in corso
    incrementi_immobilizzazioni: float = 0.0  # Incrementi di immobilizzazioni
    altri_ricavi: float = 0.0  # Altri ricavi e proventi

    @property
    def totale(self) -> float:
        """Totale valore della produzione"""
        return (
            self.ricavi_vendite +
            self.variazione_rimanenze +
            self.variazione_lavorazioni +
            self.incrementi_immobilizzazioni +
            self.altri_ricavi
        )

    @property
    def ricavi_totali(self) -> float:
        """Ricavi totali = Ricavi vendite + Variazioni"""
        return self.ricavi_vendite + self.variazione_rimanenze + self.variazione_lavorazioni


@dataclass
class CostiProduzione:
    """Costi della Produzione (Production Costs) - CE section"""
    materie_prime: float = 0.0  # Per materie prime, sussidiarie, di consumo e merci
    servizi: float = 0.0  # Per servizi
    godimento_terzi: float = 0.0  # Per godimento di beni di terzi
    personale: float = 0.0  # Per il personale (totale)
    salari_stipendi: float = 0.0  # Salari e stipendi
    oneri_sociali: float = 0.0  # Oneri sociali
    tfr: float = 0.0  # Trattamento di fine rapporto
    ammortamenti: float = 0.0  # Ammortamenti e svalutazioni (totale)
    ammortamento_immateriali: float = 0.0  # Ammortamento immobilizzazioni immateriali
    ammortamento_materiali: float = 0.0  # Ammortamento immobilizzazioni materiali
    svalutazioni: float = 0.0  # Svalutazioni dei crediti
    variazione_rimanenze: float = 0.0  # Variazioni delle rimanenze
    accantonamento_rischi: float = 0.0  # Accantonamento per rischi
    altri_accantonamenti: float = 0.0  # Altri accantonamenti
    oneri_diversi: float = 0.0  # Oneri diversi di gestione

    @property
    def totale(self) -> float:
        """Totale costi della produzione"""
        return (
            self.materie_prime +
            self.servizi +
            self.godimento_terzi +
            self.personale +
            self.ammortamenti +
            self.variazione_rimanenze +
            self.accantonamento_rischi +
            self.altri_accantonamenti +
            self.oneri_diversi
        )

    @property
    def costi_variabili(self) -> float:
        """Costi variabili = Materie + Servizi + Godimento terzi"""
        return self.materie_prime + self.servizi + self.godimento_terzi

    @property
    def costi_fissi(self) -> float:
        """Costi fissi = Personale + Ammortamenti + Accantonamenti + Oneri diversi"""
        return (
            self.personale +
            self.ammortamenti +
            self.accantonamento_rischi +
            self.altri_accantonamenti +
            self.oneri_diversi
        )


@dataclass
class ProventiOneriFinanziari:
    """Proventi e Oneri Finanziari - CE section"""
    proventi_partecipazioni: float = 0.0
    altri_proventi: float = 0.0
    interessi_passivi: float = 0.0
    utili_perdite_cambi: float = 0.0

    @property
    def totale(self) -> float:
        """Totale proventi e oneri finanziari"""
        return (
            self.proventi_partecipazioni +
            self.altri_proventi -
            self.interessi_passivi +
            self.utili_perdite_cambi
        )


@dataclass
class ContoEconomico:
    """Conto Economico (Income Statement)"""
    valore_produzione: ValoreProduzione = field(default_factory=ValoreProduzione)
    costi_produzione: CostiProduzione = field(default_factory=CostiProduzione)
    proventi_oneri_finanziari: ProventiOneriFinanziari = field(default_factory=ProventiOneriFinanziari)
    rettifiche_attivita_finanziarie: float = 0.0
    proventi_oneri_straordinari: float = 0.0
    imposte: float = 0.0

    @property
    def differenza_valore_costi(self) -> float:
        """Differenza tra valore e costi della produzione (EBIT operativo)"""
        return self.valore_produzione.totale - self.costi_produzione.totale

    @property
    def ebitda(self) -> float:
        """EBITDA = Valore produzione - Costi (esclusi ammortamenti)"""
        return (
            self.valore_produzione.totale -
            self.valore_produzione.altri_ricavi -
            (self.costi_produzione.totale -
             self.costi_produzione.ammortamenti -
             self.costi_produzione.oneri_diversi)
        )

    @property
    def ebit(self) -> float:
        """EBIT = Reddito Operativo"""
        return self.differenza_valore_costi

    @property
    def risultato_ante_imposte(self) -> float:
        """Risultato prima delle imposte"""
        return (
            self.differenza_valore_costi +
            self.proventi_oneri_finanziari.totale +
            self.rettifiche_attivita_finanziarie +
            self.proventi_oneri_straordinari
        )

    @property
    def utile_netto(self) -> float:
        """Utile (perdita) dell'esercizio"""
        return self.risultato_ante_imposte - self.imposte


@dataclass
class AttivoImmobilizzato:
    """Attivo Immobilizzato - SP section"""
    immobilizzazioni_immateriali: float = 0.0
    immobilizzazioni_materiali: float = 0.0
    immobilizzazioni_finanziarie: float = 0.0

    @property
    def totale(self) -> float:
        return (
            self.immobilizzazioni_immateriali +
            self.immobilizzazioni_materiali +
            self.immobilizzazioni_finanziarie
        )


@dataclass
class AttivoCircolante:
    """Attivo Circolante - SP section"""
    rimanenze: float = 0.0  # Magazzino
    crediti_commerciali: float = 0.0  # Crediti verso clienti
    crediti_tributari: float = 0.0
    crediti_altri: float = 0.0
    attivita_finanziarie: float = 0.0
    disponibilita_liquide: float = 0.0

    @property
    def totale(self) -> float:
        return (
            self.rimanenze +
            self.crediti_commerciali +
            self.crediti_tributari +
            self.crediti_altri +
            self.attivita_finanziarie +
            self.disponibilita_liquide
        )

    @property
    def totale_crediti(self) -> float:
        return self.crediti_commerciali + self.crediti_tributari + self.crediti_altri


@dataclass
class Attivo:
    """Attivo (Assets) - SP section"""
    crediti_verso_soci: float = 0.0
    immobilizzato: AttivoImmobilizzato = field(default_factory=AttivoImmobilizzato)
    circolante: AttivoCircolante = field(default_factory=AttivoCircolante)
    ratei_risconti_attivi: float = 0.0

    @property
    def totale(self) -> float:
        return (
            self.crediti_verso_soci +
            self.immobilizzato.totale +
            self.circolante.totale +
            self.ratei_risconti_attivi
        )


@dataclass
class PatrimonioNetto:
    """Patrimonio Netto - SP Passivo section"""
    capitale_sociale: float = 0.0
    riserva_sovrapprezzo: float = 0.0
    riserve_rivalutazione: float = 0.0
    riserva_legale: float = 0.0
    riserve_statutarie: float = 0.0
    altre_riserve: float = 0.0
    utili_perdite_portati: float = 0.0  # Utili (perdite) portati a nuovo
    utile_esercizio: float = 0.0  # Utile (perdita) dell'esercizio

    @property
    def totale(self) -> float:
        return (
            self.capitale_sociale +
            self.riserva_sovrapprezzo +
            self.riserve_rivalutazione +
            self.riserva_legale +
            self.riserve_statutarie +
            self.altre_riserve +
            self.utili_perdite_portati +
            self.utile_esercizio
        )


@dataclass
class Passivo:
    """Passivo (Liabilities) - SP section"""
    patrimonio_netto: PatrimonioNetto = field(default_factory=PatrimonioNetto)
    fondi_rischi: float = 0.0
    tfr: float = 0.0
    debiti_banche_breve: float = 0.0  # Debiti verso banche < 12 mesi
    debiti_banche_lungo: float = 0.0  # Debiti verso banche > 12 mesi
    debiti_fornitori: float = 0.0
    debiti_tributari: float = 0.0
    debiti_previdenziali: float = 0.0
    altri_debiti: float = 0.0
    ratei_risconti_passivi: float = 0.0

    @property
    def totale_debiti_finanziari(self) -> float:
        """Totale debiti finanziari (verso banche)"""
        return self.debiti_banche_breve + self.debiti_banche_lungo

    @property
    def totale_debiti(self) -> float:
        """Totale debiti"""
        return (
            self.debiti_banche_breve +
            self.debiti_banche_lungo +
            self.debiti_fornitori +
            self.debiti_tributari +
            self.debiti_previdenziali +
            self.altri_debiti
        )

    @property
    def totale(self) -> float:
        return (
            self.patrimonio_netto.totale +
            self.fondi_rischi +
            self.tfr +
            self.totale_debiti +
            self.ratei_risconti_passivi
        )


@dataclass
class StatoPatrimoniale:
    """Stato Patrimoniale (Balance Sheet)"""
    attivo: Attivo = field(default_factory=Attivo)
    passivo: Passivo = field(default_factory=Passivo)

    @property
    def totale_attivo(self) -> float:
        return self.attivo.totale

    @property
    def totale_passivo(self) -> float:
        return self.passivo.totale

    @property
    def is_balanced(self) -> bool:
        """Verifica quadratura: Attivo == Passivo"""
        return abs(self.totale_attivo - self.totale_passivo) < 0.01


@dataclass
class BalanceSheetData:
    """
    Complete balance sheet data structure for a single year.
    Compatible with KBAI JSON format.
    """
    year: int
    month: int = 12  # Default: annual balance (December)
    conto_economico: ContoEconomico = field(default_factory=ContoEconomico)
    stato_patrimoniale: StatoPatrimoniale = field(default_factory=StatoPatrimoniale)

    # Metadata
    company_name: Optional[str] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None

    @property
    def periodo(self) -> str:
        """Periodo di riferimento"""
        return f"{self.year}-{self.month:02d}"

    def validate(self) -> List[str]:
        """Validate balance sheet data, return list of warnings"""
        warnings = []

        # Check balance
        if not self.stato_patrimoniale.is_balanced:
            diff = self.stato_patrimoniale.totale_attivo - self.stato_patrimoniale.totale_passivo
            warnings.append(f"Bilancio non quadrato: differenza = {diff:.2f}")

        # Check utile consistency
        utile_ce = self.conto_economico.utile_netto
        utile_pn = self.stato_patrimoniale.passivo.patrimonio_netto.utile_esercizio
        if abs(utile_ce - utile_pn) > 0.01:
            warnings.append(f"Utile CE ({utile_ce:.2f}) != Utile PN ({utile_pn:.2f})")

        return warnings

    @classmethod
    def from_kbai_json(cls, json_data: Dict[str, Any], year: int, month: int = 12) -> "BalanceSheetData":
        """
        Create BalanceSheetData from KBAI JSON format.
        Uses fuzzy key matching for compatibility with various JSON structures.
        """
        from ..core.formula_library import safe_get_nested

        balance = cls(year=year, month=month)

        # Parse Conto Economico - Valore Produzione
        vp = balance.conto_economico.valore_produzione
        vp.ricavi_vendite = safe_get_nested(
            json_data,
            "Conto_economico", "Valore_della_produzione",
            "Ricavi_delle_vendite_e_delle_prestazioni"
        )
        vp.variazione_rimanenze = safe_get_nested(
            json_data,
            "Conto_economico", "Valore_della_produzione",
            "Variazione_delle_rimanenze"
        )
        vp.variazione_lavorazioni = safe_get_nested(
            json_data,
            "Conto_economico", "Valore_della_produzione",
            "Variazione_delle_lavorazioni_in_corso_di_esecuzione"
        )
        vp.incrementi_immobilizzazioni = safe_get_nested(
            json_data,
            "Conto_economico", "Valore_della_produzione",
            "Incrementi_di_immobilizzazioni"
        )
        vp.altri_ricavi = safe_get_nested(
            json_data,
            "Conto_economico", "Valore_della_produzione",
            "Altri_ricavi_e_proventi", "Totale_altri_ricavi_e_proventi"
        )

        # Parse Conto Economico - Costi Produzione
        cp = balance.conto_economico.costi_produzione
        cp.materie_prime = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_materie_prime,_sussidiarie_di_consumo_merci"
        )
        cp.servizi = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_servizi"
        )
        cp.godimento_terzi = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_godimento_di_terzi"
        )
        cp.personale = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_il_personale", "Totale_costi_per_il_personale"
        )
        cp.salari_stipendi = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_il_personale", "Salari_e_stipendi"
        )
        cp.oneri_sociali = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_il_personale", "Oneri_sociali"
        )
        cp.tfr = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Per_il_personale", "Trattamento_di_fine_rapporto"
        )
        cp.ammortamenti = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Ammortamento_e_svalutazioni", "Totale_ammortamenti_e_svalutazioni"
        )
        cp.ammortamento_immateriali = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Ammortamento_e_svalutazioni", "Ammortamento_delle_immobilizzazioni_immateriali"
        )
        cp.ammortamento_materiali = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Ammortamento_e_svalutazioni", "Ammortamento_delle_immobilizzazioni_materiali"
        )
        cp.oneri_diversi = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Oneri_diversi_di_gestione"
        )
        cp.accantonamento_rischi = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Accantonamento_per_rischi"
        )
        cp.altri_accantonamenti = safe_get_nested(
            json_data,
            "Conto_economico", "Costi_di_produzione",
            "Altri_accantonamenti"
        )

        # Parse Proventi e Oneri Finanziari
        pof = balance.conto_economico.proventi_oneri_finanziari
        pof.interessi_passivi = safe_get_nested(
            json_data,
            "Conto_economico", "Proventi_e_oneri_finanziari",
            "Interessi_e_altri_oneri_finanziari", "Totale_interessi_e_altri_oneri_finanziari"
        )
        pof.altri_proventi = safe_get_nested(
            json_data,
            "Conto_economico", "Proventi_e_oneri_finanziari",
            "Altri_proventi_finanziari", "Totale_altri_proventi_finanziari"
        )

        # Parse Imposte
        balance.conto_economico.imposte = safe_get_nested(
            json_data,
            "Conto_economico", "Imposte_sul_reddito"
        )

        # Parse Stato Patrimoniale - Attivo
        att = balance.stato_patrimoniale.attivo
        att.immobilizzato.immobilizzazioni_immateriali = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Immobilizzazioni",
            "Immobilizzazioni_immateriali", "Totale_immobilizzazioni_immateriali"
        )
        att.immobilizzato.immobilizzazioni_materiali = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Immobilizzazioni",
            "Immobilizzazioni_materiali", "Totale_immobilizzazioni_materiali"
        )
        att.immobilizzato.immobilizzazioni_finanziarie = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Immobilizzazioni",
            "Immobilizzazioni_finanziarie", "Totale_immobilizzazioni_finanziarie"
        )
        att.circolante.rimanenze = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Attivo_circolante",
            "Rimanenze", "Totale_rimanenze"
        )
        att.circolante.crediti_commerciali = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Attivo_circolante",
            "Crediti", "Verso_clienti"
        )
        att.circolante.disponibilita_liquide = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Attivo", "Attivo_circolante",
            "Disponibilità_liquide", "Totale_disponibilità_liquide"
        )

        # Parse Stato Patrimoniale - Passivo
        pas = balance.stato_patrimoniale.passivo
        pn = pas.patrimonio_netto
        pn.capitale_sociale = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Patrimonio_netto",
            "Capitale"
        )
        pn.riserva_legale = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Patrimonio_netto",
            "Riserva_legale"
        )
        pn.altre_riserve = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Patrimonio_netto",
            "Altre_riserve", "Totale_altre_riserve"
        )
        pn.utili_perdite_portati = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Patrimonio_netto",
            "Utili_perdite_portati_a_nuovo"
        )
        pn.utile_esercizio = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Patrimonio_netto",
            "Utile_perdita_dell_esercizio"
        )

        pas.fondi_rischi = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Fondi_per_rischi_e_oneri",
            "Totale_fondi_per_rischi_e_oneri"
        )
        pas.tfr = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo",
            "Trattamento_di_fine_rapporto_di_lavoro_subordinato"
        )
        pas.debiti_fornitori = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Debiti",
            "Debiti_verso_fornitori"
        )
        pas.debiti_banche_breve = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Debiti",
            "Debiti_verso_banche_esigibili_entro_esercizio_successivo"
        )
        pas.debiti_banche_lungo = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Debiti",
            "Debiti_verso_banche_esigibili_oltre_esercizio_successivo"
        )
        pas.debiti_tributari = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Debiti",
            "Debiti_tributari"
        )
        pas.debiti_previdenziali = safe_get_nested(
            json_data,
            "Stato_patrimoniale", "Passivo", "Debiti",
            "Debiti_verso_istituti_di_previdenza"
        )

        return balance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            "metadata": {
                "year": self.year,
                "month": self.month,
                "periodo": self.periodo,
                "company_name": self.company_name,
            },
            "conto_economico": {
                "valore_produzione": {
                    "ricavi_vendite": self.conto_economico.valore_produzione.ricavi_vendite,
                    "variazione_rimanenze": self.conto_economico.valore_produzione.variazione_rimanenze,
                    "variazione_lavorazioni": self.conto_economico.valore_produzione.variazione_lavorazioni,
                    "incrementi_immobilizzazioni": self.conto_economico.valore_produzione.incrementi_immobilizzazioni,
                    "altri_ricavi": self.conto_economico.valore_produzione.altri_ricavi,
                    "totale": self.conto_economico.valore_produzione.totale,
                },
                "costi_produzione": {
                    "materie_prime": self.conto_economico.costi_produzione.materie_prime,
                    "servizi": self.conto_economico.costi_produzione.servizi,
                    "godimento_terzi": self.conto_economico.costi_produzione.godimento_terzi,
                    "personale": self.conto_economico.costi_produzione.personale,
                    "ammortamenti": self.conto_economico.costi_produzione.ammortamenti,
                    "oneri_diversi": self.conto_economico.costi_produzione.oneri_diversi,
                    "totale": self.conto_economico.costi_produzione.totale,
                },
                "ebitda": self.conto_economico.ebitda,
                "ebit": self.conto_economico.ebit,
                "risultato_ante_imposte": self.conto_economico.risultato_ante_imposte,
                "imposte": self.conto_economico.imposte,
                "utile_netto": self.conto_economico.utile_netto,
            },
            "stato_patrimoniale": {
                "attivo": {
                    "immobilizzato": self.stato_patrimoniale.attivo.immobilizzato.totale,
                    "circolante": self.stato_patrimoniale.attivo.circolante.totale,
                    "totale": self.stato_patrimoniale.attivo.totale,
                },
                "passivo": {
                    "patrimonio_netto": self.stato_patrimoniale.passivo.patrimonio_netto.totale,
                    "debiti_finanziari": self.stato_patrimoniale.passivo.totale_debiti_finanziari,
                    "debiti_totali": self.stato_patrimoniale.passivo.totale_debiti,
                    "totale": self.stato_patrimoniale.passivo.totale,
                },
                "is_balanced": self.stato_patrimoniale.is_balanced,
            },
        }
