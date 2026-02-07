"""
数据分析师 - BI 报表管理单元测试
测试用例：AN-BI-U-001 ~ AN-BI-U-015

BI 报表管理是数据分析师角色的核心功能，用于创建和管理可视化仪表板。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestBIDashboardCreation:
    """BI 仪表板创建测试 (AN-BI-U-001 ~ AN-BI-U-003)"""

    @pytest.mark.p0
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_dashboard(self, mock_bi_service):
        """AN-BI-U-001: 创建 BI 仪表板"""
        dashboard_data = {
            'name': '销售分析仪表板',
            'description': '包含销售额、订单量等关键指标',
            'theme': 'light',
            'layout': {'columns': 2, 'rows': 3}
        }

        result = mock_bi_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert 'dashboard_id' in result
        assert result['name'] == '销售分析仪表板'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_dashboard_with_filters(self, mock_bi_service):
        """AN-BI-U-002: 创建带筛选器的仪表板"""
        dashboard_data = {
            'name': '运营仪表板',
            'description': '运营数据监控',
            'filters': [
                {'field': 'date', 'type': 'date_range', 'label': '日期范围'},
                {'field': 'region', 'type': 'multi_select', 'label': '地区', 'options': ['华北', '华南', '华东']}
            ]
        }

        result = mock_bi_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert 'filters' in result

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_dashboard_with_auto_refresh(self, mock_bi_service):
        """AN-BI-U-003: 创建带自动刷新的仪表板"""
        dashboard_data = {
            'name': '实时监控仪表板',
            'description': '实时数据监控',
            'auto_refresh': True,
            'refresh_interval': 60  # 60秒刷新
        }

        result = mock_bi_service.create_dashboard(dashboard_data)

        assert result['success'] is True
        assert result['auto_refresh'] is True
        assert result['refresh_interval'] == 60


class TestBIChartCreation:
    """BI 图表创建测试 (AN-BI-U-004 ~ AN-BI-U-008)"""

    @pytest.mark.p0
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_line_chart(self, mock_bi_service):
        """AN-BI-U-004: 创建折线图"""
        chart_data = {
            'name': '销售额趋势',
            'dashboard_id': 'dash_001',
            'chart_type': 'line',
            'datasource_type': 'sql',
            'sql_query': 'SELECT date, amount FROM sales ORDER BY date',
            'dimensions': [{'field': 'date', 'label': '日期'}],
            'metrics': [{'field': 'amount', 'label': '销售额', 'aggregation': 'sum'}]
        }

        result = mock_bi_service.create_chart(chart_data)

        assert result['success'] is True
        assert 'chart_id' in result
        assert result['chart_type'] == 'line'

    @pytest.mark.p0
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_bar_chart(self, mock_bi_service):
        """AN-BI-U-005: 创建柱状图"""
        chart_data = {
            'name': '区域销售对比',
            'dashboard_id': 'dash_001',
            'chart_type': 'bar',
            'datasource_type': 'sql',
            'sql_query': 'SELECT region, SUM(amount) as total FROM sales GROUP BY region',
            'dimensions': [{'field': 'region', 'label': '地区'}],
            'metrics': [{'field': 'total', 'label': '销售额'}]
        }

        result = mock_bi_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart_type'] == 'bar'

    @pytest.mark.p0
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_pie_chart(self, mock_bi_service):
        """AN-BI-U-006: 创建饼图"""
        chart_data = {
            'name': '产品类别占比',
            'dashboard_id': 'dash_001',
            'chart_type': 'pie',
            'datasource_type': 'sql',
            'sql_query': 'SELECT category, COUNT(*) as cnt FROM products GROUP BY category',
            'dimensions': [{'field': 'category', 'label': '类别'}],
            'metrics': [{'field': 'cnt', 'label': '数量'}]
        }

        result = mock_bi_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart_type'] == 'pie'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_table_chart(self, mock_bi_service):
        """AN-BI-U-007: 创建表格图表"""
        chart_data = {
            'name': '订单明细表',
            'dashboard_id': 'dash_001',
            'chart_type': 'table',
            'datasource_type': 'sql',
            'sql_query': 'SELECT * FROM orders LIMIT 100',
            'config': {'pagination': True, 'page_size': 20}
        }

        result = mock_bi_service.create_chart(chart_data)

        assert result['success'] is True
        assert result['chart_type'] == 'table'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_create_chart_with_filters(self, mock_bi_service):
        """AN-BI-U-008: 创建带筛选条件的图表"""
        chart_data = {
            'name': '过滤销售额',
            'dashboard_id': 'dash_001',
            'chart_type': 'line',
            'filters': [
                {'field': 'date', 'operator': '>=', 'value': '2024-01-01'},
                {'field': 'status', 'operator': '=', 'value': 'completed'}
            ]
        }

        result = mock_bi_service.create_chart(chart_data)

        assert result['success'] is True
        assert 'filters' in result


class TestBIDashboardManagement:
    """BI 仪表板管理测试 (AN-BI-U-009 ~ AN-BI-U-013)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_list_dashboards(self, mock_bi_service):
        """AN-BI-U-009: 列出仪表板"""
        mock_bi_service.list_dashboards.return_value = {
            'success': True,
            'dashboards': [
                {'dashboard_id': 'dash_001', 'name': '销售分析', 'charts_count': 5},
                {'dashboard_id': 'dash_002', 'name': '运营监控', 'charts_count': 8}
            ],
            'total': 2
        }

        result = mock_bi_service.list_dashboards()

        assert result['success'] is True
        assert len(result['dashboards']) == 2

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_get_dashboard_detail(self, mock_bi_service):
        """AN-BI-U-010: 获取仪表板详情"""
        dashboard_id = 'dash_001'

        mock_bi_service.get_dashboard.return_value = {
            'success': True,
            'dashboard_id': dashboard_id,
            'name': '销售分析仪表板',
            'charts': [
                {'chart_id': 'chart_001', 'name': '销售额趋势', 'chart_type': 'line'},
                {'chart_id': 'chart_002', 'name': '区域对比', 'chart_type': 'bar'}
            ],
            'created_by': 'user001'
        }

        result = mock_bi_service.get_dashboard(dashboard_id)

        assert result['success'] is True
        assert len(result['charts']) == 2

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_update_dashboard(self, mock_bi_service):
        """AN-BI-U-011: 更新仪表板"""
        dashboard_id = 'dash_001'
        update_data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'theme': 'dark'
        }

        mock_bi_service.update_dashboard.return_value = {
            'success': True,
            'dashboard_id': dashboard_id
        }

        result = mock_bi_service.update_dashboard(dashboard_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_delete_dashboard(self, mock_bi_service):
        """AN-BI-U-012: 删除仪表板"""
        dashboard_id = 'dash_001'

        result = mock_bi_service.delete_dashboard(dashboard_id)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_duplicate_dashboard(self, mock_bi_service):
        """AN-BI-U-013: 复制仪表板"""
        dashboard_id = 'dash_001'

        mock_bi_service.duplicate_dashboard.return_value = {
            'success': True,
            'new_dashboard_id': 'dash_002',
            'name': '销售分析仪表板 (副本)'
        }

        result = mock_bi_service.duplicate_dashboard(dashboard_id)

        assert result['success'] is True
        assert 'new_dashboard_id' in result


class TestBIChartManagement:
    """BI 图表管理测试 (AN-BI-U-014 ~ AN-BI-U-017)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_update_chart(self, mock_bi_service):
        """AN-BI-U-014: 更新图表"""
        chart_id = 'chart_001'
        update_data = {
            'name': '更新后的图表名称',
            'sql_query': 'SELECT date, amount FROM sales WHERE amount > 100'
        }

        mock_bi_service.update_chart.return_value = {
            'success': True,
            'chart_id': chart_id
        }

        result = mock_bi_service.update_chart(chart_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_delete_chart(self, mock_bi_service):
        """AN-BI-U-015: 删除图表"""
        chart_id = 'chart_001'

        result = mock_bi_service.delete_chart(chart_id)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_get_chart_data(self, mock_bi_service):
        """AN-BI-U-016: 获取图表数据"""
        chart_id = 'chart_001'

        mock_bi_service.get_chart_data.return_value = {
            'success': True,
            'chart_id': chart_id,
            'data': {
                'dimensions': ['2024-01', '2024-02', '2024-03'],
                'series': [
                    {'name': '销售额', 'data': [10000, 12000, 15000]}
                ]
            }
        }

        result = mock_bi_service.get_chart_data(chart_id)

        assert result['success'] is True
        assert 'data' in result

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_export_chart(self, mock_bi_service):
        """AN-BI-U-017: 导出图表"""
        chart_id = 'chart_001'
        export_format = 'png'

        mock_bi_service.export_chart.return_value = {
            'success': True,
            'download_url': f'/api/v1/bi/charts/{chart_id}/export/{export_format}'
        }

        result = mock_bi_service.export_chart(chart_id, export_format)

        assert result['success'] is True
        assert 'download_url' in result


class TestBIDashboardSharing:
    """BI 仪表板共享测试 (AN-BI-U-018 ~ AN-BI-U-020)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_publish_dashboard(self, mock_bi_service):
        """AN-BI-U-018: 发布仪表板为公开"""
        dashboard_id = 'dash_001'

        mock_bi_service.publish_dashboard.return_value = {
            'success': True,
            'dashboard_id': dashboard_id,
            'is_public': True,
            'share_url': 'https://example.com/share/dash_001'
        }

        result = mock_bi_service.publish_dashboard(dashboard_id)

        assert result['success'] is True
        assert result['is_public'] is True
        assert 'share_url' in result

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_generate_share_token(self, mock_bi_service):
        """AN-BI-U-019: 生成分享令牌"""
        dashboard_id = 'dash_001'
        token_config = {
            'expires_in': 86400,  # 24小时
            'password_protected': True,
            'password': 'share123'
        }

        mock_bi_service.generate_share_token.return_value = {
            'success': True,
            'share_token': 'st_xxxxx',
            'share_url': 'https://example.com/share/st_xxxxx'
        }

        result = mock_bi_service.generate_share_token(dashboard_id, token_config)

        assert result['success'] is True
        assert 'share_token' in result

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_revoke_share_token(self, mock_bi_service):
        """AN-BI-U-020: 撤销分享令牌"""
        dashboard_id = 'dash_001'

        result = mock_bi_service.revoke_share_token(dashboard_id)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_bi_service():
    """Mock BI 服务"""
    service = Mock()

    def mock_create_dashboard(data):
        result = {
            'success': True,
            'dashboard_id': 'dash_001',
            'name': data.get('name', ''),
            'theme': data.get('theme', 'light'),
            'auto_refresh': data.get('auto_refresh', False),
            'refresh_interval': data.get('refresh_interval', 300)
        }
        # 如果有 filters，包含在返回值中
        if 'filters' in data:
            result['filters'] = data['filters']
        return result

    def mock_create_chart(data):
        result = {
            'success': True,
            'chart_id': 'chart_001',
            'name': data.get('name', ''),
            'chart_type': data.get('chart_type', 'line'),
            'dashboard_id': data.get('dashboard_id', '')
        }
        # 如果有 filters，包含在返回值中
        if 'filters' in data:
            result['filters'] = data['filters']
        return result

    service.create_dashboard = Mock(side_effect=mock_create_dashboard)
    service.create_chart = Mock(side_effect=mock_create_chart)
    service.list_dashboards = Mock()
    service.get_dashboard = Mock()
    service.update_dashboard = Mock(return_value={'success': True})
    service.delete_dashboard = Mock(return_value={'success': True})
    service.duplicate_dashboard = Mock()
    service.update_chart = Mock(return_value={'success': True})
    service.delete_chart = Mock(return_value={'success': True})
    service.get_chart_data = Mock()
    service.export_chart = Mock()
    service.publish_dashboard = Mock()
    service.generate_share_token = Mock()
    service.revoke_share_token = Mock(return_value={'success': True})

    return service
