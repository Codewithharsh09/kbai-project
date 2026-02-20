"""
OTP Schemas for 2-Step Verification
Marshmallow schemas for OTP validation and serialization
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from marshmallow.decorators import post_load
from datetime import datetime


class CreateOtpSchema(Schema):
    """Schema for creating OTP"""
    
    email = fields.Email(
        required=True,
        validate=validate.Length(max=255, error="Email must be less than 255 characters"),
        metadata={
            "description": "User email address",
            "example": "john@example.com",
            "maxLength": 255
        }
    )


class VerifyOtpSchema(Schema):
    """Schema for verifying OTP"""
    
    email = fields.Email(
        required=True,
        validate=validate.Length(max=255, error="Email must be less than 255 characters"),
        metadata={
            "description": "User email address",
            "example": "john@example.com",
            "maxLength": 255
        }
    )
    
    otp = fields.Str(
        required=True,
        validate=[
            validate.Length(min=6, max=6, error="OTP must be exactly 6 digits"),
            validate.Regexp(r'^\d{6}$', error="OTP must contain only digits")
        ],
        metadata={
            "description": "6-digit OTP code",
            "example": "123456",
            "minLength": 6,
            "maxLength": 6
        }
    )


class OtpResponseSchema(Schema):
    """Schema for OTP response"""
    
    message = fields.Str(
        metadata={
            "description": "Response message",
            "example": "OTP sent successfully"
        }
    )
    
    email = fields.Email(
        metadata={
            "description": "Email address",
            "example": "john@example.com"
        }
    )
    
    expires_in_minutes = fields.Int(
        metadata={
            "description": "OTP expiry time in minutes",
            "example": 10
        }
    )
    
    success = fields.Bool(
        metadata={
            "description": "Indicates if the request was successful",
            "example": True
        }
    )


class OtpVerificationResponseSchema(Schema):
    """Schema for OTP verification response"""
    
    message = fields.Str(
        metadata={
            "description": "Response message",
            "example": "OTP verified successfully"
        }
    )
    
    user = fields.Dict(
        metadata={
            "description": "User information",
            "example": {
                "id_user": 1,
                "email": "john@example.com",
                "role": "USER",
                "status": "ACTIVE"
            }
        }
    )
    
    success = fields.Bool(
        metadata={
            "description": "Indicates if the request was successful",
            "example": True
        }
    )


# Example data for Swagger documentation
EXAMPLE_CREATE_OTP = {
    'email': 'john@example.com'
}

EXAMPLE_VERIFY_OTP = {
    'email': 'john@example.com',
    'otp': '123456'
}

EXAMPLE_OTP_RESPONSE = {
    'message': 'OTP sent successfully',
    'email': 'john@example.com',
    'expires_in_minutes': 10,
    'success': True
}

EXAMPLE_OTP_VERIFICATION_RESPONSE = {
    'message': 'OTP verified successfully',
    'user': {
        'id_user': 1,
        'email': 'john@example.com',
        'role': 'USER',
        'status': 'ACTIVE'
    },
    'success': True
}
