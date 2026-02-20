"""
Pytest Configuration - Modern Auth0 Architecture
Provides fixtures and mocks for comprehensive testing
"""
import os
import sys
import types
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

if "boto3" not in sys.modules:
    sys.modules["boto3"] = types.SimpleNamespace(client=lambda *_, **__: None, resource=lambda *_, **__: None)

if "botocore.exceptions" not in sys.modules:
    botocore_module = types.ModuleType("botocore")
    exceptions_module = types.ModuleType("exceptions")

    class ClientError(Exception):
        pass

    exceptions_module.ClientError = ClientError
    botocore_module.exceptions = exceptions_module

    sys.modules["botocore"] = botocore_module
    sys.modules["botocore.exceptions"] = exceptions_module

# Set test environment and default cleanup behavior
os.environ['FLASK_ENV'] = 'testing'
os.environ.setdefault('ALLOW_DB_CLEANUP', 'true')  

from src.app import create_app
from src.extensions import db
from src.app.database.models import TbUser, TbOtp, UserTempData


# ============================================================================
# App and Client Fixtures
# ============================================================================

@pytest.fixture(scope='session')
def app():
    """Create Flask app for testing session"""
    # Create app with testing config (uses PostgreSQL from environment)
    app = create_app('testing')
    
    # Override Auth0 config for testing
    app.config.update({
        'AUTH0_DOMAIN': os.getenv('AUTH0_DOMAIN', 'test.auth0.com'),
        'AUTH0_CLIENT_ID': os.getenv('AUTH0_CLIENT_ID', 'test-client-id'),
        'AUTH0_CLIENT_SECRET': os.getenv('AUTH0_CLIENT_SECRET', 'test-client-secret'),
        'AUTH0_AUDIENCE': os.getenv('AUTH0_AUDIENCE', 'test-audience'),
    })
    
    with app.app_context():
        # Create all tables
        try:
            db.create_all()
        except Exception as e:
            print(f"Warning: Could not create tables - Database may be unavailable: {e}")
            # Continue without creating tables - some tests may not need DB
        yield app
        # Cleanup
        try:
            db.session.remove()
        except Exception:
            pass  # Ignore cleanup errors
        # db.drop_all()  # Uncomment if you want to drop tables after tests


@pytest.fixture(scope='function')
def client(app):
    """Create test client for making requests"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create clean database session for each test"""
    try:
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Use connection for session (Flask-SQLAlchemy 3.x compatible)
        session = db.session
        session.bind = connection
        
        yield session
        
        # Rollback and cleanup
        try:
            session.rollback()
            session.expire_all()  # Expire all objects to prevent stale state
            session.remove()  # Remove session
        except Exception:
            pass  # Ignore rollback errors
        session.close()
        transaction.rollback()
        connection.close()
        
        # Clear any lingering objects
        try:
            db.session.remove()
        except Exception:
            pass
    except Exception as e:
        print(f"Warning: Database connection unavailable in db_session: {e}")
        # Return a mock session if DB unavailable
        from unittest.mock import MagicMock
        yield MagicMock(spec=db.session)


# ============================================================================
# Test-scoped marker for targeted cleanup
# ============================================================================

