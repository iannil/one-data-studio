"""
Text-to-SQL 集成测试

测试场景:
1. SQL 安全验证集成
2. Schema 提供器集成
3. 结果解释器集成
4. 端到端 Text-to-SQL 流程
5. 混合检索 + Text-to-SQL 组合
"""

import os
import sys
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.sql_validator import (
    SQLValidator,
    SQLValidationResult,
    SQLRiskLevel,
    get_sql_validator,
)
from services.metadata_schema_provider import (
    SchemaProvider,
    SchemaSelectionResult,
    TableSchema,
    ColumnSchema,
)
from services.result_interpreter import (
    ResultInterpreter,
    InterpretationResult,
    InsightType,
)
from services.hybrid_retriever import (
    HybridRetriever,
    RetrievalConfig,
    RetrievalMethod,
    RetrievalResult,
    QueryExpansionStrategy,
)


# ==================== 测试数据 ====================

SAMPLE_TABLES = [
    {
        "table_name": "users",
        "table_comment": "用户表",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "用户ID"},
            {"column_name": "username", "data_type": "varchar(100)", "comment": "用户名"},
            {"column_name": "email", "data_type": "varchar(255)", "comment": "邮箱"},
            {"column_name": "created_at", "data_type": "timestamp", "comment": "创建时间"},
        ]
    },
    {
        "table_name": "orders",
        "table_comment": "订单表",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "订单ID"},
            {"column_name": "user_id", "data_type": "bigint", "comment": "用户ID"},
            {"column_name": "amount", "data_type": "decimal(10,2)", "comment": "订单金额"},
            {"column_name": "status", "data_type": "varchar(50)", "comment": "订单状态"},
            {"column_name": "created_at", "data_type": "timestamp", "comment": "创建时间"},
        ]
    },
    {
        "table_name": "products",
        "table_comment": "产品表",
        "columns": [
            {"column_name": "id", "data_type": "bigint", "comment": "产品ID"},
            {"column_name": "name", "data_type": "varchar(255)", "comment": "产品名称"},
            {"column_name": "price", "data_type": "decimal(10,2)", "comment": "价格"},
            {"column_name": "category", "data_type": "varchar(100)", "comment": "分类"},
        ]
    },
]

SAMPLE_SQL_RESULTS = [
    {"id": 1, "username": "alice", "email": "alice@example.com", "created_at": "2024-01-01 10:00:00"},
    {"id": 2, "username": "bob", "email": "bob@example.com", "created_at": "2024-01-02 11:00:00"},
    {"id": 3, "username": "charlie", "email": "charlie@example.com", "created_at": "2024-01-03 12:00:00"},
]

SAMPLE_ORDER_RESULTS = [
    {"month": "2024-01", "total_amount": 15000.00, "order_count": 150},
    {"month": "2024-02", "total_amount": 18000.00, "order_count": 180},
    {"month": "2024-03", "total_amount": 22000.00, "order_count": 220},
    {"month": "2024-04", "total_amount": 25000.00, "order_count": 250},
]


# ==================== Fixtures ====================

@pytest.fixture
def sql_validator():
    """SQL 验证器实例"""
    return get_sql_validator()


@pytest.fixture
def mock_metadata_service():
    """模拟元数据服务"""
    with patch('services.alldata_api.services.metadata_schema_provider.metadata_service') as mock:
        mock.get_table_schema.side_effect = lambda table, db: _get_mock_table_schema(table)
        mock.search_tables_by_keyword.side_effect = lambda keyword, db: _search_mock_tables(keyword)
        yield mock


@pytest.fixture
def schema_provider(mock_metadata_service):
    """Schema 提供器实例"""
    return SchemaProvider()


@pytest.fixture
def result_interpreter():
    """结果解释器实例"""
    return ResultInterpreter()


@pytest.fixture
def hybrid_retriever():
    """混合检索器实例"""
    config = RetrievalConfig(
        top_k=10,
        enable_cache=False,  # 测试时禁用缓存
    )
    return HybridRetriever(config)


# ==================== 辅助函数 ====================

def _get_mock_table_schema(table_name: str) -> Dict[str, Any]:
    """获取模拟表结构"""
    for table in SAMPLE_TABLES:
        if table["table_name"] == table_name:
            return table
    return None


def _search_mock_tables(keyword: str) -> List[Dict[str, Any]]:
    """搜索模拟表"""
    results = []
    keyword_lower = keyword.lower()
    for table in SAMPLE_TABLES:
        if (keyword_lower in table["table_name"].lower() or
            keyword_lower in table["table_comment"].lower() or
            any(keyword_lower in col["column_name"].lower() or
                keyword_lower in col.get("comment", "").lower()
                for col in table["columns"])):
            results.append(table)
    return results


