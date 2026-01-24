"""
RBAC 角色权限数据模型
Sprint 30: API 成熟度提升

提供动态角色和权限管理的数据库模型
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Table, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

RBACBase = declarative_base()


class Role(RBACBase):
    """
    角色表

    支持自定义角色定义
    """
    __tablename__ = 'roles'

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 角色信息
    name = Column(String(64), nullable=False, unique=True, index=True, comment='角色名称')
    display_name = Column(String(128), nullable=True, comment='显示名称')
    description = Column(Text, nullable=True, comment='角色描述')

    # 角色类型
    role_type = Column(String(20), nullable=False, default='custom', comment='角色类型: system/custom')

    # 租户信息（null 表示全局角色）
    tenant_id = Column(String(64), nullable=True, index=True, comment='租户ID')

    # 继承关系
    parent_role_id = Column(String(36), ForeignKey('roles.id'), nullable=True, comment='父角色ID')

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment='是否激活')
    is_system = Column(Boolean, nullable=False, default=False, comment='是否系统内置')

    # 优先级（数值越大优先级越高）
    priority = Column(Integer, nullable=False, default=0, comment='优先级')

    # 审计字段
    created_by = Column(String(64), nullable=True, comment='创建者')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    permissions = relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')
    parent_role = relationship('Role', remote_side=[id], backref='child_roles')

    __table_args__ = (
        Index('ix_roles_tenant_name', 'tenant_id', 'name'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'comment': '角色表'
        }
    )

    def to_dict(self, include_permissions: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'role_type': self.role_type,
            'tenant_id': self.tenant_id,
            'parent_role_id': self.parent_role_id,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'priority': self.priority,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_permissions:
            data['permissions'] = [rp.permission.to_dict() for rp in self.permissions if rp.permission]

        return data

    def get_all_permissions(self) -> List['Permission']:
        """
        获取角色的所有权限（包括继承的权限）

        Returns:
            权限列表
        """
        permissions = [rp.permission for rp in self.permissions if rp.permission]

        # 递归获取父角色权限
        if self.parent_role:
            parent_permissions = self.parent_role.get_all_permissions()
            # 去重
            existing_ids = {p.id for p in permissions}
            for p in parent_permissions:
                if p.id not in existing_ids:
                    permissions.append(p)

        return permissions

    def has_permission(self, resource: str, operation: str) -> bool:
        """
        检查角色是否有指定权限

        Args:
            resource: 资源类型
            operation: 操作类型

        Returns:
            是否有权限
        """
        for permission in self.get_all_permissions():
            if permission.resource == resource and permission.operation == operation:
                return True
            # 支持通配符
            if permission.resource == '*' or permission.operation == '*':
                if (permission.resource == '*' or permission.resource == resource) and \
                   (permission.operation == '*' or permission.operation == operation):
                    return True

        return False

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(RBACBase):
    """
    权限表

    定义资源-操作权限
    """
    __tablename__ = 'permissions'

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 权限信息
    name = Column(String(128), nullable=False, unique=True, index=True, comment='权限名称')
    display_name = Column(String(128), nullable=True, comment='显示名称')
    description = Column(Text, nullable=True, comment='权限描述')

    # 资源-操作
    resource = Column(String(50), nullable=False, index=True, comment='资源类型')
    operation = Column(String(20), nullable=False, index=True, comment='操作类型')

    # 权限范围
    scope = Column(String(20), nullable=False, default='all', comment='范围: all/own/tenant')

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment='是否激活')
    is_system = Column(Boolean, nullable=False, default=False, comment='是否系统内置')

    # 审计字段
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    role_permissions = relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_permissions_resource_operation', 'resource', 'operation', unique=True),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'comment': '权限表'
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'resource': self.resource,
            'operation': self.operation,
            'scope': self.scope,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def permission_string(self) -> str:
        """获取权限字符串表示"""
        return f"{self.resource}:{self.operation}"

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class RolePermission(RBACBase):
    """
    角色-权限关联表
    """
    __tablename__ = 'role_permissions'

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 外键
    role_id = Column(String(36), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)

    # 授予信息
    granted_by = Column(String(64), nullable=True, comment='授权者')
    granted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    role = relationship('Role', back_populates='permissions')
    permission = relationship('Permission', back_populates='role_permissions')

    __table_args__ = (
        Index('ix_role_permissions_unique', 'role_id', 'permission_id', unique=True),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'comment': '角色权限关联表'
        }
    )

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


# 预定义的系统权限
SYSTEM_PERMISSIONS = [
    # 数据集权限
    {'name': 'dataset:create', 'resource': 'dataset', 'operation': 'create', 'display_name': '创建数据集'},
    {'name': 'dataset:read', 'resource': 'dataset', 'operation': 'read', 'display_name': '查看数据集'},
    {'name': 'dataset:update', 'resource': 'dataset', 'operation': 'update', 'display_name': '更新数据集'},
    {'name': 'dataset:delete', 'resource': 'dataset', 'operation': 'delete', 'display_name': '删除数据集'},

    # 工作流权限
    {'name': 'workflow:create', 'resource': 'workflow', 'operation': 'create', 'display_name': '创建工作流'},
    {'name': 'workflow:read', 'resource': 'workflow', 'operation': 'read', 'display_name': '查看工作流'},
    {'name': 'workflow:update', 'resource': 'workflow', 'operation': 'update', 'display_name': '更新工作流'},
    {'name': 'workflow:delete', 'resource': 'workflow', 'operation': 'delete', 'display_name': '删除工作流'},
    {'name': 'workflow:execute', 'resource': 'workflow', 'operation': 'execute', 'display_name': '执行工作流'},

    # 聊天权限
    {'name': 'chat:execute', 'resource': 'chat', 'operation': 'execute', 'display_name': '使用聊天'},

    # 模型权限
    {'name': 'model:read', 'resource': 'model', 'operation': 'read', 'display_name': '查看模型'},
    {'name': 'model:manage', 'resource': 'model', 'operation': 'manage', 'display_name': '管理模型'},

    # 用户管理权限
    {'name': 'user:create', 'resource': 'user', 'operation': 'create', 'display_name': '创建用户'},
    {'name': 'user:read', 'resource': 'user', 'operation': 'read', 'display_name': '查看用户'},
    {'name': 'user:update', 'resource': 'user', 'operation': 'update', 'display_name': '更新用户'},
    {'name': 'user:delete', 'resource': 'user', 'operation': 'delete', 'display_name': '删除用户'},
    {'name': 'user:manage', 'resource': 'user', 'operation': 'manage', 'display_name': '管理用户'},

    # 系统管理权限
    {'name': 'system:config', 'resource': 'system', 'operation': 'config', 'display_name': '系统配置'},
    {'name': 'system:audit', 'resource': 'system', 'operation': 'audit', 'display_name': '查看审计日志'},
    {'name': 'system:admin', 'resource': 'system', 'operation': 'admin', 'display_name': '系统管理'},

    # 角色管理权限
    {'name': 'role:create', 'resource': 'role', 'operation': 'create', 'display_name': '创建角色'},
    {'name': 'role:read', 'resource': 'role', 'operation': 'read', 'display_name': '查看角色'},
    {'name': 'role:update', 'resource': 'role', 'operation': 'update', 'display_name': '更新角色'},
    {'name': 'role:delete', 'resource': 'role', 'operation': 'delete', 'display_name': '删除角色'},
]

# 预定义的系统角色
SYSTEM_ROLES = [
    {
        'name': 'admin',
        'display_name': '管理员',
        'description': '系统管理员，拥有所有权限',
        'role_type': 'system',
        'is_system': True,
        'priority': 100,
    },
    {
        'name': 'data_engineer',
        'display_name': '数据工程师',
        'description': '数据集和元数据管理权限',
        'role_type': 'system',
        'is_system': True,
        'priority': 50,
    },
    {
        'name': 'ai_developer',
        'display_name': 'AI开发者',
        'description': '工作流和聊天权限',
        'role_type': 'system',
        'is_system': True,
        'priority': 50,
    },
    {
        'name': 'data_analyst',
        'display_name': '数据分析师',
        'description': '只读权限',
        'role_type': 'system',
        'is_system': True,
        'priority': 30,
    },
    {
        'name': 'user',
        'display_name': '普通用户',
        'description': '基础权限',
        'role_type': 'system',
        'is_system': True,
        'priority': 10,
    },
    {
        'name': 'guest',
        'display_name': '访客',
        'description': '只读部分资源',
        'role_type': 'system',
        'is_system': True,
        'priority': 0,
    },
]
