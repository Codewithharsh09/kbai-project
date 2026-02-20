"""
KBAI Companies Tab Swagger Documentation

Contains all KBAI companies related API documentation including:
- Company creation (auto-select license)
- Company retrieval by ID
- Company updates (license cannot be changed)
- Company deletion
- Get companies by user ID (role-based access)
"""

from flask_restx import Namespace, fields

# Create KBAI Companies Namespace
kbai_companies_ns = Namespace('companies', description='KBAI Companies CRUD operations')

# Company Models
create_company_model = kbai_companies_ns.model('CreateCompany', {
    'company_name': fields.String(required=True, description='Company name (license auto-selected from available licenses)'),
    'vat': fields.String(description='VAT number'),
    'fiscal_code': fields.String(description='Fiscal code'),
    'sdi': fields.String(description='SDI code'),
    'logo': fields.String(description='Logo URL or file path'),
    'contact_person': fields.String(description='Contact person name'),
    'phone': fields.String(description='Phone number'),
    'email': fields.String(description='Email address'),
    'website': fields.String(description='Website URL'),
    'status_flag': fields.String(description='Status flag (default: ACTIVE)', enum=['ACTIVE', 'INACTIVE', 'SUSPENDED'])
})

update_company_model = kbai_companies_ns.model('UpdateCompany', {
    'company_name': fields.String(description='Company name'),
    'vat': fields.String(description='VAT number'),
    'fiscal_code': fields.String(description='Fiscal code'),
    'sdi': fields.String(description='SDI code'),
    'logo': fields.String(description='Logo URL or file path'),
    'contact_person': fields.String(description='Contact person name'),
    'phone': fields.String(description='Phone number'),
    'email': fields.String(description='Email address'),
    'website': fields.String(description='Website URL'),
    'status_flag': fields.String(description='Status flag', enum=['ACTIVE', 'INACTIVE', 'SUSPENDED'])
})

# Response Models
company_model = kbai_companies_ns.model('Company', {
    'id_company': fields.Integer(description='Company ID'),
    'id_licence': fields.Integer(description='Licence ID'),
    'company_name': fields.String(description='Company name'),
    'vat': fields.String(description='VAT number'),
    'fiscal_code': fields.String(description='Fiscal code'),
    'sdi': fields.String(description='SDI code'),
    'logo': fields.String(description='Logo URL or file path'),
    'contact_person': fields.String(description='Contact person name'),
    'phone': fields.String(description='Phone number'),
    'email': fields.String(description='Email address'),
    'website': fields.String(description='Website URL'),
    'status_flag': fields.String(description='Status flag'),
})

company_response_model = kbai_companies_ns.model('CompanyResponse', {
    'message': fields.String(description='Response message'),
    'data': fields.Nested(company_model, description='Company data'),
    'success': fields.Boolean(description='Operation success status')
})

companies_list_response_model = kbai_companies_ns.model('CompaniesListResponse', {
    'message': fields.String(description='Response message'),
    'data': fields.List(fields.Nested(company_model), description='List of companies'),
    'pagination': fields.Raw(description='Pagination information', example={
        'page': 1,
        'per_page': 10,
        'total': 100,
        'pages': 10
    }),
    'success': fields.Boolean(description='Operation success status')
})

# User Companies Response Model (for GET /user/{tb_user_id})
user_companies_response_model = kbai_companies_ns.model('UserCompaniesResponse', {
    'message': fields.String(description='Response message'),
    'data': fields.List(fields.Nested(company_model), description='List of companies assigned to user'),
    'pagination': fields.Raw(description='Pagination information', example={
        'page': 1,
        'per_page': 10,
        'total': 5,
        'pages': 1
    }),
    'success': fields.Boolean(description='Operation success status')
})

# Error Response Models
validation_error_model = kbai_companies_ns.model('ValidationError', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message'),
    'details': fields.Raw(description='Validation error details')
})

not_found_error_model = kbai_companies_ns.model('NotFoundError', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message')
})

internal_error_model = kbai_companies_ns.model('InternalError', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message')
})

success_message_model = kbai_companies_ns.model('SuccessMessage', {
    'message': fields.String(description='Success message'),
    'success': fields.Boolean(description='Operation success status')
})

# Example Responses
EXAMPLE_COMPANY_CREATED = {
    "message": "Company created successfully",
    "company": {
        "id_company": 1,
        "id_licence": 123,  # Auto-selected from available licenses
        "company_name": "Example Corp",
        "vat": "IT12345678901",
        "fiscal_code": "EXMPLR80A01H501U",
        "sdi": "ABC123",
        "logo": "https://example.com/logo.png",
        "contact_person": "John Doe",
        "phone": "+39 123 456 7890",
        "email": "info@example.com",
        "website": "https://example.com",
        "status_flag": "ACTIVE",
        "time": "2023-12-01T15:30:00Z"
    },
    "success": True
}