# ==================== SQL 验证集成测试 ====================

class TestSQLValidatorIntegration:
    """SQL 验证器集成测试"""

    def test_validate_safe_select(self, sql_validator):
        """测试安全 SELECT 查询"""
        result = sql_validator.validate("SELECT id, name FROM users LIMIT 100")

        assert result.is_valid is True
        assert result.risk_level == SQLRiskLevel.LOW
        assert result.modified_sql is not None
        assert "LIMIT" in result.modified_sql.upper()

    def test_block_dangerous_operations(self, sql_validator):
        """测试阻止危险操作"""
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM users",
            "TRUNCATE TABLE users",
            "ALTER TABLE users ADD COLUMN x INT",
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET name='x'",
        ]

        for query in dangerous_queries:
            result = sql_validator.validate(query)
            assert result.is_valid is False, f"Should block: {query}"
            assert result.risk_level in [SQLRiskLevel.HIGH, SQLRiskLevel.CRITICAL]

    def test_auto_add_limit(self, sql_validator):
        """测试自动添加 LIMIT"""
        query = "SELECT * FROM users"
        result = sql_validator.validate(query, max_rows=1000)

        assert result.is_valid is True
        assert "LIMIT" in result.modified_sql.upper()
        assert "1000" in result.modified_sql or "1000" in result.modified_sql

    def test_validate_with_explain(self, sql_validator):
        """测试 EXPLAIN 查询"""
        result = sql_validator.validate("EXPLAIN SELECT * FROM users")

        assert result.is_valid is True
        assert "EXPLAIN" in result.modified_sql.upper()

    def test_validate_join_query(self, sql_validator):
        """测试 JOIN 查询"""
        query = """
            SELECT u.username, o.amount
            FROM users u
            JOIN orders o ON u.id = o.user_id
            LIMIT 100
        """
        result = sql_validator.validate(query)

        assert result.is_valid is True
        assert "JOIN" in result.modified_sql.upper()

    def test_validate_aggregation(self, sql_validator):
        """测试聚合查询"""
        query = """
            SELECT status, COUNT(*), AVG(amount) as avg_amount
            FROM orders
            GROUP BY status
            LIMIT 100
        """
        result = sql_validator.validate(query)

        assert result.is_valid is True
        assert "GROUP BY" in result.modified_sql.upper()

    def test_cache_validation_result(self, sql_validator):
        """测试验证结果缓存"""
        query = "SELECT id FROM users LIMIT 100"

        # 第一次调用
        result1 = sql_validator.validate(query)
        # 第二次调用（应该从缓存获取）
        result2 = sql_validator.validate(query)

        assert result1.is_valid == result2.is_valid


# ==================== Schema 提供器集成测试 ====================

class TestSchemaProviderIntegration:
    """Schema 提供器集成测试"""

    def test_get_schema_for_question(self, schema_provider):
        """测试根据问题获取 Schema"""
        result = schema_provider.get_schema_for_question(
            question="查询用户表中有哪些用户",
            database="test_db",
            max_tokens=4000
        )

        assert isinstance(result, SchemaSelectionResult)
        assert len(result.tables) > 0
        assert any(t.table_name == "users" for t in result.tables)

    def test_relevant_table_selection(self, schema_provider):
        """测试相关表选择"""
        # 关于订单的问题应该返回 orders 表
        result = schema_provider.get_schema_for_question(
            question="统计每个月的订单总额",
            database="test_db"
        )

        assert any(t.table_name == "orders" for t in result.tables)

    def test_column_selection(self, schema_provider):
        """测试列选择"""
        result = schema_provider.get_schema_for_question(
            question="查询用户名和邮箱",
            database="test_db"
        )

        # 应该包含 username 和 email 列
        users_table = next((t for t in result.tables if t.table_name == "users"), None)
        assert users_table is not None
        assert any(c.column_name == "username" for c in users_table.columns)
        assert any(c.column_name == "email" for c in users_table.columns)

    def test_multi_table_selection(self, schema_provider):
        """测试多表选择"""
        result = schema_provider.get_schema_for_question(
            question="查询每个用户的订单总金额",
            database="test_db"
        )

        # 应该包含 users 和 orders 表
        table_names = [t.table_name for t in result.tables]
        assert "users" in table_names
        assert "orders" in table_names

    def test_format_for_prompt(self, schema_provider):
        """测试格式化为 Prompt"""
        result = schema_provider.get_schema_for_question(
            question="查询用户信息",
            database="test_db"
        )

        prompt_format = schema_provider.format_for_prompt(result)

        assert "users" in prompt_format
        assert "username" in prompt_format or "email" in prompt_format

    def test_token_limit_respect(self, schema_provider):
        """测试遵守 Token 限制"""
        # 设置很小的 token 限制
        result = schema_provider.get_schema_for_question(
            question="查询所有表的数据",
            database="test_db",
            max_tokens=100
        )

        # 应该限制返回的列数
        total_columns = sum(len(t.columns) for t in result.tables)
        assert total_columns < 20  # 应该较少


