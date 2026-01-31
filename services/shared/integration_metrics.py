"""
集成组件 Prometheus 指标模块
Phase 1-2 组件监控：Hop、ShardingSphere、Great Expectations、Label Studio、Ollama

提供统一的 Prometheus 指标收集功能：
- ETL 引擎指标（Hop/Kettle）
- 数据质量指标（Great Expectations）
- 数据标注指标（Label Studio）
- 透明脱敏指标（ShardingSphere）
- LLM 推理指标（Ollama/vLLM）
"""

import time
import logging
import functools
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# 尝试导入 prometheus_client
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Summary,
        CollectorRegistry,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available. Metrics will be disabled.")

    # 占位符类
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


class ETLEngine(str, Enum):
    """ETL 引擎类型"""
    KETTLE = "kettle"
    HOP = "hop"


class LLMBackend(str, Enum):
    """LLM 后端类型"""
    VLLM = "vllm"
    OLLAMA = "ollama"
    OPENAI = "openai"


@dataclass
class ETLMetrics:
    """ETL 指标数据"""
    engine: str
    pipeline_name: str
    duration_seconds: float
    rows_processed: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class QualityMetrics:
    """数据质量指标数据"""
    engine: str  # ge / builtin
    rule_type: str
    table_name: str
    duration_seconds: float
    rows_validated: int
    pass_count: int
    fail_count: int


@dataclass
class LabelingMetrics:
    """标注指标数据"""
    project_id: str
    task_count: int
    completed_count: int
    duration_seconds: float


@dataclass
class MaskingMetrics:
    """脱敏指标数据"""
    database: str
    table: str
    query_count: int
    duration_seconds: float


@dataclass
class LLMMetrics:
    """LLM 推理指标数据"""
    backend: str
    model: str
    duration_seconds: float
    input_tokens: int
    output_tokens: int
    success: bool


