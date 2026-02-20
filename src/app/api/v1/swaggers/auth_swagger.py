"""
Authentication Swagger Documentation - Simplified

This module contains Swagger documentation for 3 essential authentication endpoints:
1. Register - for admin, super admin, and user registration
2. Login - for admin, super admin, and user login  
3. Auth0 - for Auth0 authentication

Author: Flask Enterprise Template
License: MIT
"""

from flask_restx import fields, Namespace

# Create authentication namespace
auth_ns = Namespace('auth', description='Authentication operations')

# =============================================================================
# REQUEST MODELS
# =============================================================================

# Auth0 Verify Request Model - NEW for /auth0/verify endpoint
auth0_verify_model = auth_ns.model('Auth0Verify', {
    'access_token': fields.String(
        required=True,
        description='Auth0 access token to verify (from SDK or password-realm login)',
        example='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkRMRUVsSlI4YjJXQ2dvd1lBcVRzTSJ9...',
        min_length=1
    )
})

# =============================================================================
# RESPONSE MODELS
# =============================================================================

# User Response Model
user_response_model = auth_ns.model('UserResponse', {
    'id_user': fields.Integer(
        description='Unique user ID', 
        example=1
    ),
    'email': fields.String(
        description='Email address', 
        example='john@example.com'
    ),
    'role': fields.String(
        description='User role', 
        example='USER',
        enum=['SUPER_ADMIN', 'ADMIN', 'USER']
    ),
    'name': fields.String(
        description='First name', 
        example='John'
    ),
    'surname': fields.String(
        description='Last name', 
        example='Doe'
    ),
    'language': fields.String(
        description='Preferred language', 
        example='en'
    ),
    'status': fields.String(
        description='Account status', 
        example='ACTIVE',
        enum=['ACTIVE', 'INACTIVE', 'SUSPENDED']
    ),
    'is_verified': fields.Boolean(
        description='Email verification status', 
        example=True
    ),
    'created_at': fields.String(
        description='Account creation timestamp', 
        example='2023-09-23T13:20:00Z'
    ),
    'auth0_user_id': fields.String(
        description='Auth0 user ID (if using Auth0)', 
        example='google-oauth2|123456789012345678901'
    )
})

# Old login response model removed - using Auth0 only

# Success Response Model
success_response_model = auth_ns.model('SuccessResponse', {
    'message': fields.String(
        description='Success message', 
        example='User registered successfully'
    ),
    'user': fields.Nested(user_response_model)
})

# Error Response Model
error_response_model = auth_ns.model('ErrorResponse', {
    'error': fields.String(
        description='Error message', 
        example='Invalid credentials'
    ),
    'message': fields.String(
        description='Additional error details', 
        example='Username or password is incorrect'
    )
})


# Auth0 Login Response Model (with tokens) - kept for legacy compatibility
auth0_login_response_model = auth_ns.model('Auth0LoginResponse', {
    'message': fields.String(
        description='Response message',
        example='Auth0 login successful'
    ),
    'user': fields.Nested(user_response_model),
    'auth0_tokens': fields.Nested(auth_ns.model('Auth0Tokens', {
        'id_token': fields.String(
            description='Auth0 ID token',
            example='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
        ),
        'access_token': fields.String(
            description='Auth0 access token',
            example='eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0...'
        ),
        'refresh_token': fields.String(
            description='Auth0 refresh token',
            example='v1.eyJzdWIiOiJnb29nbGUtb2F1dGgyfDExMzc3NTU5Mzg2NTgxNzI0MzQ5NyIsIm5hbWUiOiJURUpBUyBOSVJBTEEiLCJlbWFpbCI6InRlamFzbmlyYWxhNEBnbWFpbC5jb20iLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jS0N2QjhJMzk4RG1ZaWpMSTlGUDJncWxzaUFpSnEyYzBRVlZvYXBUbHFE...'
        ),
        'expires_in': fields.Integer(
            description='Token expiration time in seconds',
            example=86400
        ),
        'token_type': fields.String(
            description='Token type',
            example='Bearer'
        )
    }))
})

# Auth0 Logout Response Model
auth0_logout_response_model = auth_ns.model('Auth0LogoutResponse', {
    'message': fields.String(
        description='Response message',
        example='Logout successful'
    ),
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    )
})

# Auth0 Verify Token Response Model
auth0_verify_token_response_model = auth_ns.model('Auth0VerifyTokenResponse', {
    'message': fields.String(
        description='Response message',
        example='Token is valid'
    ),
    'user': fields.Nested(user_response_model),
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    )
})

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Password validation rules
PASSWORD_RULES = {
    'min_length': 8,
    'max_length': 128,
    'must_contain': [
        'lowercase letter',
        'uppercase letter', 
        'number',
        'special character'
    ],
    'pattern': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]'
}

