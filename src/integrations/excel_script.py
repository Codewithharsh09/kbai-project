import json
from pathlib import Path
import openpyxl

def extract_bilancio_from_xlsx(xlsx_path):
    """
    Extract balance sheet data from Italian XLSX format to JSON structure.
    
    Args:
        xlsx_path: Path to the Excel file
        
    Returns:
        Dictionary with balance sheet data in the expected JSON format
    """
    
    # Load the workbook
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    
    # Initialize the output structure
    bilancio = {
        "informazioni_generali": {
            "id_bilancio": "1"
        },
        "Stato_patrimoniale": {
            "Attivo": {
                "Crediti_verso_soci_per_versamenti_ancora_dovuti": {
                    "Parte_richiamata": 0.0,
                    "Parte_da_richiamare": 0.0,
                    "Totale_crediti_verso_soci_per_versamenti_ancora_dovuti": 0.0
                },
                "Immobilizzazioni": {
                    "Immobilizzazioni_Immateriali": {},
                    "Immobilizzazioni_Materiali": {},
                    "Immobilizzazioni_Finanziarie": {
                        "Partecipazioni": {},
                        "Crediti": {}
                    },
                    "Totale_immobilizzazioni": 0.0
                },
                "Attivo_circolante": {
                    "Rimanenze": {},
                    "Crediti": {},
                    "Attivita_finanziarie_che_non_costituiscono_immobilizzazioni": {},
                    "Disponibilita_liquide": {},
                    "Totale_attivo_circolante": 0.0
                },
                "Ratei_e_risconti": {},
                "Totale_attivo": 0.0
            },
            "Passivo": {
                "Patrimonio_netto": {
                    "Altre_riserve_distintamente": {}
                },
                "Fondi_per_rischi_e_oneri": {},
                "Trattamento_di_fine_rapporto_di_lavoro_subordinato": 0.0,
                "Debiti": {},
                "Ratei_e_risconti": {},
                "Totale_passivo": 0.0
            }
        },
        "Conto_economico": {
            "Valore_della_produzione": {
                "Altri_ricavi_e_proventi": {}
            },
            "Costi_di_produzione": {
                "Per_personale": {},
                "Ammortamento_e_svalutazioni": {}
            },
            "Differenza_valore_produzione_costi_produzione": 0.0,
            "Proventi_e_oneri_finanziari": {
                "Proventi_da_partecipazioni": {},
                "Altri_proventi_finanziari": {
                    "Da_crediti_iscritti_nelle_immobilizzazioni": {},
                    "Proventi_diversi_dai_precedenti": {}
                },
                "Interessi_e_oneri_finanziari": {}
            },
            "Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie": {
                "Rivalutazioni": {},
                "Svalutazioni": {}
            },
            "Proventi_e_oneri_straordinari": {},
            "Risultato_prima_delle_imposte": {
                "Imposte_sul_reddito_di_esercizio_correnti_differite_anticipate": {}
            }
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
    
    # Mapping based on the screenshots provided
    # STATO PATRIMONIALE ATTIVO (SPA)
    
    # A - Crediti verso soci
    bilancio["Stato_patrimoniale"]["Attivo"]["Crediti_verso_soci_per_versamenti_ancora_dovuti"]["Parte_richiamata"] = get_value(4)
    bilancio["Stato_patrimoniale"]["Attivo"]["Crediti_verso_soci_per_versamenti_ancora_dovuti"]["Parte_da_richiamare"] = get_value(5)
    bilancio["Stato_patrimoniale"]["Attivo"]["Crediti_verso_soci_per_versamenti_ancora_dovuti"]["Totale_crediti_verso_soci_per_versamenti_ancora_dovuti"] = get_value(6)
    
    # B - Immobilizzazioni
    # I - Immobilizzazioni Immateriali
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Immateriali"] = {
        "Costi_impianto_e_di_ampliamento": get_value(9),
        "Costi_di_sviluppo": get_value(10),
        "Diritti_di_brevetto_industriale_e_diritti_di_utilizzazione_opere_dell_ingegno": get_value(11),
        "Concessioni,_licenze,_marchi_e_diritti_simili": get_value(12),
        "Avviamento": get_value(13),
        "Immobilizzazioni_in_corso_e_acconti": get_value(14),
        "Altre": get_value(15),
        "Totale_immobilizzazioni_immateriali": get_value(16)
    }
    
    # II - Immobilizzazioni Materiali
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Materiali"] = {
        "Terreni_e_fabbricati": get_value(18),
        "Impianti_e_macchinari": get_value(19),
        "Attrezzature_industriali_e_commerciali": get_value(20),
        "Altri_beni": get_value(21),
        "Immobilizzazioni_in_corso_e_acconti": get_value(22),
        "Totale_immobilizzazioni_materiali": get_value(23)
    }
    
    # III - Immobilizzazioni Finanziarie
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["Partecipazioni"] = {
        "Imprese_controllate": get_value(26),
        "Imprese_collegate": get_value(27),
        "Imprese_controllanti": get_value(28),
        "Imprese_sottoposte_al_controllo_delle_controllanti": get_value(29),
        "Altre_imprese": get_value(30),
        "Totale_partecipazioni": get_value(31)
    }
    
    # Crediti nelle immobilizzazioni finanziarie
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["Crediti"] = {
        "Verso_imprese_controllate": {
            "esigibili_entro_l_esercizio_successivo": get_value(34),
            "esigibili_oltre_l_esercizio_successivo": get_value(35),
            "Totale_crediti_verso_imprese_controllate": get_value(36)
        },
        "Verso_imprese_collegate": {
            "esigibili_entro_l_esercizio_successivo": get_value(38),
            "esigibili_oltre_l_esercizio_successivo": get_value(39),
            "Totale_crediti_verso_imprese_collegate": get_value(40)
        },
        "Verso_imprese_controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(42),
            "esigibili_oltre_l_esercizio_successivo": get_value(43),
            "Totale_crediti_verso_imprese_controllanti": get_value(44)
        },
        "Imprese_sottoposte_al_controllo_delle_controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(46),
            "esigibili_oltre_l_esercizio_successivo": get_value(47),
            "Totale_crediti_verso_imprese_sottoposte_al_controllo_delle_controllanti": get_value(48)
        },
        "Altre_imprese": {
            "esigibili_entro_l_esercizio_successivo": get_value(50),
            "esigibili_oltre_l_esercizio_successivo": get_value(51),
            "Totale_crediti_verso_altre_imprese": get_value(52)
        },
        "Totale_crediti": get_value(53)
    }
    
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["Altri_titoli"] = get_value(54)
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]["Strumenti_finanziari_derivati_attivi"] = get_value(55)
    bilancio["Stato_patrimoniale"]["Attivo"]["Immobilizzazioni"]["Totale_immobilizzazioni"] = get_value(56)
    
    # C - Attivo Circolante
    # I - Rimanenze
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Rimanenze"] = {
        "Materie_prime_sussidiarie_e_consumo": get_value(59),
        "Prodotti_in_corso_di_lavorazione_e_semilavorati": get_value(60),
        "Lavori_in_corso_su_ordinazione": get_value(61),
        "Prodotti_finiti_e_merci": get_value(62),
        "Accont": get_value(63),
        "Totale_rimanenze": get_value(64)
    }
    
    # II - Crediti
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Crediti"] = {
        "Verso_clienti": {
            "esigibili_entro_l_esercizio_successivo": get_value(67),
            "esigibili_oltre_l_esercizio_successivo": get_value(68),
            "Totale_crediti_verso_clienti": get_value(69)
        },
        "Verso_imprese_controllate": {
            "esigibili_entro_l_esercizio_successivo": get_value(71),
            "esigibili_oltre_l_esercizio_successivo": get_value(72),
            "Totale_crediti_verso_imprese_controllate": get_value(73)
        },
        "Verso_imprese_collegate": {
            "esigibili_entro_l_esercizio_successivo": get_value(75),
            "esigibili_oltre_l_esercizio_successivo": get_value(76),
            "Totale_crediti_verso_imprese_collegate": get_value(77)
        },
        "Verso_Controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(79),
            "esigibili_oltre_l_esercizio_successivo": get_value(80),
            "Totale_crediti_verso_controllanti": get_value(81)
        },
        "Verso_imprese_sottoposte_al_controllo_delle_controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(83),
            "esigibili_oltre_l_esercizio_successivo": get_value(84),
            "Totale_crediti_verso_imprese_sottoposte_al_controllo_delle_controllanti": get_value(85)
        },
        "Crediti_tributari": {
            "esigibili_entro_l_esercizio_successivo": get_value(87),
            "esigibili_oltre_l_esercizio_successivo": get_value(88),
            "Totale_crediti_tributari": get_value(89)
        },
        "Imposte_anticipate": get_value(90),
        "Verso_altri": {
            "esigibili_entro_l_esercizio_successivo": get_value(92),
            "esigibili_oltre_l_esercizio_successivo": get_value(93),
            "Totale_crediti_verso_altri": get_value(94)
        },
        "Totale_crediti": get_value(95)
    }
    
    # III - Attività finanziarie
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Attivita_finanziarie_che_non_costituiscono_immobilizzazioni"] = {
        "Partecipazioni_in_imprese_controllate": get_value(97),
        "Partecipazioni_in_imprese_collegate": get_value(98),
        "Partecipazioni_in_imprese_controllanti": get_value(99),
        "Partecipazioni_in_imprese_sottoposte_al_controllo_delle_controllanti": get_value(100),
        "Altre_partecipazioni": get_value(101),
        "Strumenti_finanziari_derivati_attivi": get_value(102),
        "Altri_titoli": get_value(103),
        "Totale_attivita_finanziarie": get_value(104)
    }
    
    # IV - Disponibilità liquide
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Disponibilita_liquide"] = {
        "Depositi_bancari_e_postali:": get_value(106),
        "Assegni": get_value(107),
        "Denaro_e_valori_in_cassa": get_value(108),
        "Totale_disponibilita_liquide": get_value(109)
    }
    
    bilancio["Stato_patrimoniale"]["Attivo"]["Attivo_circolante"]["Totale_attivo_circolante"] = get_value(109)
    
    # D - Ratei e risconti
    bilancio["Stato_patrimoniale"]["Attivo"]["Ratei_e_risconti"] = {
        "Ratei_attivi:": get_value(111),
        "Ratei_inattivi:": get_value(112)
    }
    
    bilancio["Stato_patrimoniale"]["Attivo"]["Totale_attivo"] = get_value(113)
    
    # STATO PATRIMONIALE PASSIVO (SPP)
    
    # A - Patrimonio Netto
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Capitale"] = get_value(116)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_da_sovrapprezzo_azioni"] = get_value(117)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_da_rivalutazioni"] = get_value(118)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_legali"] = get_value(119)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_statutarie"] = get_value(120)
    
    # Altre riserve
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Altre_riserve_distintamente"] = {
        "Riserva_straordinaria": get_value(122),
        "Riserva_da_deroghe_ex_articolo_2423_codice_civile": get_value(123),
        "Riserva_azioni_(quote)_della_societÃ _controllante": get_value(124),
        "Riserva_da_rivalutazione_delle_partecipazioni": get_value(125),
        "Versamenti_in_conto_aumento_di_capitale": get_value(126),
        "Versamenti_in_conto_futuro_aumento_di_capitale": get_value(127),
        "Versamenti_in_conto_capitale": get_value(128),
        "Versamenti_a_copertura_perdite": get_value(129),
        "Riserva_da_riduzione_capitale_sociale": get_value(130),
        "Riserva_avanzo_di_fusione": get_value(131),
        "Riserva_per_utili_su_cambi_non_realizzati": get_value(132),
        "Riserva_da_conguaglio_utili_in_corso": get_value(133),
        "Varie_altre_riserve": get_value(134),
        "Totale_altre_riserve": get_value(135)
    }
    
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi"] = get_value(136)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Utili_(perdite)_portati_a_nuovo"] = get_value(137)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Utile_(perdita)_dellesercizio"] = get_value(138)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Perdita_ripristinata_nellesercizio"] = get_value(139)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Riserva_negativa_per_azioni_proprie_in_portafoglio"] = get_value(140)
    bilancio["Stato_patrimoniale"]["Passivo"]["Patrimonio_netto"]["Totale_patrimonio_netto"] = get_value(141)
    
    # B - Fondi per rischi e oneri
    bilancio["Stato_patrimoniale"]["Passivo"]["Fondi_per_rischi_e_oneri"] = {
        "Per_trattamento_di_quiescenza": get_value(143),
        "Per_imposte_anche_differite": get_value(144),
        "Strumenti_finanziari_derivati_passivi": get_value(145),
        "Altri": get_value(146),
        "Totale_fondi_per_rischi_e_oneri": get_value(147)
    }
    
    # C - TFR
    bilancio["Stato_patrimoniale"]["Passivo"]["Trattamento_di_fine_rapporto_di_lavoro_subordinato"] = get_value(148)
    
    # D - Debiti
    bilancio["Stato_patrimoniale"]["Passivo"]["Debiti"] = {
        "Obbligazioni": {
            "esigibili_entro_l_esercizio_successivo": get_value(151),
            "esigibili_oltre_l_esercizio_successivo": get_value(152),
            "Totale_obbligazioni": get_value(153)
        },
        "Obbligazioni_convertibili": {
            "esigibili_entro_l_esercizio_successivo": get_value(155),
            "esigibili_oltre_l_esercizio_successivo": get_value(156),
            "Totale_obbligazioni_convertibili": get_value(157)
        },
        "Debiti_verso_soci_per_finanziamenti": {
            "esigibili_entro_l_esercizio_successivo": get_value(159),
            "esigibili_oltre_l_esercizio_successivo": get_value(160),
            "Totale_debiti_verso_soci_per_finanziamenti": get_value(161)
        },
        "Debiti_verso_banche": {
            "esigibili_entro_l_esercizio_successivo": get_value(163),
            "esigibili_oltre_l_esercizio_successivo": get_value(164),
            "Totale_debiti_verso_banche": get_value(165)
        },
        "Debiti_verso_altri_finanziatori": {
            "esigibili_entro_l_esercizio_successivo": get_value(167),
            "esigibili_oltre_l_esercizio_successivo": get_value(168),
            "Totale_debiti_verso_altri_finanziatori": get_value(169)
        },
        "Acconti": {
            "esigibili_entro_l_esercizio_successivo": get_value(171),
            "esigibili_oltre_l_esercizio_successivo": get_value(172),
            "Totale_acconti": get_value(173)
        },
        "Debiti_verso_fornitori": {
            "esigibili_entro_l_esercizio_successivo": get_value(175),
            "esigibili_oltre_l_esercizio_successivo": get_value(176),
            "Totale_debiti_verso_fornitori": get_value(177)
        },
        "Debiti_verso_rappresentati_da_titoli_di_credito": {
            "esigibili_entro_l_esercizio_successivo": get_value(179),
            "esigibili_oltre_l_esercizio_successivo": get_value(180),
            "Totale_debiti_verso_rappresentati_da_titoli_di_credito": get_value(181)
        },
        "Debiti_verso_imprese_controllate": {
            "esigibili_entro_l_esercizio_successivo": get_value(183),
            "esigibili_oltre_l_esercizio_successivo": get_value(184),
            "Totale_debiti_verso_imprese_controllate": get_value(185)
        },
        "Debiti_verso_imprese_collegate": {
            "esigibili_entro_l_esercizio_successivo": get_value(187),
            "esigibili_oltre_l_esercizio_successivo": get_value(188),
            "Totale_debiti_verso_imprese_collegate": get_value(189)
        },
        "Debiti_verso_controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(191),
            "esigibili_oltre_l_esercizio_successivo": get_value(192),
            "Totale_debiti_verso_controllanti": get_value(193)
        },
        "Debiti_verso_imprese_sottoposte_al_controllo_di_controllanti": {
            "esigibili_entro_l_esercizio_successivo": get_value(195),
            "esigibili_oltre_l_esercizio_successivo": get_value(196),
            "Totale_debiti_verso_imprese_sottoposte_al_controllo_delle_controllanti": get_value(197)
        },
        "Debiti_tributari": {
            "esigibili_entro_l_esercizio_successivo": get_value(199),
            "esigibili_oltre_l_esercizio_successivo": get_value(200),
            "Totale_debiti_tributari": get_value(201)
        },
        "Debiti_verso_istituti_di_previdenza_e_di_sicurezza_sociale": {
            "esigibili_entro_l_esercizio_successivo": get_value(203),
            "esigibili_oltre_l_esercizio_successivo": get_value(204),
            "Totale_debiti_verso_istituti_di_previdenza_e_di_sicurezza_sociale": get_value(205)
        },
        "Altri_debiti": {
            "esigibili_entro_l_esercizio_successivo": get_value(207),
            "esigibili_oltre_l_esercizio_successivo": get_value(208),
            "Totale_altri_debiti": get_value(209)
        },
        "Totale_debiti": get_value(210)
    }
    
    # E - Ratei e risconti passivi
    bilancio["Stato_patrimoniale"]["Passivo"]["Ratei_e_risconti"] = {
        "Ratei_passivi": get_value(212),
        "Risconti_passivi": get_value(213)
    }
    
    bilancio["Stato_patrimoniale"]["Passivo"]["Totale_passivo"] = get_value(214)
    
    # CONTO ECONOMICO (CE)
    
    # A - Valore della produzione
    bilancio["Conto_economico"]["Valore_della_produzione"]["Ricavi_delle_vendite_e_delle_prestazioni"] = get_value(217)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Variazione_delle_lavorazioni_in_corso_di_esecuzione"] = get_value(218)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Variazione_dei_lavori_in_corso_di_esecuzione"] = get_value(219)
    bilancio["Conto_economico"]["Valore_della_produzione"]["Incrementi_di_immobilizzazioni_per_lavori_interni"] = get_value(220)
    
    bilancio["Conto_economico"]["Valore_della_produzione"]["Altri_ricavi_e_proventi"] = {
        "Contributi_in_conto_esercizio": get_value(222),
        "Altri": get_value(223),
        "Totale_altri_ricavi_e_proventi": get_value(224)
    }
    
    bilancio["Conto_economico"]["Valore_della_produzione"]["Totale_valore_della_produzione"] = get_value(225)
    
    # B - Costi di produzione
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_materie_prime,_sussidiarie_di_consumo_merci"] = get_value(227)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_servizi"] = get_value(228)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_godimento_di_terzi"] = get_value(229)
    
    bilancio["Conto_economico"]["Costi_di_produzione"]["Per_personale"] = {
        "Salari_e_stipendi": get_value(231),
        "Oneri_sociali": get_value(232),
        "Trattamento_di_fine_rapporto": get_value(233),
        "Trattamento_di_quiescenza_e_simili": get_value(234),
        "Altri_costi": get_value(235),
        "Totale_costi_per_il_personale": get_value(236)
    }
    
    bilancio["Conto_economico"]["Costi_di_produzione"]["Ammortamento_e_svalutazioni"] = {
        "Ammortamento_delle_immobilizzazioni_immateriale": get_value(238),
        "Ammortamento_delle_immobilizzazioni_materiali": get_value(239),
        "Altre_svalutazioni_delle_immobilizzaioni": get_value(240),
        "Svalutazioni_dei_crediti_compresi_nell_attivo_circolante": get_value(241),
        "Totale_ammortamenti_e_svalutazioni": get_value(242)
    }
    
    bilancio["Conto_economico"]["Costi_di_produzione"]["Variazione_delle_rimanenze_di_materie_prime_sussidiarie_consumo"] = get_value(243)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Accantonamento_per_rischi"] = get_value(244)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Altri_accantonamenti"] = get_value(245)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Oneri_diversi_di_gestione"] = get_value(246)
    bilancio["Conto_economico"]["Costi_di_produzione"]["Totale_costi_della_produzione"] = get_value(247)
    
    bilancio["Conto_economico"]["Differenza_valore_produzione_costi_produzione"] = get_value(248)
    
    # C - Proventi e oneri finanziari
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Proventi_da_partecipazioni"] = {
        "Da_imprese_controllate": get_value(251),
        "Da_imprese_collegate": get_value(252),
        "Da_imprese_controllanti": get_value(253),
        "Da_imprese_sottoposte_al_controllo_delle_controllanti": get_value(254),
        "Altre_imprese": get_value(255),
        "Totale_proventi_da_partecipazioni": get_value(256)
    }
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nelle_immobilizzazioni"] = {
        "Da_imprese_controllate": get_value(259),
        "Da_imprese_collegate": get_value(260),
        "Da_imprese_controllanti": get_value(261),
        "Da_imprese_sottoposte_al_controllo_delle_controllanti": get_value(262),
        "Da_altri": get_value(263),
        "Totale_proventi_finanziari_da_crediti_iscritti_nelle_immobilizzazioni": get_value(264)
    }
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_titoli_iscritti_nelle_immobilizzazioni_diversi_dalle_partecipazioni"] = get_value(265)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Da_crediti_iscritti_nell_attivo_circolante_diversi_dalle_partecipazioni"] = get_value(266)
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Proventi_diversi_dai_precedenti"] = {
        "Da_imprese_controllate": get_value(268),
        "Da_imprese_collegate": get_value(269),
        "Da_imprese_controllanti": get_value(270),
        "Da_imprese_sottoposte_al_controllo_delle_controllanti": get_value(271),
        "Altri": get_value(272),
        "Totale_proventi_diversi_dai_precedenti_immobilizzazioni": get_value(273)
    }
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Altri_proventi_finanziari"]["Totale_altri_proventi_finanziari"] = get_value(274)
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Interessi_e_oneri_finanziari"] = {
        "Da_imprese_controllate": get_value(276),
        "Da_imprese_collegate": get_value(277),
        "Da_imprese_controllanti": get_value(278),
        "Da_imprese_sottoposte_al_controllo_delle_controllanti": get_value(279),
        "Altri": get_value(280),
        "Totale_interessi_e_altri_oneri_finanziari": get_value(281)
    }
    
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Utili_e_perdite_su_cambi"] = get_value(282)
    bilancio["Conto_economico"]["Proventi_e_oneri_finanziari"]["Totale_proventi_e_oneri_finanziari"] = get_value(283)
    
    # D - Rettifiche di valore
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie"]["Rivalutazioni"] = {
        "Di_partecipazioni": get_value(286),
        "Di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": get_value(287),
        "Di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": get_value(288),
        "Strumenti_finanziari_derivati": get_value(289)
    }
    
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie"]["Svalutazioni"] = {
        "Di_partecipazioni": get_value(292),
        "Di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": get_value(293),
        "Di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": get_value(294),
        "Strumenti_finanziari_derivati": get_value(295)
    }
    
    bilancio["Conto_economico"]["Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie"]["Totale_rettifiche_di_valore_di_attivita'_finanziarie"] = get_value(297)
    
    # E - Proventi e oneri straordinari
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Proventi_straordinari"] = get_value(299)
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Oneri_straordinari"] = get_value(300)
    bilancio["Conto_economico"]["Proventi_e_oneri_straordinari"]["Totale_delle_partite_straordinarie"] = get_value(301)
    
    # bilancio["Conto_economico"]["Risultato_prima_delle_imposte"]["Risultato_prima_delle_imposte"] = get_value(302)
    
    # Imposte
    bilancio["Conto_economico"]["Risultato_prima_delle_imposte"]["Imposte_sul_reddito_di_esercizio_correnti_differite_anticipate"] = {
        "Imposte_correnti": get_value(304),
        "Imposte_relative_esercizi_precedenti": get_value(305),
        "Imposte_differite_anticipate": get_value(306),
        "Proventi_da_adesioni_al_regime_di_copnsolidato_fiscale": get_value(307),
        "Totale_delle_imposte_sul_reddito_di_esercizio_correnti,_differite_e_anticipate": get_value(308)
    }
    
    bilancio["Conto_economico"]["Risultato_prima_delle_imposte"]["Utile_(perdita)_dell'esercizio"] = get_value(309)
    
    return bilancio


def main():
    """
    Main function to run the extraction.
    Usage: python script.py <path_to_xlsx_file>
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_xlsx_file>")
        print("\nExample: python script.py ORDINARIO_annuale.xlsx")
        return
    
    xlsx_path = sys.argv[1]
    
    if not Path(xlsx_path).exists():
        print(f"Error: File '{xlsx_path}' not found!")
        return
    
    print(f"Extracting data from: {xlsx_path}")
    
    try:
        bilancio_data = extract_bilancio_from_xlsx(xlsx_path)
        
        # Save to JSON file
        output_file = "Ordinario_Annuale.json"
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