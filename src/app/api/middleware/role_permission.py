"""
Role-Based Permission System

Smart permission system for USER and COMPANY CRUD operations.

Roles: superadmin > staff > admin > user

Author: Flask Enterprise Template
License: MIT
"""

from functools import wraps
from typing import List, Tuple
from flask import current_app, request
from src.common.response_utils import unauthorized_response
from src.common.localization import get_message
from .auth0_verify import get_current_user


# -------------------------------------------------------------------------
# Validate role
# -------------------------------------------------------------------------
def normalize_role(role: str) -> str:
    """Normalize role to lowercase"""
    if not role:
        return 'user'
    return role.lower().strip()


# --------------------------------------------------------------------------
# Validate creator role for create user
# --------------------------------------------------------------------------
def can_create_role(creator_role: str, target_role: str) -> Tuple[bool, str]:
    """
    Check if creator can create user with target role.
    
    Business Rules:
    - superadmin: Can create anyone (superadmin, staff, admin, user)
    - staff: Can create admin and user only
    - admin: Can create admin and user
    - user: Cannot create anyone
    
    Args:
        creator_role (str): Role of user creating new user
        target_role (str): Role to be assigned to new user
        
    Returns:
        Tuple[bool, str]: (can_create, reason)
    """
    creator_normalized = normalize_role(creator_role)
    target_normalized = normalize_role(target_role)
    
    # superadmin can create anyone
    if creator_normalized == 'superadmin':
        return True, ""
    
    # staff can create admin and user
    if creator_normalized == 'staff':
        if target_normalized in ['admin', 'user']:
            return True, ""
        else:
            return False, "staff_create_only"
    
    # admin can create admin and user
    if creator_normalized == 'admin':
        if target_normalized in ['admin', 'user']:
            return True, ""
        else:
            return False, "admin_create_only"
    
    # user cannot create anyone
    if creator_normalized == 'user':
        return False, "user_cannot_create"
    
    return False, f"unknown_creator_role:{creator_role}"

# --------------------------------------------------------------------------------
# Validate role for user management
# --------------------------------------------------------------------------------
def can_manage_user(manager_role: str, target_user_role: str) -> Tuple[bool, str]:
    """
    Check if manager can update/delete user with target role.
    
    Business Rules:
    - superadmin: Can manage everyone
    - staff: Can manage admin and user only
    - admin: Can manage admin and user
    - user: Can only manage self
    
    Args:
        manager_role (str): Role of user managing
        target_user_role (str): Role of user being managed
        
    Returns:
        Tuple[bool, str]: (can_manage, reason)
    """
    manager_normalized = normalize_role(manager_role)
    target_normalized = normalize_role(target_user_role)
    
    # superadmin can manage everyone
    if manager_normalized == 'superadmin':
        return True, ""
    
    # staff can manage admin and user
    if manager_normalized == 'staff':
        if target_normalized in ['admin', 'user']:
            return True, ""
        else:
            return False, "staff_manage_only"
    
    # admin can manage admin and user
    if manager_normalized == 'admin':
        if target_normalized in ['admin', 'user']:
            return True, ""
        else:
            return False, "admin_manage_only"
    
    # user can only manage self (checked in route)
    return False, f"insufficient_permissions:{target_user_role}"


# ----------------------------------------------------------------------------------
# Check role bassed permission
# ----------------------------------------------------------------------------------
def check_permission(user_role: str, resource_action: str) -> Tuple[bool, str]:
    """
    Check permission for USER and COMPANY operations.
    
    Permissions:
    - users: superadmin, staff, admin (full CRUD)
    - company: superadmin, staff, admin (full CRUD)
    - user role: Cannot create/update/delete (company filtered by their company_id)
    """
    normalized_role = normalize_role(user_role)
    PERMISSIONS = {
        # User CRUD - superadmin, staff, admin
        'users:list': ['superadmin', 'staff', 'admin'],
        'users:create': ['superadmin', 'staff', 'admin'],
        'users:read': ['superadmin', 'staff', 'admin'],
        'users:update': ['superadmin', 'staff', 'admin'],
        'users:delete': ['superadmin', 'staff', 'admin'],
        
        # Company CRUD - superadmin, staff, admin (full access)
        'company:create': ['superadmin', 'staff', 'admin'],
        'company:read': ['superadmin', 'staff', 'admin', 'user'],
        'company:update': ['superadmin', 'staff', 'admin'],
        'company:delete': ['superadmin', 'staff', 'admin'],
        'company:list': ['superadmin', 'staff', 'admin', 'user'],  # user can list (filtered)
    }
    
    allowed_roles = PERMISSIONS.get(resource_action, [])
    
    if not allowed_roles:
        return False, f"unknown_permission:{resource_action}"
    
    if normalized_role in allowed_roles:
        return True, ""
    
    return False, f"permission_required:{', '.join(allowed_roles)}"


