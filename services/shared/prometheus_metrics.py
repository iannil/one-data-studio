"""
Prometheus 指标模块
Sprint 24: 监控与运维增强

提供统一的 Prometheus 指标收集功能：
- HTTP 请求指标
- 数据库连接池指标
- AI 服务调用指标
- 业务指标
"""

import time
import logging
import functools
from typing import Callable, Optional, Dict, Any, List
from flask import Flask, request, g, Response
from sqlalchemy import event
from sqlalchemy.engine import Engine
from collections import defaultdict

logger = logging.getLogger(__name__)

# 尝试导入 prometheus_client
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Summary,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available. Metrics will be disabled.")

    # 创建空的类作为占位符
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def time(self): return self

    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class CollectorRegistry:
        pass

    def generate_latest(*args, **kwargs): return b""

    CONTENT_TYPE_LATEST = "text/plain"


class PrometheusMetrics:
    """
    Prometheus 指标收集器

    用法：
        metrics = PrometheusMetrics(app, service_name="data-api")
        或
        metrics = PrometheusMetrics()
        metrics.init_app(app, service_name="data-api")
    """

    def __init__(self, app: Optional[Flask] = None, service_name: str = "api"):
        self.service_name = service_name
        self._initialized = False

        # 指标定义
        self._http_requests_total = None
        self._http_request_duration_seconds = None
        self._http_requests_in_progress = None
        self._http_response_size_bytes = None

        self._db_connections_total = None
        self._db_connection_duration_seconds = None
        self._db_connections_in_use = None

        self._ai_requests_total = None
        self._ai_request_duration_seconds = None
        self._ai_request_tokens_total = None

        self._business_operations_total = None
        self._business_operation_duration_seconds = None

        self._cache_hits_total = None
        self._cache_misses_total = None

        self._task_queue_size = None
        self._task_duration_seconds = None

        if app is not None:
            self.init_app(app, service_name)

    def init_app(self, app: Flask, service_name: str = "api"):
        """初始化 Flask 应用的指标收集"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus metrics not available")
            return

        self.service_name = service_name or app.name
        self._initialized = True

        # 创建注册表
        self.registry = CollectorRegistry()

        # HTTP 指标
        self._http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry
        )
        self._http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
            registry=self.registry
        )
        self._http_requests_in_progress = Gauge(
            "http_requests_in_progress",
            "HTTP requests currently in progress",
            ["method", "endpoint"],
            registry=self.registry
        )
        self._http_response_size_bytes = Histogram(
            "http_response_size_bytes",
            "HTTP response size",
            ["method", "endpoint"],
            buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
            registry=self.registry
        )

        # 数据库指标
        self._db_connections_total = Counter(
            "db_connections_total",
            "Total database connections",
            ["database", "state"],
            registry=self.registry
        )
        self._db_connection_duration_seconds = Histogram(
            "db_connection_duration_seconds",
            "Database connection latency",
            ["database", "operation"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )
        self._db_connections_in_use = Gauge(
            "db_connections_in_use",
            "Database connections currently in use",
            ["database"],
            registry=self.registry
        )

        # AI 服务指标
        self._ai_requests_total = Counter(
            "ai_requests_total",
            "Total AI service requests",
            ["service", "model", "status"],
            registry=self.registry
        )
        self._ai_request_duration_seconds = Histogram(
            "ai_request_duration_seconds",
            "AI service request latency",
            ["service", "model"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry
        )
        self._ai_request_tokens_total = Counter(
            "ai_request_tokens_total",
            "Total AI tokens processed",
            ["service", "model", "type"],
            registry=self.registry
        )

        # 业务操作指标
        self._business_operations_total = Counter(
            "business_operations_total",
            "Total business operations",
            ["operation", "status"],
            registry=self.registry
        )
        self._business_operation_duration_seconds = Histogram(
            "business_operation_duration_seconds",
            "Business operation latency",
            ["operation"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )

        # 缓存指标
        self._cache_hits_total = Counter(
            "cache_hits_total",
            "Total cache hits",
            ["cache"],
            registry=self.registry
        )
        self._cache_misses_total = Counter(
            "cache_misses_total",
            "Total cache misses",
            ["cache"],
            registry=self.registry
        )

        # 任务指标
        self._task_queue_size = Gauge(
            "task_queue_size",
            "Current task queue size",
            ["queue"],
            registry=self.registry
        )
        self._task_duration_seconds = Histogram(
            "task_duration_seconds",
            "Task execution duration",
            ["task_type"],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0),
            registry=self.registry
        )

        # 注册请求中间件
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

        # 添加 metrics 端点
        app.add_url_rule("/metrics", "metrics", self._metrics_endpoint)

        # SQL 指标收集（如果配置了 SQLAlchemy）
        if hasattr(app, "extensions") and "sqlalchemy" in app.extensions:
            self._register_sqlalchemy_metrics(app)

        logger.info(f"Prometheus metrics initialized for {self.service_name}")

    def _before_request(self):
        """请求开始前"""
        if not self._initialized:
            return
        g.start_time = time.time()
        if self._http_requests_in_progress:
            self._http_requests_in_progress.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown"
            ).inc()

    def _after_request(self, response: Response) -> Response:
        """请求完成后"""
        if not self._initialized:
            return response

        # 记录请求总数
        if self._http_requests_total:
            self._http_requests_total.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown",
                status=response.status_code
            ).inc()

        # 记录请求耗时
        if hasattr(g, "start_time") and self._http_request_duration_seconds:
            duration = time.time() - g.start_time
            self._http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown"
            ).observe(duration)

        # 记录响应大小
        if response.content_length and self._http_response_size_bytes:
            self._http_response_size_bytes.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown"
            ).observe(response.content_length)

        # 添加响应头（用于追踪）
        response.headers["X-Request-Duration"] = f"{(time.time() - g.start_time) * 1000:.2f}ms"

        return response

    def _teardown_request(self, exception):
        """请求清理"""
        if not self._initialized:
            return
        if self._http_requests_in_progress:
            self._http_requests_in_progress.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown"
            ).dec()

    def _metrics_endpoint(self) -> Response:
        """Prometheus metrics 端点"""
        if not PROMETHEUS_AVAILABLE:
            return "Prometheus metrics not available", 503

        from flask import Response
        return Response(
            generate_latest(self.registry),
            mimetype=CONTENT_TYPE_LATEST
        )

    def _register_sqlalchemy_metrics(self, app: Flask):
        """注册 SQLAlchemy 指标"""
        if not PROMETHEUS_AVAILABLE:
            return

        @event.listens_for(Engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            if self._db_connections_total:
                self._db_connections_total.labels(
                    database=app.config.get("DB_NAME", "default"),
                    state="connected"
                ).inc()
            if self._db_connections_in_use:
                self._db_connections_in_use.labels(
                    database=app.config.get("DB_NAME", "default")
                ).inc()

        @event.listens_for(Engine, "close")
        def receive_close(dbapi_conn, connection_record):
            if self._db_connections_total:
                self._db_connections_total.labels(
                    database=app.config.get("DB_NAME", "default"),
                    state="closed"
                ).inc()
            if self._db_connections_in_use:
                self._db_connections_in_use.labels(
                    database=app.config.get("DB_NAME", "default")
                ).dec()

        logger.info("SQLAlchemy metrics registered")

    # 公共方法：记录 AI 服务调用

    def record_ai_request(
        self,
        service: str,
        model: str,
        status: str,
        duration: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ):
        """记录 AI 服务请求"""
        if not self._initialized:
            return

        if self._ai_requests_total:
            self._ai_requests_total.labels(
                service=service,
                model=model,
                status=status
            ).inc()

        if self._ai_request_duration_seconds:
            self._ai_request_duration_seconds.labels(
                service=service,
                model=model
            ).observe(duration)

        if self._ai_request_tokens_total:
            self._ai_request_tokens_total.labels(
                service=service,
                model=model,
                type="prompt"
            ).inc(prompt_tokens)
            self._ai_request_tokens_total.labels(
                service=service,
                model=model,
                type="completion"
            ).inc(completion_tokens)

    # 公共方法：记录业务操作

    def record_business_operation(self, operation: str, status: str, duration: float):
        """记录业务操作"""
        if not self._initialized:
            return

        if self._business_operations_total:
            self._business_operations_total.labels(
                operation=operation,
                status=status
            ).inc()

        if self._business_operation_duration_seconds:
            self._business_operation_duration_seconds.labels(
                operation=operation
            ).observe(duration)

    # 公共方法：缓存操作

    def record_cache_hit(self, cache: str = "default"):
        """记录缓存命中"""
        if self._cache_hits_total:
            self._cache_hits_total.labels(cache=cache).inc()

    def record_cache_miss(self, cache: str = "default"):
        """记录缓存未命中"""
        if self._cache_misses_total:
            self._cache_misses_total.labels(cache=cache).inc()

    # 公共方法：任务指标

    def record_task_start(self, queue: str = "default"):
        """记录任务开始"""
        if self._task_queue_size:
            self._task_queue_size.labels(queue=queue).inc()

    def record_task_complete(self, task_type: str, duration: float, queue: str = "default"):
        """记录任务完成"""
        if self._task_queue_size:
            self._task_queue_size.labels(queue=queue).dec()

        if self._task_duration_seconds:
            self._task_duration_seconds.labels(task_type=task_type).observe(duration)


# 装饰器：跟踪业务操作

def track_operation(metrics: PrometheusMetrics, operation_name: str):
    """装饰器：跟踪业务操作"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Operation {operation_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_business_operation(operation_name, status, duration)
        return wrapper
    return decorator