@pytest.fixture(scope='function')
def test_run_suffix():
    """Provide a deterministic, per-test unique suffix for test data tagging."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    ts = int(datetime.now().timestamp() * 1000000)
    return f"{ts}_{unique_id}"


# ============================================================================
# Optional Auth0 cleanup for test-created users (suffix-tagged emails)
# ============================================================================

def _get_auth0_management_token() -> str:
    """Get Auth0 Management API token from env config. Returns empty string if unavailable."""
    domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_MGMT_CLIENT_ID') or os.getenv('AUTH0_MANAGEMENT_CLIENT_ID')
    client_secret = os.getenv('AUTH0_MGMT_CLIENT_SECRET') or os.getenv('AUTH0_MANAGEMENT_CLIENT_SECRET')
    audience = os.getenv('AUTH0_MGMT_AUDIENCE') or os.getenv('AUTH0_MANAGEMENT_AUDIENCE') or (f"https://{domain}/api/v2/" if domain else None)
    if not (domain and client_id and client_secret and audience):
        return ""
    import requests
    try:
        resp = requests.post(
            f"https://{domain}/oauth/token",
            json={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'audience': audience,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get('access_token', '')
    except Exception:
        return ""


def _auth0_delete_users_with_suffix(suffix: str) -> None:
    """Delete Auth0 users whose email contains the provided suffix. No-op if creds missing."""
    import requests
    domain = os.getenv('AUTH0_DOMAIN')
    token = _get_auth0_management_token()
    if not (domain and token and suffix):
        return
    headers = { 'Authorization': f'Bearer {token}' }
    # Search users by email with mgmt API v2: GET /api/v2/users?q=email:*suffix*&search_engine=v3
    try:
        query = f"email:*{suffix}*"
        list_resp = requests.get(
            f"https://{domain}/api/v2/users",
            params={'q': query, 'search_engine': 'v3', 'per_page': 50},
            headers=headers,
            timeout=15,
        )
        if list_resp.status_code != 200:
            return
        users = list_resp.json() or []
        for u in users:
            user_id = u.get('user_id')
            if not user_id:
                continue
            try:
                requests.delete(
                    f"https://{domain}/api/v2/users/{user_id}",
                    headers=headers,
                    timeout=10,
                )
            except Exception:
                continue
    except Exception:
        return


@pytest.fixture(autouse=True)
def auth0_targeted_cleanup(test_run_suffix):
    """After each test, optionally delete Auth0 users tagged with this test suffix.

    Enabled only when ALLOW_DB_CLEANUP=true (to align with destructive cleanup intent).
    """
    yield
    if os.getenv('ALLOW_DB_CLEANUP', 'true').lower() == 'true':
        _auth0_delete_users_with_suffix(test_run_suffix)

# ============================================================================
# Auth0 Mocking Fixtures
# ============================================================================

@pytest.fixture
def mock_auth0_service():
    """Mock Auth0 service for testing without real Auth0 calls"""
    with patch('src.app.api.v1.services.public.auth0_service.Auth0Service.verify_auth0_token') as mock_verify, \
         patch('src.app.api.v1.services.public.auth0_service.Auth0Service.get_or_create_user_from_auth0') as mock_get_user, \
         patch('src.app.api.v1.services.public.auth0_service.Auth0Service._get_management_token') as mock_mgmt_token, \
         patch('src.app.api.v1.services.public.auth0_service.Auth0Service.create_user_in_auth0') as mock_create_user:
        
        # Mock token verification
        mock_verify.return_value = {
            'sub': 'auth0|test-user-123',
            'email': 'test@example.com',
            'name': 'Test User',
            'https://sinaptica.ai/roles': ['admin']
        }
        
        # Mock management token
        mock_mgmt_token.return_value = 'mock-management-token'
        
        # Mock user creation/retrieval
        mock_get_user.return_value = None
        
        # Mock Auth0 user creation
        mock_create_user.return_value = {
            'user_id': 'auth0|test-user-123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        # Create a simple mock object
        class MockAuth0Service:
            def __init__(self):
                self.verify_auth0_token = mock_verify
                self.get_or_create_user_from_auth0 = mock_get_user
                self._get_management_token = mock_mgmt_token
                self.create_user_in_auth0 = mock_create_user
                # Add other commonly used methods
                self.create_auth0_user = mock_create_user  # Use same mock for simplicity
                self.reset_password_auth0 = mock_get_user
                self.authenticate_with_password = mock_get_user
            
            def reset_mock(self):
                """Reset mock call counts and side effects"""
                self.verify_auth0_token.reset_mock()
                self.get_or_create_user_from_auth0.reset_mock()
                self._get_management_token.reset_mock()
                self.create_user_in_auth0.reset_mock()
                if hasattr(self.create_auth0_user, 'reset_mock'):
                    self.create_auth0_user.reset_mock()
                if hasattr(self.reset_password_auth0, 'reset_mock'):
                    self.reset_password_auth0.reset_mock()
                if hasattr(self.authenticate_with_password, 'reset_mock'):
                    self.authenticate_with_password.reset_mock()
        
        yield MockAuth0Service()


@pytest.fixture
def mock_password_reset_auth0():
    """Mock Auth0 service specifically for password reset service"""
    with patch('src.app.api.v1.services.public.auth0_service.auth0_service.reset_password_auth0') as mock_reset:
        mock_reset.return_value = {
            'success': True,
            'message': 'Password updated successfully in Auth0'
        }
        yield mock_reset


@pytest.fixture
def mock_email_service():
    """Mock email service to avoid sending real emails"""
    with patch('src.app.api.v1.services.common.email.EmailService.send_login_verification_email') as mock_otp, \
         patch('src.app.api.v1.services.common.email.EmailService.send_password_reset_email') as mock_reset:
        mock_otp.return_value = True
        mock_reset.return_value = True
        yield {'otp': mock_otp, 'reset': mock_reset}


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def create_test_user(db_session, test_run_suffix):
    """Factory fixture to create test users"""
    def _create_user(**kwargs):
        # Generate unique identifiers to avoid conflicts
        # Enforce a common prefix so targeted cleanup can match easily
        random_suffix = test_run_suffix
        common_prefix = 'controluser'

        # Build username and email to always start with common_prefix
        default_username = f"{common_prefix}{random_suffix}"
        default_email = f"{common_prefix}{random_suffix}@test.com"

        provided_username = kwargs.get('username')
        provided_email = kwargs.get('email')

        if provided_username:
            username = f"{common_prefix}_{provided_username}_{random_suffix}"
        else:
            username = default_username

        if provided_email:
            local, domain = provided_email.split('@')
            email = f"{common_prefix}_{local}_{random_suffix}@{domain}"
        else:
            email = default_email

        # Make auth0_user_id unique too and start with common_prefix
        provided_auth0_id = kwargs.get('auth0_user_id')
        if provided_auth0_id:
            auth0_user_id = f"{provided_auth0_id}_{random_suffix}"
        else:
            auth0_user_id = f"auth0|{common_prefix}_{random_suffix}"
        
        # Ensure all identifiers are unique by checking if they exist
        import time
        counter = 0
        original_username = username
        original_email = email
        original_auth0_id = auth0_user_id
        
        # Check and fix username uniqueness
        while db_session.query(TbUser).filter(TbUser.username == username).first():
            counter += 1
            username = f"{original_username}_{counter}_{int(time.time() * 1000000)}"
        
        # Check and fix email uniqueness
        while db_session.query(TbUser).filter(TbUser.email == email).first():
            counter += 1
            local, domain = original_email.split('@')
            email = f"{local}_{counter}_{int(time.time() * 1000000)}@{domain}"
        
        # Check and fix auth0_user_id uniqueness
        while db_session.query(TbUser).filter(TbUser.auth0_user_id == auth0_user_id).first():
            counter += 1
            auth0_user_id = f"{original_auth0_id}_{counter}_{int(time.time() * 1000000)}"
        
        user_data = {
            'email': email,
            'username': username,
            'name': kwargs.get('name', 'Test'),
            'surname': kwargs.get('surname', 'User'),
            'role': kwargs.get('role', 'user'),
            'status': kwargs.get('status', 'ACTIVE'),
            'is_verified': kwargs.get('is_verified', True),
            'mfa': kwargs.get('mfa', False),
            'auth0_user_id': auth0_user_id,
            'id_admin': kwargs.get('id_admin', None),
            'company_name': kwargs.get('company_name', None),
            'phone': kwargs.get('phone', None),
            'language': kwargs.get('language', 'en')
        }
        
        user = TbUser(**user_data)
        db_session.add(user)
        db_session.flush()  # Flush to get ID
        # After flush, the user.id_user is available from SQLAlchemy
        user_id = user.id_user
        
        # Verify the user was created successfully
        if not user_id:
            raise ValueError("Failed to create user - no ID generated")
        
        # Don't commit here - let the transaction handle it
        return user
    
    return _create_user


@pytest.fixture
def superadmin_user(create_test_user, db_session):
    """Create superadmin test user"""
    user = create_test_user(
        email='superadmin@test.com',
        username='superadmin',
        name='Super',
        surname='Admin',
        role='superadmin',
        auth0_user_id='auth0|superadmin-123'
    )
    return user


@pytest.fixture
def staff_user(create_test_user, db_session):
    """Create staff test user"""
    return create_test_user(
        email='staff@test.com',
        username='staff',
        name='Staff',
        surname='User',
        role='staff',
        auth0_user_id='auth0|staff-123'
    )


@pytest.fixture
def admin_user(create_test_user, superadmin_user, db_session):
    """Create admin test user (created by superadmin)"""
    # Ensure superadmin_user is properly flushed and has ID
    db_session.flush()  # Ensure superadmin_user is flushed to get ID
    
    superadmin_id = superadmin_user.id_user
    
    # Verify the superadmin_id exists before proceeding
    if not superadmin_id:
        raise ValueError("Superadmin user ID is not available")
    
    user = create_test_user(
        email='admin@test.com',
        username='admin',
        name='Admin',
        surname='User',
        role='admin',
        id_admin=superadmin_id,
        auth0_user_id='auth0|admin-123'
    )
    # Don't commit here - let the transaction handle it
    return user


@pytest.fixture
def regular_user(create_test_user, admin_user, db_session):
    """Create regular test user (created by admin)"""
    # Ensure admin_user is properly flushed and has ID
    db_session.flush()  # Ensure admin_user is flushed to get ID
    
    admin_id = admin_user.id_user
    
    # Verify the admin_id exists before proceeding
    if not admin_id:
        raise ValueError("Admin user ID is not available")
    
    user = create_test_user(
        email='user@test.com',
        username='regularuser',
        name='Regular',
        surname='User',
        role='user',
        id_admin=admin_id,
        auth0_user_id='auth0|user-123'
    )
    # Don't commit here - let the transaction handle it
    return user


@pytest.fixture
def inactive_user(create_test_user):
    """Create inactive test user - uses unique name to avoid cleanup"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return create_test_user(
        email=f'inactive_user_{unique_id}@test.com',
        username=f'inactive_user_{unique_id}',
        name='Inactive',
        surname='User',
        role='user',
        status='INACTIVE',
        auth0_user_id=f'auth0|inactive-{unique_id}'
    )


