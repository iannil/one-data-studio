"""
元数据版本差异对比服务
支持表结构版本管理和差异对比
"""

import logging
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
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


# ==================== 版本对比服务 ====================

class MetadataVersionService:
    """元数据版本对比服务"""

    def __init__(self):
        # 内存存储，实际应使用数据库
        self._snapshots: Dict[str, MetadataSnapshot] = {}

        # 初始化示例数据
        self._init_sample_data()

    def _init_sample_data(self):
        """初始化示例数据"""
        # 创建 v1 版本
        users_columns_v1 = {
            "id": ColumnVersion("id", "INT", False, True),
            "username": ColumnVersion("username", "VARCHAR(50)", False, False),
            "email": ColumnVersion("email", "VARCHAR(100)", False, False),
            "created_at": ColumnVersion("created_at", "TIMESTAMP", True, False),
        }
        orders_columns_v1 = {
            "id": ColumnVersion("id", "INT", False, True),
            "user_id": ColumnVersion("user_id", "INT", False, False),
            "total": ColumnVersion("total", "DECIMAL(10,2)", False, False, comment="订单总额"),
            "status": ColumnVersion("status", "VARCHAR(20)", False, False),
        }

        snapshot_v1 = MetadataSnapshot(
            snapshot_id="snap_v1",
            version="1.0.0",
            database="business_db",
            tables={
                "users": TableVersion("users", "business_db", users_columns_v1),
                "orders": TableVersion("orders", "business_db", orders_columns_v1),
            },
            created_at=datetime.now() - timedelta(days=30),
            created_by="system",
            description="初始版本",
        )

        # 创建 v2 版本（有变更）
        users_columns_v2 = {
            "id": ColumnVersion("id", "INT", False, True),
            "username": ColumnVersion("username", "VARCHAR(50)", False, False, comment="用户名"),  # 新增注释
            "email": ColumnVersion("email", "VARCHAR(100)", True, False),  # 改为可空
            "phone": ColumnVersion("phone", "VARCHAR(20)", True, False),  # 新增字段
            "created_at": ColumnVersion("created_at", "TIMESTAMP", True, False),
            "updated_at": ColumnVersion("updated_at", "TIMESTAMP", True, False),  # 新增字段
        }
        orders_columns_v2 = {
            "id": ColumnVersion("id", "INT", False, True),
            "user_id": ColumnVersion("user_id", "INT", False, False),
            "total": ColumnVersion("total", "DECIMAL(12,2)", False, False, comment="订单含税总额"),  # 类型变更
            "status": ColumnVersion("status", "VARCHAR(20)", False, False),
            "discount": ColumnVersion("discount", "DECIMAL(5,2)", True, None, comment="折扣金额"),  # 新增
        }
        products_columns_v2 = {  # 新表
            "id": ColumnVersion("id", "INT", False, True),
            "name": ColumnVersion("name", "VARCHAR(100)", False, False),
            "price": ColumnVersion("price", "DECIMAL(10,2)", False, False),
            "stock": ColumnVersion("stock", "INT", False, None, default_value=0),
        }

        snapshot_v2 = MetadataSnapshot(
            snapshot_id="snap_v2",
            version="1.1.0",
            database="business_db",
            tables={
                "users": TableVersion("users", "business_db", users_columns_v2),
                "orders": TableVersion("orders", "business_db", orders_columns_v2),
                "products": TableVersion("products", "business_db", products_columns_v2),
            },
            created_at=datetime.now() - timedelta(days=15),
            created_by="admin",
            description="新增电话和更新时间字段，新增产品表",
        )

        self._snapshots[snapshot_v1.snapshot_id] = snapshot_v1
        self._snapshots[snapshot_v2.snapshot_id] = snapshot_v2

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
        snapshot = MetadataSnapshot(
            snapshot_id=f"snap_{secrets.token_hex(8)}",
            version=version,
            database=database,
            tables=tables,
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
            tags=tags or [],
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[MetadataSnapshot]:
        """获取快照"""
        return self._snapshots.get(snapshot_id)

    def list_snapshots(
        self,
        database: str = None,
        limit: int = 50,
    ) -> List[MetadataSnapshot]:
        """列出快照"""
        snapshots = list(self._snapshots.values())

        if database:
            snapshots = [s for s in snapshots if s.database == database]

        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots[:limit]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False

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
        from_snapshot = self._snapshots.get(from_snapshot_id)
        to_snapshot = self._snapshots.get(to_snapshot_id)

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

        for table_name, table_diff in diff["table_diffs"].items():
            table_sql = []

            # 新增表
            if table_diff.get("is_new_table"):
                to_snapshot = self._snapshots.get(to_snapshot_id)
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
