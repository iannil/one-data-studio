"""
工作流调度器
Phase 7: Sprint 7.4

使用 APScheduler 实现工作流调度
支持 Cron 表达式、固定间隔、事件触发
"""

import os
import asyncio
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.executors.pool import ThreadPoolExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


class WorkflowScheduler:
    """工作流调度器

    管理、执行、调度工作流
    """

    def __init__(self):
        if not APSCHEDULER_AVAILABLE:
            raise RuntimeError("APScheduler is not available. Install it with: pip install apscheduler")

        # 配置执行器
        executors = {
            'default': ThreadPoolExecutor(max_workers=10)
        }

        # 配置作业存储（内存存储，生产环境应使用数据库）
        job_defaults = {
            'coalesce': True,  # 合并错过的执行
            'max_instances': 1,  # 同一作业最多同时运行1个实例
            'misfire_grace_time': 300  # 错过执行的宽限时间（秒）
        }

        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        # 调度回调注册表
        self.callbacks: Dict[str, Callable] = {}

        # 启动调度器
        self.scheduler.start()

    def add_schedule(
        self,
        schedule_id: str,
        schedule_type: str,
        workflow_id: str,
        cron_expression: str = None,
        interval_seconds: int = None,
        event_trigger: str = None,
        enabled: bool = True,
        callback: Callable = None
    ) -> bool:
        """添加调度

        Args:
            schedule_id: 调度ID
            schedule_type: 调度类型 (cron, interval, event)
            workflow_id: 工作流ID
            cron_expression: Cron 表达式
            interval_seconds: 间隔秒数
            event_trigger: 事件触发器
            enabled: 是否启用
            callback: 触发时的回调函数

        Returns:
            是否成功添加
        """
        if not enabled:
            return True

        # 移除已存在的作业
        self.remove_schedule(schedule_id)

        # 注册回调
        if callback:
            self.callbacks[schedule_id] = callback

        # 根据类型添加作业
        if schedule_type == "cron" and cron_expression:
            if not CRONITER_AVAILABLE:
                print("Warning: croniter not available, cannot parse cron expression")
                return False

            try:
                self.scheduler.add_job(
                    self._execute_schedule,
                    trigger=CronTrigger.from_crontab(cron_expression),
                    id=schedule_id,
                    name=f"workflow-{workflow_id}",
                    args=[schedule_id, workflow_id],
                    replace_existing=True
                )
                return True
            except Exception as e:
                print(f"Failed to add cron schedule: {e}")
                return False

        elif schedule_type == "interval" and interval_seconds:
            try:
                self.scheduler.add_job(
                    self._execute_schedule,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=schedule_id,
                    name=f"workflow-{workflow_id}",
                    args=[schedule_id, workflow_id],
                    replace_existing=True
                )
                return True
            except Exception as e:
                print(f"Failed to add interval schedule: {e}")
                return False

        elif schedule_type == "event" and event_trigger:
            # 事件触发由外部调用，不注册到调度器
            return True

        return False

    def remove_schedule(self, schedule_id: str) -> bool:
        """移除调度

        Args:
            schedule_id: 调度ID

        Returns:
            是否成功移除
        """
        try:
            # 移除作业
            if self.scheduler.get_job(schedule_id):
                self.scheduler.remove_job(schedule_id)

            # 移除回调
            if schedule_id in self.callbacks:
                del self.callbacks[schedule_id]

            return True
        except Exception as e:
            print(f"Failed to remove schedule: {e}")
            return False

    def trigger_schedule(self, schedule_id: str, workflow_id: str) -> bool:
        """手动触发调度

        Args:
            schedule_id: 调度ID
            workflow_id: 工作流ID

        Returns:
            是否成功触发
        """
        try:
            # 立即执行
            self._execute_schedule(schedule_id, workflow_id)
            return True
        except Exception as e:
            print(f"Failed to trigger schedule: {e}")
            return False

    def _execute_schedule(self, schedule_id: str, workflow_id: str):
        """执行调度的回调函数"""
        if schedule_id in self.callbacks:
            try:
                self.callbacks[schedule_id](schedule_id, workflow_id)
            except Exception as e:
                print(f"Schedule callback error for {schedule_id}: {e}")

    def get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        """获取下次运行时间

        Args:
            schedule_id: 调度ID

        Returns:
            下次运行时间
        """
        job = self.scheduler.get_job(schedule_id)
        if job:
            return job.next_run_time
        return None

    def pause_schedule(self, schedule_id: str) -> bool:
        """暂停调度"""
        try:
            self.scheduler.pause_job(schedule_id)
            return True
        except Exception:
            return False

    def resume_schedule(self, schedule_id: str) -> bool:
        """恢复调度"""
        try:
            self.scheduler.resume_job(schedule_id)
            return True
        except Exception:
            return False

    def list_schedules(self) -> list:
        """列出所有调度"""
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        self.scheduler.shutdown(wait=wait)


