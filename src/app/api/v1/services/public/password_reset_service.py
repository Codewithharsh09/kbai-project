"""
Password Reset Service
Handles secure password reset with time-limited, single-use tokens
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from flask import current_app
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from src.extensions import db
from src.app.database.models import TbOtp, TbUser
from ..common.email import EmailService
from flask import request
from src.common.localization import get_message


class PasswordResetService:
    """Service for handling password reset operations"""
    
    def __init__(self):
        self.token_expiry_minutes = 30  # 30 minutes expiry
        self.max_attempts_per_hour = 3  # Max 3 attempts per hour per email
        self.max_attempts_per_ip = 5    # Max 5 attempts per hour per IP
    
    # -------------------------------------------------------------------------
    # Request for forgot password
    # -------------------------------------------------------------------------
    def request_password_reset(self, email: str, ip_address: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Request password reset for an email
        
        Args:
            email: User's email address
            ip_address: Client IP address for security tracking
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Check rate limiting
            rate_limit_check = self._check_rate_limits(email, ip_address)
            locale = request.headers.get('Accept-Language', 'en')
            if not rate_limit_check['allowed']:
                return {
                    'error': get_message('rate_limit_exceeded', locale),
                    'message': rate_limit_check['message'],
                    'retry_after': rate_limit_check['retry_after']
                }, 429
            
            # Check if user exists (without revealing existence)
            user = TbUser.query.filter_by(email=email, status='ACTIVE').first()
            
            # Always return success message (security best practice)
            # Don't reveal whether email exists or not
            response_message = get_message('password_reset_request_success', locale)
            
            # Only proceed if user exists
            if not user:
                return {
                    'message': response_message,
                    'success': True
                }, 200
            
            # Invalidate any existing reset tokens for this email
            self._invalidate_existing_tokens(email)
            
            # Generate secure token
            token = TbOtp.generate_secure_token()
            token_hash = TbOtp.hash_token(token)
            
            # Create reset record
            reset_record = TbOtp(
                email=email,
                token_hash=token_hash,
                expires_in_minutes=self.token_expiry_minutes
            )
            
            db.session.add(reset_record)
            db.session.commit()
            
            # Send reset email using email service
            email_service = EmailService()
            email_sent = email_service.send_password_reset_email(user, token)
            
            # if not email_sent:
            #     # If email fails, clean up the token
            #     db.session.delete(reset_record)
            #     db.session.commit()
                
            #     return {
            #         'error': 'Failed to send reset email',
            #         'message': 'Please try again later'
            #     }, 500
            
            # Log the request
            current_app.logger.info(f"Password reset requested for email: {email}")
            
            return {
                'message': response_message,
                'success': True
            }, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in password reset request: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('database_error', locale),
                'message': get_message('generic_error_message', locale)
            }, 500
            
        except Exception as e:
            current_app.logger.error(f"Password reset request error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('password_reset_request_failed', locale),
                'message': get_message('generic_error_message', locale)
            }, 500
    
    def verify_reset_token(self, token: str) -> Tuple[Dict[str, Any], int]:
        """
        Verify password reset token
        
        Args:
            token: Reset token to verify
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            token_hash = TbOtp.hash_token(token)
            
            # Find the reset record
            reset_record = TbOtp.get_valid_token(token_hash)
            locale = request.headers.get('Accept-Language', 'en')
            
            if not reset_record:
                return {
                    'error': get_message('invalid_reset_token', locale),
                    'message': get_message('token_invalid_expired', locale)
                }, 400
            
            # Check if token is valid
            if not reset_record.is_valid():
                if reset_record.is_expired():
                    return {
                        'error': 'Token expired',
                        'message': 'The reset link has expired. Please request a new one.'
                    }, 400
                elif reset_record.is_used:
                    return {
                        'error': 'Token already used',
                        'message': 'This reset link has already been used. Please request a new one.'
                    }, 400
            
            # Get user details
            user = TbUser.query.filter_by(email=reset_record.email).first()
            
            if not user:
                return {
                    'error': get_message('user_not_found', locale),
                    'message': get_message('user_not_found_inactive', locale)
                }, 404
            
            return {
                'message': get_message('token_valid', locale),
                'user': {
                    'id_user': user.id_user,
                    'email': user.email,
                    'name': user.name,
                    'surname': user.surname
                },
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Token verification error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('token_verification_failed', locale),
                'message': get_message('generic_error_message', locale)
            }, 500
    
    def reset_password(self, token: str, new_password: str) -> Tuple[Dict[str, Any], int]:
        """
        Reset password using valid token
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            token_hash = TbOtp.hash_token(token)
            
            # Find the reset record
            reset_record = TbOtp.query.filter_by(
                token_hash=token_hash
            ).first()
            
            locale = request.headers.get('Accept-Language', 'en')

            if not reset_record:
                return {
                    'error': get_message('invalid_reset_token', locale),
                    'message': get_message('token_invalid_expired', locale)
                }, 400
            
            # Check if token is valid
            if not reset_record.is_valid():
                if reset_record.is_expired():
                    return {
                        'error': get_message('token_expired', locale),
                        'message': get_message('token_expired_message', locale)
                    }, 400
                elif reset_record.is_used:
                    return {
                        'error': get_message('token_already_used', locale),
                        'message': get_message('token_already_used_message', locale)
                    }, 400
            
            # Get user from reset record
            user = TbUser.query.filter_by(email=reset_record.email).first()
            
            if not user:
                return {
                    'error': get_message('user_not_found', locale),
                    'message': get_message('user_not_found_inactive', locale)
                }, 404
            
            # Check if user has Auth0 user ID
            if not user.auth0_user_id:
                return {
                    'error': get_message('auth0_user_not_found', locale),
                    'message': get_message('user_auth0_config_error', locale)
                }, 400
            
            # Reset password in Auth0 using Management API
            from .auth0_service import auth0_service
            
            auth0_result = auth0_service.reset_password_auth0(
                user_id=user.auth0_user_id,
                new_password=new_password
            )
            
            if auth0_result.get('error'):
                current_app.logger.error(f"Auth0 password reset failed for user {user.email}: {auth0_result.get('message')}")
                return {
                    'error': get_message('password_reset_failed', locale),
                    'message': auth0_result.get('localized_message') or auth0_result.get('message', get_message('auth0_reset_failed', locale))
                }, 400
            
            # Mark token as used
            reset_record.mark_as_used()
            
            # Invalidate all other reset tokens for this user
            self._invalidate_existing_tokens(user.email)
            
            db.session.commit()
            
            # Log the password reset
            current_app.logger.info(f"Password reset completed for user: {user.email} via Auth0")
            
            return {
                'message': get_message('password_reset_success_login', locale),
                'success': True
            }, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in password reset: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('database_error', locale),
                'message': get_message('generic_error_message', locale)
            }, 500
            
        except Exception as e:
            current_app.logger.error(f"Password reset error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('password_reset_failed', locale),
                'message': get_message('generic_error_message', locale)
            }, 500
    
    def _check_rate_limits(self, email: str, ip_address: str = None) -> Dict[str, Any]:
        """Check rate limits for password reset requests"""
        try:
            # Check email-based rate limit
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            email_attempts = TbOtp.query.filter(
                and_(
                    TbOtp.email == email,
                    TbOtp.token_hash.isnot(None),  # Only count password reset tokens
                    TbOtp.created_at >= one_hour_ago
                )
            ).count()
            
            if email_attempts >= self.max_attempts_per_hour:
                locale = request.headers.get('Accept-Language', 'en')
                return {
                    'allowed': False,
                    'message': get_message('rate_limit_exceeded_message', locale),
                    'retry_after': 3600  # 1 hour
                }
            
            return {'allowed': True}
            
        except Exception as e:
            current_app.logger.error(f"Rate limit check error: {str(e)}")
            return {'allowed': True}  # Allow on error to avoid blocking legitimate users
    
    def _invalidate_existing_tokens(self, email: str):
        """Invalidate all existing reset tokens for an email"""
        try:
            TbOtp.query.filter(
                and_(
                    TbOtp.email == email,
                    TbOtp.token_hash.isnot(None)
                )
            ).delete()
        except Exception as e:
            current_app.logger.error(f"Error invalidating tokens for {email}: {str(e)}")
    
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired password reset tokens"""
        try:
            expired_tokens = TbOtp.query.filter(
                TbOtp.expires_at < datetime.utcnow()
            ).all()
            
            count = len(expired_tokens)
            
            for token in expired_tokens:
                db.session.delete(token)
            
            db.session.commit()
            
            current_app.logger.info(f"Cleaned up {count} expired password reset tokens")
            return count
            
        except Exception as e:
            current_app.logger.error(f"Error cleaning up expired tokens: {str(e)}")
            db.session.rollback()
            return 0


# Create service instance
password_reset_service = PasswordResetService()
