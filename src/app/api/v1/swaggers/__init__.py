"""
Swagger Documentation Package - Tab-based Organization

This package contains Swagger documentation organized by tabs:
1. Auth Tab - Authentication operations (login, register, user management)
2. OTP Tab - One-time password operations (2FA)
3. Password Reset Tab - Password reset operations
4. Health Tab - Health check operations

Author: Flask Enterprise Template
License: MIT
"""

# Import from individual tab files
from .public.auth_tab import (
    auth_ns,
    auth0_verify_model,  # NEW: for /auth0/verify endpoint
    user_response_model,
    auth0_logout_response_model,
    auth0_verify_token_response_model,
    success_response_model,
    error_response_model,
    create_user_model,
    update_user_model,
    change_password_model,
    users_list_response_model,
    EXAMPLE_AUTH0_LOGIN,
    EXAMPLE_USER_CREATED,
    EXAMPLE_USERS_LIST,
    EXAMPLE_CHANGE_PASSWORD,
    EXAMPLE_VALIDATION_ERROR,
    EXAMPLE_AUTH_ERROR
)

from .public.otp_tab import (
    otp_ns,
    create_otp_model,
    verify_otp_model,
    otp_response_model,
    otp_verification_response_model,
    EXAMPLE_OTP_RESPONSE,
    EXAMPLE_OTP_VERIFICATION_RESPONSE
)

from .public.password_reset_tab import (
    password_reset_ns,
    request_password_reset_model,
    reset_password_model,
    password_reset_response_model,
    password_reset_success_model,
    PASSWORD_RULES,
    EMAIL_RULES,
    TOKEN_RULES,
    EXAMPLE_PASSWORD_RESET_REQUEST,
    EXAMPLE_PASSWORD_RESET_SUCCESS
)


from .common.health_tab import (
    health_ns,
    basic_health_response_model,
    detailed_health_response_model,
    health_summary_response_model,
    EXAMPLE_BASIC_HEALTH,
    EXAMPLE_DETAILED_HEALTH,
    EXAMPLE_HEALTH_SUMMARY
)

from .kbai.companies_tab import (
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
    EXAMPLE_COMPANY_CREATED,
    EXAMPLE_COMPANY_RETRIEVED,
    EXAMPLE_COMPANIES_LIST,
    EXAMPLE_COMPANY_UPDATED,
    EXAMPLE_COMPANY_DELETED,
    EXAMPLE_VALIDATION_ERROR
)

from .kbai.pre_dashboard_tab import (
    pre_dashboard_model,
    update_pre_dashboard_model,
    pre_dashboard_response_model,
    pre_dashboard_error_response_model,
    EXAMPLE_PRE_DASHBOARD_CREATED,
    EXAMPLE_PRE_DASHBOARD_UPDATED,
    EXAMPLE_PRE_DASHBOARD_COMPLETED
)

from .kbai.company_import_tab import (
    company_import_ns,
    import_company_request_model,
    import_company_response_model
)

from .k_balance.balance_sheet_tab import (
    balance_sheet_ns,
    upload_parser,
    balance_sheet_model,
    balance_sheet_list_item_model,
    balance_sheet_response_model,
    balance_sheets_list_response_model,
    validation_error_model,
    extraction_error_model,
    database_error_model,
    internal_error_model,
    not_found_error_model,
    EXAMPLE_BALANCE_SHEET_UPLOADED,
    EXAMPLE_VALIDATION_ERROR,
    EXAMPLE_EXTRACTION_ERROR,
    EXAMPLE_DATABASE_ERROR
)

from .k_balance.comparison_report_tab import (
    comparison_report_ns,
    comparison_report_request_model,
    comparison_report_response_model
)

