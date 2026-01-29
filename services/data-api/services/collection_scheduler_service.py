"""
采集任务智能调度增强服务
基于数据源变化率、业务优先级和资源感知的智能调度
"""

import logging
import secrets
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import heapq
import statistics

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class CollectionType(str, Enum):
    """采集类型"""
    FULL = "full"                    # 全量采集
    INCREMENTAL = "incremental"      # 增量采集
    CDC = "cdc"                      # CDC 变更数据采集
    STREAMING = "streaming"          # 流式采集


class SourceType(str, Enum):
    """数据源类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    MONGODB = "mongodb"
    KAFKA = "kafka"
    API = "api"
    FILE = "file"
    FTP = "ftp"
    HDFS = "hdfs"
    S3 = "s3"


class CollectionStatus(str, Enum):
    """采集状态"""
    IDLE = "idle"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleStrategy(str, Enum):
    """调度策略"""
    FIXED_INTERVAL = "fixed_interval"          # 固定间隔
    ADAPTIVE = "adaptive"                       # 自适应（根据变化率）
    EVENT_DRIVEN = "event_driven"               # 事件驱动
    PRIORITY_BASED = "priority_based"           # 优先级驱动
    RESOURCE_AWARE = "resource_aware"           # 资源感知


class BusinessPriority(str, Enum):
    """业务优先级"""
    CRITICAL = "critical"      # 关键业务
    HIGH = "high"              # 高优先级
    NORMAL = "normal"          # 普通
    LOW = "low"                # 低优先级
    BACKGROUND = "background"  # 后台任务


# ==================== 数据类定义 ====================

@dataclass
class ChangeRateMetrics:
    """数据变化率指标"""
    source_id: str
    table_name: str
    avg_changes_per_minute: float = 0.0
    peak_changes_per_minute: float = 0.0
    change_rate_variance: float = 0.0
    last_change_count: int = 0
    last_measurement_time: Optional[datetime] = None
    measurement_window_minutes: int = 60
    trend: str = "stable"  # increasing, decreasing, stable, volatile

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "table_name": self.table_name,
            "avg_changes_per_minute": self.avg_changes_per_minute,
            "peak_changes_per_minute": self.peak_changes_per_minute,
            "change_rate_variance": self.change_rate_variance,
            "last_change_count": self.last_change_count,
            "last_measurement_time": self.last_measurement_time.isoformat() if self.last_measurement_time else None,
            "measurement_window_minutes": self.measurement_window_minutes,
            "trend": self.trend,
        }


@dataclass
class CollectionTaskConfig:
    """采集任务配置"""
    task_id: str
    name: str
    description: str = ""
    source_type: SourceType = SourceType.MYSQL
    collection_type: CollectionType = CollectionType.INCREMENTAL

    # 数据源连接
    connection_config: Dict[str, Any] = field(default_factory=dict)

    # 采集范围
    database: str = ""
    schema: str = ""
    tables: List[str] = field(default_factory=list)
    query: str = ""  # 自定义查询

    # 调度配置
    schedule_strategy: ScheduleStrategy = ScheduleStrategy.ADAPTIVE
    base_interval_seconds: int = 300  # 基础间隔（秒）
    min_interval_seconds: int = 60    # 最小间隔
    max_interval_seconds: int = 3600  # 最大间隔

    # 优先级
    business_priority: BusinessPriority = BusinessPriority.NORMAL
    priority_score: float = 500.0

    # 资源限制
    max_concurrent_tables: int = 4
    batch_size: int = 10000
    memory_limit_mb: int = 1024

    # 依赖
    depends_on: List[str] = field(default_factory=list)

    # 元数据
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type.value,
            "collection_type": self.collection_type.value,
            "database": self.database,
            "schema": self.schema,
            "tables": self.tables,
            "schedule_strategy": self.schedule_strategy.value,
            "base_interval_seconds": self.base_interval_seconds,
            "min_interval_seconds": self.min_interval_seconds,
            "max_interval_seconds": self.max_interval_seconds,
            "business_priority": self.business_priority.value,
            "priority_score": self.priority_score,
            "max_concurrent_tables": self.max_concurrent_tables,
            "batch_size": self.batch_size,
            "memory_limit_mb": self.memory_limit_mb,
            "depends_on": self.depends_on,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class CollectionExecution:
    """采集执行记录"""
    execution_id: str
    task_id: str
    status: CollectionStatus = CollectionStatus.SCHEDULED
    scheduled_time: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 执行结果
    rows_collected: int = 0
    bytes_transferred: int = 0
    tables_processed: int = 0
    errors: List[str] = field(default_factory=list)

    # 性能指标
    duration_ms: int = 0
    avg_throughput_rows_per_sec: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rows_collected": self.rows_collected,
            "bytes_transferred": self.bytes_transferred,
            "tables_processed": self.tables_processed,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "avg_throughput_rows_per_sec": self.avg_throughput_rows_per_sec,
        }


@dataclass
class ScheduleDecision:
    """调度决策"""
    task_id: str
    next_run_time: datetime
    adjusted_interval_seconds: int
    priority_score: float
    decision_factors: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "next_run_time": self.next_run_time.isoformat(),
            "adjusted_interval_seconds": self.adjusted_interval_seconds,
            "priority_score": self.priority_score,
            "decision_factors": self.decision_factors,
            "recommendations": self.recommendations,
        }


@dataclass
class ResourceSnapshot:
    """资源快照"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    network_bandwidth_mbps: float = 0.0
    active_connections: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "active_connections": self.active_connections,
            "pending_tasks": self.pending_tasks,
            "running_tasks": self.running_tasks,
        }


