"""
Flink 实时计算模型
P4.1: 实时计算（Flink）管理
P4.2: Streaming IDE
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class FlinkJob(Base):
    """Flink 作业表"""
    __tablename__ = "flink_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 作业类型
    job_type = Column(String(32), default="sql")  # sql, jar, python

    # SQL 作业配置
    sql_content = Column(Text)

    # JAR 作业配置
    jar_path = Column(String(512))
    main_class = Column(String(255))
    program_args = Column(Text)

    # Flink 配置
    parallelism = Column(Integer, default=1)
    checkpoint_interval = Column(Integer, default=60000)  # ms
    savepoint_path = Column(String(512))

    # 资源配置
    task_manager_memory = Column(String(16), default="1024m")
    job_manager_memory = Column(String(16), default="1024m")
    task_slots = Column(Integer, default=1)

    # 状态
    status = Column(String(32), default="created")  # created, running, stopped, failed, finished
    flink_job_id = Column(String(64))  # Flink 集群返回的 Job ID

    # 执行时间
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 指标
    records_in = Column(Integer, default=0)
    records_out = Column(Integer, default=0)
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)

    # 错误信息
    error_message = Column(Text)

    # 标签
    tags = Column(JSON)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.job_id,
            "name": self.name,
            "description": self.description,
            "job_type": self.job_type,
            "sql_content": self.sql_content,
            "jar_path": self.jar_path,
            "main_class": self.main_class,
            "program_args": self.program_args,
            "parallelism": self.parallelism,
            "checkpoint_interval": self.checkpoint_interval,
            "savepoint_path": self.savepoint_path,
            "task_manager_memory": self.task_manager_memory,
            "job_manager_memory": self.job_manager_memory,
            "task_slots": self.task_slots,
            "status": self.status,
            "flink_job_id": self.flink_job_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "duration_seconds": self.duration_seconds,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "error_message": self.error_message,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FlinkJobLog(Base):
    """Flink 作业日志表"""
    __tablename__ = "flink_job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=False, index=True)

    # 日志内容
    level = Column(String(16), default="INFO")  # DEBUG, INFO, WARN, ERROR
    message = Column(Text)
    logger_name = Column(String(255))

    # 时间
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "level": self.level,
            "message": self.message,
            "logger_name": self.logger_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class FlinkSavedQuery(Base):
    """Flink SQL 保存的查询"""
    __tablename__ = "flink_saved_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # SQL 内容
    sql_content = Column(Text, nullable=False)

    # 分类
    category = Column(String(64))

    # 标签
    tags = Column(JSON)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.query_id,
            "name": self.name,
            "description": self.description,
            "sql_content": self.sql_content,
            "category": self.category,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
