"""
CORS Module Re-export
H-09: Create shared CORS module reference

This module re-exports the CORS functionality from the security submodule
for easier imports.
"""

from services.shared.security.cors import (
    CORSConfig,
    get_cors_config,
    configure_cors,
    cors_allow,
)

__all__ = [
    'CORSConfig',
    'get_cors_config',
    'configure_cors',
    'cors_allow',
]
