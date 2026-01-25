"""
用户管理数据模型
Admin API - User 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Boolean, Table, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


# 用户-角色关联表
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', String(64), ForeignKey('users.user_id'), primary_key=True),
    Column('role_id', String(64), ForeignKey('roles.role_id'), primary_key=True),
    Column('created_at', TIMESTAMP, server_default=func.current_timestamp())
)

# 用户-用户组关联表
user_groups = Table(
    'user_group_members',
    Base.metadata,
    Column('user_id', String(64), ForeignKey('users.user_id'), primary_key=True),
    Column('group_id', String(64), ForeignKey('user_groups.group_id'), primary_key=True),
    Column('created_at', TIMESTAMP, server_default=func.current_timestamp())
)


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, comment='用户唯一标识')
    username = Column(String(128), unique=True, nullable=False, comment='用户名')
    email = Column(String(255), unique=True, nullable=False, comment='邮箱')
    password_hash = Column(String(255), comment='密码哈希')
    display_name = Column(String(128), comment='显示名称')
    avatar_url = Column(String(512), comment='头像URL')
    phone = Column(String(32), comment='手机号')
    department = Column(String(128), comment='部门')
    position = Column(String(128), comment='职位')
    status = Column(String(32), default='active', comment='状态: active, inactive, locked, deleted')
    last_login_at = Column(TIMESTAMP, comment='最后登录时间')
    last_login_ip = Column(String(64), comment='最后登录IP')
    login_count = Column(Integer, default=0, comment='登录次数')
    failed_login_count = Column(Integer, default=0, comment='登录失败次数')
    locked_until = Column(TIMESTAMP, comment='锁定截止时间')
    password_changed_at = Column(TIMESTAMP, comment='密码修改时间')
    extra_data = Column(Text, comment='扩展数据 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    groups = relationship("UserGroup", secondary=user_groups, back_populates="members")

    def get_extra_data(self) -> dict:
        """获取扩展数据"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except json.JSONDecodeError:
            return {}

    def set_extra_data(self, data: dict):
        """设置扩展数据"""
        self.extra_data = json.dumps(data, ensure_ascii=False)

    def to_dict(self, include_roles: bool = False, include_groups: bool = False):
        """转换为字典"""
        result = {
            "id": self.user_id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name or self.username,
            "avatar_url": self.avatar_url,
            "phone": self.phone,
            "department": self.department,
            "position": self.position,
            "status": self.status,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_login_ip": self.last_login_ip,
            "login_count": self.login_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_roles:
            result["roles"] = [r.to_dict() for r in self.roles]
        if include_groups:
            result["groups"] = [g.to_dict() for g in self.groups]
        return result
