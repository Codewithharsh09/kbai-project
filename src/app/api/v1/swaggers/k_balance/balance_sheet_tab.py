"""
KBAI Balance Sheet Tab Swagger Documentation

Contains all KBAI balance sheet upload related API documentation including:
- Balance sheet file upload (PDF, XLSX, XBRL/XML)
- File extraction and data processing
- Balance data storage in JSONB format
"""

from flask_restx import Namespace, fields
from werkzeug.datastructures import FileStorage

# Create KBAI Balance Sheet Namespace
balance_sheet_ns = Namespace(
    'kbai-balance',
    description='KBAI Balance Sheet upload operations',
    path='/api/v1/kbai-balance'
)

# =============================================================================
# REQUEST MODELS
# =============================================================================

# Request parser for file upload
upload_parser = balance_sheet_ns.parser()
upload_parser.add_argument(
    'file',
    type=FileStorage,
    location='files',
    required=True,
    help='Balance sheet file to upload. Supported formats: PDF, XLSX, XBRL, XML'
)
upload_parser.add_argument(
    'year',
    type=int,
    location='form',
    required=True,
    help='Balance year (e.g., 2024)'
)
upload_parser.add_argument(
    'month',
    type=int,
    location='form',
    required=True,
    help='Balance month (1-12)'
)
upload_parser.add_argument(
    'type',
    type=str,
    location='form',
    required=True,
    help='Balance type (e.g., final, provisional, forecast)'
)
upload_parser.add_argument(
    'mode',
    type=str,
    location='form',
    required=True,
    help='Upload mode (e.g., manual, pdf, xls)'
)
upload_parser.add_argument(
    'note',
    type=str,
    location='form',
    required=False,
    help='Optional notes'
)
upload_parser.add_argument(
    'overwrite',
    type=str,
    location='form',
    required=False,
    help='Set to true to overwrite an existing balance sheet for the same period'
)

# =============================================================================
# RESPONSE MODELS
# =============================================================================

# Balance Sheet Response Model
balance_sheet_model = balance_sheet_ns.model('BalanceSheet', {
    'id_balance': fields.Integer(
        description='Balance sheet record ID',
        example=1
    ),
    'id_company': fields.Integer(
        description='Company ID',
        example=549
    ),
    'year': fields.Integer(
        description='Balance sheet year',
        example=2024
    ),
    'month': fields.Integer(
        description='Balance sheet month (1-12)',
        example=12
    ),
    'type': fields.String(
        description='Balance sheet type',
        example='pdf'
    ),
    'mode': fields.String(
        description='Balance sheet upload mode',
        example='manual'
    ),
    'file': fields.String(
        description='S3 file URL (if uploaded) for balance sheet',
        example='https://bucket.s3.region.amazonaws.com/balances/file.pdf',
        allow_none=True
    ),
    'note': fields.String(
        description='Optional notes for balance sheet',
        example='Year-end balance sheet',
        allow_none=True
    ),
    'balance': fields.Raw(
        description='Extracted balance sheet data in JSONB format',
        example={
            'Stato_patrimoniale': {
                'Attivo': {
                    'Immobilizzazioni': {}
                },
                'Passivo': {}
            }
        }
    ),
    'created_at': fields.String(
        description='Creation timestamp for balance sheet',
        example='2024-11-05T17:56:33Z'
    ),
    'updated_at': fields.String(
        description='Last update timestamp for balance sheet',
        example='2024-11-05T17:56:33Z'
    ),
    'is_deleted': fields.String(
        description='Deletion flag for balance sheet',
        example='N',
        enum=['N', 'Y']
    ),
    'deleted_at': fields.String(
        description='Deletion timestamp for balance sheet',
        example=None,
        allow_none=True
    )
})

