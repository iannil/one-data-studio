"""
Mock Milvus 向量存储服务
模拟向量数据库的操作
"""

import pytest
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class MilvusCollection:
    """Milvus 集合"""
    name: str
    dimension: int
    index_type: str = "IVF_FLAT"
    metric_type: str = "L2"
    description: str = ""
    entities: List[Dict] = field(default_factory=list)

    # 统计信息
    row_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """搜索结果"""
    id: int
    score: float
    metadata: Dict = field(default_factory=dict)


class MockMilvusClient:
    """
    Mock Milvus 客户端

    模拟向量数据库的行为，支持:
    - 集合管理（创建、删除、列出）
    - 数据插入、删除、查询
    - 向量检索（相似度搜索）
    - 索引管理
    """

    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.collections: Dict[str, MilvusCollection] = {}
        self._id_counter = 1
        self._call_history: List[Dict] = []

    def _record_call(self, method: str, **kwargs):
        """记录调用历史"""
        self._call_history.append({
            'method': method,
            'params': kwargs,
            'timestamp': datetime.utcnow().isoformat()
        })

    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度
            index_type: 索引类型
            metric_type: 距离度量类型
            description: 描述

        Returns:
            创建结果
        """
        self._record_call(
            'create_collection',
            collection_name=collection_name,
            dimension=dimension,
            index_type=index_type,
            metric_type=metric_type
        )

        if collection_name in self.collections:
            return {'success': False, 'error': f'Collection {collection_name} already exists'}

        collection = MilvusCollection(
            name=collection_name,
            dimension=dimension,
            index_type=index_type,
            metric_type=metric_type,
            description=description
        )
        self.collections[collection_name] = collection

        return {
            'success': True,
            'collection_name': collection_name,
            'dimension': dimension
        }

    async def drop_collection(self, collection_name: str) -> Dict[str, Any]:
        """删除集合"""
        self._record_call('drop_collection', collection_name=collection_name)

        if collection_name not in self.collections:
            return {'success': False, 'error': f'Collection {collection_name} not found'}

        del self.collections[collection_name]
        return {'success': True}

    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        self._record_call('list_collections')
        return list(self.collections.keys())

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合信息"""
        self._record_call('get_collection_info', collection_name=collection_name)

        if collection_name not in self.collections:
            return None

        collection = self.collections[collection_name]
        return {
            'name': collection.name,
            'dimension': collection.dimension,
            'index_type': collection.index_type,
            'metric_type': collection.metric_type,
            'row_count': collection.row_count,
            'description': collection.description,
            'created_at': collection.created_at.isoformat()
        }

    async def insert(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        metadata: Optional[List[Dict]] = None,
        ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        插入向量数据

        Args:
            collection_name: 集合名称
            embeddings: 向量列表
            metadata: 元数据列表
            ids: 指定ID列表

        Returns:
            插入结果
        """
        self._record_call(
            'insert',
            collection_name=collection_name,
            count=len(embeddings)
        )

        if collection_name not in self.collections:
            return {'success': False, 'error': f'Collection {collection_name} not found'}

        collection = self.collections[collection_name]

        # 验证向量维度
        if embeddings and len(embeddings[0]) != collection.dimension:
            return {'success': False, 'error': f'Vector dimension mismatch'}

        insert_ids = []
        for i, embedding in enumerate(embeddings):
            entity_id = ids[i] if ids and i < len(ids) else self._id_counter
            self._id_counter = max(self._id_counter, entity_id + 1)

            entity = {
                'id': entity_id,
                'vector': embedding,
                'metadata': metadata[i] if metadata and i < len(metadata) else {}
            }
            collection.entities.append(entity)
            insert_ids.append(entity_id)

        collection.row_count += len(embeddings)

        return {
            'success': True,
            'insert_count': len(embeddings),
            'ids': insert_ids
        }

    async def delete(
        self,
        collection_name: str,
        ids: Optional[List[int]] = None,
        expr: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        删除向量数据

        Args:
            collection_name: 集合名称
            ids: 要删除的ID列表
            expr: 删除表达式

        Returns:
            删除结果
        """
        self._record_call(
            'delete',
            collection_name=collection_name,
            ids=ids,
            expr=expr
        )

        if collection_name not in self.collections:
            return {'success': False, 'error': f'Collection {collection_name} not found'}

        collection = self.collections[collection_name]

        if ids:
            # 按 ID 删除
            original_count = len(collection.entities)
            collection.entities = [e for e in collection.entities if e['id'] not in ids]
            deleted_count = original_count - len(collection.entities)
        elif expr:
            # 按表达式删除（简化实现）
            deleted_count = 0
            # 这里可以实现更复杂的表达式解析
        else:
            deleted_count = 0

        collection.row_count -= deleted_count

        return {
            'success': True,
            'deleted_count': deleted_count
        }

    async def search(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        top_k: int = 10,
        expr: Optional[str] = None,
        output_fields: Optional[List[str]] = None
    ) -> List[List[SearchResult]]:
        """
        向量相似度搜索

        Args:
            collection_name: 集合名称
            query_vectors: 查询向量列表
            top_k: 返回top-k结果
            expr: 过滤表达式
            output_fields: 输出字段列表

        Returns:
            搜索结果列表
        """
        self._record_call(
            'search',
            collection_name=collection_name,
            top_k=top_k,
            query_count=len(query_vectors)
        )

        if collection_name not in self.collections:
            return []

        collection = self.collections[collection_name]
        results = []

        for query_vector in query_vectors:
            # 计算相似度（使用简化的欧氏距离）
            scored_entities = []
            for entity in collection.entities:
                # 简化的距离计算
                distance = self._calculate_distance(
                    query_vector,
                    entity['vector'],
                    collection.metric_type
                )
                # 转换为相似度分数
                score = 1.0 / (1.0 + distance)
                scored_entities.append(SearchResult(
                    id=entity['id'],
                    score=score,
                    metadata=entity.get('metadata', {})
                ))

            # 排序并取 top-k
            scored_entities.sort(key=lambda x: x.score, reverse=True)
            results.append(scored_entities[:top_k])

        return results

    def _calculate_distance(
        self,
        vec1: List[float],
        vec2: List[float],
        metric_type: str
    ) -> float:
        """计算向量距离"""
        if len(vec1) != len(vec2):
            return float('inf')

        if metric_type == "L2":
            # 欧氏距离
            return sum((a - b) ** 2 for a, b in zip(vec1, vec2)) ** 0.5
        elif metric_type == "IP":
            # 内积（转换为距离）
            return 1.0 - sum(a * b for a, b in zip(vec1, vec2))
        elif metric_type == "COSINE":
            # 余弦距离
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a ** 2 for a in vec1) ** 0.5
            norm2 = sum(b ** 2 for b in vec2) ** 0.5
            if norm1 == 0 or norm2 == 0:
                return 1.0
            return 1.0 - dot_product / (norm1 * norm2)
        else:
            return 0.0

    async def query(
        self,
        collection_name: str,
        expr: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        查询数据（按表达式）

        Args:
            collection_name: 集合名称
            expr: 查询表达式
            limit: 返回数量限制

        Returns:
            查询结果列表
        """
        self._record_call(
            'query',
            collection_name=collection_name,
            expr=expr,
            limit=limit
        )

        if collection_name not in self.collections:
            return []

        collection = self.collections[collection_name]
        # 简化实现：返回所有实体
        return collection.entities[:limit]

    async def count(self, collection_name: str) -> int:
        """统计集合中实体数量"""
        self._record_call('count', collection_name=collection_name)

        if collection_name not in self.collections:
            return 0

        return self.collections[collection_name].row_count

    async def create_index(
        self,
        collection_name: str,
        index_type: str = "IVF_FLAT",
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建索引"""
        self._record_call(
            'create_index',
            collection_name=collection_name,
            index_type=index_type
        )

        if collection_name not in self.collections:
            return {'success': False, 'error': f'Collection {collection_name} not found'}

        collection = self.collections[collection_name]
        collection.index_type = index_type

        return {'success': True, 'index_type': index_type}

    async def load_collection(self, collection_name: str) -> Dict[str, Any]:
        """加载集合到内存"""
        self._record_call('load_collection', collection_name=collection_name)
        return {'success': True}

    async def release_collection(self, collection_name: str) -> Dict[str, Any]:
        """释放集合"""
        self._record_call('release_collection', collection_name=collection_name)
        return {'success': True}

    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self._call_history

    def reset(self):
        """重置客户端状态"""
        self.collections.clear()
        self._id_counter = 1
        self._call_history.clear()


@pytest.fixture
def mock_milvus_client():
    """Mock Milvus 客户端 fixture"""
    client = MockMilvusClient()
    return client


@pytest.fixture
async def mock_milvus_with_collection(mock_milvus_client):
    """带有预创建集合的 Milvus fixture"""
    collection_name = "test_collection"
    await mock_milvus_client.create_collection(
        collection_name=collection_name,
        dimension=1536,
        index_type="HNSW",
        metric_type="COSINE"
    )

    # 插入一些测试数据
    embeddings = [[0.1] * 1536 for _ in range(5)]
    metadata = [
        {'doc_id': 'doc_001', 'content': '测试内容1'},
        {'doc_id': 'doc_002', 'content': '测试内容2'},
        {'doc_id': 'doc_003', 'content': '测试内容3'},
        {'doc_id': 'doc_004', 'content': '测试内容4'},
        {'doc_id': 'doc_005', 'content': '测试内容5'},
    ]
    await mock_milvus_client.insert(collection_name, embeddings, metadata)

    return mock_milvus_client, collection_name
