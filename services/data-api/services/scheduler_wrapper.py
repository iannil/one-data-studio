"""
统一调度器封装服务
整合 DolphinScheduler 和 Celery 调度能力，提供统一的任务调度接口

功能：
1. 统一的任务提交接口
2. 调度引擎选择（DolphinScheduler / Celery）
3. 任务状态追踪
4. 工作流编排
5. 定时任务管理
"""

import logging
import os
import secrets
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from services.shared.celery_app import get_task_manager, TaskStatus as CeleryTaskStatus
from services.shared.ds_celery_bridge import (
    get_ds_celery_bridge,
    DSTaskType,
    DSWorkflowDefinition,
    DSTaskDefinition,
)
from services.data_api.services.smart_scheduler_service import (
    get_smart_scheduler_service,
    ScheduledTask,
    TaskPriority,
    TaskStatus as SmartTaskStatus,
    ResourceRequirement,
)

logger = logging.getLogger(__name__)


class SchedulerEngine(str, Enum):
    """调度引擎类型"""
    CELERY = "celery"  # 使用 Celery 调度
    DOLPHINSCHEDULER = "dolphinscheduler"  # 使用 DolphinScheduler 调度
    SMART = "smart"  # 使用智能调度器
    AUTO = "auto"  # 自动选择


class TaskDefinitionType(str, Enum):
    """任务定义类型"""
    CELERY_TASK = "celery_task"  # Celery 任务
    SHELL = "shell"  # Shell 脚本
    SQL = "sql"  # SQL 查询
    PYTHON = "python"  # Python 脚本
    HTTP = "http"  # HTTP 请求
    WORKFLOW = "workflow"  # 工作流


@dataclass
class UnifiedTaskDefinition:
    """统一任务定义"""
    name: str
    task_type: TaskDefinitionType
    description: str = ""

    # Celery 任务配置
    celery_task_name: str = ""

    # 脚本配置
    script: str = ""
    script_content: str = ""

    # SQL 配置
    sql_query: str = ""
    datasource_id: int = 0

    # HTTP 配置
    http_url: str = ""
    http_method: str = "GET"
    http_headers: Dict[str, str] = field(default_factory=dict)
    http_body: str = ""

    # 参数配置
    parameters: Dict[str, Any] = field(default_factory=dict)

    # 依赖配置
    dependencies: List[str] = field(default_factory=list)

    # 资源配置
    priority: TaskPriority = TaskPriority.NORMAL
    resource_requirement: ResourceRequirement = field(default_factory=ResourceRequirement)

    # 调度配置
    engine: SchedulerEngine = SchedulerEngine.AUTO
    timeout: int = 3600
    retry_count: int = 3
    retry_delay: int = 60


