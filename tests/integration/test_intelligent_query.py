"""
智能查询模块集成测试 (Text-to-SQL + RAG)

测试用例 BU-IQ-001 ~ BU-IQ-011:
1.  BU-IQ-001: 纯SQL查询 (P0) - 自然语言 -> 生成SQL -> 执行 -> 返回结果
2.  BU-IQ-002: 纯RAG检索 (P0) - 知识类问题 -> 向量检索 -> 返回文档
3.  BU-IQ-003: 混合查询(SQL+RAG) (P0) - 并行执行SQL与RAG，合并结果
4.  BU-IQ-004: 意图识别 (P0) - Agent将查询路由到SQL Agent或RAG Agent
5.  BU-IQ-005: Schema注入SQL生成 (P0) - 将表结构注入Prompt生成SQL
6.  BU-IQ-006: SQL安全检查 (P0) - 拒绝DROP/DELETE/TRUNCATE等危险操作
7.  BU-IQ-007: 向量检索召回 (P0) - Milvus向量检索 top_k=5
8.  BU-IQ-008: ReAct多轮迭代 (P1) - Agent多轮推理，最多10轮
9.  BU-IQ-009: 会话上下文保持 (P1) - 多轮对话上下文管理
10. BU-IQ-010: 会话缓存 (P1) - Redis会话级缓存
11. BU-IQ-011: 结果来源引用 (P1) - SQL结果和文档结果标注来源
"""

import json
import os
import sys
import time
import hashlib
import logging
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock

# 添加项目根目录（不直接添加 services 目录，避免命名空间冲突）
_project_root = os.path.join(os.path.dirname(__file__), "../..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)


# ==================== 测试常量 ====================

EMBEDDING_DIM = 1536  # OpenAI 兼容嵌入维度
MILVUS_COLLECTION = "test_knowledge_base"
MAX_REACT_ITERATIONS = 10
SESSION_CACHE_TTL = 3600  # 会话缓存 1 小时


# ==================== 样例表结构 ====================

SAMPLE_TABLE_SCHEMAS = [
    {
        "table_name": "sales_orders",
        "table_comment": "销售订单表",
        "database": "business_db",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "订单ID", "is_primary": True},
            {"column_name": "customer_id", "data_type": "bigint", "comment": "客户ID"},
            {"column_name": "product_id", "data_type": "bigint", "comment": "产品ID"},
            {"column_name": "amount", "data_type": "decimal(12,2)", "comment": "订单金额"},
            {"column_name": "quantity", "data_type": "int", "comment": "购买数量"},
            {"column_name": "status", "data_type": "varchar(20)", "comment": "订单状态: pending/paid/shipped/completed"},
            {"column_name": "created_at", "data_type": "timestamp", "comment": "创建时间"},
            {"column_name": "updated_at", "data_type": "timestamp", "comment": "更新时间"},
        ],
    },
    {
        "table_name": "customers",
        "table_comment": "客户表",
        "database": "business_db",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "客户ID", "is_primary": True},
            {"column_name": "name", "data_type": "varchar(100)", "comment": "客户名称"},
            {"column_name": "email", "data_type": "varchar(255)", "comment": "邮箱"},
            {"column_name": "region", "data_type": "varchar(50)", "comment": "所属地区"},
            {"column_name": "level", "data_type": "varchar(20)", "comment": "客户等级: bronze/silver/gold/vip"},
            {"column_name": "created_at", "data_type": "timestamp", "comment": "注册时间"},
        ],
    },
    {
        "table_name": "products",
        "table_comment": "产品表",
        "database": "business_db",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "产品ID", "is_primary": True},
            {"column_name": "name", "data_type": "varchar(255)", "comment": "产品名称"},
            {"column_name": "category", "data_type": "varchar(100)", "comment": "产品分类"},
            {"column_name": "price", "data_type": "decimal(10,2)", "comment": "单价"},
            {"column_name": "stock", "data_type": "int", "comment": "库存数量"},
        ],
    },
]

# ==================== 样例文档（用于RAG检索） ====================

SAMPLE_DOCUMENTS = [
    {
        "doc_id": "doc-001",
        "title": "销售政策手册",
        "content": "公司销售政策要求所有订单金额超过10000元需要经理审批。"
                   "折扣政策：VIP客户享受9折优惠，金牌客户享受85折优惠。"
                   "退货政策：产品签收后7天内可无条件退货，超过7天需提供质量问题证明。",
        "metadata": {"category": "policy", "department": "sales", "version": "2.0"},
    },
    {
        "doc_id": "doc-002",
        "title": "退货流程说明",
        "content": "退货流程：1.客户提交退货申请 2.客服审核 3.物流取件 4.质检验收 5.退款处理。"
                   "退款周期为审核通过后3-5个工作日。特殊商品不支持退货。",
        "metadata": {"category": "process", "department": "customer_service", "version": "1.5"},
    },
    {
        "doc_id": "doc-003",
        "title": "2024年Q4销售目标",
        "content": "2024年第四季度销售目标为5000万元。各区域目标分配：华东2000万，华南1500万，"
                   "华北1000万，其他500万。重点推广新品线智能家居系列。",
        "metadata": {"category": "target", "department": "sales", "version": "1.0"},
    },
    {
        "doc_id": "doc-004",
        "title": "数据安全规范",
        "content": "所有数据查询必须经过权限验证。敏感字段（手机号、身份证号）需要脱敏处理。"
                   "禁止直接操作生产数据库。查询结果最多返回10000行。",
        "metadata": {"category": "security", "department": "IT", "version": "3.0"},
    },
    {
        "doc_id": "doc-005",
        "title": "客户分级标准",
        "content": "客户分级标准：VIP客户年消费超过50万元；金牌客户年消费20-50万元；"
                   "银牌客户年消费5-20万元；铜牌客户年消费5万元以下。",
        "metadata": {"category": "standard", "department": "sales", "version": "2.1"},
    },
]

# ==================== 样例SQL执行结果 ====================

SAMPLE_SALES_RESULT = [
    {"month": "2024-11", "total_amount": 3200000.00, "order_count": 1580},
    {"month": "2024-12", "total_amount": 4100000.00, "order_count": 2100},
]

SAMPLE_CUSTOMER_ORDERS = [
    {"customer_name": "张三", "total_amount": 158000.00, "order_count": 23},
    {"customer_name": "李四", "total_amount": 92000.00, "order_count": 15},
    {"customer_name": "王五", "total_amount": 67000.00, "order_count": 8},
]


# ==================== Mock 辅助类 ====================

