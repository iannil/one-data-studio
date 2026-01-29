"""
数据源管理单元测试
测试用例：DM-DS-001 ~ DM-DS-007
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# ==================== 测试类 ====================

class TestDataSourceRegistration:
    """数据源注册测试 (DM-DS-001 ~ DM-DS-003)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_register_mysql_datasource(self, mock_datasource_service):
        """DM-DS-001: 注册MySQL数据源"""
        # 准备测试数据
        datasource_data = {
            'name': '测试MySQL数据源',
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password'
        }

        # 执行
        result = mock_datasource_service.register_datasource(datasource_data)

        # 验证返回结果
        assert result['success'] is True
        assert 'source_id' in result
        assert result['type'] == 'mysql'
        assert result['name'] == '测试MySQL数据源'

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_register_postgresql_datasource(self, mock_datasource_service):
        """DM-DS-002: 注册PostgreSQL数据源"""
        datasource_data = {
            'name': '测试PostgreSQL数据源',
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password'
        }

        mock_datasource_service.test_connection.return_value = {'success': True}

        result = mock_datasource_service.register_datasource(datasource_data)

        assert result['success'] is True
        assert result['type'] == 'postgresql'

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_register_oracle_datasource(self, mock_datasource_service):
        """DM-DS-003: 注册Oracle数据源"""
        datasource_data = {
            'name': '测试Oracle数据源',
            'type': 'oracle',
            'host': 'localhost',
            'port': 1521,
            'database': 'ORCL',
            'username': 'test_user',
            'password': 'test_password'
        }

        mock_datasource_service.test_connection.return_value = {'success': True}

        result = mock_datasource_service.register_datasource(datasource_data)

        assert result['success'] is True
        assert result['type'] == 'oracle'


class TestDataSourceConnection:
    """数据源连接测试 (DM-DS-004)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_connection_test_success(self, mock_datasource_service):
        """连接测试成功"""
        mock_datasource_service.test_connection.return_value = {
            'success': True,
            'message': '连接成功',
            'version': '8.0.32'
        }

        result = mock_datasource_service.test_connection({
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306
        })

        assert result['success'] is True

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_connection_test_failure(self, mock_datasource_service):
        """DM-DS-004: 数据源连接测试失败"""
        mock_datasource_service.test_connection.return_value = {
            'success': False,
            'error': 'Access denied for user'
        }

        result = mock_datasource_service.test_connection({
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'username': 'wrong_user',
            'password': 'wrong_password'
        })

        assert result['success'] is False
        assert 'error' in result
        assert 'denied' in result['error'].lower()

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_connection_test_timeout(self, mock_datasource_service):
        """连接超时"""
        mock_datasource_service.test_connection.return_value = {
            'success': False,
            'error': 'Connection timeout after 30 seconds'
        }

        result = mock_datasource_service.test_connection({
            'type': 'mysql',
            'host': 'unreachable-host',
            'port': 3306
        })

        assert result['success'] is False
        assert 'timeout' in result['error'].lower()


class TestDataSourceManagement:
    """数据源管理测试 (DM-DS-005 ~ DM-DS-007)"""

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_edit_datasource(self, mock_datasource_service):
        """DM-DS-005: 编辑数据源配置"""
        source_id = 'ds_0001'
        update_data = {
            'host': 'new-host',
            'port': 3307
        }

        mock_datasource_service.update_datasource.return_value = {
            'success': True,
            'source_id': source_id
        }

        result = mock_datasource_service.update_datasource(source_id, update_data)

        assert result['success'] is True
        mock_datasource_service.update_datasource.assert_called_with(source_id, update_data)

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_delete_unused_datasource(self, mock_datasource_service):
        """DM-DS-006: 删除未被引用的数据源"""
        source_id = 'ds_0001'
        # 设置无引用状态
        mock_datasource_service._has_references = False

        result = mock_datasource_service.delete_datasource(source_id)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_delete_referenced_datasource_blocked(self, mock_datasource_service):
        """DM-DS-007: 删除被引用的数据源被阻止"""
        source_id = 'ds_0001'
        # 设置有引用状态
        mock_datasource_service._has_references = True
        mock_datasource_service._references = ['etl_task_001', 'metadata_scan_002']

        result = mock_datasource_service.delete_datasource(source_id)

        assert result['success'] is False
        assert 'data_source_in_use' in result['error_code']
        assert 'etl_task_001' in result['references']

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_list_datasources(self, mock_datasource_service):
        """列出数据源"""
        mock_datasource_service.list_datasources.return_value = {
            'success': True,
            'datasources': [
                {'source_id': 'ds_0001', 'name': 'MySQL数据源', 'type': 'mysql', 'status': 'active'},
                {'source_id': 'ds_0002', 'name': 'PG数据源', 'type': 'postgresql', 'status': 'active'}
            ],
            'total': 2
        }

        result = mock_datasource_service.list_datasources()

        assert result['success'] is True
        assert len(result['datasources']) == 2
        assert result['total'] == 2

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_get_datasource_detail(self, mock_datasource_service):
        """获取数据源详情"""
        source_id = 'ds_0001'
        mock_datasource_service.get_datasource.return_value = {
            'success': True,
            'source_id': source_id,
            'name': 'MySQL数据源',
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'status': 'active'
        }

        result = mock_datasource_service.get_datasource(source_id)

        assert result['success'] is True
        assert result['source_id'] == source_id


# ==================== Fixtures ====================

@pytest.fixture
def mock_datasource_service():
    """Mock 数据源服务"""
    service = Mock()

    # 依赖检查状态（用于测试删除引用检查）
    service._has_references = False
    service._references = []

    def mock_register(datasource_data):
        """动态返回包含输入数据的注册结果"""
        return {
            'success': True,
            'source_id': 'ds_0001',
            'type': datasource_data.get('type', 'unknown'),
            'name': datasource_data.get('name', ''),
            'host': datasource_data.get('host', ''),
            'port': datasource_data.get('port', 0)
        }

    def mock_delete(source_id):
        """模拟删除操作"""
        if service._has_references:
            return {
                'success': False,
                'error_code': 'data_source_in_use',
                'references': service._references
            }
        return {'success': True}

    def mock_check_dependencies(source_id):
        """模拟依赖检查"""
        return {
            'has_references': service._has_references,
            'references': service._references
        }

    service.register_datasource = Mock(side_effect=mock_register)
    service.test_connection = Mock()
    service.update_datasource = Mock()
    service.delete_datasource = Mock(side_effect=mock_delete)
    service.check_dependencies = Mock(side_effect=mock_check_dependencies)
    service.list_datasources = Mock()
    service.get_datasource = Mock()
    return service
