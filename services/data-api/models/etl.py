"""
ETL 任务模型
P1.1: ETL 任务管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Enum as SQLEnum
)
import enum
from .base import Base


class ETLTaskStatus(enum.Enum):
    """ETL 任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ETLTaskType(enum.Enum):
    """ETL 任务类型"""
    BATCH = "batch"
    INCREMENTAL = "incremental"
    CDC = "cdc"
    FULL_SYNC = "full_sync"


class ETLEngineType(enum.Enum):
    """ETL 执行引擎类型"""
    BUILTIN = "builtin"  # 内置引擎
    KETTLE = "kettle"    # Kettle/PDI 引擎
    HOP = "hop"          # Apache Hop 引擎
    SPARK = "spark"      # Spark 引擎
    FLINK = "flink"      # Flink 引擎


class ETLTask(Base):
    """ETL 任务表"""
    __tablename__ = "etl_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 任务类型和状态
    task_type = Column(String(32), default="batch")
    engine_type = Column(String(32), default="builtin")  # builtin, kettle, spark, flink
    status = Column(String(32), default="pending")

    # 数据源配置
    source_type = Column(String(64))  # mysql, postgres, hive, kafka, etc.
    source_config = Column(JSON)  # 连接配置
    source_query = Column(Text)  # 源查询/表名

    # 目标配置
    target_type = Column(String(64))  # mysql, hive, s3, etc.
    target_config = Column(JSON)  # 目标连接配置
    target_table = Column(String(255))  # 目标表名

    # 转换配置
    transform_config = Column(JSON)  # 转换规则

    # 调度配置
    schedule_type = Column(String(32), default="manual")  # manual, cron, interval
    schedule_config = Column(JSON)  # cron 表达式或间隔配置

    # Kettle 引擎配置（仅当 engine_type='kettle' 时使用）
    kettle_job_path = Column(String(512))  # Kettle 作业文件路径 (.kjb)
    kettle_trans_path = Column(String(512))  # Kettle 转换文件路径 (.ktr)
    kettle_repository = Column(String(255))  # Kettle 仓库名称
    kettle_directory = Column(String(255))  # Kettle 目录
    kettle_params = Column(JSON)  # Kettle 参数

    # Hop 引擎配置（仅当 engine_type='hop' 时使用）
    hop_pipeline_path = Column(String(512))  # Hop Pipeline 文件路径 (.hpl)
    hop_workflow_path = Column(String(512))  # Hop Workflow 文件路径 (.hwf)
    hop_params = Column(JSON)  # Hop 参数

    # 执行信息
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    next_run_at = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)

    # 最近一次执行统计
    last_row_count = Column(Integer, default=0)
    last_duration_seconds = Column(Integer, default=0)
    last_error = Column(Text)

    # 创建者信息
    created_by = Column(String(64))
    updated_by = Column(String(64))

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "engine_type": self.engine_type,
            "status": self.status,
            "source_type": self.source_type,
            "source_config": self.source_config,
            "source_query": self.source_query,
            "target_type": self.target_type,
            "target_config": self.target_config,
            "target_table": self.target_table,
            "transform_config": self.transform_config,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "kettle_job_path": self.kettle_job_path,
            "kettle_trans_path": self.kettle_trans_path,
            "kettle_repository": self.kettle_repository,
            "kettle_directory": self.kettle_directory,
            "kettle_params": self.kettle_params,
            "hop_pipeline_path": self.hop_pipeline_path,
            "hop_workflow_path": self.hop_workflow_path,
            "hop_params": self.hop_params,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_row_count": self.last_row_count,
            "last_duration_seconds": self.last_duration_seconds,
            "last_error": self.last_error,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ETLTaskLog(Base):
    """ETL 任务执行日志表"""
    __tablename__ = "etl_task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True)
    task_id = Column(String(64), nullable=False, index=True)

    # 执行信息
    status = Column(String(32), default="running")  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer, default=0)

    # 统计信息
    rows_read = Column(Integer, default=0)
    rows_written = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    bytes_read = Column(Integer, default=0)
    bytes_written = Column(Integer, default=0)

    # 错误信息
    error_message = Column(Text)
    error_stack = Column(Text)

    # 详细日志
    log_content = Column(Text)  # 执行过程日志

    # 触发方式
    trigger_type = Column(String(32), default="manual")  # manual, scheduled, api
    triggered_by = Column(String(64))

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.log_id,
            "task_id": self.task_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "rows_read": self.rows_read,
            "rows_written": self.rows_written,
            "rows_failed": self.rows_failed,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "error_message": self.error_message,
            "trigger_type": self.trigger_type,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
