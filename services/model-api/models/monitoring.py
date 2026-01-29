"""
系统监控模型
P4.4: 系统监控
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class MonitoringDashboard(Base):
    """监控仪表板表"""
    __tablename__ = "monitoring_dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 面板配置
    panels = Column(JSON)  # [{id, type, title, query, position, size}]
    layout = Column(JSON)  # 布局配置
    variables = Column(JSON)  # 变量定义

    # 刷新配置
    refresh_interval = Column(Integer, default=30)  # seconds

    # 时间范围
    default_time_range = Column(String(32), default="1h")  # 1h, 6h, 24h, 7d

    # 标签
    tags = Column(JSON)

    # 状态
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.dashboard_id,
            "name": self.name,
            "description": self.description,
            "panels": self.panels,
            "layout": self.layout,
            "variables": self.variables,
            "refresh_interval": self.refresh_interval,
            "default_time_range": self.default_time_range,
            "tags": self.tags,
            "is_public": self.is_public,
            "is_default": self.is_default,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlertRule(Base):
    """告警规则表"""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 监控目标
    metric_name = Column(String(128), nullable=False)
    metric_labels = Column(JSON)  # 标签筛选

    # 告警条件
    condition = Column(String(32), default="gt")  # gt, lt, eq, ne, gte, lte
    threshold = Column(Float, nullable=False)
    duration = Column(Integer, default=60)  # 持续时间（秒）

    # 告警级别
    severity = Column(String(16), default="warning")  # info, warning, critical

    # 通知配置
    notification_channels = Column(JSON)  # [channel_id, ...]
    notification_interval = Column(Integer, default=300)  # 通知间隔（秒）

    # 状态
    is_enabled = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime)
    trigger_count = Column(Integer, default=0)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "metric_labels": self.metric_labels,
            "condition": self.condition,
            "threshold": self.threshold,
            "duration": self.duration,
            "severity": self.severity,
            "notification_channels": self.notification_channels,
            "notification_interval": self.notification_interval,
            "is_enabled": self.is_enabled,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "trigger_count": self.trigger_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlertNotification(Base):
    """告警通知表"""
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(64), unique=True, nullable=False, index=True)
    rule_id = Column(String(64), nullable=False, index=True)
    rule_name = Column(String(255))

    # 告警信息
    metric_name = Column(String(128))
    metric_value = Column(Float)
    threshold = Column(Float)
    severity = Column(String(16))
    message = Column(Text)

    # 状态
    status = Column(String(32), default="firing")  # firing, resolved, acknowledged
    acknowledged_by = Column(String(64))
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    # 时间
    fired_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.notification_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "severity": self.severity,
            "message": self.message,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
        }
