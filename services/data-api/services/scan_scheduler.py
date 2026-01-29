"""
敏感扫描定时调度器
Phase 2: 数据安全管理增强 - 定时扫描调度

功能：
- 基于 cron 表达式的定时敏感扫描
- 从数据库加载扫描策略配置
- 支持动态添加/删除/修改调度任务
- 与 SensitivityAutoScanService 集成
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from services.sensitivity_auto_scan_service import (
    SensitivityAutoScanService,
    AutoScanPolicy,
    AutoScanMode,
    get_sensitivity_auto_scan_service,
)

logger = logging.getLogger(__name__)


class ScanScheduler:
    """
    敏感扫描定时调度器

    使用 APScheduler 实现基于 cron 表达式的定时扫描，
    支持从数据库加载扫描策略并动态管理调度任务。
    """

    def __init__(self, db_session_factory=None):
        """
        初始化调度器

        Args:
            db_session_factory: 数据库会话工厂函数
        """
        self._scheduler = BackgroundScheduler(
            timezone=os.getenv("TZ", "Asia/Shanghai"),
            job_defaults={
                "coalesce": True,  # 合并错过的任务
                "max_instances": 1,  # 同一任务最多一个实例
                "misfire_grace_time": 300,  # 5分钟的容错时间
            }
        )
        self._db_session_factory = db_session_factory
        self._scan_service = get_sensitivity_auto_scan_service()
        self._registered_jobs: Dict[str, Dict[str, Any]] = {}
        self._running = False

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._running

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行中")
            return

        try:
            # 加载所有已配置的扫描策略
            self._load_scheduled_scans()

            # 启动调度器
            self._scheduler.start()
            self._running = True
            logger.info("敏感扫描调度器已启动")

        except Exception as e:
            logger.error(f"启动调度器失败: {e}", exc_info=True)
            raise

    def stop(self):
        """停止调度器"""
        if not self._running:
            return

        try:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("敏感扫描调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")

    def _load_scheduled_scans(self):
        """从数据库加载所有已配置的扫描策略"""
        if not self._db_session_factory:
            logger.warning("无数据库会话工厂，跳过加载扫描策略")
            return

        try:
            from models.security_audit import SensitivityScanConfig

            db = self._db_session_factory()
            try:
                configs = db.query(SensitivityScanConfig).filter(
                    SensitivityScanConfig.enabled == True,
                    SensitivityScanConfig.schedule_cron.isnot(None),
                    SensitivityScanConfig.schedule_cron != "",
                ).all()

                for config in configs:
                    self.register_scan_job(
                        policy_id=config.id,
                        name=config.name,
                        cron_expression=config.schedule_cron,
                        policy_config={
                            "databases": config.databases or [],
                            "exclude_databases": config.exclude_databases or [],
                            "exclude_table_patterns": config.exclude_table_patterns or [],
                            "sample_size": config.sample_size or 200,
                            "confidence_threshold": config.confidence_threshold or 60,
                            "auto_update_metadata": config.auto_update_metadata,
                            "auto_generate_masking_rules": config.auto_generate_masking_rules,
                            "mode": config.scan_mode or "incremental",
                        }
                    )

                logger.info(f"已加载 {len(configs)} 个定时扫描任务")

            finally:
                db.close()

        except ImportError:
            logger.warning("SensitivityScanConfig 模型不可用，跳过加载")
        except Exception as e:
            logger.error(f"加载扫描策略失败: {e}", exc_info=True)

    def register_scan_job(
        self,
        policy_id: str,
        name: str,
        cron_expression: str = None,
        interval_hours: int = None,
        policy_config: Dict[str, Any] = None,
    ) -> bool:
        """
        注册定时扫描任务

        Args:
            policy_id: 策略 ID（唯一标识）
            name: 任务名称
            cron_expression: cron 表达式（如 "0 2 * * *" 表示每天凌晨2点）
            interval_hours: 间隔小时数（与 cron_expression 二选一）
            policy_config: 扫描策略配置

        Returns:
            是否注册成功
        """
        job_id = f"scan_{policy_id}"

        # 构建触发器
        if cron_expression:
            try:
                trigger = CronTrigger.from_crontab(cron_expression)
            except ValueError as e:
                logger.error(f"无效的 cron 表达式 [{cron_expression}]: {e}")
                return False
        elif interval_hours:
            trigger = IntervalTrigger(hours=interval_hours)
        else:
            logger.error("必须提供 cron_expression 或 interval_hours")
            return False

        # 构建扫描策略
        policy = AutoScanPolicy(
            policy_id=policy_id,
            name=name,
            mode=AutoScanMode(policy_config.get("mode", "incremental")),
            databases=policy_config.get("databases", []),
            exclude_databases=policy_config.get("exclude_databases", []),
            exclude_table_patterns=policy_config.get("exclude_table_patterns", []),
            sample_size=policy_config.get("sample_size", 200),
            confidence_threshold=policy_config.get("confidence_threshold", 60),
            auto_update_metadata=policy_config.get("auto_update_metadata", True),
            auto_generate_masking_rules=policy_config.get("auto_generate_masking_rules", True),
            schedule_cron=cron_expression or "",
            schedule_interval_hours=interval_hours or 0,
        )

        # 移除已有的同名任务
        if job_id in self._registered_jobs:
            self.remove_scan_job(policy_id)

        # 注册新任务
        try:
            self._scheduler.add_job(
                func=self._execute_scheduled_scan,
                trigger=trigger,
                id=job_id,
                name=name,
                kwargs={"policy": policy},
                replace_existing=True,
            )

            self._registered_jobs[job_id] = {
                "policy_id": policy_id,
                "name": name,
                "cron": cron_expression,
                "interval_hours": interval_hours,
                "registered_at": datetime.now().isoformat(),
            }

            logger.info(f"已注册定时扫描任务: {name} (ID: {policy_id})")
            return True

        except Exception as e:
            logger.error(f"注册定时扫描任务失败: {e}")
            return False

    def remove_scan_job(self, policy_id: str) -> bool:
        """
        移除定时扫描任务

        Args:
            policy_id: 策略 ID

        Returns:
            是否移除成功
        """
        job_id = f"scan_{policy_id}"

        try:
            self._scheduler.remove_job(job_id)
            if job_id in self._registered_jobs:
                del self._registered_jobs[job_id]
            logger.info(f"已移除定时扫描任务: {policy_id}")
            return True
        except JobLookupError:
            logger.warning(f"任务不存在: {policy_id}")
            return False
        except Exception as e:
            logger.error(f"移除定时扫描任务失败: {e}")
            return False

    def pause_scan_job(self, policy_id: str) -> bool:
        """暂停定时扫描任务"""
        job_id = f"scan_{policy_id}"
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"已暂停定时扫描任务: {policy_id}")
            return True
        except JobLookupError:
            return False

    def resume_scan_job(self, policy_id: str) -> bool:
        """恢复定时扫描任务"""
        job_id = f"scan_{policy_id}"
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"已恢复定时扫描任务: {policy_id}")
            return True
        except JobLookupError:
            return False

    def trigger_scan_now(self, policy_id: str) -> bool:
        """
        立即触发一次扫描（不影响原有调度）

        Args:
            policy_id: 策略 ID

        Returns:
            是否触发成功
        """
        job_id = f"scan_{policy_id}"

        if job_id not in self._registered_jobs:
            logger.warning(f"任务不存在: {policy_id}")
            return False

        try:
            job = self._scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"已触发立即执行: {policy_id}")
                return True
        except Exception as e:
            logger.error(f"触发立即执行失败: {e}")

        return False

    def _execute_scheduled_scan(self, policy: AutoScanPolicy):
        """执行定时扫描任务"""
        logger.info(f"开始执行定时扫描: {policy.name} (ID: {policy.policy_id})")

        try:
            # 获取数据库会话
            db_session = None
            if self._db_session_factory:
                db_session = self._db_session_factory()

            try:
                # 执行扫描
                self._scan_service.start_auto_scan(
                    policy=policy,
                    db_session=db_session,
                )
            finally:
                if db_session:
                    db_session.close()

        except Exception as e:
            logger.error(f"定时扫描执行失败 [{policy.name}]: {e}", exc_info=True)

    def get_registered_jobs(self) -> List[Dict[str, Any]]:
        """获取所有已注册的扫描任务"""
        jobs = []
        for job_id, info in self._registered_jobs.items():
            job = self._scheduler.get_job(job_id)
            if job:
                jobs.append({
                    **info,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "pending": job.pending,
                })
            else:
                jobs.append({
                    **info,
                    "next_run_time": None,
                    "pending": False,
                })
        return jobs

    def get_job_status(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """获取指定任务的状态"""
        job_id = f"scan_{policy_id}"
        job = self._scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "policy_id": policy_id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending,
            "registered_at": self._registered_jobs.get(job_id, {}).get("registered_at"),
        }


# 全局实例
_scan_scheduler: Optional[ScanScheduler] = None


def get_scan_scheduler(db_session_factory=None) -> ScanScheduler:
    """获取敏感扫描调度器单例"""
    global _scan_scheduler
    if _scan_scheduler is None:
        _scan_scheduler = ScanScheduler(db_session_factory=db_session_factory)
    return _scan_scheduler


def init_scan_scheduler(app=None, db_session_factory=None):
    """
    初始化并启动敏感扫描调度器

    在 Flask 应用启动时调用此函数。

    Args:
        app: Flask 应用实例（可选）
        db_session_factory: 数据库会话工厂函数
    """
    scheduler = get_scan_scheduler(db_session_factory=db_session_factory)

    # 仅在生产环境或显式启用时启动
    if os.getenv("SCAN_SCHEDULER_ENABLED", "false").lower() == "true":
        scheduler.start()
        logger.info("敏感扫描调度器已初始化并启动")
    else:
        logger.info("敏感扫描调度器未启用 (设置 SCAN_SCHEDULER_ENABLED=true 启用)")

    return scheduler