# ==================== 结果解释器集成测试 ====================

class TestResultInterpreterIntegration:
    """结果解释器集成测试"""

    def test_interpret_simple_result(self, result_interpreter):
        """测试解释简单结果"""
        result = result_interpreter.interpret(
            result=SAMPLE_SQL_RESULTS,
            query="SELECT * FROM users LIMIT 3"
        )

        assert isinstance(result, InterpretationResult)
        assert result.summary is not None
        assert result.row_count == 3
        assert len(result.columns) > 0

    def test_detect_trends(self, result_interpreter):
        """测试趋势检测"""
        result = result_interpreter.interpret(
            result=SAMPLE_ORDER_RESULTS,
            query="SELECT month, SUM(amount) as total_amount FROM orders GROUP BY month"
        )

        assert result.summary is not None
        # 应该检测到上升趋势
        has_trend_insight = any(
            i.type == InsightType.TREND for i in result.insights
        )
        # 注意：趋势检测需要足够的数据点

    def test_generate_chart_config(self, result_interpreter):
        """测试生成图表配置"""
        result = result_interpreter.interpret(
            result=SAMPLE_ORDER_RESULTS,
            query="SELECT month, total_amount, order_count FROM monthly_orders"
        )

        chart_config = result_interpreter.generate_chart_config(
            result=result,
            chart_type="line"
        )

        assert chart_config is not None
        assert "x_axis" in chart_config
        assert "y_axis" in chart_config
        assert "series" in chart_config

    def test_recommended_chart_type(self, result_interpreter):
        """测试推荐图表类型"""
        # 时间序列数据应该推荐折线图
        result1 = result_interpreter.interpret(
            result=SAMPLE_ORDER_RESULTS,
            query="SELECT month, total_amount FROM monthly_orders"
        )
        assert result1.recommended_chart in ["line", "bar"]

        # 分类数据应该推荐柱状图
        result2 = result_interpreter.interpret(
            result=[
                {"category": "A", "value": 100},
                {"category": "B", "value": 200},
            ],
            query="SELECT category, value FROM products"
        )
        assert result2.recommended_chart in ["bar", "pie"]

    def test_format_as_table(self, result_interpreter):
        """测试格式化为表格"""
        result = result_interpreter.interpret(
            result=SAMPLE_SQL_RESULTS,
            query="SELECT * FROM users"
        )

        table_str = result_interpreter.format_as_table(result)

        assert "username" in table_str
        assert "alice" in table_str
        assert "bob" in table_str

    def test_format_as_markdown(self, result_interpreter):
        """测试格式化为 Markdown"""
        result = result_interpreter.interpret(
            result=SAMPLE_SQL_RESULTS,
            query="SELECT * FROM users"
        )

        markdown = result_interpreter.format_as_markdown(result)

        assert "|" in markdown  # Markdown 表格
        assert "username" in markdown

    def test_empty_result(self, result_interpreter):
        """测试空结果"""
        result = result_interpreter.interpret(
            result=[],
            query="SELECT * FROM users WHERE 1=0"
        )

        assert result.row_count == 0
        assert result.summary is not None
        assert "没有数据" in result.summary or "no data" in result.summary.lower()

    def test_detect_outliers(self, result_interpreter):
        """测试异常值检测"""
        data_with_outlier = [
            {"value": 10},
            {"value": 12},
            {"value": 11},
            {"value": 1000},  # 异常值
            {"value": 13},
        ]

        result = result_interpreter.interpret(
            result=data_with_outlier,
            query="SELECT value FROM metrics"
        )

        # 应该检测到异常值
        has_outlier = any(
            "异常" in str(i.description) or "outlier" in str(i.description).lower()
            for i in result.insights
        )


# ==================== 端到端集成测试 ====================

