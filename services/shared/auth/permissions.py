"""
RBAC 权限管理模块
Sprint 3.1: 基于角色的访问控制
Sprint 30: 动态角色和权限管理

功能：
- 权限定义
- 资源-操作-角色映射
- 权限检查装饰器
- 动态角色创建和权限继承
"""

import logging
from enum import Enum
from typing import Set, List, Dict, Callable, Optional, Any
from functools import wraps

try:
    from flask import jsonify, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    jsonify = None
    g = None

logger = logging.getLogger(__name__)

# 数据库会话工厂（延迟初始化）
_db_session_factory = None


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


def owner_or_admin(
    resource_id_param: str = "id",
    owner_key: str = "owner",
    get_resource_owner: Optional[Callable] = None
):
    """
    资源所有者或管理员权限验证

    用于验证用户是否为资源所有者或管理员

    Args:
        resource_id_param: URL 中的资源 ID 参数名
        owner_key: 资源对象中的所有者字段名
        get_resource_owner: 获取资源所有者的回调函数
                           签名: (resource_id: str) -> Optional[str]
                           返回资源所有者的 user_id，如果资源不存在则返回 None

    Usage:
        # 方式 1：使用自定义回调函数
        def get_dataset_owner(dataset_id):
            dataset = db.query(Dataset).get(dataset_id)
            return dataset.created_by if dataset else None

        @app.route("/api/v1/datasets/<id>", methods=["DELETE"])
        @require_jwt()
        @owner_or_admin("id", "created_by", get_resource_owner=get_dataset_owner)
        def delete_dataset(id):
            ...

        # 方式 2：使用默认行为（仅检查 admin）
        @app.route("/api/v1/datasets/<id>", methods=["DELETE"])
        @require_jwt()
        @owner_or_admin("id")
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

            # 获取资源 ID
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                logger.warning(f"Resource ID parameter '{resource_id_param}' not found in kwargs")
                return jsonify({
                    "code": 40000,
                    "message": "Resource ID not provided",
                    "error": "bad_request"
                }), 400

            # 如果提供了获取所有者的回调函数，使用它
            if get_resource_owner:
                try:
                    resource_owner = get_resource_owner(resource_id)

                    if resource_owner is None:
                        return jsonify({
                            "code": 40400,
                            "message": "Resource not found",
                            "error": "not_found"
                        }), 404

                    if resource_owner != user_id:
                        logger.warning(
                            f"Permission denied: user={user_id} is not owner of resource {resource_id} "
                            f"(owner={resource_owner})"
                        )
                        return jsonify({
                            "code": 40300,
                            "message": "Only the resource owner or admin can perform this action",
                            "error": "forbidden"
                        }), 403

                except Exception as e:
                    logger.error(f"Error checking resource ownership: {e}")
                    return jsonify({
                        "code": 50000,
                        "message": "Error checking resource ownership",
                        "error": "internal_error"
                    }), 500
            else:
                # 没有提供回调函数，记录警告但允许通过
                # 在生产环境中应该提供回调函数
                logger.warning(
                    f"No owner check callback provided for resource {resource_id}. "
                    f"Consider providing get_resource_owner callback for proper ownership verification."
                )

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def create_owner_checker(model_class, owner_field: str = 'created_by'):
    """
    创建资源所有者检查函数

    用于与 SQLAlchemy 模型配合使用

    Args:
        model_class: SQLAlchemy 模型类
        owner_field: 所有者字段名

    Returns:
        获取资源所有者的函数

    Usage:
        from models import Dataset

        get_dataset_owner = create_owner_checker(Dataset, 'created_by')

        @owner_or_admin("id", get_resource_owner=get_dataset_owner)
        def delete_dataset(id):
            ...
    """
    def get_owner(resource_id: str) -> Optional[str]:
        try:
            from models import get_db_session
            db = get_db_session()
            try:
                resource = db.query(model_class).get(resource_id)
                if resource:
                    return getattr(resource, owner_field, None)
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting resource owner: {e}")
            return None

    return get_owner


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


# =============================================================================
# Sprint 30: 动态角色和权限管理
# =============================================================================

class DynamicRBACManager:
    """
    动态 RBAC 管理器

    Sprint 30: 支持运行时创建和管理角色权限

    功能：
    - 动态创建/更新/删除角色
    - 权限继承
    - 数据库持久化
    - 缓存支持
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._role_cache: Dict[str, Set[tuple]] = {}
        self._cache_ttl = 300  # 5 分钟缓存

    def _get_session(self):
        """获取数据库会话"""
        global _db_session_factory

        if self._session_factory:
            return self._session_factory()

        if _db_session_factory is None:
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from ..config import get_config
                from ..models.rbac import RBACBase

                config = get_config()
                engine = create_engine(config.database.url)
                RBACBase.metadata.create_all(engine)
                _db_session_factory = sessionmaker(bind=engine)
            except Exception as e:
                logger.error(f"Failed to initialize RBAC database: {e}")
                return None

        return _db_session_factory()

    def create_role(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        parent_role: Optional[str] = None,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建新角色

        Args:
            name: 角色名称
            display_name: 显示名称
            description: 描述
            permissions: 权限列表，格式 ["resource:operation", ...]
            parent_role: 父角色名称（用于权限继承）
            tenant_id: 租户 ID
            created_by: 创建者 ID

        Returns:
            创建的角色信息
        """
        session = self._get_session()
        if session is None:
            return None

        try:
            from ..models.rbac import Role, Permission, RolePermission

            # 检查角色是否已存在
            existing = session.query(Role).filter(
                Role.name == name,
                Role.tenant_id == tenant_id
            ).first()

            if existing:
                logger.warning(f"Role already exists: {name}")
                return None

            # 查找父角色
            parent_role_id = None
            if parent_role:
                parent = session.query(Role).filter(Role.name == parent_role).first()
                if parent:
                    parent_role_id = parent.id

            # 创建角色
            role = Role(
                name=name,
                display_name=display_name or name,
                description=description,
                parent_role_id=parent_role_id,
                tenant_id=tenant_id,
                role_type='custom',
                is_system=False,
                created_by=created_by
            )
            session.add(role)
            session.flush()  # 获取角色 ID

            # 添加权限
            if permissions:
                for perm_str in permissions:
                    if ':' in perm_str:
                        resource, operation = perm_str.split(':', 1)

                        # 查找或创建权限
                        perm = session.query(Permission).filter(
                            Permission.resource == resource,
                            Permission.operation == operation
                        ).first()

                        if perm is None:
                            perm = Permission(
                                name=perm_str,
                                resource=resource,
                                operation=operation
                            )
                            session.add(perm)
                            session.flush()

                        # 创建角色-权限关联
                        role_perm = RolePermission(
                            role_id=role.id,
                            permission_id=perm.id,
                            granted_by=created_by
                        )
                        session.add(role_perm)

            session.commit()

            # 清除缓存
            self._role_cache.pop(name, None)

            logger.info(f"Created role: {name} with {len(permissions or [])} permissions")

            return role.to_dict(include_permissions=True)

        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def update_role(
        self,
        role_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """更新角色信息"""
        session = self._get_session()
        if session is None:
            return None

        try:
            from ..models.rbac import Role

            role = session.query(Role).filter(Role.id == role_id).first()
            if role is None:
                return None

            if role.is_system:
                logger.warning(f"Cannot modify system role: {role.name}")
                return None

            if display_name is not None:
                role.display_name = display_name
            if description is not None:
                role.description = description
            if is_active is not None:
                role.is_active = is_active

            session.commit()

            # 清除缓存
            self._role_cache.pop(role.name, None)

            return role.to_dict()

        except Exception as e:
            logger.error(f"Failed to update role: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        session = self._get_session()
        if session is None:
            return False

        try:
            from ..models.rbac import Role

            role = session.query(Role).filter(Role.id == role_id).first()
            if role is None:
                return False

            if role.is_system:
                logger.warning(f"Cannot delete system role: {role.name}")
                return False

            role_name = role.name
            session.delete(role)
            session.commit()

            # 清除缓存
            self._role_cache.pop(role_name, None)

            logger.info(f"Deleted role: {role_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete role: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def add_permission_to_role(
        self,
        role_id: str,
        resource: str,
        operation: str,
        granted_by: Optional[str] = None
    ) -> bool:
        """为角色添加权限"""
        session = self._get_session()
        if session is None:
            return False

        try:
            from ..models.rbac import Role, Permission, RolePermission

            role = session.query(Role).filter(Role.id == role_id).first()
            if role is None:
                return False

            # 查找或创建权限
            perm = session.query(Permission).filter(
                Permission.resource == resource,
                Permission.operation == operation
            ).first()

            if perm is None:
                perm = Permission(
                    name=f"{resource}:{operation}",
                    resource=resource,
                    operation=operation
                )
                session.add(perm)
                session.flush()

            # 检查是否已存在
            existing = session.query(RolePermission).filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm.id
            ).first()

            if existing:
                return True  # 已存在

            # 创建关联
            role_perm = RolePermission(
                role_id=role_id,
                permission_id=perm.id,
                granted_by=granted_by
            )
            session.add(role_perm)
            session.commit()

            # 清除缓存
            self._role_cache.pop(role.name, None)

            return True

        except Exception as e:
            logger.error(f"Failed to add permission to role: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def remove_permission_from_role(
        self,
        role_id: str,
        resource: str,
        operation: str
    ) -> bool:
        """从角色移除权限"""
        session = self._get_session()
        if session is None:
            return False

        try:
            from ..models.rbac import Role, Permission, RolePermission

            role = session.query(Role).filter(Role.id == role_id).first()
            if role is None or role.is_system:
                return False

            perm = session.query(Permission).filter(
                Permission.resource == resource,
                Permission.operation == operation
            ).first()

            if perm is None:
                return True  # 权限不存在

            role_perm = session.query(RolePermission).filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm.id
            ).first()

            if role_perm:
                session.delete(role_perm)
                session.commit()

            # 清除缓存
            self._role_cache.pop(role.name, None)

            return True

        except Exception as e:
            logger.error(f"Failed to remove permission from role: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_role_permissions(self, role_name: str, include_inherited: bool = True) -> Set[tuple]:
        """
        获取角色的所有权限

        Args:
            role_name: 角色名称
            include_inherited: 是否包含继承的权限

        Returns:
            权限集合 {(resource, operation), ...}
        """
        # 检查缓存
        cache_key = f"{role_name}:{include_inherited}"
        if cache_key in self._role_cache:
            return self._role_cache[cache_key]

        session = self._get_session()
        if session is None:
            # 回退到静态权限
            return ROLE_PERMISSIONS.get(role_name, set())

        try:
            from ..models.rbac import Role

            role = session.query(Role).filter(Role.name == role_name).first()
            if role is None:
                # 回退到静态权限
                return ROLE_PERMISSIONS.get(role_name, set())

            if include_inherited:
                permissions = role.get_all_permissions()
            else:
                permissions = [rp.permission for rp in role.permissions if rp.permission]

            result = {(p.resource, p.operation) for p in permissions}

            # 更新缓存
            self._role_cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Failed to get role permissions: {e}")
            return ROLE_PERMISSIONS.get(role_name, set())
        finally:
            session.close()

    def list_roles(
        self,
        tenant_id: Optional[str] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """列出所有角色"""
        session = self._get_session()
        if session is None:
            return []

        try:
            from ..models.rbac import Role

            query = session.query(Role)

            if tenant_id:
                query = query.filter(
                    (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None))
                )

            if not include_system:
                query = query.filter(Role.is_system == False)

            roles = query.order_by(Role.priority.desc()).all()

            return [role.to_dict(include_permissions=True) for role in roles]

        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            return []
        finally:
            session.close()

    def list_permissions(self) -> List[Dict[str, Any]]:
        """列出所有权限"""
        session = self._get_session()
        if session is None:
            return []

        try:
            from ..models.rbac import Permission

            permissions = session.query(Permission).filter(
                Permission.is_active == True
            ).all()

            return [perm.to_dict() for perm in permissions]

        except Exception as e:
            logger.error(f"Failed to list permissions: {e}")
            return []
        finally:
            session.close()

    def clear_cache(self):
        """清除缓存"""
        self._role_cache.clear()


# 全局 RBAC 管理器实例
_rbac_manager: Optional[DynamicRBACManager] = None


def get_rbac_manager() -> DynamicRBACManager:
    """获取全局 RBAC 管理器"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = DynamicRBACManager()
    return _rbac_manager


def get_dynamic_permissions(roles: List[str]) -> Set[tuple]:
    """
    获取用户的动态权限（优先使用数据库，回退到静态配置）

    Args:
        roles: 用户角色列表

    Returns:
        权限集合 {(resource, operation), ...}
    """
    manager = get_rbac_manager()
    permissions = set()

    for role in roles:
        role_perms = manager.get_role_permissions(role)
        permissions.update(role_perms)

    return permissions


def has_dynamic_permission(roles: List[str], resource: Resource, operation: Operation) -> bool:
    """
    检查用户是否有动态权限

    优先使用数据库权限，回退到静态配置

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

    permissions = get_dynamic_permissions(roles)
    resource_str = resource.value if isinstance(resource, Resource) else resource
    operation_str = operation.value if isinstance(operation, Operation) else operation

    # 检查精确匹配
    if (resource_str, operation_str) in permissions:
        return True

    # 检查通配符
    if ('*', '*') in permissions:
        return True
    if (resource_str, '*') in permissions:
        return True
    if ('*', operation_str) in permissions:
        return True

    return False

