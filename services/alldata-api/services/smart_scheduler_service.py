"""
智能任务调度增强服务
基于 AI 的任务优先级优化、动态资源分配和依赖感知调度
"""

import logging
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


# ==================== 任务状态定义 ====================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 待调度
    QUEUED = "queued"             # 已排队
    RUNNING = "running"           # 运行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消
    SKIPPED = "skipped"           # 已跳过
    RETRYING = "retrying"         # 重试中


class TaskPriority(str, Enum):
    """任务优先级"""
    CRITICAL = "critical"         # 紧急
    HIGH = "high"                 # 高
    NORMAL = "normal"             # 普通
    LOW = "low"                   # 低


# ==================== 任务实体 ====================

@dataclass
class TaskDependency:
    """任务依赖"""
    task_id: str                 # 依赖的任务ID
    type: str = "success"         # 依赖类型：success, completion, failure
    condition: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceRequirement:
    """资源需求"""
    cpu_cores: float = 1.0
    memory_mb: int = 512
    gpu_count: int = 0
    gpu_memory_mb: int = 0
    disk_mb: int = 0

    def to_dict(self) -> Dict:
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "gpu_count": self.gpu_count,
            "gpu_memory_mb": self.gpu_memory_mb,
            "disk_mb": self.disk_mb,
        }


@dataclass
class TaskMetrics:
    """任务指标"""
    execution_time_ms: int = 0
    wait_time_ms: int = 0
    retry_count: int = 0
    last_error: str = ""
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    success_rate: float = 1.0
    avg_execution_time_ms: int = 0


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    name: str
    description: str = ""
    task_type: str = "etl"       # etl, ml, data_quality, notification, etc.
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[TaskDependency] = field(default_factory=list)
    resource_requirement: ResourceRequirement = field(default_factory=ResourceRequirement)
    estimated_duration_ms: int = 60000
    timeout_ms: int = 3600000
    max_retries: int = 3
    retry_delay_ms: int = 60000
    schedule_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": [
                {"task_id": d.task_id, "type": d.type, "condition": d.condition}
                for d in self.dependencies
            ],
            "resource_requirement": self.resource_requirement.to_dict(),
            "estimated_duration_ms": self.estimated_duration_ms,
            "timeout_ms": self.timeout_ms,
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": {
                "execution_time_ms": self.metrics.execution_time_ms,
                "wait_time_ms": self.metrics.wait_time_ms,
                "retry_count": self.metrics.retry_count,
                "last_error": self.metrics.last_error,
                "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "success_rate": self.metrics.success_rate,
                "avg_execution_time_ms": self.metrics.avg_execution_time_ms,
            },
            "tags": self.tags,
            "metadata": self.metadata,
        }


# ==================== 调度策略 ====================

class SchedulingPolicy:
    """调度策略"""

    @staticmethod
    def calculate_priority_score(task: ScheduledTask) -> float:
        """
        计算任务优先级分数（分数越高越优先）

        考虑因素：
        1. 任务基础优先级
        2. 截止时间紧迫度
        3. 等待时长
        4. 依赖状态
        5. 业务价值
        """
        score = 0.0

        # 基础优先级分数
        priority_scores = {
            TaskPriority.CRITICAL: 1000,
            TaskPriority.HIGH: 750,
            TaskPriority.NORMAL: 500,
            TaskPriority.LOW: 250,
        }
        score += priority_scores.get(task.priority, 500)

        # 截止时间紧迫度
        if task.deadline:
            time_to_deadline = (task.deadline - datetime.now()).total_seconds()
            if time_to_deadline < 3600:  # 1小时内
                score += 500
            elif time_to_deadline < 86400:  # 24小时内
                score += 300
            elif time_to_deadline < 604800:  # 7天内
                score += 100

        # 等待时长（等待越久越优先）
        wait_time = (datetime.now() - task.created_at).total_seconds()
        score += min(wait_time / 60, 100)  # 最多加100分

        # 依赖状态（依赖越少越优先）
        score -= len(task.dependencies) * 20

        # 历史成功率（成功率低优先级降低）
        score *= (0.5 + task.metrics.success_rate * 0.5)

        return score

    @staticmethod
    def estimate_resource_availability(
        total_resources: ResourceRequirement,
        used_resources: ResourceRequirement,
    ) -> Dict[str, float]:
        """估算资源可用性（0-1）"""
        return {
            "cpu": max(0, 1 - (used_resources.cpu_cores / total_resources.cpu_cores if total_resources.cpu_cores > 0 else 0)),
            "memory": max(0, 1 - (used_resources.memory_mb / total_resources.memory_mb if total_resources.memory_mb > 0 else 0)),
            "gpu": max(0, 1 - (used_resources.gpu_count / total_resources.gpu_count if total_resources.gpu_count > 0 else 0)),
        }


