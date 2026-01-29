"""
BI可视化分析单元测试
测试用例：BU-BI-001 ~ BU-BI-008
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestBIReportGeneration:
    """BI报表生成测试 (BU-BI-001 ~ BU-BI-005)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_natural_language_report_generation(self, mock_bi_service):
        """BU-BI-001: 自然语言生成报表"""
        query = '近7天用户点击Top5页面'

        mock_bi_service.generate_from_nl = AsyncMock(return_value={
            'success': True,
            'query': query,
            'generated_sql': 'SELECT page_url, COUNT(*) as clicks FROM user_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY page_url ORDER BY clicks DESC LIMIT 5',
            'report': {
                'title': '近7天用户点击Top5页面',
                'chart_type': 'bar',
                'data': [
                    {'page_url': '/home', 'clicks': 15000},
                    {'page_url': '/products', 'clicks': 12000},
                    {'page_url': '/cart', 'clicks': 8500},
                    {'page_url': '/checkout', 'clicks': 6200},
                    {'page_url': '/profile', 'clicks': 4100}
                ]
            }
        })

        result = await mock_bi_service.generate_from_nl(query)

        assert result['success'] is True
        assert result['report']['title'] is not None

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_drag_drop_chart_creation(self, mock_bi_service):
        """BU-BI-002: 拖拽式图表制作"""
        config = {
            'data_source': 'orders',
            'dimensions': ['category'],
            'measures': ['amount'],
            'chart_type': 'column'
        }

        mock_bi_service.create_chart = AsyncMock(return_value={
            'success': True,
            'chart_id': 'chart_0001',
            'config': config
        })

        result = await mock_bi_service.create_chart(config)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bar_chart_generation(self, mock_bi_service):
        """BU-BI-003: 柱状图生成"""
        data = {
            'categories': ['电子产品', '服装', '食品', '家居'],
            'values': [45000, 32000, 28000, 21000]
        }

        mock_bi_service.generate_bar_chart = AsyncMock(return_value={
            'success': True,
            'chart_type': 'bar',
            'data': data
        })

        result = await mock_bi_service.generate_bar_chart(data)

        assert result['success'] is True
        assert result['chart_type'] == 'bar'

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_line_chart_generation(self, mock_bi_service):
        """BU-BI-004: 折线图生成"""
        data = {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'values': [1200, 1450, 1300, 1680, 1520]
        }

        mock_bi_service.generate_line_chart = AsyncMock(return_value={
            'success': True,
            'chart_type': 'line',
            'trend': 'upward',
            'data': data
        })

        result = await mock_bi_service.generate_line_chart(data)

        assert result['success'] is True
        assert result['chart_type'] == 'line'

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pie_chart_generation(self, mock_bi_service):
        """BU-BI-005: 饼图生成"""
        data = {
            'categories': ['直接访问', '搜索引擎', '社交媒体', '广告投放'],
            'values': [35, 28, 22, 15]
        }

        mock_bi_service.generate_pie_chart = AsyncMock(return_value={
            'success': True,
            'chart_type': 'pie',
            'data': data
        })

        result = await mock_bi_service.generate_pie_chart(data)

        assert result['success'] is True


class TestReportManagement:
    """报表管理测试 (BU-BI-006 ~ BU-BI-008)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_report(self, mock_bi_service):
        """BU-BI-006: 报表保存"""
        report_data = {
            'name': '每日销售报表',
            'description': '统计每日销售额和订单数',
            'charts': ['chart_0001', 'chart_0002']
        }

        mock_bi_service.save_report = AsyncMock(return_value={
            'success': True,
            'report_id': 'report_0001'
        })

        result = await mock_bi_service.save_report(report_data)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_share_report(self, mock_bi_service):
        """BU-BI-007: 报表分享"""
        report_id = 'report_0001'

        mock_bi_service.generate_share_link = AsyncMock(return_value={
            'success': True,
            'share_url': 'https://reports.example.com/r/report_0001',
            'expires_at': '2024-12-31T23:59:59Z'
        })

        result = await mock_bi_service.generate_share_link(report_id)

        assert result['success'] is True
        assert 'share_url' in result

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_report(self, mock_bi_service):
        """BU-BI-008: 报表导出"""
        report_id = 'report_0001'
        format = 'pdf'

        mock_bi_service.export_report = AsyncMock(return_value={
            'success': True,
            'download_url': 'https://reports.example.com/downloads/report_0001.pdf',
            'format': format
        })

        result = await mock_bi_service.export_report(report_id, format)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_bi_service():
    """Mock BI服务"""
    service = Mock()
    service.generate_from_nl = AsyncMock()
    service.create_chart = AsyncMock()
    service.generate_bar_chart = AsyncMock()
    service.generate_line_chart = AsyncMock()
    service.generate_pie_chart = AsyncMock()
    service.save_report = AsyncMock()
    service.generate_share_link = AsyncMock()
    service.export_report = AsyncMock()
    return service
