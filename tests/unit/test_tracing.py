"""
分布式追踪模块单元测试
Sprint 11.2: P2 测试覆盖 - OpenTelemetry 集成
"""

import pytest
from unittest.mock import patch, MagicMock


class TestTracingAvailability:
    """追踪可用性测试"""

    def test_otel_available_flag(self):
        """测试 OpenTelemetry 可用标志"""
        from services.shared.tracing import OTEL_AVAILABLE
        # 标志应该存在（True 或 False 取决于是否安装了 opentelemetry）
        assert isinstance(OTEL_AVAILABLE, bool)

    def test_is_tracing_enabled_when_disabled(self):
        """测试追踪未启用时"""
        from services.shared.tracing import is_tracing_enabled
        # 如果没有初始化，应该返回 False
        # 注意：这取决于全局状态


class TestSpanAttrs:
    """Span 属性常量测试"""

    def test_http_attributes(self):
        """测试 HTTP 属性"""
        from services.shared.tracing import SpanAttrs

        assert SpanAttrs.HTTP_METHOD == "http.method"
        assert SpanAttrs.HTTP_URL == "http.url"
        assert SpanAttrs.HTTP_STATUS_CODE == "http.status_code"

    def test_database_attributes(self):
        """测试数据库属性"""
        from services.shared.tracing import SpanAttrs

        assert SpanAttrs.DB_SYSTEM == "db.system"
        assert SpanAttrs.DB_NAME == "db.name"
        assert SpanAttrs.DB_STATEMENT == "db.statement"

    def test_cache_attributes(self):
        """测试缓存属性"""
        from services.shared.tracing import SpanAttrs

        assert SpanAttrs.CACHE_OPERATION == "cache.operation"
        assert SpanAttrs.CACHE_KEY == "cache.key"
        assert SpanAttrs.CACHE_HIT == "cache.hit"

    def test_llm_attributes(self):
        """测试 LLM 属性"""
        from services.shared.tracing import SpanAttrs

        assert SpanAttrs.LLM_PROVIDER == "llm.provider"
        assert SpanAttrs.LLM_MODEL == "llm.model"
        assert SpanAttrs.LLM_PROMPT_TOKENS == "llm.prompt_tokens"

    def test_workflow_attributes(self):
        """测试工作流属性"""
        from services.shared.tracing import SpanAttrs

        assert SpanAttrs.WORKFLOW_ID == "workflow.id"
        assert SpanAttrs.WORKFLOW_NAME == "workflow.name"


class TestStartSpan:
    """start_span 上下文管理器测试"""

    def test_start_span_when_disabled(self):
        """测试追踪禁用时的 start_span"""
        from services.shared.tracing import start_span

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            with start_span("test_span") as span:
                assert span is None

    def test_start_span_yields_span(self):
        """测试 start_span 返回 span"""
        from services.shared.tracing import start_span, _tracer

        if _tracer is None:
            pytest.skip("Tracing not initialized")

        with start_span("test_span", {"key": "value"}) as span:
            assert span is not None


class TestTraceFunction:
    """trace_function 装饰器测试"""

    def test_trace_function_when_disabled(self):
        """测试追踪禁用时装饰器正常工作"""
        from services.shared.tracing import trace_function

        @trace_function("test_function")
        def my_func(x, y):
            return x + y

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            result = my_func(1, 2)
            assert result == 3

    def test_trace_function_preserves_function(self):
        """测试装饰器保留函数功能"""
        from services.shared.tracing import trace_function

        @trace_function("test")
        def add(a, b):
            return a + b

        assert add(5, 3) == 8

    def test_trace_function_preserves_name(self):
        """测试装饰器保留函数名"""
        from services.shared.tracing import trace_function

        @trace_function("custom_name")
        def my_function():
            pass

        assert my_function.__name__ == 'my_function'


class TestTraceAsyncFunction:
    """trace_async_function 装饰器测试"""

    @pytest.mark.asyncio
    async def test_trace_async_function_when_disabled(self):
        """测试追踪禁用时异步装饰器正常工作"""
        from services.shared.tracing import trace_async_function

        @trace_async_function("test_async")
        async def my_async_func(x):
            return x * 2

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            result = await my_async_func(5)
            assert result == 10


class TestTracedClient:
    """HTTP 客户端追踪测试"""

    def test_inject_headers_when_disabled(self):
        """测试追踪禁用时注入头"""
        from services.shared.tracing import TracedClient

        headers = {'Content-Type': 'application/json'}

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            result = TracedClient.inject_headers(headers)
            assert result == headers

    def test_inject_headers_preserves_original(self):
        """测试注入头保留原始头"""
        from services.shared.tracing import TracedClient

        original = {'Authorization': 'Bearer token'}
        result = TracedClient.inject_headers(original)

        assert 'Authorization' in result


class TestTracedDatabase:
    """数据库追踪测试"""

    def test_trace_query_when_disabled(self):
        """测试追踪禁用时数据库查询"""
        from services.shared.tracing import TracedDatabase

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            with TracedDatabase.trace_query("postgresql", "test_db", "SELECT 1") as span:
                assert span is None


class TestTracedCache:
    """缓存追踪测试"""

    def test_trace_cache_operation_when_disabled(self):
        """测试追踪禁用时缓存操作"""
        from services.shared.tracing import TracedCache

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            with TracedCache.trace_cache_operation("get", "my_key") as span:
                assert span is None


class TestTracedVectorStore:
    """向量存储追踪测试"""

    def test_trace_vector_operation_when_disabled(self):
        """测试追踪禁用时向量操作"""
        from services.shared.tracing import TracedVectorStore

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            with TracedVectorStore.trace_vector_operation("search", "docs", 100) as span:
                assert span is None


class TestHelperFunctions:
    """辅助函数测试"""

    def test_get_trace_id_when_disabled(self):
        """测试追踪禁用时获取追踪 ID"""
        from services.shared.tracing import get_trace_id

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            assert get_trace_id() is None

    def test_get_span_id_when_disabled(self):
        """测试追踪禁用时获取 Span ID"""
        from services.shared.tracing import get_span_id

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            assert get_span_id() is None

    def test_add_span_event_when_disabled(self):
        """测试追踪禁用时添加事件"""
        from services.shared.tracing import add_span_event

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            # 不应该抛出异常
            add_span_event("test_event", {"key": "value"})

    def test_set_span_attribute_when_disabled(self):
        """测试追踪禁用时设置属性"""
        from services.shared.tracing import set_span_attribute

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            # 不应该抛出异常
            set_span_attribute("key", "value")

    def test_record_span_exception_when_disabled(self):
        """测试追踪禁用时记录异常"""
        from services.shared.tracing import record_span_exception

        with patch('services.shared.tracing.is_tracing_enabled', return_value=False):
            # 不应该抛出异常
            record_span_exception(ValueError("test"))


class TestGetTracer:
    """获取 Tracer 测试"""

    def test_get_tracer_returns_global(self):
        """测试获取全局 Tracer"""
        from services.shared.tracing import get_tracer

        tracer = get_tracer()
        # 可能为 None 如果未初始化
        # 主要测试函数不抛出异常