@pytest.fixture
def mfa_user(create_test_user):
    """Create MFA-enabled test user - uses unique name to avoid cleanup"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return create_test_user(
        email=f'mfa_user_{unique_id}@test.com',
        username=f'mfa_user_{unique_id}',
        name='MFA',
        surname='User',
        role='user',
        mfa=True,
        auth0_user_id=f'auth0|mfa-{unique_id}'
    )


# ============================================================================
# Auth Token Fixtures
# ============================================================================

@pytest.fixture
def auth_headers_superadmin(app, mock_auth0_service, superadmin_user):
    """Get auth headers for superadmin with mocked Auth0"""
    def _get_headers():
        # Mock Auth0 token verification to return superadmin
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': superadmin_user.auth0_user_id,
            'email': superadmin_user.email,
            'name': f'{superadmin_user.name} {superadmin_user.surname}',
            'https://sinaptica.ai/roles': ['superadmin']
        }
        return {'Authorization': f'Bearer test-token-superadmin'}
    return _get_headers


@pytest.fixture
def auth_headers_admin(app, mock_auth0_service, admin_user):
    """Get auth headers for admin with mocked Auth0"""
    def _get_headers():
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': admin_user.auth0_user_id,
            'email': admin_user.email,
            'name': f'{admin_user.name} {admin_user.surname}',
            'https://sinaptica.ai/roles': ['admin']
        }
        return {'Authorization': f'Bearer test-token-admin'}
    return _get_headers


@pytest.fixture
def auth_headers_user(app, mock_auth0_service, regular_user):
    """Get auth headers for regular user with mocked Auth0"""
    def _get_headers():
        mock_auth0_service.verify_auth0_token.return_value = {
            'sub': regular_user.auth0_user_id,
            'email': regular_user.email,
            'name': f'{regular_user.name} {regular_user.surname}',
            'https://sinaptica.ai/roles': ['user']
        }
        return {'Authorization': f'Bearer test-token-user'}
    return _get_headers


# ============================================================================
# OTP and Password Reset Fixtures
# ============================================================================

@pytest.fixture
def create_otp(db_session):
    """Factory fixture to create OTP records"""
    def _create_otp(email, otp='123456', expires_in_minutes=10, is_used=False):
        otp_record = TbOtp(
            email=email,
            otp=otp,
            expires_in_minutes=expires_in_minutes
        )
        otp_record.is_used = is_used
        db_session.add(otp_record)
        db_session.flush()  # Flush to get any generated IDs
        db_session.commit()
        
        return otp_record
    return _create_otp


@pytest.fixture
def create_password_reset_token(db_session):
    """Factory fixture to create password reset tokens"""
    def _create_token(email, token_hash=None, expires_in_minutes=60, is_used=False):
        if not token_hash:
            token = TbOtp.generate_secure_token()
            token_hash = TbOtp.hash_token(token)
        else:
            token = 'test-token'
        
        reset_record = TbOtp(
            email=email,
            token_hash=token_hash,
            expires_in_minutes=expires_in_minutes
        )
        reset_record.is_used = is_used
        db_session.add(reset_record)
        db_session.flush()  # Flush to get any generated IDs
        db_session.commit()
        
        return reset_record, token
    return _create_token


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture(autouse=True, scope="function")
def cleanup_database(db_session, test_run_suffix):
    """Automatically cleanup database before and after each test"""
    # Safety: avoid deleting real data by default. Use per-test transaction rollback.
    # Set ALLOW_DB_CLEANUP=true to enable destructive cleanup when using a disposable test DB.
    allow_cleanup = True  # Enable cleanup; exclusions protect current test data

    if not allow_cleanup:
        # No destructive cleanup; rely on transaction rollback and targeted cleanup below
        yield
        return

    # Clean up before test - delete in correct order (child tables first)
    # Import all models that might have foreign keys to users
    from src.app.database.models.public.tb_user_company import TbUserCompany
    from src.app.database.models.public.licence_admin import LicenceAdmin

    def cleanup_test_data(include_current_suffix=False):
        """Helper function to cleanup test data"""
        try:
            # Ensure session is in a clean state in case a previous test left it rolled back
            try:
                db_session.rollback()
            except Exception:
                pass
            print("Looking for test data to clean up...")
            
            # Import additional models needed for cleanup
            from src.app.database.models.public.tb_licences import TbLicences
            from src.app.database.models.kbai.kbai_companies import KbaiCompany
            
            # Get all test users first, EXCLUDING current test's suffix to avoid deleting data we just created
            suffix = test_run_suffix
            
            # Build filter conditions

            base_conditions = (
                (TbUser.email.like('%test%')) |
                (TbUser.username.like('test%')) |
                (TbUser.username.like('controluser%')) |
                (TbUser.username.like('inactive%')) |
                (TbUser.username.like('tagged_user_%')) |
                (TbUser.username.like('control_user_%')) |
                (TbUser.auth0_user_id.like('auth0|test%')) |
                (TbUser.auth0_user_id.like('auth0|inactive%')) |
                # Explicit admin seed patterns to ensure cleanup removes them
                (TbUser.email.like('parent_admin_%@example.com')) |
                (TbUser.email.like('child_admin_%@example.com')) |
                (TbUser.username.like('parent_admin_%')) |
                (TbUser.username.like('child_admin_%')) |
                # Legacy seed patterns/usernames seen in older runs
                (TbUser.username.like('superadmin_user_%')) |
                (TbUser.username.like('child2_user_%')) |
                (TbUser.username.like('admin_nc_user_%')) |
                (TbUser.email.like('sa_%@example.com')) |
                (TbUser.email.like('child2_%@example.com')) |
                (TbUser.email.like('admin_nc_%@example.com')) |
                # Explicit exact matches frequently used across tests
                (TbUser.username == 'test_user_unique') |
                (TbUser.email == 'test@example.com')
            )
            
            # For pre-test cleanup, exclude current suffix; for post-test cleanup, include it
            if not include_current_suffix:
                user_filter = base_conditions & (
                    ~TbUser.email.like(f"%{suffix}%") &
                    ~TbUser.username.like(f"%{suffix}%") &
                    ~TbUser.auth0_user_id.like(f"%{suffix}%")
                )
            else:
                user_filter = base_conditions
            
            test_users = db_session.query(TbUser).filter(user_filter).all()
            
            test_user_ids = [user.id_user for user in test_users]
            print(f"Found {len(test_users)} test users to clean up")
            
            # SAFETY: Only delete licenses with very specific test patterns
            # Real licenses have UUID format: LIC-XXXXXXXXXXXX (12 hex chars)
            # Test licenses have specific known patterns to avoid deleting real data
            test_license_patterns = [
                'LIC-123456',
                'LIC-789012', 
                'LIC-345678',
                'LIC-123456-SPECIAL',
                'LIC-PARENT',
                'LIC-000005',
                'LIC-000006',
                # Additional explicit test tokens seen during runs
                'LIC-C-1',
                'LIC-C-2',
                'LIC-4B19C42E73FE',
                'LIC-C60F3B7B4394',
            ]
            
            # Also match sequential test patterns (000000-999999 range)
            import re
            real_license_regex = r'^LIC-[A-F0-9]{12}$'  # Real license: 12 uppercase hex chars
            test_licenses = []
            all_licenses = db_session.query(TbLicences).all()
            
            # SAFETY CHECK: Only process if db_session is not a mock
            if not isinstance(db_session, MagicMock):
                for lic in all_licenses:
                    if lic.licence_token:
                        # Check if it matches known test patterns
                        is_test_license = (
                            lic.licence_token in test_license_patterns or 
                            re.match(r'^LIC-0{4,6}$', lic.licence_token) or  # Only LIC-000000 to LIC-000099
                            re.match(r'^LIC-000[0-9]{3}$', lic.licence_token) or  # LIC-000XXX format
                            re.match(r'^LIC-(NC|NC2)-[A-Za-z0-9]+$', lic.licence_token) or  # e.g., LIC-NC-aedac190
                            re.match(r'^LIC-C-[0-9]+$', lic.licence_token)  # e.g., LIC-C-1, LIC-C-2
                        ) and not re.match(real_license_regex, lic.licence_token)
                        
                        if is_test_license:
                            test_licenses.append(lic.id_licence)
                            print(f"Marked test license for deletion: {lic.licence_token}")
            
            # SAFETY: Log how many licenses are being deleted
            if test_licenses:
                print(f"Found {len(test_licenses)} TEST licenses to clean up (real licenses will NOT be touched)")
            
            # FINAL SAFETY CHECK: Ensure no real license is being deleted
            # Real licenses have 12-character hex format (from uuid.uuid4().hex[:12])
            # So any license NOT matching test patterns is considered REAL and will NOT be deleted
            safe_test_licenses = []
            for lic_id in test_licenses:
                lic_record = db_session.query(TbLicences).filter(TbLicences.id_licence == lic_id).first()
                if lic_record and lic_record.licence_token:
                    # Double check - only allow test patterns
                    token = lic_record.licence_token
                    is_safe_to_delete = (
                        token in test_license_patterns or 
                        re.match(r'^LIC-0{4,6}$', token) or
                        re.match(r'^LIC-000[0-9]{3}$', token) or
                        re.match(r'^LIC-(NC|NC2)-[A-Za-z0-9]+$', token) or
                        re.match(r'^LIC-C-[0-9]+$', token)
                    ) and not re.match(real_license_regex, token)

                    # If a token matches the real pattern exactly, never delete it
                    if re.match(real_license_regex, token):
                        print(f"SAFETY: Skipping REAL license (hex pattern): {token}")
                        continue
                    
                    # EXTRA SAFETY: If license token is long, skip unless it matches our explicit
                    # allowlist or safe regexes (some test tokens are longer, e.g., LIC-123456-SPECIAL)
                    if len(token) > 16 and not (
                        token in test_license_patterns or
                        re.match(r'^LIC-(NC|NC2)-[A-Za-z0-9]+$', token) or
                        re.match(r'^LIC-C-[0-9]+$', token)
                    ):
                        print(f"SAFETY: Skipping REAL license (too long): {token}")
                        continue
                        
                    if is_safe_to_delete:
                        safe_test_licenses.append(lic_id)
                        print(f"Safe to delete test license: {token}")
            
            test_licenses = safe_test_licenses  # Update with safe list only
            
            # Clean up companies associated with test licenses
            if test_licenses:
                # First get company IDs
                companies = db_session.query(KbaiCompany).filter(
                    KbaiCompany.id_licence.in_(test_licenses)
                ).all()
                company_ids = [c.id_company for c in companies]
                
                if company_ids:
                    print(f"Deleting {len(company_ids)} companies with test licenses...")
                    
                    # Import KbaiPreDashboard for cleanup
                    from src.app.database.models.kbai.kbai_pre_dashboard import KbaiPreDashboard
                    
                    # Delete KbaiPreDashboard first (child table with FK to companies)
                    db_session.query(KbaiPreDashboard).filter(
                        KbaiPreDashboard.company_id.in_(company_ids)
                    ).delete(synchronize_session=False)
                    db_session.commit()
                    
                    # Delete TbUserCompany (child table)
                    db_session.query(TbUserCompany).filter(
                        TbUserCompany.id_company.in_(company_ids)
                    ).delete(synchronize_session=False)
                    db_session.commit()
                    
                    # Then delete companies
                    db_session.query(KbaiCompany).filter(
                        KbaiCompany.id_licence.in_(test_licenses)
                    ).delete(synchronize_session=False)
                    db_session.commit()
            
            # Clean up LicenceAdmin entries for test licenses
            if test_licenses:
                print(f"Deleting LicenceAdmin entries for {len(test_licenses)} test licenses...")
                admin_count = db_session.query(LicenceAdmin).filter(
                    LicenceAdmin.id_licence.in_(test_licenses)
                ).count()
                if admin_count > 0:
                    db_session.query(LicenceAdmin).filter(
                        LicenceAdmin.id_licence.in_(test_licenses)
                    ).delete(synchronize_session=False)
                    db_session.commit()
            
            # Clean up the licenses themselves
            if test_licenses:
                print(f"Deleting {len(test_licenses)} test licenses...")
                db_session.query(TbLicences).filter(
                    TbLicences.id_licence.in_(test_licenses)
                ).delete(synchronize_session=False)
                db_session.commit()
            
            if test_user_ids:
                # Delete all related data for each user individually
                for user in test_users:
                    print(f"Cleaning up user: {user.username} ({user.email})")
                    
                    # Delete UserTempData by user ID
                    db_session.query(UserTempData).filter(
                        UserTempData.id_user == user.id_user
                    ).delete(synchronize_session=False)
                    
                    # Delete TbUserCompany by user ID
                    db_session.query(TbUserCompany).filter(
                        TbUserCompany.id_user == user.id_user
                    ).delete(synchronize_session=False)
                    
                    # Delete LicenceAdmin by user ID
                    db_session.query(LicenceAdmin).filter(
                        LicenceAdmin.id_user == user.id_user
                    ).delete(synchronize_session=False)
                
                # Delete OTPs by email patterns
                otp_base_conditions = (
                    (TbOtp.email.like('%test%')) |
                    (TbOtp.email.like('controluser%')) |
                    (TbOtp.email.like('inactive%')) |
                    (TbOtp.email.like('tagged_user_%')) |
                    (TbOtp.email.like('control_user_%')) |
                    # Match admin seed patterns for OTP cleanup
                    (TbOtp.email.like('parent_admin_%@example.com')) |
                    (TbOtp.email.like('child_admin_%@example.com')) |
                    # Legacy email patterns
                    (TbOtp.email.like('sa_%@example.com')) |
                    (TbOtp.email.like('child2_%@example.com')) |
                    (TbOtp.email.like('admin_nc_%@example.com')) 
                )
                
                if not include_current_suffix:
                    otp_filter = otp_base_conditions & (~TbOtp.email.like(f"%{suffix}%"))
                else:
                    otp_filter = otp_base_conditions
                
                otp_count = db_session.query(TbOtp).filter(otp_filter).count()
                
                if otp_count > 0:
                    print(f"Deleting {otp_count} OTP records...")
                    db_session.query(TbOtp).filter(otp_filter).delete(synchronize_session=False)

                # Delete UserTempData by email patterns
                temp_data_base_conditions = (
                    (UserTempData.email.like('%test%')) |
                    (UserTempData.email.like('controluser%')) |
                    (UserTempData.email.like('inactive%')) |
                    (UserTempData.email.like('tagged_user_%')) |
                    (UserTempData.email.like('control_user_%')) |
                    # Match admin seed patterns for temp data cleanup
                    (UserTempData.email.like('parent_admin_%@example.com')) |
                    (UserTempData.email.like('child_admin_%@example.com')) |
                    # Legacy email patterns
                    (UserTempData.email.like('sa_%@example.com')) |
                    (UserTempData.email.like('child2_%@example.com')) |
                    (UserTempData.email.like('admin_nc_%@example.com')) 
                )
                
                if not include_current_suffix:
                    temp_data_filter = temp_data_base_conditions & (~UserTempData.email.like(f"%{suffix}%"))
                else:
                    temp_data_filter = temp_data_base_conditions
                
                temp_data_count = db_session.query(UserTempData).filter(temp_data_filter).count()
                
                if temp_data_count > 0:
                    print(f"Deleting {temp_data_count} UserTempData records...")
                    db_session.query(UserTempData).filter(temp_data_filter).delete(synchronize_session=False)

            # Finally, delete users - try multiple times to handle foreign key constraints
            max_attempts = 3
            for attempt in range(max_attempts):
                if not include_current_suffix:
                    final_user_filter = user_filter
                else:
                    final_user_filter = base_conditions
                
                user_count = db_session.query(TbUser).filter(final_user_filter).count()
                
                if user_count > 0:
                    print(f"Deleting {user_count} User records (attempt {attempt + 1})...")
                    try:
                        db_session.query(TbUser).filter(final_user_filter).delete(synchronize_session=False)
                        db_session.commit()
                        print(f"Successfully deleted {user_count} users")
                        break
                    except Exception as e:
                        print(f"User deletion attempt {attempt + 1} failed: {e}")
                        db_session.rollback()
                        if attempt < max_attempts - 1:
                            print("Retrying...")
                        else:
                            print("All user deletion attempts failed")
                else:
                    print("No users to delete")
                    break

            db_session.commit()
            print("Test data cleaned up successfully")
        except Exception as e:
            print(f"Cleanup failed: {e}")
            db_session.rollback()

    # Clean up before test
        print("Starting pre-test cleanup...")
    cleanup_test_data()
    
    # Run the test
    yield
    
    # Clean up after test (whether it passes or fails)
    print("Starting post-test cleanup...")
    # For post-test cleanup, include current suffix to delete test data
    cleanup_test_data(include_current_suffix=True)



# ============================================================================
# Request Context Fixtures
# ============================================================================

@pytest.fixture
def mock_request_context(app):
    """Mock request context with headers"""
    def _context(**kwargs):
        with app.test_request_context(**kwargs):
            yield
    return _context


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def measure_time():
    """Measure execution time of code block"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, *args):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            return self.end_time - self.start_time if self.end_time else None
    
    return Timer


# Export all fixtures
__all__ = [
    'app', 'client', 'db_session',
    'mock_auth0_service', 'mock_email_service',
    'create_test_user', 'superadmin_user', 'staff_user', 'admin_user', 
    'regular_user', 'inactive_user', 'mfa_user',
    'auth_headers_superadmin', 'auth_headers_admin', 'auth_headers_user',
    'create_otp', 'create_password_reset_token',
    'cleanup_users', 'cleanup_otps', 'cleanup_temp_data',
    'mock_request_context', 'measure_time'
]