"""
LLM 调优模型
P4.5: LLM 调优
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class LLMTuningTask(Base):
    """LLM 调优任务表"""
    __tablename__ = "llm_tuning_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 基础模型
    base_model = Column(String(255), nullable=False)
    base_model_path = Column(String(512))

    # 调优方法
    method = Column(String(32), default="lora")  # lora, qlora, full, prefix, adapter

    # 数据集
    dataset_id = Column(String(64))
    dataset_name = Column(String(255))

    # 训练配置
    epochs = Column(Integer, default=3)
    batch_size = Column(Integer, default=4)
    learning_rate = Column(Float, default=2e-5)
    max_seq_length = Column(Integer, default=2048)
    warmup_ratio = Column(Float, default=0.1)

    # LoRA 配置
    lora_r = Column(Integer, default=8)
    lora_alpha = Column(Integer, default=16)
    lora_dropout = Column(Float, default=0.05)
    target_modules = Column(JSON)

    # 量化配置
    quantization = Column(String(16))  # 4bit, 8bit, none
    compute_dtype = Column(String(16), default="float16")

    # 资源配置
    gpu_count = Column(Integer, default=1)
    gpu_type = Column(String(32))

    # 状态
    status = Column(String(32), default="pending")  # pending, running, completed, failed, stopped

    # 执行时间
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 进度
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    current_epoch = Column(Integer, default=0)

    # 训练指标
    train_loss = Column(Float)
    eval_loss = Column(Float)
    metrics_history = Column(JSON)

    # 输出
    output_model_path = Column(String(512))
    adapter_path = Column(String(512))

    # 错误信息
    error_message = Column(Text)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.task_id,
            "name": self.name,
            "description": self.description,
            "base_model": self.base_model,
            "base_model_path": self.base_model_path,
            "method": self.method,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "max_seq_length": self.max_seq_length,
            "warmup_ratio": self.warmup_ratio,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "quantization": self.quantization,
            "compute_dtype": self.compute_dtype,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_epoch": self.current_epoch,
            "train_loss": self.train_loss,
            "eval_loss": self.eval_loss,
            "metrics_history": self.metrics_history,
            "output_model_path": self.output_model_path,
            "adapter_path": self.adapter_path,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