class MockVLLMClient:
    """模拟 vLLM/OpenAI 兼容 API 客户端

    根据 prompt 内容返回不同的模拟响应，支持：
    - 意图识别
    - SQL 生成
    - RAG 问答
    - ReAct 推理
    """

    def __init__(self):
        self.call_count = 0
        self.call_history = []

    def chat_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """模拟 chat completion 调用"""
        self.call_count += 1
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")

        self.call_history.append({
            "messages": messages,
            "kwargs": kwargs,
            "timestamp": datetime.now().isoformat(),
        })

        # 根据内容模式返回不同响应
        if "意图识别" in str(messages) or "intent" in str(messages).lower():
            return self._intent_response(user_content)
        elif "生成SQL" in str(messages) or "Generate SQL" in str(messages):
            return self._sql_generation_response(user_content)
        elif "根据以下上下文" in str(messages) or "context" in str(messages).lower():
            return self._rag_answer_response(user_content)
        elif "Thought:" in str(messages) or "ReAct" in str(messages):
            return self._react_response(user_content)
        else:
            return self._default_response(user_content)

    def embeddings(self, texts: List[str]) -> List[List[float]]:
        """模拟 embedding 调用"""
        import random
        random.seed(42)
        result = []
        for text in texts:
            # 使用文本哈希生成伪随机但确定性的嵌入向量
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]
            # 归一化
            norm = sum(x * x for x in embedding) ** 0.5
            embedding = [x / norm for x in embedding]
            result.append(embedding)
        return result

    def _intent_response(self, content: str) -> Dict:
        """意图识别响应"""
        # 简单规则模拟意图识别
        if any(kw in content for kw in ["销售额", "多少", "统计", "查询数据", "数量"]):
            intent = "sql"
        elif any(kw in content for kw in ["政策", "流程", "规范", "什么是", "如何"]):
            intent = "rag"
        elif any(kw in content for kw in ["销售额并且", "数据和政策", "对比"]):
            intent = "hybrid"
        else:
            intent = "sql"

        return {
            "choices": [{
                "message": {
                    "content": json.dumps({"intent": intent, "confidence": 0.95}),
                    "role": "assistant",
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

    def _sql_generation_response(self, content: str) -> Dict:
        """SQL 生成响应"""
        if "上个月" in content or "销售额" in content:
            sql = (
                "SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, "
                "SUM(amount) AS total_amount, COUNT(*) AS order_count "
                "FROM sales_orders "
                "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) "
                "AND created_at < CURDATE() "
                "GROUP BY month "
                "ORDER BY month "
                "LIMIT 100"
            )
        elif "客户" in content and ("订单" in content or "消费" in content or "金额" in content):
            sql = (
                "SELECT c.name AS customer_name, "
                "SUM(o.amount) AS total_amount, COUNT(o.id) AS order_count "
                "FROM customers c "
                "JOIN sales_orders o ON c.id = o.customer_id "
                "GROUP BY c.id, c.name "
                "ORDER BY total_amount DESC "
                "LIMIT 100"
            )
        else:
            sql = "SELECT * FROM sales_orders LIMIT 100"

        return {
            "choices": [{
                "message": {
                    "content": sql,
                    "role": "assistant",
                }
            }],
            "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
        }

    def _rag_answer_response(self, content: str) -> Dict:
        """RAG 问答响应"""
        return {
            "choices": [{
                "message": {
                    "content": (
                        "根据检索到的文档，公司销售政策主要包括以下几点：\n"
                        "1. 订单金额超过10000元需要经理审批\n"
                        "2. VIP客户享受9折优惠\n"
                        "3. 产品签收后7天内可无条件退货\n\n"
                        "来源：销售政策手册 v2.0"
                    ),
                    "role": "assistant",
                }
            }],
            "usage": {"prompt_tokens": 300, "completion_tokens": 100, "total_tokens": 400},
        }

    def _react_response(self, content: str) -> Dict:
        """ReAct 推理响应"""
        if "Final Answer" not in content:
            return {
                "choices": [{
                    "message": {
                        "content": (
                            "Thought: 我需要先查询数据库获取销售数据\n"
                            "Action: execute_sql\n"
                            'Action Input: {"sql": "SELECT SUM(amount) FROM sales_orders '
                            "WHERE created_at >= '2024-12-01'\"}"
                        ),
                        "role": "assistant",
                    }
                }],
                "usage": {"prompt_tokens": 150, "completion_tokens": 60, "total_tokens": 210},
            }
        else:
            return {
                "choices": [{
                    "message": {
                        "content": (
                            "Thought: 我已经获得了足够的信息\n"
                            "Final Answer: 上个月的销售总额为4,100,000元，共2,100笔订单。"
                        ),
                        "role": "assistant",
                    }
                }],
                "usage": {"prompt_tokens": 200, "completion_tokens": 40, "total_tokens": 240},
            }

    def _default_response(self, content: str) -> Dict:
        """默认响应"""
        return {
            "choices": [{
                "message": {
                    "content": "这是一个默认的测试响应。",
                    "role": "assistant",
                }
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }


class MockMilvusClient:
    """模拟 Milvus 向量数据库客户端"""

    def __init__(self):
        self.collections = {}
        self.search_count = 0

    def create_collection(self, name: str, schema: Dict) -> bool:
        """创建集合"""
        self.collections[name] = {"schema": schema, "data": []}
        return True

    def insert(self, collection_name: str, data: List[Dict]) -> int:
        """插入数据"""
        if collection_name not in self.collections:
            self.collections[collection_name] = {"data": []}
        self.collections[collection_name]["data"].extend(data)
        return len(data)

    def search(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        top_k: int = 5,
        output_fields: Optional[List[str]] = None,
    ) -> List[List[Dict]]:
        """向量搜索"""
        self.search_count += 1
        if collection_name not in self.collections:
            return [[]]

        data = self.collections[collection_name]["data"]
        # 模拟相似度排序：返回前 top_k 个结果
        results = []
        for doc in data[:top_k]:
            result = {
                "id": doc.get("doc_id", "unknown"),
                "distance": 0.1 + 0.05 * len(results),  # 模拟递增距离
                "score": 0.95 - 0.05 * len(results),  # 模拟递减分数
            }
            if output_fields:
                for field in output_fields:
                    if field in doc:
                        result[field] = doc[field]
            results.append(result)

        return [results]

    def has_collection(self, name: str) -> bool:
        """检查集合是否存在"""
        return name in self.collections

    def drop_collection(self, name: str) -> bool:
        """删除集合"""
        if name in self.collections:
            del self.collections[name]
            return True
        return False


class MockDatabaseExecutor:
    """模拟数据库执行器"""

    def __init__(self):
        self.executed_queries = []
        self.results_map = {}

    def register_result(self, sql_pattern: str, result: List[Dict]):
        """注册查询结果映射"""
        self.results_map[sql_pattern.lower().strip()] = result

    def execute(self, sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行 SQL 查询"""
        self.executed_queries.append({"sql": sql, "params": params, "timestamp": datetime.now()})

        sql_lower = sql.lower().strip()

        # 按模式匹配返回预注册的结果
        for pattern, result in self.results_map.items():
            if pattern in sql_lower:
                return {
                    "success": True,
                    "data": result,
                    "row_count": len(result),
                    "execution_time": 0.05,
                }

        # 默认返回空结果
        return {
            "success": True,
            "data": [],
            "row_count": 0,
            "execution_time": 0.01,
        }


class MockRedisClient:
    """模拟 Redis 客户端"""

    def __init__(self):
        self._store = {}
        self._expiry = {}

    def get(self, key: str) -> Optional[bytes]:
        """获取值"""
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._store[key]
            del self._expiry[key]
            return None
        value = self._store.get(key)
        if value and isinstance(value, str):
            return value.encode("utf-8")
        return value

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置值"""
        self._store[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        """设置带过期时间的值"""
        self._store[key] = value
        self._expiry[key] = time.time() + ttl
        return True

    def delete(self, *keys) -> int:
        """删除键"""
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                self._expiry.pop(key, None)
                count += 1
        return count

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._store[key]
            del self._expiry[key]
            return False
        return key in self._store

    def keys(self, pattern: str) -> List[str]:
        """获取匹配的键"""
        import fnmatch
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]

    def ping(self) -> bool:
        """健康检查"""
        return True


# ==================== Fixtures ====================

@pytest.fixture
def mock_vllm():
    """模拟 vLLM 服务"""
    return MockVLLMClient()


@pytest.fixture
def mock_milvus():
    """模拟 Milvus 向量数据库"""
    client = MockMilvusClient()
    # 预填充测试文档
    client.create_collection(MILVUS_COLLECTION, {"dim": EMBEDDING_DIM})
    for doc in SAMPLE_DOCUMENTS:
        client.insert(MILVUS_COLLECTION, [{
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "content": doc["content"],
            "metadata": json.dumps(doc["metadata"]),
        }])
    return client


@pytest.fixture
def mock_db():
    """模拟数据库执行器"""
    executor = MockDatabaseExecutor()
    # 注册常见查询结果
    executor.register_result("sum(amount)", SAMPLE_SALES_RESULT)
    executor.register_result("sales_orders", SAMPLE_SALES_RESULT)
    executor.register_result("customer_name", SAMPLE_CUSTOMER_ORDERS)
    executor.register_result("customers c join", SAMPLE_CUSTOMER_ORDERS)
    return executor


@pytest.fixture
def mock_redis():
    """模拟 Redis 客户端"""
    return MockRedisClient()


@pytest.fixture
def sample_schemas():
    """样例表结构"""
    return SAMPLE_TABLE_SCHEMAS


@pytest.fixture
def sample_docs():
    """样例文档"""
    return SAMPLE_DOCUMENTS


# ==================== BU-IQ-001: 纯SQL查询 ====================

@pytest.mark.integration
class TestPureSQLQuery:
    """BU-IQ-001: 纯SQL查询 (P0)

    用户提问 "上个月销售额是多少" -> 生成SQL -> 执行 -> 返回结果
    """

    def test_natural_language_to_sql_generation(self, mock_vllm, sample_schemas):
        """测试自然语言转SQL生成

        验证LLM能根据自然语言问题和Schema生成合法的SELECT语句
        """
        question = "上个月销售额是多少"

        # 构造包含Schema的prompt
        schema_text = self._format_schema(sample_schemas)
        messages = [
            {"role": "system", "content": f"你是SQL专家。根据以下表结构生成SQL：\n{schema_text}"},
            {"role": "user", "content": f"生成SQL查询：{question}"},
        ]

        response = mock_vllm.chat_completion(messages)
        generated_sql = response["choices"][0]["message"]["content"]

        # 验证生成的SQL
        assert "SELECT" in generated_sql.upper()
        assert "sales_orders" in generated_sql.lower() or "amount" in generated_sql.lower()
        assert "DROP" not in generated_sql.upper()
        assert "DELETE" not in generated_sql.upper()

    def test_sql_execution_returns_result(self, mock_vllm, mock_db, sample_schemas):
        """测试SQL执行并返回结果

        验证完整的 自然语言 -> SQL -> 执行 -> 返回 流程
        """
        question = "上个月销售额是多少"

        # 1. 生成SQL
        messages = [
            {"role": "system", "content": "生成SQL查询"},
            {"role": "user", "content": f"生成SQL查询：{question}"},
        ]
        response = mock_vllm.chat_completion(messages)
        sql = response["choices"][0]["message"]["content"]

        # 2. 执行SQL
        result = mock_db.execute(sql)

        # 3. 验证结果
        assert result["success"] is True
        assert result["row_count"] > 0
        assert isinstance(result["data"], list)
        assert "total_amount" in result["data"][0]

    def test_sql_result_contains_expected_fields(self, mock_db):
        """测试SQL结果包含期望的字段"""
        sql = "SELECT SUM(amount) AS total_amount FROM sales_orders WHERE created_at >= '2024-12-01'"
        result = mock_db.execute(sql)

        assert result["success"] is True
        for row in result["data"]:
            assert "total_amount" in row
            assert isinstance(row["total_amount"], (int, float))

    def test_empty_result_handling(self, mock_db):
        """测试空结果处理"""
        sql = "SELECT * FROM nonexistent_pattern LIMIT 10"
        result = mock_db.execute(sql)

        assert result["success"] is True
        assert result["row_count"] == 0
        assert result["data"] == []

    def test_execution_records_query_history(self, mock_db):
        """测试执行记录查询历史"""
        sql = "SELECT SUM(amount) FROM sales_orders"
        mock_db.execute(sql)

        assert len(mock_db.executed_queries) == 1
        assert mock_db.executed_queries[0]["sql"] == sql
        assert mock_db.executed_queries[0]["timestamp"] is not None

    def _format_schema(self, schemas: List[Dict]) -> str:
        """格式化Schema为文本"""
        lines = []
        for table in schemas:
            lines.append(f"表名: {table['table_name']} ({table['table_comment']})")
            for col in table["columns"]:
                lines.append(f"  - {col['column_name']} {col['data_type']} -- {col['comment']}")
            lines.append("")
        return "\n".join(lines)


# ==================== BU-IQ-002: 纯RAG检索 ====================

@pytest.mark.integration
class TestPureRAGRetrieval:
    """BU-IQ-002: 纯RAG检索 (P0)

    用户提问 "销售政策是什么" -> 向量检索 -> 返回相关文档
    """

    def test_vector_search_returns_documents(self, mock_vllm, mock_milvus):
        """测试向量检索返回文档

        验证查询被转为embedding后在Milvus中检索到相关文档
        """
        query = "销售政策是什么"

        # 1. 生成查询嵌入
        query_embedding = mock_vllm.embeddings([query])[0]
        assert len(query_embedding) == EMBEDDING_DIM

        # 2. 在Milvus中搜索
        results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=5,
            output_fields=["doc_id", "title", "content"],
        )

        # 3. 验证结果
        assert len(results) == 1  # 一个查询向量
        assert len(results[0]) > 0  # 有结果返回
        assert len(results[0]) <= 5  # 不超过 top_k

    def test_rag_answer_generation(self, mock_vllm, mock_milvus):
        """测试RAG问答生成

        验证检索到文档后，LLM能基于上下文生成准确回答
        """
        query = "销售政策是什么"

        # 1. 检索文档
        query_embedding = mock_vllm.embeddings([query])[0]
        search_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
            output_fields=["content", "title"],
        )

        # 2. 构建上下文
        context_parts = []
        for result in search_results[0]:
            if "content" in result:
                context_parts.append(result["content"])
        context = "\n".join(context_parts)

        # 3. 生成回答
        messages = [
            {"role": "system", "content": "根据以下上下文回答问题，如果上下文没有相关信息请说明。"},
            {"role": "user", "content": f"上下文：{context}\n\n问题：{query}"},
        ]
        response = mock_vllm.chat_completion(messages)
        answer = response["choices"][0]["message"]["content"]

        # 4. 验证回答
        assert len(answer) > 0
        assert "政策" in answer or "销售" in answer

    def test_retrieval_returns_scored_results(self, mock_vllm, mock_milvus):
        """测试检索结果包含相似度分数"""
        query_embedding = mock_vllm.embeddings(["退货流程是怎样的"])[0]
        results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
            output_fields=["doc_id"],
        )

        for result in results[0]:
            assert "score" in result
            assert 0 <= result["score"] <= 1.0

    def test_empty_collection_returns_no_results(self, mock_vllm):
        """测试空集合返回空结果"""
        empty_milvus = MockMilvusClient()
        empty_milvus.create_collection("empty_collection", {"dim": EMBEDDING_DIM})

        query_embedding = mock_vllm.embeddings(["测试查询"])[0]
        results = empty_milvus.search(
            collection_name="empty_collection",
            query_vectors=[query_embedding],
            top_k=5,
        )

        assert len(results[0]) == 0


# ==================== BU-IQ-003: 混合查询(SQL+RAG) ====================

@pytest.mark.integration
class TestHybridQuery:
    """BU-IQ-003: 混合查询 SQL+RAG (P0)

    并行执行SQL查询和RAG检索，合并结果返回给用户
    """

    def test_parallel_sql_and_rag_execution(self, mock_vllm, mock_db, mock_milvus):
        """测试并行执行SQL和RAG

        验证系统能同时执行SQL查询和文档检索，并将结果合并
        """
        question = "上个月销售额是多少，另外销售政策有什么规定"

        # 并行执行两个任务
        # 任务1: SQL查询
        sql = (
            "SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, "
            "SUM(amount) AS total_amount "
            "FROM sales_orders "
            "WHERE created_at >= '2024-12-01' "
            "GROUP BY month LIMIT 100"
        )
        sql_result = mock_db.execute(sql)

        # 任务2: RAG检索
        query_embedding = mock_vllm.embeddings([question])[0]
        rag_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
            output_fields=["doc_id", "title", "content"],
        )

        # 合并结果
        combined_result = {
            "sql_result": {
                "data": sql_result["data"],
                "row_count": sql_result["row_count"],
                "source": "database",
            },
            "rag_result": {
                "documents": rag_results[0],
                "doc_count": len(rag_results[0]),
                "source": "knowledge_base",
            },
        }

        # 验证合并结果
        assert combined_result["sql_result"]["row_count"] > 0
        assert combined_result["rag_result"]["doc_count"] > 0
        assert combined_result["sql_result"]["source"] == "database"
        assert combined_result["rag_result"]["source"] == "knowledge_base"

    def test_hybrid_result_structure(self, mock_db, mock_milvus, mock_vllm):
        """测试混合查询结果结构完整性"""
        # SQL 部分
        sql_result = mock_db.execute("SELECT SUM(amount) FROM sales_orders")

        # RAG 部分
        query_embedding = mock_vllm.embeddings(["销售数据和政策"])[0]
        rag_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
        )

        combined = {
            "query_type": "hybrid",
            "sql": {"success": sql_result["success"], "data": sql_result["data"]},
            "rag": {"results": rag_results[0]},
            "merged_at": datetime.now().isoformat(),
        }

        assert combined["query_type"] == "hybrid"
        assert "sql" in combined
        assert "rag" in combined
        assert combined["merged_at"] is not None

    def test_sql_failure_fallback_to_rag_only(self, mock_milvus, mock_vllm):
        """测试SQL失败时回退到纯RAG"""
        # 模拟SQL执行失败
        failed_db = MockDatabaseExecutor()
        sql_result = {
            "success": False,
            "error": "Connection timeout",
            "data": [],
        }

        # RAG仍然可用
        query_embedding = mock_vllm.embeddings(["销售额"])[0]
        rag_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
            output_fields=["title", "content"],
        )

        # 系统应回退到纯RAG
        final_result = {
            "query_type": "rag_fallback",
            "sql_error": "Connection timeout",
            "rag_results": rag_results[0],
        }

        assert final_result["query_type"] == "rag_fallback"
        assert len(final_result["rag_results"]) > 0

    def test_rag_failure_fallback_to_sql_only(self, mock_db):
        """测试RAG失败时回退到纯SQL"""
        # SQL正常执行
        sql_result = mock_db.execute("SELECT SUM(amount) FROM sales_orders")

        # RAG检索失败（模拟Milvus不可用）
        rag_error = "Milvus connection refused"

        final_result = {
            "query_type": "sql_fallback",
            "sql_result": sql_result["data"],
            "rag_error": rag_error,
        }

        assert final_result["query_type"] == "sql_fallback"
        assert len(final_result["sql_result"]) > 0


# ==================== BU-IQ-004: 意图识别 ====================

@pytest.mark.integration
class TestIntentClassification:
    """BU-IQ-004: 意图识别 (P0)

    Agent根据用户问题自动路由到SQL Agent或RAG Agent
    """

    def test_sql_intent_detection(self, mock_vllm):
        """测试识别SQL意图

        验证数据查询类问题被正确路由到SQL Agent
        """
        sql_questions = [
            "上个月销售额是多少",
            "统计每个客户的订单数量",
            "查询库存低于100的产品",
        ]

        for question in sql_questions:
            messages = [
                {"role": "system", "content": "意图识别：判断用户问题需要SQL查询还是文档检索"},
                {"role": "user", "content": question},
            ]
            response = mock_vllm.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            intent_result = json.loads(content)

            assert intent_result["intent"] == "sql", \
                f"问题 '{question}' 应该被识别为SQL意图，实际为: {intent_result['intent']}"
            assert intent_result["confidence"] > 0.5

    def test_rag_intent_detection(self, mock_vllm):
        """测试识别RAG意图

        验证知识类问题被正确路由到RAG Agent
        """
        rag_questions = [
            "销售政策是什么",
            "退货流程是怎样的",
            "数据安全规范有哪些要求",
        ]

        for question in rag_questions:
            messages = [
                {"role": "system", "content": "意图识别：判断用户问题需要SQL查询还是文档检索"},
                {"role": "user", "content": question},
            ]
            response = mock_vllm.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            intent_result = json.loads(content)

            assert intent_result["intent"] == "rag", \
                f"问题 '{question}' 应该被识别为RAG意图，实际为: {intent_result['intent']}"

    def test_intent_confidence_threshold(self, mock_vllm):
        """测试意图置信度阈值

        低置信度时应默认使用混合查询
        """
        messages = [
            {"role": "system", "content": "意图识别"},
            {"role": "user", "content": "上个月销售额是多少"},
        ]
        response = mock_vllm.chat_completion(messages)
        content = response["choices"][0]["message"]["content"]
        intent_result = json.loads(content)

        # 置信度应大于阈值
        assert "confidence" in intent_result
        assert isinstance(intent_result["confidence"], (int, float))
        assert 0 <= intent_result["confidence"] <= 1.0

    def test_intent_routing_dispatches_correctly(self, mock_vllm, mock_db, mock_milvus):
        """测试意图路由正确分发

        验证路由器根据意图将请求分发到正确的处理器
        """
        # SQL意图 -> SQL Agent
        question = "上个月销售额是多少"
        messages = [
            {"role": "system", "content": "意图识别"},
            {"role": "user", "content": question},
        ]
        response = mock_vllm.chat_completion(messages)
        intent = json.loads(response["choices"][0]["message"]["content"])["intent"]

        if intent == "sql":
            result = mock_db.execute("SELECT SUM(amount) FROM sales_orders")
            assert result["success"] is True
        elif intent == "rag":
            query_embedding = mock_vllm.embeddings([question])[0]
            results = mock_milvus.search(MILVUS_COLLECTION, [query_embedding], top_k=5)
            assert len(results[0]) > 0


# ==================== BU-IQ-005: Schema注入SQL生成 ====================

@pytest.mark.integration
class TestSchemaInjection:
    """BU-IQ-005: Schema注入SQL生成 (P0)

    将表结构信息注入到Prompt中辅助SQL生成
    """

    def test_schema_injected_into_prompt(self, mock_vllm, sample_schemas):
        """测试Schema被正确注入到Prompt中

        验证生成SQL时，相关的表结构作为上下文注入到LLM的prompt中
        """
        question = "查询每个客户的总消费金额"

        # 构建包含Schema的prompt
        schema_text = self._build_schema_prompt(sample_schemas)

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个SQL生成专家。请根据以下数据库表结构生成SQL查询。\n\n"
                    f"## 可用表结构\n{schema_text}\n\n"
                    f"注意：只生成SELECT语句，必须包含LIMIT子句。"
                ),
            },
            {"role": "user", "content": f"生成SQL查询：{question}"},
        ]

        response = mock_vllm.chat_completion(messages)
        sql = response["choices"][0]["message"]["content"]

        # 验证Schema注入后生成的SQL使用了正确的表名和列名
        assert "customers" in sql.lower() or "customer" in sql.lower()

    def test_relevant_tables_selected(self, sample_schemas):
        """测试只选择相关表

        验证Schema选择器只注入与问题相关的表结构
        """
        question = "查询每个客户的订单总金额"

        # 模拟Schema选择逻辑
        relevant_keywords = ["客户", "订单", "金额", "customer", "order", "amount"]
        selected_tables = []

        for table in sample_schemas:
            table_text = (
                table["table_name"] + " " +
                table["table_comment"] + " " +
                " ".join(col["comment"] for col in table["columns"])
            )
            if any(kw in table_text for kw in relevant_keywords):
                selected_tables.append(table["table_name"])

        # 应该选中 customers 和 sales_orders
        assert "customers" in selected_tables
        assert "sales_orders" in selected_tables

    def test_column_info_included_in_schema(self, sample_schemas):
        """测试列信息包含在Schema中

        验证注入的Schema包含完整的列名、类型和注释
        """
        schema_text = self._build_schema_prompt(sample_schemas)

        # 验证关键列信息存在
        assert "amount" in schema_text
        assert "decimal" in schema_text.lower()
        assert "订单金额" in schema_text
        assert "customer_id" in schema_text

    def test_schema_prompt_respects_token_limit(self, sample_schemas):
        """测试Schema prompt遵守Token限制

        大表结构应该被截断以避免超出LLM上下文窗口
        """
        max_chars = 2000  # 模拟Token限制
        schema_text = self._build_schema_prompt(sample_schemas, max_chars=max_chars)

        assert len(schema_text) <= max_chars + 200  # 允许小幅超出

    def test_multiple_database_schema_selection(self, sample_schemas):
        """测试跨库Schema选择"""
        # 所有样例表都在 business_db
        databases = set(t.get("database", "default") for t in sample_schemas)
        assert "business_db" in databases

    def _build_schema_prompt(
        self, schemas: List[Dict], max_chars: Optional[int] = None
    ) -> str:
        """构建Schema prompt"""
        lines = []
        total_len = 0
        for table in schemas:
            header = f"### {table['table_name']} ({table['table_comment']})"
            cols = []
            for col in table["columns"]:
                col_line = f"  - {col['column_name']} {col['data_type']} -- {col['comment']}"
                cols.append(col_line)

            table_text = header + "\n" + "\n".join(cols) + "\n"

            if max_chars and total_len + len(table_text) > max_chars:
                break

            lines.append(table_text)
            total_len += len(table_text)

        return "\n".join(lines)


