"""
OCR服务指标收集和导出服务
支持Prometheus格式的指标导出
"""

import time
import threading
from typing import Dict, Counter, Optional
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta


class Metrics:
    """指标收集器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # 计数器
        self._counters: Dict[str, int] = defaultdict(int)

        # 直方图 (值 -> 次数)
        self._histograms: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))

        # 仪表盘 (当前值)
        self._gauges: Dict[str, float] = {}

        # 摘要 (百分位数)
        self._summaries: Dict[str, list] = defaultdict(list)

        # 标签
        self._label_values: Dict[str, Dict[tuple, int]] = defaultdict(lambda: defaultdict(int))

        # 开始时间
        self._start_time = time.time()

    def inc(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def dec(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """减少计数器"""
        key = self._make_key(name, labels)
        self._counters[key] -= value

    def set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """观察直方图值"""
        key = self._make_key(name, labels)
        self._histograms[key][value] += 1

        # 同时添加到摘要
        self._summaries[key].append(value)

    def timing(self, name: str, labels: Optional[Dict[str, str]] = None):
        """计时装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.observe(name, time.time() - start, labels)
                    return result
                except Exception:
                    self.observe(f"{name}_errors", time.time() - start, labels)
                    raise

            return wrapper

        return decorator

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """创建带标签的键"""
        if not labels:
            return name

        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """获取计数器值"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """获取仪表盘值"""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    def get_histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[float, int]:
        """获取直方图"""
        key = self._make_key(name, labels)
        return dict(self._histograms.get(key, {}))

    def get_summary(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """获取摘要统计"""
        key = self._make_key(name, labels)
        values = self._summaries.get(key, [])

        if not values:
            return {}

        import statistics
        sorted_values = sorted(values)

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "p50": statistics.median(sorted_values),
            "p90": sorted_values[int(len(sorted_values) * 0.9)] if len(sorted_values) > 1 else sorted_values[0],
            "p95": sorted_values[int(len(sorted_values) * 0.95)] if len(sorted_values) > 1 else sorted_values[0],
            "p99": sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[0],
        }

    def export_prometheus(self) -> str:
        """导出Prometheus格式指标"""
        lines = []

        # 计数器
        for key, value in self._counters.items():
            safe_name = key.replace("-", "_").replace(" ", "_")
            lines.append(f"# TYPE {safe_name} counter")
            lines.append(f"{safe_name} {value}")

        # 仪表盘
        for key, value in self._gauges.items():
            safe_name = key.replace("-", "_").replace(" ", "_")
            lines.append(f"# TYPE {safe_name} gauge")
            lines.append(f"{safe_name} {value}")

        # 直方图
        for key, buckets in self._histograms.items():
            safe_name = key.replace("-", "_").replace(" ", "_")
            base_name = safe_name.split("{")[0]
            lines.append(f"# TYPE {base_name} histogram")

            total = sum(buckets.values())
            lines.append(f"{base_name}_count {total}")
            lines.append(f"{base_name}_sum {sum(v * c for v, c in buckets.items())}")

            # 计算bucket
            sorted_values = sorted(buckets.keys())
            cumulative = 0
            for value in sorted_values:
                cumulative += buckets[value]
                lines.append(f'{base_name}_bucket{{le="{value}"}} {cumulative}')

            lines.append(f'{base_name}_bucket{{le="+Inf"}} {total}')

        # 摘要
        for key in self._summaries.keys():
            safe_name = key.replace("-", "_").replace(" ", "_")
            base_name = safe_name.split("{")[0]
            summary = self.get_summary(key)

            if summary:
                lines.append(f"# TYPE {base_name} summary")
                lines.append(f"{base_name}_count {summary['count']}")
                lines.append(f"{base_name}_sum {summary['sum']}")
                lines.append(f'{base_name} {{quantile="0.5"}} {summary["p50"]}')
                lines.append(f'{base_name} {{quantile="0.9"}} {summary["p90"]}')
                lines.append(f'{base_name} {{quantile="0.95"}} {summary["p95"]}')
                lines.append(f'{base_name} {{quantile="0.99"}} {summary["p99"]}')

        # 运行时间
        uptime = time.time() - self._start_time
        lines.append(f"# TYPE ocr_service_uptime_seconds gauge")
        lines.append(f"ocr_service_uptime_seconds {uptime}")

        return "\n".join(lines)

    def export_json(self) -> Dict:
        """导出JSON格式指标"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self._start_time,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "summaries": {}
        }

        # 添加摘要
        for key in list(self._summaries.keys()):
            result["summaries"][key] = self.get_summary(key)

        return result

    def reset(self):
        """重置所有指标"""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()
        self._summaries.clear()


# 全局指标实例
metrics = Metrics()


# 任务相关指标
def track_task(document_type: str, status: str, processing_time: float):
    """跟踪任务指标"""
    metrics.inc("tasks_total", labels={"type": document_type, "status": status})
    metrics.observe("task_processing_seconds", processing_time, labels={"type": document_type})

    if status == "completed":
        metrics.inc("tasks_completed", labels={"type": document_type})
    elif status == "failed":
        metrics.inc("tasks_failed", labels={"type": document_type})


# 文档相关指标
def track_document(size: int, page_count: int):
    """跟踪文档指标"""
    metrics.observe("document_size_bytes", size)
    metrics.observe("document_page_count", page_count)


# 提取相关指标
def track_extraction(document_type: str, confidence: float, field_count: int, table_count: int):
    """跟踪提取指标"""
    metrics.set("extraction_confidence", confidence, labels={"type": document_type})
    metrics.set("extraction_fields_count", field_count, labels={"type": document_type})
    metrics.set("extraction_tables_count", table_count, labels={"type": document_type})


# 验证相关指标
def track_validation(is_valid: bool, has_errors: bool, has_warnings: bool):
    """跟踪验证指标"""
    metrics.inc("validation_total", labels={"valid": str(is_valid)})
    if has_errors:
        metrics.inc("validation_errors_total")
    if has_warnings:
        metrics.inc("validation_warnings_total")


# 系统相关指标
def track_system(memory_usage: float, cpu_usage: float, queue_size: int):
    """跟踪系统指标"""
    metrics.set("system_memory_usage_percent", memory_usage)
    metrics.set("system_cpu_usage_percent", cpu_usage)
    metrics.set("system_queue_size", queue_size)


def get_metrics_summary() -> Dict:
    """获取指标摘要"""
    return {
        "tasks": {
            "total": metrics.get_counter("tasks_total"),
            "completed": metrics.get_counter("tasks_completed"),
            "failed": metrics.get_counter("tasks_failed"),
            "processing_time": metrics.get_summary("task_processing_seconds")
        },
        "extraction": {
            "avg_confidence": metrics.get_gauge("extraction_confidence"),
            "avg_fields": metrics.get_gauge("extraction_fields_count"),
            "avg_tables": metrics.get_gauge("extraction_tables_count")
        },
        "validation": {
            "total": metrics.get_counter("validation_total"),
            "errors": metrics.get_counter("validation_errors_total"),
            "warnings": metrics.get_counter("validation_warnings_total")
        },
        "system": {
            "uptime": time.time() - metrics._start_time,
            "memory_usage": metrics.get_gauge("system_memory_usage_percent"),
            "queue_size": metrics.get_gauge("system_queue_size")
        }
    }
