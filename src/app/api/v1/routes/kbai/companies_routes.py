"""
KBAI Companies Routes

Contains API endpoints for KBAI companies operations:
- POST /api/v1/kbai/companies - Create company
- GET /api/v1/kbai/companies/{id} - Find one company by ID
- PUT /api/v1/kbai/companies/{id} - Update company
- DELETE /api/v1/kbai/companies/{id} - Delete company
- GET /api/v1/kbai/companies/user/{tb_user_id} - Get companies for specific user
"""

from flask import request, make_response, jsonify
from flask_restx import Resource, marshal
from marshmallow import ValidationError
from flask import request
from flask_restx import Resource

from src.app.api.v1.services import kbai_companies_service
from src.app.api.schemas import create_company_schema, update_company_schema
from src.app.api.middleware import require_auth0, get_current_user
from src.app.database.models import TbUser, TbUserCompany, KbaiCompany
from src.common.response_utils import (
    success_response, error_response, validation_error_response,
    unauthorized_response, internal_error_response, not_found_response
)
from src.common.localization import get_message
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
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            data = request.get_json()
            
            if not data:
                resp, code = error_response(
                    message=get_message('request_body_required', locale),
                    status_code=400
                )
                return make_response(jsonify(resp), code)
            
            # Validate data using Marshmallow schema
            try:
                validated_data = create_company_schema.load(data)
            except ValidationError as e:
                resp, code = validation_error_response(
                    message=get_message('validation_error', locale),
                    validation_errors=e.messages
                )
                return make_response(jsonify(resp), code)

            vat_value = validated_data.get('vat')
            if vat_value:
                vat = KbaiCompany.query.filter_by(vat=vat_value,is_deleted=False).first()
                if vat:
                    resp, code = error_response(
                        message=get_message('company_already_exists', locale),
                        status_code=400
                    )
                    return make_response(jsonify(resp), code)

            # Call service to create company with validated data and current user
            result, status_code = kbai_companies_service.create(
                validated_data, 
                current_user_id=current_user.id_user
            )
            
            if status_code == 201:
                # result already contains message and data from service.create
                response_data = {
                    "success": True,
                    "message": result.get('message'),
                    "data": result.get('data')
                }
                # Manually marshal only the dictionary data
                return marshal(response_data, company_response_model), 201
            else:
                if isinstance(result, dict) and 'success' in result and 'message' in result:
                    return make_response(jsonify(result), status_code)
                    
                resp, code = error_response(
                    message=get_message('company_create_failed', locale),
                    data=result,
                    status_code=status_code
                )
                return make_response(jsonify(resp), code)
                
        except Exception as e:
            resp, code = internal_error_response(
                message=get_message('internal_server_error', locale),
                error_details=str(e)
            )
            return make_response(jsonify(resp), code)
    
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
        locale = request.headers.get('Accept-Language', 'en')
        try:
            current_user = get_current_user()

            if current_user.role.lower() not in ['superadmin', 'staff']:
                return error_response(
                    message=get_message('permission_denied_use_user_endpoint', locale),
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
                message=get_message('companies_retrieve_failed', locale),
                data=result,
                status_code=status_code
            )

        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
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
    @kbai_companies_ns.doc('get_company', responses={
        200: ('Company retrieved successfully', company_response_model),
        404: ('Company not found', not_found_error_model),
        500: ('Internal server error', internal_error_model)
    })
    def get(self, company_id):
        """Get company by ID"""
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Call service to find one company
            result, status_code = kbai_companies_service.findOne(company_id)
            
            if status_code == 200:
                # Manually marshal the response to maintain the API contract
                response_data = {
                    'message': result['message'],
                    'data': result['data'],
                    'success': result['success']
                }
                return marshal(response_data, company_response_model), 200
            else:
                return error_response(
                    message=get_message('company_retrieve_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
                error_details=str(e)
            )
    
    # -------------------------------------------------------------------------
    # Update one company
    # -------------------------------------------------------------------------
    @kbai_companies_ns.expect(update_company_model)
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
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            data = request.get_json()
            
            if not data:
                return error_response(
                    message=get_message('request_body_required', locale),
                    status_code=400
                )
            
            # Validate data using Marshmallow schema
            try:
                validated_data = update_company_schema.load(data)
            except ValidationError as e:
                return validation_error_response(
                    message=get_message('validation_error', locale),
                    validation_errors=e.messages
                )
            
            # Call service to update company with validated data and current user
            result, status_code = kbai_companies_service.update(
                company_id, 
                validated_data,
                current_user_id=current_user.id_user
            )
            
            if status_code == 200:
                # Manually marshal the response to maintain the API contract
                response_data = {
                    'message': result['message'],
                    'data': result['data'],
                    'success': result['success']
                }
                return marshal(response_data, company_response_model), 200
            else:
                if isinstance(result, dict) and 'success' in result and 'message' in result:
                    return make_response(jsonify(result), status_code)
                    
                return error_response(
                    message=get_message('company_update_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
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
        locale = request.headers.get('Accept-Language', 'en')
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
                    message=get_message('company_delete_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
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
        locale = request.headers.get('Accept-Language', 'en')
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
                        message=get_message('permission_denied_own_companies', locale, role=current_user_role.capitalize()),
                        data={
                            'current_user_id': current_user_id,
                            'requested_user_id': tb_user_id,
                            'reason': get_message('cannot_access_others_companies', locale, role=current_user_role.capitalize())
                        },
                        status_code=403
                    )
            else:
                return error_response(
                    message=get_message('permission_denied', locale),
                    status_code=403
                )
            
            # Verify that the target user exists
            target_user = TbUser.findOne(id_user=tb_user_id)
            if not target_user:
                return error_response(
                    message=get_message('user_not_found_id', locale, id=tb_user_id),
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
                    message=get_message('user_companies_retrieve_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
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
        locale = request.headers.get('Accept-Language', 'en')
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
                        message=get_message('admin_own_companies_only', locale),
                        data={
                            'current_user_id': current_user_id,
                            'requested_user_id': tb_user_id,
                            'reason': get_message('admin_cannot_access_others', locale)
                        },
                        status_code=403
                    )
            elif current_user_role == 'user':
                # User role has NO ACCESS to this endpoint
                return error_response(
                    message=get_message('user_no_access_company_lists', locale),
                    data={
                        'reason': get_message('user_role_no_permission', locale)
                    },
                    status_code=403
                )
            else:
                return error_response(
                    message=get_message('permission_denied', locale),
                    status_code=403
                )
            
            # Verify that the target user exists
            target_user = TbUser.findOne(id_user=tb_user_id)
            if not target_user:
                return error_response(
                    message=get_message('user_not_found_id', locale, id=tb_user_id),
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
                    message=get_message('companies_retrieve_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
                error=str(e)
            )

# -----------------------------------------------------------------------------
# Companies by User ID - Get companies assigned to specific user
# -----------------------------------------------------------------------------
@kbai_companies_ns.route('/company/competitor/<int:id_company>')
class CompetitorCompanies(Resource):
    """Handle getting competitor companies for a specific parent company"""
    
    # @kbai_companies_ns.marshal_with(user_companies_response_model, code=200)
    @kbai_companies_ns.doc('list_competitor_companies', params={
        'id_company': 'Parent company ID to get companies for',
        'search': 'Search term for company name, contact person, or email',
        'status': 'Filter by status flag (ACTIVE, INACTIVE, SUSPENDED)'
    }, responses={
        200: ('Competitor companies retrieved successfully', user_companies_response_model),
        403: ('Permission denied - parent company can only access own competitor companies', validation_error_model),
        404: ('Parent company not found', not_found_error_model),
        500: ('Internal server error', internal_error_model)
    })
    @require_auth0
    def get(self,id_company: int): # current_user is the current user object
        """
        Get competitor companies with role-based access control
        
        Access Rules:
        - superadmin/staff: Can get companies for ANY user
        - admin: Can ONLY get their own companies (current_user_id must match tb_user_id)
        - user: Can ONLY get their own companies (current_user_id must match tb_user_id)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            if not current_user:
                return error_response(
                    message=get_message('user_not_found', locale),
                    status_code=404
                )
            # Get query parameters
            search = request.args.get('search', type=str)
            status = request.args.get('status', type=str)
            
            # Call service to find companies for this user
            result, status_code = kbai_companies_service.find_competitor_companies(
                id_company=id_company,
                search=search,
                status=status
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
                    message=get_message('user_companies_retrieve_failed', locale),
                    data=result,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('internal_server_error', locale),
                error=str(e)
            )
