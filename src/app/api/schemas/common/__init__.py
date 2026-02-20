"""
Common Schemas Package

Contains Marshmallow schemas for shared/common entities used across the application:
- Pagination
- Error responses
- Generic response wrappers
"""

from .common_schemas import (
    PaginationSchema,
    SortSchema,
    FilterSchema,
    BaseResponseSchema,
    ErrorResponseSchema,
    SuccessResponseSchema,
    PaginatedResponseSchema,
    HealthCheckSchema,
    ValidationErrorSchema,
    BulkOperationSchema,
    FileUploadSchema,
    AuditLogSchema,
)

__all__ = [
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
    'AuditLogSchema',
]

