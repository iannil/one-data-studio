"""
Agent API 认证模块
统一使用 shared/auth 模块

此文件作为 shared/auth 的薄包装层，保持向后兼容性。
所有认证逻辑已统一到 services/shared/auth/
"""

import sys
import os

# 添加 shared 模块路径
shared_path = os.path.join(os.path.dirname(__file__), '..', 'shared')
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

# 从 shared/auth 导入所有功能
from auth import (
    # JWT Middleware
    require_jwt,
    require_role,
    get_current_user,
    extract_token_from_request,
    decode_jwt_token,
    is_health_check_endpoint,
    get_user_roles,
    check_permission,
    refresh_token,
    logout_user,
    introspect_token,
    AUTH_MODE,
    VERIFY_SSL,
    # Permissions
    Resource,
    Operation,
    ROLE_PERMISSIONS,
    require_permission,
    require_any_permission,
    owner_or_admin,
    create_owner_checker,
    has_permission,
    get_user_permissions,
    can_create_dataset,
    can_delete_dataset,
    can_execute_workflow,
    can_manage_users,
    can_access_chat,
    DynamicRBACManager,
    get_rbac_manager,
    get_dynamic_permissions,
    has_dynamic_permission,
    # Token Refresh
    TokenRefreshMiddleware,
    set_auth_cookies,
    clear_auth_cookies,
    get_token_from_cookie_or_header,
    token_expires_soon,
    init_token_refresh,
)

# 保持向后兼容性的别名
DEFAULT_PERMISSIONS = ROLE_PERMISSIONS

__all__ = [
    # JWT Middleware
    "require_jwt",
    "require_role",
    "get_current_user",
    "extract_token_from_request",
    "decode_jwt_token",
    "is_health_check_endpoint",
    "get_user_roles",
    "check_permission",
    "refresh_token",
    "logout_user",
    "introspect_token",
    "AUTH_MODE",
    "VERIFY_SSL",
    # Permissions
    "Resource",
    "Operation",
    "ROLE_PERMISSIONS",
    "DEFAULT_PERMISSIONS",  # 向后兼容别名
    "require_permission",
    "require_any_permission",
    "owner_or_admin",
    "create_owner_checker",
    "has_permission",
    "get_user_permissions",
    "can_create_dataset",
    "can_delete_dataset",
    "can_execute_workflow",
    "can_manage_users",
    "can_access_chat",
    "DynamicRBACManager",
    "get_rbac_manager",
    "get_dynamic_permissions",
    "has_dynamic_permission",
    # Token Refresh
    "TokenRefreshMiddleware",
    "set_auth_cookies",
    "clear_auth_cookies",
    "get_token_from_cookie_or_header",
    "token_expires_soon",
    "init_token_refresh",
]
