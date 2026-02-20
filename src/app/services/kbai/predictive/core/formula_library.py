"""
Formula Library - Deterministic Financial Formulas

All formulas are deterministic and traceable (no ML/AI).
Each formula is documented with its financial logic.

Reference: CFO logic from mappa_logica_previsione.md
"""

from typing import Dict, Any, Optional, List, Tuple
from difflib import get_close_matches
import re


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_key(key: str) -> str:
    """Normalize key by removing special characters and converting to lowercase"""
    return re.sub(r'[^a-z0-9]', '', key.lower())


def find_key_fuzzy(data: dict, target_key: str, threshold: float = 0.6) -> Optional[str]:
    """Find the closest matching key in dictionary using fuzzy matching"""
    if not isinstance(data, dict):
        return None

    # First try exact match
    if target_key in data:
        return target_key

    # Normalize target key
    normalized_target = normalize_key(target_key)

    # Try normalized exact match
    for key in data.keys():
        if normalize_key(key) == normalized_target:
            return key

    # Use close_matches for fuzzy matching
    all_keys = list(data.keys())
    normalized_keys = [normalize_key(k) for k in all_keys]

    matches = get_close_matches(normalized_target, normalized_keys, n=1, cutoff=threshold)

    if matches:
        matched_normalized = matches[0]
        for i, norm_key in enumerate(normalized_keys):
            if norm_key == matched_normalized:
                return all_keys[i]

    return None


def safe_get_nested(data: dict, *keys, default: float = 0.0) -> float:
    """
    Safely navigate nested dictionary with fuzzy key matching.

    Args:
        data: Nested dictionary
        *keys: Path of keys to navigate
        default: Default value if path not found

    Returns:
        Value at path or default
    """
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        matched_key = find_key_fuzzy(current, key)

        if matched_key is None:
            return default

        current = current[matched_key]

    try:
        return float(current) if current is not None else default
    except (ValueError, TypeError):
        return default


# ============================================================================
# REVENUE FORMULAS (Ricavi)
# ============================================================================

def calcola_ricavi(
    ricavi_base: float,
    tasso_crescita: float,
    anno_n: int,
    growth_mode: str = "geometric"
) -> float:
    """
    Calcola ricavi per anno N.

    Formula (geometrica):
        ricavi_anno_n = ricavi_base * (1 + tasso_crescita) ** n

    Formula (lineare/costante):
        ricavi_anno_n = ricavi_base * (1 + tasso_crescita * n)

    Args:
        ricavi_base: Ricavi anno base
        tasso_crescita: Tasso crescita (es. 0.05 = 5%)
        anno_n: Numero anno di previsione (1, 2, 3)
        growth_mode: "geometric", "constant", or "cagr_based"

    Returns:
        Ricavi previsti per anno N
    """
    if growth_mode == "constant":
        # Crescita lineare costante
        return ricavi_base * (1 + tasso_crescita * anno_n)
    else:
        # Crescita geometrica (composta) - default
        return ricavi_base * (1 + tasso_crescita) ** anno_n


def calcola_cagr(valori: List[float]) -> float:
    """
    Calcola CAGR (Compound Annual Growth Rate).

    Formula:
        CAGR = (valore_finale / valore_iniziale) ^ (1/n) - 1

    Args:
        valori: Lista valori ordinati dal più vecchio al più recente

    Returns:
        CAGR come decimale (es. 0.05 = 5%)
    """
    if len(valori) < 2:
        return 0.0

    valore_iniziale = valori[0]
    valore_finale = valori[-1]
    n = len(valori) - 1

    if valore_iniziale <= 0 or valore_finale <= 0:
        return 0.0

    return (valore_finale / valore_iniziale) ** (1 / n) - 1


# ============================================================================
# COST FORMULAS (Costi)
# ============================================================================

