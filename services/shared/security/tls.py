"""
TLS Configuration Module
Sprint 21: Security Hardening

Provides TLS/HTTPS configuration utilities and enforcement.
"""

import os
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class TLSConfig:
    """
    TLS Configuration.

    Controls HTTPS enforcement and related settings.
    """

    # Force HTTPS redirect
    force_https: bool = field(default_factory=lambda:
        os.getenv('SECURITY_FORCE_HTTPS', 'true').lower() == 'true' and
        os.getenv('FLASK_ENV') == 'production'
    )

    # Trust proxy headers (X-Forwarded-Proto)
    trust_proxy: bool = field(default_factory=lambda:
        os.getenv('SECURITY_TRUST_PROXY', 'true').lower() == 'true'
    )

    # Proxy header names
    proto_header: str = field(default_factory=lambda:
        os.getenv('SECURITY_PROTO_HEADER', 'X-Forwarded-Proto')
    )

    # Paths exempt from HTTPS redirect
    exempt_paths: list = field(default_factory=lambda: [
        '/api/v1/health',
        '/metrics',
        '/.well-known/',  # ACME challenges
    ])

    # Minimum TLS version (for documentation/config generation)
    min_tls_version: str = 'TLSv1.2'

    # Recommended cipher suites
    cipher_suites: str = field(default_factory=lambda:
        os.getenv('SECURITY_CIPHER_SUITES',
            'ECDHE+AESGCM:DHE+AESGCM:ECDHE+CHACHA20:DHE+CHACHA20'
        )
    )

    def is_https(self, request) -> bool:
        """
        Check if request is over HTTPS.

        Args:
            request: Flask request object

        Returns:
            True if request is secure
        """
        # Direct HTTPS
        if request.is_secure:
            return True

        # Check proxy header
        if self.trust_proxy:
            proto = request.headers.get(self.proto_header, '')
            if proto.lower() == 'https':
                return True

        return False

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from HTTPS redirect."""
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True
        return False

    def get_https_url(self, request) -> str:
        """
        Get HTTPS version of current URL.

        Args:
            request: Flask request object

        Returns:
            HTTPS URL
        """
        url = request.url
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        return url


# Global TLS configuration
_tls_config: Optional[TLSConfig] = None


def get_tls_config() -> TLSConfig:
    """Get global TLS configuration."""
    global _tls_config
    if _tls_config is None:
        _tls_config = TLSConfig()
    return _tls_config


def require_https(app, config: Optional[TLSConfig] = None):
    """
    Configure HTTPS enforcement for Flask application.

    This should be used in production environments where TLS
    termination happens at a reverse proxy.

    Args:
        app: Flask application instance
        config: Optional custom TLS configuration
    """
    tls_config = config or get_tls_config()

    if not tls_config.force_https:
        logger.info("HTTPS enforcement disabled")
        return

    @app.before_request
    def enforce_https():
        """Redirect HTTP requests to HTTPS."""
        from flask import request, redirect

        # Skip exempt paths
        if tls_config.is_exempt(request.path):
            return None

        # Check if already HTTPS
        if tls_config.is_https(request):
            return None

        # Redirect to HTTPS
        https_url = tls_config.get_https_url(request)
        logger.debug(f"Redirecting to HTTPS: {request.url} -> {https_url}")
        return redirect(https_url, code=301)

    logger.info("HTTPS enforcement enabled")


def https_required(func: Callable) -> Callable:
    """
    Decorator to require HTTPS for specific endpoint.

    Usage:
        @app.route('/api/v1/sensitive')
        @https_required
        def sensitive_endpoint():
            ...

    Args:
        func: The function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request, redirect, jsonify

        tls_config = get_tls_config()

        if not tls_config.is_https(request):
            if tls_config.force_https:
                return redirect(tls_config.get_https_url(request), code=301)
            else:
                return jsonify({
                    'code': 40300,
                    'message': 'HTTPS required for this endpoint',
                    'error': 'https_required'
                }), 403

        return func(*args, **kwargs)

    return wrapper


def generate_nginx_tls_config(
    cert_path: str,
    key_path: str,
    dhparam_path: Optional[str] = None,
    config: Optional[TLSConfig] = None
) -> str:
    """
    Generate NGINX TLS configuration snippet.

    Args:
        cert_path: Path to SSL certificate
        key_path: Path to SSL private key
        dhparam_path: Path to DH parameters file (optional)
        config: TLS configuration

    Returns:
        NGINX configuration string
    """
    tls_config = config or get_tls_config()

    nginx_config = f"""
# TLS Configuration (generated)
ssl_certificate {cert_path};
ssl_certificate_key {key_path};

# TLS Protocols
ssl_protocols TLSv1.2 TLSv1.3;

# Cipher Suites
ssl_ciphers '{tls_config.cipher_suites}';
ssl_prefer_server_ciphers on;

# SSL Session
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;
"""

    if dhparam_path:
        nginx_config += f"""
# Diffie-Hellman Parameters
ssl_dhparam {dhparam_path};
"""

    nginx_config += """
# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
"""

    return nginx_config


def generate_ssl_context():
    """
    Generate Python SSL context for secure connections.

    Returns:
        ssl.SSLContext configured with secure defaults
    """
    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    # Load default CA certificates
    context.load_default_certs()

    return context
