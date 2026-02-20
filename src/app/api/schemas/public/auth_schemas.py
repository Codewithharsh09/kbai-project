"""
Authentication API Schemas - Auth0 Only

This module contains Marshmallow schemas for Auth0 authentication endpoints:
1. Auth0 Login - Username/password via Auth0
2. Auth0 Callback - Social login callback

Author: Flask Enterprise Template
License: MIT
"""

from marshmallow import Schema, fields, validate


class Auth0VerifySchema(Schema):
    """
    Schema for verifying Auth0 access token.

    NEW ENDPOINT: POST /auth0/verify
    Used to verify Auth0 tokens and sync user data.
    """

    access_token = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Access token is required"),
        metadata={
            "description": "Auth0 access token to verify (obtained from Auth0 SDK or password-realm login)",
            "example": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkRMRUVsSlI4YjJXQ2dvd1lBcVRzTSJ9..."
        }
    )


class UserResponseSchema(Schema):
    """Schema for user response data"""
    
    id_user = fields.Int(
        metadata={
            "description": "Unique user ID",
            "example": 1
        }
    )
    
    email = fields.Str(
        metadata={
            "description": "Email address",
            "example": "john@example.com"
        }
    )
    
    role = fields.Str(
        metadata={
            "description": "User role",
            "example": "USER",
            "enum": ["SUPER_ADMIN", "ADMIN", "USER"]
        }
    )
    
    name = fields.Str(
        metadata={
            "description": "First name",
            "example": "John"
        }
    )
    
    surname = fields.Str(
        metadata={
            "description": "Last name",
            "example": "Doe"
        }
    )
    
    language = fields.Str(
        metadata={
            "description": "Preferred language",
            "example": "en"
        }
    )
    
    status = fields.Str(
        metadata={
            "description": "Account status",
            "example": "ACTIVE",
            "enum": ["ACTIVE", "INACTIVE", "SUSPENDED"]
        }
    )
    
    is_verified = fields.Bool(
        metadata={
            "description": "Email verification status",
            "example": True
        }
    )
    
    mfa = fields.Bool(
        metadata={
            "description": "Multi-Factor Authentication enabled status",
            "example": False
        }
    )
    
    companies = fields.List(
        fields.Dict(),
        metadata={
            "description": "List of companies assigned to user (only for USER role)",
            "example": [
                {"id_company": 1, "company_name": "ABC Corp"},
                {"id_company": 5, "company_name": "Tech Solutions"}
            ]
        }
    )
    
    created_at = fields.DateTime(
        metadata={
            "description": "Account creation timestamp",
            "example": "2023-09-23T13:20:00Z"
        }
    )
    
    auth0_user_id = fields.Str(
        metadata={
            "description": "Auth0 user ID (if using Auth0)",
            "example": "google-oauth2|123456789012345678901"
        }
    )


class ErrorResponseSchema(Schema):
    """Schema for error responses"""
    
    error = fields.Str(
        metadata={
            "description": "Error message",
            "example": "Invalid credentials"
        }
    )
    
    message = fields.Str(
        metadata={
            "description": "Additional error details",
            "example": "Username or password is incorrect"
        }
    )


class SuccessResponseSchema(Schema):
    """Schema for success responses"""
    
    message = fields.Str(
        metadata={
            "description": "Success message",
            "example": "Operation completed successfully"
        }
    )
    
    user = fields.Nested(UserResponseSchema)


