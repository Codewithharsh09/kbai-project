"""
API Schemas Package

This package contains all Marshmallow schemas for API validation,
serialization, and Swagger documentation.

Author: Flask Enterprise Template
License: MIT
"""

# Import all schemas from organized folders
from .public.auth_schemas import *
from .public.otp_schemas import *
from .public.password_reset_schemas import *
from .kbai.kbai_companies_schemas import *
from .kbai.kbai_pre_dashboard_schemas import *
from .common.common_schemas import *

# Export all schemas
__all__ = [
    # AUTH0 SCHEMAS
    'UserResponseSchema',
    'ErrorResponseSchema',
    'SuccessResponseSchema',
    
    # USER MANAGEMENT SCHEMAS
    'CreateUserSchema',
    'UpdateUserSchema',
    'ChangePasswordSchema',
    'UsersListResponseSchema',
    
    # OTP SCHEMAS
    'CreateOtpSchema',
    'VerifyOtpSchema',
    'OtpResponseSchema',
    'OtpVerificationResponseSchema',
    
    # PASSWORD RESET SCHEMAS
    'RequestPasswordResetSchema',
    'ResetPasswordSchema',
    'PasswordResetResponseSchema',
    'PasswordResetSuccessSchema',
    'PasswordValidationSchema',
    'PASSWORD_VALIDATION_RULES',
    
    # KBAI COMPANIES SCHEMAS
    'CreateCompanySchema',
    'UpdateCompanySchema',
    'CompanyResponseSchema',
    'create_company_schema',
    'update_company_schema',
    'company_response_schema',
    
    # KBAI PRE-DASHBOARD SCHEMAS
    'UpdatePreDashboardSchema',
    'PreDashboardResponseSchema',
    'update_pre_dashboard_schema',
    'pre_dashboard_response_schema',
    
    # Common schemas
    'PaginationSchema',
    'SortSchema',
    'FilterSchema',
    'BaseResponseSchema',
    'ErrorResponseSchema',
    'SuccessResponseSchema',
    'PaginatedResponseSchema',
    'HealthCheckSchema',
    'ValidationErrorSchema',
    'BulkOperationSchema',
    'FileUploadSchema',
    'AuditLogSchema'
]