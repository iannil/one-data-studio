"""
数据监控模型
P5.1: 数据监控
P6.2: 智能预警推送
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


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


class MetricAlertRule(Base):
    """指标预警规则表 - P6.2 智能预警推送"""
    __tablename__ = "metric_alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 关联指标
    metric_id = Column(String(255), index=True)  # 指标ID
    metric_name = Column(String(255))  # 指标名称
    metric_type = Column(String(32))  # 指标类型: etl_task, data_quality, api_latency, etc.

    # 条件类型与配置
    condition_type = Column(String(32), nullable=False)  # threshold, change_rate, anomaly
    condition_config = Column(JSON)  # 条件配置
    # threshold: {"operator": "gt|lt|eq|gte|lte", "value": 100}
    # change_rate: {"period": "1h", "operator": "gt|lt", "value": 0.2}
    # anomaly: {"algorithm": "zscore|isolation_forest", "sensitivity": 0.95}

    # 告警配置
    severity = Column(String(32), default="warning")  # info, warning, critical
    alert_title_template = Column(String(512))  # 告警标题模板
    alert_message_template = Column(Text)  # 告警内容模板

    # 通知配置
    notification_channels = Column(JSON)  # ["email", "dingtalk", "wechat_work"]
    notification_targets = Column(JSON)  # ["user_id_1", "group_id_1"]

    # 冷却配置（避免重复告警）
    cooldown_minutes = Column(Integer, default=30)
    last_triggered_at = Column(DateTime)

    # 状态
    is_enabled = Column(Boolean, default=True)
    trigger_count = Column(Integer, default=0)  # 累计触发次数

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
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "condition_type": self.condition_type,
            "condition_config": self.condition_config,
            "severity": self.severity,
            "alert_title_template": self.alert_title_template,
            "alert_message_template": self.alert_message_template,
            "notification_channels": self.notification_channels,
            "notification_targets": self.notification_targets,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "is_enabled": self.is_enabled,
            "trigger_count": self.trigger_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }

    def can_trigger(self) -> bool:
        """检查是否可以触发（冷却期判断）"""
        if not self.last_triggered_at:
            return True
        from datetime import timedelta
        cooldown_delta = timedelta(minutes=self.cooldown_minutes)
        return datetime.utcnow() - self.last_triggered_at > cooldown_delta

    def render_alert(self, context: dict) -> tuple:
        """渲染告警标题和内容"""
        import re
        title = self.alert_title_template or "{{metric_name}} 告警"
        message = self.alert_message_template or "指标 {{metric_name}} 当前值: {{current_value}}"

        for key, value in context.items():
            title = re.sub(r'\{\{\s*' + key + r'\s*\}\}', str(value), title)
            message = re.sub(r'\{\{\s*' + key + r'\s*\}\}', str(value), message)

        return title, message


class AlertHistory(Base):
    """告警历史记录表 - 记录告警状态变更"""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(String(64), unique=True, nullable=False, index=True)

    # 关联告警
    alert_id = Column(String(64), index=True, nullable=False)
    rule_id = Column(String(64), index=True)

    # 状态变更
    previous_status = Column(String(32))  # active, acknowledged, resolved, null(新建)
    new_status = Column(String(32), nullable=False)

    # 变更信息
    action = Column(String(32))  # triggered, acknowledged, resolved, escalated, reopened
    action_by = Column(String(64))  # 操作人
    action_note = Column(Text)  # 备注

    # 告警快照
    alert_snapshot = Column(JSON)  # 当时的告警详情

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.history_id,
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "action": self.action,
            "action_by": self.action_by,
            "action_note": self.action_note,
            "alert_snapshot": self.alert_snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MonitoringMetricValue(Base):
    """监控指标值记录表 - 用于时序分析和异常检测"""
    __tablename__ = "monitoring_metric_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(String(255), index=True, nullable=False)
    metric_name = Column(String(255))
    metric_type = Column(String(32))

    # 指标值
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # 额外维度
    dimensions = Column(JSON)  # {"source": "etl_task_1", "env": "prod"}

    def to_dict(self):
        """转换为字典"""
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "dimensions": self.dimensions,
        }