from .k_balance.benchmark_tab import (
    benchmark_ns,
    create_benchmark_payload_model,
    benchmark_create_response_model,
    add_competitor_comparison_response_model,
    benchmarks_list_response_model,
    competitor_reports_response_model,
    validation_error_model,
    internal_error_model,
    benchmark_list_item_model,
    not_found_error_model,
    benchmarks_list_response,
    benchmarks_report_list_response,
    benchmarks_report_response_model,
    benchmark_delete_response_model,
    benchmark_update_response_model,
    update_benchmark_payload_model,
    update_validation_error_model,
    note_not_found_error_model,
    validation_error_getbenchmark_model,
    not_found_error_getBenchmark_model,
    suggested_competitors_response_model
)
__all__ = [
    # Namespaces
    'auth_ns',
    'otp_ns', 
    'password_reset_ns',
    'health_ns',
    'kbai_companies_ns',
    'balance_sheet_ns',
    'comparison_report_ns',
    
    # Auth Models
    'auth0_verify_model',  # NEW: for /auth0/verify endpoint
    'user_response_model',
    'auth0_logout_response_model',
    'auth0_verify_token_response_model',
    'success_response_model',
    'error_response_model',
    'create_user_model',
    'update_user_model',
    'change_password_model',
    'users_list_response_model',
    
    # OTP Models
    'create_otp_model',
    'verify_otp_model',
    'otp_response_model',
    'otp_verification_response_model',
    
    # Password Reset Models
    'request_password_reset_model',
    'reset_password_model',
    'password_reset_response_model',
    'password_reset_success_model',
    
    
    # Health Models
    'basic_health_response_model',
    'detailed_health_response_model',
    'health_summary_response_model',
    
    # KBAI Companies Models
    'create_company_model',
    'update_company_model',
    'company_response_model',
    'companies_list_response_model',
    'validation_error_model',
    'not_found_error_model',
    'internal_error_model',
    'success_message_model',
    
    # KBAI Pre-Dashboard Models
    'pre_dashboard_model',
    'update_pre_dashboard_model',
    'pre_dashboard_response_model',
    'pre_dashboard_error_response_model',
    
    # KBAI Balance Sheet Models
    'upload_parser',
    'balance_sheet_model',
    'balance_sheet_list_item_model',
    'balance_sheet_response_model',
    'balance_sheets_list_response_model',
    'validation_error_model',
    'extraction_error_model',
    'database_error_model',
    'internal_error_model',
    'not_found_error_model',
    
    # Comparison Report Models
    'comparison_report_request_model',
    'comparison_report_response_model',
    # Benchmark Models
    'create_benchmark_payload_model',
    'benchmark_create_response_model',
    'add_competitor_comparison_response_model',
    'benchmarks_report_response_model',
    'competitor_reports_response_model',
    'benchmark_list_item_model',
    'benchmarks_list_response',
    'benchmark_delete_response_model',
    'update_benchmark_payload_model',
    'update_validation_error_model',
    'note_not_found_error_model',
    'validation_error_getbenchmark_model',
    'not_found_error_getBenchmark_model',
    'suggested_competitors_response_model',
    
    # Company Import
    'company_import_ns',
    'import_company_request_model',
    'import_company_response_model',
    
    # Validation Rules
    'PASSWORD_RULES',
    'EMAIL_RULES',
    'TOKEN_RULES',
    
    # Example Responses
    'EXAMPLE_AUTH0_LOGIN',
    'EXAMPLE_USER_CREATED',
    'EXAMPLE_USERS_LIST',
    'EXAMPLE_CHANGE_PASSWORD',
    'EXAMPLE_VALIDATION_ERROR',
    'EXAMPLE_AUTH_ERROR',
    'EXAMPLE_OTP_RESPONSE',
    'EXAMPLE_OTP_VERIFICATION_RESPONSE',
    'EXAMPLE_PASSWORD_RESET_REQUEST',
    'EXAMPLE_PASSWORD_RESET_SUCCESS',
    'EXAMPLE_BASIC_HEALTH',
    'EXAMPLE_DETAILED_HEALTH',
    'EXAMPLE_HEALTH_SUMMARY',
    'EXAMPLE_COMPANY_CREATED',
    'EXAMPLE_COMPANY_RETRIEVED',
    'EXAMPLE_COMPANIES_LIST',
    'EXAMPLE_COMPANY_UPDATED',
    'EXAMPLE_COMPANY_DELETED',
    'EXAMPLE_PRE_DASHBOARD_CREATED',
    'EXAMPLE_PRE_DASHBOARD_UPDATED',
    'EXAMPLE_PRE_DASHBOARD_COMPLETED',
    'EXAMPLE_BALANCE_SHEET_UPLOADED',
    'EXAMPLE_VALIDATION_ERROR',
    'EXAMPLE_EXTRACTION_ERROR',
    'EXAMPLE_DATABASE_ERROR'
]