"""
Public Schemas Package

Contains Marshmallow schemas for public-facing API endpoints:
- Authentication (Auth0)
- OTP (One-Time Password)
- Password reset
"""

from .auth_schemas import (
    Auth0VerifySchema,
    CreateUserSchema,
)

from .otp_schemas import (
    CreateOtpSchema,
    VerifyOtpSchema
)

from .password_reset_schemas import (
    RequestPasswordResetSchema,
    ResetPasswordSchema
)

__all__ = [
    # Auth
    'Auth0VerifySchema',
    'CreateUserSchema',
    
    # OTP
    'CreateOtpSchema',
    'VerifyOtpSchema',
    
    # Password Reset
    'RequestPasswordResetSchema',
    'ResetPasswordSchema',
]

