"""
KBAI Companies Marshmallow Schemas

Handles validation for KBAI companies CRUD operations.
All validation happens here before reaching the model layer.
"""

from marshmallow import Schema, fields, validate


class CreateCompanySchema(Schema):
    """
    Schema for creating a new KBAI company
    Note: id_licence is auto-selected from admin's available licenses
    """
    company_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={
            'required': 'Company name is required',
            'invalid': 'Company name must be between 1 and 255 characters'
        }
    )
    
    vat = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'VAT must be maximum 50 characters'
        }
    )
    
    fiscal_code = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'Fiscal code must be maximum 50 characters'
        }
    )
    
    sdi = fields.String(
        required=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'SDI must be maximum 50 characters'
        }
    )
    
    logo = fields.String(
        allow_none=True,
        validate=validate.Length(max=1000),
        error_messages={
            'invalid': 'Logo URL must be maximum 1000 characters'
        }
    )
    
    contact_person = fields.String(
        required=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Contact person name must be maximum 255 characters'
        }
    )
    
    phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'Phone number must be maximum 50 characters'
        }
    )
    
    email = fields.Email(
        required=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Email must be a valid email address and maximum 255 characters'
        }
    )
    
    website = fields.String(
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Website URL must be maximum 255 characters'
        }
    )
    
    status_flag = fields.String(
        allow_none=True,
        validate=validate.OneOf(['ACTIVE', 'INACTIVE', 'SUSPENDED']),
        error_messages={
            'invalid': 'Status must be one of: ACTIVE, INACTIVE, SUSPENDED'
        }
    )
    
    # Timestamp fields (read-only for create)
    created_at = fields.DateTime(dump_only=True, allow_none=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)
    
    # Soft delete fields (read-only for create)
    is_deleted = fields.Boolean(dump_only=True, allow_none=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class UpdateCompanySchema(Schema):
    """
    Schema for updating an existing KBAI company
    Note: id_licence cannot be updated after company creation
    """
    company_name = fields.String(
        allow_none=True,
        validate=validate.Length(min=1, max=255),
        error_messages={
            'invalid': 'Company name must be between 1 and 255 characters'
        }
    )
    
    vat = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'VAT must be maximum 50 characters'
        }
    )
    
    fiscal_code = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'Fiscal code must be maximum 50 characters'
        }
    )
    
    sdi = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'SDI must be maximum 50 characters'
        }
    )
    
    logo = fields.String(
        allow_none=True,
        validate=validate.Length(max=1000),
        error_messages={
            'invalid': 'Logo URL must be maximum 1000 characters'
        }
    )
    
    contact_person = fields.String(
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Contact person name must be maximum 255 characters'
        }
    )
    
    phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'Phone number must be maximum 50 characters'
        }
    )
    
    email = fields.Email(
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Email must be a valid email address and maximum 255 characters'
        }
    )
    
    website = fields.String(
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            'invalid': 'Website URL must be maximum 255 characters'
        }
    )
    
    status_flag = fields.String(
        allow_none=True,
        validate=validate.OneOf(['ACTIVE', 'INACTIVE', 'SUSPENDED']),
        error_messages={
            'invalid': 'Status must be one of: ACTIVE, INACTIVE, SUSPENDED'
        }
    )
    
    # Timestamp fields (read-only for update)
    created_at = fields.DateTime(dump_only=True, allow_none=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)
    
    # Soft delete fields (read-only for update)
    is_deleted = fields.Boolean(dump_only=True, allow_none=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class CompanyResponseSchema(Schema):
    """
    Schema for company response data
    """
    id_company = fields.Integer()
    id_licence = fields.Integer()
    company_name = fields.String()
    vat = fields.String(allow_none=True)
    fiscal_code = fields.String(allow_none=True)
    sdi = fields.String(allow_none=True)
    logo = fields.String(allow_none=True)
    contact_person = fields.String(allow_none=True)
    phone = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    website = fields.String(allow_none=True)
    status_flag = fields.String(allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    is_deleted = fields.Boolean(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


# Create schema instances
create_company_schema = CreateCompanySchema()
update_company_schema = UpdateCompanySchema()
company_response_schema = CompanyResponseSchema()
