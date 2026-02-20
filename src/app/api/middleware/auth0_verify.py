"""
Auth0 Token Verification Middleware

This middleware provides Auth0 token verification:
- @require_auth0: Require valid Auth0 token (mandatory auth)
- get_current_user(): Get current authenticated user from request context

Usage Example:
    from src.app.api.middleware import require_auth0, get_current_user
    
    @auth_ns.route('/protected')
    class ProtectedResource(Resource):
        @require_auth0
        def get(self):
            current_user = get_current_user()
            return {'user': current_user.to_dict()}

Author: Flask Enterprise Template
License: MIT
"""

from functools import wraps
from flask import request, current_app, g
from src.common.response_utils import unauthorized_response, internal_error_response
from src.app.api.v1.services import auth0_service
from src.common.localization import get_message


# -----------------------------------------------------------------------
# Get Currect User
# -----------------------------------------------------------------------
def get_current_user():
    """
    Get current authenticated user from request context.
    
    Returns:
        TbUser: Current authenticated user or None
        
    Usage:
        current_user = get_current_user()
        if current_user:
            print(f"User: {current_user.email}")
    """
    return getattr(g, 'current_user', None)


# -----------------------------------------------------------------------
# Extract token from request
# -----------------------------------------------------------------------
def _extract_token_from_request():
    """
    Extract Auth0 access token from Authorization header.
    
    Returns:
        tuple: (token, error_response)
            - token (str): Extracted token or None
            - error_response (tuple): Error response tuple or None
    """
    auth_header = request.headers.get('Authorization')
    locale = request.headers.get('Accept-Language', 'en')
    
    if not auth_header:
        return None, unauthorized_response(
            message=get_message('authorization_required', locale),
            reason="missing_authorization_header"
        )
    
    # Check Bearer token format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None, unauthorized_response(
            message=get_message('invalid_auth_header', locale),
            reason="invalid_authorization_format"
        )
    
    token = parts[1]
    return token, None


# ----------------------------------------------------------------------
# Verify and get user from Auth0
# ----------------------------------------------------------------------
def _verify_and_get_user(token):
    """
    Verify Auth0 token and get user from database (NO AUTO-CREATE).
    
    Args:
        token (str): Auth0 access token
        
    Returns:
        tuple: (user, error_response)
            - user (TbUser): User object or None
            - error_response (tuple): Error response tuple or None
    """
    locale = request.headers.get('Accept-Language', 'en')
    try:
        from src.app.database.models import TbUser
        
        # Verify Auth0 token using JWKS
        claims = auth0_service.verify_auth0_token(token)
        
        if not claims:
            return None, unauthorized_response(
                message=get_message('invalid_token', locale),
                reason="invalid_token"
            )
        
        # Extract Auth0 user ID
        auth0_user_id = claims.get('sub')
        
        if not auth0_user_id:
            return None, unauthorized_response(
                message=get_message('missing_claims', locale),
                reason="missing_sub_claim"
            )
        
        # Find user in database by Auth0 ID (GET ONLY - no create)
        user = TbUser.findOne(auth0_user_id=auth0_user_id)
        
        if not user:
            current_app.logger.warning(
                f"User not found in database for Auth0 ID: {auth0_user_id}"
            )
            return None, unauthorized_response(
                message=get_message('user_not_found', locale),
                reason="user_not_found"
            )
        
        # Check if user is active
        if user.status != 'ACTIVE':
            current_app.logger.warning(
                f"Inactive user attempted login: {user.email} (Status: {user.status})"
            )
            return None, unauthorized_response(
                message=get_message('account_status_error', locale, status=user.status),
                reason="account_inactive"
            )
        
        current_app.logger.info(f"User authenticated: {user.email} (ID: {user.id_user})")
        return user, None
        
    except Exception as e:
        current_app.logger.error(f"Auth0 token verification error: {str(e)}")
        return None, internal_error_response(
            message=get_message('Authentication failed', locale),
            error_details=str(e)
        )


# ----------------------------------------------------------------------------
# Verify Auth0 token
# ----------------------------------------------------------------------------
def require_auth0(f):
    """
    Decorator to require Auth0 authentication.
    
    This decorator:
    1. Extracts token from Authorization header
    2. Verifies token using Auth0 JWKS
    3. Gets/creates user from database
    4. Sets g.current_user for request context
    5. Returns 401 if authentication fails
    
    Usage:
        @auth_ns.route('/protected')
        class ProtectedResource(Resource):
            @require_auth0
            def get(self):
                current_user = get_current_user()
                return {'message': f'Hello {current_user.email}'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from request
        token, error_response = _extract_token_from_request()
        if error_response:
            return error_response
        
        # Verify token and get user
        user, error_response = _verify_and_get_user(token)
        if error_response:
            return error_response
        
        # Set current user in request context
        g.current_user = user
        
        # Log authentication
        current_app.logger.info(f"Authenticated request: {user.email} (ID: {user.id_user})")
        
        # Call the original function
        return f(*args, **kwargs)
    
    return decorated_function

