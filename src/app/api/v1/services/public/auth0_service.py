"""
Auth0 Integration Service

This service handles Auth0 authentication integration including:
- User authentication via Auth0
- Token validation
- User profile management
- Role-based access control

Author: Flask Enterprise Template
License: MIT
"""

import os
import json
from dotenv.main import logger
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from jose import jwt, JWTError
from src.app.database.models import TbUser
from src.app.database.models.public.tb_user import UserTempData
from src.app.database.models.public.tb_user import UserTempData
from src.extensions import db
from src.common.localization import get_message


class Auth0Service:
    """Auth0 service for authentication and authorization"""
    
    def __init__(self):
        self.domain = os.getenv('AUTH0_DOMAIN')
        self.client_id = os.getenv('AUTH0_CLIENT_ID')
        self.client_secret = os.getenv('AUTH0_CLIENT_SECRET')
        self.audience = os.getenv('AUTH0_AUDIENCE')
        self.algorithm = 'RS256'
        self.jwks_url = f'https://{self.domain}/.well-known/jwks.json'
        self._jwks = None

        # Management API configuration
        self.management_client_id = os.getenv('AUTH0_MANAGEMENT_CLIENT_ID')
        self.management_client_secret = os.getenv('AUTH0_MANAGEMENT_CLIENT_SECRET')
        self.management_audience = os.getenv('AUTH0_MANAGEMENT_AUDIENCE', f'https://{self.domain}/api/v2/')

        # Database connection name for user creation and authentication
        self.connection_name = os.getenv('AUTH0_DB_CONNECTION', 'KBAISTAGE')
    
    def get_jwks(self):
        """Get JSON Web Key Set from Auth0"""
        if not self._jwks:
            try:
                response = requests.get(self.jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
            except Exception as e:
                current_app.logger.error(f"Failed to fetch JWKS: {str(e)}")
                return None
        return self._jwks
    
    def verify_token(self, token):
        """Verify Auth0 JWT token"""
        try:
            # Get the signing key
            jwks = self.get_jwks()
            if not jwks:
                return None
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            # Find the correct key
            key = None
            for jwk in jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwt.RSAKey(jwk)
                    break
            
            if not key:
                return None
            
            # Verify and decode the token
            payload = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=f'https://{self.domain}/'
            )
            
            return payload
            
        except JWTError as e:
            current_app.logger.error(f"JWT verification failed: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Token verification error: {str(e)}")
            return None
    
    def get_user_from_token(self, token):
        """Get user from Auth0 token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        auth0_user_id = payload.get('sub')
        if not auth0_user_id:
            return None
        
        # Find user in database by Auth0 user ID
        user = TbUser.query.filter_by(auth0_user_id=auth0_user_id).first()
        if user:
            return user
        
        # If user doesn't exist, create new user from Auth0 data
        return self.create_user_from_auth0(payload)
    
    def create_user_from_auth0(self, payload):
        """Create new user from Auth0 payload"""
        try:
            auth0_user_id = payload.get('sub')
            email = payload.get('email')
            name = payload.get('name', '')
            
            # Check if user already exists by email
            existing_user = TbUser.query.filter_by(email=email).first()
            if existing_user:
                # Link Auth0 ID to existing user
                existing_user.auth0_user_id = auth0_user_id
                existing_user.auth0_metadata = json.dumps(payload)
                db.session.commit()
                return existing_user
            
            # Create new user
            user = TbUser(
                email=email,
                name=name.split(' ')[0] if name else '',
                surname=' '.join(name.split(' ')[1:]) if len(name.split(' ')) > 1 else '',
                role='USER',  # Default role
                status='ACTIVE',
                is_verified=True,
                auth0_user_id=auth0_user_id,
                auth0_metadata=json.dumps(payload)
            )
            
            db.session.add(user)
            db.session.commit()
            
            return user
            
        except Exception as e:
            current_app.logger.error(f"Failed to create user from Auth0: {str(e)}")
            return None

    # -------------------------------------------------------------------------
    # Get management token from auth0
    # -------------------------------------------------------------------------
    def _get_management_token(self) -> str:
        """Get Auth0 Management API token via client credentials"""
        try:
            # Use Management API credentials (not regular client credentials)
            mgmt_client_id = self.management_client_id
            mgmt_client_secret = self.management_client_secret
            mgmt_audience = self.management_audience

            if not self.domain or not mgmt_client_id or not mgmt_client_secret or not mgmt_audience:
                raise ValueError('Missing Auth0 management configuration (domain/client_id/client_secret/audience)')

            payload = {
                'grant_type': 'client_credentials',
                'client_id': mgmt_client_id,
                'client_secret': mgmt_client_secret,
                'audience': mgmt_audience,
            }
            resp = requests.post(f'https://{self.domain}/oauth/token', json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get('access_token')
        except Exception as e:
            current_app.logger.error(f"Failed to get Auth0 management token: {str(e)}")
            raise ValueError('Auth0 management authentication failed')
    
    # -------------------------------------------------------------------------------------------
    # Create user in auth0 database connection
    # -------------------------------------------------------------------------------------------
    def create_auth0_user(self, *, email: str, password: str, name: str = None, role: str = None, language: str = None) -> dict:
        """Create a user in Auth0 Database Connection and return Auth0 user payload"""
        # Ensure connection name exists even if instance predates new attributes
        if not hasattr(self, 'connection_name') or not self.connection_name:
            self.connection_name = os.getenv('AUTH0_DB_CONNECTION', 'Username-Password-Authentication')

        token = self._get_management_token()
        logger.info(f"Token: {token}")
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        body = {
            'connection': self.connection_name,
            'email': email,
            'password': password,
            'email_verified': False,
            'verify_email': False,
            'app_metadata': {
                'role': role or 'USER',
                'language': language or 'en'
            },
            'user_metadata': {}
        }
        # Set name if provided
        if name:
            body['name'] = name

        try:
            resp = requests.post(f'https://{self.domain}/api/v2/users', headers=headers, json=body, timeout=15)
            if resp.status_code in (200, 201):
                created_user = resp.json()
                logger.info(f"User created: {created_user.get('user_id')}")

                # Assign Auth0 role after user creation
                if role:
                    try:
                        self._assign_role_to_user(created_user['user_id'], role, token)
                        logger.info(f"Role '{role}' assigned to user {created_user['user_id']}")
                    except Exception as e:
                        logger.warning(f"Failed to assign role to user: {str(e)}")
                        # Don't fail user creation if role assignment fails

                return created_user

            # Parse error response
            try:
                err_json = resp.json()
                error_message = err_json.get('message', 'Auth0 user creation failed')
                error_code = err_json.get('errorCode', 'unknown')
            except Exception:
                err_json = None
                error_message = f"Auth0 error: {resp.text}"
                error_code = 'parse_error'

            # Log detailed error
            current_app.logger.error(f"Auth0 user creation failed: {resp.status_code} {resp.text}")
            
            # Raise with actual Auth0 error message
            raise ValueError(error_message)
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Auth0 user creation request failed: {str(e)}")
            raise ValueError('Auth0 user creation request failed')
  
    
    def update_user_metadata(self, user, metadata):
        """Update user's Auth0 metadata"""
        try:
            user.auth0_metadata = json.dumps(metadata)
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to update user metadata: {str(e)}")
            return False

    # -------------------------------------------------------------------------------------------
    # Authenticate user with email/password via Auth0 password realm grant
    # -------------------------------------------------------------------------------------------
    def authenticate_with_password(self, email: str, password: str) -> dict:
        """
        Authenticate user with email/password via Auth0 password realm grant.
        This implements the Resource Owner Password Grant (ROPG) flow.
        """
        try:
            current_app.logger.info(f"Auth0 Config - Domain: {self.domain}, Client ID: {self.client_id}")
            
            payload = {
                "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
                "username": email,
                "password": password,
                "scope": "openid profile email offline_access",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "realm": self.connection_name,
            }
            
            # Optional: Add API audience for API-scoped access token
            api_audience = os.getenv('AUTH0_AUDIENCE')
            if api_audience:
                payload["audience"] = api_audience
                current_app.logger.info(f"Added audience to payload: {api_audience}")
            
            current_app.logger.info(f"Making request to Auth0 with payload keys: {list(payload.keys())}")
            
            # Make request to Auth0
            response = requests.post(
                f"https://{self.domain}/oauth/token",
                json=payload,
                timeout=10
            )
            
            current_app.logger.info(f"Auth0 response status: {response.status_code}")
            
            if response.status_code != 200:
                current_app.logger.error(f"Auth0 authentication failed: {response.text}")
                raise ValueError(f"Auth0 Unauthorized: {response.text}")
            
            response_data = response.json()
            current_app.logger.info(f"Auth0 response data keys: {list(response_data.keys()) if response_data else 'None'}")
            return response_data
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Auth0 request failed: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            raise ValueError(f"{get_message('auth0_request_failed', locale)}: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Password authentication error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            raise ValueError(f"{get_message('auth0_user_authentication_failed', locale)}: {str(e)}")

    # -------------------------------------------------------------------------------------------
    # Verify Auth0 token using JWKS (supports both ID token and Access token)
    # -------------------------------------------------------------------------------------------
    def verify_auth0_token(self, token: str) -> dict:
        """
        Verify Auth0 JWT token (ID token OR Access token) using JWKS.

        Dual-mode verification:
        - ID token: audience = CLIENT_ID (contains user info: email, name, etc.)
        - Access token: audience = API_AUDIENCE (for API access)

        This is the PRIMARY method for token verification according to documentation.

        Args:
            token (str): JWT token from Auth0

        Returns:
            dict: Decoded token payload with user claims

        Raises:
            ValueError: If token verification fails
        """
        try:
            # Get JWKS keys from Auth0
            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            jwks_response = requests.get(jwks_url, timeout=10)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            # Pre-validate token format
            try:
                unverified_header = jwt.get_unverified_header(token)
            except Exception as e:
                raise ValueError(f"Invalid JWT format: {str(e)}")

            # Validate 'kid' header presence (Auth0 requirement)
            kid = unverified_header.get('kid')
            if not kid:
                raise ValueError("Token missing 'kid' header - not an Auth0 token")

            # Find matching RSA key
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key["kid"] == kid:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break

            if not rsa_key:
                raise ValueError("Unable to find appropriate key in JWKS")

            # Dual-mode verification: Try ID token first, then access token
            payload = None
            verification_errors = []

            # Try ID token verification (audience = client_id)
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=self.client_id,
                    issuer=f"https://{self.domain}/"
                )
                current_app.logger.info("Token verified as ID token (contains user profile)")
                return payload
            except JWTError as e:
                verification_errors.append(f"ID token verification failed: {str(e)}")
                current_app.logger.debug(f"ID token verification failed: {str(e)}")

            # Fallback: Try access token verification (audience = API audience)
            if self.audience:
                try:
                    payload = jwt.decode(
                        token,
                        rsa_key,
                        algorithms=["RS256"],
                        audience=self.audience,
                        issuer=f"https://{self.domain}/"
                    )
                    current_app.logger.info("Token verified as access token (API access)")
                    return payload
                except JWTError as e:
                    verification_errors.append(f"Access token verification failed: {str(e)}")
                    current_app.logger.debug(f"Access token verification failed: {str(e)}")

            # Both verifications failed
            error_msg = " | ".join(verification_errors)
            raise ValueError(f"Token verification failed for both ID and Access token: {error_msg}")

        except requests.RequestException as e:
            current_app.logger.error(f"Failed to fetch JWKS: {str(e)}")
            raise ValueError(f"Unable to fetch JWKS keys: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            current_app.logger.error(f"Token verification error: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")

    # -------------------------------------------------------------------------------------------
    # Verify id_token using JWKS (LEGACY - kept for backward compatibility)
    # -------------------------------------------------------------------------------------------
    def verify_id_token(self, id_token: str) -> dict:
        """
        Verify Auth0 id_token using JWKS.
        Also handles test tokens for development.

        LEGACY METHOD: Use verify_auth0_token() instead for new code.
        This method is kept for backward compatibility only.
        """
        try:
            # First try to decode as test token (for development)
            try:
                # Check if it's a test token by trying to decode with test secret
                test_payload = jwt.decode(id_token, 'test-secret', algorithms=['HS256'])
                current_app.logger.info("Test token detected and verified")
                return test_payload
            except:
                # Not a test token, proceed with normal Auth0 verification
                pass

            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            jwks = requests.get(jwks_url).json()

        # Get unverified header
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header["kid"]

        # Find the matching JWK
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                    }
                if not rsa_key:
                    raise ValueError("Unable to find appropriate key")

        # Verify and decode
            payload = jwt.decode(
            id_token,
            rsa_key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=f"https://{self.domain}/"
            )

            return payload


        except JWTError as e:
            current_app.logger.error(f"JWT verification failed: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"ID token verification error: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")

    def get_or_create_user_from_auth0(self, auth0_user_id: str, email: str, name: str = None, picture: str = None, role: str = None):
        """
        Get or create user from Auth0 data.
        Handles both existing users and new Auth0 users with dynamic role support.
        """
        try:
            from src.extensions import db
            import json

            current_app.logger.info(f"get_or_create_user_from_auth0 called - Auth0 ID: {auth0_user_id}, Email: {email}, Name: {name}, Role: {role}")

            # First try to find by Auth0 user ID
            current_app.logger.info(f"Searching user by Auth0 ID: {auth0_user_id}")
            user = TbUser.query.filter_by(auth0_user_id=auth0_user_id).first()
            if user:
                current_app.logger.info(f"User found by Auth0 ID: {user.id_user} - {user.email}")
                return user

            # If not found, try by email
            current_app.logger.info(f"User not found by Auth0 ID, searching by email: {email}")
            user = TbUser.query.filter_by(email=email).first()
            if user:
                # Link Auth0 ID to existing user
                current_app.logger.info(f"User found by email: {user.id_user} - Linking Auth0 ID")
                user.auth0_user_id = auth0_user_id
                user.auth0_metadata = {
                    'sub': auth0_user_id,
                    'email': email,
                    'name': name,
                    'picture': picture,
                    'linked_at': datetime.utcnow().isoformat()
                }
                db.session.commit()
                current_app.logger.info(f"Auth0 ID linked to existing user: {user.id_user}")
                return user

            # Create new user from Auth0 data with dynamic role
            # current_app.logger.info(f"Creating new user from Auth0 data")
            # username = email.split('@')[0] if email else auth0_user_id
            # name_parts = name.split(' ', 1) if name else [username, '']
            current_app.logger.info(f"Creating new user from Auth0 data")
            name_parts = name.split(' ', 1) if name else [email.split('@')[0], '']
            username = email.split('@')[0] if email else auth0_user_id
            
            if not name or name.strip() == '':
                try:
                    from flask import request
                    import requests
                    access_token = request.json.get('access_token')
                    if access_token:
                        userinfo_url = f"https://{current_app.config['AUTH0_DOMAIN']}/userinfo"
                        resp = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
                        if resp.status_code == 200:
                            userinfo = resp.json()
                            name = userinfo.get('name') or userinfo.get('nickname') or username
                except Exception as e:
                    current_app.logger.warning(f"Could not fetch userinfo from Auth0: {str(e)}")
                    name = username
            name_parts = name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''                     
            current_app.logger.info(f"User details - Email: {email}, Name: {name_parts[0]}, Surname: {name_parts[1] if len(name_parts) > 1 else ''}, Role: {role or 'USER'}")
            
            # Try to get temp data (if user was created via admin panel)
            temp_user = UserTempData.query.filter_by(email=email).first()
            
            if temp_user:
                current_app.logger.info(f"Found temp data for email: {email}")
                temp_dict = temp_user.to_dict()
                phone = temp_dict.get('phone')
                premium1 = temp_dict.get('premium_licenses_1') or 0
                premium2 = temp_dict.get('premium_licenses_2') or 0
                company_name = temp_dict.get('company_name')
                language = temp_dict.get('language') or 'en'
                id_admin = temp_dict.get('id_user')
            else:
                current_app.logger.warning(f"No temp data found for email: {email} - User likely created directly in Auth0")
                phone = None
                company_name = None
                language = 'en'
                id_admin = None
                premium1 = None
                premium2 = None
            # Normalize role to lowercase for database (ADMIN -> admin, SUPER_ADMIN -> superadmin)
            
            role_normalized = (role or 'USER').lower().replace('_', '')
            user = TbUser(
                email=email,
                username=username,
                name=first_name,
                surname=last_name,
                role=role_normalized,  # Lowercase role (admin, superadmin, user, manager)
                status='ACTIVE',
                is_verified=True,
                phone=phone,
                company_name=company_name,
                language=language,
                premium_licenses_1= premium1,
                premium_licenses_2= premium2,
                id_admin=id_admin,  # Set direct creator
                auth0_user_id=auth0_user_id,
                auth0_metadata={
                    'sub': auth0_user_id,
                    'email': email,
                    'name': name,
                    'picture': picture,
                    'role': role or 'USER',
                    'created_via': 'auth0_api'
                },
                password=None  # Password managed by Auth0
            )
            delete_temp_data = UserTempData.query.filter_by(email=email).delete()
            if delete_temp_data:
                current_app.logger.info(f"Deleted temp data for email: {email}")
            else:
                current_app.logger.warning(f"No temp data found for email: {email}")
            current_app.logger.info(f"Adding user to database session")
            db.session.add(user)
            current_app.logger.info(f"Committing database session")
            db.session.commit()
            current_app.logger.info(f"Refreshing user object")
            db.session.refresh(user)
            current_app.logger.info(f"User created successfully with ID: {user.id_user}")
            return user

        except Exception as e:
            current_app.logger.error(f"Failed to get/create user from Auth0: {str(e)}", exc_info=True)
            raise ValueError(f"User creation failed: {str(e)}")

    def create_user_in_auth0(self, email: str, password: str, name: str = None, role: str = 'USER'):
        """
        Create user in Auth0 Management API.
        This allows creating users that can login via Auth0 password realm.
        """
        try:
            # Check if Auth0 is configured
            if not self.domain:
                raise ValueError("Auth0 not configured - missing AUTH0_DOMAIN")
            
            # Try to use Management API if configured, otherwise use basic credentials
            if self.management_client_id and self.management_client_secret:
                # Use Management API credentials
                management_token = self._get_management_token()
                if not management_token:
                    raise ValueError("Failed to get Auth0 Management API token")
                
                # Prepare user data for Auth0
                user_data = {
                    "email": email,
                    "password": password,
                    "email_verified": True,
                    "connection": "Username-Password-Authentication",  # Database connection
                    "app_metadata": {
                        "role": role
                    },
                    "user_metadata": {
                        "name": name or email.split('@')[0]
                    }
                }
                
                # Create user in Auth0 using Management API
                headers = {
                    "Authorization": f"Bearer {management_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"https://{self.domain}/api/v2/users",
                    json=user_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code not in [200, 201]:
                    current_app.logger.error(f"Auth0 Management API user creation failed: {response.text}")
                    raise ValueError(f"Auth0 user creation failed: {response.text}")
                
                auth0_user_data = response.json()
                auth0_user_id = auth0_user_data.get('user_id')
                
                current_app.logger.info(f"User created in Auth0 via Management API: {email} (ID: {auth0_user_id})")
                
                return {
                    'auth0_user_id': auth0_user_id,
                    'email': email,
                    'name': name,
                    'role': role,
                    'auth0_data': auth0_user_data,
                    'method': 'management_api'
                }
                
            else:
                # Fallback: Use basic Auth0 credentials to create user via password realm
                current_app.logger.info("Management API not configured, using basic Auth0 credentials")
                
                # Try to authenticate with the user credentials to create them
                try:
                    # First, try to authenticate the user (this will create them if they don't exist)
                    auth_result = self.authenticate_with_password(email, password)
                    
                    if auth_result and auth_result.get('id_token'):
                        # User exists and can authenticate
                        current_app.logger.info(f"User already exists in Auth0: {email}")
                        return {
                            'auth0_user_id': 'existing_user',
                            'email': email,
                            'name': name,
                            'role': role,
                            'method': 'existing_user'
                        }
                    else:
                        raise ValueError("User authentication failed")
                        
                except Exception as auth_error:
                    current_app.logger.warning(f"User authentication failed: {str(auth_error)}")
                    # User doesn't exist, we can't create them without Management API
                    raise ValueError("Cannot create user in Auth0 without Management API credentials. Please set up Management API or create user manually in Auth0 Dashboard.")
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Auth0 request failed: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            raise ValueError(f"{get_message('auth0_user_creation_failed', locale)}: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Auth0 user creation error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            raise ValueError(f"{get_message('auth0_user_creation_failed', locale)}: {str(e)}")

    def reset_password_auth0(self, user_id: str, new_password: str) -> dict:
        """
        Reset password in Auth0 using Management API
        
        Args:
            user_id: Auth0 user ID
            new_password: New password
            
        Returns:
            dict: Response from Auth0
        """
        try:
            # Get management token
            management_token = self._get_management_token()
            if not management_token:
                return {'error': 'Failed to get management token'}
            
            # Auth0 Management API endpoint for updating user password
            url = f"https://{self.domain}/api/v2/users/{user_id}"
            
            headers = {
                'Authorization': f'Bearer {management_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare password reset data
            data = {
                'password': new_password,
                'connection': self.connection_name   # Default connection
            }
            
            # Make PATCH request to update password
            response = requests.patch(url, headers=headers, json=data)
            
            if response.status_code == 200:
                current_app.logger.info(f"Password reset successful for Auth0 user: {user_id}")
                return {
                    'success': True,
                    'message': 'Password updated successfully in Auth0'
                }
            else:
                current_app.logger.error(f"Auth0 password reset failed: {response.status_code} - {response.text}")
                return {
                    'error': 'Password reset failed',
                    'message': response.json().get('message', 'Unknown error')
                }
                
        except Exception as e:
            current_app.logger.error(f"Auth0 password reset error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': 'Password reset error',
                'message': str(e),
                'localized_message': get_message('password_reset_error', locale)
            }

    # --------------------------------------------------------------------------------
    # Get user role from Auth0 Management API
    # --------------------------------------------------------------------------------
    def get_auth0_user_role(self, user_id: str) -> str:
        """
        Get user role from Auth0 Management API.
        """
        try:
            token = self._get_management_token()
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get user details from Auth0
            url = f'https://{self.domain}/api/v2/users/{user_id}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                app_metadata = user_data.get('app_metadata', {})
                role = app_metadata.get('role', 'USER')
                current_app.logger.info(f"Auth0 user role: {role}")
                return role
            else:
                current_app.logger.error(f"Failed to get user role: {response.status_code}")
                return 'USER'
                
        except Exception as e:
            current_app.logger.error(f"Error getting Auth0 user role: {str(e)}")
            return 'USER'

    def get_user_roles_from_auth0(self, auth0_user_id: str) -> list:
        """
        Fetch assigned roles for a user from Auth0 Management API.

        This method fetches the ACTUAL roles assigned to a user in the Auth0 Dashboard
        under User Management > Users > [User] > Roles tab.

        This is different from get_auth0_user_role which fetches from app_metadata.

        Args:
            auth0_user_id: The Auth0 user ID (e.g., 'auth0|1234567890')

        Returns:
            list: List of role names assigned to the user, e.g., ['superadmin', 'user']
                    Returns empty list if no roles found or on error.
        """
        try:
            token = self._get_management_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            # Fetch roles assigned to this user
            url = f"https://{self.domain}/api/v2/users/{auth0_user_id}/roles"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                roles_data = response.json()
                # Extract role names from the response
                role_names = [
                    role.get("name", "").lower()
                    for role in roles_data
                    if role.get("name")
                ]
                current_app.logger.info(
                    f"Fetched Auth0 roles for user {auth0_user_id}: {role_names}"
                )
                return role_names
            else:
                current_app.logger.error(
                    f"Failed to fetch user roles from Auth0: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            current_app.logger.error(f"Error fetching Auth0 user roles: {str(e)}")
            return []
        
    def generate_test_id_token(self, user_id: str, email: str, role: str = 'USER') -> str:
        """
        Generate a test ID token for newly created users.
        This is for testing purposes - in production, Auth0 will handle token generation.
        """
        try:
            import jwt
            import time
            
            # Get Auth0 domain and audience
            domain = os.getenv('AUTH0_DOMAIN')
            audience = os.getenv('AUTH0_AUDIENCE')
            
            if not domain or not audience:
                raise ValueError("Auth0 domain and audience must be configured")
            
            # Create token payload
            now = int(time.time())
            payload = {
                'iss': f'https://{domain}/',
                'sub': user_id,
                'aud': audience,
                'iat': now,
                'exp': now + 3600,  # 1 hour expiry
                'email': email,
                'app_metadata': {
                    'role': role
                },
                'user_metadata': {},
                'email_verified': True
            }
            
            # For testing, we'll create a simple JWT
            # In production, this should be signed by Auth0
            test_token = jwt.encode(payload, 'test-secret', algorithm='HS256')
            
            current_app.logger.info(f"Generated test ID token for user: {email}")
            return test_token
            
        except Exception as e:
            current_app.logger.error(f"Failed to generate test ID token: {str(e)}")
            return None

    def _get_auth0_role_id(self, role_name: str, token: str) -> str:
        """
        Get Auth0 role ID by role name.
        Maps: SUPER_ADMIN -> superadmin, ADMIN -> admin, MANAGER -> manager, USER -> user
        """
        # Normalize role name to lowercase for Auth0
        role_name_lower = role_name.lower().replace('_', '')  # SUPER_ADMIN -> superadmin

        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # List all roles
            url = f'https://{self.domain}/api/v2/roles'
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                roles = response.json()
                # Find role by name
                for role in roles:
                    if role.get('name', '').lower() == role_name_lower:
                        logger.info(f"Found Auth0 role '{role_name}' with ID: {role['id']}")
                        return role['id']

                logger.warning(f"Auth0 role '{role_name}' not found. Available roles: {[r.get('name') for r in roles]}")
                return None
            else:
                logger.error(f"Failed to list Auth0 roles: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting Auth0 role ID: {str(e)}")
            return None

    def _assign_role_to_user(self, user_id: str, role: str, token: str):
        """
        Assign Auth0 role to user.
        """
        role_id = self._get_auth0_role_id(role, token)

        if not role_id:
            logger.warning(f"Cannot assign role '{role}' - role not found in Auth0")
            return

        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # Assign roles to user
            url = f'https://{self.domain}/api/v2/users/{user_id}/roles'
            payload = {
                'roles': [role_id]
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code in (200, 201, 204):
                logger.info(f"Successfully assigned role '{role}' (ID: {role_id}) to user {user_id}")
            else:
                logger.error(f"Failed to assign role: {response.status_code} {response.text}")
                raise ValueError(f"Auth0 role assignment failed: {response.text}")

        except Exception as e:
            logger.error(f"Error assigning Auth0 role: {str(e)}")
            raise


# Global Auth0 service instance
auth0_service = Auth0Service()


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        locale = request.headers.get('Accept-Language', 'en')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': get_message('auth_header_invalid', locale)}), 401
        
        if not token:
            return jsonify({'error': get_message('auth_token_required', locale)}), 401
        
        # Verify token and get user
        user = auth0_service.get_user_from_token(token)
        if not user:
            return jsonify({'error': get_message('auth_token_invalid_expired', locale)}), 401
        
        if user.status != 'ACTIVE':
            return jsonify({'error': get_message('account_not_active', locale)}), 403
        
        # Add user to request context
        request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                locale = request.headers.get('Accept-Language', 'en')
                return jsonify({'error': get_message('authentication_required', locale)}), 401
            
            user = request.current_user
            locale = request.headers.get('Accept-Language', 'en')
            
            if required_role == 'SUPER_ADMIN' and not user.is_super_admin():
                return jsonify({'error': get_message('super_admin_access_required', locale)}), 403
            
            if required_role == 'ADMIN' and not user.is_admin():
                return jsonify({'error': get_message('admin_access_required', locale)}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
