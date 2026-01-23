"""
工作流调度模型
Phase 7: Sprint 7.4
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, BigInteger, Text

from .base import Base


class WorkflowSchedule(Base):
    """工作流调度表

    支持三种调度类型：
    - cron: Cron 表达式调度
    - interval: 固定间隔调度
    - event: 事件触发调度
    """

    __tablename__ = "workflow_schedules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    schedule_id = Column(String(64), unique=True, nullable=False, index=True)
    workflow_id = Column(String(64), nullable=False, index=True)

    # 调度类型: cron, interval, event
    schedule_type = Column(String(32), nullable=False, default="cron")

    # Cron 调度参数
    cron_expression = Column(String(100), nullable=True)

    # 间隔调度参数（秒）
    interval_seconds = Column(Integer, nullable=True)

    # 事件触发参数
    event_trigger = Column(String(64), nullable=True)

    # 状态
    enabled = Column(Boolean, default=True, nullable=False)

    # 运行时间记录
    next_run_at = Column(TIMESTAMP, nullable=True)
    last_run_at = Column(TIMESTAMP, nullable=True)

    # 元数据
    description = Column(Text, nullable=True)
    created_by = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "workflow_id": self.workflow_id,
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "event_trigger": self.event_trigger,
            "enabled": self.enabled,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_next_run_time(self) -> datetime:
        """计算下次运行时间"""
        if self.schedule_type == "cron" and self.cron_expression:
            try:
                from croniter import croniter
                base = self.last_run_at or datetime.utcnow()
                cron = croniter(self.cron_expression, base)
                return cron.get_next(datetime)
            except Exception:
                return None
        elif self.schedule_type == "interval" and self.interval_seconds:
            base = self.last_run_at or datetime.utcnow()
            return datetime.fromtimestamp(base.timestamp() + self.interval_seconds)
        return None