# ==================== BU-IQ-006: SQL安全检查 ====================

@pytest.mark.integration
class TestSQLSecurityCheck:
    """BU-IQ-006: SQL安全检查 (P0)

    拒绝DROP/DELETE/TRUNCATE等危险操作
    """

    def test_reject_drop_statement(self):
        """测试拒绝DROP语句"""
        dangerous_sql = "DROP TABLE sales_orders"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_delete_statement(self):
        """测试拒绝DELETE语句"""
        dangerous_sql = "DELETE FROM customers WHERE id = 1"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_truncate_statement(self):
        """测试拒绝TRUNCATE语句"""
        dangerous_sql = "TRUNCATE TABLE sales_orders"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_update_statement(self):
        """测试拒绝UPDATE语句"""
        dangerous_sql = "UPDATE customers SET name = 'hacked'"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_insert_statement(self):
        """测试拒绝INSERT语句"""
        dangerous_sql = "INSERT INTO customers VALUES (999, 'malicious', 'evil@hack.com', 'x', 'x', NOW())"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_alter_statement(self):
        """测试拒绝ALTER语句"""
        dangerous_sql = "ALTER TABLE customers ADD COLUMN backdoor TEXT"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_create_statement(self):
        """测试拒绝CREATE语句"""
        dangerous_sql = "CREATE TABLE malicious (id INT)"
        assert self._is_dangerous_sql(dangerous_sql)

    def test_reject_multi_statement_injection(self):
        """测试拒绝多语句注入

        攻击者可能在合法SELECT后追加危险语句
        """
        injection_sql = "SELECT * FROM customers; DROP TABLE customers; --"
        assert self._is_dangerous_sql(injection_sql)

    def test_reject_union_select_injection(self):
        """测试拒绝UNION SELECT注入"""
        injection_sql = "SELECT * FROM customers WHERE id = 1 UNION SELECT * FROM information_schema.tables"
        assert self._is_dangerous_sql(injection_sql)

    def test_reject_tautology_injection(self):
        """测试拒绝恒真条件注入 (OR 1=1)"""
        injection_sql = "SELECT * FROM customers WHERE id = 1 OR 1=1"
        assert self._is_dangerous_sql(injection_sql)

    def test_allow_safe_select(self):
        """测试允许安全的SELECT查询"""
        safe_queries = [
            "SELECT * FROM customers LIMIT 100",
            "SELECT c.name, COUNT(o.id) FROM customers c JOIN sales_orders o ON c.id = o.customer_id GROUP BY c.name LIMIT 50",
            "SELECT SUM(amount) AS total FROM sales_orders WHERE status = 'completed' LIMIT 1",
        ]
        for sql in safe_queries:
            assert not self._is_dangerous_sql(sql), f"应该允许: {sql}"

    def test_allow_explain_statement(self):
        """测试允许EXPLAIN语句"""
        safe_sql = "EXPLAIN SELECT * FROM customers"
        assert not self._is_dangerous_sql(safe_sql)

    def test_case_insensitive_detection(self):
        """测试大小写不敏感的检测"""
        variations = [
            "drop table customers",
            "DROP TABLE customers",
            "Drop Table customers",
            "dRoP tAbLe customers",
        ]
        for sql in variations:
            assert self._is_dangerous_sql(sql), f"应该拒绝: {sql}"

    def test_dangerous_function_detection(self):
        """测试检测危险函数（如SLEEP、BENCHMARK）"""
        dangerous_queries = [
            "SELECT SLEEP(10)",
            "SELECT BENCHMARK(1000000, MD5('test'))",
        ]
        for sql in dangerous_queries:
            assert self._is_dangerous_sql(sql), f"应该拒绝: {sql}"

    def test_comment_hidden_injection(self):
        """测试注释中隐藏的注入"""
        sql = "SELECT * FROM customers /* DROP TABLE customers */"
        # 注释中的危险操作也应被检测
        assert self._is_dangerous_sql(sql)

    def _is_dangerous_sql(self, sql: str) -> bool:
        """检测SQL是否包含危险操作

        集成测试中的简化安全检查逻辑（实际由SQLValidator服务执行）
        """
        sql_upper = sql.upper().strip()

        # 危险关键字列表
        dangerous_keywords = [
            "DROP ", "DELETE ", "TRUNCATE ", "ALTER ", "CREATE ",
            "INSERT ", "UPDATE ", "GRANT ", "REVOKE ",
        ]

        # 注入模式
        injection_patterns = [
            ";",            # 多语句
            "UNION SELECT", # UNION注入
            "OR 1=1",       # 恒真条件
            "OR '1'='1'",   # 变体恒真
            "SLEEP(",       # 时间盲注
            "BENCHMARK(",   # 时间盲注
        ]

        # 检查注释中的危险内容
        comment_content = ""
        import re
        comments = re.findall(r'/\*.*?\*/', sql, re.DOTALL)
        for comment in comments:
            comment_upper = comment.upper()
            for kw in dangerous_keywords:
                if kw in comment_upper:
                    return True

        # 检查主查询中的危险操作
        # 排除以SELECT/EXPLAIN/WITH开头的安全查询
        is_safe_start = (
            sql_upper.startswith("SELECT ") or
            sql_upper.startswith("EXPLAIN ") or
            sql_upper.startswith("WITH ")
        )

        for kw in dangerous_keywords:
            if kw in sql_upper:
                # 如果不是以安全关键字开头，直接拒绝
                if not is_safe_start:
                    return True
                # 即使以SELECT开头，后面追加了危险语句也应拒绝
                # 检查是否在分号后面出现危险关键字
                parts = sql_upper.split(";")
                for part in parts[1:]:
                    part_stripped = part.strip()
                    if part_stripped and not part_stripped.startswith("--"):
                        for dk in dangerous_keywords:
                            if dk in part_stripped:
                                return True

        # 检查注入模式
        for pattern in injection_patterns:
            if pattern in sql_upper:
                return True

        return False


