"""
Unit tests for security headers module
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


class TestSecurityHeaders:
    """Tests for security headers configuration."""

    @pytest.fixture
    def security_headers(self):
        """Create security headers instance."""
        from security.headers import SecurityHeaders
        return SecurityHeaders()

    @pytest.mark.unit
    @pytest.mark.security
    def test_hsts_header(self, security_headers):
        """Test HSTS header generation."""
        headers = security_headers.get_headers()

        assert 'Strict-Transport-Security' in headers
        hsts = headers['Strict-Transport-Security']
        assert 'max-age=' in hsts
        assert 'includeSubDomains' in hsts

    @pytest.mark.unit
    @pytest.mark.security
    def test_hsts_disabled(self):
        """Test HSTS can be disabled."""
        from security.headers import SecurityHeaders

        config = SecurityHeaders(hsts_enabled=False)
        headers = config.get_headers()

        assert 'Strict-Transport-Security' not in headers

    @pytest.mark.unit
    @pytest.mark.security
    def test_frame_options_deny(self, security_headers):
        """Test X-Frame-Options header."""
        headers = security_headers.get_headers()

        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] == 'DENY'

    @pytest.mark.unit
    @pytest.mark.security
    def test_frame_options_sameorigin(self):
        """Test X-Frame-Options with SAMEORIGIN."""
        from security.headers import SecurityHeaders

        config = SecurityHeaders(frame_options='SAMEORIGIN')
        headers = config.get_headers()

        assert headers['X-Frame-Options'] == 'SAMEORIGIN'

    @pytest.mark.unit
    @pytest.mark.security
    def test_content_type_nosniff(self, security_headers):
        """Test X-Content-Type-Options header."""
        headers = security_headers.get_headers()

        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'

    @pytest.mark.unit
    @pytest.mark.security
    def test_xss_protection(self, security_headers):
        """Test X-XSS-Protection header."""
        headers = security_headers.get_headers()

        assert 'X-XSS-Protection' in headers
        assert '1; mode=block' in headers['X-XSS-Protection']

    @pytest.mark.unit
    @pytest.mark.security
    def test_referrer_policy(self, security_headers):
        """Test Referrer-Policy header."""
        headers = security_headers.get_headers()

        assert 'Referrer-Policy' in headers
        assert headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'

    @pytest.mark.unit
    @pytest.mark.security
    def test_permissions_policy(self, security_headers):
        """Test Permissions-Policy header."""
        headers = security_headers.get_headers()

        assert 'Permissions-Policy' in headers
        assert 'geolocation=()' in headers['Permissions-Policy']
        assert 'camera=()' in headers['Permissions-Policy']

    @pytest.mark.unit
    @pytest.mark.security
    def test_cache_control(self, security_headers):
        """Test Cache-Control header for secure responses."""
        headers = security_headers.get_headers()

        assert 'Cache-Control' in headers
        assert 'no-store' in headers['Cache-Control']
        assert 'no-cache' in headers['Cache-Control']

    @pytest.mark.unit
    @pytest.mark.security
    def test_csp_enabled(self, security_headers):
        """Test CSP header when enabled."""
        headers = security_headers.get_headers()

        assert 'Content-Security-Policy' in headers
        csp = headers['Content-Security-Policy']
        assert "default-src 'self'" in csp

    @pytest.mark.unit
    @pytest.mark.security
    def test_csp_disabled(self):
        """Test CSP can be disabled."""
        from security.headers import SecurityHeaders

        config = SecurityHeaders(csp_enabled=False)
        headers = config.get_headers()

        assert 'Content-Security-Policy' not in headers

    @pytest.mark.unit
    @pytest.mark.security
    def test_csp_report_only(self):
        """Test CSP report-only mode."""
        from security.headers import SecurityHeaders

        config = SecurityHeaders(csp_report_only=True)
        headers = config.get_headers()

        assert 'Content-Security-Policy-Report-Only' in headers
        assert 'Content-Security-Policy' not in headers

    @pytest.mark.unit
    @pytest.mark.security
    def test_custom_headers(self):
        """Test custom headers can be added."""
        from security.headers import SecurityHeaders

        config = SecurityHeaders(
            custom_headers={'X-Custom-Header': 'custom-value'}
        )
        headers = config.get_headers()

        assert 'X-Custom-Header' in headers
        assert headers['X-Custom-Header'] == 'custom-value'


class TestSecurityHeadersAPI:
    """Tests for API-specific security headers."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_create_api_headers(self):
        """Test creating headers optimized for API."""
        from security.headers import create_security_headers_for_api

        config = create_security_headers_for_api()
        headers = config.get_headers()

        # API should have strict CSP
        assert 'Content-Security-Policy' in headers
        assert "default-src 'none'" in headers['Content-Security-Policy']

        # Frame options should be DENY
        assert headers['X-Frame-Options'] == 'DENY'

        # Cache should be completely disabled
        assert 'no-store' in headers['Cache-Control']
        assert 'max-age=0' in headers['Cache-Control']
