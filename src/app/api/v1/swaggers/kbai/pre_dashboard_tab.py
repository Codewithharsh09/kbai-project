"""
Swagger documentation for KBAI Pre-Dashboard API endpoints.

This module defines the Swagger models and examples for pre-dashboard operations
including create, read, update, delete, and list operations.
"""

from flask_restx import fields

# --------------------------------------------------------------------------
# Pre-Dashboard Models
# --------------------------------------------------------------------------

# Base pre-dashboard model
pre_dashboard_model = {
    'company_id': fields.Integer(
        required=True,
        description='Company ID for which pre-dashboard is being managed',
        example=1
    ),
    'step_upload': fields.Boolean(
        required=False,
        description='Upload step completion status',
        example=False,
        default=False
    ),
    'step_compare': fields.Boolean(
        required=False,
        description='Compare step completion status',
        example=False,
        default=False
    ),
    'step_competitor': fields.Boolean(
        required=False,
        description='Competitor analysis step completion status',
        example=False,
        default=False
    ),
    'step_predictive': fields.Boolean(
        required=False,
        description='Predictive analysis step completion status',
        example=False,
        default=False
    ),
    'completed_flag': fields.Boolean(
        required=False,
        description='Overall completion status (auto-calculated)',
        example=False,
        default=False
    ),
    'created_at': fields.DateTime(
        required=False,
        description='Record creation timestamp',
        example='2024-01-15T10:30:00Z'
    ),
    'updated_at': fields.DateTime(
        required=False,
        description='Record last update timestamp',
        example='2024-01-15T10:30:00Z'
    )
}


# Update pre-dashboard model
update_pre_dashboard_model = {
    'step_upload': fields.Boolean(
        required=False,
        description='Upload step completion status',
        example=True
    ),
    'step_compare': fields.Boolean(
        required=False,
        description='Compare step completion status',
        example=True
    ),
    'step_competitor': fields.Boolean(
        required=False,
        description='Competitor analysis step completion status',
        example=False
    ),
    'step_predictive': fields.Boolean(
        required=False,
        description='Predictive analysis step completion status',
        example=False
    ),
    'completed_flag': fields.Boolean(
        required=False,
        description='Overall completion status',
        example=False
    )
}

# Pre-dashboard response model
pre_dashboard_response_model = {
    'message': fields.String(
        required=True,
        description='Response message',
        example='Pre-dashboard retrieved successfully'
    ),
    'data': fields.Nested(
        pre_dashboard_model,
        required=True,
        description='Pre-dashboard data'
    ),
    'success': fields.Boolean(
        required=True,
        description='Operation success status',
        example=True
    )
}


# Error response model
pre_dashboard_error_response_model = {
    'error': fields.String(
        required=True,
        description='Error type',
        example='Not found'
    ),
    'message': fields.String(
        required=True,
        description='Error message',
        example='Pre-dashboard record not found for this company'
    )
}


# --------------------------------------------------------------------------
# Example Data
# --------------------------------------------------------------------------

# Example pre-dashboard data
EXAMPLE_PRE_DASHBOARD_CREATED = {
    'company_id': 1,
    'step_upload': False,
    'step_compare': False,
    'step_competitor': False,
    'step_predictive': False,
    'completed_flag': False,
    'created_at': '2024-01-15T10:30:00Z',
    'updated_at': '2024-01-15T10:30:00Z'
}

EXAMPLE_PRE_DASHBOARD_UPDATED = {
    'company_id': 1,
    'step_upload': True,
    'step_compare': True,
    'step_competitor': False,
    'step_predictive': False,
    'completed_flag': False,
    'created_at': '2024-01-15T10:30:00Z',
    'updated_at': '2024-01-15T11:45:00Z'
}

EXAMPLE_PRE_DASHBOARD_COMPLETED = {
    'company_id': 1,
    'step_upload': True,
    'step_compare': True,
    'step_competitor': True,
    'step_predictive': True,
    'completed_flag': True,
    'created_at': '2024-01-15T10:30:00Z',
    'updated_at': '2024-01-15T12:00:00Z'
}


# --------------------------------------------------------------------------
# Export all models
# --------------------------------------------------------------------------

__all__ = [
    'pre_dashboard_model',
    'update_pre_dashboard_model',
    'pre_dashboard_response_model',
    'pre_dashboard_error_response_model',
    'EXAMPLE_PRE_DASHBOARD_CREATED',
    'EXAMPLE_PRE_DASHBOARD_UPDATED',
    'EXAMPLE_PRE_DASHBOARD_COMPLETED'
]