# -----------------------------------------------------------------------------
# Create an admin or user and staff
# -----------------------------------------------------------------------------
class CreateUserSchema(Schema):
    """Schema for creating new user/admin - MVP Simple Validation"""

    email = fields.Email(
        required=True,
        metadata={"description": "Email address", "example": "user@example.com"}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters"),
        metadata={"description": "Password (min 8 characters)", "example": "SecurePass123!"}
    )
    first_name = fields.Str(
        required=True,
        metadata={"description": "First name", "example": "John"}
    )
    last_name = fields.Str(
        required=True,
        metadata={"description": "Last name", "example": "Doe"}
    )
    role = fields.Str(
        required=True,
        validate=validate.OneOf(['superadmin', 'admin', 'manager', 'staff', 'user'], error="Role must be one of: superadmin, admin, manager, staff, user"),
        metadata={"description": "User role", "example": "user"}
    )
    language = fields.Str(
        required=False,
        metadata={"description": "Language preference", "example": "en"}
    )
    phone = fields.Str(
        required=False,
        metadata={"description": "Phone number", "example": "+1234567890"}
    )
    company_name = fields.Str(
        required=False,
        metadata={"description": "Company name", "example": "KBAI Corp"}
    )
    number_licences = fields.Int(
        required=False,
        metadata={"description": "Number of licenses acquired", "example": 10}
    )
    premium_licenses_1 = fields.Int(
        required=False,
        metadata={"description": "Premium licenses type 1", "example": 5}
    )
    premium_licenses_2 = fields.Int(
        required=False,
        metadata={"description": "Premium licenses type 2", "example": 3}
    )
    companies = fields.List(
        fields.Int(),
        required=False,
        metadata={"description": "Array of company IDs to assign to user", "example": [1, 2, 3]}
    )


# ------------------------------------------------------------------------------
# Update a account
# ------------------------------------------------------------------------------
class UpdateUserSchema(Schema):
    """Schema for updating user information"""
    
    name = fields.Str(
        validate=validate.Length(min=1, max=120, error=" name must be between 1 and 120 characters"),
        metadata={
            "description": "First name",
            "example": "John"
        }
    )
    
    surname = fields.Str(
        validate=validate.Length(min=1, max=120, error="surname must be between 1 and 120 characters"),
        metadata={
            "description": "Last name",
            "example": "Doe"
        }
    )
        
    status = fields.Str(
        validate=validate.OneOf(['ACTIVE', 'INACTIVE', 'SUSPENDED'], error="Status must be one of: ACTIVE, INACTIVE, SUSPENDED"),
        metadata={
            "description": "User status",
            "example": "ACTIVE"
        }
    )
    
    language = fields.Str(
        validate=validate.OneOf(['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko'], error="Language must be a valid language code"),
        metadata={
            "description": "Preferred language",
            "example": "en"
        }
    )
    
    phone = fields.Str(
        validate=validate.Length(max=20, error="Phone number must be less than 20 characters"),
        metadata={
            "description": "Phone number",
            "example": "+1234567890"
        }
    )
    
    company_name = fields.Str(
        validate=validate.Length(max=255, error="Company name must be less than 255 characters"),
        metadata={
            "description": "Company name",
            "example": "KBAI Corp"
        }
    )
    
    number_licences = fields.Int(
        metadata={
            "description": "Number of licenses",
            "example": 10
        }
    )
    
    premium_licenses_1 = fields.Int(
        metadata={
            "description": "Premium licenses type 1",
            "example": 5
        }
    )
    
    premium_licenses_2 = fields.Int(
        metadata={
            "description": "Premium licenses type 2",
            "example": 3
        }
    )
    
    mfa = fields.Bool(
        metadata={
            "description": "Enable/Disable Multi-Factor Authentication",
            "example": True
        }
    )
    
    companies = fields.List(
        fields.Int(),
        required=False,
        allow_none=True,
        metadata={
            "description": "Optional array of company IDs to assign to user (only for USER role). If provided, will update company assignments.",
            "example": [1, 2, 3]
        }
    )


class ChangePasswordSchema(Schema):
    """Schema for changing user password"""
    
    current_password = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Current password is required"),
        metadata={
            "description": "Current password",
            "example": "CurrentPass@123"
        }
    )
    
    new_password = fields.Str(
        required=True,
        validate=[
            validate.Length(min=8, max=128, error="New password must be between 8 and 128 characters"),
            validate.Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                error="New password must contain at least one lowercase letter, one uppercase letter, one number, and one special character"
            )
        ],
        metadata={
            "description": "New password",
            "example": "NewPassword@123"
        }
    )


class UsersListResponseSchema(Schema):
    """Schema for users list response"""
    
    users = fields.List(fields.Nested(UserResponseSchema))
    total = fields.Int(metadata={"description": "Total number of users", "example": 25})
    page = fields.Int(metadata={"description": "Current page number", "example": 1})
    per_page = fields.Int(metadata={"description": "Number of users per page", "example": 10})
    total_pages = fields.Int(metadata={"description": "Total number of pages", "example": 3})