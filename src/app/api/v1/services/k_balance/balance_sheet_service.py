"""
Balance Sheet Service

Handles balance sheet PDF/Excel upload, extraction, S3 upload, and database storage.
"""

import os
import re
import uuid
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import openpyxl
from sqlalchemy import text
from flask import current_app, request
from src.common.localization import get_message

from src.app.database.models import (
    KbaiBalance, 
    TbUser, 
    TbUserCompany,
    KbaiKpiValue,
    KpiLogic,
    KbaiAnalysisKpi,
    KbaiAnalysis, 
    KbaiReport 
)
from src.app.database.models.kbai.kbai_companies import KbaiCompany
from src.extensions import db
from src.integrations.estrazione_bilancio import extract_balance_from_pdf, extract_text_from_pdf, extract_balance_from_xbrl, extract_text_from_xbrl, load_existing_json
from src.integrations.excel_script import extract_bilancio_from_xlsx
from src.integrations.excel_script_2 import extract_bilancio_abbreviato_from_xlsx
from src.integrations.xls_date_format_extract import extract_balance_year, detect_excel_format
# from src.app.api.v1.services.common.upload import FileUploadService
from src.app.api.v1.services.k_balance.comparison_report_service import ComparisonReportService

import logging
logger = logging.getLogger(__name__)

# Mapping for month names in English and Italian to month numbers
MONTH_NAME_TO_NUMBER = {
    'january': 1,
    'february': 2,
    'march': 3,
    'april': 4,
    'may': 5,
    'june': 6,
    'july': 7,
    'august': 8,
    'september': 9,
    'october': 10,
    'november': 11,
    'december': 12,
    'gennaio': 1,
    'febbraio': 2,
    'marzo': 3,
    'aprile': 4,
    'maggio': 5,
    'giugno': 6,
    'luglio': 7,
    'agosto': 8,
    'settembre': 9,
    'ottobre': 10,
    'novembre': 11,
    'dicembre': 12
}

NUMBER_TO_MONTH = {
    1:'gennaio',
    2:'febbraio',
    3:'marzo',
    4:'aprile',
    5:'maggio',
    6:'giugno',
    7:'luglio',
    8:'agosto',
    9:'settembre',
    10:'ottobre',
    11:'novembre',
    12:'dicembre'
}

# Create FileUploadService instance
# file_upload_service = FileUploadService()


