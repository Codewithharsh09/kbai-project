"""
Balance Sheet Routes

Handles balance sheet file upload endpoints (PDF, XLSX, XBRL/XML).
"""

from flask import request, current_app
from flask_restx import Resource

from src.app.api.v1.services.k_balance.balance_sheet_service import balance_sheet_service
from src.app.api.middleware import require_auth0, get_current_user
from src.app.database.models import TbUserCompany
from src.common.response_utils import (
    success_response, error_response, internal_error_response
)
from src.app.api.v1.swaggers import (
    balance_sheet_ns,
    upload_parser,
    balance_sheet_response_model,
    balance_sheets_list_response_model,
    validation_error_model,
    extraction_error_model,
    database_error_model,
    internal_error_model,
    not_found_error_model
)


@balance_sheet_ns.route('/upload/<int:company_id>')
@balance_sheet_ns.param('company_id', 'Company ID')
class BalanceSheet(Resource):
    """Handle balance sheet file upload (PDF, XLSX, XBRL/XML)"""
    
    @balance_sheet_ns.doc(
        'balance_sheet',
        params={'company_id': 'Company ID from URL'},
        responses={
            201: ('Success', balance_sheet_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            500: ('Internal Error', internal_error_model)
        }
    )
    @balance_sheet_ns.expect(upload_parser)
    @require_auth0
    def post(self, company_id):
        """
        Upload balance sheet file, extract data, and save to database.
        
        Supported file formats:
        - PDF: Balance sheet in PDF format
        - XLSX: Balance sheet in Excel format (full or abbreviated format)
        - XBRL/XML: Balance sheet in XBRL XML format
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - company_id: Company ID (required in URL path)
        
        Request:
        - Headers: Authorization: Bearer <auth0_token>
        - multipart/form-data with:
          - file: Balance sheet file (required) - Supported: PDF, XLSX, XBRL, XML
          - year: Balance year (required) - e.g., 2024
          - month: Balance month (required) - Range: 1-12
          - type: Balance type (required) - e.g., "annual", "quarterly"
          - mode: Upload mode (required) - e.g., "manual", "automatic"
          - note: Optional notes - Additional information about the balance sheet
          - overwrite: Optional flag (true/false) - Set to true to replace an existing balance sheet for the same period
        
        Flow:
        1. Verify Auth0 token and get company_id from URL params
        2. Validate file format (PDF, XLSX, or XBRL/XML)
        3. Extract balance data from file based on format:
           - PDF: Text extraction and parsing
           - XLSX: Excel parsing (auto-detects full or abbreviated format)
           - XBRL/XML: XML parsing and data extraction
        4. Validate extracted period (year/month) matches payload values
        5. Check for existing balance sheet and handle overwrite if needed
        6. Save balance record with extracted JSON data
        7. Return response with balance sheet data
        
        Notes:
        - For XLSX files, the system automatically detects full or abbreviated format
        - Period validation compares file content with payload year/month
        - If overwrite=true, existing balance sheet for same period will be soft-deleted
        """
        try:
            # Get current user from Auth0 token (set by @require_auth0 decorator)
            current_user = get_current_user()
            
            # This check should not be needed as @require_auth0 already handles it
            # But keeping as safety check
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Validate company_id
            if not company_id or company_id <= 0:
                return error_response(
                    message="Valid company_id is required",
                    status_code=400
                )
            
            # Get file and form data
            if 'file' not in request.files:
                return error_response(
                    message="File is required",
                    status_code=400
                )
            
            file = request.files['file']
            year = request.form.get('year', type=int)
            month = request.form.get('month', type=int)
            type = request.form.get('type', type=str)
            mode = request.form.get('mode', type=str)
            note = request.form.get('note', type=str)
            overwrite_raw = request.form.get('overwrite')
            overwrite = False
            if overwrite_raw is not None:
                overwrite = str(overwrite_raw).strip().lower() in {'true', '1', 'yes', 'y'}
            
            # Validate required fields
            if not year:
                return error_response(
                    message="Year is required",
                    status_code=400
                )

            
            if not type:
                return error_response(
                    message="Type is required",
                    status_code=400
                )
            
            if not mode:
                return error_response(
                    message="Mode is required",
                    status_code=400
                )
            
            # Call service to upload balance sheet
            response_data, status_code = balance_sheet_service.balance_sheet(
                file=file,
                company_id=company_id,
                year=year,
                month=month,
                type=type,
                mode=mode,
                note=note,
                overwrite=overwrite,
                current_user=current_user
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
                    message=response_data.get('message', 'Failed to upload balance'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Balance sheet upload error: {str(e)}")
            return internal_error_response(
                message="Failed to upload balance sheet",
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# Get Balance Sheets by Company ID (without balance field)
# -----------------------------------------------------------------------------
@balance_sheet_ns.route('/company/<int:company_id>')
@balance_sheet_ns.param('company_id', 'Company ID')
class BalanceSheetsByCompany(Resource):
    """Handle balance sheets retrieval by company ID"""
    
    @balance_sheet_ns.doc(
        'get_balance_sheets_by_company',
        params={
            'company_id': 'Company ID from URL',
            'page': 'Page number (default: 1)',
            'per_page': 'Items per page (default: 10)'
        },
        responses={
            200: ('Success', balance_sheets_list_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, company_id):
        """
        Get all balance sheets for a company (without balance field).
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - company_id: Company ID (required in URL path)
        
        Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10, max: 100)
        
        Returns:
        - List of balance sheets without balance field
        - Pagination information
        """
        try:
            # Get current user from Auth0 token (set by @require_auth0 decorator)
            current_user = get_current_user()
            
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # Validate pagination
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 10
            
            # Call service to get balance sheets
            response_data, status_code = balance_sheet_service.get_by_company_id(
                company_id=company_id,
                page=page,
                per_page=per_page,
                current_user=current_user
            )
            
            # Return response
            if status_code == 200:
                # Include pagination in data dict
                response_data_with_pagination = {
                    'balance_sheets': response_data['data'],
                    'pagination': response_data.get('pagination')
                }
                return success_response(
                    message=response_data['message'],
                    data=response_data_with_pagination,
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to retrieve balance sheets'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Get balance sheets by company error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve balance sheets",
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# Get Balance Sheet by ID (with complete data including balance field)
# -----------------------------------------------------------------------------
@balance_sheet_ns.route('/<int:id_balance>')
@balance_sheet_ns.param('id_balance', 'Balance Sheet ID')
class BalanceSheetDetail(Resource):
    """Handle individual balance sheet retrieval by ID"""
    
    @balance_sheet_ns.doc(
        'get_balance_sheet_by_id',
        params={'id_balance': 'Balance Sheet ID from URL'},
        responses={
            200: ('Success', balance_sheet_response_model),
            404: ('Not Found', not_found_error_model),
            401: 'Authentication required',
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def get(self, id_balance):
        """
        Get balance sheet by ID (with complete data including balance field).
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - id_balance: Balance Sheet ID (required in URL path)
        
        Returns:
        - Complete balance sheet data including balance field (JSONB)
        """
        try:
            # Get current user from Auth0 token (set by @require_auth0 decorator)
            current_user = get_current_user()
            
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Call service to get balance sheet
            response_data, status_code = balance_sheet_service.get_by_id(
                id_balance=id_balance,
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
                    message=response_data.get('message', 'Failed to retrieve balance sheet'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Get balance sheet by ID error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve balance sheet",
                error_details=str(e)
            )
    
    @balance_sheet_ns.doc(
        'delete_balance_sheet_by_id',
        params={'id_balance': 'Balance Sheet ID from URL'},
        responses={
            200: ('Success', balance_sheet_response_model),
            400: ('Validation Error', validation_error_model),
            401: 'Authentication required',
            403: 'Permission denied',
            404: ('Not Found', not_found_error_model),
            500: ('Internal Error', internal_error_model)
        }
    )
    @require_auth0
    def delete(self, id_balance):
        """
        Delete (soft delete) a balance sheet by ID.
        
        Authentication:
        - Auth0 token required in Authorization header: "Bearer <token>"
        
        URL Parameters:
        - id_balance: Balance Sheet ID (required in URL path)
        
        Returns:
        - Success message confirming deletion
        """
        try:
            # Get current user from Auth0 token (set by @require_auth0 decorator)
            current_user = get_current_user()
            
            if not current_user:
                return error_response(
                    message="Authentication required",
                    status_code=401
                )
            
            # Validate id_balance
            if not id_balance or id_balance <= 0:
                return error_response(
                    message="Valid id_balance is required",
                    status_code=400
                )
            
            # Call service to delete balance sheet (no company_id needed - will be checked from balance)
            response_data, status_code = balance_sheet_service.delete(
                id_balance=id_balance,
                current_user=current_user
            )
            
            # Return response
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data.get('data'),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to delete balance sheet'),
                    data=response_data,
                    status_code=status_code
                )
                
        except Exception as e:
            current_app.logger.error(f"Balance sheet delete error: {str(e)}")
            return internal_error_response(
                message="Failed to delete balance sheet",
                error_details=str(e)
            )

