"""
KBAI Companies Routes

Contains API endpoints for KBAI companies operations:
- POST /api/v1/kbai/companies - Create company
- GET /api/v1/kbai/companies/{id} - Find one company by ID
- PUT /api/v1/kbai/companies/{id} - Update company
- DELETE /api/v1/kbai/companies/{id} - Delete company
- GET /api/v1/kbai/companies/user/{tb_user_id} - Get companies for specific user
"""

from flask import request
from flask_restx import Resource
from marshmallow import ValidationError

from src.app.api.v1.services import kbai_companies_service
from src.app.api.schemas import create_company_schema, update_company_schema
from src.app.api.middleware import require_auth0, get_current_user
from src.app.database.models import TbUser, TbUserCompany, KbaiCompany
from src.common.response_utils import (
    success_response, error_response, validation_error_response,
    unauthorized_response, internal_error_response, not_found_response
)
from src.app.api.v1.swaggers import (
    kbai_companies_ns,
    create_company_model,
    update_company_model,
    company_response_model,
    companies_list_response_model,
    user_companies_response_model,
    companies_dropdown_response_model,
    validation_error_model,
    not_found_error_model,
    internal_error_model,
    success_message_model,
)


# -----------------------------------------------------------------------------
# Company - Create, get all
# -----------------------------------------------------------------------------
@kbai_companies_ns.route('/')
class CompaniesList(Resource):
    """Handle company listing and creation"""
    
    # -------------------------------------------------------------------------
    # Create a new company
    # -------------------------------------------------------------------------
    @kbai_companies_ns.expect(create_company_model)
    @kbai_companies_ns.marshal_with(company_response_model, code=201)
    @kbai_companies_ns.doc('create_company', responses={
        201: ('Company created successfully', company_response_model),
        400: ('Validation error', validation_error_model),
        403: ('Permission denied', validation_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def post(self):
        """
        Create a new KBAI company with role-based permissions
        
        Permissions:
        - superadmin: Can create companies
        - staff: Can create companies
        - admin: Can create companies
        - user: Cannot create companies (403)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            data = request.get_json()
            
            if not data:
                return error_response(
                    message="Request body is required",
                    status_code=400
                )
            
            # Validate data using Marshmallow schema
            try:
                validated_data = create_company_schema.load(data)
            except ValidationError as e:
                return validation_error_response(
                    message="Validation error",
                    errors=e.messages
                )
            
            # Call service to create company with validated data and current user
            result, status_code = kbai_companies_service.create(
                validated_data, 
                current_user_id=current_user.id_user
            )
            
            if status_code == 201:
                return success_response(
                    message=result['message'],
                    data=result['data'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get('message', 'Failed to create company'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )
    
    # -------------------------------------------------------------------------
    # Get all companies (superadmin/staff)
    # -------------------------------------------------------------------------
    @kbai_companies_ns.doc('list_all_companies', params={
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 15, max: 100)',
        'search': 'Search term for company name, contact person, or email',
        'status': 'Filter by status flag (ACTIVE, INACTIVE, SUSPENDED)'
    }, responses={
        200: ('Companies retrieved successfully', companies_list_response_model),
        403: ('Permission denied', validation_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def get(self):
        """
        List all KBAI companies with filtering and pagination.

        Permissions:
        - superadmin/staff: full access
        - others: must use /user/{tb_user_id}
        """
        try:
            current_user = get_current_user()

            if current_user.role.lower() not in ['superadmin', 'staff']:
                return error_response(
                    message="Permission denied. Use /user/{tb_user_id} endpoint to get your companies.",
                    status_code=403
                )

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 15, type=int)
            search = request.args.get('search', type=str)
            status = request.args.get('status', type=str)

            filters = {}
            if status:
                filters['status_flag'] = status

            result, status_code = kbai_companies_service.find(
                page=page,
                per_page=per_page,
                search=search,
                **filters
            )

            if status_code == 200:
                return success_response(
                    message=result['message'],
                    data={
                        'companies': result.get('data', []),
                        'pagination': result.get('pagination')
                    },
                    status_code=status_code
                )

            return error_response(
                message=result.get('message', 'Failed to retrieve companies'),
                data=result,
                status_code=status_code
            )

        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )


# -----------------------------------------------------------------------------
# Company - Get one, update, delete
# -----------------------------------------------------------------------------
@kbai_companies_ns.route('/<int:company_id>')
class CompanyDetail(Resource):
    """Handle individual company operations"""
    
    # -------------------------------------------------------------------------
    # Get one company
    # -------------------------------------------------------------------------
    @kbai_companies_ns.marshal_with(company_response_model, code=200)
    @kbai_companies_ns.doc('get_company', responses={
        200: ('Company retrieved successfully', company_response_model),
        404: ('Company not found', not_found_error_model),
        500: ('Internal server error', internal_error_model)
    })
    def get(self, company_id):
        """Get company by ID"""
        try:
            # Call service to find one company
            result, status_code = kbai_companies_service.findOne(company_id)
            
            if status_code == 200:
                # Return direct data without double wrapping
                return {
                    'message': result['message'],
                    'data': result['data'],
                    'success': result['success']
                }, status_code
            else:
                return error_response(
                    message=result.get('message', 'Failed to retrieve company'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )
    
    # -------------------------------------------------------------------------
    # Update one company
    # -------------------------------------------------------------------------
    @kbai_companies_ns.expect(update_company_model)
    @kbai_companies_ns.marshal_with(company_response_model, code=200)
    @kbai_companies_ns.doc('update_company', responses={
        200: ('Company updated successfully', company_response_model),
        404: ('Company not found', not_found_error_model),
        400: ('Validation error', validation_error_model),
        403: ('Permission denied', validation_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def put(self, company_id):
        """
        Update company information with role-based permissions
        
        Permissions:
        - superadmin: Can update all companies
        - staff: Can update all companies
        - parent admin: Can update companies in their hierarchy
        - child admin: Can update only companies they created
        - user: Cannot update companies (403)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            data = request.get_json()
            
            if not data:
                return error_response(
                    message="Request body is required",
                    status_code=400
                )
            
            # Validate data using Marshmallow schema
            try:
                validated_data = update_company_schema.load(data)
            except ValidationError as e:
                return validation_error_response(
                    message="Validation error",
                    errors=e.messages
                )
            
            # Call service to update company with validated data and current user
            result, status_code = kbai_companies_service.update(
                company_id, 
                validated_data,
                current_user_id=current_user.id_user
            )
            
            if status_code == 200:
                # Return direct data without double wrapping
                return {
                    'message': result['message'],
                    'data': result['data'],
                    'success': result['success']
                }, status_code
            else:
                return error_response(
                    message=result.get('message', 'Failed to update company'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )
    
    # -------------------------------------------------------------------------
    # Delete one company
    # -------------------------------------------------------------------------
    @kbai_companies_ns.doc('delete_company', responses={
        200: ('Company deleted successfully', success_message_model),
        404: ('Company not found', not_found_error_model),
        403: ('Permission denied', validation_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def delete(self, company_id):
        """
        Delete company with role-based permissions
        
        Permissions:
        - superadmin: Can delete all companies
        - staff: Can delete all companies
        - parent admin: Can delete companies in their hierarchy
        - child admin: Can delete only companies they created
        - user: Cannot delete companies (403)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            # Call service to delete company with current user
            result, status_code = kbai_companies_service.delete(
                company_id,
                current_user_id=current_user.id_user
            )
            
            if status_code == 200:
                return success_response(
                    message=result['message'],
                    data=result,
                    status_code=status_code
                )
            else:
                return error_response(
                    message=result.get('message', 'Failed to delete company'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )


# -----------------------------------------------------------------------------
# Companies by User ID - Get companies assigned to specific user
# -----------------------------------------------------------------------------
@kbai_companies_ns.route('/user/<int:tb_user_id>')
class CompaniesByUser(Resource):
    """Handle getting companies assigned to a specific user"""
    
    # @kbai_companies_ns.marshal_with(user_companies_response_model, code=200)
    @kbai_companies_ns.doc('list_user_companies', params={
        'tb_user_id': 'User ID to get companies for',
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 10, max: 100)',
        'search': 'Search term for company name, contact person, or email',
        'status': 'Filter by status flag (ACTIVE, INACTIVE, SUSPENDED)'
    }, responses={
        200: ('Companies retrieved successfully', user_companies_response_model),
        403: ('Permission denied - user can only access own companies', validation_error_model),
        404: ('User not found', not_found_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def get(self, tb_user_id):
        """
        Get companies assigned to a specific user with role-based access control
        
        Access Rules:
        - superadmin/staff: Can get companies for ANY user
        - admin: Can ONLY get their own companies (current_user_id must match tb_user_id)
        - user: Can ONLY get their own companies (current_user_id must match tb_user_id)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            current_user_role = current_user.role.lower()
            current_user_id = current_user.id_user
            
            # Permission check based on role
            if current_user_role in ['superadmin', 'staff']:
                # Superadmin and Staff can get companies for any user
                pass
            elif current_user_role in ['admin', 'user']:
                # Admin and User can ONLY get their own companies
                if current_user_id != tb_user_id:
                    return error_response(
                        message=f"Permission denied. {current_user_role.capitalize()}s can only access their own companies.",
                        data={
                            'current_user_id': current_user_id,
                            'requested_user_id': tb_user_id,
                            'reason': f'{current_user_role.capitalize()} cannot access other users\' companies'
                        },
                        status_code=403
                    )
            else:
                return error_response(
                    message="Permission denied",
                    status_code=403
                )
            
            # Verify that the target user exists
            target_user = TbUser.findOne(id_user=tb_user_id)
            if not target_user:
                return error_response(
                    message=f"User with ID {tb_user_id} not found",
                    status_code=404
                )
            
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            search = request.args.get('search', type=str)
            status = request.args.get('status', type=str)
            
            # Call service to find companies for this user
            result, status_code = kbai_companies_service.find_by_user(
                tb_user_id=tb_user_id,
                page=page,
                per_page=per_page,
                search=search,
                status=status
            )
            
            if status_code == 200:
                # Return direct data without double wrapping
                return {
                    'message': result['message'],
                    'data': result['data'],
                    'pagination': result.get('pagination'),
                    'success': result['success']
                }, status_code
            else:
                return error_response(
                    message=result.get('message', 'Failed to retrieve user companies'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )

#-------------------------------------------------------------------------------
# Get all Companies list for dropdown (simple, no pagination)
#-------------------------------------------------------------------------------
@kbai_companies_ns.route('/list/<int:tb_user_id>')
class CompaniesDropdownList(Resource):
    """Get simple companies list for dropdown (only id and name)"""
    
    # @kbai_companies_ns.marshal_with(companies_dropdown_response_model, code=200)
    @kbai_companies_ns.doc('list_companies_dropdown', params={
        'tb_user_id': 'User ID to get companies for',
    }, responses={
        200: ('Companies list retrieved successfully', companies_dropdown_response_model),
        403: ('Permission denied - user can only access own companies', validation_error_model),
        404: ('User not found', not_found_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def get(self, tb_user_id):
        """
        Get simple companies list for dropdown (no pagination, no filters)
        Returns only id_company and company_name for dropdown usage
        
        Access Rules:
        - superadmin/staff: Can get companies for ANY user (tb_user_id)
        - admin: Can ONLY get their own companies (current_user_id must match tb_user_id)
        - user: NO ACCESS to this endpoint (403 error)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            current_user_role = current_user.role.lower()
            current_user_id = current_user.id_user
            
            # Permission check based on role
            if current_user_role in ['superadmin', 'staff']:
                # Superadmin and Staff can get companies for any user
                pass
            elif current_user_role == 'admin':
                # Admin can ONLY get their own companies
                if current_user_id != tb_user_id:
                    return error_response(
                        message=f"Permission denied. Admins can only access their own companies.",
                        data={
                            'current_user_id': current_user_id,
                            'requested_user_id': tb_user_id,
                            'reason': 'Admin cannot access other admins\' companies'
                        },
                        status_code=403
                    )
            elif current_user_role == 'user':
                # User role has NO ACCESS to this endpoint
                return error_response(
                    message="Permission denied. Users cannot access company lists.",
                    data={
                        'reason': 'User role does not have permission to access company lists'
                    },
                    status_code=403
                )
            else:
                return error_response(
                    message="Permission denied",
                    status_code=403
                )
            
            # Verify that the target user exists
            target_user = TbUser.findOne(id_user=tb_user_id)
            if not target_user:
                return error_response(
                    message=f"User with ID {tb_user_id} not found",
                    status_code=404
                )
            
            # Call service to find companies for dropdown
            result, status_code = kbai_companies_service.find_companies(
                tb_user_id=tb_user_id
            )
            
            if status_code == 200:
                # Return direct data without wrapping in another data object
                return {
                    'message': result['message'],
                    'data': result['data'],
                    'success': result['success']
                }, status_code
            else:
                return error_response(
                    message=result.get('message', 'Failed to retrieve companies'),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message="Internal server error",
                error=str(e)
            )

