"""
Routes Package - Main entry point for all API routes

This package contains all route blueprints for API v1 including:
- Authentication routes
- Entity routes
- Health routes
- Other business routes

Author: Flask Enterprise Template
License: MIT
"""

from flask import Blueprint

# Create main API v1 blueprint
api_v1 = Blueprint("api_v1", __name__)

# Import all route modules to register them with Flask-RESTX namespaces
# Public schema routes
from .public import auth_routes
from .public import otp_routes
from .public import password_reset_routes

# Common routes
from .common import health_routes

# Kbai schema routes
from .kbai import companies_routes

# KBAI Balance routes
from .k_balance import balance_sheet_routes, comparison_report_routes,benchmark_routes

# Note: Routes are now registered via Flask-RESTX namespaces
# No need to register blueprints here as they're handled by the API

__all__ = ['api_v1']