# ==================== 变化率分析器 ====================

class ChangeRateAnalyzer:
    """数据变化率分析器"""

    def __init__(self):
        self._metrics: Dict[str, List[ChangeRateMetrics]] = defaultdict(list)
        self._history_limit = 100  # 保留最近100条记录

    def record_change_count(
        self,
        source_id: str,
        table_name: str,
        change_count: int,
        measurement_time: datetime = None,
    ) -> ChangeRateMetrics:
        """记录变更计数"""
        if measurement_time is None:
            measurement_time = datetime.now()

        key = f"{source_id}:{table_name}"
        history = self._metrics[key]

        # 计算变化率
        avg_changes = 0.0
        peak_changes = 0.0
        variance = 0.0
        trend = "stable"

        if history:
            # 获取最近的记录用于计算
            recent_records = history[-20:]
            changes = [r.last_change_count for r in recent_records]

            avg_changes = statistics.mean(changes) if changes else 0
            peak_changes = max(changes) if changes else 0

            if len(changes) >= 2:
                variance = statistics.variance(changes)

                # 计算趋势
                if len(changes) >= 5:
                    recent_avg = statistics.mean(changes[-5:])
                    older_avg = statistics.mean(changes[:-5]) if len(changes) > 5 else avg_changes

                    if recent_avg > older_avg * 1.2:
                        trend = "increasing"
                    elif recent_avg < older_avg * 0.8:
                        trend = "decreasing"
                    elif variance > avg_changes * 0.5:
                        trend = "volatile"

        metrics = ChangeRateMetrics(
            source_id=source_id,
            table_name=table_name,
            avg_changes_per_minute=avg_changes,
            peak_changes_per_minute=peak_changes,
            change_rate_variance=variance,
            last_change_count=change_count,
            last_measurement_time=measurement_time,
            trend=trend,
        )

        # 保存记录
        history.append(metrics)
        if len(history) > self._history_limit:
            history.pop(0)

        return metrics

    def get_metrics(self, source_id: str, table_name: str) -> Optional[ChangeRateMetrics]:
        """获取最新指标"""
        key = f"{source_id}:{table_name}"
        history = self._metrics.get(key, [])
        return history[-1] if history else None

    def get_optimal_interval(
        self,
        source_id: str,
        table_name: str,
        min_interval: int,
        max_interval: int,
        base_interval: int,
    ) -> int:
        """根据变化率计算最优采集间隔"""
        metrics = self.get_metrics(source_id, table_name)

        if not metrics:
            return base_interval

        # 基于变化率调整
        if metrics.avg_changes_per_minute > 100:
            # 高变化率，缩短间隔
            factor = 0.5
        elif metrics.avg_changes_per_minute > 10:
            # 中等变化率
            factor = 0.8
        elif metrics.avg_changes_per_minute > 1:
            # 低变化率
            factor = 1.0
        else:
            # 极低变化率，延长间隔
            factor = 2.0

        # 根据趋势调整
        if metrics.trend == "increasing":
            factor *= 0.8  # 变化加速，缩短间隔
        elif metrics.trend == "decreasing":
            factor *= 1.2  # 变化减缓，延长间隔
        elif metrics.trend == "volatile":
            factor *= 0.7  # 波动大，缩短间隔以捕获变化

        optimal_interval = int(base_interval * factor)

        return max(min_interval, min(max_interval, optimal_interval))


