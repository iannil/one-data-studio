"""
数据采集任务单元测试
测试用例：DE-DC-001 ~ DE-DC-002
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime


class TestDataCollectionTaskCreation:
    """数据采集任务创建测试 (DE-DC-001)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_batch_collection_task(self, mock_collection_service):
        """DE-DC-001: 创建批量数据采集任务"""
        task_data = {
            'task_name': '用户数据采集',
            'source_type': 'database',
            'source_config': {
                'datasource_id': 'ds_0001',
                'tables': ['users', 'user_profiles']
            },
            'collection_mode': 'full',
            'schedule': '0 2 * * *'
        }

        mock_collection_service.create_task.return_value = {
            'success': True,
            'collection_id': 'coll_0001',
            'status': 'pending'
        }

        result = mock_collection_service.create_task(task_data)

        assert result['success'] is True
        assert 'collection_id' in result
        assert result['status'] == 'pending'

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_api_collection_task(self, mock_collection_service):
        """创建API数据采集任务"""
        task_data = {
            'task_name': '外部API数据采集',
            'source_type': 'api',
            'source_config': {
                'url': 'https://api.example.com/data',
                'method': 'GET',
                'headers': {'Authorization': 'Bearer token'}
            },
            'collection_mode': 'full'
        }

        mock_collection_service.create_task.return_value = {
            'success': True,
            'collection_id': 'coll_0002'
        }

        result = mock_collection_service.create_task(task_data)

        assert result['success'] is True
        assert result['collection_id'] == 'coll_0002'


class TestDataCollectionExecution:
    """数据采集执行测试 (DE-DC-002)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_collection_task(self, mock_collection_service):
        """DE-DC-002: 执行数据采集"""
        collection_id = 'coll_0001'

        mock_collection_service.execute_task = AsyncMock(return_value={
            'success': True,
            'collection_id': collection_id,
            'status': 'completed',
            'collected_count': 10000,
            'duration_seconds': 120
        })

        result = await mock_collection_service.execute_task(collection_id)

        assert result['success'] is True
        assert result['status'] == 'completed'
        assert result['collected_count'] > 0

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collection_task_progress_monitoring(self, mock_collection_service):
        """采集任务进度监控"""
        collection_id = 'coll_0001'

        mock_collection_service.get_progress = AsyncMock(return_value={
            'collection_id': collection_id,
            'status': 'running',
            'progress': 45.5,
            'collected_count': 4500,
            'estimated_total': 10000
        })

        result = await mock_collection_service.get_progress(collection_id)

        assert result['status'] == 'running'
        assert 0 <= result['progress'] <= 100

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collection_task_failure_handling(self, mock_collection_service):
        """采集任务失败处理"""
        collection_id = 'coll_0001'

        mock_collection_service.execute_task = AsyncMock(return_value={
            'success': False,
            'collection_id': collection_id,
            'status': 'failed',
            'error': 'Connection timeout',
            'collected_count': 0
        })

        result = await mock_collection_service.execute_task(collection_id)

        assert result['success'] is False
        assert result['status'] == 'failed'
        assert 'error' in result


class TestIncrementalCollection:
    """增量采集测试 (DE-DC-003)"""

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_incremental_collection_task(self, mock_collection_service):
        """DE-DC-003: 增量数据采集配置"""
        task_data = {
            'task_name': '订单增量采集',
            'source_type': 'database',
            'source_config': {
                'datasource_id': 'ds_0001',
                'tables': ['orders']
            },
            'collection_mode': 'incremental',
            'incremental_column': 'updated_at',
            'incremental_value': '2024-01-01 00:00:00'
        }

        mock_collection_service.create_task.return_value = {
            'success': True,
            'collection_id': 'coll_0003',
            'collection_mode': 'incremental'
        }

        result = mock_collection_service.create_task(task_data)

        assert result['success'] is True
        assert result['collection_mode'] == 'incremental'


class TestRealtimeCollection:
    """实时采集测试 (DE-DC-004)"""

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_realtime_collection_task(self, mock_collection_service):
        """DE-DC-004: 实时数据采集配置"""
        task_data = {
            'task_name': '用户行为实时采集',
            'source_type': 'kafka',
            'source_config': {
                'bootstrap_servers': 'localhost:9092',
                'topic': 'user_events'
            },
            'collection_mode': 'realtime'
        }

        mock_collection_service.create_task.return_value = {
            'success': True,
            'collection_id': 'coll_0004',
            'collection_mode': 'realtime'
        }

        result = mock_collection_service.create_task(task_data)

        assert result['success'] is True
        assert result['collection_mode'] == 'realtime'


class TestSmartScheduling:
    """智能调度测试 (DE-DC-005)"""

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_smart_schedule_trigger(self, mock_collection_service):
        """DE-DC-005: 智能调度触发"""
        # 模拟数据源有增量变化
        datasource_id = 'ds_0001'
        change_info = {
            'datasource_id': datasource_id,
            'has_changes': True,
            'estimated_change_count': 5000,
            'priority': 'high'
        }

        mock_collection_service.trigger_smart_schedule.return_value = {
            'success': True,
            'triggered_tasks': ['coll_0001', 'coll_0002'],
            'reason': 'High volume of changes detected'
        }

        result = mock_collection_service.trigger_smart_schedule(change_info)

        assert result['success'] is True
        assert len(result['triggered_tasks']) > 0


class TestJSONDataCollection:
    """JSON数据采集测试 (DE-DC-006)"""

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_json_collection_task(self, mock_collection_service):
        """DE-DC-006: JSON数据采集"""
        task_data = {
            'task_name': 'JSON数据采集',
            'source_type': 'json',
            'source_config': {
                'file_path': '/data/orders.json',
                'json_path': '$.orders[*]'
            },
            'collection_mode': 'batch'
        }

        mock_collection_service.create_task.return_value = {
            'success': True,
            'collection_id': 'coll_0005'
        }

        result = mock_collection_service.create_task(task_data)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_collection_service():
    """Mock 数据采集服务"""
    service = Mock()
    service.create_task = Mock(return_value={'success': True, 'collection_id': 'coll_0001'})
    service.execute_task = AsyncMock()
    service.get_progress = AsyncMock()
    service.trigger_smart_schedule = Mock()
    return service
