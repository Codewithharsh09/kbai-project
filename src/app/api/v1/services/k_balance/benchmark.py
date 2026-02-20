"""
Banchmark Service

Handles financial KPI between benchmark balance sheets (years).
"""

from typing import Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import or_
import logging

from src.app.database.models import (
    KbaiBalance,
    KbaiAnalysis,
    KbaiCompany,
    KbaiReport,
    KbaiKpiValue,
    KbaiAnalysisKpi,
    TbUser
)
from flask import request
from collections import defaultdict
from src.app.api.v1.services.k_balance.comparison_report_service import ComparisonReportService

# from src.app.database.models.kbai_balance.kbai_kpi_values import KbaiKpiValue
from src.extensions import db

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
            balance_specs_raw = [balanceSheetToCompare, comparitiveBalancesheet, referenceBalanceSheet]
            balances_specs = [spec for spec in balance_specs_raw if spec is not None]
            if not company_id or len(balances_specs) == 0:
                return {"message": "company_id and at least one balance sheet are required"}, 400
            
            # Validate each spec (month is now optional)
            allowed_types = ["final", "forecast", "provisional"]  # Define allowed balance types (map to budgetType)
            for spec in balances_specs:
                if not isinstance(spec, dict) or "year" not in spec or "budgetType" not in spec:
                    return {"message": "Each balance sheet must have 'year' and 'budgetType' (month is optional)"}, 400
                if spec["budgetType"] not in allowed_types:
                    return {"message": f"Invalid budgetType '{spec['budgetType']}'"}, 400

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
                        return {"message": f"No balance found for year {year}, budgetType '{b_type}', month {month}"}, 400
                else:
                    # If month not specified, check if any balance matches year and type (ignoring month)
                    if not any(b.year == year and b.type == b_type for b in balances):
                        return {"message": f"No balance found for year {year}, budgetType '{b_type}'"}, 400

            balance_ids = [b.id_balance for b in balances]

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
                return {"message": "No KPI values found for selected balances"}, 200
             # Compose report name as companyName-year1-year2-year3 etc
            # Assume all balances are for the same company (from balances list)
            first_balance = balances[0] if balances else None
            company_obj = KbaiCompany.query.filter_by(id_company=first_balance.id_company if first_balance else None).first()
            company_name = company_obj.company_name if company_obj and hasattr(company_obj, "company_name") else "Company"
            # Gather all years from balances
            all_years = [b.year for b in balances if hasattr(b, "year")]
            years_sorted = sorted(set(all_years))
            years_joined = "-".join(str(y) for y in years_sorted)
            report_name = f"{company_name}-{years_joined}" if years_joined else company_name
            # 5. Create Benchmark Analysis Entry
            analysis = KbaiAnalysis(
                analysis_name=f"benchmark_generated {report_name}",
                analysis_type="BENCHMARK",
                time=datetime.utcnow()
            )
            db.session.add(analysis)
            db.session.flush()  # get id_analysis
            analysis_id = analysis.id_analysis

            # 6. Create KbaiAnalysisKpi Mapping -- now with storing kpis in JSON format
            kpis_by_balance = defaultdict(dict)
            # Optionally, also collect all years if present in KbaiBalance
            year_by_balance = {}

            balances_dict = {b.id_balance: b for b in balances}

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

            # 8. Final Response
            return {
                "message": "Benchmark report created successfully",
                "data": {}
            }, 201

        except Exception as e:
            db.session.rollback()
            return {"message": str(e)}, 500
    
    def get_benchmarks_by_report(self, current_user, report_id: int) -> Tuple[Dict[str, Any], int]:
        try:
            if not report_id:
                return {"message": "report_id is required"}, 400

            # Fetch the report
            report = KbaiReport.query.filter_by(id_report=report_id).first()
            if not report:
                return {"message": "Report not found"}, 404

            # Fetch the associated analysis
            analysis = KbaiAnalysis.query.filter_by(id_analysis=report.id_analysis).first()
            if not analysis:
                return {"message": "Analysis not found for the report"}, 404

            # Fetch all KbaiAnalysisKpi entries for this analysis
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpis:
                return {"message": "No benchmarks found for the report"}, 200
            
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
                if balance:
                    balance_type = ak.kpi_list_json.get("balance_type", "") if ak.kpi_list_json else ""
                    kpis = ak.kpi_list_json.get("kpis", {}) if ak.kpi_list_json else {}
                    if balance_type:
                        balances_data[balance_type] = {
                            "file": balance.file or "",
                            "kpis": kpis
                        }

            return {
                "message": "Benchmarks fetched successfully",
                "data": {
                    "id_report": report.id_report,
                    "name": report.name,
                    "time": report.time.isoformat() if report.time else None,
                    "benchmarks": balances_data
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
                    'message': 'Valid company_id is required'
                }, 400
            
            # Query balance sheets for company
            records = KbaiBalance.query.filter_by(
                id_company=company_id,
                is_deleted=False
            ).all()
            if not records:
                return {
                    'message': 'No balance sheets found',
                    'data': {
                        'balance_years': ()
                            },
                    'success': True
                    }, 200
                    
            # Collect unique years
            years_set = set()

            for record in records:
                years_set.add(record.year)

            # Convert to tuple
            years_tuple = tuple(sorted(years_set))

            logger.info(f"Retrieved {len(years_tuple)} unique years for company {company_id}")

            return {
                'message': 'Balance sheet years retrieved successfully',
                'data': {
                        'balance_years': years_tuple
                        },
                'success': True
            }, 200

            
        except Exception as e:
            logger.error(f"Error in get_by_company_id_and_balance_year: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve balance sheet years'
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
                    "message": "No balances found for the company",
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
                    "message": "No benchmark reports found",
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
                    "message": "No benchmark reports found",
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
                "message": "Benchmark reports retrieved successfully",
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
            if not report_id:
                return {"message": "report_id is required"}, 400

            # Fetch the report
            report = KbaiReport.query.filter_by(id_report=report_id).first()
            if not report:
                return {"message": "Report not found"}, 404

            # Fetch the associated analysis
            analysis = KbaiAnalysis.query.filter_by(id_analysis=report.id_analysis).first()
            if not analysis:
                return {"message": "Analysis not found for the report"}, 404

            # Check company access
            analysis_kpis = KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).all()
            if not analysis_kpis:
                return {"message": "No benchmarks found for the report"}, 200

            first_balance = KbaiBalance.query.filter_by(id_balance=analysis_kpis[0].id_balance).first()
            company_id = first_balance.id_company if first_balance else None    
            has_access, error_msg = ComparisonReportService().check_company_access(current_user, company_id)
            if not has_access:
                return {"message": error_msg}, 403

            # Delete entries
            KbaiAnalysisKpi.query.filter_by(id_analysis=analysis.id_analysis).delete()
            KbaiReport.query.filter_by(id_report=report_id).delete()
            KbaiAnalysis.query.filter_by(id_analysis=analysis.id_analysis).delete()
            db.session.commit()

            return {
                "message": "Benchmark report deleted successfully"
            }, 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting benchmark report {str(e)}")
            return {"message": "Internal server error", "error_details": str(e)}, 500
        