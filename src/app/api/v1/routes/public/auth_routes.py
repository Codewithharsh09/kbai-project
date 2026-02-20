"""
Authentication Routes - Auth0 Only

This module provides Auth0 authentication endpoints only:
1. Auth0 Login - Username/password via Auth0
2. Auth0 Callback - Social login callback
3. Auth0 Logout - Logout and clear session
4. Auth0 Verify Token - Verify JWT token
5. Auth0 User - Get current user profile
6. Auth0 Config - Get Auth0 configuration

Author: Flask Enterprise Template
License: MIT
"""

from flask import request, current_app
from flask_restx import Resource
from marshmallow import ValidationError
from src.common.logger import api_logger
from src.app.database.models import TbUser, UserTempData
from src.app.api.v1.services import auth0_service, user_service
from src.common.response_utils import (
    success_response,
    error_response,
    validation_error_response,
    unauthorized_response,
    internal_error_response,
)
from src.app.api.schemas.public.auth_schemas import CreateUserSchema
from src.app.api.v1.swaggers import (
    auth_ns,
    auth0_verify_model,
    create_user_model,
    update_user_model,
    change_password_model,
)
from src.extensions import db
from src.app.api.v1.services import otp_service
from src.app.api.middleware import (
    require_auth0,
    get_current_user,
    validate_user_action,
    require_permission,
)
from src.app.api.v1.routes.public.otp_routes import send_otp_in_background
from src.app.api.v1.services.public.license_service import LicenseManager
from src.common.localization import get_message


