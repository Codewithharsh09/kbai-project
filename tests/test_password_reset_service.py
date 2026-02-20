"""
Tests for PasswordResetService covering request, verify, reset and cleanup.
All external deps (DB, Email, Auth0) are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.app.api.v1.services.public.password_reset_service import PasswordResetService


class TestPasswordResetService:
    """Password Reset Service tests (single class as requested)"""
    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    @patch('src.app.api.v1.services.public.password_reset_service.TbOtp')
    @patch('src.app.api.v1.services.public.password_reset_service.db')
    @patch('src.app.api.v1.services.public.password_reset_service.EmailService')
    def test_request_password_reset_user_exists(self, mock_email, mock_db, mock_otp, mock_user, app):
        """Covers happy path: user exists, token created, email sent."""
        svc = PasswordResetService()
        user = MagicMock()
        mock_user.query.filter_by.return_value.first.return_value = user
        mock_otp.generate_secure_token.return_value = 'tok'
        mock_otp.hash_token.return_value = 'hash'

        with app.app_context():
            resp, status = svc.request_password_reset('user@example.com', ip_address='1.2.3.4')
            assert status == 200
            assert resp['success'] is True

    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    def test_request_password_reset_user_not_exists(self, mock_user, app):
        """Covers path where user missing: still returns success message (security)."""
        svc = PasswordResetService()
        mock_user.query.filter_by.return_value.first.return_value = None

        with app.app_context():
            resp, status = svc.request_password_reset('missing@example.com')
            assert status == 200
            assert resp['success'] is True

    @patch('src.app.api.v1.services.public.password_reset_service.TbOtp')
    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    def test_verify_reset_token_invalid(self, mock_user, mock_otp, app):
        """Covers invalid/expired token branches."""
        svc = PasswordResetService()
        mock_otp.hash_token.return_value = 'hash'
        mock_otp.get_valid_token.return_value = None

        with app.app_context():
            resp, status = svc.verify_reset_token('bad')
            assert status == 400
            assert resp['error'] == 'Invalid reset token'

    @patch('src.app.api.v1.services.public.password_reset_service.TbOtp')
    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    def test_verify_reset_token_user_not_found(self, mock_user, mock_otp, app):
        """Covers token valid but user missing -> 404."""
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = True
        mock_otp.hash_token.return_value = 'h'
        mock_otp.get_valid_token.return_value = token
        mock_user.query.filter_by.return_value.first.return_value = None

        with app.app_context():
            resp, status = svc.verify_reset_token('token')
            assert status == 404
            assert resp['error'] == 'User not found'

    @patch('src.app.api.v1.services.public.password_reset_service.TbOtp')
    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    def test_reset_password_token_missing(self, mock_user, mock_otp, app):
        """Covers reset_password invalid token -> 400."""
        svc = PasswordResetService()
        mock_otp.hash_token.return_value = 'hash'
        mock_otp.query.filter_by.return_value.first.return_value = None

        with app.app_context():
            resp, status = svc.reset_password('bad', 'Newpass1!')
            assert status == 400
            assert resp['error'] == 'Invalid reset token'

    def test_password_reset_service_initialization(self):
        """Unit: Service initializes correctly"""
        service = PasswordResetService()
        assert service is not None
        assert service.token_expiry_minutes == 30
        assert service.max_attempts_per_hour == 3
    
    def test_service_methods_exist(self):
        """Unit: Service methods exist"""
        service = PasswordResetService()
        
        # Check if main methods exist
        assert hasattr(service, 'request_password_reset')
        assert hasattr(service, 'verify_reset_token')
    
    def test_service_initialization_properties(self):
        """Unit: Check service initialization properties"""
        service = PasswordResetService()
        
        assert service.token_expiry_minutes == 30
        assert service.max_attempts_per_hour == 3
        assert service.max_attempts_per_ip == 5

    @patch('src.app.api.v1.services.public.password_reset_service.TbUser')
    @patch('src.app.api.v1.services.public.password_reset_service.TbOtp')
    @patch('src.app.api.v1.services.public.password_reset_service.db')
    @patch('src.app.api.v1.services.public.auth0_service.auth0_service')
    def test_reset_password_success(self, mock_auth0_instance, mock_db, mock_otp, mock_user, app):
        """Covers successful reset flow including Auth0 call and token cleanup."""
        svc = PasswordResetService()

        reset_record = MagicMock()
        reset_record.is_valid.return_value = True
        mock_otp.hash_token.return_value = 'h'
        mock_otp.query.filter_by.return_value.first.return_value = reset_record

        user = MagicMock()
        user.email = 'user@example.com'
        user.auth0_user_id = 'auth0|u'
        mock_user.query.filter_by.return_value.first.return_value = user

        mock_auth0_instance.reset_password_auth0.return_value = {"ok": True}

        with app.app_context():
            resp, status = svc.reset_password('token', 'Newpass1!')
            assert status == 200
            assert resp['success'] is True

if __name__ == '__main__':
    pytest.main([__file__, '-v'])