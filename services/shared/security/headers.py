"""
Security Headers Module
Sprint 21: Security Hardening

Implements security response headers following OWASP recommendations.
Can be used standalone or with Flask-Talisman.
"""

import os
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SecurityHeaders:
    """
    Security headers configuration.

    Implements headers recommended by OWASP:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Referrer-Policy
    - Permissions-Policy
    """

    # Strict Transport Security (HSTS)
    hsts_enabled: bool = field(default_factory=lambda:
        os.getenv('SECURITY_HSTS_ENABLED', 'true').lower() == 'true'
    )
    hsts_max_age: int = field(default_factory=lambda:
        int(os.getenv('SECURITY_HSTS_MAX_AGE', '31536000'))  # 1 year
    )
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    # Content Security Policy
    csp_enabled: bool = field(default_factory=lambda:
        os.getenv('SECURITY_CSP_ENABLED', 'true').lower() == 'true'
    )
    csp_policy: Optional[str] = None
    csp_report_only: bool = False
    csp_report_uri: Optional[str] = field(default_factory=lambda:
        os.getenv('SECURITY_CSP_REPORT_URI')
    )

    # X-Frame-Options
    frame_options: str = field(default_factory=lambda:
        os.getenv('SECURITY_FRAME_OPTIONS', 'DENY')
    )
    frame_options_allow_from: Optional[str] = None

    # X-Content-Type-Options
    content_type_nosniff: bool = True

    # X-XSS-Protection (legacy, but still useful for older browsers)
    xss_protection: bool = True
    xss_protection_block: bool = True

    # Referrer-Policy
    referrer_policy: str = field(default_factory=lambda:
        os.getenv('SECURITY_REFERRER_POLICY', 'strict-origin-when-cross-origin')
    )

    # Permissions-Policy (formerly Feature-Policy)
    permissions_policy: Optional[str] = field(default_factory=lambda:
        os.getenv('SECURITY_PERMISSIONS_POLICY',
            'geolocation=(), microphone=(), camera=(), payment=()'
        )
    )

    # Cache-Control for sensitive responses
    cache_control: str = 'no-store, no-cache, must-revalidate, private'

    # Additional custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default CSP if not provided."""
        if self.csp_enabled and not self.csp_policy:
            self.csp_policy = self._build_default_csp()

    def _build_default_csp(self) -> str:
        """Build default Content Security Policy."""
        # Secure default CSP
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # unsafe-inline often needed for UI frameworks
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
        ]

        # Add report URI if configured
        if self.csp_report_uri:
            directives.append(f"report-uri {self.csp_report_uri}")

        return "; ".join(directives)

    def get_headers(self) -> Dict[str, str]:
        """
        Get all security headers as a dictionary.

        Returns:
            Dictionary of header name -> value
        """
        headers = {}

        # HSTS
        if self.hsts_enabled:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            headers['Strict-Transport-Security'] = hsts_value

        # CSP
        if self.csp_enabled and self.csp_policy:
            header_name = 'Content-Security-Policy-Report-Only' if self.csp_report_only else 'Content-Security-Policy'
            headers[header_name] = self.csp_policy

        # X-Frame-Options
        if self.frame_options:
            if self.frame_options.upper() == 'ALLOW-FROM' and self.frame_options_allow_from:
                headers['X-Frame-Options'] = f"ALLOW-FROM {self.frame_options_allow_from}"
            else:
                headers['X-Frame-Options'] = self.frame_options.upper()

        # X-Content-Type-Options
        if self.content_type_nosniff:
            headers['X-Content-Type-Options'] = 'nosniff'

        # X-XSS-Protection
        if self.xss_protection:
            value = '1'
            if self.xss_protection_block:
                value += '; mode=block'
            headers['X-XSS-Protection'] = value

        # Referrer-Policy
        if self.referrer_policy:
            headers['Referrer-Policy'] = self.referrer_policy

        # Permissions-Policy
        if self.permissions_policy:
            headers['Permissions-Policy'] = self.permissions_policy

        # Cache-Control for API responses
        headers['Cache-Control'] = self.cache_control

        # Prevent caching of authenticated responses
        headers['Pragma'] = 'no-cache'

        # Add custom headers
        headers.update(self.custom_headers)

        return headers


