"""
Banchmark Service

Handles financial KPI between benchmark balance sheets (years).
"""
from typing import Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import or_
import logging

from src.app.database.models import (
    AnalysisKpiInfo,
    KbaiBalance,
    KbaiAnalysis,
    KbaiCompany,
    KbaiReport,
    KbaiKpiValue,
    KbaiAnalysisKpi,
    TbUser,
    KbaiPreDashboard,
    AnalysisKpiInfo
)
from flask import request
from collections import defaultdict
from src.app.api.v1.services.k_balance.comparison_report_service import ComparisonReportService
from .kpi_status_services import (
    store_analysis_kpi_info, 
    calculate_kpi_statuses, 
    calculate_goal_percentage,
    calculate_competitor_kpi_statuses,
    build_competitor_kpi_insight
)

# from src.app.database.models.kbai_balance.kbai_kpi_values import KbaiKpiValue
from src.extensions import db
from src.common.localization import get_message

logger = logging.getLogger(__name__)

class BenchmarkService:
    def create_benchmark(self, current_user, company_id):
        try:
            payload = request.get_json()
            # New payload structure: object with three keys
            balanceSheetToCompare = payload.get("balanceSheetToCompare")
            comparitiveBalancesheet = payload.get("comparitiveBalancesheet")
            referenceBalanceSheet = payload.get("referenceBalanceSheet")

            # 1. Validate Input
            locale = request.headers.get('Accept-Language', 'en')
            
            balance_specs_raw = [balanceSheetToCompare, comparitiveBalancesheet, referenceBalanceSheet]
            balances_specs = [spec for spec in balance_specs_raw if spec is not None]
            if not company_id or len(balances_specs) == 0:
                return {"message": get_message("company_id_and_balance_required", locale)}, 400
            
            # Validate each spec (month is now optional)
            allowed_types = ["final", "forecast", "provisional"]  # Define allowed balance types (map to budgetType)
            for spec in balances_specs:
                if not isinstance(spec, dict) or "year" not in spec or "budgetType" not in spec:
                    return {"message": get_message("balance_sheet_spec_error", locale)}, 400
                if spec["budgetType"] not in allowed_types:
                    return {"message": get_message("invalid_budget_type", locale, type=spec['budgetType'])}, 400

            # 2. Check Company Access
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403

            # 3. Build Query with OR Conditions for Multiple Specs
            conditions = []
            for spec in balances_specs:
                year = spec["year"]
                b_type = spec["budgetType"]  # Map budgetType to type
                month = spec.get("month")  # Optional
                cond = (KbaiBalance.year == year) & (KbaiBalance.type == b_type) & (KbaiBalance.is_deleted == False)
                if month is not None:
                    cond &= (KbaiBalance.month == month)
                else:
                    cond &= (KbaiBalance.month.is_(None))
                conditions.append(cond)

            
            query = KbaiBalance.query.filter(
                KbaiBalance.id_company == company_id,
                or_(*conditions)  # OR all conditions
            )
            balances = query.all()

            # Verify each spec has a matching balance in the table (adjust for optional month)
            exact_matches = {(b.year, b.type, b.month) for b in balances}
            for spec in balances_specs:
                year = spec["year"]
                b_type = spec["budgetType"]
                month = spec.get("month")
                if month is not None:
                    if (year, b_type, month) not in exact_matches:
                        return {"message": get_message("no_balance_found_with_month", locale, year=year, type=b_type, month=month)}, 400
                else:
                    # If month not specified, check if any balance matches year and type (ignoring month)
                    if not any(b.year == year and b.type == b_type for b in balances):
                        return {"message": get_message("no_balance_found", locale, year=year, type=b_type)}, 400

            balance_ids = [b.id_balance for b in balances]

            # 3.5. Check if benchmark report already exists with same balance sheets
            benchmark_balance_types = [
                "balanceSheetToCompare",
                "comparitiveBalancesheet",
                "referenceBalanceSheet"
            ]
            
            # Get all existing BENCHMARK analyses for this company
            existing_benchmark_analyses = (
                db.session.query(KbaiAnalysis)
                .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                .join(KbaiBalance, KbaiAnalysisKpi.id_balance == KbaiBalance.id_balance)
                .filter(
                    KbaiAnalysis.analysis_type == "BENCHMARK",
                    KbaiBalance.id_company == company_id,
                    KbaiBalance.is_deleted == False
                )
                .distinct()
                .all()
            )
            
            # Check each existing benchmark analysis for exact balance match
            for existing_analysis in existing_benchmark_analyses:
                existing_analysis_kpis = KbaiAnalysisKpi.query.filter_by(
                    id_analysis=existing_analysis.id_analysis
                ).all()
                
                # Get balance IDs from this analysis (only benchmark types, not competitor)
                existing_balance_ids = set()
                for ak in existing_analysis_kpis:
                    if ak.kpi_list_json and ak.kpi_list_json.get("balance_type") in benchmark_balance_types:
                        existing_balance_ids.add(ak.id_balance)
                
                # Compare with current balance_ids (convert to set for comparison)
                current_balance_ids_set = set(balance_ids)
                
                # If exact match found, return error
                if existing_balance_ids == current_balance_ids_set and len(existing_balance_ids) > 0:
                    # Get the existing report name for better error message
                    existing_report = KbaiReport.query.filter_by(
                        id_analysis=existing_analysis.id_analysis,
                        type="BENCHMARK"
                    ).first()
                    
                    report_name_info = existing_report.name if existing_report else "existing benchmark report"
                    years_str = ", ".join(str(b.year) for b in sorted(balances, key=lambda x: x.year))
                    return {
                        "message": get_message("benchmark_report_already_exists", locale)
                    }, 400

            # Create spec to key mapping
            spec_to_key = {}
            keys = ["balanceSheetToCompare", "comparitiveBalancesheet", "referenceBalanceSheet"]
            for i, spec in enumerate(balance_specs_raw):
                if spec:
                    key = (spec["year"], spec["budgetType"])
                    if spec.get("month") is not None:
                        key = (spec["year"], spec["budgetType"], spec["month"])
                    spec_to_key[key] = keys[i]

            kpi_values = KbaiKpiValue.query.filter(
                KbaiKpiValue.id_balance.in_(balance_ids)
            ).all()
            if not kpi_values:
                return {"message": get_message("no_kpi_values_found", locale)}, 200
             # Compose report name as companyName-year1-year2-year3 etc
            # Assume all balances are for the same company (from balances list)
            first_balance = balances[0] if balances else None
            company_obj = KbaiCompany.query.filter_by(id_company=first_balance.id_company if first_balance else None).first()
            company_name = company_obj.company_name if company_obj and hasattr(company_obj, "company_name") else "Company"
            # Gather all years from balances
            all_years = [b.year for b in balances if hasattr(b, "year")]
            years_sorted = sorted(all_years)
            years_joined = "-".join(str(y) for y in years_sorted)
            report_name = f"{company_name}-{years_joined}" if years_joined else company_name
            
            # 5. Create Benchmark Analysis Entry
            analysis = KbaiAnalysis(
                analysis_name=f"benchmark_generated {report_name}",
                analysis_type="BENCHMARK",
                time=datetime.utcnow()
            )
            db.session.add(analysis)
            db.session.flush()
            analysis_id = analysis.id_analysis

            

            # Calculate KPI statuses
            kpi_years = defaultdict(list)
            balances_dict = {b.id_balance: b for b in balances}
            for kv in kpi_values:
                balance = balances_dict.get(kv.id_balance)
                if not balance:
                    logger.error(
                        "Missing balance_type for balance id=%s year=%s month=%s",
                        balance.id_balance,
                        balance.year,
                        balance.month
                    )
                    continue
                year = balance.year
                value = float(kv.value) if kv.value is not None else None
                kpi_years[kv.kpi_name].append((year, value))
            kpi_statuses = calculate_kpi_statuses(kpi_years)
            store_analysis_kpi_info(
                analysis_id=analysis_id,
                kpi_values=kpi_values,
                kpi_statuses=kpi_statuses,
                balances=balances
            )
            # 6. Create KbaiAnalysisKpi Mapping -- now with storing kpis in JSON format
            kpis_by_balance = defaultdict(dict)
            # Optionally, also collect all years if present in KbaiBalance
            year_by_balance = {}

            for kv in kpi_values:
                kpis_by_balance[kv.id_balance][kv.kpi_name] = float(kv.value) if kv.value is not None else None
                if kv.id_balance in balances_dict:
                    year_by_balance[kv.id_balance] = balances_dict[kv.id_balance].year

            for id_balance, kpis in kpis_by_balance.items():
                year = year_by_balance.get(id_balance)
                balance = balances_dict.get(id_balance)
                balance_type = ""
                if balance:
                    # Try exact match first, then without month
                    balance_type = spec_to_key.get((balance.year, balance.type, balance.month), "") or spec_to_key.get((balance.year, balance.type), "")
                kpi_json = {
                    "kpis": kpis,
                    "year": year,
                    "balance_type": balance_type,
                    "missing_fields": []  # Benchmark context may not track missing fields, can adapt later.
                }
                mapping = KbaiAnalysisKpi(
                    id_analysis=analysis_id,
                    id_balance=id_balance,
                    kpi_list_json=kpi_json
                )
                db.session.add(mapping)

            # 7. Create Benchmark Report Entry
            report = KbaiReport(
                id_analysis=analysis_id,
                name=report_name,
                type="BENCHMARK",
                time=datetime.utcnow()
            )
            db.session.add(report)
            db.session.commit()

            # Update pre-dashboard step_compare to true after successful report generation
            try:
                pre_dashboard = KbaiPreDashboard.findOne(id_company=company_id)
                if pre_dashboard:
                    success, update_error = pre_dashboard.update({'step_compare': True})

                    if success:
                        logger.info(f"Updated step_compare to true for company {company_id} after comparison report generation")
                    else:
                        logger.warning(f"Failed to update step_compare for company {company_id}: {update_error}")
                else:
                    logger.warning(f"Pre-dashboard not found for company {company_id}, cannot update step_compare")
            except Exception as e:
                # Log error but don't fail the report generation
                logger.error(f"Error updating pre-dashboard step_compare for company {company_id}: {str(e)}")

            # 8. Final Response
            return {
                "message": get_message("benchmark_report_created", locale),
                "data": {"balance_id": balance_ids}
            }, 201

        except Exception as e:
            db.session.rollback()
            return {"message": str(e)}, 500
    
    def get_benchmarks_by_report(self, current_user, report_id: int) -> Tuple[Dict[str, Any], int]:
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Fetch the report
            report = KbaiReport.query.filter_by(id_report=report_id, type = "BENCHMARK").first() 
            if not report:
                return {"message": get_message("report_not_found", locale)}, 404

            # Fetch the associated analysis
            analysis = KbaiAnalysis.query.filter_by(id_analysis=report.id_analysis).first()
            if not analysis:
                return {"message": get_message("analysis_not_found_for_report", locale)}, 404

            # Fetch all KbaiAnalysisKpi entries for this analysis
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpis:
                return {"message": get_message("no_benchmarks_found_for_report", locale)}, 200
            
            #add check user access to company
            first_balance = KbaiBalance.query.filter_by(id_balance=analysis_kpis[0].id_balance).first()
            company_id = first_balance.id_company if first_balance else None    
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403
            
            # Get balances for the analysis_kpis
            balance_ids = [ak.id_balance for ak in analysis_kpis]
            balances = KbaiBalance.query.filter(KbaiBalance.id_balance.in_(balance_ids)).all()
            id_to_balance = {b.id_balance: b for b in balances}
            
            # Build balances data
            balances_data = {}

            for ak in analysis_kpis:
                balance = id_to_balance.get(ak.id_balance)
                if not balance or not ak.kpi_list_json:
                    continue

                balance_type = ak.kpi_list_json.get("balance_type", "")
                if not balance_type:
                    continue

                balances_data[balance_type] = {
                    "file": balance.file or "",
                    "kpis": ak.kpi_list_json.get("kpis", {}),
                    "year": ak.kpi_list_json.get("year")
                }

            # Calculate KPI statuses
            kpi_years = defaultdict(list)

            for ak in analysis_kpis:
                if not ak.kpi_list_json:
                    continue

                kpis = ak.kpi_list_json.get("kpis", {})
                year = ak.kpi_list_json.get("year")

                for kpi_name, value in kpis.items():
                    kpi_years[kpi_name].append((year, value))

            calculated_statuses = calculate_kpi_statuses(kpi_years)

            analysis_kpi_infos = AnalysisKpiInfo.query.filter_by(
            id_analysis=analysis.id_analysis).all()

            kpi_statuses = {
                info.kpi_value.kpi_name: {
                    "id_kpi": info.id_kpi,
                    "status": calculated_statuses.get(info.kpi_value.kpi_name),
                    "note": info.note,
                    "goal": calculate_goal_percentage(kpi_years.get(info.kpi_value.kpi_name, [])),
                    "synthesis": info.synthesis,
                    "suggestion": [info.suggestion] if info.suggestion else []
                }
                for info in analysis_kpi_infos
                if info.kpi_value
            }
            parent_reports = KbaiReport.query.filter_by(parent_report_id=report.id_report).all()
            reports_data: list[dict[str, Any]] = []

            for comp_report in parent_reports:
                # 1) Fetch competitor analysis for this competitor report
                comp_analysis = KbaiAnalysis.query.filter_by(
                    id_analysis=comp_report.id_analysis
                ).first()
                if not comp_analysis:
                    continue

                # 2) Get all KPI mappings for this competitor analysis
                comp_analysis_kpis = KbaiAnalysisKpi.query.filter_by(
                    id_analysis=comp_analysis.id_analysis
                ).all()
                if not comp_analysis_kpis:
                    continue

                # 3) Find the competitor balance row:
                #    - balance_type == "competitor"
                #    - competitor_report_id in kpi_list_json matches this comp_report.id_report
                competitor_balance_id: int | None = None
                for ak in comp_analysis_kpis:
                    if not ak.kpi_list_json:
                        continue

                    balance_type = ak.kpi_list_json.get("balance_type")
                    if balance_type == "competitor" :
                        competitor_balance_id = ak.id_balance
                        break

                # 4) From competitor balance, get balance_name and competitor company name
                competitor_balance_name: str | None = None
                competitor_company_name: str | None = None

                if competitor_balance_id is not None:
                    comp_balance = KbaiBalance.query.filter_by(
                        id_balance=competitor_balance_id,is_deleted=False
                    ).first()
                    print(comp_balance,"COMP_BALANCE")
                    if comp_balance:
                        competitor_balance_name = comp_balance.file

                        comp_company = KbaiCompany.query.filter_by(
                            id_company=comp_balance.id_company,is_competitor=True,
                            is_deleted=False
                        ).first()
                        print(comp_company,"COMP_COMPANY")
                        if comp_company:
                            competitor_company_name = comp_company.company_name

                report_data = {
                    "competitor_id_report": comp_report.id_report,
                    "comparison_name": comp_report.name,
                    "type": comp_report.type,
                    "competitor_name": competitor_company_name,
                    "balance_name": competitor_balance_name,  # ✅ competitor balance sheet name
                    "time": comp_report.time.isoformat() if comp_report.time else None,
                }
                reports_data.append(report_data)
            return {
                "message": get_message("benchmarks_fetched_successfully", locale),
                "data": {
                    "parent_id_report": report.id_report,
                    "parent_analysis_id": report.id_analysis,  
                    "parent_name": report.name,
                    "time": report.time.isoformat() if report.time else None,
                    "benchmarks": balances_data,
                    "kpi_statuses": kpi_statuses,
                    "competitor_reports": reports_data
                }
            }, 200

        except Exception as e:
            logger.error(f"Error fetching benchmarks for report {report_id}: {str(e)}")
            return {"message": "Internal server error", "error_details": str(e)}, 500
    
        
    def get_by_company_id_and_balance_year(
        self,
        company_id: int,
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
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Check company access if current_user is provided
            if current_user:
                has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
                if not has_access:
                    return {
                        'error': 'Permission denied',
                        'message': error_msg
                    }, 403
            
            # Validate company_id
            if not company_id or company_id <= 0:
                return {
                    'error': 'Validation error',
                    'message': get_message("valid_company_id_required", locale)
                }, 400
            
            # Query balance sheets for company
            records = KbaiBalance.query.filter_by(
                id_company=company_id,
                is_deleted=False
            ).all()
            if not records:
                return {
                    'message': get_message("no_balance_sheets_found", locale),
                    'data': {
                        'balance_years': ()
                            },
                    'success': True
                    }, 200
                    
            # Collect unique years
            years_set = set()
            balance_name = []
            for record in records:
                years_set.add(record.year)
                balance_name.append(record.file)
            # Convert to tuple
            years_tuple = tuple(sorted(years_set))

            logger.info(f"Retrieved {len(years_tuple)} unique years for company {company_id}")

            return {
                'message': get_message("balance_sheet_years_retrieved", locale),
                'data': {
                        'balance_years': years_tuple,
                        'balance_name': balance_name
                        },
                'success': True
            }, 200

            
        except Exception as e:
            logger.error(f"Error in get_by_company_id_and_balance_year: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message("failed_retrieve_balance_years", locale)
            }, 500
        
# update benchmark report note by report id
    def update_benchmark_report_note(
        self,
        current_user,
        id_analysis: int,
        name: str,
        note: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Update note for a specific KPI (matched by name) in a benchmark analysis.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            if not id_analysis or not name:
                return {"message": get_message("analysis_id_and_kpi_required", locale)}, 400

            #  Fetch analysis directly (DO NOT use AnalysisKpiInfo here)
            analysis = KbaiAnalysis.query.filter_by(id_analysis=id_analysis).first()
            if not analysis:
                return {"message": get_message("analysis_not_found", locale)}, 404

            #  Fetch benchmark balances to validate company access
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=id_analysis).all()
            if not analysis_kpis:
                return {"message": get_message("no_benchmarks_found_for_analysis", locale)}, 404

            first_balance = KbaiBalance.query.filter_by(
                id_balance=analysis_kpis[0].id_balance
            ).first()

            company_id = first_balance.id_company if first_balance else None
            has_access, error_msg = ComparisonReportService().check_company_access(
                current_user, company_id
            )
            if not has_access:
                return {"message": error_msg}, 403

            # Fetch ALL KPI infos for analysis
            analysis_kpi_infos = AnalysisKpiInfo.query.filter_by(
                id_analysis=id_analysis
            ).all()

            if not analysis_kpi_infos:
                return {"message": get_message("no_kpi_info_found_for_analysis", locale)}, 404

            # Find KPI by name
            target_kpi_info = None
            for info in analysis_kpi_infos:
                if info.kpi_value and info.kpi_value.kpi_name == name:
                    target_kpi_info = info
                    break

            if not target_kpi_info:
                return {"message": get_message("kpi_not_found_in_analysis", locale, name=name)}, 404

            # Update note
            target_kpi_info.note = note
            db.session.commit()

            return {
                "message": get_message("benchmark_kpi_note_updated", locale)
            }, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating benchmark KPI note: {str(e)}", exc_info=True)
            return {
                "message": "Internal server error",
                "error_details": str(e)
            }, 500


    # get benchmark report list by company id
    def get_benchmark_report_list(
        self,
        company_id: int,
        current_user: TbUser,
        page: int = 1,
        per_page: int = 10
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get benchmark report list with pagination.
        Returns paginated list of benchmark reports with balances mapped to keys.

        Args:
            company_id: Company ID
            current_user: Current authenticated user
            page: Page number (default 1)
            per_page: Items per page (default 10)

        Returns:
            Tuple of (response_data, status_code)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Validate pagination params
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 10

            # 1. Check access
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403

            # 2. Get all balances for this company
            balances = KbaiBalance.query.filter_by(id_company=company_id, is_deleted=False).all()
            if not balances:
                return {
                    "success": False,
                    "message": get_message("no_benchmark_reports_found", locale),
                    "data": {
                        "balance_sheets": [],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "total_pages": 0
                        }
                    }
                }, 200

            balance_ids = [b.id_balance for b in balances]
            id_to_balance_info = {b.id_balance: b for b in balances}

            # 3. Get analysis_kpi entries for these balances
            analysis_kpis = KbaiAnalysisKpi.query.filter(
                KbaiAnalysisKpi.id_balance.in_(balance_ids)
            ).all()

            if not analysis_kpis:
                return {
                    "sucess": False,
                    "message": get_message("no_benchmark_reports_found", locale),
                    "data": {
                    "balance_sheets": [],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "total_pages": 0
                        }
                    }
                }, 200

            # Extract all analysis_ids linked to these balances
            analysis_ids = {ak.id_analysis for ak in analysis_kpis}

            # 4. Get only BENCHMARK analyses from these IDs
            benchmark_analyses = KbaiAnalysis.query.filter(
                KbaiAnalysis.id_analysis.in_(analysis_ids),
                KbaiAnalysis.analysis_type == "BENCHMARK"
            ).all()

            if not benchmark_analyses:
                return {
                    "success": False,
                    "message": get_message("no_benchmark_reports_found", locale),
                    "data": {
                        "balance_sheets": [],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "total_pages": 0
                        }
                    }
                }, 200

            benchmark_analysis_ids = [a.id_analysis for a in benchmark_analyses]

            # 5. Get total count of reports for pagination
            total_reports = KbaiReport.query.filter(
                KbaiReport.id_analysis.in_(benchmark_analysis_ids)
            ).count()

            total_pages = (total_reports + per_page - 1) // per_page

            # 6. Get paginated reports
            reports = KbaiReport.query.filter(
                KbaiReport.id_analysis.in_(benchmark_analysis_ids)
            ).offset((page - 1) * per_page).limit(per_page).all()

            output = []
            for report in reports:
                balances_obj = {}
                for ak in analysis_kpis:
                    if ak.id_analysis == report.id_analysis:
                        balance = id_to_balance_info.get(ak.id_balance)
                        if balance:
                            balance_type = ak.kpi_list_json.get("balance_type", "") if ak.kpi_list_json else ""
                            if balance_type:
                                balances_obj[balance_type] = balance.file or ""

                output.append({
                    "id_report": report.id_report,
                    "name": report.name,
                    "time": report.time.isoformat() if report.time else None,
                    "balances": balances_obj
                })

            return {
                "success": True,
                "message": get_message("benchmark_reports_retrieved", locale),
                "data": {
                    "balance_sheets": output,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total_reports,
                        "total_pages": total_pages
                    }
                }
            }, 200

        except Exception as e:
            logger.error(f"Error getting benchmark report list: {str(e)}", exc_info=True)
            return {"message": "Internal server error", "error_details": str(e)}, 500

    # create delete benchmark report by report id
    def delete_benchmark_report(self, current_user, report_id: int) -> Tuple[Dict[str, Any], int]:
        try:
            locale = request.headers.get('Accept-Language', 'en')
            if not report_id:
                return {"message": get_message("report_id_required", locale)}, 400

            # Fetch the report
            report = KbaiReport.query.filter_by(id_report=report_id).first()
            if not report:
                return {"message": get_message("report_not_found", locale)}, 404

            # Fetch the associated analysis
            analysis = KbaiAnalysis.query.filter_by(id_analysis=report.id_analysis).first()
            if not analysis:
                return {"message": get_message("analysis_not_found_for_report", locale)}, 404

            # Check company access
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpis:
                return {"message": get_message("no_benchmarks_found_for_report", locale)}, 200

            analysis_kpi_infos = AnalysisKpiInfo.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpi_infos:
                return {"message": get_message("no_analysis_kpi_infos_found", locale)}, 200

            first_balance = KbaiBalance.query.filter_by(id_balance=analysis_kpis[0].id_balance).first()
            company_id = first_balance.id_company if first_balance else None    
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403

            # CASCADE DELETE: Find and delete all competitor reports (child reports)
            competitor_reports = KbaiReport.query.filter_by(parent_report_id=report_id).all()
            
            for competitor_report in competitor_reports:
                competitor_analysis_id = competitor_report.id_analysis
                
                # Delete in correct order to avoid foreign key constraint violations
                # 1. Delete AnalysisKpiInfo (references id_analysis)
                AnalysisKpiInfo.query.filter_by(
                    id_analysis=competitor_analysis_id
                ).delete()
                
                # 2. Delete KbaiAnalysisKpi (references id_analysis)
                KbaiAnalysisKpi.query.filter_by(
                    id_analysis=competitor_analysis_id
                ).delete()
                
                # 3. Delete KbaiReport (references id_analysis)
                KbaiReport.query.filter_by(id_report=competitor_report.id_report).delete()
                
                # 4. Finally delete KbaiAnalysis
                KbaiAnalysis.query.filter_by(
                    id_analysis=competitor_analysis_id
                ).delete()
            
            # Delete parent report entries in correct order
            # 1. Delete AnalysisKpiInfo (references id_analysis)
            AnalysisKpiInfo.query.filter_by(id_analysis=analysis.id_analysis).delete()
            
            # 2. Delete KbaiAnalysisKpi (references id_analysis)
            KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).delete()
            
            # 3. Delete KbaiReport (references id_analysis)
            KbaiReport.query.filter_by(id_report=report_id).delete()
            
            # 4. Finally delete KbaiAnalysis
            KbaiAnalysis.query.filter_by(id_analysis=analysis.id_analysis).delete()
            
            db.session.commit()

            deleted_count = len(competitor_reports)
            message = get_message("benchmark_deleted_with_competitors", locale, count=deleted_count) if deleted_count > 0 else get_message("benchmark_deleted_successfully", locale)

            return {
                "message": message
            }, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting benchmark report {str(e)}")
            return {"message": "Internal server error", "error_details": str(e)}, 500

    def add_competitor_to_benchmark(
        self,
        current_user,
        parent_report_id: int,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create a NEW competitor comparison report based on an existing benchmark.
        
        Frontend payload:
        {
          "comparison_name": "Analisi Febbraio",
          "tipologia": "Diretto",
          "competitor_id": 13,
          "year": 2024,
          "balancesheet_name": "Definitivo 2024"
        }
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            if not parent_report_id:
                return {"message": get_message("parent_report_id_required", locale)}, 400

            payload = request.get_json() or {}
            competitor_company_id = payload.get("competitor_id")
            year = payload.get("year")
            balancesheet_name = payload.get("balancesheet_name")
            comparison_name = payload.get("comparison_name")
            tipologia = payload.get("tipologia", "Diretto")

            if not competitor_company_id:
                return {"message": get_message("competitor_id_required", locale)}, 400
            if not year:
                return {"message": get_message("year_required", locale)}, 400
            if not balancesheet_name:
                return {"message": get_message("balancesheet_name_required", locale)}, 400

            # 1) Get parent benchmark report & analysis
            parent_report = KbaiReport.query.filter_by(
                id_report=parent_report_id,
                type="BENCHMARK"
            ).first()
            if not parent_report:
                return {"message": get_message("parent_benchmark_not_found", locale)}, 404

            parent_analysis = KbaiAnalysis.query.filter_by(
                id_analysis=parent_report.id_analysis
            ).first()
            if not parent_analysis:
                return {"message": get_message("parent_analysis_not_found", locale)}, 404

            # 2) Get all parent benchmark balances
            parent_analysis_kpis = KbaiAnalysisKpi.query.filter_by(
                id_analysis=parent_analysis.id_analysis
            ).all()
            if not parent_analysis_kpis:
                return {"message": get_message("no_balances_found_in_parent", locale)}, 400

            parent_balance_ids = [ak.id_balance for ak in parent_analysis_kpis]

            # 3) Infer main company + access check
            first_balance = KbaiBalance.query.filter_by(
                id_balance=parent_balance_ids[0]
            ).first()
            if not first_balance:
                return {"message": get_message("main_company_balance_not_found", locale)}, 400

            has_access, error_msg = ComparisonReportService().check_company_access(
                current_user, first_balance.id_company
            )
            if not has_access:
                return {"message": error_msg}, 403

            # 4) Validate competitor company
            # Update validation to support typologies
            competitor_query = KbaiCompany.query.filter_by(
                id_company=competitor_company_id,
                is_competitor=True,
                is_deleted=False
            )
            
            if tipologia == "Diretto":
                competitor_query = competitor_query.filter_by(parent_company_id=first_balance.id_company)
            
            competitor = competitor_query.first()
            if not competitor:
                return {"message": get_message("invalid_competitor_for_company", locale)}, 400

            # 5) Find competitor balance (try multiple strategies)
            from sqlalchemy import and_, func

            # Strategy 1: Exact match on file
            competitor_balance = KbaiBalance.query.filter_by(
                id_company=competitor_company_id,
                year=year,
                file=balancesheet_name,
                is_deleted=False
            ).first()

            # Strategy 2: Case-insensitive match
            if not competitor_balance:
                competitor_balance = KbaiBalance.query.filter(
                    KbaiBalance.id_company == competitor_company_id,
                    KbaiBalance.year == year,
                    func.lower(KbaiBalance.file) == func.lower(balancesheet_name),
                    KbaiBalance.is_deleted == False
                ).first()

            if not competitor_balance:
                return {"message": get_message("competitor_balance_not_found", locale)}, 404

            # 5.5) Check if this competitor has already been added to this benchmark report
            existing_competitor_reports = KbaiReport.query.filter_by(
                parent_report_id=parent_report_id
            ).all()
            
            for existing_report in existing_competitor_reports:
                existing_analysis = KbaiAnalysis.query.filter_by(
                    id_analysis=existing_report.id_analysis
                ).first()
                
                if not existing_analysis:
                    continue
                
                # Check if this competitor balance is already in this analysis
                existing_competitor_mapping = KbaiAnalysisKpi.query.filter_by(
                    id_analysis=existing_analysis.id_analysis,
                    id_balance=competitor_balance.id_balance
                ).first()
                
                if existing_competitor_mapping:
                    if existing_competitor_mapping.kpi_list_json and \
                       existing_competitor_mapping.kpi_list_json.get("balance_type") == "competitor":
                        competitor_name = competitor.company_name if competitor else "Competitor"
                        return {
                            "message": get_message("competitor_benchmark_already_exists", locale)
                        }, 400

            # 6) Create NEW analysis for competitor comparison
            new_analysis = KbaiAnalysis(
                analysis_name=f"{comparison_name or 'Competitor Comparison'}",
                analysis_type="BENCHMARK_COMPETITOR",
                time=datetime.utcnow()
            )
            db.session.add(new_analysis)
            db.session.flush()
            new_analysis_id = new_analysis.id_analysis

            # 7) Copy parent 3 benchmark balances to new analysis
            for parent_ak in parent_analysis_kpis:
                new_mapping = KbaiAnalysisKpi(
                    id_analysis=new_analysis_id,
                    id_balance=parent_ak.id_balance,
                    kpi_list_json=parent_ak.kpi_list_json
                )
                db.session.add(new_mapping)

            # 8) Add competitor balance to new analysis
            competitor_kpis = KbaiKpiValue.query.filter_by(
                id_balance=competitor_balance.id_balance
            ).all()

            kpi_map: Dict[str, float] = {}
            for kv in competitor_kpis:
                kpi_map[kv.kpi_name] = float(kv.value) if kv.value is not None else None

            competitor_mapping = KbaiAnalysisKpi(
                id_analysis=new_analysis_id,
                id_balance=competitor_balance.id_balance,
                kpi_list_json={
                    "kpis": kpi_map,
                    "year": competitor_balance.year,
                    "balance_type": "competitor",
                    "missing_fields": [],
                },
            )
            db.session.add(competitor_mapping)

            # 9) Recompute KPI insights for competitor comparison (competitor-specific calculation)
            all_balance_ids = parent_balance_ids + [competitor_balance.id_balance]
            all_balances = KbaiBalance.query.filter(
                KbaiBalance.id_balance.in_(all_balance_ids)
            ).all()
            all_kpi_values = KbaiKpiValue.query.filter(
                KbaiKpiValue.id_balance.in_(all_balance_ids)
            ).all()

            # Separate benchmark and competitor data
            benchmark_kpi_data = defaultdict(list)  # {kpi_name: [(year, value), ...]}
            competitor_kpi_data = {}  # {kpi_name: value}
            benchmark_years = []

            balances_dict = {b.id_balance: b for b in all_balances}
            
            for kv in all_kpi_values:
                balance = balances_dict.get(kv.id_balance)
                if not balance:
                    continue
                
                value = float(kv.value) if kv.value is not None else None
                
                # Check if this balance is competitor
                is_competitor = (balance.id_balance == competitor_balance.id_balance)
                
                if is_competitor:
                    competitor_kpi_data[kv.kpi_name] = value
                else:
                    benchmark_kpi_data[kv.kpi_name].append((balance.year, value))
                    benchmark_years.append(balance.year)

            # Calculate competitor statuses (competitor vs benchmark)
            competitor_statuses = calculate_competitor_kpi_statuses(
                competitor_kpi_data, benchmark_kpi_data
            )

            # Build insights and store in AnalysisKpiInfo for competitor KPIs only
            for kpi_name, comp_value in competitor_kpi_data.items():
                benchmark_values = benchmark_kpi_data.get(kpi_name, [])
                
                if not benchmark_values:
                    continue
                
                values = [v for _, v in sorted(benchmark_values)]
                benchmark_baseline = sum(values) / len(values) if values else 0
                benchmark_min = min(values) if values else 0
                benchmark_max = max(values) if values else 0
                
                # Calculate deviation: ((Competitor - Benchmark Baseline) / Benchmark Baseline) * 100
                deviation = None
                if benchmark_baseline != 0 and comp_value is not None:
                    try:
                        # Same formula as comparison report: ((new - old) / abs(old)) * 100
                        deviation = ((comp_value - benchmark_baseline) / abs(benchmark_baseline)) * 100
                        # Store full numeric deviation (rounded to 2 decimals, no artificial range limit)
                        deviation = round(deviation, 2)
                    except (ZeroDivisionError, TypeError, ValueError) as e:
                        logger.warning(f"Error calculating deviation for {kpi_name}: {str(e)}")
                        deviation = None
                
                status = competitor_statuses.get(kpi_name, "AVERAGE")
                
                insight = build_competitor_kpi_insight(
                    kpi_name=kpi_name,
                    competitor_value=comp_value,
                    benchmark_baseline=benchmark_baseline,
                    benchmark_min=benchmark_min,
                    benchmark_max=benchmark_max,
                    benchmark_years=benchmark_years,
                    status=status
                )
                
                # Get KPI value record for id_kpi (from competitor balance)
                kv_record = next(
                    (kv for kv in all_kpi_values 
                     if kv.kpi_name == kpi_name and kv.id_balance == competitor_balance.id_balance), 
                    None
                )
                if not kv_record:
                    continue
                
                # Update competitor KbaiKpiValue with deviation
                try:
                    kv_record.deviation = deviation
                    kv_record.source = f"competitor_benchmark_{parent_report_id}"
                    db.session.add(kv_record)

                    # Also update KpiLogic thresholds based on this deviation so that
                    # new competitor benchmark entries immediately get correct
                    # critical/acceptable percentages.
                    try:
                        from src.app.api.v1.services.k_balance.comparison_report_service import (
                            comparison_report_service,
                        )
                        comparison_report_service._update_kpi_logic_for_value(kv_record)
                    except Exception as inner_e:
                        # Log but don't fail competitor benchmark creation
                        logger.error(
                            "Failed to update KpiLogic from competitor deviation for id_kpi %s: %s",
                            getattr(kv_record, "id_kpi", None),
                            str(inner_e),
                        )

                    logger.info(
                        f"Updated deviation for competitor KPI '{kpi_name}': {deviation}% "
                        f"(Competitor: {comp_value}, Baseline: {benchmark_baseline})"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to update deviation for competitor KPI {kpi_name}: {str(e)}"
                    )
                
                # Store in AnalysisKpiInfo (competitor-specific synthesis and suggestion)
                record = AnalysisKpiInfo(
                    id_analysis=new_analysis_id,
                    id_kpi=kv_record.id_kpi,
                    synthesis=insight["synthesis"],
                    suggestion=insight["suggestion"],
                    note=None
                )
                db.session.merge(record)
            
            db.session.commit()

            # 10) Create NEW report
            new_report = KbaiReport(
                id_analysis=new_analysis_id,
                name=comparison_name or f"Competitor Comparison {datetime.utcnow().strftime('%Y-%m-%d')}",
                type=tipologia,
                time=datetime.utcnow(),
                parent_report_id=parent_report_id
            )
            db.session.add(new_report)
            db.session.commit()

            return {
                "message": get_message("competitor_benchmark_created", locale),
            }, 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating competitor comparison: {str(e)}", exc_info=True)
            return {"message": "Internal server error", "error_details": str(e)}, 500

    def get_suggested_competitors(self, current_user, parent_report_id: int, tipologia: str = "Diretto") -> Tuple[Dict[str, Any], int]:
        """
        Fetch matching competitors based on typology and parent report context.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            if not parent_report_id:
                return {"message": get_message("parent_report_id_required", locale)}, 400

            # 1) Get parent company context
            parent_report = KbaiReport.query.filter_by(id_report=parent_report_id, type="BENCHMARK").first()
            if not parent_report:
                return {"message": get_message("parent_benchmark_not_found", locale)}, 404

            parent_analysis_kpi = KbaiAnalysisKpi.query.filter_by(id_analysis=parent_report.id_analysis).first()
            if not parent_analysis_kpi:
                return {"message": get_message("no_balances_found_in_parent", locale)}, 400
            
            parent_balance = KbaiBalance.query.get(parent_analysis_kpi.id_balance)
            if not parent_balance:
                return {"message": get_message("main_company_balance_not_found", locale)}, 400
            
            parent_company_id = parent_balance.id_company

            # Check access
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, parent_company_id)
            if not has_access:
                return {"message": error_msg}, 403

            # 2) Extract Parent Attributes
            from src.app.database.models.kbai import KbaiCompanyZone, KbaiZone, KbaiCompanySector, KbaiSector
            
            parent_region = None
            parent_ateco_division = None
            parent_geographic_area = None
            parent_country = "Italy"

            zone_mapping = KbaiCompanyZone.query.filter_by(id_company=parent_company_id, primary_flag=True).first()
            if zone_mapping:
                zone = KbaiZone.query.get(zone_mapping.id_zone)
                if zone:
                    parent_region = zone.region
                    parent_country = zone.country or "Italy"

            sector_mapping = KbaiCompanySector.query.filter_by(id_company=parent_company_id, primary_flag=True).first()
            if sector_mapping:
                sector = KbaiSector.query.get(sector_mapping.id_sector)
                if sector:
                    parent_ateco_division = sector.division
                    parent_geographic_area = sector.geographic_area

            # 3) Build Competitor Query only for parent company
            query = db.session.query(KbaiCompany).filter(
                KbaiCompany.is_deleted == False,
                KbaiCompany.is_competitor == True,
                KbaiCompany.parent_company_id == parent_company_id
            )

            if tipologia == "Diretto":
                query = query.filter(KbaiCompany.parent_company_id == parent_company_id)
            elif tipologia == "Regionale":
                if not parent_region or not parent_ateco_division:
                    query = query.filter(KbaiCompany.parent_company_id == parent_company_id)
                else:
                    query = query.join(KbaiCompanyZone, KbaiCompany.id_company == KbaiCompanyZone.id_company)\
                                 .join(KbaiZone, KbaiCompanyZone.id_zone == KbaiZone.id_zone)\
                                 .join(KbaiCompanySector, KbaiCompany.id_company == KbaiCompanySector.id_company)\
                                 .join(KbaiSector, KbaiCompanySector.id_sector == KbaiSector.id_sector)\
                                 .filter(KbaiZone.region == parent_region, KbaiSector.division == parent_ateco_division)
            elif tipologia == "Nazionale":
                if not parent_country or not parent_ateco_division:
                    query = query.filter(KbaiCompany.parent_company_id == parent_company_id)
                else:
                    query = query.join(KbaiCompanyZone, KbaiCompany.id_company == KbaiCompanyZone.id_company)\
                                 .join(KbaiZone, KbaiCompanyZone.id_zone == KbaiZone.id_zone)\
                                 .join(KbaiCompanySector, KbaiCompany.id_company == KbaiCompanySector.id_company)\
                                 .join(KbaiSector, KbaiCompanySector.id_sector == KbaiSector.id_sector)\
                                 .filter(KbaiZone.country == parent_country, KbaiSector.division == parent_ateco_division)
            elif tipologia == "Macro Area":
                if parent_geographic_area is None or not parent_ateco_division:
                    query = query.filter(KbaiCompany.parent_company_id == parent_company_id)
                else:
                    query = query.join(KbaiCompanySector, KbaiCompany.id_company == KbaiCompanySector.id_company)\
                                 .join(KbaiSector, KbaiCompanySector.id_sector == KbaiSector.id_sector)\
                                 .filter(KbaiSector.geographic_area == parent_geographic_area, KbaiSector.division == parent_ateco_division)

            companies = query.all()

            # 4) Extract Companies + Nested Balances
            result_data = []
            for company in companies:
                balances = KbaiBalance.query.filter_by(id_company=company.id_company, is_deleted=False).all()
                result_data.append({
                    "id_company": company.id_company,
                    "company_name": company.company_name,
                    "balances": [
                        {
                            "id_balance": b.id_balance,
                            "year": b.year,
                            "type": b.type,
                            "file": b.file
                        } for b in balances
                    ]
                })

            return {
                "message": get_message("competitor_companies_retrieved_success", locale),
                "data": result_data,
                "success": True
            }, 200

        except Exception as e:
            logger.error(f"Error in get_suggested_competitors: {str(e)}")
            return {"message": str(e)}, 500
    
    def get_competitor_reports(self, current_user, report_id: int) -> Tuple[Dict[str, Any], int]:
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Fetch the report
            report = KbaiReport.query.filter_by(id_report=report_id).first() 
            if not report:
                return {"message": get_message("report_not_found", locale)}, 404
                      
            # Fetch the associated analysis
            analysis = KbaiAnalysis.query.filter_by(id_analysis=report.id_analysis).first()
            if not analysis:
                return {"message": get_message("analysis_not_found_for_report", locale)}, 404

            # Fetch all KbaiAnalysisKpi entries for this analysis
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpis:
                return {"message": get_message("no_benchmarks_found_for_report", locale)}, 200
            
            #add check user access to company
            first_balance = KbaiBalance.query.filter_by(id_balance=analysis_kpis[0].id_balance).first()
            company_id = first_balance.id_company if first_balance else None    
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403
            
            # Get balances for the analysis_kpis
            balance_ids = [ak.id_balance for ak in analysis_kpis]
            
            balances = KbaiBalance.query.filter(KbaiBalance.id_balance.in_(balance_ids)).all()
            id_to_balance = {b.id_balance: b for b in balances}
            
            # Build balances data
            balances_data = {}

            for ak in analysis_kpis:
                balance = id_to_balance.get(ak.id_balance)
                if not balance or not ak.kpi_list_json:
                    continue

                balance_type = ak.kpi_list_json.get("balance_type", "")
                if not balance_type:
                    continue
                if balance_type != "competitor":
                    continue
                print(balance_type,"BALANCE_TYPE")

                balances_data[balance_type] = {
                    "file": balance.file or "",
                    "kpis": ak.kpi_list_json.get("kpis", {}),
                    "year": ak.kpi_list_json.get("year")
                }
                print(balances_data,"BALANCES_DATA")

            # Separate benchmark and competitor data for competitor-specific calculation
            benchmark_kpi_data = defaultdict(list)  # {kpi_name: [(year, value), ...]}
            competitor_kpi_data = {}  # {kpi_name: value}
            benchmark_years = []

            for ak in analysis_kpis:
                if not ak.kpi_list_json:
                    continue
                
                balance_type = ak.kpi_list_json.get("balance_type", "")
                kpis = ak.kpi_list_json.get("kpis", {})
                year = ak.kpi_list_json.get("year")
                
                if balance_type == "competitor":
                    for kpi_name, value in kpis.items():
                        competitor_kpi_data[kpi_name] = value
                else:
                    benchmark_years.append(year)
                    for kpi_name, value in kpis.items():
                        benchmark_kpi_data[kpi_name].append((year, value))

            # Calculate competitor statuses (competitor vs benchmark)
            competitor_statuses = calculate_competitor_kpi_statuses(
                competitor_kpi_data, benchmark_kpi_data
            )

            # Get stored AnalysisKpiInfo (already has competitor-specific synthesis/suggestion)
            analysis_kpi_infos = AnalysisKpiInfo.query.filter_by(
                id_analysis=analysis.id_analysis
            ).all()

            # Build kpi_statuses response with competitor-specific data
            kpi_statuses = {}
            for kpi_name, comp_value in competitor_kpi_data.items():
                benchmark_values = benchmark_kpi_data.get(kpi_name, [])
                
                if not benchmark_values:
                    continue
                
                values = [v for _, v in sorted(benchmark_values)]
                benchmark_baseline = sum(values) / len(values) if values else 0
                benchmark_min = min(values) if values else 0
                benchmark_max = max(values) if values else 0
                
                status = competitor_statuses.get(kpi_name, "AVERAGE")
                
                # Get stored insight from AnalysisKpiInfo (competitor-specific)
                kpi_info = next(
                    (info for info in analysis_kpi_infos 
                     if info.kpi_value and info.kpi_value.kpi_name == kpi_name), 
                    None
                )
                
                if kpi_info:
                    # Use stored competitor-specific synthesis and suggestion
                    # Calculate goal percentage for response
                    from .kpi_status_services import calculate_competitor_goal_percentage
                    goal_percentage = calculate_competitor_goal_percentage(
                        comp_value, benchmark_baseline, kpi_name
                    )
                    
                    kpi_statuses[kpi_name] = {
                        "id_kpi": kpi_info.id_kpi,
                        "status": status,
                        "note": kpi_info.note,
                        "goal": goal_percentage,
                        "synthesis": kpi_info.synthesis,  # Competitor-specific synthesis
                        "suggestion": [kpi_info.suggestion] if kpi_info.suggestion else []  # Competitor-specific suggestion
                    }
            return {
                "message": get_message("competitor_benchmarks_fetched", locale),
                "data": {
                    "parent_id_report": report.id_report,
                    "parent_analysis_id": report.id_analysis,  
                    "parent_name": report.name,
                    "time": report.time.isoformat() if report.time else None,
                    "benchmarks": balances_data,
                    "kpi_statuses": kpi_statuses
                }
            }, 200
        except Exception as e:
            logger.error(f"Error fetching benchmarks for report {report_id}: {str(e)}")
            return {"message": get_message("internal_server_error", locale), "error_details": str(e)}, 500

