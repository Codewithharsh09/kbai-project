import json
from typing import Dict, Any, Optional
from difflib import get_close_matches
import re

class FuzzyKeyMatcher:
    """Helper class for fuzzy matching JSON keys"""
    
    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize key by removing special characters and converting to lowercase"""
        normalized = re.sub(r'[^a-z0-9]', '', key.lower())
        return normalized
    
    @staticmethod
    def find_key_fuzzy(data: dict, target_key: str, threshold: float = 0.6) -> Optional[str]:
        """Find the closest matching key in dictionary using fuzzy matching"""
        if not isinstance(data, dict):
            return None
        
        # First try exact match
        if target_key in data:
            return target_key
        
        # Normalize target key
        normalized_target = FuzzyKeyMatcher.normalize_key(target_key)
        
        # Try normalized exact match
        for key in data.keys():
            if FuzzyKeyMatcher.normalize_key(key) == normalized_target:
                return key
        
        # Use close_matches for fuzzy matching
        all_keys = list(data.keys())
        normalized_keys = [FuzzyKeyMatcher.normalize_key(k) for k in all_keys]
        
        matches = get_close_matches(normalized_target, normalized_keys, n=1, cutoff=threshold)
        
        if matches:
            matched_normalized = matches[0]
            for i, norm_key in enumerate(normalized_keys):
                if norm_key == matched_normalized:
                    return all_keys[i]
        
        return None
    
    @staticmethod
    def fuzzy_navigate(data: dict, *keys, default=0) -> tuple:
        """Navigate nested dict with fuzzy key matching"""
        current = data
        path_found = True
        matched_path = []
        
        for key in keys:
            if not isinstance(current, dict):
                return default, False, matched_path
            
            matched_key = FuzzyKeyMatcher.find_key_fuzzy(current, key)
            
            if matched_key is None:
                return default, False, matched_path
            
            matched_path.append(matched_key)
            current = current[matched_key]
        
        try:
            value = float(current) if current is not None else default
            return value, True, matched_path
        except (ValueError, TypeError):
            return current, True, matched_path


class FinancialKPIAnalyzer:
    """Analyzer that strictly follows formulas.txt with detailed debugging"""
    
    def __init__(self, json_data: Dict[str, Any], year_label: str = "Unknown"):
        self.data = json_data
        self.year_label = year_label
        self.missing_fields = []
        self.matched_paths = {}
        self.matcher = FuzzyKeyMatcher()
        self.debug_info = {}
    
    def safe_get(self, *keys, default=0) -> float:
        """Safely navigate nested dictionary with fuzzy matching and debugging"""
        value, found, matched_path = self.matcher.fuzzy_navigate(self.data, *keys, default=default)
        
        path_key = " -> ".join(keys)
        
        if found:
            self.matched_paths[path_key] = " -> ".join(matched_path)
        else:
            self.missing_fields.append(path_key)
        
        # Store debug info
        self.debug_info[path_key] = {
            "value": value,
            "found": found,
            "matched_path": " -> ".join(matched_path) if found else "NOT_FOUND"
        }
        
        return value
    
    def calculate_ebitda(self) -> float:
        """EBITDA with detailed breakdown"""
        tot_valore_prod = self.safe_get("Conto_economico", "Valore_della_produzione", 
                                        "Totale_valore_della_produzione")
        tot_altri_ricavi = self.safe_get("Conto_economico", "Valore_della_produzione",
                                         "Altri_ricavi_e_proventi", "Totale_altri_ricavi_e_proventi")
        tot_costi_prod = self.safe_get("Conto_economico", "Costi_di_produzione",
                                       "Totale_costi_della_produzione")
        tot_ammortamenti = self.safe_get("Conto_economico", "Costi_di_produzione",
                                         "Ammortamento_e_svalutazioni", 
                                         "Totale_ammortamenti_e_svalutazioni")
        oneri_diversi = self.safe_get("Conto_economico", "Costi_di_produzione",
                                      "Oneri_diversi_di_gestione")
        
        ebitda = (tot_valore_prod - tot_altri_ricavi) - (tot_costi_prod - tot_ammortamenti - oneri_diversi)
        
        # Store breakdown for debugging
        self.debug_info['EBITDA_breakdown'] = {
            "Totale_valore_produzione": tot_valore_prod,
            "Totale_altri_ricavi": tot_altri_ricavi,
            "Totale_costi_produzione": tot_costi_prod,
            "Totale_ammortamenti": tot_ammortamenti,
            "Oneri_diversi": oneri_diversi,
            "Formula": f"({tot_valore_prod} - {tot_altri_ricavi}) - ({tot_costi_prod} - {tot_ammortamenti} - {oneri_diversi})",
            "EBITDA": ebitda
        }
        
        return ebitda
    
    def calculate_ebit(self) -> float:
        """EBIT = EBITDA - Ammortamenti + Altri ricavi - Oneri diversi"""
        tot_valore_prod = self.safe_get("Conto_economico", "Valore_della_produzione",
                                        "Totale_valore_della_produzione")
        tot_altri_ricavi = self.safe_get("Conto_economico", "Valore_della_produzione",
                                         "Altri_ricavi_e_proventi", "Totale_altri_ricavi_e_proventi")
        tot_costi_prod = self.safe_get("Conto_economico", "Costi_di_produzione",
                                       "Totale_costi_della_produzione")
        tot_ammortamenti = self.safe_get("Conto_economico", "Costi_di_produzione",
                                         "Ammortamento_e_svalutazioni",
                                         "Totale_ammortamenti_e_svalutazioni")
        oneri_diversi = self.safe_get("Conto_economico", "Costi_di_produzione",
                                      "Oneri_diversi_di_gestione")
        
        ebit = ((tot_valore_prod - tot_altri_ricavi) - 
                (tot_costi_prod - tot_ammortamenti - oneri_diversi) - 
                tot_ammortamenti + tot_altri_ricavi - oneri_diversi)
        
        self.debug_info['EBIT_breakdown'] = {
            "Components": {
                "Totale_valore_produzione": tot_valore_prod,
                "Totale_altri_ricavi": tot_altri_ricavi,
                "Totale_costi_produzione": tot_costi_prod,
                "Totale_ammortamenti": tot_ammortamenti,
                "Oneri_diversi": oneri_diversi
            },
            "EBIT": ebit
        }
        
        return ebit
    
    def get_ricavi_totali(self) -> float:
        """Ricavi totali = Ricavi + Variazioni"""
        ricavi = self.safe_get("Conto_economico", "Valore_della_produzione",
                               "Ricavi_delle_vendite_e_delle_prestazioni")
        var_lav = self.safe_get("Conto_economico", "Valore_della_produzione",
                                "Variazione_delle_lavorazioni_in_corso_di_esecuzione")
        var_lavori = self.safe_get("Conto_economico", "Valore_della_produzione",
                                   "Variazione_dei_lavori_in_corso_di_esecuzione")
        
        total = ricavi + var_lav + var_lavori
        
        self.debug_info['Ricavi_Totali_breakdown'] = {
            "Ricavi_vendite": ricavi,
            "Var_lavorazioni": var_lav,
            "Var_lavori": var_lavori,
            "Total": total
        }
        
        return total
    
    def calculate_mol_ricavi(self) -> float:
        """MOL/RICAVI = [EBITDA / Ricavi_totali] * 100"""
        ebitda = self.calculate_ebitda()
        ricavi_totali = self.get_ricavi_totali()
        
        if ricavi_totali == 0:
            return 0
        return (ebitda / ricavi_totali) * 100
    
    def calculate_ebitda_margin(self) -> float:
        """EBITDA Margin = [EBITDA / (Tot_valore_prod - Tot_altri_ricavi)] * 100"""
        ebitda = self.calculate_ebitda()
        tot_valore_prod = self.safe_get("Conto_economico", "Valore_della_produzione",
                                        "Totale_valore_della_produzione")
        tot_altri_ricavi = self.safe_get("Conto_economico", "Valore_della_produzione",
                                         "Altri_ricavi_e_proventi", "Totale_altri_ricavi_e_proventi")
        
        denominatore = tot_valore_prod - tot_altri_ricavi
        if denominatore == 0:
            return 0
        return (ebitda / denominatore) * 100
    
    def get_costi_variabili(self) -> float:
        """Costi variabili = Materie + Servizi + Godimento"""
        materie = self.safe_get("Conto_economico", "Costi_di_produzione",
                                "Per_materie_prime,_sussidiarie_di_consumo_merci")
        servizi = self.safe_get("Conto_economico", "Costi_di_produzione", "Per_servizi")
        godimento = self.safe_get("Conto_economico", "Costi_di_produzione",
                                  "Per_godimento_di_terzi")
        
        total = materie + servizi + godimento
        
        self.debug_info['Costi_Variabili_breakdown'] = {
            "Materie_prime": materie,
            "Servizi": servizi,
            "Godimento_terzi": godimento,
            "Total": total
        }
        
        return total
    
    def calculate_mdc_percentage(self) -> float:
        """MdC % = [(Ricavi_totali - Costi_variabili) / Ricavi_totali] * 100"""
        ricavi_totali = self.get_ricavi_totali()
        costi_variabili = self.get_costi_variabili()
        
        if ricavi_totali == 0:
            return 0
        return ((ricavi_totali - costi_variabili) / ricavi_totali) * 100
    
    def calculate_patrimonio_netto(self) -> float:
        """PN = Tot_patrimonio - Crediti_soci - Proventi_part - Riserve_copertura"""
        tot_patrimonio = self.safe_get("Stato_patrimoniale", "Passivo", "Patrimonio_netto",
                                       "Totale_patrimonio_netto")
        tot_crediti_soci = self.safe_get("Stato_patrimoniale", "Attivo",
                                         "Crediti_verso_soci_per_versamenti_ancora_dovuti",
                                         "Totale_crediti_verso_soci_per_versamenti_ancora_dovuti")
        tot_proventi_part = self.safe_get("Conto_economico", "Proventi_e_oneri_finanziari",
                                          "Proventi_da_partecipazioni",
                                          "Totale_proventi_da_partecipazioni")
        riserve_copertura = self.safe_get("Stato_patrimoniale", "Passivo", "Patrimonio_netto",
                                          "Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi")
        
        pn = tot_patrimonio - tot_crediti_soci - tot_proventi_part - riserve_copertura
        
        self.debug_info['Patrimonio_Netto_breakdown'] = {
            "Totale_patrimonio": tot_patrimonio,
            "Crediti_soci": tot_crediti_soci,
            "Proventi_partecipazioni": tot_proventi_part,
            "Riserve_copertura": riserve_copertura,
            "PN_Adjusted": pn
        }
        
        return pn
    
    def calculate_markup(self) -> float:
        """Mark Up = MdC_ratio / (1 - MdC_ratio)"""
        mdc_ratio = self.calculate_mdc_percentage() / 100
        
        if (1 - mdc_ratio) == 0:
            return 0
        return mdc_ratio / (1 - mdc_ratio)
    
    def calculate_bep(self) -> float:
        """BEP = Spese_fisse / MdC_ratio"""
        servizi = self.safe_get("Conto_economico", "Costi_di_produzione", "Per_servizi")
        godimento = self.safe_get("Conto_economico", "Costi_di_produzione",
                                  "Per_godimento_di_terzi")
        acc_rischi = self.safe_get("Conto_economico", "Costi_di_produzione",
                                   "Accantonamento_per_rischi")
        altri_acc = self.safe_get("Conto_economico", "Costi_di_produzione",
                                  "Altri_accantonamenti")
        
        spese_fisse = servizi + godimento + acc_rischi + altri_acc
        mdc_ratio = self.calculate_mdc_percentage() / 100
        
        if mdc_ratio == 0:
            return 0
        return spese_fisse / mdc_ratio
    
    def calculate_spese_generali(self) -> float:
        """Spese Generali = (Servizi + Godimento + Accantonamenti) / Ricavi_totali"""
        servizi = self.safe_get("Conto_economico", "Costi_di_produzione", "Per_servizi")
        godimento = self.safe_get("Conto_economico", "Costi_di_produzione",
                                  "Per_godimento_di_terzi")
        acc_rischi = self.safe_get("Conto_economico", "Costi_di_produzione",
                                   "Accantonamento_per_rischi")
        altri_acc = self.safe_get("Conto_economico", "Costi_di_produzione",
                                  "Altri_accantonamenti")
        
        spese = servizi + godimento + acc_rischi + altri_acc
        ricavi_totali = self.get_ricavi_totali()
        
        if ricavi_totali == 0:
            return 0
        return spese / ricavi_totali
    
    def calculate_all_kpis(self) -> Dict[str, float]:
        """Calculate all KPIs"""
        return {
            "EBITDA": round(self.calculate_ebitda(), 2),
            "EBIT_Reddito_Operativo": round(self.calculate_ebit(), 2),
            "MOL_RICAVI_%": round(self.calculate_mol_ricavi(), 2),
            "EBITDA_Margin_%": round(self.calculate_ebitda_margin(), 2),
            "Margine_Contribuzione_%": round(self.calculate_mdc_percentage(), 2),
            "Patrimonio_Netto": round(self.calculate_patrimonio_netto(), 2),
            "Mark_Up": round(self.calculate_markup(), 4),
            "Fatturato_Equilibrio_BEP": round(self.calculate_bep(), 2),
            "Spese_Generali_Ratio": round(self.calculate_spese_generali(), 4),
            "Ricavi_Totali": round(self.get_ricavi_totali(), 2),
            "Costi_Variabili": round(self.get_costi_variabili(), 2)
        }


def compare_kpis(kpis1: Dict[str, float], kpis2: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Compare KPIs between two years"""
    comparison = {}
    
    for key in kpis1.keys():
        if key in kpis2:
            year1_val = kpis1[key]
            year2_val = kpis2[key]
            
            if year1_val != 0:
                change_pct = ((year2_val - year1_val) / abs(year1_val)) * 100
            else:
                change_pct = 0 if year2_val == 0 else float('inf')
            
            absolute_change = year2_val - year1_val
            
            comparison[key] = {
                "Year1": year1_val,
                "Year2": year2_val,
                "Absolute_Change": round(absolute_change, 2),
                "Change_%": round(change_pct, 2) if change_pct != float('inf') else "N/A"
            }
    
    return comparison


