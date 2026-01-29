"""
元数据版本差异对比服务
支持表结构版本管理和差异对比
持久化到 MySQL 数据库
"""

import logging
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ==================== 变更类型定义 ====================

class ChangeType(str, Enum):
    """变更类型"""
    ADDED = "added"           # 新增
    REMOVED = "removed"       # 删除
    MODIFIED = "modified"     # 修改
    UNCHANGED = "unchanged"   # 未变化


class MetadataType(str, Enum):
    """元数据类型"""
    TABLE = "table"           # 表
    COLUMN = "column"         # 列
    INDEX = "index"           # 索引
    RELATION = "relation"     # 关系
    CONSTRAINT = "constraint" # 约束


# ==================== 变更记录 ====================

@dataclass
class FieldChange:
    """字段变更记录"""
    change_type: ChangeType
    field_name: str
    old_value: Any
    new_value: Any

    def to_dict(self) -> Dict:
        return {
            "change_type": self.change_type.value,
            "field_name": self.field_name,
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
        }


@dataclass
class ColumnDiff:
    """列差异对比结果"""
    column_name: str
    changes: List[FieldChange]
    has_changes: bool

    def to_dict(self) -> Dict:
        return {
            "column_name": self.column_name,
            "changes": [c.to_dict() for c in self.changes],
            "has_changes": self.has_changes,
        }


@dataclass
class TableDiff:
    """表差异对比结果"""
    table_name: str
    added_columns: List[str]
    removed_columns: List[str]
    modified_columns: List[ColumnDiff]
    unchanged_columns: List[str]
    summary: str

    def to_dict(self) -> Dict:
        return {
            "table_name": self.table_name,
            "added_columns": self.added_columns,
            "removed_columns": self.removed_columns,
            "modified_columns": [c.to_dict() for c in self.modified_columns],
            "unchanged_columns": self.unchanged_columns,
            "summary": self.summary,
        }


# ==================== 元数据版本 ====================

@dataclass
class ColumnVersion:
    """列版本信息"""
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default_value: Any = None
    comment: str = ""
    max_length: int = None
    decimal_places: int = None
    auto_increment: bool = False

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "default_value": str(self.default_value) if self.default_value is not None else None,
            "comment": self.comment,
            "max_length": self.max_length,
            "decimal_places": self.decimal_places,
            "auto_increment": self.auto_increment,
        }

    def __eq__(self, other) -> bool:
        if not isinstance(other, ColumnVersion):
            return False
        return (
            self.name == other.name and
            self.type == other.type and
            self.nullable == other.nullable and
            self.primary_key == other.primary_key and
            self.default_value == other.default_value and
            self.comment == other.comment
        )


@dataclass
class TableVersion:
    """表版本信息"""
    table_name: str
    database: str
    columns: Dict[str, ColumnVersion]
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    comment: str = ""
    engine: str = ""
    charset: str = ""
    collation: str = ""

    def get_column_names(self) -> List[str]:
        """获取所有列名"""
        return list(self.columns.keys())

    def to_dict(self) -> Dict:
        return {
            "table_name": self.table_name,
            "database": self.database,
            "columns": {k: v.to_dict() for k, v in self.columns.items()},
            "indexes": self.indexes,
            "relations": self.relations,
            "row_count": self.row_count,
            "comment": self.comment,
            "engine": self.engine,
            "charset": self.charset,
            "collation": self.collation,
        }


@dataclass
class MetadataSnapshot:
    """元数据快照"""
    snapshot_id: str
    version: str
    database: str
    tables: Dict[str, TableVersion]
    created_at: datetime
    created_by: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        return list(self.tables.keys())

    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "version": self.version,
            "database": self.database,
            "tables": {k: v.to_dict() for k, v in self.tables.items()},
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "tags": self.tags,
        }


# ==================== 序列化辅助 ====================

def _tables_to_json(tables: Dict[str, TableVersion]) -> Dict[str, Any]:
    """将 TableVersion 字典序列化为 JSON 可存储格式"""
    return {k: v.to_dict() for k, v in tables.items()}


