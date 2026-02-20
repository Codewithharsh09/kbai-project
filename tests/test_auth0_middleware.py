"""
Comprehensive Test Suite for Auth0 Middleware
Tests auth0 verification and user extraction
"""
import pytest
from unittest.mock import patch, Mock
from flask import Flask, g


class TestAuth0VerifyMiddleware:
    """Test Auth0 Verification Middleware"""
    
    def test_get_current_user_no_context(self):
        """Unit: get_current_user returns None when no context"""
        from src.app.api.middleware.auth0_verify import get_current_user
        
        # No Flask context
        result = get_current_user()
        assert result is None
    
    def test_extract_token_from_request_missing_header(self):
        """Unit: Extract token returns error when header missing"""
        from src.app.api.middleware.auth0_verify import _extract_token_from_request
        from flask import Flask
        
        app = Flask(__name__)
        with app.test_request_context():
            token, error = _extract_token_from_request()
            assert token is None
            assert error is not None
    
    def test_extract_token_from_request_invalid_format(self):
        """Unit: Extract token returns error for invalid format"""
        from src.app.api.middleware.auth0_verify import _extract_token_from_request
        from flask import Flask
        
        app = Flask(__name__)
        with app.test_request_context(headers={'Authorization': 'Invalid'}):
            token, error = _extract_token_from_request()
            assert token is None
            assert error is not None
    
    def test_extract_token_from_request_success(self):
        """Unit: Extract token successfully from Bearer header"""
        from src.app.api.middleware.auth0_verify import _extract_token_from_request
        from flask import Flask
        
        app = Flask(__name__)
        with app.test_request_context(headers={'Authorization': 'Bearer test-token-123'}):
            token, error = _extract_token_from_request()
            assert token == 'test-token-123'
            assert error is None
    
    def test_require_auth0_decorator_exists(self):
        """Unit: require_auth0 decorator exists"""
        from src.app.api.middleware import require_auth0
        assert require_auth0 is not None
        assert callable(require_auth0)


class TestRolePermissionMiddleware:
    """Test Role Permission Middleware"""
    
    def test_normalize_role(self):
        """Unit: normalize_role converts to lowercase"""
        from src.app.api.middleware.role_permission import normalize_role
        
        assert normalize_role('ADMIN') == 'admin'
        assert normalize_role('User') == 'user'
        assert normalize_role('SuperAdmin') == 'superadmin'
        assert normalize_role('') == 'user'
        assert normalize_role(None) == 'user'
    
    def test_can_create_role_superadmin(self):
        """Unit: Superadmin can create any role"""
        from src.app.api.middleware.role_permission import can_create_role
        
        can_create, msg = can_create_role('superadmin', 'staff')
        assert can_create is True
        
        can_create, msg = can_create_role('superadmin', 'admin')
        assert can_create is True
        
        can_create, msg = can_create_role('superadmin', 'user')
        assert can_create is True
    
    def test_can_create_role_staff(self):
        """Unit: Staff can create admin and user only"""
        from src.app.api.middleware.role_permission import can_create_role
        
        can_create, msg = can_create_role('staff', 'admin')
        assert can_create is True
        
        can_create, msg = can_create_role('staff', 'user')
        assert can_create is True
        
        can_create, msg = can_create_role('staff', 'superadmin')
        assert can_create is False
        
        can_create, msg = can_create_role('staff', 'staff')
        assert can_create is False
    
    def test_can_create_role_admin(self):
        """Unit: Admin can create admin and user"""
        from src.app.api.middleware.role_permission import can_create_role
        
        can_create, msg = can_create_role('admin', 'admin')
        assert can_create is True
        
        can_create, msg = can_create_role('admin', 'user')
        assert can_create is True
        
        can_create, msg = can_create_role('admin', 'superadmin')
        assert can_create is False
    
    def test_can_create_role_user_forbidden(self):
        """Unit: User cannot create anyone"""
        from src.app.api.middleware.role_permission import can_create_role
        
        can_create, msg = can_create_role('user', 'user')
        assert can_create is False
        
        can_create, msg = can_create_role('user', 'admin')
        assert can_create is False
    
    def test_can_manage_user_superadmin(self):
        """Unit: Superadmin can manage everyone"""
        from src.app.api.middleware.role_permission import can_manage_user
        
        can_manage, msg = can_manage_user('superadmin', 'staff')
        assert can_manage is True
        
        can_manage, msg = can_manage_user('superadmin', 'admin')
        assert can_manage is True
        
        can_manage, msg = can_manage_user('superadmin', 'user')
        assert can_manage is True
    
    def test_can_manage_user_staff(self):
        """Unit: Staff can manage admin and user"""
        from src.app.api.middleware.role_permission import can_manage_user
        
        can_manage, msg = can_manage_user('staff', 'admin')
        assert can_manage is True
        
        can_manage, msg = can_manage_user('staff', 'user')
        assert can_manage is True
        
        can_manage, msg = can_manage_user('staff', 'superadmin')
        assert can_manage is False
    
    def test_require_permission_decorator_exists(self):
        """Unit: require_permission decorator exists"""
        from src.app.api.middleware import require_permission
        assert require_permission is not None
        assert callable(require_permission)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
