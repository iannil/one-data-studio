"""
AI Hub 模型
P4.7: AI Hub
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class AIHubModel(Base):
    """AI Hub 模型市场表"""
    __tablename__ = "aihub_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 模型信息
    author = Column(String(128))
    source = Column(String(32), default="huggingface")  # huggingface, modelscope, local
    source_id = Column(String(255))  # 原始模型 ID

    # 分类
    category = Column(String(64))  # llm, cv, nlp, audio, multimodal
    task_type = Column(String(64))  # text-generation, classification, etc.

    # 规格
    model_size = Column(String(32))  # 7B, 13B, 70B
    parameters = Column(Float)  # 参数量（B）
    context_length = Column(Integer)
    license = Column(String(64))

    # 统计
    downloads = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    stars = Column(Integer, default=0)

    # 标签
    tags = Column(JSON)

    # 是否官方推荐
    is_featured = Column(Boolean, default=False)
    is_trending = Column(Boolean, default=False)

    # 状态
    status = Column(String(32), default="available")  # available, deprecated, importing

    # 本地导入信息
    local_model_id = Column(String(64))
    imported_at = Column(DateTime)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.model_id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "source": self.source,
            "source_id": self.source_id,
            "category": self.category,
            "task_type": self.task_type,
            "model_size": self.model_size,
            "parameters": self.parameters,
            "context_length": self.context_length,
            "license": self.license,
            "downloads": self.downloads,
            "likes": self.likes,
            "stars": self.stars,
            "tags": self.tags,
            "is_featured": self.is_featured,
            "is_trending": self.is_trending,
            "status": self.status,
            "local_model_id": self.local_model_id,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AIHubCategory(Base):
    """AI Hub 分类表"""
    __tablename__ = "aihub_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)

    # 父分类
    parent_id = Column(String(64))

    # 图标
    icon = Column(String(64))

    # 排序
    sort_order = Column(Integer, default=0)

    # 统计
    model_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.category_id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "model_count": self.model_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
