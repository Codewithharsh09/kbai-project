"""
API package for Flask Enterprise Template

This package contains API-related modules including:
- v1 API implementation with namespaces, routes, and services
- Flask-RESTX namespaces for Swagger documentation
- Route handlers with authentication and validation
- Service layer for business logic
- API utilities for responses and validation

Author: Flask Enterprise Template
License: MIT
"""

from .v1 import api_v1, register_all_namespaces

__all__ = ['api_v1', 'register_all_namespaces']
