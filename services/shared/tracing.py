"""
ONE-DATA-STUDIO Distributed Tracing Module
Sprint 11.2: 分布式追踪 - OpenTelemetry 集成

提供跨服务的分布式追踪功能，与 Jaeger 集成。
"""

import os
import time
from functools import wraps
from typing import Optional, Callable, Any, Dict, List, ContextManager
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# OpenTelemetry 导入
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry import propagate
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.trace import Status, StatusCode, Span
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.context import Context
    from opentelemetry.semconv.trace import SpanAttributes

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")


# Tracer 实例
_tracer: Optional[Any] = None
_provider: Optional[Any] = None


def init_tracing(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "production",
    exporter: str = "otlp",
    exporter_endpoint: Optional[str] = None,
    sample_rate: float = 0.1,
    headers: Optional[Dict[str, str]] = None
) -> Any:
    """
    初始化 OpenTelemetry 追踪

    Args:
        service_name: 服务名称
        service_version: 服务版本
        environment: 部署环境 (production, staging, development)
        exporter: 导出器类型 (otlp, jaeger, console)
        exporter_endpoint: 导出器端点
        sample_rate: 采样率 (0.0-1.0)
        headers: 请求头（用于认证等）

    Returns:
        Tracer 实例
    """
    global _tracer, _provider

    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, returning noop tracer")
        return None

    # 创建资源
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        DEPLOYMENT_ENVIRONMENT: environment,
    })

    # 创建 TracerProvider
    _provider = TracerProvider(resource=resource)

    # 配置导出器
    if exporter == "otlp":
        endpoint = exporter_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
        otlp_exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers,
        )
        processor = BatchSpanProcessor(otlp_exporter)
        _provider.add_span_processor(processor)
        logger.info(f"OTLP exporter configured: {endpoint}")

    elif exporter == "jaeger":
        endpoint = exporter_endpoint or os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "jaeger"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        )
        processor = BatchSpanProcessor(jaeger_exporter)
        _provider.add_span_processor(processor)
        logger.info(f"Jaeger exporter configured: {endpoint}")

    elif exporter == "console":
        console_exporter = ConsoleSpanExporter()
        processor = BatchSpanProcessor(console_exporter)
        _provider.add_span_processor(processor)
        logger.info("Console exporter configured")

    # 设置全局 TracerProvider
    trace.set_tracer_provider(_provider)

    # 创建 Tracer
    _tracer = trace.get_tracer(__name__, service_version)

    logger.info(f"Tracing initialized for {service_name} v{service_version} (sample_rate={sample_rate})")

    return _tracer


def get_tracer() -> Optional[Any]:
    """获取全局 Tracer 实例"""
    return _tracer


def is_tracing_enabled() -> bool:
    """检查追踪是否启用"""
    return OTEL_AVAILABLE and _tracer is not None


@contextmanager
def start_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: Optional[Any] = None
):
    """
    启动一个 Span 的上下文管理器

    Args:
        name: Span 名称
        attributes: Span 属性
        kind: Span 类型

    Usage:
        with start_span("database.query", {"db.system": "postgresql"}) as span:
            result = db.query("SELECT * FROM users")
    """
    if not is_tracing_enabled():
        yield None
        return

    if kind is None:
        from opentelemetry.trace import SpanKind
        kind = SpanKind.INTERNAL

    span = _tracer.start_span(name, attributes=attributes, kind=kind)

    try:
        yield span
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


def trace_function(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    kind: Optional[Any] = None
):
    """
    函数追踪装饰器

    Args:
        name: Span 名称（默认使用函数名）
        attributes: Span 属性
        kind: Span 类型

    Usage:
        @trace_function("cache.get")
        def get_from_cache(key: str):
            return cache.get(key)

        @trace_function(attributes={"operation": "query"})
        def query_database(sql: str):
            return db.execute(sql)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_tracing_enabled():
                return func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__name__}"

            if kind is None:
                from opentelemetry.trace import SpanKind
                span_kind = SpanKind.INTERNAL
            else:
                span_kind = kind

            with _tracer.start_as_current_span(span_name, kind=span_kind) as span:
                # 添加属性
                if attributes:
                    span.set_attributes(attributes)

                # 添加函数参数
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # 记录参数（避免记录敏感数据）
                if args and len(args) < 10:
                    for i, arg in enumerate(args[:5]):  # 最多记录前5个参数
                        if isinstance(arg, (str, int, float, bool)):
                            span.set_attribute(f"function.args.{i}", str(arg)[:100])

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)

                    # 记录执行时间
                    duration = time.time() - start_time
                    span.set_attribute("function.duration_ms", duration * 1000)

                    return result

                except Exception as e:
                    # 记录异常
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.message", str(e))
                    span.set_attribute("error.type", type(e).__name__)
                    raise

        return wrapper

    return decorator


def trace_async_function(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    异步函数追踪装饰器

    Args:
        name: Span 名称
        attributes: Span 属性

    Usage:
        @trace_async_function("http.request")
        async def fetch_data(url: str):
            return await aiohttp.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_tracing_enabled():
                return await func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__name__}"

            with _tracer.start_as_current_span(span_name) as span:
                if attributes:
                    span.set_attributes(attributes)

                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.async", True)

                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)

                    duration = time.time() - start_time
                    span.set_attribute("function.duration_ms", duration * 1000)

                    return result

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper

    return decorator


class TracedClient:
    """
    HTTP 客户端追踪包装器

    为 HTTP 请求自动添加追踪头和 Span
    """

    def __init__(self, session=None):
        self._session = session

    @staticmethod
    def inject_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """
        注入追踪上下文到 HTTP 头

        Args:
            headers: 原始请求头

        Returns:
            包含追踪上下文的请求头
        """
        if not is_tracing_enabled():
            return headers

        carrier = {}
        propagate.inject(carrier)

        # 合并到原始请求头
        result = headers.copy()
        result.update(carrier)

        return result

    @staticmethod
    @contextmanager
    def trace_http_request(
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        追踪 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            headers: 请求头
        """
        if not is_tracing_enabled():
            yield None
            return

        from opentelemetry.trace import SpanKind
        from opentelemetry.semconv.trace import SpanAttributes

        attributes = {
            SpanAttributes.HTTP_METHOD: method.upper(),
            SpanAttributes.HTTP_URL: url,
        }

        with start_span(f"HTTP {method.upper()}", attributes, kind=SpanKind.CLIENT) as span:
            # 注入追踪头
            if headers is not None:
                carrier = {}
                propagate.inject(carrier)
                headers.update(carrier)

                # 记录请求头（不含敏感信息）
                safe_headers = {k: v for k, v in headers.items()
                               if k.lower() not in ('authorization', 'cookie', 'set-cookie')}
                span.set_attributes({f"http.request.header.{k}": v for k, v in safe_headers.items()})

            yield span


