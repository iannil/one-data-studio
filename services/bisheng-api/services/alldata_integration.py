"""
Alldata 客户端集成模块
Sprint 24: 增强 Alldata → Bisheng 集成

功能:
- 元数据查询与缓存
- 向量检索优化
- Text-to-SQL 增强（带历史上下文）
- 跨服务调用重试逻辑
"""

import os
import logging
import hashlib
import time
import asyncio
import requests
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta
from collections import OrderedDict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# 配置
ALDATA_API_URL = os.getenv("ALDATA_API_URL", "http://alldata-api:8080")
ALDATA_API_KEY = os.getenv("ALDATA_API_KEY", "")
ALDATA_TIMEOUT = int(os.getenv("ALDATA_TIMEOUT", "30"))

# SSL 验证
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"


# ==================== 缓存实现 ====================

class LRUCache:
    """LRU 缓存实现"""

    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        """
        初始化缓存

        Args:
            maxsize: 最大缓存条目数
            ttl: 缓存生存时间（秒）
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_str = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        # 检查是否过期
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None

        # 移动到末尾（最近使用）
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.maxsize:
                # 移除最旧的条目
                self._cache.popitem(last=False)

        self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> bool:
        """使缓存失效"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


def cached(cache: LRUCache):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache._make_key(func.__name__, *args, **kwargs)
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result

            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(key, result)
            return result
        return wrapper
    return decorator


# ==================== 重试逻辑 ====================

class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retryable_status_codes: List[int] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_status_codes = retryable_status_codes or [429, 500, 502, 503, 504]


def with_retry(config: RetryConfig = None):
    """重试装饰器"""
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None

                    # 检查是否可重试
                    if status_code and status_code not in config.retryable_status_codes:
                        raise

                    if attempt < config.max_retries:
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{config.max_retries + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


# ==================== Alldata 客户端 ====================

class AlldataClient:
    """Alldata API 客户端"""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: int = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600
    ):
        self.base_url = base_url or ALDATA_API_URL
        self.api_key = api_key or ALDATA_API_KEY
        self.timeout = timeout or ALDATA_TIMEOUT
        self.cache_enabled = cache_enabled

        # 初始化缓存
        if cache_enabled:
            self._metadata_cache = LRUCache(maxsize=200, ttl=cache_ttl)
            self._schema_cache = LRUCache(maxsize=100, ttl=cache_ttl)
        else:
            self._metadata_cache = None
            self._schema_cache = None

        # 重试配置
        self.retry_config = RetryConfig()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @with_retry()
    async def _request(
        self,
        method: str,
        path: str,
        params: Dict = None,
        json: Dict = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json,
            timeout=self.timeout,
            verify=VERIFY_SSL
        )

        response.raise_for_status()
        return response.json()


# ==================== 元数据服务 ====================

