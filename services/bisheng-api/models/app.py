"""
应用管理模型
Apps are published workflows with runtime configuration
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, TIMESTAMP, Boolean
from sqlalchemy.sql import func

from .base import Base


class App(Base):
    """应用表 - 已发布的工作流"""
    __tablename__ = "apps"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    app_id = Column(String(64), unique=True, nullable=False, comment='应用唯一标识')
    name = Column(String(255), nullable=False, comment='应用名称')
    description = Column(Text, comment='应用描述')
    type = Column(String(32), nullable=False, default='chat', comment='类型: chat, workflow, agent')
    workflow_id = Column(String(64), nullable=False, comment='关联的工作流ID')
    status = Column(String(32), nullable=False, default='draft', comment='状态: draft, published, archived')
    icon = Column(String(64), comment='图标名称')
    version = Column(String(32), default='1.0.0', comment='版本号')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    published_at = Column(TIMESTAMP, comment='发布时间')
    endpoint = Column(String(512), comment='API端点')
    access_count = Column(Integer, default=0, comment='访问次数')
    api_key_count = Column(Integer, default=0, comment='API密钥数量')
    last_accessed = Column(TIMESTAMP, comment='最后访问时间')
    tags = Column(Text, comment='标签 (JSON数组字符串)')

    def get_tags(self) -> list:
        """获取标签列表"""
        if not self.tags:
            return []
        import json
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list):
        """设置标签列表"""
        import json
        self.tags = json.dumps(tags, ensure_ascii=False)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "app_id": self.app_id,
            "name": self.name,
            "description": self.description or "",
            "type": self.type,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "icon": self.icon,
            "version": self.version,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "endpoint": self.endpoint,
            "access_count": self.access_count or 0,
            "api_key_count": self.api_key_count or 0,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "tags": self.get_tags()
        }
