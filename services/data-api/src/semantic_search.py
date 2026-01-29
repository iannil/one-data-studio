"""
语义资产检索服务
Phase 4: 基于 Milvus 的向量语义检索

功能：
- 自然语言查询数据资产
- 向量嵌入语义相似度搜索
- LLM 重排序增强检索精度
- 元数据标签融合检索
"""

import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL", "http://openai-proxy:8000")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
SEMANTIC_SEARCH_ENABLED = os.getenv("SEMANTIC_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")

# Milvus 集合配置
COLLECTION_NAME = "data_assets"
INDEX_TYPE = "IVF_FLAT"
METRIC_TYPE = "COSINE"
NLIST = 128
NPROBE = 16


class AssetType(str, Enum):
    """资产类型"""
    TABLE = "table"
    COLUMN = "column"
    DATABASE = "database"
    SCHEMA = "schema"
    VIEW = "view"
    PIPELINE = "pipeline"


@dataclass
class DataAsset:
    """数据资产"""
    id: str
    name: str
    asset_type: AssetType
    description: str = ""
    database: str = ""
    schema: str = ""
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    columns: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type.value if isinstance(self.asset_type, AssetType) else self.asset_type,
            "description": self.description,
            "database": self.database,
            "schema": self.schema,
            "tags": self.tags,
            "owner": self.owner,
            "columns": self.columns,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_text(self) -> str:
        """转换为文本用于嵌入"""
        parts = [
            f"表名: {self.name}",
            f"类型: {self.asset_type.value if isinstance(self.asset_type, AssetType) else self.asset_type}",
        ]
        if self.description:
            parts.append(f"描述: {self.description}")
        if self.database:
            parts.append(f"数据库: {self.database}")
        if self.schema:
            parts.append(f"Schema: {self.schema}")
        if self.tags:
            parts.append(f"标签: {', '.join(self.tags)}")
        if self.columns:
            col_names = [c.get("name", "") for c in self.columns[:20]]  # 限制列数
            parts.append(f"列: {', '.join(col_names)}")
        if self.owner:
            parts.append(f"负责人: {self.owner}")

        return "\n".join(parts)


@dataclass
class SearchResult:
    """搜索结果"""
    asset: DataAsset
    score: float
    relevance_reason: str = ""
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset.to_dict(),
            "score": self.score,
            "relevance_reason": self.relevance_reason,
            "highlights": self.highlights,
        }


