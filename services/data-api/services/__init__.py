"""
data API 服务模块
"""

from .metadata_graph_builder import MetadataGraphBuilder
from .ai_asset_search import AIAssetSearchService, get_ai_asset_search_service
from .ai_cleaning_advisor import AICleaningAdvisor, get_ai_cleaning_advisor
from .ai_field_mapping import AIFieldMappingService, get_ai_field_mapping_service
from .smart_alert_service import SmartAlertService, get_smart_alert_service
from .enhanced_sso_service import EnhancedSSOService, get_enhanced_sso_service
from .data_service_manager import DataServiceManager, get_data_service_manager
from .portal_service import PortalService, get_portal_service
from .notification_service import (
    NotificationService,
    get_notification_service,
    NotificationTemplate,
    NotificationRule,
)
from .content_service import (
    ContentService,
    get_content_service,
    ContentArticle,
    ContentCategory,
    ContentTag,
    ContentType,
    ContentStatus,
)
from .metadata_version_service import (
    MetadataVersionService,
    get_metadata_version_service,
    MetadataSnapshot,
    TableVersion,
    ColumnVersion,
    TableDiff,
    ChangeType,
)
from .smart_scheduler_service import (
    SmartSchedulerService,
    get_smart_scheduler_service,
    ScheduledTask,
    TaskDependency,
    TaskStatus,
    TaskPriority,
    ResourceRequirement,
    SchedulingPolicy,
)
from .table_fusion_service import (
    TableFusionService,
    get_table_fusion_service,
    JoinType,
    JoinKeyPair,
    JoinQualityScore,
    JoinStrategyRecommendation,
)
from .asset_value_calculator import (
    AssetValueCalculator,
    get_asset_value_calculator,
    ValueLevel,
    ValueScoreBreakdown,
    AssetValueReport,
)
from .sensitivity_auto_scan_service import (
    SensitivityAutoScanService,
    get_sensitivity_auto_scan_service,
    AutoScanMode,
    AutoScanStatus,
    AutoScanPolicy,
    AutoScanProgress,
)
from .kettle_orchestration_service import (
    KettleOrchestrationService,
    get_kettle_orchestration_service,
    OrchestrationStatus,
    PipelineType,
    OrchestrationRequest,
    OrchestrationResult,
)
from .asset_auto_catalog_service import (
    AssetAutoCatalogService,
    get_asset_auto_catalog_service,
)
from .metadata_auto_scan_engine import (
    MetadataAutoScanEngine,
    get_metadata_auto_scan_engine,
)
from .ai_service import (
    AIService,
    AIServiceConfig,
    get_ai_service,
)
from .unified_auth_service import (
    UnifiedAuthService,
    get_unified_auth_service,
)
from .approval_workflow_engine import (
    ApprovalWorkflowEngine,
    get_approval_workflow_engine,
)
from .scan_scheduler import (
    ScanScheduler,
    get_scan_scheduler,
    init_scan_scheduler,
)
from .openlineage_event_service import (
    OpenLineageEventService,
    get_openlineage_event_service,
    init_openlineage_event_service,
    emit_etl_lineage,
    emit_dataset_created,
    emit_dataset_updated,
)

# OpenMetadata 集成服务
try:
    from integrations.openmetadata import (
        OpenMetadataClient,
        OpenMetadataConfig,
        MetadataSyncService,
        OpenLineageService,
    )
    from integrations.openmetadata.client import get_client as get_openmetadata_client
    from integrations.openmetadata.sync_service import get_sync_service as get_metadata_sync_service
    from integrations.openmetadata.lineage_service import get_lineage_service as get_openlineage_service
    from integrations.openmetadata.config import is_enabled as is_openmetadata_enabled
    OPENMETADATA_AVAILABLE = True
except ImportError:
    OPENMETADATA_AVAILABLE = False
    OpenMetadataClient = None
    OpenMetadataConfig = None
    MetadataSyncService = None
    OpenLineageService = None
    get_openmetadata_client = None
    get_metadata_sync_service = None
    get_openlineage_service = None
    is_openmetadata_enabled = lambda: False

__all__ = [
    'MetadataGraphBuilder',
    'AIAssetSearchService',
    'get_ai_asset_search_service',
    'AICleaningAdvisor',
    'get_ai_cleaning_advisor',
    'AIFieldMappingService',
    'get_ai_field_mapping_service',
    'SmartAlertService',
    'get_smart_alert_service',
    'EnhancedSSOService',
    'get_enhanced_sso_service',
    'DataServiceManager',
    'get_data_service_manager',
    'PortalService',
    'get_portal_service',
    'NotificationService',
    'get_notification_service',
    'NotificationTemplate',
    'NotificationRule',
    'ContentService',
    'get_content_service',
    'ContentArticle',
    'ContentCategory',
    'ContentTag',
    'ContentType',
    'ContentStatus',
    'MetadataVersionService',
    'get_metadata_version_service',
    'MetadataSnapshot',
    'TableVersion',
    'ColumnVersion',
    'TableDiff',
    'ChangeType',
    'SmartSchedulerService',
    'get_smart_scheduler_service',
    'ScheduledTask',
    'TaskDependency',
    'TaskStatus',
    'TaskPriority',
    'ResourceRequirement',
    'SchedulingPolicy',
    'TableFusionService',
    'get_table_fusion_service',
    'JoinType',
    'JoinKeyPair',
    'JoinQualityScore',
    'JoinStrategyRecommendation',
    'AssetValueCalculator',
    'get_asset_value_calculator',
    'ValueLevel',
    'ValueScoreBreakdown',
    'AssetValueReport',
    'SensitivityAutoScanService',
    'get_sensitivity_auto_scan_service',
    'AutoScanMode',
    'AutoScanStatus',
    'AutoScanPolicy',
    'AutoScanProgress',
    'KettleOrchestrationService',
    'get_kettle_orchestration_service',
    'OrchestrationStatus',
    'PipelineType',
    'OrchestrationRequest',
    'OrchestrationResult',
    'AssetAutoCatalogService',
    'get_asset_auto_catalog_service',
    'MetadataAutoScanEngine',
    'get_metadata_auto_scan_engine',
    'AIService',
    'AIServiceConfig',
    'get_ai_service',
    'UnifiedAuthService',
    'get_unified_auth_service',
    'ApprovalWorkflowEngine',
    'get_approval_workflow_engine',
    'ScanScheduler',
    'get_scan_scheduler',
    'init_scan_scheduler',
    # OpenLineage 事件服务
    'OpenLineageEventService',
    'get_openlineage_event_service',
    'init_openlineage_event_service',
    'emit_etl_lineage',
    'emit_dataset_created',
    'emit_dataset_updated',
    # OpenMetadata 集成
    'OPENMETADATA_AVAILABLE',
    'OpenMetadataClient',
    'OpenMetadataConfig',
    'MetadataSyncService',
    'OpenLineageService',
    'get_openmetadata_client',
    'get_metadata_sync_service',
    'get_openlineage_service',
    'is_openmetadata_enabled',
]
