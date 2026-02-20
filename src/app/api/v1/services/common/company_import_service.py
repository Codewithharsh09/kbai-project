import os
import uuid
import requests
from datetime import datetime, date
from flask import current_app
from src.common.localization import get_message
from src.extensions import db
from src.app.database.models.kbai import KbaiCompany, KbaiZone, KbaiCompanyZone, KbaiSector, KbaiCompanySector, ProvinceRegion
from src.app.database.models.kbai_balance.kbai_balances import KbaiBalance
from src.app.database.models.public.tb_licences import TbLicences
from src.app.database.models.public.licence_admin import LicenceAdmin
from src.app.database.models.public.tb_user_company import TbUserCompany
from sqlalchemy import text, func

class CreditSafeClient:
    def __init__(self):
        # Configuration from environment or defaults
        self.auth_url = os.getenv("CREDITSAFE_AUTH_URL", "https://connect.creditsafe.com/v1/authenticate")
        self.search_url = os.getenv("CREDITSAFE_SEARCH_URL", "https://connect.creditsafe.com/v1/companies/")
        self.username = os.getenv("CREDITSAFE_USERNAME")
        self.password = os.getenv("CREDITSAFE_PASSWORD")
        self.token = None

    def _authenticate(self):
        """Authenticate with CreditSafe and get JWT token."""
        if not self.username or not self.password:
            raise ValueError("CREDITSAFE_USERNAME or CREDITSAFE_PASSWORD not found in environment")
        
        resp = requests.post(
            self.auth_url,
            json={"username": self.username, "password": self.password},
            timeout=180
        )
        resp.raise_for_status()
        self.token = resp.json().get("token")
        if not self.token:
            raise RuntimeError("No token in authentication response")
        return self.token

    def search_by_vat(self, vat_number):
        """Search for company by VAT and return companyId."""
        if not self.token:
            self._authenticate()
        
        resp = requests.get(
            self.search_url,
            params={"vatNo": vat_number, "countries": "IT", "page": 1, "pageSize": 10},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=180
        )
        resp.raise_for_status()
        data = resp.json()

        companies = data.get("companies", [])
        if not companies:
            return None

        # Return the first matching company ID
        return companies[0].get("id")

    def get_company_report(self, company_id):
        """Retrieve full company data from CreditSafe."""
        if not self.token:
            self._authenticate()
            
        url = f"{self.search_url}{company_id}"
        resp = requests.get(
            url,
            params={"countries": "IT", "template": "financial"},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=180
        )
        resp.raise_for_status()
        return resp.json().get("report", {})

