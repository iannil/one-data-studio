"""
数据分析师 - SQL Lab 单元测试
测试用例：AN-SQ-U-001 ~ AN-SQ-U-012

SQL Lab 是数据分析师角色执行 SQL 查询的核心功能。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestSQLQueryExecution:
    """SQL 查询执行测试 (AN-SQ-U-001 ~ AN-SQ-U-006)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_simple_select_query(self, mock_sql_lab_service):
        """AN-SQ-U-001: 执行简单 SELECT 查询"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT * FROM users LIMIT 10',
            'database': 'analytics'
        }

        mock_sql_lab_service.execute_query.return_value = {
            'success': True,
            'query_id': 'q_001',
            'status': 'completed',
            'rows': [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'}
            ],
            'row_count': 2,
            'execution_time_ms': 150
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is True
        assert result['status'] == 'completed'
        assert 'rows' in result

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_aggregation_query(self, mock_sql_lab_service):
        """AN-SQ-U-002: 执行聚合查询"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT region, COUNT(*) as user_count FROM users GROUP BY region',
            'database': 'analytics'
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is True
        assert result['row_count'] == 3

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_join_query(self, mock_sql_lab_service):
        """AN-SQ-U-003: 执行 JOIN 查询"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id LIMIT 10',
            'database': 'analytics'
        }

        mock_sql_lab_service.execute_query.return_value = {
            'success': True,
            'query_id': 'q_003',
            'status': 'completed',
            'rows': [
                {'name': 'Alice', 'amount': 199.99},
                {'name': 'Bob', 'amount': 59.99}
            ],
            'row_count': 2
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_query_with_timeout(self, mock_sql_lab_service):
        """AN-SQ-U-004: 执行带超时的查询"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT * FROM large_table',
            'database': 'analytics',
            'timeout_seconds': 30
        }

        mock_sql_lab_service.execute_query.return_value = {
            'success': False,
            'query_id': 'q_004',
            'status': 'timeout',
            'error': 'Query execution timeout after 30 seconds'
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is False
        assert result['status'] == 'timeout'

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_query_with_parameters(self, mock_sql_lab_service):
        """AN-SQ-U-005: 执行带参数的查询"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT * FROM users WHERE region = :region AND created_at >= :start_date',
            'database': 'analytics',
            'parameters': {
                'region': '华北',
                'start_date': '2024-01-01'
            }
        }

        mock_sql_lab_service.execute_query.return_value = {
            'success': True,
            'query_id': 'q_005',
            'status': 'completed',
            'rows': [
                {'id': 1, 'name': 'Alice', 'region': '华北'}
            ],
            'row_count': 1
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_execute_invalid_sql(self, mock_sql_lab_service):
        """AN-SQ-U-006: 执行无效 SQL"""
        query_request = {
            'datasource_id': 'ds_001',
            'sql': 'SELECT * FROM non_existent_table',
            'database': 'analytics'
        }

        mock_sql_lab_service.execute_query.return_value = {
            'success': False,
            'query_id': 'q_006',
            'status': 'error',
            'error': "Table 'non_existent_table' doesn't exist"
        }

        result = mock_sql_lab_service.execute_query(query_request)

        assert result['success'] is False
        assert result['status'] == 'error'
        assert 'error' in result


class TestSQLQueryManagement:
    """SQL 查询管理测试 (AN-SQ-U-007 ~ AN-SQ-U-010)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_save_query(self, mock_sql_lab_service):
        """AN-SQ-U-007: 保存查询"""
        save_request = {
            'name': '日销售额查询',
            'description': '每日销售总额统计',
            'datasource_id': 'ds_001',
            'database': 'analytics',
            'sql': 'SELECT DATE(order_time) as date, SUM(amount) as total FROM orders GROUP BY DATE(order_time)'
        }

        mock_sql_lab_service.save_query.return_value = {
            'success': True,
            'saved_query_id': 'sq_001'
        }

        result = mock_sql_lab_service.save_query(save_request)

        assert result['success'] is True
        assert 'saved_query_id' in result

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_list_saved_queries(self, mock_sql_lab_service):
        """AN-SQ-U-008: 列出已保存的查询"""
        mock_sql_lab_service.list_saved_queries.return_value = {
            'success': True,
            'queries': [
                {'saved_query_id': 'sq_001', 'name': '日销售额查询', 'created_at': '2024-01-01T00:00:00Z'},
                {'saved_query_id': 'sq_002', 'name': '用户统计', 'created_at': '2024-01-02T00:00:00Z'}
            ],
            'total': 2
        }

        result = mock_sql_lab_service.list_saved_queries()

        assert result['success'] is True
        assert len(result['queries']) == 2

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_get_saved_query(self, mock_sql_lab_service):
        """AN-SQ-U-009: 获取已保存的查询"""
        saved_query_id = 'sq_001'

        mock_sql_lab_service.get_saved_query.return_value = {
            'success': True,
            'saved_query_id': saved_query_id,
            'name': '日销售额查询',
            'sql': 'SELECT DATE(order_time) as date, SUM(amount) as total FROM orders GROUP BY DATE(order_time)',
            'datasource_id': 'ds_001',
            'database': 'analytics'
        }

        result = mock_sql_lab_service.get_saved_query(saved_query_id)

        assert result['success'] is True
        assert result['saved_query_id'] == saved_query_id

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_delete_saved_query(self, mock_sql_lab_service):
        """AN-SQ-U-010: 删除已保存的查询"""
        saved_query_id = 'sq_001'

        result = mock_sql_lab_service.delete_saved_query(saved_query_id)

        assert result['success'] is True


class TestSQLQueryHistory:
    """SQL 查询历史测试 (AN-SQ-U-011 ~ AN-SQ-U-012)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_get_query_history(self, mock_sql_lab_service):
        """AN-SQ-U-011: 获取查询历史"""
        mock_sql_lab_service.get_query_history.return_value = {
            'success': True,
            'history': [
                {'query_id': 'q_001', 'sql': 'SELECT * FROM users', 'executed_at': '2024-01-01T10:00:00Z', 'status': 'completed'},
                {'query_id': 'q_002', 'sql': 'SELECT COUNT(*) FROM orders', 'executed_at': '2024-01-01T10:05:00Z', 'status': 'completed'},
                {'query_id': 'q_003', 'sql': 'SELECT * FROM invalid_table', 'executed_at': '2024-01-01T10:10:00Z', 'status': 'error'}
            ],
            'total': 3
        }

        result = mock_sql_lab_service.get_query_history(limit=10)

        assert result['success'] is True
        assert len(result['history']) == 3

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_get_query_detail(self, mock_sql_lab_service):
        """AN-SQ-U-012: 获取查询详情"""
        query_id = 'q_001'

        mock_sql_lab_service.get_query_detail.return_value = {
            'success': True,
            'query_id': query_id,
            'sql': 'SELECT * FROM users LIMIT 10',
            'datasource_id': 'ds_001',
            'database': 'analytics',
            'status': 'completed',
            'row_count': 10,
            'execution_time_ms': 150,
            'executed_at': '2024-01-01T10:00:00Z'
        }

        result = mock_sql_lab_service.get_query_detail(query_id)

        assert result['success'] is True
        assert result['query_id'] == query_id


class TestSQLQueryExport:
    """SQL 查询导出测试 (AN-SQ-U-013 ~ AN-SQ-U-015)"""

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_export_query_result_to_csv(self, mock_sql_lab_service):
        """AN-SQ-U-013: 导出查询结果为 CSV"""
        query_id = 'q_001'

        mock_sql_lab_service.export_result.return_value = {
            'success': True,
            'export_id': 'exp_001',
            'format': 'csv',
            'download_url': '/api/v1/sql-lab/exports/exp_001',
            'file_size': 2048
        }

        result = mock_sql_lab_service.export_result(query_id, format='csv')

        assert result['success'] is True
        assert result['format'] == 'csv'
        assert 'download_url' in result

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_export_query_result_to_excel(self, mock_sql_lab_service):
        """AN-SQ-U-014: 导出查询结果为 Excel"""
        query_id = 'q_001'

        mock_sql_lab_service.export_result.return_value = {
            'success': True,
            'export_id': 'exp_002',
            'format': 'xlsx',
            'download_url': '/api/v1/sql-lab/exports/exp_002',
            'file_size': 4096
        }

        result = mock_sql_lab_service.export_result(query_id, format='xlsx')

        assert result['success'] is True
        assert result['format'] == 'xlsx'

    @pytest.mark.p1
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_export_query_result_to_json(self, mock_sql_lab_service):
        """AN-SQ-U-015: 导出查询结果为 JSON"""
        query_id = 'q_001'

        mock_sql_lab_service.export_result.return_value = {
            'success': True,
            'export_id': 'exp_003',
            'format': 'json',
            'download_url': '/api/v1/sql-lab/exports/exp_003',
            'file_size': 1024
        }

        result = mock_sql_lab_service.export_result(query_id, format='json')

        assert result['success'] is True
        assert result['format'] == 'json'


class TestSQLQueryValidation:
    """SQL 查询验证测试 (AN-SQ-U-016 ~ AN-SQ-U-017)"""

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_validate_sql_syntax(self, mock_sql_lab_service):
        """AN-SQ-U-016: 验证 SQL 语法"""
        sql = 'SELECT * FROM users WHERE id = 1'

        mock_sql_lab_service.validate_sql.return_value = {
            'success': True,
            'is_valid': True,
            'warnings': []
        }

        result = mock_sql_lab_service.validate_sql(sql)

        assert result['success'] is True
        assert result['is_valid'] is True

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_format_sql(self, mock_sql_lab_service):
        """AN-SQ-U-017: 格式化 SQL"""
        sql = 'select id,name from users where status=1'

        mock_sql_lab_service.format_sql.return_value = {
            'success': True,
            'formatted': 'SELECT\n  id,\n  name\nFROM users\nWHERE status = 1'
        }

        result = mock_sql_lab_service.format_sql(sql)

        assert result['success'] is True
        assert 'formatted' in result
        assert '\n' in result['formatted']


class TestSQLSchemaExplorer:
    """SQL 结构浏览测试 (AN-SQ-U-018 ~ AN-SQ-U-019)"""

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_list_databases(self, mock_sql_lab_service):
        """AN-SQ-U-018: 列出数据库"""
        datasource_id = 'ds_001'

        mock_sql_lab_service.list_databases.return_value = {
            'success': True,
            'databases': ['analytics', 'production', 'staging']
        }

        result = mock_sql_lab_service.list_databases(datasource_id)

        assert result['success'] is True
        assert len(result['databases']) == 3

    @pytest.mark.p2
    @pytest.mark.data_analyst
    @pytest.mark.unit
    def test_list_tables(self, mock_sql_lab_service):
        """AN-SQ-U-019: 列出表"""
        datasource_id = 'ds_001'
        database = 'analytics'

        mock_sql_lab_service.list_tables.return_value = {
            'success': True,
            'tables': [
                {'name': 'users', 'type': 'table', 'row_count': 10000},
                {'name': 'orders', 'type': 'table', 'row_count': 50000},
                {'name': 'products', 'type': 'table', 'row_count': 1000}
            ]
        }

        result = mock_sql_lab_service.list_tables(datasource_id, database)

        assert result['success'] is True
        assert len(result['tables']) == 3


# ==================== Fixtures ====================

@pytest.fixture
def mock_sql_lab_service():
    """Mock SQL Lab 服务"""
    service = Mock()

    def mock_execute(request):
        sql = request.get('sql', '')
        if 'non_existent_table' in sql:
            return {
                'success': False,
                'query_id': 'q_006',
                'status': 'error',
                'error': "Table 'non_existent_table' doesn't exist"
            }
        if request.get('timeout_seconds') == 30:
            return {
                'success': False,
                'query_id': 'q_004',
                'status': 'timeout',
                'error': 'Query execution timeout after 30 seconds'
            }
        # 处理聚合查询 (GROUP BY)
        if 'GROUP BY' in sql and 'region' in sql:
            return {
                'success': True,
                'query_id': 'q_002',
                'status': 'completed',
                'rows': [
                    {'region': '华北', 'user_count': 1500},
                    {'region': '华南', 'user_count': 1200},
                    {'region': '华东', 'user_count': 1800}
                ],
                'row_count': 3,
                'execution_time_ms': 150
            }
        return {
            'success': True,
            'query_id': 'q_001',
            'status': 'completed',
            'rows': [
                {'id': 1, 'name': 'Alice'}
            ],
            'row_count': 1,
            'execution_time_ms': 150
        }

    service.execute_query = Mock(side_effect=mock_execute)
    service.save_query = Mock(return_value={'success': True, 'saved_query_id': 'sq_001'})
    service.list_saved_queries = Mock()
    service.get_saved_query = Mock()
    service.delete_saved_query = Mock(return_value={'success': True})
    service.get_query_history = Mock()
    service.get_query_detail = Mock()
    service.export_result = Mock()
    service.validate_sql = Mock()
    service.format_sql = Mock()
    service.list_databases = Mock()
    service.list_tables = Mock()

    return service
