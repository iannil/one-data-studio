"""
Security Module
Sprint 21: Security Hardening
Sprint 29: Data Encryption

Provides security features including:
- CSRF protection
- CORS configuration
- Security headers
- TLS configuration utilities
- Field-level encryption (AES-256-GCM)
"""

from .csrf import (
    CSRFProtection,
    generate_csrf_token,
    validate_csrf_token,
    csrf_protect,
    get_csrf_token_from_request,
)

from .cors import (
    CORSConfig,
    configure_cors,
    get_cors_config,
)

from .headers import (
    SecurityHeaders,
    configure_security_headers,
    add_security_headers,
)

from .tls import (
    TLSConfig,
    require_https,
    get_tls_config,
)

from .encryption import (
    EncryptionService,
    EncryptionConfig,
    EncryptionError,
    EncryptedField,
    get_encryption_service,
    encrypt,
    decrypt,
    is_encrypted,
    generate_encryption_key,
)

__all__ = [
    # CSRF
    'CSRFProtection',
    'generate_csrf_token',
    'validate_csrf_token',
    'csrf_protect',
    'get_csrf_token_from_request',
    # CORS
    'CORSConfig',
    'configure_cors',
    'get_cors_config',
    # Headers
    'SecurityHeaders',
    'configure_security_headers',
    'add_security_headers',
    # TLS
    'TLSConfig',
    'require_https',
    'get_tls_config',
    # Encryption
    'EncryptionService',
    'EncryptionConfig',
    'EncryptionError',
    'EncryptedField',
    'get_encryption_service',
    'encrypt',
    'decrypt',
    'is_encrypted',
    'generate_encryption_key',
]
