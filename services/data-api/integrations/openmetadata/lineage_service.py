"""
OpenLineage 血缘集成服务

实现与 OpenMetadata 的血缘关系集成:
- 将 Data LineageNode/LineageEdge 转换为 OpenLineage 格式
- 推送血缘关系到 OpenMetadata
- 从 OpenMetadata 获取血缘图谱
- 导出 DAG 可视化（Mermaid、JSON 等）
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from .client import OpenMetadataClient, get_client
from .config import OpenMetadataConfig, get_config, is_enabled

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """导出格式"""
    MERMAID = "mermaid"       # Mermaid 流程图
    JSON = "json"             # JSON 格式
    DOT = "dot"               # Graphviz DOT
    PLANTUML = "plantuml"     # PlantUML


@dataclass
class LineageNode:
    """血缘节点"""
    id: str
    name: str
    type: str  # table, pipeline, dashboard, etc.
    fqn: str
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageEdge:
    """血缘边"""
    source_id: str
    target_id: str
    description: Optional[str] = None
    transformation: Optional[str] = None


@dataclass
class LineageDAG:
    """血缘 DAG 图"""
    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    root_node: Optional[str] = None

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_upstream(self, node_id: str) -> List[LineageNode]:
        """获取上游节点"""
        parent_ids = {e.source_id for e in self.edges if e.target_id == node_id}
        return [n for n in self.nodes if n.id in parent_ids]

    def get_downstream(self, node_id: str) -> List[LineageNode]:
        """获取下游节点"""
        child_ids = {e.target_id for e in self.edges if e.source_id == node_id}
        return [n for n in self.nodes if n.id in child_ids]

    def get_path(
        self,
        source_id: str,
        target_id: str,
        visited: Optional[Set[str]] = None,
    ) -> Optional[List[str]]:
        """
        获取两个节点之间的路径

        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            visited: 已访问节点集合（避免循环）

        Returns:
            节点ID路径列表，如果不存在路径则返回 None
        """
        if visited is None:
            visited = set()

        if source_id == target_id:
            return [source_id]

        if source_id in visited:
            return None

        visited.add(source_id)

        for edge in self.edges:
            if edge.source_id == source_id:
                result = self.get_path(edge.target_id, target_id, visited)
                if result:
                    return [source_id] + result

        return None


class EntityType(Enum):
    """OpenMetadata 实体类型"""
    TABLE = "table"
    PIPELINE = "pipeline"
    DASHBOARD = "dashboard"
    TOPIC = "topic"
    MLMODEL = "mlmodel"


class OpenLineageService:
    """
    OpenLineage 血缘集成服务

    将 data 的血缘模型转换为 OpenLineage 标准格式，
    并与 OpenMetadata 进行双向同步。
    """

    def __init__(
        self,
        client: Optional[OpenMetadataClient] = None,
        config: Optional[OpenMetadataConfig] = None,
    ):
        """
        初始化血缘服务

        Args:
            client: OpenMetadata 客户端
            config: 配置对象
        """
        self.config = config or get_config()
        self.client = client or get_client()
        self._service_name = "data-service"

    def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.config.enabled:
            return False
        return self.client.health_check()

    # ========================================
    # 血缘推送 (data -> OpenMetadata)
    # ========================================

    def push_lineage(
        self,
        source_db: str,
        source_table: str,
        target_db: str,
        target_table: str,
        description: Optional[str] = None,
        transformation: Optional[str] = None,
    ) -> Dict:
        """
        推送表级血缘关系到 OpenMetadata

        Args:
            source_db: 源数据库名
            source_table: 源表名
            target_db: 目标数据库名
            target_table: 目标表名
            description: 关系描述
            transformation: 转换逻辑（SQL 等）

        Returns:
            创建的血缘关系对象
        """
        if not self.is_available():
            logger.warning("OpenMetadata lineage service not available")
            return {}

        # 构建 FQN（Fully Qualified Name）
        source_fqn = f"{self._service_name}.{source_db}.{source_table}"
        target_fqn = f"{self._service_name}.{target_db}.{target_table}"

        # 构建描述
        full_description = description or ""
        if transformation:
            full_description = f"{full_description}\n\nTransformation:\n```sql\n{transformation}\n```"

        logger.info(
            "Pushing lineage: %s -> %s",
            source_fqn,
            target_fqn
        )

        return self.client.add_lineage(
            from_entity_type=EntityType.TABLE.value,
            from_entity_fqn=source_fqn,
            to_entity_type=EntityType.TABLE.value,
            to_entity_fqn=target_fqn,
            description=full_description.strip() if full_description else None,
        )

    def push_pipeline_lineage(
        self,
        pipeline_name: str,
        input_tables: List[Tuple[str, str]],
        output_tables: List[Tuple[str, str]],
        description: Optional[str] = None,
    ) -> List[Dict]:
        """
        推送 Pipeline 级血缘关系

        Args:
            pipeline_name: Pipeline/ETL 任务名称
            input_tables: 输入表列表 [(db, table), ...]
            output_tables: 输出表列表 [(db, table), ...]
            description: 描述

        Returns:
            创建的血缘关系列表
        """
        if not self.is_available():
            return []

        results = []

        # 创建 input -> output 的血缘关系
        for in_db, in_table in input_tables:
            for out_db, out_table in output_tables:
                try:
                    result = self.push_lineage(
                        source_db=in_db,
                        source_table=in_table,
                        target_db=out_db,
                        target_table=out_table,
                        description=f"Pipeline: {pipeline_name}\n{description or ''}",
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "Failed to push lineage %s.%s -> %s.%s: %s",
                        in_db, in_table, out_db, out_table, e
                    )

        return results

    def push_etl_task_lineage(self, etl_task) -> List[Dict]:
        """
        从 ETL 任务推送血缘关系

        Args:
            etl_task: data ETLTask 模型实例

        Returns:
            创建的血缘关系列表
        """
        if not self.is_available():
            return []

        # 从 ETL 任务配置中提取输入输出表
        config = etl_task.config or {}

        input_tables = []
        output_tables = []

        # 解析输入表
        if config.get("source_tables"):
            for src in config["source_tables"]:
                db = src.get("database", "default")
                table = src.get("table")
                if table:
                    input_tables.append((db, table))

        # 解析输出表
        if config.get("target_tables"):
            for tgt in config["target_tables"]:
                db = tgt.get("database", "default")
                table = tgt.get("table")
                if table:
                    output_tables.append((db, table))

        if not input_tables or not output_tables:
            logger.debug("ETL task %s has no input/output tables defined", etl_task.name)
            return []

        return self.push_pipeline_lineage(
            pipeline_name=etl_task.name,
            input_tables=input_tables,
            output_tables=output_tables,
            description=etl_task.description,
        )

    def push_lineage_edge(self, lineage_edge) -> Dict:
        """
        从 data LineageEdge 模型推送血缘

        Args:
            lineage_edge: data LineageEdge 模型实例

        Returns:
            创建的血缘关系对象
        """
        if not self.is_available():
            return {}

        # 获取源和目标节点
        source_node = lineage_edge.source_node
        target_node = lineage_edge.target_node

        if not source_node or not target_node:
            logger.warning("LineageEdge missing source or target node")
            return {}

        # 转换节点类型
        source_type = self._convert_node_type(source_node.node_type)
        target_type = self._convert_node_type(target_node.node_type)

        # 构建 FQN
        source_fqn = self._build_fqn(source_node)
        target_fqn = self._build_fqn(target_node)

        if not source_fqn or not target_fqn:
            logger.warning("Cannot build FQN for lineage edge")
            return {}

        return self.client.add_lineage(
            from_entity_type=source_type,
            from_entity_fqn=source_fqn,
            to_entity_type=target_type,
            to_entity_fqn=target_fqn,
            description=lineage_edge.description,
        )

    def _convert_node_type(self, data_type: str) -> str:
        """将 data 节点类型转换为 OpenMetadata 实体类型"""
        type_mapping = {
            "database": EntityType.TABLE.value,
            "table": EntityType.TABLE.value,
            "column": EntityType.TABLE.value,
            "job": EntityType.PIPELINE.value,
            "dataset": EntityType.TABLE.value,
            "model": EntityType.MLMODEL.value,
        }
        return type_mapping.get(data_type, EntityType.TABLE.value)

    def _build_fqn(self, lineage_node) -> Optional[str]:
        """从 LineageNode 构建 OpenMetadata FQN"""
        node_type = lineage_node.node_type

        if node_type in ("table", "database", "dataset"):
            # 表级 FQN: service.database.schema.table
            parts = [self._service_name]

            if lineage_node.database_name:
                parts.append(lineage_node.database_name)
            else:
                parts.append("default")

            if lineage_node.table_name:
                parts.append(lineage_node.table_name)
            elif lineage_node.name:
                parts.append(lineage_node.name)
            else:
                return None

            return ".".join(parts)

        elif node_type == "job":
            # Pipeline FQN
            return f"data-pipelines.{lineage_node.name}"

        return None

    # ========================================
    # 血缘获取 (OpenMetadata -> data)
    # ========================================

    def get_table_lineage(
        self,
        db_name: str,
        table_name: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3,
    ) -> Dict:
        """
        获取表的血缘关系

        Args:
            db_name: 数据库名
            table_name: 表名
            upstream_depth: 上游追溯深度
            downstream_depth: 下游追溯深度

        Returns:
            血缘关系图
        """
        if not self.is_available():
            return {}

        table_fqn = f"{self._service_name}.{db_name}.{table_name}"

        try:
            return self.client.get_lineage(
                entity_type=EntityType.TABLE.value,
                entity_fqn=table_fqn,
                upstream_depth=upstream_depth,
                downstream_depth=downstream_depth,
            )
        except Exception as e:
            logger.error("Failed to get lineage for %s: %s", table_fqn, e)
            return {}

    def get_upstream_tables(self, db_name: str, table_name: str) -> List[Dict]:
        """
        获取表的上游依赖表

        Args:
            db_name: 数据库名
            table_name: 表名

        Returns:
            上游表列表
        """
        lineage = self.get_table_lineage(db_name, table_name, upstream_depth=1, downstream_depth=0)

        upstream = []
        for node in lineage.get("upstreamEdges", []):
            from_entity = node.get("fromEntity", {})
            if from_entity.get("type") == "table":
                upstream.append({
                    "fqn": from_entity.get("fqn"),
                    "name": from_entity.get("name"),
                    "description": from_entity.get("description"),
                })

        return upstream

    def get_downstream_tables(self, db_name: str, table_name: str) -> List[Dict]:
        """
        获取表的下游依赖表

        Args:
            db_name: 数据库名
            table_name: 表名

        Returns:
            下游表列表
        """
        lineage = self.get_table_lineage(db_name, table_name, upstream_depth=0, downstream_depth=1)

        downstream = []
        for node in lineage.get("downstreamEdges", []):
            to_entity = node.get("toEntity", {})
            if to_entity.get("type") == "table":
                downstream.append({
                    "fqn": to_entity.get("fqn"),
                    "name": to_entity.get("name"),
                    "description": to_entity.get("description"),
                })

        return downstream

    # ========================================
    # 批量同步
    # ========================================

    def sync_all_lineage(self, lineage_edges: List) -> Dict[str, int]:
        """
        批量同步所有血缘关系

        Args:
            lineage_edges: LineageEdge 模型实例列表

        Returns:
            同步统计 {"synced": N, "failed": N, "skipped": N}
        """
        stats = {"synced": 0, "failed": 0, "skipped": 0}

        if not self.is_available():
            stats["skipped"] = len(lineage_edges)
            return stats

        for edge in lineage_edges:
            try:
                result = self.push_lineage_edge(edge)
                if result:
                    stats["synced"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error("Failed to sync lineage edge: %s", e)
                stats["failed"] += 1

        logger.info(
            "Lineage sync completed: synced=%d, failed=%d, skipped=%d",
            stats["synced"],
            stats["failed"],
            stats["skipped"],
        )
        return stats

    # ========================================
    # DAG 导出与可视化
    # ========================================

    def build_lineage_dag(
        self,
        db_name: str,
        table_name: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3,
    ) -> LineageDAG:
        """
        构建血缘 DAG 图

        Args:
            db_name: 数据库名
            table_name: 表名
            upstream_depth: 上游追溯深度
            downstream_depth: 下游追溯深度

        Returns:
            LineageDAG 对象
        """
        lineage_data = self.get_table_lineage(
            db_name, table_name, upstream_depth, downstream_depth
        )

        dag = LineageDAG()
        node_map: Dict[str, LineageNode] = {}

        root_fqn = f"{self._service_name}.{db_name}.{table_name}"
        dag.root_node = root_fqn

        # 处理上游节点
        for edge in lineage_data.get("upstreamEdges", []):
            from_entity = edge.get("fromEntity", {})
            to_entity = edge.get("toEntity", {})

            from_id = from_entity.get("fqn", "")
            to_id = to_entity.get("fqn", "")

            if from_id and from_id not in node_map:
                node_map[from_id] = LineageNode(
                    id=from_id,
                    name=from_entity.get("name", ""),
                    type=from_entity.get("type", "table"),
                    fqn=from_id,
                    description=from_entity.get("description"),
                )

            if to_id and to_id not in node_map:
                node_map[to_id] = LineageNode(
                    id=to_id,
                    name=to_entity.get("name", ""),
                    type=to_entity.get("type", "table"),
                    fqn=to_id,
                    description=to_entity.get("description"),
                )

            if from_id and to_id:
                dag.edges.append(LineageEdge(
                    source_id=from_id,
                    target_id=to_id,
                    description=edge.get("description"),
                ))

        # 处理下游节点
        for edge in lineage_data.get("downstreamEdges", []):
            from_entity = edge.get("fromEntity", {})
            to_entity = edge.get("toEntity", {})

            from_id = from_entity.get("fqn", "")
            to_id = to_entity.get("fqn", "")

            if from_id and from_id not in node_map:
                node_map[from_id] = LineageNode(
                    id=from_id,
                    name=from_entity.get("name", ""),
                    type=from_entity.get("type", "table"),
                    fqn=from_id,
                    description=from_entity.get("description"),
                )

            if to_id and to_id not in node_map:
                node_map[to_id] = LineageNode(
                    id=to_id,
                    name=to_entity.get("name", ""),
                    type=to_entity.get("type", "table"),
                    fqn=to_id,
                    description=to_entity.get("description"),
                )

            if from_id and to_id:
                dag.edges.append(LineageEdge(
                    source_id=from_id,
                    target_id=to_id,
                    description=edge.get("description"),
                ))

        # 添加根节点（如果还没有）
        if root_fqn not in node_map:
            node_map[root_fqn] = LineageNode(
                id=root_fqn,
                name=table_name,
                type="table",
                fqn=root_fqn,
            )

        dag.nodes = list(node_map.values())
        return dag

    def export_dag(
        self,
        dag: LineageDAG,
        format: ExportFormat = ExportFormat.MERMAID,
    ) -> str:
        """
        导出 DAG 为指定格式

        Args:
            dag: 血缘 DAG 对象
            format: 导出格式

        Returns:
            格式化的字符串
        """
        if format == ExportFormat.MERMAID:
            return self._export_mermaid(dag)
        elif format == ExportFormat.JSON:
            return self._export_json(dag)
        elif format == ExportFormat.DOT:
            return self._export_dot(dag)
        elif format == ExportFormat.PLANTUML:
            return self._export_plantuml(dag)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_mermaid(self, dag: LineageDAG) -> str:
        """导出为 Mermaid 流程图格式"""
        lines = ["graph TD"]

        # 定义节点样式
        lines.append("    classDef table fill:#e1f5fe,stroke:#01579b,stroke-width:2px;")
        lines.append("    classDef pipeline fill:#fff3e0,stroke:#e65100,stroke-width:2px;")
        lines.append("    classDef dashboard fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;")

        # 节点 ID 映射（避免特殊字符问题）
        node_id_map = {}
        for i, node in enumerate(dag.nodes):
            safe_id = f"N{i}"
            node_id_map[node.id] = safe_id

            # 提取表名（去掉服务前缀）
            display_name = node.name
            if "." in node.fqn:
                parts = node.fqn.split(".")
                if len(parts) > 2:
                    display_name = f"{parts[-2]}.{parts[-1]}"

            label = display_name
            if node.description:
                label = f"{display_name}\\n{node.description[:50]}"

            lines.append(f'    {safe_id}["{label}"]')

        # 边
        for edge in dag.edges:
            source_id = node_id_map.get(edge.source_id)
            target_id = node_id_map.get(edge.target_id)
            if source_id and target_id:
                label = ""
                if edge.description:
                    label = f"|{edge.description[:30]}|"
                lines.append(f"    {source_id} --> {label} {target_id}")

        # 样式分配
        for node in dag.nodes:
            safe_id = node_id_map.get(node.id)
            if safe_id:
                if node.type == "table":
                    lines.append(f"    class {safe_id} table")
                elif node.type == "pipeline":
                    lines.append(f"    class {safe_id} pipeline")
                elif node.type == "dashboard":
                    lines.append(f"    class {safe_id} dashboard")

        return "\n".join(lines)

    def _export_json(self, dag: LineageDAG) -> str:
        """导出为 JSON 格式"""
        import json

        data = {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "fqn": n.fqn,
                    "description": n.description,
                    "properties": n.properties,
                }
                for n in dag.nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "description": e.description,
                    "transformation": e.transformation,
                }
                for e in dag.edges
            ],
            "root_node": dag.root_node,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _export_dot(self, dag: LineageDAG) -> str:
        """导出为 Graphviz DOT 格式"""
        lines = ["digraph LineageDAG {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # 节点
        for node in dag.nodes:
            label = node.name
            if node.description:
                label = f"{node.name}\\n{node.description[:30]}"

            # 根据类型设置颜色
            color = "#e1f5fe"
            if node.type == "pipeline":
                color = "#fff3e0"
            elif node.type == "dashboard":
                color = "#f3e5f5"

            # 转义 FQN 中的特殊字符
            safe_id = node.id.replace(".", "_").replace(":", "_")
            lines.append(f'    "{safe_id}" [label="{label}", fillcolor="{color}", style="filled"];')

        lines.append("")

        # 边
        for edge in dag.edges:
            source_safe = edge.source_id.replace(".", "_").replace(":", "_")
            target_safe = edge.target_id.replace(".", "_").replace(":", "_")
            label = f' [label="{edge.description[:30]}"]' if edge.description else ""
            lines.append(f'    "{source_safe}" -> "{target_safe}"{label};')

        lines.append("}")
        return "\n".join(lines)

    def _export_plantuml(self, dag: LineageDAG) -> str:
        """导出为 PlantUML 格式"""
        lines = ["@startuml LineageDAG"]
        lines.append("hide empty members")

        # 定义样式
        lines.append("skinparam node {")
        lines.append("    BackgroundColor<<Table>> #e1f5fe")
        lines.append("    BorderColor<<Table>> #01579b")
        lines.append("    BackgroundColor<<Pipeline>> #fff3e0")
        lines.append("    BorderColor<<Pipeline>> #e65100")
        lines.append("    BackgroundColor<<Dashboard>> #f3e5f5")
        lines.append("    BorderColor<<Dashboard>> #7b1fa2")
        lines.append("}")

        # 节点
        for node in dag.nodes:
            safe_id = node.id.replace(".", "_").replace(":", "_")
            stereotype = "<<Table>>"
            if node.type == "pipeline":
                stereotype = "<<Pipeline>>"
            elif node.type == "dashboard":
                stereotype = "<<Dashboard>>"

            lines.append(f'class "{safe_id}" {stereotype} {{')
            lines.append(f'    {node.name}')
            if node.description:
                lines.append(f'    --')
                lines.append(f'    {node.description[:50]}')
            lines.append("}")

        # 关系
        for edge in dag.edges:
            source_safe = edge.source_id.replace(".", "_").replace(":", "_")
            target_safe = edge.target_id.replace(".", "_").replace(":", "_")
            label = f" : {edge.description}" if edge.description else ""
            lines.append(f'"{source_safe}" --> "{target_safe}"{label}')

        lines.append("@enduml")
        return "\n".join(lines)

    def get_lineage_path(
        self,
        source_db: str,
        source_table: str,
        target_db: str,
        target_table: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """
        获取两个表之间的血缘路径

        Args:
            source_db: 源数据库名
            source_table: 源表名
            target_db: 目标数据库名
            target_table: 目标表名
            max_depth: 最大搜索深度

        Returns:
            路径列表，如果不存在路径则返回 None
        """
        source_fqn = f"{self._service_name}.{source_db}.{source_table}"
        target_fqn = f"{self._service_name}.{target_db}.{target_table}"

        # 获取源表的上游血缘
        source_lineage = self.get_table_lineage(
            source_db, source_table, upstream_depth=max_depth, downstream_depth=0
        )

        # 构建可达性映射
        reachable = {source_fqn: [source_fqn]}

        def trace_upstream(fqn: str, path: List[str], depth: int) -> None:
            if depth > max_depth:
                return
            for edge in source_lineage.get("upstreamEdges", []):
                from_entity = edge.get("fromEntity", {})
                to_entity = edge.get("toEntity", {})
                if to_entity.get("fqn") == fqn:
                    upstream_fqn = from_entity.get("fqn")
                    if upstream_fqn and upstream_fqn not in reachable:
                        new_path = path + [upstream_fqn]
                        reachable[upstream_fqn] = new_path
                        trace_upstream(upstream_fqn, new_path, depth + 1)

        trace_upstream(source_fqn, [source_fqn], 0)

        return reachable.get(target_fqn)

    def trace_column_lineage(
        self,
        db_name: str,
        table_name: str,
        column_name: str,
        direction: str = "upstream",
    ) -> List[Dict[str, Any]]:
        """
        追踪列级血缘

        Args:
            db_name: 数据库名
            table_name: 表名
            column_name: 列名
            direction: 追溯方向 (upstream/downstream)

        Returns:
            列血缘路径列表
        """
        # 注意: OpenMetadata 的列级血缘支持有限
        # 这里提供基本框架，实际实现可能需要自定义存储

        if not self.is_available():
            return []

        table_fqn = f"{self._service_name}.{db_name}.{table_name}"

        try:
            lineage = self.client.get_lineage(
                entity_type=EntityType.TABLE.value,
                entity_fqn=table_fqn,
                upstream_depth=(direction == "upstream") * 3,
                downstream_depth=(direction == "downstream") * 3,
            )

            # 这里需要根据实际的列级血缘数据进行匹配
            # OpenMetadata 返回的是表级血缘，需要结合具体的 ETL 配置推断列级关系

            column_paths = []
            edges = (
                lineage.get("upstreamEdges", [])
                if direction == "upstream"
                else lineage.get("downstreamEdges", [])
            )

            for edge in edges:
                from_entity = edge.get("fromEntity", {})
                to_entity = edge.get("toEntity", {})

                column_paths.append({
                    "source_table": from_entity.get("fqn", ""),
                    "source_column": column_name,  # 需要从实际数据中推断
                    "target_table": to_entity.get("fqn", ""),
                    "target_column": column_name,
                    "transformation": edge.get("description", ""),
                })

            return column_paths

        except Exception as e:
            logger.error("Failed to trace column lineage: %s", e)
            return []


# 全局血缘服务实例
_lineage_service: Optional[OpenLineageService] = None


def get_lineage_service() -> OpenLineageService:
    """获取全局血缘服务实例（单例）"""
    global _lineage_service
    if _lineage_service is None:
        _lineage_service = OpenLineageService()
    return _lineage_service
