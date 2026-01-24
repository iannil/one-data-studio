"""
Celery 应用模块单元测试
Sprint 8: P2 测试覆盖 - 异步任务处理
"""

import pytest
from unittest.mock import patch, MagicMock


class TestTaskStatus:
    """任务状态测试"""

    def test_task_status_values(self):
        """测试任务状态值"""
        from services.shared.celery_app import TaskStatus

        assert TaskStatus.PENDING == 'PENDING'
        assert TaskStatus.STARTED == 'STARTED'
        assert TaskStatus.SUCCESS == 'SUCCESS'
        assert TaskStatus.FAILURE == 'FAILURE'
        assert TaskStatus.RETRY == 'RETRY'
        assert TaskStatus.REVOKED == 'REVOKED'


class TestTaskResult:
    """任务结果测试"""

    def test_task_result_success(self):
        """测试成功任务结果"""
        from services.shared.celery_app import TaskResult

        result = TaskResult(
            success=True,
            data={'count': 10},
            metadata={'source': 'test'}
        )

        assert result.success is True
        assert result.data == {'count': 10}
        assert result.error is None

    def test_task_result_failure(self):
        """测试失败任务结果"""
        from services.shared.celery_app import TaskResult

        result = TaskResult(
            success=False,
            error='Connection failed'
        )

        assert result.success is False
        assert result.error == 'Connection failed'

    def test_task_result_to_dict(self):
        """测试任务结果转字典"""
        from services.shared.celery_app import TaskResult

        result = TaskResult(
            success=True,
            data={'id': 1},
            metadata={'key': 'value'}
        )

        data = result.to_dict()

        assert data['success'] is True
        assert data['data'] == {'id': 1}
        assert data['metadata'] == {'key': 'value'}


class TestTaskManager:
    """任务管理器测试"""

    @pytest.fixture
    def mock_celery(self):
        """Mock Celery 应用"""
        with patch('services.shared.celery_app.celery_app') as mock:
            yield mock

    def test_submit_task(self, mock_celery):
        """测试提交任务"""
        from services.shared.celery_app import TaskManager

        mock_result = MagicMock()
        mock_result.id = 'task-123'
        mock_celery.send_task.return_value = mock_result

        manager = TaskManager()
        task_id = manager.submit_task('test_task', 'arg1', key='value')

        assert task_id == 'task-123'
        mock_celery.send_task.assert_called_once()

    def test_get_task_status(self, mock_celery):
        """测试获取任务状态"""
        from services.shared.celery_app import TaskManager

        with patch('services.shared.celery_app.AsyncResult') as MockAsyncResult:
            mock_result = MagicMock()
            mock_result.state = 'SUCCESS'
            mock_result.ready.return_value = True
            mock_result.failed.return_value = False
            mock_result.result = {'data': 'value'}
            mock_result.info = {}
            MockAsyncResult.return_value = mock_result

            manager = TaskManager()
            status = manager.get_task_status('task-123')

            assert status['task_id'] == 'task-123'
            assert status['status'] == 'SUCCESS'
            assert status['result'] == {'data': 'value'}

    def test_revoke_task(self, mock_celery):
        """测试撤销任务"""
        from services.shared.celery_app import TaskManager

        manager = TaskManager()
        manager.revoke_task('task-123', terminate=True)

        mock_celery.control.revoke.assert_called_once_with('task-123', terminate=True)


class TestGetTaskManager:
    """获取任务管理器测试"""

    def test_get_task_manager_singleton(self):
        """测试任务管理器单例"""
        from services.shared.celery_app import get_task_manager, _task_manager

        # 重置全局变量
        import services.shared.celery_app as module
        module._task_manager = None

        manager1 = get_task_manager()
        manager2 = get_task_manager()

        assert manager1 is manager2


class TestAsyncTaskDecorator:
    """异步任务装饰器测试"""

    def test_async_task_decorator(self):
        """测试异步任务装饰器"""
        from services.shared.celery_app import async_task

        @async_task('test.task', queue='test')
        def my_task(x, y):
            return x + y

        # 装饰后应该有这些属性
        assert hasattr(my_task, 'submit_async')
        assert hasattr(my_task, 'submit_apply')
        assert hasattr(my_task, 'task')
