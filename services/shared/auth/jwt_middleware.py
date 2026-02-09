"""
JWT 认证中间件
Sprint 3.1: 为所有后端 API 提供统一的 JWT 认证

功能：
- JWT Token 验证
- Keycloak RS256 公钥验证
- Token 自动刷新
- 用户信息提取
"""

import os
import jwt
import time
import requests
import logging
from functools import wraps
from flask import request, jsonify, g
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from typing import Dict, Optional, List

# 配置日志
logger = logging.getLogger(__name__)

# Keycloak 配置
KEYCLOAK_URL = os.getenv(
    "KEYCLOAK_URL",
    "http://keycloak.one-data-system.svc.cluster.local:80"
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "one-data-studio")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "web-frontend")

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# AUTH_MODE: Enable/disable authentication (development only)
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"

# SSL verification for external requests
# In production, this should always be True. Only disable for local development with self-signed certs.
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

# SECURITY: Critical checks for production environment
if IS_PRODUCTION:
    if not AUTH_MODE:
        raise ValueError(
            "CRITICAL: AUTH_MODE cannot be disabled in production environment. "
            "Remove AUTH_MODE=false or set ENVIRONMENT to a non-production value."
        )
    if not VERIFY_SSL:
        raise ValueError(
            "CRITICAL: VERIFY_SSL cannot be disabled in production environment."
        )
elif not AUTH_MODE:
    logger.warning(
        "SECURITY WARNING: AUTH_MODE is disabled. All requests will bypass authentication. "
        "This should ONLY be used for local development."
    )
elif not VERIFY_SSL:
    logger.warning(
        "SECURITY WARNING: SSL verification is disabled. This should ONLY be used for local development."
    )

# SECURITY: In production, optional=True only applies to explicitly whitelisted endpoints
# Configure via environment variable (comma-separated paths)
# Example: PUBLIC_API_ENDPOINTS=/api/v1/health,/api/v1/public/*
PUBLIC_API_ENDPOINTS = set(
    endpoint.strip()
    for endpoint in os.getenv("PUBLIC_API_ENDPOINTS", "").split(",")
    if endpoint.strip()
)

# SECURITY: Strict authentication mode for production
# When enabled, optional=True is ignored unless endpoint is explicitly public
STRICT_AUTH_MODE = os.getenv("STRICT_AUTH_MODE", "true" if IS_PRODUCTION else "false").lower() == "true"

# JWT audience validation - comma-separated list of allowed audiences
# SECURITY: Always configure this for production to prevent token misuse
JWT_ALLOWED_AUDIENCES = os.getenv(
    "JWT_ALLOWED_AUDIENCES",
    "account,web-frontend"  # Default audiences for Keycloak
).split(",")

# Token 缓存
_public_key_cache = None
_public_key_cache_time = 0
PUBLIC_KEY_CACHE_TTL = 300  # 5 分钟


def get_keycloak_public_key() -> Optional[str]:
    """
    从 Keycloak 获取 Realm 公钥

    Returns:
        PEM 格式的公钥字符串
    """
    global _public_key_cache, _public_key_cache_time

    current_time = time.time()
    if _public_key_cache and (current_time - _public_key_cache_time) < PUBLIC_KEY_CACHE_TTL:
        return _public_key_cache

    try:
        # 获取 Keycloak Realm 公钥
        url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        certs_data = response.json()

        # 提取公钥并转换为 PEM 格式
        for key in certs_data.get("keys", []):
            if key.get("kty") == "RSA" and key.get("use") == "sig":
                # 构建 PEM 格式公钥
                n = int.from_bytes(jwt.utils.base64url_decode(key["n"]), "big")
                e = int.from_bytes(jwt.utils.base64url_decode(key["e"]), "big")

                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization

                public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode("utf-8")

                _public_key_cache = pem
                _public_key_cache_time = current_time
                logger.info("Successfully fetched and cached Keycloak public key")
                return pem

        logger.warning("No suitable RSA key found in Keycloak certs")
        return None

    except Exception as e:
        logger.error(f"Failed to fetch Keycloak public key: {e}")
        # 返回缓存值（如果存在）
        return _public_key_cache


