"""
Comparison Report Service

Handles financial KPI comparison between two balance sheets (years).
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
import logging
from flask import current_app, request
from src.common.localization import get_message

from src.app.database.models import (
    KbaiBalance,
    KbaiAnalysis,
    KbaiCompany,
    KbaiReport,
    KbaiKpiValue,
    KpiLogic,
    KbaiAnalysisKpi,
    TbUser,
    TbUserCompany,
    KbaiPreDashboard,
)
from src.app.database.models.kbai.kbai_companies import KbaiCompany
# from src.app.database.models.kbai_balance.kbai_kpi_values import KbaiKpiValue
from src.extensions import db
from .comparison_report import (
    FinancialKPIAnalyzer,
    compare_kpis,
)

logger = logging.getLogger(__name__)


# KPI code mapping: display name -> technical code
# NOTE: Adjust codes according to your formulas/DB configuration
KPI_CODE_MAP: Dict[str, str] = {
    "EBITDA": "m_cod_380",
    "EBIT_Reddito_Operativo": "m_cod_381",
    "MOL_RICAVI_%": "m_cod_382",
    "EBITDA_Margin_%": "m_cod_9360",
    "Margine_Contribuzione_%": "m_cod_384",
    "Patrimonio_Netto": "m_cod_9100",
    "Mark_Up": "m_cod_386",
    "Fatturato_Equilibrio_BEP": "m_cod_387",
    "Spese_Generali_Ratio": "m_cod_388",
    "Ricavi_Totali": "m_cod_389",
    "Costi_Variabili": "m_cod_390",
}


class ComparisonReportService:
    """Service for handling financial comparison reports"""
    
    def __init__(self):
        pass

    def _get_kpi_code(self, kpi_name: str) -> str:
        """
        Map human KPI name to technical KPI code (e.g., 'EBITDA' -> 'm_cod_380').
        Falls back to a normalized code if not found in KPI_CODE_MAP.
        """
        if kpi_name in KPI_CODE_MAP:
            return KPI_CODE_MAP[kpi_name]

        base = re.sub(r"[^A-Za-z0-9]+", "_", kpi_name.upper()).strip("_")
        return f"CUSTOM_{base}"
    
    def _is_valid_db_percentage(self, value: float) -> bool:
        """
        Validate percentage value before saving to DB.

        Currently we accept any numeric value (no artificial range limit).
        Database column uses generic NUMERIC type which can store large values.
        """
        try:
            if value is None:
                return True

            # Ensure it is numeric; any finite float is accepted
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _store_kpis_for_balance(
        self,
        id_balance: int,
        kpis: Dict[str, float],
        source: str = "comparison_report",
        comparison: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Upsert KPI values into kbai_kpi_values for a given balance.
        Continues processing even if one KPI fails.

        Raises:
            Exception: Only if all KPIs fail or critical error occurs.
        """
        errors = []
        success_count = 0
        
        for kpi_name, value in kpis.items():
            try:
                # Skip if value is None or invalid
                if value is None:
                    logger.warning(
                        f"Skipping KPI {kpi_name} for balance {id_balance}: value is None"
                    )
                    continue
                
                # Convert to float if not already
                try:
                    float_value = float(value)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Skipping KPI {kpi_name} for balance {id_balance}: invalid value {value}"
                    )
                    continue
                
                kpi_code = self._get_kpi_code(kpi_name)

                # Extract Change_% from comparison if available
                deviation = None
                if comparison and kpi_name in comparison:
                    change_pct = comparison[kpi_name].get("Change_%")
                    if change_pct is not None and change_pct != "N/A":
                        try:
                            deviation = float(change_pct)
                        except (ValueError, TypeError):
                            deviation = None

                # Determine unit: 
                # - "%" if KPI name contains "%"
                # - "" (empty) for Ratio KPIs
                # - "€" otherwise
                if "%" in kpi_name:
                    unit = "%"
                elif "Ratio" in kpi_name or "Mark_Up" in kpi_name:
                    unit = ""  # Ratio/unitless
                else:
                    unit = "€"

                kpi_data = {
                    "id_balance": id_balance,
                    "kpi_code": kpi_code,
                    "kpi_name": kpi_name,
                    "value": float_value,
                    "unit": unit,
                    "deviation": deviation,
                    "source": source,
                }

                existing = KbaiKpiValue.findOne(id_balance=id_balance, kpi_code=kpi_code)

                if existing:
                    ok, err = existing.update(
                        {
                            "kpi_name": kpi_name,
                            "value": float_value,
                            "unit": unit,
                            "deviation": deviation,
                            "source": source,
                        }
                    )
                    if not ok and err:
                        error_msg = (
                            f"Failed to update KbaiKpiValue (balance={id_balance}, "
                            f"kpi_name={kpi_name}, kpi_code={kpi_code}): {err}"
                        )
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue  # Continue with next KPI instead of raising

                    self._update_kpi_logic_for_value(existing)
                    success_count += 1
                else:
                    created_kpi_value, err = KbaiKpiValue.create(kpi_data)
                    if err:
                        error_msg = (
                            f"Failed to create KbaiKpiValue (balance={id_balance}, "
                            f"kpi_name={kpi_name}, kpi_code={kpi_code}): {err}"
                        )
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue  # Continue with next KPI instead of raising

                    self._update_kpi_logic_for_value(created_kpi_value)
                    success_count += 1

            except Exception as e:
                # Log error but continue with other KPIs
                error_msg = (
                    f"Error storing KPI (balance={id_balance}, kpi_name={kpi_name}): {str(e)}"
                )
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                continue  # Continue with next KPI
        
        # If all KPIs failed, raise an exception
        if success_count == 0 and len(kpis) > 0:
            raise Exception(
                f"Failed to store any KPIs for balance {id_balance}. Errors: {errors}"
            )
        
        # Log summary
        if errors:
            logger.warning(
                f"Stored {success_count}/{len(kpis)} KPIs for balance {id_balance}. "
                f"Errors: {len(errors)}"
            )
        else:
            logger.info(
                f"Successfully stored all {success_count} KPIs for balance {id_balance}"
            )

    def _update_kpi_logic_for_value(self, kpi_value: KbaiKpiValue) -> None:
        """
        Create or update KpiLogic row for a given KbaiKpiValue based on deviation.

        Rules:
            - deviation < 0.00   -> critical_percentage = deviation, acceptable_percentage = 0
            - deviation >= 0.00  -> acceptable_percentage = deviation, critical_percentage = 0
            - deviation is None  -> both = 0
        """
        try:
            # Normalize deviation to a float where possible.
            deviation_raw = kpi_value.deviation
            deviation: Optional[float]
            if deviation_raw is None:
                deviation = None
            else:
                try:
                    deviation = float(deviation_raw)
                except (TypeError, ValueError):
                    # For non-numeric deviations (e.g. "invalid"), treat as no deviation
                    # instead of raising. This keeps KPI logic robust to unexpected input.
                    logger.warning(
                        "Ignoring non-numeric deviation value for id_kpi %s: %r",
                        getattr(kpi_value, "id_kpi", None),
                        deviation_raw,
                    )
                    deviation = None

            critical_percentage: float = 0.0
            acceptable_percentage: float = 0.0

            if deviation is not None:
                if deviation < 0.0:
                    critical_percentage = deviation
                    acceptable_percentage = 0.0
                elif deviation >= 0.0:
                    critical_percentage = 0.0
                    acceptable_percentage = deviation
            existing_logic = KpiLogic.findOne(id_kpi=kpi_value.id_kpi)

            if existing_logic:
                ok, err = existing_logic.update(
                    {
                        "critical_percentage": critical_percentage,
                        "acceptable_percentage": acceptable_percentage,
                    }
                )
                if not ok and err:
                    logger.error(
                        "Failed to update KpiLogic for id_kpi %s: %s",
                        kpi_value.id_kpi,
                        err,
                    )
                    # Do not swallow DB error – propagate to caller
                    raise Exception(
                        f"Failed to update KpiLogic (id_kpi={kpi_value.id_kpi}): {err}"
                    )
            else:
                _, err = KpiLogic.create(
                    {
                        "id_kpi": kpi_value.id_kpi,
                        "critical_percentage": critical_percentage,
                        "acceptable_percentage": acceptable_percentage,
                    }
                )
                if err:
                    logger.error(
                        "Failed to create KpiLogic for id_kpi %s: %s",
                        kpi_value.id_kpi,
                        err,
                    )
                    # Do not swallow DB error – propagate to caller
                    raise Exception(
                        f"Failed to create KpiLogic (id_kpi={kpi_value.id_kpi}): {err}"
                    )

        except Exception as e:
            logger.error(
                "Unexpected error updating KpiLogic for id_kpi %s: %s",
                getattr(kpi_value, "id_kpi", None),
                str(e),
                exc_info=True,
            )
            # Re-raise so outer try/except surfaces the real DB error
            raise
    
    def check_company_access(
        self,
        current_user: TbUser,
        company_id: int
    ) -> Tuple[bool, str]:
        """
        Check if current user has access to a company.
        
        Args:
            current_user: Current authenticated user
            company_id: Company ID to check access for
            
        Returns:
            Tuple of (has_access, error_message)
        """
        user_role = current_user.role.lower()
        
        # Superadmin and Staff have full access
        if user_role in ['superadmin', 'staff']:
            return True, ""
        
        # Admin and User can only access assigned companies
        if user_role in ['admin', 'user']:
            user_company = TbUserCompany.query.filter_by(
                id_user=current_user.id_user,
                id_company=company_id
            ).first()
            
            if user_company:
                return True, ""

            # Competitor flow: allow access via parent_company_id assignment
            competitor_company = KbaiCompany.query.filter_by(
                id_company=company_id,
                is_competitor=True,
                is_deleted=False
            ).first()

            if competitor_company:
                parent_company_id = competitor_company.parent_company_id
                if not parent_company_id:
                    return False, get_message('invalid_competitor_company_msg', request.headers.get('Accept-Language', 'en'))

                parent_user_company = TbUserCompany.query.filter_by(
                    id_user=current_user.id_user,
                    id_company=parent_company_id
                ).first()

                if parent_user_company:
                    return True, ""

            return False, get_message('access_denied_permission', request.headers.get('Accept-Language', 'en'))
        
        return True, ""
    
    def _get_month_name(self, month: int) -> str:
        """Get month name in Italian"""
        months = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
            5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
            9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }
        return months.get(month, '')
    
    def calculate_and_store_kpis_for_balance(
        self,
        id_balance: int,
        source: str = "single_balance_upload"
    ) -> Tuple[Dict[str, Any], int]:
        """
        Calculate and store KPIs for a single balance sheet (without comparison).
        Used when uploading a balance sheet that doesn't trigger comparison generation.
        
        Args:
            id_balance: Balance sheet ID
            source: Source identifier for the KPI calculation
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = 'en'
            try:
                if request:
                    locale = request.headers.get('Accept-Language', 'en')
            except (RuntimeError, AttributeError):
                pass
            balance = KbaiBalance.query.filter_by(id_balance=id_balance, is_deleted = False).first()
            
            if not balance:
                return {
                    'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance),
                    'data': None
                }, 404
            
            if not balance.balance:
                return {
                    'message': get_message('balance_sheet_no_data', locale),
                    'data': None
                }, 400
            # Calculate KPIs using FinancialKPIAnalyzer
            analyzer = FinancialKPIAnalyzer(
                balance.balance,
                f"Year {balance.year}"
            )
            kpis = analyzer.calculate_all_kpis()
            
            # Store KPIs without comparison (comparison=None)
            try:
                self._store_kpis_for_balance(
                    id_balance=id_balance,
                    kpis=kpis,
                    source=source,
                    comparison=None,  # No comparison, just store KPIs
                )
            except Exception as e:
                logger.error(
                    f"Error storing KPI values for balance {id_balance}: {str(e)}",
                    exc_info=True
                )
                db.session.rollback()
                return {
                    "message": get_message('failed_store_kpi_values', locale),
                    "data": None,
                    "error": str(e),
                }, 500
            
            return {
                'message': get_message('kpi_calc_stored_success', locale),
                'data': {
                    'id_balance': id_balance,
                    'year': balance.year,
                    'kpis': kpis,
                    'missing_fields': analyzer.missing_fields
                }
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(
                f"Error calculating KPIs for balance {id_balance}: {str(e)}",
                exc_info=True
            )
            return {
                'message': get_message('kpi_calc_failed', locale),
                'data': None,
                'error': str(e)
            }, 500

    def auto_generate_comparison_after_upload(
        self,
        company_id: int,
        current_user: Optional[TbUser] = None,
        newly_uploaded_balance_id: int = None,
        newly_uploaded_year: int = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Automatically check and generate comparison report after balance sheet upload.
        
        Logic:
        1. Check if company has at least 2 balance sheets with balance data
        2. Sort all years and get the last 2 years
        3. If the newly uploaded year is one of the last 2 years, generate comparison between these 2 years
        4. If the newly uploaded year is not in the last 2, only calculate and store KPIs (no comparison)
        
        Args:
            company_id: Company ID
            current_user: Current authenticated user (optional)
            newly_uploaded_balance_id: ID of the newly uploaded balance sheet
            newly_uploaded_year: Year of the newly uploaded balance sheet
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = 'en'
            try:
                if request:
                    locale = request.headers.get('Accept-Language', 'en')
            except (RuntimeError, AttributeError):
                pass
                
            # Check company access if current_user is provided
            if current_user:
                has_access, error_msg = self.check_company_access(current_user, company_id)
                if not has_access:
                    return {
                        'message': error_msg,
                        'data': None,
                        'auto_generated': False
                    }, 403
            
            # Get all balance sheets with balance data, ordered by year DESC only
            # Group by year and get the most recent balance sheet for each year
            balances_by_year = (
                KbaiBalance.query
                .filter_by(id_company=company_id)
                .filter(KbaiBalance.balance.isnot(None))
                .filter(KbaiBalance.is_deleted == False)
                .order_by(KbaiBalance.year.desc(), KbaiBalance.month.desc())
                .all()
            )
            
            # Group by year and get the first (most recent month) for each year
            year_to_balance = {}
            for balance in balances_by_year:
                if balance.year not in year_to_balance:
                    year_to_balance[balance.year] = balance
            
            # Get unique years sorted ascending (to get last 2 easily)
            unique_years = sorted(year_to_balance.keys())
            # Check if we have at least 2 balance sheets (from different years)
            if len(unique_years) < 2:
                logger.info(
                    f"Company {company_id} has balance sheets from only {len(unique_years)} year(s). "
                    "At least 2 different years are required for comparison. "
                    "Calculating KPIs for uploaded balance sheet only."
                )
                kpi_result, kpi_status = self.calculate_and_store_kpis_for_balance(
                    id_balance=newly_uploaded_balance_id,
                    source="single_balance_upload"
                    )
                return {
                'message': get_message('insufficient_balance_sheets', locale),
                'data': {
                    'balance_count': len(unique_years),
                    'required': 2,
                    'kpis_calculated': kpi_result.get('data') is not None
                },
                'auto_generated': False
                    }, 200
                
                # Calculate and store KPIs for the newly uploaded balance
            kpi_result, kpi_status = self.calculate_and_store_kpis_for_balance(
                id_balance=newly_uploaded_balance_id,
                source="single_balance_upload"
            )
            
            # Get the last 2 years (after sorting ascending)
            last_two_years = unique_years[-2:]  # Last 2 years
            last_year = last_two_years[1]  # Newer year (last)
            second_last_year = last_two_years[0]  # Older year (second last)
            
            last_balance = year_to_balance[last_year]
            second_last_balance = year_to_balance[second_last_year]
            
            # Check if the newly uploaded year is one of the last 2 years
            if newly_uploaded_year in last_two_years:
                # Check if comparison already exists for these two balance sheets
                existing_analysis = (
                    db.session.query(KbaiAnalysis)
                    .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                    .filter(
                        KbaiAnalysisKpi.id_balance.in_([last_balance.id_balance, second_last_balance.id_balance]),
                        KbaiAnalysis.analysis_type == 'year_comparison'
                    )
                    .group_by(KbaiAnalysis.id_analysis)
                    .having(db.func.count(KbaiAnalysisKpi.id_balance.distinct()) == 2)
                    .order_by(KbaiAnalysis.time.desc())
                    .first()
                )
                
                if existing_analysis:
                    logger.info(
                        f"Comparison report already exists for years {second_last_year} and {last_year}. "
                        "Skipping regeneration."
                    )
                    return {
                        'message': get_message('comparison_report_exists', locale),
                        'data': {
                            'existing_analysis_id': existing_analysis.id_analysis,
                            'year1': second_last_year,
                            'year2': last_year,
                            'id_balance_year1': second_last_balance.id_balance,
                            'id_balance_year2': last_balance.id_balance
                        },
                        'auto_generated': False
                    }, 200
                
                # Generate comparison report between the last 2 years
                # Order: older year first, newer year second
                logger.info(
                    f"Auto-generating comparison report for company {company_id} between "
                    f"balance {second_last_balance.id_balance} ({second_last_year}) and "
                    f"balance {last_balance.id_balance} ({last_year})"
                )
                
                response_data, status_code = self.generate_comparison_report(
                    id_balance_year1=second_last_balance.id_balance,  # Older year
                    id_balance_year2=last_balance.id_balance,  # Newer year
                    current_user=current_user,
                    analysis_name=f"Auto-generated: {second_last_year} vs {last_year}",
                    debug_mode=False
                )
                
                if status_code == 201:
                    return {
                        'message': get_message('comparison_report_auto_generated_success', locale),
                        'data': response_data.get('data'),
                        'auto_generated': True
                    }, 201
                else:
                    logger.warning(
                        f"Failed to auto-generate comparison report: {response_data.get('message', 'Unknown error')}"
                    )
                    return {
                        'message': get_message('comparison_report_auto_generated_failed', locale),
                        'data': response_data,
                        'auto_generated': False
                    }, status_code
            
            else:
                # Newly uploaded year is not in the last 2 years
                # Just calculate and store KPIs for the uploaded balance sheet
                logger.info(
                    f"Newly uploaded year {newly_uploaded_year} is not in the last 2 years ({last_two_years}). "
                    f"Calculating KPIs for balance {newly_uploaded_balance_id} without comparison."
                )
                
                kpi_result, kpi_status = self.calculate_and_store_kpis_for_balance(
                    id_balance=newly_uploaded_balance_id,
                    source="single_balance_upload"
                )
                return {
                    'message': get_message('kpi_calc_uploaded_no_comparison', locale),
                    'data': {
                        'last_two_years': last_two_years,
                        'uploaded_year': newly_uploaded_year,
                        'kpis_calculated': kpi_result.get('data') is not None,
                        'kpi_data': kpi_result.get('data')
                    },
                    'auto_generated': False
                }, 200
                
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(
                f"Error in auto_generate_comparison_after_upload for company {company_id}: {str(e)}",
                exc_info=True
            )
            # Don't fail the upload if auto-generation fails
            return {
                'message': get_message('comparison_report_generation_error', locale),
                'data': None,
                'error': str(e),
                'auto_generated': False
            }, 500
    
    def generate_comparison_report(
        self,
        id_balance_year1: int,
        id_balance_year2: int,
        current_user: Optional[TbUser] = None,
        analysis_name: Optional[str] = None,
        debug_mode: bool = False
    ) -> Tuple[Dict[str, Any], int]:
        """
        Generate comparison report between two balance sheets.
        
        Args:
            id_balance_year1: Balance sheet ID for year 1
            id_balance_year2: Balance sheet ID for year 2
            current_user: Current authenticated user (optional)
            analysis_name: Optional custom name for the analysis
            debug_mode: Include debug information in response
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = 'en'
            try:
                if request:
                    locale = request.headers.get('Accept-Language', 'en')
            except (RuntimeError, AttributeError):
                pass
            # Fetch balance sheets
            balance_year1 = KbaiBalance.query.filter_by(
                id_balance=id_balance_year1,
            ).first()
            
            balance_year2 = KbaiBalance.query.filter_by(
                id_balance=id_balance_year2,
            ).first()
            
            if not balance_year1:
                return {
                    'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance_year1),
                    'data': None
                }, 404
            
            if not balance_year2:
                return {
                    'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance_year2),
                    'data': None
                }, 404
            
            # Check access to both companies if current_user is provided
            if current_user:
                has_access, error_msg = self.check_company_access(
                    current_user, 
                    balance_year1.id_company
                )
                if not has_access:
                    return {
                        'message': error_msg,
                        'data': None
                    }, 403
                
                has_access, error_msg = self.check_company_access(
                    current_user, 
                    balance_year2.id_company
                )
                if not has_access:
                    return {
                        'message': error_msg,
                        'data': None
                    }, 403
            
            # Verify both balances belong to same company
            if balance_year1.id_company != balance_year2.id_company:
                return {
                    'message': get_message('balance_sheet_same_company_required', locale),
                    'data': None
                }, 400
            
            # Check if balance data exists
            if not balance_year1.balance:
                return {
                    'message': get_message('balance_sheet_id_no_data', locale, id_balance=id_balance_year1),
                    'data': None
                }, 400
            
            if not balance_year2.balance:
                return {
                    'message': get_message('balance_sheet_id_no_data', locale, id_balance=id_balance_year2),
                    'data': None
                }, 400
            
            # Analyze both years using existing FinancialKPIAnalyzer
            analyzer1 = FinancialKPIAnalyzer(
                balance_year1.balance, 
                f"Year {balance_year1.year}"
            )
            kpis_year1 = analyzer1.calculate_all_kpis()
            
            analyzer2 = FinancialKPIAnalyzer(
                balance_year2.balance, 
                f"Year {balance_year2.year}"
            )
            kpis_year2 = analyzer2.calculate_all_kpis()

            # Compare KPIs using existing compare_kpis function
            comparison = compare_kpis(kpis_year1, kpis_year2)

            # Store KPI values in kbai_kpi_values for both balances
            try:
                self._store_kpis_for_balance(
                    id_balance=balance_year1.id_balance,
                    kpis=kpis_year1,
                    source=f"comparison_year_{balance_year1.year}",
                    comparison=comparison,
                )
                self._store_kpis_for_balance(
                    id_balance=balance_year2.id_balance,
                    kpis=kpis_year2,
                    source=f"comparison_year_{balance_year2.year}",
                    comparison=comparison,
                )
            except Exception as e:
                logger.error(
                    "Error storing KPI values into KbaiKpiValue: %s",
                    str(e),
                    exc_info=True,
                )
                db.session.rollback()
                return {
                    "message": get_message('failed_store_kpi_values', locale),
                    "data": None,
                    "error": str(e),
                }, 500
            
            # Combine missing fields
            all_missing = list(set(analyzer1.missing_fields + analyzer2.missing_fields))
            
            # Create report data
            report_data = {
                "KPIs_Year1": kpis_year1,
                "KPIs_Year2": kpis_year2,
                "Comparison": comparison,
                "Missing_Fields": all_missing if all_missing else ["None"],
                "Status": "complete" if not all_missing else "complete_with_warnings",
                "Year1": balance_year1.year,
                "Year2": balance_year2.year,
                "Year1_Balance_ID": id_balance_year1,
                "Year2_Balance_ID": id_balance_year2
            }
            
            # Add debug information if requested
            if debug_mode:
                report_data["Debug_Info"] = {
                    "Year1": analyzer1.debug_info,
                    "Year2": analyzer2.debug_info
                }
            
            # Create analysis record
            analysis_name = analysis_name or f"Comparison {balance_year1.year} vs {balance_year2.year}"
            analysis, error = KbaiAnalysis.create({
                'analysis_name': analysis_name,
                'analysis_type': 'year_comparison',
                'time': datetime.utcnow()
            })
            
            if error:
                logger.error(f"Failed to create analysis: {error}")
                return {
                    'message': get_message('failed_create_analysis', locale),
                    'data': None,
                    'error': error
                }, 500
            
            # Create report record
            company_obj = KbaiCompany.query.filter_by(id_company=balance_year1.id_company).first()
            company_name = company_obj.company_name if company_obj and hasattr(company_obj, "company_name") else "Company"
            years_sorted = sorted([balance_year1.year, balance_year2.year])
            report_name = f"{company_name}-{years_sorted[0]}-{years_sorted[1]}"

            report, error = KbaiReport.create({
                'id_analysis': analysis.id_analysis,
                'name': report_name,
                'type': 'year_comparison',
                'time': datetime.utcnow(),
                'export_format': 'json'
            })
            
            if error:
                logger.error(f"Failed to create report: {error}")
                return {
                    'message': get_message('failed_create_report', locale),
                    'data': None,
                    'error': error
                }, 500
            
            # Store KPI comparison for year 1
            analysis_kpi1, error = KbaiAnalysisKpi.create({
                'id_balance': id_balance_year1,
                'id_analysis': analysis.id_analysis,
                'kpi_list_json': {
                    'kpis': kpis_year1,
                    'year': balance_year1.year,
                    'missing_fields': analyzer1.missing_fields
                }
            })
            
            if error:
                logger.error(f"Failed to create analysis KPI for year 1: {error}")
            
            # Store KPI comparison for year 2
            analysis_kpi2, error = KbaiAnalysisKpi.create({
                'id_balance': id_balance_year2,
                'id_analysis': analysis.id_analysis,
                'kpi_list_json': {
                    'kpis': kpis_year2,
                    'year': balance_year2.year,
                    'missing_fields': analyzer2.missing_fields
                }
            })
            
            if error:
                logger.error(f"Failed to create analysis KPI for year 2: {error}")
            
            # Prepare response
            response_data = {
                'id_analysis': analysis.id_analysis,
                'id_report': report.id_report,
                'analysis_name': analysis.analysis_name,
                'report_name': report.name,
                'year1': balance_year1.year,
                'year2': balance_year2.year,
                'id_balance_year1': id_balance_year1,
                'id_balance_year2': id_balance_year2,
                'comparison_data': report_data,
                # 'created_at': analysis.created_at.isoformat() if analysis.created_at else None
            }
            
            # # Update pre-dashboard step_compare to true after successful report generation
            # try:
            #     pre_dashboard = KbaiPreDashboard.findOne(id_company=balance_year1.id_company)
            #     if pre_dashboard:
            #         success, update_error = pre_dashboard.update({'step_compare': True,'step_competitor': True})

            #         if success:
            #             logger.info(f"Updated step_compare to true for company {balance_year1.id_company} after comparison report generation")
            #         else:
            #             logger.warning(f"Failed to update step_compare for company {balance_year1.id_company}: {update_error}")
            #     else:
            #         logger.warning(f"Pre-dashboard not found for company {balance_year1.id_company}, cannot update step_compare")
            # except Exception as e:
            #     # Log error but don't fail the report generation
            #     logger.error(f"Error updating pre-dashboard step_compare for company {balance_year1.id_company}: {str(e)}")
            
            return {
                'message': get_message('comparison_report_generated_success', locale),
                'data': response_data
            }, 201
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(f"Error generating comparison report: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                'message': get_message('comparison_report_generation_failed', locale),
                'data': None,
                'error': str(e)
            }, 500

    def get_comparison_report_by_company_id(
        self,
        company_id: int,
        current_user: TbUser
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get latest comparison report for a company along with all previous comparisons.
        Also includes KPIs from kbai_kpi_values for years that don't have comparison reports.
        
        Args:
            company_id: Company ID
            current_user: Current authenticated user
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Check company access
            has_access, error_msg = self.check_company_access(current_user, company_id)
            if not has_access:
                return {
                    'message': error_msg,
                    'data': None
                }, 403
            
            # Get all balance sheets for this company with balance data
            all_balances = (
                KbaiBalance.query
                .filter_by(id_company=company_id)
                .filter(KbaiBalance.balance.isnot(None))
                .filter(KbaiBalance.is_deleted == False)
                .order_by(KbaiBalance.year.desc())
                .all()
            )
            
            if not all_balances:
                return {
                    'message': get_message('no_balance_sheets_found', locale),
                    'data': None
                }, 404
            
            # Check if we have at least 2 balance sheets (by unique years)
            unique_years = set(balance.year for balance in all_balances)
            if len(unique_years) < 2:
                return {
                    'message': get_message('min_balance_sheets_required', locale),
                    'data': {
                        'data': None
                    }
                }, 200
            
            # Auto-generate comparison for last 2 years if it doesn't exist
            # Group by year and get the first (most recent month) for each year
            year_to_balance = {}
            for balance in all_balances:
                if balance.year not in year_to_balance:
                    year_to_balance[balance.year] = balance
            
            # Get unique years sorted ascending (to get last 2 easily)
            sorted_years = sorted(year_to_balance.keys())
            
            # Get the last 2 years
            if len(sorted_years) >= 2:
                last_two_years = sorted_years[-2:]  # Last 2 years
                last_year = last_two_years[1]  # Newer year (last)
                second_last_year = last_two_years[0]  # Older year (second last)
                
                last_balance = year_to_balance[last_year]
                second_last_balance = year_to_balance[second_last_year]
                
                # Check if comparison already exists for these two balance sheets
                existing_analysis = (
                    db.session.query(KbaiAnalysis)
                    .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                    .filter(
                        KbaiAnalysisKpi.id_balance.in_([last_balance.id_balance, second_last_balance.id_balance]),
                        KbaiAnalysis.analysis_type == 'year_comparison'
                    )
                    .group_by(KbaiAnalysis.id_analysis)
                    .having(db.func.count(KbaiAnalysisKpi.id_balance.distinct()) == 2)
                    .order_by(KbaiAnalysis.time.desc())
                    .first()
                )
                
                # If no comparison exists, generate it automatically
                if not existing_analysis:
                    logger.info(
                        f"Auto-generating comparison for company {company_id} between "
                        f"years {second_last_year} and {last_year} (last 2 years)"
                    )
                    try:
                        response_data, status_code = self.generate_comparison_report(
                            id_balance_year1=second_last_balance.id_balance,  # Older year
                            id_balance_year2=last_balance.id_balance,  # Newer year
                            current_user=current_user,
                            analysis_name=f"Auto-generated for last 2 years (Years {second_last_year}-{last_year})"
                        )
                        if status_code == 201:
                            logger.info(
                                f"Successfully auto-generated comparison report. "
                                f"Analysis ID: {response_data.get('data', {}).get('id_analysis', 'N/A')}"
                            )
                        else:
                            logger.warning(
                                f"Failed to auto-generate comparison: {response_data.get('message', 'Unknown error')}"
                            )
                    except Exception as e:
                        # Log error but don't fail the GET request
                        logger.error(
                            f"Error auto-generating comparison in GET API: {str(e)}",
                            exc_info=True
                        )
            
            # Get all analyses for this company through balance sheets
            # Filter out analyses that reference deleted balance sheets
            analyses_query = (
                db.session.query(KbaiAnalysis)
                .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                .join(KbaiBalance, KbaiAnalysisKpi.id_balance == KbaiBalance.id_balance)
                .filter(
                    KbaiBalance.id_company == company_id,
                    KbaiBalance.is_deleted == False,  # Filter out deleted balance sheets
                    KbaiAnalysis.analysis_type == 'year_comparison'
                )
                .distinct()
                .order_by(KbaiAnalysis.time.desc())
            )
            
            all_analyses = analyses_query.all()
            
            # Collect all years' KPI values from all sources
            all_years_kpis = {}  # {kpi_name: {year: value}}
            latest_comparison_metrics = {}  # {kpi_name: {Absolute_Change, Change_%}}
            latest_kpis_year1 = {}
            latest_kpis_year2 = {}
            
            # Step 1: Get KPIs from comparison reports (KbaiAnalysisKpi)
            # Find the latest valid comparison (where both balance sheets exist and are not deleted)
            if all_analyses:
                latest_analysis = None
                latest_kpi_data = []
                
                for analysis in all_analyses:
                    # Get analysis KPIs for this comparison
                    analysis_kpis = (
                        KbaiAnalysisKpi.query
                        .filter_by(id_analysis=analysis.id_analysis)
                        .all()
                    )
                    
                    if len(analysis_kpis) >= 2:
                        # Get balance sheets for this comparison (filter deleted)
                        balance_ids = [ak.id_balance for ak in analysis_kpis]
                        balances = (
                            KbaiBalance.query
                            .filter(KbaiBalance.id_balance.in_(balance_ids))
                            .filter(KbaiBalance.is_deleted == False)  # Filter out deleted balance sheets
                            .all()
                        )
                        balance_dict = {b.id_balance: b for b in balances}
                        
                        # Check if we have both balance sheets (valid comparison)
                        valid_kpi_data = []
                        for ak in analysis_kpis:
                            balance = balance_dict.get(ak.id_balance)
                            if balance and balance.is_deleted == False and ak.kpi_list_json:  # Only process if balance exists and is not deleted
                                year = balance.year
                                kpis = ak.kpi_list_json.get('kpis', {})
                                valid_kpi_data.append({
                                    'year': year,
                                    'kpis': kpis
                                })
                        
                        # Only use this as latest if we have both years (valid comparison)
                        if len(valid_kpi_data) >= 2:
                            # Sort by year to ensure correct order (older first, newer second)
                            valid_kpi_data.sort(key=lambda x: x['year'])
                            latest_kpi_data = valid_kpi_data
                            latest_analysis = analysis
                            latest_kpis_year1 = latest_kpi_data[0]['kpis']  # Older year
                            latest_kpis_year2 = latest_kpi_data[1]['kpis']  # Newer year
                            
                            # Store all years' values from latest comparison
                            for kpi_data in latest_kpi_data:
                                year = kpi_data['year']
                                kpis = kpi_data['kpis']
                                for kpi_name, kpi_value in kpis.items():
                                    if kpi_name not in all_years_kpis:
                                        all_years_kpis[kpi_name] = {}
                                    all_years_kpis[kpi_name][year] = float(kpi_value) if kpi_value is not None else 0.0
                            
                            # Calculate latest comparison metrics (newer vs older)
                            if latest_kpis_year1 and latest_kpis_year2:
                                latest_comparison = compare_kpis(latest_kpis_year1, latest_kpis_year2)
                                for kpi_name, comparison_data in latest_comparison.items():
                                    latest_comparison_metrics[kpi_name] = {
                                        'Absolute_Change': comparison_data.get('Absolute_Change'),
                                        'Change_%': comparison_data.get('Change_%')
                                    }
                            
                            # Found valid latest comparison, break
                            break
                
                # Process remaining comparisons (previous comparisons) to get more years' data
                # Skip the latest_analysis if we found one
                analyses_to_process = all_analyses
                if latest_analysis:
                    # Skip the latest analysis and any analyses before it (they're already processed or invalid)
                    latest_index = next((i for i, a in enumerate(all_analyses) if a.id_analysis == latest_analysis.id_analysis), -1)
                    analyses_to_process = all_analyses[latest_index + 1:] if latest_index >= 0 else all_analyses
                
                for prev_analysis in analyses_to_process:
                    prev_analysis_kpis = (
                        KbaiAnalysisKpi.query
                        .filter_by(id_analysis=prev_analysis.id_analysis)
                        .all()
                    )
                    
                    if len(prev_analysis_kpis) >= 2:
                        prev_balance_ids = [ak.id_balance for ak in prev_analysis_kpis]
                        prev_balances = (
                            KbaiBalance.query
                            .filter(KbaiBalance.id_balance.in_(prev_balance_ids))
                            .filter(KbaiBalance.is_deleted == False)  # Filter out deleted balance sheets
                            .all()
                        )
                        
                        prev_balance_dict = {b.id_balance: b for b in prev_balances}
                        
                        # Only process if we have both balance sheets (valid comparison)
                        prev_kpi_data = []
                        for ak in prev_analysis_kpis:
                            balance = prev_balance_dict.get(ak.id_balance)
                            if balance and balance.is_deleted == False and ak.kpi_list_json:  # Only process if balance exists and is not deleted
                                year = balance.year
                                kpis = ak.kpi_list_json.get('kpis', {})
                                prev_kpi_data.append({
                                    'year': year,
                                    'kpis': kpis
                                })
                        
                        # Only store data if we have a valid comparison (both years)
                        if len(prev_kpi_data) >= 2:
                            for kpi_data in prev_kpi_data:
                                year = kpi_data['year']
                                kpis = kpi_data['kpis']
                                
                                # Store all years' values
                                for kpi_name, kpi_value in kpis.items():
                                    if kpi_name not in all_years_kpis:
                                        all_years_kpis[kpi_name] = {}
                                    # Only add if not already present (comparison data takes priority)
                                    if year not in all_years_kpis[kpi_name]:
                                        all_years_kpis[kpi_name][year] = float(kpi_value) if kpi_value is not None else 0.0
            
            # Step 2: Get KPIs from kbai_kpi_values for all balance sheets
            # This will include years that don't have comparison reports (like 2025)
            all_balance_ids = [b.id_balance for b in all_balances]
            
            kpi_values = (
                KbaiKpiValue.query
                .filter(KbaiKpiValue.id_balance.in_(all_balance_ids))
                .all()
            )
            
            # Group KPI values by balance_id and then by kpi_name
            balance_kpis = {}  # {id_balance: {kpi_name: value}}
            for kpi_value in kpi_values:
                if kpi_value.id_balance not in balance_kpis:
                    balance_kpis[kpi_value.id_balance] = {}
                balance_kpis[kpi_value.id_balance][kpi_value.kpi_name] = float(kpi_value.value) if kpi_value.value is not None else 0.0
            
            # Add KPIs from kbai_kpi_values to all_years_kpis
            for balance in all_balances:
                if balance.id_balance in balance_kpis:
                    year = balance.year
                    kpis = balance_kpis[balance.id_balance]
                    
                    for kpi_name, kpi_value in kpis.items():
                        if kpi_name not in all_years_kpis:
                            all_years_kpis[kpi_name] = {}
                        # Only add if not already present (comparison data takes priority)
                        if year not in all_years_kpis[kpi_name]:
                            all_years_kpis[kpi_name][year] = kpi_value
            
            # Build final Comparison object
            final_comparison = {}
            for kpi_name, years_data in all_years_kpis.items():
                final_comparison[kpi_name] = {}
                
                # Add all years' values (sorted by year)
                for year in sorted(years_data.keys()):
                    final_comparison[kpi_name][str(year)] = years_data[year]
                
                # Add latest comparison metrics (only if we have a comparison)
                if kpi_name in latest_comparison_metrics:
                    final_comparison[kpi_name]['Absolute_Change'] = latest_comparison_metrics[kpi_name]['Absolute_Change']
                    final_comparison[kpi_name]['Change_%'] = latest_comparison_metrics[kpi_name]['Change_%']
            
            # Get missing fields from latest analysis if available
            all_missing = []
            if all_analyses:
                latest_analysis = all_analyses[0]
                analysis_kpis = (
                    KbaiAnalysisKpi.query
                    .filter_by(id_analysis=latest_analysis.id_analysis)
                    .all()
                )
                for ak in analysis_kpis:
                    if ak.kpi_list_json and ak.kpi_list_json.get('missing_fields'):
                        all_missing.extend(ak.kpi_list_json.get('missing_fields', []))
            all_missing = list(set(all_missing))
            
            # Prepare response
            response_data = {
                'Comparison': final_comparison,
                'Status': "complete" if not all_missing else "complete_with_warnings"
            }
            
            return {
                'message': get_message('comparison_reports_retrieved_success', locale),
                'data': response_data
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(f"Error getting comparison reports by company ID: {str(e)}", exc_info=True)
            return {
                'message': get_message('comparison_reports_retrieve_failed', locale),
                'data': None,
                'error': str(e)
            }, 500

    def auto_generate_comparison_after_delete(
        self,
        company_id: int,
        current_user: TbUser,
        deleted_balance_id: int
    ) -> Tuple[Dict[str, Any], int]:
        """
        Automatically check and generate comparison report after balance sheet deletion.
        
        Logic:
        1. Get all remaining active balance sheets for the company
        2. Sort years and get the last 2 years
        3. Check if comparison exists for the last 2 years
        4. If comparison exists, return (nothing to do)
        5. If comparison doesn't exist, generate comparison between last 2 years
        
        Args:
            company_id: Company ID
            current_user: Current authenticated user
            deleted_balance_id: ID of the deleted balance sheet (for logging)
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Check company access
            has_access, error_msg = self.check_company_access(current_user, company_id)
            if not has_access:
                return {
                    'message': error_msg,
                    'data': None,
                    'auto_generated': False
                }, 403
            
            # Get all remaining active balance sheets with balance data, ordered by year DESC
            balances_by_year = (
                KbaiBalance.query
                .filter_by(id_company=company_id)
                .filter(KbaiBalance.balance.isnot(None))
                .filter(KbaiBalance.is_deleted == False)
                .order_by(KbaiBalance.year.desc(), KbaiBalance.month.desc())
                .all()
            )
            
            # Group by year and get the first (most recent month) for each year
            year_to_balance = {}
            for balance in balances_by_year:
                if balance.year not in year_to_balance:
                    year_to_balance[balance.year] = balance
            
            # Get unique years sorted ascending (to get last 2 easily)
            unique_years = sorted(year_to_balance.keys())
            
            # Check if we have at least 2 balance sheets (from different years)
            if len(unique_years) < 2:
                logger.info(
                    f"Company {company_id} has balance sheets from only {len(unique_years)} year(s) after deletion. "
                    "At least 2 different years are required for comparison."
                )
                return {
                    'message': get_message('insufficient_balance_sheets', locale),
                    'data': {
                        'balance_count': len(unique_years),
                        'required': 2
                    },
                    'auto_generated': False
                }, 200
            
            # Get the last 2 years (after sorting ascending)
            last_two_years = unique_years[-2:]  # Last 2 years
            last_year = last_two_years[1]  # Newer year (last)
            second_last_year = last_two_years[0]  # Older year (second last)
            
            last_balance = year_to_balance[last_year]
            second_last_balance = year_to_balance[second_last_year]
            
            # Check if comparison already exists for these two balance sheets
            existing_analysis = (
                db.session.query(KbaiAnalysis)
                .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                .filter(
                    KbaiAnalysisKpi.id_balance.in_([last_balance.id_balance, second_last_balance.id_balance]),
                    KbaiAnalysis.analysis_type == 'year_comparison'
                )
                .group_by(KbaiAnalysis.id_analysis)
                .having(db.func.count(KbaiAnalysisKpi.id_balance.distinct()) == 2)
                .order_by(KbaiAnalysis.time.desc())
                .first()
            )
            
            if existing_analysis:
                logger.info(
                    f"Comparison report already exists for years {second_last_year} and {last_year} after deletion. "
                    "No regeneration needed."
                )
                return {
                    'message': get_message('comparison_report_exists', locale),
                    'data': {
                        'existing_analysis_id': existing_analysis.id_analysis,
                        'year1': second_last_year,
                        'year2': last_year,
                        'id_balance_year1': second_last_balance.id_balance,
                        'id_balance_year2': last_balance.id_balance
                    },
                    'auto_generated': False
                }, 200
            
            # Generate comparison report between the last 2 years
            # Order: older year first, newer year second
            logger.info(
                f"Auto-generating comparison report for company {company_id} after deletion. "
                f"Comparing balance {second_last_balance.id_balance} ({second_last_year}) and "
                f"balance {last_balance.id_balance} ({last_year})"
            )
            
            response_data, status_code = self.generate_comparison_report(
                id_balance_year1=second_last_balance.id_balance,  # Older year
                id_balance_year2=last_balance.id_balance,  # Newer year
                current_user=current_user,
                analysis_name=f"Auto-generated after deletion (Years {second_last_year}-{last_year})"
            )
            
            if status_code == 201:
                return {
                    'message': get_message('comparison_report_auto_generated_success', locale),
                    'data': {
                        'id_analysis': response_data.get('data', {}).get('id_analysis'),
                        'year1': second_last_year,
                        'year2': last_year,
                        'id_balance_year1': second_last_balance.id_balance,
                        'id_balance_year2': last_balance.id_balance
                    },
                    'auto_generated': True
                }, 200
            else:
                logger.warning(
                    f"Failed to auto-generate comparison after deletion: {response_data.get('message', 'Unknown error')}"
                )
                return {
                    'message': get_message('comparison_report_auto_generated_failed', locale),
                    'data': response_data,
                    'auto_generated': False
                }, status_code
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(
                f"Error during auto-generation of comparison report after deletion: {str(e)}",
                exc_info=True
            )
            return {
                'message': get_message('comparison_report_generation_error', locale),
                'data': None,
                'error': str(e),
                'auto_generated': False
            }, 500


# Create service instance
comparison_report_service = ComparisonReportService()

