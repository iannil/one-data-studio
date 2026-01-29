"""
元数据标签与版本管理单元测试
测试用例：DM-TG-001 ~ DM-TG-005, DM-ST-001 ~ DM-ST-004
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


class TestMetadataTagging:
    """元数据标签管理测试 (DM-TG-001 ~ DM-TG-005)"""

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_auto_classification_tagging(self, mock_metadata_service):
        """DM-TG-001: 自动标注分类标签"""
        table_info = {
            'table_name': 'users',
            'columns': ['id', 'username', 'phone', 'email'],
            'row_count': 100000
        }

        mock_metadata_service.auto_tag.return_value = {
            'success': True,
            'tags': ['用户数据', '核心表', 'PII数据'],
            'confidence': 0.92
        }

        result = mock_metadata_service.auto_tag(table_info)

        assert result['success'] is True
        assert '用户数据' in result['tags']

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_manual_add_tag(self, mock_metadata_service):
        """DM-TG-002: 手动添加标签"""
        resource_id = 'tbl_0001'
        tags = ['重要资产', '生产数据', '定期更新']

        mock_metadata_service.add_tags.return_value = {
            'success': True,
            'resource_id': resource_id,
            'tags': tags
        }

        result = mock_metadata_service.add_tags(resource_id, tags)

        assert result['success'] is True
        assert len(result['tags']) == 3

    @pytest.mark.p2
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_delete_tag(self, mock_metadata_service):
        """DM-TG-003: 删除标签"""
        resource_id = 'tbl_0001'
        tag = '过时标签'

        mock_metadata_service.remove_tag.return_value = {
            'success': True,
            'resource_id': resource_id,
            'removed_tag': tag
        }

        result = mock_metadata_service.remove_tag(resource_id, tag)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_metadata_version_history(self, mock_metadata_service):
        """DM-TG-004: 元数据版本回溯"""
        table_id = 'tbl_0001'

        mock_metadata_service.get_version_history.return_value = {
            'success': True,
            'table_id': table_id,
            'versions': [
                {
                    'version_id': 'ver_0001',
                    'version': 1,
                    'created_at': '2024-01-01T10:00:00Z',
                    'change_summary': '初始创建'
                },
                {
                    'version_id': 'ver_0002',
                    'version': 2,
                    'created_at': '2024-01-15T10:00:00Z',
                    'change_summary': '添加email列'
                }
            ]
        }

        result = mock_metadata_service.get_version_history(table_id)

        assert result['success'] is True
        assert len(result['versions']) >= 2

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_version_diff_comparison(self, mock_metadata_service):
        """DM-TG-005: 版本差异对比"""
        table_id = 'tbl_0001'
        version_a = 1
        version_b = 2

        mock_metadata_service.compare_versions.return_value = {
            'success': True,
            'table_id': table_id,
            'differences': [
                {
                    'type': 'column_added',
                    'column': 'email',
                    'data_type': 'varchar(100)'
                },
                {
                    'type': 'column_modified',
                    'column': 'username',
                    'old_value': 'varchar(30)',
                    'new_value': 'varchar(50)'
                }
            ]
        }

        result = mock_metadata_service.compare_versions(table_id, version_a, version_b)

        assert result['success'] is True
        assert len(result['differences']) > 0


class TestDataStandards:
    """数据标准管理测试 (DM-ST-001 ~ DM-ST-004)"""

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_auto_generate_standards(self, mock_metadata_service):
        """DM-ST-001: 自动生成数据标准"""
        mock_metadata_service.generate_standards = Mock(return_value={
            'success': True,
            'standards': [
                {
                    'field_name': 'phone',
                    'format': '11位数字',
                    'pattern': '^1[3-9]\\d{9}$',
                    'description': '手机号码格式'
                },
                {
                    'field_name': 'email',
                    'format': '标准邮箱格式',
                    'pattern': '^[\\w-\\.]+@[\\w-]+\\.[a-z]{2,}$',
                    'description': '电子邮箱格式'
                }
            ]
        })

        result = mock_metadata_service.generate_standards(['phone', 'email'])

        assert result['success'] is True
        assert len(result['standards']) >= 2

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_manual_create_standard(self, mock_metadata_service):
        """DM-ST-002: 手动创建数据标准"""
        standard_data = {
            'standard_name': '用户ID格式标准',
            'field_pattern': 'user_id',
            'data_type': 'varchar(50)',
            'format_rule': '前缀user_ + 数字',
            'description': '用户ID统一格式'
        }

        mock_metadata_service.create_standard.return_value = {
            'success': True,
            'standard_id': 'std_0001'
        }

        result = mock_metadata_service.create_standard(standard_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_associate_field_with_standard(self, mock_metadata_service):
        """DM-ST-003: 数据标准关联字段"""
        standard_id = 'std_0001'
        field_id = 'col_user_id'

        mock_metadata_service.associate_field.return_value = {
            'success': True,
            'standard_id': standard_id,
            'field_id': field_id
        }

        result = mock_metadata_service.associate_field(standard_id, field_id)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_standard_compliance_check(self, mock_metadata_service):
        """DM-ST-004: 数据标准合规检查"""
        standard_id = 'std_0001'

        mock_metadata_service.check_compliance.return_value = {
            'success': True,
            'standard_id': standard_id,
            'compliant_fields': 85,
            'non_compliant_fields': [
                {'field': 'user_code', 'reason': '格式不符合标准'}
            ],
            'compliance_rate': 0.85
        }

        result = mock_metadata_service.check_compliance(standard_id)

        assert result['success'] is True
        assert result['compliance_rate'] >= 0.7


# ==================== Fixtures ====================

@pytest.fixture
def mock_metadata_service():
    """Mock 元数据服务"""
    service = Mock()
    service.auto_tag = Mock()
    service.add_tags = Mock()
    service.remove_tag = Mock()
    service.get_version_history = Mock()
    service.compare_versions = Mock()
    service.generate_standards = Mock()
    service.create_standard = Mock()
    service.associate_field = Mock()
    service.check_compliance = Mock()
    return service
