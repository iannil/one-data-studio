"""
SFT 微调模型
P3.3: SFT 微调
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class SFTTask(Base):
    """SFT 微调任务表"""
    __tablename__ = "sft_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 基础模型
    base_model = Column(String(255), nullable=False)  # llama-2-7b, qwen-7b, etc.
    base_model_path = Column(String(512))

    # 微调方法
    method = Column(String(32), default="lora")  # lora, qlora, full, prefix

    # 数据集
    dataset_id = Column(String(64))
    dataset_name = Column(String(255))
    dataset_path = Column(String(512))

    # 训练配置
    epochs = Column(Integer, default=3)
    batch_size = Column(Integer, default=4)
    learning_rate = Column(Float, default=2e-5)
    warmup_steps = Column(Integer, default=100)
    max_seq_length = Column(Integer, default=512)
    gradient_accumulation_steps = Column(Integer, default=4)

    # LoRA 配置
    lora_r = Column(Integer, default=8)
    lora_alpha = Column(Integer, default=16)
    lora_dropout = Column(Float, default=0.05)
    target_modules = Column(JSON)  # ["q_proj", "v_proj"]

    # 量化配置 (QLoRA)
    use_4bit = Column(Boolean, default=False)
    bnb_4bit_compute_dtype = Column(String(32), default="float16")
    bnb_4bit_quant_type = Column(String(32), default="nf4")

    # 资源配置
    gpu_count = Column(Integer, default=1)
    gpu_type = Column(String(32))
    memory_limit = Column(String(16))

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
    best_loss = Column(Float)
    metrics_history = Column(JSON)  # [{step, loss, lr, ...}]

    # 输出
    output_model_path = Column(String(512))
    checkpoint_path = Column(String(512))
    logs_path = Column(String(512))

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
            "id": self.task_id,
            "name": self.name,
            "description": self.description,
            "base_model": self.base_model,
            "base_model_path": self.base_model_path,
            "method": self.method,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "dataset_path": self.dataset_path,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "warmup_steps": self.warmup_steps,
            "max_seq_length": self.max_seq_length,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "use_4bit": self.use_4bit,
            "bnb_4bit_compute_dtype": self.bnb_4bit_compute_dtype,
            "bnb_4bit_quant_type": self.bnb_4bit_quant_type,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "memory_limit": self.memory_limit,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_epoch": self.current_epoch,
            "train_loss": self.train_loss,
            "eval_loss": self.eval_loss,
            "best_loss": self.best_loss,
            "metrics_history": self.metrics_history,
            "output_model_path": self.output_model_path,
            "checkpoint_path": self.checkpoint_path,
            "logs_path": self.logs_path,
            "error_message": self.error_message,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SFTDataset(Base):
    """SFT 微调数据集表"""
    __tablename__ = "sft_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 数据集类型
    dataset_type = Column(String(32), default="instruction")  # instruction, chat, completion

    # 存储
    storage_path = Column(String(512))
    file_format = Column(String(32), default="jsonl")  # jsonl, csv, parquet

    # 统计
    sample_count = Column(Integer, default=0)
    file_size = Column(Integer)  # bytes
    avg_input_length = Column(Integer)
    avg_output_length = Column(Integer)

    # 结构信息
    schema = Column(JSON)  # {instruction_field, input_field, output_field}

    # 预处理配置
    preprocessing_config = Column(JSON)

    # 标签
    tags = Column(JSON)

    # 状态
    is_public = Column(Boolean, default=False)
    status = Column(String(32), default="ready")  # uploading, processing, ready, error

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "dataset_type": self.dataset_type,
            "storage_path": self.storage_path,
            "file_format": self.file_format,
            "sample_count": self.sample_count,
            "file_size": self.file_size,
            "avg_input_length": self.avg_input_length,
            "avg_output_length": self.avg_output_length,
            "schema": self.schema,
            "preprocessing_config": self.preprocessing_config,
            "tags": self.tags,
            "is_public": self.is_public,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
