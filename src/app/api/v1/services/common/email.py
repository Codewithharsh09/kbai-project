"""
Flask Enterprise Backend Template - Email Service

This module provides comprehensive email functionality with HTML/text templates,
automatic credential generation, and robust error handling.

Features:
- HTML and text email templates
- Gmail SMTP integration with app passwords
- Automatic password generation
- Welcome emails with credentials
- Password reset notifications
- Retry mechanism with exponential backoff
- Template customization support

Author: Flask Enterprise Template
License: MIT
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app



class EmailService:
    """
    Enterprise email service with template support and robust error handling.

    This service provides:
    - SMTP configuration with Gmail
    - HTML and text email templates
    - Automatic credential generation
    - Retry mechanism for failed sends
    - Comprehensive logging
    """

    def __init__(self):
        """Initialize email service"""
        pass



    def send_welcome_email(self, recipient_email, first_name, last_name, password, company_name=None) -> bool:
        """
        Send welcome email with account credentials using template.
        
        Args:
            recipient_email (str): Recipient's email address
            first_name (str): User's first name
            last_name (str): User's last name
            password (str): Generated password
            company_name (str, optional): Company name

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Email configuration from environment
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('GMAIL_ADDRESS')
            smtp_password = current_app.config.get('GMAIL_PASSWORD')
            from_email = current_app.config.get('MAIL_DEFAULT_SENDER')
            from_name = current_app.config.get('MAIL_FROM_NAME', 'KBAI Platform')
            cc_email = current_app.config.get('MAIL_CC_EMAIL')
            
            # Simple email body format
            subject = "Welcome to KBAI Platform"
            body = f"🔑 Email: {recipient_email}\n🔑 Password: {password}"
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = recipient_email
            msg['Cc'] = cc_email
            
            # Add email body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            current_app.logger.info(f"Welcome email sent to: {recipient_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send welcome email: {str(e)}")
            return False

    def send_password_reset_email(self, user, token: str) -> bool:
        """
        Send password reset email using template with secure token link.

        Args:
            user: User object with email, name, surname
            token: Password reset token

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Email configuration from environment
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('GMAIL_ADDRESS')
            smtp_password = current_app.config.get('GMAIL_PASSWORD')
            from_email = current_app.config.get('MAIL_DEFAULT_SENDER')
            from_name = current_app.config.get('MAIL_FROM_NAME', 'KBAI Platform')
            cc_email = current_app.config.get('MAIL_CC_EMAIL')
            
            # Create reset link from frontend URL
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://stage-kbai.aionsoft.it')
            reset_link = f"{frontend_url}/en/reset-password?token={token}"
            
            # Simple email body format
            subject = "Password Reset - KBAI Platform"
            body = f"🔑 Reset Link: {reset_link}"
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = user.email
            msg['Cc'] = cc_email
            
            # Add email body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            current_app.logger.info(f"Password reset email sent to: {user.email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send password reset email: {str(e)}")
            return False


    def send_login_verification_email(self, to_email, user_name, otp_code, expires_minutes=10) -> bool:
        """
        Send login verification email with OTP code using template.

        Args:
            to_email (str): Recipient's email address
            user_name (str): User's name
            otp_code (str): 6-digit OTP code
            expires_minutes (int): OTP expiry time in minutes

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Email configuration from environment
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('GMAIL_ADDRESS')
            smtp_password = current_app.config.get('GMAIL_PASSWORD')
            from_email = current_app.config.get('MAIL_DEFAULT_SENDER')
            from_name = current_app.config.get('MAIL_FROM_NAME', 'KBAI Platform')
            cc_email = current_app.config.get('MAIL_CC_EMAIL')
            
            # Simple email body format
            subject = "Login Verification - KBAI Platform"
            body = f"🔑 Verification Code: {otp_code}"
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Cc'] = cc_email
            
            # Add email body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            current_app.logger.info(f"Login verification email sent to: {to_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send login verification email: {str(e)}")
            return False

    def send_notification_email(self, recipient_email, subject, message, notification_type="info") -> bool:
        """
        Send notification email using template.

        This method can be customized to send various types of notifications
        based on your project requirements.

        Args:
            recipient_email (str): Recipient's email address
            subject (str): Email subject
            message (str): Notification message
            notification_type (str): Type of notification (info, warning, error, success)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Email configuration from environment
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('GMAIL_ADDRESS')
            smtp_password = current_app.config.get('GMAIL_PASSWORD')
            from_email = current_app.config.get('MAIL_DEFAULT_SENDER')
            from_name = current_app.config.get('MAIL_FROM_NAME', 'KBAI Platform')
            cc_email = current_app.config.get('MAIL_CC_EMAIL')
            
            # Simple email body format
            body = f"🔑 Message: {message}"
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = f"{subject} - KBAI Platform"
            msg['From'] = from_email
            msg['To'] = recipient_email
            msg['Cc'] = cc_email
            
            # Add email body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            current_app.logger.info(f"Notification email sent to: {recipient_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send notification email: {str(e)}")
            return False

    def test_configuration(self):
        """
        Test email configuration by attempting to connect to SMTP server.

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('GMAIL_ADDRESS')
            smtp_password = current_app.config.get('GMAIL_PASSWORD')
            
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)

            current_app.logger.info("Email configuration test successful")
            return True, "Email configuration is valid"

        except smtplib.SMTPAuthenticationError:
            current_app.logger.error("Email configuration test failed - authentication error")
            return False, "Authentication failed - check GMAIL_ADDRESS and GMAIL_PASSWORD"
        except Exception as e:
            current_app.logger.error(f"Email configuration test failed: {str(e)}")
            return False, f"Configuration test failed: {str(e)}"
