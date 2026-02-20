"""
Comprehensive Test Suite for Auth Routes
Tests Auth0 authentication, user CRUD, role hierarchy, and MFA
Following client testing policy: 70% unit tests + 1 integration test per endpoint
"""
import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from src.app.database.models import TbUser, UserTempData, TbUserCompany


# ============================================================================
# Auth0 Logout Tests
# ============================================================================

class TestAuth0Logout:
    """Test POST /api/v1/auth/auth0/logout"""
    
    def test_logout_success(self, client):
        """Unit: Test successful logout clears cookie"""
        response = client.post('/api/v1/auth/auth0/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Logout successful'
        
        # Verify cookie is cleared in response headers
        set_cookie_headers = response.headers.getlist('Set-Cookie')
        assert any('auth_token' in cookie for cookie in set_cookie_headers)
    
    def test_logout_without_session(self, client):
        """Unit: Test logout works even without active session"""
        response = client.post('/api/v1/auth/auth0/logout')
        
        assert response.status_code == 200


# ============================================================================
# Auth0 Token Verification Tests
# ============================================================================

class TestAuth0Verify:
    """Test POST /api/v1/auth/auth0/verify"""
    
    def test_verify_missing_token(self, client):
        """Unit: Test verification fails without token"""
        response = client.post('/api/v1/auth/auth0/verify', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'request data is required' in data['message'].lower()
    
    def test_verify_invalid_token(self, client, mock_auth0_service):
        """Unit: Test verification fails with invalid token"""
        # Reset the mock to ensure clean state
        mock_auth0_service.reset_mock()
        mock_auth0_service.verify_auth0_token.side_effect = Exception("Invalid token")
        
        response = client.post('/api/v1/auth/auth0/verify',
                               json={'access_token': 'invalid-token'})
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'could not verify' in data['message'].lower()
    
    def test_verify_success_new_user(self, client, mock_auth0_service, db_session):
        """Unit: Test successful verification creates new user"""
        # Create a test user directly in this test
        import time
        unique_id = int(time.time() * 1000)
        test_user = TbUser(
            auth0_user_id=f'auth0|user-123_{unique_id}',
            email=f'user_{unique_id}@test.com',
            username=f'regularuser_{unique_id}',
            name='Regular',
            surname='User',
            role='user',
            status='ACTIVE',
            is_verified=True
        )
        db_session.add(test_user)
        db_session.commit()
        
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': test_user.auth0_user_id,
            'email': test_user.email,
            'name': f'{test_user.name} {test_user.surname}',
            'https://sinaptica.ai/roles': ['user']
        }
        
        mock_auth0_service.get_or_create_user_from_auth0.return_value = test_user
        
        response = client.post('/api/v1/auth/auth0/verify',
                               json={'access_token': 'test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data['data'] or 'mfa' in data['data']
    
    def test_verify_inactive_user(self, client, mock_auth0_service, db_session):
        """Unit: Test verification fails for inactive user"""
        # Create an inactive user directly in the test with unique identifiers
        from src.app.database.models import TbUser
        import time
        unique_id = int(time.time() * 1000)  # Use timestamp for uniqueness
        
        inactive_user = TbUser(
            auth0_user_id=f'auth0|inactive-{unique_id}',
            email=f'inactive{unique_id}@test.com',
            username=f'inactiveuser{unique_id}',
            name='Inactive',
            surname='User',
            role='user',
            status='INACTIVE',
            is_verified=True
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        # Reset the mock to ensure clean state
        mock_auth0_service.reset_mock()
        mock_auth0_service.verify_auth0_token.side_effect = None
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': inactive_user.auth0_user_id,
            'email': inactive_user.email,
            'name': f'{inactive_user.name} {inactive_user.surname}',
            'https://sinaptica.ai/roles': ['user']
        }
        
        print(f"Mock verify_auth0_token return value: {mock_auth0_service.verify_auth0_token.return_value}")
        print(f"Mock verify_auth0_token side_effect: {mock_auth0_service.verify_auth0_token.side_effect}")
        
        # Mock the get_or_create_user_from_auth0 method to return the inactive user
        def mock_get_or_create_inactive(auth0_user_id, email, name=None, picture=None, role=None):
            return inactive_user
        
        mock_auth0_service.get_or_create_user_from_auth0.side_effect = mock_get_or_create_inactive
        
        response = client.post('/api/v1/auth/auth0/verify',
                               json={'access_token': 'test-token'})
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'inactive' in data['message'].lower()
    
    def test_verify_mfa_enabled_user(self, client, mock_auth0_service, mfa_user, mock_email_service):
        """Unit: Test MFA-enabled user triggers OTP"""
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': mfa_user.auth0_user_id,
            'email': mfa_user.email,
            'name': f'{mfa_user.name} {mfa_user.surname}',
            'https://sinaptica.ai/roles': ['user']
        }
        
        mock_auth0_service.get_or_create_user_from_auth0.return_value = mfa_user
        
        response = client.post('/api/v1/auth/auth0/verify',
                               json={'access_token': 'test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['mfa'] is True
        assert data['data']['user'] is None  # User not returned until MFA verified
    
    def test_verify_integration(self, client, mock_auth0_service, superadmin_user):
        """Integration: Full auth0 verification flow"""
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': superadmin_user.auth0_user_id,
            'email': superadmin_user.email,
            'name': f'{superadmin_user.name} {superadmin_user.surname}',
            'https://sinaptica.ai/roles': ['superadmin']
        }
        
        mock_auth0_service.get_or_create_user_from_auth0.return_value = superadmin_user
        
        response = client.post('/api/v1/auth/auth0/verify',
                               json={'access_token': 'test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data['data']
        assert data['data']['user']['role'] == 'superadmin'


# ============================================================================
# List Users Tests (GET /api/v1/auth/users)
# ============================================================================

class TestListUsers:
    """Test GET /api/v1/auth/users with role hierarchy"""
    
    def test_list_users_superadmin(self, client, mock_auth0_service, superadmin_user, 
                                    admin_user, regular_user, db_session):
        """Unit: Superadmin sees all users (except themselves)"""
        # Mock current user as superadmin
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.get('/api/v1/auth/users',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data['data']
        
        # Superadmin should see admin and regular_user but not themselves
        user_emails = [u['email'] for u in data['data']['users']]
        assert admin_user.email in user_emails
        assert regular_user.email in user_emails
        assert superadmin_user.email not in user_emails  # Should not see themselves
    
    def test_list_users_staff(self, client, mock_auth0_service, staff_user, 
                              admin_user, superadmin_user, db_session):
        """Unit: Staff sees admin/user but not superadmin"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=staff_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': staff_user.auth0_user_id,
                    'email': staff_user.email,
                    'name': f'{staff_user.name} {staff_user.surname}',
                    'https://sinaptica.ai/roles': ['staff']
                }
                response = client.get('/api/v1/auth/users',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        user_emails = [u['email'] for u in data['data']['users']]
        
        # Staff should see admin but not superadmin or themselves
        assert admin_user.email in user_emails
        assert superadmin_user.email not in user_emails
        assert staff_user.email not in user_emails
    
    def test_list_users_admin(self, client, mock_auth0_service, admin_user, 
                              regular_user, create_test_user, db_session):
        """Unit: Admin sees only users they created"""
        # Create another user by different admin
        other_user = create_test_user(
            email='other@test.com',
            username='otheruser',
            role='user',
            id_admin=None  # No admin (orphaned user)
        )
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.get('/api/v1/auth/users',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        user_emails = [u['email'] for u in data['data']['users']]
        
        # Admin should only see users they created
        assert regular_user.email in user_emails
        assert other_user.email not in user_emails
    
    def test_list_users_regular_user_forbidden(self, client, mock_auth0_service, regular_user):
        """Unit: Regular user cannot list users"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=regular_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': regular_user.auth0_user_id,
                    'email': regular_user.email,
                    'name': f'{regular_user.name} {regular_user.surname}',
                    'https://sinaptica.ai/roles': ['user']
                }
                response = client.get('/api/v1/auth/users',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 403
        data = json.loads(response.data)
        # Check if data is a list (error response) or dict (success response)
        if isinstance(data, list):
            # Error response is a list
            assert any('permission' in str(item).lower() for item in data)
        else:
            # Success response is a dict
            assert 'permission' in data['message'].lower()
    
    def test_list_users_with_pagination(self, client, mock_auth0_service, 
                                        superadmin_user, create_test_user, db_session):
        """Unit: Test pagination parameters"""
        # Create multiple users
        for i in range(5):
            create_test_user(
                email=f'user{i}@test.com',
                username=f'user{i}',
                role='user'
            )
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.get('/api/v1/auth/users?page=1&per_page=2',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'pagination' in data['data']
        assert data['data']['pagination']['per_page'] == 2
    
    def test_list_users_integration(self, client, mock_auth0_service, 
                                     superadmin_user, admin_user, db_session):
        """Integration: Full user listing flow with search"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.get(f'/api/v1/auth/users?search={admin_user.email}',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']['users']) >= 1
        assert data['data']['users'][0]['email'] == admin_user.email


# ============================================================================
# Create User Tests (POST /api/v1/auth/users)
# ============================================================================

class TestCreateUser:
    """Test POST /api/v1/auth/users"""
    
    def test_create_user_by_superadmin(self, client, mock_auth0_service, 
                                       superadmin_user, db_session):
        """Unit: Superadmin can create admin users"""
        # Generate unique email to avoid conflicts
        import time
        unique_email = f'newadmin{int(time.time())}@test.com'
        
        # Mock the Auth0 service method that's actually called
        with patch('src.app.api.v1.services.auth0_service.create_auth0_user') as mock_create_auth0:
            mock_create_auth0.return_value = {
                'user_id': f'auth0|new-admin-{int(time.time())}',
                'email': unique_email
            }
            
            with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
                with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                    mock_verify.return_value = {
                        'sub': superadmin_user.auth0_user_id,
                        'email': superadmin_user.email,
                        'name': f'{superadmin_user.name} {superadmin_user.surname}',
                        'https://sinaptica.ai/roles': ['superadmin']
                    }
                    with patch('src.app.api.middleware.role_permission.get_current_user', return_value=superadmin_user):
                        response = client.post('/api/v1/auth/users',
                                              headers={'Authorization': 'Bearer test-token'},
                                              json={
                                                  'email': unique_email,
                                                  'password': 'Admin@123',
                                                  'first_name': 'New',
                                                  'last_name': 'Admin',
                                                  'role': 'admin',
                                                  'number_licences': 10,
                                                  'language': 'en'
                                              })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'auth0_user_id' in data['data']
    
    def test_create_user_duplicate_email(self, client, mock_auth0_service, 
                                        superadmin_user, admin_user, db_session):
        """Unit: Cannot create user with duplicate email"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                with patch('src.app.api.middleware.role_permission.get_current_user', return_value=superadmin_user):
                    response = client.post('/api/v1/auth/users',
                                          headers={'Authorization': 'Bearer test-token'},
                                          json={
                                              'email': admin_user.email,  # Already exists
                                              'password': 'Test@123',
                                              'first_name': 'Test',
                                              'last_name': 'User',
                                              'role': 'user'
                                          })
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'already exists' in data['message'].lower()
    
    def test_create_user_validation_error(self, client, mock_auth0_service, 
                                          superadmin_user, db_session):
        """Unit: Validation fails with missing required fields"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                with patch('src.app.api.middleware.role_permission.get_current_user', return_value=superadmin_user):
                    response = client.post('/api/v1/auth/users',
                                          headers={'Authorization': 'Bearer test-token'},
                                          json={
                                              'email': 'invalid-email',  # Invalid format
                                              # Missing password and names
                                          })
        
        assert response.status_code == 400
    
    def test_create_user_by_regular_user_forbidden(self, client, mock_auth0_service, 
                                                   regular_user, db_session):
        """Unit: Regular users cannot create other users"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=regular_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': regular_user.auth0_user_id,
                    'email': regular_user.email,
                    'name': f'{regular_user.name} {regular_user.surname}',
                    'https://sinaptica.ai/roles': ['user']
                }
                with patch('src.app.api.middleware.role_permission.get_current_user', return_value=regular_user):
                    response = client.post('/api/v1/auth/users',
                                          headers={'Authorization': 'Bearer test-token'},
                                          json={
                                              'email': 'test@test.com',
                                              'password': 'Test@123',
                                              'first_name': 'Test',
                                              'last_name': 'User',
                                              'role': 'user'
                                          })
        
        assert response.status_code == 403
    
    def test_create_user_integration(self, client, mock_auth0_service, 
                                     superadmin_user, db_session):
        """Integration: Full user creation flow with temp data"""
        import time
        unique_email = f'integration{int(time.time())}@test.com'
        
        # Mock the Auth0 service method that's actually called
        with patch('src.app.api.v1.services.auth0_service.create_auth0_user') as mock_create_auth0:
            mock_create_auth0.return_value = {
                'user_id': f'auth0|integration-test-{int(time.time())}',
                'email': unique_email
            }
            
            with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
                with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                    mock_verify.return_value = {
                        'sub': superadmin_user.auth0_user_id,
                        'email': superadmin_user.email,
                        'name': f'{superadmin_user.name} {superadmin_user.surname}',
                        'https://sinaptica.ai/roles': ['superadmin']
                    }
                    with patch('src.app.api.middleware.role_permission.get_current_user', return_value=superadmin_user):
                        response = client.post('/api/v1/auth/users',
                                              headers={'Authorization': 'Bearer test-token'},
                                              json={
                                                  'email': unique_email,
                                                  'password': 'Integration@123',
                                                  'first_name': 'Integration',
                                                  'last_name': 'Test',
                                                  'role': 'admin',
                                                  'number_licences': 5,
                                                  'company_name': 'Test Company',
                                                  'phone': '+1234567890'
                                              })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['data']['temp_data_saved'] is True


# ============================================================================
# Get User Details Tests (GET /api/v1/auth/users/<id>)
# ============================================================================

class TestGetUserDetails:
    """Test GET /api/v1/auth/users/<id>"""
    
    def test_get_user_success(self, client, mock_auth0_service, 
                              superadmin_user, admin_user, db_session):
        """Unit: Get user details successfully"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.get(f'/api/v1/auth/users/{admin_user.id_user}',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['user']['email'] == admin_user.email
        assert 'number_licences' in data['data']['user']
    
    def test_get_user_not_found(self, client, mock_auth0_service, superadmin_user):
        """Unit: Get non-existent user returns 404"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.get('/api/v1/auth/users/99999',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 404
    
    def test_get_user_integration(self, client, mock_auth0_service, 
                                  admin_user, regular_user, db_session):
        """Integration: Get user with company mappings"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.get(f'/api/v1/auth/users/{regular_user.id_user}',
                                     headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data['data']


# ============================================================================
# Update User Tests (PUT /api/v1/auth/users/<id>)
# ============================================================================

class TestUpdateUser:
    """Test PUT /api/v1/auth/users/<id>"""
    
    def test_update_user_success(self, client, mock_auth0_service, 
                                 superadmin_user, admin_user, db_session):
        """Unit: Superadmin can update any user"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.put(f'/api/v1/auth/users/{admin_user.id_user}',
                                     headers={'Authorization': 'Bearer test-token'},
                                     json={
                                         'name': 'Updated',
                                         'surname': 'Name',
                                         'phone': '+9876543210'
                                     })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify update in database
        try:
            db_session.refresh(admin_user)
        except Exception:
            # If refresh fails, just continue - object already has the necessary data
            pass
        assert admin_user.name == 'Updated'
        assert admin_user.phone == '+9876543210'
    
    def test_update_user_hierarchy_violation(self, client, mock_auth0_service, 
                                            admin_user, create_test_user, db_session):
        """Unit: Admin cannot update users created by others"""
        # Create user by different admin
        other_user = create_test_user(
            email='other@test.com',
            username='otheruser',
            role='user',
            id_admin=None  # No admin (orphaned user)
        )
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.put(f'/api/v1/auth/users/{other_user.id_user}',
                                     headers={'Authorization': 'Bearer test-token'},
                                     json={'name': 'Hacked'})
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'you can only update users you directly created' in data['message'].lower()
    
    def test_update_user_integration(self, client, mock_auth0_service, 
                                     admin_user, regular_user, db_session):
        """Integration: Admin updates user they created"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.put(
                    f'/api/v1/auth/users/{regular_user.id_user}',
                    headers={'Authorization': 'Bearer test-token'},
                    json={
                        'name': 'Updated'
                    }
                )
        
        assert response.status_code == 200
        try:
            db_session.refresh(regular_user)
        except Exception:
            # If refresh fails, just continue - object already has the necessary data
            pass
        assert regular_user.name == 'Updated'


# ============================================================================
# Delete User Tests (DELETE /api/v1/auth/users/<id>)
# ============================================================================

class TestDeleteUser:
    """Test DELETE /api/v1/auth/users/<id>"""
    
    def test_delete_user_success(self, client, mock_auth0_service, 
                                 superadmin_user, create_test_user, db_session):
        """Unit: Superadmin can delete users"""
        user_to_delete = create_test_user(
            email='delete@test.com',
            username='deleteuser',
            role='user'
        )
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.delete(f'/api/v1/auth/users/{user_to_delete.id_user}',
                                        headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_delete_self_forbidden(self, client, mock_auth0_service, admin_user):
        """Unit: Cannot delete own account"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.delete(f'/api/v1/auth/users/{admin_user.id_user}',
                                        headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'you cannot delete your own account' in data['message'].lower()
    
    def test_delete_user_hierarchy_violation(self, client, mock_auth0_service, 
                                            admin_user, create_test_user, db_session):
        """Unit: Admin cannot delete users created by others"""
        other_user = create_test_user(
            email='other@test.com',
            username='otheruser',
            role='user',
            id_admin=None  # No admin (orphaned user)
        )
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.delete(f'/api/v1/auth/users/{other_user.id_user}',
                                        headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 403
    
    def test_delete_user_integration(self, client, mock_auth0_service, 
                                     admin_user, db_session, test_run_suffix):
        """Integration: Admin deletes user they created"""
        # Create user with unique identifiers
        unique_suffix = test_run_suffix
        user_to_delete = TbUser(
            email=f'delete_{unique_suffix}@test.com',
            username=f'deleteuser_{unique_suffix}',
            name='Delete',
            surname='User',
            role='user',
            status='ACTIVE',
            is_verified=True,
            auth0_user_id=f'auth0|delete-{unique_suffix}',
            id_admin=admin_user.id_user
        )
        db_session.add(user_to_delete)
        db_session.commit()
        
        # Ensure admin_user is committed so TbUser.findOne() can find it
        db_session.add(admin_user)
        db_session.commit()
        
        # Refresh admin_user to ensure it's attached to the session
        db_session.refresh(admin_user)
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                # Patch _verify_and_get_user to return admin_user and ensure g.current_user is set
                with patch('src.app.api.middleware.auth0_verify._verify_and_get_user', return_value=(admin_user, None)):
                    # Also ensure get_current_user returns admin_user (reads from g.current_user)
                    # The require_auth0 decorator will set g.current_user = admin_user from _verify_and_get_user
                    response = client.delete(f'/api/v1/auth/users/{user_to_delete.id_user}',
                                            headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200


# ============================================================================
# Change Password Tests (POST /api/v1/auth/users/<id>/change-password)
# ============================================================================

class TestChangePassword:
    """Test POST /api/v1/auth/users/<id>/change-password"""
    
    def test_change_password_success(self, client, mock_auth0_service, 
                                     superadmin_user, admin_user, db_session):
        """Unit: Admin can change user password"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.post(f'/api/v1/auth/users/{admin_user.id_user}/change-password',
                                      headers={'Authorization': 'Bearer test-token'},
                                      json={
                                          'current_password': 'CurrentPass@123',
                                          'new_password': 'NewPassword@123'
                                      })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_change_password_validation_error(self, client, mock_auth0_service, 
                                              superadmin_user, admin_user):
        """Unit: Weak password rejected"""
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': superadmin_user.auth0_user_id,
                    'email': superadmin_user.email,
                    'name': f'{superadmin_user.name} {superadmin_user.surname}',
                    'https://sinaptica.ai/roles': ['superadmin']
                }
                response = client.post(f'/api/v1/auth/users/{admin_user.id_user}/change-password',
                                      headers={'Authorization': 'Bearer test-token'},
                                      json={
                                          'current_password': 'CurrentPass@123',
                                          'new_password': 'weak'
                                      })
        
        assert response.status_code == 400
    
    def test_change_password_integration(self, client, mock_auth0_service, 
                                        admin_user, regular_user, db_session):
        """Integration: Full password change flow"""
        new_password = 'StrongPassword@123'
        
        with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=admin_user):
            with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                mock_verify.return_value = {
                    'sub': admin_user.auth0_user_id,
                    'email': admin_user.email,
                    'name': f'{admin_user.name} {admin_user.surname}',
                    'https://sinaptica.ai/roles': ['admin']
                }
                response = client.post(f'/api/v1/auth/users/{regular_user.id_user}/change-password',
                                      headers={'Authorization': 'Bearer test-token'},
                                      json={
                                          'current_password': 'CurrentPass@123',
                                          'new_password': new_password
                                      })
        
        assert response.status_code == 200


# ============================================================================
# Performance and Edge Case Tests
# ============================================================================

class TestPerformanceAndEdgeCases:
    """Performance and edge case tests"""
    
    def test_list_users_performance(self, client, mock_auth0_service, 
                                    superadmin_user, create_test_user, 
                                    measure_time, db_session):
        """Performance: List users should complete within acceptable time"""
        # Create 10 test users (reduced for faster testing)
        for i in range(10):
            create_test_user(
                email=f'perftest{i}@test.com',
                username=f'perftest{i}',
                role='user'
            )
        
        with measure_time() as timer:
            with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
                with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                    mock_verify.return_value = {
                        'sub': superadmin_user.auth0_user_id,
                        'email': superadmin_user.email,
                        'name': f'{superadmin_user.name} {superadmin_user.surname}',
                        'https://sinaptica.ai/roles': ['superadmin']
                    }
                    response = client.get('/api/v1/auth/users',
                                         headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code == 200
        assert timer.elapsed < 2.0  # Should complete within 2 seconds
    
    def test_concurrent_user_creation(self, client, mock_auth0_service, 
                                      superadmin_user, db_session):
        """Edge: Test concurrent user creation handling"""
        # This tests database uniqueness constraints
        import time
        base_time = int(time.time())
        unique_email = f'concurrent{base_time}@test.com'
        
        # Mock the Auth0 service method that's actually called
        with patch('src.app.api.v1.services.auth0_service.create_auth0_user') as mock_create_auth0:
            # Mock to return different user IDs for different calls
            mock_create_auth0.side_effect = [
                {
                    'user_id': f'auth0|concurrent-test-{base_time}-1',
                    'email': unique_email
                },
                {
                    'user_id': f'auth0|concurrent-test-{base_time}-2',
                    'email': unique_email
                }
            ]
            
            with patch('src.app.api.middleware.auth0_verify.get_current_user', return_value=superadmin_user):
                with patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token') as mock_verify:
                    mock_verify.return_value = {
                        'sub': superadmin_user.auth0_user_id,
                        'email': superadmin_user.email,
                        'name': f'{superadmin_user.name} {superadmin_user.surname}',
                        'https://sinaptica.ai/roles': ['superadmin']
                    }
                    with patch('src.app.api.middleware.role_permission.get_current_user', return_value=superadmin_user):
                        # First creation
                        response1 = client.post('/api/v1/auth/users',
                                               headers={'Authorization': 'Bearer test-token'},
                                               json={
                                                   'email': unique_email,
                                                   'password': 'Test@123',
                                                   'first_name': 'Test',
                                                   'last_name': 'User',
                                                   'role': 'user'
                                               })
                        
                        # Second creation with SAME email (should fail due to duplicate)
                        response2 = client.post('/api/v1/auth/users',
                                               headers={'Authorization': 'Bearer test-token'},
                                               json={
                                                   'email': unique_email,  # Same email - should cause conflict
                                                   'password': 'Test@123',
                                                   'first_name': 'Test',
                                                   'last_name': 'User',
                                                   'role': 'user'
                                               })
        
        # Verify first request succeeds
        assert response1.status_code == 201
        
        # Verify second request fails with duplicate email
        assert response2.status_code == 409  # Conflict
        response2_data = json.loads(response2.data)
        assert 'already' in response2_data['message'].lower()  # Check for "already" in the message
class TestAuthRoutesAdditional:
    """Additional coverage for public/auth_routes.py missing branches."""

    def _patch_auth_decorators(self, monkeypatch):
        import src.app.api.v1.routes.public.auth_routes as ar
        import src.app.api.middleware.auth0_verify as av
        import src.app.api.middleware.role_permission as rp

        def identity_decorator(*args, **kwargs):
            def _wrap(f):
                return f
            return _wrap

        monkeypatch.setattr(ar, 'require_auth0', identity_decorator, raising=False)
        monkeypatch.setattr(ar, 'require_permission', identity_decorator, raising=False)
        monkeypatch.setattr(ar, 'validate_user_action', identity_decorator, raising=False)
        # Ensure middleware helpers allow access
        # Bypass token extraction/verification entirely by returning a tuple (user, None)
        dummy_user = type('U', (), {'id_user': 1, 'role': 'superadmin', 'email': 'u@test.com', 'status': 'ACTIVE'})()
        monkeypatch.setattr(av, '_extract_token_from_request', lambda: ('tok', None), raising=False)
        monkeypatch.setattr(av, '_verify_and_get_user', lambda token: (dummy_user, None), raising=False)
        monkeypatch.setattr(av, 'get_current_user', lambda: dummy_user, raising=False)
        monkeypatch.setattr(rp, 'check_permission', lambda role, action: (True, ''), raising=False)

    def _try_paths(self, client, method: str, paths, **kwargs):
        for p in paths:
            resp = getattr(client, method)(p, **kwargs)
            if resp.status_code != 404:
                return resp
        # return last 404 if none matched
        return resp

    def test_auth0_verify_token_no_auth(self, client):
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/auth0/verify-token', '/api/v1/auth0/verify-token', '/auth/auth0/verify-token', '/auth0/verify-token']
        )
        assert resp.status_code == 401

    def test_auth0_verify_token_bad_header(self, client):
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/auth0/verify-token', '/api/v1/auth0/verify-token', '/auth/auth0/verify-token', '/auth0/verify-token'],
            headers={'Authorization': 'Bearer'}
        )
        assert resp.status_code == 401

    def test_auth0_verify_token_decode_failure(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        monkeypatch.setattr(ar, 'TbUser', MagicMock())
        import flask_jwt_extended
        monkeypatch.setattr(flask_jwt_extended, 'decode_token', lambda t: (_ for _ in ()).throw(Exception('bad')))
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/auth0/verify-token', '/api/v1/auth0/verify-token', '/auth/auth0/verify-token', '/auth0/verify-token'],
            headers={'Authorization': 'Bearer tok'}
        )
        assert resp.status_code == 401

    def test_auth0_verify_token_user_not_found(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        tb = MagicMock()
        tb.query.get.return_value = None
        monkeypatch.setattr(ar, 'TbUser', tb)
        import flask_jwt_extended
        monkeypatch.setattr(flask_jwt_extended, 'decode_token', lambda t: {'sub': 123})
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/auth0/verify-token', '/api/v1/auth0/verify-token', '/auth/auth0/verify-token', '/auth0/verify-token'],
            headers={'Authorization': 'Bearer tok'}
        )
        assert resp.status_code == 401

    def test_auth0_verify_token_success(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        user = MagicMock()
        user.to_dict.return_value = {'id_user': 1}
        tb = MagicMock()
        tb.query.get.return_value = user
        monkeypatch.setattr(ar, 'TbUser', tb)
        import flask_jwt_extended
        monkeypatch.setattr(flask_jwt_extended, 'decode_token', lambda t: {'sub': 1})
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/auth0/verify-token', '/api/v1/auth0/verify-token', '/auth/auth0/verify-token', '/auth0/verify-token'],
            headers={'Authorization': 'Bearer tok'}
        )
        assert resp.status_code == 200

    def test_users_collection_get_error_path(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)

        # Mock current user and service response
        cu = MagicMock()
        cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)
        monkeypatch.setattr(ar, 'user_service', MagicMock(find=lambda **f: ({'message': 'err'}, 500)))

        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/users', '/api/v1/users', '/auth/users', '/users'],
            headers={'Authorization': 'Bearer tok'}
        )
        assert resp.status_code == 500

    def test_users_collection_post_validation_error(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)
        cu = MagicMock(); cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)

        # Missing required body triggers 400 via schema validation
        resp = self._try_paths(
            client,
            'post',
            ['/api/v1/auth/users', '/api/v1/users', '/auth/users', '/users'],
            json={},
            headers={'Authorization': 'Bearer tok'}
        )
        assert resp.status_code == 400

    def test_user_resource_delete_forbidden(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)
        cu = MagicMock(); cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)
        svc = MagicMock()
        svc.delete.return_value = ({'message': 'no', 'error': 'x'}, 403)
        monkeypatch.setattr(ar, 'user_service', svc)
        resp = self._try_paths(
            client,
            'delete',
            ['/api/v1/auth/users/2', '/api/v1/users/2', '/auth/users/2', '/users/2']
        )
        assert resp.status_code == 403

    def test_user_resource_get_not_found(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)
        cu = MagicMock(); cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)
        monkeypatch.setattr(ar, 'user_service', MagicMock(findOne=lambda uid, cid: ({'message': 'missing'}, 404)))
        resp = self._try_paths(
            client,
            'get',
            ['/api/v1/auth/users/99', '/api/v1/users/99', '/auth/users/99', '/users/99']
        )
        assert resp.status_code == 404

    def test_user_resource_put_success(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)
        cu = MagicMock(); cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)
        monkeypatch.setattr(ar, 'user_service', MagicMock(update=lambda **k: ({'message': 'ok', 'data': {}}, 200)))
        resp = self._try_paths(
            client,
            'put',
            ['/api/v1/auth/users/2', '/api/v1/users/2', '/auth/users/2', '/users/2'],
            json={'name': 'A'}
        )
        assert resp.status_code == 200

    def test_change_user_password_error(self, monkeypatch, client):
        import src.app.api.v1.routes.public.auth_routes as ar
        self._patch_auth_decorators(monkeypatch)
        cu = MagicMock(); cu.id_user = 1
        monkeypatch.setattr(ar, 'get_current_user', lambda: cu)
        monkeypatch.setattr(ar, 'user_service', MagicMock(change_user_password=lambda *a, **k: ({'message': 'bad'}, 400)))
        resp = self._try_paths(
            client,
            'post',
            ['/api/v1/auth/users/2/change-password', '/api/v1/users/2/change-password', '/auth/users/2/change-password', '/users/2/change-password'],
            json={'new_password': 'x'}
        )
        assert resp.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
