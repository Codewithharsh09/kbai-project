from flask_restx import Namespace, fields

# Namespace definition
company_import_ns = Namespace('kbai/import', description='Company Import operations from CreditSafe')

# Request models
# Request models
import_company_request_model = company_import_ns.model('ImportCompanyRequest', {
    'vat': fields.String(required=False, description='VAT number (optional if manually creating)', example='03004880872'),
    'company_name': fields.String(description='Company Name (required for manual creation)'),
    'region': fields.String(description='Region'),
    'ateco': fields.String(description='ATECO Code'),
    'fiscal_code': fields.String(description='Fiscal Code'),
    'phone': fields.String(description='Phone'),
    'email': fields.String(description='Email'),
    'website': fields.String(description='Website'),
    'contact_person': fields.String(description='Contact Person'),
    'address': fields.String(description='Address'),
    'city': fields.String(description='City'),
    'country': fields.String(description='Country'),
    'postal_code': fields.String(description='Postal Code'),
    'is_competitor': fields.Boolean(description='Import as a competitor (true/false)', default=False),
})

# Response models
company_data_model = company_import_ns.model('CompanyData', {
    'company_name': fields.String(description='Name of the company'),
    'vat': fields.String(description='VAT number'),
    'fiscal_code': fields.String(description='Fiscal code'),
    'phone': fields.String(description='Phone number'),
    'email': fields.String(description='Email address'),
    'region': fields.String(description='Region name'),
    'address': fields.String(description='Address'),
    'city': fields.String(description='City'),
    'country': fields.String(description='Country'),
    'postal_code': fields.String(description='Postal code'),
    'ateco': fields.String(description='ATECO code'),
    'website': fields.String(description='Website URL'),
    'contact_person': fields.String(description='Contact Person'),
    'sdi': fields.String(description='SDI Code')
})

import_company_response_model = company_import_ns.model('ImportCompanyResponse', {
    'source': fields.String(description='Source of data (database/creditsafe/null)'),
    'status': fields.String(description='Operation status (found/not_found/skipped)'),
    'message': fields.String(description='Status message'),
    'id_company': fields.Integer(description='ID of the company (if source is database)'),
    'company_data': fields.Nested(company_data_model, description='Company details for form pre-filling')
})
