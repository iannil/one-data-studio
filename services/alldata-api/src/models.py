"""
Alldata API 数据模型
使用 SQLAlchemy ORM 定义数据库模型
"""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Dataset(Base):
    """数据集模型"""
    __tablename__ = 'datasets'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), unique=True, nullable=False, comment='数据集唯一标识')
    name = Column(String(255), nullable=False, comment='数据集名称')
    description = Column(Text, comment='数据集描述')
    storage_type = Column(String(32), nullable=False, default='s3', comment='存储类型')
    storage_path = Column(String(512), nullable=False, comment='存储路径')
    format = Column(String(32), nullable=False, default='csv', comment='文件格式')
    status = Column(String(32), nullable=False, default='active', comment='状态')
    row_count = Column(BigInteger, default=0, comment='记录数')
    size_bytes = Column(BigInteger, default=0, comment='文件大小')
    tags = Column(JSON, comment='标签列表')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关系
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        {'comment': '数据集表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'dataset_id': self.dataset_id,
            'name': self.name,
            'description': self.description,
            'storage_type': self.storage_type,
            'storage_path': self.storage_path,
            'format': self.format,
            'status': self.status,
            'row_count': self.row_count,
            'size_bytes': self.size_bytes,
            'tags': self.tags or [],
            'schema': {
                'columns': [
                    {
                        'name': col.column_name,
                        'type': col.column_type,
                        'nullable': col.is_nullable,
                        'description': col.description
                    }
                    for col in sorted(self.columns, key=lambda x: x.position)
                ]
            } if self.columns else {},
            'statistics': {
                'row_count': self.row_count,
                'size_bytes': self.size_bytes
            },
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class DatasetColumn(Base):
    """数据集列定义模型"""
    __tablename__ = 'dataset_columns'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), ForeignKey('datasets.dataset_id', ondelete='CASCADE'), nullable=False)
    column_name = Column(String(128), nullable=False, comment='列名')
    column_type = Column(String(64), nullable=False, comment='数据类型')
    is_nullable = Column(Boolean, default=True, comment='是否可空')
    description = Column(Text, comment='列描述')
    position = Column(Integer, nullable=False, comment='列位置')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    # 关系
    dataset = relationship("Dataset", back_populates="columns")

    __table_args__ = (
        Index('idx_dataset_id', 'dataset_id'),
    )


class DatasetVersion(Base):
    """数据集版本模型"""
    __tablename__ = 'dataset_versions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_id = Column(String(64), unique=True, nullable=False, comment='版本唯一标识')
    dataset_id = Column(String(64), ForeignKey('datasets.dataset_id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False, comment='版本号')
    storage_path = Column(String(512), nullable=False, comment='版本存储路径')
    description = Column(Text, comment='版本描述')
    row_count = Column(BigInteger, default=0, comment='记录数')
    size_bytes = Column(BigInteger, default=0, comment='文件大小')
    checksum = Column(String(64), comment='文件校验和')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    # 关系
    dataset = relationship("Dataset", back_populates="versions")

    __table_args__ = (
        Index('idx_dataset_id', 'dataset_id'),
        Index('idx_version_number', 'version_number'),
        {'comment': '数据集版本表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'version_id': self.version_id,
            'dataset_id': self.dataset_id,
            'version_number': self.version_number,
            'storage_path': self.storage_path,
            'description': self.description,
            'row_count': self.row_count,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class MetadataDatabase(Base):
    """元数据 - 数据库模型"""
    __tablename__ = 'metadata_databases'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    database_name = Column(String(128), unique=True, nullable=False, comment='数据库名')
    description = Column(Text, comment='描述')
    owner = Column(String(128), comment='所有者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关系
    tables = relationship("MetadataTable", back_populates="database", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            'name': self.database_name,
            'description': self.description,
            'owner': self.owner
        }


class MetadataTable(Base):
    """元数据 - 表模型"""
    __tablename__ = 'metadata_tables'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(128), nullable=False, comment='表名')
    database_name = Column(String(128), ForeignKey('metadata_databases.database_name', ondelete='CASCADE'), nullable=False)
    description = Column(Text, comment='表描述')
    row_count = Column(BigInteger, default=0, comment='行数')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关系
    database = relationship("MetadataDatabase", back_populates="tables")
    columns = relationship("MetadataColumn", back_populates="table", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_database_name', 'database_name'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'name': self.table_name,
            'description': self.description,
            'row_count': self.row_count,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class MetadataColumn(Base):
    """元数据 - 列模型"""
    __tablename__ = 'metadata_columns'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(128), nullable=False, comment='表名')
    database_name = Column(String(128), ForeignKey('metadata_databases.database_name', ondelete='CASCADE'), nullable=False)
    column_name = Column(String(128), nullable=False, comment='列名')
    column_type = Column(String(64), nullable=False, comment='数据类型')
    is_nullable = Column(Boolean, default=True, comment='是否可空')
    description = Column(Text, comment='列描述')
    position = Column(Integer, nullable=False, comment='列位置')

    # 关系
    database = relationship("MetadataDatabase")
    table = relationship("MetadataTable", back_populates="columns")

    __table_args__ = (
        Index('idx_table', 'table_name', 'database_name'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'name': self.column_name,
            'type': self.column_type,
            'nullable': self.is_nullable,
            'description': self.description
        }


class FileUpload(Base):
    """文件上传记录模型"""
    __tablename__ = 'file_uploads'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    upload_id = Column(String(64), unique=True, nullable=False, comment='上传ID')
    dataset_id = Column(String(64), ForeignKey('datasets.dataset_id', ondelete='SET NULL'), comment='关联数据集ID')
    file_name = Column(String(512), nullable=False, comment='文件名')
    file_size = Column(BigInteger, default=0, comment='文件大小')
    content_type = Column(String(128), comment='内容类型')
    storage_path = Column(String(512), nullable=False, comment='MinIO 存储路径')
    status = Column(String(32), nullable=False, default='pending', comment='状态')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    completed_at = Column(DateTime, comment='完成时间')

    __table_args__ = (
        Index('idx_dataset_id', 'dataset_id'),
        Index('idx_status', 'status'),
        {'comment': '文件上传记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'upload_id': self.upload_id,
            'dataset_id': self.dataset_id,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'storage_path': self.storage_path,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None
        }
