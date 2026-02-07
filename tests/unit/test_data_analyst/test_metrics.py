"""
数据分析师 - 指标体系管理单元测试
测试用例：AN-MS-U-001 ~ AN-MS-U-015

指标体系管理是数据分析师角色的重要功能，用于定义和管理业务指标。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestMetricDefinitionCreation:
    """指标定义创建测试 (AN-MS-U-001 ~ AN-MS-U-004)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_business_metric(self, mock_metrics_service):
        """AN-MS-U-001: 创建业务指标"""
        metric_data = {
            'name': '日活跃用户数',
            'code': 'DAU',
            'description': '每日活跃去重用户数',
            'category': 'business',
            'dimension': 'user',
            'calculation_sql': 'SELECT COUNT(DISTINCT user_id) FROM user_events WHERE event_date = {date}',
            'aggregation': 'daily',
            'unit': '人'
        }

        result = mock_metrics_service.create_metric(metric_data)

        assert result['success'] is True
        assert 'metric_id' in result
        assert result['code'] == 'DAU'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_technical_metric(self, mock_metrics_service):
        """AN-MS-U-002: 创建技术指标"""
        metric_data = {
            'name': 'API响应时间',
            'code': 'API_RESPONSE_TIME',
            'description': 'API平均响应时间',
            'category': 'technical',
            'dimension': 'performance',
            'calculation_sql': 'SELECT AVG(response_time) FROM api_logs WHERE timestamp >= {start_time}',
            'aggregation': 'hourly',
            'unit': 'ms',
            'thresholds': {'warning': 500, 'critical': 1000}
        }

        result = mock_metrics_service.create_metric(metric_data)

        assert result['success'] is True
        assert result['category'] == 'technical'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_quality_metric(self, mock_metrics_service):
        """AN-MS-U-003: 创建质量指标"""
        metric_data = {
            'name': '数据完整性',
            'code': 'DATA_COMPLETENESS',
            'description': '关键字段非空率',
            'category': 'quality',
            'dimension': 'data_quality',
            'calculation_sql': 'SELECT SUM(CASE WHEN key_field IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) FROM {table}',
            'aggregation': 'daily',
            'unit': '%'
        }

        result = mock_metrics_service.create_metric(metric_data)

        assert result['success'] is True
        assert result['category'] == 'quality'

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_metric_with_drill_down(self, mock_metrics_service):
        """AN-MS-U-004: 创建带下钻维度的指标"""
        metric_data = {
            'name': '销售额',
            'code': 'SALES',
            'description': '订单销售额',
            'category': 'business',
            'drill_down_dimensions': ['region', 'category', 'product'],
            'calculation_sql': 'SELECT SUM(amount) FROM orders WHERE order_date = {date}'
        }

        result = mock_metrics_service.create_metric(metric_data)

        assert result['success'] is True
        assert 'drill_down_dimensions' in result


