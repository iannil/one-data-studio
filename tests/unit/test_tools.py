"""
工具模块单元测试
测试 tools.py 中的安全功能和工具执行

Coverage:
- SafeMathEvaluator (安全数学表达式求值)
- SQLQueryTool (SQL 查询工具 + SQL 注入防护)
- SSRFProtection (SSRF 防护)
- HTTPRequestTool (HTTP 请求工具)
- CalculatorTool (计算器工具)
- 生产环境 mock 数据检查
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestSafeMathEvaluator:
    """SafeMathEvaluator 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """导入 SafeMathEvaluator"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import SafeMathEvaluator
        self.evaluator = SafeMathEvaluator

    def test_basic_arithmetic(self):
        """测试基本算术运算"""
        assert self.evaluator.evaluate("1 + 1") == 2
        assert self.evaluator.evaluate("10 - 3") == 7
        assert self.evaluator.evaluate("4 * 5") == 20
        assert self.evaluator.evaluate("20 / 4") == 5.0
        assert self.evaluator.evaluate("10 // 3") == 3
        assert self.evaluator.evaluate("10 % 3") == 1
        assert self.evaluator.evaluate("2 ** 3") == 8

    def test_math_functions(self):
        """测试数学函数"""
        import math
        assert self.evaluator.evaluate("sqrt(16)") == 4.0
        assert self.evaluator.evaluate("abs(-5)") == 5
        assert self.evaluator.evaluate("round(3.7)") == 4
        assert self.evaluator.evaluate("min(1, 2, 3)") == 1
        assert self.evaluator.evaluate("max(1, 2, 3)") == 3
        assert abs(self.evaluator.evaluate("sin(0)") - 0) < 0.0001
        assert abs(self.evaluator.evaluate("cos(0)") - 1) < 0.0001

    def test_math_constants(self):
        """测试数学常量"""
        import math
        assert abs(self.evaluator.evaluate("pi") - math.pi) < 0.0001
        assert abs(self.evaluator.evaluate("e") - math.e) < 0.0001

    def test_complex_expression(self):
        """测试复杂表达式"""
        assert self.evaluator.evaluate("(1 + 2) * 3") == 9
        assert self.evaluator.evaluate("sqrt(16) + 2 * 3") == 10.0

    def test_rejects_unknown_function(self):
        """测试拒绝未知函数"""
        with pytest.raises(ValueError, match="Unknown function"):
            self.evaluator.evaluate("dangerous_func()")

    def test_rejects_unknown_variable(self):
        """测试拒绝未知变量"""
        with pytest.raises(ValueError, match="Unknown variable"):
            self.evaluator.evaluate("unknown_var + 1")

    def test_rejects_code_injection(self):
        """测试拒绝代码注入尝试"""
        # 尝试执行系统命令
        with pytest.raises(ValueError):
            self.evaluator.evaluate("__import__('os').system('ls')")

        # 尝试访问内置函数
        with pytest.raises(ValueError):
            self.evaluator.evaluate("eval('1+1')")

        # 尝试导入模块
        with pytest.raises(ValueError):
            self.evaluator.evaluate("import os")

    def test_syntax_error(self):
        """测试语法错误处理"""
        with pytest.raises(ValueError, match="Invalid expression"):
            self.evaluator.evaluate("1 + + 1")


class TestSQLQueryTool:
    """SQLQueryTool 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

    def test_sql_injection_drop_blocked(self):
        """测试 SQL 注入 - DROP 语句被阻止"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="DROP TABLE users;")
        )
        assert result["success"] is False
        assert "Dangerous SQL" in result["error"]

    def test_sql_injection_delete_blocked(self):
        """测试 SQL 注入 - DELETE 语句被阻止"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="DELETE FROM users WHERE 1=1;")
        )
        assert result["success"] is False
        assert "Dangerous SQL" in result["error"]

    def test_sql_injection_union_blocked(self):
        """测试 SQL 注入 - UNION 注入被阻止"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="SELECT * FROM users UNION SELECT * FROM passwords;")
        )
        assert result["success"] is False
        assert "injection" in result["error"].lower()

    def test_sql_injection_comment_blocked(self):
        """测试 SQL 注入 - 注释攻击被阻止"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="SELECT * FROM users WHERE id = 1;--")
        )
        assert result["success"] is False
        assert "injection" in result["error"].lower()

    def test_sql_injection_or_1_equals_1_blocked(self):
        """测试 SQL 注入 - OR 1=1 被阻止"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="SELECT * FROM users WHERE id = 1 OR 1=1;")
        )
        assert result["success"] is False
        assert "injection" in result["error"].lower()

    def test_valid_select_query(self):
        """测试有效的 SELECT 查询"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={"mock_data": True})
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(sql="SELECT name, email FROM users WHERE status = 'active';")
        )
        assert result["success"] is True
        assert "results" in result

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_rejects_mock_data(self):
        """测试生产环境拒绝 mock 数据"""
        from tools import SQLQueryTool

        with pytest.raises(RuntimeError, match="mock_data=True is not allowed in production"):
            SQLQueryTool(config={"mock_data": True})

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_default_no_mock(self):
        """测试生产环境默认不使用 mock 数据"""
        from tools import SQLQueryTool

        tool = SQLQueryTool(config={})
        assert tool.mock_data is False