class TracedDatabase:
    """
    数据库操作追踪包装器
    """

    @staticmethod
    @contextmanager
    def trace_query(
        db_type: str,
        db_name: str,
        query: Optional[str] = None
    ):
        """
        追踪数据库查询

        Args:
            db_type: 数据库类型 (postgresql, mysql, redis, etc.)
            db_name: 数据库名称
            query: SQL 查询语句
        """
        if not is_tracing_enabled():
            yield None
            return

        from opentelemetry.trace import SpanKind
        from opentelemetry.semconv.trace import SpanAttributes

        attributes = {
            "db.system": db_type,
            "db.name": db_name,
        }

        if query:
            # 截断过长的查询
            safe_query = query[:1000] if len(query) > 1000 else query
            attributes["db.statement"] = safe_query

        with start_span(f"DB Query", attributes, kind=SpanKind.CLIENT) as span:
            yield span


class TracedCache:
    """
    缓存操作追踪包装器
    """

    @staticmethod
    @contextmanager
    def trace_cache_operation(operation: str, key: str):
        """
        追踪缓存操作

        Args:
            operation: 操作类型 (get, set, delete, etc.)
            key: 缓存键
        """
        if not is_tracing_enabled():
            yield None
            return

        from opentelemetry.trace import SpanKind

        attributes = {
            "cache.operation": operation,
            "cache.key": key[:100] if key else None,
        }

        with start_span(f"Cache {operation}", attributes, kind=SpanKind.CLIENT) as span:
            yield span


class TracedVectorStore:
    """
    向量存储操作追踪包装器
    """

    @staticmethod
    @contextmanager
    def trace_vector_operation(operation: str, collection: str, num_vectors: int = 0):
        """
        追踪向量存储操作

        Args:
            operation: 操作类型 (search, insert, delete, etc.)
            collection: 集合名称
            num_vectors: 向量数量
        """
        if not is_tracing_enabled():
            yield None
            return

        from opentelemetry.trace import SpanKind

        attributes = {
            "vector.operation": operation,
            "vector.collection": collection,
            "vector.count": num_vectors,
        }

        with start_span(f"Vector {operation}", attributes, kind=SpanKind.CLIENT) as span:
            yield span


# Span 属性常量
class SpanAttrs:
    """常用的 Span 属性"""

    # HTTP
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_ROUTE = "http.route"

    # Database
    DB_SYSTEM = "db.system"
    DB_NAME = "db.name"
    DB_STATEMENT = "db.statement"
    DB_OPERATION = "db.operation"

    # Cache
    CACHE_OPERATION = "cache.operation"
    CACHE_KEY = "cache.key"
    CACHE_HIT = "cache.hit"

    # Vector Store
    VECTOR_OPERATION = "vector.operation"
    VECTOR_COLLECTION = "vector.collection"
    VECTOR_COUNT = "vector.count"
    VECTOR_DIMENSIONS = "vector.dimensions"

    # LLM
    LLM_PROVIDER = "llm.provider"
    LLM_MODEL = "llm.model"
    LLM_PROMPT_TOKENS = "llm.prompt_tokens"
    LLM_COMPLETION_TOKENS = "llm.completion_tokens"
    LLM_TOTAL_TOKENS = "llm.total_tokens"

    # Workflow
    WORKFLOW_ID = "workflow.id"
    WORKFLOW_NAME = "workflow.name"
    WORKFLOW_NODE_ID = "workflow.node.id"
    WORKFLOW_NODE_TYPE = "workflow.node.type"

    # User
    USER_ID = "user.id"
    TENANT_ID = "tenant.id"

    # Error
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"


def get_trace_id() -> Optional[str]:
    """获取当前追踪 ID"""
    if not is_tracing_enabled():
        return None

    current_span = trace.get_current_span()
    if current_span and current_span.context:
        return format(current_span.context.trace_id, "032x")
    return None


def get_span_id() -> Optional[str]:
    """获取当前 Span ID"""
    if not is_tracing_enabled():
        return None

    current_span = trace.get_current_span()
    if current_span and current_span.context:
        return format(current_span.context.span_id, "016x")
    return None


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """添加事件到当前 Span"""
    if not is_tracing_enabled():
        return

    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes)


def set_span_attribute(key: str, value: Any):
    """设置当前 Span 属性"""
    if not is_tracing_enabled():
        return

    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)


def record_span_exception(exception: Exception):
    """记录异常到当前 Span"""
    if not is_tracing_enabled():
        return

    current_span = trace.get_current_span()
    if current_span:
        current_span.record_exception(exception)
        current_span.set_status(Status(StatusCode.ERROR, str(exception)))