def decode_jwt_token(token: str) -> Optional[Dict]:
    """
    解码并验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的 Token Payload，验证失败返回 None
    """
    try:
        public_key = get_keycloak_public_key()
        if not public_key:
            logger.warning("No public key available for JWT verification")
            return None

        # 验证并解码 Token
        # SECURITY: Audience verification enabled to prevent cross-client token abuse
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=JWT_ALLOWED_AUDIENCES,
            issuer=f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}",
            options={
                "verify_aud": True,  # SECURITY: Always verify audience in production
                "verify_exp": True,
            }
        )

        # 检查 Token 是否过期
        exp = payload.get("exp")
        if exp and exp < time.time():
            logger.warning("Token has expired")
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


def extract_token_from_request(request_obj) -> Optional[str]:
    """
    从请求中提取 JWT Token

    优先级：
    1. Authorization Header (Bearer token)
    2. 查询参数 access_token
    3. Cookie access_token

    Args:
        request_obj: Flask Request 对象

    Returns:
        JWT Token 字符串或 None
    """
    # 1. Authorization Header
    auth_header = request_obj.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    # 2. 查询参数
    token = request_obj.args.get("access_token")
    if token:
        return token

    # 3. Cookie
    token = request_obj.cookies.get("access_token")
    if token:
        return token

    return None


def get_user_roles(payload: Dict) -> List[str]:
    """
    从 Token Payload 中提取用户角色

    Args:
        payload: JWT Token Payload

    Returns:
        角色列表
    """
    # Keycloak roles 可能在不同位置
    roles = []

    # resource_access (client-specific roles)
    resource_access = payload.get("resource_access", {})
    for client, client_data in resource_access.items():
        roles.extend(client_data.get("roles", []))

    # realm_access (realm roles)
    realm_access = payload.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))

    return roles


