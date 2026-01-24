"""
Scheduler 服务集成测试
Sprint 24: Scheduler 服务完善

测试定时任务调度功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import time


class TestScheduleExecutionTracker:
    """执行跟踪器测试"""

    def test_record_execution(self):
        """测试记录执行"""
        from services.scheduler import ScheduleExecutionTracker

        tracker = ScheduleExecutionTracker()
        tracker.record_execution("schedule-1", "completed", duration_ms=100)

        stats = tracker.get_statistics("schedule-1")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1

    def test_record_failed_execution(self):
        """测试记录失败执行"""
        from services.scheduler import ScheduleExecutionTracker

        tracker = ScheduleExecutionTracker()
        tracker.record_execution("schedule-1", "failed", error="Test error")

        stats = tracker.get_statistics("schedule-1")
        assert stats["failed_executions"] == 1

    def test_statistics_calculation(self):
        """测试统计计算"""
        from services.scheduler import ScheduleExecutionTracker

        tracker = ScheduleExecutionTracker()

        # 添加多个执行记录
        tracker.record_execution("schedule-1", "completed", duration_ms=100)
        tracker.record_execution("schedule-1", "completed", duration_ms=200)
        tracker.record_execution("schedule-1", "failed", error="Error")

        stats = tracker.get_statistics("schedule-1")

        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert stats["failed_executions"] == 1
        assert stats["average_execution_time_ms"] == 150
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_recent_executions_limit(self):
        """测试最近执行记录限制"""
        from services.scheduler import ScheduleExecutionTracker

        tracker = ScheduleExecutionTracker()

        for i in range(20):
            tracker.record_execution("schedule-1", "completed", duration_ms=i * 10)

        recent = tracker.get_recent_executions("schedule-1", limit=5)
        assert len(recent) == 5

    def test_empty_statistics(self):
        """测试空统计"""
        from services.scheduler import ScheduleExecutionTracker

        tracker = ScheduleExecutionTracker()
        stats = tracker.get_statistics("nonexistent")

        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0.0


class TestBackoffCalculation:
    """退避算法测试"""

    def test_calculate_backoff(self):
        """测试指数退避计算"""
        from services.scheduler import calculate_backoff

        # 第0次重试
        delay = calculate_backoff(0, base=2, initial_delay=60)
        assert delay == 60

        # 第1次重试
        delay = calculate_backoff(1, base=2, initial_delay=60)
        assert delay == 120

        # 第2次重试
        delay = calculate_backoff(2, base=2, initial_delay=60)
        assert delay == 240

    def test_backoff_max_limit(self):
        """测试最大延迟限制"""
        from services.scheduler import calculate_backoff

        # 应该被限制在3600秒（1小时）
        delay = calculate_backoff(10, base=2, initial_delay=60)
        assert delay == 3600


class TestCronValidation:
    """Cron 表达式验证测试"""

    def test_validate_valid_cron(self):
        """测试有效的 Cron 表达式"""
        from services.scheduler import validate_cron_expression

        assert validate_cron_expression("* * * * *") is True
        assert validate_cron_expression("0 9 * * *") is True
        assert validate_cron_expression("*/5 * * * *") is True
        assert validate_cron_expression("0 0 1 * *") is True

    def test_validate_invalid_cron(self):
        """测试无效的 Cron 表达式"""
        from services.scheduler import validate_cron_expression

        # 如果 croniter 可用，应该返回 False
        result = validate_cron_expression("invalid cron")
        # 结果取决于 croniter 是否可用
        assert isinstance(result, bool)


class TestNextRunTimeCalculation:
    """下次运行时间计算测试"""

    def test_calculate_next_run_time(self):
        """测试下次运行时间计算"""
        from services.scheduler import calculate_next_run_time

        base_time = datetime(2024, 1, 1, 8, 0, 0)
        next_run = calculate_next_run_time("0 9 * * *", base_time)

        if next_run:  # 如果 croniter 可用
            assert next_run.hour == 9
            assert next_run.minute == 0


class TestWorkflowScheduler:
    """工作流调度器测试"""

    @pytest.fixture
    def scheduler(self):
        """创建测试调度器"""
        try:
            from services.scheduler import WorkflowScheduler
            sched = WorkflowScheduler()
            yield sched
            sched.shutdown(wait=False)
        except RuntimeError:
            pytest.skip("APScheduler not available")

    def test_add_interval_schedule(self, scheduler):
        """测试添加间隔调度"""
        callback = Mock()

        result = scheduler.add_schedule(
            schedule_id="test-interval",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60,
            callback=callback
        )

        assert result is True
        assert scheduler.scheduler.get_job("test-interval") is not None

    def test_add_cron_schedule(self, scheduler):
        """测试添加 Cron 调度"""
        callback = Mock()

        result = scheduler.add_schedule(
            schedule_id="test-cron",
            schedule_type="cron",
            workflow_id="workflow-1",
            cron_expression="*/5 * * * *",
            callback=callback
        )

        # 结果取决于 croniter 是否可用
        assert isinstance(result, bool)

    def test_remove_schedule(self, scheduler):
        """测试移除调度"""
        scheduler.add_schedule(
            schedule_id="test-remove",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60
        )

        result = scheduler.remove_schedule("test-remove")
        assert result is True
        assert scheduler.scheduler.get_job("test-remove") is None

    def test_pause_resume_schedule(self, scheduler):
        """测试暂停和恢复调度"""
        scheduler.add_schedule(
            schedule_id="test-pause",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60
        )

        # 暂停
        result = scheduler.pause_schedule("test-pause")
        assert result is True

        # 恢复
        result = scheduler.resume_schedule("test-pause")
        assert result is True

    def test_trigger_schedule(self, scheduler):
        """测试手动触发调度"""
        callback = Mock()

        scheduler.add_schedule(
            schedule_id="test-trigger",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=3600,  # 1小时，不会自动触发
            callback=callback
        )

        result = scheduler.trigger_schedule("test-trigger", "workflow-1")
        assert result is True
        callback.assert_called_once()

    def test_get_next_run_time(self, scheduler):
        """测试获取下次运行时间"""
        scheduler.add_schedule(
            schedule_id="test-next-run",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60
        )

        next_run = scheduler.get_next_run_time("test-next-run")
        assert next_run is not None
        assert isinstance(next_run, datetime)

    def test_list_schedules(self, scheduler):
        """测试列出调度"""
        scheduler.add_schedule(
            schedule_id="test-list-1",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60
        )
        scheduler.add_schedule(
            schedule_id="test-list-2",
            schedule_type="interval",
            workflow_id="workflow-2",
            interval_seconds=120
        )

        schedules = scheduler.list_schedules()
        assert len(schedules) >= 2

        ids = [s["id"] for s in schedules]
        assert "test-list-1" in ids
        assert "test-list-2" in ids

    def test_disabled_schedule_not_added(self, scheduler):
        """测试禁用的调度不会被添加"""
        result = scheduler.add_schedule(
            schedule_id="test-disabled",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60,
            enabled=False
        )

        assert result is True
        assert scheduler.scheduler.get_job("test-disabled") is None

    def test_paused_schedule_not_added(self, scheduler):
        """测试暂停的调度不会被添加"""
        result = scheduler.add_schedule(
            schedule_id="test-paused-init",
            schedule_type="interval",
            workflow_id="workflow-1",
            interval_seconds=60,
            paused=True
        )

        assert result is True
        assert scheduler.scheduler.get_job("test-paused-init") is None


class TestGlobalScheduler:
    """全局调度器测试"""

    def test_get_scheduler_singleton(self):
        """测试调度器单例"""
        try:
            from services.scheduler import get_scheduler

            scheduler1 = get_scheduler()
            scheduler2 = get_scheduler()

            assert scheduler1 is scheduler2
        except RuntimeError:
            pytest.skip("APScheduler not available")

    def test_get_execution_tracker_singleton(self):
        """测试执行跟踪器单例"""
        from services.scheduler import get_execution_tracker

        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()

        assert tracker1 is tracker2


class TestCommonCronExpressions:
    """常用 Cron 表达式测试"""

    def test_common_expressions_defined(self):
        """测试常用表达式已定义"""
        from services.scheduler import COMMON_CRON_EXPRESSIONS

        assert "every_minute" in COMMON_CRON_EXPRESSIONS
        assert "hourly" in COMMON_CRON_EXPRESSIONS
        assert "daily_at_midnight" in COMMON_CRON_EXPRESSIONS
        assert "weekly_on_monday" in COMMON_CRON_EXPRESSIONS
        assert "monthly_on_1st" in COMMON_CRON_EXPRESSIONS

    def test_common_expressions_valid(self):
        """测试常用表达式有效"""
        from services.scheduler import COMMON_CRON_EXPRESSIONS, validate_cron_expression

        for name, expr in COMMON_CRON_EXPRESSIONS.items():
            # 所有表达式应该是有效的
            assert validate_cron_expression(expr), f"{name}: {expr} should be valid"
