"""
元数据同步服务
Phase 3 P1: ETL 完成后的元数据自动同步与版本管理

功能：
- ETL 任务完成后自动同步元数据
- 更新表统计信息（行数、最后同步时间）
- 触发 AI 重新标注（如有新字段）
- 记录元数据版本历史
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MetadataChangeType(str, Enum):
    """元数据变更类型"""
    CREATED = "created"            # 新建
    UPDATED = "updated"            # 更新
    DELETED = "deleted"            # 删除
    SCHEMA_CHANGED = "schema_changed"  # 结构变更
    STATS_UPDATED = "stats_updated"    # 统计信息更新
    AI_ANNOTATED = "ai_annotated"      # AI 标注更新
    ETL_SYNCED = "etl_synced"          # ETL 同步


class SyncTrigger(str, Enum):
    """同步触发来源"""
    ETL_COMPLETION = "etl_completion"  # ETL 完成
    MANUAL = "manual"                  # 手动触发
    SCHEDULED = "scheduled"            # 定时任务
    API_CALL = "api_call"              # API 调用


@dataclass
class ETLExecutionResult:
    """ETL 执行结果"""
    task_id: str
    status: str  # success, failed, partial
    rows_read: int = 0
    rows_written: int = 0
    rows_error: int = 0
    start_time: datetime = None
    end_time: datetime = None
    source_table: str = ""
    target_table: str = ""
    error_message: str = ""
    execution_log: str = ""


@dataclass
class TableStats:
    """表统计信息"""
    row_count: int = 0
    column_count: int = 0
    data_size_bytes: int = 0
    last_modified: datetime = None
    last_synced: datetime = None
    sample_data: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MetadataVersion:
    """元数据版本"""
    version_id: str
    table_id: str
    change_type: MetadataChangeType
    changed_by: str
    changed_at: datetime
    previous_version_id: Optional[str] = None
    change_summary: str = ""
    change_details: Dict[str, Any] = field(default_factory=dict)
    # 快照
    schema_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    table_id: str
    trigger: SyncTrigger
    synced_at: datetime
    changes_detected: List[str] = field(default_factory=list)
    version_created: Optional[str] = None
    ai_annotation_triggered: bool = False
    error_message: str = ""


class MetadataSyncService:
    """元数据同步服务"""

    def __init__(
        self,
        db_session=None,
        ai_annotation_service=None,
        notification_service=None,
    ):
        """
        初始化服务

        Args:
            db_session: 数据库会话
            ai_annotation_service: AI 标注服务
            notification_service: 通知服务
        """
        self.db_session = db_session
        self.ai_annotation_service = ai_annotation_service
        self.notification_service = notification_service

        # 回调函数列表
        self._post_sync_callbacks: List[Callable] = []
        self._pre_sync_callbacks: List[Callable] = []

    def register_post_sync_callback(self, callback: Callable) -> None:
        """注册同步后回调"""
        self._post_sync_callbacks.append(callback)

    def register_pre_sync_callback(self, callback: Callable) -> None:
        """注册同步前回调"""
        self._pre_sync_callbacks.append(callback)

    def sync_after_etl(
        self,
        etl_result: ETLExecutionResult,
        auto_annotate: bool = True,
    ) -> SyncResult:
        """
        ETL 任务完成后同步元数据

        Args:
            etl_result: ETL 执行结果
            auto_annotate: 是否自动触发 AI 标注

        Returns:
            同步结果
        """
        sync_result = SyncResult(
            success=False,
            table_id="",
            trigger=SyncTrigger.ETL_COMPLETION,
            synced_at=datetime.utcnow(),
        )

        try:
            # 执行前置回调
            for callback in self._pre_sync_callbacks:
                try:
                    callback(etl_result)
                except Exception as e:
                    logger.warning(f"前置回调执行失败: {e}")

            # 1. 查找目标表元数据
            target_table_meta = self._find_table_metadata(etl_result.target_table)
            if not target_table_meta:
                logger.warning(f"目标表元数据未找到: {etl_result.target_table}")
                # 尝试创建新的元数据记录
                target_table_meta = self._create_table_metadata(etl_result.target_table)

            sync_result.table_id = target_table_meta.get("id", "")

            # 2. 检测结构变更
            changes = self._detect_schema_changes(target_table_meta, etl_result)
            sync_result.changes_detected = changes

            # 3. 更新表统计信息
            stats = TableStats(
                row_count=etl_result.rows_written,
                last_synced=datetime.utcnow(),
            )
            self._update_table_stats(target_table_meta, stats, etl_result)

            # 4. 创建版本记录
            change_type = MetadataChangeType.ETL_SYNCED
            if changes:
                change_type = MetadataChangeType.SCHEMA_CHANGED

            version_id = self._create_metadata_version(
                table_id=sync_result.table_id,
                change_type=change_type,
                change_summary=f"ETL 同步: {etl_result.rows_written} 行写入",
                change_details={
                    "etl_task_id": etl_result.task_id,
                    "rows_read": etl_result.rows_read,
                    "rows_written": etl_result.rows_written,
                    "rows_error": etl_result.rows_error,
                    "changes": changes,
                },
                schema_snapshot=target_table_meta,
            )
            sync_result.version_created = version_id

            # 5. 如果有新字段，触发 AI 标注
            if auto_annotate and changes and any("new_column" in c for c in changes):
                sync_result.ai_annotation_triggered = True
                self._trigger_ai_annotation(target_table_meta)

            # 6. 发送通知
            if self.notification_service:
                self._send_sync_notification(sync_result, etl_result)

            sync_result.success = True

            # 执行后置回调
            for callback in self._post_sync_callbacks:
                try:
                    callback(sync_result, etl_result)
                except Exception as e:
                    logger.warning(f"后置回调执行失败: {e}")

        except Exception as e:
            logger.error(f"元数据同步失败: {e}")
            sync_result.error_message = str(e)

        return sync_result

    def update_table_stats(
        self,
        table_id: str,
        stats: TableStats,
        create_version: bool = True,
    ) -> bool:
        """
        更新表统计信息

        Args:
            table_id: 表 ID
            stats: 统计信息
            create_version: 是否创建版本记录

        Returns:
            是否成功
        """
        try:
            table_meta = self._get_table_by_id(table_id)
            if not table_meta:
                logger.error(f"表不存在: {table_id}")
                return False

            # 更新统计信息
            updates = {
                "row_count": stats.row_count,
                "last_synced_at": stats.last_synced or datetime.utcnow(),
            }

            if stats.column_count > 0:
                updates["column_count"] = stats.column_count
            if stats.data_size_bytes > 0:
                updates["data_size_bytes"] = stats.data_size_bytes

            self._update_table_metadata(table_id, updates)

            # 创建版本记录
            if create_version:
                self._create_metadata_version(
                    table_id=table_id,
                    change_type=MetadataChangeType.STATS_UPDATED,
                    change_summary=f"统计信息更新: {stats.row_count} 行",
                    change_details={
                        "row_count": stats.row_count,
                        "column_count": stats.column_count,
                        "data_size_bytes": stats.data_size_bytes,
                    },
                )

            return True

        except Exception as e:
            logger.error(f"更新表统计信息失败: {e}")
            return False

    def create_metadata_version(
        self,
        table_id: str,
        change_type: MetadataChangeType,
        change_summary: str = "",
        change_details: Dict[str, Any] = None,
        changed_by: str = "system",
    ) -> Optional[str]:
        """
        创建元数据版本记录

        Args:
            table_id: 表 ID
            change_type: 变更类型
            change_summary: 变更摘要
            change_details: 变更详情
            changed_by: 变更人

        Returns:
            版本 ID
        """
        return self._create_metadata_version(
            table_id=table_id,
            change_type=change_type,
            change_summary=change_summary,
            change_details=change_details or {},
            changed_by=changed_by,
        )

    def get_version_history(
        self,
        table_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取表的元数据版本历史

        Args:
            table_id: 表 ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            版本历史列表
        """
        try:
            if self.db_session:
                # 实际数据库查询
                from models.metadata_version import MetadataVersionModel
                versions = self.db_session.query(MetadataVersionModel).filter(
                    MetadataVersionModel.table_id == table_id
                ).order_by(
                    MetadataVersionModel.created_at.desc()
                ).offset(offset).limit(limit).all()

                return [v.to_dict() for v in versions]
            else:
                # 模拟返回
                return []

        except Exception as e:
            logger.error(f"获取版本历史失败: {e}")
            return []

    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str,
    ) -> Dict[str, Any]:
        """
        比较两个版本的差异

        Args:
            version_id_1: 版本 1 ID
            version_id_2: 版本 2 ID

        Returns:
            差异比较结果
        """
        try:
            v1 = self._get_version_by_id(version_id_1)
            v2 = self._get_version_by_id(version_id_2)

            if not v1 or not v2:
                return {"error": "版本不存在"}

            # 比较 schema
            schema1 = v1.get("schema_snapshot", {})
            schema2 = v2.get("schema_snapshot", {})

            diff = {
                "version_1": {
                    "id": version_id_1,
                    "created_at": v1.get("created_at"),
                },
                "version_2": {
                    "id": version_id_2,
                    "created_at": v2.get("created_at"),
                },
                "columns_added": [],
                "columns_removed": [],
                "columns_modified": [],
                "stats_diff": {},
            }

            # 比较列
            cols1 = {c.get("name"): c for c in schema1.get("columns", [])}
            cols2 = {c.get("name"): c for c in schema2.get("columns", [])}

            for name in set(cols2.keys()) - set(cols1.keys()):
                diff["columns_added"].append(cols2[name])

            for name in set(cols1.keys()) - set(cols2.keys()):
                diff["columns_removed"].append(cols1[name])

            for name in set(cols1.keys()) & set(cols2.keys()):
                if cols1[name] != cols2[name]:
                    diff["columns_modified"].append({
                        "name": name,
                        "before": cols1[name],
                        "after": cols2[name],
                    })

            # 比较统计信息
            stats_keys = ["row_count", "column_count", "data_size_bytes"]
            for key in stats_keys:
                v1_val = schema1.get(key)
                v2_val = schema2.get(key)
                if v1_val != v2_val:
                    diff["stats_diff"][key] = {
                        "before": v1_val,
                        "after": v2_val,
                    }

            return diff

        except Exception as e:
            logger.error(f"版本比较失败: {e}")
            return {"error": str(e)}

    def rollback_to_version(
        self,
        table_id: str,
        version_id: str,
    ) -> bool:
        """
        回滚到指定版本（仅元数据）

        Args:
            table_id: 表 ID
            version_id: 目标版本 ID

        Returns:
            是否成功
        """
        try:
            version = self._get_version_by_id(version_id)
            if not version:
                logger.error(f"版本不存在: {version_id}")
                return False

            if version.get("table_id") != table_id:
                logger.error(f"版本不属于此表: {version_id}")
                return False

            # 恢复 schema 快照
            schema_snapshot = version.get("schema_snapshot", {})

            # 更新元数据
            self._update_table_metadata(table_id, {
                "columns": schema_snapshot.get("columns", []),
                "description": schema_snapshot.get("description", ""),
                "tags": schema_snapshot.get("tags", []),
            })

            # 创建回滚版本记录
            self._create_metadata_version(
                table_id=table_id,
                change_type=MetadataChangeType.UPDATED,
                change_summary=f"回滚到版本 {version_id}",
                change_details={
                    "rollback_from": version_id,
                },
                schema_snapshot=schema_snapshot,
            )

            return True

        except Exception as e:
            logger.error(f"版本回滚失败: {e}")
            return False

    # =========================================
    # 内部方法
    # =========================================

    def _find_table_metadata(self, table_name: str) -> Optional[Dict[str, Any]]:
        """根据表名查找元数据"""
        try:
            if self.db_session:
                from models.metadata import MetadataTable
                table = self.db_session.query(MetadataTable).filter(
                    MetadataTable.table_name == table_name
                ).first()
                return table.to_dict() if table else None
            return None
        except Exception as e:
            logger.error(f"查找表元数据失败: {e}")
            return None

    def _get_table_by_id(self, table_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取表元数据"""
        try:
            if self.db_session:
                from models.metadata import MetadataTable
                table = self.db_session.query(MetadataTable).filter(
                    MetadataTable.id == table_id
                ).first()
                return table.to_dict() if table else None
            return None
        except Exception as e:
            logger.error(f"获取表元数据失败: {e}")
            return None

    def _create_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """创建新的表元数据记录"""
        try:
            if self.db_session:
                from models.metadata import MetadataTable
                import uuid
                table = MetadataTable(
                    id=str(uuid.uuid4()),
                    table_name=table_name,
                    created_at=datetime.utcnow(),
                )
                self.db_session.add(table)
                self.db_session.commit()
                return table.to_dict()
            return {"id": "", "table_name": table_name}
        except Exception as e:
            logger.error(f"创建表元数据失败: {e}")
            return {"id": "", "table_name": table_name}

    def _update_table_metadata(self, table_id: str, updates: Dict[str, Any]) -> bool:
        """更新表元数据"""
        try:
            if self.db_session:
                from models.metadata import MetadataTable
                table = self.db_session.query(MetadataTable).filter(
                    MetadataTable.id == table_id
                ).first()
                if table:
                    for key, value in updates.items():
                        if hasattr(table, key):
                            setattr(table, key, value)
                    table.updated_at = datetime.utcnow()
                    self.db_session.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"更新表元数据失败: {e}")
            return False

    def _detect_schema_changes(
        self,
        table_meta: Dict[str, Any],
        etl_result: ETLExecutionResult,
    ) -> List[str]:
        """检测结构变更"""
        changes = []
        # 简化实现：实际应该连接数据库检查真实结构
        # 这里仅作为占位
        return changes

    def _update_table_stats(
        self,
        table_meta: Dict[str, Any],
        stats: TableStats,
        etl_result: ETLExecutionResult,
    ) -> None:
        """更新表统计信息"""
        table_id = table_meta.get("id")
        if table_id:
            self._update_table_metadata(table_id, {
                "row_count": stats.row_count,
                "last_synced_at": stats.last_synced,
                "updated_at": datetime.utcnow(),
            })

    def _create_metadata_version(
        self,
        table_id: str,
        change_type: MetadataChangeType,
        change_summary: str,
        change_details: Dict[str, Any],
        schema_snapshot: Dict[str, Any] = None,
        changed_by: str = "system",
    ) -> Optional[str]:
        """创建版本记录"""
        try:
            import uuid
            version_id = str(uuid.uuid4())

            if self.db_session:
                from models.metadata_version import MetadataVersionModel
                version = MetadataVersionModel(
                    id=version_id,
                    table_id=table_id,
                    change_type=change_type.value,
                    change_summary=change_summary,
                    change_details=change_details,
                    schema_snapshot=schema_snapshot or {},
                    changed_by=changed_by,
                    created_at=datetime.utcnow(),
                )
                self.db_session.add(version)
                self.db_session.commit()

            return version_id

        except Exception as e:
            logger.error(f"创建版本记录失败: {e}")
            return None

    def _get_version_by_id(self, version_id: str) -> Optional[Dict[str, Any]]:
        """获取版本记录"""
        try:
            if self.db_session:
                from models.metadata_version import MetadataVersionModel
                version = self.db_session.query(MetadataVersionModel).filter(
                    MetadataVersionModel.id == version_id
                ).first()
                return version.to_dict() if version else None
            return None
        except Exception as e:
            logger.error(f"获取版本记录失败: {e}")
            return None

    def _trigger_ai_annotation(self, table_meta: Dict[str, Any]) -> None:
        """触发 AI 标注"""
        if self.ai_annotation_service:
            try:
                columns = table_meta.get("columns", [])
                table_name = table_meta.get("table_name", "")

                # 只对未标注的列进行标注
                unannotated_columns = [
                    c for c in columns
                    if not c.get("ai_description")
                ]

                if unannotated_columns:
                    self.ai_annotation_service.annotate_table(
                        table_name=table_name,
                        columns=unannotated_columns,
                        use_llm=True,
                    )
                    logger.info(f"已触发 AI 标注: {table_name}, {len(unannotated_columns)} 列")

            except Exception as e:
                logger.error(f"触发 AI 标注失败: {e}")

    def _send_sync_notification(
        self,
        sync_result: SyncResult,
        etl_result: ETLExecutionResult,
    ) -> None:
        """发送同步通知"""
        if self.notification_service:
            try:
                message = f"元数据同步完成: {etl_result.target_table}"
                if sync_result.changes_detected:
                    message += f", 检测到 {len(sync_result.changes_detected)} 处变更"

                self.notification_service.send(
                    channel="metadata_sync",
                    title="元数据同步通知",
                    message=message,
                    data={
                        "table_id": sync_result.table_id,
                        "trigger": sync_result.trigger.value,
                        "changes": sync_result.changes_detected,
                    },
                )
            except Exception as e:
                logger.warning(f"发送通知失败: {e}")


# 创建全局实例
_metadata_sync_service: Optional[MetadataSyncService] = None


def get_metadata_sync_service(
    db_session=None,
    ai_annotation_service=None,
    notification_service=None,
) -> MetadataSyncService:
    """获取元数据同步服务单例"""
    global _metadata_sync_service
    if _metadata_sync_service is None:
        _metadata_sync_service = MetadataSyncService(
            db_session=db_session,
            ai_annotation_service=ai_annotation_service,
            notification_service=notification_service,
        )
    return _metadata_sync_service
