"""
Unit tests for CSRF protection module
Sprint 22: Quality Assurance
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# Add the services/shared path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/shared'))


class TestCSRFProtection:
    """Tests for CSRF protection functionality."""

    @pytest.fixture
    def csrf_protection(self):
        """Create CSRF protection instance."""
        from security.csrf import CSRFProtection
        return CSRFProtection(
            secret_key='test-secret-key',
            token_expiry=3600,
        )

    @pytest.mark.unit
    @pytest.mark.security
    def test_generate_token(self, csrf_protection):
        """Test CSRF token generation."""
        raw_token, signed_token = csrf_protection.generate_token()

        assert raw_token is not None
        assert signed_token is not None
        assert len(raw_token) > 20
        assert '.' in signed_token
        assert signed_token.count('.') == 2

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_token_success(self, csrf_protection):
        """Test successful CSRF token validation."""
        raw_token, signed_token = csrf_protection.generate_token()

        is_valid = csrf_protection.validate_token(raw_token, signed_token)

        assert is_valid is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_token_mismatch(self, csrf_protection):
        """Test CSRF token validation with mismatched tokens."""
        raw_token, signed_token = csrf_protection.generate_token()
        wrong_token = 'wrong_token_value'

        is_valid = csrf_protection.validate_token(wrong_token, signed_token)

        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_token_expired(self, csrf_protection):
        """Test CSRF token validation with expired token."""
        # Create CSRF with 1 second expiry
        short_expiry_csrf = type(csrf_protection)(
            secret_key='test-secret-key',
            token_expiry=1,
        )

        raw_token, signed_token = short_expiry_csrf.generate_token()
        time.sleep(2)  # Wait for expiry

        is_valid = short_expiry_csrf.validate_token(raw_token, signed_token)

        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_token_invalid_format(self, csrf_protection):
        """Test CSRF token validation with invalid format."""
        raw_token = 'some_token'
        invalid_signed = 'invalid.format'  # Only 1 dot, should have 2

        is_valid = csrf_protection.validate_token(raw_token, invalid_signed)

        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_token_with_session_id(self, csrf_protection):
        """Test CSRF token with session binding."""
        session_id = 'user-session-123'
        raw_token, signed_token = csrf_protection.generate_token(session_id=session_id)

        # Valid with correct session
        is_valid = csrf_protection.validate_token(raw_token, signed_token, session_id=session_id)
        assert is_valid is True

        # Invalid with wrong session
        is_valid = csrf_protection.validate_token(raw_token, signed_token, session_id='wrong-session')
        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_exempt_methods(self, csrf_protection):
        """Test exempt HTTP methods."""
        assert csrf_protection.is_exempt('GET', '/api/v1/users') is True
        assert csrf_protection.is_exempt('HEAD', '/api/v1/users') is True
        assert csrf_protection.is_exempt('OPTIONS', '/api/v1/users') is True
        assert csrf_protection.is_exempt('POST', '/api/v1/users') is False
        assert csrf_protection.is_exempt('PUT', '/api/v1/users') is False
        assert csrf_protection.is_exempt('DELETE', '/api/v1/users') is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_exempt_paths(self, csrf_protection):
        """Test exempt URL paths."""
        assert csrf_protection.is_exempt('POST', '/api/v1/health') is True
        assert csrf_protection.is_exempt('POST', '/metrics') is True
        assert csrf_protection.is_exempt('POST', '/api/v1/auth/login') is True
        assert csrf_protection.is_exempt('POST', '/api/v1/workflows') is False


class TestCSRFFunctions:
    """Tests for CSRF helper functions."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_generate_csrf_token(self):
        """Test standalone token generation function."""
        from security.csrf import generate_csrf_token

        raw_token, signed_token = generate_csrf_token()

        assert raw_token is not None
        assert signed_token is not None

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_csrf_token(self):
        """Test standalone token validation function."""
        from security.csrf import generate_csrf_token, validate_csrf_token

        raw_token, signed_token = generate_csrf_token()

        assert validate_csrf_token(raw_token, signed_token) is True
        assert validate_csrf_token('wrong', signed_token) is False
