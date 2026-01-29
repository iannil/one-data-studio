"""
元数据版本回滚服务
支持版本回滚预览、SQL 迁移脚本生成和回滚执行
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RollbackAction(str, Enum):
    """回滚动作类型"""
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    MODIFY_COLUMN = "modify_column"
    RESTORE_DATA = "restore_data"
    RESTORE_METADATA = "restore_metadata"


@dataclass
class RollbackPlan:
    """回滚计划"""
    version_id: str
    target_version_id: str
    table_name: str
    database_name: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    sql_statements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    estimated_duration_seconds: int = 0
    requires_data_backup: bool = False
    is_reversible: bool = True

    def to_dict(self) -> Dict:
        return {
            "version_id": self.version_id,
            "target_version_id": self.target_version_id,
            "table_name": self.table_name,
            "database_name": self.database_name,
            "actions": self.actions,
            "sql_statements": self.sql_statements,
            "warnings": self.warnings,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "requires_data_backup": self.requires_data_backup,
            "is_reversible": self.is_reversible,
        }


@dataclass
class RollbackResult:
    """回滚结果"""
    success: bool
    version_id: str
    target_version_id: str
    new_version_id: Optional[str] = None
    executed_sql: List[str] = field(default_factory=list)
    error_message: str = ""
    rollback_version_id: Optional[str] = None  # 可用于回滚本次操作的版本ID

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "version_id": self.version_id,
            "target_version_id": self.target_version_id,
            "new_version_id": self.new_version_id,
            "executed_sql": self.executed_sql,
            "error_message": self.error_message,
            "rollback_version_id": self.rollback_version_id,
        }


class MetadataRollbackService:
    """元数据版本回滚服务"""

    def __init__(self, db_session: Session = None):
        self.db_session = db_session

    def preview_rollback(
        self,
        table_id: str,
        target_version_id: str,
    ) -> RollbackPlan:
        """
        预览回滚操作

        Args:
            table_id: 表 ID
            target_version_id: 目标版本 ID

        Returns:
            回滚计划
        """
        try:
            # 获取当前版本的元数据
            current_meta = self._get_current_metadata(table_id)
            if not current_meta:
                raise ValueError(f"表元数据不存在: {table_id}")

            # 获取目标版本
            target_version = self._get_version_by_id(target_version_id)
            if not target_version:
                raise ValueError(f"目标版本不存在: {target_version_id}")

            if target_version.get("table_id") != table_id:
                raise ValueError(f"版本不属于此表: {target_version_id}")

            target_schema = target_version.get("schema_snapshot", {})

            # 生成回滚计划
            plan = RollbackPlan(
                version_id=current_meta.get("version_id", ""),
                target_version_id=target_version_id,
                table_name=current_meta.get("table_name", ""),
                database_name=current_meta.get("database_name", ""),
            )

            # 分析差异并生成动作
            actions = self._generate_rollback_actions(current_meta, target_schema)
            plan.actions = actions

            # 生成 SQL 语句
            plan.sql_statements = self._generate_rollback_sql(
                current_meta, target_schema, actions
            )

            # 生成警告
            plan.warnings = self._generate_rollback_warnings(actions)

            # 判断是否需要数据备份
            plan.requires_data_backup = any(
                a.get("action") in ["drop_column", "modify_column"]
                for a in actions
            )

            # 估算执行时间
            plan.estimated_duration_seconds = len(plan.sql_statements) * 5

            return plan

        except Exception as e:
            logger.error(f"预览回滚失败: {e}")
            raise

    def execute_rollback(
        self,
        table_id: str,
        target_version_id: str,
        create_backup: bool = True,
        execute_on_database: bool = False,
        changed_by: str = "system",
    ) -> RollbackResult:
        """
        执行回滚操作

        Args:
            table_id: 表 ID
            target_version_id: 目标版本 ID
            create_backup: 是否创建备份
            execute_on_database: 是否在数据库上执行（默认只更新元数据）
            changed_by: 操作人

        Returns:
            回滚结果
        """
        result = RollbackResult(
            success=False,
            version_id=table_id,
            target_version_id=target_version_id,
        )

        try:
            # 预览回滚
            plan = self.preview_rollback(table_id, target_version_id)

            # 创建备份（如果需要）
            backup_version_id = None
            if create_backup:
                backup_version_id = self._create_backup_version(table_id)

            # 在数据库上执行 SQL（如果启用）
            executed_sql = []
            if execute_on_database:
                executed_sql = self._execute_sql_on_database(
                    table_id, plan.sql_statements
                )
                if not executed_sql:
                    result.error_message = "数据库 SQL 执行失败"
                    return result

            # 更新元数据
            success = self._apply_metadata_rollback(
                table_id, target_version_id, changed_by
            )

            if success:
                result.success = True
                result.executed_sql = executed_sql if execute_on_database else plan.sql_statements
                result.rollback_version_id = backup_version_id

                # 创建新版本记录
                new_version_id = self._create_rollback_version(
                    table_id, target_version_id, plan, changed_by
                )
                result.new_version_id = new_version_id

                logger.info(f"回滚成功: {table_id} -> {target_version_id}")
            else:
                result.error_message = "元数据更新失败"

        except Exception as e:
            logger.error(f"执行回滚失败: {e}")
            result.error_message = str(e)

        return result

    def generate_migration_script(
        self,
        table_id: str,
        from_version_id: str,
        to_version_id: str,
        dialect: str = "mysql",
    ) -> Dict[str, Any]:
        """
        生成迁移 SQL 脚本

        Args:
            table_id: 表 ID
            from_version_id: 源版本 ID
            to_version_id: 目标版本 ID
            dialect: SQL 方言 (mysql, postgresql, oracle, sqlserver)

        Returns:
            迁移脚本
        """
        try:
            from_version = self._get_version_by_id(from_version_id)
            to_version = self._get_version_by_id(to_version_id)

            if not from_version or not to_version:
                return {"error": "版本不存在"}

            from_schema = from_version.get("schema_snapshot", {})
            to_schema = to_version.get("schema_snapshot", {})

            # 生成迁移脚本
            script = self._generate_migration_sql(
                from_schema, to_schema, dialect
            )

            return {
                "from_version": from_version_id,
                "to_version": to_version_id,
                "dialect": dialect,
                "script": script,
                "statement_count": len(script),
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"生成迁移脚本失败: {e}")
            return {"error": str(e)}

    # ==================== 私有方法 ====================

    def _get_current_metadata(self, table_id: str) -> Optional[Dict[str, Any]]:
        """获取当前元数据"""
        try:
            if self.db_session:
                from models.metadata import MetadataTable
                table = self.db_session.query(MetadataTable).filter(
                    MetadataTable.id == table_id
                ).first()
                if table:
                    return table.to_dict()
            return None
        except Exception as e:
            logger.error(f"获取当前元数据失败: {e}")
            return None

    def _get_version_by_id(self, version_id: str) -> Optional[Dict[str, Any]]:
        """获取版本记录"""
        try:
            if self.db_session:
                from models.metadata_version import MetadataVersionModel
                version = self.db_session.query(MetadataVersionModel).filter(
                    MetadataVersionModel.id == version_id
                ).first()
                if version:
                    return version.to_dict()
            return None
        except Exception as e:
            logger.error(f"获取版本记录失败: {e}")
            return None

    def _generate_rollback_actions(
        self,
        current_meta: Dict[str, Any],
        target_schema: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成回滚动作列表"""
        actions = []
        table_name = current_meta.get("table_name", "")

        current_columns = {c.get("name"): c for c in current_meta.get("columns", [])}
        target_columns = {c.get("name"): c for c in target_schema.get("columns", [])}

        # 检测需要删除的列（当前有，目标没有）
        for col_name in set(current_columns.keys()) - set(target_columns.keys()):
            actions.append({
                "action": RollbackAction.DROP_COLUMN.value,
                "table": table_name,
                "column": col_name,
                "description": f"删除列 {col_name}",
                "risk": "high",
            })

        # 检测需要新增的列（目标有，当前没有）
        for col_name in set(target_columns.keys()) - set(current_columns.keys()):
            target_col = target_columns[col_name]
            actions.append({
                "action": RollbackAction.ADD_COLUMN.value,
                "table": table_name,
                "column": col_name,
                "column_type": target_col.get("type", "VARCHAR(255)"),
                "nullable": target_col.get("nullable", True),
                "default": target_col.get("default_value"),
                "description": f"新增列 {col_name}",
                "risk": "low",
            })

        # 检测需要修改的列
        for col_name in set(current_columns.keys()) & set(target_columns.keys()):
            current_col = current_columns[col_name]
            target_col = target_columns[col_name]

            # 检查类型变更
            if current_col.get("type") != target_col.get("type"):
                actions.append({
                    "action": RollbackAction.MODIFY_COLUMN.value,
                    "table": table_name,
                    "column": col_name,
                    "change_type": "type",
                    "from": current_col.get("type"),
                    "to": target_col.get("type"),
                    "description": f"修改列 {col_name} 类型",
                    "risk": "medium",
                })

            # 检查可空性变更
            if current_col.get("nullable") != target_col.get("nullable"):
                actions.append({
                    "action": RollbackAction.MODIFY_COLUMN.value,
                    "table": table_name,
                    "column": col_name,
                    "change_type": "nullable",
                    "from": current_col.get("nullable"),
                    "to": target_col.get("nullable"),
                    "description": f"修改列 {col_name} 可空性",
                    "risk": "medium",
                })

            # 检查默认值变更
            if current_col.get("default_value") != target_col.get("default_value"):
                actions.append({
                    "action": RollbackAction.MODIFY_COLUMN.value,
                    "table": table_name,
                    "column": col_name,
                    "change_type": "default",
                    "from": current_col.get("default_value"),
                    "to": target_col.get("default_value"),
                    "description": f"修改列 {col_name} 默认值",
                    "risk": "low",
                })

        # 元数据恢复动作
        if current_meta.get("description") != target_schema.get("description"):
            actions.append({
                "action": RollbackAction.RESTORE_METADATA.value,
                "field": "description",
                "description": "恢复表描述",
                "risk": "low",
            })

        if set(current_meta.get("tags", [])) != set(target_schema.get("tags", [])):
            actions.append({
                "action": RollbackAction.RESTORE_METADATA.value,
                "field": "tags",
                "description": "恢复表标签",
                "risk": "low",
            })

        return actions

    def _generate_rollback_sql(
        self,
        current_meta: Dict[str, Any],
        target_schema: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> List[str]:
        """生成回滚 SQL 语句"""
        sql_statements = []
        table_name = current_meta.get("table_name", "")
        target_columns = {c.get("name"): c for c in target_schema.get("columns", [])}

        for action in actions:
            if action["action"] == RollbackAction.DROP_COLUMN.value:
                col = action["column"]
                sql_statements.append(
                    f"ALTER TABLE `{table_name}` DROP COLUMN `{col}`;"
                )

            elif action["action"] == RollbackAction.ADD_COLUMN.value:
                col = action["column"]
                col_type = action.get("column_type", "VARCHAR(255)")
                nullable = "" if action.get("nullable", True) else "NOT NULL"
                default = f"DEFAULT {action['default']}" if action.get("default") else ""
                sql_statements.append(
                    f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {col_type} {nullable} {default};"
                )

            elif action["action"] == RollbackAction.MODIFY_COLUMN.value:
                col = action["column"]
                change_type = action.get("change_type")

                if change_type == "type":
                    sql_statements.append(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` {action['to']};"
                    )
                elif change_type == "nullable":
                    nullable = "NULL" if action["to"] else "NOT NULL"
                    sql_statements.append(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` {nullable};"
                    )
                elif change_type == "default":
                    default = f"DEFAULT {action['to']}" if action["to"] else "DROP DEFAULT"
                    sql_statements.append(
                        f"ALTER TABLE `{table_name}` ALTER COLUMN `{col}` {default};"
                    )

        return sql_statements

    def _generate_rollback_warnings(self, actions: List[Dict[str, Any]]) -> List[str]:
        """生成回滚警告"""
        warnings = []

        high_risk_actions = [a for a in actions if a.get("risk") == "high"]
        if high_risk_actions:
            warnings.append(
                f"检测到 {len(high_risk_actions)} 个高风险操作，请确保已备份数据"
            )

        drop_columns = [a["column"] for a in actions if a["action"] == "drop_column"]
        if drop_columns:
            warnings.append(
                f"将删除以下列: {', '.join(drop_columns)}，这些列的数据将永久丢失"
            )

        type_changes = [
            a for a in actions
            if a["action"] == "modify_column" and a.get("change_type") == "type"
        ]
        if type_changes:
            warnings.append(
                f"将修改 {len(type_changes)} 个列的数据类型，可能导致数据转换错误"
            )

        return warnings

    def _create_backup_version(self, table_id: str) -> Optional[str]:
        """创建当前状态的备份版本"""
        try:
            import uuid
            from models.metadata_version import MetadataVersionModel

            current_meta = self._get_current_metadata(table_id)
            if not current_meta:
                return None

            backup_id = str(uuid.uuid4())
            backup = MetadataVersionModel(
                id=backup_id,
                table_id=table_id,
                change_type="backup",
                change_summary="回滚前自动备份",
                schema_snapshot=current_meta,
                changed_by="system",
                created_at=datetime.utcnow(),
            )

            self.db_session.add(backup)
            self.db_session.commit()

            return backup_id

        except Exception as e:
            logger.error(f"创建备份版本失败: {e}")
            return None

    def _apply_metadata_rollback(
        self,
        table_id: str,
        target_version_id: str,
        changed_by: str,
    ) -> bool:
        """应用元数据回滚"""
        try:
            target_version = self._get_version_by_id(target_version_id)
            if not target_version:
                return False

            target_schema = target_version.get("schema_snapshot", {})

            # 更新表元数据
            if self.db_session:
                from models.metadata import MetadataTable, MetadataColumn

                table = self.db_session.query(MetadataTable).filter(
                    MetadataTable.id == table_id
                ).first()

                if table:
                    # 更新表级属性
                    if "description" in target_schema:
                        table.description = target_schema["description"]
                    if "tags" in target_schema:
                        table.tags = target_schema["tags"]
                    table.updated_at = datetime.utcnow()

                    # 更新列
                    target_columns = target_schema.get("columns", [])
                    for col_data in target_columns:
                        col_name = col_data.get("name")
                        column = self.db_session.query(MetadataColumn).filter(
                            MetadataColumn.table_id == table_id,
                            MetadataColumn.column_name == col_name,
                        ).first()

                        if column:
                            # 更新现有列
                            if "description" in col_data:
                                column.ai_description = col_data.get("description", "")
                            if "sensitivity_level" in col_data:
                                column.sensitivity_level = col_data.get("sensitivity_level", "")
                            if "semantic_tags" in col_data:
                                column.semantic_tags = col_data.get("semantic_tags", [])

                    self.db_session.commit()
                    return True

            return False

        except Exception as e:
            logger.error(f"应用元数据回滚失败: {e}")
            if self.db_session:
                self.db_session.rollback()
            return False

    def _create_rollback_version(
        self,
        table_id: str,
        target_version_id: str,
        plan: RollbackPlan,
        changed_by: str,
    ) -> Optional[str]:
        """创建回滚版本记录"""
        try:
            import uuid
            from models.metadata_version import MetadataVersionModel

            version_id = str(uuid.uuid4())
            version = MetadataVersionModel(
                id=version_id,
                table_id=table_id,
                change_type="rollback",
                change_summary=f"回滚到版本 {target_version_id}",
                change_details={
                    "target_version_id": target_version_id,
                    "actions_count": len(plan.actions),
                    "sql_count": len(plan.sql_statements),
                },
                schema_snapshot=plan.actions,  # 存储执行的动作
                changed_by=changed_by,
                created_at=datetime.utcnow(),
            )

            self.db_session.add(version)
            self.db_session.commit()

            return version_id

        except Exception as e:
            logger.error(f"创建回滚版本失败: {e}")
            return None

    def _execute_sql_on_database(
        self,
        table_id: str,
        sql_statements: List[str],
    ) -> List[str]:
        """在数据库上执行 SQL（需要数据源连接）"""
        try:
            # 获取数据源连接
            current_meta = self._get_current_metadata(table_id)
            if not current_meta:
                return []

            # 这里需要实际的数据源连接逻辑
            # 简化实现：返回 SQL 列表表示"将要执行"
            logger.info(f"准备执行 {len(sql_statements)} 条 SQL 语句")
            return sql_statements

        except Exception as e:
            logger.error(f"执行 SQL 失败: {e}")
            return []

    def _generate_migration_sql(
        self,
        from_schema: Dict[str, Any],
        to_schema: Dict[str, Any],
        dialect: str,
    ) -> List[str]:
        """生成迁移 SQL"""
        sql_statements = []
        table_name = to_schema.get("table_name", "")

        # 根据方言调整语法
        quote_char = "`" if dialect in ["mysql"] else '"'

        from_columns = {c.get("name"): c for c in from_schema.get("columns", [])}
        to_columns = {c.get("name"): c for c in to_schema.get("columns", [])}

        # 新增列
        for col_name in set(to_columns.keys()) - set(from_columns.keys()):
            col = to_columns[col_name]
            col_def = self._format_column_definition(col, dialect)
            sql_statements.append(
                f"ALTER TABLE {quote_char}{table_name}{quote_char} ADD COLUMN {quote_char}{col_name}{quote_char} {col_def};"
            )

        # 删除列
        for col_name in set(from_columns.keys()) - set(to_columns.keys()):
            sql_statements.append(
                f"ALTER TABLE {quote_char}{table_name}{quote_char} DROP COLUMN {quote_char}{col_name}{quote_char};"
            )

        # 修改列
        for col_name in set(from_columns.keys()) & set(to_columns.keys()):
            from_col = from_columns[col_name]
            to_col = to_columns[col_name]

            if from_col.get("type") != to_col.get("type"):
                if dialect == "mysql":
                    sql_statements.append(
                        f"ALTER TABLE {quote_char}{table_name}{quote_char} MODIFY COLUMN {quote_char}{col_name}{quote_char} {to_col.get('type')};"
                    )
                elif dialect == "postgresql":
                    sql_statements.append(
                        f"ALTER TABLE {quote_char}{table_name}{quote_char} ALTER COLUMN {quote_char}{col_name}{quote_char} TYPE {to_col.get('type')};"
                    )

        return sql_statements

    def _format_column_definition(self, column: Dict, dialect: str) -> str:
        """格式化列定义"""
        parts = [column.get("type", "VARCHAR(255)")]

        if not column.get("nullable", True):
            parts.append("NOT NULL")

        if column.get("default_value"):
            parts.append(f"DEFAULT {column['default_value']}")

        if column.get("auto_increment"):
            parts.append("AUTO_INCREMENT")

        return " ".join(parts)


# 创建全局实例
_rollback_service = None


def get_metadata_rollback_service(db_session: Session = None) -> MetadataRollbackService:
    """获取元数据回滚服务实例"""
    global _rollback_service
    if _rollback_service is None or db_session is not None:
        _rollback_service = MetadataRollbackService(db_session)
    return _rollback_service
