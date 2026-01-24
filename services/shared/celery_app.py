"""
Celery 异步任务队列模块
Sprint 8: 异步任务处理

提供文档索引、工作流执行等异步任务能力
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from celery import Celery, current_task
from celery.result import AsyncResult
from celery.exceptions import SoftTimeLimitExceeded

from .config import get_config

logger = logging.getLogger(__name__)

# 获取配置
config = get_config()
celery_config = config.celery

# 创建 Celery 应用
celery_app = Celery(
    'one_data_studio',
    broker=celery_config.broker_url,
    backend=celery_config.result_backend,
    include=[
        'services.shared.celery_tasks',
    ]
)

# Celery 配置
celery_app.conf.update(
    # 任务设置
    task_track_started=celery_config.task_track_started,
    task_time_limit=celery_config.task_time_limit,
    task_soft_time_limit=celery_config.task_soft_time_limit,
    task_acks_late=True,  # 任务执行完成后才确认
    worker_prefetch_multiplier=1,  # 防止任务堆积

    # 结果设置
    result_expires=celery_config.result_expires,
    result_extended=True,  # 扩展结果存储时间

    # Worker 设置
    worker_max_tasks_per_child=celery_config.worker_max_tasks_per_child,

    # 序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 时区
    timezone='UTC',
    enable_utc=True,

    # 任务路由（可选）
    task_routes={
        'services.shared.celery_tasks.index_document': {'queue': 'indexing'},
        'services.shared.celery_tasks.index_documents_batch': {'queue': 'indexing'},
        'services.shared.celery_tasks.execute_workflow': {'queue': 'workflow'},
        'services.shared.celery_tasks.execute_workflow_long_running': {'queue': 'long_running'},
    },

    # 任务限流
    task_annotations={
        'services.shared.celery_tasks.index_document': {'rate_limit': '10/m'},
    },
)


class TaskStatus:
    """任务状态"""
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.celery = celery_app

    def submit_task(self, task_name: str, *args, **kwargs) -> str:
        """
        提交异步任务

        Args:
            task_name: 任务名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            任务 ID
        """
        result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
        logger.info(f"Task submitted: {task_name} - {result.id}")
        return result.id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态信息
        """
        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "status": result.state,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback if result.failed() else None,
            "info": result.info,
        }

    def wait_for_result(self, task_id: str, timeout: Optional[int] = None) -> Any:
        """
        等待任务结果

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            任务结果
        """
        result = AsyncResult(task_id, app=celery_app)
        return result.get(timeout=timeout)

    def revoke_task(self, task_id: str, terminate: bool = False):
        """
        撤销任务

        Args:
            task_id: 任务 ID
            terminate: 是否强制终止正在执行的任务
        """
        celery_app.control.revoke(task_id, terminate=terminate)
        logger.info(f"Task revoked: {task_id}")

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取活动任务列表"""
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active:
            return [
                {"task_id": t["id"], "name": t["name"], "args": t["args"]}
                for worker_tasks in active.values()
                for t in worker_tasks
            ]
        return []

    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取预定任务列表"""
        inspect = celery_app.control.inspect()
        scheduled = inspect.scheduled()
        if scheduled:
            return [
                {"task_id": t["id"], "name": t["name"], "eta": t["eta"]}
                for worker_tasks in scheduled.values()
                for t in worker_tasks
            ]
        return []

    def get_worker_stats(self) -> Dict[str, Any]:
        """获取 Worker 统计信息"""
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            return {
                "total_tasks": sum(s.get("total", {}) for s in stats.values()),
                "workers": list(stats.keys())
            }
        return {}


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


# 任务结果类
class TaskResult:
    """任务结果封装"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


# 任务装饰器
def async_task(name: str, queue: str = 'default'):
    """
    异步任务装饰器

    Args:
        name: 任务名称
        queue: 任务队列

    Usage:
        @async_task('process_document', queue='indexing')
        def process_document(doc_id):
            ...
    """
    def decorator(func):
        # 注册为 Celery 任务
        task = celery_app.task(func, name=name)

        # 添加便捷方法
        def submit_async(*args, **kwargs):
            """异步提交任务"""
            return task.delay(*args, **kwargs)

        def submit_apply(*args, **kwargs):
            """同步执行任务"""
            return task.apply(args=args, kwargs=kwargs)

        func.submit_async = submit_async
        func.submit_apply = submit_apply
        func.task = task

        return func

    return decorator


# 导出
__all__ = [
    'celery_app',
    'TaskStatus',
    'TaskManager',
    'get_task_manager',
    'TaskResult',
    'async_task',
]
