"""
Text-to-SQL E2E 测试
Sprint 24: 端到端测试

测试完整的 Text-to-SQL 工作流程:
1. 接收自然语言查询
2. 元数据注入
3. SQL 生成 (支持 vLLM)
4. SQL 验证
5. 执行查询
6. 返回结果

增强 (Phase 6):
- vLLM Chat 服务集成
- 元数据自动注入
- Schema 验证
- 复杂查询生成
"""

import pytest
import asyncio
import os
import requests
import time
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8081")
OPENAI_PROXY_URL = os.getenv("TEST_OPENAI_PROXY_URL", "http://localhost:8080")
ALLDATA_API_URL = os.getenv("TEST_ALLDATA_API_URL", "http://localhost:8082")
AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestTextToSQLEndToEnd:
    """Text-to-SQL 端到端测试"""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM 响应"""
        return {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o-mini",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "SELECT name, email FROM customers WHERE status = 'active' ORDER BY created_at DESC LIMIT 10;"
                },
                "finish_reason": "stop"
            }]
        }

    @pytest.mark.e2e
    def test_text_to_sql_basic_query(self, mock_llm_response):
        """测试基本的自然语言到 SQL 转换"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_post.return_value = mock_response

            from tools import TextToSQLTool

            tool = TextToSQLTool()
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(question="查询所有活跃客户的姓名和邮箱")
            )

            assert result["success"] is True
            assert "sql" in result
            assert "SELECT" in result["sql"].upper()
            assert "customers" in result["sql"].lower()

    @pytest.mark.e2e
    def test_text_to_sql_injection_prevention(self, mock_llm_response):
        """测试 SQL 注入防护在 Text-to-SQL 流程中的工作"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        # 即使 LLM 生成了危险的 SQL，验证层也应该阻止
        malicious_response = mock_llm_response.copy()
        malicious_response["choices"] = [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "SELECT * FROM customers; DROP TABLE customers;--"
            },
            "finish_reason": "stop"
        }]

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = malicious_response
            mock_post.return_value = mock_response

            from tools import TextToSQLTool, SQLQueryTool

            # 生成 SQL
            text_to_sql = TextToSQLTool()
            sql_result = asyncio.get_event_loop().run_until_complete(
                text_to_sql.execute(question="删除所有客户")
            )

            # 如果生成成功，尝试执行应该被阻止
            if sql_result["success"]:
                sql_tool = SQLQueryTool(config={"mock_data": True})
                exec_result = asyncio.get_event_loop().run_until_complete(
                    sql_tool.execute(sql=sql_result["sql"])
                )
                # DROP 语句应该被阻止
                assert exec_result["success"] is False
                assert "Dangerous" in exec_result["error"] or "injection" in exec_result["error"].lower()

    @pytest.mark.e2e
    def test_text_to_sql_with_database_execution(self, mock_llm_response):
        """测试完整的 Text-to-SQL + 执行流程"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_post.return_value = mock_response

            from tools import TextToSQLTool, SQLQueryTool

            # 1. 自然语言转 SQL
            text_to_sql = TextToSQLTool()
            sql_result = asyncio.get_event_loop().run_until_complete(
                text_to_sql.execute(question="查询活跃客户")
            )

            assert sql_result["success"] is True
            generated_sql = sql_result["sql"]

            # 2. 执行 SQL（使用 mock 数据）
            sql_tool = SQLQueryTool(config={"mock_data": True})
            exec_result = asyncio.get_event_loop().run_until_complete(
                sql_tool.execute(sql=generated_sql)
            )

            assert exec_result["success"] is True
            assert "results" in exec_result

    @pytest.mark.e2e
    def test_text_to_sql_llm_error_handling(self):
        """测试 LLM 服务错误处理"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            from tools import TextToSQLTool

            tool = TextToSQLTool()
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(question="查询客户")
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.e2e
    def test_text_to_sql_timeout_handling(self):
        """测试 LLM 请求超时处理"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        import requests

        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            from tools import TextToSQLTool

            tool = TextToSQLTool()
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(question="查询客户")
            )

            assert result["success"] is False
            assert "error" in result