def calcola_costi_variabili(
    ricavi: float,
    perc_costi_variabili: float,
    inflazione: float = 0.0,
    variazione_aggiuntiva: float = 0.0
) -> float:
    """
    Calcola costi variabili.

    Formula:
        costi_variabili = ricavi * perc_costi_variabili * (1 + inflazione + variazione)

    Args:
        ricavi: Ricavi previsti
        perc_costi_variabili: Percentuale costi variabili su ricavi (es. 0.60 = 60%)
        inflazione: Tasso inflazione (es. 0.02 = 2%)
        variazione_aggiuntiva: Variazione aggiuntiva (es. 0.05 = +5%)

    Returns:
        Costi variabili previsti
    """
    return ricavi * perc_costi_variabili * (1 + inflazione + variazione_aggiuntiva)


def calcola_costi_fissi(
    costi_fissi_base: float,
    anno_n: int,
    inflazione: float = 0.0,
    variazione_aggiuntiva: float = 0.0
) -> float:
    """
    Calcola costi fissi indicizzati.

    Formula:
        costi_fissi = costi_fissi_base * (1 + inflazione + variazione) ** n

    Args:
        costi_fissi_base: Costi fissi anno base
        anno_n: Numero anno di previsione
        inflazione: Tasso inflazione
        variazione_aggiuntiva: Variazione aggiuntiva

    Returns:
        Costi fissi previsti
    """
    return costi_fissi_base * (1 + inflazione + variazione_aggiuntiva) ** anno_n


def calcola_materie_prime(
    ricavi: float,
    perc_materie: float,
    inflazione_materie: float = 0.0,
    variazione: float = 0.0
) -> float:
    """
    Calcola costi materie prime.

    Args:
        ricavi: Ricavi previsti
        perc_materie: Percentuale materie prime su ricavi
        inflazione_materie: Inflazione settoriale materie
        variazione: Variazione aggiuntiva

    Returns:
        Costi materie prime previsti
    """
    return ricavi * perc_materie * (1 + inflazione_materie + variazione)


def calcola_servizi(
    ricavi: float,
    perc_servizi: float,
    inflazione: float = 0.0,
    variazione: float = 0.0
) -> float:
    """
    Calcola costi per servizi.

    Args:
        ricavi: Ricavi previsti
        perc_servizi: Percentuale servizi su ricavi
        inflazione: Tasso inflazione
        variazione: Variazione aggiuntiva

    Returns:
        Costi servizi previsti
    """
    return ricavi * perc_servizi * (1 + inflazione + variazione)


# ============================================================================
# PERSONNEL FORMULAS (Personale)
# ============================================================================

def calcola_personale(
    n_dipendenti: int,
    salario_medio: float,
    aumento_salariale: float,
    anno_n: int,
    aliquota_oneri: float = 0.30,
    include_oneri: bool = True
) -> Tuple[float, float, float]:
    """
    Calcola costo del personale.

    Formula:
        salari = n_dipendenti * salario_medio * (1 + aumento_salariale) ** n
        oneri = salari * aliquota_oneri

    Args:
        n_dipendenti: Numero dipendenti
        salario_medio: Salario medio annuo
        aumento_salariale: Tasso aumento salariale annuo
        anno_n: Numero anno di previsione
        aliquota_oneri: Aliquota oneri sociali (default 30%)
        include_oneri: Se includere oneri nel calcolo

    Returns:
        Tuple (salari, oneri, totale_personale)
    """
    salari = n_dipendenti * salario_medio * (1 + aumento_salariale) ** anno_n
    oneri = salari * aliquota_oneri if include_oneri else 0.0
    totale = salari + oneri

    return salari, oneri, totale


def calcola_tfr(costo_personale: float, aliquota_tfr: float = 0.0691) -> float:
    """
    Calcola accantonamento TFR.

    Formula:
        TFR = costo_personale * aliquota_tfr

    Args:
        costo_personale: Costo totale personale (salari)
        aliquota_tfr: Aliquota TFR (default 6.91%)

    Returns:
        Accantonamento TFR annuo
    """
    return costo_personale * aliquota_tfr


