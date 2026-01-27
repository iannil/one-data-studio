"""
Alldata API 外部集成模块

支持的集成:
- OpenMetadata: 元数据治理平台
- Kettle: ETL 执行引擎
"""

from .openmetadata import (
    OpenMetadataClient,
    OpenMetadataConfig,
    MetadataSyncService,
    OpenLineageService,
)

from .kettle import (
    KettleConfig,
    KettleBridge,
)

__all__ = [
    # OpenMetadata
    "OpenMetadataClient",
    "OpenMetadataConfig",
    "MetadataSyncService",
    "OpenLineageService",
    # Kettle
    "KettleConfig",
    "KettleBridge",
]
