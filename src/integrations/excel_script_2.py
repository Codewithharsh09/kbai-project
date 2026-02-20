import openpyxl
import json
from pathlib import Path

def extract_bilancio_abbreviato_from_xlsx(xlsx_path):
    """
    Extract abbreviated balance sheet data from Italian XLSX format to JSON structure.
    This is for the "ABBREVIATO_annuale" format.
    
    Args:
        xlsx_path: Path to the Excel file
        
    Returns:
        Dictionary with abbreviated balance sheet data in JSON format
    """
    
    # Load the workbook
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    
    # Initialize the output structure for abbreviated format
    bilancio = {
        "informazioni_generali": {
            "id_bilancio": "1"
        },
        "Stato_patrimoniale": {
            "Attivo": {
                "Immobilizzazioni": {
                    "Immobilizzazioni_Immateriali": 0.0,
                    "Immobilizzazioni_Materiali": 0.0,
                    "Immobilizzazioni_Finanziarie": {
                        "dell_esercizio_corrente": 0.0,
                        "oltre_l_esercizio_corrente": 0.0,
                    },
                },
                "Attivo_circolante": {
                    "Rimanenze": 0.0,
                    "Crediti": 0.0,
                    "Attivita_finanziarie_che_non_costituiscono_immobilizzazioni": 0.0,
                    "Disponibilita_liquide": 0.0,
                },
                "Totale_attivo": 0.0
            },
            "Passivo": {
                "Patrimonio_netto": {
                    "Capitale": 0.0,
                    "Riserve_da_sovrapprezzo_azioni": 0.0,
                    "Riserve_da_rivalutazioni": 0.0,
                    "Riserve_legali": 0.0,
                    "Riserve_statutarie": 0.0,
                    "Altre_riserve_distintamente_indicate": 0.0,
                    "Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi": 0.0,
                    "Utili_(perdite)_portati_a_nuovo": 0.0,
                    "Utile_(perdita)_dell_esercizio": 0.0,
                    "Riserva_negativa_per_azioni_proprie_in_portafoglio": 0.0,
                    "Totale_patrimonio_netto": 0.0
                },
                "Fondi_per_rischi_e_oneri": 0.0,
                "Trattamento_di_fine_rapporto_di_lavoro_subordinato": 0.0,
                "Debiti": {
                    "dell_esercizio_corrente": 0.0,
                    "oltre_l_esercizio_corrente": 0.0,
                },
                "Ratei_e_risconti": 0.0,
                "Totale_passivo": 0.0
            }
        },
        "Conto_economico": {
            "Valore_della_produzione": {
                "Ricavi_delle_vendite_e_delle_prestazioni": 0.0,
                "Variazione_delle_rimanenze_di_prodotti_in_corso_di_lavorazione_semilav": 0.0,
                "Variazione_dei_lavori_in_corso_su_ordinazione": 0.0,
                "Incrementi_di_immobilizzazioni_per_lavori_interni": 0.0,
                "Altri_ricavi_e_proventi": {
                    "contributi_in_conto_esercizio": 0.0,
                    "altri": 0.0,
                    "Totale_altri_ricavi_e_proventi": 0.0
                },
                "Totale_valore_della_produzione": 0.0
            },
            "Costi_di_produzione": {
                "Per_materie_prime_sussidiarie_di_consumo_merci": 0.0,
                "Per_servizi": 0.0,
                "Per_godimento_di_beni_terzi": 0.0,
                "Per_personale": {
                    "Salari_e_stipendi": 0.0,
                    "Oneri_sociali": 0.0,
                    "Trattamento_di_fine_rapporto": 0.0,
                    "Trattamento_di_quiescenza_e_simili": 0.0,
                    "Altri_costi": 0.0,
                    "Totale_costi_per_il_personale": 0.0
                },
                "Ammortamento_e_svalutazioni": {
                    "Ammortamento_delle_immobilizzazioni_immateriali": 0.0,
                    "Ammortamento_delle_immobilizzazioni_materiali": 0.0,
                    "Altre_svalutazioni_delle_immobilizzazioni": 0.0,
                    "Svalutazioni_dei_crediti_compresi_nell_attivo_circolante_e_disp_liq": 0.0,
                    "Totale_ammortamenti_e_svalutazioni": 0.0
                },
                "Variazione_delle_rimanenze_di_materie_prime_sussidiarie_di_consumo": 0.0,
                "Accantonamento_per_rischi": 0.0,
                "Altri_accantonamenti": 0.0,
                "Oneri_diversi_di_gestione": 0.0,
                "Totale_costi_della_produzione": 0.0
            },
            "Differenza_A_B": 0.0,
            "Proventi_e_oneri_finanziari": {
                "Proventi_da_partecipazioni": {
                    "da_imprese_controllate": 0.0,
                    "da_imprese_collegate": 0.0,
                    "da_imprese_controllanti": 0.0,
                    "da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                    "altri": 0.0,
                    "Totale_proventi_da_partecipazioni": 0.0
                },
                "Altri_proventi_finanziari": {
                    "Da_crediti_iscritti_nelle_immobilizzazioni": {
                        "da_imprese_controllate": 0.0,
                        "da_imprese_collegate": 0.0,
                        "da_imprese_controllanti": 0.0,
                        "da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                        "altri": 0.0,
                        "Totale_proventi_finanziari_da_crediti_iscritti_nelle_immobilizzazioni": 0.0
                    },
                    "Da_titoli_iscritti_nelle_immobilizzazioni_diversi_dalle_partecipazioni": 0.0,
                    "Da_titoli_iscritti_nell_attivo_circolante_diversi_dalle_partecipazioni": 0.0,
                    "Proventi_diversi_dai_precedenti": {
                        "da_imprese_controllate": 0.0,
                        "da_imprese_collegate": 0.0,
                        "da_imprese_controllanti": 0.0,
                        "da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                        "altri": 0.0,
                        "Totale_proventi_diversi_dai_precedenti": 0.0
                    },
                    "Totale_altri_proventi_finanziari": 0.0
                },
                "Interessi_ed_oneri_finanziari": {
                    "verso_imprese_controllate": 0.0,
                    "verso_imprese_collegate": 0.0,
                    "verso_imprese_controllanti": 0.0,
                    "verso_imprese_sottoposte_al_controllo_delel_controllanti": 0.0,
                    "altri": 0.0,
                    "Totale_interessi_e_altri_oneri_finanziari": 0.0
                },
                "Utili_e_perdite_su_cambi": 0.0,
                "Totale_proventi_e_oneri_finanziari": 0.0
            },
            "Rettifiche_di_valore_di_attivita_passivita_e_finanziarie": {
                "Rivalutazioni": {
                    "di_partecipazioni": 0.0,
                    "di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": 0.0,
                    "di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": 0.0,
                    "di_strumenti_finanziari_derivati": 0.0,
                    "Totale_rivalutazioni": 0.0
                },
                "Svalutazioni": {
                    "di_partecipazioni": 0.0,
                    "di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": 0.0,
                    "di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": 0.0,
                    "di_strumenti_finanziari_derivati": 0.0,
                    "Totale_svalutazioni": 0.0
                },
                "Totale_rettifiche_di_valore_di_attivita_finanziarie": 0.0
            },
            "Proventi_e_oneri_straordinari": {
                "Proventi_con_separata_indicazione_delle_plusvalenze_da_alienazioni": 0.0,
                "Oneri_con_separata_indicazione_delle_minusvalenze_da_alienazioni": 0.0,
                "Totale_delle_partite_straordinarie": 0.0
            },
            "Risultato_prima_delle_imposte": 0.0,
            "Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate": {
                "imposte_correnti": 0.0,
                "imposte_relative_a_esercizi_precedenti": 0.0,
                "imposte_differite_e_anticipate": 0.0,
                "proventi_oneri_da_adesione_al_regime_di_consolidato_fiscale": 0.0,
                "Totale_delle_imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate": 0.0
            },
            "Utile_(perdita)_dell_esercizio": 0.0
        }
    }
    
    # Helper function to get numeric value from cell
    def get_value(row, col='K'):
        cell_value = ws[f'{col}{row}'].value
        if cell_value is None or cell_value == '':
            return 0.0
        try:
            # Handle Italian number format (comma as decimal separator)
            if isinstance(cell_value, str):
                cell_value = cell_value.replace('.', '').replace(',', '.')
            return float(cell_value)
        except (ValueError, TypeError):
            return 0.0
    
    # STATO PATRIMONIALE ATTIVO (SPA)
    
    # B - Immobilizzazioni
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Immateriali"] = get_value(4)
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Materiali"] = get_value(5)
    
    # III - Immobilizzazioni Finanziarie (simplified)
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["dell_esercizio_corrente"] = get_value(7)
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["oltre_l_esercizio_corrente"] = get_value(8)
    
    # Total Immobilizzazioni is not shown in abbreviated format, calculate it
    # bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Totale_immobilizzazioni"] = (
    #     bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Immateriali"] +
    #     bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Materiali"] +
    #     bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["Totale_immobilizzazioni_finanziarie"]
    # )
    
    # C - Attivo Circolante (simplified)
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Rimanenze"] = get_value(10)
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Crediti"] = get_value(11)
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Attivita_finanziarie_che_non_costituiscono_immobilizzazioni"] = get_value(12)
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Disponibilita_liquide"] = get_value(13)
    # bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Totale_attivo_circolante"] = get_value(9)
    
    # Total Attivo
    bilancio["Stato_patrimoniale"]["Attivo"]["Totale_attivo"] = get_value(14)
    
    # STATO PATRIMONIALE PASSIVO (SPP)
    
    # A - Patrimonio Netto (simplified)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Capitale"] = get_value(17)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_da_sovrapprezzo_azioni"] = get_value(18)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_da_rivalutazioni"] = get_value(19)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_legali"] = get_value(20)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_statutarie"] = get_value(21)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Altre_riserve_distintamente_indicate"] = get_value(22)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi"] = get_value(23)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Utili_(perdite)_portati_a_nuovo"] = get_value(24)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Utile_(perdita)_dell_esercizio"] = get_value(25)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserva_negativa_per_azioni_proprie_in_portafoglio"] = get_value(26)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Totale_patrimonio_netto"] = get_value(27)
    
    # B - Fondi per rischi e oneri
    bilancio["Stato_patrimoniale"]["Passivo"]["Fondi_per_rischi_e_oneri"] = get_value(28)
    
    # C - TFR
    bilancio["Stato_patrimoniale"]["Passivo"]["Trattamento_di_fine_rapporto_di_lavoro_subordinato"] = get_value(29)
    
    # D - Debiti (simplified)
    bilancio["Stato_patrimoniale"]["Passivo"]["Debiti"]["dell_esercizio_corrente"] = get_value(31)
    bilancio["Stato_patrimoniale"]["Passivo"]["Debiti"]["oltre_l_esercizio_corrente"] = get_value(32)
    
    # E - Ratei e risconti
    bilancio["Stato_patrimoniale"]["Passivo"]["Ratei_e_risconti"] = get_value(33)
    
    # Total Passivo
    bilancio["Stato_patrimoniale"]["Passivo"]["Totale_passivo"] = get_value(34)
    
    # CONTO ECONOMICO (CE)
    
    # A - Valore della produzione
    bilancio["Conto_economico"]["Valore_della_produzione"]["Ricavi_delle_vendite_e_delle_prestazioni"] = get_value(37)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Variazione_delle_rimanenze_di_prodotti_in_corso_di_lavorazione_semilav"] = get_value(38)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Variazione_dei_lavori_in_corso_su_ordinazione"] = get_value(39)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Incrementi_di_immobilizzazioni_per_lavori_interni"] = get_value(40)
    
    bilancio["Conto_economico"]["Valore_della_produzione"]["Altri_ricavi_e_proventi"]["contributi_in_conto_esercizio"] = get_value(42)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Altri_ricavi_e_proventi"]["altri"] = get_value(43)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Altri_ricavi_e_proventi"]["Totale_altri_ricavi_e_proventi"] = get_value(44)
    
    bilancio["Conto_economico"]["Valore_della_produzione"]["Totale_valore_della_produzione"] = get_value(45)
    
    # B - Costi di produzione
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_materie_prime_sussidiarie_di_consumo_merci"] = get_value(47)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_servizi"] = get_value(48)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_godimento_di_beni_terzi"] = get_value(49)
    
    # Per personale
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Salari_e_stipendi"] = get_value(51)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Oneri_sociali"] = get_value(52)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Trattamento_di_fine_rapporto"] = get_value(53)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Trattamento_di_quiescenza_e_simili"] = get_value(54)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Altri_costi"] = get_value(55)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"]["Totale_costi_per_il_personale"] = get_value(56)
    
    # Ammortamenti e svalutazioni
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"]["Ammortamento_delle_immobilizzazioni_immateriali"] = get_value(58)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"]["Ammortamento_delle_immobilizzazioni_materiali"] = get_value(59)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"]["Altre_svalutazioni_delle_immobilizzazioni"] = get_value(60)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"]["Svalutazioni_dei_crediti_compresi_nell_attivo_circolante_e_disp_liq"] = get_value(61)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"]["Totale_ammortamenti_e_svalutazioni"] = get_value(62)
    
    bilancio["Conto_economico"]["Costi_di_produzione"]["Variazione_delle_rimanenze_di_materie_prime_sussidiarie_di_consumo"] = get_value(63)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Accantonamento_per_rischi"] = get_value(64)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Altri_accantonamenti"] = get_value(65)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Oneri_diversi_di_gestione"] = get_value(66)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Totale_costi_della_produzione"] = get_value(67)
    
    bilancio["Conto_economico"]["Differenza_A_B"] = get_value(68)
    
    # C - Proventi e oneri finanziari
    # Proventi da partecipazioni
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["da_imprese_controllate"] = get_value(71)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["da_imprese_collegate"] = get_value(72)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["da_imprese_controllanti"] = get_value(73)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["da_imprese_sottoposte_al_controllo_delle_controllanti"] = get_value(74)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["altri"] = get_value(75)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"]["Totale_proventi_da_partecipazioni"] = get_value(76)
    
    # Altri proventi finanziari - Da crediti iscritti nelle immobilizzazioni
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["da_imprese_controllate"] = get_value(79)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["da_imprese_collegate"] = get_value(80)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["da_imprese_controllanti"] = get_value(81)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["da_imprese_sottoposte_al_controllo_delle_controllanti"] = get_value(82)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["altri"] = get_value(83)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"]["Totale_proventi_finanziari_da_crediti_iscritti_nelle_immobilizzazioni"] = get_value(84)
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_titoli_iscritti_nelle_immobilizzazioni_diversi_dalle_partecipazioni"] = get_value(85)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_titoli_iscritti_nell_attivo_circolante_diversi_dalle_partecipazioni"] = get_value(86)
    
    # Proventi diversi dai precedenti
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["da_imprese_controllate"] = get_value(88)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["da_imprese_collegate"] = get_value(89)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["da_imprese_controllanti"] = get_value(90)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["da_imprese_sottoposte_al_controllo_delle_controllanti"] = get_value(91)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["altri"] = get_value(92)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"]["Totale_proventi_diversi_dai_precedenti"] = get_value(93)
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Totale_altri_proventi_finanziari"] = get_value(94)
    
    # Interessi ed oneri finanziari
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["verso_imprese_controllate"] = get_value(96)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["verso_imprese_collegate"] = get_value(97)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["verso_imprese_controllanti"] = get_value(98)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["verso_imprese_sottoposte_al_controllo_delel_controllanti"] = get_value(99)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["altri"] = get_value(100)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_ed_oneri_finanziari"]["Totale_interessi_e_altri_oneri_finanziari"] = get_value(101)
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Utili_e_perdite_su_cambi"] = get_value(102)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Totale_proventi_e_oneri_finanziari"] = get_value(103)
    
    # D - Rettifiche di valore
    # Rivalutazioni
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Rivalutazioni"]["di_partecipazioni"] = get_value(106)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Rivalutazioni"]["di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni"] = get_value(107)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Rivalutazioni"]["di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni"] = get_value(108)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Rivalutazioni"]["di_strumenti_finanziari_derivati"] = get_value(109)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Rivalutazioni"]["Totale_rivalutazioni"] = get_value(110)
    
    # Svalutazioni
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Svalutazioni"]["di_partecipazioni"] = get_value(112)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Svalutazioni"]["di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni"] = get_value(113)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Svalutazioni"]["di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni"] = get_value(114)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Svalutazioni"]["di_strumenti_finanziari_derivati"] = get_value(115)
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Svalutazioni"]["Totale_svalutazioni"] = get_value(116)
    
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanziarie"]["Totale_rettifiche_di_valore_di_attivita_finanziarie"] = get_value(117)
    
    # E - Proventi e oneri straordinari
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Proventi_con_separata_indicazione_delle_plusvalenze_da_alienazioni"] = get_value(119)
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Oneri_con_separata_indicazione_delle_minusvalenze_da_alienazioni"] = get_value(120)
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Totale_delle_partite_straordinarie"] = get_value(121)
    
    # Risultato prima delle imposte
    bilancio["Conto_economico"]["Risultato_prima_delle_imposte"] = get_value(122)
    
    # Imposte
    bilancio["Conto_economico"]["Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"]["imposte_correnti"] = get_value(124)
    bilancio["Conto_economico"]["Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"]["imposte_relative_a_esercizi_precedenti"] = get_value(125)
    bilancio["Conto_economico"]["Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"]["imposte_differite_e_anticipate"] = get_value(126)
    bilancio["Conto_economico"]["Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"]["proventi_oneri_da_adesione_al_regime_di_consolidato_fiscale"] = get_value(127)
    bilancio["Conto_economico"]["Imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"]["Totale_delle_imposte_sul_reddito_di_esercizio_correnti_differite_e_anticipate"] = get_value(128)
    
    # Utile/Perdita dell'esercizio
    bilancio["Conto_economico"]["Utile_(perdita)_dell_esercizio"] = get_value(129)
    
    return bilancio


def main():
    """
    Main function to run the extraction.
    Usage: python script.py <path_to_xlsx_file>
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_xlsx_file>")
        print("\nExample: python script.py ABBREVIATO_annuale.xlsx")
        return
    
    xlsx_path = sys.argv[1]
    
    if not Path(xlsx_path).exists():
        print(f"Error: File '{xlsx_path}' not found!")
        return
    
    print(f"Extracting data from: {xlsx_path}")
    
    try:
        bilancio_data = extract_bilancio_abbreviato_from_xlsx(xlsx_path)
        
        # Save to JSON file
        output_file = "Abbreviato_Extracted_3.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bilancio_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Extraction completed successfully!")
        print(f"✓ Output saved to: {output_file}")
                
    except Exception as e:
        import logging
        logging.info(f"\n✗ Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()