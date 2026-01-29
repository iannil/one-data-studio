"""
Prompt 模板管理模型
P3.1: Prompt 模板管理
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class PromptTemplate(Base):
    """Prompt 模板表"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 分类
    category = Column(String(64))  # chat, completion, code, summary, translate, etc.

    # 模板内容
    content = Column(Text, nullable=False)  # 模板正文，支持变量占位符 {{variable}}
    variables = Column(JSON)  # 变量定义 [{name, type, default, description}]

    # 使用的模型
    model = Column(String(128))  # gpt-4o, claude-3-opus, etc.
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer)

    # 系统提示
    system_prompt = Column(Text)

    # 版本控制
    version = Column(String(32), default="1.0.0")
    is_latest = Column(Boolean, default=True)
    parent_id = Column(String(64))  # 父版本 ID

    # 使用统计
    use_count = Column(Integer, default=0)
    avg_rating = Column(Float)

    # 标签
    tags = Column(JSON)

    # 状态
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_by = Column(String(64))
    updated_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "content": self.content,
            "variables": self.variables,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "version": self.version,
            "is_latest": self.is_latest,
            "parent_id": self.parent_id,
            "use_count": self.use_count,
            "avg_rating": self.avg_rating,
            "tags": self.tags,
            "is_public": self.is_public,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