# 装饰器：跟踪 AI 调用

def track_ai_call(metrics: PrometheusMetrics, service: str, model: str):
    """装饰器：跟踪 AI 服务调用"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            prompt_tokens = 0
            completion_tokens = 0
            try:
                result = func(*args, **kwargs)
                # 尝试从结果中提取 token 信息
                if isinstance(result, dict):
                    prompt_tokens = result.get("usage", {}).get("prompt_tokens", 0)
                    completion_tokens = result.get("usage", {}).get("completion_tokens", 0)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"AI call to {service}/{model} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_ai_request(
                    service=service,
                    model=model,
                    status=status,
                    duration=duration,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens
                )
        return wrapper
    return decorator


# 全局实例
_global_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> Optional[PrometheusMetrics]:
    """获取全局指标实例"""
    return _global_metrics


def init_metrics(app: Flask, service_name: str = "api") -> PrometheusMetrics:
    """初始化全局指标"""
    global _global_metrics
    _global_metrics = PrometheusMetrics(app, service_name)
    return _global_metrics


# ==================== 八阶段生命周期指标扩展 ====================

class LifecycleMetrics:
    """
    八阶段数据生命周期专用指标

    阶段：
    1. metadata_scan - 元数据自动发现
    2. sensitivity_scan - 敏感数据识别
    3. etl_orchestration - ETL 编排
    4. lineage_sync - 血缘同步
    5. asset_catalog - 资产编目
    6. table_fusion - 表融合
    7. vector_index - 向量索引
    8. intelligent_query - 智能查询
    """

    def __init__(self, registry: CollectorRegistry = None):
        if not PROMETHEUS_AVAILABLE:
            self._initialized = False
            return

        self._initialized = True
        self.registry = registry or CollectorRegistry()

        # 阶段执行时间
        self._stage_duration_seconds = Histogram(
            "lifecycle_stage_duration_seconds",
            "Time spent in each lifecycle stage",
            ["stage", "operation"],
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
            registry=self.registry
        )

        # 阶段吞吐量
        self._stage_records_processed = Counter(
            "lifecycle_stage_records_processed_total",
            "Total records processed by each stage",
            ["stage", "status"],
            registry=self.registry
        )

        # 阶段错误率
        self._stage_errors_total = Counter(
            "lifecycle_stage_errors_total",
            "Total errors in each lifecycle stage",
            ["stage", "error_type"],
            registry=self.registry
        )

        # 阶段数据量
        self._stage_data_size_bytes = Gauge(
            "lifecycle_stage_data_size_bytes",
            "Data size processed by each stage",
            ["stage"],
            registry=self.registry
        )

        # Text-to-SQL 专用指标
        self._sql_generation_duration_seconds = Histogram(
            "sql_generation_duration_seconds",
            "Time to generate SQL from natural language",
            ["method"],
            buckets=(0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
            registry=self.registry
        )
        self._sql_validation_total = Counter(
            "sql_validation_total",
            "Total SQL validations performed",
            ["result"],  # allowed, blocked, modified
            registry=self.registry
        )
        self._sql_execution_duration_seconds = Histogram(
            "sql_execution_duration_seconds",
            "Time to execute validated SQL",
            ["database"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry
        )

        # RAG 检索专用指标
        self._rag_retrieval_duration_seconds = Histogram(
            "rag_retrieval_duration_seconds",
            "Time spent on RAG retrieval",
            ["method"],  # vector, keyword, hybrid
            buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0),
            registry=self.registry
        )
        self._rag_retrieval_relevance_score = Histogram(
            "rag_retrieval_relevance_score",
            "Relevance score of retrieved documents",
            ["source"],
            buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 1.0),
            registry=self.registry
        )
        self._rag_results_count = Histogram(
            "rag_results_count",
            "Number of results returned from RAG",
            ["query_type"],
            buckets=(1, 5, 10, 20, 50, 100),
            registry=self.registry
        )

        # Agent 工具调用指标
        self._agent_tool_duration_seconds = Histogram(
            "agent_tool_duration_seconds",
            "Time spent on agent tool execution",
            ["tool_name", "status"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        self._agent_tool_total = Counter(
            "agent_tool_total",
            "Total agent tool invocations",
            ["tool_name", "status"],
            registry=self.registry
        )
        self._agent_step_count = Histogram(
            "agent_step_count",
            "Number of steps taken by agent",
            ["agent_type"],
            buckets=(1, 3, 5, 10, 20, 50),
            registry=self.registry
        )

        # 数据脱敏指标
        self._data_masking_duration_seconds = Histogram(
            "data_masking_duration_seconds",
            "Time spent on data masking",
            ["strategy", "role"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5),
            registry=self.registry
        )
        self._data_masking_records_total = Counter(
            "data_masking_records_total",
            "Total records masked",
            ["role", "sensitivity_level"],
            registry=self.registry
        )
        self._data_masking_bytes_processed = Counter(
            "data_masking_bytes_processed_total",
            "Total bytes processed for masking",
            ["role"],
            registry=self.registry
        )

    # 八阶段通用方法

    def record_stage_start(self, stage: str, operation: str = "process"):
        """记录阶段开始（返回计时器）"""
        if not self._initialized:
            return None
        return StageTimer(self, stage, operation)

    def record_stage_complete(
        self,
        stage: str,
        operation: str,
        duration: float,
        record_count: int = 0,
        data_size_bytes: int = 0,
        success: bool = True,
    ):
        """记录阶段完成"""
        if not self._initialized:
            return

        self._stage_duration_seconds.labels(stage=stage, operation=operation).observe(duration)

        status = "success" if success else "error"
        self._stage_records_processed.labels(stage=stage, status=status).inc(record_count)

        if data_size_bytes > 0:
            self._stage_data_size_bytes.labels(stage=stage).set(data_size_bytes)

    def record_stage_error(self, stage: str, error_type: str):
        """记录阶段错误"""
        if not self._initialized:
            return
        self._stage_errors_total.labels(stage=stage, error_type=error_type).inc()

    # Text-to-SQL 方法

    def record_sql_generation(
        self,
        method: str,
        duration: float,
        success: bool = True,
    ):
        """记录 SQL 生成"""
        if not self._initialized:
            return
        self._sql_generation_duration_seconds.labels(method=method).observe(duration)

    def record_sql_validation(self, result: str):
        """
        记录 SQL 验证结果

        Args:
            result: "allowed", "blocked", "modified"
        """
        if not self._initialized:
            return
        self._sql_validation_total.labels(result=result).inc()

    def record_sql_execution(self, database: str, duration: float, row_count: int = 0):
        """记录 SQL 执行"""
        if not self._initialized:
            return
        self._sql_execution_duration_seconds.labels(database=database).observe(duration)

    # RAG 检索方法

    def record_rag_retrieval(
        self,
        method: str,
        duration: float,
        result_count: int,
        avg_relevance: float = 0,
    ):
        """记录 RAG 检索"""
        if not self._initialized:
            return

        self._rag_retrieval_duration_seconds.labels(method=method).observe(duration)
        self._rag_results_count.labels(query_type="default").observe(result_count)

        if avg_relevance > 0:
            self._rag_retrieval_relevance_score.labels(source="rag").observe(avg_relevance)

    # Agent 工具方法

    def record_agent_tool_call(
        self,
        tool_name: str,
        duration: float,
        status: str = "success",
    ):
        """记录 Agent 工具调用"""
        if not self._initialized:
            return

        self._agent_tool_duration_seconds.labels(tool_name=tool_name, status=status).observe(duration)
        self._agent_tool_total.labels(tool_name=tool_name, status=status).inc()

    def record_agent_completion(self, agent_type: str, step_count: int):
        """记录 Agent 完成步数"""
        if not self._initialized:
            return
        self._agent_step_count.labels(agent_type=agent_type).observe(step_count)

    # 数据脱敏方法

    def record_masking_operation(
        self,
        strategy: str,
        role: str,
        duration: float,
        record_count: int = 0,
        data_size_bytes: int = 0,
    ):
        """记录脱敏操作"""
        if not self._initialized:
            return

        self._data_masking_duration_seconds.labels(strategy=strategy, role=role).observe(duration)
        self._data_masking_records_total.labels(role=role, sensitivity_level="default").inc(record_count)
        self._data_masking_bytes_processed.labels(role=role).inc(data_size_bytes)


class StageTimer:
    """阶段计时器上下文管理器"""

    def __init__(self, metrics: LifecycleMetrics, stage: str, operation: str = "process"):
        self.metrics = metrics
        self.stage = stage
        self.operation = operation
        self.start_time = None
        self.record_count = 0
        self.data_size = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None

        self.metrics.record_stage_complete(
            stage=self.stage,
            operation=self.operation,
            duration=duration,
            record_count=self.record_count,
            data_size_bytes=self.data_size,
            success=success,
        )

        if exc_type is not None:
            self.metrics.record_stage_error(
                stage=self.stage,
                error_type=exc_type.__name__,
            )

    def set_record_count(self, count: int):
        """设置记录数"""
        self.record_count = count

    def set_data_size(self, size: int):
        """设置数据大小"""
        self.data_size = size


# ==================== SLO/SLI 指标 ====================

class SLOMetrics:
    """
    SLO (Service Level Objectives) 和 SLI (Service Level Indicators) 指标

    常见 SLO:
    - 可用性: 99.9% uptime
    - 延迟: P95 < 500ms
    - 错误率: < 0.1%
    - 吞吐量: > 1000 req/s
    """

    def __init__(self, registry: CollectorRegistry = None):
        if not PROMETHEUS_AVAILABLE:
            self._initialized = False
            return

        self._initialized = True
        self.registry = registry or CollectorRegistry()

        # SLO 指标
        self._slo_availability_uptime = Gauge(
            "slo_availability_uptime_ratio",
            "Service availability ratio (0-1)",
            ["service"],
            registry=self.registry
        )
        self._slo_latency_budget = Gauge(
            "slo_latency_budget_remaining",
            "Remaining latency budget (0-1)",
            ["service", "threshold"],  # p95, p99
            registry=self.registry
        )
        self._slo_error_budget = Gauge(
            "slo_error_budget_remaining",
            "Remaining error budget (0-1)",
            ["service"],
            registry=self.registry
        )
        self._slo_throughput = Gauge(
            "slo_throughput_requests_per_second",
            "Current throughput in requests per second",
            ["service"],
            registry=self.registry
        )

        # SLI 原始指标
        self._sli_requests_total = Counter(
            "sli_requests_total",
            "Total requests for SLO calculation",
            ["service", "status"],  # success, error
            registry=self.registry
        )
        self._sli_latency_seconds = Histogram(
            "sli_latency_seconds",
            "Request latency for SLO calculation",
            ["service"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        # 错误预算追踪
        self._error_budget_window = Counter(
            "slo_error_budget_events",
            "Events affecting error budget",
            ["service", "impact"],  # high, medium, low
            registry=self.registry
        )

    def record_request(self, service: str, success: bool, latency: float):
        """记录请求"""
        if not self._initialized:
            return

        status = "success" if success else "error"
        self._sli_requests_total.labels(service=service, status=status).inc()
        self._sli_latency_seconds.labels(service=service).observe(latency)

    def update_availability(self, service: str, ratio: float):
        """更新可用性"""
        if not self._initialized:
            return
        self._slo_availability_uptime.labels(service=service).set(ratio)

    def update_latency_budget(self, service: str, threshold: str, remaining: float):
        """更新延迟预算"""
        if not self._initialized:
            return
        self._slo_latency_budget.labels(service=service, threshold=threshold).set(remaining)

    def update_error_budget(self, service: str, remaining: float):
        """更新错误预算"""
        if not self._initialized:
            return
        self._slo_error_budget.labels(service=service).set(remaining)

    def record_error_budget_event(self, service: str, impact: str):
        """记录影响错误预算的事件"""
        if not self._initialized:
            return
        self._error_budget_window.labels(service=service, impact=impact).inc()

    def get_sli_summary(self, service: str) -> Dict[str, Any]:
        """
        获取 SLI 摘要

        注意：这是计算值，不是直接从 Prometheus 获取
        实际部署时应该使用 Prometheus 查询
        """
        return {
            "service": service,
            "availability_target": 0.999,
            "latency_target_p95_ms": 500,
            "latency_target_p99_ms": 1000,
            "error_rate_target": 0.001,
            "current_status": "unknown",
        }


# ==================== 熔断器指标 ====================

class CircuitBreakerMetrics:
    """
    熔断器模式指标

    用于保护外部服务调用，防止级联故障
    """

    def __init__(self, registry: CollectorRegistry = None):
        if not PROMETHEUS_AVAILABLE:
            self._initialized = False
            return

        self._initialized = True
        self.registry = registry or CollectorRegistry()

        self._circuit_state = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=half_open, 2=open)",
            ["service", "circuit"],
            registry=self.registry
        )
        self._circuit_requests_total = Counter(
            "circuit_breaker_requests_total",
            "Total requests through circuit breaker",
            ["service", "circuit", "result"],  # success, failure, rejected
            registry=self.registry
        )
        self._circuit_failure_count = Gauge(
            "circuit_breaker_failure_count",
            "Current consecutive failure count",
            ["service", "circuit"],
            registry=self.registry
        )
        self._circuit_last_state_change = Gauge(
            "circuit_breaker_last_state_change_timestamp",
            "Timestamp of last state change",
            ["service", "circuit"],
            registry=self.registry
        )

    def set_state(self, service: str, circuit: str, state: str):
        """
        设置熔断器状态

        Args:
            service: 服务名
            circuit: 熔断器名
            state: "closed", "half_open", "open"
        """
        if not self._initialized:
            return

        state_map = {"closed": 0, "half_open": 1, "open": 2}
        self._circuit_state.labels(service=service, circuit=circuit).set(state_map.get(state, 0))

    def record_request(self, service: str, circuit: str, result: str):
        """
        记录请求结果

        Args:
            result: "success", "failure", "rejected"
        """
        if not self._initialized:
            return
        self._circuit_requests_total.labels(
            service=service, circuit=circuit, result=result
        ).inc()

    def set_failure_count(self, service: str, circuit: str, count: int):
        """设置失败计数"""
        if not self._initialized:
            return
        self._circuit_failure_count.labels(service=service, circuit=circuit).set(count)

    def update_state_change_time(self, service: str, circuit: str):
        """更新状态变更时间"""
        if not self._initialized:
            return
        import time
        self._circuit_last_state_change.labels(
            service=service, circuit=circuit
        ).set(time.time())


# ==================== 健康检查增强 ====================

class HealthCheckMetrics:
    """
    增强健康检查指标

    支持多个健康检查项和依赖项检查
    """

    def __init__(self, registry: CollectorRegistry = None):
        if not PROMETHEUS_AVAILABLE:
            self._initialized = False
            return

        self._initialized = True
        self.registry = registry or CollectorRegistry()

        self._health_check_status = Gauge(
            "health_check_status",
            "Health check status (1=healthy, 0=unhealthy)",
            ["check_name"],
            registry=self.registry
        )
        self._health_check_duration_seconds = Gauge(
            "health_check_duration_seconds",
            "Health check execution time",
            ["check_name"],
            registry=self.registry
        )
        self._dependency_status = Gauge(
            "dependency_status",
            "Dependency health status (1=healthy, 0=unhealthy)",
            ["dependency_name", "dependency_type"],
            registry=self.registry
        )
        self._dependency_latency_seconds = Gauge(
            "dependency_latency_seconds",
            "Dependency response latency",
            ["dependency_name"],
            registry=self.registry
        )

    def set_health_status(self, check_name: str, healthy: bool, duration: float = None):
        """设置健康检查状态"""
        if not self._initialized:
            return

        self._health_check_status.labels(check_name=check_name).set(1 if healthy else 0)

        if duration is not None:
            self._health_check_duration_seconds.labels(check_name=check_name).set(duration)

    def set_dependency_status(
        self,
        dependency_name: str,
        dependency_type: str,
        healthy: bool,
        latency: float = None,
    ):
        """设置依赖状态"""
        if not self._initialized:
            return

        self._dependency_status.labels(
            dependency_name=dependency_name,
            dependency_type=dependency_type,
        ).set(1 if healthy else 0)

        if latency is not None:
            self._dependency_latency_seconds.labels(dependency_name=dependency_name).set(latency)


# ==================== 全局实例 ====================

_lifecycle_metrics: Optional[LifecycleMetrics] = None
_slo_metrics: Optional[SLOMetrics] = None
_circuit_breaker_metrics: Optional[CircuitBreakerMetrics] = None
_health_check_metrics: Optional[HealthCheckMetrics] = None


def get_lifecycle_metrics() -> Optional[LifecycleMetrics]:
    """获取生命周期指标实例"""
    global _lifecycle_metrics
    if _lifecycle_metrics is None:
        _lifecycle_metrics = LifecycleMetrics()
    return _lifecycle_metrics


def get_slo_metrics() -> Optional[SLOMetrics]:
    """获取 SLO 指标实例"""
    global _slo_metrics
    if _slo_metrics is None:
        _slo_metrics = SLOMetrics()
    return _slo_metrics


def get_circuit_breaker_metrics() -> Optional[CircuitBreakerMetrics]:
    """获取熔断器指标实例"""
    global _circuit_breaker_metrics
    if _circuit_breaker_metrics is None:
        _circuit_breaker_metrics = CircuitBreakerMetrics()
    return _circuit_breaker_metrics


def get_health_check_metrics() -> Optional[HealthCheckMetrics]:
    """获取健康检查指标实例"""
    global _health_check_metrics
    if _health_check_metrics is None:
        _health_check_metrics = HealthCheckMetrics()
    return _health_check_metrics


# ==================== 便捷装饰器 ====================

def track_lifecycle_stage(stage: str, operation: str = "process"):
    """
    装饰器：跟踪八阶段生命周期操作

    用法:
        @track_lifecycle_stage("metadata_scan", "scan_table")
        def scan_table(table_name):
            ...
    """
    lifecycle_metrics = get_lifecycle_metrics()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if lifecycle_metrics is None:
                return func(*args, **kwargs)

            with lifecycle_metrics.record_stage_start(stage, operation) as timer:
                result = func(*args, **kwargs)
                # 如果结果是列表或字典，尝试提取记录数
                if isinstance(result, list):
                    timer.set_record_count(len(result))
                elif isinstance(result, dict) and "count" in result:
                    timer.set_record_count(result["count"])
                return result
        return wrapper
    return decorator


def track_sql_generation(method: str = "llm"):
    """
    装饰器：跟踪 SQL 生成

    用法:
        @track_sql_generation("gpt-4")
        def generate_sql(question):
            ...
    """
    lifecycle_metrics = get_lifecycle_metrics()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if lifecycle_metrics is None:
                return func(*args, **kwargs)

            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                lifecycle_metrics.record_sql_generation(method, duration, success)
        return wrapper
    return decorator


def track_rag_retrieval(method: str = "hybrid"):
    """
    装饰器：跟踪 RAG 检索

    用法:
        @track_rag_retrieval("vector")
        def retrieve_documents(query):
            ...
    """
    lifecycle_metrics = get_lifecycle_metrics()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if lifecycle_metrics is None:
                return func(*args, **kwargs)

            start_time = time.time()
            try:
                results = func(*args, **kwargs)
                result_count = len(results) if isinstance(results, list) else 0

                duration = time.time() - start_time
                lifecycle_metrics.record_rag_retrieval(
                    method=method,
                    duration=duration,
                    result_count=result_count,
                )

                return results
            except Exception:
                duration = time.time() - start_time
                lifecycle_metrics.record_rag_retrieval(
                    method=method,
                    duration=duration,
                    result_count=0,
                )
                raise
        return wrapper
    return decorator


def track_agent_tool(tool_name: str):
    """
    装饰器：跟踪 Agent 工具调用

    用法:
        @track_agent_tool("sql_query")
        def execute_sql(query):
            ...
    """
    lifecycle_metrics = get_lifecycle_metrics()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if lifecycle_metrics is None:
                return func(*args, **kwargs)

            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                lifecycle_metrics.record_agent_tool_call(tool_name, duration, status)
        return wrapper
    return decorator

