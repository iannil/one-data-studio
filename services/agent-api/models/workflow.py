"""
工作流模型
Sprint 4.2: Workflow 模型
Phase 6: Sprint 6.1 - 添加定义解析支持
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from .base import Base


class Workflow(Base):
    """工作流表"""
    __tablename__ = "workflows"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(String(64), unique=True, nullable=False, comment='工作流唯一标识')
    name = Column(String(255), nullable=False, comment='工作流名称')
    description = Column(Text, comment='工作流描述')
    type = Column(String(32), nullable=False, default='rag', comment='类型: rag, sql, agent')
    status = Column(String(32), nullable=False, default='stopped', comment='状态: running, stopped, error')
    definition = Column(Text, comment='工作流定义 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_definition(self) -> dict:
        """获取解析后的工作流定义"""
        if not self.definition:
            return {}
        try:
            return json.loads(self.definition)
        except json.JSONDecodeError:
            return {}

    def set_definition(self, definition: dict):
        """设置工作流定义"""
        self.definition = json.dumps(definition, ensure_ascii=False)

    def to_dict(self, include_definition: bool = False):
        """转换为字典"""
        result = {
            "id": self.workflow_id,
            "name": self.name,
            "description": self.description or "",
            "type": self.type,
            "status": self.status,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_definition and self.definition:
            result["definition"] = self.get_definition()
        return result