class IntegrationMetrics:
    """
    集成组件指标收集器

    用法:
        metrics = IntegrationMetrics(registry)
        metrics.record_etl_execution(ETLMetrics(...))
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry
        self._initialized = PROMETHEUS_AVAILABLE

        if not self._initialized:
            logger.warning("Integration metrics not available (prometheus_client not installed)")
            return

        # ==================== ETL 引擎指标 ====================
        self._etl_executions_total = Counter(
            "etl_executions_total",
            "Total ETL pipeline executions",
            ["engine", "pipeline", "status"],
            registry=registry
        )
        self._etl_execution_duration_seconds = Histogram(
            "etl_execution_duration_seconds",
            "ETL pipeline execution duration",
            ["engine", "pipeline"],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0),
            registry=registry
        )
        self._etl_rows_processed_total = Counter(
            "etl_rows_processed_total",
            "Total rows processed by ETL pipelines",
            ["engine", "pipeline"],
            registry=registry
        )
        self._etl_pipelines_active = Gauge(
            "etl_pipelines_active",
            "Number of currently active ETL pipelines",
            ["engine"],
            registry=registry
        )
        self._etl_engine_health = Gauge(
            "etl_engine_health",
            "ETL engine health status (1=healthy, 0=unhealthy)",
            ["engine"],
            registry=registry
        )

        # ==================== 数据质量指标 ====================
        self._quality_validations_total = Counter(
            "quality_validations_total",
            "Total data quality validations",
            ["engine", "rule_type", "status"],
            registry=registry
        )
        self._quality_validation_duration_seconds = Histogram(
            "quality_validation_duration_seconds",
            "Data quality validation duration",
            ["engine", "rule_type"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=registry
        )
        self._quality_rows_validated_total = Counter(
            "quality_rows_validated_total",
            "Total rows validated",
            ["engine", "table"],
            registry=registry
        )
        self._quality_pass_rate = Gauge(
            "quality_pass_rate",
            "Data quality pass rate (0-1)",
            ["table", "rule_type"],
            registry=registry
        )
        self._quality_expectation_count = Gauge(
            "quality_expectation_count",
            "Number of active quality expectations",
            ["engine"],
            registry=registry
        )

        # ==================== 数据标注指标 ====================
        self._labeling_tasks_total = Counter(
            "labeling_tasks_total",
            "Total labeling tasks created",
            ["project"],
            registry=registry
        )
        self._labeling_tasks_completed_total = Counter(
            "labeling_tasks_completed_total",
            "Total labeling tasks completed",
            ["project"],
            registry=registry
        )
        self._labeling_annotations_total = Counter(
            "labeling_annotations_total",
            "Total annotations submitted",
            ["project", "user"],
            registry=registry
        )
        self._labeling_task_duration_seconds = Histogram(
            "labeling_task_duration_seconds",
            "Time to complete labeling task",
            ["project"],
            buckets=(10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
            registry=registry
        )
        self._labeling_projects_active = Gauge(
            "labeling_projects_active",
            "Number of active labeling projects",
            registry=registry
        )
        self._labeling_tasks_pending = Gauge(
            "labeling_tasks_pending",
            "Number of pending labeling tasks",
            ["project"],
            registry=registry
        )

        # ==================== 透明脱敏指标 ====================
        self._masking_queries_total = Counter(
            "masking_queries_total",
            "Total queries through masking proxy",
            ["database", "table"],
            registry=registry
        )
        self._masking_query_duration_seconds = Histogram(
            "masking_query_duration_seconds",
            "Query duration through masking proxy",
            ["database"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=registry
        )
        self._masking_rules_active = Gauge(
            "masking_rules_active",
            "Number of active masking rules",
            ["database"],
            registry=registry
        )
        self._masking_columns_protected = Gauge(
            "masking_columns_protected",
            "Number of columns with masking rules",
            ["database", "table"],
            registry=registry
        )
        self._masking_proxy_health = Gauge(
            "masking_proxy_health",
            "Masking proxy health status (1=healthy, 0=unhealthy)",
            registry=registry
        )

        # ==================== LLM 推理指标 ====================
        self._llm_requests_total = Counter(
            "llm_requests_total",
            "Total LLM inference requests",
            ["backend", "model", "status"],
            registry=registry
        )
        self._llm_request_duration_seconds = Histogram(
            "llm_request_duration_seconds",
            "LLM inference request duration",
            ["backend", "model"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=registry
        )
        self._llm_tokens_total = Counter(
            "llm_tokens_total",
            "Total tokens processed",
            ["backend", "model", "direction"],  # direction: input/output
            registry=registry
        )
        self._llm_backend_health = Gauge(
            "llm_backend_health",
            "LLM backend health status (1=healthy, 0=unhealthy)",
            ["backend"],
            registry=registry
        )
        self._llm_queue_size = Gauge(
            "llm_queue_size",
            "Current LLM request queue size",
            ["backend"],
            registry=registry
        )

        logger.info("Integration metrics initialized")

    # ==================== ETL 方法 ====================

    def record_etl_execution(self, metrics: ETLMetrics):
        """记录 ETL 执行指标"""
        if not self._initialized:
            return

        status = "success" if metrics.success else "error"

        self._etl_executions_total.labels(
            engine=metrics.engine,
            pipeline=metrics.pipeline_name,
            status=status
        ).inc()

        self._etl_execution_duration_seconds.labels(
            engine=metrics.engine,
            pipeline=metrics.pipeline_name
        ).observe(metrics.duration_seconds)

        self._etl_rows_processed_total.labels(
            engine=metrics.engine,
            pipeline=metrics.pipeline_name
        ).inc(metrics.rows_processed)

    def set_etl_pipelines_active(self, engine: str, count: int):
        """设置活跃 Pipeline 数量"""
        if not self._initialized:
            return
        self._etl_pipelines_active.labels(engine=engine).set(count)

    def set_etl_engine_health(self, engine: str, healthy: bool):
        """设置 ETL 引擎健康状态"""
        if not self._initialized:
            return
        self._etl_engine_health.labels(engine=engine).set(1 if healthy else 0)

    # ==================== 数据质量方法 ====================

    def record_quality_validation(self, metrics: QualityMetrics):
        """记录数据质量校验指标"""
        if not self._initialized:
            return

        total = metrics.pass_count + metrics.fail_count
        status = "pass" if metrics.fail_count == 0 else "fail"

        self._quality_validations_total.labels(
            engine=metrics.engine,
            rule_type=metrics.rule_type,
            status=status
        ).inc()

        self._quality_validation_duration_seconds.labels(
            engine=metrics.engine,
            rule_type=metrics.rule_type
        ).observe(metrics.duration_seconds)

        self._quality_rows_validated_total.labels(
            engine=metrics.engine,
            table=metrics.table_name
        ).inc(metrics.rows_validated)

        if total > 0:
            pass_rate = metrics.pass_count / total
            self._quality_pass_rate.labels(
                table=metrics.table_name,
                rule_type=metrics.rule_type
            ).set(pass_rate)

    def set_quality_expectation_count(self, engine: str, count: int):
        """设置质量规则数量"""
        if not self._initialized:
            return
        self._quality_expectation_count.labels(engine=engine).set(count)

    # ==================== 数据标注方法 ====================

    def record_labeling_task_created(self, project: str, count: int = 1):
        """记录标注任务创建"""
        if not self._initialized:
            return
        self._labeling_tasks_total.labels(project=project).inc(count)

    def record_labeling_task_completed(self, project: str, duration_seconds: float):
        """记录标注任务完成"""
        if not self._initialized:
            return
        self._labeling_tasks_completed_total.labels(project=project).inc()
        self._labeling_task_duration_seconds.labels(project=project).observe(duration_seconds)

    def record_annotation_submitted(self, project: str, user: str):
        """记录标注提交"""
        if not self._initialized:
            return
        self._labeling_annotations_total.labels(project=project, user=user).inc()

    def set_labeling_projects_active(self, count: int):
        """设置活跃项目数"""
        if not self._initialized:
            return
        self._labeling_projects_active.set(count)

    def set_labeling_tasks_pending(self, project: str, count: int):
        """设置待处理任务数"""
        if not self._initialized:
            return
        self._labeling_tasks_pending.labels(project=project).set(count)

    # ==================== 透明脱敏方法 ====================

    def record_masking_query(self, database: str, table: str, duration_seconds: float):
        """记录脱敏查询"""
        if not self._initialized:
            return
        self._masking_queries_total.labels(database=database, table=table).inc()
        self._masking_query_duration_seconds.labels(database=database).observe(duration_seconds)

    def set_masking_rules_active(self, database: str, count: int):
        """设置活跃脱敏规则数"""
        if not self._initialized:
            return
        self._masking_rules_active.labels(database=database).set(count)

    def set_masking_columns_protected(self, database: str, table: str, count: int):
        """设置受保护列数"""
        if not self._initialized:
            return
        self._masking_columns_protected.labels(database=database, table=table).set(count)

    def set_masking_proxy_health(self, healthy: bool):
        """设置脱敏代理健康状态"""
        if not self._initialized:
            return
        self._masking_proxy_health.set(1 if healthy else 0)

    # ==================== LLM 推理方法 ====================

    def record_llm_request(self, metrics: LLMMetrics):
        """记录 LLM 推理请求"""
        if not self._initialized:
            return

        status = "success" if metrics.success else "error"

        self._llm_requests_total.labels(
            backend=metrics.backend,
            model=metrics.model,
            status=status
        ).inc()

        self._llm_request_duration_seconds.labels(
            backend=metrics.backend,
            model=metrics.model
        ).observe(metrics.duration_seconds)

        self._llm_tokens_total.labels(
            backend=metrics.backend,
            model=metrics.model,
            direction="input"
        ).inc(metrics.input_tokens)

        self._llm_tokens_total.labels(
            backend=metrics.backend,
            model=metrics.model,
            direction="output"
        ).inc(metrics.output_tokens)

    def set_llm_backend_health(self, backend: str, healthy: bool):
        """设置 LLM 后端健康状态"""
        if not self._initialized:
            return
        self._llm_backend_health.labels(backend=backend).set(1 if healthy else 0)

    def set_llm_queue_size(self, backend: str, size: int):
        """设置 LLM 请求队列大小"""
        if not self._initialized:
            return
        self._llm_queue_size.labels(backend=backend).set(size)


# ==================== 装饰器工具 ====================

def etl_metrics(metrics: IntegrationMetrics, engine: str, pipeline: str):
    """
    ETL 执行指标装饰器

    用法:
        @etl_metrics(metrics, "hop", "my_pipeline")
        def run_pipeline():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            rows = 0
            error_msg = None

            try:
                result = func(*args, **kwargs)
                # 尝试从结果中提取行数
                if isinstance(result, dict):
                    rows = result.get("rows_processed", 0)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_etl_execution(ETLMetrics(
                    engine=engine,
                    pipeline_name=pipeline,
                    duration_seconds=duration,
                    rows_processed=rows,
                    success=success,
                    error_message=error_msg
                ))

        return wrapper
    return decorator


