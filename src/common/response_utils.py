"""
Standardized API Response Utilities

This module provides utility functions for creating consistent API responses
across all endpoints in the format:
{
    "success": true/false,
    "message": "Related message",
    "data": { ... }
}
"""

from flask import jsonify, make_response
from typing import Any, Dict, Optional, Union
from datetime import datetime

# ---------------------------------------------------------------------
# Create a standardized API response
# ---------------------------------------------------------------------
def create_response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    set_cookie: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], tuple]:
    """
    Create a standardized API response
    
    Args:
        success (bool): Whether the operation was successful
        message (str): Response message
        data (Optional[Dict]): Response data
        status_code (int): HTTP status code
        set_cookie (Optional[Dict]): Cookie information for setting cookies
    
    Returns:
        Dict or tuple: Standardized response
    """
    response_data = {
        "success": success,
        "message": message,
        "data": data or {}
    }
    
    if set_cookie:
        # Create response with cookie
        response = make_response(jsonify(response_data), status_code)
        response.set_cookie(**set_cookie)
        return response
    
    return response_data, status_code


# ---------------------------------------------------------------------
# Success response
# ---------------------------------------------------------------------
def success_response(
    message: str = "Operation completed successfully",
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    set_cookie: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], tuple]:
    """
    Create a success response
    
    Args:
        message (str): Success message
        data (Optional[Dict]): Response data
        status_code (int): HTTP status code
        set_cookie (Optional[Dict]): Cookie information for setting cookies
    
    Returns:
        Dict or tuple: Success response
    """
    return create_response(
        success=True,
        message=message,
        data=data,
        status_code=status_code,
        set_cookie=set_cookie
    )


# ---------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------
def error_response(
    message: str = "An error occurred",
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
    error_details: Optional[str] = None
) -> tuple:
    """
    Create an error response
    
    Args:
        message (str): Error message
        data (Optional[Dict]): Additional error data
        status_code (int): HTTP status code
        error_details (Optional[str]): Detailed error information
    
    Returns:
        tuple: Error response with status code
    """
    error_data = data or {}
    if error_details:
        error_data["error_details"] = error_details
    
    return create_response(
        success=False,
        message=message,
        data=error_data,
        status_code=status_code
    )


# ---------------------------------------------------------------------
# Validation error response
# ---------------------------------------------------------------------
def validation_error_response(
    validation_errors: Union[str, Dict],
    message: str = "Validation failed"
) -> tuple:
    """
    Create a validation error response
    
    Args:
        validation_errors: Validation error details
        message (str): Error message
    
    Returns:
        tuple: Validation error response
    """
    return error_response(
        message=message,
        data={"validation_errors": validation_errors},
        status_code=400
    )


# ---------------------------------------------------------------------
# Not found response
# ---------------------------------------------------------------------
def not_found_response(
    message: str = "Resource not found",
    resource_type: str = "Resource"
) -> tuple:
    """
    Create a not found response
    
    Args:
        message (str): Error message
        resource_type (str): Type of resource not found
    
    Returns:
        tuple: Not found response
    """
    return error_response(
        message=message,
        data={"resource_type": resource_type},
        status_code=404
    )


# ---------------------------------------------------------------------
# Unauthorized response
# ---------------------------------------------------------------------
def unauthorized_response(
    message: str = "Unauthorized access",
    reason: str = None
) -> tuple:
    """
    Create an unauthorized response
    
    Args:
        message (str): Error message
        reason (str): Reason for unauthorized access
    
    Returns:
        tuple: Unauthorized response
    """
    data = {}
    if reason:
        data["reason"] = reason
    
    return error_response(
        message=message,
        data=data,
        status_code=401
    )


# ---------------------------------------------------------------------
# Forbidden response
# ---------------------------------------------------------------------
def forbidden_response(
    message: str = "Access forbidden",
    reason: str = None
) -> tuple:
    """
    Create a forbidden response
    
    Args:
        message (str): Error message
        reason (str): Reason for forbidden access
    
    Returns:
        tuple: Forbidden response
    """
    data = {}
    if reason:
        data["reason"] = reason
    
    return error_response(
        message=message,
        data=data,
        status_code=403
    )


# ---------------------------------------------------------------------
# Internal error response
# ---------------------------------------------------------------------
def internal_error_response(
    message: str = "Internal server error",
    error_details: str = None
) -> tuple:
    """
    Create an internal server error response
    
    Args:
        message (str): Error message
        error_details (str): Detailed error information
    
    Returns:
        tuple: Internal error response
    """
    return error_response(
        message=message,
        data={"error_details": error_details} if error_details else {},
        status_code=500
    )
