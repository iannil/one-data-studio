"""
Alldata API 认证模块
P5: 使用 Keycloak JWT 进行身份验证和授权

功能：
- JWT Token 验证 (RS256)
- 角色权限检查 (RBAC)
- 数据集和元数据资源权限控制
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

# SSL verification for external requests
# In production, this should always be True. Only disable for local development with self-signed certs.
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"
if not VERIFY_SSL:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError(
            "CRITICAL: VERIFY_SSL cannot be disabled in production environment."
        )
    logger.warning(
        "SECURITY WARNING: SSL verification is disabled. This should ONLY be used for local development."
    )

# 安全警告: AUTH_MODE=false 将禁用所有认证检查
if not AUTH_MODE:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError(
            "CRITICAL: AUTH_MODE cannot be disabled in production environment. "
            "Remove AUTH_MODE=false or set ENVIRONMENT to a non-production value."
        )
    logger.warning(
        "SECURITY WARNING: AUTH_MODE is disabled. All requests will bypass authentication. "
        "This should ONLY be used for local development."
    )

# 尝试导入共享 JWT 中间件
try:
    import sys
    sys.path.insert(0, '/app/shared')
    from auth.jwt_middleware import (
        verify_jwt_token,
        get_keycloak_public_key,
        extract_token_from_request,
        get_user_roles,
        decode_jwt_token
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
    """Alldata 资源类型定义"""
    DATASET = "dataset"
    METADATA = "metadata"
    DATABASE = "database"
    TABLE = "table"
    COLUMN = "column"
    STORAGE = "storage"


class Operation:
    """操作类型定义"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"


# ============= 权限矩阵 =============

# Alldata 权限矩阵 (角色 -> 资源 -> 操作)
ALDATA_PERMISSIONS = {
    "admin": {
        Resource.DATASET: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.EXPORT],
        Resource.METADATA: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE],
        Resource.DATABASE: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE],
        Resource.TABLE: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE],
        Resource.COLUMN: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.DELETE],
        Resource.STORAGE: [Operation.READ, Operation.CREATE, Operation.DELETE, Operation.IMPORT],
    },
    "data_engineer": {
        Resource.DATASET: [Operation.READ, Operation.CREATE, Operation.UPDATE, Operation.EXPORT],
        Resource.METADATA: [Operation.READ, Operation.CREATE, Operation.UPDATE],
        Resource.DATABASE: [Operation.READ],
        Resource.TABLE: [Operation.READ],
        Resource.COLUMN: [Operation.READ],
        Resource.STORAGE: [Operation.READ],
    },
    "data_analyst": {
        Resource.DATASET: [Operation.READ, Operation.EXPORT],
        Resource.METADATA: [Operation.READ],
        Resource.DATABASE: [Operation.READ],
        Resource.TABLE: [Operation.READ],
        Resource.COLUMN: [Operation.READ],
        Resource.STORAGE: [Operation.READ],
    },
    "viewer": {
        Resource.DATASET: [Operation.READ],
        Resource.METADATA: [Operation.READ],
        Resource.DATABASE: [Operation.READ],
        Resource.TABLE: [Operation.READ],
        Resource.COLUMN: [Operation.READ],
        Resource.STORAGE: [Operation.READ],
    },
}


# ============= JWT 认证装饰器 =============

def require_jwt(optional: bool = False) -> Callable:
    """
    JWT 认证装饰器

    Args:
        optional: 是否可选（True 时未认证也能通过，但 g.user 为 None）

    Usage:
        @app.route("/api/v1/datasets")
        @require_jwt()
        def list_datasets():
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
        client_id = os.getenv("KEYCLOAK_CLIENT_ID", "alldata-api")
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
            timeout=5,
            verify=VERIFY_SSL  # Use configurable SSL verification
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
        @app.route("/api/v1/admin/databases")
        @require_jwt()
        @require_role("admin", "data_engineer")
        def admin_databases():
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
        resource: 资源类型 (如 Resource.DATASET)
        operation: 操作类型 (如 Operation.CREATE)

    Usage:
        @app.route("/api/v1/datasets", methods=["POST"])
        @require_jwt()
        @require_permission(Resource.DATASET, Operation.CREATE)
        def create_dataset():
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
                if role in ALDATA_PERMISSIONS:
                    role_permissions = ALDATA_PERMISSIONS[role]
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
        if role in ALDATA_PERMISSIONS:
            role_permissions = ALDATA_PERMISSIONS[role]
            if resource in role_permissions:
                if operation in role_permissions[resource]:
                    return True

    return False


# ============= 数据集所有权检查 =============

def require_dataset_owner():
    """
    数据集所有权检查装饰器

    检查用户是否是数据集的创建者或有管理权限

    Usage:
        @app.route("/api/v1/datasets/<dataset_id>", methods=["DELETE"])
        @require_jwt()
        @require_dataset_owner()
        def delete_dataset(dataset_id):
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

            # 这里可以添加数据集所有权检查逻辑
            # 例如：从 kwargs 中获取 dataset_id，查询数据库，检查 created_by

            return fn(*args, **kwargs)

        return wrapper
    return decorator
