"""
数据血缘模型
P1.3: 数据血缘管理后端
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON
)
from .base import Base


class LineageNode(Base):
    """血缘节点表"""
    __tablename__ = "lineage_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(64), unique=True, nullable=False, index=True)

    # 节点信息
    node_type = Column(String(32), nullable=False)  # database, table, column, job, dataset
    name = Column(String(255), nullable=False)
    full_name = Column(String(512))  # database.table.column 形式

    # 关联信息
    database_name = Column(String(255), index=True)
    table_name = Column(String(255), index=True)
    column_name = Column(String(255))

    # 元数据
    description = Column(Text)
    tags = Column(JSON)
    properties = Column(JSON)

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "full_name": self.full_name,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "description": self.description,
            "tags": self.tags,
            "properties": self.properties,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LineageEdge(Base):
    """血缘边表"""
    __tablename__ = "lineage_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edge_id = Column(String(64), unique=True, nullable=False, index=True)

    # 源节点
    source_node_id = Column(String(64), nullable=False, index=True)
    source_type = Column(String(32))
    source_name = Column(String(512))

    # 目标节点
    target_node_id = Column(String(64), nullable=False, index=True)
    target_type = Column(String(32))
    target_name = Column(String(512))

    # 关系信息
    relation_type = Column(String(32), default="derive")  # derive, transform, copy, join
    transformation = Column(Text)  # 转换逻辑描述或 SQL

    # 来源
    job_id = Column(String(64))  # 关联的 ETL 任务 ID
    job_type = Column(String(32))  # etl, sql, spark, etc.

    # 置信度
    confidence = Column(Integer, default=100)  # 0-100

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.edge_id,
            "source_node_id": self.source_node_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "target_node_id": self.target_node_id,
            "target_type": self.target_type,
            "target_name": self.target_name,
            "relation_type": self.relation_type,
            "transformation": self.transformation,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LineageSnapshot(Base):
    """血缘快照表 - 用于保存特定时间点的血缘图"""
    __tablename__ = "lineage_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(64), unique=True, nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 快照数据
    nodes = Column(JSON)  # 节点列表
    edges = Column(JSON)  # 边列表

    # 统计
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.snapshot_id,
            "name": self.name,
            "description": self.description,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
