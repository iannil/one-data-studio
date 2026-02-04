"""
向量存储服务
基于 Milvus 实现向量存取功能

Sprint 8: 性能优化
- 分页支持
- 搜索结果缓存
- 索引参数优化

Production: 高可用支持
- 多主机故障转移
- 连接池管理
- 自动重连
"""

import logging
import os
import json
import hashlib
import time
import uuid
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
# 支持多主机配置，逗号分隔: "host1:19530,host2:19530,host3:19530"
MILVUS_HOSTS = os.getenv("MILVUS_HOSTS", os.getenv("MILVUS_HOST", "localhost"))
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

# 解析主机列表
def _parse_hosts(hosts_str: str, default_port: str) -> List[Tuple[str, str]]:
    """解析主机列表字符串"""
    result = []
    for host in hosts_str.split(","):
        host = host.strip()
        if ":" in host:
            h, p = host.split(":", 1)
            result.append((h.strip(), p.strip()))
        else:
            result.append((host, default_port))
    return result or [("localhost", default_port)]

MILVUS_ENDPOINTS = _parse_hosts(MILVUS_HOSTS, MILVUS_PORT)
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))  # OpenAI ada-002 维度

# Sprint 8: 索引参数优化
INDEX_TYPE = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
METRIC_TYPE = os.getenv("MILVUS_METRIC_TYPE", "L2")
NLIST = int(os.getenv("MILVUS_NLIST", "128"))  # IVF 索引的聚类中心数量
NPROBE = int(os.getenv("MILVUS_NPROBE", "16"))  # 搜索时探测的聚类中心数量

# Sprint 8: 搜索结果缓存
SEARCH_CACHE_SIZE = int(os.getenv("VECTOR_SEARCH_CACHE_SIZE", "1000"))
SEARCH_CACHE_TTL = int(os.getenv("VECTOR_SEARCH_CACHE_TTL", "60"))  # 秒

# Production: 故障转移配置
FAILOVER_ENABLED = os.getenv("MILVUS_FAILOVER_ENABLED", "true").lower() == "true"
FAILOVER_TIMEOUT = int(os.getenv("MILVUS_FAILOVER_TIMEOUT", "5"))  # 秒
HEALTH_CHECK_INTERVAL = int(os.getenv("MILVUS_HEALTH_CHECK_INTERVAL", "30"))  # 秒


