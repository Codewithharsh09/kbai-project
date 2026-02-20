"""
API routes for KBAI Predictive Engine.
"""

from flask import request, jsonify, current_app
from flask_restx import Resource, Namespace

from src.app.services.kbai.predictive.predictive_service import PredictiveService
from src.app.api.middleware import require_auth0, get_current_user
from src.app.api.v1.services import kbai_companies_service
from src.common.response_utils import (
    success_response,
    error_response,
    validation_error_response,
    internal_error_response,
    unauthorized_response,
)
from src.common.localization import get_message

# Create namespace
predictive_ns = Namespace("predictive", description="KBAI Predictive Engine operations")


@predictive_ns.route("/<int:company_id>/generate")
class PredictiveGenerateResource(Resource):
    """Resource to generate financial predictions"""

    @predictive_ns.doc("generate_prediction")
    @predictive_ns.param("horizon", "Number of years to project (default: 3)")
    @require_auth0
    def get(self, company_id):
        """
        Generate financial prediction for a company.

        This endpoint triggers the predictive engine to calculate
        future balance sheets based on historical data.

        Permissions:
        - superadmin/staff: Can generate for ANY company
        - admin/user: Can ONLY generate for their own companies

        Returns:
            JSON object containing the prediction scenarios (Base, Optimistic, Pessimistic).
        """
        locale = request.headers.get("Accept-Language", "en")

        try:
            # 1. Authorization Check
            current_user = get_current_user()

            # Check company permissions using the existing service helper

            # Fetch Company
            from src.app.database.models import KbaiCompany

            company = KbaiCompany.findOne(
                id_company=company_id, is_deleted=False, is_competitor=False
            )

            if not company:
                return error_response(
                    message=get_message("company_not_found", locale), status_code=404
                )

            has_permission, error_msg = kbai_companies_service.check_company_permission(
                current_user=current_user,
                company=company,
                action="view",  # Generating a forecast is viewing/analyzing data
            )

            if not has_permission:
                return error_response(
                    message=get_message("permission_denied", locale),
                    data={"reason": error_msg},
                    status_code=403,
                )

            # 2. Parse Input
            horizon = request.args.get("horizon", 3, type=int)

            # 3. Call Service
            result = PredictiveService.generate_prediction(
                company_id, horizon, locale=locale
            )

            if result["status"] == "error":
                return error_response(message=result["message"], status_code=400)

            return success_response(
                message=get_message("pred_prediction_success", locale),
                data=result["data"],
            )

        except Exception as e:
            current_app.logger.error(f"Prediction API error: {str(e)}")
            return internal_error_response(
                message=get_message("default_error", locale), error_details=str(e)
            )