def _tables_from_json(data: Dict[str, Any]) -> Dict[str, TableVersion]:
    """从 JSON 反序列化为 TableVersion 字典"""
    tables = {}
    for table_name, table_data in (data or {}).items():
        columns = {}
        for col_name, col_data in table_data.get("columns", {}).items():
            columns[col_name] = ColumnVersion(
                name=col_data.get("name", col_name),
                type=col_data.get("type", "VARCHAR(255)"),
                nullable=col_data.get("nullable", True),
                primary_key=col_data.get("primary_key", False),
                default_value=col_data.get("default_value"),
                comment=col_data.get("comment", ""),
                max_length=col_data.get("max_length"),
                decimal_places=col_data.get("decimal_places"),
                auto_increment=col_data.get("auto_increment", False),
            )
        tables[table_name] = TableVersion(
            table_name=table_data.get("table_name", table_name),
            database=table_data.get("database", ""),
            columns=columns,
            indexes=table_data.get("indexes", []),
            relations=table_data.get("relations", []),
            row_count=table_data.get("row_count", 0),
            comment=table_data.get("comment", ""),
            engine=table_data.get("engine", ""),
            charset=table_data.get("charset", ""),
            collation=table_data.get("collation", ""),
        )
    return tables


def _snapshot_from_model(model) -> MetadataSnapshot:
    """从 ORM 模型转换为 MetadataSnapshot dataclass"""
    return MetadataSnapshot(
        snapshot_id=model.id,
        version=model.version,
        database=model.database,
        tables=_tables_from_json(model.tables_snapshot),
        created_at=model.created_at,
        created_by=model.created_by or "",
        description=model.description or "",
        tags=model.tags or [],
    )


# ==================== 版本对比服务 ====================