BALANCE_TEMPLATE = {
    "informazioni_generali": {
        "id_bilancio": ""
    },
    "Stato_patrimoniale": {
        "Attivo": {
            "Crediti_verso_soci_per_versamenti_ancora_dovuti": {
                "Parte_richiamata": 0.0,
                "Parte_da_richiamare": 0.0,
                "Totale_crediti_verso_soci_per_versamenti_ancora_dovuti": 0.0
            },
            "Immobilizzazioni": {
                "Immobilizzazioni_Immateriali": {
                    "Costi_impianto_e_di_ampliamento": 0.0,
                    "Costi_di_sviluppo": 0.0,
                    "Diritti_di_brevetto_industriale_e_diritti_di_utilizzazione_opere_dell_ingegno": 0.0,
                    "Concessioni,_licenze,_marchi_e_diritti_simili": 0.0,
                    "Avviamento": 0.0,
                    "Immobilizzazioni_in_corso_e_acconti": 0.0,
                    "Altre": 0.0,
                    "Totale_immobilizzazioni_immateriali": 0.0
                },
                "Immobilizzazioni_Materiali": {
                    "Terreni_e_fabbricati": 0.0,
                    "Impianti_e_macchinari": 0.0,
                    "Attrezzature_industriali_e_commerciali": 0.0,
                    "Altri_beni": 0.0,
                    "Immobilizzazioni_in_corso_e_acconti": 0.0,
                    "Totale_immobilizzazioni_materiali": 0.0
                },
                "Immobilizzazioni_Finanziarie": {
                    "Partecipazioni": {
                        "Imprese_controllate": 0.0,
                        "Imprese_collegate": 0.0,
                        "Imprese_controllanti": 0.0,
                        "Imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                        "Altre_imprese": 0.0,
                        "Totale_partecipazioni": 0.0
                    },
                    "Crediti": {
                        "Verso_imprese_controllate": {
                            "esigibili_entro_l_esercizio_successivo": 0.0,
                            "esigibili_oltre_l_esercizio_successivo": 0.0,
                            "Totale_crediti_verso_imprese_controllate": 0.0
                        },
                        "Verso_imprese_collegate": {
                            "esigibili_entro_l_esercizio_successivo": 0.0,
                            "esigibili_oltre_l_esercizio_successivo": 0.0,
                            "Totale_crediti_verso_imprese_collegate": 0.0
                        },
                        "Verso_imprese_controllanti": {
                            "esigibili_entro_l_esercizio_successivo": 0.0,
                            "esigibili_oltre_l_esercizio_successivo": 0.0,
                            "Totale_crediti_verso_imprese_controllanti": 0.0
                        },
                        "Imprese_sottoposte_al_controllo_delle_controllanti": {
                            "esigibili_entro_l_esercizio_successivo": 0.0,
                            "esigibili_oltre_l_esercizio_successivo": 0.0,
                            "Totale_crediti_verso_imprese_sottoposte_al_controllo_delle_controllanti": 0.0
                        },
                        "Altre_imprese": {
                            "esigibili_entro_l_esercizio_successivo": 0.0,
                            "esigibili_oltre_l_esercizio_successivo": 0.0,
                            "Totale_crediti_verso_altre_imprese": 0.0
                        },
                        "Totale_crediti": 0.0
                    },
                    "Altri_titoli": 0.0,
                    "Strumenti_finanziari_derivati_attivi": 0.0
                },
                "Totale_immobilizzazioni": 0.0
            },
            "Attivo_circolante": {
                "Rimanenze": {
                    "Materie_prime_sussidiarie_e_consumo": 0.0,
                    "Prodotti_in_corso_di_lavorazione_e_semilavorati": 0.0,
                    "Lavori_in_corso_su_ordinazione": 0.0,
                    "Prodotti_finiti_e_merci": 0.0,
                    "Accont": 0.0,
                    "Totale_rimanenze": 0.0
                },
                "Crediti": {
                    "Verso_clienti": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_clienti": 0.0
                    },
                    "Verso_imprese_controllate": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_imprese_controllate": 0.0
                    },
                    "Verso_imprese_collegate": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_imprese_collegate": 0.0
                    },
                    "Verso_Controllanti": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_controllanti": 0.0
                    },
                    "Verso_imprese_sottoposte_al_controllo_delle_controllanti": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_imprese_sottoposte_al_controllo_delle_controllanti": 0.0
                    },
                    "Crediti_tributari": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_tributari": 0.0
                    },
                    "Imposte_anticipate": 0.0,
                    "Verso_altri": {
                        "esigibili_entro_l_esercizio_successivo": 0.0,
                        "esigibili_oltre_l_esercizio_successivo": 0.0,
                        "Totale_crediti_verso_altri": 0.0
                    },
                    "Totale_crediti": 0.0
                },
                "Attivita_finanziarie_che_non_costituiscono_immobilizzazioni": {
                    "Partecipazioni_in_imprese_controllate": 0.0,
                    "Partecipazioni_in_imprese_collegate": 0.0,
                    "Partecipazioni_in_imprese_controllanti": 0.0,
                    "Partecipazioni_in_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                    "Altre_partecipazioni": 0.0,
                    "Strumenti_finanziari_derivati_attivi": 0.0,
                    "Altri_titoli": 0.0,
                    "Totale_attivita_finanziarie": 0.0
                },
                "Disponibilita_liquide": {
                    "Depositi_bancari_e_postali:": 0.0,
                    "Assegni": 0.0,
                    "Denaro_e_valori_in_cassa": 0.0,
                    "Totale_disponibilita_liquide": 0.0
                },
                "Totale_attivo_circolante": 0.0
            },
            "Ratei_e_risconti": {
                "Ratei_attivi:": 0.0,
                "Ratei_inattivi:": 0.0
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
                "Altre_riserve_distintamente": {
                    "Riserva_straordinaria": 0.0,
                    "Riserva_da_deroghe_ex_articolo_2423_codice_civile": 0.0,
                    "Riserva_azioni_(quote)_della_società_controllante": 0.0,
                    "Riserva_da_rivalutazione_delle_partecipazioni": 0.0,
                    "Versamenti_in_conto_aumento_di_capitale": 0.0,
                    "Versamenti_in_conto_futuro_aumento_di_capitale": 0.0,
                    "Versamenti_in_conto_capitale": 0.0,
                    "Versamenti_a_copertura_perdite": 0.0,
                    "Riserva_da_riduzione_capitale_sociale": 0.0,
                    "Riserva_avanzo_di_fusione": 0.0,
                    "Riserva_per_utili_su_cambi_non_realizzati": 0.0,
                    "Riserva_da_conguaglio_utili_in_corso": 0.0,
                    "Varie_altre_riserve": 0.0,
                    "Totale_altre_riserve": 0.0
                },
                "Riserve_per_operazioni_di_copertura_dei_flussi_finanziari_attesi": 0.0,
                "Utili_(perdite)_portati_a_nuovo": 0.0,
                "Utile_(perdita)_dellesercizio": 0.0,
                "Perdita_ripristinata_nellesercizio": 0.0,
                "Riserva_negativa_per_azioni_proprie_in_portafoglio": 0.0,
                "Totale_patrimonio_netto": 0.0
            },
            "Fondi_per_rischi_e_oneri": {
                "Per_trattamento_di_quiescenza": 0.0,
                "Per_imposte_anche_differite": 0.0,
                "Strumenti_finanziari_derivati_passivi": 0.0,
                "Altri": 0.0,
                "Totale_fondi_per_rischi_e_oneri": 0.0
            },
            "Trattamento_di_fine_rapporto_di_lavoro_subordinato": 0.0,
            "Debiti": {
                "Obbligazioni": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_obbligazioni": 0.0
                },
                "Obbligazioni_convertibili": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_obbligazioni_convertibili": 0.0
                },
                "Debiti_verso_soci_per_finanziamenti": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_soci_per_finanziamenti": 0.0
                },
                "Debiti_verso_banche": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_banche": 0.0
                },
                "Debiti_verso_altri_finanziatori": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_altri_finanziatori": 0.0
                },
                "Acconti": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_acconti": 0.0
                },
                "Debiti_verso_fornitori": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_fornitori": 0.0
                },
                "Debiti_verso_rappresentati_da_titoli_di_credito": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_rappresentati_da_titoli_di_credito": 0.0
                },
                "Debiti_verso_imprese_controllate": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_imprese_controllate": 0.0
                },
                "Debiti_verso_imprese_collegate": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_imprese_collegate": 0.0
                },
                "Debiti_verso_controllanti": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_controllanti": 0.0
                },
                "Debiti_verso_imprese_sottoposte_al_controllo_di_controllanti": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_imprese_sottoposte_al_controllo_delle_controllanti": 0.0
                },
                "Debiti_tributari": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_tributari": 0.0
                },
                "Debiti_verso_istituti_di_previdenza_e_di_sicurezza_sociale": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_debiti_verso_istituti_di_previdenza_e_di_sicurezza_sociale": 0.0
                },
                "Altri_debiti": {
                    "esigibili_entro_l_esercizio_successivo": 0.0,
                    "esigibili_oltre_l_esercizio_successivo": 0.0,
                    "Totale_altri_debiti": 0.0
                },
                "Totale_debiti": 0.0
            },
            "Ratei_e_risconti": {
                "Ratei_passivi": 0.0,
                "Risconti_passivi": 0.0
            },
            "Totale_passivo": 0.0
        }
    },
    "Conto_economico": {
        "Valore_della_produzione": {
            "Ricavi_delle_vendite_e_delle_prestazioni": 0.0,
            "Variazione_delle_lavorazioni_in_corso_di_esecuzione": 0.0,
            "Variazione_dei_lavori_in_corso_di_esecuzione": 0.0,
            "Incrementi_di_immobilizzazioni_per_lavori_interni": 0.0,
            "Altri_ricavi_e_proventi": {
                "Contributi_in_conto_esercizio": 0.0,
                "Altri": 0.0,
                "Totale_altri_ricavi_e_proventi": 0.0
            },
            "Totale_valore_della_produzione": 0.0
        },
        "Costi_di_produzione": {
            "Per_materie_prime,_sussidiarie_di_consumo_merci": 0.0,
            "Per_servizi": 0.0,
            "Per_godimento_di_terzi": 0.0,
            "Per_personale": {
                "Salari_e_stipendi": 0.0,
                "Oneri_sociali": 0.0,
                "Trattamento_di_fine_rapporto": 0.0,
                "Trattamento_di_quiescenza_e_simili": 0.0,
                "Altri_costi": 0.0,
                "Totale_costi_per_il_personale": 0.0
            },
            "Ammortamento_e_svalutazioni": {
                "Ammortamento_delle_immobilizzazioni_immateriale": 0.0,
                "Ammortamento_delle_immobilizzazioni_materiali": 0.0,
                "Altre_svalutazioni_delle_immobilizzaioni": 0.0,
                "Svalutazioni_dei_crediti_compresi_nell_attivo_circolante": 0.0,
                "Totale_ammortamenti_e_svalutazioni": 0.0
            },
            "Variazione_delle_rimanenze_di_materie_prime_sussidiarie_consumo": 0.0,
            "Accantonamento_per_rischi": 0.0,
            "Altri_accantonamenti": 0.0,
            "Oneri_diversi_di_gestione": 0.0,
            "Totale_costi_della_produzione": 0.0
        },
        "Differenza_valore_produzione_costi_produzione": 0.0,
        "Proventi_e_oneri_finanziari": {
            "Proventi_da_partecipazioni": {
                "Da_imprese_controllate": 0.0,
                "Da_imprese_collegate": 0.0,
                "Da_imprese_controllanti": 0.0,
                "Da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                "Altre_imprese": 0.0,
                "Totale_proventi_da_partecipazioni": 0.0
            },
            "Altri_proventi_finanziari": {
                "Da_crediti_iscritti_nelle_immobilizzazioni": {
                    "Da_imprese_controllate": 0.0,
                    "Da_imprese_collegate": 0.0,
                    "Da_imprese_controllanti": 0.0,
                    "Da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                    "Da_altri": 0.0,
                    "Totale_proventi_finanziari_da_crediti_iscritti_nelle_immobilizzazioni": 0.0
                },
                "Da_titoli_iscritti_nelle_immobilizzazioni_diversi_dalle_partecipazioni": 0.0,
                "Da_crediti_iscritti_nell_attivo_circolante_diversi_dalle_partecipazioni": 0.0,
                "Proventi_diversi_dai_precedenti": {
                    "Da_imprese_controllate": 0.0,
                    "Da_imprese_collegate": 0.0,
                    "Da_imprese_controllanti": 0.0,
                    "Da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                    "Altri": 0.0,
                    "Totale_proventi_diversi_dai_precedenti_immobilizzazioni": 0.0
                },
                "Totale_altri_proventi_finanziari": 0.0
            },
            "Interessi_e_oneri_finanziari": {
                "Da_imprese_controllate": 0.0,
                "Da_imprese_collegate": 0.0,
                "Da_imprese_controllanti": 0.0,
                "Da_imprese_sottoposte_al_controllo_delle_controllanti": 0.0,
                "Altri": 0.0,
                "Totale_interessi_e_altri_oneri_finanziari": 0.0
            },
            "Utili_e_perdite_su_cambi": 0.0,
            "Totale_proventi_e_oneri_finanziari": 0.0
        },
        "Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie ": {
            "Rivalutazioni": {
                "Di_partecipazioni": 0.0,
                "Di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": 0.0,
                "Di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": 0.0,
                "Strumenti_finanziari_derivati": 0.0
            },
            "Svalutazioni": {
                "Di_partecipazioni": 0.0,
                "Di_immobilizzazioni_finanziarie_che_non_costituiscono_partecipazioni": 0.0,
                "Di_titoli_iscritti_nell_attivo_circolante_che_non_costituiscono_partecipazioni": 0.0,
                "Strumenti_finanziari_derivati": 0.0
            },
            "Totale_rettifiche_di_valore_di_attivita'_finanziarie": 0.0
        },
        "Proventi_e_oneri_straordinari": {
            "Proventi_straordinari": 0.0,
            "Oneri_straordinari": 0.0,
            "Totale_delle_partite_straordinarie": 0.0
        },
        "Risultato_prima_delle_imposte": {
            "Imposte_sul_reddito_di_esercizio_correnti_differite_anticipate": {
                "Imposte_correnti": 0.0,
                "Imposte_relative_esercizi_precedenti": 0.0,
                "Imposte_differite_anticipate": 0.0,
                "Proventi_da_adesioni_al_regime_di_copnsolidato_fiscale": 0.0,
                "Totale_delle_imposte_sul_reddito_di_esercizio_correnti,_differite_e_anticipate": 0.0
            },
            "Utile_(perdita)_dell'esercizio": 0.0
        }
    }
}

