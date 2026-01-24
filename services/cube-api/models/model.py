"""
模型管理数据模型
Cube API - MLModel 和 ModelVersion 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Float, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class MLModel(Base):
    """机器学习模型表"""
    __tablename__ = "ml_models"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String(64), unique=True, nullable=False, comment='模型唯一标识')
    name = Column(String(255), nullable=False, comment='模型名称')
    description = Column(Text, comment='模型描述')
    model_type = Column(String(64), nullable=False, comment='模型类型: text-generation, text-classification, etc.')
    framework = Column(String(64), comment='框架: transformers, pytorch, tensorflow')
    source = Column(String(32), default='local', comment='来源: local, huggingface, custom')
    source_id = Column(String(255), comment='来源ID (如 HuggingFace model_id)')
    status = Column(String(32), default='created', comment='状态: created, downloading, ready, deploying, serving, error')
    tags = Column(Text, comment='标签 (JSON数组)')
    config = Column(Text, comment='模型配置 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    deployments = relationship("ModelDeployment", back_populates="model", cascade="all, delete-orphan")

    def get_tags(self) -> list:
        """获取标签列表"""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list):
        """设置标签"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def get_config(self) -> dict:
        """获取模型配置"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict):
        """设置模型配置"""
        self.config = json.dumps(config, ensure_ascii=False)

    def to_dict(self, include_versions: bool = False):
        """转换为字典"""
        result = {
            "id": self.model_id,
            "name": self.name,
            "description": self.description or "",
            "model_type": self.model_type,
            "framework": self.framework,
            "source": self.source,
            "source_id": self.source_id,
            "status": self.status,
            "tags": self.get_tags(),
            "config": self.get_config(),
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_versions:
            result["versions"] = [v.to_dict() for v in self.versions]
        return result


class ModelVersion(Base):
    """模型版本表"""
    __tablename__ = "model_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_id = Column(String(64), unique=True, nullable=False, comment='版本唯一标识')
    model_id = Column(String(64), ForeignKey('ml_models.model_id'), nullable=False, comment='所属模型ID')
    version = Column(String(32), nullable=False, comment='版本号')
    storage_path = Column(String(512), comment='存储路径 (MinIO/本地)')
    file_size = Column(BigInteger, comment='文件大小 (字节)')
    checksum = Column(String(128), comment='文件校验和')
    status = Column(String(32), default='pending', comment='状态: pending, uploading, ready, error')
    metrics = Column(Text, comment='评估指标 (JSON)')
    extra_metadata = Column(Text, comment='元数据 (JSON)')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 关系
    model = relationship("MLModel", back_populates="versions")

    def get_metrics(self) -> dict:
        """获取评估指标"""
        if not self.metrics:
            return {}
        try:
            return json.loads(self.metrics)
        except json.JSONDecodeError:
            return {}

    def set_metrics(self, metrics: dict):
        """设置评估指标"""
        self.metrics = json.dumps(metrics, ensure_ascii=False)

    def get_metadata(self) -> dict:
        """获取元数据"""
        if not self.extra_metadata:
            return {}
        try:
            return json.loads(self.extra_metadata)
        except json.JSONDecodeError:
            return {}

    def set_metadata(self, metadata: dict):
        """设置元数据"""
        self.extra_metadata = json.dumps(metadata, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.version_id,
            "model_id": self.model_id,
            "version": self.version,
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "status": self.status,
            "metrics": self.get_metrics(),
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelDeployment(Base):
    """模型部署表"""
    __tablename__ = "model_deployments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    deployment_id = Column(String(64), unique=True, nullable=False, comment='部署唯一标识')
    model_id = Column(String(64), ForeignKey('ml_models.model_id'), nullable=False, comment='模型ID')
    version_id = Column(String(64), comment='版本ID')
    endpoint = Column(String(512), comment='服务端点 URL')
    replicas = Column(Integer, default=1, comment='副本数')
    gpu_count = Column(Integer, default=0, comment='GPU 数量')
    memory_limit = Column(String(32), default='4Gi', comment='内存限制')
    cpu_limit = Column(String(32), default='2', comment='CPU 限制')
    status = Column(String(32), default='pending', comment='状态: pending, deploying, running, stopped, error')
    config = Column(Text, comment='部署配置 (JSON)')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    model = relationship("MLModel", back_populates="deployments")

    def get_config(self) -> dict:
        """获取部署配置"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict):
        """设置部署配置"""
        self.config = json.dumps(config, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.deployment_id,
            "model_id": self.model_id,
            "version_id": self.version_id,
            "endpoint": self.endpoint,
            "replicas": self.replicas,
            "gpu_count": self.gpu_count,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "status": self.status,
            "config": self.get_config(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
