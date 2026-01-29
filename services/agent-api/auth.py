"""
Agent API 认证模块
P5: 使用 Keycloak JWT 进行身份验证和授权

功能：
- JWT Token 验证 (RS256)
- 角色权限检查 (RBAC)
- Token 刷新和登出支持
- 与共享 JWT 中间件集成
"""

import logging
import os
import functools
import requests
from typing import Dict, List, Optional, Callable
from flask import g, request, jsonify

logger = logging.getLogger(__name__)

# Keycloak 配置
KEYCLOAK_URL = os.getenv(
    "KEYCLOAK_URL",
    "http://keycloak:8080"
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "one-data")
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"

# 尝试导入共享 JWT 中间件
try:
    import sys
    sys.path.insert(0, '/app/shared')
    from auth.jwt_middleware import (
        verify_jwt_token,
        get_keycloak_public_key,
        extract_token_from_request,
        get_user_roles,
        decode_jwt_token,
        get_current_user as get_shared_user
    )
    JWT_SHARED_AVAILABLE = True
except ImportError:
    JWT_SHARED_AVAILABLE = False
    # 降级实现
    def extract_token_from_request(request_obj):
        auth_header = request_obj.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def get_user_roles(payload: Dict) -> List[str]:
        roles = []
        resource_access = payload.get("resource_access", {})
        for client, client_data in resource_access.items():
            roles.extend(client_data.get("roles", []))
        realm_access = payload.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))
        return roles


# ============= 资源和操作定义 =============

class Resource:
    """资源类型定义"""
    WORKFLOW = "workflow"
    CHAT = "chat"
    AGENT = "agent"
    SCHEDULE = "schedule"
    DOCUMENT = "document"
    EXECUTION = "execution"
    TEMPLATE = "template"