class MetadataVersionService:
    """元数据版本对比服务 - 使用数据库持久化"""

    def __init__(self, db_session_factory=None):
        self._db_session_factory = db_session_factory

    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self._db_session_factory:
            return self._db_session_factory()
        from models import get_db
        return next(get_db())

    # ==================== 快照管理 ====================

    def create_snapshot(
        self,
        version: str,
        database: str,
        tables: Dict[str, TableVersion],
        created_by: str = "",
        description: str = "",
        tags: List[str] = None,
    ) -> MetadataSnapshot:
        """创建元数据快照"""
        from models.metadata_version import MetadataSnapshotModel

        snapshot_id = f"snap_{secrets.token_hex(8)}"
        now = datetime.utcnow()

        db = self._get_db()
        try:
            model = MetadataSnapshotModel(
                id=snapshot_id,
                version=version,
                database=database,
                tables_snapshot=_tables_to_json(tables),
                created_by=created_by,
                description=description,
                tags=tags or [],
                created_at=now,
            )
            db.add(model)
            db.commit()

            return MetadataSnapshot(
                snapshot_id=snapshot_id,
                version=version,
                database=database,
                tables=tables,
                created_at=now,
                created_by=created_by,
                description=description,
                tags=tags or [],
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_snapshot(self, snapshot_id: str) -> Optional[MetadataSnapshot]:
        """获取快照"""
        from models.metadata_version import MetadataSnapshotModel

        db = self._get_db()
        try:
            model = db.query(MetadataSnapshotModel).filter(
                MetadataSnapshotModel.id == snapshot_id
            ).first()
            if not model:
                return None
            return _snapshot_from_model(model)
        finally:
            db.close()

    def list_snapshots(
        self,
        database: str = None,
        limit: int = 50,
    ) -> List[MetadataSnapshot]:
        """列出快照"""
        from models.metadata_version import MetadataSnapshotModel

        db = self._get_db()
        try:
            query = db.query(MetadataSnapshotModel)
            if database:
                query = query.filter(MetadataSnapshotModel.database == database)
            query = query.order_by(MetadataSnapshotModel.created_at.desc())
            query = query.limit(limit)

            return [_snapshot_from_model(m) for m in query.all()]
        finally:
            db.close()

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        from models.metadata_version import MetadataSnapshotModel

        db = self._get_db()
        try:
            model = db.query(MetadataSnapshotModel).filter(
                MetadataSnapshotModel.id == snapshot_id
            ).first()
            if not model:
                return False
            db.delete(model)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== 差异对比 ====================

    def compare_snapshots(
        self,
        from_snapshot_id: str,
        to_snapshot_id: str,
    ) -> Dict[str, Any]:
        """
        对比两个快照的差异

        Returns:
            包含以下内容的字典:
            - added_tables: 新增的表
            - removed_tables: 删除的表
            - modified_tables: 有变更的表
            - table_diffs: 每个表的详细差异
        """
        from_snapshot = self.get_snapshot(from_snapshot_id)
        to_snapshot = self.get_snapshot(to_snapshot_id)

        if not from_snapshot or not to_snapshot:
            raise ValueError("快照不存在")

        from_tables = set(from_snapshot.get_table_names())
        to_tables = set(to_snapshot.get_table_names())

        added_tables = to_tables - from_tables
        removed_tables = from_tables - to_tables
        common_tables = from_tables & to_tables

        modified_tables = []
        table_diffs = {}

        for table_name in common_tables:
            diff = self._compare_tables(
                from_snapshot.tables[table_name],
                to_snapshot.tables[table_name],
            )
            table_diffs[table_name] = diff.to_dict()

            if diff.added_columns or diff.removed_columns or diff.modified_columns:
                modified_tables.append(table_name)

        # 为新增表生成差异
        for table_name in added_tables:
            table_diffs[table_name] = {
                "table_name": table_name,
                "added_columns": list(to_snapshot.tables[table_name].columns.keys()),
                "removed_columns": [],
                "modified_columns": [],
                "unchanged_columns": [],
                "summary": "新增表",
                "is_new_table": True,
            }

        # 为删除表生成差异
        for table_name in removed_tables:
            table_diffs[table_name] = {
                "table_name": table_name,
                "added_columns": [],
                "removed_columns": list(from_snapshot.tables[table_name].columns.keys()),
                "modified_columns": [],
                "unchanged_columns": [],
                "summary": "删除表",
                "is_removed_table": True,
            }

        return {
            "from_snapshot": {
                "id": from_snapshot.snapshot_id,
                "version": from_snapshot.version,
                "created_at": from_snapshot.created_at.isoformat(),
            },
            "to_snapshot": {
                "id": to_snapshot.snapshot_id,
                "version": to_snapshot.version,
                "created_at": to_snapshot.created_at.isoformat(),
            },
            "added_tables": list(added_tables),
            "removed_tables": list(removed_tables),
            "modified_tables": modified_tables,
            "unchanged_tables": list(common_tables - set(modified_tables)),
            "table_diffs": table_diffs,
            "summary": self._generate_summary(
                added_tables, removed_tables, modified_tables, table_diffs
            ),
        }

    def _compare_tables(
        self,
        from_table: TableVersion,
        to_table: TableVersion,
    ) -> TableDiff:
        """对比两个表的差异"""
        from_columns = from_table.columns
        to_columns = to_table.columns

        from_col_names = set(from_columns.keys())
        to_col_names = set(to_columns.keys())

        added_columns = list(to_col_names - from_col_names)
        removed_columns = list(from_col_names - to_col_names)
        common_columns = from_col_names & to_col_names

        modified_columns = []
        unchanged_columns = []

        for col_name in common_columns:
            from_col = from_columns[col_name]
            to_col = to_columns[col_name]

            changes = self._compare_columns(from_col, to_col)

            if changes:
                modified_columns.append(ColumnDiff(col_name, changes, True))
            else:
                unchanged_columns.append(col_name)

        # 生成摘要
        summary_parts = []
        if added_columns:
            summary_parts.append(f"+{len(added_columns)}列")
        if removed_columns:
            summary_parts.append(f"-{len(removed_columns)}列")
        if modified_columns:
            summary_parts.append(f"~{len(modified_columns)}列")
        summary = ", ".join(summary_parts) if summary_parts else "无变化"

        return TableDiff(
            table_name=to_table.table_name,
            added_columns=added_columns,
            removed_columns=removed_columns,
            modified_columns=modified_columns,
            unchanged_columns=unchanged_columns,
            summary=summary,
        )

    def _compare_columns(
        self,
        from_col: ColumnVersion,
        to_col: ColumnVersion,
    ) -> List[FieldChange]:
        """对比两个列的差异"""
        changes = []

        # 对比各个字段
        field_mappings = [
            ("type", "类型"),
            ("nullable", "可空"),
            ("primary_key", "主键"),
            ("default_value", "默认值"),
            ("comment", "注释"),
            ("max_length", "长度"),
            ("auto_increment", "自增"),
        ]

        for field, field_name in field_mappings:
            from_value = getattr(from_col, field)
            to_value = getattr(to_col, field)

            if from_value != to_value:
                change_type = ChangeType.MODIFIED
                if to_value is None and from_value is not None:
                    change_type = ChangeType.REMOVED
                elif from_value is None and to_value is not None:
                    change_type = ChangeType.ADDED

                changes.append(FieldChange(
                    change_type=change_type,
                    field_name=field_name,
                    old_value=from_value,
                    new_value=to_value,
                ))

        return changes

    def _generate_summary(
        self,
        added_tables: set,
        removed_tables: set,
        modified_tables: list,
        table_diffs: dict,
    ) -> str:
        """生成差异摘要"""
        parts = []

        if added_tables:
            parts.append(f"新增 {len(added_tables)} 个表")
        if removed_tables:
            parts.append(f"删除 {len(removed_tables)} 个表")
        if modified_tables:
            parts.append(f"修改 {len(modified_tables)} 个表")

        # 统计列变更
        total_added_cols = sum(
            len(d.get("added_columns", [])) for d in table_diffs.values()
        )
        total_removed_cols = sum(
            len(d.get("removed_columns", [])) for d in table_diffs.values()
        )
        total_modified_cols = sum(
            len(d.get("modified_columns", [])) for d in table_diffs.values()
        )

        if total_added_cols or total_removed_cols or total_modified_cols:
            col_parts = []
            if total_added_cols:
                col_parts.append(f"+{total_added_cols}列")
            if total_removed_cols:
                col_parts.append(f"-{total_removed_cols}列")
            if total_modified_cols:
                col_parts.append(f"~{total_modified_cols}列")
            parts.append("列变更: " + ", ".join(col_parts))

        return "; ".join(parts) if parts else "无变化"

    # ==================== SQL 生成 ====================

    def generate_migration_sql(
        self,
        from_snapshot_id: str,
        to_snapshot_id: str,
    ) -> Dict[str, List[str]]:
        """
        生成迁移 SQL

        Returns:
            按表分类的 SQL 语句列表
        """
        diff = self.compare_snapshots(from_snapshot_id, to_snapshot_id)
        sql_statements: Dict[str, List[str]] = {}

        # 获取 to_snapshot 用于新增表
        to_snapshot = self.get_snapshot(to_snapshot_id)

        for table_name, table_diff in diff["table_diffs"].items():
            table_sql = []

            # 新增表
            if table_diff.get("is_new_table"):
                if to_snapshot and table_name in to_snapshot.tables:
                    table_sql.append(self._generate_create_table_sql(to_snapshot.tables[table_name]))

            # 删除表
            elif table_diff.get("is_removed_table"):
                table_sql.append(f"DROP TABLE `{table_name}`;")

            # 修改表
            else:
                # 新增列
                for col in table_diff.get("added_columns", []):
                    table_sql.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` VARCHAR(255);")

                # 删除列
                for col in table_diff.get("removed_columns", []):
                    table_sql.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{col}`;")

                # 修改列
                for col_diff in table_diff.get("modified_columns", []):
                    for change in col_diff.get("changes", []):
                        if change["field_name"] == "类型":
                            table_sql.append(
                                f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_diff['column_name']}` {change['new_value']};"
                            )
                        elif change["field_name"] == "可空":
                            nullable = "NULL" if change["new_value"] else "NOT NULL"
                            table_sql.append(
                                f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_diff['column_name']}` {nullable};"
                            )
                        elif change["field_name"] == "默认值":
                            default = f"DEFAULT {change['new_value']}" if change["new_value"] else "DROP DEFAULT"
                            table_sql.append(
                                f"ALTER TABLE `{table_name}` ALTER COLUMN `{col_diff['column_name']}` {default};"
                            )
                        elif change["field_name"] == "注释":
                            comment = change["new_value"] or ""
                            table_sql.append(
                                f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_diff['column_name']}` COMMENT '{comment}';"
                            )

            if table_sql:
                sql_statements[table_name] = table_sql

        return sql_statements

    def _generate_create_table_sql(self, table: TableVersion) -> str:
        """生成创建表的 SQL"""
        columns_sql = []
        primary_keys = []

        for col_name, col in table.columns.items():
            col_def = f"`{col_name}` {col.type}"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default_value:
                col_def += f" DEFAULT {col.default_value}"
            if col.auto_increment:
                col_def += " AUTO_INCREMENT"
            if col.comment:
                col_def += f" COMMENT '{col.comment}'"
            columns_sql.append(col_def)

            if col.primary_key:
                primary_keys.append(col_name)

        if primary_keys:
            columns_sql.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

        sql = f"CREATE TABLE `{table.table_name}` (\n"
        sql += ",\n".join(f"  {col}" for col in columns_sql)
        sql += f"\n) ENGINE={table.engine} DEFAULT CHARSET={table.charset};"

        return sql

    # ==================== 版本历史 ====================

    def get_version_history(
        self,
        database: str,
        table_name: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取版本历史"""
        snapshots = self.list_snapshots(database=database, limit=limit)

        history = []
        for snapshot in snapshots:
            version_info = {
                "snapshot_id": snapshot.snapshot_id,
                "version": snapshot.version,
                "created_at": snapshot.created_at.isoformat(),
                "created_by": snapshot.created_by,
                "description": snapshot.description,
                "table_count": len(snapshot.tables),
            }

            if table_name:
                version_info["table_exists"] = table_name in snapshot.tables
                if table_name in snapshot.tables:
                    version_info["column_count"] = len(snapshot.tables[table_name].columns)

            history.append(version_info)

        return history


# 创建全局服务实例
_version_service = None


def get_metadata_version_service() -> MetadataVersionService:
    """获取元数据版本服务实例"""
    global _version_service
    if _version_service is None:
        _version_service = MetadataVersionService()
    return _version_service