# 全局调度器实例
_global_scheduler: Optional[WorkflowScheduler] = None
_scheduler_lock = threading.Lock()


def get_scheduler() -> WorkflowScheduler:
    """获取全局调度器实例"""
    global _global_scheduler

    if _global_scheduler is None:
        with _scheduler_lock:
            if _global_scheduler is None:
                _global_scheduler = WorkflowScheduler()

    return _global_scheduler


def init_scheduler_from_db(db_session):
    """从数据库初始化调度器

    启动时加载所有启用的调度
    """
    if not APSCHEDULER_AVAILABLE:
        print("APScheduler not available, skipping scheduler initialization")
        return

    try:
        from models import WorkflowSchedule

        schedules = db_session.query(WorkflowSchedule).filter(
            WorkflowSchedule.enabled == True
        ).all()

        scheduler = get_scheduler()

        for schedule in schedules:
            # 创建执行回调
            def execute_callback(sid, wid, s=schedule):
                # 这里可以触发工作流执行
                print(f"Triggering workflow {wid} from schedule {sid}")

            scheduler.add_schedule(
                schedule_id=schedule.schedule_id,
                schedule_type=schedule.schedule_type,
                workflow_id=schedule.workflow_id,
                cron_expression=schedule.cron_expression,
                interval_seconds=schedule.interval_seconds,
                event_trigger=schedule.event_trigger,
                enabled=schedule.enabled,
                callback=execute_callback
            )

        print(f"Initialized {len(schedules)} schedules")

    except Exception as e:
        print(f"Failed to initialize scheduler from database: {e}")


# 调度器辅助函数
def calculate_next_run_time(cron_expression: str, base_time: datetime = None) -> Optional[datetime]:
    """计算下次运行时间

    Args:
        cron_expression: Cron 表达式
        base_time: 基准时间，默认为当前时间

    Returns:
        下次运行时间
    """
    if not CRONITER_AVAILABLE:
        return None

    try:
        base = base_time or datetime.utcnow()
        cron = croniter(cron_expression, base)
        return cron.get_next(datetime)
    except Exception:
        return None


def validate_cron_expression(cron_expression: str) -> bool:
    """验证 Cron 表达式

    Args:
        cron_expression: Cron 表达式

    Returns:
        是否有效
    """
    if not CRONITER_AVAILABLE:
        return True  # 无法验证时假设有效

    try:
        croniter(cron_expression)
        return True
    except Exception:
        return False


# 常用 Cron 表达式
COMMON_CRON_EXPRESSIONS = {
    "every_minute": "* * * * *",
    "every_5_minutes": "*/5 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "hourly": "0 * * * *",
    "daily_at_midnight": "0 0 * * *",
    "daily_at_9am": "0 9 * * *",
    "weekly_on_monday": "0 0 * * 1",
    "monthly_on_1st": "0 0 1 * *",
}