def analyze_financials(json_file1: str, json_file2: str, debug_mode: bool = False) -> Dict[str, Any]:
    """Main function with detailed debugging"""
    
    # Load JSON files
    with open(json_file1, 'r', encoding='utf-8') as f:
        data1 = json.load(f)
    
    with open(json_file2, 'r', encoding='utf-8') as f:
        data2 = json.load(f)
    
    # Analyze both years
    print(f"\n{'='*70}")
    print(f"Analyzing {json_file1}...")
    print(f"{'='*70}")
    
    analyzer1 = FinancialKPIAnalyzer(data1, "Year 1")
    kpis_year1 = analyzer1.calculate_all_kpis()
    
    print(f"\n{'='*70}")
    print(f"Analyzing {json_file2}...")
    print(f"{'='*70}")
    
    analyzer2 = FinancialKPIAnalyzer(data2, "Year 2")
    kpis_year2 = analyzer2.calculate_all_kpis()
    
    # Compare KPIs
    comparison = compare_kpis(kpis_year1, kpis_year2)
    
    # Combine missing fields
    all_missing = list(set(analyzer1.missing_fields + analyzer2.missing_fields))
    
    # Create detailed report
    report = {
        "KPIs_Year1": kpis_year1,
        "KPIs_Year2": kpis_year2,
        "Comparison": comparison,
        "Missing_Fields": all_missing if all_missing else ["None"],
        "Status": "complete" if not all_missing else "complete_with_warnings"
    }
    
    # Add debug information if requested
    if debug_mode:
        report["Debug_Info"] = {
            "Year1": analyzer1.debug_info,
            "Year2": analyzer2.debug_info
        }
    
    return report, analyzer1, analyzer2
