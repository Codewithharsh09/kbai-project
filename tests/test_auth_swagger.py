"""
Covers src/app/api/v1/swaggers/auth_swagger.py to 100% by importing and
validating exported models and constants.
"""

import pytest


class TestAuthSwagger:
    def test_models_and_constants_exist(self):
        from src.app.api.v1.swaggers import auth_swagger as s

        # Namespace
        assert getattr(s, 'auth_ns').name == 'auth'

        # Request/response models exported via __all__
        expected_exports = {
            'auth_ns', 'auth0_verify_model', 'user_response_model',
            'auth0_login_response_model', 'auth0_logout_response_model',
            'auth0_verify_token_response_model', 'success_response_model',
            'error_response_model', 'create_user_model', 'update_user_model',
            'change_password_model', 'users_list_response_model',
            'PASSWORD_RULES', 'USERNAME_RULES', 'EMAIL_RULES',
            'EXAMPLE_AUTH0_CALLBACK', 'EXAMPLE_USER_RESPONSE',
            'EXAMPLE_CREATE_USER', 'EXAMPLE_UPDATE_USER',
            'EXAMPLE_CHANGE_PASSWORD', 'EXAMPLE_VALIDATION_ERROR',
            'EXAMPLE_AUTH_ERROR'
        }
        assert set(s.__all__) == expected_exports

        # Spot-check a few fields on various models
        assert 'access_token' in s.auth0_verify_model
        assert 'email' in s.user_response_model and 'role' in s.user_response_model
        assert 'auth0_tokens' in s.auth0_login_response_model
        assert 'message' in s.auth0_logout_response_model and 'success' in s.auth0_logout_response_model
        assert 'user' in s.auth0_verify_token_response_model and 'success' in s.auth0_verify_token_response_model
        assert 'user' in s.success_response_model
        assert 'error' in s.error_response_model
        assert 'email' in s.create_user_model and 'password' in s.create_user_model
        assert 'role' in s.update_user_model and 'status' in s.update_user_model
        assert 'new_password' in s.change_password_model
        assert 'users' in s.users_list_response_model and 'total' in s.users_list_response_model

        # Constants/examples sanity
        assert s.PASSWORD_RULES['min_length'] >= 8
        assert s.USERNAME_RULES['min_length'] <= s.USERNAME_RULES['max_length']
        assert '@' in s.EXAMPLE_CREATE_USER['email']
        assert 'message' in s.EXAMPLE_VALIDATION_ERROR
        assert 'error' in s.EXAMPLE_AUTH_ERROR