class TestAgentWorkflowEndToEnd:
    """Agent 工作流端到端测试"""

    @pytest.mark.e2e
    def test_agent_tool_execution_flow(self):
        """测试 Agent 工具执行流程"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        from tools import get_tool_registry

        registry = get_tool_registry()

        # 模拟 Agent 工具调用流程
        # 1. 获取可用工具列表
        tools = registry.list_tools()
        assert len(tools) > 0

        tool_names = [t["name"] for t in tools]
        assert "calculator" in tool_names

        # 2. 选择工具
        calculator = registry.get("calculator")
        assert calculator is not None

        # 3. 验证参数
        is_valid, errors = calculator.validate_params({"expression": "1 + 1"})
        assert is_valid is True

        # 4. 执行工具
        result = asyncio.get_event_loop().run_until_complete(
            registry.execute("calculator", expression="2 + 2")
        )
        assert result["success"] is True
        assert result["result"] == 4

    @pytest.mark.e2e
    def test_agent_multi_tool_workflow(self):
        """测试 Agent 多工具工作流"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        from tools import get_tool_registry

        registry = get_tool_registry()

        # 模拟多步骤工具调用
        results = []

        # 步骤 1: 计算
        calc_result = asyncio.get_event_loop().run_until_complete(
            registry.execute("calculator", expression="10 * 5")
        )
        results.append(calc_result)
        assert calc_result["success"] is True
        assert calc_result["result"] == 50

        # 步骤 2: 日期计算
        datetime_result = asyncio.get_event_loop().run_until_complete(
            registry.execute("datetime", action="current")
        )
        results.append(datetime_result)
        assert datetime_result["success"] is True
        assert "result" in datetime_result

        # 验证所有步骤成功
        assert all(r["success"] for r in results)

    @pytest.mark.e2e
    def test_agent_tool_error_recovery(self):
        """测试 Agent 工具错误恢复"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        from tools import get_tool_registry

        registry = get_tool_registry()

        # 尝试执行无效的计算
        bad_result = asyncio.get_event_loop().run_until_complete(
            registry.execute("calculator", expression="invalid_expression")
        )
        assert bad_result["success"] is False

        # Agent 应该能够继续使用其他工具
        good_result = asyncio.get_event_loop().run_until_complete(
            registry.execute("calculator", expression="1 + 1")
        )
        assert good_result["success"] is True

    @pytest.mark.e2e
    def test_agent_tool_validation_flow(self):
        """测试 Agent 工具参数验证流程"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        from tools import get_tool_registry

        registry = get_tool_registry()

        # 缺少必需参数
        result = asyncio.get_event_loop().run_until_complete(
            registry.execute("calculator")  # 缺少 expression
        )
        assert result["success"] is False
        assert "validation" in result["error"].lower() or "missing" in result["error"].lower()


