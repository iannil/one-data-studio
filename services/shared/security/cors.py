"""
CORS Configuration Module
Sprint 21: Security Hardening

Provides configurable CORS (Cross-Origin Resource Sharing) settings.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CORSConfig:
    """
    CORS Configuration.

    Implements secure defaults while allowing customization
    for specific deployment scenarios.
    """

    # Allowed origins (explicit list for production)
    origins: List[str] = field(default_factory=lambda: _get_allowed_origins())

    # Allowed HTTP methods
    methods: List[str] = field(default_factory=lambda: [
        'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'
    ])

    # Allowed headers
    allowed_headers: List[str] = field(default_factory=lambda: [
        'Content-Type',
        'Authorization',
        'X-Requested-With',
        'X-CSRF-Token',
        'Accept',
        'Accept-Language',
        'Origin',
    ])

    # Headers exposed to the browser
    expose_headers: List[str] = field(default_factory=lambda: [
        'Content-Length',
        'Content-Type',
        'X-Request-Id',
        'X-CSRF-Token',
    ])

    # Allow credentials (cookies, authorization headers)
    supports_credentials: bool = True

    # Preflight cache duration (seconds)
    max_age: int = 600

    # Whether to allow all origins (DANGEROUS - DISABLED for security)
    # NOTE: This option has been removed for security. Always configure explicit origins.
    allow_all_origins: bool = False

    def __post_init__(self):
        """Validate configuration."""
        # Force disable allow_all_origins in all environments
        env_allow_all = os.getenv('CORS_ALLOW_ALL', 'false').lower() == 'true'
        if env_allow_all:
            logger.warning(
                "CORS_ALLOW_ALL environment variable is set but will be ignored. "
                "Configure explicit origins using CORS_ALLOWED_ORIGINS instead."
            )
        self.allow_all_origins = False

        if not self.origins and os.getenv('FLASK_ENV') == 'production':
            logger.warning("No CORS origins configured for production. Set CORS_ALLOWED_ORIGINS.")

    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin is allowed.

        Args:
            origin: The Origin header value

        Returns:
            True if origin is allowed
        """
        if self.allow_all_origins:
            return True

        if not origin:
            return False

        # Normalize origin
        origin = origin.lower().rstrip('/')

        for allowed in self.origins:
            allowed = allowed.lower().rstrip('/')

            # Exact match
            if origin == allowed:
                return True

            # Wildcard subdomain match (e.g., *.example.com)
            if allowed.startswith('*.'):
                domain = allowed[2:]
                if origin.endswith(domain) or origin == f"https://{domain}" or origin == f"http://{domain}":
                    return True

        return False

    def get_cors_headers(self, origin: str) -> Dict[str, str]:
        """
        Get CORS headers for a response.

        Args:
            origin: The request Origin

        Returns:
            Dictionary of CORS headers
        """
        headers = {}

        if self.allow_all_origins:
            headers['Access-Control-Allow-Origin'] = '*'
        elif self.is_origin_allowed(origin):
            headers['Access-Control-Allow-Origin'] = origin
            # Vary header required when origin is dynamic
            headers['Vary'] = 'Origin'
        else:
            return {}  # No CORS headers for disallowed origin

        if self.supports_credentials and not self.allow_all_origins:
            headers['Access-Control-Allow-Credentials'] = 'true'

        headers['Access-Control-Allow-Methods'] = ', '.join(self.methods)
        headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        headers['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
        headers['Access-Control-Max-Age'] = str(self.max_age)

        return headers


def _get_allowed_origins() -> List[str]:
    """
    Get allowed origins from environment.

    Format: CORS_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"
    """
    origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')

    if origins_env:
        return [o.strip() for o in origins_env.split(',') if o.strip()]

    # Default origins for development
    if os.getenv('FLASK_ENV') != 'production':
        return [
            'http://localhost:3000',
            'http://localhost:5173',
            'http://localhost:8080',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173',
            'http://127.0.0.1:8080',
        ]

    # Production: require explicit configuration
    logger.warning("No CORS_ALLOWED_ORIGINS configured. Set this in production.")
    return []


# Global CORS configuration
_cors_config: Optional[CORSConfig] = None


def get_cors_config() -> CORSConfig:
    """Get global CORS configuration."""
    global _cors_config
    if _cors_config is None:
        _cors_config = CORSConfig()
    return _cors_config


def configure_cors(app, config: Optional[CORSConfig] = None):
    """
    Configure CORS for Flask application.

    Args:
        app: Flask application instance
        config: Optional custom CORS configuration
    """
    cors_config = config or get_cors_config()

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to response."""
        origin = request.headers.get('Origin')

        if origin:
            headers = cors_config.get_cors_headers(origin)
            for key, value in headers.items():
                response.headers[key] = value

        return response

    @app.route('/', methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_preflight(path=''):
        """Handle CORS preflight requests."""
        origin = request.headers.get('Origin')

        if not origin or not cors_config.is_origin_allowed(origin):
            return '', 403

        response = app.make_default_options_response()
        headers = cors_config.get_cors_headers(origin)
        for key, value in headers.items():
            response.headers[key] = value

        return response

    logger.info(f"CORS configured with {len(cors_config.origins)} allowed origins")
    return cors_config


def cors_allow(origins: Optional[List[str]] = None, methods: Optional[List[str]] = None):
    """
    CORS decorator for individual endpoints.

    Usage:
        @app.route('/api/public', methods=['GET'])
        @cors_allow(origins=['https://partner.example.com'])
        def public_endpoint():
            ...

    Args:
        origins: List of allowed origins for this endpoint
        methods: List of allowed methods for this endpoint
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, make_response

            # Handle preflight
            if request.method == 'OPTIONS':
                response = make_response()
            else:
                response = make_response(func(*args, **kwargs))

            origin = request.headers.get('Origin')
            if not origin:
                return response

            allowed = origins or get_cors_config().origins
            if origin in allowed or any(
                o.startswith('*.') and origin.endswith(o[1:]) for o in allowed
            ):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = ', '.join(
                    methods or get_cors_config().methods
                )
                response.headers['Access-Control-Allow-Headers'] = ', '.join(
                    get_cors_config().allowed_headers
                )

            return response

        return wrapper

    return decorator


# Import request at module level for use in functions
try:
    from flask import request
except ImportError:
    request = None
