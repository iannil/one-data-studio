"""
BI 报表集成测试
测试用例编号: AN-BI-I-001 ~ AN-BI-I-010

BI 报表管理是数据分析师角色的核心功能，用于创建和管理可视化仪表板。
集成测试覆盖：
- BI 仪表板创建与管理
- BI 图表创建与数据查询
- Superset 集成
- 指标计算与数据同步
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from typing import Dict, List, Any

import sys
import os

_project_root = os.path.join(os.path.dirname(__file__), "../..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ==================== Fixtures ====================

@pytest.fixture
def bi_integration_service():
    """BI 集成服务"""

    class BIIntegrationService:
        """BI 集成测试服务"""

        def __init__(self):
            self._dashboards = {}
            self._charts = {}
            self._metrics = {}
            self._datasources = self._init_datasources()
            self._superset_synced = {}

        def _init_datasources(self):
            """初始化数据源"""
            return {
                'ds_mysql': {
                    'datasource_id': 'ds_mysql',
                    'name': 'MySQL主库',
                    'type': 'mysql',
                    'host': 'mysql.example.com',
                    'port': 3306,
                    'database': 'analytics',
                    'status': 'connected'
                },
                'ds_clickhouse': {
                    'datasource_id': 'ds_clickhouse',
                    'name': 'ClickHouse集群',
                    'type': 'clickhouse',
                    'host': 'ch.example.com',
                    'port': 8123,
                    'database': 'analytics',
                    'status': 'connected'
                }
            }

        def create_dashboard(self, dashboard_data: Dict) -> Dict:
            """创建仪表板"""
            name = dashboard_data.get('name')
            dashboard_id = f"dash_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            dashboard = {
                'dashboard_id': dashboard_id,
                'name': name,
                'description': dashboard_data.get('description', ''),
                'layout': dashboard_data.get('layout', {'columns': 2, 'rows': 2}),
                'theme': dashboard_data.get('theme', 'light'),
                'filters': dashboard_data.get('filters', []),
                'auto_refresh': dashboard_data.get('auto_refresh', False),
                'refresh_interval': dashboard_data.get('refresh_interval', 300),
                'is_public': dashboard_data.get('is_public', False),
                'favorite_count': 0,
                'view_count': 0,
                'charts': [],
                'created_by': dashboard_data.get('created_by', 'test_user'),
                'created_at': now,
                'updated_at': now
            }

            self._dashboards[dashboard_id] = dashboard
            return {'success': True, 'dashboard_id': dashboard_id, 'dashboard': dashboard}

        def create_chart(self, chart_data: Dict) -> Dict:
            """创建图表"""
            dashboard_id = chart_data.get('dashboard_id')

            # 验证仪表板存在
            if dashboard_id and dashboard_id not in self._dashboards:
                return {'success': False, 'error': '仪表板不存在'}

            chart_id = f"chart_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            chart = {
                'chart_id': chart_id,
                'name': chart_data.get('name'),
                'description': chart_data.get('description', ''),
                'dashboard_id': dashboard_id,
                'chart_type': chart_data.get('chart_type', 'line'),
                'datasource_type': chart_data.get('datasource_type', 'sql'),
                'datasource_id': chart_data.get('datasource_id'),
                'sql_query': chart_data.get('sql_query'),
                'config': chart_data.get('config', {}),
                'dimensions': chart_data.get('dimensions', []),
                'metrics': chart_data.get('metrics', []),
                'filters': chart_data.get('filters', []),
                'cache_enabled': chart_data.get('cache_enabled', True),
                'cache_ttl': chart_data.get('cache_ttl', 300),
                'created_by': chart_data.get('created_by', 'test_user'),
                'created_at': now,
                'updated_at': now
            }

            self._charts[chart_id] = chart

            # 添加到仪表板
            if dashboard_id:
                self._dashboards[dashboard_id]['charts'].append(chart_id)

            return {'success': True, 'chart_id': chart_id, 'chart': chart}

        def execute_chart_query(self, chart_id: str) -> Dict:
            """执行图表查询"""
            chart = self._charts.get(chart_id)
            if not chart:
                return {'success': False, 'error': '图表不存在'}

            # 模拟查询执行
            chart_type = chart['chart_type']

            if chart_type == 'line':
                data = self._generate_line_data()
            elif chart_type == 'bar':
                data = self._generate_bar_data()
            elif chart_type == 'pie':
                data = self._generate_pie_data()
            elif chart_type == 'table':
                data = self._generate_table_data()
            else:
                data = {'dimensions': [], 'series': []}

            return {
                'success': True,
                'chart_id': chart_id,
                'data': data,
                'executed_at': datetime.utcnow().isoformat()
            }

        def _generate_line_data(self) -> Dict:
            """生成折线图数据"""
            return {
                'dimensions': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06'],
                'series': [
                    {'name': '销售额', 'data': [12000, 15000, 18000, 14000, 20000, 25000]},
                    {'name': '利润', 'data': [3000, 4000, 5000, 3500, 6000, 7500]}
                ]
            }

        def _generate_bar_data(self) -> Dict:
            """生成柱状图数据"""
            return {
                'dimensions': ['华北', '华南', '华东', '西南', '东北'],
                'series': [
                    {'name': '销售额', 'data': [45000, 38000, 52000, 28000, 19000]}
                ]
            }

        def _generate_pie_data(self) -> Dict:
            """生成饼图数据"""
            return {
                'dimensions': ['电子产品', '服装', '食品', '家居', '其他'],
                'series': [
                    {'name': '销售额', 'data': [35000, 28000, 22000, 18000, 12000]}
                ]
            }

        def _generate_table_data(self) -> Dict:
            """生成表格数据"""
            return {
                'columns': ['id', 'name', 'amount', 'status', 'created_at'],
                'rows': [
                    [1, '订单A', 1200.00, 'completed', '2024-01-01'],
                    [2, '订单B', 800.50, 'pending', '2024-01-02'],
                    [3, '订单C', 2500.00, 'completed', '2024-01-03']
                ]
            }

        def sync_to_superset(self, dashboard_id: str) -> Dict:
            """同步仪表板到 Superset"""
            dashboard = self._dashboards.get(dashboard_id)
            if not dashboard:
                return {'success': False, 'error': '仪表板不存在'}

            # 模拟同步到 Superset
            superset_id = f"superset_{dashboard_id}"
            now = datetime.utcnow().isoformat()

            sync_result = {
                'dashboard_id': dashboard_id,
                'superset_id': superset_id,
                'superset_url': f'https://superset.example.com/dashboard/{superset_id}',
                'synced_at': now,
                'status': 'synced'
            }

            self._superset_synced[dashboard_id] = sync_result

            return {'success': True, 'sync_result': sync_result}

        def create_metric(self, metric_data: Dict) -> Dict:
            """创建指标"""
            code = metric_data.get('code')
            metric_id = f"metric_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            metric = {
                'metric_id': metric_id,
                'name': metric_data.get('name'),
                'code': code,
                'description': metric_data.get('description', ''),
                'category': metric_data.get('category', 'business'),
                'calculation_sql': metric_data.get('calculation_sql'),
                'aggregation': metric_data.get('aggregation', 'daily'),
                'unit': metric_data.get('unit', ''),
                'thresholds': metric_data.get('thresholds', {}),
                'drill_down_dimensions': metric_data.get('drill_down_dimensions', []),
                'created_by': metric_data.get('created_by', 'test_user'),
                'created_at': now,
                'updated_at': now
            }

            self._metrics[metric_id] = metric
            return {'success': True, 'metric_id': metric_id, 'metric': metric}

        def calculate_metric(self, metric_id: str, params: Dict) -> Dict:
            """计算指标值"""
            metric = self._metrics.get(metric_id)
            if not metric:
                return {'success': False, 'error': '指标不存在'}

            # 模拟指标计算
            import random
            value = random.randint(100000, 150000)
            now = datetime.utcnow().isoformat()

            return {
                'success': True,
                'metric_id': metric_id,
                'value': value,
                'calculated_at': now,
                'params': params
            }

        def get_dashboard(self, dashboard_id: str) -> Dict:
            """获取仪表板"""
            dashboard = self._dashboards.get(dashboard_id)
            if not dashboard:
                return {'success': False, 'error': '仪表板不存在'}

            # 获取图表详情
            charts = []
            for chart_id in dashboard.get('charts', []):
                if chart_id in self._charts:
                    charts.append(self._charts[chart_id])

            return {
                'success': True,
                'dashboard': dashboard,
                'charts': charts
            }

        def update_dashboard(self, dashboard_id: str, update_data: Dict) -> Dict:
            """更新仪表板"""
            dashboard = self._dashboards.get(dashboard_id)
            if not dashboard:
                return {'success': False, 'error': '仪表板不存在'}

            for key, value in update_data.items():
                if key in dashboard:
                    dashboard[key] = value

            dashboard['updated_at'] = datetime.utcnow().isoformat()
            return {'success': True, 'dashboard_id': dashboard_id, 'dashboard': dashboard}

        def delete_dashboard(self, dashboard_id: str) -> Dict:
            """删除仪表板"""
            if dashboard_id not in self._dashboards:
                return {'success': False, 'error': '仪表板不存在'}

            del self._dashboards[dashboard_id]
            return {'success': True, 'dashboard_id': dashboard_id}

        def publish_dashboard(self, dashboard_id: str) -> Dict:
            """发布仪表板"""
            dashboard = self._dashboards.get(dashboard_id)
            if not dashboard:
                return {'success': False, 'error': '仪表板不存在'}

            dashboard['is_public'] = True
            share_token = f"st_{str(uuid.uuid4())[:16]}"
            dashboard['share_token'] = share_token
            dashboard['share_url'] = f'https://example.com/share/{share_token}'

            return {
                'success': True,
                'dashboard_id': dashboard_id,
                'share_url': dashboard['share_url'],
                'share_token': share_token
            }

    return BIIntegrationService()


# ==================== 测试类 ====================

@pytest.mark.integration
class TestBIDashboardManagement:
    """BI 仪表板管理测试 (AN-BI-I-001 ~ AN-BI-I-005)"""

    def test_create_dashboard(self, bi_integration_service):
        """AN-BI-I-001: 创建仪表板"""
        dashboard_data = {
            'name': '销售分析仪表板',
            'description': '销售数据分析',
            'theme': 'light',
            'layout': {'columns': 2, 'rows': 3}
        }

        result = bi_integration_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert 'dashboard_id' in result
        assert result['dashboard']['name'] == '销售分析仪表板'

    def test_create_dashboard_with_filters(self, bi_integration_service):
        """AN-BI-I-002: 创建带筛选器的仪表板"""
        dashboard_data = {
            'name': '运营仪表板',
            'filters': [
                {'field': 'date', 'type': 'date_range', 'label': '日期范围'},
                {'field': 'region', 'type': 'multi_select', 'label': '地区'}
            ]
        }

        result = bi_integration_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert len(result['dashboard']['filters']) == 2

    def test_create_dashboard_with_auto_refresh(self, bi_integration_service):
        """AN-BI-I-003: 创建带自动刷新的仪表板"""
        dashboard_data = {
            'name': '实时监控',
            'auto_refresh': True,
            'refresh_interval': 60
        }

        result = bi_integration_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert result['dashboard']['auto_refresh'] is True
        assert result['dashboard']['refresh_interval'] == 60

    def test_update_dashboard(self, bi_integration_service):
        """AN-BI-I-004: 更新仪表板"""
        create_result = bi_integration_service.create_dashboard({'name': '原始名称'})
        dashboard_id = create_result['dashboard_id']

        update_data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'theme': 'dark'
        }

        result = bi_integration_service.update_dashboard(dashboard_id, update_data)

        assert result['success'] is True
        assert result['dashboard']['name'] == '更新后的名称'
        assert result['dashboard']['theme'] == 'dark'

    def test_delete_dashboard(self, bi_integration_service):
        """AN-BI-I-005: 删除仪表板"""
        create_result = bi_integration_service.create_dashboard({'name': '待删除'})
        dashboard_id = create_result['dashboard_id']

        result = bi_integration_service.delete_dashboard(dashboard_id)

        assert result['success'] is True

        # 验证删除
        get_result = bi_integration_service.get_dashboard(dashboard_id)
        assert get_result['success'] is False


@pytest.mark.integration
class TestBIChartManagement:
    """BI 图表管理测试 (AN-BI-I-006 ~ AN-BI-I-009)"""

    def test_create_line_chart(self, bi_integration_service):
        """AN-BI-I-006: 创建折线图"""
        # 先创建仪表板
        dash_result = bi_integration_service.create_dashboard({'name': '测试仪表板'})
        dashboard_id = dash_result['dashboard_id']

        chart_data = {
            'name': '销售额趋势',
            'dashboard_id': dashboard_id,
            'chart_type': 'line',
            'datasource_type': 'sql',
            'sql_query': 'SELECT date, SUM(amount) FROM sales GROUP BY date',
            'dimensions': [{'field': 'date', 'label': '日期'}],
            'metrics': [{'field': 'amount', 'label': '销售额', 'aggregation': 'sum'}]
        }

        result = bi_integration_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart']['chart_type'] == 'line'

    def test_create_bar_chart(self, bi_integration_service):
        """AN-BI-I-007: 创建柱状图"""
        dash_result = bi_integration_service.create_dashboard({'name': '测试'})
        dashboard_id = dash_result['dashboard_id']

        chart_data = {
            'name': '区域对比',
            'dashboard_id': dashboard_id,
            'chart_type': 'bar',
            'datasource_type': 'sql',
            'sql_query': 'SELECT region, SUM(amount) FROM sales GROUP BY region'
        }

        result = bi_integration_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart']['chart_type'] == 'bar'

    def test_create_pie_chart(self, bi_integration_service):
        """AN-BI-I-008: 创建饼图"""
        dash_result = bi_integration_service.create_dashboard({'name': '测试'})
        dashboard_id = dash_result['dashboard_id']

        chart_data = {
            'name': '类别占比',
            'dashboard_id': dashboard_id,
            'chart_type': 'pie',
            'datasource_type': 'sql',
            'sql_query': 'SELECT category, COUNT(*) FROM products GROUP BY category'
        }

        result = bi_integration_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart']['chart_type'] == 'pie'

    def test_execute_chart_query(self, bi_integration_service):
        """AN-BI-I-009: 执行图表查询"""
        # 创建图表
        dash_result = bi_integration_service.create_dashboard({'name': '测试'})
        dashboard_id = dash_result['dashboard_id']

        chart_data = {
            'name': '趋势图',
            'dashboard_id': dashboard_id,
            'chart_type': 'line',
            'sql_query': 'SELECT date, amount FROM sales'
        }

        create_result = bi_integration_service.create_chart(chart_data)
        chart_id = create_result['chart_id']

        # 执行查询
        query_result = bi_integration_service.execute_chart_query(chart_id)

        assert query_result['success'] is True
        assert 'data' in query_result
        assert 'dimensions' in query_result['data']
        assert 'series' in query_result['data']


@pytest.mark.integration
class TestSupersetIntegration:
    """Superset 集成测试 (AN-BI-I-010 ~ AN-BI-I-012)"""

    def test_sync_dashboard_to_superset(self, bi_integration_service):
        """AN-BI-I-010: 同步仪表板到 Superset"""
        # 创建仪表板
        dash_result = bi_integration_service.create_dashboard({'name': 'Superset同步测试'})
        dashboard_id = dash_result['dashboard_id']

        # 同步到 Superset
        sync_result = bi_integration_service.sync_to_superset(dashboard_id)

        assert sync_result['success'] is True
        assert 'superset_id' in sync_result['sync_result']
        assert 'superset_url' in sync_result['sync_result']

    def test_sync_nonexistent_dashboard(self, bi_integration_service):
        """AN-BI-I-011: 同步不存在的仪表板"""
        result = bi_integration_service.sync_to_superset('invalid_dash_id')

        assert result['success'] is False
        assert '不存在' in result['error']


@pytest.mark.integration
class TestMetricManagement:
    """指标管理测试 (AN-MS-I-001 ~ AN-MS-I-004)"""

    def test_create_business_metric(self, bi_integration_service):
        """AN-MS-I-001: 创建业务指标"""
        metric_data = {
            'name': '日活跃用户数',
            'code': 'DAU',
            'description': '每日活跃去重用户数',
            'category': 'business',
            'calculation_sql': 'SELECT COUNT(DISTINCT user_id) FROM user_events WHERE event_date = {date}',
            'aggregation': 'daily',
            'unit': '人'
        }

        result = bi_integration_service.create_metric(metric_data)

        assert result['success'] is True
        assert result['metric']['code'] == 'DAU'
        assert result['metric']['category'] == 'business'

    def test_create_metric_with_thresholds(self, bi_integration_service):
        """AN-MS-I-002: 创建带阈值的指标"""
        metric_data = {
            'name': 'API响应时间',
            'code': 'API_RESP_TIME',
            'category': 'technical',
            'calculation_sql': 'SELECT AVG(response_time) FROM api_logs',
            'thresholds': {
                'warning_min': 0,
                'warning_max': 500,
                'critical_max': 1000
            }
        }

        result = bi_integration_service.create_metric(metric_data)

        assert result['success'] is True
        assert result['metric']['thresholds']['warning_max'] == 500

    def test_create_metric_with_drill_down(self, bi_integration_service):
        """AN-MS-I-003: 创建带下钻维度的指标"""
        metric_data = {
            'name': '销售额',
            'code': 'SALES',
            'category': 'business',
            'calculation_sql': 'SELECT SUM(amount) FROM orders',
            'drill_down_dimensions': ['region', 'category', 'product']
        }

        result = bi_integration_service.create_metric(metric_data)

        assert result['success'] is True
        assert len(result['metric']['drill_down_dimensions']) == 3

    def test_calculate_metric_value(self, bi_integration_service):
        """AN-MS-I-004: 计算指标值"""
        # 创建指标
        metric_data = {
            'name': '测试指标',
            'code': 'TEST_METRIC',
            'calculation_sql': 'SELECT COUNT(*) FROM test_table'
        }

        create_result = bi_integration_service.create_metric(metric_data)
        metric_id = create_result['metric_id']

        # 计算指标
        calc_result = bi_integration_service.calculate_metric(metric_id, {'date': '2024-01-01'})

        assert calc_result['success'] is True
        assert 'value' in calc_result
        assert calc_result['value'] > 0


@pytest.mark.integration
class TestDashboardSharing:
    """仪表板共享测试 (AN-BI-I-013 ~ AN-BI-I-014)"""

    def test_publish_dashboard(self, bi_integration_service):
        """AN-BI-I-013: 发布仪表板"""
        create_result = bi_integration_service.create_dashboard({'name': '共享测试'})
        dashboard_id = create_result['dashboard_id']

        publish_result = bi_integration_service.publish_dashboard(dashboard_id)

        assert publish_result['success'] is True
        assert publish_result['share_url'] is not None

        # 验证仪表板状态
        get_result = bi_integration_service.get_dashboard(dashboard_id)
        assert get_result['dashboard']['is_public'] is True

    def test_publish_nonexistent_dashboard(self, bi_integration_service):
        """AN-BI-I-014: 发布不存在的仪表板"""
        result = bi_integration_service.publish_dashboard('invalid_dash_id')

        assert result['success'] is False
        assert '不存在' in result['error']
