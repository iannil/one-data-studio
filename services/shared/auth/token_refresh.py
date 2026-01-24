"""
Token Refresh Middleware
Sprint 21: Security Hardening

Provides automatic token refresh and HttpOnly cookie management.
"""

import os
import time
import logging
from typing import Optional, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

# Cookie configuration
COOKIE_NAME_ACCESS = os.getenv('AUTH_COOKIE_ACCESS', 'access_token')
COOKIE_NAME_REFRESH = os.getenv('AUTH_COOKIE_REFRESH', 'refresh_token')
COOKIE_DOMAIN = os.getenv('AUTH_COOKIE_DOMAIN')  # None = current domain
COOKIE_PATH = '/'
COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
COOKIE_SAMESITE = os.getenv('AUTH_COOKIE_SAMESITE', 'Lax')  # Lax allows top-level navigations
COOKIE_HTTPONLY = True

# Token refresh settings
TOKEN_REFRESH_THRESHOLD = int(os.getenv('TOKEN_REFRESH_THRESHOLD', '300'))  # 5 minutes


class TokenRefreshMiddleware:
    """
    Middleware for automatic token refresh and secure cookie management.

    Features:
    - Stores tokens in HttpOnly cookies (prevents XSS)
    - Automatically refreshes tokens before expiry
    - SameSite cookie attribute (prevents CSRF)
    """

    def __init__(self, app=None, keycloak_url: Optional[str] = None, client_id: Optional[str] = None):
        """
        Initialize the middleware.

        Args:
            app: Flask application instance
            keycloak_url: Keycloak server URL
            client_id: OAuth2 client ID
        """
        self.keycloak_url = keycloak_url or os.getenv(
            'KEYCLOAK_URL',
            'http://keycloak.one-data-system.svc.cluster.local:80'
        )
        self.realm = os.getenv('KEYCLOAK_REALM', 'one-data-studio')
        self.client_id = client_id or os.getenv('KEYCLOAK_CLIENT_ID', 'web-frontend')

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize middleware with Flask app.

        Args:
            app: Flask application instance
        """
        @app.after_request
        def refresh_token_if_needed(response):
            """Check and refresh token if close to expiry."""
            from flask import g, request

            # Skip if no authenticated user
            if not hasattr(g, 'payload') or not g.payload:
                return response

            # Check if token needs refresh
            exp = g.payload.get('exp', 0)
            current_time = time.time()

            if exp - current_time < TOKEN_REFRESH_THRESHOLD:
                # Token is close to expiry, try to refresh
                refresh_token = request.cookies.get(COOKIE_NAME_REFRESH)
                if refresh_token:
                    new_tokens = self._refresh_tokens(refresh_token)
                    if new_tokens:
                        self._set_token_cookies(response, new_tokens)
                        logger.debug("Token refreshed successfully")

            return response

        logger.info("Token refresh middleware initialized")

    def _refresh_tokens(self, refresh_token: str) -> Optional[dict]:
        """
        Refresh tokens using refresh_token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token dict or None if failed
        """
        try:
            import requests

            token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

            response = requests.post(
                token_url,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': self.client_id,
                },
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Token refresh failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None

    def _set_token_cookies(self, response, tokens: dict):
        """
        Set token cookies on response.

        Args:
            response: Flask response object
            tokens: Token dict from OAuth2 server
        """
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        expires_in = tokens.get('expires_in', 3600)

        if access_token:
            response.set_cookie(
                COOKIE_NAME_ACCESS,
                access_token,
                max_age=expires_in,
                secure=COOKIE_SECURE,
                httponly=COOKIE_HTTPONLY,
                samesite=COOKIE_SAMESITE,
                domain=COOKIE_DOMAIN,
                path=COOKIE_PATH,
            )

        if refresh_token:
            # Refresh token has longer expiry
            refresh_expires = tokens.get('refresh_expires_in', 604800)  # 7 days default
            response.set_cookie(
                COOKIE_NAME_REFRESH,
                refresh_token,
                max_age=refresh_expires,
                secure=COOKIE_SECURE,
                httponly=COOKIE_HTTPONLY,
                samesite=COOKIE_SAMESITE,
                domain=COOKIE_DOMAIN,
                path=COOKIE_PATH,
            )


def set_auth_cookies(response, tokens: dict):
    """
    Helper function to set authentication cookies.

    Args:
        response: Flask response object
        tokens: Token dict containing access_token and optionally refresh_token
    """
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')
    expires_in = tokens.get('expires_in', 3600)

    if access_token:
        response.set_cookie(
            COOKIE_NAME_ACCESS,
            access_token,
            max_age=expires_in,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path=COOKIE_PATH,
        )

    if refresh_token:
        refresh_expires = tokens.get('refresh_expires_in', 604800)
        response.set_cookie(
            COOKIE_NAME_REFRESH,
            refresh_token,
            max_age=refresh_expires,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path=COOKIE_PATH,
        )


def clear_auth_cookies(response):
    """
    Clear authentication cookies (for logout).

    Args:
        response: Flask response object
    """
    response.delete_cookie(
        COOKIE_NAME_ACCESS,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    response.delete_cookie(
        COOKIE_NAME_REFRESH,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )


def get_token_from_cookie_or_header():
    """
    Get access token from cookie (preferred) or Authorization header.

    Returns:
        Token string or None
    """
    try:
        from flask import request

        # Prefer cookie (more secure)
        token = request.cookies.get(COOKIE_NAME_ACCESS)
        if token:
            return token

        # Fallback to Authorization header (for API clients)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]

        return None

    except ImportError:
        logger.error("Flask not available")
        return None


def token_expires_soon(payload: dict, threshold: int = TOKEN_REFRESH_THRESHOLD) -> bool:
    """
    Check if token is close to expiry.

    Args:
        payload: Decoded JWT payload
        threshold: Seconds before expiry to consider "soon"

    Returns:
        True if token expires within threshold
    """
    exp = payload.get('exp', 0)
    return time.time() > exp - threshold


def init_token_refresh(app, keycloak_url: Optional[str] = None, client_id: Optional[str] = None):
    """
    Initialize token refresh middleware.

    Args:
        app: Flask application instance
        keycloak_url: Keycloak server URL
        client_id: OAuth2 client ID

    Returns:
        TokenRefreshMiddleware instance
    """
    middleware = TokenRefreshMiddleware(app, keycloak_url, client_id)
    return middleware