# ============================================================================
# DEPRECIATION FORMULAS (Ammortamenti)
# ============================================================================

def calcola_ammortamenti(
    ammortamenti_storici: float,
    investimento: float = 0.0,
    vita_utile: int = 10,
    anno_investimento: int = 1,
    anno_corrente: int = 1
) -> float:
    """
    Calcola ammortamenti totali.

    Formula:
        ammortamenti = ammortamenti_storici + (investimento / vita_utile) se anno >= anno_investimento

    Args:
        ammortamenti_storici: Ammortamenti anno base
        investimento: Importo nuovo investimento
        vita_utile: Anni vita utile investimento
        anno_investimento: Anno in cui avviene l'investimento
        anno_corrente: Anno corrente di previsione

    Returns:
        Ammortamenti totali previsti
    """
    quota_nuova = 0.0
    if investimento > 0 and vita_utile > 0 and anno_corrente >= anno_investimento:
        quota_nuova = investimento / vita_utile

    return ammortamenti_storici + quota_nuova


# ============================================================================
# RESULT FORMULAS (Risultati)
# ============================================================================

def calcola_ebitda(
    ricavi: float,
    costi_variabili: float,
    costo_personale: float,
    altri_ricavi: float = 0.0
) -> float:
    """
    Calcola EBITDA.

    Formula:
        EBITDA = Ricavi - Costi variabili - Costo personale + Altri ricavi

    Note: Non include ammortamenti, accantonamenti, oneri diversi

    Args:
        ricavi: Ricavi totali
        costi_variabili: Costi variabili (materie + servizi + godimento)
        costo_personale: Costo totale personale
        altri_ricavi: Altri ricavi e proventi

    Returns:
        EBITDA
    """
    return ricavi - costi_variabili - costo_personale + altri_ricavi


def calcola_ebit(
    ebitda: float,
    ammortamenti: float,
    accantonamenti: float = 0.0,
    oneri_diversi: float = 0.0
) -> float:
    """
    Calcola EBIT (Reddito Operativo).

    Formula:
        EBIT = EBITDA - Ammortamenti - Accantonamenti - Oneri diversi

    Args:
        ebitda: EBITDA
        ammortamenti: Ammortamenti totali
        accantonamenti: Accantonamenti per rischi e altri
        oneri_diversi: Oneri diversi di gestione

    Returns:
        EBIT
    """
    return ebitda - ammortamenti - accantonamenti - oneri_diversi


def calcola_utile_ante_imposte(
    ebit: float,
    proventi_finanziari: float = 0.0,
    oneri_finanziari: float = 0.0,
    proventi_straordinari: float = 0.0
) -> float:
    """
    Calcola utile ante imposte.

    Formula:
        Utile ante imposte = EBIT + Proventi finanziari - Oneri finanziari + Straordinari

    Args:
        ebit: EBIT
        proventi_finanziari: Proventi finanziari
        oneri_finanziari: Interessi passivi e altri oneri
        proventi_straordinari: Proventi/oneri straordinari netti

    Returns:
        Utile ante imposte
    """
    return ebit + proventi_finanziari - oneri_finanziari + proventi_straordinari


def calcola_utile_netto(
    utile_ante_imposte: float,
    aliquota_imposte: float = 0.24
) -> float:
    """
    Calcola utile netto.

    Formula:
        Utile netto = Utile ante imposte * (1 - aliquota_imposte)

    Note: Formula semplificata, non considera IRAP e altre componenti

    Args:
        utile_ante_imposte: Utile ante imposte
        aliquota_imposte: Aliquota IRES (default 24%)

    Returns:
        Utile netto
    """
    if utile_ante_imposte <= 0:
        # Perdita: no imposte
        return utile_ante_imposte

    imposte = utile_ante_imposte * aliquota_imposte
    return utile_ante_imposte - imposte


