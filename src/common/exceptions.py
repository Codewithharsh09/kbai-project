"""
Custom Exception Classes for Flask Enterprise Template

This module defines custom exception classes for better error handling
and standardized error responses across the application.

Features:
- API-specific exceptions with status codes
- User management exceptions
- Database operation exceptions
- Validation exceptions
- Authentication exceptions
- Global error handlers

Author: Flask Enterprise Template
License: MIT
"""

from flask import jsonify, request
from src.extensions import db


class APIError(Exception):
    """Base API exception class with status code"""
    
    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class UserNotFoundError(APIError):
    """Exception raised when user is not found"""
    
    def __init__(self, message="User not found", user_id=None):
        super().__init__(message, status_code=404, error_code="USER_NOT_FOUND")
        self.user_id = user_id


class UserEmailExistsError(APIError):
    """Exception raised when user email already exists"""
    
    def __init__(self, message="Email already exists", email=None):
        super().__init__(message, status_code=400, error_code="EMAIL_EXISTS")
        self.email = email


class UserValidationError(APIError):
    """Exception raised when user validation fails"""
    
    def __init__(self, message="User validation failed", details=None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", details=details)


class UserAuthenticationError(APIError):
    """Exception raised when user authentication fails"""
    
    def __init__(self, message="Authentication failed", details=None):
        super().__init__(message, status_code=401, error_code="AUTHENTICATION_FAILED", details=details)


class UserAuthorizationError(APIError):
    """Exception raised when user authorization fails"""
    
    def __init__(self, message="Access denied", details=None):
        super().__init__(message, status_code=403, error_code="AUTHORIZATION_FAILED", details=details)


class DatabaseError(APIError):
    """Exception raised when database operation fails"""
    
    def __init__(self, message="Database operation failed", details=None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class EntityNotFoundError(APIError):
    """Exception raised when entity is not found"""
    
    def __init__(self, message="Entity not found", entity_type=None, entity_id=None):
        super().__init__(message, status_code=404, error_code="ENTITY_NOT_FOUND")
        self.entity_type = entity_type
        self.entity_id = entity_id


class EntityValidationError(APIError):
    """Exception raised when entity validation fails"""
    
    def __init__(self, message="Entity validation failed", details=None):
        super().__init__(message, status_code=400, error_code="ENTITY_VALIDATION_ERROR", details=details)


class ExternalServiceError(APIError):
    """Exception raised when external service fails"""
    
    def __init__(self, message="External service error", service_name=None, details=None):
        super().__init__(message, status_code=502, error_code="EXTERNAL_SERVICE_ERROR", details=details)
        self.service_name = service_name


class RateLimitExceededError(APIError):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message="Rate limit exceeded", details=None):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details)


class FileUploadError(APIError):
    """Exception raised when file upload fails"""
    
    def __init__(self, message="File upload failed", details=None):
        super().__init__(message, status_code=400, error_code="FILE_UPLOAD_ERROR", details=details)


class ConfigurationError(APIError):
    """Exception raised when configuration is invalid"""
    
    def __init__(self, message="Configuration error", details=None):
        super().__init__(message, status_code=500, error_code="CONFIGURATION_ERROR", details=details)


def register_error_handlers(app):
    """
    Register global error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors"""
        response = {
            'success': False,
            'message': error.message,
            'error_code': error.error_code,
            'status_code': error.status_code
        }
        
        if error.details:
            response['details'] = error.details
            
        return jsonify(response), error.status_code
    
    @app.errorhandler(UserNotFoundError)
    def handle_user_not_found(error):
        """Handle user not found errors"""
        return jsonify({
            'success': False,
            'message': error.message,
            'error_code': error.error_code,
            'status_code': 404,
            'user_id': getattr(error, 'user_id', None)
        }), 404
    
    @app.errorhandler(UserEmailExistsError)
    def handle_email_exists(error):
        """Handle email exists errors"""
        return jsonify({
            'success': False,
            'message': error.message,
            'error_code': error.error_code,
            'status_code': 400,
            'email': getattr(error, 'email', None)
        }), 400
    
    @app.errorhandler(UserValidationError)
    def handle_validation_error(error):
        """Handle validation errors"""
        return jsonify({
            'success': False,
            'message': error.message,
            'error_code': error.error_code,
            'status_code': 400,
            'details': error.details
        }), 400
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        """Handle database errors"""
        # Rollback database session in case of error
        try:
            db.session.rollback()
        except Exception:
            pass
            
        return jsonify({
            'success': False,
            'message': error.message,
            'error_code': error.error_code,
            'status_code': 500,
            'details': error.details
        }), 500
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found errors"""
        return jsonify({
            'success': False,
            'message': 'Resource not found',
            'error_code': 'NOT_FOUND',
            'status_code': 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        """Handle 405 Method Not Allowed errors"""
        return jsonify({
            'success': False,
            'message': 'Method not allowed',
            'error_code': 'METHOD_NOT_ALLOWED',
            'status_code': 405
        }), 405
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 Internal Server Error"""
        # Rollback database session in case of error
        try:
            db.session.rollback()
        except Exception:
            pass
            
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'status_code': 500
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions"""
        # Rollback database session
        try:
            db.session.rollback()
        except Exception:
            pass
        
        # Log the error
        app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        
        # Return generic error in production, detailed in development
        if app.config.get('DEBUG'):
            return jsonify({
                'success': False,
                'message': str(error),
                'error_code': 'UNHANDLED_EXCEPTION',
                'status_code': 500
            }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'status_code': 500
            }), 500

