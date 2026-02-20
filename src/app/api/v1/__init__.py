"""
API v1 Package - Main entry point for API version 1

This package contains all API v1 components including:
- Routes (authentication, entities, etc.)
- Services (business logic)
- Utils (utility functions)
- Swaggers (documentation)
- Schemas (validation)

Author: Flask Enterprise Template
License: MIT
"""

from .routes import api_v1
from .swaggers import auth_ns, otp_ns, password_reset_ns, kbai_companies_ns, comparison_report_ns, company_import_ns
from .routes.kbai.pre_dashboard_routes import pre_dashboard_ns
from .routes.common.health_routes import health_ns
from .routes.k_balance.balance_sheet_routes import balance_sheet_ns
from .routes.k_balance.benchmark_routes import benchmark_ns
from .routes.kbai.predictive_routes import predictive_ns
# from .routes.common.fileupload import file_upload_ns


def register_all_namespaces(restx_api):
    """Register all RESTX namespaces with the shared Api instance."""
    # Mount /auth namespace under v1 prefix in swagger
    restx_api.add_namespace(auth_ns, path='/api/v1/auth')
    # Mount /otp namespace under v1 prefix in swagger
    restx_api.add_namespace(otp_ns, path='/api/v1/otp')
    # Mount /password-reset namespace under v1 prefix in swagger
    restx_api.add_namespace(password_reset_ns, path='/api/v1/password-reset')
    # Mount /health namespace under v1 prefix in swagger
    restx_api.add_namespace(health_ns, path='/api/v1/health')
    # Mount /kbai/companies namespace under v1 prefix in swagger
    restx_api.add_namespace(kbai_companies_ns, path='/api/v1/kbai/companies')
    # Mount /kbai/pre-dashboard namespace under v1 prefix in swagger
    restx_api.add_namespace(pre_dashboard_ns, path='/api/v1/kbai/pre-dashboard')
    # Mount /kbai-balance namespace under v1 prefix in swagger
    restx_api.add_namespace(balance_sheet_ns, path='/api/v1/kbai-balance')
    # Mount /kbai-balance/comparison namespace under v1 prefix in swagger
    restx_api.add_namespace(comparison_report_ns, path='/api/v1/kbai-balance')
    # Mount /kbai-balance/comparison namespace under v1 prefix in swagger
    restx_api.add_namespace(benchmark_ns, path='/api/v1/kbai-benchmark')
    # Mount company import namespace
    restx_api.add_namespace(company_import_ns, path='/api/v1/kbai/import')
    # Mount predictive namespace
    restx_api.add_namespace(predictive_ns, path='/api/v1/kbai/predictive')
    # Mount upload namespace under v1 prefix in swagger
    # restx_api.add_namespace(file_upload_ns)


__all__ = [
    'api_v1',
    'register_all_namespaces',
    'auth_ns',
    'health_ns',
    'kbai_companies_ns',
    'pre_dashboard_ns',
    # 'file_upload_ns'
]