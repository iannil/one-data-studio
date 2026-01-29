"""
data API 数据模型
使用 SQLAlchemy ORM 定义数据库模型
"""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, DateTime, TIMESTAMP, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
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
    dataset_id = Column(String(64), ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
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
    dataset_id = Column(String(64), ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
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
    table_id = Column(BigInteger, ForeignKey('metadata_tables.id', ondelete='CASCADE'), nullable=False, comment='表ID')
    table_name = Column(String(128), nullable=False, comment='表名')
    database_name = Column(String(128), nullable=False, comment='数据库名')
    column_name = Column(String(128), nullable=False, comment='列名')
    column_type = Column(String(64), nullable=False, comment='数据类型')
    is_nullable = Column(Boolean, default=True, comment='是否可空')
    description = Column(Text, comment='列描述')
    position = Column(Integer, nullable=False, comment='列位置')

    # 关系
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


class DataSource(Base):
    """数据源模型"""
    __tablename__ = 'datasources'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(String(64), unique=True, nullable=False, comment='数据源唯一标识')
    name = Column(String(255), nullable=False, comment='数据源名称')
    description = Column(Text, comment='数据源描述')
    type = Column(String(32), nullable=False, comment='数据源类型')
    connection_config = Column(JSON, nullable=False, comment='连接配置')
    status = Column(String(32), nullable=False, default='disconnected', comment='状态')
    last_connected = Column(DateTime, comment='最后连接时间')
    last_error = Column(Text, comment='最后错误信息')
    source_metadata = Column(JSON, comment='数据源元数据')
    tags = Column(JSON, comment='标签列表')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    created_by = Column(String(128), nullable=False, comment='创建者')

    __table_args__ = (
        Index('idx_source_id', 'source_id'),
        Index('idx_type', 'type'),
        Index('idx_status', 'status'),
        {'comment': '数据源表'}
    )

    def to_dict(self, include_connection=False):
        """转换为字典"""
        result = {
            'source_id': self.source_id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'status': self.status,
            'last_connected': self.last_connected.isoformat() + 'Z' if self.last_connected else None,
            'last_error': self.last_error,
            'metadata': self.source_metadata or {},
            'tags': self.tags or [],
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'created_by': self.created_by,
        }
        if include_connection:
            result['connection'] = self.connection_config or {}
        return result


# ==================== 特征存储模型 ====================

class FeatureGroup(Base):
    """特征组表"""
    __tablename__ = 'feature_groups'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(String(64), unique=True, nullable=False, index=True, comment='特征组唯一标识')
    name = Column(String(255), nullable=False, comment='特征组名称')
    description = Column(Text, comment='特征组描述')

    # 实体配置
    entity_name = Column(String(128), comment='实体名称')
    entity_key = Column(String(128), comment='实体键')

    # 数据源
    source_type = Column(String(32), comment='数据源类型')
    source_config = Column(JSON, comment='数据源配置')

    # 存储配置
    online_store = Column(Boolean, default=True, comment='在线存储')
    offline_store = Column(Boolean, default=True, comment='离线存储')
    ttl_days = Column(Integer, comment='TTL天数')

    # 统计
    feature_count = Column(Integer, default=0, comment='特征数量')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 状态
    status = Column(String(32), default='active', comment='状态')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_group_id', 'group_id'),
        Index('idx_status', 'status'),
        {'comment': '特征组表'}
    )

    def to_dict(self):
        """转换为字典 - 兼容前端 FeatureGroup 接口"""
        # 从 source_config 提取配置
        source_config = self.source_config or {}
        source_table = source_config.get('source_table', self.entity_name or '')

        # 映射 join_keys 和 entity_columns
        join_keys = source_config.get('join_keys', [])
        if not join_keys and self.entity_key:
            join_keys = [self.entity_key]

        entity_columns = source_config.get('entity_columns', [])
        if not entity_columns and self.entity_key:
            entity_columns = [self.entity_key]

        return {
            'group_id': self.group_id,  # 前端期望的字段名
            'name': self.name,
            'description': self.description,
            'source_table': source_table,  # 前端期望的字段名
            'join_keys': join_keys,  # 前端期望的字段名
            'entity_columns': entity_columns,  # 前端期望的字段名
            'entity_name': self.entity_name,
            'entity_key': self.entity_key,
            'source_type': self.source_type,
            'source_config': self.source_config,
            'online_store': self.online_store,
            'offline_store': self.offline_store,
            'ttl_days': self.ttl_days,
            'feature_count': self.feature_count,
            'features': [],  # 前端期望的字段名，默认为空数组
            'tags': self.tags or [],
            'status': self.status or 'active',
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


class Feature(Base):
    """特征表"""
    __tablename__ = 'features'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    feature_id = Column(String(64), unique=True, nullable=False, index=True, comment='特征唯一标识')
    name = Column(String(255), nullable=False, comment='特征名称')
    description = Column(Text, comment='特征描述')

    # 所属特征组
    group_id = Column(String(64), index=True, comment='特征组ID')
    group_name = Column(String(255), comment='特征组名称')

    # 特征类型
    data_type = Column(String(32), default='float', comment='数据类型')
    feature_type = Column(String(32), default='raw', comment='特征类型')

    # 计算逻辑
    expression = Column(Text, comment='计算表达式')
    dependencies = Column(JSON, comment='依赖特征')

    # 聚合配置
    aggregation_type = Column(String(32), comment='聚合类型')
    aggregation_window = Column(String(32), comment='聚合窗口')

    # 统计信息
    statistics = Column(JSON, comment='统计信息')
    last_computed_at = Column(DateTime, comment='最后计算时间')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 状态
    status = Column(String(32), default='active', comment='状态')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_feature_id', 'feature_id'),
        Index('idx_group_id', 'group_id'),
        Index('idx_status', 'status'),
        {'comment': '特征表'}
    )

    def to_dict(self):
        """转换为字典 - 兼容前端 Feature 接口"""
        # 映射 feature_type 为 value_type
        value_type_map = {
            'continuous': 'continuous',
            'categorical': 'categorical',
            'ordinal': 'ordinal',
        }
        value_type = value_type_map.get(self.feature_type, 'continuous')

        # 映射 data_type
        data_type_map = {
            'boolean': 'boolean',
            'int': 'integer',
            'integer': 'integer',
            'float': 'float',
            'str': 'string',
            'string': 'string',
            'array': 'array',
            'map': 'map',
        }
        data_type = data_type_map.get(str(self.data_type).lower(), 'float')

        return {
            'feature_id': self.feature_id,  # 前端期望的字段名
            'name': self.name,
            'description': self.description,
            'feature_group': self.group_name or '',  # 前端期望的字段名
            'group_id': self.group_id,
            'group_name': self.group_name,
            'data_type': data_type,
            'value_type': value_type,  # 前端期望的字段名
            'feature_type': self.feature_type,
            'source_table': self.group_name or '',  # 从 group_name 映射
            'source_column': self.name,  # 从 name 映射
            'transform_sql': self.expression,  # 前端期望的字段名
            'expression': self.expression,
            'dependencies': self.dependencies or [],
            'aggregation_type': self.aggregation_type,
            'aggregation_window': self.aggregation_window,
            'statistics': self.statistics,
            'last_computed_at': self.last_computed_at.isoformat() + 'Z' if self.last_computed_at else None,
            'tags': self.tags or [],
            'metadata': self.statistics or {},
            'status': self.status or 'active',
            'version': 1,  # 默认版本
            'created_by': self.created_by or 'system',
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== 数据标准模型 ====================

class DataStandard(Base):
    """数据标准表"""
    __tablename__ = 'data_standards'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    standard_id = Column(String(64), unique=True, nullable=False, index=True, comment='标准唯一标识')
    name = Column(String(255), nullable=False, comment='标准名称')
    description = Column(Text, comment='标准描述')

    # 分类
    category = Column(String(64), comment='分类')

    # 标准规则
    rule_type = Column(String(32), comment='规则类型')
    rule_config = Column(JSON, comment='规则配置')

    # 适用范围
    apply_to = Column(JSON, comment='适用范围')
    data_types = Column(JSON, comment='数据类型')

    # 示例
    examples = Column(JSON, comment='示例')

    # 状态
    status = Column(String(32), default='active', comment='状态')
    is_required = Column(Boolean, default=False, comment='是否必需')

    # 版本
    version = Column(String(32), default='1.0', comment='版本')

    # 统计
    apply_count = Column(Integer, default=0, comment='应用次数')
    violation_count = Column(Integer, default=0, comment='违规次数')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    created_by = Column(String(64), comment='创建者')

    __table_args__ = (
        Index('idx_standard_id', 'standard_id'),
        Index('idx_category', 'category'),
        Index('idx_status', 'status'),
        {'comment': '数据标准表'}
    )

    def to_dict(self):
        """转换为字典 - 兼容前端 DataElement 接口"""
        # 从 rule_config 中提取配置
        rule_config = self.rule_config or {}

        return {
            'id': self.standard_id,
            'element_id': self.standard_id,  # 前端期望的字段名
            'name': self.name,
            'description': self.description,
            'code': self.rule_type or 'default',  # 前端期望的字段名
            'category': self.category,
            'data_type': (self.data_types or ['string'])[0] if self.data_types else 'string',  # 前端期望的字段名
            'length': rule_config.get('length'),  # 前端期望的字段名
            'precision': rule_config.get('precision'),  # 前端期望的字段名
            'scale': rule_config.get('scale'),  # 前端期望的字段名
            'standard_value': rule_config.get('standard_value'),  # 前端期望的字段名
            'library_id': f"lib-{self.category}" if self.category else None,  # 前端期望的字段名
            'tags': rule_config.get('tags', []),  # 前端期望的字段名
            'rule_type': self.rule_type,
            'rule_config': self.rule_config,
            'apply_to': self.apply_to,
            'data_types': self.data_types,
            'examples': self.examples,
            'status': self.status,
            'is_required': self.is_required,
            'version': self.version,
            'apply_count': self.apply_count,
            'violation_count': self.violation_count,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'created_by': self.created_by or 'system',
        }


class StandardValidation(Base):
    """标准验证记录表"""
    __tablename__ = 'standard_validations'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    validation_id = Column(String(64), unique=True, nullable=False, index=True, comment='验证唯一标识')

    # 关联标准
    standard_id = Column(String(64), index=True, comment='标准ID')
    standard_name = Column(String(255), comment='标准名称')

    # 验证目标
    target_type = Column(String(32), comment='目标类型')
    target_id = Column(String(255), comment='目标ID')
    target_name = Column(String(255), comment='目标名称')

    # 验证数据
    input_value = Column(Text, comment='输入值')

    # 验证结果
    is_valid = Column(Boolean, comment='是否有效')
    error_message = Column(Text, comment='错误信息')
    details = Column(JSON, comment='详情')

    # 时间戳
    validated_at = Column(DateTime, default=func.now(), comment='验证时间')
    validated_by = Column(String(64), comment='验证者')

    __table_args__ = (
        Index('idx_validation_id', 'validation_id'),
        Index('idx_standard_id', 'standard_id'),
        {'comment': '标准验证记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.validation_id,
            'standard_id': self.standard_id,
            'standard_name': self.standard_name,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'input_value': self.input_value,
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'details': self.details,
            'validated_at': self.validated_at.isoformat() + 'Z' if self.validated_at else None,
            'validated_by': self.validated_by,
        }


# ==================== 数据资产模型 ====================

class DataAsset(Base):
    """数据资产表"""
    __tablename__ = 'data_assets'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(String(64), unique=True, nullable=False, index=True, comment='资产唯一标识')
    name = Column(String(255), nullable=False, comment='资产名称')
    description = Column(Text, comment='资产描述')

    # 资产类型
    asset_type = Column(String(32), comment='资产类型')

    # 分类
    category_id = Column(String(64), index=True, comment='分类ID')
    category_name = Column(String(128), comment='分类名称')

    # 来源
    source_type = Column(String(32), comment='来源类型')
    source_id = Column(String(64), comment='来源ID')
    source_name = Column(String(255), comment='来源名称')

    # 路径/位置
    path = Column(String(512), comment='路径')
    database_name = Column(String(128), comment='数据库名')
    schema_name = Column(String(128), comment='模式名')
    table_name = Column(String(255), comment='表名')

    # 元数据
    columns = Column(JSON, comment='字段列表')
    row_count = Column(Integer, comment='行数')
    size_bytes = Column(Integer, comment='大小字节')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 所有者
    owner = Column(String(64), comment='所有者')
    owner_name = Column(String(128), comment='所有者名称')

    # 数据等级
    data_level = Column(String(32), comment='数据等级')

    # 质量评分
    quality_score = Column(Integer, comment='质量评分')

    # 统计
    view_count = Column(Integer, default=0, comment='查看次数')
    collect_count = Column(Integer, default=0, comment='收藏次数')
    usage_count = Column(Integer, default=0, comment='使用次数')

    # 状态
    status = Column(String(32), default='active', comment='状态')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    last_sync_at = Column(DateTime, comment='最后同步时间')

    __table_args__ = (
        Index('idx_asset_id', 'asset_id'),
        Index('idx_category_id', 'category_id'),
        Index('idx_asset_type', 'asset_type'),
        Index('idx_status', 'status'),
        {'comment': '数据资产表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.asset_id,
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_name': self.source_name,
            'path': self.path,
            'database_name': self.database_name,
            'schema_name': self.schema_name,
            'table_name': self.table_name,
            'columns': self.columns,
            'row_count': self.row_count,
            'size_bytes': self.size_bytes,
            'tags': self.tags or [],
            'owner': self.owner,
            'owner_name': self.owner_name,
            'data_level': self.data_level,
            'quality_score': self.quality_score,
            'view_count': self.view_count,
            'collect_count': self.collect_count,
            'usage_count': self.usage_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'last_sync_at': self.last_sync_at.isoformat() + 'Z' if self.last_sync_at else None,
        }


class AssetCategory(Base):
    """资产分类表"""
    __tablename__ = 'asset_categories'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True, comment='分类唯一标识')
    name = Column(String(128), nullable=False, comment='分类名称')
    description = Column(Text, comment='分类描述')

    # 父分类
    parent_id = Column(String(64), comment='父分类ID')

    # 图标
    icon = Column(String(64), comment='图标')

    # 排序
    sort_order = Column(Integer, default=0, comment='排序')

    # 统计
    asset_count = Column(Integer, default=0, comment='资产数量')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    __table_args__ = (
        Index('idx_category_id', 'category_id'),
        Index('idx_parent_id', 'parent_id'),
        {'comment': '资产分类表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.category_id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'asset_count': self.asset_count,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class AssetCollection(Base):
    """资产收藏表"""
    __tablename__ = 'asset_collections'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 收藏信息
    asset_id = Column(String(64), index=True, comment='资产ID')
    user_id = Column(String(64), index=True, comment='用户ID')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    __table_args__ = (
        Index('idx_asset_collection_asset', 'asset_id'),
        Index('idx_asset_collection_user', 'user_id'),
        {'comment': '资产收藏表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'asset_id': self.asset_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


# ==================== 数据服务模型 ====================

class DataService(Base):
    """数据服务表"""
    __tablename__ = 'data_services'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_id = Column(String(64), unique=True, nullable=False, index=True, comment='服务唯一标识')
    name = Column(String(255), nullable=False, comment='服务名称')
    description = Column(Text, comment='服务描述')

    # 服务类型
    service_type = Column(String(32), comment='服务类型')

    # 数据源
    source_type = Column(String(32), comment='数据源类型')
    source_id = Column(String(64), comment='数据源ID')
    sql_query = Column(Text, comment='SQL查询')

    # 接口配置
    path = Column(String(255), comment='API路径')
    method = Column(String(16), default='GET', comment='HTTP方法')
    parameters = Column(JSON, comment='请求参数')
    response_format = Column(String(32), default='json', comment='响应格式')

    # 认证配置
    auth_type = Column(String(32), default='none', comment='认证类型')
    auth_config = Column(JSON, comment='认证配置')

    # 限流配置
    rate_limit_enabled = Column(Boolean, default=True, comment='启用限流')
    rate_limit_per_minute = Column(Integer, default=60, comment='每分钟限制')
    rate_limit_per_day = Column(Integer, default=10000, comment='每天限制')

    # 缓存配置
    cache_enabled = Column(Boolean, default=True, comment='启用缓存')
    cache_ttl = Column(Integer, default=300, comment='缓存TTL')

    # 状态
    status = Column(String(32), default='stopped', comment='状态')

    # 版本
    version = Column(String(32), default='v1', comment='版本')

    # 统计
    total_calls = Column(Integer, default=0, comment='总调用次数')
    success_calls = Column(Integer, default=0, comment='成功调用次数')
    error_calls = Column(Integer, default=0, comment='错误调用次数')
    avg_response_time_ms = Column(Integer, comment='平均响应时间')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    started_at = Column(DateTime, comment='启动时间')
    stopped_at = Column(DateTime, comment='停止时间')
    created_by = Column(String(64), comment='创建者')

    __table_args__ = (
        Index('idx_service_id', 'service_id'),
        Index('idx_status', 'status'),
        Index('idx_service_type', 'service_type'),
        {'comment': '数据服务表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.service_id,
            'name': self.name,
            'description': self.description,
            'service_type': self.service_type,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'sql_query': self.sql_query,
            'path': self.path,
            'method': self.method,
            'parameters': self.parameters,
            'response_format': self.response_format,
            'auth_type': self.auth_type,
            'auth_config': self.auth_config,
            'rate_limit_enabled': self.rate_limit_enabled,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'rate_limit_per_day': self.rate_limit_per_day,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl,
            'status': self.status,
            'version': self.version,
            'total_calls': self.total_calls,
            'success_calls': self.success_calls,
            'error_calls': self.error_calls,
            'avg_response_time_ms': self.avg_response_time_ms,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() + 'Z' if self.stopped_at else None,
            'created_by': self.created_by,
        }


class ServiceCallLog(Base):
    """服务调用日志表"""
    __tablename__ = 'service_call_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True, comment='日志唯一标识')

    # 关联服务
    service_id = Column(String(64), index=True, comment='服务ID')

    # 请求信息
    request_path = Column(String(512), comment='请求路径')
    request_method = Column(String(16), comment='请求方法')
    request_params = Column(JSON, comment='请求参数')
    request_headers = Column(JSON, comment='请求头')
    client_ip = Column(String(64), comment='客户端IP')
    user_agent = Column(String(512), comment='用户代理')

    # 响应信息
    response_status = Column(Integer, comment='响应状态')
    response_size_bytes = Column(Integer, comment='响应大小')
    response_time_ms = Column(Integer, comment='响应时间')

    # 错误信息
    error_code = Column(String(32), comment='错误代码')
    error_message = Column(Text, comment='错误信息')

    # 时间戳
    called_at = Column(DateTime, default=func.now(), index=True, comment='调用时间')

    __table_args__ = (
        Index('idx_log_id', 'log_id'),
        Index('idx_service_call_service', 'service_id'),
        Index('idx_called_at', 'called_at'),
        {'comment': '服务调用日志表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.log_id,
            'service_id': self.service_id,
            'request_path': self.request_path,
            'request_method': self.request_method,
            'request_params': self.request_params,
            'client_ip': self.client_ip,
            'response_status': self.response_status,
            'response_size_bytes': self.response_size_bytes,
            'response_time_ms': self.response_time_ms,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'called_at': self.called_at.isoformat() + 'Z' if self.called_at else None,
        }


# ==================== BI仪表板模型 ====================

class BIDashboard(Base):
    """BI仪表板表"""
    __tablename__ = 'bi_dashboards'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dashboard_id = Column(String(64), unique=True, nullable=False, index=True, comment='仪表板唯一标识')
    name = Column(String(255), nullable=False, comment='仪表板名称')
    description = Column(Text, comment='仪表板描述')

    # 布局配置
    layout = Column(JSON, comment='布局配置')
    theme = Column(String(32), default='light', comment='主题')

    # 全局筛选器
    filters = Column(JSON, comment='筛选器')

    # 刷新设置
    auto_refresh = Column(Boolean, default=False, comment='自动刷新')
    refresh_interval = Column(Integer, default=300, comment='刷新间隔')

    # 分享设置
    is_public = Column(Boolean, default=False, comment='是否公开')
    share_token = Column(String(128), comment='分享令牌')

    # 收藏统计
    favorite_count = Column(Integer, default=0, comment='收藏次数')
    view_count = Column(Integer, default=0, comment='查看次数')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    created_by = Column(String(64), comment='创建者')

    __table_args__ = (
        Index('idx_dashboard_id', 'dashboard_id'),
        Index('idx_is_public', 'is_public'),
        {'comment': 'BI仪表板表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.dashboard_id,
            'name': self.name,
            'description': self.description,
            'layout': self.layout,
            'theme': self.theme,
            'filters': self.filters,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'is_public': self.is_public,
            'favorite_count': self.favorite_count,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'created_by': self.created_by,
        }


class BIChart(Base):
    """BI图表表"""
    __tablename__ = 'bi_charts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chart_id = Column(String(64), unique=True, nullable=False, index=True, comment='图表唯一标识')
    name = Column(String(255), nullable=False, comment='图表名称')
    description = Column(Text, comment='图表描述')

    # 所属仪表板
    dashboard_id = Column(String(64), index=True, comment='仪表板ID')

    # 图表类型
    chart_type = Column(String(32), comment='图表类型')

    # 数据源配置
    datasource_type = Column(String(32), comment='数据源类型')
    datasource_id = Column(String(64), comment='数据源ID')
    sql_query = Column(Text, comment='SQL查询')

    # 图表配置
    config = Column(JSON, comment='图表配置')
    dimensions = Column(JSON, comment='维度字段')
    metrics = Column(JSON, comment='指标字段')
    filters = Column(JSON, comment='筛选器')

    # 缓存设置
    cache_enabled = Column(Boolean, default=True, comment='启用缓存')
    cache_ttl = Column(Integer, default=300, comment='缓存TTL')

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    created_by = Column(String(64), comment='创建者')

    __table_args__ = (
        Index('idx_chart_id', 'chart_id'),
        Index('idx_dashboard_id', 'dashboard_id'),
        {'comment': 'BI图表表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.chart_id,
            'name': self.name,
            'description': self.description,
            'dashboard_id': self.dashboard_id,
            'chart_type': self.chart_type,
            'datasource_type': self.datasource_type,
            'datasource_id': self.datasource_id,
            'sql_query': self.sql_query,
            'config': self.config,
            'dimensions': self.dimensions,
            'metrics': self.metrics,
            'filters': self.filters,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'created_by': self.created_by,
        }


# ==================== 指标管理模型 ====================

class MetricDefinition(Base):
    """指标定义表"""
    __tablename__ = 'metric_definitions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_id = Column(String(64), unique=True, nullable=False, index=True, comment='指标唯一标识')
    name = Column(String(255), nullable=False, comment='指标名称')
    display_name = Column(String(255), comment='显示名称')
    description = Column(Text, comment='指标描述')

    # 分类
    category = Column(String(64), comment='分类')
    subcategory = Column(String(64), comment='子分类')
    tags = Column(JSON, comment='标签列表')

    # 指标类型
    metric_type = Column(String(32), default='count', comment='指标类型')

    # 计算定义
    source_database = Column(String(255), comment='源数据库')
    source_table = Column(String(255), comment='源表')
    source_column = Column(String(255), comment='源列')
    calculation_sql = Column(Text, comment='计算SQL')
    aggregation_type = Column(String(32), comment='聚合类型')
    time_column = Column(String(255), comment='时间列')

    # 单位和格式
    unit = Column(String(32), comment='单位')
    decimal_places = Column(Integer, default=2, comment='小数位数')
    format_pattern = Column(String(64), comment='格式模式')

    # 阈值和告警
    warning_threshold = Column(Integer, comment='警告阈值')
    critical_threshold = Column(Integer, comment='严重阈值')
    threshold_direction = Column(String(16), default='above', comment='阈值方向')

    # 负责人
    owner = Column(String(64), comment='负责人')
    owner_team = Column(String(64), comment='负责团队')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_certified = Column(Boolean, default=False, comment='是否认证')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    updated_by = Column(String(64), comment='更新者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_metric_id', 'metric_id'),
        Index('idx_category', 'category'),
        Index('idx_is_active', 'is_active'),
        {'comment': '指标定义表'}
    )

    def to_dict(self):
        """转换为字典 - 兼容前端 Metric 接口"""
        # 将 is_active 映射为 status
        if self.is_active is None:
            status = 'draft'
        elif self.is_active:
            status = 'active'
        else:
            status = 'deprecated'

        # 将 metric_type 映射为 value_type
        value_type = self.metric_type or 'absolute'

        # 将 aggregation_type 映射为 aggregation
        aggregation = self.aggregation_type or 'count'

        # 生成 code: 使用 name 的 snake_case 格式或 metric_id
        code = self.name.lower().replace(' ', '_').replace('-', '_') if self.name else (self.metric_id or '')

        return {
            'metric_id': self.metric_id,
            'name': self.name,
            'code': code,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category or 'business',
            'subcategory': self.subcategory,
            'tags': self.tags or [],
            'value_type': value_type,  # 前端期望的字段名
            'metric_type': self.metric_type,  # 保留原始字段
            'source_database': self.source_database,
            'source_table': self.source_table or '',
            'source_column': self.source_column,
            'formula': self.calculation_sql,  # 前端期望的字段名
            'calculation_sql': self.calculation_sql,  # 保留原始字段
            'aggregation': aggregation,  # 前端期望的字段名
            'aggregation_type': self.aggregation_type,  # 保留原始字段
            'time_column': self.time_column,
            'unit': self.unit,
            'decimal_places': self.decimal_places,
            'format_pattern': self.format_pattern,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'threshold_direction': self.threshold_direction,
            'owner': self.owner,
            'department': self.owner_team,  # 前端期望的字段名
            'owner_team': self.owner_team,  # 保留原始字段
            'status': status,  # 前端期望的字段名
            'is_active': self.is_active,
            'is_certified': self.is_certified,
            'created_by': self.created_by or 'system',
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


class MetricValue(Base):
    """指标数据值表"""
    __tablename__ = 'metric_values'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_id = Column(String(64), nullable=False, index=True, comment='指标ID')

    # 时间维度
    time_key = Column(DateTime, nullable=False, index=True, comment='时间键')
    granularity = Column(String(16), default='daily', comment='粒度')

    # 值
    value = Column(Integer, comment='值')
    previous_value = Column(Integer, comment='上期值')
    change_value = Column(Integer, comment='变化值')
    change_percent = Column(Integer, comment='变化百分比')

    # 维度
    dimension_1 = Column(String(255), comment='维度1')
    dimension_2 = Column(String(255), comment='维度2')
    dimension_3 = Column(String(255), comment='维度3')
    dimensions = Column(JSON, comment='额外维度')

    # 状态
    status = Column(String(16), default='normal', comment='状态')

    created_at = Column(DateTime, default=func.now(), comment='创建时间')

    __table_args__ = (
        Index('idx_metric_value_metric', 'metric_id'),
        Index('idx_time_key', 'time_key'),
        {'comment': '指标数据值表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'metric_id': self.metric_id,
            'time_key': self.time_key.isoformat() + 'Z' if self.time_key else None,
            'granularity': self.granularity,
            'value': self.value,
            'previous_value': self.previous_value,
            'change_value': self.change_value,
            'change_percent': self.change_percent,
            'dimension_1': self.dimension_1,
            'dimension_2': self.dimension_2,
            'dimension_3': self.dimension_3,
            'dimensions': self.dimensions,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class MetricCategory(Base):
    """指标分类表"""
    __tablename__ = 'metric_categories'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True, comment='分类唯一标识')
    name = Column(String(255), nullable=False, comment='分类名称')
    display_name = Column(String(255), comment='显示名称')
    description = Column(Text, comment='分类描述')
    parent_id = Column(String(64), comment='父分类ID')
    level = Column(Integer, default=1, comment='层级')
    sort_order = Column(Integer, default=0, comment='排序')
    icon = Column(String(64), comment='图标')
    is_active = Column(Boolean, default=True, comment='是否激活')

    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_metric_category_id', 'category_id'),
        Index('idx_parent_id', 'parent_id'),
        {'comment': '指标分类表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.category_id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'parent_id': self.parent_id,
            'level': self.level,
            'sort_order': self.sort_order,
            'icon': self.icon,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== ETL任务模型 ====================

class ETLTask(Base):
    """ETL任务表"""
    __tablename__ = 'etl_tasks'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment='任务唯一标识')
    name = Column(String(255), nullable=False, comment='任务名称')
    description = Column(Text, comment='任务描述')

    # 任务类型
    task_type = Column(String(32), default='batch', comment='任务类型: batch/streaming')

    # 数据源配置
    source_type = Column(String(32), comment='源类型')
    source_id = Column(String(64), comment='源ID')
    source_config = Column(JSON, comment='源配置')

    # 目标配置
    target_type = Column(String(32), comment='目标类型')
    target_id = Column(String(64), comment='目标ID')
    target_config = Column(JSON, comment='目标配置')

    # 转换规则
    transform_rules = Column(JSON, comment='转换规则')
    sql_script = Column(Text, comment='SQL脚本')

    # 调度配置
    schedule_type = Column(String(32), default='manual', comment='调度类型')
    schedule_cron = Column(String(128), comment='Cron表达式')
    schedule_interval = Column(Integer, comment='间隔(秒)')

    # 运行状态
    status = Column(String(32), default='draft', comment='状态: draft/running/stopped/failed')

    # 统计信息
    last_run_at = Column(DateTime, comment='最后运行时间')
    last_run_status = Column(String(32), comment='最后运行状态')
    total_runs = Column(Integer, default=0, comment='总运行次数')
    success_runs = Column(Integer, default=0, comment='成功次数')
    failed_runs = Column(Integer, default=0, comment='失败次数')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_etl_task_id', 'task_id'),
        Index('idx_etl_status', 'status'),
        Index('idx_etl_task_type', 'task_type'),
        {'comment': 'ETL任务表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'task_type': self.task_type,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_config': self.source_config,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_config': self.target_config,
            'transform_rules': self.transform_rules,
            'sql_script': self.sql_script,
            'schedule_type': self.schedule_type,
            'schedule_cron': self.schedule_cron,
            'schedule_interval': self.schedule_interval,
            'status': self.status,
            'last_run_at': self.last_run_at.isoformat() + 'Z' if self.last_run_at else None,
            'last_run_status': self.last_run_status,
            'total_runs': self.total_runs,
            'success_runs': self.success_runs,
            'failed_runs': self.failed_runs,
            'tags': self.tags or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== 数据质量模型 ====================

class QualityRule(Base):
    """数据质量规则表"""
    __tablename__ = 'quality_rules'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True, comment='规则唯一标识')
    name = Column(String(255), nullable=False, comment='规则名称')
    description = Column(Text, comment='规则描述')

    # 关联数据源
    source_id = Column(String(64), index=True, comment='数据源ID')
    table_name = Column(String(255), comment='表名')

    # 规则配置
    rule_type = Column(String(32), nullable=False, comment='规则类型')
    rule_config = Column(JSON, comment='规则配置')

    # 阈值配置
    threshold_warning = Column(Integer, comment='警告阈值')
    threshold_critical = Column(Integer, comment='严重阈值')

    # 状态
    severity = Column(String(32), default='medium', comment='严重程度')
    status = Column(String(32), default='active', comment='状态')

    # 统计
    check_count = Column(Integer, default=0, comment='检查次数')
    violation_count = Column(Integer, default=0, comment='违规次数')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_quality_rule_id', 'rule_id'),
        Index('idx_quality_rule_status', 'status'),
        Index('idx_quality_rule_source', 'source_id'),
        {'comment': '数据质量规则表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'source_id': self.source_id,
            'table_name': self.table_name,
            'rule_type': self.rule_type,
            'rule_config': self.rule_config,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical,
            'severity': self.severity,
            'status': self.status,
            'check_count': self.check_count,
            'violation_count': self.violation_count,
            'tags': self.tags or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


class QualityAlert(Base):
    """数据质量告警表"""
    __tablename__ = 'quality_alerts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, nullable=False, index=True, comment='告警唯一标识')

    # 关联规则
    rule_id = Column(String(64), index=True, comment='规则ID')
    rule_name = Column(String(255), comment='规则名称')

    # 告警信息
    alert_type = Column(String(32), default='warning', comment='告警类型')
    severity = Column(String(32), default='medium', comment='严重程度')
    title = Column(String(255), comment='告警标题')
    message = Column(Text, comment='告警消息')

    # 告警配置
    alert_config = Column(JSON, comment='告警配置')
    notification_channels = Column(JSON, comment='通知渠道')

    # 状态
    status = Column(String(32), default='active', comment='状态')
    is_enabled = Column(Boolean, default=True, comment='是否启用')

    # 统计
    triggered_count = Column(Integer, default=0, comment='触发次数')
    last_triggered_at = Column(DateTime, comment='最后触发时间')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_quality_alert_id', 'alert_id'),
        Index('idx_quality_alert_rule', 'rule_id'),
        Index('idx_quality_alert_status', 'status'),
        {'comment': '数据质量告警表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'alert_config': self.alert_config,
            'notification_channels': self.notification_channels or [],
            'status': self.status,
            'is_enabled': self.is_enabled,
            'triggered_count': self.triggered_count,
            'last_triggered_at': self.last_triggered_at.isoformat() + 'Z' if self.last_triggered_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== 离线计算模型 ====================

class OfflineTask(Base):
    """离线计算任务表"""
    __tablename__ = 'offline_tasks'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(String(64), unique=True, nullable=False, index=True, comment='工作流唯一标识')
    name = Column(String(255), nullable=False, comment='工作流名称')
    description = Column(Text, comment='工作流描述')

    # 工作流配置
    workflow_type = Column(String(32), default='batch', comment='工作流类型')
    workflow_config = Column(JSON, comment='工作流配置')
    dag_definition = Column(JSON, comment='DAG定义')

    # 资源配置
    cluster_id = Column(String(64), comment='集群ID')
    executor_type = Column(String(32), default='spark', comment='执行器类型')
    executor_cores = Column(Integer, default=1, comment='执行器核心数')
    executor_memory = Column(String(32), default='1g', comment='执行器内存')
    num_executors = Column(Integer, default=1, comment='执行器数量')

    # 调度配置
    schedule_type = Column(String(32), default='manual', comment='调度类型')
    schedule_cron = Column(String(128), comment='Cron表达式')

    # 运行状态
    status = Column(String(32), default='draft', comment='状态')

    # 统计
    last_run_at = Column(DateTime, comment='最后运行时间')
    last_run_status = Column(String(32), comment='最后运行状态')
    total_runs = Column(Integer, default=0, comment='总运行次数')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_offline_workflow_id', 'workflow_id'),
        Index('idx_offline_status', 'status'),
        Index('idx_offline_type', 'workflow_type'),
        {'comment': '离线计算任务表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'workflow_type': self.workflow_type,
            'workflow_config': self.workflow_config,
            'dag_definition': self.dag_definition,
            'cluster_id': self.cluster_id,
            'executor_type': self.executor_type,
            'executor_cores': self.executor_cores,
            'executor_memory': self.executor_memory,
            'num_executors': self.num_executors,
            'schedule_type': self.schedule_type,
            'schedule_cron': self.schedule_cron,
            'status': self.status,
            'last_run_at': self.last_run_at.isoformat() + 'Z' if self.last_run_at else None,
            'last_run_status': self.last_run_status,
            'total_runs': self.total_runs,
            'tags': self.tags or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== 流计算模型 ====================

class FlinkJob(Base):
    """Flink流计算任务表"""
    __tablename__ = 'flink_jobs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True, comment='任务唯一标识')
    name = Column(String(255), nullable=False, comment='任务名称')
    description = Column(Text, comment='任务描述')

    # 任务配置
    job_type = Column(String(32), default='sql', comment='任务类型: sql/jar/python')
    job_config = Column(JSON, comment='任务配置')

    # Flink配置
    flink_version = Column(String(32), default='1.17', comment='Flink版本')
    parallelism = Column(Integer, default=1, comment='并行度')
    checkpoint_interval = Column(Integer, comment='检查点间隔(毫秒)')
    savepoint_path = Column(String(512), comment='保存点路径')

    # 资源配置
    cluster_id = Column(String(64), comment='集群ID')
    task_slots = Column(Integer, default=1, comment='Task Slot数量')
    task_manager_memory = Column(String(32), default='1g', comment='TaskManager内存')
    job_manager_memory = Column(String(32), default='1g', comment='JobManager内存')

    # 源和汇配置
    sources = Column(JSON, comment='数据源配置')
    sinks = Column(JSON, comment='数据汇配置')
    transformation = Column(Text, comment='转换逻辑(SQL/代码)')

    # 运行状态
    status = Column(String(32), default='created', comment='状态: created/running/stopped/failed')

    # Flink集群状态
    flink_job_id = Column(String(128), comment='Flink集群中的JobID')
    flink_web_url = Column(String(512), comment='Flink Web UI URL')

    # 统计
    started_at = Column(DateTime, comment='启动时间')
    stopped_at = Column(DateTime, comment='停止时间')
    last_checkpoint_at = Column(DateTime, comment='最后检查点时间')
    total_duration_ms = Column(BigInteger, comment='总运行时长(毫秒)')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 时间戳
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_flink_job_id', 'job_id'),
        Index('idx_flink_status', 'status'),
        Index('idx_flink_type', 'job_type'),
        {'comment': 'Flink流计算任务表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'job_id': self.job_id,
            'name': self.name,
            'description': self.description,
            'job_type': self.job_type,
            'job_config': self.job_config,
            'flink_version': self.flink_version,
            'parallelism': self.parallelism,
            'checkpoint_interval': self.checkpoint_interval,
            'savepoint_path': self.savepoint_path,
            'cluster_id': self.cluster_id,
            'task_slots': self.task_slots,
            'task_manager_memory': self.task_manager_memory,
            'job_manager_memory': self.job_manager_memory,
            'sources': self.sources,
            'sinks': self.sinks,
            'transformation': self.transformation,
            'status': self.status,
            'flink_job_id': self.flink_job_id,
            'flink_web_url': self.flink_web_url,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() + 'Z' if self.stopped_at else None,
            'last_checkpoint_at': self.last_checkpoint_at.isoformat() + 'Z' if self.last_checkpoint_at else None,
            'total_duration_ms': self.total_duration_ms,
            'tags': self.tags or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


# ==================== 敏感数据扫描模型 ====================

class SensitivityScanTask(Base):
    """敏感数据扫描任务表"""
    __tablename__ = "sensitivity_scan_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment='扫描任务ID')

    # 扫描目标
    target_type = Column(String(32), nullable=False, comment='扫描目标类型: database, table, column, dataset')
    target_id = Column(String(128), comment='目标ID（数据源/表/数据集ID）')
    target_name = Column(String(255), comment='目标名称（用于显示）')

    # 扫描配置
    scan_mode = Column(String(32), default='full', comment='扫描模式: full(全量), incremental(增量), sampling(采样)')
    sample_rate = Column(Integer, default=100, comment='采样率（百分比）')
    confidence_threshold = Column(Integer, default=70, comment='置信度阈值 0-100')

    # 扫描范围
    databases = Column(Text, comment='扫描的数据库列表 (JSON)')
    tables = Column(Text, comment='扫描的表列表 (JSON)')
    exclude_patterns = Column(Text, comment='排除的表/列模式 (JSON)')

    # 状态
    status = Column(String(32), default='pending', comment='状态: pending, running, completed, failed, cancelled')
    progress = Column(Integer, default=0, comment='进度百分比 0-100')

    # 扫描结果统计
    total_columns = Column(Integer, default=0, comment='总列数')
    scanned_columns = Column(Integer, default=0, comment='已扫描列数')
    sensitive_found = Column(Integer, default=0, comment='发现敏感字段数')

    # 详细结果（按类型）
    pii_count = Column(Integer, default=0, comment='PII类型数量')
    financial_count = Column(Integer, default=0, comment='财务类型数量')
    health_count = Column(Integer, default=0, comment='健康类型数量')
    credential_count = Column(Integer, default=0, comment='凭证类型数量')

    # 时间信息
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')
    estimated_duration = Column(Integer, comment='预估耗时（秒）')

    # 执行信息
    created_by = Column(String(128), comment='创建者')
    error_message = Column(Text, comment='错误信息')

    __table_args__ = (
        Index('idx_sensitivity_task_id', 'task_id'),
        Index('idx_sensitivity_task_status', 'status'),
        {'comment': '敏感数据扫描任务表'}
    )

    def get_databases(self) -> list:
        """获取数据库列表"""
        if not self.databases:
            return []
        import json
        try:
            return json.loads(self.databases)
        except json.JSONDecodeError:
            return []

    def set_databases(self, databases: list):
        """设置数据库列表"""
        import json
        self.databases = json.dumps(databases, ensure_ascii=False)

    def get_tables(self) -> list:
        """获取表列表"""
        if not self.tables:
            return []
        import json
        try:
            return json.loads(self.tables)
        except json.JSONDecodeError:
            return []

    def set_tables(self, tables: list):
        """设置表列表"""
        import json
        self.tables = json.dumps(tables, ensure_ascii=False)

    def get_exclude_patterns(self) -> list:
        """获取排除模式"""
        if not self.exclude_patterns:
            return []
        import json
        try:
            return json.loads(self.exclude_patterns)
        except json.JSONDecodeError:
            return []

    def set_exclude_patterns(self, patterns: list):
        """设置排除模式"""
        import json
        self.exclude_patterns = json.dumps(patterns, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "scan_mode": self.scan_mode,
            "sample_rate": self.sample_rate,
            "confidence_threshold": self.confidence_threshold,
            "databases": self.get_databases(),
            "tables": self.get_tables(),
            "exclude_patterns": self.get_exclude_patterns(),
            "status": self.status,
            "progress": self.progress,
            "total_columns": self.total_columns,
            "scanned_columns": self.scanned_columns,
            "sensitive_found": self.sensitive_found,
            "pii_count": self.pii_count,
            "financial_count": self.financial_count,
            "health_count": self.health_count,
            "credential_count": self.credential_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration": self.estimated_duration,
            "created_by": self.created_by,
            "error_message": self.error_message,
        }


class SensitivityScanResult(Base):
    """敏感数据扫描结果表"""
    __tablename__ = "sensitivity_scan_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    result_id = Column(String(64), unique=True, nullable=False, index=True, comment='结果ID')

    # 所属任务
    task_id = Column(String(64), ForeignKey('sensitivity_scan_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)

    # 扫描对象
    database_name = Column(String(128), comment='数据库名')
    table_name = Column(String(128), comment='表名')
    column_name = Column(String(128), nullable=False, comment='列名')

    # 识别结果
    sensitivity_type = Column(String(64), comment='敏感类型: pii, financial, health, credential')
    sensitivity_sub_type = Column(String(64), comment='敏感子类型: phone, email, id_card, bank_card, etc.')
    sensitivity_level = Column(String(32), comment='敏感级别: public, internal, confidential, restricted')

    # AI 识别信息
    confidence = Column(Integer, comment='置信度 0-100')
    matched_pattern = Column(String(255), comment='匹配的模式')
    sample_values = Column(Text, comment='样本值 (JSON)')

    # 校验状态
    verified = Column(Boolean, default=False, comment='是否已人工校验')
    verified_by = Column(String(128), comment='校验人')
    verified_at = Column(TIMESTAMP, comment='校验时间')
    verified_result = Column(String(16), comment='校验结果: confirmed, rejected, modified')

    # 修正后的结果
    original_type = Column(String(64), comment='原始识别类型（修正前）')
    original_level = Column(String(32), comment='原始敏感级别（修正前）')
    original_confidence = Column(Integer, comment='原始置信度（修正前）')

    # 脱敏建议
    masking_strategy = Column(String(64), comment='推荐脱敏策略: mask, hash, encrypt, redact')
    is_masked = Column(Boolean, default=False, comment='是否已应用脱敏')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    __table_args__ = (
        Index('idx_sensitivity_result_id', 'result_id'),
        Index('idx_sensitivity_result_task', 'task_id'),
        {'comment': '敏感数据扫描结果表'}
    )

    def get_sample_values(self) -> list:
        """获取样本值"""
        if not self.sample_values:
            return []
        import json
        try:
            return json.loads(self.sample_values)
        except json.JSONDecodeError:
            return []

    def set_sample_values(self, values: list):
        """设置样本值"""
        import json
        # 限制样本值数量，避免存储过大
        limited_values = values[:10]
        self.sample_values = json.dumps(limited_values, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "sensitivity_type": self.sensitivity_type,
            "sensitivity_sub_type": self.sensitivity_sub_type,
            "sensitivity_level": self.sensitivity_level,
            "confidence": self.confidence,
            "matched_pattern": self.matched_pattern,
            "sample_values": self.get_sample_values(),
            "verified": self.verified,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_result": self.verified_result,
            "original_type": self.original_type,
            "original_level": self.original_level,
            "original_confidence": self.original_confidence,
            "masking_strategy": self.masking_strategy,
            "is_masked": self.is_masked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SensitivityPattern(Base):
    """敏感数据模式库表（动态模式）"""
    __tablename__ = "sensitivity_patterns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    pattern_id = Column(String(64), unique=True, nullable=False, index=True, comment='模式ID')

    # 模式分类
    category = Column(String(64), nullable=False, comment='分类: pii, financial, health, credential')
    sub_type = Column(String(64), nullable=False, comment='子类型: phone, email, id_card, etc.')
    name = Column(String(128), nullable=False, comment='模式名称')

    # 模式定义
    pattern_type = Column(String(32), default='regex', comment='模式类型: regex, keyword, llm')
    pattern = Column(String(512), comment='正则表达式模式')
    keywords = Column(Text, comment='关键词列表 (JSON)')
    description = Column(Text, comment='模式描述')

    # 检测配置
    confidence_weight = Column(Integer, default=80, comment='置信度权重')
    sensitivity_level = Column(String(32), default='confidential', comment='默认敏感级别')
    masking_strategy = Column(String(64), default='mask', comment='推荐脱敏策略')

    # 示例
    examples = Column(Text, comment='匹配示例 (JSON)')
    counter_examples = Column(Text, comment='不匹配示例 (JSON)')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_system = Column(Boolean, default=False, comment='是否系统预置')

    # 统计
    match_count = Column(Integer, default=0, comment='匹配次数')
    false_positive_count = Column(Integer, default=0, comment='误报次数')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    created_by = Column(String(128), comment='创建者')

    __table_args__ = (
        Index('idx_sensitivity_pattern_id', 'pattern_id'),
        {'comment': '敏感数据模式库表'}
    )

    def get_keywords(self) -> list:
        """获取关键词列表"""
        if not self.keywords:
            return []
        import json
        try:
            return json.loads(self.keywords)
        except json.JSONDecodeError:
            return []

    def set_keywords(self, keywords: list):
        """设置关键词列表"""
        import json
        self.keywords = json.dumps(keywords, ensure_ascii=False)

    def get_examples(self) -> list:
        """获取示例"""
        if not self.examples:
            return []
        import json
        try:
            return json.loads(self.examples)
        except json.JSONDecodeError:
            return []

    def set_examples(self, examples: list):
        """设置示例"""
        import json
        self.examples = json.dumps(examples, ensure_ascii=False)

    def get_counter_examples(self) -> list:
        """获取反例"""
        if not self.counter_examples:
            return []
        import json
        try:
            return json.loads(self.counter_examples)
        except json.JSONDecodeError:
            return []

    def set_counter_examples(self, examples: list):
        """设置反例"""
        import json
        self.counter_examples = json.dumps(examples, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category,
            "sub_type": self.sub_type,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "pattern": self.pattern,
            "keywords": self.get_keywords(),
            "description": self.description,
            "confidence_weight": self.confidence_weight,
            "sensitivity_level": self.sensitivity_level,
            "masking_strategy": self.masking_strategy,
            "examples": self.get_examples(),
            "counter_examples": self.get_counter_examples(),
            "is_active": self.is_active,
            "is_system": self.is_system,
            "match_count": self.match_count,
            "false_positive_count": self.false_positive_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
