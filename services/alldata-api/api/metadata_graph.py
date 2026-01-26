"""
元数据图谱API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import get_db
from services.metadata_graph_builder import MetadataGraphBuilder

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
graph_builder = MetadataGraphBuilder()


class GraphNode(BaseModel):
    """图节点"""
    id: str
    label: str
    type: str
    database_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    data_type: Optional[str] = None
    description: Optional[str] = None
    is_center: Optional[bool] = False
    properties: Optional[dict] = None


class GraphEdge(BaseModel):
    """图边"""
    source: str
    target: str
    label: Optional[str] = None
    type: str
    direction: Optional[str] = None
    relation_type: Optional[str] = None
    properties: Optional[dict] = None


class MetadataGraphResponse(BaseModel):
    """元数据图谱响应"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    statistics: Optional[dict] = None


@router.get("/graph")
async def get_metadata_graph(
    tenant_id: str = Query("default"),
    node_types: Optional[str] = Query(None, description="节点类型，逗号分隔: database,table,column"),
    include_lineage: bool = Query(True, description="是否包含血缘关系"),
    db: Session = Depends(get_db)
):
    """
    获取完整的元数据图谱

    返回数据库、表、列的层次结构以及它们之间的关系
    """
    node_type_list = None
    if node_types:
        node_type_list = [t.strip() for t in node_types.split(",")]

    try:
        graph_data = graph_builder.build_full_graph(
            db, tenant_id, node_type_list, include_lineage
        )
        return graph_data
    except Exception as e:
        logger.error(f"Failed to build metadata graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/lineage/{table_name}")
async def get_table_lineage_graph(
    table_name: str,
    tenant_id: str = Query("default"),
    depth: int = Query(3, ge=1, le=5, description="血缘层级深度"),
    db: Session = Depends(get_db)
):
    """
    获取单个表的数据血缘图谱

    返回该表的上游依赖和下游被依赖
    """
    try:
        lineage_data = graph_builder.build_table_lineage_graph(
            db, tenant_id, table_name, depth
        )
        return lineage_data
    except Exception as e:
        logger.error(f"Failed to build table lineage graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/columns/{table_name}")
async def get_column_relation_graph(
    table_name: str,
    tenant_id: str = Query("default"),
    db: Session = Depends(get_db)
):
    """
    获取表的列关系图

    返回表内列之间的关系（外键、关联等）
    """
    try:
        column_data = graph_builder.build_column_relation_graph(
            db, tenant_id, table_name
        )
        return column_data
    except Exception as e:
        logger.error(f"Failed to build column relation graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/search")
async def search_metadata_nodes(
    query: str = Query(..., description="搜索关键词"),
    tenant_id: str = Query("default"),
    node_types: Optional[str] = Query(None, description="节点类型筛选"),
    db: Session = Depends(get_db)
):
    """
    搜索元数据节点

    支持按名称、描述搜索数据库、表、列
    """
    node_type_list = None
    if node_types:
        node_type_list = [t.strip() for t in node_types.split(",")]

    try:
        results = graph_builder.search_nodes(
            db, tenant_id, query, node_type_list
        )
        return {
            "query": query,
            "total": len(results),
            "nodes": results
        }
    except Exception as e:
        logger.error(f"Failed to search metadata nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/impact/{node_type}/{node_id}")
async def get_impact_analysis(
    node_type: str,
    node_id: str,
    tenant_id: str = Query("default"),
    db: Session = Depends(get_db)
):
    """
    获取影响分析

    分析当修改指定节点时，会影响哪些下游节点
    """
    try:
        impact_data = graph_builder.get_impact_analysis(
            db, tenant_id, node_id, node_type
        )
        return impact_data
    except Exception as e:
        logger.error(f"Failed to get impact analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/statistics")
async def get_graph_statistics(
    tenant_id: str = Query("default"),
    db: Session = Depends(get_db)
):
    """
    获取元数据统计信息

    返回数据库、表、列的数量统计
    """
    try:
        stats = graph_builder.build_statistics_graph(db, tenant_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get graph statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/neighbors/{node_type}/{node_id}")
async def get_node_neighbors(
    node_type: str,
    node_id: str,
    tenant_id: str = Query("default"),
    depth: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db)
):
    """
    获取节点的邻居

    返回指定节点的直接关联节点
    """
    # 实现邻居节点查询
    neighbors = {"nodes": [], "edges": []}

    if node_type == "table":
        # 获取表的数据库和列
        from models.metadata import MetadataTable, MetadataDatabase, MetadataColumn

        table = db.query(MetadataTable).filter(
            MetadataTable.tenant_id == tenant_id,
            MetadataTable.id == node_id
        ).first()

        if not table:
            raise HTTPException(status_code=404, detail="Table not found")

        # 父节点（数据库）
        database = db.query(MetadataDatabase).filter(
            MetadataDatabase.tenant_id == tenant_id,
            MetadataDatabase.database_name == table.database_name
        ).first()

        if database:
            neighbors["nodes"].append({
                "id": f"db_{database.id}",
                "label": database.database_name,
                "type": "database",
                "relation": "parent"
            })
            neighbors["edges"].append({
                "source": f"db_{database.id}",
                "target": f"table_{node_id}",
                "label": "contains",
                "type": "hierarchy"
            })

        # 子节点（列）
        columns = db.query(MetadataColumn).filter(
            MetadataColumn.tenant_id == tenant_id,
            MetadataColumn.table_name == table.table_name,
            MetadataColumn.database_name == table.database_name
        ).limit(100).all()

        for col in columns:
            neighbors["nodes"].append({
                "id": f"column_{col.id}",
                "label": col.column_name,
                "type": "column",
                "relation": "child",
                "data_type": col.data_type
            })
            neighbors["edges"].append({
                "source": f"table_{node_id}",
                "target": f"column_{col.id}",
                "label": "",
                "type": "hierarchy",
                "position": col.position
            })

    return neighbors
