"""
OTP Tab Swagger Documentation

Contains all OTP (One-Time Password) related API documentation including:
- OTP generation
- OTP verification
"""

from flask_restx import Namespace, fields

# Create OTP Namespace
otp_ns = Namespace('otp', description='OTP operations for 2-step verification')

# OTP Models
create_otp_model = otp_ns.model('CreateOTP', {
    'email': fields.String(required=True, description='Email address to send OTP to')
})

verify_otp_model = otp_ns.model('VerifyOTP', {
    'email': fields.String(required=True, description='Email address'),
    'otp': fields.String(required=True, description='6-digit OTP code')
})

# Response Models
otp_response_model = otp_ns.model('OTPResponse', {
    'message': fields.String(description='Response message'),
    'success': fields.Boolean(description='Operation success status')
})

otp_verification_response_model = otp_ns.model('OTPVerificationResponse', {
    'message': fields.String(description='Response message'),
    'success': fields.Boolean(description='Verification success status'),
    'access_token': fields.String(description='JWT access token if verification successful')
})

# Example Responses
EXAMPLE_OTP_RESPONSE = {
    "message": "OTP sent successfully to your email",
    "success": True
}

EXAMPLE_OTP_VERIFICATION_RESPONSE = {
    "message": "OTP verified successfully",
    "success": True,
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
