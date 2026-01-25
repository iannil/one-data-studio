"""
指标管理模型
P1.4: 指标管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class MetricDefinition(Base):
    """指标定义表"""
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)

    # 分类
    category = Column(String(64))  # business, technical, quality, performance
    subcategory = Column(String(64))
    tags = Column(JSON)

    # 指标类型
    metric_type = Column(String(32), default="count")  # count, sum, avg, min, max, rate, ratio, custom

    # 计算定义
    source_database = Column(String(255))
    source_table = Column(String(255))
    source_column = Column(String(255))
    calculation_sql = Column(Text)  # 自定义计算 SQL
    aggregation_type = Column(String(32))  # daily, hourly, realtime
    time_column = Column(String(255))  # 时间列名

    # 单位和格式
    unit = Column(String(32))  # count, percent, currency, etc.
    decimal_places = Column(Integer, default=2)
    format_pattern = Column(String(64))

    # 阈值和告警
    warning_threshold = Column(Float)
    critical_threshold = Column(Float)
    threshold_direction = Column(String(16), default="above")  # above, below

    # 负责人
    owner = Column(String(64))
    owner_team = Column(String(64))

    # 状态
    is_active = Column(Boolean, default=True)
    is_certified = Column(Boolean, default=False)  # 是否认证指标

    # 时间戳
    created_by = Column(String(64))
    updated_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.metric_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "metric_type": self.metric_type,
            "source_database": self.source_database,
            "source_table": self.source_table,
            "source_column": self.source_column,
            "calculation_sql": self.calculation_sql,
            "aggregation_type": self.aggregation_type,
            "time_column": self.time_column,
            "unit": self.unit,
            "decimal_places": self.decimal_places,
            "format_pattern": self.format_pattern,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "threshold_direction": self.threshold_direction,
            "owner": self.owner,
            "owner_team": self.owner_team,
            "is_active": self.is_active,
            "is_certified": self.is_certified,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MetricValue(Base):
    """指标数据值表"""
    __tablename__ = "metric_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(String(64), nullable=False, index=True)

    # 时间维度
    time_key = Column(DateTime, nullable=False, index=True)
    granularity = Column(String(16), default="daily")  # hourly, daily, weekly, monthly

    # 值
    value = Column(Float)
    previous_value = Column(Float)  # 上期值
    change_value = Column(Float)  # 变化值
    change_percent = Column(Float)  # 变化百分比

    # 维度（用于切片）
    dimension_1 = Column(String(255))  # 可选维度
    dimension_2 = Column(String(255))
    dimension_3 = Column(String(255))
    dimensions = Column(JSON)  # 额外维度

    # 状态
    status = Column(String(16), default="normal")  # normal, warning, critical

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "metric_id": self.metric_id,
            "time_key": self.time_key.isoformat() if self.time_key else None,
            "granularity": self.granularity,
            "value": self.value,
            "previous_value": self.previous_value,
            "change_value": self.change_value,
            "change_percent": self.change_percent,
            "dimension_1": self.dimension_1,
            "dimension_2": self.dimension_2,
            "dimension_3": self.dimension_3,
            "dimensions": self.dimensions,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MetricCategory(Base):
    """指标分类表"""
    __tablename__ = "metric_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    parent_id = Column(String(64))  # 父分类
    level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    icon = Column(String(64))
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.category_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "icon": self.icon,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
