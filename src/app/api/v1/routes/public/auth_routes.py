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
from src.app.database.models import TbUser
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
        - can_transfer
        """
        try:
            current_user = get_current_user()
            
            # Only admins should see license stats; others get 403.
            if not current_user or current_user.role.lower() != "admin":
                return error_response(
                    message="Only admin users can access license statistics",
                    data={"role": getattr(current_user, "role", None)},
                    status_code=403,
                )

            stats = LicenseManager.calculate_license_stats(current_user.id_user)

            # If calculation returned an error, surface it with 500.
            if "error" in stats:
                return error_response(
                    message="Failed to calculate license statistics",
                    data=stats,
                    status_code=500,
                )

            return success_response(
                message="License statistics retrieved successfully",
                data=stats,
                status_code=200,
            )

        except Exception as e:
            current_app.logger.error(f"Get license stats error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve license statistics",
                error_details=str(e),
            )


# -------------------------------------------------------------------------
# Logout
# -------------------------------------------------------------------------
@auth_ns.route('/auth0/logout')
class Auth0Logout(Resource):
    def post(self):
        """Logout user and clear session"""
        try:
            # In a real implementation, you would:
            # 1. Blacklist the JWT token
            # 2. Clear any server-side session data
            # 3. Log the logout event
            
            # Clear the HTTP-only cookie
            return success_response(
                message="Logout successful",
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
                message="Logout failed",
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
        try:
            # Get JSON data
            data = request.get_json()
            if not data:
                return error_response(
                    message="Request data is required",
                    data={"required_field": "access_token"},
                    status_code=400
                )

            access_token = data.get('access_token')

            if not access_token:
                return error_response(
                    message="Please provide the access token to continue.",
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
                    message="We could not verify your login. Please make sure you are logged in with a valid account and try again.",
                    reason="invalid_token"
                )

            # Extract user information from claims
            auth0_user_id = claims.get('sub')
            email = claims.get('email')
            name = claims.get('name', '')
            picture = claims.get('picture', '')

            if not auth0_user_id or not email:
                return unauthorized_response(
                    message="Token does not contain required user information",
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
                    message="User synchronization failed",
                    error_details=str(e)
                )
            
            # Check user status before allowing access
            if user.status and user.status.upper() != 'ACTIVE':
                current_app.logger.warning(f"User login blocked due to status: {user.status} for email: {email}")
                
                # Return appropriate error message based on status
                status_messages = {
                    'INACTIVE': 'Your account is inactive. Please contact support to activate your account.',
                    'SUSPENDED': 'Your account has been suspended. Please contact support for assistance.',
                    'BLOCKED': 'Your account has been blocked. Please contact support.',
                    'PENDING': 'Your account is pending approval. Please wait for admin approval.'
                }
                
                error_message = status_messages.get(
                    user.status.upper(), 
                    f'Your account status is {user.status}. Please contact support.'
                )
                
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
            if user.mfa:
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
                message="Token verified successfully",
                data={
                    "mfa": user.mfa,
                    "user": user.to_dict() if not user.mfa else None
                }
            )

        except Exception as e:
            current_app.logger.error(f"Auth0 verify error: {str(e)}")
            return internal_error_response(
                message="Token verification failed",
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
                    message=response_data.get('message', 'Users retrieved successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to retrieve users'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"List users error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve users",
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
        try:
            # Get authenticated user
            current_user = get_current_user()
            
            # Validate input
            schema = CreateUserSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return validation_error_response(
                    validation_errors=err.messages,
                    message="Input validation failed"
                )
            
            # Call service layer
            response_data, status_code = user_service.create(
                validated_data=validated_data,
                current_user_id=current_user.id_user
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
                    message=response_data.get('message', 'Failed to create user'),
                    data=response_data,
                    status_code=status_code
                )
            
        except Exception as e:
            current_app.logger.error(f"Create user error: {str(e)}")
            return internal_error_response(
                message="Failed to create user",
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
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Call service layer for business logic
            response_data, status_code = user_service.delete(user_id, current_user.id_user)

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=response_data.get('message', 'User deleted successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to delete user'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Delete user error: {str(e)}")
            return internal_error_response(
                message="Failed to delete user",
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
        
        Permissions:
        - superadmin, staff, admin: Can read any user
        - user: Cannot read (403)
        """
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()
            
            # Call service layer for business logic
            response_data, status_code = user_service.findOne(user_id, current_user.id_user)
            
            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=response_data.get('message', 'User retrieved successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to retrieve user'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Get user error: {str(e)}")
            return internal_error_response(
                message="Failed to retrieve user",
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
                    message=response_data.get('message', 'User updated successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to update user'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Update user error: {str(e)}")
            return internal_error_response(
                message="Failed to update user",
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
        try:
            # Get current user from Auth0 token
            current_user = get_current_user()

            # Call service layer for business logic
            response_data, status_code = user_service.hard_delete(user_id, current_user.id_user)

            # Return consistent response
            if status_code == 200:
                return success_response(
                    message=response_data.get('message', 'User permanently deleted successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to permanently delete user'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Hard delete user error: {str(e)}")
            return internal_error_response(
                message="Failed to permanently delete user",
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
                    message=response_data.get('message', 'Password changed successfully'),
                    data=response_data.get('data', {}),
                    status_code=status_code
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Failed to change password'),
                    data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Change password error: {str(e)}")
            return internal_error_response(
                message="Failed to change password",
                error_details=str(e)
            )
    
    