EXAMPLE_COMPANY_RETRIEVED = {
    "message": "Company retrieved successfully",
    "company": {
        "id_company": 1,
        "id_licence": 123,
        "company_name": "Example Corp",
        "vat": "IT12345678901",
        "fiscal_code": "EXMPLR80A01H501U",
        "sdi": "ABC123",
        "logo": "https://example.com/logo.png",
        "contact_person": "John Doe",
        "phone": "+39 123 456 7890",
        "email": "info@example.com",
        "website": "https://example.com",
        "status_flag": "ACTIVE",
        "time": "2023-12-01T15:30:00Z"
    },
    "success": True
}

EXAMPLE_COMPANIES_LIST = {
    "message": "Companies retrieved successfully",
    "companies": [
        {
            "id_company": 1,
            "id_licence": 123,
            "company_name": "Example Corp",
            "vat": "IT12345678901",
            "fiscal_code": "EXMPLR80A01H501U",
            "sdi": "ABC123",
            "logo": "https://example.com/logo.png",
            "contact_person": "John Doe",
            "phone": "+39 123 456 7890",
            "email": "info@example.com",
            "website": "https://example.com",
            "status_flag": "ACTIVE",
            "time": "2023-12-01T15:30:00Z"
        },
        {
            "id_company": 2,
            "id_licence": 124,
            "company_name": "Another Corp",
            "vat": "IT98765432109",
            "fiscal_code": "NTHR80A01H501V",
            "sdi": "XYZ789",
            "logo": None,
            "contact_person": "Jane Smith",
            "phone": "+39 987 654 3210",
            "email": "contact@another.com",
            "website": "https://another.com",
            "status_flag": "ACTIVE",
            "time": "2023-12-01T16:00:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 10,
        "total": 2,
        "pages": 1
    },
    "success": True
}

EXAMPLE_COMPANY_UPDATED = {
    "message": "Company updated successfully",
    "company": {
        "id_company": 1,
        "id_licence": 123,
        "company_name": "Updated Corp",
        "vat": "IT12345678901",
        "fiscal_code": "EXMPLR80A01H501U",
        "sdi": "ABC123",
        "logo": "https://example.com/new-logo.png",
        "contact_person": "John Updated",
        "phone": "+39 123 456 7890",
        "email": "updated@example.com",
        "website": "https://updated.com",
        "status_flag": "ACTIVE",
        "time": "2023-12-01T15:30:00Z"
    },
    "success": True
}

EXAMPLE_COMPANY_DELETED = {
    "message": "Company deleted successfully",
    "success": True
}

EXAMPLE_VALIDATION_ERROR = {
    "error": "Validation error",
    "message": "company_name is required",
    "details": {
        "company_name": ["This field is required"]
    }
}

EXAMPLE_NO_LICENSE_ERROR = {
    "error": "No licenses available",
    "message": "You do not have any available licenses to create a company. All your licenses are currently in use.",
    "license_stats": {
        "total_licenses": 5,
        "used_by_companies": 5,
        "available": 0
    }
}

EXAMPLE_USER_COMPANIES_LIST = {
    "message": "Companies for user 123 retrieved successfully",
    "data": [
        {
            "id_company": 1,
            "id_licence": 123,
            "company_name": "User's Company 1",
            "vat": "IT12345678901",
            "fiscal_code": "EXMPLR80A01H501U",
            "sdi": "ABC123",
            "logo": "https://example.com/logo.png",
            "contact_person": "John Doe",
            "phone": "+39 123 456 7890",
            "email": "info@example.com",
            "website": "https://example.com",
            "status_flag": "ACTIVE",
            "created_at": "2023-12-01T15:30:00Z"
        },
        {
            "id_company": 2,
            "id_licence": 124,
            "company_name": "User's Company 2",
            "vat": "IT98765432109",
            "status_flag": "ACTIVE",
            "created_at": "2023-12-02T10:00:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 10,
        "total": 2,
        "pages": 1
    },
    "success": True
}

EXAMPLE_PERMISSION_DENIED_USER_COMPANIES = {
    "error": "Permission denied. Admins can only access their own companies.",
    "data": {
        "current_user_id": 5,
        "requested_user_id": 10,
        "reason": "Admin cannot access other users' companies"
    }
}

# Dropdown Response Model (simple list)
company_dropdown_model = kbai_companies_ns.model('CompanyDropdown', {
    'id_company': fields.Integer(description='Company ID'),
    'company_name': fields.String(description='Company name')
})

companies_dropdown_response_model = kbai_companies_ns.model('CompaniesDropdownResponse', {
    'message': fields.String(description='Response message'),
    'data': fields.List(fields.Nested(company_dropdown_model), description='Simple list of companies for dropdown'),
    'success': fields.Boolean(description='Operation success status')
})

EXAMPLE_COMPANIES_DROPDOWN = {
    "message": "Companies list retrieved successfully",
    "data": [
        {"id_company": 1, "company_name": "ABC Corp"},
        {"id_company": 5, "company_name": "Tech Solutions"},
        {"id_company": 10, "company_name": "XYZ Industries"}
    ],
    "success": True
}
