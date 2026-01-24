"""
向量存储服务
基于 Milvus 实现向量存取功能
Phase 6: Sprint 6.2
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
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


class VectorStore:
    """Milvus 向量存储服务"""

    _connected = False

    def __init__(self):
        """初始化向量存储"""
        if not self._connected:
            self._connect()
            VectorStore._connected = True

    def _connect(self):
        """连接 Milvus"""
        try:
            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT
            )
            logger.info(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
        except Exception as e:
            logger.warning(f"Failed to connect to Milvus: {e}")
            # 在开发模式下继续运行，使用内存存储
            self._memory_store = {}

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

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index("embedding", index_params)

        # 为 doc_id 字段创建索引以加速删除查询
        collection.create_index("doc_id", index_params={"index_type": "INVERTED"})

        return collection

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
               top_k: int = 5, output_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        向量相似度搜索

        Args:
            collection_name: 集合名称
            query_embedding: 查询向量
            top_k: 返回结果数量
            output_fields: 返回的字段列表

        Returns:
            搜索结果列表
        """
        if not utility.has_collection(collection_name):
            return []

        collection = Collection(collection_name)
        collection.load()

        # 执行搜索
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=top_k,
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

        return formatted_results

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
