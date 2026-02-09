"""
共享认证模块
Sprint 3.1: ONE-DATA-STUDIO 统一认证授权
Sprint 21: Security Hardening - HttpOnly cookies, token refresh
Sprint 30: 动态角色和权限管理
"""

from .jwt_middleware import (
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
)

from .permissions import (
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
)

from .token_refresh import (
    TokenRefreshMiddleware,
    set_auth_cookies,
    clear_auth_cookies,
    get_token_from_cookie_or_header,
    token_expires_soon,
    init_token_refresh,
)

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
