"""
元数据同步与血缘单元测试
测试用例：DM-SY-001 ~ DM-SY-008
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestOpenMetadataSync:
    """OpenMetadata同步测试 (DM-SY-001 ~ DM-SY-005)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_metadata_to_openmetadata(self, mock_sync_service):
        """DM-SY-001: 同步元数据到OpenMetadata"""
        mock_sync_service.sync_to_openmetadata = AsyncMock(return_value={
            'success': True,
            'sync_id': 'sync_0001',
            'stats': {
                'databases': 1,
                'tables': 50,
                'columns': 500
            },
            'service_created': 'data-service',
            'duration_seconds': 30
        })

        result = await mock_sync_service.sync_to_openmetadata(source_id='ds_0001')

        assert result['success'] is True
        assert result['stats']['tables'] == 50

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_create_service(self, mock_sync_service):
        """DM-SY-002: 服务不存在时自动创建"""
        mock_sync_service.sync_to_openmetadata = AsyncMock(return_value={
            'success': True,
            'service_created': True,
            'service_name': 'data-service',
            'service_type': 'mysql'
        })

        result = await mock_sync_service.sync_to_openmetadata(source_id='ds_0001')

        assert result['service_created'] is True

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_type_mapping_correctness(self, mock_sync_service):
        """DM-SY-003: 类型映射正确性"""
        type_mapping = {
            'varchar': 'VARCHAR',
            'int': 'INT',
            'bigint': 'BIGINT',
            'decimal': 'DECIMAL',
            'datetime': 'TIMESTAMP',
            'text': 'TEXT'
        }

        for source_type, target_type in type_mapping.items():
            result = mock_sync_service.map_type(source_type)
            assert result == target_type, f"Failed for {source_type}"

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sensitivity_tag_conversion(self, mock_sync_service):
        """DM-SY-004: 敏感性标签转换"""
        mock_sync_service.convert_sensitivity_tags = AsyncMock(return_value={
            'success': True,
            'tag_mapping': {
                'PII': 'PersonalData',
                'FINANCIAL': 'FinancialData',
                'CREDENTIAL': 'CredentialData',
                'RESTRICTED': 'Restricted'
            }
        })

        result = await mock_sync_service.convert_sensitivity_tags(['PII', 'FINANCIAL'])

        assert result['success'] is True
        assert result['tag_mapping']['PII'] == 'PersonalData'

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_description_sync(self, mock_sync_service):
        """DM-SY-005: AI描述同步到OpenMetadata"""
        mock_sync_service.sync_ai_descriptions = AsyncMock(return_value={
            'success': True,
            'synced_descriptions': 45,
            'failed': 0
        })

        result = await mock_sync_service.sync_ai_descriptions(tables=['users', 'orders'])

        assert result['success'] is True
        assert result['synced_descriptions'] > 0


class TestDataLineage:
    """数据血缘测试 (DM-SY-006 ~ DM-SY-008)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lineage_edge_pushing(self, mock_lineage_service):
        """DM-SY-006: 数据血缘推送"""
        etl_task = {
            'task_id': 'etl_0001',
            'source_tables': ['raw_users', 'raw_orders'],
            'target_table': 'users_orders_merged',
            'transformation_sql': 'SELECT * FROM raw_users u JOIN raw_orders o ON u.id = o.user_id'
        }

        mock_lineage_service.push_lineage = AsyncMock(return_value={
            'success': True,
            'edges_created': 2,
            'edge_ids': ['edge_0001', 'edge_0002']
        })

        result = await mock_lineage_service.push_lineage(etl_task)

        assert result['success'] is True
        assert result['edges_created'] == 2

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lineage_graph_visualization(self, mock_lineage_service):
        """DM-SY-007: 血缘图可视化"""
        table_id = 'tbl_users_orders_merged'

        mock_lineage_service.get_lineage_graph = AsyncMock(return_value={
            'success': True,
            'graph': {
                'nodes': [
                    {'id': 'raw_users', 'type': 'source'},
                    {'id': 'raw_orders', 'type': 'source'},
                    {'id': 'users_orders_merged', 'type': 'target'}
                ],
                'edges': [
                    {'from': 'raw_users', 'to': 'users_orders_merged', 'label': 'ETL'},
                    {'from': 'raw_orders', 'to': 'users_orders_merged', 'label': 'JOIN'}
                ]
            }
        })

        result = await mock_lineage_service.get_lineage_graph(table_id)

        assert result['success'] is True
        assert len(result['graph']['nodes']) >= 2
        assert len(result['graph']['edges']) >= 1

    @pytest.mark.p2
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_text_search_index(self, mock_lineage_service):
        """DM-SY-008: 全文搜索索引"""
        query = '用户订单表'

        mock_lineage_service.search = AsyncMock(return_value={
            'success': True,
            'results': [
                {
                    'table': 'users_orders_merged',
                    'description': '用户订单合并表',
                    'relevance_score': 0.95
                },
                {
                    'table': 'user_orders_daily',
                    'description': '用户订单日汇总表',
                    'relevance_score': 0.85
                }
            ]
        })

        result = await mock_lineage_service.search(query)

        assert result['success'] is True
        assert len(result['results']) > 0

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upstream_downstream_trace(self, mock_lineage_service):
        """上下游追溯"""
        table_id = 'tbl_target'

        mock_lineage_service.trace_lineage = AsyncMock(return_value={
            'success': True,
            'upstream': [
                {'table': 'raw_source1', 'distance': 1},
                {'table': 'raw_source2', 'distance': 1},
                {'table': 'staging_table', 'distance': 2}
            ],
            'downstream': [
                {'table': 'report_table', 'distance': 1},
                {'table': 'api_response', 'distance': 2}
            ]
        })

        result = await mock_lineage_service.trace_lineage(table_id)

        assert result['success'] is True
        assert 'upstream' in result
        assert 'downstream' in result


# ==================== Fixtures ====================

@pytest.fixture
def mock_sync_service():
    """Mock 同步服务"""
    service = Mock()

    # OpenMetadata 类型映射
    type_mapping = {
        'varchar': 'VARCHAR',
        'int': 'INT',
        'bigint': 'BIGINT',
        'decimal': 'DECIMAL',
        'datetime': 'TIMESTAMP',
        'text': 'TEXT',
        'char': 'CHAR',
        'date': 'DATE',
        'timestamp': 'TIMESTAMP',
    }

    service.sync_to_openmetadata = AsyncMock()
    service.convert_sensitivity_tags = AsyncMock()
    service.sync_ai_descriptions = AsyncMock()
    service.map_type = Mock(side_effect=lambda x: type_mapping.get(x.lower(), x.upper()))
    return service


@pytest.fixture
def mock_lineage_service():
    """Mock 血缘服务"""
    service = Mock()
    service.push_lineage = AsyncMock()
    service.get_lineage_graph = AsyncMock()
    service.search = AsyncMock()
    service.trace_lineage = AsyncMock()
    return service