# Balance Sheet Model without balance field (for list)
balance_sheet_list_item_model = balance_sheet_ns.model('BalanceSheetListItem', {
    'id_balance': fields.Integer(
        description='Balance sheet record ID',
        example=1
    ),
    'id_company': fields.Integer(
        description='Company ID',
        example=549
    ),
    'year': fields.Integer(
        description='Balance sheet year',
        example=2024
    ),
    'month': fields.Integer(
        description='Balance sheet month (1-12)',
        example=12
    ),
    'type': fields.String(
        description='Balance sheet type',
        example='pdf'
    ),
    'mode': fields.String(
        description='Balance sheet upload mode',
        example='manual'
    ),
    'file': fields.String(
        description='S3 file URL (if uploaded) for balance sheet',
        example='https://bucket.s3.region.amazonaws.com/balances/file.pdf',
        allow_none=True
    ),
    'note': fields.String(
        description='Optional notes for balance sheet',
        example='Year-end balance sheet',
        allow_none=True
    ),
    'created_at': fields.String(
        description='Creation timestamp for balance sheet',
        example='2024-11-05T17:56:33Z'
    ),
    'updated_at': fields.String(
        description='Last update timestamp for balance sheet',
        example='2024-11-05T17:56:33Z'
    ),
    'is_deleted': fields.String(
        description='Deletion flag for balance sheet',
        example='N',
        enum=['N', 'Y']
    ),
    'deleted_at': fields.String(
        description='Deletion timestamp for balance sheet',
        example=None,
        allow_none=True
    )
    # Note: balance field is intentionally excluded
})

# Success Response Model (with balance field)
balance_sheet_response_model = balance_sheet_ns.model('BalanceSheetResponse', {
    'message': fields.String(
        description='Response message',
        example='Balance sheet uploaded successfully'
    ),
    'data': fields.Raw(
        description='Balance sheet data',
        example={}
    ),
    'success': fields.Boolean(
        description='Operation success status for balance sheet',
        example=True
    )
})

# List Response Model (without balance field)
balance_sheets_list_response_model = balance_sheet_ns.model('BalanceSheetsListResponse', {
    'message': fields.String(
        description='Response message',
        example='Balance sheets retrieved successfully'
    ),
    'data': fields.List(
        fields.Nested(balance_sheet_list_item_model),
        description='List of balance sheets (without balance field)'
    ),
    'pagination': fields.Raw(
        description='Pagination information',
        example={
            'page': 1,
            'per_page': 10,
            'total': 25,
            'pages': 3
        }
    ),
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    )
})

# Error Response Models
validation_error_model = balance_sheet_ns.model('ValidationError', {
    'error': fields.String(
        description='Error type',
        example='Validation error'
    ),
    'message': fields.String(
        description='Error message',
        example='File is required. Only PDF, XLSX, and XBRL/XML files are allowed'
    )
})

extraction_error_model = balance_sheet_ns.model('ExtractionError', {
    'error': fields.String(
        description='Error type',
        example='Extraction error'
    ),
    'message': fields.String(
        description='Error message',
        example='Failed to extract data from PDF: Invalid file format'
    )
})

database_error_model = balance_sheet_ns.model('DatabaseError', {
    'error': fields.String(
        description='Error type',
        example='Database error'
    ),
    'message': fields.String(
        description='Error message',
        example='Failed to save balance record'
    )
})

internal_error_model = balance_sheet_ns.model('InternalError', {
    'error': fields.String(
        description='Error type',
        example='Internal server error'
    ),
    'message': fields.String(
        description='Error message',
        example='Failed to upload balance sheet'
    )
})

not_found_error_model = balance_sheet_ns.model('NotFoundError', {
    'error': fields.String(
        description='Error type',
        example='Not found'
    ),
    'message': fields.String(
        description='Error message',
        example='Balance sheet with ID 1 not found'
    )
})

# =============================================================================
# EXAMPLE RESPONSES
# =============================================================================

EXAMPLE_BALANCE_SHEET_UPLOADED = {
    "message": "Balance uploaded successfully",
    "data": {},
    "success": True
}

EXAMPLE_VALIDATION_ERROR = {
    "error": "Validation error",
    "message": "File is required. Only PDF, XLSX, and XBRL/XML files are allowed"
}

EXAMPLE_EXTRACTION_ERROR = {
    "error": "Extraction error",
    "message": "Failed to extract data from XBRL: Invalid file format"
}

EXAMPLE_DATABASE_ERROR = {
    "error": "Database error",
    "message": "Failed to save balance record"
}

# =============================================================================
# EXPORT ALL MODELS
# =============================================================================

__all__ = [
    'balance_sheet_ns',
    'upload_parser',
    'balance_sheet_model',
    'balance_sheet_list_item_model',
    'balance_sheet_response_model',
    'balance_sheets_list_response_model',
    'validation_error_model',
    'extraction_error_model',
    'database_error_model',
    'internal_error_model',
    'not_found_error_model',
    'EXAMPLE_BALANCE_SHEET_UPLOADED',
    'EXAMPLE_VALIDATION_ERROR',
    'EXAMPLE_EXTRACTION_ERROR',
    'EXAMPLE_DATABASE_ERROR'
]

