"""
数据资产模型
P5.4: 数据资产目录
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class DataAsset(Base):
    """数据资产表"""
    __tablename__ = "data_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 资产类型
    asset_type = Column(String(32))  # table, view, dataset, file, api

    # 分类
    category_id = Column(String(64), index=True)
    category_name = Column(String(128))

    # 来源
    source_type = Column(String(32))  # database, datalake, file, external
    source_id = Column(String(64))
    source_name = Column(String(255))

    # 路径/位置
    path = Column(String(512))
    database_name = Column(String(128))
    schema_name = Column(String(128))
    table_name = Column(String(255))

    # 元数据
    columns = Column(JSON)  # 字段列表
    row_count = Column(Integer)
    size_bytes = Column(Integer)

    # 标签
    tags = Column(JSON)

    # 所有者
    owner = Column(String(64))
    owner_name = Column(String(128))

    # 数据等级
    data_level = Column(String(32))  # public, internal, confidential, restricted

    # 质量评分
    quality_score = Column(Float)

    # 统计
    view_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)

    # 状态
    status = Column(String(32), default="active")  # active, deprecated, archived

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.asset_id,
            "name": self.name,
            "description": self.description,
            "asset_type": self.asset_type,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "path": self.path,
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "columns": self.columns,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "tags": self.tags,
            "owner": self.owner,
            "owner_name": self.owner_name,
            "data_level": self.data_level,
            "quality_score": self.quality_score,
            "view_count": self.view_count,
            "collect_count": self.collect_count,
            "usage_count": self.usage_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
        }


class AssetCategory(Base):
    """资产分类表"""
    __tablename__ = "asset_categories"

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
    asset_count = Column(Integer, default=0)

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
            "asset_count": self.asset_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssetCollection(Base):
    """资产收藏表"""
    __tablename__ = "asset_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 收藏信息
    asset_id = Column(String(64), index=True)
    user_id = Column(String(64), index=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "asset_id": self.asset_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