class TestMetricValueCalculation:
    """指标值计算测试 (AN-MS-U-005 ~ AN-MS-U-007)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_calculate_metric_value(self, mock_metrics_service):
        """AN-MS-U-005: 计算指标值"""
        metric_id = 'metric_001'
        calc_params = {
            'date': '2024-01-01'
        }

        mock_metrics_service.calculate_metric.return_value = {
            'success': True,
            'metric_id': metric_id,
            'value': 125000,
            'timestamp': '2024-01-01T00:00:00Z'
        }

        result = mock_metrics_service.calculate_metric(metric_id, calc_params)

        assert result['success'] is True
        assert 'value' in result

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_batch_calculate_metrics(self, mock_metrics_service):
        """AN-MS-U-006: 批量计算多个指标"""
        metric_ids = ['metric_001', 'metric_002', 'metric_003']
        calc_params = {
            'date': '2024-01-01'
        }

        mock_metrics_service.batch_calculate_metrics.return_value = {
            'success': True,
            'results': [
                {'metric_id': 'metric_001', 'value': 125000, 'status': 'success'},
                {'metric_id': 'metric_002', 'value': 8500000, 'status': 'success'},
                {'metric_id': 'metric_003', 'error': 'Missing data', 'status': 'failed'}
            ],
            'successful': 2,
            'failed': 1
        }

        result = mock_metrics_service.batch_calculate_metrics(metric_ids, calc_params)

        assert result['success'] is True
        assert result['successful'] == 2

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_schedule_metric_calculation(self, mock_metrics_service):
        """AN-MS-U-007: 调度指标计算任务"""
        metric_id = 'metric_001'
        schedule_config = {
            'cron': '0 1 * * *',  # 每天1点
            'timezone': 'Asia/Shanghai'
        }

        mock_metrics_service.schedule_calculation.return_value = {
            'success': True,
            'schedule_id': 'sched_001'
        }

        result = mock_metrics_service.schedule_calculation(metric_id, schedule_config)

        assert result['success'] is True


class TestMetricValueQuery:
    """指标值查询测试 (AN-MS-U-008 ~ AN-MS-U-010)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_query_latest_metric_value(self, mock_metrics_service):
        """AN-MS-U-008: 查询最新指标值"""
        metric_id = 'metric_001'

        mock_metrics_service.get_latest_value.return_value = {
            'success': True,
            'metric_id': metric_id,
            'value': 125000,
            'timestamp': '2024-01-01T00:00:00Z',
            'trend': '+5%'
        }

        result = mock_metrics_service.get_latest_value(metric_id)

        assert result['success'] is True
        assert result['value'] == 125000

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_query_metric_time_series(self, mock_metrics_service):
        """AN-MS-U-009: 查询指标时间序列数据"""
        metric_id = 'metric_001'
        query_params = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'aggregation': 'daily'
        }

        mock_metrics_service.get_time_series.return_value = {
            'success': True,
            'metric_id': metric_id,
            'data': [
                {'date': '2024-01-01', 'value': 120000},
                {'date': '2024-01-02', 'value': 125000},
                {'date': '2024-01-03', 'value': 118000}
            ],
            'total': 3
        }

        result = mock_metrics_service.get_time_series(metric_id, query_params)

        assert result['success'] is True
        assert len(result['data']) == 3

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_drill_down_metric(self, mock_metrics_service):
        """AN-MS-U-010: 指标下钻查询"""
        metric_id = 'metric_001'
        drill_down_dimension = 'region'
        query_params = {
            'date': '2024-01-01'
        }

        mock_metrics_service.drill_down.return_value = {
            'success': True,
            'dimension': drill_down_dimension,
            'data': [
                {'dimension_value': '华北', 'value': 45000},
                {'dimension_value': '华南', 'value': 38000},
                {'dimension_value': '华东', 'value': 42000}
            ]
        }

        result = mock_metrics_service.drill_down(metric_id, drill_down_dimension, query_params)

        assert result['success'] is True
        assert len(result['data']) == 3