def calcola_interessi_passivi(
    debiti_finanziari: float,
    tasso_interesse: float
) -> float:
    """
    Calcola interessi passivi.

    Formula:
        Interessi = Debiti finanziari * Tasso interesse

    Args:
        debiti_finanziari: Totale debiti verso banche
        tasso_interesse: Tasso interesse annuo

    Returns:
        Interessi passivi
    """
    return debiti_finanziari * tasso_interesse


# ============================================================================
# WORKING CAPITAL FORMULAS (Capitale Circolante)
# ============================================================================

def calcola_crediti(ricavi: float, dso: float) -> float:
    """
    Calcola crediti commerciali basati su DSO.

    Formula:
        Crediti = Ricavi / 365 * DSO

    Args:
        ricavi: Ricavi annui
        dso: Days Sales Outstanding (giorni incasso)

    Returns:
        Crediti commerciali
    """
    return ricavi / 365 * dso


def calcola_magazzino(costi_diretti: float, doh: float) -> float:
    """
    Calcola magazzino (rimanenze) basato su DOH.

    Formula:
        Magazzino = Costi diretti / 365 * DOH

    Args:
        costi_diretti: Costi diretti (materie prime)
        doh: Days On Hand (giorni magazzino)

    Returns:
        Valore magazzino
    """
    return costi_diretti / 365 * doh


def calcola_debiti_fornitori(costi_diretti: float, dpo: float) -> float:
    """
    Calcola debiti verso fornitori basati su DPO.

    Formula:
        Debiti fornitori = Costi diretti / 365 * DPO

    Args:
        costi_diretti: Costi diretti (materie + servizi)
        dpo: Days Payable Outstanding (giorni pagamento)

    Returns:
        Debiti verso fornitori
    """
    return costi_diretti / 365 * dpo


def calcola_capitale_circolante(
    crediti: float,
    magazzino: float,
    debiti_fornitori: float
) -> float:
    """
    Calcola Capitale Circolante Netto (CCN).

    Formula:
        CCN = Crediti + Magazzino - Debiti fornitori

    Args:
        crediti: Crediti commerciali
        magazzino: Rimanenze
        debiti_fornitori: Debiti verso fornitori

    Returns:
        Capitale Circolante Netto
    """
    return crediti + magazzino - debiti_fornitori


def calcola_fabbisogno_ccn(
    ccn_anno_corrente: float,
    ccn_anno_precedente: float
) -> float:
    """
    Calcola variazione del fabbisogno di CCN.

    Formula:
        Delta CCN = CCN anno corrente - CCN anno precedente

    Positivo = aumento fabbisogno (cash out)
    Negativo = diminuzione fabbisogno (cash in)

    Args:
        ccn_anno_corrente: CCN anno corrente
        ccn_anno_precedente: CCN anno precedente

    Returns:
        Variazione CCN
    """
    return ccn_anno_corrente - ccn_anno_precedente


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calcola_percentuale_su_ricavi(valore: float, ricavi: float) -> float:
    """
    Calcola percentuale di un valore sui ricavi.

    Args:
        valore: Valore da calcolare come percentuale
        ricavi: Ricavi totali

    Returns:
        Percentuale (es. 0.60 = 60%)
    """
    if ricavi == 0:
        return 0.0
    return valore / ricavi


def calcola_media(valori: List[float]) -> float:
    """
    Calcola media aritmetica.

    Args:
        valori: Lista di valori

    Returns:
        Media aritmetica
    """
    if not valori:
        return 0.0
    return sum(valori) / len(valori)


def calcola_variazione_percentuale(
    valore_iniziale: float,
    valore_finale: float
) -> float:
    """
    Calcola variazione percentuale tra due valori.

    Formula:
        Variazione % = (valore_finale - valore_iniziale) / |valore_iniziale|

    Args:
        valore_iniziale: Valore iniziale
        valore_finale: Valore finale

    Returns:
        Variazione percentuale (es. 0.10 = +10%)
    """
    if valore_iniziale == 0:
        return 0.0 if valore_finale == 0 else float('inf')
    return (valore_finale - valore_iniziale) / abs(valore_iniziale)