def quality_metrics(metrics: IntegrationMetrics, engine: str, rule_type: str, table: str):
    """
    数据质量校验指标装饰器

    用法:
        @quality_metrics(metrics, "ge", "not_null", "users")
        def validate_data():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            pass_count = 0
            fail_count = 0
            rows = 0

            try:
                result = func(*args, **kwargs)
                # 尝试从结果中提取统计
                if isinstance(result, dict):
                    pass_count = result.get("pass_count", 0)
                    fail_count = result.get("fail_count", 0)
                    rows = result.get("rows_validated", 0)
                return result
            finally:
                duration = time.time() - start_time
                metrics.record_quality_validation(QualityMetrics(
                    engine=engine,
                    rule_type=rule_type,
                    table_name=table,
                    duration_seconds=duration,
                    rows_validated=rows,
                    pass_count=pass_count,
                    fail_count=fail_count
                ))

        return wrapper
    return decorator


def llm_metrics(metrics: IntegrationMetrics, backend: str, model: str):
    """
    LLM 推理指标装饰器

    用法:
        @llm_metrics(metrics, "ollama", "qwen2.5")
        def generate_text():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            input_tokens = 0
            output_tokens = 0

            try:
                result = func(*args, **kwargs)
                # 尝试从结果中提取 token 统计
                if isinstance(result, dict):
                    usage = result.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_llm_request(LLMMetrics(
                    backend=backend,
                    model=model,
                    duration_seconds=duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    success=success
                ))

        return wrapper
    return decorator


# ==================== 全局实例 ====================

_integration_metrics: Optional[IntegrationMetrics] = None


def get_integration_metrics(registry: Optional[CollectorRegistry] = None) -> IntegrationMetrics:
    """获取集成指标实例"""
    global _integration_metrics
    if _integration_metrics is None:
        _integration_metrics = IntegrationMetrics(registry)
    return _integration_metrics
