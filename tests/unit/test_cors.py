"""
Unit tests for CORS configuration module
Sprint 22: Quality Assurance
"""

import pytest
import os
from unittest.mock import patch

# Add services/shared path for direct imports from security module
import sys
_services_shared = os.path.join(os.path.dirname(__file__), '../../services/shared')
if _services_shared not in sys.path:
    sys.path.append(_services_shared)  # Use append to not interfere with project root


class TestCORSConfig:
    """Tests for CORS configuration."""

    @pytest.fixture
    def cors_config(self):
        """Create CORS config instance."""
        from security.cors import CORSConfig
        return CORSConfig(
            origins=['https://app.example.com', 'https://admin.example.com'],
            allow_all_origins=False,
        )

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_origin_allowed_exact_match(self, cors_config):
        """Test exact origin matching."""
        assert cors_config.is_origin_allowed('https://app.example.com') is True
        assert cors_config.is_origin_allowed('https://admin.example.com') is True
        assert cors_config.is_origin_allowed('https://unknown.example.com') is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_origin_allowed_with_trailing_slash(self, cors_config):
        """Test origin matching with trailing slash."""
        assert cors_config.is_origin_allowed('https://app.example.com/') is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_origin_allowed_case_insensitive(self, cors_config):
        """Test case insensitive origin matching."""
        assert cors_config.is_origin_allowed('HTTPS://APP.EXAMPLE.COM') is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_origin_allowed_wildcard(self):
        """Test wildcard subdomain matching."""
        from security.cors import CORSConfig

        config = CORSConfig(
            origins=['*.example.com'],
            allow_all_origins=False,
        )

        assert config.is_origin_allowed('https://app.example.com') is True
        assert config.is_origin_allowed('https://admin.example.com') is True
        assert config.is_origin_allowed('https://other.com') is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_origin_allowed_all_origins(self):
        """Test that allow_all_origins is always disabled for security."""
        from security.cors import CORSConfig

        # Even in development, allow_all_origins should be forced to False
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            config = CORSConfig(allow_all_origins=True)
            # Security: allow_all_origins is always disabled
            assert config.allow_all_origins is False
            # Unknown origins should be rejected
            assert config.is_origin_allowed('https://any-origin.com') is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_allow_all_blocked_in_production(self):
        """Test that allow_all_origins is blocked in production."""
        from security.cors import CORSConfig

        with patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            config = CORSConfig(allow_all_origins=True)
            # Should be forced to False in production
            assert config.allow_all_origins is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_cors_headers(self, cors_config):
        """Test CORS headers generation."""
        headers = cors_config.get_cors_headers('https://app.example.com')

        assert 'Access-Control-Allow-Origin' in headers
        assert headers['Access-Control-Allow-Origin'] == 'https://app.example.com'
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers
        assert 'Access-Control-Allow-Credentials' in headers

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_cors_headers_disallowed_origin(self, cors_config):
        """Test no CORS headers for disallowed origin."""
        headers = cors_config.get_cors_headers('https://evil.com')

        assert headers == {}

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_cors_headers_vary_header(self, cors_config):
        """Test Vary header is included for dynamic origins."""
        headers = cors_config.get_cors_headers('https://app.example.com')

        assert 'Vary' in headers
        assert headers['Vary'] == 'Origin'

    @pytest.mark.unit
    @pytest.mark.security
    def test_no_credentials_with_wildcard(self):
        """Test credentials not allowed with wildcard origin."""
        from security.cors import CORSConfig

        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            config = CORSConfig(allow_all_origins=True, supports_credentials=True)
            headers = config.get_cors_headers('https://any.com')

            # When allow_all_origins is True, credentials should not be included
            # (this is a browser security requirement)
            assert 'Access-Control-Allow-Credentials' not in headers