class BalanceSheetService:
    """Service for handling balance sheet uploads"""
    
    def __init__(self):
        pass
    
    def check_company_access(
        self,
        current_user: TbUser,
        company_id: int
    ) -> Tuple[bool, str]:
        """
        Check if current user has access to a company for balance sheet operations.
        
        Args:
            current_user: Current authenticated user
            company_id: Company ID to check access for
            
        Returns:
            Tuple of (has_access, error_message)
            
        Permission Rules:
        - superadmin: Can access ALL companies
        - staff: Can access ALL companies
        - admin: Can access ONLY companies assigned to them (in tb_user_company)
        - user: Can access ONLY companies assigned to them (in tb_user_company)
        - competitor company: admin/user can access if they are assigned to the competitor's parent_company_id
        """
        locale = request.headers.get('Accept-Language', 'en')
        user_role = current_user.role.lower()
        
        # Superadmin and Staff have full access to all companies
        if user_role in ['superadmin', 'staff']:
            return True, ""
        
        # Admin and User can only access companies assigned to them
        if user_role in ['admin', 'user']:
            # 1) Direct assignment to this company
            user_company = TbUserCompany.query.filter_by(
                id_user=current_user.id_user,
                id_company=company_id
            ).first()
            
            if user_company:
                return True, ""

            # 2) Competitor flow: allow if assigned to parent_company_id
            competitor_company = KbaiCompany.query.filter_by(
                id_company=company_id,
                is_competitor=True,
                is_deleted=False
            ).first()

            if competitor_company:
                parent_company_id = competitor_company.parent_company_id
                if not parent_company_id:
                    return False, get_message('invalid_competitor_company_msg', locale)

                parent_user_company = TbUserCompany.query.filter_by(
                    id_user=current_user.id_user,
                    id_company=parent_company_id
                ).first()

                if parent_user_company:
                    return True, ""

                return False, get_message('competitor_access_denied_msg', locale, parent_company_id=parent_company_id)

            return False, get_message('company_access_denied_msg', locale, company_id=company_id)
        
        # Unknown role
        return False, get_message('unknown_user_role', locale, user_role=user_role)
    
    def _extract_period_from_file(
        self,
        file_path: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract year and month information from PDF or XBRL file.
        Automatically detects file type based on extension.

        Args:
            file_path: Path to the temporarily stored PDF or XBRL/XML file.

        Returns:
            Tuple containing (year, month) if detected, otherwise (None, None).
        """
        try:
            # Detect file type from extension
            file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
            
            if file_ext in ['xbrl', 'xml']:
                # Read XBRL file and extract only context sections with dates
                xbrl_content_filtered = ""  # Initialize the variable
                with open(file_path, 'r', encoding='utf-8') as f:
                    inside_context = False
                    for i, line in enumerate(f):
                        # Stop reading after contexts end (usually around line 100)
                        if i > 100:
                            break
                        # Extract only context sections
                        if '<context' in line.lower():
                            inside_context = True
                        if inside_context:
                            xbrl_content_filtered += line
                            if '</context>' in line.lower():
                                inside_context = False
                
                # Extract all ISO format dates and return the latest one
                # ISO format (YYYY-MM-DD) is ONLY for XBRL files, not PDF
                iso_date_pattern = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
                found_dates = []
                
                for match in iso_date_pattern.finditer(xbrl_content_filtered):
                    year_str, month_str, day_str = match.groups()
                    try:
                        month_value = int(month_str)
                        year_value = int(year_str)
                    except ValueError:
                        continue
                    
                    if 1 <= month_value <= 12 and 1900 <= year_value <= 2100:
                        found_dates.append((year_value, month_value))
                
                # Return latest date if found, otherwise fall back to text extraction
                if found_dates:
                    found_dates.sort(reverse=True)  # Sort descending to get latest first
                    return found_dates[0]  # Return latest (year, month)
                
                # Fallback to text extraction if no ISO dates found
                return self._extract_period_from_text(xbrl_content_filtered)
            
            elif file_ext == 'pdf':
                # Extract text from PDF
                pdf_text = extract_text_from_pdf(file_path)
                return self._extract_period_from_text(pdf_text)
            
            elif file_ext == 'xlsx':
                extracted_value = extract_balance_year(file_path)
                print("Extracted raw:", extracted_value)

                if extracted_value:
                    # Case 1: Full date string: "2024-12-31"
                    if isinstance(extracted_value, str) and re.match(r"\d{4}-\d{2}-\d{2}", extracted_value):
                        year = int(extracted_value[:4])
                        month = int(extracted_value[5:7])
                        return year, month

                    # Case 2: Only year like "2024"
                    if extracted_value.isdigit() and len(extracted_value) == 4:
                        return int(extracted_value), None

                # ---- FALLBACK ----
                wb = openpyxl.load_workbook(file_path, data_only=True)
                ws = wb.active
                fallback_text = " ".join(
                    str(cell) for row in ws.iter_rows(min_row=1, max_row=10, values_only=True)
                    for cell in row if cell
                )
                return self._extract_period_from_text(fallback_text)
                
            else:
                logger.warning(
                    f"Unsupported file type for period extraction: {file_ext}"
                )
                return None, None         
                
        except Exception as extract_error:
            logger.warning(
                "Unable to extract text from file for period validation: %s",
                str(extract_error)
            )
            return None, None

    def _extract_period_from_text(
        self,
        text: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse the supplied text and attempt to determine the reported year and month.
        """
        if not text:
            return None, None


        # Look for explicit date patterns like 31/12/2023 or 31-12-2023
        date_pattern = re.compile(r'(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})')
        for match in date_pattern.finditer(text):
            day_str, month_str, year_str = match.groups()
            try:
                month_value = int(month_str)
                year_value = int(year_str)
            except ValueError:
                continue

            if 1 <= month_value <= 12 and 1900 <= year_value <= 2100:
                return year_value, month_value

        # Look for textual month names paired with a year (e.g., "dicembre 2023")
        month_name_pattern = re.compile(
            r'(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|'
            r'january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
            re.IGNORECASE
        )
        for match in month_name_pattern.finditer(text):
            month_name, year_str = match.groups()
            month_value = MONTH_NAME_TO_NUMBER.get(month_name.lower())
            try:
                year_value = int(year_str)
            except ValueError:
                continue

            if month_value and 1900 <= year_value <= 2100:
                return year_value, month_value

        # Look for the year near typical Italian labels (esercizio/bilancio/al)
        context_year_pattern = re.compile(
            r'(?:esercizio|bilancio|al)\D{0,15}(20\d{2}|19\d{2})',
            re.IGNORECASE
        )
        context_match = context_year_pattern.search(text)
        if context_match:
            year_value = int(context_match.group(1))
            return year_value, None

        # Fallback: first standalone 4-digit year
        generic_year_pattern = re.compile(r'\b(20\d{2}|19\d{2})\b')
        generic_match = generic_year_pattern.search(text)
        if generic_match:
            year_value = int(generic_match.group(1))
            return year_value, None

        return None, None

    def _validate_pdf_period(
        self,
        pdf_year: Optional[int],
        pdf_month: Optional[int],
        payload_year: int,
        payload_month: int,
        file_type: str = "PDF"
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """
        Compare period extracted from file against payload period values.
        
        Args:
            pdf_year: Year extracted from file
            pdf_month: Month extracted from file
            payload_year: Year from request payload
            payload_month: Month from request payload
            file_type: Type of file for error messages (e.g., "PDF", "XBRL")
        """
        # Only validate year if we successfully extracted a year from the file.
        locale = request.headers.get('Accept-Language', 'en')
        if pdf_year is not None and pdf_year != payload_year:
            return {
                'error': get_message('validation_error', locale),
                'message': get_message('year_mismatch', locale, file_type=file_type, pdf_year=pdf_year, payload_year=payload_year)
            }, 400

        # Only validate month when both payload and extracted month are available.
        # If extraction failed (pdf_month is None), skip this check to avoid
        # incorrectly rejecting valid uploads due to parsing limitations.
        if payload_month is not None and pdf_month is not None and pdf_month != payload_month:
            return {
                'error': get_message('validation_error', locale),
                'message': get_message('month_mismatch', locale, file_type=file_type, pdf_month=pdf_month, payload_month=payload_month)
            }, 400

        return None

    def _check_existing_balance(
        self,
        company_id: int,
        year: int,
        month: int
    ) -> Tuple[Optional[KbaiBalance], Optional[Tuple[Dict[str, Any], int]]]:
        """
        Fetch the most recent balance sheet for the provided filters.
        Returns a tuple with the balance instance (if any) and an optional error response.
        """
        try:
            existing_balance = (
                KbaiBalance.query
                .filter_by(
                    id_company=company_id,
                    year=year,
                    month=month
                )
                .order_by(KbaiBalance.id_balance.desc())
                .first()
            )
        except Exception as query_error:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(
                "Error while checking for existing balance sheets: %s",
                str(query_error)
            )
            return None, ({
                'error': get_message('database_error', locale),
                'message': get_message('verification_failed_msg', locale)
            }, 500)

        if existing_balance and existing_balance.is_deleted is True:
            logger.info(
                "Existing balance sheet found but marked as deleted (id=%s). "
                "Proceeding with new creation.",
                existing_balance.id_balance
            )

        return existing_balance, None
    
    # Soft delete method for balance sheets(not currently used, but kept for reference), also deletes related benchmark data
    def _soft_delete_balance(self, balance: KbaiBalance):
        if balance.is_deleted:
            logger.info(
                "Skip soft delete: balance already deleted (id_balance=%s)",
                balance.id_balance
            )
            return None

        logger.info(
            "Starting soft delete for balance | id=%s | year=%s | month=%s",
            balance.id_balance,
            getattr(balance, "year", None),
            getattr(balance, "month", None)
        )

        balance.is_deleted = True
        balance.deleted_at = datetime.utcnow()

        try:
            benchmark_balance_types = [
                "balanceSheetToCompare",
                "comparitiveBalancesheet",
                "referenceBalanceSheet"
            ]

            # 1. Find benchmark analyses using this balance
            raw_analysis_ids = (
                db.session.query(KbaiAnalysisKpi.id_analysis)
                .filter(
                    KbaiAnalysisKpi.id_balance == balance.id_balance,
                    KbaiAnalysisKpi.kpi_list_json["balance_type"].astext.in_(benchmark_balance_types)
                )
                .distinct()
                .all()
            )

            analysis_ids = [a[0] for a in raw_analysis_ids]

            # 1.5. Also find competitor analyses using this balance
            raw_competitor_analysis_ids = (
                db.session.query(KbaiAnalysisKpi.id_analysis)
                .filter(
                    KbaiAnalysisKpi.id_balance == balance.id_balance,
                    KbaiAnalysisKpi.kpi_list_json["balance_type"].astext == "competitor"
                )
                .distinct()
                .all()
            )

            competitor_analysis_ids = [a[0] for a in raw_competitor_analysis_ids]
            
            # Combine both benchmark and competitor analysis IDs
            all_analysis_ids = list(set(analysis_ids + competitor_analysis_ids))

            logger.info(
                "Balance id=%s is used in %d benchmark analyses: %s and %d competitor analyses: %s",
                balance.id_balance,
                len(analysis_ids),
                analysis_ids,
                len(competitor_analysis_ids),
                competitor_analysis_ids
            )

            if not all_analysis_ids:
                logger.info(
                    "No benchmark or competitor analyses found for balance id=%s. Only soft delete applied.",
                    balance.id_balance
                )

            if all_analysis_ids:
                # 2. Delete reports
                result = db.session.execute(
                    text("""
                        DELETE FROM kbai_balance.kbai_reports
                        WHERE id_analysis IN :analysis_ids
                    """),
                    {"analysis_ids": tuple(all_analysis_ids)}
                )
                logger.info(
                    "Deleted %d rows from kbai_reports for analyses %s",
                    result.rowcount,
                    all_analysis_ids
                )

                # 3. Delete analysis KPI info
                result = db.session.execute(
                    text("""
                        DELETE FROM kbai_balance.analysis_kpi_info
                        WHERE id_analysis IN :analysis_ids
                    """),
                    {"analysis_ids": tuple(all_analysis_ids)}
                )
                logger.info(
                    "Deleted %d rows from analysis_kpi_info for analyses %s",
                    result.rowcount,
                    all_analysis_ids
                )

                # 4. Delete analysis KPIs
                result = db.session.execute(
                    text("""
                        DELETE FROM kbai_balance.kbai_analysis_kpi
                        WHERE id_analysis IN :analysis_ids
                    """),
                    {"analysis_ids": tuple(all_analysis_ids)}
                )
                logger.info(
                    "Deleted %d rows from kbai_analysis_kpi for analyses %s",
                    result.rowcount,
                    all_analysis_ids
                )

                # 5. Delete analyses
                result = db.session.execute(
                    text("""
                        DELETE FROM kbai_balance.kbai_analysis
                        WHERE id_analysis IN :analysis_ids
                    """),
                    {"analysis_ids": tuple(all_analysis_ids)}
                )
                logger.info(
                    "Deleted %d rows from kbai_analysis for analyses %s",
                    result.rowcount,
                    all_analysis_ids
                )

            db.session.add(balance)
            db.session.commit()

            logger.info(
                "Soft delete completed successfully for balance id=%s",
                balance.id_balance
            )

        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            db.session.rollback()
            logger.error(
                "Soft delete FAILED for balance id=%s | error=%s",
                balance.id_balance,
                str(e),
                exc_info=True
            )
            return {
                "error": get_message('database_error', locale),
                "message": get_message('delete_failed_msg', locale)
            }, 500

        return None

    def _hard_delete_balance_and_related_data(
        self,
        company_id: int,
        year: int,
        month: int
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """
        Hard delete ALL balance sheets (including soft-deleted) for given year/month
        and all their related data.
        
        Deletes:
        1. KbaiKpiValue records
        2. KpiLogic records (via id_kpi)
        3. KbaiAnalysisKpi records
        4. KbaiBalance records (hard delete)
        
        Args:
            company_id: Company ID
            year: Balance year
            month: Balance month
            
        Returns:
            None on success, (error_dict, status_code) on failure
        """
        try:
            # Step 1: Find ALL balances (including soft-deleted)
            all_balances = (
                KbaiBalance.query
                .filter_by(
                    id_company=company_id,
                    year=year,
                    month=month
                )
                # Don't filter by is_deleted - get ALL (including soft-deleted)
                .all()
            )
            
            if not all_balances:
                logger.info(
                    f"No existing balances found for company {company_id}, "
                    f"year {year}, month {month}"
                )
                return None
            
            balance_ids = [b.id_balance for b in all_balances]
            logger.info(
                f"Found {len(balance_ids)} balance(s) to hard delete: {balance_ids} "
                f"(company={company_id}, year={year}, month={month})"
            )
            
            # Step 1: Get KPI IDs FIRST (before deleting)
            kpi_values = KbaiKpiValue.query.filter(
                KbaiKpiValue.id_balance.in_(balance_ids)
            ).all()

            kpi_ids = [kpi.id_kpi for kpi in kpi_values]

            # Step 2: Delete KpiLogic records FIRST (child of KbaiKpiValue)
            kpi_logics = []
            if kpi_ids:
                kpi_logics = KpiLogic.query.filter(
                    KpiLogic.id_kpi.in_(kpi_ids)
                ).all()
                
                if kpi_logics:
                    logger.info(f"Deleting {len(kpi_logics)} KPI logic records")
                    for kpi_logic in kpi_logics:
                        db.session.delete(kpi_logic)

            # Step 3: Delete KbaiKpiValue records (parent of KpiLogic)
            if kpi_values:
                logger.info(f"Deleting {len(kpi_values)} KPI value records")
                for kpi_value in kpi_values:
                    db.session.delete(kpi_value)

            # Step 4: Get affected analysis IDs from KbaiAnalysisKpi (before deleting)
            analysis_kpis = KbaiAnalysisKpi.query.filter(
                KbaiAnalysisKpi.id_balance.in_(balance_ids)
            ).all()

            affected_analysis_ids = list(set([ak.id_analysis for ak in analysis_kpis]))

            # Step 5: Delete KbaiReport using SQL (child of KbaiAnalysis)
            reports_count = 0
            if affected_analysis_ids:
                delete_reports_sql = text("""
                    DELETE FROM kbai_balance.kbai_reports
                    WHERE id_analysis IN :analysis_ids
                """)
                result = db.session.execute(delete_reports_sql, {"analysis_ids": tuple(affected_analysis_ids)})
                reports_count = result.rowcount
                logger.info(f"Deleted {reports_count} report records using SQL")

            # Step 6: Delete KbaiAnalysisKpi records (junction table - child of KbaiAnalysis)
            if analysis_kpis:
                logger.info(
                    f"Deleting {len(analysis_kpis)} AnalysisKpi records. "
                    f"Affected analysis IDs: {affected_analysis_ids}"
                )
                for analysis_kpi in analysis_kpis:
                    db.session.delete(analysis_kpi)

            # Step 7: Delete KbaiAnalysis using SQL (only orphaned - no remaining AnalysisKpi)
            analyses_count = 0
            if affected_analysis_ids:
                delete_analyses_sql = text("""
                    DELETE FROM kbai_balance.kbai_analysis
                    WHERE id_analysis IN :analysis_ids
                    AND NOT EXISTS (
                        SELECT 1 FROM kbai_balance.kbai_analysis_kpi
                        WHERE kbai_analysis_kpi.id_analysis = kbai_analysis.id_analysis
                    )
                """)
                result = db.session.execute(delete_analyses_sql, {"analysis_ids": tuple(affected_analysis_ids)})
                analyses_count = result.rowcount
                logger.info(f"Deleted {analyses_count} analysis records using SQL (orphaned analyses)")

            # Step 8: Hard delete balance records
            logger.info(f"Hard deleting {len(all_balances)} balance record(s)")
            for balance in all_balances:
                db.session.delete(balance)
            
            # Commit all deletions in one transaction
            db.session.commit()
            
            logger.info(
                f"Successfully hard deleted {len(balance_ids)} balance(s) and all related data. "
                f"Deleted: {len(kpi_values)} KPIs, {len(kpi_logics)} KPI logics, "
                f"{len(analysis_kpis)} AnalysisKPIs, {reports_count} Reports, "
                f"{analyses_count} Analyses"
            )
            
            return None
            
        except Exception as delete_error:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(
                f"Error hard deleting balances and related data: {str(delete_error)}",
                exc_info=True
            )
            db.session.rollback()
            return {
                'error': get_message('database_error', locale),
                'message': get_message('delete_existing_failed_msg', locale, error=str(delete_error))
            }, 500

    def balance_sheet(
        self,
        file,
        company_id: int,
        year: int,
        month: int,
        type: str,
        mode: str,
        note: str = None,
        overwrite: bool = False,
        current_user: TbUser = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Upload balance PDF/Excel, extract data, upload to S3, and save to database.
        
        Args:
            file: PDF or Excel file object from request
            company_id: Company ID from token
            year: Balance year
            month: Balance month
            type: Balance type (e.g., "annual", "quarterly")
            mode: Upload mode (e.g., "manual", "automatic")
            note: Optional notes
            overwrite: If True, soft deletes existing balance sheet for the same period
                and type before creating the new record.
            
        Returns:
            Tuple of (response_data, status_code)
        """
        temp_file_path = None
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Step 0: Check company access if current_user is provided
            if current_user:
                has_access, error_msg = self.check_company_access(current_user, company_id)
                if not has_access:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
            
            # Step 1: Validate inputs
            if not file or not file.filename:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('file_required', locale)
                }, 400
            
            # Check file extension
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if file_ext not in ['pdf', 'xlsx', 'xbrl', 'xml']:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('invalid_file_type', locale)
                }, 400
            
            # mode and file extension consistency check
            file_ext_lower = file_ext.lower()
            mode_lower = mode.lower()
            # Define valid mode to file extension mappings
            mode_file_mapping = {
                'pdf': ['pdf'],
                'xlsx': ['xlsx'],
                'xls': ['xlsx'],  # xls mode also accepts xlsx files
                'xbrl': ['xbrl', 'xml'],
                'xml': ['xbrl', 'xml'],
                'manual': ['pdf', 'xlsx', 'xbrl', 'xml']  # manual mode accepts all
            }  
           
            # Check if mode is valid
            if mode_lower not in mode_file_mapping:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('invalid_mode', locale, mode=mode)
                }, 400
                
           
            # Check if file extension matches the mode
            valid_extensions = mode_file_mapping[mode_lower]
            if file_ext_lower not in valid_extensions:
                # Get the expected file type name for better error message
                mode_display = mode_lower.upper() if mode_lower in ['pdf', 'xlsx', 'xbrl', 'xml'] else mode_lower
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('mode_mismatch', locale, mode_display=mode_display, file_ext=file_ext.upper())
                }, 400
            # Validate year and month
            if not isinstance(year, int) or year < 1900 or year > 2100:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('invalid_year', locale)
                }, 400   
                 
            if month is not None :
                if not isinstance(month, int) or month < 1 or month > 12:
                    return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('invalid_month', locale)
                    }, 400

            # Step 2: Save file temporarily
            temp_dir = tempfile.gettempdir()
            temp_filename = f"balance_{uuid.uuid4().hex}.{file_ext}"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            file.save(temp_file_path)
            logger.info(f"File saved temporarily: {temp_file_path} (type: {file_ext})")
            # Step 3: Extract balance data from file based on type
            try:
                if file_ext == 'pdf':
                    balance_json = extract_balance_from_pdf(temp_file_path)
                    logger.info("Balance data extracted successfully from PDF")
                elif file_ext == 'xlsx':
                    # Detect Excel format
                    print("Detecting Excel format...")
                    format_type = detect_excel_format(temp_file_path)

                    if format_type == "full":
                        logger.info("Detected FULL Excel format (script.py)")
                        balance_json = extract_bilancio_from_xlsx(temp_file_path)

                    elif format_type == "abbreviated":
                        logger.info("Detected ABBREVIATED Excel format (script2.py)")
                        balance_json = extract_bilancio_abbreviato_from_xlsx(temp_file_path)
                    else:
                        return {
                            "error": get_message('unknown_excel_format', locale),
                            "message": get_message('excel_script_error', locale)
                        }, 400
                elif file_ext in ['xbrl', 'xml']:
                    balance_json = extract_balance_from_xbrl(temp_file_path)
                    logger.info("Balance data extracted successfully from XBRL")
                else:
                    return {
                        'error': get_message('validation_error', locale),
                        'message': get_message('unsupported_file_type', locale, file_ext=file_ext)
                    }, 400
                
                logger.info(f"Extracted balance data keys: {list(balance_json.keys()) if isinstance(balance_json, dict) else 'Not a dict'}")
            except Exception as e:
                logger.error(f"Error extracting balance data: {str(e)}")
                return {
                    'error': get_message('extraction_error', locale),
                    'message': get_message('extraction_failed_msg', locale, file_ext=file_ext.upper(), error=str(e))
                }, 500

            # Step 4: Extract and validate period (for PDF and XBRL, Excel doesn't have text extraction)
            if file_ext in ['pdf', 'xbrl', 'xml', 'xlsx']:
                file_year, file_month = self._extract_period_from_file(temp_file_path)
                # Determine file type for error messages
                if file_ext in ['pdf', 'xbrl', 'xml', 'xlsx']:
                    file_type_display = file_ext.upper()
                else:
                    file_type_display = "file"
                period_validation_response = self._validate_pdf_period(
                    pdf_year=file_year,
                    pdf_month=file_month,
                    payload_year=year,
                    payload_month=month,
                    file_type=file_type_display
                )
                if period_validation_response:
                    return period_validation_response

            existing_balance, lookup_error = self._check_existing_balance(
                company_id=company_id,
                year=year,
                month=month
            )
            if lookup_error:
                return lookup_error

            if existing_balance and existing_balance.is_deleted is not True:
                if not overwrite:
                    return {
                        'error': get_message('validation_error', locale),
                        'message': get_message('balance_sheet_exists', locale)
                    }, 400

                # Hard delete ALL existing balances (including soft-deleted) and related data
                hard_delete_error = self._hard_delete_balance_and_related_data(
                    company_id=company_id,
                    year=year,
                    month=month
                )
                
                if hard_delete_error:
                    return hard_delete_error
                
                logger.info(
                    f"Hard deleted all existing balances for company {company_id}, "
                    f"year {year}, month {month}. Proceeding with new upload."
                )
            
            # Step 5: Upload file to S3 using existing FileUploadService
            # Temporarily commented out for testing
            # try:
            #     folder = 'balances'
            #     result, status_code = file_upload_service.upload(file, folder)
            #     
            #     if not result.get('success') or status_code != 200:
            #         return {
            #             'error': 'Upload error',
            #             'message': result.get('message', 'Failed to upload file to S3')
            #         }, status_code
            #     
            #     # Get URL from result
            #     s3_url = result.get('data', {}).get('url')
            #     if not s3_url:
            #         # Fallback: generate URL from s3_filename
            #         s3_filename = result.get('data', {}).get('s3_filename')
            #         if s3_filename:
            #             url_result, _ = file_upload_service.get_url(s3_filename)
            #             s3_url = url_result.get('data', {}).get('s3_url')
            #     
            #     if not s3_url:
            #         return {
            #             'error': 'Upload error',
            #             'message': 'Failed to get S3 URL after upload'
            #         }, 500
            #     
            #     logger.info(f"File uploaded to S3: {s3_url}")
            # except Exception as e:
            #     logger.error(f"Error uploading to S3: {str(e)}")
            #     return {
            #         'error': 'Upload error',
            #         'message': f'Failed to upload file to S3: {str(e)}'
            #     }, 500
            
            if month is not None:
                month_name = NUMBER_TO_MONTH.get(month)
            else:
                month_name = "" 
            
            # Step 6: Save to database
            balance_data = {
                'id_company': company_id,
                'year': year,
                'month': month,
                'type': type,
                'mode': mode,
                'file': f"{type} {year} {month_name}",
                'note': note,
                'balance': balance_json  # JSONB field
            }
            
            balance, error = KbaiBalance.create(balance_data)
            
            if error:
                logger.error(f"Error creating balance record: {error}")
                return {
                    'error': f"Database error {error}",
                    'message': get_message('save_balance_failed', locale),
                }, 500
            
            logger.info(f"Balance record created: {balance.id_balance}")
            
            # Step 7.5: Auto-generate comparison report if conditions are met
            try:
                from src.app.api.v1.services.k_balance.comparison_report_service import comparison_report_service
                
                auto_comparison_result, auto_comparison_status = comparison_report_service.auto_generate_comparison_after_upload(
                    company_id=company_id,
                    current_user=current_user,
                    newly_uploaded_balance_id=balance.id_balance,
                    newly_uploaded_year=year
                )
                result = auto_comparison_result or {}
                if result.get('auto_generated'):
                    logger.info(
                        f"Comparison report auto-generated after balance sheet upload. "
                        f"Analysis ID: {result.get('data', {}).get('id_analysis', 'N/A')}"
                    )
                else:
                    logger.info(
                        f"Comparison report not auto-generated: {result.get('message', 'Unknown reason')}. " 
                        f"KPIs calculated: {result.get('data', {}).get('kpis_calculated', False)}"
                    )
                if auto_comparison_result.get('auto_generated'):
                    logger.info(
                        f"Comparison report auto-generated after balance sheet upload. "
                        f"Analysis ID: {auto_comparison_result.get('data', {}).get('id_analysis', 'N/A')}"
                    )
                else:
                    logger.info(
                        f"Comparison report not auto-generated: {auto_comparison_result.get('message', 'Unknown reason')}. " 
                        f"KPIs calculated: {auto_comparison_result.get('data', {}).get('kpis_calculated', False)}"
                    )
            except Exception as e:
                # Log error but don't fail the upload
                logger.error(
                    f"Error during auto-generation of comparison report after upload: {str(e)}",
                    exc_info=True
                )
            
            # Step 7: Cleanup temp file
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.info(f"Temp file removed: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {str(e)}")
            
            # Step 8: Return response
            return {
                'message': get_message('balance_sheet_uploaded_success', locale),
                'data': {"balance_id": balance.id_balance},
                'success': True
            }, 201
            
        except Exception as e:
            logger.error(f"Error in balance_sheet: {str(e)}")
            
            # Cleanup temp file on error
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception:
                pass
            
            return {
                'error': 'Internal server error',
                'message': get_message('balance_sheet_upload_failed', locale)
            }, 500
    
    def get_by_company_id(
        self,
        company_id: int,
        page: int = 1,
        per_page: int = 10,
        current_user: TbUser = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get balance sheets by company ID (without balance field).
        
        Args:
            company_id: Company ID
            page: Page number (default: 1)
            per_page: Items per page (default: 10)
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Check company access if current_user is provided
            if current_user:
                has_access, error_msg = self.check_company_access(current_user, company_id)
                if not has_access:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
            
            # Validate company_id
            if not company_id or company_id <= 0:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('valid_company_id_required', locale)
                }, 400
            
            # Query balance sheets for company
            records, total, error = KbaiBalance.find(
                page=page,
                per_page=per_page,
                id_company=company_id
            )
            
            if error:
                logger.error(f"Error querying balance sheets: {error}")
                return {
                    'error': get_message('database_error', locale),
                    'message': get_message('balance_sheets_retrieve_failed', locale)
                }, 500
            
            # Convert to dict and exclude balance field
            balance_sheets = []
            for record in records:
                record_dict = record.to_dict()
                # Remove balance field
                record_dict.pop('balance', None)
                balance_sheets.append(record_dict)
            
            # Calculate pagination
            total_pages = (total + per_page - 1) // per_page if total > 0 else 0
            
            logger.info(f"Retrieved {len(balance_sheets)} balance sheets for company {company_id}")
            
            return {
                'message': get_message('balance_sheets_retrieved_success', locale),
                'data': balance_sheets,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': total_pages
                },
                'success': True
            }, 200
            
        except Exception as e:
            logger.error(f"Error in get_by_company_id: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': 'Internal server error',
                'message': get_message('balance_sheets_retrieve_failed', locale)
            }, 500
    
    def get_by_id(
        self,
        id_balance: int,
        current_user: TbUser = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get balance sheet by ID (with complete data including balance field).
        
        Args:
            id_balance: Balance sheet ID
            current_user: Current authenticated user
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Validate id_balance
            if not id_balance or id_balance <= 0:
                return {
                    'error': get_message('validation_error', locale),
                    'message': get_message('valid_balance_id_required', locale)
                }, 400
            
            # First, check company access if current_user is provided
            # Fetch only company_id to minimize data exposure
            if current_user:
                balance = KbaiBalance.findOne(id_balance=id_balance)
                
                if not balance:
                    logger.warning(f"Balance sheet not found: {id_balance}")
                    return {
                        'error': 'Not found',
                        'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance)
                    }, 404
                
                company_id = balance.id_company
                
                # Check company access immediately before fetching full balance
                has_access, error_msg = self.check_company_access(current_user, company_id)
                if not has_access:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
            
            else:# Now fetch the full balance sheet (access already verified if user provided)
                balance = KbaiBalance.findOne(id_balance=id_balance)
            
            if not balance:
                logger.warning(f"Balance sheet not found: {id_balance}")
                return {
                    'error': 'Not found',
                    'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance)
                }, 404
            
            # Return complete data including balance field
            logger.info(f"Retrieved balance sheet: {id_balance}")
            
            return {
                'message': get_message('balance_sheet_retrieved_success', locale),
                'data': balance.to_dict(),
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(f"Error in get_by_id: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('balance_sheet_retrieve_failed', locale)
            }, 500
    
    def delete(
        self,
        id_balance: int,
        company_id: int = None,
        current_user: TbUser = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Delete (soft delete) a balance sheet by ID.
        
        Args:
            id_balance: Balance sheet ID
            company_id: Optional company ID to validate balance belongs to company
            current_user: Current authenticated user
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # First, check company access if current_user is provided
            # Fetch only company_id to minimize data exposure
            if current_user:
                company_id_result = db.session.query(KbaiBalance.id_company).filter_by(
                    id_balance=id_balance
                ).first()
                
                if not company_id_result:
                    logger.warning(f"Balance sheet not found: {id_balance}")
                    return {
                        'error': 'Not found',
                        'message': get_message('balance_sheet_id_not_found', locale, id_balance=id_balance)
                    }, 404
                
                balance_company_id = company_id_result[0]
                
                # Check company access immediately before fetching full balance
                has_access, error_msg = ComparisonReportService().check_company_access(current_user, balance_company_id)
                if not has_access:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
                
                # Validate balance belongs to company_id if provided
                if company_id and balance_company_id != company_id:
                    return {
                        'error': get_message('validation_error', locale),
                        'message': get_message('balance_does_not_belong', locale, id_balance=id_balance, company_id=company_id)
                    }, 400
            
            # Query balance sheet by ID
            balance = KbaiBalance.findOne(id_balance=id_balance)
            
            if not balance:
                logger.warning(f"Balance sheet not found")
                return {
                    'error': 'Not found',
                    'message': get_message('balance_sheet_not_found', locale)
                }, 404
            
            # Check if already deleted
            if balance.is_deleted is True:
                return {
                    'error': get_message('already_deleted', locale),
                    'message': get_message('balance_sheet_already_deleted', locale)
                }, 400
            
            # Use existing soft delete method
            delete_result = self._soft_delete_balance(balance)
            
            # _soft_delete_balance returns None on success or (error_dict, status_code) on failure
            if delete_result is not None:
                error_dict, error_status = delete_result
                return error_dict, error_status
            
            logger.info(f"Balance sheet deleted: {id_balance}")
            
            # Step: Auto-generate comparison report if conditions are met
            try:
                from src.app.api.v1.services.k_balance.comparison_report_service import comparison_report_service
                
                # Get company_id from the deleted balance
                company_id_for_comparison = balance.id_company
                
                auto_comparison_result, auto_comparison_status = comparison_report_service.auto_generate_comparison_after_delete(
                    company_id=company_id_for_comparison,
                    current_user=current_user,
                    deleted_balance_id=id_balance
                )
                
                if auto_comparison_result.get('auto_generated'):
                    logger.info(
                        f"Comparison report auto-generated after balance sheet deletion. "
                        f"Analysis ID: {auto_comparison_result.get('data', {}).get('id_analysis', 'N/A')}"
                    )
                else:
                    logger.info(
                        f"Comparison report not auto-generated after deletion: {auto_comparison_result.get('message', 'Unknown reason')}"
                    )
            except Exception as e:
                # Log error but don't fail the deletion
                logger.error(
                    f"Error during auto-generation of comparison report after deletion: {str(e)}",
                    exc_info=True
                )
            
            return {
                'message': get_message('balance_sheet_deleted_success', locale),
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            logger.error(f"Error in delete: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('balance_sheet_delete_failed', locale)
            }, 500

# Create service instance
balance_sheet_service = BalanceSheetService()

