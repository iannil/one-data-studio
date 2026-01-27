"""
元数据同步服务

实现 Alldata 和 OpenMetadata 之间的双向元数据同步:
- Alldata -> OpenMetadata: 将本地元数据推送到 OpenMetadata
- OpenMetadata -> Alldata: 从 OpenMetadata 拉取元数据更新
- 增量同步: 检测并同步变更部分
- 自定义属性: 支持扩展属性同步
- 敏感标签: 完整的敏感数据标签映射
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum

from .client import OpenMetadataClient, get_client
from .config import OpenMetadataConfig, get_config, is_enabled

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """变更类型"""
    ADDED = "added"       # 新增表/列
    MODIFIED = "modified"  # 修改
    DELETED = "deleted"    # 删除
    UNCHANGED = "unchanged"  # 无变化


@dataclass
class ColumnChange:
    """列变更详情"""
    column_name: str
    change_type: ChangeType
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    old_description: Optional[str] = None
    new_description: Optional[str] = None


@dataclass
class TableChange:
    """表变更详情"""
    table_name: str
    database_name: str
    change_type: ChangeType
    column_changes: List[ColumnChange] = field(default_factory=list)
    old_description: Optional[str] = None
    new_description: Optional[str] = None


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    database: str = ""
    table_name: str = ""
    action: str = ""  # created, updated, skipped, failed
    changes: Optional[TableChange] = None
    error: Optional[str] = None
    duration_ms: int = 0


class MetadataSyncService:
    """元数据同步服务"""

    # Alldata 数据类型到 OpenMetadata 数据类型的映射
    TYPE_MAPPING = {
        "varchar": "VARCHAR",
        "char": "CHAR",
        "text": "TEXT",
        "longtext": "LONGTEXT",
        "mediumtext": "TEXT",
        "int": "INT",
        "integer": "INT",
        "bigint": "BIGINT",
        "smallint": "SMALLINT",
        "tinyint": "TINYINT",
        "float": "FLOAT",
        "double": "DOUBLE",
        "decimal": "DECIMAL",
        "datetime": "TIMESTAMP",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "time": "TIME",
        "boolean": "BOOLEAN",
        "bool": "BOOLEAN",
        "json": "JSON",
        "blob": "BLOB",
        "longblob": "BLOB",
        "enum": "STRING",
        "set": "ARRAY",
    }

    # 敏感级别到 OpenMetadata 标签的映射
    SENSITIVITY_TAG_MAPPING = {
        "public": "Tier1",
        "internal": "Tier2",
        "confidential": "Tier3",
        "restricted": "Tier4",
    }

    # 敏感数据类型标签映射
    PII_TYPE_TAG_MAPPING = {
        "pii": "PII",
        "financial": "FINANCIAL",
        "health": "HEALTH",
        "credential": "CREDENTIAL",
        "contact": "CONTACT",
    }

    def __init__(
        self,
        client: Optional[OpenMetadataClient] = None,
        config: Optional[OpenMetadataConfig] = None,
    ):
        """
        初始化同步服务

        Args:
            client: OpenMetadata 客户端
            config: 配置对象
        """
        self.config = config or get_config()
        self.client = client or get_client()
        self._service_name = "alldata-service"

    def is_available(self) -> bool:
        """检查同步服务是否可用"""
        if not self.config.enabled:
            return False
        return self.client.health_check()

    # ========================================
    # 推送同步 (Alldata -> OpenMetadata)
    # ========================================

    def ensure_database_service(self, description: Optional[str] = None) -> Dict:
        """
        确保数据库服务存在

        Returns:
            数据库服务对象
        """
        service = self.client.get_database_service(self._service_name)
        if service:
            return service

        logger.info("Creating database service: %s", self._service_name)
        return self.client.create_database_service(
            name=self._service_name,
            service_type="Mysql",
            description=description or "Alldata 数据治理平台数据源",
        )

    def sync_database(
        self,
        db_name: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        同步数据库到 OpenMetadata

        Args:
            db_name: 数据库名称
            description: 描述

        Returns:
            同步后的数据库对象
        """
        if not self.is_available():
            logger.warning("OpenMetadata sync not available, skipping")
            return {}

        # 确保服务存在
        self.ensure_database_service()

        # 检查数据库是否存在
        db_fqn = f"{self._service_name}.{db_name}"
        existing = self.client.get_database(db_fqn)
        if existing:
            logger.debug("Database already exists: %s", db_fqn)
            return existing

        logger.info("Syncing database to OpenMetadata: %s", db_name)
        return self.client.create_database(
            name=db_name,
            service_fqn=self._service_name,
            description=description,
        )

    def sync_table(
        self,
        db_name: str,
        table_name: str,
        columns: List[Dict[str, Any]],
        description: Optional[str] = None,
        table_type: str = "Regular",
        custom_properties: Optional[Dict[str, Any]] = None,
        force_update: bool = False,
    ) -> Dict:
        """
        同步表到 OpenMetadata

        Args:
            db_name: 数据库名称
            table_name: 表名称
            columns: Alldata 格式的列定义列表
            description: 表描述
            table_type: 表类型
            custom_properties: 自定义属性扩展
            force_update: 是否强制更新（即使无变化）

        Returns:
            同步后的表对象
        """
        if not self.is_available():
            logger.warning("OpenMetadata sync not available, skipping")
            return {}

        # 确保数据库存在
        self.sync_database(db_name)

        # 转换列定义
        om_columns = self._convert_columns(columns)

        # 检查表是否存在
        table_fqn = f"{self._service_name}.{db_name}.{table_name}"
        existing = self.client.get_table(table_fqn)

        if existing:
            logger.debug("Table already exists: %s", table_fqn)
            # 检查是否需要更新
            changes = self._detect_table_changes(existing, {
                "name": table_name,
                "description": description,
                "columns": om_columns,
                "custom_properties": custom_properties,
            })

            if changes or force_update:
                logger.info("Updating table in OpenMetadata: %s (changes: %s)",
                           table_fqn, len(changes.column_changes) if changes else 0)
                return self._update_table(
                    table_fqn, existing, om_columns, description, custom_properties
                )
            return existing

        logger.info("Syncing table to OpenMetadata: %s.%s", db_name, table_name)
        return self.client.create_table(
            name=table_name,
            database_fqn=f"{self._service_name}.{db_name}",
            columns=om_columns,
            description=description,
            table_type=table_type,
            custom_properties=custom_properties,
        )

    def _update_table(
        self,
        table_fqn: str,
        existing: Dict,
        new_columns: List[Dict],
        description: Optional[str] = None,
        custom_properties: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """
        更新已存在的表

        Args:
            table_fqn: 表的完全限定名
            existing: 现有表对象
            new_columns: 新的列定义
            description: 新的描述
            custom_properties: 自定义属性

        Returns:
            更新后的表对象
        """
        updates = {}

        # 更新描述
        if description and description != existing.get("description"):
            updates["description"] = description

        # 更新列
        existing_columns = existing.get("columns", [])
        existing_col_map = {col["name"]: col for col in existing_columns}
        new_col_map = {col["name"]: col for col in new_columns}

        # 检测列变更
        columns_to_add = []
        columns_to_update = []

        for col_name, new_col in new_col_map.items():
            if col_name not in existing_col_map:
                columns_to_add.append(new_col)
            else:
                existing_col = existing_col_map[col_name]
                # 检查列是否有变化
                if (new_col.get("dataType") != existing_col.get("dataType") or
                    new_col.get("description") != existing_col.get("description") or
                    new_col.get("dataLength") != existing_col.get("dataLength")):
                    columns_to_update.append(new_col)

        # 合并所有列（OpenMetadata 需要）
        all_columns = list(existing_columns)

        # 标记需要添加的列
        for col in columns_to_add:
            all_columns.append(col)

        # 标记需要更新的列
        for col in columns_to_update:
            for i, existing_col in enumerate(all_columns):
                if existing_col["name"] == col["name"]:
                    all_columns[i] = col
                    break

        updates["columns"] = all_columns

        # 更新自定义属性
        if custom_properties:
            existing_properties = existing.get("customProperties", {})
            merged_properties = {**existing_properties, **custom_properties}
            updates["customProperties"] = merged_properties

        if updates:
            return self.client.update_table(table_fqn, updates)

        return existing

    def _detect_table_changes(
        self,
        existing: Dict,
        new_table: Dict,
    ) -> Optional[TableChange]:
        """
        检测表变更

        Args:
            existing: 现有表对象
            new_table: 新表数据

        Returns:
            TableChange 对象，无变更返回 None
        """
        changes = []
        existing_columns = existing.get("columns", [])
        new_columns = new_table.get("columns", [])

        existing_col_map = {col["name"]: col for col in existing_columns}
        new_col_map = {col["name"]: col for col in new_columns}

        # 检测新增列
        for col_name in new_col_map:
            if col_name not in existing_col_map:
                changes.append(ColumnChange(
                    column_name=col_name,
                    change_type=ChangeType.ADDED,
                    new_type=new_col_map[col_name].get("dataType"),
                ))

        # 检测修改的列
        for col_name in new_col_map:
            if col_name in existing_col_map:
                old_col = existing_col_map[col_name]
                new_col = new_col_map[col_name]
                if (old_col.get("dataType") != new_col.get("dataType") or
                    old_col.get("description") != new_col.get("description")):
                    changes.append(ColumnChange(
                        column_name=col_name,
                        change_type=ChangeType.MODIFIED,
                        old_type=old_col.get("dataType"),
                        new_type=new_col.get("dataType"),
                        old_description=old_col.get("description"),
                        new_description=new_col.get("description"),
                    ))

        # 检测删除的列
        for col_name in existing_col_map:
            if col_name not in new_col_map:
                changes.append(ColumnChange(
                    column_name=col_name,
                    change_type=ChangeType.DELETED,
                    old_type=existing_col_map[col_name].get("dataType"),
                ))

        # 检测描述变更
        desc_changed = (
            new_table.get("description") and
            new_table.get("description") != existing.get("description")
        )

        if changes or desc_changed:
            return TableChange(
                table_name=new_table.get("name", ""),
                database_name="",
                change_type=ChangeType.MODIFIED if changes else ChangeType.UNCHANGED,
                column_changes=changes,
                old_description=existing.get("description"),
                new_description=new_table.get("description"),
            )

        return None

    def _convert_columns(self, alldata_columns: List[Dict[str, Any]]) -> List[Dict]:
        """
        将 Alldata 列定义转换为 OpenMetadata 格式

        Args:
            alldata_columns: Alldata 格式的列列表

        Returns:
            OpenMetadata 格式的列列表
        """
        om_columns = []
        for col in alldata_columns:
            # 获取数据类型
            data_type = col.get("data_type", col.get("type", "VARCHAR"))
            data_type_lower = data_type.lower().split("(")[0]  # 移除长度定义
            om_type = self.TYPE_MAPPING.get(data_type_lower, "VARCHAR")

            om_col = {
                "name": col.get("name", col.get("column_name", "")),
                "dataType": om_type,
                "dataLength": col.get("length", 255),
            }

            # 可选字段
            if col.get("description") or col.get("comment"):
                om_col["description"] = col.get("description") or col.get("comment")

            if col.get("ai_description"):
                # 将 AI 描述追加到描述中
                ai_desc = col.get("ai_description")
                if om_col.get("description"):
                    om_col["description"] = f"{om_col['description']}\n\nAI: {ai_desc}"
                else:
                    om_col["description"] = f"AI: {ai_desc}"

            # 标签 (敏感性) - 使用增强映射
            tags = []
            sensitivity_level = col.get("sensitivity_level", "")
            if sensitivity_level:
                tier_tag = self.SENSITIVITY_TAG_MAPPING.get(sensitivity_level.lower())
                if tier_tag:
                    tags.append({
                        "tagFQN": f"Sensitivity.{tier_tag}",
                        "labelType": "Automated",
                        "state": "Confirmed",
                    })

            sensitivity_type = col.get("sensitivity_type", "")
            if sensitivity_type:
                pii_tag = self.PII_TYPE_TAG_MAPPING.get(sensitivity_type.lower())
                if pii_tag:
                    tags.append({
                        "tagFQN": f"PII.{pii_tag}",
                        "labelType": "Automated",
                        "state": "Confirmed",
                    })
            # 保留旧格式兼容
            elif sensitivity_type:
                tags.append({
                    "tagFQN": f"PII.{sensitivity_type.upper()}",
                    "labelType": "Automated",
                    "state": "Confirmed",
                })

            if tags:
                om_col["tags"] = tags

            # 自定义属性
            custom_props = {}
            if col.get("business_term"):
                custom_props["business_term"] = col["business_term"]
            if col.get("data_quality_score"):
                custom_props["data_quality_score"] = col["data_quality_score"]
            if col.get("null_rate") is not None:
                custom_props["null_rate"] = col["null_rate"]
            if col.get("uniqueness") is not None:
                custom_props["uniqueness"] = col["uniqueness"]
            if col.get("stale"):
                custom_props["stale"] = col["stale"]

            if custom_props:
                om_col["customProperties"] = custom_props

            om_columns.append(om_col)

        return om_columns

    def sync_metadata_table(self, metadata_table) -> Dict:
        """
        同步 Alldata MetadataTable 模型到 OpenMetadata

        Args:
            metadata_table: Alldata MetadataTable 模型实例

        Returns:
            同步后的 OpenMetadata 表对象
        """
        if not self.is_available():
            return {}

        # 获取数据库名
        db_name = metadata_table.database.name if metadata_table.database else "default"

        # 构建列定义
        columns = []
        for col in metadata_table.columns:
            columns.append({
                "name": col.name,
                "data_type": col.data_type,
                "length": col.length,
                "comment": col.comment,
                "description": col.description,
                "ai_description": col.ai_description,
                "sensitivity_level": col.sensitivity_level,
                "sensitivity_type": col.sensitivity_type,
            })

        return self.sync_table(
            db_name=db_name,
            table_name=metadata_table.name,
            columns=columns,
            description=metadata_table.description or metadata_table.comment,
        )

    # ========================================
    # 拉取同步 (OpenMetadata -> Alldata)
    # ========================================

    def fetch_tables(self, database: Optional[str] = None) -> List[Dict]:
        """
        从 OpenMetadata 获取表列表

        Args:
            database: 数据库名称过滤

        Returns:
            表列表
        """
        if not self.is_available():
            return []

        db_filter = f"{self._service_name}.{database}" if database else None
        return self.client.list_tables(database=db_filter, include_columns=True)

    def fetch_table_detail(self, db_name: str, table_name: str) -> Optional[Dict]:
        """
        从 OpenMetadata 获取表详情

        Args:
            db_name: 数据库名称
            table_name: 表名称

        Returns:
            表详情或 None
        """
        if not self.is_available():
            return None

        table_fqn = f"{self._service_name}.{db_name}.{table_name}"
        return self.client.get_table(table_fqn, include_columns=True)

    # ========================================
    # 批量同步
    # ========================================

    def sync_all_metadata(self, metadata_tables: List) -> Dict[str, int]:
        """
        批量同步所有元数据表

        Args:
            metadata_tables: MetadataTable 模型实例列表

        Returns:
            同步统计 {"synced": N, "failed": N, "skipped": N}
        """
        stats = {"synced": 0, "failed": 0, "skipped": 0}

        if not self.is_available():
            stats["skipped"] = len(metadata_tables)
            return stats

        for table in metadata_tables:
            try:
                self.sync_metadata_table(table)
                stats["synced"] += 1
            except Exception as e:
                logger.error("Failed to sync table %s: %s", table.name, e)
                stats["failed"] += 1

        logger.info(
            "Metadata sync completed: synced=%d, failed=%d, skipped=%d",
            stats["synced"],
            stats["failed"],
            stats["skipped"],
        )
        return stats


# 全局同步服务实例
_sync_service: Optional[MetadataSyncService] = None


def get_sync_service() -> MetadataSyncService:
    """获取全局同步服务实例（单例）"""
    global _sync_service
    if _sync_service is None:
        _sync_service = MetadataSyncService()
    return _sync_service
