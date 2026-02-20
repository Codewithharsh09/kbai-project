"""
Public Services Package

This package contains all public services:
- Auth0Service (from auth0_service.py)
- UserService (from auth_user_service.py)
- OtpService (from otp_service.py) 
- PasswordResetService (from password_reset_service.py)

Author: Flask Enterprise Template
License: MIT
"""

# Import all public services
from .auth0_service import auth0_service, Auth0Service, require_auth, require_role
from .auth_user_service import user_service, UserService
from .otp_service import otp_service, OtpService
from .password_reset_service import password_reset_service, PasswordResetService
from .tb_user_company_service import tb_user_company_service, TbUserCompanyService

__all__ = [
    'auth0_service',
    'Auth0Service', 
    'user_service',
    'UserService',
    'require_auth',
    'require_role',
    'otp_service',
    'OtpService',
    'password_reset_service',
    'PasswordResetService',
    'tb_user_company_service',
    'TbUserCompanyService',
]