def _is_public_endpoint(path: str) -> bool:
    """
    Check if the endpoint is explicitly marked as public.

    Args:
        path: Request path

    Returns:
        True if endpoint is public
    """
    import fnmatch

    for pattern in PUBLIC_API_ENDPOINTS:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def require_jwt(optional: bool = False):
    """
    JWT 认证装饰器

    Args:
        optional: 是否可选（True 时未认证也能通过，但 g.user 为 None）

    SECURITY NOTE:
        In production (STRICT_AUTH_MODE=true), optional=True is only honored
        if the endpoint is explicitly listed in PUBLIC_API_ENDPOINTS.
        This prevents accidental exposure of data through misconfigured endpoints.

    Usage:
        @app.route("/api/v1/datasets")
        @require_jwt()
        def list_datasets():
            user = g.user
            roles = g.roles
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 开发模式: 跳过认证检查
            if not AUTH_MODE:
                g.user = "dev_user"
                g.user_id = "dev_user_001"
                g.email = "dev@example.com"
                g.name = "Development User"
                g.roles = ["admin"]
                g.payload = {"sub": "dev_user_001"}
                return fn(*args, **kwargs)

            # Determine if authentication is truly optional
            # In strict mode, optional is only honored for explicit public endpoints
            is_optional = optional
            if STRICT_AUTH_MODE and optional:
                path = request.path
                if not _is_public_endpoint(path):
                    # Log warning about optional auth being ignored
                    logger.warning(
                        f"STRICT_AUTH_MODE: optional=True ignored for endpoint {path}. "
                        f"Add to PUBLIC_API_ENDPOINTS if this should be public."
                    )
                    is_optional = False

            # 提取 Token
            token = extract_token_from_request(request)

            if not token:
                if is_optional:
                    g.user = None
                    g.roles = []
                    g.user_id = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "code": 40100,
                    "message": "Missing authentication token",
                    "error": "unauthorized"
                }), 401

            # 验证 Token
            payload = decode_jwt_token(token)

            if not payload:
                if is_optional:
                    g.user = None
                    g.roles = []
                    g.user_id = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "code": 40101,
                    "message": "Invalid or expired token",
                    "error": "invalid_token"
                }), 401

            # 存储用户信息到 Flask g 对象
            g.user = payload.get("preferred_username") or payload.get("email") or payload.get("sub")
            g.user_id = payload.get("sub")
            g.email = payload.get("email")
            g.name = payload.get("name")
            g.roles = get_user_roles(payload)
            g.payload = payload

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_role(*required_roles: str):
    """
    角色权限验证装饰器

    需要与 @require_jwt() 配合使用

    Args:
        *required_roles: 需要的角色列表（满足其一即可）

    Usage:
        @app.route("/api/v1/admin/users")
        @require_jwt()
        @require_role("admin", "super_admin")
        def admin_users():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 开发模式: 跳过角色检查
            if not AUTH_MODE:
                return fn(*args, **kwargs)

            if not hasattr(g, 'roles'):
                return jsonify({
                    "code": 40100,
                    "message": "Authentication required",
                    "error": "unauthorized"
                }), 401

            user_roles = g.roles if g.roles else []

            # 检查是否有任一所需角色
            if not any(role in user_roles for role in required_roles):
                return jsonify({
                    "code": 40300,
                    "message": f"Insufficient permissions. Required roles: {', '.join(required_roles)}",
                    "error": "forbidden",
                    "required_roles": list(required_roles),
                    "user_roles": user_roles
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def get_current_user() -> Optional[Dict]:
    """
    获取当前登录用户信息

    Returns:
        用户信息字典或 None
    """
    if hasattr(g, 'payload') and g.payload:
        return {
            "user_id": g.user_id,
            "username": g.user,
            "email": g.email,
            "name": g.name,
            "roles": g.roles if hasattr(g, 'roles') else []
        }
    return None


# 健康检查 - 不需要认证
HEALTH_CHECK_ENDPOINTS = ["/health", "/readiness", "/metrics", "/api/v1/health"]


def is_health_check_endpoint(request_obj) -> bool:
    """判断是否为健康检查端点"""
    path = request_obj.path
    for endpoint in HEALTH_CHECK_ENDPOINTS:
        if path.startswith(endpoint):
            return True
    return False


def check_permission(resource: str, operation: str, roles: List[str]) -> bool:
    """
    检查角色是否有指定资源的操作权限

    Args:
        resource: 资源类型
        operation: 操作类型
        roles: 用户角色列表

    Returns:
        是否有权限
    """
    if "admin" in roles:
        return True

    from .permissions import ROLE_PERMISSIONS
    for role in roles:
        if role in ROLE_PERMISSIONS:
            if (resource, operation) in ROLE_PERMISSIONS[role]:
                return True

    return False


# ============= Token 管理端点辅助函数 =============

def refresh_token(refresh_token_str: str) -> Optional[Dict]:
    """
    刷新访问 Token

    Args:
        refresh_token_str: 刷新令牌

    Returns:
        新的 Token 信息或 None
    """
    try:
        client_id = os.getenv("KEYCLOAK_CLIENT_ID", "web-frontend")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        if not client_secret:
            logger.warning("KEYCLOAK_CLIENT_SECRET not set, token refresh may fail")

        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_str,
                "client_id": client_id,
                "client_secret": client_secret,
            } if client_secret else {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_str,
                "client_id": client_id,
            },
            timeout=5,
            verify=VERIFY_SSL
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
    return None


def logout_user(token: str) -> bool:
    """
    登出用户（使 Token 失效）

    Args:
        token: 刷新令牌

    Returns:
        是否成功
    """
    try:
        client_id = os.getenv("KEYCLOAK_CLIENT_ID", "web-frontend")
        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout",
            data={
                "client_id": client_id,
                "refresh_token": token,
            },
            timeout=5,
            verify=VERIFY_SSL
        )
        return response.status_code == 204
    except Exception as e:
        logger.warning(f"Logout failed: {e}")
    return False


def introspect_token(token: str, client_id: Optional[str] = None) -> Optional[Dict]:
    """
    Token 内省 (降级方案)

    使用 Keycloak token introspection 端点验证 token

    Args:
        token: JWT token
        client_id: 客户端 ID (可选，默认从环境变量获取)

    Returns:
        Token payload 或 None
    """
    try:
        _client_id = client_id or os.getenv("KEYCLOAK_CLIENT_ID", "web-frontend")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        if not client_secret:
            logger.warning("KEYCLOAK_CLIENT_SECRET not set, token introspection may fail")
            return None
        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect",
            data={
                "token": token,
                "client_id": _client_id,
                "client_secret": client_secret,
            },
            timeout=5,
            verify=VERIFY_SSL
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Token introspection failed: {e}")
    return None
