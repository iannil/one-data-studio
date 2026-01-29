"""
Bisheng API Tracer Setup
Sprint 11.2: 分布式追踪 - Bisheng 追踪配置

初始化 Bisheng API 的 OpenTelemetry 追踪配置。
"""

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# 尝试导入追踪模块
try:
    from services.shared.tracing import (
        init_tracing,
        trace_function,
        trace_async_function,
        TracedClient,
        TracedDatabase,
        TracedCache,
        TracedVectorStore,
        SpanAttrs,
        get_trace_id,
        is_tracing_enabled
    )
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    logger.warning("Tracing module not available")

# 追踪配置
TRACING_CONFIG = {
    "service_name": "bisheng-api",
    "service_version": os.getenv("SERVICE_VERSION", "1.0.0"),
    "environment": os.getenv("ENVIRONMENT", "production"),
    "exporter": os.getenv("TRACING_EXPORTER", "otlp"),
    "exporter_endpoint": os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://opentelemetry-collector:4317"
    ),
    "sample_rate": float(os.getenv("TRACING_SAMPLE_RATE", "0.1")),
}


def setup_tracing():
    """
    设置 Bisheng API 的追踪

    在应用启动时调用此函数初始化追踪。
    """
    if not TRACING_AVAILABLE:
        logger.info("Tracing not available, skipping setup")
        return None

    try:
        tracer = init_tracing(**TRACING_CONFIG)
        if tracer:
            logger.info(f"Bisheng API tracing initialized: {TRACING_CONFIG}")
        return tracer
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
        return None


# Bisheng 特定的追踪装饰器
def trace_chat_request():
    """追踪聊天请求"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="chat.request",
            attributes={
                SpanAttrs.LLM_PROVIDER: "openai",
            }
        )(func)
    return decorator


def trace_workflow_execution():
    """追踪工作流执行"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="workflow.execute",
            attributes={
                "component": "workflow_engine",
            }
        )(func)
    return decorator


def trace_rag_query():
    """追踪 RAG 查询"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="rag.query",
            attributes={
                "component": "rag",
            }
        )(func)
    return decorator


def trace_text2sql():
    """追踪 Text-to-SQL 请求"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="text2sql.generate",
            attributes={
                "component": "text2sql",
                SpanAttrs.DB_SYSTEM: "mysql",
            }
        )(func)
    return decorator


def trace_agent_execution():
    """追踪 Agent 执行"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="agent.execute",
            attributes={
                "component": "agent",
            }
        )(func)
    return decorator


def trace_llm_call(provider: str = "openai", model: str = "gpt-3.5-turbo"):
    """追踪 LLM 调用"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs

    def decorator(func):
        return trace_function(
            name="llm.call",
            attributes={
                SpanAttrs.LLM_PROVIDER: provider,
                SpanAttrs.LLM_MODEL: model,
            }
        )(func)
    return decorator


def trace_vector_search(collection: str):
    """追踪向量搜索"""
    if not TRACING_AVAILABLE:
        return lambda f: f

    from services.shared.tracing import SpanAttrs, TracedVectorStore

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TracedVectorStore.trace_vector_operation("search", collection):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 预配置的追踪器
class BishengTracer:
    """Bisheng API 追踪器"""

    def __init__(self):
        self.tracer = setup_tracing()

    def is_enabled(self) -> bool:
        """检查追踪是否启用"""
        return is_tracing_enabled()

    def get_trace_id(self) -> str:
        """获取当前追踪 ID"""
        return get_trace_id()

    def add_event(self, name: str, attributes: dict = None):
        """添加事件到当前 Span"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import add_span_event
            add_span_event(name, attributes)

    def set_attribute(self, key: str, value):
        """设置 Span 属性"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import set_span_attribute
            set_span_attribute(key, value)

    def record_error(self, error: Exception):
        """记录错误"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import record_span_exception
            record_span_exception(error)


# 单例实例
_bisheng_tracer = None


def get_bisheng_tracer() -> BishengTracer:
    """获取 Bisheng 追踪器单例"""
    global _bisheng_tracer
    if _bisheng_tracer is None:
        _bisheng_tracer = BishengTracer()
    return _bisheng_tracer


# Flask 集成
def init_flask_tracing(app):
    """
    初始化 Flask 应用的追踪

    Args:
        app: Flask 应用实例
    """
    if not TRACING_AVAILABLE:
        return

    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        logger.info("Flask tracing instrumentation enabled")
    except ImportError:
        logger.warning("Flask instrumentation not available")

    # 添加请求前处理
    @app.before_request
    def before_request():
        if TRACING_AVAILABLE:
            from services.shared.tracing import set_span_attribute
            set_span_attribute("http.request_id", os.urandom(16).hex())

    # 添加请求后处理
    @app.after_request
    def after_request(response):
        if TRACING_AVAILABLE:
            from services.shared.tracing import set_span_attribute
            set_span_attribute("http.status_code", response.status_code)
        return response


# Celery 集成
def init_celery_tracing(celery_app):
    """
    初始化 Celery 的追踪

    Args:
        celery_app: Celery 应用实例
    """
    if not TRACING_AVAILABLE:
        return

    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.info("Celery tracing instrumentation enabled")
    except ImportError:
        logger.warning("Celery instrumentation not available")


# HTTP 客户端包装
class TracedRequests:
    """追踪的 HTTP 请求客户端"""

    @staticmethod
    def get(url: str, **kwargs):
        """追踪的 GET 请求"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import TracedClient
            import requests

            headers = TracedClient.inject_headers(kwargs.pop('headers', {}))
            with TracedClient.trace_http_request("GET", url, headers):
                return requests.get(url, headers=headers, **kwargs)

        import requests
        return requests.get(url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        """追踪的 POST 请求"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import TracedClient
            import requests

            headers = TracedClient.inject_headers(kwargs.pop('headers', {}))
            with TracedClient.trace_http_request("POST", url, headers):
                return requests.post(url, headers=headers, **kwargs)

        import requests
        return requests.post(url, **kwargs)

    @staticmethod
    def put(url: str, **kwargs):
        """追踪的 PUT 请求"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import TracedClient
            import requests

            headers = TracedClient.inject_headers(kwargs.pop('headers', {}))
            with TracedClient.trace_http_request("PUT", url, headers):
                return requests.put(url, headers=headers, **kwargs)

        import requests
        return requests.put(url, **kwargs)

    @staticmethod
    def delete(url: str, **kwargs):
        """追踪的 DELETE 请求"""
        if TRACING_AVAILABLE:
            from services.shared.tracing import TracedClient
            import requests

            headers = TracedClient.inject_headers(kwargs.pop('headers', {}))
            with TracedClient.trace_http_request("DELETE", url, headers):
                return requests.delete(url, headers=headers, **kwargs)

        import requests
        return requests.delete(url, **kwargs)


if __name__ == "__main__":
    # 测试追踪初始化
    tracer = setup_tracing()
    if tracer:
        logger.info("Bisheng API tracing initialized successfully")
    else:
        logger.warning("Bisheng API tracing initialization failed")