# Username validation rules
USERNAME_RULES = {
    'min_length': 3,
    'max_length': 120,
    'pattern': r'^[a-zA-Z0-9_]+$',
    'description': 'Username can only contain letters, numbers, and underscores'
}

# Email validation rules
EMAIL_RULES = {
    'max_length': 255,
    'format': 'Valid email address',
    'unique': True
}

# =============================================================================
# EXAMPLE DATA
# =============================================================================

# Example request data
EXAMPLE_REGISTER = {
    'email': 'john@example.com',
    'password': 'Password@123',
    'first_name': 'John',
    'last_name': 'Doe',
    'role': 'USER'
}

EXAMPLE_LOGIN = {
    'email': 'john@example.com',
    'password': 'Password@123'
}

EXAMPLE_AUTH0_CALLBACK = {
    'id_token': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkRMRUVsSlI4YjJXQ2dvd1lBcVRzTSJ9.eyJnaXZlbl9uYW1lIjoiVEVKQVMiLCJmYW1pbHlfbmFtZSI6Ik5JUkFMQSIsIm5pY2tuYW1lIjoidGVqYXNuaXJhbGE0IiwibmFtZSI6IlRFSkFTIE5JUkFMQSIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NLQ3ZCOEkzOThEbVlpakxJOUZQMmdxbHNpQWlKcTJjMFFWVm9hcFRscUR3QTVYR2h6Tz1zOTYtYyIsInVwZGF0ZWRfYXQiOiIyMDI1LTA5LTIzVDExOjIyOjU2LjgwMVoiLCJlbWFpbCI6InRlamFzbmlyYWxhNEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6Ly9kZXYtNnR1YmhuMjFjbTJhNGkyNi51cy5hdXRoMC5jb20vIiwiYXVkIjoic0lSN2sxSlRLeE1YUGJid2k4bmhyUTdUdWRMcThMNmUiLCJzdWIiOiJnb29nbGUtb2F1dGgyfDExMzc3NTU5Mzg2NTgxNzI0MzQ5NyIsImlhdCI6MTc1ODYzMDc1OCwiZXhwIjoxNzU4NjY2NzU4LCJzaWQiOiI3TDZxNC10WjMtZUw4OGdGeHVGLVZlWGpINURlMFl1bSIsIm5vbmNlIjoiclk3VzRON2Rjd2ZDeTN0QmdmYkNBZmViTGM1Y0dQbXlLM3p5Z1Y2OUZpcyJ9.kn1-gsaS8FSn46nHqToRUWENaVs91xu07lOlJoAtFmq-TWayY2VtNvbfkUQ4SpDwTGfqjG0VLCytwftiaEvnLLIcdpFOo5mowsvyYbexgPvqDiWy0sIVDsaISqrPWJkESPqmryq5DTw0tNqPEvfyE6nCCC9n407jebvTg7nHDJg1oplmckdcrbsGVj0n_Y1JH4463OiTfZky8sZDFheGi4wzRmeBR0mPdVNp5YJO1g4E_W_1aqzM2IqKJeOiKNPQdS6lVFFmxdsrCPDWz_Bcer6FA-l4Y5B7AEMq-si_0TKz9-VbTmp1xsWl-PcffAKC8eeGTyxZk4N_PydEd0szTQ'
}

# Example response data
EXAMPLE_USER_RESPONSE = {
    'id_user': 1,
    'email': 'john@example.com',
    'role': 'USER',
    'name': 'John',
    'surname': 'Doe',
    'language': 'en',
    'status': 'ACTIVE',
    'is_verified': True,
    'created_at': '2023-09-23T13:20:00Z',
    'auth0_user_id': None
}

EXAMPLE_LOGIN_RESPONSE = {
    'message': 'Login successful',
    'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
    'user': EXAMPLE_USER_RESPONSE
}

# =============================================================================
# ERROR EXAMPLES
# =============================================================================

# Validation error examples
EXAMPLE_VALIDATION_ERROR = {
    'error': 'Validation failed',
    'message': {
        'password': ['Password must contain at least one lowercase letter, one uppercase letter, one number, and one special character']
    }
}

# Authentication error examples
EXAMPLE_AUTH_ERROR = {
    'error': 'Invalid credentials',
    'message': 'Username or password is incorrect'
}

# =============================================================================

