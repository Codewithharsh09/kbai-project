"""
API V1 Services Package

This package contains all business logic services for API v1 including:
- Public Schema Services (auth0, otp, password_reset, role, users)
- Common Services (cache, email, health, performance)
- Kbai Schema Services (future)

Author: Flask Enterprise Template
License: MIT
"""

# Public schema services - Import everything from public package
from .public import *
from .public.auth_user_service import user_service, UserService

# Common services
from .common.health_service import HealthService
from .common.email import EmailService
from .common.performance_service import PerformanceService

# Kbai schema services
from .kbai.companies_service import kbai_companies_service
from .kbai.pre_dashboard_service import kbai_pre_dashboard_service

# KBAI Balance services
from .k_balance.balance_sheet_service import balance_sheet_service

__all__ = [
    # Public schema services (from public package)
    'Auth0Service',
    'auth0_service',
    'require_auth',
    'require_role',
    'OtpService',
    'otp_service',
    'PasswordResetService',
    'password_reset_service',
    'HealthService',
    
    # Additional public services
    'UserService',
    'user_service',
    'role_service',
    'Role',
    'Permission',
    
    # Common services
    'cache_user_list',
    'cache_user_details',
    'EmailService',
    'PerformanceService',
    
    # Kbai schema services
    'kbai_companies_service',
    'kbai_pre_dashboard_service',
    
    # KBAI Balance services
    'balance_sheet_service'
]
