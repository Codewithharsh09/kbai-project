"""
OTP Routes for 2-Step Verification
Handles OTP generation and verification
"""

import threading
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource
from marshmallow import ValidationError

from src.app.api.v1.services import otp_service
from src.common.response_utils import (
    success_response, error_response, validation_error_response,
    internal_error_response, not_found_response
)
from src.common.localization import get_message
from src.app.api.schemas.public.otp_schemas import (
    CreateOtpSchema,
    VerifyOtpSchema
)
from src.app.api.v1.swaggers import (
    otp_ns,
    create_otp_model,
    verify_otp_model
)


# -----------------------------------------------------------------------------
# Background OTP Sender - Common Helper Function
# -----------------------------------------------------------------------------
def send_otp_in_background(app, user_email, user_name=None):
    """
    Send OTP in background thread with Flask app context
    
    Args:
        app: Flask app instance
        user_email: User's email address
        user_name: User's name (optional)
    """
    def _send_otp(application, email, name):
        with application.app_context():
            try:
                response_data, status_code = otp_service.create_otp(email, name)
                
                if status_code == 200:
                    current_app.logger.info(f"OTP sent successfully to {email} (background)")
                else:
                    current_app.logger.warning(f"Failed to send OTP to {email} (background): {response_data}")
            except Exception as e:
                current_app.logger.error(f"OTP sending error for {email} (background): {str(e)}")
    
    # Start background thread
    otp_thread = threading.Thread(target=_send_otp, args=(app, user_email, user_name))
    otp_thread.daemon = True
    otp_thread.start()


# -----------------------------------------------------------------------------
# OTP Generation
# -----------------------------------------------------------------------------
@otp_ns.route('/create')
class CreateOtp(Resource):
    @otp_ns.doc('create_otp')
    @otp_ns.expect(create_otp_model)
    def post(self):
        """
        Create and send OTP for 2-step verification.
        Sends 6-digit OTP to user's email with 10-minute expiry.
        Response is immediate - OTP sending happens in background.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Validate input data
            schema = CreateOtpSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return validation_error_response(
                    validation_errors=err.messages,
                    message=get_message('input_validation_failed', locale)
                )

            email = validated_data.get('email')

            # Validate user exists and is active (quick check)
            from src.app.database.models import TbUser
            user = TbUser.query.filter_by(email=email).first()
            
            if user and user.status != 'ACTIVE':
                return error_response(
                    message=get_message('account_inactive', locale),
                    data={'error': 'Account inactive'},
                    status_code=403
                )

            # Send OTP in background thread (non-blocking)
            send_otp_in_background(
                app=current_app._get_current_object(),
                user_email=email,
                user_name=user.name if user else None
            )
            
            # Return immediate success response
            return success_response(
                message=get_message('otp_sending', locale),
                data={
                    'email': email,
                    'expires_in_minutes': 10,
                    'success': True,
                    'note': get_message('otp_check_email', locale)
                }
            )

        except Exception as e:
            current_app.logger.error(f"Create OTP error: {str(e)}")
            return internal_error_response(
                message=get_message('otp_create_failed', locale),
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# OTP Verification (2-Step Verification)
# -----------------------------------------------------------------------------
@otp_ns.route('/verify')
class VerifyOtp(Resource):
    @otp_ns.doc('verify_otp')
    @otp_ns.expect(verify_otp_model)
    def post(self):
        """
        Verify OTP and complete 2-step verification.
        Returns user data and creates JWT token for session.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Validate input data
            schema = VerifyOtpSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return validation_error_response(
                    validation_errors=err.messages,
                    message=get_message('input_validation_failed', locale)
                )

            email = validated_data.get('email')
            otp = validated_data.get('otp')

            # Verify OTP
            response_data, status_code = otp_service.verify_otp(email, otp)

            # If verification successful, create JWT token
            if status_code == 200 and response_data.get('success'):
                user = response_data.get('user')

                # Create standardized response with cookie
                return success_response(
                    message=get_message('otp_verified', locale),
                    data={
                        "user": user,
                        "two_factor_verified": True,
                        "development_mode": response_data.get('development_mode', False)
                    },
                    set_cookie={
                        'key': 'auth_token',
                        'httponly': True,
                        'secure': current_app.config.get('SESSION_COOKIE_SECURE', False),
                        'samesite': 'Lax',
                        'max_age': 60*60*24*7,  # 7 days
                        'path': '/'
                    }
                )

            # Handle error cases
            if status_code == 400:
                return error_response(
                    message=get_message('otp_invalid', locale),
                    data=response_data,
                    status_code=400
                )
            elif status_code == 404:
                # Security: Normalize 404 (User not found) to 400 to prevent user enumeration attacks
                # Don't reveal to client whether email exists or OTP is invalid - return same error format
                return error_response(
                    message=get_message('otp_invalid_expired', locale),
                    data={
                        'error': get_message('otp_invalid', locale),
                        'message': get_message('otp_invalid_expired', locale)
                    },
                    status_code=400
                )
            else:
                return error_response(
                    message=get_message('otp_verify_failed', locale),
                    data=response_data,
                    status_code=status_code
                )

        except Exception as e:
            current_app.logger.error(f"Verify OTP error: {str(e)}")
            return internal_error_response(
                message=get_message('otp_verify_failed', locale),
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# OTP Cleanup (Admin endpoint)
# -----------------------------------------------------------------------------
@otp_ns.route('/cleanup')
class OtpCleanup(Resource):
    @otp_ns.doc('cleanup_expired_otps')
    @jwt_required()
    def post(self):
        """
        Clean up expired OTPs (Admin only).
        Removes all expired OTP records from database.
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Get current user
            current_user_id = get_jwt_identity()
            
            # TODO: Add admin permission check
            # For now, allow any authenticated user
            
            # Clean up expired OTPs
            cleaned_count = otp_service.cleanup_expired_otps()

            return success_response(
                message=get_message('otp_cleanup_success', locale, count=cleaned_count),
                data={
                    'cleaned_count': cleaned_count,
                    'success': True
                }
            )

        except Exception as e:
            current_app.logger.error(f"OTP cleanup error: {str(e)}")
            return internal_error_response(
                message=get_message('otp_cleanup_failed', locale),
                error_details=str(e)
            )
