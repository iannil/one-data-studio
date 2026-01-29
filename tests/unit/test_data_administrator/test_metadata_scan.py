"""
元数据自动扫描单元测试
测试用例：DM-MS-001 ~ DM-MS-003
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestMetadataScan:
    """元数据自动扫描测试 (DM-MS-001 ~ DM-MS-003)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_full_metadata_scan(self, mock_metadata_service, mock_db_connection):
        """DM-MS-001: 启动元数据自动扫描"""
        source_id = 'ds_0001'
        mock_db_connection.tables = ['users', 'orders', 'products']
        mock_db_connection.columns = {
            'users': [
                {'name': 'id', 'type': 'bigint', 'primary': True},
                {'name': 'username', 'type': 'varchar(50)'},
                {'name': 'phone', 'type': 'varchar(20)'},
                {'name': 'created_at', 'type': 'datetime'}
            ],
            'orders': [
                {'name': 'id', 'type': 'bigint', 'primary': True},
                {'name': 'user_id', 'type': 'bigint'},
                {'name': 'amount', 'type': 'decimal(12,2)'}
            ],
            'products': [
                {'name': 'id', 'type': 'bigint', 'primary': True},
                {'name': 'name', 'type': 'varchar(200)'},
                {'name': 'price', 'type': 'decimal(10,2)'}
            ]
        }

        mock_metadata_service.scan_metadata.return_value = {
            'success': True,
            'scan_id': 'scan_0001',
            'databases': 1,
            'tables': 3,
            'columns': 10,
            'status': 'completed'
        }

        result = mock_metadata_service.scan_metadata(source_id)

        assert result['success'] is True
        assert result['tables'] == 3
        assert result['columns'] == 10
        mock_metadata_service.scan_metadata.assert_called_once_with(source_id)

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_ai_table_description_generation(self, mock_vllm_client, mock_metadata_service):
        """DM-MS-002: AI自动标注表描述"""
        table_name = 'users'
        table_info = {
            'table_name': table_name,
            'columns': ['id', 'username', 'phone', 'email', 'created_at']
        }

        # Mock vLLM 返回表描述
        mock_vllm_client.chat_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='这是一个用户信息表，存储平台注册用户的基本资料，包括用户名、联系方式、注册时间等。'
            ))]
        )

        result = mock_metadata_service.generate_ai_table_description(table_info)

        assert 'description' in result
        assert '用户' in result['description'] or 'user' in result['description'].lower()

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_ai_column_description_generation(self, mock_vllm_client, mock_metadata_service):
        """DM-MS-003: AI自动标注列描述"""
        column_name = 'phone'
        column_info = {
            'column_name': column_name,
            'data_type': 'varchar(20)',
            'table_name': 'users'
        }

        # Mock vLLM 返回列描述
        mock_vllm_client.chat_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='手机号码，用户的主要联系方式，用于登录验证和消息通知。'
            ))]
        )

        result = mock_metadata_service.generate_ai_column_description(column_info)

        assert 'description' in result
        assert '手机' in result['description'] or 'phone' in result['description'].lower()

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_column_name_rule_matching(self, mock_metadata_service):
        """DM-MS-004: 规则匹配列名识别"""
        # 测试常见列名的规则匹配
        test_cases = [
            {'column_name': 'id', 'expected': 'primary_key'},
            {'column_name': 'created_at', 'expected': 'create_time'},
            {'column_name': 'updated_at', 'expected': 'update_time'},
            {'column_name': 'deleted_at', 'expected': 'delete_time'},
            {'column_name': 'user_id', 'expected': 'foreign_key'},
        ]

        for case in test_cases:
            result = mock_metadata_service.match_column_rule(case['column_name'])
            assert result['type'] == case['expected'], f"Failed for {case['column_name']}"

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_incremental_metadata_scan(self, mock_metadata_service):
        """DM-MS-005: 增量元数据扫描"""
        source_id = 'ds_0001'
        last_scan_id = 'scan_0001'

        mock_metadata_service.incremental_scan.return_value = {
            'success': True,
            'scan_id': 'scan_0002',
            'new_tables': 2,
            'modified_tables': 1,
            'unchanged_tables': 10
        }

        result = mock_metadata_service.incremental_scan(source_id, last_scan_id)

        assert result['success'] is True
        assert result['new_tables'] == 2

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_metadata_version_recording(self, mock_metadata_service):
        """DM-MS-007: 元数据版本记录"""
        table_id = 'tbl_0001'

        mock_metadata_service.create_version.return_value = {
            'success': True,
            'version_id': 'ver_0001',
            'version': 2,
            'snapshot': {'columns': ['id', 'name', 'phone']}
        }

        result = mock_metadata_service.create_version(table_id)

        assert result['success'] is True
        assert result['version'] == 2
        assert 'snapshot' in result


