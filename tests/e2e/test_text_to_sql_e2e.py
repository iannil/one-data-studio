"""
Text-to-SQL E2E 测试
Sprint 24: 端到端测试

测试完整的 Text-to-SQL 工作流程:
1. 接收自然语言查询
2. 元数据注入
3. SQL 生成
4. SQL 验证
5. 执行查询
6. 返回结果
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock


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
