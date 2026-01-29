"""
数据血缘事件模型
用于捕获和存储数据操作过程中的血缘关系事件

支持 OpenLineage 标准协议:
- DATASET_EVENT: 数据集操作事件 (CREATE/UPDATE/DELETE/DROP)
- JOB_EVENT: ETL 任务事件 (START/RUN/COMPLETE/FAIL/ABORT)
- OUTPUT_DATASET: 任务输出数据集

事件生命周期:
1. 捕获: 从 ETL 任务、SQL 操作、API 调用中捕获事件
2. 存储: 持久化到数据库，支持查询和审计
3. 推送: 推送到 OpenLineage 服务 (OpenMetadata/Marquez)
4. 分析: 支持血缘路径查询和影响分析
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Text, Integer, JSON, Boolean
from sqlalchemy.dialects.mysql import BIGINT
from database import Base

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型"""
    # 数据集事件
    DATASET_CREATED = "DATASET_CREATED"
    DATASET_UPDATED = "DATASET_UPDATED"
    DATASET_DELETED = "DATASET_DELETED"
    DATASET_DROPPED = "DATASET_DROPPED"
    DATASET_SCANNED = "DATASET_SCANNED"  # 元数据扫描

    # 任务事件
    JOB_STARTED = "JOB_STARTED"
    JOB_RUNNING = "JOB_RUNNING"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_ABORTED = "JOB_ABORTED"
    JOB_PAUSED = "JOB_PAUSED"

    # 字段事件
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_REMOVED = "COLUMN_REMOVED"
    COLUMN_MODIFIED = "COLUMN_MODIFIED"
    COLUMN_MASKED = "COLUMN_MASKED"  # 脱敏操作


class EventSource(str, Enum):
    """事件来源"""
    KETTLE_ETL = "kettle_etl"           # Kettle ETL 任务
    SQL_EXECUTION = "sql_execution"     # SQL 直接执行
    API_OPERATION = "api_operation"     # API 调用
    METADATA_SCAN = "metadata_scan"     # 元数据扫描
    DATA_PIPELINE = "data_pipeline"     # 数据管道
    MANUAL_ENTRY = "manual_entry"       # 手动录入


class DatasetType(str, Enum):
    """数据集类型"""
    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    FEATURE_GROUP = "feature_group"
    MODEL = "model"
    FILE = "file"


@dataclass
class DatasetIdentifier:
    """数据集标识符 (OpenLineage Dataset)"""
    namespace: str                    # 命名空间 (如: alldata-service)
    name: str                          # 数据集名称
    type: DatasetType = DatasetType.TABLE
    facets: Dict[str, Any] = field(default_factory=dict)  # schema/ownership/statistics

    def to_fqn(self) -> str:
        """返回完全限定名"""
        return f"{self.namespace}.{self.name}"

    @classmethod
    def from_fqn(cls, fqn: str, default_namespace: str = "alldata-service") -> "DatasetIdentifier":
        """从 FQN 解析"""
        parts = fqn.split(".")
        if len(parts) >= 2:
            return cls(namespace=parts[0], name=".".join(parts[1:]))
        return cls(namespace=default_namespace, name=fqn)


@dataclass
class JobIdentifier:
    """任务标识符 (OpenLineage Job)"""
    namespace: str                     # 命名空间
    name: str                          # 任务名称
    facets: Dict[str, Any] = field(default_factory=dict)  # source_code/context

    def to_fqn(self) -> str:
        """返回完全限定名"""
        return f"{self.namespace}.{self.name}"