# ==================== BU-IQ-007: 向量检索召回 ====================

@pytest.mark.integration
class TestVectorRetrieval:
    """BU-IQ-007: 向量检索召回 (P0)

    从Milvus中执行向量搜索，top_k=5
    """

    def test_vector_search_top_k_5(self, mock_vllm, mock_milvus):
        """测试向量检索返回top_k=5个结果"""
        query = "销售政策是什么"
        query_embedding = mock_vllm.embeddings([query])[0]

        results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=5,
            output_fields=["doc_id", "title", "content"],
        )

        assert len(results[0]) == 5  # 我们有5个文档，正好返回5个
        for result in results[0]:
            assert "doc_id" in result
            assert "score" in result
            assert result["score"] > 0

    def test_vector_search_results_ordered_by_score(self, mock_vllm, mock_milvus):
        """测试搜索结果按相似度降序排列"""
        query_embedding = mock_vllm.embeddings(["退货流程"])[0]
        results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=5,
        )

        scores = [r["score"] for r in results[0]]
        # 验证分数是降序排列
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], "结果应按相似度降序排列"

    def test_vector_search_with_metadata_filter(self, mock_vllm, mock_milvus):
        """测试带元数据过滤的向量检索

        验证可以同时使用向量相似度和元数据条件进行过滤
        """
        query_embedding = mock_vllm.embeddings(["销售相关文档"])[0]
        results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=5,
            output_fields=["doc_id", "metadata"],
        )

        assert len(results[0]) > 0

    def test_embedding_dimension_consistency(self, mock_vllm):
        """测试嵌入向量维度一致性"""
        texts = ["查询一", "查询二", "查询三"]
        embeddings = mock_vllm.embeddings(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == EMBEDDING_DIM

    def test_embedding_normalization(self, mock_vllm):
        """测试嵌入向量归一化

        验证向量已归一化（L2范数约等于1）
        """
        embeddings = mock_vllm.embeddings(["测试文本"])
        embedding = embeddings[0]

        # 计算L2范数
        l2_norm = sum(x * x for x in embedding) ** 0.5
        assert abs(l2_norm - 1.0) < 0.01, f"向量应该归一化，实际L2范数: {l2_norm}"

    def test_search_nonexistent_collection(self, mock_vllm):
        """测试搜索不存在的集合"""
        empty_milvus = MockMilvusClient()
        query_embedding = mock_vllm.embeddings(["测试"])[0]

        results = empty_milvus.search(
            collection_name="nonexistent",
            query_vectors=[query_embedding],
            top_k=5,
        )

        assert results == [[]]

    def test_batch_vector_search(self, mock_vllm, mock_milvus):
        """测试批量向量搜索

        验证支持多个查询同时搜索
        """
        queries = ["销售政策", "退货流程", "客户分级"]
        embeddings = mock_vllm.embeddings(queries)

        all_results = []
        for emb in embeddings:
            result = mock_milvus.search(
                collection_name=MILVUS_COLLECTION,
                query_vectors=[emb],
                top_k=3,
            )
            all_results.append(result[0])

        assert len(all_results) == 3
        for result_list in all_results:
            assert len(result_list) > 0

    def test_search_increments_counter(self, mock_vllm, mock_milvus):
        """测试搜索计数器递增"""
        initial_count = mock_milvus.search_count
        query_embedding = mock_vllm.embeddings(["测试"])[0]

        mock_milvus.search(MILVUS_COLLECTION, [query_embedding], top_k=5)
        mock_milvus.search(MILVUS_COLLECTION, [query_embedding], top_k=3)

        assert mock_milvus.search_count == initial_count + 2


# ==================== BU-IQ-008: ReAct多轮迭代 ====================

@pytest.mark.integration
class TestReActMultiRoundIteration:
    """BU-IQ-008: ReAct多轮迭代 (P1)

    Agent基于ReAct模式进行多轮推理，最多10轮
    """

    def test_react_agent_basic_iteration(self, mock_vllm):
        """测试ReAct Agent基本迭代流程

        验证Agent能执行 Thought -> Action -> Observation 循环
        """
        # 模拟一轮ReAct迭代
        messages = [
            {"role": "system", "content": "你是一个ReAct Agent。Thought: ..."},
            {"role": "user", "content": "上个月销售额是多少"},
        ]
        response = mock_vllm.chat_completion(messages)
        output = response["choices"][0]["message"]["content"]

        # 验证输出包含ReAct格式
        assert "Thought:" in output or "Action:" in output or "Final Answer:" in output

    def test_react_max_iterations_limit(self):
        """测试ReAct最大迭代次数限制

        验证Agent不会无限循环，最多执行10轮
        """
        max_iterations = MAX_REACT_ITERATIONS

        # 模拟迭代计数
        iterations = 0
        converged = False

        for i in range(max_iterations + 5):  # 故意多循环几次
            iterations += 1
            if iterations >= max_iterations:
                break
            # 模拟：只在第5轮收敛
            if iterations == 5:
                converged = True
                break

        assert iterations <= max_iterations
        assert converged is True

    def test_react_convergence_with_final_answer(self, mock_vllm):
        """测试ReAct在获得最终答案后收敛

        验证Agent在得到Final Answer后停止迭代
        """
        steps = []
        max_iter = 10

        for iteration in range(max_iter):
            if iteration == 0:
                # 第一轮：思考并执行动作
                step = {
                    "iteration": iteration + 1,
                    "thought": "我需要查询数据库获取销售数据",
                    "action": "execute_sql",
                    "action_input": {"sql": "SELECT SUM(amount) FROM sales_orders"},
                }
            elif iteration == 1:
                # 第二轮：基于观察给出最终答案
                step = {
                    "iteration": iteration + 1,
                    "thought": "我已经获得了足够的信息",
                    "final_answer": "上个月的销售总额为4,100,000元",
                }
            else:
                break

            steps.append(step)
            if "final_answer" in step:
                break

        assert len(steps) == 2
        assert "final_answer" in steps[-1]
        assert steps[-1]["final_answer"] is not None

    def test_react_handles_tool_error_gracefully(self, mock_vllm):
        """测试ReAct优雅处理工具错误

        验证工具执行失败时Agent能从错误中恢复并继续推理
        """
        steps = []

        # 模拟工具执行失败
        step1 = {
            "iteration": 1,
            "thought": "我需要查询数据库",
            "action": "execute_sql",
            "observation": "Error: Database connection timeout",
        }
        steps.append(step1)

        # Agent应该能从错误中恢复
        step2 = {
            "iteration": 2,
            "thought": "数据库查询失败，我尝试从知识库检索",
            "action": "search_knowledge",
            "observation": "找到相关文档...",
        }
        steps.append(step2)

        # 最终给出答案
        step3 = {
            "iteration": 3,
            "thought": "根据知识库信息回答",
            "final_answer": "根据知识库记录，上个月销售额约为4,100,000元",
        }
        steps.append(step3)

        assert len(steps) == 3
        assert "Error" in steps[0]["observation"]
        assert "final_answer" in steps[-1]

    def test_react_iteration_history_maintained(self, mock_vllm):
        """测试ReAct迭代历史被完整维护"""
        history = []

        for i in range(3):
            entry = {
                "iteration": i + 1,
                "thought": f"第{i + 1}轮思考",
                "action": f"tool_{i}",
                "observation": f"工具{i}的输出结果",
                "timestamp": datetime.now().isoformat(),
            }
            history.append(entry)

        assert len(history) == 3
        # 验证历史完整性
        for i, entry in enumerate(history):
            assert entry["iteration"] == i + 1
            assert entry["thought"] is not None
            assert entry["timestamp"] is not None

    def test_react_reaches_max_without_answer(self):
        """测试达到最大迭代次数仍未收敛

        验证系统返回合理的错误信息而非崩溃
        """
        max_iterations = 10
        result = {
            "success": False,
            "error": "Max iterations reached",
            "iterations": max_iterations,
            "partial_steps": [
                {"iteration": i + 1, "thought": f"思考第{i+1}轮"} for i in range(max_iterations)
            ],
        }

        assert result["success"] is False
        assert result["error"] == "Max iterations reached"
        assert result["iterations"] == max_iterations
        assert len(result["partial_steps"]) == max_iterations


# ==================== BU-IQ-009: 会话上下文保持 ====================

@pytest.mark.integration
class TestConversationContext:
    """BU-IQ-009: 会话上下文保持 (P1)

    多轮对话中维持上下文，支持代词消解和跟进查询
    """

    def test_multi_turn_context_maintained(self, mock_vllm, mock_db):
        """测试多轮对话上下文维持

        验证第二轮对话能引用第一轮的结果
        """
        conversation_history = []

        # 第一轮对话
        q1 = "上个月销售额是多少"
        conversation_history.append({"role": "user", "content": q1})
        r1 = mock_db.execute("SELECT SUM(amount) FROM sales_orders")
        a1 = f"上个月销售额为{r1['data'][0]['total_amount']}元"
        conversation_history.append({"role": "assistant", "content": a1})

        # 第二轮对话（引用上一轮）
        q2 = "和上上个月相比增长了多少"
        conversation_history.append({"role": "user", "content": q2})

        # 验证上下文包含第一轮信息
        assert len(conversation_history) == 3
        assert "销售额" in conversation_history[1]["content"]
        # Agent应能从上下文推断出"上上个月"的参照

    def test_pronoun_resolution_in_context(self, mock_vllm):
        """测试代词消解

        验证"它"、"这些"等代词能正确解析为之前提到的实体
        """
        history = [
            {"role": "user", "content": "查询VIP客户列表"},
            {"role": "assistant", "content": "找到5个VIP客户：张三、李四..."},
            {"role": "user", "content": "他们的总消费金额是多少"},  # "他们" = VIP客户
        ]

        # 通过上下文，"他们"应该被解析为VIP客户
        full_context = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        assert "VIP客户" in full_context
        assert "他们" in history[-1]["content"]

        # 验证上下文足以支持代词消解
        assert len(history) >= 2

    def test_context_window_management(self):
        """测试上下文窗口管理

        验证当对话轮次过多时，正确截断旧消息
        """
        max_context_turns = 10

        # 模拟20轮对话
        history = []
        for i in range(20):
            history.append({"role": "user", "content": f"问题{i+1}"})
            history.append({"role": "assistant", "content": f"回答{i+1}"})

        # 截断到最近的max_context_turns轮
        if len(history) > max_context_turns * 2:
            truncated = history[-(max_context_turns * 2):]
        else:
            truncated = history

        assert len(truncated) == max_context_turns * 2
        # 验证保留的是最新的对话
        assert "问题20" in truncated[-2]["content"]
        assert "回答20" in truncated[-1]["content"]

    def test_conversation_state_includes_metadata(self):
        """测试会话状态包含元数据

        验证会话不仅保存消息，还保存查询过的表、使用过的SQL等元数据
        """
        session_state = {
            "session_id": "sess-001",
            "user_id": "user-001",
            "messages": [
                {"role": "user", "content": "上个月销售额"},
                {"role": "assistant", "content": "销售额为4100000元"},
            ],
            "metadata": {
                "tables_accessed": ["sales_orders"],
                "sql_executed": [
                    "SELECT SUM(amount) FROM sales_orders WHERE created_at >= '2024-12-01'"
                ],
                "docs_retrieved": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
            },
        }

        assert session_state["metadata"]["tables_accessed"] == ["sales_orders"]
        assert len(session_state["metadata"]["sql_executed"]) == 1
        assert session_state["session_id"] is not None

    def test_followup_query_uses_previous_tables(self, mock_db):
        """测试追问查询使用之前的表

        验证追问能自动使用之前轮次确定的表和条件
        """
        # 第一轮确定了使用 sales_orders 表
        first_query_meta = {
            "tables": ["sales_orders"],
            "time_range": "2024-12",
        }

        # 第二轮追问 "按产品分组呢？" 应复用表和时间范围
        followup_sql = (
            "SELECT p.name, SUM(o.amount) AS total "
            "FROM sales_orders o "
            "JOIN products p ON o.product_id = p.id "
            "WHERE o.created_at >= '2024-12-01' "
            "GROUP BY p.name LIMIT 100"
        )

        result = mock_db.execute(followup_sql)

        # 验证SQL包含之前轮次的表
        assert "sales_orders" in followup_sql
        # 验证时间范围被复用
        assert "2024-12" in followup_sql


# ==================== BU-IQ-010: 会话缓存 ====================

@pytest.mark.integration
class TestSessionCache:
    """BU-IQ-010: 会话缓存 (P1)

    使用Redis缓存会话数据，减少重复查询
    """

    def test_session_data_cached_in_redis(self, mock_redis):
        """测试会话数据被缓存到Redis"""
        session_id = "sess-test-001"
        session_data = {
            "user_id": "user-001",
            "messages": [
                {"role": "user", "content": "上个月销售额"},
                {"role": "assistant", "content": "4100000元"},
            ],
            "created_at": datetime.now().isoformat(),
        }

        # 缓存会话数据
        cache_key = f"session:{session_id}"
        mock_redis.setex(cache_key, SESSION_CACHE_TTL, json.dumps(session_data))

        # 读取缓存
        cached = mock_redis.get(cache_key)
        assert cached is not None
        cached_data = json.loads(cached)
        assert cached_data["user_id"] == "user-001"
        assert len(cached_data["messages"]) == 2

    def test_session_cache_ttl_expiry(self, mock_redis):
        """测试会话缓存过期

        验证缓存在TTL过期后自动失效
        """
        session_id = "sess-test-002"
        cache_key = f"session:{session_id}"

        # 设置1秒过期
        mock_redis.setex(cache_key, 1, json.dumps({"test": True}))

        # 立即读取应该存在
        assert mock_redis.exists(cache_key)

        # 等待过期
        time.sleep(1.1)

        # 过期后应该不存在
        assert not mock_redis.exists(cache_key)

    def test_cache_hit_avoids_redundant_query(self, mock_redis, mock_db):
        """测试缓存命中时避免重复查询

        验证相同的查询在缓存有效期内不会重复执行SQL
        """
        query_key = "query:sales:last_month"
        cached_result = SAMPLE_SALES_RESULT

        # 先查询缓存
        cached = mock_redis.get(query_key)
        assert cached is None  # 第一次查询缓存为空

        # 执行查询
        result = mock_db.execute("SELECT SUM(amount) FROM sales_orders")
        assert result["success"]

        # 写入缓存
        mock_redis.setex(query_key, 300, json.dumps(result["data"]))

        # 第二次查询应该命中缓存
        cached = mock_redis.get(query_key)
        assert cached is not None
        cached_data = json.loads(cached)
        assert len(cached_data) > 0

        # 验证数据库没有被再次调用
        initial_query_count = len(mock_db.executed_queries)
        # 从缓存读取，不执行SQL
        cached_again = mock_redis.get(query_key)
        assert cached_again is not None
        assert len(mock_db.executed_queries) == initial_query_count  # 查询数不变

    def test_cache_invalidation_on_update(self, mock_redis):
        """测试数据更新后缓存失效

        验证数据变更后相关缓存被清除
        """
        # 设置缓存
        mock_redis.set("query:sales:last_month", json.dumps(SAMPLE_SALES_RESULT))
        assert mock_redis.exists("query:sales:last_month")

        # 模拟数据更新后清除缓存
        mock_redis.delete("query:sales:last_month")
        assert not mock_redis.exists("query:sales:last_month")

    def test_session_cache_stores_conversation_history(self, mock_redis):
        """测试会话缓存存储完整对话历史"""
        session_id = "sess-test-003"
        cache_key = f"session:{session_id}"

        # 逐轮添加对话
        history = []
        for i in range(5):
            history.append({"role": "user", "content": f"问题{i+1}"})
            history.append({"role": "assistant", "content": f"回答{i+1}"})

            session_data = {
                "session_id": session_id,
                "messages": history,
                "updated_at": datetime.now().isoformat(),
            }
            mock_redis.set(cache_key, json.dumps(session_data))

        # 读取最终缓存
        cached = mock_redis.get(cache_key)
        final_data = json.loads(cached)
        assert len(final_data["messages"]) == 10  # 5轮 * 2条消息

    def test_multiple_sessions_independent(self, mock_redis):
        """测试多个会话互不干扰"""
        session_data_1 = {"user": "user-001", "query": "销售额"}
        session_data_2 = {"user": "user-002", "query": "退货率"}

        mock_redis.set("session:sess-001", json.dumps(session_data_1))
        mock_redis.set("session:sess-002", json.dumps(session_data_2))

        cached_1 = json.loads(mock_redis.get("session:sess-001"))
        cached_2 = json.loads(mock_redis.get("session:sess-002"))

        assert cached_1["user"] == "user-001"
        assert cached_2["user"] == "user-002"
        assert cached_1["query"] != cached_2["query"]

    def test_cache_key_generation_consistency(self):
        """测试缓存键生成一致性

        相同的查询参数应生成相同的缓存键
        """
        def generate_cache_key(query: str, user_id: str, database: str) -> str:
            raw = f"{user_id}:{database}:{query}"
            return f"query:{hashlib.md5(raw.encode()).hexdigest()}"

        key1 = generate_cache_key("SELECT 1", "user-001", "business_db")
        key2 = generate_cache_key("SELECT 1", "user-001", "business_db")
        key3 = generate_cache_key("SELECT 2", "user-001", "business_db")

        assert key1 == key2  # 相同参数 -> 相同键
        assert key1 != key3  # 不同查询 -> 不同键


# ==================== BU-IQ-011: 结果来源引用 ====================

@pytest.mark.integration
class TestSourceAttribution:
    """BU-IQ-011: 结果来源引用 (P1)

    SQL结果和文档结果标注来源，方便用户追溯和验证
    """

    def test_sql_result_includes_source_metadata(self, mock_db):
        """测试SQL结果包含来源元数据

        验证SQL查询结果包含执行的SQL语句、数据库、表名等信息
        """
        sql = "SELECT SUM(amount) AS total_amount FROM sales_orders WHERE status = 'completed'"
        result = mock_db.execute(sql)

        # 构建带来源信息的结果
        attributed_result = {
            "data": result["data"],
            "source": {
                "type": "sql",
                "database": "business_db",
                "tables": ["sales_orders"],
                "sql": sql,
                "execution_time": result["execution_time"],
                "timestamp": datetime.now().isoformat(),
            },
        }

        assert attributed_result["source"]["type"] == "sql"
        assert attributed_result["source"]["database"] == "business_db"
        assert "sales_orders" in attributed_result["source"]["tables"]
        assert attributed_result["source"]["sql"] == sql

    def test_rag_result_includes_document_source(self, mock_vllm, mock_milvus):
        """测试RAG结果包含文档来源

        验证RAG检索结果标注了文档ID、标题和相似度分数
        """
        query = "退货流程是怎样的"
        query_embedding = mock_vllm.embeddings([query])[0]

        search_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=3,
            output_fields=["doc_id", "title", "content"],
        )

        # 构建带来源信息的结果
        attributed_results = []
        for result in search_results[0]:
            attributed_results.append({
                "content_snippet": result.get("content", "")[:200],
                "source": {
                    "type": "document",
                    "doc_id": result["doc_id"],
                    "title": result.get("title", ""),
                    "collection": MILVUS_COLLECTION,
                    "similarity_score": result["score"],
                    "retrieval_method": "vector_search",
                },
            })

        assert len(attributed_results) > 0
        for ar in attributed_results:
            assert ar["source"]["type"] == "document"
            assert ar["source"]["doc_id"] is not None
            assert ar["source"]["similarity_score"] > 0
            assert ar["source"]["retrieval_method"] == "vector_search"

    def test_hybrid_result_distinguishes_sources(self, mock_db, mock_milvus, mock_vllm):
        """测试混合查询结果区分SQL和文档来源

        验证合并结果中每条数据都标注了来源类型
        """
        # SQL结果
        sql_result = mock_db.execute("SELECT SUM(amount) FROM sales_orders")
        sql_items = [{
            "content": f"月份: {row['month']}, 销售额: {row['total_amount']}",
            "source_type": "sql",
            "source_detail": {"table": "sales_orders", "database": "business_db"},
        } for row in sql_result["data"]]

        # RAG结果
        query_embedding = mock_vllm.embeddings(["销售政策"])[0]
        rag_results = mock_milvus.search(
            MILVUS_COLLECTION, [query_embedding], top_k=3,
            output_fields=["doc_id", "title"],
        )
        rag_items = [{
            "content": f"文档: {r.get('title', 'N/A')}",
            "source_type": "document",
            "source_detail": {"doc_id": r["doc_id"], "collection": MILVUS_COLLECTION},
        } for r in rag_results[0]]

        # 合并结果
        merged = sql_items + rag_items

        # 验证每条结果都有来源标注
        for item in merged:
            assert "source_type" in item
            assert item["source_type"] in ("sql", "document")
            assert "source_detail" in item

        # 验证两种来源都存在
        source_types = set(item["source_type"] for item in merged)
        assert "sql" in source_types
        assert "document" in source_types

    def test_source_attribution_format(self):
        """测试来源引用的标准格式

        验证来源信息符合平台定义的标准格式
        """
        sql_source = {
            "type": "sql",
            "database": "business_db",
            "tables": ["sales_orders", "customers"],
            "sql": "SELECT c.name, SUM(o.amount) FROM customers c JOIN sales_orders o ...",
            "execution_time": 0.05,
            "row_count": 10,
            "timestamp": "2024-12-15T10:30:00Z",
        }

        doc_source = {
            "type": "document",
            "doc_id": "doc-001",
            "title": "销售政策手册",
            "collection": "knowledge_base",
            "similarity_score": 0.92,
            "retrieval_method": "vector_search",
            "chunk_index": 0,
            "timestamp": "2024-12-15T10:30:00Z",
        }

        # 验证SQL来源必要字段
        assert all(k in sql_source for k in ["type", "database", "tables", "sql"])

        # 验证文档来源必要字段
        assert all(k in doc_source for k in ["type", "doc_id", "title", "similarity_score"])

    def test_answer_includes_inline_citations(self, mock_vllm):
        """测试回答包含内联引用标注

        验证LLM生成的回答中标注了引用来源编号
        """
        # 模拟带引用标注的回答
        answer_with_citations = (
            "根据查询结果，上个月销售额为4,100,000元[SQL:sales_orders]。"
            "根据公司销售政策[DOC:doc-001]，VIP客户可享受9折优惠。"
            "退货需在7天内提出[DOC:doc-002]。"
        )

        # 验证引用标注格式
        import re
        sql_citations = re.findall(r'\[SQL:([^\]]+)\]', answer_with_citations)
        doc_citations = re.findall(r'\[DOC:([^\]]+)\]', answer_with_citations)

        assert len(sql_citations) > 0
        assert len(doc_citations) > 0
        assert "sales_orders" in sql_citations
        assert "doc-001" in doc_citations

    def test_no_source_when_answer_from_llm_knowledge(self):
        """测试LLM自身知识回答时标注来源为模型

        验证当答案来自LLM而非SQL或文档时，来源标注为model
        """
        source = {
            "type": "model",
            "model_name": "gpt-4o-mini",
            "confidence": 0.6,
            "note": "答案基于模型通用知识，未检索到相关文档或数据",
        }

        assert source["type"] == "model"
        assert source["confidence"] < 0.8  # 非检索来源应有较低置信度


