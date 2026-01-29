"""
数据资产检索单元测试
测试用例：BU-AS-001 ~ BU-AS-008
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestAssetSearch:
    """资产检索测试 (BU-AS-001 ~ BU-AS-005)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_natural_language_asset_search(self, mock_asset_search_service):
        """BU-AS-001: 自然语言资产检索"""
        query = '近30天活跃用户数据'

        mock_asset_search_service.search_nl = AsyncMock(return_value={
            'success': True,
            'query': query,
            'results': [
                {
                    'asset_id': 'asset_0001',
                    'name': '用户活跃度表',
                    'type': 'table',
                    'description': '记录用户近30天的活跃行为',
                    'relevance_score': 0.95,
                    'tags': ['用户数据', '行为分析']
                },
                {
                    'asset_id': 'asset_0002',
                    'name': 'DAU指标表',
                    'type': 'view',
                    'description': '日活跃用户聚合视图',
                    'relevance_score': 0.88,
                    'tags': ['指标', 'DAU']
                }
            ]
        })

        result = await mock_asset_search_service.search_nl(query)

        assert result['success'] is True
        assert len(result['results']) > 0

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_keyword_asset_search(self, mock_asset_search_service):
        """BU-AS-002: 关键词资产检索"""
        keyword = '用户'

        mock_asset_search_service.search_keyword = AsyncMock(return_value={
            'success': True,
            'keyword': keyword,
            'results': [
                {'asset_id': 'asset_0001', 'name': '用户表', 'type': 'table'},
                {'asset_id': 'asset_0002', 'name': '用户画像表', 'type': 'table'},
                {'asset_id': 'asset_0003', 'name': '用户行为表', 'type': 'table'}
            ],
            'total_count': 3
        })

        result = await mock_asset_search_service.search_keyword(keyword)

        assert result['success'] is True
        assert result['total_count'] > 0

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_asset_detail_view(self, mock_asset_search_service):
        """BU-AS-003: 资产详情查看"""
        asset_id = 'asset_0001'

        mock_asset_search_service.get_detail = AsyncMock(return_value={
            'success': True,
            'asset': {
                'asset_id': asset_id,
                'name': '用户表',
                'type': 'table',
                'description': '存储平台注册用户信息',
                'owner': 'data_admin',
                'department': '数据治理部',
                'source': 'MySQL',
                'row_count': 1000000,
                'size_mb': 256,
                'tags': ['用户数据', '核心表'],
                'created_at': '2024-01-01T10:00:00Z',
                'updated_at': '2024-01-15T10:00:00Z'
            }
        })

        result = await mock_asset_search_service.get_detail(asset_id)

        assert result['success'] is True
        assert result['asset']['owner'] is not None

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_asset_lineage_view(self, mock_asset_search_service):
        """BU-AS-005: 资产血缘查看"""
        asset_id = 'asset_0001'

        mock_asset_search_service.get_lineage = AsyncMock(return_value={
            'success': True,
            'lineage': {
                'upstream': [
                    {'asset_id': 'asset_source', 'name': '原始用户表', 'type': 'table'}
                ],
                'downstream': [
                    {'asset_id': 'asset_etl', 'name': '清洗后用户表', 'type': 'table'},
                    {'asset_id': 'asset_report', 'name': '用户报表', 'type': 'view'}
                ]
            }
        })

        result = await mock_asset_search_service.get_lineage(asset_id)

        assert result['success'] is True
        assert 'upstream' in result['lineage']


class TestAssetService:
    """资产服务测试 (BU-AS-006 ~ BU-AS-008)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_service_call(self, mock_asset_search_service):
        """BU-AS-006: 数据服务调用"""
        service_id = 'svc_0001'

        mock_asset_search_service.call_service = AsyncMock(return_value={
            'success': True,
            'service_id': service_id,
            'data': [
                {'user_id': 'U001', 'username': 'user1', 'clicks': 150},
                {'user_id': 'U002', 'username': 'user2', 'clicks': 89}
            ],
            'row_count': 2
        })

        result = await mock_asset_search_service.call_service(service_id, params={})

        assert result['success'] is True
        assert len(result['data']) > 0

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_export(self, mock_asset_search_service):
        """BU-AS-007: 数据导出"""
        asset_id = 'asset_0001'
        export_format = 'csv'

        mock_asset_search_service.export_data = AsyncMock(return_value={
            'success': True,
            'download_url': 'https://storage.example.com/exports/asset_0001.csv',
            'format': export_format,
            'expires_at': '2024-01-16T10:00:00Z'
        })

        result = await mock_asset_search_service.export_data(asset_id, export_format)

        assert result['success'] is True
        assert 'download_url' in result

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_call_history(self, mock_asset_search_service):
        """BU-AS-008: 服务调用记录"""
        service_id = 'svc_0001'

        mock_asset_search_service.get_call_history = AsyncMock(return_value={
            'success': True,
            'service_id': service_id,
            'calls': [
                {
                    'call_id': 'call_0001',
                    'caller': 'user_0001',
                    'called_at': '2024-01-15T10:00:00Z',
                    'row_count': 100
                },
                {
                    'call_id': 'call_0002',
                    'caller': 'user_0002',
                    'called_at': '2024-01-15T11:00:00Z',
                    'row_count': 50
                }
            ],
            'total_calls': 2
        })

        result = await mock_asset_search_service.get_call_history(service_id)

        assert result['success'] is True
        assert result['total_calls'] > 0


# ==================== Fixtures ====================

@pytest.fixture
def mock_asset_search_service():
    """Mock 资产检索服务"""
    service = Mock()
    service.search_nl = AsyncMock()
    service.search_keyword = AsyncMock()
    service.get_detail = AsyncMock()
    service.get_lineage = AsyncMock()
    service.call_service = AsyncMock()
    service.export_data = AsyncMock()
    service.get_call_history = AsyncMock()
    return service
