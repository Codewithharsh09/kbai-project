"""
KBAI Predictive Service
Orchestrates the predictive engine within the Flask application context.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import models
# We need to access db models
from src.app.database.models import (
    KbaiCompany,
    KbaiBalance,
    KbaiAnalysis,
    KbaiAnalysisKpi,
    KbaiReport,
)

# Import predictive engine components
# Adjusted imports relative to the new location
from .models.balance_sheet import BalanceSheetData
from .core.historical_analyzer import HistoricalAnalyzer
from .core.parameterizer import Parameterizer, ForecastParameters
from .core.projection_engine import ProjectionEngine
from .models.scenario import ScenarioType
from flask import request
from src.common.localization import get_message
from .core.suggester_engine import SuggesterEngine

logger = logging.getLogger(__name__)


class PredictiveService:
    """
    Service to run financial projections for companies.
    Integrates the standalone prototype logic into the backend.
    """

    @staticmethod
    def generate_prediction(
        company_id: int, horizon_years: int = 3, locale: str = None
    ) -> Dict[str, Any]:
        """
        Generate a full 3-scenario prediction for a company.

        Args:
            company_id: The ID of the company to predict for.
            horizon_years: Number of years to project (default 3).
            locale: Language for suggestions (optional).

        Returns:
            Dictionary containing the full forecast results (JSON compatible).
        """
        # Pick locale from request if not provided
        if not locale:
            try:
                locale = request.headers.get("Accept-Language", "en")
            except Exception:
                locale = "en"

        try:
            # 1. Fetch Company Data
            company = KbaiCompany.query.get(company_id)
            if not company:
                raise ValueError(f"Company {company_id} not found")

            # 2. Fetch Historical Balances
            # Get all active balance sheets, ordered by year
            # Note: We filter out balances without JSON data
            balances = (
                KbaiBalance.query.filter(
                    KbaiBalance.id_company == company_id,
                    KbaiBalance.is_deleted == False,
                )
                .order_by(KbaiBalance.year.asc())
                .all()
            )

            if not balances:
                return {
                    "status": "error",
                    "message": get_message("no_balance_sheets_found", locale),
                }

            # 3. Identify Complete Balances and Base Year
            # Logic: year, type=="final", month == None consider as complete year.
            complete_balances_objs = [
                b
                for b in balances
                if b.type.lower() == "final" and (b.month is None or b.month == 12)
            ]

            if not complete_balances_objs:
                return {
                    "status": "error",
                    "message": get_message("pred_no_complete_balances", locale),
                }

            # Latest complete balance is our anchor for forecast
            base_balance_obj = max(
                complete_balances_objs, key=lambda b: (b.year, b.month or 0)
            )
            base_year = base_balance_obj.year

            historical_data = []  # Complete years up to base_year
            trimester_actuals = []  # For trimester object (data after/during base year)

            from .core.kpi_calculator import KPICalculator

            kpi_calc = KPICalculator()

            for b in balances:
                if not b.balance:
                    continue

                try:
                    m = b.month or 12
                    bs_data = BalanceSheetData.from_kbai_json(b.balance, b.year, m)
                    bs_data.company_name = company.company_name

                    # Logic for grouping
                    is_complete = b.type.lower() == "final" and (
                        b.month is None or b.month == 12
                    )

                    if is_complete and b.year <= base_year:
                        historical_data.append(bs_data)

                    # Trimester / Actuals: strictly only data for years AFTER the base year
                    if b.year > base_year:
                        ce = bs_data.conto_economico
                        sp = bs_data.stato_patrimoniale
                        raw_kpis = kpi_calc.calculate_all_kpis(
                            ricavi=ce.valore_produzione.totale,
                            ebitda=ce.ebitda,
                            ebit=ce.ebit,
                            utile_netto=ce.utile_netto,
                            patrimonio_netto=sp.passivo.patrimonio_netto.totale,
                            totale_attivo=sp.totale_attivo,
                            debiti_finanziari=sp.passivo.totale_debiti_finanziari,
                            costi_variabili=ce.costi_produzione.costi_variabili,
                            attivo_circolante=sp.attivo.circolante.totale,
                            passivo_corrente=sp.passivo.debiti_banche_breve
                            + sp.passivo.debiti_fornitori,
                            immobilizzazioni=sp.attivo.immobilizzato.totale,
                            totale_debiti=sp.passivo.totale_debiti,
                        )
                        trimester_actuals.append(
                            {
                                "year": b.year,
                                "month": b.month,
                                "type": b.type,
                                "ricavi": round(ce.valore_produzione.totale, 2),
                                "ebitda": round(ce.ebitda, 2),
                                "utile_netto": round(ce.utile_netto, 2),
                                "kpi": {
                                    k: round(v.value, 4) if hasattr(v, "value") else v
                                    for k, v in raw_kpis.items()
                                },
                            }
                        )
                except Exception as e:
                    logger.error(f"Error parsing balance {b.id_balance}: {str(e)}")

            if not historical_data:
                return {
                    "status": "error",
                    "message": get_message("pred_no_historical_trend", locale),
                }

            # 4. Run Analysis (Step 1)
            # Create Analyzer instance
            analyzer = HistoricalAnalyzer(historical_data)
            # Analyze returns self, but it computes internal state
            analyzer.analyze()

            # 5. Setup Parameters (Step 2)
            parameterizer = Parameterizer(historical_analyzer=analyzer)
            scenarios = parameterizer.get_all_scenario_parameters()

            from .models.scenario import Scenario

            # 6. Run Projections (Step 3 & 4)
            engine = ProjectionEngine(analyzer)

            results = {}
            for scenario_type, params in scenarios.items():
                name = scenario_type.value.capitalize()
                scenario_obj = Scenario(
                    name=name, parameters=params, type=scenario_type
                )
                scenario_obj.parameters.orizzonte_anni = horizon_years
                results[name] = engine.run_scenario(scenario_obj)

            # 7. Format Output
            metrics = analyzer.metrics
            comparison_data = engine.compare_scenarios(results)

            # Base data point for charting
            base_projection = engine._create_base_projection()
            base_kpis = engine._calculate_kpis(base_projection)
            base_year_str = str(base_projection.year)

            base_p_dict = base_projection.to_dict()
            base_ce = base_p_dict.get("conto_economico", {})
            base_sp = base_p_dict.get("stato_patrimoniale", {})

            formatted_base_data = {
                "year": base_projection.year,
                "ricavi": base_ce.get("ricavi", 0),
                "ebitda": base_ce.get("ebitda", 0),
                "ebit": base_ce.get("ebit", 0),
                "utile_netto": base_ce.get("utile_netto", 0),
                "patrimonio_netto": base_sp.get("patrimonio_netto", 0),
                "debiti_finanziari": base_sp.get("debiti_finanziari", 0),
                "totale_attivo": base_sp.get("totale_attivo", 0),
                "capitale_circolante": base_p_dict.get("capitale_circolante", 0),
                "dettaglio_ce": base_ce,
                "dettaglio_sp": base_sp,
                "kpi": {
                    k: round(v, 4) if isinstance(v, float) else v
                    for k, v in base_kpis.items()
                },
            }

            # 7. Format Output - Full Data for Internal/DB use
            full_output = {
                "metadata": {
                    "data_generazione": datetime.utcnow().isoformat() + "Z",
                    "anno_base": analyzer.anno_base,
                    "orizzonte_anni": horizon_years,
                    "versione_prototipo": "1.0.0",
                    "note": "Output generato dal modulo Predictive integrato",
                    "company_id": company_id,
                    "company_name": company.company_name,
                    "generated_by": "KBAI Predictive Engine",
                },
                "analisi_storica": {
                    "status": "complete",
                    "cagr_ricavi": round(metrics.cagr_ricavi, 4),
                    "cagr_ebitda": round(metrics.cagr_ebitda, 4),
                    "cagr_utile": round(metrics.cagr_utile, 4),
                    "ros_medio": round(metrics.ros_medio, 4),
                    "ebitda_margin_medio": round(metrics.ebitda_margin_medio, 4),
                    "mdc_medio": round(metrics.mdc_medio, 4),
                    "percentuali_costi": {
                        "materie_prime": round(metrics.perc_materie_prime, 4),
                        "servizi": round(metrics.perc_servizi, 4),
                        "godimento_terzi": round(metrics.perc_godimento_terzi, 4),
                        "personale": round(metrics.perc_personale, 4),
                        "costi_variabili_totale": round(
                            metrics.perc_costi_variabili, 4
                        ),
                    },
                    "capitale_circolante": {
                        "dso_medio": round(metrics.dso_medio, 1),
                        "dpo_medio": round(metrics.dpo_medio, 1),
                        "doh_medio": round(metrics.doh_medio, 1),
                    },
                    "serie_storiche": {
                        "anni": metrics.anni,
                        "ricavi": [round(r, 2) for r in metrics.ricavi_storici],
                        "ebitda": [round(e, 2) for e in metrics.ebitda_storici],
                        "utile": [round(u, 2) for u in metrics.utile_storici],
                    },
                },
                "dati_base": formatted_base_data,
                "trimester": trimester_actuals,
                "scenari": {},
                "confronto_scenari": comparison_data,
            }

            for name, result in results.items():
                formatted_previsioni = {}
                for p in result.projections:
                    year_str = str(p.year)
                    p_dict = p.to_dict()
                    ce = p_dict.get("conto_economico", {})
                    sp = p_dict.get("stato_patrimoniale", {})

                    formatted_previsioni[year_str] = {
                        "ricavi": ce.get("ricavi", 0),
                        "ebitda": ce.get("ebitda", 0),
                        "ebit": ce.get("ebit", 0),
                        "utile_netto": ce.get("utile_netto", 0),
                        "patrimonio_netto": sp.get("patrimonio_netto", 0),
                        "debiti_finanziari": sp.get("debiti_finanziari", 0),
                        "totale_attivo": sp.get("totale_attivo", 0),
                        "capitale_circolante": p_dict.get("capitale_circolante", 0),
                        "dettaglio_ce": ce,
                        "dettaglio_sp": sp,
                    }

                formatted_kpi = {}
                for year, kpis in result.kpis.items():
                    formatted_kpi[str(year)] = {
                        k: round(v, 4) if isinstance(v, float) else v
                        for k, v in kpis.items()
                    }

                full_output["scenari"][name] = {
                    "nome": name,
                    "tipo": result.scenario_type.value,
                    "modificatori": result.modifiers.to_dict(),
                    "previsioni": formatted_previsioni,
                    "kpi": formatted_kpi,
                    "warnings": result.warnings,
                }

            # 7.5 Generate Monitoraggio (Dynamic Suggestions)
            suggester = SuggesterEngine(locale=locale)
            for name, result in results.items():
                monitoraggio = suggester.generate_monitoraggio(
                    result, trimester_actuals
                )
                full_output["scenari"][name]["monitoraggio"] = monitoraggio

            # 8. Store or Update in Database (Using full_output)
            try:
                from src.extensions import db

                # Search for an existing predictive analysis for this company
                existing_analysis = (
                    KbaiAnalysis.query.join(KbaiAnalysisKpi)
                    .join(KbaiBalance)
                    .filter(
                        KbaiBalance.id_company == company_id,
                        KbaiAnalysis.analysis_type == "predictive",
                    )
                    .first()
                )
                if existing_analysis:
                    # UPDATE existing records
                    existing_analysis.time = datetime.utcnow()
                    existing_analysis.analysis_name = (
                        f"Predictive Analysis - {company.company_name}"
                    )

                    # Update associated report
                    report = KbaiReport.query.filter_by(
                        id_analysis=existing_analysis.id_analysis
                    ).first()
                    if report:
                        report.time = datetime.utcnow()

                    # Update analysis KPI record
                    if balances:
                        last_balance = balances[-1]
                        analysis_kpi = KbaiAnalysisKpi.query.filter_by(
                            id_analysis=existing_analysis.id_analysis
                        ).first()
                        if analysis_kpi:
                            analysis_kpi.id_balance = last_balance.id_balance
                            analysis_kpi.kpi_list_json = full_output
                        else:
                            KbaiAnalysisKpi.create(
                                {
                                    "id_balance": last_balance.id_balance,
                                    "id_analysis": existing_analysis.id_analysis,
                                    "kpi_list_json": full_output,
                                }
                            )
                    db.session.commit()
                    full_output["metadata"][
                        "analysis_id"
                    ] = existing_analysis.id_analysis
                    full_output["metadata"]["note"] += " (Updated existing report)"
                else:
                    # CREATE new records
                    analysis_name = f"Predictive Analysis - {company.company_name}"
                    analysis, err = KbaiAnalysis.create(
                        {
                            "analysis_name": analysis_name,
                            "analysis_type": "predictive",
                            "time": datetime.utcnow(),
                        }
                    )

                    if not err:
                        report_name = f"Prediction Report - {datetime.utcnow().strftime('%Y-%m-%d')}"
                        KbaiReport.create(
                            {
                                "id_analysis": analysis.id_analysis,
                                "name": report_name,
                                "type": "predictive",
                                "time": datetime.utcnow(),
                                "export_format": "json",
                            }
                        )

                        if balances:
                            last_balance = balances[-1]
                            KbaiAnalysisKpi.create(
                                {
                                    "id_balance": last_balance.id_balance,
                                    "id_analysis": analysis.id_analysis,
                                    "kpi_list_json": full_output,
                                }
                            )
                            full_output["metadata"][
                                "analysis_id"
                            ] = analysis.id_analysis

            except Exception as e:
                logger.error(
                    f"Exception saving/updating predictive analysis to DB: {str(e)}"
                )
                db.session.rollback()
                full_output["metadata"]["db_save_error"] = str(e)

            # 9. Return Filtered Output (Commented sections per request)
            output = {
                # "metadata": full_output["metadata"],
                # "analisi_storica": full_output["analisi_storica"],
                "dati_base": full_output["dati_base"],
                "trimester": full_output["trimester"],
                "scenari": full_output["scenari"],
                # "confronto_scenari": full_output["confronto_scenari"],
            }

            return {"status": "success", "data": output}

        except Exception as e:
            logger.exception(f"Error generating prediction for company {company_id}")
            return {"status": "error", "message": str(e)}
