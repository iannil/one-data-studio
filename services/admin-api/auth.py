"""
Admin API 认证模块 - 开发模式
Sprint 3.1: 本地开发认证实现

开发模式下直接跳过认证检查
"""

import os
import functools

# 开发模式：检查 AUTH_MODE 环境变量
AUTH_MODE = os.getenv("AUTH_MODE", "false").lower() == "true"
STRICT_AUTH_MODE = os.getenv("STRICT_AUTH_MODE", "false").lower() == "true"

# 如果未启用认证，所有装饰器都直接通过
if not AUTH_MODE and not STRICT_AUTH_MODE:
    def require_jwt(optional=False):
        """开发模式：跳过 JWT 认证"""
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                # 设置模拟用户信息
                from flask import g
                g.user = "dev_user"
                g.user_id = "dev_user_001"
                g.roles = ["admin"]
                g.payload = {"sub": "dev_user_001"}
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    def require_role(*required_roles):
        """开发模式：跳过角色检查"""
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    def require_permission(resource, operation):
        """开发模式：跳过权限检查"""
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    class Resource:
        """资源类型"""
        USER = "user"
        SYSTEM = "system"

    class Operation:
        """操作类型"""
        CREATE = "create"
        READ = "read"
        UPDATE = "update"
        DELETE = "delete"
        MANAGE = "manage"

    def get_current_user():
        """开发模式：返回模拟用户"""
        return {
            "user_id": "dev_user_001",
            "username": "dev_user",
            "roles": ["admin"]
        }

else:
    # 生产模式：从 shared 模块导入
    try:
        from auth import (
            require_jwt,
            require_role,
            require_permission,
            Resource,
            Operation,
            get_current_user
        )
    except ImportError:
        raise ImportError(
            "Authentication module is required in production. "
            "Ensure shared/auth is available."
        )