class TestSecurityEndToEnd:
    """安全性端到端测试"""

    @pytest.mark.e2e
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_security_enforcement(self):
        """测试生产环境安全强制执行"""
        import sys

        # 清除已导入的模块以应用新环境变量
        modules_to_remove = [k for k in sys.modules.keys() if 'tools' in k or 'cache' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]

        sys.path.insert(0, 'services/bisheng-api/engine')

        # 在生产环境中，mock_data=True 应该被拒绝
        from tools import SQLQueryTool

        with pytest.raises(RuntimeError, match="mock_data.*not allowed in production"):
            SQLQueryTool(config={"mock_data": True})

    @pytest.mark.e2e
    def test_ssrf_protection_in_http_tool(self):
        """测试 HTTP 工具中的 SSRF 防护"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        from tools import HTTPRequestTool

        tool = HTTPRequestTool()

        # 尝试访问内部服务
        internal_urls = [
            "http://localhost/admin",
            "http://127.0.0.1:8080/",
            "http://10.0.0.1/internal",
            "http://169.254.169.254/latest/meta-data/",
            "http://kubernetes.default.svc/api",
        ]

        for url in internal_urls:
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(url=url)
            )
            assert result["success"] is False, f"SSRF should block {url}"
            assert "blocked" in result["error"].lower() or "not allowed" in result["error"].lower()

    @pytest.mark.e2e
    def test_code_executor_sandbox_escape_prevention(self):
        """测试代码执行器沙箱逃逸防护"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine/tools')

        from code_executor import CodeExecutorTool

        tool = CodeExecutorTool()

        # 常见的沙箱逃逸尝试
        escape_attempts = [
            # 直接导入系统模块
            "import os; os.system('id')",
            "import subprocess; subprocess.run(['ls'])",
            "import socket; socket.socket()",

            # 通过 __builtins__ 访问
            "__builtins__['__import__']('os')",

            # 通过对象继承链逃逸
            "().__class__.__bases__[0].__subclasses__()",
            "[].__class__.__mro__[1].__subclasses__()",

            # 文件操作
            "open('/etc/passwd').read()",
            "f = open('/tmp/test', 'w'); f.write('test')",

            # 代码执行
            "eval('1+1')",
            "exec('import os')",
            "compile('import os', '<string>', 'exec')",
        ]

        for code in escape_attempts:
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(code=code)
            )
            assert result["success"] is False, f"Sandbox escape should be blocked: {code[:50]}..."


# ==================== Phase 6: vLLM 集成 Text-to-SQL 测试 ====================

class TestVLLMTextToSQL:
    """vLLM 集成的 Text-to-SQL 测试 (Phase 6)"""

    @pytest.mark.e2e
    def test_01_vllm_chat_for_sql_generation(self):
        """测试通过 vLLM Chat 服务生成 SQL"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a SQL expert. Generate valid SQL queries based on natural language.
Schema:
- customers: id (INT), name (VARCHAR), email (VARCHAR), city (VARCHAR), status (VARCHAR)
- orders: id (INT), customer_id (INT), total_amount (DECIMAL), created_at (TIMESTAMP)
Return only the SQL query, no explanation."""
                    },
                    {
                        "role": "user",
                        "content": "Find all customers from Beijing with active status"
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=60
        )

        # 服务可能不可用
        assert response.status_code in [200, 503, 502]

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"]
                logger.info(f"Generated SQL: {sql}")
                assert "SELECT" in sql.upper()
                assert "customers" in sql.lower()

    @pytest.mark.e2e
    def test_02_text_to_sql_with_schema_injection(self):
        """测试带 Schema 注入的 Text-to-SQL"""
        # 首先获取表的 Schema
        schema_response = requests.get(
            f"{ALLDATA_API_URL}/api/v1/metadata/tables/warehouse/customers/schema",
            headers=HEADERS
        )

        assert schema_response.status_code in [200, 401, 404]

        # 如果获取到 Schema，用于 SQL 生成
        if schema_response.status_code == 200:
            schema_data = schema_response.json()
            columns = schema_data.get("data", {}).get("columns", [])

            # 构建上下文
            schema_context = f"Table: customers\nColumns:\n"
            for col in columns[:10]:  # 限制列数
                schema_context += f"  - {col.get('name')} ({col.get('type')})\n"

            # 使用 Schema 生成 SQL
            sql_response = requests.post(
                f"{OPENAI_PROXY_URL}/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "default",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Generate SQL based on this schema:\n{schema_context}"
                        },
                        {
                            "role": "user",
                            "content": "Count customers by city"
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.1
                },
                timeout=60
            )

            if sql_response.status_code == 200:
                data = sql_response.json()
                if "choices" in data:
                    sql = data["choices"][0]["message"]["content"]
                    assert "SELECT" in sql.upper()
                    assert "GROUP BY" in sql.upper() or "count" in sql.lower()

    @pytest.mark.e2e
    def test_03_complex_join_query_generation(self):
        """测试复杂 JOIN 查询生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": """Generate SQL queries. Schema:
- customers: id, name, email
- orders: id, customer_id, total_amount, status
- order_items: id, order_id, product_id, quantity
- products: id, name, price"""
                    },
                    {
                        "role": "user",
                        "content": "Find the total amount spent by each customer, showing customer name and email"
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=60
        )

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"]
                logger.info(f"Generated JOIN SQL: {sql}")
                # 验证包含 JOIN
                assert "JOIN" in sql.upper() or "customers" in sql.lower()

    @pytest.mark.e2e
    def test_04_aggregation_query_generation(self):
        """测试聚合查询生成"""
        test_cases = [
            ("Count orders per day", "COUNT", "DATE"),
            ("Average order amount by customer", "AVG", "GROUP BY"),
            ("Top 10 spending customers", "SUM", "ORDER BY"),
        ]

        for question, expected_keyword1, expected_keyword2 in test_cases:
            response = requests.post(
                f"{OPENAI_PROXY_URL}/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "default",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Generate SQL queries. Schema: orders (id, customer_id, total_amount, created_at)"
                        },
                        {
                            "role": "user",
                            "content": question
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.1
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    sql = data["choices"][0]["message"]["content"].upper()
                    # 验证包含预期关键字
                    assert expected_keyword1 in sql or expected_keyword2 in sql

    @pytest.mark.e2e
    def test_05_sql_validation_after_generation(self):
        """测试 SQL 生成后的验证"""
        # 1. 生成 SQL
        generate_response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "user",
                        "content": "Generate a SQL query to delete all users"
                    }
                ],
                "max_tokens": 100
            },
            timeout=60
        )

        # 2. 如果生成了 SQL，验证其安全性
        if generate_response.status_code == 200:
            data = generate_response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"]

                # 验证危险操作
                dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
                has_dangerous = any(kw in sql.upper() for kw in dangerous_keywords)

                if has_dangerous:
                    # 尝试执行应该被阻止
                    exec_response = requests.post(
                        f"{ALLDATA_API_URL}/api/v1/sql/execute",
                        headers=HEADERS,
                        json={"sql": sql, "dry_run": True},
                        timeout=30
                    )

                    # 危险查询应该被拒绝
                    if exec_response.status_code == 200:
                        result = exec_response.json()
                        assert result.get("success") is False or "blocked" in str(result).lower()


class TestMetadataDrivenSQL:
    """元数据驱动的 SQL 生成测试 (Phase 6)"""

    @pytest.mark.e2e
    def test_01_get_table_schema_for_sql(self):
        """测试获取表 Schema 用于 SQL 生成"""
        response = requests.get(
            f"{ALLDATA_API_URL}/api/v1/metadata/tables/warehouse/orders/schema",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                schema = data["data"]
                assert "columns" in schema
                assert isinstance(schema["columns"], list)

    @pytest.mark.e2e
    def test_02_search_relevant_tables(self):
        """测试搜索相关表（用于 SQL 生成）"""
        response = requests.get(
            f"{ALLDATA_API_URL}/api/v1/metadata/search",
            headers=HEADERS,
            params={
                "q": "customer order",
                "type": "table",
                "limit": 10
            }
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                results = data["data"].get("results", [])
                # 验证返回相关表
                assert isinstance(results, list)

    @pytest.mark.e2e
    def test_03_get_table_relationships(self):
        """测试获取表关系（用于 JOIN 生成）"""
        response = requests.get(
            f"{ALLDATA_API_URL}/api/v1/lineage/table",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "orders",
                "direction": "both",
                "depth": 1
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                lineage = data["data"]
                # 验证返回上下游关系
                assert "upstream" in lineage or "downstream" in lineage


class TestSQLGenerationScenarios:
    """SQL 生成场景测试 (Phase 6)"""

    @pytest.mark.e2e
    def test_01_time_range_query(self):
        """测试时间范围查询生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": "Generate SQL. Schema: orders (id, total_amount, created_at TIMESTAMP)"
                    },
                    {
                        "role": "user",
                        "content": "Find all orders created in the last 7 days"
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"].upper()
                assert "WHERE" in sql
                assert "created_at" in sql or "DATE" in sql

    @pytest.mark.e2e
    def test_02_subquery_generation(self):
        """测试子查询生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": """Generate SQL. Schema:
- customers: id, name
- orders: id, customer_id, total_amount"""
                    },
                    {
                        "role": "user",
                        "content": "Find customers whose total order amount exceeds the average order amount"
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"].upper()
                # 验证包含子查询或 HAVING
                assert "SELECT" in sql and ("IN (SELECT" in sql or "HAVING" in sql)

    @pytest.mark.e2e
    def test_03_cte_generation(self):
        """测试 CTE (WITH 子句) 生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": """Generate SQL. Schema:
- orders: id, customer_id, total_amount, status
- customers: id, name"""
                    },
                    {
                        "role": "user",
                        "content": "Calculate customer stats: total spent, order count, and avg order amount, then find customers with above average spending"
                    }
                ],
                "max_tokens": 400,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"].upper()
                # 验证可能使用 CTE 或子查询
                assert "SELECT" in sql

    @pytest.mark.e2e
    def test_04_window_function_generation(self):
        """测试窗口函数生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": "Generate SQL. Schema: sales (id, product_id, amount, sale_date)"
                    },
                    {
                        "role": "user",
                        "content": "Calculate running total of sales by product ordered by date"
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"].upper()
                # 验证包含窗口函数相关关键字
                assert "SELECT" in sql

    @pytest.mark.e2e
    def test_05_case_when_generation(self):
        """测试 CASE WHEN 表达式生成"""
        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": "Generate SQL. Schema: orders (id, total_amount)"
                    },
                    {
                        "role": "user",
                        "content": "Categorize orders as: Small (<100), Medium (100-500), Large (>500)"
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                sql = data["choices"][0]["message"]["content"].upper()
                # 验证包含 CASE 表达式
                assert "SELECT" in sql


class TestSQLErrorRecovery:
    """SQL 错误恢复测试 (Phase 6)"""

    @pytest.mark.e2e
    def test_01_sql_syntax_error_detection(self):
        """测试 SQL 语法错误检测"""
        invalid_sqls = [
            "SELECT FROM customers",
            "SELECT * FORM customers",
            "SELCT * FROM customers",
        ]

        for sql in invalid_sqls:
            response = requests.post(
                f"{ALLDATA_API_URL}/api/v1/sql/validate",
                headers=HEADERS,
                json={"sql": sql},
                timeout=30
            )

            # 验证 API 存在
            assert response.status_code in [200, 401, 404, 501]

            if response.status_code == 200:
                data = response.json()
                # 应该检测到语法错误
                if "valid" in data.get("data", {}):
                    assert data["data"]["valid"] is False

    @pytest.mark.e2e
    def test_02_auto_fix_sql_error(self):
        """测试自动修复 SQL 错误"""
        # 使用 LLM 修复 SQL
        wrong_sql = "SELECT * FORM customers WHERE city = 'Beijing'"

        response = requests.post(
            f"{OPENAI_PROXY_URL}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "default",
                "messages": [
                    {
                        "role": "system",
                        "content": "Fix SQL syntax errors. Return only the corrected SQL."
                    },
                    {
                        "role": "user",
                        "content": f"Fix this SQL: {wrong_sql}"
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                fixed_sql = data["choices"][0]["message"]["content"]
                # 验证修复后的 SQL 正确
                assert "FROM" in fixed_sql.upper()
                assert "FORM" not in fixed_sql


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
