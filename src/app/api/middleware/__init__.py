"""
API Middleware Package

This package contains middleware for request processing:
- auth0_verify: Auth0 token verification and authentication
- role_permission: Role-based permission system
"""

from .auth0_verify import require_auth0, get_current_user
from .role_permission import (
    validate_user_action,
    require_permission,
    filter_by_role,
    can_create_role,
    can_manage_user,
    normalize_role
)

__all__ = [
    # Auth0
    'require_auth0',
    'get_current_user',
    
    # USER CRUD
    'validate_user_action',
    'can_create_role',
    'can_manage_user',
    
    # COMPANY CRUD
    'require_permission',
    'filter_by_role',
    
    # Utility
    'normalize_role'
]