class EmbeddingService:
    """向量嵌入服务"""

    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = api_url or MODEL_API_URL
        self.model = model or EMBEDDING_MODEL
        self._cache: Dict[str, List[float]] = {}

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的向量嵌入

        Args:
            text: 输入文本

        Returns:
            嵌入向量或 None
        """
        # 检查缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = requests.post(
                f"{self.api_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": text,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data["data"][0]["embedding"]
                # 缓存结果
                self._cache[cache_key] = embedding
                return embedding
            else:
                logger.warning(f"Embedding API 返回错误: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Embedding API 请求失败: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Embedding 响应解析失败: {e}")
            return None

    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量获取文本的向量嵌入

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        results = []
        # 分批处理，避免单次请求过大
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = requests.post(
                    f"{self.api_url}/v1/embeddings",
                    json={
                        "model": self.model,
                        "input": batch,
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    for item in data["data"]:
                        results.append(item["embedding"])
                else:
                    logger.warning(f"Batch embedding API 返回错误: {response.status_code}")
                    results.extend([None] * len(batch))

            except Exception as e:
                logger.error(f"Batch embedding 失败: {e}")
                results.extend([None] * len(batch))

        return results

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


class SemanticSearchService:
    """语义检索服务"""

    def __init__(
        self,
        milvus_host: str = None,
        milvus_port: int = None,
        api_url: str = None,
    ):
        """
        初始化语义检索服务

        Args:
            milvus_host: Milvus 主机地址
            milvus_port: Milvus 端口
            api_url: LLM API 地址
        """
        self.milvus_host = milvus_host or MILVUS_HOST
        self.milvus_port = milvus_port or MILVUS_PORT
        self.api_url = api_url or MODEL_API_URL
        self.embedding_service = EmbeddingService(api_url)
        self.enabled = SEMANTIC_SEARCH_ENABLED

        self._milvus_client = None
        self._collection = None

    def _get_milvus_connection(self):
        """获取 Milvus 连接"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

            # 检查是否已连接
            if connections.has_connection("default"):
                return True

            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port,
            )
            logger.info(f"已连接到 Milvus: {self.milvus_host}:{self.milvus_port}")
            return True

        except ImportError:
            logger.error("pymilvus 未安装，请执行: pip install pymilvus")
            return False
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            return False

    def _ensure_collection(self):
        """确保集合存在"""
        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility

            if not self._get_milvus_connection():
                return None

            # 检查集合是否存在
            if utility.has_collection(COLLECTION_NAME):
                self._collection = Collection(COLLECTION_NAME)
                self._collection.load()
                return self._collection

            # 创建集合
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="asset_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="asset_name", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="asset_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="database", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="schema", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="owner", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="text_content", dtype=DataType.VARCHAR, max_length=5000),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]

            schema = CollectionSchema(fields=fields, description="数据资产语义检索集合")
            self._collection = Collection(name=COLLECTION_NAME, schema=schema)

            # 创建索引
            index_params = {
                "metric_type": METRIC_TYPE,
                "index_type": INDEX_TYPE,
                "params": {"nlist": NLIST},
            }
            self._collection.create_index(field_name="embedding", index_params=index_params)
            self._collection.load()

            logger.info(f"已创建 Milvus 集合: {COLLECTION_NAME}")
            return self._collection

        except Exception as e:
            logger.error(f"创建 Milvus 集合失败: {e}")
            return None

    def index_asset(self, asset: DataAsset) -> bool:
        """
        索引数据资产

        Args:
            asset: 数据资产

        Returns:
            是否成功
        """
        if not self.enabled:
            logger.warning("语义检索服务未启用")
            return False

        collection = self._ensure_collection()
        if collection is None:
            return False

        try:
            # 生成文本内容
            text_content = asset.to_text()

            # 获取嵌入
            embedding = self.embedding_service.get_embedding(text_content)
            if embedding is None:
                logger.warning(f"无法获取资产 {asset.id} 的嵌入向量")
                return False

            # 准备数据
            data = [
                [f"{asset.id}_{int(datetime.utcnow().timestamp())}"],  # id
                [asset.id],  # asset_id
                [asset.name[:500]],  # asset_name
                [asset.asset_type.value if isinstance(asset.asset_type, AssetType) else asset.asset_type],
                [asset.database[:200] if asset.database else ""],
                [asset.schema[:200] if asset.schema else ""],
                [asset.description[:2000] if asset.description else ""],
                [",".join(asset.tags)[:1000] if asset.tags else ""],
                [asset.owner[:200] if asset.owner else ""],
                [text_content[:5000]],  # text_content
                [embedding],  # embedding
                [int(datetime.utcnow().timestamp())],  # created_at
            ]

            # 删除旧记录（如果存在）
            self._delete_asset_by_id(asset.id)

            # 插入新记录
            collection.insert(data)
            collection.flush()

            logger.info(f"已索引资产: {asset.id} - {asset.name}")
            return True

        except Exception as e:
            logger.error(f"索引资产失败: {e}")
            return False

    def index_assets_batch(self, assets: List[DataAsset]) -> int:
        """
        批量索引数据资产

        Args:
            assets: 数据资产列表

        Returns:
            成功索引的数量
        """
        if not self.enabled:
            logger.warning("语义检索服务未启用")
            return 0

        collection = self._ensure_collection()
        if collection is None:
            return 0

        success_count = 0

        try:
            # 准备文本
            texts = [asset.to_text() for asset in assets]

            # 批量获取嵌入
            embeddings = self.embedding_service.get_embeddings_batch(texts)

            # 准备批量数据
            ids = []
            asset_ids = []
            asset_names = []
            asset_types = []
            databases = []
            schemas = []
            descriptions = []
            tags_list = []
            owners = []
            text_contents = []
            valid_embeddings = []
            created_ats = []

            for i, (asset, embedding) in enumerate(zip(assets, embeddings)):
                if embedding is None:
                    logger.warning(f"跳过资产 {asset.id}，无法获取嵌入向量")
                    continue

                ids.append(f"{asset.id}_{int(datetime.utcnow().timestamp())}_{i}")
                asset_ids.append(asset.id)
                asset_names.append(asset.name[:500])
                asset_types.append(asset.asset_type.value if isinstance(asset.asset_type, AssetType) else asset.asset_type)
                databases.append(asset.database[:200] if asset.database else "")
                schemas.append(asset.schema[:200] if asset.schema else "")
                descriptions.append(asset.description[:2000] if asset.description else "")
                tags_list.append(",".join(asset.tags)[:1000] if asset.tags else "")
                owners.append(asset.owner[:200] if asset.owner else "")
                text_contents.append(texts[i][:5000])
                valid_embeddings.append(embedding)
                created_ats.append(int(datetime.utcnow().timestamp()))

            if not ids:
                return 0

            # 删除旧记录
            old_ids = [asset.id for asset in assets]
            for old_id in old_ids:
                self._delete_asset_by_id(old_id)

            # 批量插入
            data = [
                ids,
                asset_ids,
                asset_names,
                asset_types,
                databases,
                schemas,
                descriptions,
                tags_list,
                owners,
                text_contents,
                valid_embeddings,
                created_ats,
            ]
            collection.insert(data)
            collection.flush()

            success_count = len(ids)
            logger.info(f"批量索引完成: {success_count}/{len(assets)} 个资产")

        except Exception as e:
            logger.error(f"批量索引失败: {e}")

        return success_count

    def _delete_asset_by_id(self, asset_id: str) -> bool:
        """删除资产的所有索引记录"""
        try:
            collection = self._ensure_collection()
            if collection is None:
                return False

            expr = f'asset_id == "{asset_id}"'
            collection.delete(expr)
            return True
        except Exception as e:
            logger.warning(f"删除资产记录失败: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
    ) -> List[SearchResult]:
        """
        语义检索数据资产

        Args:
            query: 自然语言查询
            top_k: 返回结果数量
            filters: 过滤条件 {"asset_type": "table", "database": "xxx"}
            rerank: 是否使用 LLM 重排序

        Returns:
            搜索结果列表
        """
        if not self.enabled:
            logger.warning("语义检索服务未启用")
            return []

        collection = self._ensure_collection()
        if collection is None:
            return []

        try:
            # 获取查询向量
            query_embedding = self.embedding_service.get_embedding(query)
            if query_embedding is None:
                logger.warning("无法获取查询向量")
                return []

            # 构建过滤表达式
            filter_expr = None
            if filters:
                filter_parts = []
                if "asset_type" in filters:
                    filter_parts.append(f'asset_type == "{filters["asset_type"]}"')
                if "database" in filters:
                    filter_parts.append(f'database == "{filters["database"]}"')
                if "schema" in filters:
                    filter_parts.append(f'schema == "{filters["schema"]}"')
                if "owner" in filters:
                    filter_parts.append(f'owner == "{filters["owner"]}"')
                if filter_parts:
                    filter_expr = " and ".join(filter_parts)

            # 搜索参数
            search_params = {
                "metric_type": METRIC_TYPE,
                "params": {"nprobe": NPROBE},
            }

            # 执行搜索
            # 如果要重排序，获取更多候选
            search_top_k = top_k * 3 if rerank else top_k

            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=search_top_k,
                expr=filter_expr,
                output_fields=[
                    "asset_id", "asset_name", "asset_type", "database",
                    "schema", "description", "tags", "owner", "text_content"
                ],
            )

            # 转换结果
            search_results = []
            for hits in results:
                for hit in hits:
                    entity = hit.entity
                    asset = DataAsset(
                        id=entity.get("asset_id", ""),
                        name=entity.get("asset_name", ""),
                        asset_type=entity.get("asset_type", "table"),
                        database=entity.get("database", ""),
                        schema=entity.get("schema", ""),
                        description=entity.get("description", ""),
                        tags=entity.get("tags", "").split(",") if entity.get("tags") else [],
                        owner=entity.get("owner", ""),
                    )

                    search_results.append(SearchResult(
                        asset=asset,
                        score=hit.score,
                    ))

            # LLM 重排序
            if rerank and len(search_results) > 0:
                search_results = self._rerank_with_llm(query, search_results)

            # 返回 top_k 结果
            return search_results[:top_k]

        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return []

    def _rerank_with_llm(
        self,
        query: str,
        candidates: List[SearchResult],
    ) -> List[SearchResult]:
        """
        使用 LLM 重排序搜索结果

        Args:
            query: 原始查询
            candidates: 候选结果

        Returns:
            重排序后的结果
        """
        if not candidates:
            return candidates

        try:
            # 构建候选信息
            candidates_info = []
            for i, result in enumerate(candidates[:15]):  # 限制候选数量
                asset = result.asset
                info = f"{i+1}. {asset.name}"
                if asset.description:
                    info += f" - {asset.description[:100]}"
                if asset.tags:
                    info += f" [标签: {', '.join(asset.tags[:5])}]"
                candidates_info.append(info)

            prompt = f"""用户搜索: {query}

候选数据资产:
{chr(10).join(candidates_info)}

请分析用户意图，对候选资产的相关性进行重新排序。
返回格式为 JSON，包含:
1. ranked_indices: 按相关性从高到低排列的候选序号数组（1-based）
2. reasons: 对应每个资产的相关性说明（简短）

仅返回 JSON:"""

            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是数据资产检索助手，擅长理解用户查询意图并匹配相关数据资产。仅返回 JSON。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=15,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # 解析 JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    rerank_data = json.loads(json_match.group())
                    ranked_indices = rerank_data.get("ranked_indices", [])
                    reasons = rerank_data.get("reasons", [])

                    # 重新排序
                    reranked = []
                    for i, idx in enumerate(ranked_indices):
                        if 1 <= idx <= len(candidates):
                            result = candidates[idx - 1]
                            if i < len(reasons):
                                result.relevance_reason = reasons[i]
                            reranked.append(result)

                    # 添加未包含的候选（保持原顺序）
                    included = set(ranked_indices)
                    for i, result in enumerate(candidates):
                        if (i + 1) not in included:
                            reranked.append(result)

                    return reranked

        except json.JSONDecodeError as e:
            logger.warning(f"重排序 JSON 解析失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 重排序失败: {e}")

        return candidates

    def suggest_queries(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        查询建议（自动补全）

        Args:
            partial_query: 部分查询文本
            limit: 建议数量

        Returns:
            建议查询列表
        """
        if not self.enabled or len(partial_query) < 2:
            return []

        try:
            # 使用 LLM 生成查询建议
            prompt = f"""用户正在搜索数据资产，输入了: "{partial_query}"

请提供 {limit} 个可能的完整搜索查询建议。
考虑常见的数据资产查询场景，如：
- 查找特定业务域的表
- 查找包含特定字段的表
- 查找特定负责人的资产
- 查找特定标签的数据

返回 JSON 数组格式的建议查询:"""

            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是数据资产搜索助手。仅返回 JSON 数组。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                timeout=5,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                import re
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    suggestions = json.loads(json_match.group())
                    return suggestions[:limit]

        except Exception as e:
            logger.warning(f"查询建议生成失败: {e}")

        return []

    def get_similar_assets(
        self,
        asset_id: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        获取相似资产

        Args:
            asset_id: 资产 ID
            top_k: 返回数量

        Returns:
            相似资产列表
        """
        if not self.enabled:
            return []

        collection = self._ensure_collection()
        if collection is None:
            return []

        try:
            # 查找资产的嵌入
            results = collection.query(
                expr=f'asset_id == "{asset_id}"',
                output_fields=["embedding", "text_content"],
                limit=1,
            )

            if not results:
                logger.warning(f"未找到资产: {asset_id}")
                return []

            # 使用资产的嵌入搜索相似资产
            asset_embedding = results[0]["embedding"]

            search_params = {
                "metric_type": METRIC_TYPE,
                "params": {"nprobe": NPROBE},
            }

            # 搜索（排除自身）
            search_results = collection.search(
                data=[asset_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k + 1,  # 多取一个，排除自身
                expr=f'asset_id != "{asset_id}"',
                output_fields=[
                    "asset_id", "asset_name", "asset_type", "database",
                    "schema", "description", "tags", "owner"
                ],
            )

            # 转换结果
            similar_assets = []
            for hits in search_results:
                for hit in hits:
                    entity = hit.entity
                    asset = DataAsset(
                        id=entity.get("asset_id", ""),
                        name=entity.get("asset_name", ""),
                        asset_type=entity.get("asset_type", "table"),
                        database=entity.get("database", ""),
                        schema=entity.get("schema", ""),
                        description=entity.get("description", ""),
                        tags=entity.get("tags", "").split(",") if entity.get("tags") else [],
                        owner=entity.get("owner", ""),
                    )
                    similar_assets.append(SearchResult(
                        asset=asset,
                        score=hit.score,
                    ))

            return similar_assets[:top_k]

        except Exception as e:
            logger.error(f"获取相似资产失败: {e}")
            return []

    def delete_asset(self, asset_id: str) -> bool:
        """
        删除资产索引

        Args:
            asset_id: 资产 ID

        Returns:
            是否成功
        """
        return self._delete_asset_by_id(asset_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            collection = self._ensure_collection()
            if collection is None:
                return {"status": "disconnected", "error": "Milvus 连接失败"}

            return {
                "status": "connected",
                "collection": COLLECTION_NAME,
                "num_entities": collection.num_entities,
                "milvus_host": self.milvus_host,
                "milvus_port": self.milvus_port,
                "embedding_model": self.embedding_service.model,
                "embedding_dim": EMBEDDING_DIM,
                "index_type": INDEX_TYPE,
                "metric_type": METRIC_TYPE,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def rebuild_index(self) -> bool:
        """重建索引"""
        try:
            from pymilvus import utility

            if not self._get_milvus_connection():
                return False

            # 删除旧集合
            if utility.has_collection(COLLECTION_NAME):
                utility.drop_collection(COLLECTION_NAME)
                logger.info(f"已删除旧集合: {COLLECTION_NAME}")

            # 重置集合引用
            self._collection = None

            # 重新创建集合
            collection = self._ensure_collection()
            return collection is not None

        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False


# 全局实例
_semantic_search_service: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> SemanticSearchService:
    """获取语义检索服务单例"""
    global _semantic_search_service
    if _semantic_search_service is None:
        _semantic_search_service = SemanticSearchService()
    return _semantic_search_service


# 便捷函数
def search_assets(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    rerank: bool = True,
) -> List[Dict[str, Any]]:
    """
    搜索数据资产（便捷函数）

    Args:
        query: 自然语言查询
        top_k: 返回数量
        filters: 过滤条件
        rerank: 是否重排序

    Returns:
        搜索结果字典列表
    """
    service = get_semantic_search_service()
    results = service.search(query, top_k, filters, rerank)
    return [r.to_dict() for r in results]


def index_table_as_asset(
    table_id: str,
    table_name: str,
    database: str = "",
    schema: str = "",
    description: str = "",
    columns: List[Dict[str, Any]] = None,
    tags: List[str] = None,
    owner: str = "",
) -> bool:
    """
    将表索引为数据资产（便捷函数）

    Args:
        table_id: 表 ID
        table_name: 表名
        database: 数据库名
        schema: Schema 名
        description: 描述
        columns: 列信息列表
        tags: 标签列表
        owner: 负责人

    Returns:
        是否成功
    """
    asset = DataAsset(
        id=table_id,
        name=table_name,
        asset_type=AssetType.TABLE,
        database=database,
        schema=schema,
        description=description,
        columns=columns or [],
        tags=tags or [],
        owner=owner,
    )
    service = get_semantic_search_service()
    return service.index_asset(asset)