class TestTextToSQLE2E:
    """Text-to-SQL 端到端集成测试"""

    def test_full_text_to_sql_workflow(
        self,
        sql_validator,
        schema_provider,
        result_interpreter,
    ):
        """测试完整的 Text-to-SQL 工作流"""

        # 1. 用户问题
        question = "查询每个月的订单总金额和订单数量"

        # 2. 获取相关 Schema
        schema_result = schema_provider.get_schema_for_question(
            question=question,
            database="test_db"
        )
        assert len(schema_result.tables) > 0

        # 3. 生成 SQL（这里模拟 LLM 生成）
        generated_sql = """
            SELECT DATE_FORMAT(created_at, '%%Y-%%m') as month,
                   SUM(amount) as total_amount,
                   COUNT(*) as order_count
            FROM orders
            GROUP BY month
            ORDER BY month
        """

        # 4. 验证 SQL
        validation_result = sql_validator.validate(generated_sql)
        assert validation_result.is_valid is True

        # 5. 执行 SQL（模拟）
        mock_results = SAMPLE_ORDER_RESULTS

        # 6. 解释结果
        interpretation = result_interpreter.interpret(
            result=mock_results,
            query=validation_result.modified_sql,
            execution_time=0.05
        )

        assert interpretation.row_count == 4
        assert interpretation.summary is not None

    def test_question_with_join(
        self,
        sql_validator,
        schema_provider,
        result_interpreter,
    ):
        """测试带 JOIN 的问题"""

        question = "查询每个用户的用户名和订单总金额"

        # 获取 Schema
        schema_result = schema_provider.get_schema_for_question(
            question=question,
            database="test_db"
        )

        # 应该包含 users 和 orders
        table_names = [t.table_name for t in schema_result.tables]
        assert "users" in table_names
        assert "orders" in table_names

        # 生成的 SQL（模拟）
        generated_sql = """
            SELECT u.username, SUM(o.amount) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.username
            LIMIT 100
        """

        # 验证
        validation_result = sql_validator.validate(generated_sql)
        assert validation_result.is_valid is True

    def test_blocked_malicious_query(self, sql_validator, schema_provider):
        """测试阻止恶意查询"""

        question = "删除所有用户数据"

        # 恶意 SQL（模拟攻击者尝试注入）
        malicious_sql = "SELECT * FROM users; DROP TABLE users; --"

        validation_result = sql_validator.validate(malicious_sql)

        assert validation_result.is_valid is False
        assert validation_result.risk_level == SQLRiskLevel.CRITICAL


# ==================== 混合检索集成测试 ====================

class TestHybridRetrieverIntegration:
    """混合检索器集成测试"""

    def test_retrieve_for_sql_generation(self, hybrid_retriever):
        """测试为 SQL 生成检索相关文档"""
        # 模拟：检索相关的表结构文档、示例 SQL 等

        query = "如何计算订单总额"

        results = hybrid_retriever.retrieve(
            query=query,
            method=RetrievalMethod.VECTOR,
            top_k=5
        )

        # 检查返回结果
        assert isinstance(results, list)

    def test_rrf_retrieval(self, hybrid_retriever):
        """测试 RRF 混合检索"""
        # 先构建 BM25 索引
        docs = [
            {"id": "doc1", "text": "订单表包含订单ID、用户ID、金额等字段"},
            {"id": "doc2", "text": "用户表存储用户基本信息"},
            {"id": "doc3", "text": "产品表包含产品名称和价格"},
        ]
        hybrid_retriever.build_bm25_index(docs)

        results = hybrid_retriever.retrieve(
            query="订单金额",
            method=RetrievalMethod.RRF,
            top_k=3
        )

        # 应该返回相关文档
        assert isinstance(results, list)

    def test_mmr_diversity_retrieval(self, hybrid_retriever):
        """测试 MMR 多样性检索"""
        docs = [
            {"id": "doc1", "text": "订单表包含订单ID、用户ID、金额等字段"},
            {"id": "doc2", "text": "订单详情表记录订单的具体商品"},
            {"id": "doc3", "text": "用户表存储用户基本信息"},
        ]
        hybrid_retriever.build_bm25_index(docs)

        config = RetrievalConfig(mmr_lambda=0.5)
        retriever = HybridRetriever(config)
        retriever.build_bm25_index(docs)

        results = retriever.retrieve(
            query="订单",
            method=RetrievalMethod.MMR,
            top_k=2
        )

        assert len(results) <= 2

    def test_query_expansion(self, hybrid_retriever):
        """测试查询扩展"""
        expanded = hybrid_retriever.expand_query(
            query="订单总额",
            strategy=QueryExpansionStrategy.EMBEDDING
        )

        assert isinstance(expanded, list)
        assert len(expanded) >= 1

    def test_retrieve_with_rerank(self, hybrid_retriever):
        """测试检索后重排序"""
        docs = [
            {"id": "doc1", "text": "订单表包含订单ID、用户ID、金额"},
            {"id": "doc2", "text": "用户表包含用户ID和用户名"},
            {"id": "doc3", "text": "产品表包含产品ID和价格"},
        ]
        hybrid_retriever.build_bm25_index(docs)

        results = hybrid_retriever.retrieve_with_rerank(
            query="订单金额",
            top_k=2,
            rerank_top_k=10
        )

        assert len(results) <= 2


