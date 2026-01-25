"""
实验管理模型
P2.2: 实验管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class Experiment(Base):
    """实验表"""
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 项目关联
    project_id = Column(String(64), index=True)
    project_name = Column(String(255))

    # 实验类型
    experiment_type = Column(String(32), default="training")  # training, hyperparameter, ab_test

    # 状态
    status = Column(String(32), default="created")  # created, running, completed, failed, stopped

    # 关联
    model_id = Column(String(64))
    dataset_id = Column(String(64))
    base_model = Column(String(255))

    # 超参数
    hyperparameters = Column(JSON)

    # 指标
    metrics = Column(JSON)  # {accuracy, loss, f1, etc.}
    best_metrics = Column(JSON)

    # 训练配置
    framework = Column(String(32), default="pytorch")
    epochs = Column(Integer)
    batch_size = Column(Integer)
    learning_rate = Column(Float)

    # 资源配置
    gpu_count = Column(Integer, default=0)
    gpu_type = Column(String(32))
    memory_limit = Column(String(16))
    cpu_limit = Column(String(16))

    # 时间
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 输出
    output_model_path = Column(String(512))
    checkpoint_path = Column(String(512))
    logs_path = Column(String(512))

    # 标签
    tags = Column(JSON)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "experiment_type": self.experiment_type,
            "status": self.status,
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "base_model": self.base_model,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "best_metrics": self.best_metrics,
            "framework": self.framework,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "output_model_path": self.output_model_path,
            "checkpoint_path": self.checkpoint_path,
            "logs_path": self.logs_path,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExperimentMetric(Base):
    """实验指标记录表（时序）"""
    __tablename__ = "experiment_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String(64), nullable=False, index=True)

    # 步骤
    step = Column(Integer, default=0)
    epoch = Column(Integer, default=0)

    # 指标
    metric_name = Column(String(64), nullable=False)
    metric_value = Column(Float)

    # 时间
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "experiment_id": self.experiment_id,
            "step": self.step,
            "epoch": self.epoch,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class ExperimentArtifact(Base):
    """实验产物表"""
    __tablename__ = "experiment_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(String(64), unique=True, nullable=False, index=True)
    experiment_id = Column(String(64), nullable=False, index=True)

    # 产物信息
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(32))  # model, checkpoint, log, config, data
    storage_path = Column(String(512))
    file_size = Column(Integer)
    checksum = Column(String(64))

    # 元数据
    metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.artifact_id,
            "experiment_id": self.experiment_id,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