class CompanyImportService:
    @staticmethod
    def import_by_vat(vat: str = None, locale: str = 'en'):
        """
        Lookup company by VAT in DB or CreditSafe.
        Returns a tuple of (result_data, error_message).
        Does NOT create the company in the database.
        """
        try:
            if not vat:
                return None, get_message('vat_required_lookup', locale)

            # 1. Check if company already exists in our DB
            existing = KbaiCompany.findOne(vat=vat, is_deleted=False)
            if existing:
                # Return data directly from DB
                # Get region from zone if available
                region = None
                zone_mapping = KbaiCompanyZone.query.filter_by(id_company=existing.id_company, primary_flag=True).first()
                if zone_mapping:
                    zone = KbaiZone.query.get(zone_mapping.id_zone)
                    if zone:
                        region = zone.region
                ateco = None
                division = (
    db.session.query(KbaiSector.division)
    .join(
        KbaiCompanySector,
        KbaiCompanySector.id_sector == KbaiSector.id_sector
    )
    .filter(
        KbaiCompanySector.id_company == existing.id_company
    )
    .scalar()
)
                return {
                    "message": get_message('company_found_db', locale),
                    "id_company": existing.id_company,
                    "company_data": {
                        "company_name": existing.company_name,
                        "vat": existing.vat,
                        "fiscal_code": existing.fiscal_code,
                        "phone": existing.phone,
                        "email": existing.email,
                        "region": region,
                        "ateco": division,
                        "contact_person": existing.contact_person,
                        "sdi": existing.sdi,
                        "website": existing.website
                        # Add other fields as needed for form pre-filling
                    }
                }, None

            # 2. Try CreditSafe
            try:
                client = CreditSafeClient()
                cs_id = client.search_by_vat(vat)
                
                if cs_id:
                    # 3. CreditSafe Step: Report
                    report = client.get_company_report(cs_id)
                    if report:
                        # 4. Extraction
                        company_data, zone_data, province, ateco_division = CompanyImportService._extract_data(report)
                        
                        # Prepare data for frontend
                        return {
                            "source": "creditsafe",
                            "message": get_message('company_found_creditsafe', locale),
                            "company_data": {
                                **company_data,
                                "region": zone_data.get("region") or province, # province often maps to region
                                "address": zone_data.get("address"),
                                "city": zone_data.get("city"),
                                "country": zone_data.get("country"),
                                "postal_code": zone_data.get("postal_code"),
                                "ateco": ateco_division # Returning the code we found
                            }
                        }, None
            except Exception as e:
                msg = f"CreditSafe lookup failed for VAT {vat}: {str(e)}"
                print(msg)
                current_app.logger.warning(msg)
            
            # 3. Not found
            return {
                "message": get_message('company_not_found_search', locale),
                "status": "not_found"
            }, None

        except Exception as e:
            msg = f"Error in CompanyImportService: {str(e)}"
            print(msg)
            current_app.logger.error(msg)
            return internal_error_response(
                message="An unexpected error occurred during lookup.",
                error_details=str(e)
            )

    @staticmethod
    def _extract_data(report):
        summary = report.get("companySummary", {})
        alt = report.get("alternateSummary", {})
        contact = alt.get("contactAddress", {})

        company_data = {
            "company_name": alt.get("businessName") or summary.get("businessName"),
            "vat": alt.get("vatRegistrationNumber"),
            "fiscal_code": alt.get("taxCode"),
            "phone": alt.get("telephone"),
            "email": (alt.get("emailAddresses") or "").lower() or None,
            "website": None,
        }

        zone_data = {
            "address": f"{contact.get('street', '')} {contact.get('houseNumber', '')}".strip() or None,
            "city": contact.get("city"),
            "country": contact.get("country"),
            "postal_code": contact.get("postalCode"),
            "region": None # Will hold region name if we could look it up from province later, but for now None
        }

        province = alt.get("province", "") or contact.get("province", "")
        
        # Try to look up region from province if possible
        if province:
             pr = db.session.query(ProvinceRegion).filter(text("UPPER(province) = :p")).params(p=province.upper()).first()
             if pr:
                 zone_data["region"] = pr.region

        ateco_full = summary.get("mainActivity", {}).get("code", "")
        # ATECO division is first 2 digits
        ateco_division = ateco_full[:2] if len(ateco_full) >= 2 else ateco_full

        return company_data, zone_data, province, ateco_division

    @staticmethod
    def _v(data, key, default=0.0):
        """Extract a value from dict, returns default if absent."""
        try:
            return float(data.get(key, default) or default)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _map_balance(cs_statement, id_company):
        """
        Maps a single CreditSafe financial statement into the Italian balance template.
        """
        import copy
        bal = copy.deepcopy(BALANCE_TEMPLATE)
        v = CompanyImportService._v

        pl = cs_statement.get("profitAndLoss", {})
        bs = cs_statement.get("balanceSheet", {})
        cf = cs_statement.get("cashFlow", {})
        other = cs_statement.get("otherFinancials", {})

        # ==================================================================
        # STATO PATRIMONIALE - ATTIVO
        # ==================================================================
        attivo = bal["Stato_patrimoniale"]["Attivo"]

        # -- Immobilizzazioni immateriali --
        imm_imm = attivo["Immobilizzazioni"]["Immobilizzazioni_Immateriali"]
        imm_imm["Totale_immobilizzazioni_immateriali"] = v(bs, "intangibleFixedAssets")

        # -- Immobilizzazioni materiali --
        imm_mat = attivo["Immobilizzazioni"]["Immobilizzazioni_Materiali"]
        imm_mat["Totale_immobilizzazioni_materiali"] = v(bs, "tangibleFixedAssets")

        # -- Immobilizzazioni finanziarie --
        imm_fin = attivo["Immobilizzazioni"]["Immobilizzazioni_Finanziarie"]
        imm_fin["Partecipazioni"]["Totale_partecipazioni"] = v(bs, "financialFixedAssets")

        # -- Totale immobilizzazioni --
        attivo["Immobilizzazioni"]["Totale_immobilizzazioni"] = v(bs, "totalFixedAssets")

        # -- Attivo circolante --
        ac = attivo["Attivo_circolante"]
        ac["Rimanenze"]["Totale_rimanenze"] = v(bs, "totalInventories")

        crediti = ac["Crediti"]
        crediti["Verso_clienti"]["esigibili_entro_l_esercizio_successivo"] = v(bs, "dueFromSuppliersWithin1Year")
        crediti["Verso_clienti"]["Totale_crediti_verso_clienti"] = v(bs, "dueFromSuppliersWithin1Year")
        crediti["Imposte_anticipate"] = v(other, "prepaidTax")
        crediti["Totale_crediti"] = v(bs, "totalReceivables")

        ac["Attivita_finanziarie_che_non_costituiscono_immobilizzazioni"]["Totale_attivita_finanziarie"] = v(bs, "currentFinancialAssets")
        ac["Disponibilita_liquide"]["Totale_disponibilita_liquide"] = v(bs, "liquidAssets")
        ac["Totale_attivo_circolante"] = v(bs, "totalCurrentAssets")

        attivo["Ratei_e_risconti"]["Ratei_attivi:"] = v(bs, "accruedIncomeAndPrepayments")
        attivo["Totale_attivo"] = v(bs, "totalAssets")

        # ==================================================================
        # STATO PATRIMONIALE - PASSIVO
        # ==================================================================
        passivo = bal["Stato_patrimoniale"]["Passivo"]

        pn = passivo["Patrimonio_netto"]
        pn["Capitale"] = v(bs, "shareCapital")
        pn["Altre_riserve_distintamente"]["Totale_altre_riserve"] = v(bs, "otherReserves")
        pn["Utile_(perdita)_dellesercizio"] = v(bs, "netProfitOrLossForTheYear")
        pn["Totale_patrimonio_netto"] = v(bs, "shareholdersEquity")

        passivo["Fondi_per_rischi_e_oneri"]["Totale_fondi_per_rischi_e_oneri"] = v(bs, "provisionForRisksAndCharges")
        passivo["Trattamento_di_fine_rapporto_di_lavoro_subordinato"] = v(bs, "provisionForSeveranceIndemnity")

        debiti = passivo["Debiti"]
        debiti["Debiti_verso_banche"]["esigibili_entro_l_esercizio_successivo"] = v(bs, "dueToBankWithin1Year")
        debiti["Debiti_verso_banche"]["esigibili_oltre_l_esercizio_successivo"] = v(bs, "dueToBankAfter1Year")
        debiti["Debiti_verso_banche"]["Totale_debiti_verso_banche"] = v(bs, "dueToBankWithin1Year") + v(bs, "dueToBankAfter1Year")
        debiti["Debiti_verso_fornitori"]["esigibili_entro_l_esercizio_successivo"] = v(bs, "dueToSuppliersWithin1Year")
        debiti["Debiti_verso_fornitori"]["Totale_debiti_verso_fornitori"] = v(bs, "dueToSuppliersWithin1Year")
        debiti["Altri_debiti"]["Totale_altri_debiti"] = v(bs, "otherPayables")
        debiti["Totale_debiti"] = v(bs, "totalPayables")

        passivo["Ratei_e_risconti"]["Ratei_passivi"] = v(bs, "accruedExpensesAndPrepayments")
        passivo["Totale_passivo"] = v(bs, "totalLiabilities")

        # ==================================================================
        # CONTO ECONOMICO
        # ==================================================================
        ce = bal["Conto_economico"]
        vp = ce["Valore_della_produzione"]
        vp["Ricavi_delle_vendite_e_delle_prestazioni"] = v(pl, "operatingRevenues")
        vp["Variazione_dei_lavori_in_corso_di_esecuzione"] = v(pl, "changeInWorkInProgress") or v(pl, "changeInContractWorkInProgress")
        vp["Incrementi_di_immobilizzazioni_per_lavori_interni"] = v(pl, "increasesInInternallyConstructedFixedAssets")
        vp["Altri_ricavi_e_proventi"]["Totale_altri_ricavi_e_proventi"] = v(pl, "totalOtherIncomeAndRevenues")
        vp["Totale_valore_della_produzione"] = v(pl, "totalValueOfProduction")

        cp = ce["Costi_di_produzione"]
        cp["Per_materie_prime,_sussidiarie_di_consumo_merci"] = v(pl, "purchaseOfGoods")
        cp["Per_servizi"] = v(pl, "costOfServices")
        cp["Per_godimento_di_terzi"] = v(pl, "useOfThirdPartyAssets")
        cp["Per_personale"]["Totale_costi_per_il_personale"] = v(pl, "totalPayrollAndRelatedCosts")
        cp["Ammortamento_e_svalutazioni"]["Totale_ammortamenti_e_svalutazioni"] = v(pl, "totalAmortisationDepreciationAndWriteDowns")
        cp["Variazione_delle_rimanenze_di_materie_prime_sussidiarie_consumo"] = v(pl, "changesInInventories")
        cp["Oneri_diversi_di_gestione"] = v(pl, "otherOperatingExpenses")
        cp["Totale_costi_della_produzione"] = v(pl, "totalCostOfProduction")

        ce["Differenza_valore_produzione_costi_produzione"] = v(pl, "ebit")
        ce["Proventi_e_oneri_finanziari"]["Totale_proventi_e_oneri_finanziari"] = v(pl, "totalFinancialIncomeAndExpense")
        ce["Rettifiche_di_valore_di_attivita_passivita_e_finanzianziarie "]["Totale_rettifiche_di_valore_di_attivita'_finanziarie"] = v(pl, "totalValueAdjustmentsToFinancialAssetsAndLiabilities")

        ris = ce["Risultato_prima_delle_imposte"]
        ris["Imposte_sul_reddito_di_esercizio_correnti_differite_anticipate"]["Totale_delle_imposte_sul_reddito_di_esercizio_correnti,_differite_e_anticipate"] = v(pl, "totalTaxesOnTheIncomeForTheYear")
        ris["Utile_(perdita)_dell'esercizio"] = v(pl, "profitOrLossForTheYear")

        bal["informazioni_generali"]["id_bilancio"] = str(id_company)
        return bal

    @staticmethod
    def import_company_balances(id_company, vat):
        """
        Fetch financials from CreditSafe and sync with kbai_balances table.
        Wrapped in a transaction to ensure all or none of the balance sheets are imported.
        """
        try:
            client = CreditSafeClient()
            cs_id = client.search_by_vat(vat)
            if not cs_id:
                msg = f"Company {vat} not found on CreditSafe. No balance sheet found."
                print(msg)
                current_app.logger.warning(msg)
                return

            report = client.get_company_report(cs_id)
            statements = report.get("localFinancialStatements", [])
            # Filter for Italian statutory format only
            statements = [s for s in statements if s.get("type") == "LocalFinancialsCSIT"]

            if not statements:
                msg = "No Italian statutory balance sheet found."
                print(msg)
                current_app.logger.info(f"No Italian statutory balance sheets found for company {vat}")
                return

            try:
                imported_balances = []
                with db.session.begin_nested():
                    for stmt in statements:
                        year_end = stmt.get("yearEndDate", "")
                        if not year_end: continue
                        
                        year = int(year_end[:4])
                        month = int(year_end[5:7]) if len(year_end) >= 7 else 12
                        account_format = stmt.get("final", "final")

                        # Check if balance already exists
                        existing = KbaiBalance.findOne(id_company=id_company, year=year)
                        if existing:
                            msg = f"Balance sheet for company {id_company} year {year} already exists. Skipping."
                            print(msg)
                            current_app.logger.info(msg)
                            continue

                        # Map and insert (instantiate and flush manually to avoid unintended commits inside transaction)
                        balance_json = CompanyImportService._map_balance(stmt, id_company)
                        
                        balance_data = {
                            "id_company": id_company,
                            "year": year,
                            "month": month,
                            "file": f"final {year}",
                            "type": account_format,
                            "mode": "API_CREDITSAFE",
                            "note": f"Imported from CreditSafe API ({year})",
                            "balance": balance_json
                        }
                        
                        try:
                            new_bal = KbaiBalance(**balance_data)
                            db.session.add(new_bal)
                            db.session.flush()
                            err = None
                        except Exception as e:
                            new_bal = None
                            err = str(e)
                            
                        if err:
                            msg = f"Error saving balance for company {id_company} year {year}: {err}"
                            current_app.logger.error(msg)
                            # Raising exception to trigger rollback of the with-block
                            raise Exception(msg)
                        else:
                            current_app.logger.info(f"Successfully imported balance sheet for company {id_company} year {year}")
                            # Track imported balances for KPI calculation after commit
                            imported_balances.append({
                                'id_balance': new_bal.id_balance,
                                'year': year
                            })

                # If the with block finishes without exceptions, commit the whole session to persist changes
                db.session.commit()
                msg = f"Successfully Imported all available balancesheets for company {id_company}"
                print(msg)
                current_app.logger.info(msg)

                # After commit, trigger KPI calculation and comparison for newly imported balances
                if imported_balances:
                    try:
                        from src.app.api.v1.services.k_balance.comparison_report_service import comparison_report_service
                        
                        # Sort by year ASC to calculate KPIs in order
                        imported_balances.sort(key=lambda x: x['year'])
                        
                        for bal_info in imported_balances:
                            current_app.logger.info(f"Calculating KPIs for imported balance {bal_info['id_balance']} (Year {bal_info['year']})")
                            comparison_report_service.calculate_and_store_kpis_for_balance(
                                id_balance=bal_info['id_balance'],
                                source="creditsafe_import"
                            )
                        
                        # Trigger auto-comparison starting from the latest imported year
                        latest_bal = imported_balances[-1]
                        current_app.logger.info(f"Triggering auto-comparison for company {id_company} starting from year {latest_bal['year']}")
                        comparison_report_service.auto_generate_comparison_after_upload(
                            company_id=id_company,
                            newly_uploaded_balance_id=latest_bal['id_balance'],
                            newly_uploaded_year=latest_bal['year']
                        )
                    except Exception as e:
                        current_app.logger.error(f"Error triggering auto-comparison after CreditSafe import for company {id_company}: {str(e)}")

            except Exception as e:
                db.session.rollback()
                msg = f"Transaction rolled back for company {id_company} due to error: {str(e)}"
                print(msg)
                current_app.logger.error(msg)

        except Exception as e:
            db.session.rollback()
            msg = f"Failed to import company balances for ID {id_company}: {str(e)}"
            print(msg)
            current_app.logger.error(msg)
