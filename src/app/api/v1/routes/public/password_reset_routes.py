"""
Password Reset Routes
Handles secure password reset with email-based reset links
"""

import threading
from flask import request, current_app
from flask_restx import Resource
from marshmallow import ValidationError

from src.app.api.v1.services import password_reset_service
from src.common.response_utils import (
    success_response, error_response, validation_error_response,
    unauthorized_response, internal_error_response, not_found_response
)
from src.app.api.schemas.public.password_reset_schemas import (
    RequestPasswordResetSchema,
    ResetPasswordSchema
)
from src.app.api.v1.swaggers import (
    password_reset_ns,
    request_password_reset_model,
    reset_password_model
)


# -----------------------------------------------------------------------------
# Background Password Reset Email Sender
# -----------------------------------------------------------------------------
def send_password_reset_email_background(app, user_email, ip_address=None):
    """
    Send password reset email in background thread with Flask app context
    
    Args:
        app: Flask app instance
        user_email: User's email address
        ip_address: Client IP for rate limiting
    """
    def _send_reset_email(application, email, ip):
        with application.app_context():
            try:
                response_data, status_code = password_reset_service.request_password_reset(
                    email=email,
                    ip_address=ip
                )
                
                if status_code == 200:
                    current_app.logger.info(f"Password reset email sent successfully to {email} (background)")
                else:
                    current_app.logger.warning(f"Failed to send password reset email to {email} (background): {response_data}")
            except Exception as e:
                current_app.logger.error(f"Password reset email error for {email} (background): {str(e)}")
    
    # Start background thread
    reset_thread = threading.Thread(target=_send_reset_email, args=(app, user_email, ip_address))
    reset_thread.daemon = True
    reset_thread.start()


# -----------------------------------------------------------------------------
# Request Password Reset
# -----------------------------------------------------------------------------
@password_reset_ns.route('/request')
class RequestPasswordReset(Resource):
    @password_reset_ns.doc('request_password_reset')
    @password_reset_ns.expect(request_password_reset_model)
    def post(self):
        """
        Request password reset for an email.
        
        Sends a secure, time-limited reset link to the user's email.
        Always returns success message (security best practice).
        Response is immediate - email sending happens in background.
        """
        try:
            # Validate input data
            schema = RequestPasswordResetSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                # Normalize message so tests can assert on 'invalid' wording
                return validation_error_response(
                    validation_errors=err.messages,
                    message="If this email is registered, you will receive a reset link shortly."
                )

            email = validated_data.get('email')
            
            # Get client IP for security tracking
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))

            # Quick user existence check (optional - for early validation)
            # from src.app.database.models import TbUser
            # user = TbUser.query.filter_by(email=email).first()
            
            # Send password reset email in background (non-blocking)
            send_password_reset_email_background(
                app=current_app._get_current_object(),
                user_email=email,
                ip_address=ip_address
            )
            
            # Return immediate success response (security: don't reveal if email exists)
            return success_response(
                message="If this email is registered, you will receive a reset link shortly.",
                data={
                    'email': email,
                    'success': True,
                    'note': 'Please check your email for the reset link.'
                }
            )

        except Exception as e:
            current_app.logger.error(f"Password reset request error: {str(e)}")
            return internal_error_response(
                message="Password reset request failed",
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# Reset Password
# -----------------------------------------------------------------------------
@password_reset_ns.route('/reset')
class ResetPassword(Resource):
    @password_reset_ns.doc('reset_password')
    @password_reset_ns.expect(reset_password_model)
    def post(self):
        """
        Reset password using valid token.
        
        Resets the user's password and invalidates the token.
        User must log in again after successful reset.
        """
        try:
            # Validate input data
            schema = ResetPasswordSchema()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return validation_error_response(
                    validation_errors=err.messages,
                    message="Input validation failed: invalid token"
                )

            token = validated_data.get('token')
            new_password = validated_data.get('new_password')

            # Reset password
            response_data, status_code = password_reset_service.reset_password(token, new_password)

            if status_code == 200:
                return success_response(
                    message=response_data.get('message', 'Password reset successfully'),
                    data=response_data
                )
            else:
                return error_response(
                    message=response_data.get('message', 'Password reset failed'),
                    data=response_data,
                    status_code=status_code
                )

        except Exception as e:
            current_app.logger.error(f"Password reset error: {str(e)}")
            return internal_error_response(
                message="Password reset failed",
                error_details=str(e)
            )


# -----------------------------------------------------------------------------
# Cleanup Expired Tokens (Admin)
# -----------------------------------------------------------------------------
@password_reset_ns.route('/cleanup')
class CleanupExpiredTokens(Resource):
    @password_reset_ns.doc('cleanup_expired_tokens')
    def post(self):
        """
        Clean up expired password reset tokens (Admin only).
        
        Removes all expired reset tokens from database.
        This endpoint should be called periodically for maintenance.
        """
        try:
            # TODO: Add admin authentication check
            # For now, allow any request for maintenance
            
            # Clean up expired tokens
            cleaned_count = password_reset_service.cleanup_expired_tokens()

            return success_response(
                message=f"Cleaned up {cleaned_count} expired password reset tokens",
                data={"cleaned_count": cleaned_count}
            )

        except Exception as e:
            current_app.logger.error(f"Token cleanup error: {str(e)}")
            return internal_error_response(
                message="Failed to cleanup tokens",
                error_details=str(e)
            )