class VectorStore:
    """
    Milvus 向量存储服务 - Production: 高可用版本

    功能：
    - 多主机故障转移
    - 连接健康检查
    - 自动重连
    - 搜索结果缓存 (Sprint 8)
    """

    _connected = False
    _search_cache: Dict[str, Tuple[Any, float]] = {}
    _connection_alias = "default"
    _max_retries = 3
    _retry_delay = 1.0  # 秒

    # Production: 故障转移状态
    _current_endpoint_index = 0
    _endpoints = MILVUS_ENDPOINTS
    _endpoint_health: Dict[str, float] = {}  # endpoint -> last healthy timestamp
    _last_health_check = 0

    def __init__(self):
        """初始化向量存储"""
        if not self._connected:
            self._connect()
            VectorStore._connected = True

    def _connect(self, retry_count: int = 0, failover_index: int = 0):
        """
        连接到 Milvus 服务器 - Production: 支持故障转移

        Args:
            retry_count: 当前重试次数
            failover_index: 故障转移端点索引

        功能：
        - 建立 Milvus 连接
        - 支持多主机故障转移
        - 连接重试
        - 健康检查
        """
        try:
            # 检查是否已有活跃连接
            if self._check_connection():
                logger.info("Milvus connection already active")
                return

            # 断开旧连接（如果存在）
            try:
                connections.disconnect(self._connection_alias)
            except Exception:
                pass

            # Production: 选择端点 (故障转移)
            if FAILOVER_ENABLED and self._endpoints:
                host, port = self._endpoints[failover_index % len(self._endpoints)]
                VectorStore._current_endpoint_index = failover_index % len(self._endpoints)
            else:
                host, port = self._endpoints[0] if self._endpoints else ("localhost", "19530")

            # 建立新连接
            logger.info(f"Connecting to Milvus at {host}:{port} (endpoint {failover_index + 1}/{len(self._endpoints)})")
            connections.connect(
                alias=self._connection_alias,
                host=host,
                port=int(port),
                timeout=FAILOVER_TIMEOUT
            )

            # 验证连接
            if self._check_connection():
                logger.info(f"Successfully connected to Milvus at {host}:{port}")
                VectorStore._connected = True
                # 标记端点健康
                self._endpoint_health[f"{host}:{port}"] = time.time()
            else:
                raise ConnectionError("Connection verification failed")

        except Exception as e:
            logger.error(f"Failed to connect to Milvus at endpoint {failover_index}: {e}")

            # Production: 尝试故障转移到下一个端点
            if FAILOVER_ENABLED and failover_index + 1 < len(self._endpoints):
                logger.warning(f"Failing over to next endpoint ({failover_index + 2}/{len(self._endpoints)})")
                time.sleep(self._retry_delay)
                self._connect(0, failover_index + 1)
            elif retry_count < self._max_retries - 1:
                # 端点重试
                time.sleep(self._retry_delay * (retry_count + 1))
                self._connect(retry_count + 1, failover_index)
            else:
                logger.error(f"Max retries ({self._max_retries}) exceeded. All endpoints failed.")
                VectorStore._connected = False
                raise ConnectionError(f"Unable to connect to Milvus after trying {len(self._endpoints)} endpoints: {e}")

    def _check_connection(self) -> bool:
        """
        检查 Milvus 连接是否活跃

        Returns:
            bool: 连接是否有效
        """
        try:
            # 尝试列出集合以验证连接
            utility.list_collections()
            return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False

    def _ensure_connection(self):
        """
        确保连接有效，如果无效则重新连接

        用于在每次操作前检查连接状态
        """
        if not self._check_connection():
            logger.warning("Milvus connection lost, attempting to reconnect...")
            VectorStore._connected = False
            self._connect()

    def reconnect(self):
        """
        强制重新连接

        可用于手动触发重连
        """
        VectorStore._connected = False
        self._connect()

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: 包含连接状态和服务器信息的字典
        """
        try:
            is_connected = self._check_connection()
            collections = []
            server_version = "unknown"

            if is_connected:
                collections = utility.list_collections()
                # 尝试获取服务器版本（如果API支持）
                try:
                    server_version = utility.get_server_version()
                except Exception:
                    pass

            current_host, current_port = self._endpoints[self._current_endpoint_index]
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "host": current_host,
                "port": current_port,
                "server_version": server_version,
                "collections_count": len(collections),
                "collections": collections[:10],  # 最多返回10个
                "index_type": INDEX_TYPE,
                "metric_type": METRIC_TYPE,
                "embedding_dim": EMBEDDING_DIM,
                "cache_size": len(VectorStore._search_cache),
                "cache_max_size": SEARCH_CACHE_SIZE
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            current_host, current_port = self._endpoints[self._current_endpoint_index]
            return {
                "status": "error",
                "connected": False,
                "error": str(e),
                "host": current_host,
                "port": current_port
            }

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
        # 确保连接有效
        self._ensure_connection()

        # 如果集合不存在，创建它
        if not utility.has_collection(collection_name):
            self.create_collection(collection_name)

        collection = Collection(collection_name)

        # 准备数据
        ids = [uuid.uuid4().hex for _ in range(len(texts))]
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
        # 确保连接有效
        self._ensure_connection()

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
            # 参数验证
            if not doc_id or not isinstance(doc_id, str):
                logger.error(f"Invalid doc_id: {doc_id} (must be non-empty string)")
                return False

            if not collection_name or not isinstance(collection_name, str):
                logger.error(f"Invalid collection_name: {collection_name}")
                return False

            # 转义 doc_id 中的特殊字符，防止 Milvus 表达式注入
            escaped_doc_id = doc_id.replace('"', '\\"')

            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} does not exist, nothing to delete")
                return False

            # 确保连接有效
            self._ensure_connection()

            collection = Collection(collection_name)

            # 先加载集合，确保删除操作能正确执行
            try:
                collection.load()
            except Exception as e:
                logger.debug(f"Collection load warning (may already be loaded): {e}")

            # 使用 doc_id 字段过滤删除所有属于该文档的向量
            # Milvus 的表达式语法：doc_id == "xxx"
            delete_expr = f'doc_id == "{escaped_doc_id}"'
            collection.delete(expr=delete_expr)

            # 刷新以确保删除立即生效
            collection.flush()

            # 记录删除操作
            logger.info(f"Deleted vectors by doc_id: collection={collection_name}, doc_id={doc_id}")

            return True
        except Exception as e:
            logger.error(f"删除向量失败: collection={collection_name}, doc_id={doc_id}, error={e}")
            return False

    def delete_by_doc_ids(self, collection_name: str, doc_ids: List[str]) -> Dict[str, Any]:
        """
        批量按文档ID删除对应的向量数据

        Args:
            collection_name: 集合名称
            doc_ids: 文档ID列表

        Returns:
            Dict: 包含删除结果的字典
                - success: 成功删除的文档数量
                - failed: 删除失败的文档数量
                - failed_ids: 失败的文档ID列表
        """
        result = {
            "success": 0,
            "failed": 0,
            "failed_ids": []
        }

        if not doc_ids:
            return result

        # 去重
        unique_doc_ids = list(set(doc_ids))

        try:
            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                result["failed"] = len(unique_doc_ids)
                result["failed_ids"] = unique_doc_ids
                return result

            # 确保连接有效
            self._ensure_connection()

            collection = Collection(collection_name)

            # 先加载集合
            try:
                collection.load()
            except Exception as e:
                logger.debug(f"Collection load warning: {e}")

            # 构建批量删除表达式：doc_id in ["id1", "id2", ...]
            # 转义每个 doc_id
            escaped_ids = [f'"{id.replace("\\", "\\\\").replace('"', "\\\"")}"' for id in unique_doc_ids]
            delete_expr = f'doc_id in [{", ".join(escaped_ids)}]'

            collection.delete(expr=delete_expr)
            collection.flush()

            result["success"] = len(unique_doc_ids)
            logger.info(f"Batch deleted vectors: collection={collection_name}, count={result['success']}")

        except Exception as e:
            logger.error(f"批量删除向量失败: collection={collection_name}, error={e}")
            # 如果批量删除失败，尝试逐个删除
            for doc_id in unique_doc_ids:
                if self.delete_by_doc_id(collection_name, doc_id):
                    result["success"] += 1
                else:
                    result["failed"] += 1
                    result["failed_ids"].append(doc_id)

        return result

    def batch_insert(self, collection_name: str, texts: List[str],
                     embeddings: List[List[float]], metadata: List[Dict] = None,
                     batch_size: int = 1000) -> int:
        """
        批量插入大规模文档向量，按分块逐批写入

        Args:
            collection_name: 集合名称
            texts: 文本列表
            embeddings: 向量列表
            metadata: 元数据列表（每个元数据应包含 doc_id 用于按文档删除）
            batch_size: 每批插入的数量，默认 1000

        Returns:
            插入的文档总数量
        """
        total = len(texts)
        if total == 0:
            return 0

        if metadata is None:
            metadata = [{}] * total

        inserted = 0
        num_batches = (total + batch_size - 1) // batch_size

        logger.info(f"Batch insert started: {total} vectors into '{collection_name}' "
                     f"in {num_batches} batches (batch_size={batch_size})")

        for batch_idx in range(num_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, total)

            batch_texts = texts[start:end]
            batch_embeddings = embeddings[start:end]
            batch_metadata = metadata[start:end]

            count = self.insert(collection_name, batch_texts, batch_embeddings, batch_metadata)
            inserted += count

            logger.info(f"Batch {batch_idx + 1}/{num_batches} inserted: "
                         f"{count} vectors ({inserted}/{total} total)")

        logger.info(f"Batch insert completed: {inserted}/{total} vectors into '{collection_name}'")
        return inserted

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合的详细统计信息

        Args:
            collection_name: 集合名称

        Returns:
            Dict: 包含行数、索引信息和内存使用的统计字典
        """
        self._ensure_connection()

        if not utility.has_collection(collection_name):
            return {"exists": False, "collection_name": collection_name}

        collection = Collection(collection_name)
        collection.load()

        # 基本信息
        num_entities = collection.num_entities

        # 字段信息
        fields = []
        for f in collection.schema.fields:
            field_info = {
                "name": f.name,
                "type": str(f.dtype),
                "is_primary": f.is_primary,
            }
            if hasattr(f, "dim") and f.dim is not None:
                field_info["dim"] = f.dim
            if hasattr(f, "max_length") and f.max_length is not None:
                field_info["max_length"] = f.max_length
            fields.append(field_info)

        # 索引信息
        indexes = []
        for f in collection.schema.fields:
            try:
                index = collection.index(f.name)
                indexes.append({
                    "field": f.name,
                    "index_type": index.params.get("index_type", "unknown"),
                    "metric_type": index.params.get("metric_type", ""),
                    "params": {k: v for k, v in index.params.items()
                               if k not in ("index_type", "metric_type")},
                })
            except Exception:
                # 该字段没有索引
                pass

        # 内存使用估算（基于实体数量和向量维度）
        embedding_dim = EMBEDDING_DIM
        for f in collection.schema.fields:
            if hasattr(f, "dim") and f.dim is not None:
                embedding_dim = f.dim
                break

        # 粗略估算：每个 float32 向量 = dim * 4 字节
        estimated_vector_bytes = num_entities * embedding_dim * 4
        estimated_memory_mb = estimated_vector_bytes / (1024 * 1024)

        return {
            "exists": True,
            "collection_name": collection_name,
            "row_count": num_entities,
            "fields": fields,
            "indexes": indexes,
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "embedding_dim": embedding_dim,
            "description": collection.schema.description,
        }

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
