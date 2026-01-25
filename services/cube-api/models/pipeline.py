"""
Pipeline 编排模型
P2.3: Pipeline 编排后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class Pipeline(Base):
    """Pipeline 表"""
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 项目关联
    project_id = Column(String(64), index=True)

    # Pipeline 定义
    nodes = Column(JSON)  # [{id, type, config, position}]
    edges = Column(JSON)  # [{source, target, sourceHandle, targetHandle}]

    # 版本
    version = Column(String(32), default="1.0.0")

    # 状态
    is_active = Column(Boolean, default=True)

    # 调度配置
    schedule_enabled = Column(Boolean, default=False)
    schedule_type = Column(String(32))  # cron, interval
    schedule_config = Column(JSON)  # cron expression or interval config
    next_run_at = Column(DateTime)

    # 执行统计
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)

    # 标签
    tags = Column(JSON)

    # 时间戳
    created_by = Column(String(64))
    updated_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.pipeline_id,
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "version": self.version,
            "is_active": self.is_active,
            "schedule_enabled": self.schedule_enabled,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PipelineExecution(Base):
    """Pipeline 执行记录表"""
    __tablename__ = "pipeline_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    pipeline_id = Column(String(64), nullable=False, index=True)

    # 执行信息
    status = Column(String(32), default="pending")  # pending, running, completed, failed, stopped
    trigger_type = Column(String(32), default="manual")  # manual, scheduled, api

    # 时间
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 节点状态
    node_statuses = Column(JSON)  # {node_id: {status, started_at, finished_at, error}}

    # 输入输出
    inputs = Column(JSON)
    outputs = Column(JSON)

    # 错误信息
    error_message = Column(Text)
    error_node_id = Column(String(64))

    # 日志
    logs = Column(Text)

    # 触发者
    triggered_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.execution_id,
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "trigger_type": self.trigger_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "node_statuses": self.node_statuses,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error_message": self.error_message,
            "error_node_id": self.error_node_id,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PipelineTemplate(Base):
    """Pipeline 模板表"""
    __tablename__ = "pipeline_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 模板分类
    category = Column(String(64))  # data_processing, training, inference, etc.

    # 模板定义
    nodes = Column(JSON)
    edges = Column(JSON)

    # 参数
    parameters = Column(JSON)  # 可配置参数定义

    # 预览图
    thumbnail = Column(String(512))

    # 使用统计
    use_count = Column(Integer, default=0)

    # 状态
    is_public = Column(Boolean, default=True)
    is_official = Column(Boolean, default=False)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "nodes": self.nodes,
            "edges": self.edges,
            "parameters": self.parameters,
            "thumbnail": self.thumbnail,
            "use_count": self.use_count,
            "is_public": self.is_public,
            "is_official": self.is_official,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