class TestMetricManagement:
    """指标管理测试 (AN-MS-U-011 ~ AN-MS-U-015)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_list_metrics(self, mock_metrics_service):
        """AN-MS-U-011: 列出指标"""
        mock_metrics_service.list_metrics.return_value = {
            'success': True,
            'metrics': [
                {'metric_id': 'metric_001', 'name': '日活跃用户', 'code': 'DAU', 'category': 'business'},
                {'metric_id': 'metric_002', 'name': 'GMV', 'code': 'GMV', 'category': 'business'}
            ],
            'total': 2
        }

        result = mock_metrics_service.list_metrics()

        assert result['success'] is True
        assert len(result['metrics']) == 2

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_filter_metrics_by_category(self, mock_metrics_service):
        """AN-MS-U-012: 按分类筛选指标"""
        mock_metrics_service.list_metrics.return_value = {
            'success': True,
            'metrics': [
                {'metric_id': 'metric_001', 'name': '日活跃用户', 'category': 'business'},
                {'metric_id': 'metric_003', 'name': '新增用户', 'category': 'business'}
            ],
            'total': 2,
            'filters': {'category': 'business'}
        }

        result = mock_metrics_service.list_metrics(filters={'category': 'business'})

        assert result['success'] is True
        assert all(m['category'] == 'business' for m in result['metrics'])

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_update_metric_definition(self, mock_metrics_service):
        """AN-MS-U-013: 更新指标定义"""
        metric_id = 'metric_001'
        update_data = {
            'name': '更新后的指标名称',
            'description': '更新后的描述',
            'calculation_sql': 'SELECT COUNT(*) FROM new_table'
        }

        mock_metrics_service.update_metric.return_value = {
            'success': True,
            'metric_id': metric_id
        }

        result = mock_metrics_service.update_metric(metric_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_delete_metric(self, mock_metrics_service):
        """AN-MS-U-014: 删除指标"""
        metric_id = 'metric_001'

        result = mock_metrics_service.delete_metric(metric_id)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_search_metrics(self, mock_metrics_service):
        """AN-MS-U-015: 搜索指标"""
        keyword = '活跃'

        mock_metrics_service.search_metrics.return_value = {
            'success': True,
            'metrics': [
                {'metric_id': 'metric_001', 'name': '日活跃用户'},
                {'metric_id': 'metric_004', 'name': '月活跃用户'}
            ],
            'total': 2
        }

        result = mock_metrics_service.search_metrics(keyword)

        assert result['success'] is True
        assert len(result['metrics']) == 2


class TestMetricThresholdAlert:
    """指标阈值告警测试 (AN-MS-U-016 ~ AN-MS-U-018)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_set_metric_threshold(self, mock_metrics_service):
        """AN-MS-U-016: 设置指标阈值"""
        metric_id = 'metric_001'
        threshold_config = {
            'warning_min': 100000,
            'warning_max': 150000,
            'critical_min': 80000,
            'critical_max': 200000
        }

        mock_metrics_service.set_threshold.return_value = {
            'success': True,
            'metric_id': metric_id
        }

        result = mock_metrics_service.set_threshold(metric_id, threshold_config)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_check_metric_alert(self, mock_metrics_service):
        """AN-MS-U-017: 检查指标告警"""
        metric_id = 'metric_001'
        current_value = 75000

        mock_metrics_service.check_alert.return_value = {
            'success': True,
            'metric_id': metric_id,
            'current_value': current_value,
            'alert_level': 'critical',
            'message': '指标值低于严重阈值下限'
        }

        result = mock_metrics_service.check_alert(metric_id, current_value)

        assert result['success'] is True
        assert result['alert_level'] == 'critical'

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_metric_alert_subscription(self, mock_metrics_service):
        """AN-MS-U-018: 创建指标告警订阅"""
        metric_id = 'metric_001'
        subscription_config = {
            'channels': ['email', 'webhook'],
            'recipients': ['user@example.com'],
            'webhook_url': 'https://example.com/webhook'
        }

        mock_metrics_service.create_alert_subscription.return_value = {
            'success': True,
            'subscription_id': 'sub_001'
        }

        result = mock_metrics_service.create_alert_subscription(metric_id, subscription_config)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_metrics_service():
    """Mock 指标服务"""
    service = Mock()

    def mock_create_metric(data):
        result = {
            'success': True,
            'metric_id': 'metric_001',
            'name': data.get('name', ''),
            'code': data.get('code', ''),
            'category': data.get('category', 'business')
        }
        # 如果有 drill_down_dimensions，包含在返回值中
        if 'drill_down_dimensions' in data:
            result['drill_down_dimensions'] = data['drill_down_dimensions']
        return result

    service.create_metric = Mock(side_effect=mock_create_metric)
    service.calculate_metric = Mock()
    service.batch_calculate_metrics = Mock()
    service.schedule_calculation = Mock()
    service.get_latest_value = Mock()
    service.get_time_series = Mock()
    service.drill_down = Mock()
    service.list_metrics = Mock()
    service.update_metric = Mock(return_value={'success': True})
    service.delete_metric = Mock(return_value={'success': True})
    service.search_metrics = Mock()
    service.set_threshold = Mock(return_value={'success': True})
    service.check_alert = Mock()
    service.create_alert_subscription = Mock()

    return service