# Global security headers configuration
_security_headers: Optional[SecurityHeaders] = None


def get_security_headers() -> SecurityHeaders:
    """Get global security headers configuration."""
    global _security_headers
    if _security_headers is None:
        _security_headers = SecurityHeaders()
    return _security_headers


def configure_security_headers(
    app,
    config: Optional[SecurityHeaders] = None,
    use_talisman: bool = False
):
    """
    Configure security headers for Flask application.

    Args:
        app: Flask application instance
        config: Optional custom security headers configuration
        use_talisman: Whether to use Flask-Talisman (if available)
    """
    headers_config = config or get_security_headers()

    if use_talisman:
        try:
            from flask_talisman import Talisman

            # Parse CSP for Talisman format
            csp = None
            if headers_config.csp_enabled and headers_config.csp_policy:
                csp = _parse_csp_for_talisman(headers_config.csp_policy)

            Talisman(
                app,
                force_https=os.getenv('FLASK_ENV') == 'production',
                strict_transport_security=headers_config.hsts_enabled,
                strict_transport_security_max_age=headers_config.hsts_max_age,
                strict_transport_security_include_subdomains=headers_config.hsts_include_subdomains,
                strict_transport_security_preload=headers_config.hsts_preload,
                content_security_policy=csp,
                content_security_policy_report_only=headers_config.csp_report_only,
                frame_options=headers_config.frame_options,
                frame_options_allow_from=headers_config.frame_options_allow_from,
                referrer_policy=headers_config.referrer_policy,
                permissions_policy=headers_config.permissions_policy,
                session_cookie_secure=True,
                session_cookie_http_only=True,
                session_cookie_samesite='Lax',
            )
            logger.info("Security headers configured via Flask-Talisman")
            return headers_config

        except ImportError:
            logger.warning("Flask-Talisman not available, using manual headers")

    # Manual header injection
    @app.after_request
    def add_security_headers(response):
        """Add security headers to response."""
        # Don't add to static files or health checks
        if request.path.startswith('/static') or request.path == '/api/v1/health':
            return response

        headers = headers_config.get_headers()
        for key, value in headers.items():
            response.headers[key] = value

        return response

    logger.info("Security headers configured manually")
    return headers_config


def _parse_csp_for_talisman(csp_string: str) -> dict:
    """
    Parse CSP string into Talisman dictionary format.

    Args:
        csp_string: CSP policy string

    Returns:
        Dictionary suitable for Talisman
    """
    csp = {}
    for directive in csp_string.split(';'):
        directive = directive.strip()
        if not directive:
            continue

        parts = directive.split()
        if len(parts) >= 2:
            key = parts[0].replace('-', '_')
            values = parts[1:]
            csp[key] = values

    return csp


def add_security_headers(response):
    """
    Add security headers to a Flask response.

    Usage:
        @app.route('/api/sensitive')
        def sensitive_endpoint():
            response = make_response(jsonify({'data': 'secret'}))
            return add_security_headers(response)

    Args:
        response: Flask response object

    Returns:
        Response with security headers added
    """
    headers_config = get_security_headers()
    headers = headers_config.get_headers()

    for key, value in headers.items():
        response.headers[key] = value

    return response


def create_security_headers_for_api() -> SecurityHeaders:
    """
    Create security headers configuration optimized for API endpoints.

    Returns:
        SecurityHeaders configured for API use
    """
    return SecurityHeaders(
        # APIs don't need HSTS in response (should be handled at load balancer)
        hsts_enabled=os.getenv('FLASK_ENV') == 'production',
        # Stricter CSP for APIs
        csp_policy="default-src 'none'; frame-ancestors 'none'",
        # Prevent framing
        frame_options='DENY',
        # API responses should never be cached
        cache_control='no-store, no-cache, must-revalidate, private, max-age=0',
    )


# Import request at module level
try:
    from flask import request
except ImportError:
    request = None
