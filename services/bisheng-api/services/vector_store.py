"""
向量存储服务
基于 Milvus 实现向量存取功能

Sprint 8: 性能优化
- 分页支持
- 搜索结果缓存
- 索引参数优化
"""

import logging
import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)

logger = logging.getLogger(__name__)

# 配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))  # OpenAI ada-002 维度

# Sprint 8: 索引参数优化
INDEX_TYPE = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
METRIC_TYPE = os.getenv("MILVUS_METRIC_TYPE", "L2")
NLIST = int(os.getenv("MILVUS_NLIST", "128"))  # IVF 索引的聚类中心数量
NPROBE = int(os.getenv("MILVUS_NPROBE", "16"))  # 搜索时探测的聚类中心数量

# Sprint 8: 搜索结果缓存
SEARCH_CACHE_SIZE = int(os.getenv("VECTOR_SEARCH_CACHE_SIZE", "1000"))
SEARCH_CACHE_TTL = int(os.getenv("VECTOR_SEARCH_CACHE_TTL", "60"))  # 秒


class VectorStore:
    """Milvus 向量存储服务 - Sprint 8: 优化版本"""

    _connected = False
    _search_cache: Dict[str, Tuple[Any, float]] = {}

    def __init__(self):
        """初始化向量存储"""
        if not self._connected:
            self._connect()
            VectorStore._connected = True

    def create_collection(self, name: str, dimension: int = EMBEDDING_DIM, drop_existing: bool = False):
        """
        创建向量集合

        Args:
            name: 集合名称
            dimension: 向量维度
            drop_existing: 是否删除已存在的集合

        Returns:
            Collection 对象
        """
        # 如果集合存在且需要删除
        if utility.has_collection(name):
            if drop_existing:
                utility.drop_collection(name)
            else:
                return Collection(name)

        # 定义字段（添加 doc_id 字段用于按文档删除）
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
        ]

        # 创建 Schema
        schema = CollectionSchema(fields, f"{name} collection")

        # 创建集合
        collection = Collection(name, schema)

        # Sprint 8: 创建优化的索引
        index_params = {
            "index_type": INDEX_TYPE,
            "metric_type": METRIC_TYPE,
            "params": {"nlist": NLIST}
        }
        collection.create_index("embedding", index_params)
        logger.info(f"Created index for {name}: {INDEX_TYPE}, nlist={NLIST}, metric={METRIC_TYPE}")

        # 为 doc_id 字段创建索引以加速删除查询
        collection.create_index("doc_id", index_params={"index_type": "INVERTED"})

        return collection

    def _get_cache_key(self, collection_name: str, query_embedding: List[float],
                       top_k: int, filters: Optional[Dict] = None) -> str:
        """生成缓存键 - Sprint 8"""
        # 对向量进行哈希以减少键的大小
        embedding_str = ",".join(f"{x:.4f}" for x in query_embedding[:10])  # 只用前10维
        filter_str = json.dumps(filters, sort_keys=True) if filters else ""
        cache_key = f"{collection_name}:{top_k}:{hashlib.md5((embedding_str + filter_str).encode()).hexdigest()}"
        return cache_key

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """从缓存获取结果 - Sprint 8"""
        import time
        if cache_key in VectorStore._search_cache:
            result, timestamp = VectorStore._search_cache[cache_key]
            if time.time() - timestamp < SEARCH_CACHE_TTL:
                logger.debug(f"Cache hit: {cache_key}")
                return result
            else:
                # 过期，删除
                del VectorStore._search_cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: List[Dict]):
        """设置缓存 - Sprint 8"""
        import time
        # LRU: 如果缓存满了，删除最旧的
        if len(VectorStore._search_cache) >= SEARCH_CACHE_SIZE:
            oldest_key = min(VectorStore._search_cache.keys(),
                           key=lambda k: VectorStore._search_cache[k][1])
            del VectorStore._search_cache[oldest_key]

        VectorStore._search_cache[cache_key] = (result, time.time())

    def clear_search_cache(self):
        """清空搜索缓存 - Sprint 8"""
        VectorStore._search_cache.clear()
        logger.info("Vector search cache cleared")

    def insert(self, collection_name: str, texts: List[str],
               embeddings: List[List[float]], metadata: List[Dict] = None) -> int:
        """
        插入文档向量

        Args:
            collection_name: 集合名称
            texts: 文本列表
            embeddings: 向量列表
            metadata: 元数据列表（每个元数据应包含 doc_id 用于按文档删除）

        Returns:
            插入的文档数量
        """
        # 如果集合不存在，创建它
        if not utility.has_collection(collection_name):
            self.create_collection(collection_name)

        collection = Collection(collection_name)

        # 准备数据
        ids = [f"{collection_name}-{i}" for i in range(len(texts))]
        metadata_json = [json.dumps(m or {}, ensure_ascii=False) for m in (metadata or [{}] * len(texts))]
        # 从 metadata 中提取 doc_id（如果存在）
        doc_ids = [m.get("doc_id", "") for m in (metadata or [{}] * len(texts))]

        # 插入数据（新 schema: id, doc_id, embedding, text, metadata）
        data = [ids, doc_ids, embeddings, texts, metadata_json]
        collection.insert(data)

        # 刷新以确保数据可搜索
        collection.flush()

        # 加载集合到内存
        collection.load()

        return len(texts)

    def search(self, collection_name: str, query_embedding: List[float],
               top_k: int = 5, output_fields: List[str] = None,
               use_cache: bool = True, offset: int = 0) -> Dict[str, Any]:
        """
        向量相似度搜索 - Sprint 8: 优化版本

        Args:
            collection_name: 集合名称
            query_embedding: 查询向量
            top_k: 返回结果数量
            output_fields: 返回的字段列表
            use_cache: 是否使用缓存
            offset: 分页偏移量

        Returns:
            包含结果和元数据的字典
        """
        if not utility.has_collection(collection_name):
            return {"results": [], "total": 0, "offset": offset, "limit": top_k}

        # Sprint 8: 检查缓存
        cache_key = None
        if use_cache and offset == 0:  # 只缓存第一页
            cache_key = self._get_cache_key(collection_name, query_embedding, top_k)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return {
                    "results": cached_result[:top_k],
                    "total": len(cached_result),
                    "offset": offset,
                    "limit": top_k,
                    "cached": True
                }

        collection = Collection(collection_name)
        collection.load()

        # Sprint 8: 优化的搜索参数
        # 对于分页，我们需要获取更多结果
        search_limit = top_k + offset

        # 执行搜索
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": METRIC_TYPE, "params": {"nprobe": NPROBE}},
            limit=search_limit,
            output_fields=output_fields or ["text", "metadata"]
        )

        # 格式化结果
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "score": float(hit.score),
                "text": hit.entity.get("text", ""),
                "metadata": json.loads(hit.entity.get("metadata", "{}"))
            })

        # 应用分页
        paginated_results = formatted_results[offset:offset + top_k]

        # Sprint 8: 缓存完整结果（仅第一页）
        if use_cache and offset == 0 and cache_key:
            self._set_cache(cache_key, formatted_results)

        return {
            "results": paginated_results,
            "total": len(formatted_results),
            "offset": offset,
            "limit": top_k,
            "cached": False
        }

    def search_batch(self, collection_name: str, query_embeddings: List[List[float]],
                     top_k: int = 5, output_fields: List[str] = None) -> List[List[Dict[str, Any]]]:
        """
        批量向量搜索 - Sprint 8: 新增

        Args:
            collection_name: 集合名称
            query_embeddings: 查询向量列表
            top_k: 每个查询返回的结果数量
            output_fields: 返回的字段列表

        Returns:
            二维结果列表，每个查询对应一个结果列表
        """
        if not utility.has_collection(collection_name):
            return [[] for _ in query_embeddings]

        collection = Collection(collection_name)
        collection.load()

        # 执行批量搜索
        results = collection.search(
            data=query_embeddings,
            anns_field="embedding",
            param={"metric_type": METRIC_TYPE, "params": {"nprobe": NPROBE}},
            limit=top_k,
            output_fields=output_fields or ["text", "metadata"]
        )

        # 格式化结果
        all_results = []
        for query_results in results:
            formatted_results = []
            for hit in query_results:
                formatted_results.append({
                    "id": hit.id,
                    "score": float(hit.score),
                    "text": hit.entity.get("text", ""),
                    "metadata": json.loads(hit.entity.get("metadata", "{}"))
                })
            all_results.append(formatted_results)

        return all_results

    def delete(self, collection_name: str, ids: List[str] = None) -> int:
        """
        删除文档

        Args:
            collection_name: 集合名称
            ids: 要删除的文档ID列表

        Returns:
            删除的文档数量
        """
        if not utility.has_collection(collection_name):
            return 0

        collection = Collection(collection_name)

        if ids:
            collection.delete(f"id in {ids}")

        return len(ids) if ids else 0

    def delete_by_doc_id(self, collection_name: str, doc_id: str) -> bool:
        """
        按文档ID删除对应的向量数据

        Args:
            collection_name: 集合名称
            doc_id: 文档ID (metadata中存储的doc_id)

        Returns:
            bool: 删除是否成功
        """
        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                return False

            collection = Collection(collection_name)
            # 使用 metadata 过滤删除所有属于该文档的向量
            # Milvus 的表达式语法：doc_id == "xxx"
            collection.delete(expr=f'doc_id == "{doc_id}"')
            # 刷新以确保删除生效
            collection.flush()
            return True
        except Exception as e:
            logger.error(f"删除向量失败: collection={collection_name}, doc_id={doc_id}, error={e}")
            return False

    def drop_collection(self, collection_name: str):
        """删除集合"""
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return utility.list_collections()

    def collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        if not utility.has_collection(collection_name):
            return {"exists": False}

        collection = Collection(collection_name)
        collection.load()

        return {
            "exists": True,
            "name": collection_name,
            "num_entities": collection.num_entities,
            "schema": {
                "fields": [
                    {
                        "name": f.name,
                        "type": str(f.dtype),
                        "is_primary": f.is_primary
                    }
                    for f in collection.schema.fields
                ]
            }
        }
