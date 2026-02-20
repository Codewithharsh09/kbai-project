from flask import request, current_app
from flask_restx import Resource
from src.app.api.v1.swaggers import (
    company_import_ns,
    import_company_request_model,
    import_company_response_model
)
from src.app.api.v1.services.common.company_import_service import CompanyImportService
from src.common.response_utils import (
    success_response,
    error_response,
    internal_error_response
)
from src.common.localization import get_message
from src.app.api.middleware import require_auth0, get_current_user

@company_import_ns.route('/<string:vat>')
class CompanyImportResource(Resource):
    @company_import_ns.expect(import_company_request_model)
    @company_import_ns.response(200, 'Company imported successfully', import_company_response_model)
    @company_import_ns.response(400, 'Bad Request')
    @company_import_ns.response(500, 'Internal Server Error')
    @require_auth0
    def get(self,vat):
        """
        Lookup company information by VAT number.
        
        This endpoint checks the database and CreditSafe for company details.
        It returns the found data to pre-fill the frontend form.
        It does NOT create the company in the database.
        
        If not found, it returns a 'not_found' status so the frontend can enable manual entry.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            current_user = get_current_user() # Kept for auth validation but not used in lookup
            vat = str(vat).strip()
            if not vat:
                return error_response(
                    message=get_message('missing_data', locale),
                    data={"error": "VAT number is required"},
                    status_code=400
                )

            # Call lookup service
            result, error = CompanyImportService.import_by_vat(vat=vat, locale=locale)

            if error:
                return error_response(
                    message=f"{get_message('lookup_failed', locale)}: {error}",
                    status_code=400
                )

            status_code = 200
            
            # Check if company was not found
            if result.get('status') == 'not_found':
                return error_response(
                    message=result.get('message'),
                    status_code=404
                )
                
            message = result.get('message', get_message('company_data_retrieved', locale))

            return success_response(
                message=message,
                data=result,
                status_code=status_code
            )

        except Exception as e:
            current_app.logger.error(f"API Company Import error: {str(e)}")
            return internal_error_response(
                message=get_message("lookup_error", locale),
                error_details=str(e)
            )
