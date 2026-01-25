"""
工具管理模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func

from .base import Base


class Tool(Base):
    """工具表"""
    __tablename__ = "tools"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tool_id = Column(String(64), unique=True, nullable=False, comment='工具唯一标识')
    name = Column(String(255), nullable=False, comment='工具名称')
    display_name = Column(String(255), comment='显示名称')
    description = Column(Text, comment='工具描述')
    type = Column(String(32), default='api', comment='类型: api, builtin, custom')
    category = Column(String(64), comment='分类')
    schema = Column(Text, comment='工具Schema (JSON)')
    config = Column(Text, comment='工具配置 (JSON)')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_schema(self) -> dict:
        """获取Schema"""
        if not self.schema:
            return {}
        import json
        try:
            return json.loads(self.schema)
        except json.JSONDecodeError:
            return {}

    def set_schema(self, schema: dict):
        """设置Schema"""
        import json
        self.schema = json.dumps(schema, ensure_ascii=False)

    def get_config(self) -> dict:
        """获取配置"""
        if not self.config:
            return {}
        import json
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict):
        """设置配置"""
        import json
        self.config = json.dumps(config, ensure_ascii=False)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "display_name": self.display_name or self.name,
            "description": self.description or "",
            "type": self.type,
            "category": self.category,
            "schema": self.get_schema(),
            "config": self.get_config(),
            "enabled": self.enabled,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
