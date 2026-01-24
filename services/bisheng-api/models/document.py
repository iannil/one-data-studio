"""
文档索引模型
Phase 6: Sprint 6.3
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer
from sqlalchemy.sql import func

from .base import Base


class IndexedDocument(Base):
    """已索引文档表"""
    __tablename__ = "indexed_documents"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), unique=True, nullable=False, comment='文档唯一标识')
    collection_name = Column(String(128), nullable=False, comment='向量集合名称')
    file_name = Column(String(255), comment='文件名')
    title = Column(String(255), comment='文档标题')
    content = Column(Text, comment='文档内容')
    chunk_count = Column(Integer, default=0, comment='文档块数量')
    extra_metadata = Column(Text, comment='元数据 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            "id": self.doc_id,
            "collection_name": self.collection_name,
            "file_name": self.file_name,
            "title": self.title,
            "chunk_count": self.chunk_count,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
