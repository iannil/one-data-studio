"""
离线处理模型
P5.3: 离线处理
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON
)
from .base import Base


class OfflineTask(Base):
    """离线任务表"""
    __tablename__ = "offline_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 任务类型
    task_type = Column(String(32))  # spark, hive, presto, python

    # 任务配置
    sql_content = Column(Text)
    script_path = Column(String(512))
    script_content = Column(Text)
    parameters = Column(JSON)

    # 资源配置
    executor_memory = Column(String(32), default="2g")
    executor_cores = Column(Integer, default=2)
    num_executors = Column(Integer, default=2)

    # 调度配置
    schedule_type = Column(String(32), default="manual")  # manual, cron, dependency
    cron_expression = Column(String(64))
    dependencies = Column(JSON)  # 依赖任务列表

    # 输出配置
    output_table = Column(String(255))
    output_path = Column(String(512))
    output_format = Column(String(32))

    # 执行状态
    status = Column(String(32), default="idle")  # idle, queued, running, success, failed
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "sql_content": self.sql_content,
            "script_path": self.script_path,
            "parameters": self.parameters,
            "executor_memory": self.executor_memory,
            "executor_cores": self.executor_cores,
            "num_executors": self.num_executors,
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "dependencies": self.dependencies,
            "output_table": self.output_table,
            "output_path": self.output_path,
            "output_format": self.output_format,
            "status": self.status,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class OfflineTaskLog(Base):
    """离线任务执行日志表"""
    __tablename__ = "offline_task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True)

    # 关联任务
    task_id = Column(String(64), index=True)

    # 执行信息
    execution_id = Column(String(64))
    status = Column(String(32))  # running, success, failed, cancelled

    # 时间信息
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 执行结果
    output_rows = Column(Integer)
    output_size_bytes = Column(Integer)
    error_message = Column(Text)

    # 日志内容
    log_content = Column(Text)

    # 触发方式
    triggered_by = Column(String(32))  # manual, schedule, dependency
    triggered_user = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.log_id,
            "task_id": self.task_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "output_rows": self.output_rows,
            "output_size_bytes": self.output_size_bytes,
            "error_message": self.error_message,
            "triggered_by": self.triggered_by,
            "triggered_user": self.triggered_user,
        }
