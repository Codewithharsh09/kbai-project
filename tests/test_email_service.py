"""
Comprehensive Test Suite for Email Service
Tests email sending, templates, error handling, and configuration
"""
import pytest
from unittest.mock import patch, MagicMock
from src.app.api.v1.services.common.email import EmailService


class TestEmailService:
    """Test Email Service functionality"""
    
    def test_email_service_initialization(self):
        """Unit: Service initializes correctly"""
        service = EmailService()
        assert service is not None
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_welcome_email_success(self, mock_smtp_class):
        """Unit: Send welcome email successfully"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        service = EmailService()
        result = service.send_welcome_email(
            recipient_email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='SecurePass123'
        )
        
        assert result is True
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_welcome_email_with_company(self, mock_smtp_class):
        """Unit: Send welcome email with company"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        service = EmailService()
        result = service.send_welcome_email(
            recipient_email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='SecurePass123',
            company_name='Test Company'
        )
        
        assert result is True
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_welcome_email_error(self, mock_smtp_class):
        """Unit: Handle email sending error"""
        mock_smtp_class.side_effect = Exception("SMTP error")
        
        service = EmailService()
        result = service.send_welcome_email(
            recipient_email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='SecurePass123'
        )
        
        assert result is False
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_password_reset_email_success(self, mock_smtp_class):
        """Unit: Send password reset email"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        # Mock user object
        mock_user = MagicMock()
        mock_user.email = 'test@example.com'
        
        service = EmailService()
        result = service.send_password_reset_email(
            user=mock_user,
            token='abc123'
        )
        
        assert result is True
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_login_verification_email_success(self, mock_smtp_class):
        """Unit: Send login verification email"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        service = EmailService()
        result = service.send_login_verification_email(
            to_email='test@example.com',
            user_name='John Doe',
            otp_code='123456'
        )
        
        assert result is True
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_send_notification_email_success(self, mock_smtp_class):
        """Unit: Send notification email"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        service = EmailService()
        result = service.send_notification_email(
            recipient_email='test@example.com',
            subject='Test',
            message='Test message',
            notification_type='info'
        )
        
        assert result is True
    
    @patch('src.app.api.v1.services.common.email.smtplib.SMTP')
    def test_email_configuration_test(self, mock_smtp_class):
        """Unit: Test email configuration"""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        service = EmailService()
        result, message = service.test_configuration()
        
        # Result should be boolean
        assert isinstance(result, bool)
        assert isinstance(message, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 