"""
Password Reset Tab Swagger Documentation

Contains all password reset related API documentation including:
- Password reset request
- Token verification
- Password reset completion
"""

from flask_restx import Namespace, fields

# Create Password Reset Namespace
password_reset_ns = Namespace(
    'password-reset',
    description='Password reset operations with secure token-based reset flow'
)

# Password Reset Models
request_password_reset_model = password_reset_ns.model('RequestPasswordReset', {
    'email': fields.String(required=True, description='Email address to send reset link to')
})

reset_password_model = password_reset_ns.model('ResetPassword', {
    'token': fields.String(required=True, description='Reset token from email link'),
    'new_password': fields.String(required=True, description='New password'),
    'confirm_password': fields.String(required=True, description='Confirm new password')
})

# Response Models
password_reset_response_model = password_reset_ns.model('PasswordResetResponse', {
    'message': fields.String(description='Response message'),
    'success': fields.Boolean(description='Operation success status')
})

password_reset_success_model = password_reset_ns.model('PasswordResetSuccess', {
    'message': fields.String(description='Success message'),
    'success': fields.Boolean(description='Reset success status')
})

# Validation Rules
PASSWORD_RULES = {
    'min_length': 8,
    'max_length': 128,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digit': True,
    'require_special_char': True
}

EMAIL_RULES = {
    'format': 'Valid email address format',
    'domain_validation': 'Domain must be valid'
}

TOKEN_RULES = {
    'expiry_minutes': 30,
    'single_use': True,
    'secure_generation': 'Cryptographically secure random token'
}

# Example Responses
EXAMPLE_PASSWORD_RESET_REQUEST = {
    "message": "If this email is registered, you will receive a reset link.",
    "success": True
}

EXAMPLE_PASSWORD_RESET_SUCCESS = {
    "message": "Password reset successfully. Please log in with your new password.",
    "success": True
}