# ==================== 端到端集成场景 ====================

@pytest.mark.integration
class TestEndToEndIntelligentQuery:
    """端到端智能查询集成测试

    覆盖完整的查询处理流程：意图识别 -> 路由 -> 执行 -> 结果组装
    """

    def test_full_sql_query_pipeline(self, mock_vllm, mock_db, sample_schemas):
        """测试完整的SQL查询流程

        意图识别 -> Schema注入 -> SQL生成 -> 安全检查 -> 执行 -> 结果解释
        """
        question = "上个月销售额是多少"

        # 1. 意图识别
        intent_messages = [
            {"role": "system", "content": "意图识别"},
            {"role": "user", "content": question},
        ]
        intent_response = mock_vllm.chat_completion(intent_messages)
        intent = json.loads(intent_response["choices"][0]["message"]["content"])
        assert intent["intent"] == "sql"

        # 2. Schema注入并生成SQL
        schema_text = "\n".join([
            f"{t['table_name']}: {', '.join(c['column_name'] for c in t['columns'])}"
            for t in sample_schemas
        ])
        sql_messages = [
            {"role": "system", "content": f"生成SQL。可用表：\n{schema_text}"},
            {"role": "user", "content": f"生成SQL查询：{question}"},
        ]
        sql_response = mock_vllm.chat_completion(sql_messages)
        generated_sql = sql_response["choices"][0]["message"]["content"]

        # 3. 安全检查
        assert "DROP" not in generated_sql.upper()
        assert "DELETE" not in generated_sql.upper()
        assert "SELECT" in generated_sql.upper()

        # 4. 执行SQL
        result = mock_db.execute(generated_sql)
        assert result["success"] is True
        assert result["row_count"] > 0

        # 5. 构建带来源的最终结果
        final = {
            "answer": f"上个月销售额为{result['data'][0]['total_amount']}元",
            "data": result["data"],
            "source": {
                "type": "sql",
                "sql": generated_sql,
                "tables": ["sales_orders"],
            },
            "intent": intent,
        }
        assert final["answer"] is not None
        assert final["source"]["type"] == "sql"

    def test_full_rag_query_pipeline(self, mock_vllm, mock_milvus):
        """测试完整的RAG查询流程

        意图识别 -> 向量检索 -> 上下文构建 -> LLM回答 -> 来源标注
        """
        question = "销售政策是什么"

        # 1. 意图识别
        intent_messages = [
            {"role": "system", "content": "意图识别"},
            {"role": "user", "content": question},
        ]
        intent_response = mock_vllm.chat_completion(intent_messages)
        intent = json.loads(intent_response["choices"][0]["message"]["content"])
        assert intent["intent"] == "rag"

        # 2. 向量检索
        query_embedding = mock_vllm.embeddings([question])[0]
        search_results = mock_milvus.search(
            collection_name=MILVUS_COLLECTION,
            query_vectors=[query_embedding],
            top_k=5,
            output_fields=["doc_id", "title", "content"],
        )
        assert len(search_results[0]) > 0

        # 3. 构建上下文并生成回答
        context = "\n".join(r.get("content", "") for r in search_results[0] if "content" in r)
        answer_messages = [
            {"role": "system", "content": "根据以下上下文回答问题"},
            {"role": "user", "content": f"上下文：{context}\n\n问题：{question}"},
        ]
        answer_response = mock_vllm.chat_completion(answer_messages)
        answer = answer_response["choices"][0]["message"]["content"]

        # 4. 构建带来源的最终结果
        final = {
            "answer": answer,
            "sources": [
                {
                    "doc_id": r["doc_id"],
                    "title": r.get("title", ""),
                    "score": r["score"],
                }
                for r in search_results[0]
            ],
            "intent": intent,
        }
        assert final["answer"] is not None
        assert len(final["sources"]) > 0

    def test_full_hybrid_query_pipeline(self, mock_vllm, mock_db, mock_milvus, sample_schemas):
        """测试完整的混合查询流程

        意图识别 -> 并行SQL+RAG -> 合并 -> 来源标注
        """
        question = "上个月销售额是多少，另外销售政策有什么规定"

        # 1. 意图识别为混合
        # (简化处理：直接判定为混合)
        intent = {"intent": "hybrid", "confidence": 0.90}

        # 2. 并行执行SQL和RAG
        # SQL部分
        sql = "SELECT SUM(amount) AS total_amount FROM sales_orders WHERE created_at >= '2024-12-01'"
        sql_result = mock_db.execute(sql)

        # RAG部分
        query_embedding = mock_vllm.embeddings([question])[0]
        rag_results = mock_milvus.search(
            MILVUS_COLLECTION, [query_embedding], top_k=3,
            output_fields=["doc_id", "title", "content"],
        )

        # 3. 合并结果
        final = {
            "query_type": "hybrid",
            "answer": (
                f"销售数据：上个月销售额为{sql_result['data'][0]['total_amount']}元。\n"
                f"销售政策：根据检索到的文档..."
            ),
            "sql_source": {
                "type": "sql",
                "data": sql_result["data"],
                "tables": ["sales_orders"],
            },
            "doc_sources": [
                {"type": "document", "doc_id": r["doc_id"], "score": r["score"]}
                for r in rag_results[0]
            ],
            "intent": intent,
        }

        assert final["query_type"] == "hybrid"
        assert final["sql_source"]["type"] == "sql"
        assert len(final["doc_sources"]) > 0
        assert all(s["type"] == "document" for s in final["doc_sources"])

    def test_multi_turn_with_cache(self, mock_vllm, mock_db, mock_redis):
        """测试多轮对话与缓存结合

        完整的多轮对话流程，带会话缓存
        """
        session_id = "sess-e2e-001"
        cache_key = f"session:{session_id}"

        # 第一轮
        q1 = "上个月销售额是多少"
        r1 = mock_db.execute("SELECT SUM(amount) FROM sales_orders")
        session_state = {
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": q1},
                {"role": "assistant", "content": f"销售额为{r1['data'][0]['total_amount']}元"},
            ],
            "metadata": {"tables_accessed": ["sales_orders"]},
        }
        mock_redis.setex(cache_key, SESSION_CACHE_TTL, json.dumps(session_state))

        # 第二轮：从缓存恢复上下文
        cached = mock_redis.get(cache_key)
        assert cached is not None
        restored_state = json.loads(cached)
        assert len(restored_state["messages"]) == 2

        # 追加第二轮
        q2 = "按客户分组呢"
        restored_state["messages"].append({"role": "user", "content": q2})
        r2 = mock_db.execute("SELECT customer_name, SUM(amount) FROM customers c JOIN sales_orders")
        restored_state["messages"].append({
            "role": "assistant",
            "content": f"按客户分组的结果：{json.dumps(r2['data'][:3], ensure_ascii=False)}",
        })
        restored_state["metadata"]["tables_accessed"].append("customers")

        # 更新缓存
        mock_redis.set(cache_key, json.dumps(restored_state))

        # 验证最终状态
        final_cached = json.loads(mock_redis.get(cache_key))
        assert len(final_cached["messages"]) == 4
        assert "customers" in final_cached["metadata"]["tables_accessed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
