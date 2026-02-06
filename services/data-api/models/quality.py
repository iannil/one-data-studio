"""
数据质量模型
P1.2: 数据质量管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from .base import Base


class QualityRule(Base):
    """数据质量规则表"""
    __tablename__ = "quality_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 规则类型：completeness, uniqueness, validity, accuracy, consistency, timeliness
    rule_type = Column(String(32), nullable=False)

    # 规则配置
    target_database = Column(String(255))
    target_table = Column(String(255))
    target_column = Column(String(255))

    # 规则表达式/SQL
    rule_expression = Column(Text)  # SQL 或表达式
    threshold = Column(Float, default=100.0)  # 通过阈值百分比
    severity = Column(String(16), default="warning")  # info, warning, error, critical

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_by = Column(String(64))
    updated_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "target_database": self.target_database,
            "target_table": self.target_table,
            "target_column": self.target_column,
            "rule_expression": self.rule_expression,
            "threshold": self.threshold,
            "severity": self.severity,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QualityTask(Base):
    """数据质量检查任务表"""
    __tablename__ = "quality_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 任务配置
    rule_ids = Column(JSON)  # 关联的规则ID列表
    schedule_type = Column(String(32), default="manual")  # manual, cron, interval
    schedule_config = Column(JSON)

    # 状态
    status = Column(String(32), default="pending")  # pending, running, completed, failed
    is_active = Column(Boolean, default=True)

    # 执行统计
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)

    # 时间戳
    created_by = Column(String(64))
    updated_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.task_id,
            "name": self.name,
            "description": self.description,
            "rule_ids": self.rule_ids,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "status": self.status,
            "is_active": self.is_active,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QualityReport(Base):
    """数据质量报告表"""
    __tablename__ = "quality_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    task_id = Column(String(64), nullable=False, index=True)

    # 执行信息
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer, default=0)
    status = Column(String(32), default="running")  # running, completed, failed

    # 统计信息
    total_rules = Column(Integer, default=0)
    passed_rules = Column(Integer, default=0)
    failed_rules = Column(Integer, default=0)
    warning_rules = Column(Integer, default=0)

    # 总体得分
    overall_score = Column(Float, default=0.0)

    # 详细结果
    rule_results = Column(JSON)  # [{rule_id, passed, score, details}]

    # 错误信息
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.report_id,
            "task_id": self.task_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warning_rules": self.warning_rules,
            "overall_score": self.overall_score,
            "rule_results": self.rule_results,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QualityAlert(Base):
    """数据质量告警表"""
    __tablename__ = "quality_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, nullable=False, index=True)
    report_id = Column(String(64), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False, index=True)

    # 告警信息
    severity = Column(String(16), default="warning")  # info, warning, error, critical
    title = Column(String(255))
    message = Column(Text)

    # 相关信息
    target_database = Column(String(255))
    target_table = Column(String(255))
    target_column = Column(String(255))

    # 检测值
    expected_value = Column(String(255))
    actual_value = Column(String(255))
    score = Column(Float, default=0.0)

    # 状态
    status = Column(String(32), default="open")  # open, acknowledged, resolved
    is_enabled = Column(Boolean, default=True)  # 是否启用告警
    acknowledged_by = Column(String(64))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(64))
    resolved_at = Column(DateTime)
    resolution_note = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.alert_id,
            "report_id": self.report_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "target_database": self.target_database,
            "target_table": self.target_table,
            "target_column": self.target_column,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "score": self.score,
            "status": self.status,
            "is_enabled": self.is_enabled,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