class TestSSRFProtection:
    """SSRFProtection 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """导入 SSRFProtection"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import SSRFProtection
        self.protection = SSRFProtection

    def test_blocks_localhost(self):
        """测试阻止 localhost 访问"""
        is_safe, error = self.protection.validate_url("http://localhost/admin")
        assert is_safe is False
        assert "localhost" in error.lower() or "not allowed" in error.lower()

    def test_blocks_127_0_0_1(self):
        """测试阻止 127.0.0.1 访问"""
        is_safe, error = self.protection.validate_url("http://127.0.0.1/admin")
        assert is_safe is False

    def test_blocks_private_ip_10(self):
        """测试阻止 10.x.x.x 私有 IP"""
        is_safe, error = self.protection.validate_url("http://10.0.0.1/internal")
        assert is_safe is False
        assert "private" in error.lower() or "not allowed" in error.lower()

    def test_blocks_private_ip_172(self):
        """测试阻止 172.16.x.x 私有 IP"""
        is_safe, error = self.protection.validate_url("http://172.16.0.1/internal")
        assert is_safe is False

    def test_blocks_private_ip_192(self):
        """测试阻止 192.168.x.x 私有 IP"""
        is_safe, error = self.protection.validate_url("http://192.168.1.1/router")
        assert is_safe is False

    def test_blocks_metadata_endpoint(self):
        """测试阻止云元数据端点"""
        is_safe, error = self.protection.validate_url("http://169.254.169.254/latest/meta-data/")
        assert is_safe is False

    def test_blocks_kubernetes_internal(self):
        """测试阻止 Kubernetes 内部服务"""
        is_safe, error = self.protection.validate_url("http://kubernetes.default.svc.cluster.local/api")
        assert is_safe is False

    def test_blocks_file_scheme(self):
        """测试阻止 file:// 协议"""
        is_safe, error = self.protection.validate_url("file:///etc/passwd")
        assert is_safe is False
        assert "scheme" in error.lower()

    def test_blocks_gopher_scheme(self):
        """测试阻止 gopher:// 协议"""
        is_safe, error = self.protection.validate_url("gopher://localhost:25/")
        assert is_safe is False

    def test_requires_scheme(self):
        """测试要求 URL 包含协议"""
        is_safe, error = self.protection.validate_url("example.com/path")
        assert is_safe is False
        assert "scheme" in error.lower()

    def test_requires_hostname(self):
        """测试要求 URL 包含主机名"""
        is_safe, error = self.protection.validate_url("http:///path")
        assert is_safe is False
        assert "hostname" in error.lower()


class TestCalculatorTool:
    """CalculatorTool 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """导入 CalculatorTool"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import CalculatorTool
        self.tool = CalculatorTool()

    def test_basic_calculation(self):
        """测试基本计算"""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            self.tool.execute(expression="2 + 2")
        )
        assert result["success"] is True
        assert result["result"] == 4

    def test_complex_calculation(self):
        """测试复杂计算"""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            self.tool.execute(expression="sqrt(16) * 2 + 3")
        )
        assert result["success"] is True
        assert result["result"] == 11.0

    def test_division_by_zero(self):
        """测试除零错误"""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            self.tool.execute(expression="1 / 0")
        )
        assert result["success"] is False
        assert "error" in result

    def test_rejects_code_injection(self):
        """测试拒绝代码注入"""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            self.tool.execute(expression="__import__('os').system('rm -rf /')")
        )
        assert result["success"] is False


class TestToolRegistry:
    """ToolRegistry 测试"""

    def test_registry_initialization(self):
        """测试注册表初始化"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_tools()

        # 验证默认工具已注册
        tool_names = [t["name"] for t in tools]
        assert "calculator" in tool_names
        assert "http_request" in tool_names
        assert "sql_query" in tool_names

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import get_tool_registry

        registry = get_tool_registry()
        tool = registry.get("nonexistent_tool")
        assert tool is None

    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')
        from tools import get_tool_registry
        import asyncio

        registry = get_tool_registry()
        result = asyncio.get_event_loop().run_until_complete(
            registry.execute("nonexistent_tool")
        )
        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestEnvironmentChecks:
    """环境检查测试"""

    def test_ssl_verification_disabled_blocks_production(self):
        """测试生产环境禁止禁用 SSL 验证"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "VERIFY_SSL": "false"}):
            # 重新加载模块以应用环境变量
            import sys
            if 'tools' in sys.modules:
                del sys.modules['tools']

            sys.path.insert(0, 'services/bisheng-api/engine')

            with pytest.raises(ValueError, match="VERIFY_SSL cannot be disabled in production"):
                import tools
