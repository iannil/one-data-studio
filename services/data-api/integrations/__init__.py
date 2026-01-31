"""
data API 外部集成模块

支持的集成:
- OpenMetadata: 元数据治理平台
- Kettle: ETL 执行引擎
- Apache Hop: 现代 ETL 执行引擎（Kettle 替代方案，可选）
- Great Expectations: 数据质量引擎（可选）
- ShardingSphere: 透明脱敏代理（可选）
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

# Apache Hop（可选依赖，Kettle 替代引擎）
try:
    from .hop import HopConfig, HopBridge
    __all__.extend(["HopConfig", "HopBridge"])
except ImportError:
    HopConfig = None
    HopBridge = None

# Great Expectations（可选依赖，import 失败时降级）
try:
    from .great_expectations import GEConfig, GEValidationEngine
    __all__.extend(["GEConfig", "GEValidationEngine"])
except ImportError:
    GEConfig = None
    GEValidationEngine = None

# ShardingSphere（可选依赖，透明脱敏）
try:
    from .shardingsphere import ShardingSphereConfig, ShardingSphereClient, MaskingRuleGenerator
    __all__.extend(["ShardingSphereConfig", "ShardingSphereClient", "MaskingRuleGenerator"])
except ImportError:
    ShardingSphereConfig = None
    ShardingSphereClient = None
    MaskingRuleGenerator = None
