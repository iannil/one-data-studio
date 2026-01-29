"""
元数据版本模型
Phase 3 P2: 元数据版本历史跟踪

用于记录元数据的变更历史，支持：
- 版本追踪
- 变更审计
- 版本回滚
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum


# 尝试从现有模型导入 Base
try:
    from . import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class MetadataChangeType(str, Enum):
    """元数据变更类型"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    SCHEMA_CHANGED = "schema_changed"
    STATS_UPDATED = "stats_updated"
    AI_ANNOTATED = "ai_annotated"
    ETL_SYNCED = "etl_synced"
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_MODIFIED = "column_modified"
    TAG_CHANGED = "tag_changed"
    OWNER_CHANGED = "owner_changed"


class MetadataSnapshotModel(Base):
    """元数据快照模型 - 用于版本对比服务的持久化存储"""

    __tablename__ = "metadata_snapshots"

    # 主键
    id = Column(String(36), primary_key=True)

    # 快照版本号
    version = Column(String(50), nullable=False, index=True)

    # 数据库名
    database = Column(String(200), nullable=False, index=True)

    # 表结构快照 (JSON) - 包含完整的 tables 结构
    tables_snapshot = Column(JSON, default=dict)

    # 创建者
    created_by = Column(String(100), default="system")

    # 描述
    description = Column(Text, default="")

    # 标签 (JSON 数组)
    tags = Column(JSON, default=list)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 租户 ID（多租户支持）
    tenant_id = Column(String(36), nullable=True, index=True)

    def __repr__(self):
        return f"<MetadataSnapshot {self.id} version={self.version} db={self.database}>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "snapshot_id": self.id,
            "version": self.version,
            "database": self.database,
            "tables": self.tables_snapshot or {},
            "created_by": self.created_by,
            "description": self.description,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tenant_id": self.tenant_id,
        }


class MetadataVersionModel(Base):
    """元数据版本模型"""

    __tablename__ = "metadata_versions"

    # 主键
    id = Column(String(36), primary_key=True)

    # 关联的表 ID
    table_id = Column(String(36), ForeignKey("metadata_tables.id"), nullable=False, index=True)

    # 变更类型
    change_type = Column(String(50), nullable=False, index=True)

    # 变更摘要
    change_summary = Column(String(500))

    # 变更详情 (JSON)
    change_details = Column(JSON, default=dict)

    # Schema 快照 (JSON) - 用于回滚
    schema_snapshot = Column(JSON, default=dict)

    # 前一个版本 ID
    previous_version_id = Column(String(36), ForeignKey("metadata_versions.id"), nullable=True)

    # 变更人
    changed_by = Column(String(100), default="system")

    # 变更来源 (etl, api, manual, scheduled)
    change_source = Column(String(50), default="api")

    # 版本号（自增，按表分组）
    version_number = Column(Integer, default=1)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 租户 ID（多租户支持）
    tenant_id = Column(String(36), nullable=True, index=True)

    # 关联
    # table = relationship("MetadataTable", back_populates="versions")

    def __repr__(self):
        return f"<MetadataVersion {self.id} table={self.table_id} type={self.change_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "table_id": self.table_id,
            "change_type": self.change_type,
            "change_summary": self.change_summary,
            "change_details": self.change_details or {},
            "schema_snapshot": self.schema_snapshot or {},
            "previous_version_id": self.previous_version_id,
            "changed_by": self.changed_by,
            "change_source": self.change_source,
            "version_number": self.version_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def create(
        cls,
        table_id: str,
        change_type: MetadataChangeType,
        change_summary: str = "",
        change_details: Dict[str, Any] = None,
        schema_snapshot: Dict[str, Any] = None,
        changed_by: str = "system",
        change_source: str = "api",
        previous_version_id: str = None,
        tenant_id: str = None,
    ) -> "MetadataVersionModel":
        """
        创建新版本记录

        Args:
            table_id: 表 ID
            change_type: 变更类型
            change_summary: 变更摘要
            change_details: 变更详情
            schema_snapshot: Schema 快照
            changed_by: 变更人
            change_source: 变更来源
            previous_version_id: 前一版本 ID
            tenant_id: 租户 ID

        Returns:
            新版本实例
        """
        import uuid

        return cls(
            id=str(uuid.uuid4()),
            table_id=table_id,
            change_type=change_type.value if isinstance(change_type, MetadataChangeType) else change_type,
            change_summary=change_summary,
            change_details=change_details or {},
            schema_snapshot=schema_snapshot or {},
            changed_by=changed_by,
            change_source=change_source,
            previous_version_id=previous_version_id,
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
        )


