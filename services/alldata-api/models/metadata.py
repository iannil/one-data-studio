"""
元数据相关模型
Sprint 4.1: MetadataDatabase, MetadataTable, MetadataColumn 模型
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, TIMESTAMP, BIGINT, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class MetadataDatabase(Base):
    """元数据库表"""
    __tablename__ = "metadata_databases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    database_name = Column(String(128), unique=True, nullable=False, comment='数据库名')
    description = Column(Text, comment='描述')
    owner = Column(String(128), comment='所有者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    tables = relationship("MetadataTable", back_populates="database", cascade="all, delete-orphan")

    def to_dict(self, include_tables=False):
        """转换为字典"""
        result = {
            "name": self.database_name,
            "description": self.description or "",
            "owner": self.owner or "",
        }
        if include_tables:
            result["tables"] = [t.to_dict() for t in self.tables]
        return result


class MetadataTable(Base):
    """元数据表"""
    __tablename__ = "metadata_tables"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(128), nullable=False, comment='表名')
    database_name = Column(String(128), nullable=False, comment='所属数据库')
    description = Column(Text, comment='表描述')
    row_count = Column(BIGINT, default=0, comment='行数')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 外键和约束
    __table_args__ = (
        ForeignKeyConstraint(['database_name'], ['metadata_databases.database_name'], ondelete='CASCADE'),
        UniqueConstraint('table_name', 'database_name', name='uq_table_database'),
    )

    # 关系
    database = relationship("MetadataDatabase", back_populates="tables")
    columns = relationship("MetadataColumn", back_populates="table", cascade="all, delete-orphan")

    def to_dict(self, include_columns=False):
        """转换为字典"""
        result = {
            "name": self.table_name,
            "description": self.description or "",
            "row_count": self.row_count,
        }
        if include_columns:
            result["columns"] = [c.to_dict() for c in self.columns]
        return result


class MetadataColumn(Base):
    """元数据列定义表"""
    __tablename__ = "metadata_columns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(128), nullable=False, comment='表名')
    database_name = Column(String(128), nullable=False, comment='数据库名')
    column_name = Column(String(128), nullable=False, comment='列名')
    column_type = Column(String(64), nullable=False, comment='数据类型')
    is_nullable = Column(Boolean, default=True, comment='是否可空')
    description = Column(Text, comment='列描述')
    position = Column(Integer, nullable=False, comment='列位置')

    # 外键
    __table_args__ = (
        ForeignKeyConstraint(['database_name'], ['metadata_databases.database_name'], ondelete='CASCADE'),
        ForeignKeyConstraint(['table_name', 'database_name'], ['metadata_tables.table_name', 'metadata_tables.database_name'], ondelete='CASCADE'),
    )

    # 关系
    table = relationship("MetadataTable", back_populates="columns")

    def to_dict(self):
        """转换为字典"""
        return {
            "name": self.column_name,
            "type": self.column_type,
            "nullable": self.is_nullable,
            "description": self.description or "",
        }