def require_permission(resource_action: str):
    """
    Decorator for COMPANY CRUD permission check.
    
    Usage:
        @require_auth0
        @require_permission('company:create')
        def post(self):
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            locale = request.headers.get('Accept-Language', 'en')
            current_user = get_current_user()
            
            if not current_user:
                return unauthorized_response(
                    message=get_message('authentication_required', locale),
                    reason="not_authenticated"
                ), 401
            
            # Allow a basic 'user' role to read only their own profile
            # This special-case bypasses the general permission map for self-profile access
            if resource_action == 'users:read':
                target_user_id = kwargs.get('user_id')
                if target_user_id is not None and normalize_role(current_user.role) == 'user':
                    if str(target_user_id) == str(current_user.id_user):
                        return f(*args, **kwargs)

            # Allow a basic 'user' role to update only their own profile via PUT
            # Note: intentionally limited to the PUT handler to avoid enabling password change route
            if resource_action == 'users:update' and getattr(f, '__name__', '') == 'put':
                target_user_id = kwargs.get('user_id')
                if target_user_id is not None and normalize_role(current_user.role) == 'user':
                    if str(target_user_id) == str(current_user.id_user):
                        return f(*args, **kwargs)

            has_permission, reason_key = check_permission(current_user.role, resource_action)
            
            if not has_permission:
                current_app.logger.warning(
                    f"Permission denied: {current_user.email} (role: {current_user.role}) "
                    f"for action: {resource_action}"
                )
                # Parse reason_key for dynamic values (format: key:value)
                if ':' in reason_key:
                    key, value = reason_key.split(':', 1)
                    if key == 'unknown_permission':
                        message = get_message('unknown_permission', locale, action=value)
                    elif key == 'permission_required':
                        message = get_message('permission_required', locale, roles=value)
                    else:
                        message = get_message(key, locale)
                else:
                    message = get_message(reason_key, locale)
                    
                return unauthorized_response(
                    message=message,
                    reason="permission_denied"
                ), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# -------------------------------------------------------------------------
# Smart USER CRUD Validation
# -------------------------------------------------------------------------
def validate_user_action(action_type: str):
    """
    Smart USER CRUD validator - Auto-validates role permissions.
    
    Usage:
        @require_auth0
        @validate_user_action('create')  # or 'update', 'delete'
        def post(self):
            # Validation done automatically!
            pass
    
    Validates:
    - create: Can creator create target role?
    - update/delete: Can manager manage target user?
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            locale = request.headers.get('Accept-Language', 'en')
            current_user = get_current_user()
            
            if not current_user:
                return unauthorized_response(
                    message=get_message('authentication_required', locale),
                    reason="not_authenticated"
                ), 401
            
            # Check base permission
            has_permission, reason_key = check_permission(current_user.role, f'users:{action_type}')
            if not has_permission:
                # Parse reason_key for dynamic values
                if ':' in reason_key:
                    key, value = reason_key.split(':', 1)
                    if key == 'permission_required':
                        message = get_message('permission_required', locale, roles=value)
                    else:
                        message = get_message(key, locale)
                else:
                    message = get_message(reason_key, locale)
                return unauthorized_response(
                    message=message,
                    reason="permission_denied"
                ), 403
            
            # For CREATE: Validate role creation
            if action_type == 'create':
                data = request.get_json() or {}
                target_role = data.get('role', 'user')
                
                can_create, reason_key = can_create_role(current_user.role, target_role)
                if not can_create:
                    current_app.logger.warning(
                        f"Role creation denied: {current_user.email} (role: {current_user.role}) "
                        f"attempted to create {target_role}. Reason: {reason_key}"
                    )
                    # Parse reason_key for dynamic values
                    if ':' in reason_key:
                        key, value = reason_key.split(':', 1)
                        if key == 'unknown_creator_role':
                            message = get_message('unknown_creator_role', locale, role=value)
                        else:
                            message = get_message(key, locale)
                    else:
                        message = get_message(reason_key, locale)
                    return unauthorized_response(
                        message=message,
                        reason="role_creation_denied"
                    ), 403
            
            # For UPDATE/DELETE: Validate user management
            elif action_type in ['update', 'delete']:
                # Get target user from kwargs (user_id parameter)
                target_user_id = kwargs.get('user_id')
                if target_user_id:
                    # Lazy import to avoid circular dependency
                    from src.app.database.models import TbUser
                    target_user = TbUser.query.get(target_user_id)
                    
                    if target_user:
                        # Allow users to manage themselves
                        if current_user.id_user != target_user_id:
                            can_manage, reason_key = can_manage_user(current_user.role, target_user.role)
                            if not can_manage:
                                current_app.logger.warning(
                                    f"User management denied: {current_user.email} (role: {current_user.role}) "
                                    f"attempted to {action_type} user {target_user.email} (role: {target_user.role})"
                                )
                                # Parse reason_key for dynamic values
                                if ':' in reason_key:
                                    key, value = reason_key.split(':', 1)
                                    if key == 'insufficient_permissions':
                                        message = get_message('insufficient_permissions', locale, role=value)
                                    else:
                                        message = get_message(key, locale)
                                else:
                                    message = get_message(reason_key, locale)
                                return unauthorized_response(
                                    message=message,
                                    reason="user_management_denied"
                                ), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def filter_by_role(filter_func):
    """
    Auto-filter COMPANY response by user role.
    
    Usage:
        def filter_companies(data, user):
            if user.role == 'user':
                return filter_user_company(data, user.company_id)
            return data
        
        @require_auth0
        @filter_by_role(filter_companies)
        def get(self):
            return {'companies': get_all()}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            # Call original function
            result = f(*args, **kwargs)
            
            # Apply filter if current_user exists
            if current_user and filter_func:
                # Handle tuple response (data, status_code)
                if isinstance(result, tuple):
                    data, status_code = result[0], result[1]
                    filtered_data = filter_func(data, current_user)
                    return filtered_data, status_code
                else:
                    return filter_func(result, current_user)
            
            return result
        
        return decorated_function
    return decorator

