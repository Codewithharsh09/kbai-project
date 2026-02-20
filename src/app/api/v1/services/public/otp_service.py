"""
OTP Service for 2-Step Verification
Handles OTP generation, email sending, and verification
"""

import secrets
import hashlib
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from flask import current_app, request
from sqlalchemy import and_

from src.app.database.models import TbOtp, TbUser
from src.extensions import db
from src.common.localization import get_message


class OtpService:
    """Service for OTP generation, email sending, and verification"""
    
    def __init__(self):
        self.otp_length = 6
        self.otp_expiry_minutes = 10
        self.max_attempts = 3
    
    def generate_otp(self) -> str:
        """Generate secure 6-digit OTP"""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    def hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def send_otp_email(self, email: str, otp: str, user_name: str = None) -> bool:
        """Send OTP via email using the email service"""
        try:
            # Import and use the email service
            from ..common.email import EmailService
            
            email_service = EmailService()
            
            # Send login verification email with OTP
            result = email_service.send_login_verification_email(
                to_email=email,
                user_name=user_name or "User",
                otp_code=otp
            )
            
            if result:
                current_app.logger.info(f"OTP Email sent successfully to {email}: {otp}")
                return True
            else:
                current_app.logger.error(f"Failed to send OTP email to {email}")
                return False
            
        except Exception as e:
            current_app.logger.error(f"Failed to send OTP email: {str(e)}")
            return False
    
    def create_otp(self, email: str, user_name: str = None) -> Tuple[Dict[str, Any], int]:
        """Create and send OTP for email"""
        try:
            # Check if user exists
            user = TbUser.query.filter_by(email=email).first()
            if not user:
                # If user doesn't exist in local DB, create a temporary user object for email sending
                # This can happen if the user exists in Auth0 but not yet synced to local DB
                user = type('MockUser', (), {
                    'email': email,
                    'name': user_name or 'User',
                    'status': 'ACTIVE'
                })()
                current_app.logger.info(f"User not found in local DB, using email {email} for OTP")
            else:
                # Check if user is active
                if user.status != 'ACTIVE':
                    locale = request.headers.get('Accept-Language', 'en')
                    return {
                        'error': get_message('account_inactive', locale),
                        'message': get_message('account_not_active_support', locale)
                    }, 403
            
            # Clean up expired OTPs first
            self.cleanup_expired_otps()
            
            # Check for existing valid OTP
            existing_otp = TbOtp.query.filter(
                and_(
                    TbOtp.email == email,
                    TbOtp.is_used == False,
                    TbOtp.expires_at > datetime.utcnow()
                )
            ).first()
            
            # if existing_otp:
            #     return {
            #         'error': 'OTP already sent',
            #         'message': 'An OTP has already been sent to your email. Please check your inbox or wait for it to expire.'
            #     }, 429
            
            # Generate new OTP
            otp = self.generate_otp()
            
            # Create OTP record
            otp_record = TbOtp(
                email=email,
                otp=otp,  # Store plain OTP for verification
                expires_in_minutes=self.otp_expiry_minutes
            )
            
            db.session.add(otp_record)
            db.session.commit()
            
            # Send OTP via email
            email_sent = self.send_otp_email(email, otp, user_name or user.name)
            
            if not email_sent:
                # Rollback if email sending failed
                db.session.delete(otp_record)
                db.session.commit()
                locale = request.headers.get('Accept-Language', 'en')
                return {
                    'error': get_message('email_sending_failed', locale),
                    'message': get_message('otp_email_send_failed', locale)
                }, 500
            
            current_app.logger.info(f"OTP created for {email}: {otp}")
            
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'message': get_message('otp_sent_success', locale),
                'email': email,
                'expires_in_minutes': self.otp_expiry_minutes,
                'success': True
            }, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create OTP error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('otp_create_failed', locale),
                'message': str(e)
            }, 500
    
    def verify_otp(self, email: str, otp: str) -> Tuple[Dict[str, Any], int]:
        """Verify OTP and return user if valid. Accepts both original OTP and default 123456 for development."""
        try:
            # Clean up expired OTPs first
            self.cleanup_expired_otps()
            
            # Check for default development OTP first
            if otp == "123456":
                current_app.logger.info(f"Development OTP (123456) used for {email}")
                # Get user without checking OTP record
                user = TbUser.query.filter_by(email=email).first()
                if not user:
                    locale = request.headers.get('Accept-Language', 'en')
                    return {
                        'error': get_message('user_not_found', locale),
                        'message': get_message('user_not_found', locale)
                    }, 404
                
                # Mark any existing OTP as used (if exists)
                existing_otp = TbOtp.query.filter(
                    and_(
                        TbOtp.email == email,
                        TbOtp.is_used == False,
                        TbOtp.expires_at > datetime.utcnow()
                    )
                ).first()
                
                if existing_otp:
                    existing_otp.mark_as_used()
                    db.session.commit()
                
                current_app.logger.info(f"Development OTP verified successfully for {email}")
                
                locale = request.headers.get('Accept-Language', 'en')
                return {
                    'message': get_message('otp_verified_dev_success', locale),
                    'user': user.to_dict(),
                    'success': True,
                    'development_mode': True
                }, 200
            
            # Original OTP verification logic
            otp_record = TbOtp.get_valid_otp(email, otp)
            
            if not otp_record:
                locale = request.headers.get('Accept-Language', 'en')
                return {
                    'error': get_message('invalid_otp', locale),
                    'message': get_message('invalid_otp_message', locale)
                }, 400
            
            # Mark OTP as used
            otp_record.mark_as_used()
            db.session.commit()
            
            # Get user
            user = TbUser.query.filter_by(email=email).first()
            if not user:
                locale = request.headers.get('Accept-Language', 'en')
                return {
                    'error': get_message('user_not_found', locale),
                    'message': get_message('user_not_found', locale)
                }, 404
            
            current_app.logger.info(f"OTP verified successfully for {email}")
            
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'message': get_message('otp_verified_success', locale),
                'user': user.to_dict(),
                'success': True,
                'development_mode': False
            }, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Verify OTP error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': get_message('otp_verify_failed', locale),
                'message': str(e)
            }, 500
    
    def cleanup_expired_otps(self) -> int:
        """Clean up expired OTPs"""
        try:
            return TbOtp.cleanup_expired()
        except Exception as e:
            current_app.logger.error(f"Cleanup expired OTPs error: {str(e)}")
            return 0


# Initialize OTP service
otp_service = OtpService()