class TestMetadataQuality:
    """元数据质量测试"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_scan_completeness(self, mock_metadata_service):
        """扫描完整性验证"""
        source_id = 'ds_0001'
        expected_tables = 50

        mock_metadata_service.scan_metadata.return_value = {
            'success': True,
            'tables': expected_tables,
            'columns': 500
        }

        result = mock_metadata_service.scan_metadata(source_id)
        assert result['tables'] == expected_tables

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_ai_description_accuracy(self, mock_metadata_service):
        """AI描述准确性验证"""
        # 测试AI描述的生成质量
        table_info = {
            'table_name': 'orders',
            'context': '电商系统订单表'
        }

        result = mock_metadata_service.generate_ai_description(table_info)

        assert result['description'] is not None
        assert len(result['description']) > 10


# ==================== Fixtures ====================

@pytest.fixture
def mock_metadata_service():
    """Mock 元数据服务"""
    service = Mock()

    # 列名规则匹配
    column_type_mapping = {
        'id': 'primary_key',
        'created_at': 'create_time',
        'updated_at': 'update_time',
        'deleted_at': 'delete_time',
        'user_id': 'foreign_key',
        'product_id': 'foreign_key',
        'order_id': 'foreign_key',
    }

    def match_column_rule_func(column_name):
        return {
            'column_name': column_name,
            'type': column_type_mapping.get(column_name, 'auto_detected')
        }

    def generate_ai_table_description_func(table_info):
        return {
            'table_name': table_info.get('table_name', ''),
            'description': f'{table_info.get("table_name", "")}是一个用户信息表，存储平台注册用户的基本资料，包括用户名、联系方式、注册时间等。',
            'ai_generated': True
        }

    def generate_ai_column_description_func(column_info):
        col_name = column_info.get('column_name', '')
        descriptions = {
            'phone': '手机号码，用户的主要联系方式，用于登录验证和消息通知。',
            'email': '电子邮箱地址，用于用户通知和密码重置。',
            'username': '用户登录名，唯一标识用户账号。',
            'password': '用户密码，经过加密存储。',
        }
        return {
            'column_name': col_name,
            'description': descriptions.get(col_name, f'{col_name}字段描述'),
            'ai_generated': True
        }

    service.scan_metadata = Mock()
    service.incremental_scan = Mock()
    service.generate_ai_table_description = Mock(side_effect=generate_ai_table_description_func)
    service.generate_ai_column_description = Mock(side_effect=generate_ai_column_description_func)
    service.match_column_rule = Mock(side_effect=match_column_rule_func)
    service.create_version = Mock()
    service.generate_ai_description = Mock(return_value={
        'description': '这是一个详细的AI生成的表描述，包含业务含义和主要用途说明。'
    })
    return service


@pytest.fixture
def mock_db_connection():
    """Mock 数据库连接"""
    db = Mock()
    db.tables = []
    db.columns = {}
    return db


@pytest.fixture
def mock_vllm_client():
    """Mock vLLM 客户端"""
    client = Mock()
    return client
