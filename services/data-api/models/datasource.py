"""
数据源相关模型
用于管理外部数据源连接（MySQL、PostgreSQL、Oracle 等）
"""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class DataSource(Base):
    """数据源表"""
    __tablename__ = "datasources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(String(64), unique=True, nullable=False, comment='数据源唯一标识')
    name = Column(String(255), nullable=False, comment='数据源名称')
    description = Column(Text, comment='数据源描述')
    type = Column(String(32), nullable=False, comment='数据源类型: mysql, postgresql, oracle, sqlserver, hive, mongodb, redis, elasticsearch')

    # 连接配置（JSON 格式存储，不包含密码）
    connection_config = Column(JSON, nullable=False, comment='连接配置（不包含敏感信息）')

    # 状态
    status = Column(String(32), nullable=False, default='disconnected', comment='状态: connected, disconnected, error')
    last_connected = Column(TIMESTAMP, comment='最后连接时间')
    last_error = Column(Text, comment='最后错误信息')

    # 元数据
    source_metadata = Column(JSON, comment='数据源元数据（版本、表数量等）')
    tags = Column(JSON, comment='标签列表')

    # 审计字段
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    created_by = Column(String(128), nullable=False, comment='创建者')

    def to_dict(self, include_connection=False):
        """转换为字典"""
        result = {
            "source_id": self.source_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
            "last_error": self.last_error,
            "metadata": self.source_metadata or {},
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
        if include_connection:
            result["connection"] = self.connection_config or {}
        return result
