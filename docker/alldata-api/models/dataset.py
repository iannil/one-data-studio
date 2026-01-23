"""
数据集相关模型
Sprint 4.1: Dataset, DatasetColumn, DatasetVersion 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, TIMESTAMP, BIGINT, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Dataset(Base):
    """数据集表"""
    __tablename__ = "datasets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), unique=True, nullable=False, comment='数据集唯一标识')
    name = Column(String(255), nullable=False, comment='数据集名称')
    description = Column(Text, comment='数据集描述')
    storage_type = Column(String(32), nullable=False, default='s3', comment='存储类型: s3, hdfs, local')
    storage_path = Column(String(512), nullable=False, comment='存储路径')
    format = Column(String(32), nullable=False, default='csv', comment='文件格式: csv, parquet, json, jsonl')
    status = Column(String(32), nullable=False, default='active', comment='状态: active, archived, deleted')
    row_count = Column(BIGINT, default=0, comment='记录数')
    size_bytes = Column(BIGINT, default=0, comment='文件大小(字节)')
    tags = Column(JSON, comment='标签列表')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")

    def to_dict(self, include_columns=False, include_versions=False):
        """转换为字典"""
        result = {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "storage_type": self.storage_type,
            "storage_path": self.storage_path,
            "format": self.format,
            "status": self.status,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_columns:
            result["schema"] = {
                "columns": [col.to_dict() for col in self.columns]
            }
        if include_versions:
            result["versions"] = [v.to_dict() for v in self.versions]
        return result


class DatasetColumn(Base):
    """数据集列定义表"""
    __tablename__ = "dataset_columns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), nullable=False, comment='所属数据集ID')
    column_name = Column(String(128), nullable=False, comment='列名')
    column_type = Column(String(64), nullable=False, comment='数据类型')
    is_nullable = Column(Boolean, default=True, comment='是否可空')
    description = Column(Text, comment='列描述')
    position = Column(Integer, nullable=False, comment='列位置')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 关系
    dataset = relationship("Dataset", back_populates="columns")

    def to_dict(self):
        """转换为字典"""
        return {
            "name": self.column_name,
            "type": self.column_type,
            "nullable": self.is_nullable,
            "description": self.description or "",
        }


class DatasetVersion(Base):
    """数据集版本表"""
    __tablename__ = "dataset_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_id = Column(String(64), unique=True, nullable=False, comment='版本唯一标识')
    dataset_id = Column(String(64), nullable=False, comment='所属数据集ID')
    version_number = Column(Integer, nullable=False, comment='版本号')
    storage_path = Column(String(512), nullable=False, comment='版本存储路径')
    description = Column(Text, comment='版本描述')
    row_count = Column(BIGINT, default=0, comment='记录数')
    size_bytes = Column(BIGINT, default=0, comment='文件大小(字节)')
    checksum = Column(String(64), comment='文件校验和')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 关系
    dataset = relationship("Dataset", back_populates="versions")

    def to_dict(self):
        """转换为字典"""
        return {
            "version_id": self.version_id,
            "dataset_id": self.dataset_id,
            "version_number": self.version_number,
            "storage_path": self.storage_path,
            "description": self.description,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
