"""
Password Reset Schemas
Marshmallow schemas for password reset operations
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError


# --------------------------------------------------------------------------------------
# REQUEST :- PASSWORD RESET
# --------------------------------------------------------------------------------------
class RequestPasswordResetSchema(Schema):
    """Schema for requesting password reset"""
    email = fields.Email(
        required=True,
        validate=[
            validate.Length(min=5, max=255, error="Email must be between 5 and 255 characters"),
            validate.Email(error="Invalid email format")
        ],
        error_messages={
            'required': 'Email is required',
            'invalid': 'Invalid email format'
        }
    )


class ResetPasswordSchema(Schema):
    """Schema for resetting password with token"""
    token = fields.Str(
        required=True,
        validate=[
            validate.Length(min=32, max=100, error="Invalid token format"),
            validate.Regexp(
                r'^[A-Za-z0-9_-]+$',
                error="Token contains invalid characters"
            )
        ],
        error_messages={
            'required': 'Reset token is required',
            'invalid': 'Invalid token format'
        }
    )
    
    new_password = fields.Str(
        required=True,
        validate=[
            validate.Length(min=8, max=128, error="Password must be between 8 and 128 characters"),
            validate.Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$',
                error="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character (@$!%*?&)"
            )
        ],
        error_messages={
            'required': 'New password is required',
            'invalid': 'Password does not meet security requirements'
        }
    )
    
    confirm_password = fields.Str(
        required=True,
        validate=[
            validate.Length(min=8, max=128, error="Confirm password must be between 8 and 128 characters")
        ],
        error_messages={
            'required': 'Password confirmation is required',
            'invalid': 'Password confirmation is invalid'
        }
    )
    
    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        """Validate that passwords match"""
        if 'new_password' in data and 'confirm_password' in data:
            if data['new_password'] != data['confirm_password']:
                raise ValidationError('Passwords do not match', field='confirm_password')


class PasswordResetResponseSchema(Schema):
    """Schema for password reset response"""
    message = fields.Str(required=True)
    success = fields.Bool(required=True)
    error = fields.Str(required=False)
    retry_after = fields.Int(required=False)


class TokenVerificationResponseSchema(Schema):
    """Schema for token verification response"""
    message = fields.Str(required=True)
    success = fields.Bool(required=True)
    user = fields.Dict(required=False)
    error = fields.Str(required=False)


class PasswordResetSuccessSchema(Schema):
    """Schema for successful password reset"""
    message = fields.Str(required=True)
    success = fields.Bool(required=True)


class PasswordValidationSchema(Schema):
    """Schema for password validation rules"""
    min_length = fields.Int(required=True)
    max_length = fields.Int(required=True)
    require_uppercase = fields.Bool(required=True)
    require_lowercase = fields.Bool(required=True)
    require_numbers = fields.Bool(required=True)
    require_special_chars = fields.Bool(required=True)
    special_chars = fields.Str(required=True)
    requirements = fields.List(fields.Str(), required=True)


# Password validation rules for frontend
PASSWORD_VALIDATION_RULES = {
    'min_length': 8,
    'max_length': 128,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_numbers': True,
    'require_special_chars': True,
    'special_chars': '@$!%*?&',
    'requirements': [
        'Minimum 8 characters',
        'At least 1 uppercase letter',
        'At least 1 lowercase letter',
        'At least 1 number',
        'At least 1 special character (@$!%*?&)'
    ]
}
