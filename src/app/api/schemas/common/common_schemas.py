"""
Common API Schemas

This module contains common schemas used across the application
for validation, serialization, and Swagger documentation.

Author: Flask Enterprise Template
License: MIT
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError


class PaginationSchema(Schema):
    """Schema for pagination parameters"""
    
    page = fields.Int(
        missing=1,
        validate=validate.Range(min=1, error="Page number must be greater than 0"),
        metadata={
            "description": "Page number (starts from 1)",
            "example": 1,
            "minimum": 1
        }
    )
    
    per_page = fields.Int(
        missing=10,
        validate=validate.Range(min=1, max=100, error="Per page must be between 1 and 100"),
        metadata={
            "description": "Number of items per page",
            "example": 10,
            "minimum": 1,
            "maximum": 100
        }
    )


class SortSchema(Schema):
    """Schema for sorting parameters"""
    
    sort_by = fields.Str(
        missing='id',
        validate=validate.Length(min=1, max=50, error="Sort field must be between 1 and 50 characters"),
        metadata={
            "description": "Field to sort by",
            "example": "created_at",
            "minLength": 1,
            "maxLength": 50
        }
    )
    
    sort_order = fields.Str(
        missing='asc',
        validate=validate.OneOf(['asc', 'desc'], error="Sort order must be 'asc' or 'desc'"),
        metadata={
            "description": "Sort order",
            "example": "desc",
            "enum": ["asc", "desc"]
        }
    )


class FilterSchema(Schema):
    """Schema for filtering parameters"""
    
    search = fields.Str(
        validate=validate.Length(max=255, error="Search term must be less than 255 characters"),
        metadata={
            "description": "Search term for filtering",
            "example": "john",
            "maxLength": 255
        }
    )
    
    status = fields.Str(
        validate=validate.OneOf(['ACTIVE', 'INACTIVE', 'SUSPENDED'], error="Invalid status value"),
        metadata={
            "description": "Filter by status",
            "example": "ACTIVE",
            "enum": ["ACTIVE", "INACTIVE", "SUSPENDED"]
        }
    )
    
    role = fields.Str(
        validate=validate.OneOf(['SUPER_ADMIN', 'ADMIN', 'USER'], error="Invalid role value"),
        metadata={
            "description": "Filter by role",
            "example": "USER",
            "enum": ["SUPER_ADMIN", "ADMIN", "USER"]
        }
    )
    
    date_from = fields.DateTime(
        format='%Y-%m-%d',
        metadata={
            "description": "Filter from date (YYYY-MM-DD)",
            "example": "2023-01-01"
        }
    )
    
    date_to = fields.DateTime(
        format='%Y-%m-%d',
        metadata={
            "description": "Filter to date (YYYY-MM-DD)",
            "example": "2023-12-31"
        }
    )


class BaseResponseSchema(Schema):
    """Base schema for API responses"""
    
    success = fields.Bool(
        metadata={
            "description": "Indicates if the operation was successful",
            "example": True
        }
    )
    
    message = fields.Str(
        metadata={
            "description": "Response message",
            "example": "Operation completed successfully"
        }
    )
    
    timestamp = fields.DateTime(
        metadata={
            "description": "Response timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )


class ErrorResponseSchema(Schema):
    """Schema for error responses"""
    
    error = fields.Str(
        required=True,
        metadata={
            "description": "Error type or code",
            "example": "VALIDATION_ERROR"
        }
    )
    
    message = fields.Str(
        required=True,
        metadata={
            "description": "Error message",
            "example": "Invalid input data"
        }
    )
    
    details = fields.Dict(
        metadata={
            "description": "Additional error details",
            "example": {"field": "email", "error": "Email is required"}
        }
    )
    
    timestamp = fields.DateTime(
        metadata={
            "description": "Error timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )


class SuccessResponseSchema(Schema):
    """Schema for success responses"""
    
    success = fields.Bool(
        metadata={
            "description": "Indicates success",
            "example": True
        }
    )
    
    message = fields.Str(
        metadata={
            "description": "Success message",
            "example": "Operation completed successfully"
        }
    )
    
    data = fields.Dict(
        metadata={
            "description": "Response data",
            "example": {"id": 1, "name": "John Doe"}
        }
    )
    
    timestamp = fields.DateTime(
        metadata={
            "description": "Response timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )


class PaginatedResponseSchema(Schema):
    """Schema for paginated responses"""
    
    items = fields.List(fields.Dict())
    
    total = fields.Int(
        metadata={
            "description": "Total number of items",
            "example": 100
        }
    )
    
    page = fields.Int(
        metadata={
            "description": "Current page number",
            "example": 1
        }
    )
    
    per_page = fields.Int(
        metadata={
            "description": "Number of items per page",
            "example": 10
        }
    )
    
    pages = fields.Int(
        metadata={
            "description": "Total number of pages",
            "example": 10
        }
    )
    
    has_next = fields.Bool(
        metadata={
            "description": "Whether there is a next page",
            "example": True
        }
    )
    
    has_prev = fields.Bool(
        metadata={
            "description": "Whether there is a previous page",
            "example": False
        }
    )


class HealthCheckSchema(Schema):
    """Schema for health check responses"""
    
    status = fields.Str(
        metadata={
            "description": "Service status",
            "example": "healthy",
            "enum": ["healthy", "unhealthy", "degraded"]
        }
    )
    
    version = fields.Str(
        metadata={
            "description": "Application version",
            "example": "1.0.0"
        }
    )
    
    timestamp = fields.DateTime(
        metadata={
            "description": "Health check timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )
    
    services = fields.Dict(
        metadata={
            "description": "Status of individual services",
            "example": {
                "database": "healthy",
                "redis": "healthy",
                "auth0": "unhealthy"
            }
        }
    )


class ValidationErrorSchema(Schema):
    """Schema for validation errors"""
    
    field = fields.Str(
        metadata={
            "description": "Field that failed validation",
            "example": "email"
        }
    )
    
    message = fields.Str(
        metadata={
            "description": "Validation error message",
            "example": "Username is required"
        }
    )
    
    value = fields.Raw(
        metadata={
            "description": "Invalid value provided",
            "example": ""
        }
    )


class BulkOperationSchema(Schema):
    """Schema for bulk operations"""
    
    operation = fields.Str(
        required=True,
        validate=validate.OneOf(['create', 'update', 'delete'], error="Invalid operation"),
        metadata={
            "description": "Bulk operation type",
            "example": "update",
            "enum": ["create", "update", "delete"]
        }
    )
    
    items = fields.List(
        fields.Dict(),
        required=True,
        validate=validate.Length(min=1, max=100, error="Must provide 1-100 items"),
        metadata={
            "description": "List of items to process",
            "example": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}],
            "minItems": 1,
            "maxItems": 100
        }
    )
    
    batch_size = fields.Int(
        missing=10,
        validate=validate.Range(min=1, max=50, error="Batch size must be between 1 and 50"),
        metadata={
            "description": "Number of items to process in each batch",
            "example": 10,
            "minimum": 1,
            "maximum": 50
        }
    )


class FileUploadSchema(Schema):
    """Schema for file uploads"""
    
    filename = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255, error="Filename must be between 1 and 255 characters"),
        metadata={
            "description": "Name of the uploaded file",
            "example": "document.pdf",
            "minLength": 1,
            "maxLength": 255
        }
    )
    
    content_type = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100, error="Content type must be between 1 and 100 characters"),
        metadata={
            "description": "MIME type of the file",
            "example": "application/pdf",
            "minLength": 1,
            "maxLength": 100
        }
    )
    
    size = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=10485760, error="File size must be between 1 and 10MB"),
        metadata={
            "description": "File size in bytes",
            "example": 1024000,
            "minimum": 1,
            "maximum": 10485760
        }
    )
    
    description = fields.Str(
        validate=validate.Length(max=500, error="Description must be less than 500 characters"),
        metadata={
            "description": "Optional file description",
            "example": "User profile picture",
            "maxLength": 500
        }
    )


class AuditLogSchema(Schema):
    """Schema for audit log entries"""
    
    action = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100, error="Action must be between 1 and 100 characters"),
        metadata={
            "description": "Action performed",
            "example": "user_login",
            "minLength": 1,
            "maxLength": 100
        }
    )
    
    user_id = fields.Int(
        metadata={
            "description": "ID of the user who performed the action",
            "example": 1
        }
    )
    
    resource_type = fields.Str(
        validate=validate.Length(max=50, error="Resource type must be less than 50 characters"),
        metadata={
            "description": "Type of resource affected",
            "example": "user",
            "maxLength": 50
        }
    )
    
    resource_id = fields.Int(
        metadata={
            "description": "ID of the resource affected",
            "example": 123
        }
    )
    
    details = fields.Dict(
        metadata={
            "description": "Additional action details",
            "example": {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0..."}
        }
    )
    
    timestamp = fields.DateTime(
        metadata={
            "description": "Action timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )


# Export all schemas
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
    'AuditLogSchema'
]