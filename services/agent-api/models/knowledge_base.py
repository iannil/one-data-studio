"""
知识库管理模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, TIMESTAMP, Boolean
from sqlalchemy.sql import func

from .base import Base


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_bases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kb_id = Column(String(64), unique=True, nullable=False, comment='知识库唯一标识')
    name = Column(String(255), nullable=False, comment='知识库名称')
    description = Column(Text, comment='知识库描述')
    collection_name = Column(String(128), unique=True, nullable=False, comment='向量集合名称')
    embedding_model = Column(String(128), default='text-embedding-ada-002', comment='嵌入模型')
    chunk_size = Column(Integer, default=500, comment='分块大小')
    chunk_overlap = Column(Integer, default=50, comment='分块重叠')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    document_count = Column(Integer, default=0, comment='文档数量')
    vector_count = Column(Integer, default=0, comment='向量数量')
    status = Column(String(32), default='active', comment='状态: active, inactive, indexing')

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "kb_id": self.kb_id,
            "name": self.name,
            "description": self.description or "",
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "document_count": self.document_count or 0,
            "vector_count": self.vector_count or 0,
            "status": self.status
        }
