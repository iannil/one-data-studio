"""
模型服务管理模型
P2.1: 模型服务管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class ServingService(Base):
    """模型服务表"""
    __tablename__ = "serving_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 关联模型
    model_id = Column(String(64), index=True)
    model_name = Column(String(255))
    version_id = Column(String(64))

    # 服务配置
    service_type = Column(String(32), default="inference")  # inference, embedding, rerank
    framework = Column(String(32), default="vllm")  # vllm, tgi, triton, custom

    # 资源配置
    replicas = Column(Integer, default=1)
    gpu_count = Column(Integer, default=0)
    gpu_type = Column(String(32))  # A100, V100, T4, etc.
    memory_limit = Column(String(16), default="8Gi")
    cpu_limit = Column(String(16), default="4")

    # 端点信息
    endpoint = Column(String(512))
    internal_endpoint = Column(String(512))
    port = Column(Integer, default=8080)

    # 状态
    status = Column(String(32), default="pending")  # pending, deploying, running, stopped, failed
    health_status = Column(String(32), default="unknown")  # healthy, unhealthy, unknown

    # 配置
    config = Column(JSON)  # 额外配置（max_tokens, temperature等）
    env_vars = Column(JSON)  # 环境变量

    # 指标
    request_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    last_request_at = Column(DateTime)

    # 自动扩缩容
    auto_scale = Column(Boolean, default=False)
    min_replicas = Column(Integer, default=1)
    max_replicas = Column(Integer, default=10)
    target_cpu_utilization = Column(Integer, default=70)

    # 时间戳
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.service_id,
            "name": self.name,
            "description": self.description,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "version_id": self.version_id,
            "service_type": self.service_type,
            "framework": self.framework,
            "replicas": self.replicas,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "endpoint": self.endpoint,
            "internal_endpoint": self.internal_endpoint,
            "port": self.port,
            "status": self.status,
            "health_status": self.health_status,
            "config": self.config,
            "env_vars": self.env_vars,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
            "auto_scale": self.auto_scale,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "target_cpu_utilization": self.target_cpu_utilization,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ServingMetrics(Base):
    """服务指标时序表"""
    __tablename__ = "serving_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(64), nullable=False, index=True)

    # 时间
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # 指标
    request_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    latency_p50_ms = Column(Float)
    latency_p90_ms = Column(Float)
    latency_p99_ms = Column(Float)
    tokens_per_second = Column(Float)

    # 资源使用
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    gpu_usage_percent = Column(Float)
    gpu_memory_usage_percent = Column(Float)

    # 副本数
    running_replicas = Column(Integer)
    desired_replicas = Column(Integer)

    def to_dict(self):
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p90_ms": self.latency_p90_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "tokens_per_second": self.tokens_per_second,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "gpu_usage_percent": self.gpu_usage_percent,
            "gpu_memory_usage_percent": self.gpu_memory_usage_percent,
            "running_replicas": self.running_replicas,
            "desired_replicas": self.desired_replicas,
        }


class ServingLog(Base):
    """服务日志表"""
    __tablename__ = "serving_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(64), nullable=False, index=True)

    # 日志信息
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(16), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text)
    source = Column(String(64))  # container name or pod name

    # 请求相关
    request_id = Column(String(64))
    latency_ms = Column(Float)
    status_code = Column(Integer)

    def to_dict(self):
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "request_id": self.request_id,
            "latency_ms": self.latency_ms,
            "status_code": self.status_code,
        }
