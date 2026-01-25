"""
数据监控模型
P5.1: 数据监控
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class DataMonitoringRule(Base):
    """数据监控规则表"""
    __tablename__ = "data_monitoring_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 监控目标
    target_type = Column(String(32))  # table, column, pipeline
    target_id = Column(String(255))
    target_name = Column(String(255))

    # 规则配置
    rule_type = Column(String(32))  # freshness, volume, quality, schema
    condition = Column(String(32))  # gt, lt, eq, between, change
    threshold = Column(Float)
    threshold_min = Column(Float)
    threshold_max = Column(Float)

    # 检查频率
    check_interval = Column(Integer, default=3600)  # 秒
    last_check_at = Column(DateTime)
    next_check_at = Column(DateTime)

    # 告警配置
    severity = Column(String(32), default="warning")  # info, warning, critical
    notification_channels = Column(JSON)  # 通知渠道列表

    # 状态
    is_enabled = Column(Boolean, default=True)
    status = Column(String(32), default="healthy")  # healthy, warning, critical

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "rule_type": self.rule_type,
            "condition": self.condition,
            "threshold": self.threshold,
            "threshold_min": self.threshold_min,
            "threshold_max": self.threshold_max,
            "check_interval": self.check_interval,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "next_check_at": self.next_check_at.isoformat() if self.next_check_at else None,
            "severity": self.severity,
            "notification_channels": self.notification_channels,
            "is_enabled": self.is_enabled,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class DataAlert(Base):
    """数据告警表"""
    __tablename__ = "data_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, nullable=False, index=True)

    # 关联规则
    rule_id = Column(String(64), index=True)
    rule_name = Column(String(255))

    # 告警信息
    title = Column(String(255), nullable=False)
    message = Column(Text)
    severity = Column(String(32), default="warning")

    # 告警详情
    target_type = Column(String(32))
    target_id = Column(String(255))
    target_name = Column(String(255))
    current_value = Column(Float)
    threshold_value = Column(Float)

    # 状态
    status = Column(String(32), default="active")  # active, acknowledged, resolved
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(64))
    resolved_at = Column(DateTime)
    resolved_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "status": self.status,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }
