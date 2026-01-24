"""
CSRF Protection Module
Sprint 21: Security Hardening

Provides CSRF token generation and validation for API endpoints.
Uses Double Submit Cookie pattern for stateless CSRF protection.
"""

import os
import secrets
import hashlib
import hmac
import time
import logging
from typing import Optional, Callable, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

# CSRF Configuration
CSRF_SECRET_KEY = os.getenv('CSRF_SECRET_KEY') or os.getenv('JWT_SECRET_KEY')
if not CSRF_SECRET_KEY:
    raise ValueError("CSRF_SECRET_KEY or JWT_SECRET_KEY environment variable is required")
CSRF_TOKEN_LENGTH = 32
CSRF_TOKEN_EXPIRY = int(os.getenv('CSRF_TOKEN_EXPIRY', '3600'))  # 1 hour default
CSRF_HEADER_NAME = os.getenv('CSRF_HEADER_NAME', 'X-CSRF-Token')
CSRF_COOKIE_NAME = os.getenv('CSRF_COOKIE_NAME', 'csrf_token')


class CSRFError(Exception):
    """CSRF validation error"""
    pass


class CSRFProtection:
    """
    CSRF Protection using Double Submit Cookie pattern.

    The pattern works as follows:
    1. Server generates a CSRF token and sends it as a cookie
    2. Client must include the same token in a request header
    3. Server validates that cookie and header values match

    This prevents CSRF because:
    - Attacker cannot read the cookie value (SameSite + HttpOnly)
    - Attacker cannot set the header without knowing the token
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiry: int = CSRF_TOKEN_EXPIRY,
        header_name: str = CSRF_HEADER_NAME,
        cookie_name: str = CSRF_COOKIE_NAME,
        exempt_methods: Optional[list] = None,
        exempt_paths: Optional[list] = None,
    ):
        """
        Initialize CSRF protection.

        Args:
            secret_key: Secret key for signing tokens
            token_expiry: Token expiry time in seconds
            header_name: Name of the header containing CSRF token
            cookie_name: Name of the cookie containing CSRF token
            exempt_methods: HTTP methods exempt from CSRF (default: GET, HEAD, OPTIONS)
            exempt_paths: URL paths exempt from CSRF protection
        """
        self.secret_key = secret_key or CSRF_SECRET_KEY
        self.token_expiry = token_expiry
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.exempt_methods = exempt_methods or ['GET', 'HEAD', 'OPTIONS']
        self.exempt_paths = exempt_paths or [
            '/api/v1/health',
            '/metrics',
            '/api/v1/auth/login',
            '/api/v1/auth/callback',
        ]

    def generate_token(self, session_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate a new CSRF token.

        Args:
            session_id: Optional session identifier for additional binding

        Returns:
            Tuple of (token, signature) where signature includes timestamp
        """
        # Generate random token
        token = secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

        # Create timestamp
        timestamp = str(int(time.time()))

        # Create signature
        message = f"{token}:{timestamp}"
        if session_id:
            message = f"{message}:{session_id}"

        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        # Return token with embedded timestamp and signature
        signed_token = f"{token}.{timestamp}.{signature}"
        return token, signed_token

    def validate_token(
        self,
        token: str,
        signed_token: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Validate a CSRF token.

        Args:
            token: The raw token from header
            signed_token: The signed token from cookie
            session_id: Optional session identifier

        Returns:
            True if valid, False otherwise
        """
        try:
            # Parse signed token
            parts = signed_token.split('.')
            if len(parts) != 3:
                logger.warning("Invalid CSRF token format")
                return False

            stored_token, timestamp, stored_signature = parts

            # Check if tokens match
            if not secrets.compare_digest(token, stored_token):
                logger.warning("CSRF token mismatch")
                return False

            # Check timestamp
            token_time = int(timestamp)
            current_time = int(time.time())
            if current_time - token_time > self.token_expiry:
                logger.warning("CSRF token expired")
                return False

            # Verify signature
            message = f"{stored_token}:{timestamp}"
            if session_id:
                message = f"{message}:{session_id}"

            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            if not secrets.compare_digest(stored_signature, expected_signature):
                logger.warning("CSRF signature mismatch")
                return False

            return True

        except Exception as e:
            logger.warning(f"CSRF validation error: {e}")
            return False

    def is_exempt(self, method: str, path: str) -> bool:
        """Check if request is exempt from CSRF protection."""
        if method.upper() in self.exempt_methods:
            return True
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False


# Global CSRF protection instance
_csrf_protection: Optional[CSRFProtection] = None


def get_csrf_protection() -> CSRFProtection:
    """Get global CSRF protection instance."""
    global _csrf_protection
    if _csrf_protection is None:
        _csrf_protection = CSRFProtection()
    return _csrf_protection


def generate_csrf_token(session_id: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate a new CSRF token.

    Args:
        session_id: Optional session identifier

    Returns:
        Tuple of (raw_token, signed_token)
    """
    return get_csrf_protection().generate_token(session_id)


def validate_csrf_token(
    token: str,
    signed_token: str,
    session_id: Optional[str] = None
) -> bool:
    """
    Validate a CSRF token.

    Args:
        token: Raw token from header
        signed_token: Signed token from cookie
        session_id: Optional session identifier

    Returns:
        True if valid
    """
    return get_csrf_protection().validate_token(token, signed_token, session_id)


def get_csrf_token_from_request():
    """
    Get CSRF token from Flask request.

    Returns:
        Tuple of (header_token, cookie_token) or (None, None)
    """
    try:
        from flask import request

        csrf = get_csrf_protection()
        header_token = request.headers.get(csrf.header_name)
        cookie_token = request.cookies.get(csrf.cookie_name)

        return header_token, cookie_token
    except ImportError:
        logger.error("Flask not available")
        return None, None


def csrf_protect(func: Optional[Callable] = None, exempt: bool = False):
    """
    CSRF protection decorator for Flask endpoints.

    Usage:
        @app.route('/api/v1/data', methods=['POST'])
        @csrf_protect
        def create_data():
            ...

        # Exempt specific endpoint
        @app.route('/api/v1/webhook', methods=['POST'])
        @csrf_protect(exempt=True)
        def webhook_handler():
            ...

    Args:
        func: The function to decorate
        exempt: If True, skip CSRF protection
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if exempt:
                return f(*args, **kwargs)

            try:
                from flask import request, jsonify
            except ImportError:
                return f(*args, **kwargs)

            csrf = get_csrf_protection()

            # Check if exempt
            if csrf.is_exempt(request.method, request.path):
                return f(*args, **kwargs)

            # Get tokens
            header_token = request.headers.get(csrf.header_name)
            cookie_token = request.cookies.get(csrf.cookie_name)

            # Validate
            if not header_token or not cookie_token:
                logger.warning(f"CSRF token missing for {request.method} {request.path}")
                return jsonify({
                    'code': 40300,
                    'message': 'CSRF token missing',
                    'error': 'csrf_token_required'
                }), 403

            # Get session ID if available
            session_id = None
            try:
                from flask import g
                session_id = getattr(g, 'session_id', None)
            except Exception as e:
                logger.debug(f"Could not retrieve session_id for CSRF validation: {e}")

            if not csrf.validate_token(header_token, cookie_token, session_id):
                logger.warning(f"CSRF validation failed for {request.method} {request.path}")
                return jsonify({
                    'code': 40300,
                    'message': 'CSRF validation failed',
                    'error': 'csrf_token_invalid'
                }), 403

            return f(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def init_csrf_protection(app):
    """
    Initialize CSRF protection for Flask app.

    Sets up:
    - CSRF token generation on responses
    - Automatic CSRF validation on state-changing requests

    Args:
        app: Flask application instance
    """
    csrf = get_csrf_protection()

    @app.after_request
    def add_csrf_cookie(response):
        """Add CSRF cookie to responses."""
        # Only add cookie for HTML/JSON responses
        content_type = response.content_type or ''
        if 'text/html' in content_type or 'application/json' in content_type:
            # Check if cookie already exists
            if csrf.cookie_name not in request.cookies:
                # Generate new token
                raw_token, signed_token = csrf.generate_token()

                # Set cookie with security attributes
                response.set_cookie(
                    csrf.cookie_name,
                    signed_token,
                    max_age=csrf.token_expiry,
                    secure=os.getenv('FLASK_ENV') == 'production',
                    httponly=False,  # Must be readable by JavaScript
                    samesite='Strict',
                    path='/'
                )

                # Also add raw token in header for convenience
                response.headers['X-CSRF-Token'] = raw_token

        return response

    @app.before_request
    def validate_csrf():
        """Validate CSRF token on state-changing requests."""
        from flask import request, jsonify, g

        # Check if exempt
        if csrf.is_exempt(request.method, request.path):
            return None

        # Get tokens
        header_token = request.headers.get(csrf.header_name)
        cookie_token = request.cookies.get(csrf.cookie_name)

        # Validate
        if not header_token or not cookie_token:
            return jsonify({
                'code': 40300,
                'message': 'CSRF token missing',
                'error': 'csrf_token_required'
            }), 403

        session_id = getattr(g, 'session_id', None)
        if not csrf.validate_token(header_token, cookie_token, session_id):
            return jsonify({
                'code': 40300,
                'message': 'CSRF validation failed',
                'error': 'csrf_token_invalid'
            }), 403

        return None

    logger.info("CSRF protection initialized")
    return csrf
