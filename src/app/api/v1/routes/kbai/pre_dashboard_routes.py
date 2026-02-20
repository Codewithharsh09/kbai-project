"""
API routes for KBAI Pre-Dashboard operations.

This module defines the REST API endpoints for managing pre-dashboard records
that track company progress through various setup steps.
"""

from flask import request, jsonify
from flask_restx import Resource, Namespace

from src.app.api.v1.services.kbai.pre_dashboard_service import kbai_pre_dashboard_service
from src.app.api.schemas.kbai.kbai_pre_dashboard_schemas import (
    update_pre_dashboard_schema,
    pre_dashboard_response_schema
)
from src.common.response_utils import (
    success_response, error_response, validation_error_response,
    internal_error_response
)
from src.common.localization import get_message

# Create namespace for pre-dashboard operations
pre_dashboard_ns = Namespace('pre-dashboard', description='KBAI Pre-Dashboard operations')


# -------------------------------------------------------------------------
# PRE DASHBOARD - FINDONE, UPDATE
# -------------------------------------------------------------------------
@pre_dashboard_ns.route('/<int:company_id>')
class PreDashboardResource(Resource):
    """Resource for individual pre-dashboard operations"""
    
    # -------------------------------------------------------------------
    # Get a company pre-dashboard record
    # -------------------------------------------------------------------
    @pre_dashboard_ns.doc('get_pre_dashboard')
    def get(self, company_id):
        """
        Get pre-dashboard record by company ID
        
        Path Parameters:
            company_id (int): Company ID
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Call service
            response_data, status_code = kbai_pre_dashboard_service.findOne(company_id)
            
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                error_data = {}
                if 'error' in response_data:
                    error_data['error'] = response_data['error']
                
                return error_response(
                    message=response_data['message'],
                    data=error_data if error_data else None,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('pre_dashboard_retrieve_failed', locale),
                error_details=str(e)
            )
    
    # -------------------------------------------------------------------
    # Update a company pre-dashboard record
    # -------------------------------------------------------------------
    @pre_dashboard_ns.doc('update_pre_dashboard')
    def put(self, company_id):
        """
        Update pre-dashboard record by company ID
        
        Path Parameters:
            company_id (int): Company ID
            
        Body Parameters:
            step_upload (bool, optional): Upload step completion status
            step_compare (bool, optional): Compare step completion status
            step_competitor (bool, optional): Competitor analysis step completion status
            step_predictive (bool, optional): Predictive analysis step completion status
            completed_flag (bool, optional): Overall completion status
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Validate request data
            data = request.get_json()
            if not data:
                return validation_error_response(get_message('request_body_required', locale))
            
            # Validate with schema
            errors = update_pre_dashboard_schema.validate(data)
            if errors:
                return validation_error_response(
                    message=get_message('input_validation_failed', locale),
                    validation_errors=errors
                )
            
            # Call service
            response_data, status_code = kbai_pre_dashboard_service.update(company_id, data)
            
            if status_code == 200:
                return success_response(
                    message=response_data['message'],
                    data=response_data['data'],
                    status_code=status_code
                )
            else:
                error_data = {}
                if 'error' in response_data:
                    error_data['error'] = response_data['error']
                
                return error_response(
                    message=response_data['message'],
                    data=error_data if error_data else None,
                    status_code=status_code
                )
                
        except Exception as e:
            return internal_error_response(
                message=get_message('pre_dashboard_update_failed', locale),
                error_details=str(e)
            )
    