class MetadataService:
    """元数据查询服务"""

    def __init__(self, client: AlldataClient = None):
        self.client = client or AlldataClient()
        self._cache = self.client._metadata_cache

    async def search_tables(
        self,
        keywords: str,
        database: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索相关表

        Args:
            keywords: 搜索关键词
            database: 数据库名称（可选）
            limit: 返回结果数量

        Returns:
            匹配的表列表
        """
        cache_key = None
        if self._cache:
            cache_key = self._cache._make_key("search_tables", keywords, database, limit)
            cached_result = self._cache.get(cache_key)
            if cached_result:
                return cached_result

        try:
            params = {"keywords": keywords, "limit": limit}
            if database:
                params["database"] = database

            result = await self.client._request("GET", "/api/v1/metadata/tables", params=params)
            tables = result.get("data", {}).get("tables", [])

            if self._cache and cache_key:
                self._cache.set(cache_key, tables)

            return tables
        except Exception as e:
            logger.error(f"Failed to search tables: {e}")
            return []

    async def get_table_schema(
        self,
        database: str,
        table: str,
        include_sample_data: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取表结构

        Args:
            database: 数据库名称
            table: 表名
            include_sample_data: 是否包含示例数据

        Returns:
            表结构信息
        """
        cache_key = None
        if self._cache:
            cache_key = self._cache._make_key("get_table_schema", database, table, include_sample_data)
            cached_result = self._cache.get(cache_key)
            if cached_result:
                return cached_result

        try:
            params = {"include_sample_data": "true" if include_sample_data else "false"}
            result = await self.client._request(
                "GET",
                f"/api/v1/metadata/tables/{database}/{table}/schema",
                params=params
            )
            schema = result.get("data")

            if self._cache and cache_key and schema:
                self._cache.set(cache_key, schema)

            return schema
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return None

    async def get_related_tables(
        self,
        database: str,
        table: str,
        depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        获取关联表

        Args:
            database: 数据库名称
            table: 表名
            depth: 关联深度

        Returns:
            关联表列表
        """
        try:
            params = {"depth": depth}
            result = await self.client._request(
                "GET",
                f"/api/v1/metadata/tables/{database}/{table}/relations",
                params=params
            )
            return result.get("data", {}).get("relations", [])
        except Exception as e:
            logger.error(f"Failed to get related tables: {e}")
            return []

    def invalidate_cache(self, database: str = None, table: str = None) -> None:
        """使缓存失效"""
        if self._cache:
            self._cache.clear()


# ==================== 向量检索服务（增强版）====================

class EnhancedVectorSearchService:
    """增强版向量检索服务

    支持:
    - 元数据过滤
    - 混合检索（向量 + 关键词）
    - 结果重排序
    """

    def __init__(self, client: AlldataClient = None):
        self.client = client or AlldataClient()

    async def search(
        self,
        query: str,
        collection: str = "default",
        top_k: int = 5,
        filters: Dict[str, Any] = None,
        hybrid_mode: bool = False,
        keyword_weight: float = 0.3,
        rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        执行向量检索

        Args:
            query: 查询文本
            collection: 向量集合名称
            top_k: 返回结果数量
            filters: 元数据过滤条件
            hybrid_mode: 是否启用混合检索
            keyword_weight: 关键词权重（0-1）
            rerank: 是否重排序

        Returns:
            检索结果列表
        """
        try:
            request_body = {
                "query": query,
                "collection": collection,
                "top_k": top_k * 2 if rerank else top_k,  # 多检索一些用于重排序
                "hybrid_mode": hybrid_mode,
                "keyword_weight": keyword_weight
            }

            if filters:
                request_body["filters"] = filters

            result = await self.client._request(
                "POST",
                "/api/v1/vector/search",
                json=request_body
            )

            results = result.get("data", {}).get("results", [])

            # 重排序
            if rerank and len(results) > top_k:
                results = await self._rerank(query, results, top_k)

            return results[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        对结果进行重排序

        Args:
            query: 原始查询
            results: 初始结果
            top_k: 最终数量

        Returns:
            重排序后的结果
        """
        try:
            # 使用交叉编码器重排序（如果可用）
            result = await self.client._request(
                "POST",
                "/api/v1/vector/rerank",
                json={
                    "query": query,
                    "documents": [r.get("content", "") for r in results],
                    "top_k": top_k
                }
            )
            reranked_indices = result.get("data", {}).get("indices", list(range(len(results))))
            return [results[i] for i in reranked_indices[:top_k]]
        except Exception as e:
            logger.debug(f"Reranking failed, using original order: {e}")
            return results[:top_k]

    async def search_with_metadata(
        self,
        query: str,
        collection: str = "default",
        top_k: int = 5,
        doc_type: str = None,
        date_range: Tuple[str, str] = None,
        tags: List[str] = None,
        source: str = None
    ) -> List[Dict[str, Any]]:
        """
        带元数据过滤的向量检索

        Args:
            query: 查询文本
            collection: 向量集合名称
            top_k: 返回结果数量
            doc_type: 文档类型过滤
            date_range: 日期范围 (start, end)
            tags: 标签过滤
            source: 来源过滤

        Returns:
            检索结果列表
        """
        filters = {}

        if doc_type:
            filters["doc_type"] = doc_type
        if date_range:
            filters["date"] = {
                "gte": date_range[0],
                "lte": date_range[1]
            }
        if tags:
            filters["tags"] = {"in": tags}
        if source:
            filters["source"] = source

        return await self.search(
            query=query,
            collection=collection,
            top_k=top_k,
            filters=filters if filters else None,
            hybrid_mode=True,
            rerank=True
        )


# ==================== Text-to-SQL 增强服务 ====================

class EnhancedText2SQLService:
    """增强版 Text-to-SQL 服务

    支持:
    - 聊天历史上下文
    - 自动表发现
    - SQL 验证
    - 结果解释
    """

    def __init__(
        self,
        metadata_service: MetadataService = None,
        llm_endpoint: str = None
    ):
        self.metadata = metadata_service or MetadataService()
        self.llm_endpoint = llm_endpoint or os.getenv("LLM_ENDPOINT", "http://vllm-serving:8000")

        # 聊天历史缓存
        self._history_cache: Dict[str, List[Dict]] = {}

    async def generate_sql(
        self,
        question: str,
        database: str = "sales_dw",
        conversation_id: str = None,
        max_history: int = 5
    ) -> Dict[str, Any]:
        """
        生成 SQL 查询

        Args:
            question: 自然语言问题
            database: 数据库名称
            conversation_id: 会话 ID（用于上下文）
            max_history: 最大历史记录数

        Returns:
            生成结果
        """
        try:
            # 1. 获取相关表的元数据
            tables = await self.metadata.search_tables(question, database=database)

            if not tables:
                return {
                    "success": False,
                    "error": "No relevant tables found for the query",
                    "question": question
                }

            # 2. 获取详细表结构
            table_schemas = []
            for table_info in tables[:5]:  # 限制表数量
                schema = await self.metadata.get_table_schema(
                    database=table_info.get("database", database),
                    table=table_info.get("table"),
                    include_sample_data=True
                )
                if schema:
                    table_schemas.append(schema)

            # 3. 构建 Schema 上下文
            schema_context = self._build_schema_context(table_schemas)

            # 4. 获取聊天历史
            history_context = ""
            if conversation_id and conversation_id in self._history_cache:
                history = self._history_cache[conversation_id][-max_history:]
                history_context = self._build_history_context(history)

            # 5. 构建完整 Prompt
            prompt = self._build_prompt(question, schema_context, history_context)

            # 6. 调用 LLM 生成 SQL
            sql = await self._generate_with_llm(prompt)

            if not sql:
                return {
                    "success": False,
                    "error": "Failed to generate SQL",
                    "question": question
                }

            # 7. 验证 SQL
            validation_result = self._validate_sql(sql)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Generated SQL is invalid: {validation_result['error']}",
                    "sql": sql,
                    "question": question
                }

            # 8. 保存到历史
            if conversation_id:
                if conversation_id not in self._history_cache:
                    self._history_cache[conversation_id] = []
                self._history_cache[conversation_id].append({
                    "question": question,
                    "sql": sql,
                    "timestamp": datetime.now().isoformat()
                })

            return {
                "success": True,
                "question": question,
                "sql": sql,
                "tables_used": [t.get("table") for t in tables[:5]],
                "schema_context": schema_context[:500] + "..." if len(schema_context) > 500 else schema_context
            }

        except Exception as e:
            logger.error(f"Text-to-SQL generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }

    def _build_schema_context(self, schemas: List[Dict]) -> str:
        """构建 Schema 上下文"""
        context_parts = []

        for schema in schemas:
            table_name = schema.get("table", "unknown")
            db_name = schema.get("database", "")
            description = schema.get("description", "")

            full_name = f"{db_name}.{table_name}" if db_name else table_name
            context_parts.append(f"\n### 表: {full_name}")

            if description:
                context_parts.append(f"描述: {description}")

            columns = schema.get("columns", [])
            if columns:
                context_parts.append("字段:")
                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("type", "")
                    col_comment = col.get("comment", "")
                    nullable = "可空" if col.get("nullable", True) else "非空"

                    col_desc = f"  - {col_name} ({col_type}, {nullable})"
                    if col_comment:
                        col_desc += f" -- {col_comment}"
                    context_parts.append(col_desc)

            # 添加关联关系
            relations = schema.get("relations", [])
            if relations:
                context_parts.append("关联关系:")
                for rel in relations:
                    ref_table = rel.get("ref_table", "")
                    ref_column = rel.get("ref_column", "")
                    context_parts.append(f"  - 关联 {ref_table}.{ref_column}")

            # 添加示例数据
            sample_data = schema.get("sample_data", [])
            if sample_data:
                context_parts.append(f"示例数据: {sample_data[:2]}")

        return "\n".join(context_parts)

    def _build_history_context(self, history: List[Dict]) -> str:
        """构建历史上下文"""
        if not history:
            return ""

        context_parts = ["### 之前的查询历史:"]
        for item in history:
            context_parts.append(f"问题: {item['question']}")
            context_parts.append(f"SQL: {item['sql']}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _build_prompt(
        self,
        question: str,
        schema_context: str,
        history_context: str = ""
    ) -> str:
        """构建完整 Prompt"""
        prompt = f"""你是一个专业的 SQL 生成专家。请根据以下信息生成 SQL 查询。

## 可用表结构
{schema_context}

{history_context}

## 用户问题
{question}

## 要求
1. 只返回 SQL 语句，不要任何解释
2. 使用标准 SQL 语法
3. 如果需要 JOIN，在 WHERE 或 ON 子句中明确关联条件
4. 注意日期格式的处理
5. 对于聚合查询，确保使用正确的 GROUP BY
6. 如果问题涉及之前的查询，可以参考历史上下文

## SQL 查询
```sql
"""
        return prompt

    async def _generate_with_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM 生成 SQL"""
        try:
            response = requests.post(
                f"{self.llm_endpoint}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                # 清理 SQL
                sql = content.replace("```sql", "").replace("```", "").strip()
                return sql
            else:
                logger.error(f"LLM API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证 SQL 安全性"""
        sql_upper = sql.upper().strip()

        # 检查危险关键词
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE", "GRANT", "REVOKE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "error": f"Dangerous keyword '{keyword}' detected"
                }

        # 检查 SQL 注入模式
        injection_patterns = [
            ";--", "';--", "1=1", "OR 1=1", "' OR '", "UNION SELECT"
        ]
        for pattern in injection_patterns:
            if pattern.upper() in sql_upper:
                return {
                    "valid": False,
                    "error": f"Potential SQL injection pattern detected"
                }

        # 检查是否以 SELECT 开头
        if not sql_upper.startswith("SELECT"):
            return {
                "valid": False,
                "error": "Only SELECT queries are allowed"
            }

        return {"valid": True}

    def clear_history(self, conversation_id: str = None) -> None:
        """清除历史记录"""
        if conversation_id:
            if conversation_id in self._history_cache:
                del self._history_cache[conversation_id]
        else:
            self._history_cache.clear()


# ==================== 统一集成服务 ====================

class AlldataIntegrationService:
    """Alldata 统一集成服务

    提供完整的 Alldata → Bisheng 集成能力
    """

    _instance: Optional['AlldataIntegrationService'] = None

    def __init__(self):
        self.client = AlldataClient()
        self.metadata = MetadataService(self.client)
        self.vector = EnhancedVectorSearchService(self.client)
        self.text2sql = EnhancedText2SQLService(self.metadata)

    @classmethod
    def get_instance(cls) -> 'AlldataIntegrationService':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def hybrid_query(
        self,
        question: str,
        mode: str = "auto",
        database: str = None,
        collection: str = None,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        混合查询（自动选择 SQL 或 RAG）

        Args:
            question: 用户问题
            mode: 查询模式 (auto, sql, rag, hybrid)
            database: 数据库名称
            collection: 向量集合名称
            conversation_id: 会话 ID

        Returns:
            查询结果
        """
        results = {
            "question": question,
            "mode": mode,
            "sql_result": None,
            "rag_result": None
        }

        # 判断查询模式
        if mode == "auto":
            mode = self._detect_query_mode(question)
            results["detected_mode"] = mode

        # 执行查询
        if mode in ("sql", "hybrid"):
            sql_result = await self.text2sql.generate_sql(
                question=question,
                database=database or "sales_dw",
                conversation_id=conversation_id
            )
            results["sql_result"] = sql_result

        if mode in ("rag", "hybrid"):
            rag_result = await self.vector.search_with_metadata(
                query=question,
                collection=collection or "enterprise_docs",
                top_k=5
            )
            results["rag_result"] = {
                "success": True,
                "documents": rag_result
            }

        return results

    def _detect_query_mode(self, question: str) -> str:
        """检测查询模式"""
        # SQL 关键词
        sql_keywords = [
            "多少", "总数", "平均", "最大", "最小", "统计", "查询",
            "销售额", "订单", "数量", "金额", "增长", "下降", "同比", "环比",
            "上个月", "今年", "去年", "季度", "year", "month", "sum", "count"
        ]

        # RAG 关键词
        rag_keywords = [
            "政策", "规定", "流程", "说明", "解释", "什么是", "如何",
            "为什么", "文档", "手册", "指南"
        ]

        question_lower = question.lower()

        sql_score = sum(1 for kw in sql_keywords if kw in question_lower)
        rag_score = sum(1 for kw in rag_keywords if kw in question_lower)

        if sql_score > rag_score:
            return "sql"
        elif rag_score > sql_score:
            return "rag"
        else:
            return "hybrid"