# ==================== 调度队列 ====================

@dataclass
class QueueItem:
    """队列项（用于优先队列）"""
    task: ScheduledTask
    priority_score: float

    def __lt__(self, other):
        return self.priority_score > other.priority_score  # 优先队列是大顶堆


# ==================== 智能调度服务 ====================

class SmartSchedulerService:
    """智能任务调度服务"""

    def __init__(self):
        # 任务存储
        self._tasks: Dict[str, ScheduledTask] = {}
        self._task_queue: List[QueueItem] = []

        # 资源配置
        self._total_resources = ResourceRequirement(
            cpu_cores=16.0,
            memory_mb=32768,  # 32GB
            gpu_count=4,
            gpu_memory_mb=16384,  # 16GB
            disk_mb=1024000,  # 1TB
        )

        self._used_resources = ResourceRequirement()

        # 调度统计
        self._stats = {
            "total_scheduled": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0,
        }

        # 初始化示例任务
        self._init_sample_tasks()

    def _init_sample_tasks(self):
        """初始化示例任务"""
        now = datetime.now()

        tasks = [
            ScheduledTask(
                task_id="task_001",
                name="数据同步任务",
                description="从源系统同步用户数据",
                task_type="etl",
                priority=TaskPriority.HIGH,
                estimated_duration_ms=300000,
                deadline=now + timedelta(hours=2),
                created_by="system",
                metrics=TaskMetrics(success_rate=0.95, avg_execution_time_ms=280000),
            ),
            ScheduledTask(
                task_id="task_002",
                name="模型训练任务",
                description="训练用户画像模型",
                task_type="ml",
                priority=TaskPriority.NORMAL,
                resource_requirement=ResourceRequirement(gpu_count=1, gpu_memory_mb=8192),
                estimated_duration_ms=3600000,
                deadline=now + timedelta(hours=24),
                created_by="data_scientist",
                dependencies=[
                    TaskDependency(task_id="task_001", type="success")
                ],
                metrics=TaskMetrics(success_rate=0.85, avg_execution_time_ms=3500000),
            ),
            ScheduledTask(
                task_id="task_003",
                name="数据质量检测",
                description="检测数据质量问题",
                task_type="data_quality",
                priority=TaskPriority.NORMAL,
                estimated_duration_ms=120000,
                created_by="quality_engineer",
                dependencies=[
                    TaskDependency(task_id="task_001", type="completion")
                ],
                metrics=TaskMetrics(success_rate=0.98, avg_execution_time_ms=100000),
            ),
            ScheduledTask(
                task_id="task_004",
                name="报表生成任务",
                description="生成每日业务报表",
                task_type="report",
                priority=TaskPriority.LOW,
                estimated_duration_ms=60000,
                schedule_time=now + timedelta(hours=1),
                created_by="analyst",
                metrics=TaskMetrics(success_rate=0.99, avg_execution_time_ms=55000),
            ),
            ScheduledTask(
                task_id="task_005",
                name="告警通知任务",
                description="发送异常告警通知",
                task_type="notification",
                priority=TaskPriority.CRITICAL,
                estimated_duration_ms=10000,
                deadline=now + timedelta(minutes=30),
                created_by="system",
                metrics=TaskMetrics(success_rate=1.0, avg_execution_time_ms=8000),
            ),
        ]

        for task in tasks:
            self._tasks[task.task_id] = task
            if task.status == TaskStatus.PENDING:
                self._enqueue_task(task)

    def _enqueue_task(self, task: ScheduledTask):
        """将任务加入优先队列"""
        priority_score = SchedulingPolicy.calculate_priority_score(task)
        heapq.heappush(self._task_queue, QueueItem(task, priority_score))

    def _dequeue_task(self) -> Optional[ScheduledTask]:
        """从队列中取出最高优先级任务"""
        if self._task_queue:
            item = heapq.heappop(self._task_queue)
            return item.task
        return None

    # ==================== 任务管理 ====================

    def create_task(
        self,
        name: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        description: str = "",
        dependencies: List[Dict[str, Any]] = None,
        resource_requirement: Dict[str, Any] = None,
        estimated_duration_ms: int = 60000,
        deadline: datetime = None,
        created_by: str = "",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> ScheduledTask:
        """创建新任务"""
        task = ScheduledTask(
            task_id=f"task_{secrets.token_hex(8)}",
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            dependencies=[
                TaskDependency(**d) for d in dependencies or []
            ],
            resource_requirement=ResourceRequirement(**(resource_requirement or {})),
            estimated_duration_ms=estimated_duration_ms,
            deadline=deadline,
            created_by=created_by,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._tasks[task.task_id] = task
        self._enqueue_task(task)
        self._stats["total_scheduled"] += 1

        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus = None,
        priority: TaskPriority = None,
        task_type: str = None,
        limit: int = 100,
    ) -> List[ScheduledTask]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        # 按优先级分数排序
        tasks.sort(key=lambda t: SchedulingPolicy.calculate_priority_score(t), reverse=True)

        return tasks[:limit]

    def update_task(
        self,
        task_id: str,
        **updates
    ) -> Optional[ScheduledTask]:
        """更新任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if key == "priority" and isinstance(value, str):
                value = TaskPriority(value)
            if key == "status" and isinstance(value, str):
                value = TaskStatus(value)
            if key == "resource_requirement" and isinstance(value, dict):
                value = ResourceRequirement(**value)
            if hasattr(task, key):
                setattr(task, key, value)

        return task

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    # ==================== 调度执行 ====================

    def get_next_task(self) -> Optional[ScheduledTask]:
        """获取下一个可执行任务（考虑依赖和资源）"""
        while self._task_queue:
            task = self._dequeue_task()

            # 检查任务是否仍然可执行
            if task.task_id not in self._tasks:
                continue
            if self._tasks[task.task_id].status != TaskStatus.PENDING:
                continue

            # 检查依赖是否满足
            if not self._check_dependencies(task):
                # 依赖未满足，重新入队
                self._enqueue_task(task)
                continue

            # 检查资源是否充足
            if not self._check_resources(task):
                # 资源不足，重新入队
                self._enqueue_task(task)
                continue

            return task

        return None

    def _check_dependencies(self, task: ScheduledTask) -> bool:
        """检查任务依赖是否满足"""
        for dep in task.dependencies:
            dep_task = self._tasks.get(dep.task_id)
            if not dep_task:
                continue

            if dep.type == "success" and dep_task.status != TaskStatus.COMPLETED:
                return False
            if dep.type == "completion" and dep_task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False
            if dep.type == "failure" and dep_task.status != TaskStatus.FAILED:
                return False

        return True

    def _check_resources(self, task: ScheduledTask) -> bool:
        """检查资源是否充足"""
        req = task.resource_requirement
        available = SchedulingPolicy.estimate_resource_availability(
            self._total_resources, self._used_resources
        )

        return (
            req.cpu_cores <= self._total_resources.cpu_cores * available.get("cpu", 1) and
            req.memory_mb <= self._total_resources.memory_mb * available.get("memory", 1) and
            req.gpu_count <= self._total_resources.gpu_count * available.get("gpu", 1)
        )

    def start_task(self, task_id: str) -> Optional[ScheduledTask]:
        """开始执行任务"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return None

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.metrics.wait_time_ms = int((task.started_at - task.created_at).total_seconds() * 1000)

        # 占用资源
        req = task.resource_requirement
        self._used_resources.cpu_cores += req.cpu_cores
        self._used_resources.memory_mb += req.memory_mb
        self._used_resources.gpu_count += req.gpu_count
        self._used_resources.gpu_memory_mb += req.gpu_memory_mb

        return task

    def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error_message: str = "",
        execution_time_ms: int = None,
    ) -> Optional[ScheduledTask]:
        """完成任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.completed_at = datetime.now()

        if execution_time_ms:
            task.metrics.execution_time_ms = execution_time_ms
        elif task.started_at:
            task.metrics.execution_time_ms = int(
                (task.completed_at - task.started_at).total_seconds() * 1000
            )

        if not success:
            task.metrics.last_error = error_message
            task.metrics.last_failure_time = task.completed_at

            # 重试逻辑
            if task.metrics.retry_count < task.max_retries:
                task.metrics.retry_count += 1
                task.status = TaskStatus.RETRYING
                # 延迟后重新入队
                self._tasks[task_id] = task
                # 简化处理，实际应该使用定时器
                self._enqueue_task(task)
                self._stats["total_retries"] += 1
                return task
        else:
            task.metrics.last_success_time = task.completed_at

        # 释放资源
        req = task.resource_requirement
        self._used_resources.cpu_cores -= req.cpu_cores
        self._used_resources.memory_mb -= req.memory_mb
        self._used_resources.gpu_count -= req.gpu_count
        self._used_resources.gpu_memory_mb -= req.gpu_memory_mb

        # 更新统计
        if success:
            self._stats["total_completed"] += 1
        else:
            self._stats["total_failed"] += 1

        # 更新成功率
        total_runs = self._stats["total_completed"] + self._stats["total_failed"]
        task.metrics.success_rate = self._stats["total_completed"] / total_runs if total_runs > 0 else 1.0

        # 激活依赖此任务的其他任务
        self._activate_dependent_tasks(task_id)

        return task

    def _activate_dependent_tasks(self, completed_task_id: str):
        """激活依赖已完成任务的其他任务"""
        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING:
                # 检查是否所有依赖都满足
                if self._check_dependencies(task):
                    self._enqueue_task(task)

    # ==================== 调度优化 ====================

    def optimize_schedule(self, tasks: List[ScheduledTask] = None) -> Dict[str, Any]:
        """
        优化调度顺序

        使用 AI 启发式算法：
        1. 考虑任务优先级
        2. 考虑依赖关系（拓扑排序）
        3. 考虑资源约束
        4. 考虑截止时间
        """
        if tasks is None:
            tasks = list(self._tasks.values())

        pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]

        # 构建依赖图
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for task in pending_tasks:
            for dep in task.dependencies:
                dep_task = self._tasks.get(dep.task_id)
                if dep_task and dep_task.status == TaskStatus.PENDING:
                    graph[dep.task_id].append(task.task_id)
                    in_degree[task.task_id] += 1

        # 拓扑排序 + 优先级队列
        queue = []
        for task in pending_tasks:
            if in_degree[task.task_id] == 0:
                priority = SchedulingPolicy.calculate_priority_score(task)
                heapq.heappush(queue, (-priority, task.task_id))

        optimized_order = []
        while queue:
            _, task_id = heapq.heappop(queue)
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                optimized_order.append(task)

            for dependent_id in graph[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    dep_task = self._tasks.get(dependent_id)
                    if dep_task:
                        priority = SchedulingPolicy.calculate_priority_score(dep_task)
                        heapq.heappush(queue, (-priority, dependent_id))

        return {
            "optimized_order": [t.task_id for t in optimized_order],
            "total_tasks": len(optimized_order),
            "estimated_completion_time": sum(t.estimated_duration_ms for t in optimized_order),
        }

    def predict_resource_demand(
        self,
        window_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        预测资源需求

        基于当前队列中的任务预测未来资源需求
        """
        window_tasks = []
        now = datetime.now()

        for task in self._tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                window_tasks.append(task)

        # 计算并发资源需求
        max_cpu = sum(t.resource_requirement.cpu_cores for t in window_tasks)
        max_memory = sum(t.resource_requirement.memory_mb for t in window_tasks)
        max_gpu = sum(t.resource_requirement.gpu_count for t in window_tasks)

        return {
            "window_minutes": window_minutes,
            "predicted_tasks": len(window_tasks),
            "resource_demand": {
                "cpu_cores": max_cpu,
                "memory_mb": max_memory,
                "gpu_count": max_gpu,
            },
            "resource_utilization": {
                "cpu_percent": (max_cpu / self._total_resources.cpu_cores * 100) if self._total_resources.cpu_cores > 0 else 0,
                "memory_percent": (max_memory / self._total_resources.memory_mb * 100) if self._total_resources.memory_mb > 0 else 0,
                "gpu_percent": (max_gpu / self._total_resources.gpu_count * 100) if self._total_resources.gpu_count > 0 else 0,
            },
            "recommendations": self._generate_resource_recommendations(max_cpu, max_memory, max_gpu),
        }

    def _generate_resource_recommendations(
        self,
        cpu_demand: float,
        memory_demand: int,
        gpu_demand: int,
    ) -> List[str]:
        """生成资源建议"""
        recommendations = []

        if cpu_demand > self._total_resources.cpu_cores:
            recommendations.append(f"CPU 需求 ({cpu_demand:.1f}核) 超过总容量 ({self._total_resources.cpu_cores}核)，建议增加计算节点")

        if memory_demand > self._total_resources.memory_mb:
            recommendations.append(f"内存需求 ({memory_demand}MB) 超过总容量 ({self._total_resources.memory_mb}MB)，建议增加内存或启用内存交换")

        if gpu_demand > self._total_resources.gpu_count:
            recommendations.append(f"GPU 需求 ({gpu_demand}个) 超过总容量 ({self._total_resources.gpu_count}个)，建议增加 GPU 资源")

        cpu_util = cpu_demand / self._total_resources.cpu_cores if self._total_resources.cpu_cores > 0 else 0
        if cpu_util > 0.9:
            recommendations.append(f"CPU 利用率预计达到 {cpu_util*100:.1f}%，建议错峰运行高优先级任务")

        return recommendations

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取调度统计"""
        status_counts: Dict[str, int] = defaultdict(int)
        for task in self._tasks.values():
            status_counts[task.status.value] += 1

        return {
            "total_tasks": len(self._tasks),
            "status_counts": dict(status_counts),
            "queue_length": len(self._task_queue),
            "total_resources": self._total_resources.to_dict(),
            "used_resources": self._used_resources.to_dict(),
            "available_resources": {
                "cpu_cores": self._total_resources.cpu_cores - self._used_resources.cpu_cores,
                "memory_mb": self._total_resources.memory_mb - self._used_resources.memory_mb,
                "gpu_count": self._total_resources.gpu_count - self._used_resources.gpu_count,
                "gpu_memory_mb": self._total_resources.gpu_memory_mb - self._used_resources.gpu_memory_mb,
            },
            "scheduling_stats": self._stats.copy(),
        }


# 创建全局服务实例
_scheduler_service = None


def get_smart_scheduler_service() -> SmartSchedulerService:
    """获取智能调度服务实例"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SmartSchedulerService()
    return _scheduler_service
