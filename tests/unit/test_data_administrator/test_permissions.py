"""
权限与安全管理单元测试
测试用例：DM-PM-001 ~ DM-PM-004
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestPermissionManagement:
    """权限管理测试 (DM-PM-001 ~ DM-PM-002)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_configure_role_permissions(self, mock_permission_service):
        """DM-PM-001: 配置角色权限"""
        role_data = {
            'role_name': '数据只读用户',
            'role_code': 'data_reader',
            'permissions': [
                'metadata:read',
                'asset:read',
                'datasource:read'
            ]
        }

        mock_permission_service.create_role.return_value = {
            'success': True,
            'role_id': 'role_0001',
            'role_code': 'data_reader'
        }

        result = mock_permission_service.create_role(role_data)

        assert result['success'] is True
        assert 'role_id' in result

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_dynamic_permission_assignment(self, mock_permission_service):
        """DM-PM-002: 动态权限分配"""
        user_id = 'user_0001'
        scenario = 'data_analysis'

        mock_permission_service.assign_dynamic_permissions.return_value = {
            'success': True,
            'permissions': [
                'table:users:read',
                'table:orders:read',
                'column:phone:masked'
            ]
        }

        result = mock_permission_service.assign_dynamic_permissions(user_id, scenario)

        assert result['success'] is True
        assert len(result['permissions']) > 0


class TestSensitiveDataAccessControl:
    """敏感数据访问控制测试 (DM-PM-003)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_authorized_user_access_sensitive_data(self, mock_permission_service):
        """授权用户访问敏感数据"""
        user = UserFactory(role='data_administrator')
        resource = 'sensitive_column:users.phone'
        action = 'read'

        mock_permission_service.check_access.return_value = {
            'allowed': True,
            'access_type': 'plain'
        }

        result = mock_permission_service.check_access(user, resource, action)

        assert result['allowed'] is True

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_unauthorized_user_access_denied(self, mock_permission_service):
        """DM-PM-003: 非授权用户访问敏感数据被拒绝"""
        user = UserFactory(role='business_user')
        resource = 'sensitive_column:users.phone'
        action = 'read'

        mock_permission_service.check_access.return_value = {
            'allowed': False,
            'reason': 'Insufficient permissions for sensitive data access'
        }

        result = mock_permission_service.check_access(user, resource, action)

        assert result['allowed'] is False
        assert 'reason' in result

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_return_masked_data_for_limited_access(self, mock_permission_service):
        """有限权限用户返回脱敏数据"""
        user = UserFactory(role='data_engineer')
        resource = 'sensitive_column:users.phone'
        action = 'read'

        mock_permission_service.check_access.return_value = {
            'allowed': True,
            'access_type': 'masked',
            'masking_rule': 'partial_mask:3***4'
        }

        result = mock_permission_service.check_access(user, resource, action)

        assert result['allowed'] is True
        assert result['access_type'] == 'masked'

    @pytest.mark.p0
    @pytest.mark.security
    @pytest.mark.unit
    def test_permission_inheritance(self, mock_permission_service):
        """权限继承测试"""
        parent_role = 'data_administrator'
        child_role = 'data_reader'

        mock_permission_service.get_inherited_permissions.return_value = {
            'permissions': [
                'metadata:read',
                'asset:read'
            ]
        }

        result = mock_permission_service.get_inherited_permissions(child_role)

        assert len(result['permissions']) >= 2


class TestDataAudit:
    """数据审计测试 (DM-PM-004)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_data_change_tracing(self, mock_audit_service):
        """DM-PM-004: 数据留痕追溯"""
        change_event = {
            'user_id': 'user_0001',
            'action': 'update',
            'resource_type': 'table',
            'resource_id': 'users',
            'old_value': {'status': 'active'},
            'new_value': {'status': 'inactive'}
        }

        mock_audit_service.log_change.return_value = {
            'success': True,
            'log_id': 'log_0001'
        }

        result = mock_audit_service.log_change(change_event)

        assert result['success'] is True

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_trail_retrieval(self, mock_audit_service):
        """追溯链查询"""
        resource_id = 'users'

        mock_audit_service.get_trail.return_value = {
            'resource_id': resource_id,
            'changes': [
                {
                    'log_id': 'log_0001',
                    'user_id': 'user_0001',
                    'action': 'create',
                    'timestamp': '2024-01-01T10:00:00Z',
                    'details': {'columns': ['id', 'name', 'phone']}
                },
                {
                    'log_id': 'log_0002',
                    'user_id': 'user_0002',
                    'action': 'update',
                    'timestamp': '2024-01-02T11:00:00Z',
                    'details': {'added_column': 'email'}
                }
            ]
        }

        result = mock_audit_service.get_trail(resource_id)

        assert len(result['changes']) >= 2
        assert result['changes'][0]['action'] == 'create'

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_complete_audit_chain(self, mock_audit_service):
        """完整审计链"""
        # 测试从创建到修改的完整追溯
        resource_id = 'orders'

        mock_audit_service.get_full_chain.return_value = {
            'resource_id': resource_id,
            'chain': [
                {'event': 'created', 'user': 'user_0001', 'time': '2024-01-01T10:00:00Z'},
                {'event': 'metadata_updated', 'user': 'user_0002', 'time': '2024-01-02T11:00:00Z'},
                {'event': 'sensitivity_tagged', 'user': 'user_0001', 'time': '2024-01-03T12:00:00Z'},
                {'event': 'permission_modified', 'user': 'user_0003', 'time': '2024-01-04T13:00:00Z'}
            ]
        }

        result = mock_audit_service.get_full_chain(resource_id)

        assert len(result['chain']) == 4
        # 验证链的顺序
        assert result['chain'][0]['event'] == 'created'
        assert result['chain'][-1]['event'] == 'permission_modified'


class TestPermissionScopes:
    """权限范围测试"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_row_level_permission(self, mock_permission_service):
        """行级权限控制"""
        user_id = 'user_0001'
        table = 'orders'

        mock_permission_service.get_row_filter.return_value = {
            'filter': f"created_by = '{user_id}'",
            'allowed_rows': 'user_owned_only'
        }

        result = mock_permission_service.get_row_filter(user_id, table)

        assert 'filter' in result
        assert user_id in result['filter']

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_column_level_permission(self, mock_permission_service):
        """列级权限控制"""
        user_id = 'user_0001'
        table = 'users'

        mock_permission_service.get_allowed_columns.return_value = {
            'allowed_columns': ['id', 'username', 'created_at'],
            'denied_columns': ['phone', 'id_card', 'email'],
            'masked_columns': []
        }

        result = mock_permission_service.get_allowed_columns(user_id, table)

        assert 'phone' in result['denied_columns']
        assert 'id_card' in result['denied_columns']


# ==================== Fixtures ====================

@pytest.fixture
def mock_permission_service():
    """Mock 权限服务"""
    service = Mock()
    service.create_role = Mock(return_value={'success': True, 'role_id': 'role_0001'})
    service.assign_dynamic_permissions = Mock()
    service.check_access = Mock()
    service.get_inherited_permissions = Mock()
    service.get_row_filter = Mock()
    service.get_allowed_columns = Mock()
    return service


@pytest.fixture
def mock_audit_service():
    """Mock 审计服务"""
    service = Mock()
    service.log_change = Mock(return_value={'success': True, 'log_id': 'log_0001'})
    service.get_trail = Mock()
    service.get_full_chain = Mock()
    return service


def UserFactory(role='data_administrator'):
    """测试用户工厂"""
    return {
        'user_id': 'user_0001',
        'username': 'testuser',
        'role': role,
        'status': 'active'
    }
