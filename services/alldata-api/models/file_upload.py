"""
文件上传模型
Sprint 4.1: FileUpload 模型
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, BIGINT, ForeignKey
from sqlalchemy.sql import func

from .base import Base


class FileUpload(Base):
    """文件上传记录表"""
    __tablename__ = "file_uploads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    upload_id = Column(String(64), unique=True, nullable=False, comment='上传ID')
    dataset_id = Column(String(64), comment='关联数据集ID')
    file_name = Column(String(512), nullable=False, comment='文件名')
    file_size = Column(BIGINT, default=0, comment='文件大小')
    content_type = Column(String(128), comment='内容类型')
    storage_path = Column(String(512), nullable=False, comment='MinIO 存储路径')
    status = Column(String(32), nullable=False, default='pending', comment='状态: pending, completed, failed')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "upload_id": self.upload_id,
            "dataset_id": self.dataset_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "storage_path": self.storage_path,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
