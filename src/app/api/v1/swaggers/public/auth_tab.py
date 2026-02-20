"""
Authentication Tab Swagger Documentation

Contains all authentication-related API documentation including:
- Auth0 authentication
- User registration
- User login
- User management
"""

from flask_restx import Namespace, fields

# Create Authentication Namespace
auth_ns = Namespace('auth', description='Authentication operations')

# ----------------------------------------------------------------------------
# Verify auth0 access token
# ----------------------------------------------------------------------------
auth0_verify_model = auth_ns.model('Auth0Verify', {
    'access_token': fields.String(
        required=True,
        description='Auth0 access token to verify (from SDK or password-realm login)',
        example='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkRMRUVsSlI4YjJXQ2dvd1lBcVRzTSJ9...',
        min_length=1
    )
})

# User Response Models
user_response_model = auth_ns.model('UserResponse', {
    'id_user': fields.Integer(description='User ID'),
    'email': fields.String(description='User email'),
    'role': fields.String(description='User role'),
    'name': fields.String(description='First name'),
    'surname': fields.String(description='Last name'),
    'status': fields.String(description='Account status'),
    'is_verified': fields.Boolean(description='Email verification status'),
    'auth0_user_id': fields.String(description='Auth0 user ID')
})

# User Management Models
create_user_model = auth_ns.model('CreateUser', {
    'email': fields.String(required=True, description='Email address', example='user@example.com'),
    'password': fields.String(required=True, description='Password (min 8 characters)', example='SecurePass123!'),
    'first_name': fields.String(required=True, description='First name', example='John'),
    'last_name': fields.String(required=True, description='Last name', example='Doe'),
    'role': fields.String(required=True, description='User role', enum=['superadmin', 'admin', 'manager', 'staff', 'user'], example='user'),
    'language': fields.String(description='Language preference', example='en'),
    'company_name': fields.String(description='Company name', example='KBAI Corp'),
    'phone': fields.String(description='Phone number', example='+1234567890'),
    'number_licences': fields.Integer(description='Number of licenses', example=10),
    'premium_licenses_1': fields.Integer(description='Premium licenses type 1', example=5),
    'premium_licenses_2': fields.Integer(description='Premium licenses type 2', example=3)
})

update_user_model = auth_ns.model('UpdateUser', {
    'email': fields.String(description='Email address', example='user@example.com'),
    'first_name': fields.String(description='First name', example='John'),
    'last_name': fields.String(description='Last name', example='Doe'),
    'name': fields.String(description='First name (alias)', example='John'),
    'surname': fields.String(description='Last name (alias)', example='Doe'),
    'role': fields.String(description='User role', enum=['superadmin', 'admin', 'manager', 'staff', 'user'], example='user'),
    'status': fields.String(description='Account status', enum=['ACTIVE', 'INACTIVE', 'SUSPENDED'], example='ACTIVE'),
    'language': fields.String(description='Language preference', example='en'),
    'phone': fields.String(description='Phone number', example='+1234567890'),
    'company_name': fields.String(description='Company name', example='KBAI Corp'),
    'number_licences': fields.Integer(description='Number of licenses', example=10),
    'premium_licenses_1': fields.Integer(description='Premium licenses type 1', example=5),
    'premium_licenses_2': fields.Integer(description='Premium licenses type 2', example=3)
})

change_password_model = auth_ns.model('ChangePassword', {
    'current_password': fields.String(required=True, description='Current password'),
    'new_password': fields.String(required=True, description='New password'),
    'confirm_password': fields.String(required=True, description='Confirm new password')
})

users_list_response_model = auth_ns.model('UsersListResponse', {
    'users': fields.List(fields.Nested(user_response_model), description='List of users'),
    'total': fields.Integer(description='Total number of users'),
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Number of users per page')
})

# Additional Auth0 Models
auth0_logout_response_model = auth_ns.model('Auth0LogoutResponse', {
    'message': fields.String(description='Logout message'),
    'success': fields.Boolean(description='Logout success status')
})

auth0_verify_token_response_model = auth_ns.model('Auth0VerifyTokenResponse', {
    'message': fields.String(description='Verification message'),
    'valid': fields.Boolean(description='Token validity'),
    'user': fields.Nested(user_response_model, description='User information')
})

# Generic Response Models
success_response_model = auth_ns.model('SuccessResponse', {
    'message': fields.String(description='Success message'),
    'success': fields.Boolean(description='Operation success status')
})

error_response_model = auth_ns.model('ErrorResponse', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message'),
    'details': fields.Raw(description='Additional error details')
})

# Example Responses
EXAMPLE_AUTH0_LOGIN = {
    "message": "Login successful",
    "user": {
        "id_user": 1,
        "email": "john@example.com",
        "role": "user",
        "name": "John",
        "surname": "Doe",
        "status": "ACTIVE",
        "is_verified": True,
        "auth0_user_id": "auth0|1234567890"
    },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
}

EXAMPLE_USER_CREATED = {
    "message": "User created successfully",
    "user": {
        "id_user": 2,
        "email": "jane@example.com",
        "role": "user",
        "name": "Jane",
        "surname": "Doe",
        "status": "ACTIVE",
        "is_verified": False,
        "auth0_user_id": None
    }
}

EXAMPLE_USERS_LIST = {
    "users": [
        {
            "id_user": 1,
            "email": "john@example.com",
            "role": "admin",
            "name": "John",
            "surname": "Doe",
            "status": "ACTIVE",
            "is_verified": True,
            "auth0_user_id": "auth0|1234567890"
        }
    ],
    "total": 1,
    "page": 1,
    "per_page": 10
}

EXAMPLE_CHANGE_PASSWORD = {
    "message": "Password changed successfully"
}

EXAMPLE_VALIDATION_ERROR = {
    "error": "Validation error",
    "message": "Invalid input data",
    "details": {
        "email": ["Invalid email format"]
    }
}

EXAMPLE_AUTH_ERROR = {
    "error": "Authentication failed",
    "message": "Invalid credentials"
}