# -------------------------------------------------------------------------
# License stats for current admin
# -------------------------------------------------------------------------
@auth_ns.route("/licenses/stats")
class LicenseStats(Resource):
    @auth_ns.doc(
        "get_license_stats",
        description=(
            "Get license statistics for the currently authenticated admin user, "
            "including total, used, available and transferable licenses."
        ),
        responses={
            200: "License statistics retrieved successfully",
            401: "Unauthorized",
            403: "Forbidden - only admins can access license statistics",
            500: "Internal server error",
        },
    )
    @require_auth0
    def get(self):
        """
        Return license stats for the current admin:
        - total_licenses
        - used_by_companies
        - available

        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            current_user = get_current_user()
            # Only admins should see license stats; others get 403.
            if not current_user or current_user.role.lower() != "admin":
                return error_response(
                    message=get_message('license_stats_admin_only', locale),
                    data={"role": getattr(current_user, "role", None)},
                    status_code=403,
                )

            stats = LicenseManager.calculate_license_stats(current_user.id_user)

            # If calculation returned an error, surface it with 500.
            if "error" in stats:
                return error_response(
                    message=get_message('license_stats_failed', locale),
                    data=stats,
                    status_code=500,
                )

            return success_response(
                message=get_message('license_stats_success', locale),
                data=stats,
                status_code=200,
            )

        except Exception as e:
            current_app.logger.error(f"Get license stats error: {str(e)}")
            return internal_error_response(
                message=get_message('license_stats_error', locale),
                error_details=str(e),
            )


# -------------------------------------------------------------------------
# Logout
# -------------------------------------------------------------------------
@auth_ns.route('/auth0/logout')
class Auth0Logout(Resource):
    def post(self):
        """Logout user and clear session"""
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # In a real implementation, you would:
            # 1. Blacklist the JWT token
            # 2. Clear any server-side session data
            # 3. Log the logout event
            
            # Clear the HTTP-only cookie
            return success_response(
                message=get_message('logout_success', locale),
                data={},
                set_cookie={
                    'key': 'auth_token',
                    'value': '',
                    'httponly': True,
                    'secure': current_app.config.get('SESSION_COOKIE_SECURE', False),
                    'samesite': 'Lax',
                    'max_age': 0,  # Expire immediately
                    'path': '/'
                }
            )
            
        except Exception as e:
            current_app.logger.error(f"Logout error: {str(e)}")
            return internal_error_response(
                message=get_message('logout_failed', locale),
                error_details=str(e)
            )


# -------------------------------------------------------------------------
# Verify Auth0 Token - New endpoint for Auth0-first flow
# -------------------------------------------------------------------------
@auth_ns.route('/auth0/verify')
class Auth0Verify(Resource):
    @auth_ns.expect(auth0_verify_model)
    @auth_ns.doc('auth0_verify', responses={
        200: 'Token verified successfully',
        400: 'Validation error',
        401: 'Invalid token',
        500: 'Internal server error'
    })
    def post(self):
        """
        Verify Auth0 access_token and sync user.

        NEW ENDPOINT for Auth0-first authentication flow:
        - Validate request data (schema validation)
        - Receives access_token from frontend
        - Verifies token using JWKS (RS256)
        - Syncs user with database
        - Returns user data

        This endpoint is used by frontend to verify Auth0 tokens
        obtained via SDK or password-realm login.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get JSON data
            data = request.get_json()
            if not data:
                return error_response(
                    message=get_message('missing_data', locale),
                    data={"required_field": "access_token"},
                    status_code=400
                )

            access_token = data.get('access_token')
            is_mfa_verified = data.get('is_mfa_verified', False)

            if not access_token:
                return error_response(
                    message=get_message('missing_token', locale),
                    data={"required_field": "access_token"},
                    status_code=400
                )

            # Verify the Auth0 access token using JWKS
            try:
                claims = auth0_service.verify_auth0_token(access_token)
                current_app.logger.info(f"Token verified successfully. Subject: {claims.get('sub')}")
            except Exception as e:
                current_app.logger.error(f"Token verification failed: {str(e)}")
                return unauthorized_response(
                    message=get_message('verify_unauthorized', locale),
                    reason="invalid_token"
                )

            # Extract user information from claims
            auth0_user_id = claims.get('sub')
            email = claims.get('email')
            name = claims.get('name', '')
            picture = claims.get('picture', '')

            if not auth0_user_id or not email:
                return unauthorized_response(
                    message=get_message('missing_claims', locale),
                    reason="missing_claims"
                )

            # Get or create user from Auth0
            try:
                # Extract role from Auth0 custom namespace or app_metadata
                role = 'USER'  # Default

                # Try Auth0 custom namespace first (e.g., https://sinaptica.ai/roles)
                roles_claim = claims.get('https://sinaptica.ai/roles', [])
                if roles_claim and isinstance(roles_claim, list) and len(roles_claim) > 0:
                    role = roles_claim[0].upper()  # Get first role and normalize to uppercase
                    current_app.logger.info(f"Role extracted from custom namespace: {role}")
                # Fallback to app_metadata
                elif claims.get('app_metadata', {}).get('role'):
                    role = claims.get('app_metadata', {}).get('role', 'USER')
                    current_app.logger.info(f"Role extracted from app_metadata: {role}")
                                    # Final fallback: Fetch roles directly from Auth0 Management API
                else:
                    current_app.logger.info(
                        f'roles_claim and app_metadata empty, fetching roles from Auth0 API for user: {auth0_user_id}'
                    )
                    auth0_roles = auth0_service.get_user_roles_from_auth0(auth0_user_id)
                    if auth0_roles and len(auth0_roles) > 0:
                        role = auth0_roles[
                            0
                        ].upper()  # Get first role and normalize to uppercase
                        current_app.logger.info(f'Role extracted from Auth0 API: {role}')
                    else:
                        current_app.logger.warning(
                            f'No roles found for user {auth0_user_id} in Auth0, defaulting to USER'
                        )

                # Use Auth0 service to sync user
                user = auth0_service.get_or_create_user_from_auth0(
                    auth0_user_id=auth0_user_id,
                    email=email,
                    name=name,
                    picture=picture,
                    role=role
                )

                current_app.logger.info(f"User synced successfully: {email}")

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"User sync failed: {str(e)}")
                return internal_error_response(
                    message=get_message('sync_failed', locale),
                    error_details=str(e)
                )
            
            # Check user status before allowing access
            if user.status and user.status.upper() != 'ACTIVE':
                current_app.logger.warning(f"User login blocked due to status: {user.status} for email: {email}")
                
                # Return appropriate error message based on status
                status_key_map = {
                    'INACTIVE': 'account_inactive',
                    'SUSPENDED': 'account_suspended',
                    'BLOCKED': 'account_blocked',
                    'PENDING': 'account_pending'
                }
                
                status_upper = user.status.upper()
                if status_upper in status_key_map:
                    error_message = get_message(status_key_map[status_upper], locale)
                else:
                    error_message = get_message('account_status_error', locale, status=user.status)
                
                return error_response(
                    message=error_message,
                    data={
                        'status': user.status,
                        'email': email,
                        'reason': error_message
                    },
                    status_code=403
                )
            
            # Send OTP ONLY if MFA is enabled
            if user.mfa and not is_mfa_verified:
                current_app.logger.info(f"MFA enabled for user {email}, sending OTP")
                send_otp_in_background(
                    app=current_app._get_current_object(),
                    user_email=email,
                    user_name=name
                )
            else:
                current_app.logger.info(f"MFA disabled for user {email}, skipping OTP")
            
            # Return user data immediately (OTP will be sent in background if MFA enabled)
            return success_response(
                message=get_message('verify_success', locale),
                data={
                    "mfa": user.mfa,
                    "user": user.to_dict() if not user.mfa or is_mfa_verified else None
                }
            )

        except Exception as e:
            current_app.logger.error(f"Auth0 verify error: {str(e)}")
            return internal_error_response(
                message=get_message('verify_failed', locale),
                error_details=str(e)
            )


