"""
用户组管理数据模型
Admin API - UserGroup 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class UserGroup(Base):
    """用户组表"""
    __tablename__ = "user_groups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(String(64), unique=True, nullable=False, comment='用户组唯一标识')
    name = Column(String(128), unique=True, nullable=False, comment='用户组名称')
    display_name = Column(String(128), comment='显示名称')
    description = Column(Text, comment='用户组描述')
    group_type = Column(String(32), default='custom', comment='用户组类型: department, team, project, custom')
    parent_group_id = Column(String(64), comment='父用户组ID')
    is_active = Column(Boolean, default=True, comment='是否启用')
    extra_data = Column(Text, comment='扩展数据 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    members = relationship("User", secondary="user_group_members", back_populates="groups")

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

    def to_dict(self, include_members: bool = False):
        """转换为字典"""
        result = {
            "id": self.group_id,
            "name": self.name,
            "display_name": self.display_name or self.name,
            "description": self.description,
            "group_type": self.group_type,
            "parent_group_id": self.parent_group_id,
            "is_active": self.is_active,
            "member_count": len(self.members),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_members:
            result["members"] = [m.to_dict() for m in self.members]
        return result
