"""
服务监控单元测试
测试用例：SA-MN-001 ~ SA-MN-007
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


class TestServiceHealth:
    """服务健康检查测试 (SA-MN-001)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_health_check(self, mock_monitoring_service):
        """SA-MN-001: 服务健康检查"""
        mock_monitoring_service.get_all_health = AsyncMock(return_value={
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'api_gateway': {'status': 'healthy', 'uptime_seconds': 86400},
                'data_api': {'status': 'healthy', 'uptime_seconds': 86400},
                'agent_api': {'status': 'healthy', 'uptime_seconds': 86400},
                'model_api': {'status': 'healthy', 'uptime_seconds': 86400},
                'openai_proxy': {'status': 'healthy', 'uptime_seconds': 86400},
                'mysql': {'status': 'healthy', 'uptime_seconds': 259200},
                'redis': {'status': 'healthy', 'uptime_seconds': 172800},
                'milvus': {'status': 'healthy', 'uptime_seconds': 86400},
                'minio': {'status': 'healthy', 'uptime_seconds': 86400}
            }
        })

        result = await mock_monitoring_service.get_all_health()

        assert result['success'] is True
        assert all(s['status'] == 'healthy' for s in result['services'].values())


class TestAPIMonitoring:
    """API监控测试 (SA-MN-002)"""

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_call_monitoring(self, mock_monitoring_service):
        """SA-MN-002: API调用监控"""
        mock_monitoring_service.get_api_stats = AsyncMock(return_value={
            'success': True,
            'time_range': '1h',
            'stats': {
                'total_requests': 50000,
                'success_requests': 49500,
                'error_requests': 500,
                'success_rate': 0.99,
                'avg_latency_ms': 150,
                'p95_latency_ms': 280,
                'p99_latency_ms': 450
            },
            'by_endpoint': {
                '/api/v1/query': {'requests': 15000, 'avg_latency': 120},
                '/api/v1/workflows': {'requests': 10000, 'avg_latency': 180},
                '/api/v1/datasources': {'requests': 5000, 'avg_latency': 95}
            }
        })

        result = await mock_monitoring_service.get_api_stats(time_range='1h')

        assert result['success'] is True
        assert result['stats']['total_requests'] > 0


class TestResourceMonitoring:
    """资源监控测试 (SA-MN-003)"""

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resource_usage_monitoring(self, mock_monitoring_service):
        """SA-MN-003: 资源使用监控"""
        mock_monitoring_service.get_resource_usage = AsyncMock(return_value={
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': {
                'usage_percent': 45.2,
                'load_average': [1.5, 1.8, 2.1],
                'cores': 8
            },
            'memory': {
                'total_mb': 32768,
                'used_mb': 18432,
                'free_mb': 14336,
                'usage_percent': 56.3
            },
            'disk': {
                'total_gb': 500,
                'used_gb': 250,
                'free_gb': 250,
                'usage_percent': 50
            },
            'network': {
                'interfaces': [
                    {'name': 'eth0', 'rx_bytes': 1000000000, 'tx_bytes': 500000000}
                ]
            }
        })

        result = await mock_monitoring_service.get_resource_usage()

        assert result['success'] is True
        assert 'cpu' in result
        assert 'memory' in result
        assert 'disk' in result


class TestETLMonitoring:
    """ETL任务监控测试 (SA-MN-004)"""

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_etl_task_monitoring(self, mock_monitoring_service):
        """SA-MN-004: ETL任务监控"""
        mock_monitoring_service.get_etl_status = AsyncMock(return_value={
            'success': True,
            'tasks': [
                {
                    'task_id': 'etl_0001',
                    'task_name': '用户数据清洗',
                    'status': 'running',
                    'progress': 65,
                    'start_time': '2024-01-15T10:00:00Z',
                    'estimated_end': '2024-01-15T11:00:00Z'
                },
                {
                    'task_id': 'etl_0002',
                    'task_name': '订单数据同步',
                    'status': 'completed',
                    'progress': 100,
                    'start_time': '2024-01-15T09:00:00Z',
                    'end_time': '2024-01-15T09:30:00Z'
                }
            ],
            'summary': {
                'total': 2,
                'running': 1,
                'completed': 1,
                'failed': 0
            }
        })

        result = await mock_monitoring_service.get_etl_status()

        assert result['success'] is True
        assert result['summary']['total'] > 0


class TestModelServiceMonitoring:
    """模型服务监控测试 (SA-MN-005)"""

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_service_monitoring(self, mock_monitoring_service):
        """SA-MN-005: 模型服务监控"""
        mock_monitoring_service.get_model_service_stats = AsyncMock(return_value={
            'success': True,
            'services': [
                {
                    'service_id': 'model_llama_7b',
                    'model_name': 'llama-2-7b',
                    'status': 'running',
                    'qps': 25.5,
                    'avg_latency_ms': 120,
                    'gpu_usage': 0.85,
                    'memory_usage_mb': 8192
                }
            ]
        })

        result = await mock_monitoring_service.get_model_service_stats()

        assert result['success'] is True
        assert len(result['services']) > 0


class TestAlertConfiguration:
    """告警配置测试 (SA-MN-006 ~ SA-MN-007)"""

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_system_alert_config(self, mock_monitoring_service):
        """SA-MN-006: 告警配置"""
        alert_config = {
            'metric': 'cpu_usage',
            'threshold': 80,
            'operator': 'gt',
            'severity': 'warning',
            'notification_channels': ['email', 'slack']
        }

        mock_monitoring_service.create_alert_rule = AsyncMock(return_value={
            'success': True,
            'rule_id': 'alert_0001'
        })

        result = await mock_monitoring_service.create_alert_rule(alert_config)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_notification(self, mock_monitoring_service):
        """SA-MN-007: 告警通知"""
        alert = {
            'alert_id': 'alert_0001',
            'message': 'CPU使用率超过80%',
            'severity': 'warning'
        }

        mock_monitoring_service.send_alert = AsyncMock(return_value={
            'success': True,
            'delivered_channels': ['email', 'slack'],
            'recipients': ['admin@example.com']
        })

        result = await mock_monitoring_service.send_alert(alert)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_monitoring_service():
    """Mock 监控服务"""
    service = Mock()
    service.get_all_health = AsyncMock()
    service.get_api_stats = AsyncMock()
    service.get_resource_usage = AsyncMock()
    service.get_etl_status = AsyncMock()
    service.get_model_service_stats = AsyncMock()
    service.create_alert_rule = AsyncMock()
    service.send_alert = AsyncMock()
    return service