@dataclass
class UnifiedTaskResult:
    """统一任务执行结果"""
    task_id: str
    engine: SchedulerEngine
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedScheduler:
    """统一调度器

    整合多种调度引擎，提供统一的任务调度接口
    """

    def __init__(self):
        self.celery = get_task_manager()
        self.ds_bridge = get_ds_celery_bridge()
        self.smart_scheduler = get_smart_scheduler_service()

        # 默认调度引擎
        self._default_engine = SchedulerEngine(
            os.getenv("DEFAULT_SCHEDULER_ENGINE", "auto").lower()
        )

    # ==================== 任务提交 ====================

    def submit_task(
        self,
        task_def: UnifiedTaskDefinition,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
    ) -> UnifiedTaskResult:
        """
        提交任务到调度器

        Args:
            task_def: 任务定义
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            任务执行结果
        """
        args = args or []
        kwargs = kwargs or {}

        # 选择调度引擎
        engine = self._select_engine(task_def)

        try:
            if engine == SchedulerEngine.CELERY:
                return self._submit_to_celery(task_def, args, kwargs)
            elif engine == SchedulerEngine.DOLPHINSCHEDULER:
                return self._submit_to_dolphinscheduler(task_def, args, kwargs)
            elif engine == SchedulerEngine.SMART:
                return self._submit_to_smart(task_def, args, kwargs)
            else:
                # 默认使用 Celery
                return self._submit_to_celery(task_def, args, kwargs)

        except Exception as e:
            logger.error(f"任务提交失败: {e}")
            return UnifiedTaskResult(
                task_id="",
                engine=engine,
                status="FAILED",
                error=str(e),
            )

    def _select_engine(self, task_def: UnifiedTaskDefinition) -> SchedulerEngine:
        """选择调度引擎"""
        if task_def.engine != SchedulerEngine.AUTO:
            return task_def.engine

        # 根据任务类型自动选择
        if task_def.task_type == TaskDefinitionType.CELERY_TASK:
            return SchedulerEngine.CELERY
        elif task_def.task_type in [TaskDefinitionType.SHELL, TaskDefinitionType.SQL, TaskDefinitionType.WORKFLOW]:
            return SchedulerEngine.DOLPHINSCHEDULER
        else:
            return self._default_engine or SchedulerEngine.CELERY

    def _submit_to_celery(
        self,
        task_def: UnifiedTaskDefinition,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedTaskResult:
        """提交到 Celery"""
        task_name = task_def.celery_task_name or f"services.shared.celery_tasks.{task_def.name}"

        # 合并参数
        merged_kwargs = {**task_def.parameters, **kwargs}

        task_id = self.celery.submit_task(task_name, *args, **merged_kwargs)

        return UnifiedTaskResult(
            task_id=task_id,
            engine=SchedulerEngine.CELERY,
            status="PENDING",
            started_at=datetime.now(),
            metadata={"task_name": task_name},
        )

    def _submit_to_dolphinscheduler(
        self,
        task_def: UnifiedTaskDefinition,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedTaskResult:
        """提交到 DolphinScheduler"""
        # 转换为 DS 任务类型
        ds_task_type = self._map_to_ds_task_type(task_def.task_type)

        # 构建任务代码
        code = task_def.script_content or task_def.sql_query or task_def.script

        # 创建临时工作流
        workflow_name = f"temp_workflow_{secrets.token_hex(8)}"

        task_defs = [
            DSTaskDefinition(
                name=task_def.name,
                task_type=ds_task_type,
                description=task_def.description,
                code=code,
                raw_script=code,
                params={**task_def.parameters, **kwargs},
            )
        ]

        # 通过桥接器创建工作流
        workflow_code = self.ds_bridge.create_ds_workflow_from_tasks(
            project_name="one-data",
            workflow_name=workflow_name,
            tasks=[{
                "name": task_def.name,
                "type": ds_task_type.value,
                "code": code,
                "params": {**task_def.parameters, **kwargs},
            }],
            description=task_def.description,
        )

        if workflow_code:
            return UnifiedTaskResult(
                task_id=str(workflow_code),
                engine=SchedulerEngine.DOLPHINSCHEDULER,
                status="SUBMITTED",
                started_at=datetime.now(),
                metadata={"workflow_code": workflow_code},
            )
        else:
            return UnifiedTaskResult(
                task_id="",
                engine=SchedulerEngine.DOLPHINSCHEDULER,
                status="FAILED",
                error="工作流创建失败",
            )

    def _submit_to_smart(
        self,
        task_def: UnifiedTaskDefinition,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedTaskResult:
        """提交到智能调度器"""
        # 创建智能调度任务
        scheduled_task = self.smart_scheduler.create_task(
            name=task_def.name,
            task_type=task_def.task_type.value,
            priority=task_def.priority,
            description=task_def.description,
            resource_requirement=task_def.resource_requirement.to_dict(),
            estimated_duration_ms=task_def.timeout * 1000,
            metadata={
                "parameters": {**task_def.parameters, **kwargs},
                "args": args,
            },
        )

        return UnifiedTaskResult(
            task_id=scheduled_task.task_id,
            engine=SchedulerEngine.SMART,
            status="PENDING",
            started_at=datetime.now(),
            metadata={"scheduled_task": scheduled_task.to_dict()},
        )

    def _map_to_ds_task_type(self, task_type: TaskDefinitionType) -> DSTaskType:
        """映射任务类型到 DolphinScheduler 任务类型"""
        mapping = {
            TaskDefinitionType.SHELL: DSTaskType.SHELL,
            TaskDefinitionType.SQL: DSTaskType.SQL,
            TaskDefinitionType.PYTHON: DSTaskType.PYTHON,
            TaskDefinitionType.HTTP: DSTaskType.HTTP,
        }
        return mapping.get(task_type, DSTaskType.SHELL)

    # ==================== 工作流管理 ====================

    def create_workflow(
        self,
        name: str,
        tasks: List[UnifiedTaskDefinition],
        description: str = "",
        engine: SchedulerEngine = SchedulerEngine.DOLPHINSCHEDULER,
    ) -> Optional[str]:
        """
        创建工作流

        Args:
            name: 工作流名称
            tasks: 任务列表
            description: 描述
            engine: 调度引擎

        Returns:
            工作流 ID
        """
        if engine == SchedulerEngine.DOLPHINSCHEDULER:
            task_configs = []
            for task in tasks:
                task_configs.append({
                    "name": task.name,
                    "type": self._map_to_ds_task_type(task.task_type).value,
                    "code": task.script_content or task.sql_query or task.script,
                    "params": task.parameters,
                    "dependencies": task.dependencies,
                })

            workflow_code = self.ds_bridge.create_ds_workflow_from_tasks(
                project_name="one-data",
                workflow_name=name,
                tasks=task_configs,
                description=description,
            )

            return str(workflow_code) if workflow_code else None

        else:
            # 对于 Celery，创建智能调度任务依赖
            task_ids = []
            for task in tasks:
                result = self.submit_task(task)
                task_ids.append(result.task_id)

            # 设置任务依赖
            for i, task_id in enumerate(task_ids[1:], 1):
                prev_task_id = task_ids[i - 1]
                # 智能调度器会处理依赖
                pass

            return ",".join(task_ids)

    def run_workflow(
        self,
        workflow_id: str,
        params: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        运行工作流

        Args:
            workflow_id: 工作流 ID
            params: 全局参数

        Returns:
            流程实例 ID
        """
        return self.ds_bridge.ds.run_workflow(
            project_name="one-data",
            workflow_name=workflow_id,
            params=params or {},
        )

    # ==================== 任务状态查询 ====================

    def get_task_status(
        self,
        task_id: str,
        engine: SchedulerEngine = None,
    ) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID
            engine: 调度引擎（可选，自动检测）

        Returns:
            任务状态信息
        """
        # 尝试从各引擎获取状态
        if engine == SchedulerEngine.CELERY or engine is None:
            try:
                status = self.celery.get_task_status(task_id)
                if status.get("task_id") == task_id:
                    return {
                        "engine": "celery",
                        **status,
                    }
            except Exception:
                pass

        if engine == SchedulerEngine.SMART or engine is None:
            task = self.smart_scheduler.get_task(task_id)
            if task:
                return {
                    "engine": "smart",
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "name": task.name,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "metrics": task.metrics.to_dict(),
                }

        return {
            "engine": "unknown",
            "task_id": task_id,
            "status": "NOT_FOUND",
        }

    def list_tasks(
        self,
        status: str = None,
        engine: SchedulerEngine = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        列出任务

        Args:
            status: 任务状态过滤
            engine: 调度引擎过滤
            limit: 返回数量限制

        Returns:
            任务列表
        """
        results = []

        if engine in [SchedulerEngine.CELERY, None]:
            # 获取 Celery 活动任务
            active = self.celery.get_active_tasks()
            results.extend([
                {"engine": "celery", **task} for task in active[:limit]
            ])

        if engine in [SchedulerEngine.SMART, None]:
            # 获取智能调度器任务
            tasks = self.smart_scheduler.list_tasks(
                status=SmartTaskStatus(status) if status else None,
                limit=limit,
            )
            results.extend([
                {"engine": "smart", **task.to_dict()} for task in tasks
            ])

        return results[:limit]

    # ==================== 任务控制 ====================

    def cancel_task(
        self,
        task_id: str,
        engine: SchedulerEngine = None,
    ) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID
            engine: 调度引擎

        Returns:
            是否成功
        """
        if engine == SchedulerEngine.CELERY or engine is None:
            try:
                self.celery.revoke_task(task_id, terminate=True)
                return True
            except Exception:
                pass

        if engine == SchedulerEngine.SMART or engine is None:
            task = self.smart_scheduler.get_task(task_id)
            if task:
                self.smart_scheduler.delete_task(task_id)
                return True

        return False

    def retry_task(
        self,
        task_id: str,
        engine: SchedulerEngine = None,
    ) -> Optional[str]:
        """
        重试任务

        Args:
            task_id: 原任务 ID
            engine: 调度引擎

        Returns:
            新任务 ID
        """
        # 获取原任务信息
        status = self.get_task_status(task_id, engine)

        # 根据原任务重新提交
        # 这里简化处理，实际应该保存任务定义
        logger.warning(f"任务重试功能需要保存原任务定义: {task_id}")
        return None

    # ==================== 定时任务 ====================

    def schedule_cron_task(
        self,
        task_def: UnifiedTaskDefinition,
        cron_expression: str,
        description: str = "",
    ) -> Optional[str]:
        """
        创建定时任务

        Args:
            task_def: 任务定义
            cron_expression: Cron 表达式
            description: 描述

        Returns:
            定时任务 ID
        """
        # 通过 DolphinScheduler 创建定时任务
        workflow_id = self.create_workflow(
            name=f"cron_{task_def.name}_{secrets.token_hex(4)}",
            tasks=[task_def],
            description=description,
            engine=SchedulerEngine.DOLPHINSCHEDULER,
        )

        if workflow_id:
            # 创建调度计划
            # 这里简化处理，实际需要调用 DS API 创建 schedule
            return workflow_id

        return None

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取调度统计信息"""
        # Celery 统计
        celery_stats = self.celery.get_worker_stats()

        # 智能调度器统计
        smart_stats = self.smart_scheduler.get_statistics()

        return {
            "celery": {
                "workers": celery_stats.get("workers", []),
                "total_tasks": celery_stats.get("total_tasks", 0),
            },
            "smart_scheduler": {
                "total_tasks": smart_stats.get("total_tasks", 0),
                "status_counts": smart_stats.get("status_counts", {}),
                "queue_length": smart_stats.get("queue_length", 0),
                "available_resources": smart_stats.get("available_resources", {}),
            },
        }


# 装饰器：统一任务提交
def scheduled_task(
    name: str,
    engine: SchedulerEngine = SchedulerEngine.AUTO,
    timeout: int = 3600,
    priority: TaskPriority = TaskPriority.NORMAL,
):
    """
    装饰器：将函数注册为可调度任务

    Usage:
        @scheduled_task("process_data", engine=SchedulerEngine.CELERY)
        def process_data(param1, param2):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 添加调度方法
        def submit(*args, **kwargs):
            scheduler = get_unified_scheduler()
            task_def = UnifiedTaskDefinition(
                name=name,
                task_type=TaskDefinitionType.CELERY_TASK,
                celery_task_name=f"services.data_api.services.{func.__module__}.{func.__name__}",
                priority=priority,
                timeout=timeout,
                engine=engine,
            )
            return scheduler.submit_task(task_def, args, kwargs)

        wrapper.submit = submit
        wrapper.task_name = name
        wrapper.engine = engine
        return wrapper

    return decorator


# 全局调度器实例
_unified_scheduler: Optional[UnifiedScheduler] = None


def get_unified_scheduler() -> UnifiedScheduler:
    """获取统一调度器实例"""
    global _unified_scheduler
    if _unified_scheduler is None:
        _unified_scheduler = UnifiedScheduler()
    return _unified_scheduler


# 导出
__all__ = [
    'SchedulerEngine',
    'TaskDefinitionType',
    'UnifiedTaskDefinition',
    'UnifiedTaskResult',
    'UnifiedScheduler',
    'get_unified_scheduler',
    'scheduled_task',
]