# -----------------------------------------------------------------------------
# Create User Request Model
# -----------------------------------------------------------------------------
create_user_model = auth_ns.model('CreateUser', {
    'email': fields.String(
        required=True,
        description='Valid email address',
        example='john@example.com',
        max_length=255
    ),
    'password': fields.String(
        required=True,
        description='Strong password (8-128 characters, must include uppercase, lowercase, number, and special character)',
        example='Password@123',
        min_length=8,
        max_length=128
    ),
    'first_name': fields.String(
        required=True,
        description='First name',
        example='John',
        min_length=1,
        max_length=120
    ),
    'last_name': fields.String(
        required=True,
        description='Last name',
        example='Doe',
        min_length=1,
        max_length=120
    ),
    'role': fields.String(
        required=True,
        description='User role',
        example='USER',
        enum=['SUPER_ADMIN', 'ADMIN', 'USER']
    )
})

# -----------------------------------------------------------------------------
# Update User Request Model
# -----------------------------------------------------------------------------
update_user_model = auth_ns.model('UpdateUser', {
    'name': fields.String(
        description='First name',
        example='John',
        min_length=1,
        max_length=120
    ),
    'surname': fields.String(
        description='Last name',
        example='Doe',
        min_length=1,
        max_length=120
    ),
    'role': fields.String(
        description='User role',
        example='admin',
        enum=['superadmin', 'admin', 'manager', 'staff', 'user']
    ),
    'status': fields.String(
        description='User status',
        example='ACTIVE',
        enum=['ACTIVE', 'INACTIVE', 'SUSPENDED']
    ),
    'language': fields.String(
        description='Preferred language',
        example='en',
        enum=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko']
    ),
    'phone': fields.String(
        description='Phone number',
        example='+1234567890',
        max_length=20
    ),
    'company_name': fields.String(
        description='Company name',
        example='KBAI Corp',
        max_length=255
    ),
    'number_licences': fields.Integer(
        description='Number of licenses',
        example=10
    ),
    'premium_licenses_1': fields.Integer(
        description='Premium licenses type 1',
        example=5
    ),
    'premium_licenses_2': fields.Integer(
        description='Premium licenses type 2',
        example=3
    )
})

# -----------------------------------------------------------------------------
# Change Password Request Model
# -----------------------------------------------------------------------------
change_password_model = auth_ns.model('ChangePassword', {
    'current_password': fields.String(
        required=True,
        description='Current password',
        example='CurrentPass@123'
    ),
    'new_password': fields.String(
        required=True,
        description='New password (8-128 characters, must include uppercase, lowercase, number, and special character)',
        example='NewPassword@123',
        min_length=8,
        max_length=128
    )
})

# -----------------------------------------------------------------------------
# Users List Response Model
# -----------------------------------------------------------------------------
users_list_response_model = auth_ns.model('UsersListResponse', {
    'users': fields.List(fields.Nested(user_response_model)),
    'total': fields.Integer(description='Total number of users', example=25),
    'page': fields.Integer(description='Current page number', example=1),
    'per_page': fields.Integer(description='Number of users per page', example=10),
    'total_pages': fields.Integer(description='Total number of pages', example=3)
})

# Example request data
EXAMPLE_CREATE_USER = {
    'email': 'john@example.com',
    'password': 'Password@123',
    'first_name': 'John',
    'last_name': 'Doe',
    'role': 'USER'
}

EXAMPLE_UPDATE_USER = {
    'name': 'John',
    'surname': 'Smith',
    'role': 'admin',
    'status': 'ACTIVE',
    'language': 'en',
    'phone': '+1234567890',
    'company_name': 'KBAI Corp'
}

EXAMPLE_CHANGE_PASSWORD = {
    'current_password': 'CurrentPass@123',
    'new_password': 'NewPassword@123'
}

# =============================================================================
# EXPORT ALL MODELS
# =============================================================================

__all__ = [
    'auth_ns',
    'auth0_verify_model',
    'user_response_model',
    'auth0_login_response_model',
    'auth0_logout_response_model',
    'auth0_verify_token_response_model',
    'success_response_model',
    'error_response_model',
    'create_user_model',
    'update_user_model',
    'change_password_model',
    'users_list_response_model',
    'PASSWORD_RULES',
    'USERNAME_RULES',
    'EMAIL_RULES',
    'EXAMPLE_AUTH0_CALLBACK',
    'EXAMPLE_USER_RESPONSE',
    'EXAMPLE_CREATE_USER',
    'EXAMPLE_UPDATE_USER',
    'EXAMPLE_CHANGE_PASSWORD',
    'EXAMPLE_VALIDATION_ERROR',
    'EXAMPLE_AUTH_ERROR'
]