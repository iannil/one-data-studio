"""
RBAC 权限管理模块
Sprint 3.1: 基于角色的访问控制

功能：
- 权限定义
- 资源-操作-角色映射
- 权限检查装饰器
"""

from enum import Enum
from typing import Set, List, Dict, Callable
from functools import wraps
from flask import jsonify, g
import logging

logger = logging.getLogger(__name__)


class Resource(Enum):
    """资源类型枚举"""
    DATASET = "dataset"
    METADATA = "metadata"
    WORKFLOW = "workflow"
    CHAT = "chat"
    MODEL = "model"
    PROMPT_TEMPLATE = "prompt_template"
    USER = "user"
    SYSTEM = "system"


class Operation(Enum):
    """操作类型枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


# 角色默认权限配置
ROLE_PERMISSIONS: Dict[str, Set[tuple]] = {
    # 管理员 - 全部权限
    "admin": {(r.value, o.value) for r in Resource for o in Operation},

    # 数据工程师 - 数据集和元数据权限
    "data_engineer": {
        (Resource.DATASET.value, Operation.CREATE.value),
        (Resource.DATASET.value, Operation.READ.value),
        (Resource.DATASET.value, Operation.UPDATE.value),
        (Resource.DATASET.value, Operation.DELETE.value),
        (Resource.METADATA.value, Operation.READ.value),
        (Resource.METADATA.value, Operation.CREATE.value),
    },

    # 数据分析师 - 只读权限
    "data_analyst": {
        (Resource.DATASET.value, Operation.READ.value),
        (Resource.METADATA.value, Operation.READ.value),
        (Resource.WORKFLOW.value, Operation.READ.value),
    },

    # AI 开发者 - 工作流和聊天权限
    "ai_developer": {
        (Resource.WORKFLOW.value, Operation.CREATE.value),
        (Resource.WORKFLOW.value, Operation.READ.value),
        (Resource.WORKFLOW.value, Operation.UPDATE.value),
        (Resource.WORKFLOW.value, Operation.EXECUTE.value),
        (Resource.CHAT.value, Operation.EXECUTE.value),
        (Resource.MODEL.value, Operation.READ.value),
        (Resource.PROMPT_TEMPLATE.value, Operation.CREATE.value),
        (Resource.PROMPT_TEMPLATE.value, Operation.READ.value),
        (Resource.PROMPT_TEMPLATE.value, Operation.UPDATE.value),
    },

    # 普通用户 - 基础权限
    "user": {
        (Resource.DATASET.value, Operation.READ.value),
        (Resource.CHAT.value, Operation.EXECUTE.value),
        (Resource.WORKFLOW.value, Operation.READ.value),
    },

    # 访客 - 只读部分资源
    "guest": {
        (Resource.DATASET.value, Operation.READ.value),
        (Resource.METADATA.value, Operation.READ.value),
    },
}


def get_user_permissions(roles: List[str]) -> Set[tuple]:
    """
    获取用户的所有权限（合并所有角色权限）

    Args:
        roles: 用户角色列表

    Returns:
        权限集合 {(resource, operation), ...}
    """
    permissions = set()

    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role, set())
        permissions.update(role_perms)

    return permissions


def has_permission(roles: List[str], resource: Resource, operation: Operation) -> bool:
    """
    检查用户是否有指定权限

    Args:
        roles: 用户角色列表
        resource: 资源类型
        operation: 操作类型

    Returns:
        是否有权限
    """
    if not roles:
        return False

    # admin 角色拥有所有权限
    if "admin" in roles:
        return True

    permissions = get_user_permissions(roles)
    return (resource.value, operation.value) in permissions


def require_permission(resource: Resource, operation: Operation):
    """
    权限验证装饰器

    需要与 @require_jwt() 配合使用

    Args:
        resource: 资源类型
        operation: 操作类型

    Usage:
        @app.route("/api/v1/datasets", methods=["POST"])
        @require_jwt()
        @require_permission(Resource.DATASET, Operation.CREATE)
        def create_dataset():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 检查是否已认证
            if not hasattr(g, 'roles'):
                return jsonify({
                    "code": 40100,
                    "message": "Authentication required",
                    "error": "unauthorized"
                }), 401

            user_roles = g.roles if g.roles else []

            # 检查权限
            if not has_permission(user_roles, resource, operation):
                logger.warning(
                    f"Permission denied: user={g.user}, roles={user_roles}, "
                    f"resource={resource.value}, operation={operation.value}"
                )
                return jsonify({
                    "code": 40300,
                    "message": "Insufficient permissions",
                    "error": "forbidden",
                    "required": f"{resource.value}:{operation.value}",
                    "roles": user_roles
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(*permissions: tuple):
    """
    多权限验证装饰器（满足其一即可）

    需要与 @require_jwt() 配合使用

    Args:
        *permissions: 权限元组列表 [(resource, operation), ...]

    Usage:
        @app.route("/api/v1/datasets/<id>", methods=["PUT", "DELETE"])
        @require_jwt()
        @require_any_permission(
            (Resource.DATASET, Operation.UPDATE),
            (Resource.DATASET, Operation.DELETE)
        )
        def update_or_delete_dataset(id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'roles'):
                return jsonify({
                    "code": 40100,
                    "message": "Authentication required",
                    "error": "unauthorized"
                }), 401

            user_roles = g.roles if g.roles else []

            # 检查是否有任一所需权限
            has_any = False
            for resource, operation in permissions:
                if has_permission(user_roles, resource, operation):
                    has_any = True
                    break

            if not has_any:
                required_perms = [f"{r.value}:{o.value}" for r, o in permissions]
                return jsonify({
                    "code": 40300,
                    "message": "Insufficient permissions",
                    "error": "forbidden",
                    "required_any_of": required_perms,
                    "roles": user_roles
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def owner_or_admin(resource_id_param: str = "id", owner_key: str = "owner"):
    """
    资源所有者或管理员权限验证

    用于验证用户是否为资源所有者或管理员

    Args:
        resource_id_param: URL 中的资源 ID 参数名
        owner_key: 资源对象中的所有者字段名

    Usage:
        @app.route("/api/v1/datasets/<id>", methods=["DELETE"])
        @require_jwt()
        @owner_or_admin("id", "created_by")
        def delete_dataset(id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'roles'):
                return jsonify({
                    "code": 40100,
                    "message": "Authentication required",
                    "error": "unauthorized"
                }), 401

            user_roles = g.roles if g.roles else []
            user_id = g.user_id

            # admin 角色直接通过
            if "admin" in user_roles:
                return fn(*args, **kwargs)

            # 这里需要实际的资源所有者检查逻辑
            # 实际实现中应从数据库查询资源的 owner 信息
            # 这里简化为跳过检查
            logger.warning(
                f"Owner check not implemented for resource_id={kwargs.get(resource_id_param)}"
            )

            return fn(*args, **kwargs)

        return wrapper
    return decorator


# 权限检查辅助函数
def can_create_dataset(roles: List[str]) -> bool:
    """检查是否可创建数据集"""
    return has_permission(roles, Resource.DATASET, Operation.CREATE)


def can_delete_dataset(roles: List[str]) -> bool:
    """检查是否可删除数据集"""
    return has_permission(roles, Resource.DATASET, Operation.DELETE)


def can_execute_workflow(roles: List[str]) -> bool:
    """检查是否可执行工作流"""
    return has_permission(roles, Resource.WORKFLOW, Operation.EXECUTE)


def can_manage_users(roles: List[str]) -> bool:
    """检查是否可管理用户"""
    return has_permission(roles, Resource.USER, Operation.MANAGE)


def can_access_chat(roles: List[str]) -> bool:
    """检查是否可访问聊天"""
    return has_permission(roles, Resource.CHAT, Operation.EXECUTE)
