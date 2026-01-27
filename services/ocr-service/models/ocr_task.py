"""
OCR任务模型
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, Boolean, Enum as SQLEnum
import enum

from models.base import Base


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待处理
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


class DocumentType(str, enum.Enum):
    """文档类型枚举"""
    PDF = "pdf"
    IMAGE = "image"               # jpg, png, bmp等
    WORD = "word"                 # docx
    EXCEL = "excel"               # xlsx
    SCANNED_PDF = "scanned_pdf"   # 扫描件PDF
    UNKNOWN = "unknown"


class ExtractionType(str, enum.Enum):
    """提取类型枚举"""
    INVOICE = "invoice"               # 发票
    CONTRACT = "contract"             # 合同
    PURCHASE_ORDER = "purchase_order" # 采购订单
    DELIVERY_NOTE = "delivery_note"   # 送货单
    QUOTATION = "quotation"           # 报价单
    RECEIPT = "receipt"               # 收据
    REPORT = "report"                 # 报告
    TABLE = "table"                   # 表格
    GENERAL = "general"               # 通用文档


class OCRTask(Base):
    """OCR任务表"""
    __tablename__ = "ocr_tasks"

    id = Column(String(64), primary_key=True, comment="任务ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), nullable=False, index=True, comment="用户ID")

    # 文档信息
    document_name = Column(String(255), nullable=False, comment="文档名称")
    document_type = Column(String(20), nullable=False, comment="文档类型")
    document_path = Column(String(500), comment="文档存储路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    page_count = Column(Integer, default=1, comment="页数")

    # 提取配置
    extraction_type = Column(String(20), default=ExtractionType.GENERAL.value, comment="提取类型")
    template_id = Column(String(64), comment="使用的模板ID")
    extraction_config = Column(JSON, comment="提取配置")

    # 任务状态
    status = Column(String(20), default=TaskStatus.PENDING.value, index=True, comment="任务状态")
    progress = Column(Float, default=0.0, comment="处理进度 0-100")
    error_message = Column(Text, comment="错误信息")

    # 处理结果
    result_summary = Column(JSON, comment="结果摘要")
    raw_text = Column(Text, comment="提取的原始文本")
    structured_data = Column(JSON, comment="结构化数据")
    confidence_score = Column(Float, comment="置信度分数")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    started_at = Column(DateTime, comment="开始处理时间")
    completed_at = Column(DateTime, comment="完成时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 验证信息
    is_verified = Column(Boolean, default=False, comment="是否已人工验证")
    verified_by = Column(String(64), comment="验证人ID")
    verified_at = Column(DateTime, comment="验证时间")
    verification_notes = Column(Text, comment="验证备注")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "document_path": self.document_path,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "extraction_type": self.extraction_type,
            "template_id": self.template_id,
            "extraction_config": self.extraction_config,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "result_summary": self.result_summary,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_verified": self.is_verified,
            "verified_by": self.verified_by,
        }

    def __repr__(self):
        return f"<OCRTask(id={self.id}, document_name={self.document_name}, status={self.status})>"
