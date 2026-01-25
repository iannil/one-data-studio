"""
资源监控模型
P2.4: 资源监控后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class ResourcePool(Base):
    """资源池表"""
    __tablename__ = "resource_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 资源类型
    pool_type = Column(String(32), default="gpu")  # gpu, cpu, memory

    # 总资源
    total_cpu = Column(Float, default=0)  # cores
    total_memory = Column(Float, default=0)  # GB
    total_gpu = Column(Integer, default=0)
    gpu_type = Column(String(32))

    # 已使用资源
    used_cpu = Column(Float, default=0)
    used_memory = Column(Float, default=0)
    used_gpu = Column(Integer, default=0)

    # 可用资源
    available_cpu = Column(Float, default=0)
    available_memory = Column(Float, default=0)
    available_gpu = Column(Integer, default=0)

    # 节点信息
    node_count = Column(Integer, default=0)
    nodes = Column(JSON)  # [{node_name, status, cpu, memory, gpu}]

    # 状态
    status = Column(String(32), default="active")  # active, inactive, maintenance

    # 配额
    max_jobs_per_user = Column(Integer, default=10)
    default_job_timeout = Column(Integer, default=86400)  # seconds

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.pool_id,
            "name": self.name,
            "description": self.description,
            "pool_type": self.pool_type,
            "total_cpu": self.total_cpu,
            "total_memory": self.total_memory,
            "total_gpu": self.total_gpu,
            "gpu_type": self.gpu_type,
            "used_cpu": self.used_cpu,
            "used_memory": self.used_memory,
            "used_gpu": self.used_gpu,
            "available_cpu": self.available_cpu,
            "available_memory": self.available_memory,
            "available_gpu": self.available_gpu,
            "node_count": self.node_count,
            "nodes": self.nodes,
            "status": self.status,
            "max_jobs_per_user": self.max_jobs_per_user,
            "default_job_timeout": self.default_job_timeout,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GPUDevice(Base):
    """GPU 设备表"""
    __tablename__ = "gpu_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)

    # 设备信息
    node_name = Column(String(255), nullable=False)
    gpu_index = Column(Integer, default=0)
    gpu_name = Column(String(128))  # NVIDIA A100, etc.
    gpu_uuid = Column(String(64))

    # 规格
    memory_total = Column(Integer)  # MB
    compute_capability = Column(String(16))

    # 使用情况
    memory_used = Column(Integer, default=0)  # MB
    memory_free = Column(Integer, default=0)
    gpu_utilization = Column(Float, default=0)  # percent
    memory_utilization = Column(Float, default=0)
    temperature = Column(Integer, default=0)  # Celsius
    power_usage = Column(Float, default=0)  # Watts

    # 状态
    status = Column(String(32), default="available")  # available, in_use, error, maintenance

    # 当前任务
    current_job_id = Column(String(64))
    current_user = Column(String(64))

    # 资源池
    pool_id = Column(String(64), index=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.device_id,
            "node_name": self.node_name,
            "gpu_index": self.gpu_index,
            "gpu_name": self.gpu_name,
            "gpu_uuid": self.gpu_uuid,
            "memory_total": self.memory_total,
            "compute_capability": self.compute_capability,
            "memory_used": self.memory_used,
            "memory_free": self.memory_free,
            "gpu_utilization": self.gpu_utilization,
            "memory_utilization": self.memory_utilization,
            "temperature": self.temperature,
            "power_usage": self.power_usage,
            "status": self.status,
            "current_job_id": self.current_job_id,
            "current_user": self.current_user,
            "pool_id": self.pool_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ResourceUsage(Base):
    """资源使用记录表（时序）"""
    __tablename__ = "resource_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 时间
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # 资源池
    pool_id = Column(String(64), index=True)

    # CPU
    cpu_total = Column(Float)
    cpu_used = Column(Float)
    cpu_percent = Column(Float)

    # 内存
    memory_total = Column(Float)  # GB
    memory_used = Column(Float)
    memory_percent = Column(Float)

    # GPU
    gpu_total = Column(Integer)
    gpu_used = Column(Integer)
    gpu_utilization_avg = Column(Float)
    gpu_memory_used = Column(Float)  # GB
    gpu_memory_total = Column(Float)

    # 任务
    running_jobs = Column(Integer)
    queued_jobs = Column(Integer)

    def to_dict(self):
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "pool_id": self.pool_id,
            "cpu_total": self.cpu_total,
            "cpu_used": self.cpu_used,
            "cpu_percent": self.cpu_percent,
            "memory_total": self.memory_total,
            "memory_used": self.memory_used,
            "memory_percent": self.memory_percent,
            "gpu_total": self.gpu_total,
            "gpu_used": self.gpu_used,
            "gpu_utilization_avg": self.gpu_utilization_avg,
            "gpu_memory_used": self.gpu_memory_used,
            "gpu_memory_total": self.gpu_memory_total,
            "running_jobs": self.running_jobs,
            "queued_jobs": self.queued_jobs,
        }