# ==================== 优先级计算器 ====================

class PriorityCalculator:
    """优先级计算器"""

    # 业务优先级权重
    PRIORITY_WEIGHTS = {
        BusinessPriority.CRITICAL: 1000,
        BusinessPriority.HIGH: 750,
        BusinessPriority.NORMAL: 500,
        BusinessPriority.LOW: 250,
        BusinessPriority.BACKGROUND: 100,
    }

    @staticmethod
    def calculate_priority_score(
        task: CollectionTaskConfig,
        change_metrics: Optional[ChangeRateMetrics] = None,
        last_execution: Optional[CollectionExecution] = None,
        resource_snapshot: Optional[ResourceSnapshot] = None,
    ) -> float:
        """
        计算采集任务优先级分数

        考虑因素：
        1. 业务优先级
        2. 数据变化率
        3. 上次执行时间
        4. 依赖关系
        5. 资源可用性
        """
        score = 0.0

        # 1. 业务优先级基础分
        score += PriorityCalculator.PRIORITY_WEIGHTS.get(
            task.business_priority, 500
        )

        # 2. 数据变化率因子
        if change_metrics:
            # 变化率越高，优先级越高
            if change_metrics.avg_changes_per_minute > 100:
                score += 300
            elif change_metrics.avg_changes_per_minute > 10:
                score += 150
            elif change_metrics.avg_changes_per_minute > 1:
                score += 50

            # 趋势加成
            if change_metrics.trend == "increasing":
                score += 100
            elif change_metrics.trend == "volatile":
                score += 50

        # 3. 上次执行时间因子
        if last_execution and last_execution.completed_at:
            elapsed_seconds = (datetime.now() - last_execution.completed_at).total_seconds()
            overdue_ratio = elapsed_seconds / task.base_interval_seconds

            if overdue_ratio > 2:
                score += 200  # 严重超期
            elif overdue_ratio > 1.5:
                score += 100  # 超期
            elif overdue_ratio > 1:
                score += 50   # 接近超期

            # 上次执行失败，提高优先级以重试
            if last_execution.status == CollectionStatus.FAILED:
                score += 100

        # 4. 依赖因子（依赖越少越好）
        score -= len(task.depends_on) * 20

        # 5. 资源感知调整
        if resource_snapshot:
            # 资源紧张时，降低大资源任务的优先级
            if resource_snapshot.cpu_usage_percent > 80:
                if task.memory_limit_mb > 2048:
                    score -= 100
            if resource_snapshot.memory_usage_percent > 80:
                if task.memory_limit_mb > 2048:
                    score -= 100

        return max(0, score)


# ==================== 智能调度器 ====================

