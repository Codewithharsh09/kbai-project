"""
Marshmallow schemas for KBAI Pre-Dashboard validation and serialization.

This module defines the schemas used for validating and serializing
pre-dashboard data in the KBAI system.
"""

from marshmallow import Schema, fields, validate, post_load, validates_schema, ValidationError

# --------------------------------------------------------------------------
# Pre-Dashboard Schemas
# --------------------------------------------------------------------------


class UpdatePreDashboardSchema(Schema):
    """Schema for updating a pre-dashboard record"""
    
    step_upload = fields.Boolean(
        allow_none=True,
        metadata={"description": "Upload step completion status"}
    )
    step_compare = fields.Boolean(
        allow_none=True,
        metadata={"description": "Compare step completion status"}
    )
    step_competitor = fields.Boolean(
        allow_none=True,
        metadata={"description": "Competitor analysis step completion status"}
    )
    step_predictive = fields.Boolean(
        allow_none=True,
        metadata={"description": "Predictive analysis step completion status"}
    )
    completed_flag = fields.Boolean(
        allow_none=True,
        metadata={"description": "Overall completion status"}
    )

class PreDashboardResponseSchema(Schema):
    """Schema for pre-dashboard response data"""
    
    company_id = fields.Integer(metadata={"description": "Company ID"})
    step_upload = fields.Boolean(metadata={"description": "Upload step completion status"})
    step_compare = fields.Boolean(metadata={"description": "Compare step completion status"})
    step_competitor = fields.Boolean(metadata={"description": "Competitor analysis step completion status"})
    step_predictive = fields.Boolean(metadata={"description": "Predictive analysis step completion status"})
    completed_flag = fields.Boolean(metadata={"description": "Overall completion status"})
    created_at = fields.DateTime(metadata={"description": "Record creation timestamp"})
    updated_at = fields.DateTime(metadata={"description": "Record last update timestamp"})

# --------------------------------------------------------------------------
# Schema Instances
# --------------------------------------------------------------------------

# Create schema instances for use in routes
update_pre_dashboard_schema = UpdatePreDashboardSchema()
pre_dashboard_response_schema = PreDashboardResponseSchema()
