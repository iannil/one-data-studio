"""
测试数据工厂模块
提供各类测试数据的工厂类
"""

from .user_factory import (
    UserFactory,
    DataSourceFactory,
    MetadataFactory,
    DataAssetFactory,
)
from .metadata_factory import (
    MetadataDatabaseFactory,
    MetadataTableFactory,
    MetadataColumnFactory,
)
from .etl_factory import (
    ETLTaskFactory,
    ETLStepFactory,
    DataCollectionTaskFactory,
)
from .document_factory import (
    DocumentFactory,
    KnowledgeBaseFactory,
    IndexedDocumentFactory,
)

__all__ = [
    # 用户工厂
    "UserFactory",
    "DataSourceFactory",
    "MetadataFactory",
    "DataAssetFactory",
    # 元数据工厂
    "MetadataDatabaseFactory",
    "MetadataTableFactory",
    "MetadataColumnFactory",
    # ETL 工厂
    "ETLTaskFactory",
    "ETLStepFactory",
    "DataCollectionTaskFactory",
    # 文档工厂
    "DocumentFactory",
    "KnowledgeBaseFactory",
    "IndexedDocumentFactory",
]
