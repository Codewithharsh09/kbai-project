"""
Comparison Report Routes

Handles financial KPI comparison report generation endpoints.
"""

from flask import request, current_app
from flask_restx import Resource

from src.app.api.v1.services.k_balance.comparison_report_service import comparison_report_service
from src.app.api.middleware import require_auth0, get_current_user
from src.common.response_utils import (
    success_response, error_response, internal_error_response
)
from src.app.api.v1.swaggers.k_balance.comparison_report_tab import (
    comparison_report_ns,
    comparison_report_request_model,
    comparison_report_response_model,
    comparison_report_detail_response_model,  # Add this
    validation_error_model,
    not_found_error_model,
    internal_error_model
)

@comparison_report_ns.route('/comparison')
class ComparisonReport(Resource):
    """Handle financial comparison report generation"""
    
    @comparison_report_ns.doc(
        'generate_comparison_report',
        responses={
            201: ('Success', comparison_report_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @comparison_report_ns.expect(comparison_report_request_model)
    @require_auth0
    def post(self):
        """
        Generate comparison report between two balance sheets (years).
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        Request Body:
        {
            "id_balance_year1": 1,      // Balance sheet ID for first year (required)
            "id_balance_year2": 2,      // Balance sheet ID for second year (required)
            "analysis_name": "Optional custom name",  // Optional
            "debug_mode": false          // Optional, include debug info
        }
        
        Returns:
        - Comparison report with KPIs, analysis ID, and report ID
        - Results are saved to database tables:
          * kbai_analysis (analysis metadata)
          * kbai_reports (report metadata)
          * kbai_analysis_kpi (KPI data for both years)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Get request data
            data = request.get_json()
            
            if not data:
                return error_response(
                    message="Request body is required",
                    status_code=400
                )
            
            id_balance_year1 = data.get('id_balance_year1')
            id_balance_year2 = data.get('id_balance_year2')
            analysis_name = data.get('analysis_name')
            debug_mode = data.get('debug_mode', False)
            
            # Validate required fields
            if not id_balance_year1:
                return error_response(
                    message="id_balance_year1 is required",
                    status_code=400
                )
            
            if not id_balance_year2:
                return error_response(
                    message="id_balance_year2 is required",
                    status_code=400
                )
            
            if not isinstance(id_balance_year1, int) or id_balance_year1 <= 0:
                return error_response(
                    message="id_balance_year1 must be a positive integer",
                    status_code=400
                )
            
            if not isinstance(id_balance_year2, int) or id_balance_year2 <= 0:
                return error_response(
                    message="id_balance_year2 must be a positive integer",
                    status_code=400
                )
            
            if id_balance_year1 == id_balance_year2:
                return error_response(
                    message="Both balance sheet IDs must be different",
                    status_code=400
                )
            
            # Call service to generate comparison report
            response_data, status_code = comparison_report_service.generate_comparison_report(
                id_balance_year1=id_balance_year1,
                id_balance_year2=id_balance_year2,
                current_user=current_user,
                analysis_name=analysis_name,
                debug_mode=debug_mode
            )
            
            # Return response
            if status_code == 201:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to generate comparison report'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Comparison report generation error: {str(e)}")
            return internal_error_response(
                message="Failed to generate comparison report",
                error_details=str(e)
            )


@comparison_report_ns.route('/comparison/report/<int:company_id>')
@comparison_report_ns.param('company_id', 'Company ID')
class GetComparisonReportByCompanyId(Resource):
    """Get latest comparison report for a company with all previous comparisons"""
    
    @comparison_report_ns.doc(
        'get_comparison_report_by_company_id',
        params={'company_id': 'Company ID from URL'},
        responses={
            200: ('Success', comparison_report_detail_response_model),
            401: 'Authentication required',
            403: 'Access denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, company_id):
        """
        Get latest comparison report for a company with all previous comparisons.
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - company_id: Company ID (required in URL path)
        
        Returns:
        - Latest comparison report with full KPI data
        - All previous comparison reports (only comparison objects)
        """
        try:
            current_user = get_current_user()
            
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Call service to get report
            response_data, status_code = comparison_report_service.get_comparison_report_by_company_id(
                company_id=company_id,
                current_user=current_user
            )
            
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to retrieve comparison reports'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Get comparison report by company ID error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve comparison reports",
                error_details=str(e)
            )

