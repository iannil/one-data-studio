"""
BI 仪表板模型
P5.2: BI 仪表板
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON
)
from .base import Base


class BIDashboard(Base):
    """BI 仪表板表"""
    __tablename__ = "bi_dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 布局配置
    layout = Column(JSON)  # 图表布局
    theme = Column(String(32), default="light")  # light, dark

    # 全局筛选器
    filters = Column(JSON)

    # 刷新设置
    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=300)  # 秒

    # 分享设置
    is_public = Column(Boolean, default=False)
    share_token = Column(String(128))

    # 收藏统计
    favorite_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.dashboard_id,
            "name": self.name,
            "description": self.description,
            "layout": self.layout,
            "theme": self.theme,
            "filters": self.filters,
            "auto_refresh": self.auto_refresh,
            "refresh_interval": self.refresh_interval,
            "is_public": self.is_public,
            "favorite_count": self.favorite_count,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class BIChart(Base):
    """BI 图表表"""
    __tablename__ = "bi_charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chart_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 所属仪表板
    dashboard_id = Column(String(64), index=True)

    # 图表类型
    chart_type = Column(String(32))  # line, bar, pie, table, area, scatter, etc.

    # 数据源配置
    datasource_type = Column(String(32))  # sql, api, dataset
    datasource_id = Column(String(64))
    sql_query = Column(Text)

    # 图表配置
    config = Column(JSON)  # 图表样式配置
    dimensions = Column(JSON)  # 维度字段
    metrics = Column(JSON)  # 指标字段
    filters = Column(JSON)  # 图表级筛选

    # 缓存设置
    cache_enabled = Column(Boolean, default=True)
    cache_ttl = Column(Integer, default=300)  # 秒

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.chart_id,
            "name": self.name,
            "description": self.description,
            "dashboard_id": self.dashboard_id,
            "chart_type": self.chart_type,
            "datasource_type": self.datasource_type,
            "datasource_id": self.datasource_id,
            "sql_query": self.sql_query,
            "config": self.config,
            "dimensions": self.dimensions,
            "metrics": self.metrics,
            "filters": self.filters,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
