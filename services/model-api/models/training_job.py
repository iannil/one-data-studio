"""
训练任务数据模型
Model API - TrainingJob 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Float
from sqlalchemy.sql import func

from .base import Base


class TrainingJob(Base):
    """训练任务表"""
    __tablename__ = "training_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, comment='任务唯一标识')
    name = Column(String(255), nullable=False, comment='任务名称')
    description = Column(Text, comment='任务描述')
    model_id = Column(String(64), comment='关联模型ID')
    job_type = Column(String(32), default='training', comment='任务类型: training, fine-tuning, evaluation')
    status = Column(String(32), default='pending', comment='状态: pending, queued, running, completed, failed, cancelled')

    # 数据集配置
    dataset_id = Column(String(64), comment='训练数据集ID')
    dataset_path = Column(String(512), comment='数据集路径')

    # 训练配置
    framework = Column(String(64), comment='训练框架: pytorch, tensorflow, transformers')
    base_model = Column(String(255), comment='基础模型 (如 HuggingFace model_id)')
    hyperparameters = Column(Text, comment='超参数配置 (JSON)')
    resources = Column(Text, comment='资源配置 (JSON): gpu_count, memory, cpu')

    # 训练状态
    progress = Column(Float, default=0.0, comment='训练进度 (0-100)')
    current_epoch = Column(Integer, default=0, comment='当前 epoch')
    total_epochs = Column(Integer, comment='总 epoch 数')
    current_step = Column(Integer, default=0, comment='当前步数')
    total_steps = Column(Integer, comment='总步数')

    # 训练结果
    metrics = Column(Text, comment='训练指标 (JSON): loss, accuracy, etc.')
    output_model_path = Column(String(512), comment='输出模型路径')
    logs_path = Column(String(512), comment='日志路径')

    # 错误信息
    error_message = Column(Text, comment='错误信息')

    # 时间戳
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_hyperparameters(self) -> dict:
        """获取超参数配置"""
        if not self.hyperparameters:
            return {}
        try:
            return json.loads(self.hyperparameters)
        except json.JSONDecodeError:
            return {}

    def set_hyperparameters(self, params: dict):
        """设置超参数配置"""
        self.hyperparameters = json.dumps(params, ensure_ascii=False)

    def get_resources(self) -> dict:
        """获取资源配置"""
        if not self.resources:
            return {"gpu_count": 0, "memory": "8Gi", "cpu": "4"}
        try:
            return json.loads(self.resources)
        except json.JSONDecodeError:
            return {"gpu_count": 0, "memory": "8Gi", "cpu": "4"}

    def set_resources(self, resources: dict):
        """设置资源配置"""
        self.resources = json.dumps(resources, ensure_ascii=False)

    def get_metrics(self) -> dict:
        """获取训练指标"""
        if not self.metrics:
            return {}
        try:
            return json.loads(self.metrics)
        except json.JSONDecodeError:
            return {}

    def set_metrics(self, metrics: dict):
        """设置训练指标"""
        self.metrics = json.dumps(metrics, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.job_id,
            "name": self.name,
            "description": self.description or "",
            "model_id": self.model_id,
            "job_type": self.job_type,
            "status": self.status,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "framework": self.framework,
            "base_model": self.base_model,
            "hyperparameters": self.get_hyperparameters(),
            "resources": self.get_resources(),
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "metrics": self.get_metrics(),
            "output_model_path": self.output_model_path,
            "logs_path": self.logs_path,
            "error_message": self.error_message,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BatchPredictionJob(Base):
    """批量预测任务表"""
    __tablename__ = "batch_prediction_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, comment='任务唯一标识')
    name = Column(String(255), nullable=False, comment='任务名称')
    model_id = Column(String(64), nullable=False, comment='模型ID')
    deployment_id = Column(String(64), comment='部署ID')
    status = Column(String(32), default='pending', comment='状态: pending, running, completed, failed')

    # 输入输出
    input_path = Column(String(512), nullable=False, comment='输入数据路径')
    output_path = Column(String(512), comment='输出结果路径')
    input_format = Column(String(32), default='jsonl', comment='输入格式: jsonl, csv, parquet')
    output_format = Column(String(32), default='jsonl', comment='输出格式: jsonl, csv, parquet')

    # 进度
    total_records = Column(Integer, comment='总记录数')
    processed_records = Column(Integer, default=0, comment='已处理记录数')
    failed_records = Column(Integer, default=0, comment='失败记录数')
    progress = Column(Float, default=0.0, comment='进度 (0-100)')

    # 配置
    batch_size = Column(Integer, default=32, comment='批处理大小')
    config = Column(Text, comment='预测配置 (JSON)')

    # 错误信息
    error_message = Column(Text, comment='错误信息')

    # 时间戳
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')

    def get_config(self) -> dict:
        """获取预测配置"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict):
        """设置预测配置"""
        self.config = json.dumps(config, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.job_id,
            "name": self.name,
            "model_id": self.model_id,
            "deployment_id": self.deployment_id,
            "status": self.status,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "input_format": self.input_format,
            "output_format": self.output_format,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "failed_records": self.failed_records,
            "progress": self.progress,
            "batch_size": self.batch_size,
            "config": self.get_config(),
            "error_message": self.error_message,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
