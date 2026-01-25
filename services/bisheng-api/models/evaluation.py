"""
模型评估模型
P3.2: 模型评估
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class Evaluation(Base):
    """模型评估任务表"""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 评估配置
    model_id = Column(String(64))  # 被评估的模型
    model_name = Column(String(255))
    dataset_id = Column(String(64))  # 评估数据集
    dataset_name = Column(String(255))

    # 评估类型
    eval_type = Column(String(32), default="auto")  # auto, manual, ab_test

    # 评估指标配置
    metrics = Column(JSON)  # [accuracy, f1, bleu, rouge, perplexity, etc.]

    # 状态
    status = Column(String(32), default="pending")  # pending, running, completed, failed

    # 执行时间
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 结果
    results = Column(JSON)  # {metric_name: value, ...}
    summary = Column(Text)  # 评估总结
    samples_evaluated = Column(Integer, default=0)
    samples_total = Column(Integer, default=0)

    # 错误信息
    error_message = Column(Text)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.evaluation_id,
            "name": self.name,
            "description": self.description,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "eval_type": self.eval_type,
            "metrics": self.metrics,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "results": self.results,
            "summary": self.summary,
            "samples_evaluated": self.samples_evaluated,
            "samples_total": self.samples_total,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EvaluationResult(Base):
    """评估结果明细表"""
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_id = Column(String(64), nullable=False, index=True)

    # 样本信息
    sample_index = Column(Integer)
    input_text = Column(Text)
    expected_output = Column(Text)
    actual_output = Column(Text)

    # 指标得分
    scores = Column(JSON)  # {metric_name: score, ...}

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "evaluation_id": self.evaluation_id,
            "sample_index": self.sample_index,
            "input_text": self.input_text,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "scores": self.scores,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EvaluationDataset(Base):
    """评估数据集表"""
    __tablename__ = "evaluation_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 数据集类型
    dataset_type = Column(String(32), default="qa")  # qa, classification, generation, translation

    # 存储
    storage_path = Column(String(512))
    file_format = Column(String(32), default="jsonl")  # jsonl, csv, parquet

    # 统计
    sample_count = Column(Integer, default=0)
    file_size = Column(Integer)  # bytes

    # 结构信息
    schema = Column(JSON)  # {input_field, output_field, ...}

    # 标签
    tags = Column(JSON)

    # 状态
    is_public = Column(Boolean, default=False)

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
            "schema": self.schema,
            "tags": self.tags,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
