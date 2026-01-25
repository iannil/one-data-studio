"""
角色管理数据模型
Admin API - Role 和 Permission 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Boolean, Table, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String(64), ForeignKey('roles.role_id'), primary_key=True),
    Column('permission_id', String(64), ForeignKey('permissions.permission_id'), primary_key=True),
    Column('created_at', TIMESTAMP, server_default=func.current_timestamp())
)


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    permission_id = Column(String(64), unique=True, nullable=False, comment='权限唯一标识')
    name = Column(String(128), nullable=False, comment='权限名称')
    code = Column(String(128), unique=True, nullable=False, comment='权限代码: resource:operation')
    resource = Column(String(64), nullable=False, comment='资源类型')
    operation = Column(String(64), nullable=False, comment='操作类型')
    description = Column(Text, comment='权限描述')
    category = Column(String(64), comment='权限分类')
    is_system = Column(Boolean, default=False, comment='是否系统内置')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 关系
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.permission_id,
            "name": self.name,
            "code": self.code,
            "resource": self.resource,
            "operation": self.operation,
            "description": self.description,
            "category": self.category,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_id = Column(String(64), unique=True, nullable=False, comment='角色唯一标识')
    name = Column(String(128), unique=True, nullable=False, comment='角色名称')
    display_name = Column(String(128), comment='显示名称')
    description = Column(Text, comment='角色描述')
    role_type = Column(String(32), default='custom', comment='角色类型: system, custom')
    is_system = Column(Boolean, default=False, comment='是否系统内置')
    is_active = Column(Boolean, default=True, comment='是否启用')
    priority = Column(Integer, default=0, comment='优先级')
    parent_role_id = Column(String(64), comment='父角色ID')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")

    def to_dict(self, include_permissions: bool = False, include_users: bool = False):
        """转换为字典"""
        result = {
            "id": self.role_id,
            "name": self.name,
            "display_name": self.display_name or self.name,
            "description": self.description,
            "role_type": self.role_type,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "priority": self.priority,
            "parent_role_id": self.parent_role_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_permissions:
            result["permissions"] = [p.to_dict() for p in self.permissions]
        if include_users:
            result["user_count"] = len(self.users)
        return result
