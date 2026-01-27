"""
OpenMetadata 集成模块

提供与 OpenMetadata 平台的双向集成:
- 元数据同步 (Alldata <-> OpenMetadata)
- OpenLineage 血缘标准化
- 数据质量集成
"""

from .config import OpenMetadataConfig
from .client import OpenMetadataClient
from .sync_service import MetadataSyncService
from .lineage_service import OpenLineageService

__all__ = [
    "OpenMetadataConfig",
    "OpenMetadataClient",
    "MetadataSyncService",
    "OpenLineageService",
]
