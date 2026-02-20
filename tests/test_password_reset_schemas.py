"""
Validation tests for password reset schemas: required fields and formats.
"""

import pytest
from marshmallow import ValidationError
from src.app.api.schemas.public.password_reset_schemas import (
    RequestPasswordResetSchema,
    ResetPasswordSchema,
)


class TestPasswordResetSchemas:
    """Class-based tests mirroring the EmailService style."""

    def test_request_password_reset_schema_valid_email(self):
        data = {"email": "user@example.com"}
        result = RequestPasswordResetSchema().load(data)
        assert result["email"] == data["email"]

    def test_request_password_reset_schema_invalid_email(self):
        with pytest.raises(ValidationError):
            RequestPasswordResetSchema().load({"email": "bad"})

    def test_reset_password_schema_valid(self):
        valid = {
            "token": "A" * 32,
            "new_password": "Abcdef1@",
            "confirm_password": "Abcdef1@",
        }
        out = ResetPasswordSchema().load(valid)
        assert out["token"] == valid["token"]

    def test_reset_password_schema_passwords_mismatch(self):
        invalid = {
            "token": "B" * 32,
            "new_password": "Abcdef1@",
            "confirm_password": "Different1@",
        }
        with pytest.raises(ValidationError):
            ResetPasswordSchema().load(invalid)

    def test_reset_password_schema_token_invalid_chars(self):
        bad = {
            "token": "bad token!",
            "new_password": "Abcdef1@",
            "confirm_password": "Abcdef1@",
        }
        with pytest.raises(ValidationError):
            ResetPasswordSchema().load(bad)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