class CollectionScheduler:
    """采集任务智能调度器"""

    def __init__(self):
        self._tasks: Dict[str, CollectionTaskConfig] = {}
        self._executions: Dict[str, List[CollectionExecution]] = defaultdict(list)
        self._schedule_queue: List[tuple] = []  # (next_run_time, task_id)

        self._change_analyzer = ChangeRateAnalyzer()
        self._resource_snapshot = ResourceSnapshot()

        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._execution_handlers: List[Callable[[CollectionTaskConfig], None]] = []

        # 统计
        self._stats = {
            "total_scheduled": 0,
            "total_executed": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "total_skipped": 0,
        }

        # 初始化示例任务
        self._init_sample_tasks()

    def _init_sample_tasks(self):
        """初始化示例任务"""
        sample_tasks = [
            CollectionTaskConfig(
                task_id="collect_001",
                name="用户表实时同步",
                description="实时同步用户基础数据",
                source_type=SourceType.MYSQL,
                collection_type=CollectionType.CDC,
                database="production",
                tables=["users", "user_profiles"],
                schedule_strategy=ScheduleStrategy.ADAPTIVE,
                base_interval_seconds=60,
                min_interval_seconds=30,
                max_interval_seconds=300,
                business_priority=BusinessPriority.CRITICAL,
                created_by="system",
                tags=["user", "realtime", "critical"],
            ),
            CollectionTaskConfig(
                task_id="collect_002",
                name="订单数据增量同步",
                description="增量同步订单相关数据",
                source_type=SourceType.MYSQL,
                collection_type=CollectionType.INCREMENTAL,
                database="production",
                tables=["orders", "order_items", "payments"],
                schedule_strategy=ScheduleStrategy.ADAPTIVE,
                base_interval_seconds=300,
                min_interval_seconds=60,
                max_interval_seconds=900,
                business_priority=BusinessPriority.HIGH,
                depends_on=["collect_001"],
                created_by="system",
                tags=["order", "incremental"],
            ),
            CollectionTaskConfig(
                task_id="collect_003",
                name="日志数据采集",
                description="采集应用日志数据",
                source_type=SourceType.KAFKA,
                collection_type=CollectionType.STREAMING,
                schedule_strategy=ScheduleStrategy.EVENT_DRIVEN,
                base_interval_seconds=10,
                business_priority=BusinessPriority.NORMAL,
                created_by="system",
                tags=["log", "streaming"],
            ),
            CollectionTaskConfig(
                task_id="collect_004",
                name="报表数据全量同步",
                description="每日全量同步报表数据",
                source_type=SourceType.POSTGRESQL,
                collection_type=CollectionType.FULL,
                database="analytics",
                tables=["daily_reports", "weekly_summaries"],
                schedule_strategy=ScheduleStrategy.FIXED_INTERVAL,
                base_interval_seconds=86400,  # 每天
                business_priority=BusinessPriority.LOW,
                created_by="system",
                tags=["report", "daily", "full"],
            ),
        ]

        for task in sample_tasks:
            self._tasks[task.task_id] = task
            self._schedule_task(task)

    # ==================== 任务管理 ====================

    def create_task(
        self,
        name: str,
        source_type: SourceType,
        collection_type: CollectionType,
        database: str = "",
        tables: List[str] = None,
        schedule_strategy: ScheduleStrategy = ScheduleStrategy.ADAPTIVE,
        base_interval_seconds: int = 300,
        business_priority: BusinessPriority = BusinessPriority.NORMAL,
        connection_config: Dict[str, Any] = None,
        created_by: str = "",
        **kwargs,
    ) -> CollectionTaskConfig:
        """创建采集任务"""
        task = CollectionTaskConfig(
            task_id=f"collect_{secrets.token_hex(8)}",
            name=name,
            source_type=source_type,
            collection_type=collection_type,
            database=database,
            tables=tables or [],
            schedule_strategy=schedule_strategy,
            base_interval_seconds=base_interval_seconds,
            business_priority=business_priority,
            connection_config=connection_config or {},
            created_by=created_by,
            **kwargs,
        )

        self._tasks[task.task_id] = task
        self._schedule_task(task)
        self._stats["total_scheduled"] += 1

        logger.info(f"创建采集任务: {task.task_id} - {name}")
        return task

    def get_task(self, task_id: str) -> Optional[CollectionTaskConfig]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        source_type: SourceType = None,
        collection_type: CollectionType = None,
        business_priority: BusinessPriority = None,
        tags: List[str] = None,
        limit: int = 100,
    ) -> List[CollectionTaskConfig]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if source_type:
            tasks = [t for t in tasks if t.source_type == source_type]
        if collection_type:
            tasks = [t for t in tasks if t.collection_type == collection_type]
        if business_priority:
            tasks = [t for t in tasks if t.business_priority == business_priority]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

        # 按优先级排序
        tasks.sort(key=lambda t: t.priority_score, reverse=True)

        return tasks[:limit]

    def update_task(
        self,
        task_id: str,
        **updates
    ) -> Optional[CollectionTaskConfig]:
        """更新任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                if key == "source_type" and isinstance(value, str):
                    value = SourceType(value)
                elif key == "collection_type" and isinstance(value, str):
                    value = CollectionType(value)
                elif key == "schedule_strategy" and isinstance(value, str):
                    value = ScheduleStrategy(value)
                elif key == "business_priority" and isinstance(value, str):
                    value = BusinessPriority(value)
                setattr(task, key, value)

        # 重新调度
        self._reschedule_task(task)

        return task

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._executions.pop(task_id, None)
            return True
        return False

    # ==================== 调度管理 ====================

    def _schedule_task(self, task: CollectionTaskConfig):
        """调度任务"""
        decision = self._make_schedule_decision(task)
        heapq.heappush(
            self._schedule_queue,
            (decision.next_run_time, task.task_id)
        )
        task.priority_score = decision.priority_score

    def _reschedule_task(self, task: CollectionTaskConfig):
        """重新调度任务"""
        # 从队列中移除旧的调度
        self._schedule_queue = [
            (t, tid) for t, tid in self._schedule_queue
            if tid != task.task_id
        ]
        heapq.heapify(self._schedule_queue)

        # 重新调度
        self._schedule_task(task)

    def _make_schedule_decision(
        self,
        task: CollectionTaskConfig,
    ) -> ScheduleDecision:
        """做出调度决策"""
        now = datetime.now()
        recommendations = []
        factors = {}

        # 获取变化率指标
        change_metrics = None
        if task.tables:
            change_metrics = self._change_analyzer.get_metrics(
                task.task_id, task.tables[0]
            )
            if change_metrics:
                factors["change_rate"] = change_metrics.avg_changes_per_minute
                factors["change_trend"] = change_metrics.trend

        # 获取上次执行记录
        last_execution = None
        executions = self._executions.get(task.task_id, [])
        if executions:
            last_execution = executions[-1]
            factors["last_execution_status"] = last_execution.status.value
            factors["last_execution_time"] = last_execution.completed_at.isoformat() if last_execution.completed_at else None

        # 计算优先级
        priority_score = PriorityCalculator.calculate_priority_score(
            task, change_metrics, last_execution, self._resource_snapshot
        )
        factors["priority_score"] = priority_score

        # 根据策略计算下次运行时间
        if task.schedule_strategy == ScheduleStrategy.FIXED_INTERVAL:
            adjusted_interval = task.base_interval_seconds

        elif task.schedule_strategy == ScheduleStrategy.ADAPTIVE:
            # 自适应调度：根据变化率调整间隔
            if task.tables and change_metrics:
                adjusted_interval = self._change_analyzer.get_optimal_interval(
                    task.task_id,
                    task.tables[0],
                    task.min_interval_seconds,
                    task.max_interval_seconds,
                    task.base_interval_seconds,
                )
                if adjusted_interval < task.base_interval_seconds:
                    recommendations.append(
                        f"检测到数据变化加速（{change_metrics.avg_changes_per_minute:.1f}/分钟），"
                        f"建议缩短采集间隔至 {adjusted_interval} 秒"
                    )
                elif adjusted_interval > task.base_interval_seconds:
                    recommendations.append(
                        f"数据变化平稳，延长采集间隔至 {adjusted_interval} 秒以节约资源"
                    )
            else:
                adjusted_interval = task.base_interval_seconds

        elif task.schedule_strategy == ScheduleStrategy.PRIORITY_BASED:
            # 优先级驱动：高优先级任务更频繁执行
            priority_factor = priority_score / 500  # 归一化
            adjusted_interval = int(task.base_interval_seconds / max(0.5, priority_factor))
            adjusted_interval = max(
                task.min_interval_seconds,
                min(task.max_interval_seconds, adjusted_interval)
            )

        elif task.schedule_strategy == ScheduleStrategy.RESOURCE_AWARE:
            # 资源感知：根据资源使用率调整
            adjusted_interval = task.base_interval_seconds
            if self._resource_snapshot.cpu_usage_percent > 80:
                adjusted_interval = int(adjusted_interval * 1.5)
                recommendations.append("CPU 使用率较高，适当延长采集间隔")
            if self._resource_snapshot.memory_usage_percent > 80:
                adjusted_interval = int(adjusted_interval * 1.5)
                recommendations.append("内存使用率较高，适当延长采集间隔")
            adjusted_interval = max(
                task.min_interval_seconds,
                min(task.max_interval_seconds, adjusted_interval)
            )

        elif task.schedule_strategy == ScheduleStrategy.EVENT_DRIVEN:
            # 事件驱动：最小间隔（由事件触发）
            adjusted_interval = task.min_interval_seconds

        else:
            adjusted_interval = task.base_interval_seconds

        factors["adjusted_interval_seconds"] = adjusted_interval

        # 计算下次运行时间
        if last_execution and last_execution.completed_at:
            next_run_time = last_execution.completed_at + timedelta(seconds=adjusted_interval)
            if next_run_time < now:
                next_run_time = now + timedelta(seconds=10)  # 立即执行
                recommendations.append("任务已超期，建议立即执行")
        else:
            next_run_time = now + timedelta(seconds=10)  # 首次执行

        return ScheduleDecision(
            task_id=task.task_id,
            next_run_time=next_run_time,
            adjusted_interval_seconds=adjusted_interval,
            priority_score=priority_score,
            decision_factors=factors,
            recommendations=recommendations,
        )

    def get_schedule_decision(self, task_id: str) -> Optional[ScheduleDecision]:
        """获取任务的调度决策"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return self._make_schedule_decision(task)

    def get_next_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取即将执行的任务"""
        result = []
        now = datetime.now()

        # 复制队列以避免修改
        temp_queue = list(self._schedule_queue)
        heapq.heapify(temp_queue)

        while temp_queue and len(result) < limit:
            next_time, task_id = heapq.heappop(temp_queue)
            task = self._tasks.get(task_id)
            if task:
                result.append({
                    "task_id": task_id,
                    "name": task.name,
                    "next_run_time": next_time.isoformat(),
                    "seconds_until_run": (next_time - now).total_seconds(),
                    "priority_score": task.priority_score,
                    "business_priority": task.business_priority.value,
                })

        return result

    # ==================== 执行管理 ====================

    def start_scheduler(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="collection-scheduler",
        )
        self._scheduler_thread.start()
        logger.info("采集调度器已启动")

    def stop_scheduler(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("采集调度器已停止")

    def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                now = datetime.now()

                while self._schedule_queue:
                    next_time, task_id = self._schedule_queue[0]

                    if next_time > now:
                        break

                    heapq.heappop(self._schedule_queue)
                    task = self._tasks.get(task_id)

                    if task:
                        # 检查依赖
                        if self._check_dependencies(task):
                            self._execute_task(task)
                        else:
                            # 依赖未满足，延迟执行
                            new_time = now + timedelta(seconds=30)
                            heapq.heappush(self._schedule_queue, (new_time, task_id))
                            self._stats["total_skipped"] += 1

                time.sleep(1)

            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                time.sleep(5)

    def _check_dependencies(self, task: CollectionTaskConfig) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.depends_on:
            dep_executions = self._executions.get(dep_id, [])
            if not dep_executions:
                return False

            last_dep = dep_executions[-1]
            if last_dep.status != CollectionStatus.COMPLETED:
                return False

            # 检查依赖任务是否在本轮中已执行
            if last_dep.completed_at:
                elapsed = (datetime.now() - last_dep.completed_at).total_seconds()
                dep_task = self._tasks.get(dep_id)
                if dep_task and elapsed > dep_task.base_interval_seconds:
                    return False

        return True

    def _execute_task(self, task: CollectionTaskConfig):
        """执行任务"""
        execution = CollectionExecution(
            execution_id=f"exec_{secrets.token_hex(8)}",
            task_id=task.task_id,
            status=CollectionStatus.RUNNING,
            started_at=datetime.now(),
        )

        try:
            logger.info(f"开始执行采集任务: {task.task_id} - {task.name}")
            self._stats["total_executed"] += 1

            # 调用执行处理器
            for handler in self._execution_handlers:
                try:
                    handler(task)
                except Exception as e:
                    logger.error(f"执行处理器异常: {e}")

            # 模拟执行（实际应调用 CDC 服务或数据采集器）
            # 这里只是标记完成
            execution.status = CollectionStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

            # 模拟一些结果
            execution.rows_collected = 1000
            execution.tables_processed = len(task.tables)

            self._stats["total_succeeded"] += 1

        except Exception as e:
            execution.status = CollectionStatus.FAILED
            execution.completed_at = datetime.now()
            execution.errors.append(str(e))
            self._stats["total_failed"] += 1
            logger.error(f"采集任务执行失败: {task.task_id} - {e}")

        # 保存执行记录
        self._executions[task.task_id].append(execution)
        if len(self._executions[task.task_id]) > 100:
            self._executions[task.task_id].pop(0)

        # 重新调度
        self._schedule_task(task)

    def trigger_task(self, task_id: str) -> Optional[CollectionExecution]:
        """手动触发任务执行"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        execution = CollectionExecution(
            execution_id=f"exec_{secrets.token_hex(8)}",
            task_id=task_id,
            status=CollectionStatus.RUNNING,
            started_at=datetime.now(),
        )

        self._execute_task(task)

        executions = self._executions.get(task_id, [])
        return executions[-1] if executions else None

    def register_execution_handler(
        self,
        handler: Callable[[CollectionTaskConfig], None],
    ):
        """注册执行处理器"""
        self._execution_handlers.append(handler)

    # ==================== 变化率记录 ====================

    def record_change_count(
        self,
        task_id: str,
        table_name: str,
        change_count: int,
    ) -> Optional[ChangeRateMetrics]:
        """记录数据变化计数（供 CDC 服务调用）"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        metrics = self._change_analyzer.record_change_count(
            task_id, table_name, change_count
        )

        # 如果是自适应调度，根据变化率调整
        if task.schedule_strategy == ScheduleStrategy.ADAPTIVE:
            self._reschedule_task(task)

        return metrics

    def get_change_metrics(
        self,
        task_id: str,
        table_name: str,
    ) -> Optional[ChangeRateMetrics]:
        """获取变化率指标"""
        return self._change_analyzer.get_metrics(task_id, table_name)

    # ==================== 资源快照 ====================

    def update_resource_snapshot(
        self,
        cpu_usage: float = None,
        memory_usage: float = None,
        network_bandwidth: float = None,
        active_connections: int = None,
    ):
        """更新资源快照"""
        self._resource_snapshot.timestamp = datetime.now()

        if cpu_usage is not None:
            self._resource_snapshot.cpu_usage_percent = cpu_usage
        if memory_usage is not None:
            self._resource_snapshot.memory_usage_percent = memory_usage
        if network_bandwidth is not None:
            self._resource_snapshot.network_bandwidth_mbps = network_bandwidth
        if active_connections is not None:
            self._resource_snapshot.active_connections = active_connections

        self._resource_snapshot.pending_tasks = len([
            1 for _, tid in self._schedule_queue
            if tid in self._tasks
        ])
        self._resource_snapshot.running_tasks = len([
            1 for execs in self._executions.values()
            if execs and execs[-1].status == CollectionStatus.RUNNING
        ])

    def get_resource_snapshot(self) -> ResourceSnapshot:
        """获取资源快照"""
        return self._resource_snapshot

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts: Dict[str, int] = defaultdict(int)
        for task in self._tasks.values():
            execs = self._executions.get(task.task_id, [])
            if execs:
                status_counts[execs[-1].status.value] += 1
            else:
                status_counts["pending"] += 1

        return {
            "total_tasks": len(self._tasks),
            "status_counts": dict(status_counts),
            "queue_length": len(self._schedule_queue),
            "scheduling_stats": self._stats.copy(),
            "resource_snapshot": self._resource_snapshot.to_dict(),
            "tasks_by_priority": {
                priority.value: len([
                    t for t in self._tasks.values()
                    if t.business_priority == priority
                ])
                for priority in BusinessPriority
            },
            "tasks_by_type": {
                ctype.value: len([
                    t for t in self._tasks.values()
                    if t.collection_type == ctype
                ])
                for ctype in CollectionType
            },
        }

    def get_execution_history(
        self,
        task_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取执行历史"""
        executions = self._executions.get(task_id, [])
        return [e.to_dict() for e in executions[-limit:]]


# ==================== 全局服务实例 ====================

_collection_scheduler: Optional[CollectionScheduler] = None


def get_collection_scheduler() -> CollectionScheduler:
    """获取采集调度器实例"""
    global _collection_scheduler
    if _collection_scheduler is None:
        _collection_scheduler = CollectionScheduler()
    return _collection_scheduler