class ColumnVersionModel(Base):
    """列版本模型（细粒度追踪列级变更）"""

    __tablename__ = "metadata_column_versions"

    # 主键
    id = Column(String(36), primary_key=True)

    # 关联的版本 ID
    version_id = Column(String(36), ForeignKey("metadata_versions.id"), nullable=False, index=True)

    # 列 ID
    column_id = Column(String(36), ForeignKey("metadata_columns.id"), nullable=True, index=True)

    # 列名
    column_name = Column(String(200), nullable=False)

    # 变更类型
    change_type = Column(String(50), nullable=False)

    # 变更前值 (JSON)
    before_value = Column(JSON, default=dict)

    # 变更后值 (JSON)
    after_value = Column(JSON, default=dict)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ColumnVersion {self.id} column={self.column_name} type={self.change_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "version_id": self.version_id,
            "column_id": self.column_id,
            "column_name": self.column_name,
            "change_type": self.change_type,
            "before_value": self.before_value or {},
            "after_value": self.after_value or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# 辅助函数
def get_latest_version(db_session, table_id: str) -> Optional[MetadataVersionModel]:
    """
    获取表的最新版本

    Args:
        db_session: 数据库会话
        table_id: 表 ID

    Returns:
        最新版本或 None
    """
    return db_session.query(MetadataVersionModel).filter(
        MetadataVersionModel.table_id == table_id
    ).order_by(
        MetadataVersionModel.created_at.desc()
    ).first()


def get_version_count(db_session, table_id: str) -> int:
    """
    获取表的版本数量

    Args:
        db_session: 数据库会话
        table_id: 表 ID

    Returns:
        版本数量
    """
    return db_session.query(MetadataVersionModel).filter(
        MetadataVersionModel.table_id == table_id
    ).count()


def get_versions_by_type(
    db_session,
    table_id: str,
    change_type: MetadataChangeType,
    limit: int = 10,
) -> list:
    """
    按变更类型获取版本

    Args:
        db_session: 数据库会话
        table_id: 表 ID
        change_type: 变更类型
        limit: 返回数量

    Returns:
        版本列表
    """
    return db_session.query(MetadataVersionModel).filter(
        MetadataVersionModel.table_id == table_id,
        MetadataVersionModel.change_type == change_type.value,
    ).order_by(
        MetadataVersionModel.created_at.desc()
    ).limit(limit).all()


def create_version_from_diff(
    db_session,
    table_id: str,
    old_meta: Dict[str, Any],
    new_meta: Dict[str, Any],
    changed_by: str = "system",
    change_source: str = "api",
) -> Optional[MetadataVersionModel]:
    """
    从元数据差异创建版本

    Args:
        db_session: 数据库会话
        table_id: 表 ID
        old_meta: 旧元数据
        new_meta: 新元数据
        changed_by: 变更人
        change_source: 变更来源

    Returns:
        新版本或 None
    """
    import uuid

    # 检测变更
    changes = []
    change_details = {}

    # 比较列
    old_cols = {c.get("name"): c for c in old_meta.get("columns", [])}
    new_cols = {c.get("name"): c for c in new_meta.get("columns", [])}

    added_cols = set(new_cols.keys()) - set(old_cols.keys())
    removed_cols = set(old_cols.keys()) - set(new_cols.keys())
    modified_cols = []

    for name in set(old_cols.keys()) & set(new_cols.keys()):
        if old_cols[name] != new_cols[name]:
            modified_cols.append(name)

    if added_cols:
        changes.append(f"新增 {len(added_cols)} 列")
        change_details["columns_added"] = list(added_cols)

    if removed_cols:
        changes.append(f"删除 {len(removed_cols)} 列")
        change_details["columns_removed"] = list(removed_cols)

    if modified_cols:
        changes.append(f"修改 {len(modified_cols)} 列")
        change_details["columns_modified"] = modified_cols

    # 比较其他属性
    for key in ["description", "tags", "owner"]:
        if old_meta.get(key) != new_meta.get(key):
            changes.append(f"{key} 变更")
            change_details[f"{key}_changed"] = {
                "before": old_meta.get(key),
                "after": new_meta.get(key),
            }

    if not changes:
        return None

    # 确定变更类型
    if added_cols or removed_cols:
        change_type = MetadataChangeType.SCHEMA_CHANGED
    else:
        change_type = MetadataChangeType.UPDATED

    # 获取前一个版本
    prev_version = get_latest_version(db_session, table_id)
    prev_version_id = prev_version.id if prev_version else None

    # 计算版本号
    version_number = get_version_count(db_session, table_id) + 1

    # 创建版本
    version = MetadataVersionModel(
        id=str(uuid.uuid4()),
        table_id=table_id,
        change_type=change_type.value,
        change_summary="; ".join(changes),
        change_details=change_details,
        schema_snapshot=new_meta,
        changed_by=changed_by,
        change_source=change_source,
        previous_version_id=prev_version_id,
        version_number=version_number,
        created_at=datetime.utcnow(),
    )

    db_session.add(version)
    db_session.commit()

    return version
