"""
特征存储模型
P4.3: 特征存储
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class FeatureGroup(Base):
    """特征组表"""
    __tablename__ = "feature_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 实体配置
    entity_name = Column(String(128))  # user, product, order, etc.
    entity_key = Column(String(128))  # user_id, product_id, etc.

    # 数据源
    source_type = Column(String(32))  # batch, streaming
    source_config = Column(JSON)

    # 存储配置
    online_store = Column(Boolean, default=True)
    offline_store = Column(Boolean, default=True)
    ttl_days = Column(Integer)

    # 统计
    feature_count = Column(Integer, default=0)

    # 标签
    tags = Column(JSON)

    # 状态
    status = Column(String(32), default="active")  # active, deprecated

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.group_id,
            "name": self.name,
            "description": self.description,
            "entity_name": self.entity_name,
            "entity_key": self.entity_key,
            "source_type": self.source_type,
            "source_config": self.source_config,
            "online_store": self.online_store,
            "offline_store": self.offline_store,
            "ttl_days": self.ttl_days,
            "feature_count": self.feature_count,
            "tags": self.tags,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Feature(Base):
    """特征表"""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 所属特征组
    group_id = Column(String(64), index=True)
    group_name = Column(String(255))

    # 特征类型
    data_type = Column(String(32), default="float")  # int, float, string, array, embedding
    feature_type = Column(String(32), default="raw")  # raw, derived, aggregated

    # 计算逻辑
    expression = Column(Text)  # SQL 表达式或计算逻辑
    dependencies = Column(JSON)  # 依赖的其他特征

    # 聚合配置（如果是聚合特征）
    aggregation_type = Column(String(32))  # sum, avg, count, max, min
    aggregation_window = Column(String(32))  # 1h, 1d, 7d, 30d

    # 统计信息
    statistics = Column(JSON)  # {min, max, mean, std, null_ratio}
    last_computed_at = Column(DateTime)

    # 标签
    tags = Column(JSON)

    # 状态
    status = Column(String(32), default="active")  # active, deprecated, computing

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "data_type": self.data_type,
            "feature_type": self.feature_type,
            "expression": self.expression,
            "dependencies": self.dependencies,
            "aggregation_type": self.aggregation_type,
            "aggregation_window": self.aggregation_window,
            "statistics": self.statistics,
            "last_computed_at": self.last_computed_at.isoformat() if self.last_computed_at else None,
            "tags": self.tags,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
