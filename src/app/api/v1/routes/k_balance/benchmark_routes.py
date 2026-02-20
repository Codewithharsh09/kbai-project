"""
Benchmark Routes

Handles endpoints for creating/generating benchmark reports.
"""

from flask import request, current_app
from flask_restx import Resource

from src.app.api.v1.services.k_balance.benchmark import BenchmarkService
from src.app.api.middleware import require_auth0, get_current_user
from src.common.response_utils import (
    success_response, error_response, internal_error_response
)
from src.common.localization import get_message
from src.app.api.v1.swaggers import (
    benchmark_ns,
    create_benchmark_payload_model,
    benchmark_create_response_model,
    add_competitor_comparison_response_model,
    competitor_reports_response_model,
    benchmarks_list_response_model,
    validation_error_model,
    internal_error_model,
    not_found_error_model,
    benchmark_list_item_model,
    benchmarks_list_response,
    benchmarks_report_response_model,
    benchmarks_report_list_response,
    benchmark_delete_response_model,
    benchmark_update_response_model,
    update_benchmark_payload_model,
    update_validation_error_model,
    note_not_found_error_model,
    validation_error_getbenchmark_model,
    not_found_error_getBenchmark_model,
    suggested_competitors_response_model
)

# Fix route path to match OpenAPI design & avoid 404s on '/api/v1/kbai-balance/benchmark/<int:company_id>'
@benchmark_ns.route('/benchmark/<int:company_id>')
@benchmark_ns.param('company_id', 'Company ID for which to create the benchmark')
class Benchmark(Resource):
    """Handle creation of a benchmark report."""

    @benchmark_ns.doc(
        'create_benchmark',
        params={'company_id': 'The ID of the company to create a benchmark for'},
        responses={
            201: ('Benchmark report created successfully', benchmark_create_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @benchmark_ns.expect(create_benchmark_payload_model)
    @require_auth0
    def post(self, company_id):
        """
        Create a new benchmark report for a given company.

        Path Parameters:
        - company_id: int, required

        Body (JSON):
        - year: int, required
        - type: str, required
        - month: int, optional
        - note: str, optional
        - benchmarks: dict, required

        Returns:
        - 201: Benchmark report created successfully
        - 400: Validation error (missing required field)
        - 401: Authentication required
        - 403: Access denied (user cannot access this company)
        - 404: Not Found (company or balance sheets missing)
        - 500: Internal server error
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )

            # Call service to create/generate benchmark
            result, status_code = BenchmarkService().create_benchmark(current_user, company_id)
            if status_code == 201:
                return success_response(
                    message=result.get('message', get_message('benchmark_create_success', locale)),
                    data=result.get('data') if isinstance(result, dict) else None,
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get('message', get_message('benchmark_create_failed', locale)),
                    data=result.get('data') if isinstance(result, dict) else None,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Benchmark create error: {str(e)}")
            return internal_error_response(
                message=get_message('benchmark_create_error', locale),
                error_details=str(e)
            )
        
# get report list by company id
@benchmark_ns.route('/benchmark/report/list/<int:company_id>')
@benchmark_ns.param('company_id', 'Company ID')
class GetBalanceSheetsForBenchmarkReport(Resource):
    """Get benchmark report list with pagination"""
    
    @benchmark_ns.doc(
        'get_benchmark_report_list',
        params={
            'company_id': 'Company ID from URL',
            'page': 'Page number (default 1)',
            'per_page': 'Items per page (default 10, max 100)'
        },
        responses={
            200: ('Success', benchmarks_report_list_response),
            401: 'Authentication required',
            403: 'Access denied',
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, company_id):
        """
        Get benchmark report list with pagination.
        
        Query Parameters:
        - page: int, optional (default 1)
        - per_page: int, optional (default 10, max 100)
        
        Returns:
        - Paginated list of benchmark reports
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )
            
            # Get pagination params
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            
            # Call service
            response_data, status_code = BenchmarkService().get_benchmark_report_list(
                company_id=company_id,
                current_user=current_user,
                page=page,
                per_page=per_page
            )
            
            if status_code == 200:
                return response_data, 200  # Return the dict directly
            else:
                return error_response(
                    message=response_data.get('message', get_message('benchmark_list_retrieve_failed', locale)),
                    data=None,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Get benchmark report list error: {str(e)}")
            return internal_error_response(
                message=get_message('benchmark_list_retrieve_failed', locale),
                error_details=str(e)
            )

# -----------------------------------------------------------------------------
# Get Benchmarks Year by Company ID (without balance field)
# -----------------------------------------------------------------------------
@benchmark_ns.route('/year/company/<int:company_id>')
@benchmark_ns.param('company_id', 'Company ID')
class BalanceYearsByCompany(Resource):
    """Handle benchmarks retrieval by company ID"""
    
    @benchmark_ns.doc(
        'get_balance_years_by_company',
        params={
            'company_id': 'Company ID from URL',
            'page': 'Page number (default: 1)',
            'per_page': 'Items per page (default: 10)'
        },
        responses={
            200: ('Success', benchmarks_list_response),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, company_id):
        """
        Get all balance years for a company (without balance field).
    
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - company_id: Company ID (required in URL path)
        
        Returns:
        - List of balance years for a company without balance field
        """
        try:
            # Get current user from Auth0 token (set by @require_auth0 decorator)
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )
            
            # Correctly instantiate BenchmarkService before calling the instance method
            response_data, status_code = BenchmarkService().get_by_company_id_and_balance_year(
                company_id=company_id,  
                current_user=current_user
            )
            # Return response
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', get_message('balance_years_retrieve_failed', locale)),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Get balance sheet years by company error: {str(e)}")
            return internal_error_response(
                message=get_message('balance_years_retrieve_failed', locale),
                error_details=str(e)
            )


# create get api to get all kpi's by id_report
@benchmark_ns.route('/benchmark/report/<int:report_id>')
@benchmark_ns.param('report_id', 'Report ID to fetch benchmarks for')
class BenchmarkList(Resource):
    """Handle fetching benchmarks for a given report ID."""

    @benchmark_ns.doc(
        'get_benchmarks',
        params={'report_id': 'The ID of the report to fetch benchmarks for'},
        responses={
            200: ('Benchmarks fetched successfully', benchmarks_report_response_model),
            400: ('Validation Error', validation_error_getbenchmark_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_getBenchmark_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, report_id):
        """
        Get all benchmarks for a given report ID.

        Path Parameters:
        - report_id: int, required

        Returns:
        - 200: Benchmarks fetched successfully
        - 400: Validation error (invalid report ID)
        - 401: Authentication required
        - 403: Access denied (user cannot access this report)
        - 404: Not Found (report or benchmarks missing)
        - 500: Internal server error
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )
            if not report_id:
                return error_response(
                    message=get_message('report_id_required', locale),
                    status_code=400
                )
            # Call service to get benchmarks
            result, status_code = BenchmarkService().get_benchmarks_by_report(current_user, report_id)
            if status_code == 200:
                return success_response(
                    message=result.get('message', get_message('benchmarks_fetch_success', locale)),
                    data=result.get('data') if isinstance(result, dict) else None,
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get('message', get_message('benchmarks_fetch_failed', locale)),
                    data=result.get('data') if isinstance(result, dict) else None,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Get benchmarks error: {str(e)}")
            return internal_error_response(
                message=get_message('benchmarks_fetch_failed', locale),
                error_details=str(e)
            )
        
# delete benchmark report by id
@benchmark_ns.route('/benchmark/report/delete/<int:report_id>')
@benchmark_ns.param('report_id', 'Report ID to delete benchmark report for')
class DeleteBenchmarkReport(Resource):
    """Handle deletion of a benchmark report by ID."""

    @benchmark_ns.doc(
        'delete_benchmark_report',
        params={'report_id': 'The ID of the report to delete'},
        responses={
            200: ('Benchmark report deleted successfully', benchmark_delete_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def delete(self, report_id):
        """
        Delete a benchmark report by its ID.

        Path Parameters:
        - report_id: int, required

        Returns:
        - 200: Benchmark report deleted successfully
        - 400: Validation error (invalid report ID)
        - 401: Authentication required
        - 403: Access denied (user cannot delete this report)
        - 404: Not Found (report missing)
        - 500: Internal server error
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )

            # Call service to delete benchmark report
            response_data, status_code = BenchmarkService().delete_benchmark_report(current_user, report_id)
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data['message'],
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Delete benchmark report error: {str(e)}")
            return internal_error_response(
                message=get_message('benchmark_delete_failed', locale),
                error_details=str(e)
            )

# create update API to update benchmark report note by id_analysis
@benchmark_ns.route('/benchmark/update_note/<int:id_analysis>')
@benchmark_ns.param('id_analysis', 'Analysis ID to update benchmark report note for')
class UpdateBenchmarkReportNote(Resource):
    """Handle updating the note of a benchmark report by Analysis ID."""

    @benchmark_ns.doc(
        'update_benchmark_report_note',
        params={'id_analysis': 'The Analysis ID of the report note to update'},
        responses={
            200: ('Benchmark report note updated successfully', benchmark_update_response_model),
            400: ('Validation Error', update_validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', note_not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @benchmark_ns.expect(update_benchmark_payload_model)
    @require_auth0
    def put(self, id_analysis):
        """
        Update the note of a benchmark report by its analysis ID.

        Path Parameters:
        - id_analysis: int, required

        Body (JSON):
        - note: str, required

        Returns:
        - 200: Benchmark report note updated successfully
        - 400: Validation error (missing or invalid note)
        - 401: Authentication required
        - 403: Access denied (user cannot update this report)
        - 404: Not Found (report missing)
        - 500: Internal server error
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )
            
            payload = request.get_json() or {}
            name = payload.get("name")
            note = payload.get("note")

            if not name or note is None:
                return error_response(
                    message=get_message('name_and_note_required', locale),
                    status_code=400
                )

            # Call service to update benchmark report note
            response_data, status_code = BenchmarkService().update_benchmark_report_note(
                current_user, id_analysis, name, note
            )
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'] if 'data' in response_data else None,
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data['message'],
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Update benchmark report note error: {str(e)}")
            return internal_error_response(
                message=get_message('benchmark_note_update_failed', locale),
                error_details=str(e)
            )

# create post api to add competitor to benchmark@benchmark_ns.route('/benchmark/competitor/<int:parent_report_id>')
@benchmark_ns.param('parent_report_id', 'Parent benchmark report ID to create competitor comparison for')
@benchmark_ns.route('/benchmark/competitor/<int:parent_report_id>')
@benchmark_ns.param('parent_report_id', 'Parent benchmark report ID to create competitor comparison for')
class AddCompetitorComparison(Resource):
    """Create a new competitor comparison report based on an existing benchmark."""

    @benchmark_ns.doc(
        'add_competitor_comparison',
        params={'parent_report_id': 'The ID of the parent benchmark report'},
        responses={
            201: ('Competitor comparison report created successfully', add_competitor_comparison_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def post(self, parent_report_id):
        """
        Create a new competitor comparison report.
        
        Body (JSON):
        {
          "comparison_name": "Analisi Febbraio",
          "tipologia": "Diretto",
          "competitor_id": 13,
          "year": 2024,
          "balancesheet_name": "Definitivo 2024"
        }
        
        Returns:
        - 201: New competitor comparison report created with full KPI data
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )

            result, status_code = BenchmarkService().add_competitor_to_benchmark(
                current_user=current_user,
                parent_report_id=parent_report_id,
            )

            if status_code == 201:
                return success_response(
                    message=result.get("message", get_message('competitor_comparison_create_success', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get("message", get_message('competitor_comparison_create_failed', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Add competitor comparison error: {str(e)}")
            return internal_error_response(
                message=get_message('competitor_comparison_create_failed', locale),
                error_details=str(e)
            )

    @benchmark_ns.doc(
        'get_suggested_competitors',
        params={
            'parent_report_id': 'The ID of the parent benchmark report',
            'tipologia': 'Selection typology (Diretto, Regionale, Nazionale, Macro Area)'
        },
        responses={
            200: ('Suggested competitors retrieved successfully', suggested_competitors_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, parent_report_id):
        """
        Get suggested competitors for a benchmark report based on typology.
        
        Query Parameters:
        - tipologia: Diretto, Regionale, Nazionale, Macro Area (default: Diretto)
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )

            tipologia = request.args.get('tipologia', 'Diretto')

            result, status_code = BenchmarkService().get_suggested_competitors(
                current_user=current_user,
                parent_report_id=parent_report_id,
                tipologia=tipologia
            )

            if status_code == 200:
                return success_response(
                    message=result.get("message", get_message('competitor_companies_retrieved_success', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get("message", get_message('competitor_companies_retrieved_failed', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Get suggested competitors error: {str(e)}")
            return internal_error_response(
                message=get_message('failed_retrieve_competitors', locale),
                error_details=str(e)
            )

# create get api for get competitor reports by report id
@benchmark_ns.route('/benchmark/competitor/report/<int:report_id>')
@benchmark_ns.param('report_id', 'Report ID to get competitor reports for')
class GetCompetitorReportsByReportId(Resource):
    """Handle getting competitor reports for a given report ID."""

    @benchmark_ns.doc(
        'get_competitor_reports_by_report_id',
        params={'report_id': 'The ID of the report to get competitor reports for'},
        responses={
            200: ('Competitor reports fetched successfully', competitor_reports_response_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, report_id):
        """
        Get competitor reports for a given report ID.
        """
        try:
            current_user = get_current_user()
            locale = request.headers.get('Accept-Language', 'en')
            if not current_user:
                return error_response(
                    message=get_message('authentication_required', locale),
                    status_code=401
                )
            result, status_code = BenchmarkService().get_competitor_reports(current_user, report_id)
            if status_code == 200:
                return success_response(
                    message=result.get("message", get_message('competitor_reports_fetch_success', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get("message", get_message('competitor_reports_fetch_failed', locale)),
                    data=result.get("data"),
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Get competitor reports error: {str(e)}")
            return internal_error_response(
                message=get_message('competitor_reports_fetch_failed', locale),
                error_details=str(e)
            )