# -------------------------------------------------------------------------
# Verify Token - LEGACY endpoint (kept for backward compatibility)
# -------------------------------------------------------------------------
@auth_ns.route('/auth0/verify-token')
class Auth0VerifyToken(Resource):
    def get(self):
        """
        Verify current user token and return user info.

        LEGACY ENDPOINT: This verifies JWT tokens created by flask-jwt-extended.
        For new Auth0-first flow, use POST /auth0/verify instead.
        """
        try:
            # Get token from Authorization header or cookie
            token = None
            auth_header = request.headers.get('Authorization')

            if auth_header:
                try:
                    token = auth_header.split(' ')[1]
                except IndexError:
                    return unauthorized_response(
                        message='Authorization header must be in format: Bearer <token>',
                        reason='invalid_authorization_header'
                    )
            else:
                # Try to get token from cookie
                token = request.cookies.get('auth_token')
                if not token:
                    return unauthorized_response(
                        message='Please provide Authorization header or valid session cookie',
                        reason='authorization_missing'
                    )

            # Verify token and get user
            try:
                from flask_jwt_extended import decode_token
                decoded_token = decode_token(token)
                user_id = decoded_token.get('sub')
                
                if not user_id:
                    return unauthorized_response(
                        message='Token does not contain user information',
                        reason='invalid_token'
                    )
                
                # Get user from database
                user = TbUser.query.get(user_id)
                if not user:
                    return unauthorized_response(
                        message='User associated with token does not exist',
                        reason='user_not_found'
                    )
                
                return success_response(
                    message='Token is valid',
                    data={'user': user.to_dict()},
                    status_code=200
                )
                
            except Exception as e:
                current_app.logger.error(f"Token verification failed: {str(e)}")
                return unauthorized_response(
                    message='Invalid or expired token',
                    reason='token_verification_failed'
                )

        except Exception as e:
            current_app.logger.error(f"Token verification error: {str(e)}")
            return internal_error_response(
                message='Token verification failed',
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# Users Collection - GET (list) + POST (create)
# -----------------------------------------------------------------------------
@auth_ns.route('/users')
class UsersCollection(Resource):
    def options(self):
        """Handle CORS preflight request"""
        return '', 200

    @auth_ns.doc('list_users')
    @require_auth0
    @require_permission('users:list')
    def get(self):
        """
        Get list of users with simplified role-based hierarchy filtering.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Hierarchy Rules (Simplified):
        - superadmin: Sees ALL users in the system (full access)
        - staff: Sees ALL users in the system (platform manager)
        - admin: Sees ONLY users they directly created (id_admin = their id)
        - user role: Returns 403 error (not allowed)
        
        Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10, max: 100)
        - search: Search in email, name, surname
        - role: Filter by role (superadmin, admin, staff, user)
        - status: Filter by status (ACTIVE, INACTIVE, SUSPENDED)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Extract query parameters
            filters = {
                'page': request.args.get('page', 1, type=int),
                'per_page': request.args.get('per_page', 10, type=int),
                'search': request.args.get('search', '', type=str),
                'role': request.args.get('role', '', type=str),
                'status': request.args.get('status', '', type=str),
                'current_user_id': current_user.id_user  # Pass current user for hierarchy filtering
            }
            # Filter to show only ACTIVE and INACTIVE users (exclude DELETE)
            if not filters.get('status'):  # Only apply if status not provided in query params
                filters['status'] = ['ACTIVE', 'INACTIVE']  # Pass as list for IN clause
            # Call service layer for business logic
            response_data, status_code = user_service.find(**filters)

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_list_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_list_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"List users error: {str(e)}")
            return internal_error_response(
                message=get_message('user_list_failed', locale),
                error_details=str(e)
            )

    # ---------------------------------------------------------------------
    # Create a new user,staff,admin,super_admin
    # ---------------------------------------------------------------------
    @auth_ns.doc('create_user')
    @auth_ns.expect(create_user_model)
    @require_auth0
    @validate_user_action('create')
    def post(self):
        """
        Create a new user in Auth0 and save temp data.
        
        Flow:
        1. Verify Auth0 token (@require_auth0)
        2. Check role permissions (@validate_user_action)
        3. Validate input data
        4. Call service to create user
        
        Permission Matrix:
        - superadmin: Can create all roles
        - staff: Can create admin, user
        - admin: Can create admin, user
        - user: Cannot create anyone
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            print("Hello")
            # Get authenticated user
            current_user = get_current_user()
            
            # Validate input
            schema = CreateUserSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return validation_error_response(
                    validation_errors=err.messages,
                    message=get_message('input_validation_failed', locale)
                )
            
            # Call service layer
            response_data, status_code = user_service.create(
                validated_data=validated_data,
                current_user_id=current_user.id_user
            )
            
            # Return response
            if status_code == 201:
                return success_response(
                    message=get_message('user_create_success', locale),
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_create_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
            
        except Exception as e:
            current_app.logger.error(f"Create user error: {str(e)}")
            return internal_error_response(
                message=get_message('user_create_failed', locale),
                error_details=str(e)
            )

# -----------------------------------------------------------------------------
# Users Resources - delete user
# -----------------------------------------------------------------------------
@auth_ns.route('/users/<int:user_id>')
class UserResource(Resource):
    def options(self, user_id):
        """Handle CORS preflight request"""
        return '', 200

    @auth_ns.doc('soft_delete_user')
    @require_auth0
    @require_permission('users:delete')
    def delete(self, user_id):
        """
        Delete user (soft delete) with simplified role-based hierarchy validation.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Hierarchy Rules (Simplified):
        - superadmin: Can delete ALL users (except themselves)
        - staff: Can delete ALL users EXCEPT superadmin (platform manager)
        - admin: Can delete ONLY users they directly created (id_admin = their id)
        - user role: Cannot delete anyone (403 error)
        
        Examples:
        - Superadmin deletes any user ✓
        - Admin A deletes user they created ✓
        - Admin A tries to delete user created by admin B ✗ (403)
        - User tries to delete anyone ✗ (403)
        - Anyone tries to delete themselves ✗ (403 - self-deletion not allowed)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Call service layer for business logic
            response_data, status_code = user_service.delete(user_id, current_user.id_user)

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_delete_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_delete_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Delete user error: {str(e)}")
            return internal_error_response(
                message=get_message('user_delete_failed', locale),
                error_details=str(e)
            )

 
    @auth_ns.doc('get_user')
    @require_auth0
    @require_permission('users:read')
    def get(self, user_id):
        """
        Get user details by ID.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Query Parameters:
        - email_id: Optional email to search in UserTempData if user not found in TbUser
        
        Permissions:
        - superadmin, staff, admin: Can read any user
        - user: Cannot read (403)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            # Get optional email_id query parameter for UserTempData lookup
            email_id = request.args.get('email_id', None, type=str)
            # Call service layer for business logic
            response_data, status_code = user_service.findOne(
                user_id, 
                current_user.id_user,
                email_id=email_id
            )
            
            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_get_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_get_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Get user error: {str(e)}")
            return internal_error_response(
                message=get_message('user_get_failed', locale),
                error_details=str(e)
            )


    @auth_ns.doc('update_user')
    @auth_ns.expect(update_user_model)
    @require_auth0
    @require_permission('users:update')
    def put(self, user_id):
        """
        Update user information with simplified role-based hierarchy validation.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Hierarchy Rules (Simplified):
        - superadmin: Can update ALL users (full access)
        - staff: Can update ALL users EXCEPT superadmin (platform manager)
        - admin: Can update ONLY users they directly created (id_admin = their id)
        - user role: Can only update themselves
        
        Examples:
        - Superadmin updates anyone ✓
        - Admin A updates user they created ✓
        - Admin A tries to update user created by admin B ✗ (403)
        - User tries to update another user ✗ (403)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Get request data
            update_data = request.get_json()

            # Call service layer for business logic
            response_data, status_code = user_service.update(
                user_id=user_id,
                update_data=update_data,
                current_user_id=current_user.id_user
            )

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_update_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_update_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Update user error: {str(e)}")
            return internal_error_response(
                message=get_message('user_update_failed', locale),
                error_details=str(e)
            )


# ============================================================================
# Hard Delete User Route
# ============================================================================
@auth_ns.route('/users/<int:user_id>/permanent')
class HardDeleteUserResource(Resource):
    def options(self, user_id):
        """Handle CORS preflight request"""
        return '', 200

    @auth_ns.doc('hard_delete_user')
    @require_auth0
    @require_permission('users:delete')
    def delete(self, user_id):
        """
        Permanently delete user and all related data from database.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Hierarchy Rules (Simplified):
        - superadmin: Can permanently delete ALL users (except themselves)
        - staff: Can permanently delete ALL users EXCEPT superadmin (platform manager)
        - admin: Can permanently delete ONLY users they directly created (id_admin = their id)
        - user role: Cannot delete anyone (403 error)
        
        Examples:
        - Superadmin permanently deletes any user ✓
        - Admin A permanently deletes user they created ✓
        - Admin A tries to permanently delete user created by admin B ✗ (403)
        - User tries to permanently delete anyone ✗ (403)
        - Anyone tries to permanently delete themselves ✗ (403 - self-deletion not allowed)
        
        WARNING: This action is irreversible and will delete all user data!
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Call service layer for business logic
            response_data, status_code = user_service.hard_delete(user_id, current_user.id_user)

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_hard_delete_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_hard_delete_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Hard delete user error: {str(e)}")
            return internal_error_response(
                message=get_message('user_hard_delete_failed', locale),
                error_details=str(e)
            )



@auth_ns.route('/users/<int:user_id>/change-password')
class ChangeUserPassword(Resource):
    @auth_ns.doc('change_user_password')
    @auth_ns.expect(change_password_model)
    @require_auth0
    @require_permission('users:update')
    def post(self, user_id):
        """
        Change user password.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Permissions:
        - superadmin, staff, admin: Can change any user's password
        - user: Cannot change password (403)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            # Get request data
            password_data = request.get_json()
            
            # Call service layer for business logic
            response_data, status_code = user_service.change_user_password(user_id, password_data, current_user.id_user)
            
            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=get_message('user_password_change_success', locale),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=get_message('user_password_change_failed', locale),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Change password error: {str(e)}")
            return internal_error_response(
                message=get_message('user_password_change_failed', locale),
                error_details=str(e)
            )


# =============================================================================
# Temp User Resource - Update and Delete temp users by email
# =============================================================================
@auth_ns.route('/users/temp/<string:email_id>')
class TempUserResource(Resource):
    def options(self, email_id):
        """Handle CORS preflight request"""
        return '', 200

    @auth_ns.doc('update_temp_user')
    @auth_ns.expect(update_user_model)
    @require_auth0
    @require_permission('users:update')
    def put(self, email_id):
        """
        Update temp user information by email.
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Permissions:
        - superadmin, staff, admin: Can update temp users
        - user: Cannot update (403)
        
        Path Parameters:
        - email_id: Email of the temp user to update
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Get request data
            update_data = request.get_json() or {}

            # Get email from path parameter
            email = email_id
            
            # Ensure email and updated by user is in update_data for create_or_update
            update_data['email'] = email
            update_data['id_user'] = current_user.id_user
            
            # Call model method for business logic
            temp_record, error = UserTempData.create_or_update(update_data)

            # Return consistent response
            if temp_record:
                return success_response(
                    message=get_message('temp_user_update_success', locale),
                    data={'user': temp_record.to_dict()},
                    status_code=200
                )
            else:
                return error_response(
                    message=get_message('temp_user_update_failed', locale),
                    data={'error': error},
                    status_code=400
                )
        except Exception as e:
            current_app.logger.error(f"Update temp user error: {str(e)}")
            return internal_error_response(
                message=get_message('temp_user_update_failed', locale),
                error_details=str(e)
            )

    @auth_ns.doc('delete_temp_user')
    @require_auth0
    @require_permission('users:delete')
    def delete(self, email_id):
        """
        Delete temp user by email (hard delete).
        
        Authentication:
        - Auth0 token required (@require_auth0)
        - Permission check (@require_permission)
        
        Permissions:
        - superadmin, staff, admin: Can delete temp users
        - user: Cannot delete (403)
        
        Path Parameters:
        - email_id: Email of the temp user to delete
        
        WARNING: This action is irreversible!
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Get email from path parameter
            email = email_id
                
            # Find temp user by email
            temp_user = UserTempData.query.filter_by(email=email).first()
            
            if not temp_user:
                return error_response(
                    message=get_message('temp_user_not_found', locale),
                    data={'email': email},
                    status_code=404
                )
                
            # Delete the temp user
            success, error = temp_user.delete()

            # Return consistent response
            if success:
                return success_response(
                    message=get_message('temp_user_delete_success', locale),
                    data={'email': email},
                    status_code=200
                )
            else:
                return error_response(
                    message=get_message('temp_user_delete_failed', locale),
                    data={'error': error},
                    status_code=400
                )
        except Exception as e:
            current_app.logger.error(f"Delete temp user error: {str(e)}")
            return internal_error_response(
                message=get_message('temp_user_delete_failed', locale),
                error_details=str(e)
            )
