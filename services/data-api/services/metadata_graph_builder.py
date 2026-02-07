"""
元数据图谱构建服务
将元数据关系转换为可视化图谱数据
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn
from models.lineage import LineageNode, LineageEdge
try:
    import services.lineage_analyzer as lineage_module
except ImportError:
    import src.lineage_analyzer as lineage_module

logger = logging.getLogger(__name__)


class MetadataGraphBuilder:
    """元数据图谱构建器"""

    def __init__(self):
        pass

    def build_full_graph(
        self,
        db: Session,
        tenant_id: str,
        node_types: Optional[List[str]] = None,
        include_lineage: bool = True
    ) -> Dict:
        """
        构建完整的元数据图谱

        返回: {
            "nodes": [{"id": "...", "label": "...", "type": "...", ...}],
            "edges": [{"source": "...", "target": "...", "label": "...", ...}]
        }
        """
        nodes = []
        edges = []
        node_id_map = {}  # 用于建立节点ID映射

        # 如果没有指定节点类型，默认包含所有类型
        if node_types is None:
            node_types = ["database", "table", "column"]

        # 获取数据库节点
        if "database" in node_types:
            databases = db.query(MetadataDatabase).filter(
                MetadataDatabase.tenant_id == tenant_id
            ).all()

            for db_obj in databases:
                node_id = f"db_{db_obj.id}"
                node_id_map[f"database:{db_obj.database_name}"] = node_id

                nodes.append({
                    "id": node_id,
                    "label": db_obj.database_name,
                    "type": "database",
                    "database_name": db_obj.database_name,
                    "description": db_obj.description,
                    "owner": db_obj.owner,
                    "table_count": 0,  # 稍后统计
                    "properties": {
                        "created_at": db_obj.created_at.isoformat() if db_obj.created_at else None,
                        "updated_at": db_obj.updated_at.isoformat() if db_obj.updated_at else None,
                    }
                })

        # 获取表节点和边
        if "table" in node_types:
            tables = db.query(MetadataTable).filter(
                MetadataTable.tenant_id == tenant_id
            ).all()

            for table in tables:
                # 构建表节点
                table_node_id = f"table_{table.id}"
                node_id_map[f"table:{table.database_name}.{table.table_name}"] = table_node_id
                node_id_map[f"table:{table.table_name}"] = table_node_id

                nodes.append({
                    "id": table_node_id,
                    "label": table.table_name,
                    "type": "table",
                    "database_name": table.database_name,
                    "table_name": table.table_name,
                    "description": table.description,
                    "row_count": table.row_count,
                    "updated_at": table.updated_at.isoformat() if table.updated_at else None,
                    "properties": {
                        "has_ai_annotation": any([
                            table.description  # 简化判断
                        ]),
                        "column_count": 0,  # 稍后统计
                    }
                })

                # 添加数据库到表的边
                db_node_id = node_id_map.get(f"database:{table.database_name}")
                if db_node_id:
                    edges.append({
                        "source": db_node_id,
                        "target": table_node_id,
                        "label": "contains",
                        "type": "hierarchy",
                        "database": table.database_name
                    })

        # 获取列节点和边
        if "column" in node_types:
            columns = db.query(MetadataColumn).filter(
                MetadataColumn.tenant_id == tenant_id
            ).all()

            for column in columns:
                # 构建列节点
                column_node_id = f"column_{column.id}"
                full_name = f"{column.database_name}.{column.table_name}.{column.column_name}"
                node_id_map[f"column:{full_name}"] = column_node_id

                nodes.append({
                    "id": column_node_id,
                    "label": column.column_name,
                    "type": "column",
                    "database_name": column.database_name,
                    "table_name": column.table_name,
                    "column_name": column.column_name,
                    "data_type": column.data_type,
                    "is_nullable": column.is_nullable,
                    "description": column.description,
                    "position": column.position,
                    "properties": {
                        "ai_description": column.ai_description,
                        "sensitivity_level": column.sensitivity_level,
                        "sensitivity_type": column.sensitivity_type,
                        "semantic_tags": column.semantic_tags,
                        "ai_confidence": column.ai_confidence,
                    }
                })

                # 添加表到列的边
                table_node_id = node_id_map.get(f"table:{column.database_name}.{column.table_name}")
                if table_node_id:
                    edges.append({
                        "source": table_node_id,
                        "target": column_node_id,
                        "label": "",
                        "type": "hierarchy",
                        "position": column.position
                    })

        # 添加数据血缘关系
        if include_lineage:
            lineage_nodes, lineage_edges = self._build_lineage_graph(db, tenant_id, node_id_map)
            nodes.extend(lineage_nodes)
            edges.extend(lineage_edges)

        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": self._count_node_types(nodes)
            }
        }

    def build_table_lineage_graph(
        self,
        db: Session,
        tenant_id: str,
        table_name: str,
        depth: int = 3
    ) -> Dict:
        """
        构建单个表的数据血缘图谱

        返回上游和下游的依赖关系
        """
        # 查找表节点
        table = db.query(MetadataTable).filter(
            and_(
                MetadataTable.tenant_id == tenant_id,
                MetadataTable.table_name == table_name
            )
        ).first()

        if not table:
            return {"nodes": [], "edges": [], "error": "Table not found"}

        nodes = []
        edges = []
        visited_nodes = set()
        visited_edges = set()

        # 中心节点
        center_node_id = f"table_{table.id}"
        nodes.append({
            "id": center_node_id,
            "label": table.table_name,
            "type": "table",
            "is_center": True,
            "database_name": table.database_name,
            "table_name": table.table_name,
            "row_count": table.row_count,
        })
        visited_nodes.add(center_node_id)

        # 递归查找上游和下游依赖
        self._find_lineage_dependencies(
            db, tenant_id, table, center_node_id,
            "upstream", depth, nodes, edges,
            visited_nodes, visited_edges
        )
        self._find_lineage_dependencies(
            db, tenant_id, table, center_node_id,
            "downstream", depth, nodes, edges,
            visited_nodes, visited_edges
        )

        return {
            "nodes": nodes,
            "edges": edges,
            "center_table": table_name,
            "statistics": {
                "upstream_count": sum(1 for e in edges if e.get("direction") == "upstream"),
                "downstream_count": sum(1 for e in edges if e.get("direction") == "downstream"),
            }
        }

    def _find_lineage_dependencies(
        self,
        db: Session,
        tenant_id: str,
        table: MetadataTable,
        source_node_id: str,
        direction: str,
        depth: int,
        nodes: List,
        edges: List,
        visited_nodes: Set,
        visited_edges: Set
    ):
        """递归查找血缘依赖"""
        if depth <= 0:
            return

        # 查询血缘边
        if direction == "upstream":
            # 查找上游（作为目标）
            lineage_edges = db.query(LineageEdge).filter(
                and_(
                    LineageEdge.tenant_id == tenant_id,
                    LineageEdge.target_node_id.like(f"%{table.table_name}%")
                )
            ).all()
        else:
            # 查找下游（作为源）
            lineage_edges = db.query(LineageEdge).filter(
                and_(
                    LineageEdge.tenant_id == tenant_id,
                    LineageEdge.source_node_id.like(f"%{table.table_name}%")
                )
            ).all()

        for edge in lineage_edges:
            # 确定关联的节点
            if direction == "upstream":
                related_node_id = edge.source_node_id
            else:
                related_node_id = edge.target_node_id

            edge_id = f"{edge.source_node_id}_{edge.target_node_id}"

            if edge_id in visited_edges:
                continue

            # 查找或创建关联节点
            if related_node_id not in visited_nodes:
                related_node = db.query(LineageNode).filter(
                    and_(
                        LineageNode.tenant_id == tenant_id,
                        LineageNode.node_id == related_node_id
                    )
                ).first()

                if related_node:
                    new_node_id = f"lineage_{related_node.id}"
                    visited_nodes.add(new_node_id)

                    nodes.append({
                        "id": new_node_id,
                        "label": related_node.name,
                        "type": related_node.node_type,  # table, column, dataset, job
                        "node_type": related_node.node_type,
                        "properties": {
                            "database_name": related_node.database_name,
                            "table_name": related_node.table_name,
                            "column_name": related_node.column_name,
                        }
                    })

                    # 添加边
                    if direction == "upstream":
                        edges.append({
                            "source": new_node_id,
                            "target": source_node_id,
                            "label": edge.relation_type,
                            "type": "lineage",
                            "direction": "upstream",
                            "relation_type": edge.relation_type,
                        })
                    else:
                        edges.append({
                            "source": source_node_id,
                            "target": new_node_id,
                            "label": edge.relation_type,
                            "type": "lineage",
                            "direction": "downstream",
                            "relation_type": edge.relation_type,
                        })

                    visited_edges.add(edge_id)

                    # 如果关联节点是表，递归查找
                    if related_node.node_type == "table":
                        related_table = db.query(MetadataTable).filter(
                            and_(
                                MetadataTable.tenant_id == tenant_id,
                                MetadataTable.table_name == related_node.table_name
                            )
                        ).first()

                        if related_table:
                            self._find_lineage_dependencies(
                                db, tenant_id, related_table, new_node_id,
                                direction, depth - 1, nodes, edges,
                                visited_nodes, visited_edges
                            )

    def build_column_relation_graph(
        self,
        db: Session,
        tenant_id: str,
        table_name: str
    ) -> Dict:
        """
        构建表的列关系图（外键关系、关联关系）
        """
        # 获取表的所有列
        columns = db.query(MetadataColumn).filter(
            and_(
                MetadataColumn.tenant_id == tenant_id,
                MetadataColumn.table_name == table_name
            )
        ).order_by(MetadataColumn.position).all()

        if not columns:
            return {"nodes": [], "edges": [], "error": "Table not found"}

        nodes = []
        edges = []
        node_id_map = {}

        # 创建列节点
        for col in columns:
            node_id = f"column_{col.id}"
            node_id_map[col.column_name] = node_id

            nodes.append({
                "id": node_id,
                "label": col.column_name,
                "type": "column",
                "data_type": col.data_type,
                "is_nullable": col.is_nullable,
                "position": col.position,
                "properties": {
                    "description": col.description,
                    "ai_description": col.ai_description,
                    "sensitivity_level": col.sensitivity_level,
                    "sensitivity_type": col.sensitivity_type,
                    "semantic_tags": col.semantic_tags,
                }
            })

        # 检测列之间的关联关系（基于名称模式）
        for i, col1 in enumerate(columns):
            for col2 in columns[i + 1:]:
                relation = self._detect_column_relation(col1, col2)
                if relation:
                    edges.append({
                        "source": node_id_map[col1.column_name],
                        "target": node_id_map[col2.column_name],
                        "label": relation["type"],
                        "type": "relation",
                        "strength": relation["strength"]
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "table_name": table_name,
        }

    def _detect_column_relation(self, col1: MetadataColumn, col2: MetadataColumn) -> Optional[Dict]:
        """检测两列之间的关联关系"""
        name1, name2 = col1.column_name.lower(), col2.column_name.lower()

        # 检测外键关系（id结尾的列与对应的名称列）
        if name1.endswith('_id') and name2.replace('_', '') == name1.replace('_id', ''):
            return {"type": "foreign_key", "strength": "strong"}
        if name2.endswith('_id') and name1.replace('_', '') == name2.replace('_id', ''):
            return {"type": "foreign_key", "strength": "strong"}

        # 检测时间戳关系（created_at/updated_at）
        time_cols = {'created_at', 'updated_at', 'deleted_at', 'timestamp'}
        if name1 in time_cols and name2 in time_cols:
            return {"type": "timestamp_pair", "strength": "weak"}

        # 检测名称相似性
        if name1 in name2 or name2 in name1:
            return {"type": "name_similarity", "strength": "weak"}

        return None

    def _build_lineage_graph(
        self,
        db: Session,
        tenant_id: str,
        node_id_map: Dict
    ) -> Tuple[List, List]:
        """从LineageEdge表构建血缘图"""
        nodes = []
        edges = []

        # 获取所有血缘节点
        lineage_nodes = db.query(LineageNode).filter(
            LineageNode.tenant_id == tenant_id
        ).all()

        # 为未在元数据中的血缘节点创建节点
        for ln in lineage_nodes:
            existing_key = f"{ln.node_type}:{ln.full_name or ln.name}"
            if existing_key not in node_id_map:
                node_id = f"lineage_{ln.id}"
                node_id_map[existing_key] = node_id

                nodes.append({
                    "id": node_id,
                    "label": ln.name,
                    "type": ln.node_type,
                    "node_type": ln.node_type,
                    "properties": {
                        "database_name": ln.database_name,
                        "table_name": ln.table_name,
                        "column_name": ln.column_name,
                        "description": ln.description,
                        "tags": ln.tags,
                    }
                })

        # 获取所有血缘边
        all_edges = db.query(LineageEdge).filter(
            LineageEdge.tenant_id == tenant_id
        ).all()

        for edge in all_edges:
            # 查找源和目标节点ID
            source_key = f"{edge.source_node_type}:{edge.source_node_name}"
            target_key = f"{edge.target_node_type}:{edge.target_node_name}"

            source_id = node_id_map.get(source_key)
            target_id = node_id_map.get(target_key)

            if source_id and target_id:
                # 检查是否已添加此边
                edge_key = f"{source_id}_{target_id}"
                if edge_key not in node_id_map:  # 复用node_id_map来追踪已添加的边
                    node_id_map[edge_key] = edge_key

                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "label": edge.relation_type,
                        "type": "lineage",
                        "properties": {
                            "transformation": edge.transformation,
                            "confidence": edge.confidence,
                        }
                    })

        return nodes, edges

    def _count_node_types(self, nodes: List[Dict]) -> Dict[str, int]:
        """统计各类型节点数量"""
        counts = {}
        for node in nodes:
            node_type = node.get("type", "unknown")
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def search_nodes(
        self,
        db: Session,
        tenant_id: str,
        query: str,
        node_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        搜索元数据节点

        返回匹配的节点列表
        """
        results = []
        query_lower = query.lower()

        # 搜索数据库
        if not node_types or "database" in node_types:
            databases = db.query(MetadataDatabase).filter(
                and_(
                    MetadataDatabase.tenant_id == tenant_id,
                    MetadataDatabase.database_name.like(f"%{query}%")
                )
            ).all()

            for db_obj in databases:
                results.append({
                    "id": f"db_{db_obj.id}",
                    "label": db_obj.database_name,
                    "type": "database",
                    "match_type": "name"
                })

        # 搜索表
        if not node_types or "table" in node_types:
            tables = db.query(MetadataTable).filter(
                and_(
                    MetadataTable.tenant_id == tenant_id,
                    or_(
                        MetadataTable.table_name.like(f"%{query}%"),
                        MetadataTable.description.like(f"%{query}%")
                    )
                )
            ).all()

            for table in tables:
                results.append({
                    "id": f"table_{table.id}",
                    "label": table.table_name,
                    "type": "table",
                    "database_name": table.database_name,
                    "match_type": "name" if query.lower() in table.table_name.lower() else "description"
                })

        # 搜索列
        if not node_types or "column" in node_types:
            columns = db.query(MetadataColumn).filter(
                and_(
                    MetadataColumn.tenant_id == tenant_id,
                    or_(
                        MetadataColumn.column_name.like(f"%{query}%"),
                        MetadataColumn.description.like(f"%{query}%"),
                        MetadataColumn.ai_description.like(f"%{query}%")
                    )
                )
            ).limit(100).all()

            for col in columns:
                results.append({
                    "id": f"column_{col.id}",
                    "label": col.column_name,
                    "type": "column",
                    "database_name": col.database_name,
                    "table_name": col.table_name,
                    "match_type": "name"
                })

        return results

    def get_impact_analysis(
        self,
        db: Session,
        tenant_id: str,
        node_id: str,
        node_type: str
    ) -> Dict:
        """
        获取影响分析

        当修改某个表/列时，分析会影响哪些下游节点
        """
        impacted_nodes = []
        impacted_edges = []

        # 查找所有下游边
        downstream_edges = db.query(LineageEdge).filter(
            and_(
                LineageEdge.tenant_id == tenant_id,
                LineageEdge.source_node_id.like(f"%{node_id}%")
            )
        ).all()

        visited = set()
        to_visit = [edge.target_node_id for edge in downstream_edges]

        while to_visit:
            current_id = to_visit.pop(0)
            if current_id in visited:
                continue

            visited.add(current_id)

            # 查找节点详情
            node = db.query(LineageNode).filter(
                and_(
                    LineageNode.tenant_id == tenant_id,
                    LineageNode.node_id == current_id
                )
            ).first()

            if node:
                impacted_nodes.append({
                    "id": f"lineage_{node.id}",
                    "label": node.name,
                    "type": node.node_type,
                    "full_name": node.full_name,
                })

                # 继续查找下游
                further_edges = db.query(LineageEdge).filter(
                    and_(
                        LineageEdge.tenant_id == tenant_id,
                        LineageEdge.source_node_id == current_id
                    )
                ).all()

                for edge in further_edges:
                    to_visit.append(edge.target_node_id)
                    impacted_edges.append({
                        "source": f"lineage_{node.id}",
                        "target": edge.target_node_id,
                        "type": edge.relation_type,
                    })

        return {
            "impacted_nodes": impacted_nodes,
            "impacted_edges": impacted_edges,
            "impact_count": len(impacted_nodes),
            "risk_levels": self._calculate_impact_risk(impacted_nodes)
        }

    def _calculate_impact_risk(self, nodes: List[Dict]) -> Dict:
        """计算影响风险等级"""
        risk_levels = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for node in nodes:
            node_type = node.get("type")
            if node_type == "table" or node_type == "dataset":
                # 如果是生产表或关键数据集，风险较高
                risk_levels["medium"] = risk_levels.get("medium", 0) + 1
            elif node_type == "job":
                risk_levels["high"] = risk_levels.get("high", 0) + 1

        return risk_levels

    def build_statistics_graph(
        self,
        db: Session,
        tenant_id: str
    ) -> Dict:
        """
        构建统计图谱（数据库/表的数量统计）
        """
        # 数据库统计
        db_count = db.query(MetadataDatabase).filter(
            MetadataDatabase.tenant_id == tenant_id
        ).count()

        # 表统计
        table_count = db.query(MetadataTable).filter(
            MetadataTable.tenant_id == tenant_id
        ).count()

        # 列统计
        column_count = db.query(MetadataColumn).filter(
            MetadataColumn.tenant_id == tenant_id
        ).count()

        # 按数据库分组的表数量
        table_stats = db.query(
            MetadataTable.database_name,
            func.count(MetadataTable.id).label("count")
        ).filter(
            MetadataTable.tenant_id == tenant_id
        ).group_by(MetadataTable.database_name).all()

        return {
            "databases": db_count,
            "tables": table_count,
            "columns": column_count,
            "tables_per_database": [
                {"database": row.database_name, "count": row.count}
                for row in table_stats
            ]
        }

    def get_node_neighbors(
        self,
        db: Session,
        tenant_id: str,
        node_id: str,
        node_type: str,
        depth: int = 1
    ) -> Dict:
        """
        获取节点的邻居

        返回指定节点的直接关联节点
        """
        neighbors = {"nodes": [], "edges": []}

        if node_type == "table":
            # 获取表的数据库和列
            table = db.query(MetadataTable).filter(
                and_(
                    MetadataTable.tenant_id == tenant_id,
                    MetadataTable.id == int(node_id) if node_id.isdigit() else True
                )
            ).first()

            if not table:
                return {"nodes": [], "edges": [], "error": "Table not found"}

            # 父节点（数据库）
            database = db.query(MetadataDatabase).filter(
                and_(
                    MetadataDatabase.tenant_id == tenant_id,
                    MetadataDatabase.database_name == table.database_name
                )
            ).first()

            if database:
                db_node_id = f"db_{database.id}"
                table_node_id = f"table_{node_id}"
                neighbors["nodes"].append({
                    "id": db_node_id,
                    "label": database.database_name,
                    "type": "database",
                    "relation": "parent"
                })
                neighbors["edges"].append({
                    "source": db_node_id,
                    "target": table_node_id,
                    "label": "contains",
                    "type": "hierarchy"
                })

            # 子节点（列）
            columns = db.query(MetadataColumn).filter(
                and_(
                    MetadataColumn.tenant_id == tenant_id,
                    MetadataColumn.table_name == table.table_name,
                    MetadataColumn.database_name == table.database_name
                )
            ).limit(100).all()

            for col in columns:
                col_node_id = f"column_{col.id}"
                table_node_id = f"table_{node_id}"
                neighbors["nodes"].append({
                    "id": col_node_id,
                    "label": col.column_name,
                    "type": "column",
                    "relation": "child",
                    "data_type": col.data_type
                })
                neighbors["edges"].append({
                    "source": table_node_id,
                    "target": col_node_id,
                    "label": "",
                    "type": "hierarchy",
                    "position": col.position
                })

        elif node_type == "column":
            # 获取列所属的表
            column = db.query(MetadataColumn).filter(
                and_(
                    MetadataColumn.tenant_id == tenant_id,
                    MetadataColumn.id == int(node_id) if node_id.isdigit() else True
                )
            ).first()

            if column:
                table = db.query(MetadataTable).filter(
                    and_(
                        MetadataTable.tenant_id == tenant_id,
                        MetadataTable.table_name == column.table_name,
                        MetadataTable.database_name == column.database_name
                    )
                ).first()

                if table:
                    table_node_id = f"table_{table.id}"
                    col_node_id = f"column_{node_id}"
                    neighbors["nodes"].append({
                        "id": table_node_id,
                        "label": table.table_name,
                        "type": "table",
                        "relation": "parent"
                    })
                    neighbors["edges"].append({
                        "source": table_node_id,
                        "target": col_node_id,
                        "label": "",
                        "type": "hierarchy"
                    })

        return neighbors