class Operation:
    """操作类型定义"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


# ============= 权限矩阵 =============

# 默认权限矩阵 (角色 -> 资源 -> 操作)
DEFAULT_PERMISSIONS = {
    "admin": {
        Resource.WORKFLOW: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.EXECUTE],
        Resource.CHAT: [Operation.READ, Operation.CREATE, Operation.EXECUTE],
        Resource.AGENT: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.EXECUTE],
        Resource.SCHEDULE: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.MANAGE],
        Resource.DOCUMENT: [Operation.READ, Operation.CREATE, Operation.DELETE],
        Resource.EXECUTION: [Operation.READ, Operation.DELETE],
        Resource.TEMPLATE: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE],
    },
    "user": {
        Resource.WORKFLOW: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.EXECUTE],
        Resource.CHAT: [Operation.READ, Operation.CREATE, Operation.EXECUTE],
        Resource.AGENT: [Operation.READ, Operation.CREATE, Operation.EXECUTE],
        Resource.SCHEDULE: [Operation.READ],
        Resource.DOCUMENT: [Operation.READ, Operation.CREATE],
        Resource.EXECUTION: [Operation.READ],
        Resource.TEMPLATE: [Operation.READ],
    },
    "viewer": {
        Resource.WORKFLOW: [Operation.READ],
        Resource.CHAT: [Operation.READ],
        Resource.AGENT: [Operation.READ],
        Resource.SCHEDULE: [Operation.READ],
        Resource.DOCUMENT: [Operation.READ],
        Resource.EXECUTION: [Operation.READ],
        Resource.TEMPLATE: [Operation.READ],
    },
}


# ============= JWT 认证装饰器 =============

def require_jwt(optional: bool = False) -> Callable:
    """
    JWT 认证装饰器

    Args:
        optional: 是否可选（True 时未认证也能通过，但 g.user 为 None）

    Usage:
        @app.route("/api/v1/chat")
        @require_jwt()
        def chat():
            user = g.user
            roles = g.roles
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # 跳过认证检查
            if not AUTH_MODE:
                g.user = "dev_user"
                g.roles = ["admin"]
                g.payload = {}
                return fn(*args, **kwargs)

            # 提取 Token
            token = extract_token_from_request(request)

            if not token:
                if optional:
                    g.user = None
                    g.roles = []
                    g.payload = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "code": 40100,
                    "message": "Missing authentication token",
                    "error": "unauthorized"
                }), 401

            # 验证 Token
            if JWT_SHARED_AVAILABLE:
                payload = decode_jwt_token(token)
            else:
                # 降级方案: 调用 Keycloak token introspection
                payload = _introspect_token(token)

            if not payload or not payload.get("active", True):
                if optional:
                    g.user = None
                    g.roles = []
                    g.payload = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "code": 40101,
                    "message": "Invalid or expired token",
                    "error": "invalid_token"
                }), 401

            # 存储用户信息到 Flask g 对象
            g.payload = payload
            g.user = payload.get("preferred_username") or payload.get("email") or payload.get("sub", "unknown")
            g.user_id = payload.get("sub")
            g.email = payload.get("email")
            g.name = payload.get("name")
            g.roles = get_user_roles(payload)

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def _introspect_token(token: str) -> Optional[Dict]:
    """
    Token 内省 (降级方案)

    使用 Keycloak token introspection 端点验证 token
    """
    try:
        client_id = os.getenv("KEYCLOAK_CLIENT_ID", "agent-api")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        if not client_secret:
            logger.warning("KEYCLOAK_CLIENT_SECRET not set, token introspection may fail")
            return None
        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect",
            data={
                "token": token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Token introspection failed: {e}")
    return None


# ============= 权限检查装饰器 =============

def require_role(*required_roles: str) -> Callable:
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
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not AUTH_MODE:
                return fn(*args, **kwargs)

            if not hasattr(g, 'roles') or not g.roles:
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


def require_permission(resource: str, operation: str) -> Callable:
    """
    资源操作权限检查装饰器

    需要与 @require_jwt() 配合使用

    Args:
        resource: 资源类型 (如 Resource.WORKFLOW)
        operation: 操作类型 (如 Operation.CREATE)

    Usage:
        @app.route("/api/v1/workflows", methods=["POST"])
        @require_jwt()
        @require_permission(Resource.WORKFLOW, Operation.CREATE)
        def create_workflow():
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not AUTH_MODE:
                return fn(*args, **kwargs)

            # 管理员拥有所有权限
            if hasattr(g, 'roles') and "admin" in g.roles:
                return fn(*args, **kwargs)

            if not hasattr(g, 'roles'):
                return jsonify({
                    "code": 40100,
                    "message": "Authentication required",
                    "error": "unauthorized"
                }), 401

            user_roles = g.roles if g.roles else []

            # 检查每个角色的权限
            has_permission = False
            for role in user_roles:
                if role in DEFAULT_PERMISSIONS:
                    role_permissions = DEFAULT_PERMISSIONS[role]
                    if resource in role_permissions:
                        if operation in role_permissions[resource]:
                            has_permission = True
                            break

            if not has_permission:
                return jsonify({
                    "code": 40300,
                    "message": f"Insufficient permissions. Required: {operation} on {resource}",
                    "error": "forbidden",
                    "required": {"resource": resource, "operation": operation},
                    "user_roles": user_roles
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


# ============= 辅助函数 =============

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


def is_health_check_endpoint(request_obj) -> bool:
    """
    判断是否为健康检查端点（跳过认证）

    Args:
        request_obj: Flask Request 对象

    Returns:
        是否为健康检查端点
    """
    path = request_obj.path
    health_endpoints = ["/health", "/readiness", "/metrics", "/api/v1/health"]
    for endpoint in health_endpoints:
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

    for role in roles:
        if role in DEFAULT_PERMISSIONS:
            role_permissions = DEFAULT_PERMISSIONS[role]
            if resource in role_permissions:
                if operation in role_permissions[resource]:
                    return True

    return False


# ============= Token 管理端点辅助函数 =============

def refresh_token(refresh_token: str) -> Optional[Dict]:
    """
    刷新访问 Token

    Args:
        refresh_token: 刷新令牌

    Returns:
        新的 Token 信息或 None
    """
    try:
        client_id = os.getenv("KEYCLOAK_CLIENT_ID", "web")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        if not client_secret:
            logger.warning("KEYCLOAK_CLIENT_SECRET not set, token refresh may fail")
            return None
        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=5
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
        token: 访问令牌

    Returns:
        是否成功
    """
    try:
        response = requests.post(
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout",
            data={
                "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "web"),
                "refresh_token": token,
            },
            timeout=5
        )
        return response.status_code == 204
    except Exception as e:
        logger.warning(f"Logout failed: {e}")
    return False