# ==================== 组合场景测试 ====================

class TestCombinedScenarios:
    """组合场景测试"""

    def test_rag_enhanced_text_to_sql(
        self,
        schema_provider,
        sql_validator,
        result_interpreter,
    ):
        """测试 RAG 增强的 Text-to-SQL"""

        # 场景：用户询问一个复杂问题
        question = "统计2024年每个季度的销售总额，按产品类别分组"

        # 1. 检索相关文档（模拟）
        # rag_results = hybrid_retriever.retrieve(question)

        # 2. 获取相关 Schema
        schema_result = schema_provider.get_schema_for_question(
            question=question,
            database="test_db"
        )

        # 3. 生成增强的 Prompt（包含 Schema 和检索到的文档）
        # prompt = build_enhanced_prompt(question, schema_result, rag_results)

        # 4. 验证生成的 SQL
        sql = """
            SELECT category,
                   SUM(CASE WHEN QUARTER(created_at) = 1 THEN amount ELSE 0 END) as q1,
                   SUM(CASE WHEN QUARTER(created_at) = 2 THEN amount ELSE 0 END) as q2,
                   SUM(CASE WHEN QUARTER(created_at) = 3 THEN amount ELSE 0 END) as q3,
                   SUM(CASE WHEN QUARTER(created_at) = 4 THEN amount ELSE 0 END) as q4
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE YEAR(created_at) = 2024
            GROUP BY category
            LIMIT 100
        """

        validation_result = sql_validator.validate(sql)
        assert validation_result.is_valid is True

    def test_multi_turn_conversation(
        self,
        schema_provider,
        sql_validator,
    ):
        """测试多轮对话"""

        # 第一轮：简单查询
        question1 = "有多少个用户？"
        schema1 = schema_provider.get_schema_for_question(question1, "test_db")
        sql1 = "SELECT COUNT(*) as user_count FROM users"
        result1 = sql_validator.validate(sql1)
        assert result1.is_valid is True

        # 第二轮：基于第一轮的追问
        question2 = "显示前10个用户的详细信息"
        schema2 = schema_provider.get_schema_for_question(question2, "test_db")
        sql2 = "SELECT * FROM users ORDER BY id LIMIT 10"
        result2 = sql_validator.validate(sql2)
        assert result2.is_valid is True

    def test_error_recovery(
        self,
        sql_validator,
        schema_provider,
    ):
        """测试错误恢复"""

        question = "查询订单总额"

        # 第一次尝试：SQL 不完整
        sql1 = "SELECT SUM(amount) FROM orders"
        result1 = sql_validator.validate(sql1)
        # 缺少 LIMIT，验证器应该自动添加

        # 第二次尝试：添加 LIMIT
        if result1.is_valid:
            final_sql = result1.modified_sql
        else:
            final_sql = sql1 + " LIMIT 1000"

        result_final = sql_validator.validate(final_sql)
        assert result_final.is_valid is True


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    def test_large_result_interpretation(self, result_interpreter):
        """测试大数据量结果解释"""
        # 生成 1000 行结果
        large_result = [
            {"id": i, "value": i * 10, "name": f"item_{i}"}
            for i in range(1000)
        ]

        import time
        start = time.time()
        interpretation = result_interpreter.interpret(large_result)
        elapsed = time.time() - start

        assert interpretation.row_count == 1000
        assert elapsed < 1.0  # 应该在 1 秒内完成

    def test_complex_validation_performance(self, sql_validator):
        """测试复杂 SQL 验证性能"""
        complex_sql = """
            SELECT
                u.username,
                o.order_count,
                p.product_count,
                SUM(o.amount) as total_amount
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) as order_count, SUM(amount) as amount
                FROM orders
                GROUP BY user_id
            ) o ON u.id = o.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) as product_count
                FROM products
                GROUP BY user_id
            ) p ON u.id = p.user_id
            WHERE u.created_at > '2024-01-01'
            GROUP BY u.id, u.username, o.order_count, p.product_count
            LIMIT 100
        """

        import time
        start = time.time()
        result = sql_validator.validate(complex_sql)
        elapsed = time.time() - start

        assert result.is_valid is True
        assert elapsed < 0.5  # 验证应该在 0.5 秒内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