@dataclass
class LineageEvent:
    """
    血缘事件基类

    遵循 OpenLineage 事件格式:
    {
        "eventType": "START|COMPLETE|FAIL|ABORT",
        "eventTime": "ISO-8601 timestamp",
        "run": {
            "runId": "unique identifier",
            "facets": {}
        },
        "job": {
            "namespace": "string",
            "name": "string",
            "facets": {}
        },
        "inputs": [DatasetIdentifier],
        "outputs": [DatasetIdentifier]
    }
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.JOB_STARTED
    event_time: datetime = field(default_factory=datetime.utcnow)
    source: EventSource = EventSource.MANUAL_ENTRY

    # 任务信息
    job_namespace: str = "alldata"
    job_name: str = ""
    job_facets: Dict[str, Any] = field(default_factory=dict)

    # 输入输出数据集
    input_datasets: List[DatasetIdentifier] = field(default_factory=list)
    output_datasets: List[DatasetIdentifier] = field(default_factory=list)

    # 运行信息
    run_id: str = field(default_factory=lambda: str(uuid4()))
    run_facets: Dict[str, Any] = field(default_factory=dict)

    # 附加信息
    transformation: Optional[str] = None  # 转换 SQL 或描述
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_openlineage_dict(self) -> Dict[str, Any]:
        """转换为 OpenLineage 标准格式"""
        return {
            "eventType": self.event_type.value.replace("JOB_", ""),
            "eventTime": self.event_time.isoformat() + "Z",
            "run": {
                "runId": self.run_id,
                "facets": self.run_facets,
            },
            "job": {
                "namespace": self.job_namespace,
                "name": self.job_name,
                "facets": self.job_facets,
            },
            "inputs": [
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "facets": ds.facets,
                }
                for ds in self.input_datasets
            ],
            "outputs": [
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "facets": ds.facets,
                }
                for ds in self.output_datasets
            ],
        }


@dataclass
class DatasetOperationEvent(LineageEvent):
    """
    数据集操作事件

    用于追踪数据集级别的变更，不关联特定任务
    """
    dataset: Optional[DatasetIdentifier] = None
    operation_type: EventType = EventType.DATASET_UPDATED
    column_name: Optional[str] = None  # 如果是列级操作

    def to_openlineage_dict(self) -> Dict[str, Any]:
        """转换为 OpenLineage 格式"""
        base = super().to_openlineage_dict()
        if self.dataset:
            base["dataset"] = {
                "namespace": self.dataset.namespace,
                "name": self.dataset.name,
                "facets": self.dataset.facets,
            }
        if self.column_name:
            base["column"] = self.column_name
        return base


# ====================
# SQLAlchemy 模型
# ====================

class LineageEventModel(Base):
    """
    血缘事件持久化模型

    存储所有血缘事件用于:
    1. 审计追踪
    2. 血缘重建
    3. 影响分析
    4. 历史查询
    """
    __tablename__ = "lineage_events"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)  # UUID

    # 事件基本信息
    event_type = Column(String(50), nullable=False, index=True)
    event_time = Column(DateTime, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)

    # 任务信息
    job_namespace = Column(String(255), nullable=False)
    job_name = Column(String(255), nullable=False, index=True)
    run_id = Column(String(64), nullable=False, index=True)

    # 数据集信息 (JSON 存储列表)
    input_datasets = Column(JSON, nullable=True)
    output_datasets = Column(JSON, nullable=True)

    # 转换信息
    transformation = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # 额外元数据
    metadata = Column(JSON, nullable=True)

    # 状态信息
    status = Column(String(50), default="pending")  # pending/synced/failed
    error_message = Column(Text, nullable=True)

    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow)
    synced_at = Column(DateTime, nullable=True)

    def to_lineage_event(self) -> LineageEvent:
        """转换为 LineageEvent 数据类"""
        input_datasets = []
        if self.input_datasets:
            for ds in self.input_datasets:
                input_datasets.append(DatasetIdentifier(
                    namespace=ds.get("namespace", "alldata"),
                    name=ds.get("name", ""),
                    type=DatasetType(ds.get("type", "table")),
                    facets=ds.get("facets", {}),
                ))

        output_datasets = []
        if self.output_datasets:
            for ds in self.output_datasets:
                output_datasets.append(DatasetIdentifier(
                    namespace=ds.get("namespace", "alldata"),
                    name=ds.get("name", ""),
                    type=DatasetType(ds.get("type", "table")),
                    facets=ds.get("facets", {}),
                ))

        return LineageEvent(
            event_id=self.event_id,
            event_type=EventType(self.event_type),
            event_time=self.event_time,
            source=EventSource(self.source),
            job_namespace=self.job_namespace,
            job_name=self.job_name,
            run_id=self.run_id,
            input_datasets=input_datasets,
            output_datasets=output_datasets,
            transformation=self.transformation,
            description=self.description,
            metadata=self.metadata or {},
        )


class LineageEdgeModel(Base):
    """
    血缘边模型

    存储数据集之间的血缘关系边，用于快速查询血缘图
    """
    __tablename__ = "lineage_edges"

    id = Column(BIGINT, primary_key=True, autoincrement=True)

    # 源节点
    source_namespace = Column(String(255), nullable=False, index=True)
    source_name = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # table/view/pipeline

    # 目标节点
    target_namespace = Column(String(255), nullable=False, index=True)
    target_name = Column(String(255), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)

    # 关系信息
    edge_type = Column(String(50), default="data_flow")  # data_flow/dependency/ownership
    transformation = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # 元数据
    metadata = Column(JSON, nullable=True)

    # 统计
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)

    # 审计
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def source_fqn(self) -> str:
        return f"{self.source_namespace}.{self.source_name}"

    @property
    def target_fqn(self) -> str:
        return f"{self.target_namespace}.{self.target_name}"


class LineageNodeCache(Base):
    """
    血缘节点缓存

    缓存常用节点的血缘信息，加速查询
    """
    __tablename__ = "lineage_node_cache"

    id = Column(BIGINT, primary_key=True, autoincrement=True)

    # 节点标识
    namespace = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)  # table/view/pipeline/model

    # 缓存的上游节点 (JSON 数组)
    upstream_nodes = Column(JSON, nullable=True)

    # 缓存的下游节点 (JSON 数组)
    downstream_nodes = Column(JSON, nullable=True)

    # 缓存元数据
    depth = Column(Integer, default=1)  # 缓存深度
    node_count = Column(Integer, default=0)  # 关联节点数

    # 过期时间
    expires_at = Column(DateTime, nullable=True, index=True)

    # 审计
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def fqn(self) -> str:
        return f"{self.namespace}.{self.name}"

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if not self.expires_at:
            return True
        return datetime.utcnow() > self.expires_at


# ====================
# 工厂函数
# ====================

def create_etl_lineage_event(
    job_name: str,
    source_tables: List[str],
    target_tables: List[str],
    transformation: Optional[str] = None,
    run_id: Optional[str] = None,
) -> LineageEvent:
    """
    创建 ETL 任务血缘事件

    Args:
        job_name: 任务名称
        source_tables: 源表列表 [fqn, ...]
        target_tables: 目标表列表 [fqn, ...]
        transformation: 转换 SQL
        run_id: 运行 ID

    Returns:
        LineageEvent 对象
    """
    return LineageEvent(
        event_type=EventType.JOB_STARTED,
        job_namespace="alldata",
        job_name=job_name,
        run_id=run_id or str(uuid4()),
        source=EventSource.KETTLE_ETL,
        input_datasets=[
            DatasetIdentifier.from_fqn(tbl) for tbl in source_tables
        ],
        output_datasets=[
            DatasetIdentifier.from_fqn(tbl) for tbl in target_tables
        ],
        transformation=transformation,
    )


def create_scan_lineage_event(
    database: str,
    tables_scanned: List[str],
    scan_id: Optional[str] = None,
) -> LineageEvent:
    """
    创建元数据扫描血缘事件

    Args:
        database: 数据库名
        tables_scanned: 扫描到的表列表
        scan_id: 扫描 ID

    Returns:
        LineageEvent 对象
    """
    return LineageEvent(
        event_type=EventType.DATASET_SCANNED,
        job_namespace="alldata",
        job_name=f"metadata_scan_{database}",
        run_id=scan_id or str(uuid4()),
        source=EventSource.METADATA_SCAN,
        output_datasets=[
            DatasetIdentifier(
                namespace="alldata-service",
                name=f"{database}.{tbl}",
                type=DatasetType.TABLE,
            )
            for tbl in tables_scanned
        ],
        description=f"Metadata scan discovered {len(tables_scanned)} tables",
    )


def create_column_masked_event(
    table: str,
    column: str,
    masking_strategy: str,
) -> DatasetOperationEvent:
    """
    创建列脱敏事件

    Args:
        table: 表名 (fqn)
        column: 列名
        masking_strategy: 脱敏策略

    Returns:
        DatasetOperationEvent 对象
    """
    return DatasetOperationEvent(
        event_type=EventType.COLUMN_MASKED,
        job_namespace="alldata",
        job_name=f"masking_{table}",
        source=EventSource.API_OPERATION,
        dataset=DatasetIdentifier.from_fqn(table),
        column_name=column,
        description=f"Column {column} masked using {masking_strategy}",
        metadata={"strategy": masking_strategy},
    )
